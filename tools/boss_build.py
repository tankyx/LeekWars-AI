#!/usr/bin/env python3
"""Create (or reuse) a "<XX> Boss" loadout per main leek and apply it.

Stats are capital per stat (computed from the target base values with the
capital cost curve), boss weapons (WEAPONS), boss chip
kit + components as listed here.

    python3 tools/boss_build.py --dry-run
    python3 tools/boss_build.py            # create loadouts + apply them
"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lw_api import LWSession

STAT = [(0, 1, 2), (200, 1, 1), (400, 2, 1), (600, 3, 1)]
LIFE = [(0, 1, 4), (1000, 1, 3), (2000, 1, 2)]


def curve(c, amount):
    t = 0.0
    for i, (step, cap, sup) in enumerate(c):
        nxt = c[i + 1][0] if i + 1 < len(c) else 10 ** 9
        t += max(0, min(amount, nxt) - step) * cap / sup
    return t


def capital(base):
    out = {}
    for k in ('strength', 'wisdom', 'agility', 'resistance', 'science', 'magic'):
        if base.get(k):
            out[k] = int(round(curve(STAT, base[k])))
    out['life'] = int(round(curve(LIFE, base['life'] - 1000)))
    out['tp'] = sum(30 + 5 * i for i in range(base['tp'] - 10))
    out['mp'] = sum(20 * (i + 1) for i in range(base['mp'] - 3))
    return out


# Role-split boss team (2026-10-01): Kurt tank (RES, dome), Margaret buffer (SCI), Ada + Edsger strikers (STR).
PUZZLE = ['resurrection', 'spark', 'teleportation', 'adrenaline', 'motivation', 'leather_boots', 'jump']
# hybrid strikers (own RES 400 / WIS 300 to survive the dive): own shields instead of damage chips
STRIKER = PUZZLE + ['steroid', 'protein', 'regeneration', 'remission', 'liberation', 'armor',
                    'fortress', 'wall', 'solidification', 'shield']
TANK = PUZZLE + ['dome', 'rampart', 'fortress', 'wall', 'carapace', 'solidification', 'armor', 'shield',
                 'liberation', 'antidote']
BUFFER = PUZZLE + ['rage', 'seven_league_boots', 'ferocity', 'doping', 'bark', 'acceleration', 'steroid', 'protein',
                   'wall', 'armor', 'liberation', 'antidote']
# one copy of a component per leek (add-component -> already_equipped)
PLANS = {
    'AdaLovelace': dict(short='AL', base=dict(strength=450, wisdom=170, resistance=320, tp=20, mp=6, life=2540),
                        comps=['core3', 'motherboard2', 'ram2', 'power_supply', 'nuclear_core', 'ssd', 'obsidian_plate', 'soursop'],
                        chips=STRIKER),
    'EdsgerDijkstra': dict(short='ED', base=dict(strength=440, wisdom=220, resistance=275, tp=20, mp=7, life=2390),
                           comps=['core3', 'motherboard2', 'ram2', 'power_supply', 'nuclear_core', 'ssd', 'obsidian_plate', 'copper_spring'],
                           chips=STRIKER),
    'KurtGodel': dict(short='KG', base=dict(resistance=560, tp=20, mp=7, life=2555),
                      comps=['core3', 'motherboard2', 'ram3', 'power_supply', 'nuclear_core', 'obsidian_plate', 'amazonite_plate', 'watercooling'],
                      chips=TANK),
    'MargaretHamilton': dict(short='MH', base=dict(science=500, tp=17, mp=7, life=3363),
                             comps=['core3', 'neural_core_pro', 'ram2', 'motherboard2', 'ram3', 'nuclear_core', 'ssd', 'power_supply'],
                             chips=BUFFER),
}
# Boss weapons (item ids); the forgotten weapon goes IN the weapons list — the server
# files it under forgotten_weapons itself (a separate forgotten_weapons field is ignored).
WEAPONS = {'AdaLovelace': [47, 180, 153, 225],        # m_laser, lightninger, rhino, enhanced lightninger
           'EdsgerDijkstra': [47, 180, 153, 118],     # m_laser, lightninger, rhino, unbridled gazor
           'KurtGodel': [47, 180, 153, 187],          # m_laser, lightninger, rhino, dark katana (quantum rifle is half SCI nova: no SCI here)
           'MargaretHamilton': [48, 46, 39, 506]}    # gazor, flame thrower, double gun, plutonium bazooka
LEEKS = {'AdaLovelace': 20443, 'EdsgerDijkstra': 129288, 'KurtGodel': 129295, 'MargaretHamilton': 129296}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--only', default='', help='comma list of leek names (default: all four)'); a = ap.parse_args()
    lw = LWSession('main')
    I = lw.get('/item/get-all')
    item = {v['name']: int(k) for k, v in I.items()}
    item.update({'component_' + v['name']: int(k) for k, v in I.items() if v.get('type') == 8})
    loads = {l['name']: l for l in lw.get('/loadout/get-all')['loadouts']}
    for n, p in PLANS.items():
        if a.only and n not in a.only.split(','):
            continue
        stats = capital(p['base'])
        assert sum(stats.values()) <= 1780, (n, sum(stats.values()))
        solo = loads['%s Solo' % p['short']]
        chips = [item['chip_' + c] for c in p['chips']]
        comps = [{'index': i, 'template': item['component_' + c]} for i, c in enumerate(p['comps'])]
        name = '%s Boss' % p['short']
        print('%s: capital %d %s\n   chips %d, comps %s, weapons %s' % (
            name, sum(stats.values()), stats, len(chips), p['comps'], WEAPONS[n]))
        if a.dry_run:
            continue
        if name in loads:
            sid = loads[name]['id']
            r = lw.call('PUT', '/loadout/update', set_id=sid, name=name, icon='', weapons=json.dumps(WEAPONS[n]), chips=json.dumps(chips),
                        components=json.dumps(comps), stats=json.dumps(stats))
        else:
            r = lw.post('/loadout/create', name=name, icon='', weapons=json.dumps(WEAPONS[n]), chips=json.dumps(chips),
                        components=json.dumps(comps), stats=json.dumps(stats))
            sid = (r.get('set') or {}).get('id') if isinstance(r, dict) else None
        print('   loadout', sid, str(r)[:160])
        if not sid:
            continue
        r = lw.post('/loadout/apply', set_id=sid, leek_id=LEEKS[n], use_restat='true')
        print('   apply', str(r)[:200])
        l = lw.leek(LEEKS[n])
        print('   now: capital left %s  life %s STR %s MAG %s WIS %s RES %s TP %s MP %s RAM %s cores %s | chips %d weapons %d comps %d' % (
            l['capital'], l['total_life'], l['total_strength'], l['total_magic'], l['total_wisdom'], l['total_resistance'],
            l['total_tp'], l['total_mp'], l['total_ram'], l['total_cores'], len(l['chips']), len(l['weapons']),
            len([c for c in l.get('components') or [] if c])))


if __name__ == '__main__':
    main()
