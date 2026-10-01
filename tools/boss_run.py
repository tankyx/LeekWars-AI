#!/usr/bin/env python3
"""Run N Fennel (or other) boss fights over REST and report each one:
winner, graal death turn, crystal revives (action 105) by turn, our deaths,
damage to the army. Fight JSON saved to data/boss_fights/ours_<id>.json.

    python3 tools/boss_run.py 12 [--boss 2]
"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession
# Participant order = spawn slot: slot 1 -> cell 228 (next to the king's spawn, 170), slot 2 -> 491,
# slot 3 -> 563, slot 4 -> 588 (back pocket). Margaret (RES 12) spawned at 228 and took ~790 from the
# king on turn 2 on average (died turns 4-5 in 23/49 fights): the tank takes slot 1, Margaret the pocket.
LEEKS = [129295, 20443, 129288, 129296]
OURS = {129295: 'Kur', 20443: 'Ada', 129296: 'Mar', 129288: 'Eds'}


def analyze(f):
    d = f['data']
    names = {l['id']: l['name'] for l in d['leeks']}
    team = {l['id']: l['team'] for l in d['leeks']}
    rnd = 1; graal = None; revives = []; dead = []; dmg = 0; cur = None
    for a in d['actions']:
        if a[0] == 6:
            rnd = a[1]
        elif a[0] == 7:
            cur = a[1]
        elif a[0] == 105:
            revives.append('T%d %s' % (rnd, names.get(a[2], '?').split('_')[0]))
        elif a[0] == 5:
            n = names.get(a[1], '')
            if n == 'graal':
                graal = rnd
            elif team.get(a[1]) == 1 and n in ('KurtGodel', 'AdaLovelace', 'MargaretHamilton', 'EdsgerDijkstra'):
                dead.append('T%d %s' % (rnd, n[:3]))
        elif a[0] == 101 and team.get(a[1]) == 2 and 'crystal' not in names.get(a[1], ''):
            dmg += a[2]
    return graal, revives, dead, dmg, rnd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('n', type=int)
    ap.add_argument('--boss', type=int, default=2)
    a = ap.parse_args()
    lw = LWSession('main')
    out = os.path.join(ROOT, 'data', 'boss_fights')
    wins = 0; graals = 0
    for i in range(a.n):
        r = lw.post('/garden/start-boss-fight', boss_id=a.boss, participants=json.dumps(LEEKS))
        fid = r.get('fight') if isinstance(r, dict) else None
        if not fid:
            print('start failed:', r, flush=True); break
        f = None
        for _ in range(120):
            time.sleep(2)
            g = lw.get('/fight/get/%d' % fid); g = g.get('fight', g)
            if g.get('status') == 2:
                f = g; break
        if f is None:
            print('%d: not finished' % fid, flush=True); continue
        json.dump(f, open(os.path.join(out, 'ours_%d.json' % fid), 'w'))
        graal, rev, dead, dmg, turns = analyze(f)
        win = f.get('winner') == 1
        wins += win; graals += graal is not None
        print('%d: %s turns %d | graal %s | revives %s | our deaths %s | army dmg %d' % (
            fid, 'WIN ' if win else 'loss', turns, ('T%d' % graal) if graal else '-', rev, dead, dmg), flush=True)
    print('== %d/%d wins, %d graal deaths' % (wins, a.n, graals))


if __name__ == '__main__':
    main()
