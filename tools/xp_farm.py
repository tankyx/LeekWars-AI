#!/usr/bin/env python3
"""XP farm for the Cure leeks (exp unlocked, target level 300 = 14,078,968 XP).

Runs Nasu boss fights (boss 1: ~100% wins with V10, ~1,050 XP per leek per credit, XP to all
four leeks) with a few fights in flight, and after every --check fights:
  - spends any new capital following each leek's plan (CAPITAL_PLAN: stat targets in totals,
    first unmet target gets the capital; spend-capital works in tier-limited chunks, so loop),
  - lists weapons/chips whose level the leek just reached and that it does not carry
    (written to data/ladder/xp_farm_unlocks.json for review - nothing is bought automatically).
Progress log: data/ladder/xp_farm.csv

    python3 tools/xp_farm.py --fights 200 --inflight 3 --check 25
"""
import argparse, csv, json, os, sys, threading, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession

LEEKS = {19703: 'LeekRain', 21175: 'DawnFall', 129801: 'DuskHope', 130236: 'ProdigalSon'}
# stat targets on TOTAL stats, in order; the first one not reached receives the new capital
CAPITAL_PLAN = {
    'LeekRain':    [('strength', 600), ('science', 450), ('life', 99999)],
    'DawnFall':    [('magic', 600), ('wisdom', 350), ('life', 99999)],
    'DuskHope':    [('magic', 600), ('wisdom', 350), ('life', 99999)],
    'ProdigalSon': [('strength', 600), ('wisdom', 300), ('life', 99999)],
}
LOG = os.path.join(ROOT, 'data', 'ladder', 'xp_farm.csv')
UNLOCKS = os.path.join(ROOT, 'data', 'ladder', 'xp_farm_unlocks.json')
L300 = 14078968


def spend_capital(lw, lid, name):
    spent = []
    for _ in range(30):
        l = lw.leek(lid)
        cap = l.get('capital') or 0
        if cap <= 0:
            break
        stat = next((s for s, t in CAPITAL_PLAN[name] if (l.get('total_' + s) or 0) < t), 'life')
        r = lw.post('/leek/spend-capital', leek_id=lid, characteristics=json.dumps({stat: cap}))
        if isinstance(r, dict) and r.get('error'):
            # try a smaller chunk (tier limits)
            r = lw.post('/leek/spend-capital', leek_id=lid, characteristics=json.dumps({stat: 1}))
            if isinstance(r, dict) and r.get('error'):
                print('   spend-capital %s %s failed: %s' % (name, stat, r), flush=True)
                break
        spent.append(stat)
    return spent


def unlocks(lw, items, lid, level, prev_level):
    l = lw.leek(lid)
    have = {x['template'] for x in l['weapons']} | {x['template'] for x in l['chips']}
    out = []
    for k, v in items.items():
        if v.get('type') not in (1, 2) or not v.get('level'):
            continue
        if prev_level < v['level'] <= level and int(k) not in have:
            out.append({'item': int(k), 'name': v['name'], 'level': v['level'], 'price': v.get('price')})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fights', type=int, default=200)
    ap.add_argument('--inflight', type=int, default=3)
    ap.add_argument('--check', type=int, default=25)
    ap.add_argument('--boss', type=int, default=1)
    a = ap.parse_args()
    lw = LWSession('cure')
    items = lw.get('/item/get-all')
    levels = {lid: lw.leek(lid)['level'] for lid in LEEKS}
    new = not os.path.exists(LOG)
    fh = open(LOG, 'a', newline=''); w = csv.writer(fh)
    if new:
        w.writerow(['time', 'fight', 'win', 'turns'] + ['%s_xp' % n for n in LEEKS.values()] + ['%s_level' % n for n in LEEKS.values()])
    found = json.load(open(UNLOCKS)) if os.path.exists(UNLOCKS) else []
    pending = []; started = 0; done = 0; wins = 0; t0 = time.time()
    while done < a.fights:
        while started < a.fights and len(pending) < a.inflight:
            r = lw.post('/garden/start-boss-fight', boss_id=a.boss, participants=json.dumps(list(LEEKS)))
            fid = r.get('fight') if isinstance(r, dict) else None
            if not fid:
                print('start failed: %s' % str(r)[:150], flush=True)
                if 'not_enough' in str(r) or 'fights' in str(r):
                    a.fights = started
                time.sleep(3)
                break
            pending.append(fid); started += 1
        time.sleep(2)
        for fid in list(pending):
            g = lw.get('/fight/get/%d' % fid); g = g.get('fight', g) if isinstance(g, dict) else {}
            if g.get('status') != 2:
                continue
            pending.remove(fid); done += 1
            rep = g.get('report') or {}
            xp = {x['id']: x.get('xp', 0) for x in rep.get('leeks1', [])}
            win = g.get('winner') == 1; wins += win
            w.writerow([int(time.time()), fid, int(win), rep.get('duration')] + [xp.get(l, 0) for l in LEEKS] + [''] * 4)
            fh.flush()
            if done % a.check == 0 or done == a.fights:
                line = []
                for lid, name in LEEKS.items():
                    l = lw.leek(lid)
                    if l['level'] > levels[lid]:
                        u = unlocks(lw, items, lid, l['level'], levels[lid])
                        for x in u:
                            x['leek'] = name
                        found += u
                        levels[lid] = l['level']
                    sp = spend_capital(lw, lid, name)
                    l = lw.leek(lid)
                    line.append('%s L%d %.1f%% to 300%s' % (name, l['level'], 100.0 * l['xp'] / L300, (' +cap:' + ','.join(sorted(set(sp)))) if sp else ''))
                json.dump(found, open(UNLOCKS, 'w'), indent=1)
                print('%d/%d fights, %d wins, %.0f s | %s' % (done, a.fights, wins, time.time() - t0, ' | '.join(line)), flush=True)
    fh.close()
    print('done: %d fights, %d wins; unlocks to review: %d (data/ladder/xp_farm_unlocks.json)' % (done, wins, len(found)))


if __name__ == '__main__':
    main()
