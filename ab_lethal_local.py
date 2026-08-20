#!/usr/bin/env python3
"""Local A/B: lethal solver ON vs OFF. Same seeds both sides, per leek."""
import subprocess
import sys
import re

sys.path.insert(0, 'tools')
import local_test as lt

SRC = 'V9_modules/lethal_solver.lk'
LEEKS = ['AdaLovelace', 'KurtGodel', 'MargaretHamilton', 'EdsgerDijkstra']
OPPONENTS = ['smart_str', 'smart_tank', 'v8_ada']
SEEDS = [3, 7, 11, 21, 42, 55, 63, 77, 91, 105]


def set_flag(on):
    src = open(SRC).read()
    new = re.sub(r'global _v9LethalSolverEnabled = (true|false)',
                 f'global _v9LethalSolverEnabled = {"true" if on else "false"}', src)
    open(SRC, 'w').write(new)


def wipe():
    subprocess.run('rm -f /home/ubuntu/leek-wars-generator/ai/*.class '
                   '/home/ubuntu/leek-wars-generator/ai/*.java '
                   '/home/ubuntu/leek-wars-generator/ai/*.sig '
                   '/home/ubuntu/leek-wars-generator/ai/*.lines', shell=True)


def run_round(on):
    set_flag(on); wipe()
    configs = lt.load_configs()
    out = {}
    for leek_name in LEEKS:
        leek = configs['leeks'][leek_name]
        w = l = d = 0
        for opp_name in OPPONENTS:
            opp = configs['opponents'][opp_name]
            for seed in SEEDS:
                scen = lt.build_scenario(leek, opp, seed=seed)
                scen['entities'][0][0]['ai'] = 'V9_modules/main.lk'
                res = lt.run_fight(scen, 0)
                r = res.get('result')
                if r == 'WIN': w += 1
                elif r == 'LOSS': l += 1
                else: d += 1
        out[leek_name] = (w, l, d)
        print(f"  {leek_name:18s} {w}W/{l}L/{d}D", flush=True)
    return out


print('=== LETHAL SOLVER ON ===')
on = run_round(True)
print('=== OFF (baseline) ===')
off = run_round(False)
set_flag(True); wipe()
print(f"\n{'leek':18s} {'ON':>14s} {'OFF':>14s}")
for lk in LEEKS:
    print(f"{lk:18s} {str(on[lk]):>14s} {str(off[lk]):>14s}")
ow = sum(v[0] for v in on.values()); fw = sum(v[0] for v in off.values())
ol = sum(v[1] for v in on.values()); fl = sum(v[1] for v in off.values())
print(f"TOTAL: ON {ow}W/{ol}L  vs  OFF {fw}W/{fl}L  (of {sum(sum(v) for v in on.values())})")
