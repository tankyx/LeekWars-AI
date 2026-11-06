#!/usr/bin/env python3
"""Level the godson accounts' leeks (owner 2026-11-04: Brocanteur2 / Brocanteur3, sponsored by Virus - the referral
counts the godsons' total recursive level). Spends each account's garden credits on solo fights against the weakest
offered opponent (one fight in flight per leek: a fight is what regenerates the offers), and the new capital after
every --check fights with xp_farm's tier-aware spender.

    python3 tools/godson_farm.py                         # every godson account, all credits
    python3 tools/godson_farm.py --accts brocanteur2 --max 10
Log: data/ladder/godson_farm.csv (date, account, leek, fights, wins, level, xp, talent)
"""
import argparse, csv, os, sys, threading, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession
import xp_farm as xf

ACCTS = {'brocanteur2': 135764, 'brocanteur3': 135765}
# total-stat targets in order (first unmet gets the capital). Owner 2026-11-06: every new point into TP (10 TP was
# the bottleneck - two shots a turn); the spender keeps the capital until the next TP point is affordable
PLAN = [('strength', 200), ('tp', 99)]
LOG = os.path.join(ROOT, 'data', 'ladder', 'godson_farm.csv')


def farm(acct, lid, cap, check, out):
    lw = LWSession(acct)
    l = lw.leek(lid); name = l['name']
    xf.CAPITAL_PLAN[name] = PLAN
    g = lw.get('/garden/get'); g = g.get('garden', g)
    credits = min(int(g.get('fights') or 0), cap)
    lvl0 = l.get('level'); wins = n = 0
    xf.spend_capital(lw, lid, name)
    for i in range(credits):
        opps = (lw.get('/garden/get-leek-opponents/%d' % lid) or {}).get('opponents') or []
        if not opps:
            print('%s: no opponents offered - stop' % acct, flush=True); break
        tgt = min(opps, key=lambda o: (o.get('level') or 0, o.get('talent') or 0))
        r = lw.post('/garden/start-solo-fight', leek_id=lid, target_id=tgt['id'])
        fid = r.get('fight') if isinstance(r, dict) else (r if isinstance(r, int) else None)
        if not fid:
            print('%s: start failed %s' % (acct, str(r)[:120]), flush=True); break
        f = {}
        for _ in range(40):
            time.sleep(3)
            f = lw.get('/fight/get/%d' % fid); f = f.get('fight', f)
            if f.get('status') == 2:
                break
        n += 1
        team = 1 if any(x.get('id') == lid for x in f.get('leeks1') or []) else 2
        wins += f.get('winner') == team
        if n % check == 0:
            xf.spend_capital(lw, lid, name)
            l = lw.leek(lid)
            print('%s %s: %d fights, %d wins, level %s' % (acct, name, n, wins, l.get('level')), flush=True)
    xf.spend_capital(lw, lid, name)
    l = lw.leek(lid)
    out[acct] = (name, n, wins, lvl0, l.get('level'), l.get('xp'), l.get('talent'),
                 {s: l.get('total_' + s) for s in ('life', 'strength', 'tp', 'mp')})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--accts', default=','.join(ACCTS))
    ap.add_argument('--max', type=int, default=1000, help='fights per account at most')
    ap.add_argument('--check', type=int, default=10, help='spend capital every N fights')
    a = ap.parse_args()
    out = {}
    th = [threading.Thread(target=farm, args=(x, ACCTS[x], a.max, a.check, out)) for x in a.accts.split(',') if x]
    for t in th:
        t.start()
    for t in th:
        t.join()
    new = not os.path.exists(LOG)
    with open(LOG, 'a', newline='') as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(['date', 'acct', 'leek', 'fights', 'wins', 'level', 'xp', 'talent'])
        for acct, (name, n, wins, l0, l1, xp, tal, st) in out.items():
            w.writerow([time.strftime('%Y-%m-%d'), acct, name, n, wins, l1, xp, tal])
            print('== %s %s: %d fights, %d wins, level %s -> %s, talent %s, stats %s' % (acct, name, n, wins, l0, l1, tal, st))


if __name__ == '__main__':
    main()
