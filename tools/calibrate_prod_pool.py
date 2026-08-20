#!/usr/bin/env python3
"""Calibrate the prod_* opponent pool: for each entry, fight the leek that
loses to it in production (8 seeds, V8 proxy AI) and compare local vs
production loss rates. Entries where the local matchup is also genuinely hard
(prod loss rate >= 25% AND local loss rate >= prod/3) are marked calibrated
in leek_configs.json — GA jobs should train/validate only on those."""
import json
import sqlite3
import sys
from collections import defaultdict

sys.path.insert(0, 'tools')
import local_test as lt

LEEKS = {'Ada': 'AdaLovelace', 'Kur': 'KurtGodel', 'Mar': 'MargaretHamilton', 'Eds': 'EdsgerDijkstra'}
LEEK_DB = {'AdaLovelace': 20443, 'KurtGodel': 129295, 'MargaretHamilton': 129296, 'EdsgerDijkstra': 129288}
SEEDS = [3, 7, 11, 21, 42, 55, 63, 77]

configs = lt.load_configs()

# production W/L per (leek, opponent-name)
prod = {}
for lname, lid in LEEK_DB.items():
    con = sqlite3.connect(f'tools/fight_history_{lid}.db')
    for opp, w, l in con.execute("""SELECT opponent_name,
        SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END),
        SUM(CASE WHEN result='LOSS' THEN 1 ELSE 0 END)
        FROM fight_history WHERE timestamp >= '2026-06-01' GROUP BY opponent_name"""):
        prod[(lname, opp)] = (w, l)
    con.close()

results = []
for key, entry in configs['opponents'].items():
    if not key.startswith('prod_'):
        continue
    real_name = key[5:].replace('_', '')
    # find the leek(s) with the worst prod record vs this opponent
    best = None
    for lname in LEEKS.values():
        for (ln, on), (w, l) in prod.items():
            norm = on.replace(' ', '').replace('é', 'e').replace('è', 'e')
            if ln == lname and norm.lower().startswith(real_name.lower()[:12]):
                if l >= 2 and (best is None or l / (w + l) > best[2]):
                    best = (lname, on, l / (w + l), w, l)
    if best is None:
        # try exact-name fallback
        for lname in LEEKS.values():
            for (ln, on), (w, l) in prod.items():
                if ln == lname and on.replace(' ', '').lower() == real_name.lower():
                    best = (lname, on, l / (w + l) if (w + l) else 0, w, l)
    if best is None:
        print(f"{key:26s} no prod record found — skip")
        continue
    lname, oname, prod_lr, pw, pl = best
    leek = configs['leeks'][lname]
    w = l = d = 0
    for seed in SEEDS:
        scen = lt.build_scenario(leek, entry, seed=seed)
        scen['entities'][0][0]['ai'] = 'V9_modules/main.lk'
        res = lt.run_fight(scen, 0)
        r = res.get('result')
        if r == 'WIN': w += 1
        elif r == 'LOSS': l += 1
        else: d += 1
    local_lr = l / max(1, w + l + d)
    calibrated = prod_lr >= 0.25 and local_lr >= prod_lr / 3
    results.append((key, lname[:3], prod_lr, local_lr, calibrated))
    tag = 'CAL' if calibrated else 'no'
    print(f"{key:26s} {lname[:3]} prodLR={prod_lr:.2f} localLR={local_lr:.2f} [{tag}]")

# write calibration flags back into the configs
for key, _, _, _, cal in results:
    configs['opponents'][key]['calibrated'] = cal
json.dump(configs, open('tools/leek_configs.json', 'w'), indent=1)
ncal = sum(1 for r in results if r[4])
print(f"\n{ncal}/{len(results)} pool entries calibrated (usable for GA)")
