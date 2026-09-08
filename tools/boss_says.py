#!/usr/bin/env python3
"""Fetch + cache boss fights and print the PZ say timeline.

Usage:
  python3 tools/boss_says.py <fight_id> [...]      # specific fights
  python3 tools/boss_says.py --last N               # last N boss fights (type 4) from farmer history
  --brief : one summary line per fight (builds, solves, graal, deaths)
"""
import json
import os
import sys
import time
import requests
from config_loader import load_credentials

OURS = ('KurtGodel', 'AdaLovelace', 'MargaretHamilton', 'EdsgerDijkstra')
CACHE = os.path.join(os.path.dirname(__file__), '..', 'data', 'fight_cache')


def login():
    email, pw = load_credentials('main')
    s = requests.Session()
    j = s.post('https://leekwars.com/api/farmer/login-token', data={'login': email, 'password': pw}).json()
    s.headers['Authorization'] = 'Bearer ' + j['token']
    return s, j['farmer']['id']


def fetch(s, fid):
    p = os.path.join(CACHE, f'{fid}.json')
    if os.path.exists(p):
        raw = json.load(open(p))
        if raw.get('data'):
            return raw
    for _ in range(5):
        r = s.get(f'https://leekwars.com/api/fight/get/{fid}').json()
        if r.get('data'):
            json.dump(r, open(p, 'w'))
            return r
        time.sleep(4)
    return r


def parse(raw):
    d = raw['data']
    if isinstance(d, str):
        d = json.loads(d)
    names = {l['id']: l.get('name') for l in d['leeks']}
    builds = {l['name']: l for l in d['leeks'] if l['name'] in OURS}
    cur = None
    rnd = 0
    ev = []          # (rnd, who, msg)
    dead = []
    graal = None
    for a in d['actions']:
        if len(a) < 2:
            continue
        if a[0] == 6:
            rnd = a[1]
        elif a[0] == 7:
            cur = a[1]
        elif a[0] == 203 and isinstance(a[1], str):
            who = names.get(cur, '?')
            if who in OURS:
                ev.append((rnd, who[:3], a[1]))
        elif a[0] == 105:
            # RESURRECT row: [105, caster, target, cell, life, maxlife] — the
            # ground truth for kill+resurrect solves (the say is dropped at 0 TP)
            ev.append((rnd, names.get(cur, '?')[:3], f"KR-RES {names.get(a[2], '?')[:6]} ->{a[3]}"))
        elif a[0] == 5 and len(a) > 2:
            n = names.get(a[1], '')
            if n == 'graal':
                graal = rnd
            elif n in OURS:
                dead.append((rnd, n[:3]))
    return builds, ev, dead, graal, raw.get('winner')


def summarize(fid, raw, brief):
    builds, ev, dead, graal, winner = parse(raw)
    solved = [(r, w) for r, w, m in ev if m.startswith('PZ DONE') or 'KR DIVE e' in m and ' r1' in m or 'REVIVE' in m and ' r1' in m]
    kr = [(r, w, m[:44]) for r, w, m in ev if ('PZ KR' in m and 'retreat' not in m) or m.startswith('KR-RES')]
    bl = ' '.join(f"{n[:2]}:{b['life']}/{b['tp']}/{b['mp']}/S{b['strength']}/R{b['resistance']}" for n, b in builds.items())
    print(f"=== {fid} {'WIN' if winner == 1 else 'loss'} graal@{graal} solved={len(solved)} {solved} dead={dead}")
    print(f"    builds: {bl}")
    if brief:
        if kr:
            print(f"    KR: {kr}")
        return
    for r, w, m in ev:
        if m.startswith('B1'):
            continue
        print(f"  R{r:>2} {w}: {m[:120]}")


def main():
    args = sys.argv[1:]
    brief = '--brief' in args
    args = [a for a in args if a != '--brief']
    s, farmer_id = login()
    if args and args[0] == '--last':
        n = int(args[1])
        h = s.get(f'https://leekwars.com/api/history/get-farmer-history/{farmer_id}').json()['fights']
        fids = [f['id'] for f in h if f['type'] == 4][:n]
        fids.reverse()
    else:
        fids = [int(a) for a in args]
    for fid in fids:
        raw = fetch(s, fid)
        if not raw.get('data'):
            print(f'{fid}: no data yet')
            continue
        summarize(fid, raw, brief)


if __name__ == '__main__':
    main()
