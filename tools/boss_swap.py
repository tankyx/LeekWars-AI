#!/usr/bin/env python3
"""Swap the main leeks between their ladder setup and the Fennel boss setup with the saved loadouts
("XX Solo" / "XX Boss"), without ever touching the components (they carry per-instance alterations:
the TP parts would not survive a re-pick by template).

    python3 tools/boss_swap.py snapshot      # exact ladder state -> data/ladder/boss_swap_snapshot.json
    python3 tools/boss_swap.py prepare       # Solo loadouts := that snapshot; Boss loadouts := boss kit
                                              # with the CURRENT components (same index, same template)
    python3 tools/boss_swap.py boss          # apply the Boss loadouts (restat potion where a stat drops)
    python3 tools/boss_swap.py restore       # apply the Solo loadouts, then verify every stat, chip,
                                              # weapon, component instance and AI against the snapshot
    python3 tools/boss_swap.py verify        # the verification only

Boss kits match V10's boss mode (V10/src/80_boss.py): puzzle chips for everyone, Kurt tank (dome),
Margaret buffer (ferocity), Ada + Edsger strikers. Margaret keeps her ladder stats (buffs do not scale
with SCI on live) and weapons; the others take the Boss loadout stats. AI stays 10.0/V10/v10.py.
"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession

LEEKS = {'AL': 20443, 'ED': 129288, 'KG': 129295, 'MH': 129296}
SNAP = os.path.join(ROOT, 'data', 'ladder', 'boss_swap_snapshot.json')
BASE = ('life', 'strength', 'magic', 'wisdom', 'resistance', 'agility', 'science', 'frequency', 'tp', 'mp')
TOTAL = tuple('total_' + k for k in BASE)
PUZZLE = ['resurrection', 'spark', 'teleportation', 'adrenaline', 'motivation', 'leather_boots']
SELF = ['fortress', 'wall', 'armor', 'solidification', 'regeneration', 'remission', 'antidote', 'liberation']
KITS = {   # priority order, trimmed to the leek's max_chips (jump: fennel.lk's approach; plants: tank wall, buffer corn)
    'AL': PUZZLE + ['jump', 'steroid', 'hemorrhage', 'liberation', 'antidote', 'regeneration', 'remission', 'fortress', 'wall',
                    'armor', 'solidification'],
    'ED': PUZZLE + ['jump', 'steroid', 'hemorrhage', 'liberation', 'antidote', 'regeneration', 'fortress', 'wall', 'armor',
                    'remission', 'solidification'],
    'KG': PUZZLE + ['jump', 'dome', 'rampart', 'carapace', 'prototaxite'] + SELF + ['serum', 'elevation'],
    'MH': PUZZLE + ['jump', 'ferocity', 'doping', 'bark', 'rage', 'seven_league_boots', 'steroid', 'protein', 'corn'] + SELF +
          ['serum', 'knowledge', 'elevation', 'shield'],
}
# boss weapons by name (None = keep the ladder weapons); glowing saber on the strikers: it disarms the
# army (King Excalibur, knights' swords, scribe's heavy sword are 44-70% of their damage)
WEAPONS = {'AL': ['rhino', 'glowing_saber', 'heavy_sword', 'enhanced_lightninger'], 'ED': None, 'KG': None,
           'MH': ['glowing_saber', 'flame_thrower', 'gazor', 'plutonium_bazooka']}   # the 4th saber: disarm needs no STR
KEEP_STATS = {'AL', 'ED', 'KG', 'MH'}   # chip-only swaps by default (no restat potion); --boss-stats respecs AL/ED/KG
STAT = [(0, 1, 2), (200, 1, 1), (400, 2, 1), (600, 3, 1)]
LIFE = [(0, 1, 4), (1000, 1, 3), (2000, 1, 2)]


def curve(c, amount):
    t = 0.0
    for i, (step, cap, sup) in enumerate(c):
        nxt = c[i + 1][0] if i + 1 < len(c) else 10 ** 9
        t += max(0, min(amount, nxt) - step) * cap / sup
    return t


# ---- Evil Pumpkin set (2026-10-19): tanky strikers like the winners (life ~3.3k, RES ~400, TP 30) ----
PK_SHIELD = ['teleportation', 'puny_bulb', 'leather_boots', 'jump',              # blockers first (riddle)
             'knowledge', 'remission', 'regeneration', 'fortress', 'wall',     # v12: the winners heal ~16k a fight
             'solidification', 'rampart', 'protein', 'carapace', 'antidote',   # (knowledge +250 WIS before the heals)
             'armor', 'elevation', 'liberation', 'helmet', 'shield']
PK_KITS = {
    # v15: a second summon per blocker - one bulb of each kind can't cover a duty every round (v14: puny on
    # cooldown in 98 of 118 misses, wizard in 62)
    'AL': ['wizard_bulb', 'lightning_bulb', 'seven_league_boots'] + [x for x in PK_SHIELD if x != 'carapace'] + ['steroid', 'adrenaline'],
    'ED': ['savant_bulb', 'tactician_bulb', 'seven_league_boots'] + [x for x in PK_SHIELD if x != 'carapace'] + ['steroid', 'adrenaline'],
    'KG': ['prototaxite', 'wizard_bulb', 'seven_league_boots', 'dome'] + PK_SHIELD + ['steroid', 'armoring', 'serum'],   # warty's T0 blocker; SCI 579: boots +3 MP on himself / the next blocker
    'MH': ['prototaxite', 'wizard_bulb'] + PK_SHIELD + ['venom', 'toxin', 'covid', 'arsenic', 'plague', 'knowledge', 'serum', 'armoring', 'adrenaline'],
}
PK_WEAPONS = {'AL': ['glowing_saber', 'neutrino', 'rifle', 'enhanced_lightninger'],
              'ED': ['glowing_saber', 'neutrino', 'rifle', 'm_laser'],
              'KG': ['glowing_saber', 'neutrino', 'lightninger', 'quantum_rifle'],
              'MH': ['glowing_saber', 'flame_thrower', 'gazor', 'plutonium_bazooka']}
PK_BASE = {'AL': dict(tp=20, mp=7, resistance=320, strength=510),     # v8: the Fennel strikers' lines (damage once
           'ED': dict(tp=20, mp=9, resistance=275, strength=440),     # protections drop early); v10: GTGabi plays right
                                                                      # before warty's T0 rez - MP 9 reaches 93% of its cells
           'KG': dict(tp=20, mp=7, resistance=450),
           'MH': dict(tp=21, mp=6, resistance=400, magic=400)}


def pk_capital(base, budget=1780):
    """Capital per stat for the base values, the rest of the budget in life."""
    out = {}
    for k in ('strength', 'wisdom', 'agility', 'resistance', 'science', 'magic'):
        if base.get(k):
            out[k] = int(round(curve(STAT, base[k])))
    out['tp'] = sum(30 + 5 * i for i in range(base['tp'] - 10))
    out['mp'] = sum(20 * (i + 1) for i in range(base['mp'] - 3))
    rest = budget - sum(out.values())
    if rest > 0:
        out['life'] = rest
    return out


def capital_map(l):
    """Capital spent per stat, from the leek's base values (same curve as the loadout stats maps)."""
    out = {}
    for k in ('strength', 'wisdom', 'agility', 'resistance', 'science', 'magic'):
        if l.get(k):
            out[k] = int(round(curve(STAT, l[k])))
    if l['life'] > 1000:
        out['life'] = int(round(curve(LIFE, l['life'] - 1000)))
    out['tp'] = sum(30 + 5 * i for i in range(l['tp'] - 10))
    out['mp'] = sum(20 * (i + 1) for i in range(l['mp'] - 3))
    return {k: v for k, v in out.items() if v}


def call(lw, method, path, **data):
    r = None
    for _ in range(6):
        r = lw.call(method, path, **data)
        if isinstance(r, dict) and r.get('error') == 'rate_limit':
            time.sleep(1.2); continue
        return r
    return r


def leek(lw, lid):
    for _ in range(6):
        l = lw.leek(lid)
        if l.get('life') is not None and l.get('chips') is not None:
            return l
        time.sleep(1)
    raise SystemExit('leek read failed %d' % lid)


def state(l):
    return {'base': {k: l.get(k) for k in BASE}, 'total': {k: l.get(k) for k in TOTAL},
            'chips': sorted(c['template'] for c in l['chips']),
            'weapons': sorted(w['template'] for w in l['weapons']),
            'components': [[c['template'], c['id']] if c else None for c in (l.get('components') or [])],
            'ai': (l.get('ai') or {}).get('path'), 'max_chips': l['max_chips']}


def loadouts(lw):
    return {x['name']: x for x in lw.get('/loadout/get-all')['loadouts']}


def update(lw, lo, weapons, chips, comps, stats):
    r = call(lw, 'PUT', '/loadout/update', set_id=lo['id'], name=lo['name'], icon=lo.get('icon') or '',
             weapons=json.dumps(weapons), chips=json.dumps(chips), components=json.dumps(comps), stats=json.dumps(stats))
    print('  %s (%d) updated: %s' % (lo['name'], lo['id'], r if r not in ({}, [], None) else 'ok'))


def apply_all(lw, kind, names):
    """Apply every leek's <kind> loadout; a second pass picks up chips another leek still held."""
    los = loadouts(lw)
    for p in (1, 2):
        for s, lid in LEEKS.items():
            lo = los['%s %s' % (s, kind)]
            r = call(lw, 'POST', '/loadout/apply', set_id=lo['id'], leek_id=lid, use_restat='true')
            l = leek(lw, lid)
            miss = sorted(set(names[t] for t in lo['chips']) - set(names[c['template']] for c in l['chips']))
            wmiss = sorted(set(names[t] for t in lo['weapons'] + (lo.get('forgotten_weapons') or [])) -
                           set(names[w['template']] for w in l['weapons']))
            print('  pass %d %s -> %s: %s | TP %s MP %s life %s | missing chips %s weapons %s' % (
                p, s, lo['name'], str(r)[:80] if r not in ({}, [], None) else 'ok', l['total_tp'], l['total_mp'],
                l['total_life'], miss or 'none', wmiss or 'none'))


def verify(lw, snap, names):
    bad = 0
    for s, lid in LEEKS.items():
        want = snap[s]; got = state(leek(lw, lid))
        for k in ('base', 'total', 'chips', 'weapons', 'components', 'ai'):
            if got[k] != want[k]:
                bad += 1
                if k in ('chips', 'weapons'):
                    print('  %s %s DIFF: missing %s extra %s' % (s, k, [names.get(t) for t in want[k] if t not in got[k]],
                                                                  [names.get(t) for t in got[k] if t not in want[k]]))
                elif k in ('base', 'total'):
                    print('  %s %s DIFF: %s' % (s, k, {x: (want[k][x], got[k][x]) for x in want[k] if want[k][x] != got[k][x]}))
                else:
                    print('  %s %s DIFF: want %s got %s' % (s, k, want[k], got[k]))
    print('verify: %s' % ('all four leeks match the snapshot' if not bad else '%d differences' % bad))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['snapshot', 'prepare', 'boss', 'restore', 'verify'])
    ap.add_argument('--force', action='store_true', help='snapshot over an existing snapshot')
    ap.add_argument('--set', default='boss', choices=['boss', 'pumpkin'], help='which loadout set prepare/boss use')
    ap.add_argument('--boss-stats', action='store_true', help='prepare: Boss loadouts keep their boss stats for AL/ED/KG '
                    '(6 restat potions per session)')
    a = ap.parse_args()
    lw = LWSession('main')
    I = lw.get('/item/get-all'); I = I.get('items', I)
    names = {int(k): v['name'].split('_', 1)[1] if v['name'].startswith(('chip_', 'weapon_')) else v['name'] for k, v in I.items()}
    chip_id = {v['name'][5:]: int(k) for k, v in I.items() if v['name'].startswith('chip_')}
    weap_id = {v['name'][7:]: int(k) for k, v in I.items() if v['name'].startswith('weapon_')}
    if a.action == 'snapshot':
        if os.path.exists(SNAP) and not a.force:
            sys.exit('snapshot exists (%s) - restore first, or --force' % SNAP)
        snap = {}
        for s, lid in LEEKS.items():
            l = leek(lw, lid); snap[s] = state(l); snap[s]['capital'] = capital_map(l); snap[s]['name'] = l['name']
            print('%s %s TP %s | chips %s | weapons %s' % (s, l['name'], l['total_tp'], [names[t] for t in snap[s]['chips']],
                                                          [names[t] for t in snap[s]['weapons']]))
        json.dump(snap, open(SNAP, 'w'), indent=1)
        print('saved', SNAP)
        return
    snap = json.load(open(SNAP))
    if a.action == 'prepare' and a.set == 'pumpkin':
        los = loadouts(lw)
        owned = {}
        f = lw.get('/farmer/get-from-token'); f = f.get('farmer', f)
        for x in f.get('chips') or []:
            owned[x['template']] = owned.get(x['template'], 0) + (x.get('quantity') or 0)
        for s_ in LEEKS:
            for t in snap[s_]['chips']:
                owned[t] = owned.get(t, 0) + 1
        for s_ in LEEKS:
            sn = snap[s_]
            comps = [{'index': i, 'template': c[0]} for i, c in enumerate(sn['components']) if c]
            update(lw, los['%s Solo' % s_], sn['weapons'], sn['chips'], comps, sn['capital'])
            kit = []
            for n in PK_KITS[s_]:
                t = chip_id[n]
                if owned.get(t, 0) <= 0:
                    print('  %s: no %s left to equip' % (s_, n)); continue
                if len(kit) < sn['max_chips']:
                    kit.append(t); owned[t] -= 1
            weapons = [weap_id[n] for n in PK_WEAPONS[s_]]
            # --boss-stats: the Pumpkin respec (8 restat potions a session); else chip-only on the ladder stats
            stats = pk_capital(PK_BASE[s_]) if a.boss_stats else sn['capital']
            name = '%s Pumpkin' % s_
            if name in los:
                update(lw, los[name], weapons, kit, comps, stats)
            else:
                r = call(lw, 'POST', '/loadout/create', name=name, icon='', weapons=json.dumps(weapons), chips=json.dumps(kit),
                         components=json.dumps(comps), stats=json.dumps(stats))
                print('  %s created: %s' % (name, str(r)[:120]))
            print('     pumpkin kit %s: %s | weapons %s | stats %s' % (s_, [names[t] for t in kit], PK_WEAPONS[s_], stats))
        return
    if a.action == 'prepare':
        los = loadouts(lw)
        owned = {}
        f = lw.get('/farmer/get-from-token'); f = f.get('farmer', f)
        for x in f.get('chips') or []:
            owned[x['template']] = owned.get(x['template'], 0) + (x.get('quantity') or 0)
        for s in LEEKS:
            for t in snap[s]['chips']:
                owned[t] = owned.get(t, 0) + 1
        for s in LEEKS:
            sn = snap[s]
            comps = [{'index': i, 'template': c[0]} for i, c in enumerate(sn['components']) if c]
            update(lw, los['%s Solo' % s], sn['weapons'], sn['chips'], comps, sn['capital'])
            kit = []
            for n in KITS[s]:
                t = chip_id[n]
                if owned.get(t, 0) <= 0:
                    print('  %s: no %s left to equip' % (s, n)); continue
                if len(kit) < sn['max_chips']:
                    kit.append(t); owned[t] -= 1
            weapons = [weap_id[n] for n in WEAPONS[s]] if WEAPONS[s] else sn['weapons']
            stats = sn['capital']
            if a.boss_stats and s != 'MH':          # the boss builds of tools/boss_build.py
                import boss_build as bb
                full = {'AL': 'AdaLovelace', 'ED': 'EdsgerDijkstra', 'KG': 'KurtGodel'}[s]
                stats = bb.capital(bb.PLANS[full]['base'])
            update(lw, los['%s Boss' % s], weapons, kit, comps, stats)
            print('     boss kit %s: %s | weapons %s | stats %s' % (s, [names[t] for t in kit], [names[t] for t in weapons], stats))
        return
    if a.action == 'boss':
        apply_all(lw, 'Pumpkin' if a.set == 'pumpkin' else 'Boss', names)
        for s, lid in LEEKS.items():
            got = state(leek(lw, lid))
            if got['components'] != snap[s]['components']:
                print('  WARNING %s components changed: %s -> %s' % (s, snap[s]['components'], got['components']))
        return
    if a.action == 'restore':
        apply_all(lw, 'Solo', names)
    verify(lw, snap, names)


if __name__ == '__main__':
    main()
