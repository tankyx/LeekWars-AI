#!/usr/bin/env python3
"""Paired A/B of two server AI paths on seeded challenges against real
opponents (their real AIs). Challenges do not move talent.

    python3 tools/v10_challenge_ab.py --leek 129295 --opps 105863,81204 --seeds 4 \
        --a 10.0/V10/v10.py --b 10.0/V10/v10_test.py

For each arm the leek is switched to that AI path, every (opponent, seed)
challenge is started, then the leek goes back to the AI it had before. Pairs
share opponent and seed, so the discordant pairs compare the two AIs.
"""
import argparse, math, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lw_api import LWSession


def post(lw, path, data):
    for _ in range(8):
        r = lw.s.post('https://leekwars.com/api' + path, data=data).json()
        if isinstance(r, dict) and r.get('error') == 'rate_limit':
            time.sleep(1.5)
            continue
        return r
    return r


def leek_ai(lw, lid):
    l = lw.get('/leek/get/%d' % lid); l = l.get('leek', l)
    return l['ai']['path'] if l.get('ai') else None


def result(lw, fid, lid):
    """1 win, 0.5 draw, 0 loss, None if not finished / unknown."""
    f = lw.get('/fight/get/%d' % fid)
    f = f.get('fight', f) if isinstance(f, dict) else {}
    if f.get('status') != 2:
        return None
    team = 1 if any(l['id'] == lid for l in f.get('leeks1') or []) else 2
    w = f.get('winner')
    return 1.0 if w == team else (0.5 if w == 0 else 0.0)


def sign_p(k, n):
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(0, min(k, n - k) + 1)) / 2 ** n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--leek', type=int, required=True)
    ap.add_argument('--opps', required=True, help='comma list of opponent leek ids')
    ap.add_argument('--seeds', type=int, default=4)
    ap.add_argument('--a', required=True); ap.add_argument('--b', required=True)
    ap.add_argument('--account', default='main')
    a = ap.parse_args()
    lw = LWSession(a.account)
    orig = leek_ai(lw, a.leek)
    opps = [int(x) for x in a.opps.split(',')]
    fights = {}; res = {}
    try:
        for arm, path in (('A', a.a), ('B', a.b)):
            post(lw, '/leek/set-ai', {'leek_id': a.leek, 'ai_path': path})
            if leek_ai(lw, a.leek) != path:
                sys.exit('could not set %s' % path)
            for o in opps:
                for s in range(1, a.seeds + 1):
                    r = post(lw, '/garden/start-solo-challenge', {'leek_id': a.leek, 'target_id': o, 'seed': s, 'side': 0})
                    fid = r if isinstance(r, int) else (r.get('fight') if isinstance(r, dict) else None)
                    if not fid:
                        print('  %s opp %d seed %d: %s' % (arm, o, s, str(r)[:120]), flush=True)
                        continue
                    fights[(arm, o, s)] = fid
            print('%s (%s): %d challenges started' % (arm, path, sum(1 for k in fights if k[0] == arm)), flush=True)
            # the fights must be generated with this arm's AI before switching
            for k, fid in [(k, f) for k, f in fights.items() if k[0] == arm]:
                for _ in range(60):
                    r = result(lw, fid, a.leek)
                    if r is not None:
                        res[k] = r
                        break
                    time.sleep(3)
    finally:
        post(lw, '/leek/set-ai', {'leek_id': a.leek, 'ai_path': orig})
        print('leek back on %s' % leek_ai(lw, a.leek), flush=True)
    for k, fid in fights.items():
        if k in res:
            continue
        for _ in range(30):
            r = result(lw, fid, a.leek)
            if r is not None:
                res[k] = r
                break
            time.sleep(4)
    pairs = [(o, s, res.get(('A', o, s)), res.get(('B', o, s))) for o in opps for s in range(1, a.seeds + 1)]
    ok = [p for p in pairs if p[2] is not None and p[3] is not None]
    print('\n%d pairs' % len(ok))
    for o in opps:
        sub = [p for p in ok if p[0] == o]
        print('  opp %-7d A %.1f  B %.1f  / %d' % (o, sum(p[2] for p in sub), sum(p[3] for p in sub), len(sub)))
    bw = sum(1 for p in ok if p[3] > p[2]); aw = sum(1 for p in ok if p[2] > p[3])
    print('A %s: %.1f   B %s: %.1f   discordant B better %d / A better %d   sign p = %.3f' % (
        a.a, sum(p[2] for p in ok), a.b, sum(p[3] for p in ok), bw, aw, sign_p(bw, bw + aw)))


if __name__ == '__main__':
    main()
