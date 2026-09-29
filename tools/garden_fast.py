#!/usr/bin/env python3
"""Pipelined garden fights with the MCP server's smart selector (Python port).

The MCP tool starts a fight, then waits for it: the server needs ~5-15 s to
generate a V10 (Python) fight, so one leek plays one fight per ~13 s. Here
each leek keeps up to --inflight fights generating at once, all leeks in
parallel, under a shared request bucket (LW+: 10 req/s, we use 9).

Selector = server.js `smart` strategy, same data (tools/fight_history_<leek>.db):
recency-weighted win rate over the last 10 fights (decay 0.8), beatable >= 0.7,
dangerous <= 0.45 (>= 2 fights, else unknown); pool = beatable + unknown +
first half of even, weighted random favouring earlier entries; empty pool ->
least dangerous; an opponent that beat us twice this session is banned.
Results are written to the same DB (fight_history + opponent_stats), so the
MCP tool and the nightly cron keep one history.

    python3 tools/garden_fast.py --per-leek 25                  # all four main leeks
    python3 tools/garden_fast.py --per-leek 25 --leeks KurtGodel --inflight 4
"""
import argparse, datetime, os, random, sqlite3, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lw_api import LWSession

LEEKS = {'AdaLovelace': 20443, 'EdsgerDijkstra': 129288, 'KurtGodel': 129295, 'MargaretHamilton': 129296}
BEATABLE, DANGEROUS, WINDOW, DECAY, SESSION_LOSS_LIMIT = 0.7, 0.45, 10, 0.8, 2


class Bucket:
    def __init__(self, rate):
        self.rate, self.lock, self.next = rate, threading.Lock(), time.time()

    def take(self):
        with self.lock:
            now = time.time(); wait = self.next - now
            self.next = max(now, self.next) + 1.0 / self.rate
        if wait > 0:
            time.sleep(wait)


class DB:
    def __init__(self, lid):
        self.c = sqlite3.connect(os.path.join(HERE, 'fight_history_%d.db' % lid), check_same_thread=False)
        self.c.execute('CREATE TABLE IF NOT EXISTS fight_history (fight_id INTEGER PRIMARY KEY, opponent_id INTEGER, '
                       'opponent_name TEXT, opponent_level INTEGER, result TEXT, fight_url TEXT, timestamp TEXT)')
        self.c.execute('CREATE TABLE IF NOT EXISTS opponent_stats (opponent_id INTEGER PRIMARY KEY, opponent_name TEXT, '
                       'opponent_level INTEGER, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, draws INTEGER DEFAULT 0, '
                       'total_fights INTEGER DEFAULT 0, win_rate REAL DEFAULT 0.0, last_fought TEXT, last_updated TEXT)')
        self.c.commit()

    def status(self, oid):
        """(status, win score) as server.js getOpponentStats / categorizeOpponents."""
        r = self.c.execute('SELECT total_fights, win_rate FROM opponent_stats WHERE opponent_id=?', (oid,)).fetchone()
        if not r:
            return 'unknown', 0.5
        total, life = r[0] or 0, r[1] or 0.0
        rows = self.c.execute('SELECT result FROM fight_history WHERE opponent_id=? ORDER BY timestamp DESC LIMIT ?',
                              (oid, WINDOW)).fetchall()
        eff = life
        if rows:
            ww = ws = 0.0; w = 1.0
            for (res,) in rows:
                ww += w * (1 if res == 'WIN' else 0); ws += w; w *= DECAY
            eff = ww / ws
        if total < 2:
            return 'unknown', eff
        if eff >= BEATABLE:
            return 'beatable', eff
        if eff <= DANGEROUS:
            return 'dangerous', eff
        return 'even', eff

    def record(self, fid, opp, result):
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        self.c.execute('INSERT OR REPLACE INTO fight_history (fight_id, opponent_id, opponent_name, opponent_level, '
                       'result, fight_url, timestamp) VALUES (?,?,?,?,?,?,?)',
                       (fid, opp['id'], opp.get('name', ''), opp.get('level') or 0, result,
                        'https://leekwars.com/fight/%d' % fid, now))
        self.c.execute('''INSERT OR REPLACE INTO opponent_stats (opponent_id, opponent_name, opponent_level, wins, losses,
                          draws, total_fights, win_rate, last_fought, last_updated)
                          SELECT ?, ?, ?, SUM(result='WIN'), SUM(result='LOSS'), SUM(result='DRAW'), COUNT(*),
                          CAST(SUM(result='WIN') AS REAL) / COUNT(*), ?, ? FROM fight_history WHERE opponent_id=?''',
                       (opp['id'], opp.get('name', ''), opp.get('level') or 0, now, now, opp['id']))
        self.c.commit()


def reconcile(lw, db, lid, get):
    """Record finished garden fights from the leek's server history that the
    DB lacks (fights started by a tool that timed out or crashed)."""
    have = {r[0] for r in db.c.execute('SELECT fight_id FROM fight_history')}
    h = get('/history/get-leek-history/%d' % lid) or {}
    n = 0
    for f in h.get('fights', []):
        if f.get('type') != 0 or f.get('context') != 2 or f.get('status') != 2 or f['id'] in have:
            continue
        mine1 = any(l['id'] == lid for l in f.get('leeks1') or [])
        opp = ((f.get('leeks2') if mine1 else f.get('leeks1')) or [{}])[0]
        if not opp.get('id'):
            continue
        team = 1 if mine1 else 2
        res = 'DRAW' if f.get('winner') == 0 else ('WIN' if f.get('winner') == team else 'LOSS')
        db.record(f['id'], {'id': opp['id'], 'name': opp.get('name', ''), 'level': opp.get('level') or 0}, res)
        n += 1
    return n


def select(db, opponents, banned):
    elig = [o for o in opponents if o['id'] not in banned] or opponents
    cat = {'beatable': [], 'unknown': [], 'even': [], 'dangerous': []}
    for o in elig:
        st, sc = db.status(o['id']); o['_score'] = sc; cat[st].append(o)
    even = cat['even']
    pool = cat['beatable'] + cat['unknown'] + even[:(len(even) + 1) // 2]
    if not pool:
        allp = cat['beatable'] + cat['unknown'] + even + cat['dangerous']
        return max(allp, key=lambda o: o['_score']) if allp else None
    weights = [max(1, len(pool) - i) for i in range(len(pool))]
    return random.choices(pool, weights=weights)[0]


def run_leek(name, lid, n, inflight, bucket, lock, out):
    lw = LWSession('main'); db = DB(lid)

    def get(path):
        bucket.take(); return lw.get(path)

    def post(path, data):
        bucket.take(); return lw.s.post('https://leekwars.com/api' + path, data=data).json()

    started = 0; pending = {}; rec = {'W': 0, 'L': 0, 'D': 0}; losses = {}; banned = set(); errors = 0
    try:
        fixed = reconcile(lw, db, lid, get)
        if fixed:
            print('  %s: %d unrecorded fights added to the history DB' % (name, fixed), flush=True)
    except Exception as ex:
        print('  %s: reconcile failed %s' % (name, ex), flush=True)
    while started < n or pending:
        # collect finished fights
        for fid, opp in list(pending.items()):
            f = get('/fight/get/%d' % fid); f = f.get('fight', f) if isinstance(f, dict) else {}
            if f.get('status') != 2:
                continue
            team = 1 if any(l['id'] == lid for l in f.get('leeks1') or []) else 2
            res = 'DRAW' if f.get('winner') == 0 else ('WIN' if f.get('winner') == team else 'LOSS')
            try:
                db.record(fid, opp, res)
            except Exception as ex:
                print('  %s: could not record %d (%s)' % (name, fid, ex), flush=True)
            del pending[fid]
            rec[res[0]] += 1
            if res == 'LOSS':
                losses[opp['id']] = losses.get(opp['id'], 0) + 1
                if losses[opp['id']] >= SESSION_LOSS_LIMIT:
                    banned.add(opp['id'])
        # start new fights while the pipe has room
        while started < n and len(pending) < inflight and errors < 10:
            ops = (get('/garden/get-leek-opponents/%d' % lid) or {}).get('opponents') or []
            tgt = select(db, ops, banned) if ops else None
            if not tgt:
                errors += 1; time.sleep(2); break
            r = post('/garden/start-solo-fight', {'leek_id': lid, 'target_id': tgt['id']})
            fid = r.get('fight') if isinstance(r, dict) else (r if isinstance(r, int) else None)
            if not fid:
                err = r.get('error') if isinstance(r, dict) else r
                if err in ('too_many_fights', 'no_more_fights'):
                    n = started; break
                errors += 1; time.sleep(1); continue
            pending[fid] = tgt; started += 1
        if errors >= 10 and not pending:
            break
        time.sleep(1)
    with lock:
        out[name] = (started, rec)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--per-leek', type=int, default=25)
    ap.add_argument('--leeks', default=','.join(LEEKS))
    ap.add_argument('--inflight', type=int, default=4, help='fights generating at once per leek')
    ap.add_argument('--rate', type=float, default=9.0)
    a = ap.parse_args()
    lw = LWSession('main')
    names = a.leeks.split(',')

    def talent(lid):
        l = lw.get('/leek/get/%d' % lid); l = l.get('leek', l); return int(l.get('talent', 0))
    before = {n: talent(LEEKS[n]) for n in names}
    g = lw.get('/garden/get'); g = g.get('garden', g)
    print('credits %s' % g.get('fights'), flush=True)
    t0 = time.time(); bucket = Bucket(a.rate); lock = threading.Lock(); out = {}
    th = [threading.Thread(target=run_leek, args=(n, LEEKS[n], a.per_leek, a.inflight, bucket, lock, out)) for n in names]
    for t in th:
        t.start()
    for t in th:
        t.join()
    for n in names:
        st, rec = out.get(n, (0, {'W': 0, 'L': 0, 'D': 0}))
        aft = talent(LEEKS[n])
        print('  %-17s %2d fights %2dW/%2dL/%dD  talent %d -> %d (%+d)' % (n, st, rec['W'], rec['L'], rec['D'],
                                                                         before[n], aft, aft - before[n]), flush=True)
    g = lw.get('/garden/get'); g = g.get('garden', g)
    print('credits left %s  (%.0f s)' % (g.get('fights'), time.time() - t0), flush=True)


if __name__ == '__main__':
    main()
