#!/usr/bin/env python3
"""
Build the 4 Fennel-King bruisers from scratch (leeks reset to zero).

Winning formula (boss-2 leaderboard replays 53142219 / 52782590 / 52821555):
- 4x bruisers STR 600 / WIS 400+ / RES 400+ / HP 3100+ (damage is the defense)
- Puzzle: kill+resurrect (spark the 1-HP crystal, resurrect its body onto the
  goal cell, atomic same turn => no Apocalypse). Only 2 resurrection chips
  exist (not purchasable, cd 15) => MH + ED are the resolvers; all 4 carry the
  slide kit (grapple/boxing/inversion) for the other 2 crystals.
- KG is the support shield-bot (shields scale with HIS RES, buffs with HIS SCI).
- Sustain = remission self-heals (WIS-scaled).

Capital budget: 1780/leek (level 301). stats maps below are CAPITAL per stat.
TP math: spark(3) + resurrection(18) = 21 TP => resolvers get TP 21 via
capital TP 18/19 + power_supply/chiyembekezo (+3/+2 TP from components).
"""
import json
import sys
import time
import requests
from config_loader import load_credentials

BASE = 'https://leekwars.com/api'

# ---------------------------------------------------------------- builds ----
WEAPONS = [39, 37, 42, 180]          # scythe, odachi, sun_spear, lightninger (item templates)
W_INST = {39: 2401160, 37: 137497, 42: 145745, 180: 2315741}  # stack instance ids

CHIP = dict(resurrection=84, spark=18, protein=8, remission=80, flame=5,
            grapple=162, boxing=163, inversion=68, teleport=59, antidote=110,
            adrenaline=16, steroid=25, wall=23, fortress=29, solidification=96,
            knowledge=155, elevation=154, motivation=15, armor=22, armoring=67,
            carapace=81, leather_boots=14, therapy=158, dome=173)
C_INST = {84: 2399016, 18: 139128, 8: 139127, 80: 2399074, 5: 2334579,
          162: 2399063, 163: 2399042, 68: 2338411, 59: 2329610, 110: 2399045,
          16: 2399047, 25: 2337199, 23: 2401242, 29: 2399058, 96: 2318322,
          155: 2401202, 154: 2399017, 15: 2317467, 22: 2316266, 67: 2399043,
          81: 2399072, 14: 2401454, 158: 2318509, 173: 2399078}

COMP_INST = {315: 2420199, 314: 2398992, 313: 2340721, 365: 2328991,
             296: 2562183, 295: 2398996, 300: 2376733, 320: 2562182,
             322: 2396901, 374: 2420143, 311: 2324790, 308: 2562185,
             307: 2398990}

BUILDS = {
    'KG': dict(leek=129295, loadout=794, name='BOSS KG (shield-bot)',
               stats=dict(science=440, resistance=150, wisdom=90, tp=380, mp=120, life=600),
               chips=[29, 23, 22, 96, 67, 81, 80, 154, 102, 104, 103, 110, 162, 163, 68, 59],
               comps=[315, 365, 365, 296, 295, 295, 300, 320],
               expect=dict(HP=4910, STR=20, WIS=400, RES=450, SCI=500, TP=20, MP=6, RAM=16)),
    'ED': dict(leek=129288, loadout=795, name='BOSS ED (bruiser resolver)',
               stats=dict(strength=440, resistance=220, wisdom=160, tp=450, mp=60, life=450),
               chips=[8, 80, 84, 18, 5, 162, 163, 68, 59, 110, 16, 25, 23, 29, 96, 14],
               comps=[314, 313, 296, 320, 365, 322, 374, 307],
               expect=dict(HP=4080, STR=600, WIS=400, RES=400, TP=21, MP=6, RAM=16)),
    'MH': dict(leek=129296, loadout=796, name='BOSS MH (bruiser resolver)',
               stats=dict(strength=580, resistance=240, wisdom=200, tp=380, mp=120, life=260),
               chips=[8, 80, 84, 18, 5, 162, 163, 68, 59, 110, 16, 25, 23, 29, 96, 155],
               comps=[314, 313, 365, 365, 322, 295, 307, 308],
               expect=dict(HP=3150, STR=600, WIS=400, RES=400, TP=21, MP=6, RAM=16)),
    'ADA': dict(leek=20443, loadout=797, name='BOSS ADA (bruiser)',
               stats=dict(strength=500, resistance=240, wisdom=110, tp=380, mp=120, life=430),
               chips=[8, 80, 162, 163, 68, 59, 110, 16, 25, 23, 29, 5, 18, 96, 154, 155, 158, 173],
               comps=[314, 313, 365, 365, 322, 295, 311, 300],
               expect=dict(HP=3510, STR=600, WIS=400, RES=400, TP=19, MP=6, RAM=18)),
}

# ------------------------------------------------------------------ http ----
def login():
    email, pw = load_credentials('main')
    s = requests.Session()
    j = s.post(f'{BASE}/farmer/login-token', data={'login': email, 'password': pw}).json()
    s.headers['Authorization'] = 'Bearer ' + j['token']
    return s

def call(s, method, path, **data):
    for attempt in range(4):
        r = s.request(method, f'{BASE}{path}', data=data if method != 'GET' else None,
                      params=data if method == 'GET' else None, timeout=20)
        try:
            d = r.json()
        except Exception:
            d = {'error': 'bad_json', 'body': r.text[:200]}
        if 'error' not in d:
            return d
        time.sleep(0.4)
    raise RuntimeError(f'{method} {path} failed: {d}')

# ----------------------------------------------------------------- steps ----
def update_loadout(s, b):
    body = dict(set_id=b['loadout'], name=b['name'], icon='',
                weapons=json.dumps(WEAPONS), chips=json.dumps(b['chips']),
                components=json.dumps([{'index': i, 'template': t} for i, t in enumerate(b['comps'])]),
                stats=json.dumps(b['stats']))
    d = call(s, 'PUT', '/loadout/update', **body)
    return d

def apply_loadout(s, b):
    return call(s, 'POST', '/loadout/apply', set_id=b['loadout'], leek_id=b['leek'], use_restat='false')

def spend(s, leek, stat, amount):
    return call(s, 'POST', '/leek/spend-capital', leek_id=leek, characteristic=stat, amount=amount)

def get_leek(s, leek):
    return call(s, 'GET', f'/leek/get-private/{leek}') if False else s.get(f'{BASE}/leek/get/{leek}').json()

def main():
    s = login()
    only = sys.argv[1] if len(sys.argv) > 1 else None
    phase = sys.argv[2] if len(sys.argv) > 2 else 'all'
    for name, b in BUILDS.items():
        if only and name != only:
            continue
        print(f'=== {name} (leek {b["leek"]}, loadout {b["loadout"]}) ===')
        if phase in ('all', 'loadout'):
            d = update_loadout(s, b)
            print('  loadout updated:', str(d)[:120])
        if phase in ('all', 'apply'):
            d = apply_loadout(s, b)
            print('  apply:', str(d)[:200])
        time.sleep(0.4)

if __name__ == '__main__':
    main()
