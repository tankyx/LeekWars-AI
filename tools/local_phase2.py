#!/usr/bin/env python3
"""Phase-2 sandbox: our 4 leeks (live builds) vs 8 passive fennel-named units, no graal.
Usage: python3 tools/local_phase2.py [--seed S] [--ai test/ai/do_nothing.lk] [--rounds N]"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import local_boss_v9 as h
import local_test as lt

ARMY = [("fennel_king", 10000, 170), ("fennel_scribe", 6000, 259), ("fennel_knight", 4000, 201),
        ("fennel_knight", 4000, 271), ("fennel_knight", 4000, 309), ("fennel_knight", 4000, 307),
        ("fennel_squire", 2000, 167), ("fennel_squire", 2000, 275)]


def build(cfg, seed, ai):
    scn = h.build(cfg, seed, None)
    crystals = [e for e in scn['entities'][1] if 'crystal' in e['name']]
    base = dict(crystals[0]) if crystals else dict(scn['entities'][1][0])
    nid = max(e['id'] for t in scn['entities'] for e in t) + 1
    army = []
    for name, life, cell in ARMY:
        e = dict(base)
        e.update(id=nid, name=name, life=life, cell=cell, ai=ai, tp=10, mp=4, strength=300, resistance=0,
                 weapons=[], chips=[])
        army.append(e); nid += 1
    scn['entities'][1] = crystals + army
    scn['map']['team2'] = [e['cell'] for e in scn['entities'][1]]
    return scn


def report(data, rounds):
    fight = data.get('fight', data)
    names = {l['id']: l['name'] for l in fight['leeks']}
    cur = None; rnd = 0; dmg = {}; bugs = 0
    for a in fight['actions']:
        if a[0] == 6: rnd = a[1]
        elif a[0] == 7: cur = a[1]
        elif a[0] == 1002: bugs += 1
        elif a[0] in (101, 110) and len(a) > 2 and str(names.get(a[1], '')).startswith('fennel'):
            dmg[rnd] = dmg.get(rnd, 0) + a[2]
        elif a[0] == 203 and isinstance(a[1], str) and names.get(cur) in h.OURS and rnd <= rounds:
            if any(k in a[1] for k in ('GATHER', 'DUMP', 'DIVE', 'POKE', 'MELEE', 'SBOT', 'REVIVE')):
                print(f'  R{rnd:>2} {names[cur][:3]}: {a[1][:110]}')
    tot = sum(v for r, v in dmg.items() if r <= rounds)
    print(f'  dmg to army per round: {[(r, dmg.get(r, 0)) for r in range(1, rounds + 1)]}')
    print(f'  total through R{rounds}: {tot}  bugs={bugs}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, default=12345)
    ap.add_argument('--ai', default='test/ai/do_nothing.lk')
    ap.add_argument('--rounds', type=int, default=16)
    a = ap.parse_args()
    h.clear_cache()
    cfg = lt.load_configs()
    scn = build(cfg, a.seed, a.ai)
    data = h.run(scn)
    report(data, a.rounds)


if __name__ == '__main__':
    main()
