#!/usr/bin/env python3
"""Pumpkin respec, step 2 (2026-10-28): +200 RES on top of the Pumpkin builds, paid with STR capital.

Calibrated sim (80 paired seeds, live pumpkin / hubbard hits): dead by round 8 5.61 -> 4.75, dealt +1.4k,
wins 2 -> 4 (the pumpkin lands 80% of the killing blows; relative shields scale with the caster's RES).

    python3 tools/pk_respec_res.py apply [--leeks Kirby54,LeekRain] [--dry-run]

Stats only: the loadout carries the leek's current weapons, chips and components. The state before is
saved in data/ladder/pk_respec_res_snapshot.json; Zoulman / ProdigalSon (not in the first respec) get
their ladder state added to data/ladder/pk_respec_snapshot.json so `pk_respec.py revert` covers them.
"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession
import boss_swap as bs
import pk_respec as pr

LEEKS = {'main': {'Kirby54': 20443, 'GTGabi': 129288, 'Zoulman': 129295, 'Payou': 129296},
         'cure': {'LeekRain': 19703, 'DawnFall': 21175, 'DuskHope': 129801, 'ProdigalSon': 130236}}
TAG = dict(pr.TAG, Zoulman='KG', ProdigalSon='PS')
SNAP2 = os.path.join(ROOT, 'data', 'ladder', 'pk_respec_res_snapshot.json')
CURE_LADDER = os.path.join(ROOT, 'data', 'ladder', 'cure_kit_snapshot.json')
RES_GAIN = 200


def plan(l):
    """Capital map with +RES_GAIN base RES, the capital taken from STR (the capital left first)."""
    cap = bs.capital_map(l)
    left = l.get('capital') or 0
    r0 = l['resistance'] or 0
    need = round(bs.curve(bs.STAT, r0 + RES_GAIN)) - cap.get('resistance', 0)
    new = dict(cap)
    new['resistance'] = cap.get('resistance', 0) + need
    new['strength'] = cap.get('strength', 0) - max(0, need - left)
    return new, need


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['apply'])
    ap.add_argument('--leeks', default='')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    only = set(x for x in a.leeks.split(',') if x)
    snap1 = json.load(open(pr.SNAP))
    snap2 = json.load(open(SNAP2)) if os.path.exists(SNAP2) else {}
    cure_ladder = json.load(open(CURE_LADDER))
    bad = 0
    for acct, leeks in LEEKS.items():
        lw = LWSession(acct)
        los = {x['name']: x for x in lw.get('/loadout/get-all')['loadouts']}
        for n, lid in leeks.items():
            if only and n not in only:
                continue
            l = bs.leek(lw, lid); st = bs.state(l)
            new, need = plan(l)
            lv = l.get('level') or 301
            exp = pr.base_from_capital(new, lv)
            print('%-11s RES %d -> %d, STR %d -> %d (capital moved %d)' % (n, l['resistance'], exp['resistance'], l['strength'],
                                                                         exp['strength'], need))
            if a.dry_run:
                continue
            snap2.setdefault(n, dict(st, capital=bs.capital_map(l), acct=acct, id=lid))
            if n not in snap1:          # ladder state for the Nov 1 revert (pk_respec.py revert)
                ladder = dict(st, capital=bs.capital_map(l), acct=acct, id=lid, name=l['name'], capital_left=l.get('capital'))
                if n in cure_ladder:
                    ladder['chips'] = sorted(cure_ladder[n])
                snap1[n] = ladder
            comps = [{'index': i, 'template': c[0]} for i, c in enumerate(st['components']) if c]
            name = '%s PkRes' % TAG[n]
            if name in los:
                bs.update(lw, los[name], st['weapons'], st['chips'], comps, new)
            else:
                r = bs.call(lw, 'POST', '/loadout/create', name=name, icon='', weapons=json.dumps(st['weapons']),
                            chips=json.dumps(st['chips']), components=json.dumps(comps), stats=json.dumps(new))
                print('  %s created: %s' % (name, str(r)[:80]))
            los = {x['name']: x for x in lw.get('/loadout/get-all')['loadouts']}
            r = bs.call(lw, 'POST', '/loadout/apply', set_id=los[name]['id'], leek_id=lid, use_restat='true')
            print('  apply: %s' % (str(r)[:120] if r not in ({}, [], None) else 'ok'))
            got = bs.state(bs.leek(lw, lid))
            diffs = {k: (exp[k], got['base'][k]) for k in exp if abs((got['base'][k] or 0) - exp[k]) > 1}
            for k in ('chips', 'components', 'ai', 'weapons'):
                if sorted(map(str, got[k] or [])) != sorted(map(str, st[k] or [])):
                    diffs[k] = 'changed'
            bad += bool(diffs)
            print('  %s: %s | total RES %s STR %s life %s' % (n, 'OK' if not diffs else 'DIFF %s' % diffs, got['total']['total_resistance'],
                                                              got['total']['total_strength'], got['total']['total_life']))
    if not a.dry_run:
        json.dump(snap2, open(SNAP2, 'w'), indent=1)
        json.dump(snap1, open(pr.SNAP, 'w'), indent=1)
    if bad:
        sys.exit(2)


if __name__ == '__main__':
    main()
