#!/usr/bin/env python3
"""Analyze a fennel boss fight: winner, graal/crystal deaths, PZ KR says, per-leek survival."""
import json
import sys
import requests
from config_loader import load_credentials

def fetch(fid):
    email, pw = load_credentials('main')
    s = requests.Session()
    j = s.post('https://leekwars.com/api/farmer/login-token', data={'login': email, 'password': pw}).json()
    s.headers['Authorization'] = 'Bearer ' + j['token']
    r = s.get(f'https://leekwars.com/api/fight/get/{fid}').json()
    return r

def main():
    fid = sys.argv[1]
    r = fetch(fid)
    top = {k: v for k, v in r.items() if k != 'data'}
    d = r.get('data', {})
    if isinstance(d, str):
        d = json.loads(d)
    print('== top-level:', {k: top[k] for k in ('winner', 'turns', 'bonus', 'status') if k in top})
    leeks = {}
    for l in d.get('leeks', []):
        leeks[l['id']] = l.get('name', str(l['id']))
    def nm(e):
        return leeks.get(e, str(e))
    dead = d.get('dead', [])
    print('== dead:', [(nm(x.get('id', x) if isinstance(x, dict) else x), x.get('turn') if isinstance(x, dict) else '?') for x in dead])

    actions = d.get('actions', [])
    turn = 0
    cur = None  # current entity
    events = []
    for a in actions:
        t = a[0]
        if t == 7:
            cur = a[1]
            if a[1] == -1:
                turn += 1
        elif t == 203:  # say
            msg = a[2] if len(a) > 2 else ''
            if isinstance(msg, str) and ('PZ' in msg or 'B1' in msg):
                events.append((turn, nm(cur), msg))
        elif t == 5:  # death
            events.append((turn, nm(cur), f'*** {nm(a[1])} DIED'))
        elif t == 12:  # chip cast
            events.append((turn, nm(cur), f'cast tpl{a[1]} ->{a[2]} r{a[3] if len(a)>3 else "?"}'))
    # compact print: deaths + KR/DONE/graal-related says + casts of resurrection(84)/spark(18)/teleport(59)
    for turn_, who, msg in events:
        keep = ('DIED' in msg or 'KR' in msg or 'DONE' in msg or 'tpl84' in msg or 'ANCHOR' in msg
                or 'BUFF' in msg or 'PH=' in msg)
        if keep:
            print(f'T{turn_:02d} {who:18s} {msg[:150]}')

if __name__ == '__main__':
    main()
