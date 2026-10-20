#!/usr/bin/env python3
"""Swap Cure's leeks between their ladder chips and a boss chip kit. Owner 2026-10-20: "Focus on bosses",
8-leek Pumpkin first, every credit to bosses, full boss kit bought with Cure's habs.

    python3 tools/cure_kit.py snapshot             # save each Cure leek's chips (data/ladder/cure_kit_snapshot.json)
    python3 tools/cure_kit.py apply pumpkin [--dry-run]
    python3 tools/cure_kit.py restore [--dry-run]  # back to the snapshot's chips

Chips only: weapons, components, stats and the AI path are not touched, so no restat potion is used.
In the 8-leek Pumpkin the turn order (frequency) gives the block duties: DawnFall plays right before
turban; LeekRain, DuskHope and ProdigalSon play before the resurrected brothers. Every Cure leek
carries the V10 Pumpkin mode's tools:
  - blockers: bulb, boots, teleportation, puny bulb, jump
  - sustain: knowledge before remission / regeneration
  - shields: fortress, wall, solidification, armor, and rampart on allies
"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession

LEEKS = {'LeekRain': 19703, 'DawnFall': 21175, 'DuskHope': 129801, 'ProdigalSon': 130236}
SNAP = os.path.join(ROOT, 'data', 'ladder', 'cure_kit_snapshot.json')
PK_CORE = ['seven_league_boots', 'teleportation', 'puny_bulb', 'leather_boots', 'jump', 'knowledge', 'remission',
           'regeneration', 'fortress', 'wall', 'solidification', 'rampart', 'antidote', 'armor']
KITS = {'pumpkin': {
    'LeekRain': ['savant_bulb'] + PK_CORE + ['protein'],                          # 16 slots, STR/SCI (boots +2-3 MP)
    'DawnFall': ['wizard_bulb'] + PK_CORE + ['covid', 'toxin', 'venom', 'elevation'],  # 19 slots, MAG
    'DuskHope': ['wizard_bulb'] + PK_CORE + ['covid', 'toxin'],                   # 17 slots, MAG
    'ProdigalSon': ['savant_bulb'] + PK_CORE,                                     # 15 slots, STR/RES
}}


def call(lw, method, path, **data):
    r = None
    for _ in range(6):
        r = lw.call(method, path, **data)
        if isinstance(r, dict) and r.get('error') == 'rate_limit':
            time.sleep(1.2); continue
        return r
    return r


def names(lw):
    I = lw.get('/item/get-all')
    return {int(k): v['name'].replace('chip_', '') for k, v in I.items() if v['name'].startswith('chip_')}


def inventory(lw, nm):
    f = lw.get('/farmer/get-from-token'); f = f.get('farmer', f)
    return {nm.get(x['template']): x for x in f['chips'] if x.get('quantity', 0) > 0}


def set_chips(lw, lid, want, nm, dry):
    """Make the leek's chips exactly `want` (template ids); returns the names that could not be added."""
    l = lw.leek(lid)
    have = {c['template']: c['id'] for c in l['chips']}
    remove = [t for t in have if t not in want]
    add = [t for t in want if t not in have]
    print('  %s: remove %s' % (l['name'], [nm.get(t, t) for t in remove]))
    print('  %s: add    %s' % (l['name'], [nm.get(t, t) for t in add]))
    if dry:
        return []
    for t in remove:
        r = call(lw, 'DELETE', '/leek/remove-chip', leek_id=lid, chip_id=have[t])
        if isinstance(r, dict) and r.get('error'):
            print('    remove %s failed: %s' % (nm.get(t, t), r))
    missing = []
    for t in add:
        inv = inventory(lw, nm).get(nm.get(t))
        r = call(lw, 'POST', '/leek/add-chip', leek_id=lid, chip_id=inv['id']) if inv else {'error': 'none in inventory'}
        if isinstance(r, dict) and r.get('error'):
            print('    add %s failed: %s' % (nm.get(t, t), r)); missing.append(nm.get(t, t))
    return missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['snapshot', 'apply', 'restore'])
    ap.add_argument('kit', nargs='?', default='pumpkin', choices=sorted(KITS))
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    lw = LWSession('cure'); nm = names(lw); rev = {v: k for k, v in nm.items()}
    if a.action == 'snapshot':
        snap = {n: [c['template'] for c in lw.leek(lid)['chips']] for n, lid in LEEKS.items()}
        if any('resurrection' in [nm.get(t) for t in v] or 'savant_bulb' in [nm.get(t) for t in v] for v in snap.values()):
            sys.exit('a Cure leek already carries boss chips - not overwriting the ladder snapshot')
        json.dump(snap, open(SNAP, 'w'), indent=1)
        for n, v in snap.items():
            print('  %s: %s' % (n, [nm.get(t, t) for t in v]))
        print('saved %s' % SNAP)
        return
    if not os.path.exists(SNAP):
        sys.exit('no snapshot - run "snapshot" first')
    snap = json.load(open(SNAP))
    bad = 0
    for n, lid in LEEKS.items():
        if a.action == 'apply':
            l = lw.leek(lid)
            kit = KITS[a.kit][n][:l['max_chips']]
            want = [rev[c] for c in kit]
        else:
            want = snap[n]
        miss = set_chips(lw, lid, want, nm, a.dry_run)
        if not a.dry_run:
            got = sorted(nm.get(c['template']) for c in lw.leek(lid)['chips'])
            exp = sorted(nm.get(t) for t in want)
            ok = got == exp
            bad += not ok
            print('  %s: %s%s' % (n, 'OK' if ok else 'MISMATCH got %s' % got, (' (missing %s)' % miss) if miss else ''))
    if bad:
        sys.exit(2)


if __name__ == '__main__':
    main()
