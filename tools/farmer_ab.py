#!/usr/bin/env python3
"""Interleaved A/B of two AI paths in garden farmer fights (4 v 4) on the main account.
Fight i uses arm A if i is even, B if odd; before each fight all four leeks are switched to that
arm's AI path; each fight is finished before the next switch (the AI is read at generation).
The opponent is a random pick among the garden's farmer opponents (same rule for both arms).
Leeks go back to --restore at the end, whatever happens.

    python3 tools/farmer_ab.py --a 10.0/V10/v10_team.py --b 10.0/V10/v10.py --n 40
"""
import argparse, json, random, sys, time, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lw_api import LWSession
LEEKS = [20443, 129288, 129295, 129296]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--a', required=True); ap.add_argument('--b', required=True)
    ap.add_argument('--n', type=int, default=40); ap.add_argument('--restore', default='10.0/V10/v10.py')
    ap.add_argument('--seed', type=int, default=1)
    a = ap.parse_args()
    lw = LWSession('main'); rng = random.Random(a.seed)
    res = {'A': [], 'B': []}
    try:
        for i in range(a.n):
            arm = 'A' if i % 2 == 0 else 'B'; path = a.a if arm == 'A' else a.b
            for lid in LEEKS:
                lw.post('/leek/set-ai', leek_id=lid, ai_path=path)
            opps = (lw.get('/garden/get-farmer-opponents') or {}).get('opponents') or []
            if not opps:
                print('no opponents'); break
            o = rng.choice(opps)
            r = lw.post('/garden/start-farmer-fight', target_id=o['id'])
            fid = r if isinstance(r, int) else (r.get('fight') if isinstance(r, dict) else None)
            if not fid:
                print('start failed', r); break
            g = {}
            for _ in range(120):
                time.sleep(2)
                g = lw.get('/fight/get/%d' % fid); g = g.get('fight', g)
                if g.get('status') == 2:
                    break
            ours = 1 if any(str(f) == str(lw.farmer['id']) for f in (g.get('farmers1') or {})) else 2
            w = g.get('winner'); out = 1.0 if w == ours else (0.5 if w == 0 else 0.0)
            res[arm].append(out)
            print('%2d %s vs %-20s (talent %s) -> %s  turns %s' % (i, arm, o['name'], o.get('talent'), {1.0: 'WIN', 0.5: 'draw', 0.0: 'loss'}[out],
                                                                (g.get('report') or {}).get('duration')), flush=True)
    finally:
        for lid in LEEKS:
            lw.post('/leek/set-ai', leek_id=lid, ai_path=a.restore)
        print('leeks back on', a.restore)
    for arm in ('A', 'B'):
        v = res[arm]
        print('%s %s: %.1f / %d' % (arm, a.a if arm == 'A' else a.b, sum(v), len(v)))


if __name__ == '__main__':
    main()
