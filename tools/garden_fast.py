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
import argparse, datetime, json, os, random, sqlite3, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lw_api import LWSession

ACCOUNTS = {'main': {'AdaLovelace': 20443, 'EdsgerDijkstra': 129288, 'KurtGodel': 129295, 'MargaretHamilton': 129296},
            'cure': {'LeekRain': 19703, 'DawnFall': 21175, 'DuskHope': 129801, 'ProdigalSon': 130236}}
LEEKS = dict(ACCOUNTS['main'])
BEATABLE, DANGEROUS, WINDOW, DECAY, SESSION_LOSS_LIMIT = 0.7, 0.45, 10, 0.8, 2
# talent is Elo-like: a win is worth G0 + GK x (their talent - ours), a loss costs G0 - GK x gap
# (fit on 24k cached garden fights: 14.5 at equal talent, ~11 / ~17 at -/+100)
G0, GK = 13.84, 0.0279
PICKS_LOG = os.path.join(os.path.dirname(HERE), 'data', 'ladder', 'garden_picks.jsonl')
from garden_model import Model, STATS as MSTATS
MODEL = None                          # loaded per account in main(); None = history selector only


def load_model(account):
    global MODEL
    try:
        MODEL = Model(account)
    except Exception:
        MODEL = None
    return MODEL


def paris_ts(hhmm):
    """Next occurrence of HH:MM Europe/Paris as a unix time (today if still ahead)."""
    from zoneinfo import ZoneInfo
    tz = ZoneInfo('Europe/Paris'); now = datetime.datetime.now(tz)
    h, m = (int(x) for x in hhmm.split(':'))
    t = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if t <= now:
        t += datetime.timedelta(days=1)
    return t.timestamp()


BIAS_PRIOR, BIAS_WINDOW, MAX_SHARE = 40.0, 200, 0.35


def leek_bias(name):
    """Actual - predicted win rate of this leek's recent picks (data/ladder/garden_picks.jsonl),
    shrunk toward 0 with BIAS_PRIOR pseudo-picks. Picking the best-rated offer selects the
    model's optimistic errors (2026-10-06: Edsger predicted 60%, won 45% over 137 picks)."""
    try:
        rows = [json.loads(l) for l in open(PICKS_LOG)]
    except Exception:
        return 0.0
    rows = [r for r in rows if r.get('leek') == name][-BIAS_WINDOW:]
    if not rows:
        return 0.0
    d = sum((1.0 if r['result'] == 'WIN' else (0.5 if r['result'] == 'DRAW' else 0.0)) - r['p'] for r in rows)
    return d / (len(rows) + BIAS_PRIOR)


def ai_crashed(f, lid):
    """True when our leek's AI did nothing in this fight: no weapon/chip use and 2+ BUG
    actions (1002). 2026-10-07 the server's Python runtime ran out of heap ('Invalid AI')
    and Kurt lost ~20 garden fights in a row without acting."""
    data = f.get('data') or {}
    me = next((l for l in (f.get('leeks1') or []) + (f.get('leeks2') or []) if l.get('id') == lid), None)
    ent = next((e['id'] for e in data.get('leeks') or [] if me and e.get('name') == me.get('name')), None)
    if ent is None:
        return False
    cur = None; uses = bugs = 0
    for a in data.get('actions') or []:
        if a and a[0] == 7:
            cur = a[1]
        elif cur == ent:
            if a[0] in (12, 16):
                uses += 1
            elif a[0] == 1002:
                bugs += 1
    return uses == 0 and bugs >= 2


def expected_talent(p, gap):
    return p * (G0 + GK * gap) - (1.0 - p) * (G0 - GK * gap)


class Profiles:
    """Opponent profiles (/leek/get real totals), cached in tools/opponent_profiles.db for 2 days."""
    TTL = 2 * 86400

    def __init__(self):
        self.c = sqlite3.connect(os.path.join(HERE, 'opponent_profiles.db'), check_same_thread=False)
        self.c.execute('CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY, data TEXT, t REAL)')
        self.lock = threading.Lock()

    def get(self, oid, fetch):
        with self.lock:
            r = self.c.execute('SELECT data, t FROM profile WHERE id=?', (oid,)).fetchone()
        if r and time.time() - r[1] < self.TTL:
            return json.loads(r[0])
        l = fetch('/leek/get/%d' % oid) or {}
        l = l.get('leek', l) if isinstance(l, dict) else {}
        if not l.get('id'):
            return json.loads(r[0]) if r else {}
        d = {k: l.get('total_' + k, 0) or 0 for k in MSTATS}
        d['talent'] = l.get('talent', 0); d['level'] = l.get('level', 301)
        with self.lock:
            self.c.execute('INSERT OR REPLACE INTO profile VALUES (?,?,?)', (oid, json.dumps(d), time.time()))
            self.c.commit()
        return d


def model_pick(db, prof, name, my_talent, opponents, banned, fetch, model=None, bias=0.0):
    """Best opponent by expected talent: (opponent, expected talent, P(win)) or None."""
    elig = [o for o in opponents if o['id'] not in banned] or opponents
    best = None
    for o in elig:
        hist = [r for (r,) in db.c.execute('SELECT result FROM fight_history WHERE opponent_id=? ORDER BY timestamp',
                                            (o['id'],))]
        opp = dict(prof.get(o['id'], fetch))
        opp['talent'] = o.get('talent') or opp.get('talent', my_talent); opp['level'] = o.get('level') or opp.get('level', 301)
        p = min(0.97, max(0.03, (model or MODEL).p(name, my_talent, opp, hist) + bias))
        ev = expected_talent(p, opp['talent'] - my_talent)
        if best is None or ev > best[1]:
            best = (o, ev, p)
    return best


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


def run_leek(name, lid, n, inflight, bucket, lock, out, account='main'):
    lw = LWSession(account); db = DB(lid)

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
                if err == 'rate_limit':            # shared 10 req/s (crawler): wait, not an error
                    time.sleep((r.get('retry_after') or 1) + 0.5); continue
                print('  %s: start failed %s' % (name, str(r)[:120]), flush=True)
                errors += 1; time.sleep(1); continue
            pending[fid] = tgt; started += 1
        if errors >= 10 and not pending:
            break
        time.sleep(1)
    with lock:
        out[name] = (started, rec)


def run_alloc(names, leeks, total, inflight, bucket, account, min_ev, wait_min=0.0, dump_ts=None, model=None,
              reroll_ev=None, reroll_after=60.0):
    """One shared pool of `total` fights: each start goes to the leek whose best offered
    opponent has the highest expected talent (model + history); a leek whose offer is
    all bad simply waits. Reroll: a leek whose list has not changed for `reroll_after`
    minutes and whose best offer is >= `reroll_ev` (slightly negative) takes it anyway,
    because a fight is what regenerates its five offers. Returns {name: (started, rec, talent_now)}."""
    lw = LWSession(account); prof = Profiles()

    def get(path):
        bucket.take(); return lw.get(path)

    def post(path, data):
        bucket.take(); return lw.s.post('https://leekwars.com/api' + path, data=data).json()
    st = {}
    for n in names:
        lid = leeks[n]; db = DB(lid)
        try:
            fixed = reconcile(lw, db, lid, get)
            if fixed:
                print('  %s: %d unrecorded fights added to the history DB' % (n, fixed), flush=True)
        except Exception as ex:
            print('  %s: reconcile failed %s' % (n, ex), flush=True)
        l = get('/leek/get/%d' % lid); l = l.get('leek', l)
        st[n] = {'lid': lid, 'db': db, 'pending': {}, 'rec': {'W': 0, 'L': 0, 'D': 0}, 'losses': {}, 'banned': set(),
                 'talent': int(l.get('talent', 0)), 'offer': None, 'started': 0, 'ev': 0.0, 'p': 0.0,
                 'ids': None, 'since': time.time(), 'rerolls': 0, 'bias': leek_bias(n), 'crash': 0, 'paused': False}
    logf = open(PICKS_LOG, 'a')
    started = 0; errors = 0; out_of_fights = False
    deadline = dump_ts if dump_ts else time.time() + 60.0 * wait_min
    cap = max(1, int(MAX_SHARE * total + 0.999)) if len(st) > 1 else total
    print('  %s: per-leek cap %d; pick bias %s' % (account, cap, ', '.join(
        '%s %+.3f' % (n, s['bias']) for n, s in st.items())), flush=True)
    while True:
        for n, s in st.items():
            for fid, (opp, p, ev, rr) in list(s['pending'].items()):
                f = get('/fight/get/%d' % fid); f = f.get('fight', f) if isinstance(f, dict) else {}
                if f.get('status') != 2:
                    continue
                team = 1 if any(l['id'] == s['lid'] for l in f.get('leeks1') or []) else 2
                res = 'DRAW' if f.get('winner') == 0 else ('WIN' if f.get('winner') == team else 'LOSS')
                try:
                    s['db'].record(fid, opp, res)
                except Exception as ex:
                    print('  %s: could not record %d (%s)' % (n, fid, ex), flush=True)
                for l in ((f.get('report') or {}).get('leeks1' if team == 1 else 'leeks2') or []):
                    if l.get('id') == s['lid'] and l.get('talent'):
                        s['talent'] = int(l['talent'])
                del s['pending'][fid]; s['rec'][res[0]] += 1
                if ai_crashed(f, s['lid']):
                    s['crash'] += 1
                    print('  %s %s: AI did nothing in fight %d (crash %d in a row)' % (
                        time.strftime('%H:%M'), n, fid, s['crash']), flush=True)
                    if s['crash'] >= 2 and not s['paused']:
                        s['paused'] = True
                        print('  %s %s: PAUSED - its AI is crashing' % (time.strftime('%H:%M'), n), flush=True)
                else:
                    s['crash'] = 0
                logf.write(json.dumps({'fight': fid, 'leek': n, 'opp': opp['id'], 'opp_talent': opp.get('talent'),
                                       'p': round(p, 3), 'ev': round(ev, 2), 'result': res, 'reroll': rr}) + '\n'); logf.flush()
                if res == 'LOSS':
                    s['losses'][opp['id']] = s['losses'].get(opp['id'], 0) + 1
                    if s['losses'][opp['id']] >= SESSION_LOSS_LIMIT:
                        s['banned'].add(opp['id'])
        progressed = False
        while started < total and not out_of_fights and errors < 20:
            cands = []; empty = 0
            for n, s in st.items():
                if len(s['pending']) >= inflight or s['started'] >= cap or s['paused']:
                    continue
                if s['offer'] is None:
                    ops = (get('/garden/get-leek-opponents/%d' % s['lid']) or {}).get('opponents') or []
                    empty += not ops
                    s['offer'] = model_pick(s['db'], prof, n, s['talent'], ops, s['banned'], get, model, s['bias']) if ops else False
                    ids = frozenset(o['id'] for o in ops)
                    if ops and ids != s['ids']:
                        s['ids'] = ids; s['since'] = time.time()
                if s['offer']:
                    ev_ = s['offer'][1]
                    if min_ev is None or ev_ >= min_ev:
                        cands.append((1, ev_, n))
                    elif (reroll_ev is not None and ev_ >= reroll_ev
                          and time.time() - s['since'] >= 60.0 * reroll_after):
                        cands.append((0, ev_, n))     # reroll: only when no positive offer anywhere
            if not cands:
                if empty and empty == sum(1 for x in st.values() if x['offer'] is False):
                    # no offer at all for anyone while fights remain: stale session (seen after ~2 h)
                    print('  %s no offers returned - logging in again' % time.strftime('%H:%M'), flush=True)
                    try:
                        lw.login()
                    except Exception as ex:
                        print('  re-login failed: %s' % ex, flush=True)
                break
            good, ev, n = max(cands)
            s = st[n]; tgt, ev, p = s['offer']
            if not good:
                s['rerolls'] += 1
                print('  %s reroll %s: best offer %+.1f, list unchanged %.0f min' % (
                    time.strftime('%H:%M'), n, ev, (time.time() - s['since']) / 60.0), flush=True)
            r = post('/garden/start-solo-fight', {'leek_id': s['lid'], 'target_id': tgt['id']})
            fid = r.get('fight') if isinstance(r, dict) else (r if isinstance(r, int) else None)
            if not fid:
                err = r.get('error') if isinstance(r, dict) else r
                if err in ('too_many_fights', 'no_more_fights'):
                    out_of_fights = True; break
                if err == 'rate_limit':
                    time.sleep((r.get('retry_after') or 1) + 0.5); continue
                print('  %s: start failed %s' % (n, str(r)[:120]), flush=True)
                s['offer'] = None; errors += 1; time.sleep(1); continue
            s['pending'][fid] = (tgt, p, ev, not good); s['offer'] = None; s['started'] += 1
            s['ev'] += ev; s['p'] += p; started += 1; progressed = True
        busy = any(s['pending'] for s in st.values())
        if sum(1 for x in st.values() if x['paused']) >= min(2, len(st)) and not out_of_fights:
            print('  %s %d leeks crashing on %s - server-side AI failure? stopping the run' % (
                time.strftime('%H:%M'), sum(1 for x in st.values() if x['paused']), account), flush=True)
            out_of_fights = True
        if min_ev is not None and dump_ts and time.time() >= dump_ts:
            # end of the credit day: spend what is left on the best offers available
            print('  %s dump time: spending the remaining %d fights on the best offers' % (
                time.strftime('%H:%M'), total - started), flush=True)
            min_ev = None
            for s in st.values():
                s['offer'] = None
            continue
        if (not busy and not progressed and started < total and not out_of_fights and errors < 20
                and min_ev is not None and time.time() < deadline):
            # every offer is below --min-ev: offers drift on their own, look again in 5 minutes
            best = max([s['offer'][1] for s in st.values() if s['offer']] + [-99])
            print('  %s best offer %+.1f < %.1f, %d/%d used; waiting 5 min' % (
                time.strftime('%H:%M'), best, min_ev, started, total), flush=True)
            time.sleep(max(5, min(300, deadline - time.time())))
            for s in st.values():
                s['offer'] = None
            continue
        if not busy and (started >= total or out_of_fights or errors >= 20 or not progressed):
            if not progressed and started < total and not out_of_fights and errors < 20:
                # every offer is below --min-ev and nothing is in flight: nothing more to gain now
                print('  no offer above min-ev %.1f; stopping with %d of %d fights used' % (min_ev or 0, started, total), flush=True)
            break
        time.sleep(1)
    return {n: (s['started'], s['rec'], s['talent'], s['ev'], s['p']) for n, s in st.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--per-leek', type=int, default=25)
    ap.add_argument('--account', default='main', choices=sorted(ACCOUNTS))
    ap.add_argument('--leeks', default='')
    ap.add_argument('--inflight', type=int, default=4, help='fights generating at once per leek')
    ap.add_argument('--rate', type=float, default=9.0)
    ap.add_argument('--total', type=int, default=0,
                    help='shared pool: each fight goes to the leek with the best expected talent (needs the model)')
    ap.add_argument('--min-ev', type=float, default=None, help='with --total: never start a fight below this expected talent')
    ap.add_argument('--wait', type=float, default=0.0, help='with --min-ev: minutes to keep re-checking offers (every 5 min)')
    ap.add_argument('--dump-at', default=None, help='with --min-ev: HH:MM Paris time at which the remaining fights are spent anyway')
    ap.add_argument('--reroll-ev', type=float, default=None, help='with --min-ev: take an offer >= this when the list is stale')
    ap.add_argument('--reroll-after', type=float, default=60.0, help='minutes a leek list must stay unchanged before a reroll')
    a = ap.parse_args()
    global LEEKS
    LEEKS = ACCOUNTS[a.account]
    load_model(a.account)
    lw = LWSession(a.account)
    names = a.leeks.split(',') if a.leeks else list(LEEKS)

    def talent(lid):
        l = lw.get('/leek/get/%d' % lid); l = l.get('leek', l); return int(l.get('talent', 0))
    before = {n: talent(LEEKS[n]) for n in names}
    g = lw.get('/garden/get'); g = g.get('garden', g)
    print('credits %s' % g.get('fights'), flush=True)
    t0 = time.time(); bucket = Bucket(a.rate); lock = threading.Lock(); out = {}
    if a.total > 0:
        if MODEL is None or any(n not in MODEL.leeks for n in names):
            print('no garden model for these leeks (python3 tools/garden_model.py build --account %s)' % a.account); return
        res = run_alloc(names, LEEKS, a.total, a.inflight, bucket, a.account, a.min_ev, a.wait,
                        paris_ts(a.dump_at) if a.dump_at else None, None, a.reroll_ev, a.reroll_after)
        for n in names:
            st, rec, tal, sev, sp = res[n]
            aft = talent(LEEKS[n])
            print('  %-17s %3d fights %3dW/%3dL/%dD  talent %d -> %d (%+d)  predicted win %.0f%%  expected %+.0f' % (
                n, st, rec['W'], rec['L'], rec['D'], before[n], aft, aft - before[n], 100 * sp / max(1, st), sev), flush=True)
        g = lw.get('/garden/get'); g = g.get('garden', g)
        print('credits left %s  (%.0f s)' % (g.get('fights'), time.time() - t0), flush=True)
        return
    th = [threading.Thread(target=run_leek, args=(n, LEEKS[n], a.per_leek, a.inflight, bucket, lock, out, a.account)) for n in names]
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
