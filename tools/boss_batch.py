#!/usr/bin/env python3
"""Run N boss-2 fights and summarize: winner, graal-death round, crystals solved, leeks alive at graal death."""
import json
import sys
import time
import requests
from config_loader import load_credentials

LEEKS = [129295, 20443, 129296, 129288]
NAMES_SHORT = {129295: 'KG', 20443: 'ADA', 129296: 'MH', 129288: 'ED'}


def login():
    email, pw = load_credentials('main')
    s = requests.Session()
    j = s.post('https://leekwars.com/api/farmer/login-token', data={'login': email, 'password': pw}).json()
    s.headers['Authorization'] = 'Bearer ' + j['token']
    return s


def analyze(s, fid):
    r = s.get(f'https://leekwars.com/api/fight/get/{fid}').json()
    d = r['data']
    if isinstance(d, str):
        d = json.loads(d)
    names = {l['id']: l.get('name') for l in d['leeks']}
    cur = None
    rnd = 0
    graal = None
    dead_us = []
    solved = []
    for a in d['actions']:
        if len(a) < 2:
            continue
        if a[0] == 6:
            rnd = a[1]
        elif a[0] == 7:
            cur = a[1]
        elif a[0] == 203:
            m = a[1]
            if isinstance(m, str) and 'DONE' in m:
                solved.append((rnd, names.get(cur, '?')[:3]))
        elif a[0] == 5 and len(a) > 2:
            n = names.get(a[1], '')
            if n == 'graal':
                graal = rnd
            elif n in ('KurtGodel', 'AdaLovelace', 'MargaretHamilton', 'EdsgerDijkstra'):
                dead_us.append((rnd, n[:3]))
    return r.get('winner'), graal, solved, dead_us


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    s = login()
    fids = []
    for i in range(n):
        r = s.post('https://leekwars.com/api/garden/start-boss-fight',
                   data={'boss_id': 2, 'participants': json.dumps(LEEKS)}).json()
        fids.append(r.get('fight'))
        print('started', fids[-1], flush=True)
        time.sleep(3)
    print('launched all, waiting...', flush=True)
    time.sleep(max(20, n * 12))
    wins = 0
    graal_deaths = 0
    for fid in fids:
        try:
            winner, graal, solved, dead_us = analyze(s, fid)
        except Exception as e:
            print(f'{fid}: analyze error {e}')
            continue
        tag = 'WIN' if winner == 1 else 'loss'
        if winner == 1:
            wins += 1
        if graal is not None:
            graal_deaths += 1
        print(f'{fid}: {tag} | graal@{graal} | solved {len(solved)} {solved} | deaths {dead_us}', flush=True)
    print(f'== {wins}/{n} wins, {graal_deaths}/{n} graal deaths')


if __name__ == '__main__':
    main()
