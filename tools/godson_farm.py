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

ACCTS = {'brocanteur2': [135764, 136165], 'brocanteur3': [135765, 136166]}   # owner added a second leek 2026-11-14
# total-stat targets in order (first unmet gets the capital). Owner 2026-11-06: every new point into TP (10 TP was
# the bottleneck - two shots a turn); the spender keeps the capital until the next TP point is affordable
PLAN = [('strength', 200), ('tp', 99)]
# owner 2026-11-13: twin test - NotPetya (brocanteur3) puts its capital into life up to 600 total (opponents at its
# level average 565 life against our 320) and carries stalactite instead of rock; WannaCrypt stays the control
PLANS = {135765: [('strength', 200), ('life', 600), ('tp', 99)],
         # second leeks (ILOVEYOU / Emotet, level 1 on 2026-11-14): damage first, then a life cushion, 12 TP, more life
         136165: [('strength', 200), ('life', 400), ('tp', 12), ('life', 600), ('tp', 99)],
         136166: [('strength', 200), ('life', 400), ('tp', 12), ('life', 600), ('tp', 99)]}
# kit ladder of the second leeks (owner 2026-11-14 "build them"): (level, 'weapon' | 'chip', market item id, item it
# replaces or None), bought with the account's habs when missing (~60k in total) and equipped as the leek levels.
# It ends on the first leeks' kit: machine gun + laser; pebble, protein, rock, motivation, flash, flame
KIT_LEEKS = (136165, 136166)
KIT = [(1, 'weapon', 37, None), (8, 'weapon', 38, None), (27, 'weapon', 45, 37), (38, 'weapon', 42, 45),
       (2, 'chip', 1, None), (3, 'chip', 3, None), (4, 'chip', 19, None), (6, 'chip', 8, None), (9, 'chip', 2, None),
       (10, 'chip', 21, None), (13, 'chip', 7, 1), (14, 'chip', 15, 2), (24, 'chip', 6, 3), (29, 'chip', 5, 21)]
LOG = os.path.join(ROOT, 'data', 'ladder', 'godson_farm.csv')


def kit(lw, lid):
    """Bring a KIT_LEEKS leek's weapons / chips to the ladder's state for its level (buys what is missing)."""
    if lid not in KIT_LEEKS:
        return
    l = lw.leek(lid); level = l.get('level') or 1
    for kind in ('weapon', 'chip'):
        want = []
        for lv, k, item, old in sorted(KIT):
            if k == kind and lv <= level:
                if old in want:
                    want.remove(old)
                want.append(item)
        have = {x['template']: x['id'] for x in l[kind + 's']}
        for tpl, inst in have.items():
            if tpl not in want:
                lw.s.delete('https://leekwars.com/api/leek/remove-%s' % kind, data={'leek_id': lid, kind + '_id': inst})
                time.sleep(0.5)
        for tpl in want:
            if tpl in have:
                continue
            f = lw.get('/farmer/get-from-token'); f = f.get('farmer', f)
            inst = next((x['id'] for x in f.get(kind + 's') or [] if x.get('template') == tpl), None)
            if inst is None:
                r = lw.post('/market/buy-habs', item_id=tpl)
                inst = r.get('item') if isinstance(r, dict) else None
                print('%s: bought %s %s -> %s' % (l['name'], kind, tpl, str(r)[:80]), flush=True)
            if inst is not None:
                r = lw.post('/leek/add-%s' % kind, leek_id=lid, **{kind + '_id': inst})
                print('%s: equip %s %s -> %s' % (l['name'], kind, tpl, str(r)[:80]), flush=True)
            time.sleep(0.5)


def farm(acct, lid, cap, check, out):
    lw = LWSession(acct)
    l = lw.leek(lid); name = l['name']
    xf.CAPITAL_PLAN[name] = PLANS.get(lid, PLAN)
    credits = cap
    lvl0 = l.get('level'); wins = n = 0
    xf.spend_capital(lw, lid, name); kit(lw, lid)
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
            xf.spend_capital(lw, lid, name); kit(lw, lid)
            l = lw.leek(lid)
            print('%s %s: %d fights, %d wins, level %s' % (acct, name, n, wins, l.get('level')), flush=True)
    xf.spend_capital(lw, lid, name); kit(lw, lid)
    l = lw.leek(lid)
    out[(acct, lid)] = (name, n, wins, lvl0, l.get('level'), l.get('xp'), l.get('talent'),
                 {s: l.get('total_' + s) for s in ('life', 'strength', 'tp', 'mp')})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--accts', default=','.join(ACCTS))
    ap.add_argument('--max', type=int, default=1000, help='fights per account at most')
    ap.add_argument('--check', type=int, default=10, help='spend capital every N fights')
    a = ap.parse_args()
    out = {}
    th = []
    for x in a.accts.split(','):
        if not x:
            continue
        g = LWSession(x).get('/garden/get'); g = g.get('garden', g)
        total = min(int(g.get('fights') or 0), a.max); lids = ACCTS[x]
        for i, lid in enumerate(lids):
            # the account's fights are shared evenly; the remainder goes to the newest leek
            share = total // len(lids) + (total % len(lids) if i == len(lids) - 1 else 0)
            th.append(threading.Thread(target=farm, args=(x, lid, share, a.check, out)))
    for t in th:
        t.start()
    for t in th:
        t.join()
    new = not os.path.exists(LOG)
    with open(LOG, 'a', newline='') as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(['date', 'acct', 'leek', 'fights', 'wins', 'level', 'xp', 'talent'])
        for (acct, _), (name, n, wins, l0, l1, xp, tal, st) in out.items():
            w.writerow([time.strftime('%Y-%m-%d'), acct, name, n, wins, l1, xp, tal])
            print('== %s %s: %d fights, %d wins, level %s -> %s, talent %s, stats %s' % (acct, name, n, wins, l0, l1, tal, st))


if __name__ == '__main__':
    main()
