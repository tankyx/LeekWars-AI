#!/usr/bin/env python3
"""Free live-engine battery: one of our leeks vs a built-in bot or a custom
test leek, through the test-scenario API (no garden / challenge credits).

    python3 tools/live_bot_battery.py AdaLovelace StrongSTR --ai /expert -n 8
    python3 tools/live_bot_battery.py MargaretHamilton rex -n 8 --root 9.0/V9-MS/

Opponent: a name from /test-leek/get-all (custom test leeks, e.g. StrongSTR,
id -17934) or one of the built-in bots domingo/tuxo/bibol/hachess/rex
(ids -1..-6). Bot AI: /normal (default) or /expert for custom test leeks.
Prints W/L/D, turns per fight, damage dealt/taken per turn, weapons AND
chips per fight on both sides, and runtime errors per side. StrongSTR's
expert AI overruns its own ops budget on some turns (a 1002 in about one
fight in four, at 15-17M ops); our side must always be 0.
"""
import argparse, json, os, sys, time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lw_api import LWSession
from lw_decode import Decoder

BOTS = {'domingo': -1, 'tuxo': -2, 'bibol': -3, 'jean': -4, 'hachess': -5, 'rex': -6}
LEEKS = {'AdaLovelace': 20443, 'EdsgerDijkstra': 129288, 'KurtGodel': 129295, 'MargaretHamilton': 129296}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('leek'); ap.add_argument('opponent')
    ap.add_argument('-n', type=int, default=8)
    ap.add_argument('--ai', default='/normal', help="bot AI: /normal or /expert (custom test leeks)")
    ap.add_argument('--root', default='9.0/V9/', help='our AI root on the server')
    ap.add_argument('--account', default='main')
    a = ap.parse_args()
    D = Decoder(); lw = LWSession(a.account)
    ours = LEEKS.get(a.leek)
    if ours is None:
        sys.exit('unknown leek %s' % a.leek)
    if a.opponent.lower() in BOTS:
        oid = BOTS[a.opponent.lower()]; bot_ai = -2 if a.ai == '/normal' else a.ai
    else:
        tl = lw.get('/test-leek/get-all')['leeks']
        m = [l for l in tl if l['name'] == a.opponent]
        if not m:
            sys.exit('no test leek named %s; have: %s' % (a.opponent, [l['name'] for l in tl]))
        oid = m[0]['id']; bot_ai = a.ai
    ai_path = a.root.rstrip('/') + '/main.lk'
    sid = lw.post('/test-scenario/new', name='bat_%s_%s' % (a.leek, a.opponent))['id']
    lw.post('/test-scenario/update', id=sid, data=json.dumps({'type': 0, 'map': None, 'ai': ai_path}))
    lw.post('/test-scenario/add-leek', scenario_id=sid, leek=ours, team=0, ai=ai_path)
    lw.post('/test-scenario/add-leek', scenario_id=sid, leek=oid, team=1, ai=bot_ai)
    fids = []
    for i in range(a.n):
        f = lw.post('/ai/test-scenario', scenario_id=sid, ai_id=ai_path)
        if isinstance(f, dict) and f.get('fight'):
            fids.append(f['fight'])
        else:
            print('launch error:', f)
        time.sleep(0.5)
    time.sleep(8)
    res = Counter(); errs = Counter(); turns = 0; dealt = 0; taken = 0; weap = Counter(); ew = Counter()
    for fid in fids:
        f = None
        for _ in range(12):
            f = lw.get('/fight/get/%d' % fid)
            if isinstance(f, dict) and f.get('data', {}).get('actions') and f.get('winner') is not None:
                break
            time.sleep(3)
        data = f['data']; me = [x for x in data['leeks'] if x['name'] == a.leek][0]; mid = me['id']
        en = [x for x in data['leeks'] if x['team'] != me['team']][0]
        res['W' if f['winner'] == me['team'] else ('D' if f['winner'] == 0 else 'L')] += 1
        cur = None; held = {}
        for x in data['actions']:
            if not isinstance(x, list) or not x:
                continue
            if x[0] == 7:
                cur = x[1]
                if cur == mid:
                    turns += 1
            elif x[0] == 13:
                held[cur] = x[1]
            elif x[0] == 16:
                (weap if cur == mid else ew)[str(D.weapon(held.get(cur, -1)))] += 1
            elif x[0] == 12 and len(x) > 1:
                (weap if cur == mid else ew)['chip:' + str(D.chip(x[1]))] += 1
            elif x[0] == 1002:
                errs['ours' if cur == mid else 'bot'] += 1
            if x[0] in (101, 110, 108) and len(x) > 2:
                if x[1] == en['id']:
                    dealt += x[2]
                elif x[1] == mid:
                    taken += x[2]
    lw.call('DELETE', '/test-scenario/delete', id=sid)
    n = max(1, len(fids)); t = max(1, turns)
    print('%s vs %s (%s) x%d: %s  turns/fight %.1f  dealt/turn %.0f  taken/turn %.0f' % (
        a.leek, a.opponent, a.ai, len(fids), dict(res), turns / n, dealt / t, taken / t))
    print('  our weapons/fight %s' % {k: round(v / n, 1) for k, v in weap.items()})
    print('  bot weapons/fight %s' % {k: round(v / n, 1) for k, v in ew.items()})
    print('  runtime errors: ours %d, bot %d' % (errs['ours'], errs['bot']))
    if errs['ours']:
        sys.exit(2)


if __name__ == '__main__':
    main()
