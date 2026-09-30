#!/usr/bin/env python3
"""Where would each leek settle on the ladder? Seeded challenges (they do not
move talent) against real leeks spread from its current talent to above its
all-time high, then a logistic fit of win vs opponent talent: the talent
where the fitted win rate crosses 50% is the level the leek can hold.

    python3 tools/ath_challenges.py                       # main, 20 opps x 3 seeds
    python3 tools/ath_challenges.py --leeks AdaLovelace --opps 10 --seeds 2
    python3 tools/ath_challenges.py --report              # refit from the CSV only

Results append to data/ladder/ath_challenges.csv (one row per challenge).
The daily challenge allowance (~30 per account) ends a run early
(error_fight_not_enought_challenges); the opponent plan is saved to
data/ladder/ath_challenges_plan.json and later runs resume it, skipping the
(opponent, seed) pairs already in the CSV. --new-plan starts over.
Challenges nearest the all-time high are played first.
"""
import argparse, csv, json, math, os, random, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession

ACCOUNTS = {'main': {'AdaLovelace': 20443, 'EdsgerDijkstra': 129288, 'KurtGodel': 129295, 'MargaretHamilton': 129296},
            'cure': {'LeekRain': 19703, 'DawnFall': 21175, 'DuskHope': 129801, 'ProdigalSon': 130236}}
OUT = os.path.join(ROOT, 'data', 'ladder', 'ath_challenges.csv')
PLAN = os.path.join(ROOT, 'data', 'ladder', 'ath_challenges_plan.json')
FIELDS = ['date', 'leek', 'leek_talent', 'leek_ath', 'opp_id', 'opp_name', 'opp_talent', 'seed', 'fight', 'result']


class Bucket:
    def __init__(self, rate):
        self.rate, self.lock, self.next = rate, threading.Lock(), time.time()

    def take(self):
        with self.lock:
            now = time.time(); wait = self.next - now
            self.next = max(now, self.next) + 1.0 / self.rate
        if wait > 0:
            time.sleep(wait)


def ranking_band(lw, bucket, lo, hi, own_farmers):
    """Active level-301 leeks with lo <= talent <= hi (ranking pages, 50 per page)."""
    out, page = [], 1
    # skip ahead: find the first page whose last talent is <= hi
    step = 16
    while True:
        bucket.take(); r = lw.get('/ranking/get/leek/talent/%d/null' % page).get('ranking') or []
        if not r or r[-1]['talent'] <= hi:
            break
        page += step
    page = max(1, page - step)
    while True:
        bucket.take(); r = lw.get('/ranking/get/leek/talent/%d/null' % page).get('ranking') or []
        if not r:
            break
        for l in r:
            if lo <= l['talent'] <= hi and l.get('active') and l.get('level') == 301 and l.get('farmer_id') not in own_farmers:
                out.append(l)
        if r[-1]['talent'] < lo:
            break
        page += 1
    return out


def pick(pool, lo, hi, n, rng):
    """n opponents stratified over [lo, hi]."""
    chosen = []
    for i in range(n):
        a = lo + (hi - lo) * i / n; b = lo + (hi - lo) * (i + 1) / n
        c = [l for l in pool if a <= l['talent'] < b and l not in chosen]
        if c:
            chosen.append(rng.choice(c))
    return chosen


def fit(rows):
    """Logistic P(win) = 1 / (1 + exp((t - L) / s)) by grid max-likelihood; draws count half.
    Returns (L, s, loglik)."""
    best = None
    for s in (40, 60, 80, 120, 160, 240, 320):
        for L in range(1500, 3001, 5):
            ll = 0.0
            for t, y in rows:
                p = 1.0 / (1.0 + math.exp(max(-50, min(50, (t - L) / s))))
                p = min(max(p, 1e-6), 1 - 1e-6)
                ll += y * math.log(p) + (1 - y) * math.log(1 - p)
            if best is None or ll > best[2]:
                best = (L, s, ll)
    return best


def report(path):
    rows = list(csv.DictReader(open(path)))
    by = {}
    for r in rows:
        if r['result'] != '':
            by.setdefault(r['leek'], []).append(r)
    for leek, rs in by.items():
        cur = int(rs[-1]['leek_talent']); ath = int(rs[-1]['leek_ath'])
        pts = [(int(r['opp_talent']), float(r['result'])) for r in rs]
        L, s, _ = fit(pts)
        print('\n== %s  now %d  ATH %d  %d challenges  score %.1f/%d' % (leek, cur, ath, len(pts), sum(y for _, y in pts), len(pts)))
        edges = sorted({cur - 150, cur - 50, cur + 50, (cur + ath) // 2, ath - 50, ath + 50, ath + 150})
        for a, b in zip(edges, edges[1:]):
            sub = [y for t, y in pts if a <= t < b]
            if sub:
                print('   opp talent %4d-%4d  %5.1f/%-3d  %3.0f%%' % (a, b, sum(sub), len(sub), 100 * sum(sub) / len(sub)))
        print('   fitted 50%% level: %d (slope %d)  -> %+d vs now, %+d vs ATH' % (L, s, L - cur, L - ath))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--account', default='main', choices=sorted(ACCOUNTS))
    ap.add_argument('--leeks', default='', help='comma list (default: all of the account)')
    ap.add_argument('--opps', type=int, default=20, help='opponents per leek')
    ap.add_argument('--seeds', type=int, default=3)
    ap.add_argument('--below', type=int, default=100, help='band starts this far below current talent')
    ap.add_argument('--above', type=int, default=100, help='band ends this far above the all-time high')
    ap.add_argument('--inflight', type=int, default=4)
    ap.add_argument('--rate', type=float, default=8.0)
    ap.add_argument('--seed', type=int, default=1, help='opponent sampling seed')
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--new-plan', action='store_true')
    a = ap.parse_args()
    if a.report:
        return report(OUT)
    leeks = ACCOUNTS[a.account]
    names = [n for n in leeks if not a.leeks or n in a.leeks.split(',')]
    lw = LWSession(a.account); bucket = Bucket(a.rate); rng = random.Random(a.seed)
    own = set()
    for acc in ACCOUNTS:
        try:
            own.add(LWSession(acc).farmer['id'])
        except Exception:
            pass
    saved = {} if a.new_plan or not os.path.exists(PLAN) else json.load(open(PLAN))
    plan = {}
    for n in names:
        if n in saved:
            plan[n] = tuple(saved[n])
            cur, ath, opps = plan[n]
            print('%-17s plan kept: now %d ATH %d  %d opponents' % (n, cur, ath, len(opps)), flush=True)
            continue
        bucket.take(); l = lw.leek(leeks[n])
        cur, ath = l['talent'], l.get('max_talent') or l['talent']
        lo, hi = cur - a.below, max(ath, cur) + a.above
        pool = ranking_band(lw, bucket, lo, hi, own)
        opps = [{'id': o['id'], 'name': o['name'], 'talent': o['talent']} for o in pick(pool, lo, hi, a.opps, rng)]
        opps.sort(key=lambda o: abs(o['talent'] - ath))           # the all-time-high band first
        plan[n] = (cur, ath, opps)
        print('%-17s now %d ATH %d  band %d-%d  pool %d  picked %d' % (n, cur, ath, lo, hi, len(pool), len(opps)), flush=True)
    saved.update(plan)
    json.dump(saved, open(PLAN, 'w'), indent=1)
    done = set()
    if os.path.exists(OUT):
        done = {(r['leek'], int(r['opp_id']), int(r['seed'])) for r in csv.DictReader(open(OUT)) if r['result'] != ''}
    new = not os.path.exists(OUT)
    fh = open(OUT, 'a', newline=''); w = csv.DictWriter(fh, FIELDS)
    if new:
        w.writeheader()
    lock = threading.Lock(); today = time.strftime('%Y-%m-%d')

    def result(fid, lid):
        bucket.take(); f = lw.get('/fight/get/%d' % fid); f = f.get('fight', f) if isinstance(f, dict) else {}
        if f.get('status') != 2:
            return None
        team = 1 if any(x['id'] == lid for x in f.get('leeks1') or []) else 2
        return 1.0 if f.get('winner') == team else (0.5 if f.get('winner') == 0 else 0.0)

    def run(n):
        lid = leeks[n]; cur, ath, opps = plan[n]
        todo = [(o, s) for s in range(1, a.seeds + 1) for o in opps   # seed-major: every opponent gets seed 1 first
                if (n, o['id'], s) not in done]
        pending = []
        stop = threading.Event()           # per leek: the allowance may be per leek or per account
        while (todo or pending) and not (stop.is_set() and not pending):
            while todo and len(pending) < a.inflight and not stop.is_set():
                o, s = todo.pop(0)
                bucket.take()
                r = lw.post('/garden/start-solo-challenge', leek_id=lid, target_id=o['id'], seed=s, side=0)
                fid = r if isinstance(r, int) else (r.get('fight') if isinstance(r, dict) else None)
                if not fid:
                    print('  %s vs %s seed %d: %s' % (n, o['name'], s, str(r)[:100]), flush=True)
                    if 'not_enought' in str(r):
                        stop.set()
                    continue
                pending.append((fid, o, s, time.time()))
            time.sleep(1.0)
            for p in list(pending):
                fid, o, s, t0 = p
                res = result(fid, lid)
                if res is None and time.time() - t0 < 180:
                    continue
                pending.remove(p)
                with lock:
                    w.writerow({'date': today, 'leek': n, 'leek_talent': cur, 'leek_ath': ath, 'opp_id': o['id'],
                                'opp_name': o['name'], 'opp_talent': o['talent'], 'seed': s, 'fight': fid,
                                'result': '' if res is None else res})
                    fh.flush()
        print('%s done' % n, flush=True)

    t0 = time.time()
    th = [threading.Thread(target=run, args=(n,)) for n in names]
    [t.start() for t in th]; [t.join() for t in th]
    fh.close()
    print('%.0f s' % (time.time() - t0))
    report(OUT)


if __name__ == '__main__':
    main()
