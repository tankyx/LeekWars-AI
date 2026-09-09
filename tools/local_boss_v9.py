#!/usr/bin/env python3
"""Local V9 boss puzzle regression (no army). Clones a real fight's geometry.

Usage:
  python3 tools/local_boss_v9.py [--fight FID] [--seeds N] [--seed S] [--full]
    --fight FID : take graal/crystal/our spawn cells from data/fight_cache/FID.json
    (default: tools/boss_scenario_template.json layout)
Prints PZ says, resurrect rows (105) and a per-fight summary.
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
import local_test as lt  # noqa: E402

OURS = ('KurtGodel', 'AdaLovelace', 'MargaretHamilton', 'EdsgerDijkstra', 'LeekRain', 'DawnFall', 'DuskHope', 'ProdigalSon')


def clear_cache():
    for pat in ('*.class', '*.java', '*.lines', '*.sig'):
        for f in glob.glob(str(lt.GENERATOR_DIR / 'ai' / pat)):
            os.remove(f)


def clone_geometry(scn, fid):
    raw = json.load(open(f'data/fight_cache/{fid}.json'))
    d = raw['data']
    if isinstance(d, str):
        d = json.loads(d)
    pos = {l['name']: l['cellPos'] for l in d['leeks']}
    for e in scn['entities'][0]:
        if e['name'] in pos:
            e['cell'] = pos[e['name']]
    for e in scn['entities'][1]:
        if e['name'] in pos:
            e['cell'] = pos[e['name']]
    scn['map']['team1'] = [e['cell'] for e in scn['entities'][0]]
    scn['map']['team2'] = [e['cell'] for e in scn['entities'][1]]


# 8-leek lobby (Virus + Cure): Cure's four join team 1 as far-held reserves.
# Cells are far stands our leeks have occupied in real fights (walkable).
# Template geometry only — do not combine with --fight (clone maps by the
# four Virus names).
EXTRA_LEEKS = [('LeekRain', 229), ('DawnFall', 441), ('DuskHope', 549), ('ProdigalSon', 609)]

STAT_KEYS = ('type', 'level', 'life', 'cores', 'ram', 'tp', 'mp', 'strength', 'magic',
             'agility', 'wisdom', 'resistance', 'science', 'frequency')


def build(configs, seed, fid, extra=False):
    scn = lt.build_boss_scenario(configs, seed=seed)
    leeks = configs['leeks']
    if extra:
        # ids must be unique across BOTH teams (graal/crystals use low ids too)
        all_ents = [e for team in scn['entities'] for e in team]
        max_id = max(e['id'] for e in all_ents)
        for k, (nm, cell) in enumerate(EXTRA_LEEKS):
            cfg = leeks[nm]
            eid = max_id + 1 + k
            ent = {'id': eid, 'ai': 'V9_modules/main.lk', 'name': nm, 'farmer': eid, 'team': 1,
                   'cell': cell, 'weapons': list(cfg.get('weapons', [])), 'chips': list(cfg['chips'])}
            for sk in STAT_KEYS:
                if sk in cfg:
                    ent[sk] = cfg[sk]
            scn['entities'][0].append(ent)
            if isinstance(scn.get('farmers'), list):
                scn['farmers'].append({'id': eid, 'name': nm, 'country': 'fr'})
        if isinstance(scn.get('map'), dict) and isinstance(scn['map'].get('team1'), list):
            scn['map']['team1'] = [e['cell'] for e in scn['entities'][0]]
    LIVE2GEN = {}   # the generator resolves live item ids itself (heavy_sword 278 worked); keep identity
    for e in scn['entities'][0]:
        e['ai'] = 'V9_modules/main.lk'
        e['chips'] = list(leeks[e['name']]['chips'])   # exactly the live loadout, no kit injection
        e['weapons'] = [LIVE2GEN.get(w, w) for w in leeks[e['name']].get('weapons', [])]  # live item id -> generator weapon id
    if fid:
        clone_geometry(scn, fid)
    return scn


def run(scn):
    with tempfile.NamedTemporaryFile('w', suffix='.json', prefix='lw_boss_', delete=False, dir='/tmp') as f:
        json.dump(scn, f)
        path = f.name
    env = dict(os.environ, JAVA_HOME=lt.JAVA_HOME)
    cp = (lt.GENERATOR_DIR / 'runtime_classpath.txt').read_text().strip()
    r = subprocess.run([os.path.join(lt.JAVA_HOME, 'bin', 'java'), '-cp', cp, 'com.leekwars.Main', path],
                       capture_output=True, text=True, timeout=600, cwd=str(lt.GENERATOR_DIR), env=env)
    out = r.stdout
    i = out.find('{"')
    data = json.loads(out[i:], strict=False)
    os.remove(path)
    return data


def report(data, full):
    fight = data.get('fight', data)
    names = {l['id']: l['name'] for l in fight['leeks']}
    cur = None
    rnd = 0
    dives = []
    solved = []
    dead = []
    bugs = 0
    for a in fight['actions']:
        if a[0] == 6:
            rnd = a[1]
        elif a[0] == 7:
            cur = a[1]
        elif a[0] == 1002:
            bugs += 1
        elif a[0] == 105:
            dives.append(f'R{rnd} {names.get(cur, "?")[:3]} RES {names.get(a[2])}->{a[3]}')
        elif a[0] == 5 and len(a) > 2:
            dead.append((rnd, names.get(a[1])))
        elif a[0] == 203 and isinstance(a[1], str) and names.get(cur) in OURS:
            m = a[1]
            if m.startswith('B1'):
                continue
            if 'PZ DONE' in m:
                solved.append((rnd, names[cur][:3]))
            if full or 'KR' in m or 'DONE' in m or 'INV' in m:
                print(f'  R{rnd:>2} {names[cur][:3]}: {m[:120]}')
    for x in dives:
        print('  ', x)
    logs = data.get('logs') or {}
    errs = [str(v)[:200] for v in (logs.values() if isinstance(logs, dict) else logs)] if logs else []
    print(f'  summary: DONE={len(solved)} {solved} dead={dead} bugs={bugs} logs={errs[:3]}')
    return len(solved), bugs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fight', type=int, default=None)
    ap.add_argument('--seeds', type=int, default=1)
    ap.add_argument('--seed', type=int, default=12345)
    ap.add_argument('--full', action='store_true')
    ap.add_argument('--extra', action='store_true', help='add the 4 Cure leeks (8-leek lobby)')
    args = ap.parse_args()
    clear_cache()
    configs = lt.load_configs()
    tot = 0
    for k in range(args.seeds):
        seed = args.seed + k
        scn = build(configs, seed, args.fight, extra=args.extra)
        print(f'=== seed {seed} fight-geometry {args.fight}')
        data = run(scn)
        n, bugs = report(data, args.full)
        tot += n
    print(f'== total DONE {tot} over {args.seeds} seeds')


if __name__ == '__main__':
    main()
