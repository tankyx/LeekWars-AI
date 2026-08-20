#!/usr/bin/env python3
import requests, json, time, sys, os, random
os.chdir('/home/ubuntu/LeekWars-AI')
sys.path.insert(0, 'tools')
from config_loader import load_credentials

email, pw = load_credentials('cure')
s = requests.Session()
r = s.post('https://leekwars.com/api/farmer/login-token', data={'login': email, 'password': pw})
token = r.json()['token']
farmer = r.json()['farmer']
leeks = [(l['id'], l['name']) for l in farmer.get('leeks', {}).values()]

for lid, name in leeks:
    if lid == 19703: continue  # Already done LeekRain
    wins = losses = draws = 0
    errors = 0
    for i in range(25):
        r = s.get(f'https://leekwars.com/api/garden/get-leek-opponents/{lid}', params={'token': token})
        if r.status_code != 200: 
            errors += 1
            if errors > 5: break
            time.sleep(1)
            continue
        opps = r.json().get('opponents', [])
        if not opps:
            time.sleep(1)
            continue
        target = random.choice(opps)
        r2 = s.post('https://leekwars.com/api/garden/start-solo-fight', data={'leek_id': lid, 'target_id': target['id'], 'token': token})
        if r2.status_code == 200:
            resp = r2.json()
            fid = resp.get('fight', resp.get('id', resp))
            time.sleep(2)
            r3 = s.get(f'https://leekwars.com/api/fight/get/{fid}')
            if r3.status_code == 200:
                rep = r3.json().get('report', {})
                if isinstance(rep, str): rep = json.loads(rep)
                w = rep.get('win', 0)
                if w == 1: wins += 1
                elif w == 2: losses += 1
                else: draws += 1
        time.sleep(0.5)
    total = wins + losses + draws
    pct = wins * 100 / total if total > 0 else 0
    line = f'{name}: {wins}W {losses}L {draws}D ({pct:.0f}%)\n'
    print(line, end='', flush=True)
    with open('tools/cure_results.txt', 'a') as f:
        f.write(line)

print('Done.', flush=True)
with open('tools/cure_results.txt', 'a') as f:
    f.write('Done.\n')
