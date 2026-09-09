#!/usr/bin/env python3
"""Did the phase-2 poison outlive the reserve? Per-turn king damage / poison
ticks / poison effects applied, against the graal's and a leek's death turns.

Usage: python3 tools/boss_king_poison.py <fight_id> [<fight_id> ...] [--leek KurtGodel]

Reads data/fight_cache/<id>.json (populate with tools/boss_says.py --last N).
Action codes: 6 NEW_TURN, 5 PLAYER_DEAD, 101 LIFE_LOST, 110 POISON_DAMAGE,
302 ADD_CHIP_EFFECT = [302, chip, eff_idx, eff_in_chip, target, eff_type, value, turns, ...]
(EFFECT_POISON = 13). Entity ids: graal 4, fennel_king 16 (verified on boss 2).
"""
import json
import os
import sys
from collections import defaultdict

KING, GRAAL, POISON = 16, 4, 13


def analyze(fid, leek_name):
    p = f'data/fight_cache/{fid}.json'
    if not os.path.exists(p):
        print(f'=== {fid}: NOT CACHED (run tools/boss_says.py --last N first)')
        return
    d = json.load(open(p))
    data = json.loads(d['data']) if isinstance(d['data'], str) else d['data']
    leek_id = next((l['id'] for l in data['leeks'] if l.get('name') == leek_name), None)
    turn, leek_dead, graal_dead = 0, None, None
    dmg, poison, cast = defaultdict(int), defaultdict(int), defaultdict(list)
    for a in data['actions']:
        if not isinstance(a, list) or not a:
            continue
        c = a[0]
        if c == 6:
            turn += 1
        elif c == 5:
            if a[1] == leek_id and leek_dead is None:
                leek_dead = turn
            if a[1] == GRAAL and graal_dead is None:
                graal_dead = turn
        elif c == 101 and len(a) > 2 and a[1] == KING:
            dmg[turn] += a[2]
        elif c == 110 and len(a) > 2 and a[1] == KING:
            poison[turn] += a[2]
        elif c == 302 and len(a) > 5 and a[4] == KING and a[5] == POISON:
            cast[turn].append((a[1], a[6] if len(a) > 6 else '?', a[7] if len(a) > 7 else '?'))
    after = sum(v for t, v in poison.items() if leek_dead and t > leek_dead)
    print(f'=== {fid}: winner={d.get("winner")} graal dead T{graal_dead} | {leek_name} dead T{leek_dead}')
    print('  turn | king LIFE_LOST | POISON tick | poison effects on king (chip,val,turns)')
    for t in sorted(set(dmg) | set(poison) | set(cast)):
        tag = f'  <-- after {leek_name} death' if leek_dead and t > leek_dead else ''
        print(f'  T{t:>2} | {dmg[t]:>6} | {poison[t]:>6} | {cast[t]}{tag}')
    print(f'  TOTAL king direct {sum(dmg.values())} | poison ticks {sum(poison.values())} '
          f'| poison AFTER {leek_name} death {after}')


def main():
    args = sys.argv[1:]
    leek = 'KurtGodel'
    if '--leek' in args:
        i = args.index('--leek')
        leek = args[i + 1]
        del args[i:i + 2]
    if not args:
        print(__doc__)
        sys.exit(1)
    for fid in args:
        analyze(fid, leek)


if __name__ == '__main__':
    main()
