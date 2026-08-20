#!/usr/bin/env python3
"""Local scale sweep for the value-model scorer bonus: run the same opponent
matrix at several _v9ValueModelScale values (OFF = scale-equivalent baseline)
with identical seeds, to find the influence regime where the model helps —
or prove none exists."""
import subprocess
import sys
import re

sys.path.insert(0, 'tools')
import local_test as lt

SRC = 'V9_modules/value_model.lk'
LEEKS = ['AdaLovelace', 'KurtGodel', 'MargaretHamilton', 'EdsgerDijkstra']
OPPONENTS = ['smart_str', 'smart_tank', 'v8_ada']
SEEDS = [3, 7, 11, 21, 42, 55, 63, 77, 91, 105]
SCALES = [int(x) for x in (sys.argv[1].split(',') if len(sys.argv) > 1 else '500,2000,8000'.split(','))]


def set_state(enabled, scale):
    src = open(SRC).read()
    src = re.sub(r'global _v9ValueModelEnabled = (true|false)',
                 f'global _v9ValueModelEnabled = {"true" if enabled else "false"}', src)
    src = re.sub(r'global _v9ValueModelScale = \d+',
                 f'global _v9ValueModelScale = {scale}', src)
    open(SRC, 'w').write(src)


def wipe():
    subprocess.run('rm -f /home/ubuntu/leek-wars-generator/ai/*.class '
                   '/home/ubuntu/leek-wars-generator/ai/*.java '
                   '/home/ubuntu/leek-wars-generator/ai/*.sig '
                   '/home/ubuntu/leek-wars-generator/ai/*.lines', shell=True)


def run_round(enabled, scale):
    set_state(enabled, scale); wipe()
    configs = lt.load_configs()
    w = l = d = 0
    per = {}
    for leek_name in LEEKS:
        leek = configs['leeks'][leek_name]
        lw = ll = ld = 0
        for opp_name in OPPONENTS:
            opp = configs['opponents'][opp_name]
            for seed in SEEDS:
                scen = lt.build_scenario(leek, opp, seed=seed)
                scen['entities'][0][0]['ai'] = 'V9_modules/main.lk'
                res = lt.run_fight(scen, 0)
                r = res.get('result')
                if r == 'WIN': lw += 1
                elif r == 'LOSS': ll += 1
                else: ld += 1
        per[leek_name] = (lw, ll, ld)
        w += lw; l += ll; d += ld
        print(f"    {leek_name:18s} {lw}W/{ll}L/{ld}D", flush=True)
    return (w, l, d), per


print('=== OFF (model disabled) ===')
off, off_per = run_round(False, 2000)
results = {'OFF': off}
for scale in SCALES:
    print(f'=== ON scale={scale} ===')
    on, on_per = run_round(True, scale)
    results[scale] = on
    print(f"  scale={scale}: {on[0]}W/{on[1]}L/{on[2]}D   per-leek: {on_per}")

set_state(False, 2000); wipe()
print(f"\nOFF: {off[0]}W/{off[1]}L")
for scale in SCALES:
    r = results[scale]
    print(f"scale={scale}: {r[0]}W/{r[1]}L  (delta wins {r[0]-off[0]:+d})")
