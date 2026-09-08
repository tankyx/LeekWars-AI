#!/usr/bin/env python3
"""Per-fight sustain audit: damage taken / healed per round by our leeks, KG shield casts.
Usage: python3 tools/boss_dmg.py <fid> [...]  (uses data/fight_cache)"""
import json
import sys

OURS = ('KurtGodel', 'AdaLovelace', 'MargaretHamilton', 'EdsgerDijkstra')
SHIELD_CHIPS = {29: 'fort', 23: 'wall', 24: 'ramp', 81: 'cara', 22: 'armor', 20: 'shield', 67: 'arming', 96: 'solid', 173: 'dome'}


def audit(fid):
    raw = json.load(open(f'data/fight_cache/{fid}.json'))
    d = raw['data']
    if isinstance(d, str):
        d = json.loads(d)
    names = {l['id']: l.get('name') for l in d['leeks']}
    cur = None
    rnd = 0
    dmg = {}
    heal = {}
    shields = {}
    graal = None
    dead = {}
    for a in d['actions']:
        if a[0] == 6:
            rnd = a[1]
        elif a[0] == 7:
            cur = a[1]
        elif a[0] in (101, 110) and len(a) > 2 and names.get(a[1]) in OURS:
            dmg.setdefault(rnd, {}).setdefault(names[a[1]][:3], 0)
            dmg[rnd][names[a[1]][:3]] += a[2]
        elif a[0] == 103 and len(a) > 2 and names.get(a[1]) in OURS:
            heal.setdefault(rnd, {}).setdefault(names[a[1]][:3], 0)
            heal[rnd][names[a[1]][:3]] += a[2]
        elif a[0] == 302 and len(a) > 6 and names.get(cur) in OURS and a[1] in SHIELD_CHIPS:
            shields.setdefault(rnd, []).append(f"{names[cur][:2]}:{SHIELD_CHIPS[a[1]]}>{str(names.get(a[4], '?'))[:3]}")
        elif a[0] == 5 and len(a) > 2:
            if names.get(a[1]) == 'graal':
                graal = rnd
            elif names.get(a[1]) in OURS:
                dead[names[a[1]][:3]] = rnd
    print(f'=== {fid} graal@{graal} dead={dead}')
    tot = 0
    for r in sorted(set(dmg) | set(heal) | set(shields)):
        dm = dmg.get(r, {})
        tot += sum(dm.values())
        print(f"  R{r:>2} dmg {sum(dm.values()):>5} {dm}  heal {sum(heal.get(r, {}).values()):>4}  shields {' '.join(shields.get(r, []))}")
        if r > 20:
            break
    print(f'  total dmg taken through R{min(rnd, 21)}: {tot}')


if __name__ == '__main__':
    for f in sys.argv[1:]:
        audit(int(f))
