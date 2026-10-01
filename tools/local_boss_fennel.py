#!/usr/bin/env python3
"""Local check of BOSS/fennel.lk (kill+resurrect puzzle) on real Fennel geometry.
No army locally, so it only validates the crystal solve: every leek gets the
boss kit (spark/teleportation/resurrection/adrenaline + stack) on top of its
live chips.

    python3 tools/local_boss_fennel.py --fight 53569989 --seeds 3
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import local_boss_v9 as lb
import local_test as lt

KIT = ['resurrection', 'spark', 'teleportation', 'adrenaline', 'motivation', 'leather_boots', 'jump', 'shield', 'fortress',
       'wall', 'armor', 'solidification', 'regeneration', 'remission', 'knowledge', 'elevation', 'liberation']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fight', type=int, default=None)
    ap.add_argument('--seeds', type=int, default=1)
    ap.add_argument('--seed', type=int, default=12345)
    a = ap.parse_args()
    lb.clear_cache()
    g = json.load(open(os.path.join(str(lt.GENERATOR_DIR), 'data', 'chips.json')))
    ids = {v['name']: int(k) for k, v in g.items()}
    configs = lt.load_configs()
    for k in range(a.seeds):
        scn = lb.build(configs, a.seed + k, a.fight)
        for e in scn['entities'][0]:
            e['ai'] = 'BOSS/fennel.lk'
            e['chips'] = list(dict.fromkeys(list(e['chips']) + [ids[n] for n in KIT]))
        data = lb.run(scn)
        fight = data.get('fight', data)
        names = {l['id']: l['name'] for l in fight['leeks']}
        rnd = 0; out = []
        for x in fight['actions']:
            if x[0] == 6:
                rnd = x[1]
            elif x[0] == 105:
                out.append('R%d resurrect %s -> %s' % (rnd, names.get(x[2]), x[3]))
            elif x[0] == 5 and len(x) > 1 and names.get(x[1]) in ('graal',):
                out.append('R%d GRAAL DEAD' % rnd)
            elif x[0] == 1002:
                if not out or 'BUG' not in out[-1]:
                    out.append('R%d BUG' % rnd)
        logs = data.get('logs') or {}
        print('=== seed %d  geometry %s' % (a.seed + k, a.fight))
        for line in out:
            print('  ', line)
        for farmer in (logs.values() if isinstance(logs, dict) else []):
            for idx in sorted(farmer, key=int):
                for l in farmer[idx]:
                    s = str(l[2]) if isinstance(l, list) and len(l) > 2 else str(l)
                    if 'BOSS' in s or 'rror' in s:
                        print('   log', s[:240])


if __name__ == '__main__':
    main()
