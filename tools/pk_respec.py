#!/usr/bin/env python3
"""Pumpkin respec (owner 2026-10-27: "Long shot: respec + live tries", until the event ends Nov 1).

Six leeks move toward the winners' builds, budget-neutral (same capital): life -> RES on Kirby / GTGabi /
LeekRain, the three mages MAG -> STR with STR weapons (Payou, DawnFall, DuskHope; the last two also life -> RES).
Local sim (40 paired seeds): 24-25k dealt vs 14k, still 0 wins. Zoulman and ProdigalSon stay as they are.

    python3 tools/pk_respec.py apply [--dry-run]   # save "<tag> Ladder" loadouts, apply "<tag> PkRespec"
    python3 tools/pk_respec.py revert [--dry-run]  # apply "<tag> Ladder" and verify vs the snapshot

The ladder state is in data/ladder/pk_respec_snapshot.json (taken before the respec). A restat potion is
used whenever a stat drops (main: bought potion_restat, Cure: potion_restat_admin).
"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession
import boss_swap as bs

SNAP = os.path.join(ROOT, 'data', 'ladder', 'pk_respec_snapshot.json')
TAG = {'Kirby54': 'AL', 'GTGabi': 'ED', 'Payou': 'MH', 'LeekRain': 'LR', 'DawnFall': 'DF', 'DuskHope': 'DH',
       'ProdigalSon': 'PS', 'Zoulman': 'KG'}   # PS / KG: step 2 (pk_respec_res.py)
# capital per stat (boss_swap.curve); every map sums to the leek's whole budget
RESPEC = {
    'Kirby54': {'strength': 560, 'wisdom': 200, 'agility': 120, 'resistance': 100, 'life': 300, 'tp': 380, 'mp': 120},
    'GTGabi': {'strength': 574, 'agility': 274, 'resistance': 50, 'life': 232, 'tp': 450, 'mp': 200},
    'Payou': {'wisdom': 200, 'agility': 170, 'resistance': 90, 'strength': 496, 'life': 254, 'tp': 450, 'mp': 120},
    'LeekRain': {'strength': 580, 'wisdom': 50, 'science': 241, 'resistance': 100, 'life': 198, 'tp': 450, 'mp': 60},
    'DawnFall': {'wisdom': 105, 'agility': 29, 'strength': 460, 'resistance': 100, 'life': 260, 'tp': 605, 'mp': 120},
    'DuskHope': {'wisdom': 160, 'agility': 43, 'strength': 520, 'resistance': 100, 'life': 106, 'tp': 690, 'mp': 60},
}
WEAPONS = {'Payou': ['destroyer', 'grenade_launcher', 'laser', 'b_laser'],
           'DawnFall': ['destroyer', 'unstable_destroyer', 'grenade_launcher', 'laser'],
           'DuskHope': ['destroyer', 'illicit_grenade_launcher', 'grenade_launcher', 'b_laser']}


def base_from_capital(cap, level=301):
    """Base stat values a capital map buys (inverse of boss_swap.curve)."""
    def inv(c, spend):
        v = 0.0
        for i, (step, k, sup) in enumerate(c):
            nxt = c[i + 1][0] if i + 1 < len(c) else 10 ** 9
            seg = (nxt - step) * k / sup
            if spend <= seg:
                return v + spend * sup / k
            v += nxt - step; spend -= seg
        return v
    out = {k: round(inv(bs.STAT, cap.get(k, 0))) for k in ('strength', 'wisdom', 'agility', 'resistance', 'science', 'magic')}
    out['life'] = 100 + 3 * (level - 1) + round(inv(bs.LIFE, cap.get('life', 0)))   # level life: 1000 at 301
    tp, c = 10, cap.get('tp', 0)
    while c >= 30 + 5 * (tp - 10):
        c -= 30 + 5 * (tp - 10); tp += 1
    mp, c = 3, cap.get('mp', 0)
    while c >= 20 * (mp - 2):
        c -= 20 * (mp - 2); mp += 1
    out['tp'], out['mp'] = tp, mp
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['apply', 'revert'])
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    snap = json.load(open(SNAP))
    bad = 0
    for acct in ('main', 'cure'):
        lw = LWSession(acct)
        I = lw.get('/item/get-all'); I = I.get('items', I)
        weap_id = {v['name'][7:]: int(k) for k, v in I.items() if v['name'].startswith('weapon_')}
        los = {x['name']: x for x in lw.get('/loadout/get-all')['loadouts']}
        for n, sn in snap.items():
            if sn['acct'] != acct:
                continue
            lid = sn['id']
            comps = [{'index': i, 'template': c[0]} for i, c in enumerate(sn['components']) if c]
            want_w = [weap_id[w] for w in WEAPONS[n]] if n in WEAPONS else sn['weapons']
            kinds = {'Ladder': (sn['weapons'], sn['capital'])}
            if n in RESPEC:
                kinds['PkRespec'] = (want_w, RESPEC[n])
            if a.action == 'apply' and n not in RESPEC:
                continue
            if a.action == 'apply':
                assert sum(RESPEC[n].values()) == sum(sn['capital'].values()) + (sn.get('capital_left') or 0), n
            for kind, (w, st) in kinds.items():
                name = '%s %s' % (TAG[n], kind)
                if name in los:
                    if not a.dry_run:
                        bs.update(lw, los[name], w, sn['chips'], comps, st)
                elif not a.dry_run:
                    r = bs.call(lw, 'POST', '/loadout/create', name=name, icon='', weapons=json.dumps(w),
                                chips=json.dumps(sn['chips']), components=json.dumps(comps), stats=json.dumps(st))
                    print('  %s created: %s' % (name, str(r)[:100]))
            los = {x['name']: x for x in lw.get('/loadout/get-all')['loadouts']}
            target = 'PkRespec' if a.action == 'apply' else 'Ladder'
            exp = base_from_capital(RESPEC[n], 301 if acct == 'main' else 300) if a.action == 'apply' else {k: sn['base'][k] for k in sn['base'] if k != 'frequency'}
            print('%s %s -> %s: base %s weapons %s' % (n, a.action, target, exp, WEAPONS.get(n, 'unchanged') if target == 'PkRespec' else 'ladder'))
            if a.dry_run:
                continue
            r = bs.call(lw, 'POST', '/loadout/apply', set_id=los['%s %s' % (TAG[n], target)]['id'], leek_id=lid, use_restat='true')
            print('  apply: %s' % (str(r)[:160] if r not in ({}, [], None) else 'ok'))
            got = bs.state(bs.leek(lw, lid))
            diffs = {k: (exp[k], got['base'][k]) for k in exp if abs((got['base'][k] or 0) - exp[k]) > 1}
            for k in ('chips', 'components', 'ai'):
                if got[k] != sn[k]:
                    diffs[k] = (sn[k], got[k])
            if sorted(got['weapons']) != sorted(want_w if target == 'PkRespec' else sn['weapons']):
                diffs['weapons'] = got['weapons']
            bad += bool(diffs)
            print('  %s: %s | total life %s str %s mag %s res %s' % (n, 'OK' if not diffs else 'DIFF %s' % diffs,
                  got['total']['total_life'], got['total']['total_strength'], got['total']['total_magic'], got['total']['total_resistance']))
    if bad:
        sys.exit(2)


if __name__ == '__main__':
    main()
