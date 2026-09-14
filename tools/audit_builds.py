#!/usr/bin/env python3
"""
Build coherence audit: does each leek's capital, components, weapons and chips
actually serve the same plan?

Scaling rules used (see CLAUDE.md / generator Effect.java):
  weapon + chip DAMAGE  -> STRENGTH   (always; never MAG)
  POISON / debuff       -> MAGIC
  HEAL / lifesteal      -> WISDOM
  SHIELD cast by holder -> RESISTANCE
  NOVA / summons        -> SCIENCE
  crit + damage-return  -> AGILITY
So a stat is "dead" when the leek has invested in it but carries nothing that
scales off it, and an item is "orphaned" when it scales off a stat the leek
does not have.

Usage: python3 tools/audit_builds.py [--account main|cure]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lw_api import LWSession  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# chips grouped by the stat they scale from (names as in item_get-all.json)
POISON = {'chip_covid', 'chip_plague', 'chip_toxin', 'chip_arsenic', 'chip_venom',
          'chip_soporific', 'chip_ball_and_chain', 'chip_fracture', 'chip_slow_down',
          'chip_tranquilizer'}
HEAL = {'chip_regeneration', 'chip_remission', 'chip_cure', 'chip_bandage',
        'chip_drip', 'chip_therapy', 'chip_vaccine', 'chip_serum'}
SHIELD = {'chip_shield', 'chip_helmet', 'chip_armor', 'chip_armoring', 'chip_wall',
          'chip_rampart', 'chip_fortress', 'chip_solidification', 'chip_carapace',
          'chip_dome', 'chip_bark'}
# damage-return scales off AGILITY, not resistance - these are correct on a
# reflect build and must NOT be flagged as shields with low RES.
REFLECT = {'chip_thorn', 'chip_mirror', 'chip_bramble'}
# nova chips per item_roles.lk (SCIENCE-scaled max-HP reduction)
NOVA_EXTRA = {'chip_alteration', 'chip_mutation'}
NOVA = {'chip_transmutation', 'chip_desintegration', 'chip_precipitation'} | NOVA_EXTRA
SUMMON = {'chip_puny_bulb', 'chip_rocky_bulb', 'chip_fire_bulb', 'chip_iced_bulb',
          'chip_lightning_bulb', 'chip_metallic_bulb', 'chip_savant_bulb',
          'chip_healer_bulb', 'chip_tactician_bulb', 'chip_wizard_bulb'}

STAT_USERS = {'strength': 'weapons/damage chips', 'magic': 'poison chips',
              'wisdom': 'heal chips', 'resistance': 'shield chips',
              'science': 'nova/summons', 'agility': 'crit + damage return'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--account', default='main', choices=['main', 'cure'])
    args = ap.parse_args()
    with open(os.path.join(HERE, 'item_get-all.json')) as f:
        raw = json.load(f)
    by_id = {int(v['id']): v for v in raw.values()}
    with open(os.path.join(HERE, 'component_stats.json')) as f:
        cstats = json.load(f)
    nm = lambda t: by_id.get(t, {}).get('name', str(t))  # noqa: E731

    lw = LWSession(args.account)
    leeks = lw.farmer.get('leeks', {})
    leeks = list(leeks.values()) if isinstance(leeks, dict) else list(leeks)

    for meta in sorted(leeks, key=lambda x: x.get('name', '')):
        L = lw.leek(meta['id'])
        st = {k: (L.get(k) or 0) for k in
              ('strength', 'magic', 'wisdom', 'resistance', 'science', 'agility')}
        weapons = [nm(w['template']) for w in (L.get('weapons') or []) if w]
        chips = [nm(c['template']) for c in (L.get('chips') or []) if c]
        comps = [c for c in (L.get('components') or []) if c]

        has = {
            'strength': bool(weapons),
            'magic': any(c in POISON for c in chips),
            'wisdom': any(c in HEAL for c in chips),
            'resistance': any(c in SHIELD for c in chips),
            'science': any(c in NOVA or c in SUMMON for c in chips),
            'agility': True,   # crit always applies
        }
        print(f"\n=== {L.get('name')} (L{L.get('level')} HP{L.get('life')} "
              f"TP{L.get('tp')} MP{L.get('mp')})")
        print('   stats: ' + '  '.join(f'{k[:3].upper()}{v}' for k, v in st.items()))
        print(f'   weapons: {weapons}')

        issues = []
        for k, v in st.items():
            if v >= 100 and not has[k]:
                issues.append(f'{v} {k.upper()} but no {STAT_USERS[k]} equipped -> dead stat')
        # items that scale off a stat the leek lacks
        if st['magic'] < 100:
            orph = [c for c in chips if c in POISON]
            if orph:
                issues.append(f'poison chips with MAG {st["magic"]}: {orph}')
        if st['wisdom'] < 100:
            orph = [c for c in chips if c in HEAL]
            if orph:
                issues.append(f'heal chips with WIS {st["wisdom"]}: {orph}')
        if any(c in REFLECT for c in chips) and st['agility'] < 100:
            issues.append(f'damage-return chips with AGI {st["agility"]}: '
                          f'{[c for c in chips if c in REFLECT]}')
        if st['resistance'] < 100:
            orph = [c for c in chips if c in SHIELD]
            if orph:
                issues.append(f'shield chips with RES {st["resistance"]} '
                              f'(shields scale off the caster RES): {orph[:6]}')
        if st['science'] < 100:
            orph = [c for c in chips if c in NOVA or c in SUMMON]
            if orph:
                issues.append(f'nova/summon chips with SCI {st["science"]}: {orph}')

        # component contribution vs the build
        dead_comp = []
        for c in comps:
            base = dict(cstats.get(str(c['template']), {}).get('stats', []))
            base.update(c.get('stats') or {})
            useful = sum(v for k, v in base.items()
                         if k in ('life', 'tp', 'mp', 'ram', 'cores', 'frequency')
                         or (k in st and (st.get(k, 0) >= 100 or has.get(k))))
            total = sum(abs(v) for v in base.values())
            if total and useful / total < 0.5:
                dead_comp.append((nm(c['template']), base))
        for n, b in dead_comp:
            issues.append(f'component {n} mostly feeds unused stats: {b}')

        if issues:
            for i in issues:
                print(f'   [!] {i}')
        else:
            print('   coherent: every invested stat has something that uses it')


if __name__ == '__main__':
    main()
