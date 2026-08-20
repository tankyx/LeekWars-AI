#!/usr/bin/env python3
"""A/B the debuff scenario locally: KG vs shield-stacking opponents,
flag ON vs OFF (toggled by editing the global in scenario_generator.lk
via sed between rounds). Same seeds both sides."""
import subprocess
import sys
import re

sys.path.insert(0, 'tools')
import local_test as lt

GEN = 'V9_modules/scenario_generator.lk'
OPPONENTS = ['v8_ada', 'smart_tank', 'v8_excellent', 'smart_str']
SEEDS = [3, 7, 11, 21, 42, 55, 63, 77, 91, 105]


def set_flag(on):
    src = open(GEN).read()
    new = re.sub(r'global _v9DebuffScenarioEnabled = (true|false)',
                 f'global _v9DebuffScenarioEnabled = {"true" if on else "false"}', src)
    open(GEN, 'w').write(new)


def wipe_cache():
    subprocess.run('rm -f /home/ubuntu/leek-wars-generator/ai/*.class '
                   '/home/ubuntu/leek-wars-generator/ai/*.java '
                   '/home/ubuntu/leek-wars-generator/ai/*.sig '
                   '/home/ubuntu/leek-wars-generator/ai/*.lines', shell=True)


def run_round(on):
    set_flag(on)
    wipe_cache()
    configs = lt.load_configs()
    leek = configs['leeks']['KurtGodel']
    totals = {}
    for opp_name in OPPONENTS:
        opp = configs['opponents'][opp_name]
        w = l = d = 0
        for seed in SEEDS:
            scen = lt.build_scenario(leek, opp, seed=seed)
            res = lt.run_fight(scen, 0)
            r = res.get('result')
            if r == 'WIN': w += 1
            elif r == 'LOSS': l += 1
            else: d += 1
        totals[opp_name] = (w, l, d)
        print(f"  {opp_name:15s} {w}W/{l}L/{d}D")
    return totals


print('=== FLAG ON (debuff scenario) ===')
on = run_round(True)
print('=== FLAG OFF (baseline) ===')
off = run_round(False)
set_flag(True)  # leave enabled
wipe_cache()
print()
print(f"{'opponent':15s} {'ON':>12s} {'OFF':>12s}")
for o in OPPONENTS:
    print(f"{o:15s} {str(on[o]):>12s} {str(off[o]):>12s}")
on_w = sum(v[0] for v in on.values()); off_w = sum(v[0] for v in off.values())
on_l = sum(v[1] for v in on.values()); off_l = sum(v[1] for v in off.values())
print(f"TOTAL wins: ON {on_w} vs OFF {off_w}   losses: ON {on_l} vs OFF {off_l}")
