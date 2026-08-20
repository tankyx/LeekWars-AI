#!/usr/bin/env python3
"""Concept test: does equipping a summon bulb flip our hardest calibrated
matchups? ED gets metallic_bulb (drop fracture), vs his 3 calibrated
sustain opponents, 10 seeds, baseline vs bulb config."""
import json
import re
import subprocess
import sys

sys.path.insert(0, 'tools')
import local_test as lt

MATCHUPS = [
    ('EdsgerDijkstra', 'prod_ZiGouiGouis'),
    ('EdsgerDijkstra', 'prod_MangeMonAsperge'),
    ('EdsgerDijkstra', 'prod_Teelk'),
]
FLAG = 'V9_modules/bulb_ai.lk'
SEEDS = [3, 7, 11, 21, 42, 55, 63, 77, 91, 105]
METALLIC = 79   # chip id (generator namespace)
DROP = 59       # fracture


def wipe():
    subprocess.run('rm -f /home/ubuntu/leek-wars-generator/ai/*.class '
                   '/home/ubuntu/leek-wars-generator/ai/*.java '
                   '/home/ubuntu/leek-wars-generator/ai/*.sig '
                   '/home/ubuntu/leek-wars-generator/ai/*.lines', shell=True)


def set_flag(on):
    s = open(FLAG).read()
    new = re.sub(r'global _v9BulbEarlyEnabled = (true|false)', f'global _v9BulbEarlyEnabled = {"true" if on else "false"}', s)
    open(FLAG, 'w').write(new)  # evaluate BEFORE opening 'w' — a crash here must not truncate

def run(configs, bulb):
    set_flag(bulb)
    out = {}
    for leek_name, opp_key in MATCHUPS:
        leek = dict(configs['leeks'][leek_name])
        if bulb:
            leek['chips'] = [c for c in leek['chips'] if c != DROP] + [METALLIC]
        opp = configs['opponents'][opp_key]
        w = l = d = 0
        for seed in SEEDS:
            scen = lt.build_scenario(leek, opp, seed=seed)
            scen['entities'][0][0]['ai'] = 'V9_modules/main.lk'
            res = lt.run_fight(scen, 0)
            r = res.get('result')
            if r == 'WIN': w += 1
            elif r == 'LOSS': l += 1
            else: d += 1
        out[opp_key] = (w, l, d)
        print(f"  {leek_name[:3]} vs {opp_key:24s} {w}W/{l}L/{d}D", flush=True)
    return out


configs = lt.load_configs()
print('=== BASELINE (no bulb) ===')
wipe()
base = run(configs, False)
print('=== WITH METALLIC BULB (drop fracture) ===')
wipe()
bulb = run(configs, True)
bw = sum(v[0] for v in base.values()); nw = sum(v[0] for v in bulb.values())
set_flag(False); wipe()
print(f"\nTOTAL: baseline {bw}W  vs  early-bulb {nw}W  (delta {nw-bw:+d})")
for k in base:
    print(f"  {k:26s} base {base[k]}  bulb {bulb[k]}")
