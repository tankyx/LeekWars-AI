#!/usr/bin/env python3
"""Cure XP farm on solo garden fights (~3,750 XP per credit, ~45% more than Nasu, and fights
generate in parallel per leek). Rounds of tools/garden_fast.py, then capital spending and
level-unlock listing (same plans as tools/xp_farm.py) between rounds.

    python3 tools/xp_farm_solo.py --rounds 14 --per-leek 25 --inflight 4
"""
import argparse, json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession
import xp_farm as xf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rounds', type=int, default=14)
    ap.add_argument('--per-leek', type=int, default=25)
    ap.add_argument('--inflight', type=int, default=4)
    ap.add_argument('--weights', default='', help='per-leek fights per round, e.g. LeekRain=28,DawnFall=28,DuskHope=28,ProdigalSon=16 (default: --per-leek each)')
    a = ap.parse_args()
    lw = xf.Limited(LWSession('cure'), 8.0)
    items = lw.get('/item/get-all')
    levels = {lid: lw.leek(lid)['level'] for lid in xf.LEEKS}
    found = json.load(open(xf.UNLOCKS)) if os.path.exists(xf.UNLOCKS) else []
    t0 = time.time()
    for rnd in range(a.rounds):
        g = lw.get('/garden/get'); g = g.get('garden', g)
        if (g.get('fights') or 0) < 4:
            print('out of fights'); break
        groups = {}
        if a.weights:
            for kv in a.weights.split(','):
                k, v = kv.split('='); groups.setdefault(int(v), []).append(k)
        else:
            groups[a.per_leek] = list(xf.LEEKS.values())
        procs = [subprocess.Popen([sys.executable, os.path.join(HERE, 'garden_fast.py'), '--account', 'cure',
                                   '--per-leek', str(n), '--leeks', ','.join(ls), '--inflight', str(a.inflight), '--rate', '4.5'],
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) for n, ls in groups.items()]
        summary = []
        for p in procs:
            out, _ = p.communicate(timeout=3600)
            summary += [l.strip() for l in out.splitlines() if 'fights' in l and 'W/' in l]
        line = []
        for lid, name in xf.LEEKS.items():
            l = lw.leek(lid)
            if l['level'] > levels[lid]:
                u = xf.unlocks(lw, items, lid, l['level'], levels[lid])
                for x in u:
                    x['leek'] = name
                found += u
                levels[lid] = l['level']
            sp = xf.spend_capital(lw, lid, name)
            l = lw.leek(lid)
            line.append('%s L%d %.1f%%%s' % (name, l['level'], 100.0 * l['xp'] / xf.L300, (' +' + ','.join(sorted(set(sp)))) if sp else ''))
        json.dump(found, open(xf.UNLOCKS, 'w'), indent=1)
        print('round %d (%.0f min): %s\n   %s' % (rnd + 1, (time.time() - t0) / 60, ' | '.join(line), ' ; '.join(summary)), flush=True)
    print('unlocks to review: %d (%s)' % (len(found), xf.UNLOCKS))


if __name__ == '__main__':
    main()
