#!/usr/bin/env python3
"""Head-to-head validator for COUNTER_MULTS champions on the calibrated prod pool.

Runs the 8 calibrated matchups × 10 seeds with current V9 mults, then applies
the champion mults to V9_modules/strategic_depth.lk and reruns. Green if
aggregate >= +5pts over baseline and no single matchup <= -10pts.

Usage: python3 ab_prod_pool.py <best_weights.json> [--seeds 10]
"""
import argparse
import json
import re
import subprocess
import sys

sys.path.insert(0, 'tools')
import local_test as lt

MATCHUPS = [  # (leek, prod_pool_key) — the 8 calibrated entries
    ('KurtGodel', 'prod_feeddageek'),
    ('MargaretHamilton', 'prod_Wild'),
    ('EdsgerDijkstra', 'prod_ZiGouiGouis'),
    ('MargaretHamilton', 'prod_Zigotos'),
    ('AdaLovelace', 'prod_Mordor'),
    ('EdsgerDijkstra', 'prod_MangeMonAsperge'),
    ('EdsgerDijkstra', 'prod_Teelk'),
    ('MargaretHamilton', 'prod_hinasu'),
]
SD = 'V9_modules/strategic_depth.lk'


def wipe():
    subprocess.run('rm -f /home/ubuntu/leek-wars-generator/ai/*.class '
                   '/home/ubuntu/leek-wars-generator/ai/*.java '
                   '/home/ubuntu/leek-wars-generator/ai/*.sig '
                   '/home/ubuntu/leek-wars-generator/ai/*.lines', shell=True)


def apply_mults(mult_map):
    src = open(SD).read()
    for k, v in mult_map.items():
        src = re.sub(rf"('{k}': )(-?\d+)", lambda m: m.group(1) + str(int(v)), src)
    open(SD, 'w').write(src)


def snapshot():
    return open(SD).read()


def run_matrix(configs, seeds):
    out = {}
    for leek_name, opp_key in MATCHUPS:
        leek = configs['leeks'][leek_name]
        opp = configs['opponents'][opp_key]
        w = l = d = 0
        for seed in seeds:
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('champion')
    ap.add_argument('--seeds', type=int, default=10)
    args = ap.parse_args()
    champ = json.load(open(args.champion))
    mults = champ.get('weights') or champ.get('counters') or champ
    seeds = [3, 7, 11, 21, 42, 55, 63, 77, 91, 105][:args.seeds]

    configs = lt.load_configs()
    base_src = snapshot()

    print('=== BASELINE (current V9 mults) ===')
    wipe()
    base = run_matrix(configs, seeds)

    print('=== CHAMPION ===')
    apply_mults(mults)
    wipe()
    new = run_matrix(configs, seeds)

    open(SD, 'w').write(base_src)  # restore
    wipe()

    bw = sum(v[0] for v in base.values()); bl = sum(v[1] for v in base.values())
    nw = sum(v[0] for v in new.values()); nl = sum(v[1] for v in new.values())
    print(f"\nBASE {bw}W/{bl}L  vs  CHAMP {nw}W/{nl}L  (of {sum(sum(v) for v in base.values())})")
    print('per-matchup deltas:')
    worst = 0
    for k in base:
        b, n = base[k], new[k]
        bn = max(1, b[0] + b[1]); nn = max(1, n[0] + n[1])
        delta = (n[0] / nn - b[0] / bn) * 100
        worst = min(worst, delta)
        print(f"  {k[0][:3]} vs {k[1]:24s} {delta:+.0f}pts")
    agg = (nw / max(1, nw + nl) - bw / max(1, bw + bl)) * 100
    print(f"aggregate: {agg:+.1f}pts  worst matchup: {worst:+.0f}pts")
    print('VERDICT:', 'GREEN' if agg >= 5 and worst >= -10 else 'RED')


if __name__ == '__main__':
    main()
