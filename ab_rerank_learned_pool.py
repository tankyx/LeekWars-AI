#!/usr/bin/env python3
"""A/B the learned re-rank on the CALIBRATED prod pool — the 8 hard matchups
where decisions are actually close (bot matrix is too lopsided to show any
integration's effect). ON vs OFF, 10 seeds per matchup per side."""
import subprocess
import sys
import re

sys.path.insert(0, 'tools')
import local_test as lt

SRC = 'V9_modules/rollout_rerank.lk'
MATCHUPS = [
    ('KurtGodel', 'prod_feeddageek'),
    ('MargaretHamilton', 'prod_Wild'),
    ('EdsgerDijkstra', 'prod_ZiGouiGouis'),
    ('MargaretHamilton', 'prod_Zigotos'),
    ('AdaLovelace', 'prod_Mordor'),
    ('EdsgerDijkstra', 'prod_MangeMonAsperge'),
    ('EdsgerDijkstra', 'prod_Teelk'),
    ('MargaretHamilton', 'prod_hinasu'),
]
SEEDS = [3, 7, 11, 21, 42, 55, 63, 77, 91, 105]


def set_flag(on):
    src = open(SRC).read()
    new = re.sub(r'global _v9RerankLearnedEnabled = (true|false)',
                 f'global _v9RerankLearnedEnabled = {"true" if on else "false"}', src)
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
    for leek_name, opp_key in MATCHUPS:
        leek = configs['leeks'][leek_name]
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
        out[(leek_name, opp_key)] = (w, l, d)
        print(f"  {leek_name[:3]} vs {opp_key:24s} {w}W/{l}L/{d}D", flush=True)
    return out


print('=== LEARNED RE-RANK ON ===')
on = run_round(True)
print('=== OFF ===')
off = run_round(False)
set_flag(False); wipe()
ow = sum(v[0] for v in on.values()); ol = sum(v[1] for v in on.values())
fw = sum(v[0] for v in off.values()); fl = sum(v[1] for v in off.values())
print(f"\nTOTAL: ON {ow}W/{ol}L  vs  OFF {fw}W/{fl}L  (of {sum(sum(v) for v in on.values())})")
for k in on:
    print(f"  {k[0][:3]} vs {k[1]:24s} ON {on[k]}  OFF {off[k]}")
