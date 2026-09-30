#!/usr/bin/env python3
"""Who each leek beats, and who beats it (garden fights, from the smart
selector's per-leek history DBs tools/fight_history_<leek>.db).

    python3 tools/matchup_report.py                       # main, since the V10 switch
    python3 tools/matchup_report.py --account cure --since 2026-09-29
    python3 tools/matchup_report.py --min-fights 2 --top 15

Per leek: record by opponent archetype (main stat among STR/MAG/AGI/SCI of the
opponent's CURRENT stats, cached in data/ladder/opponent_cache.json), the
opponents it beats consistently ("farm") and the ones that beat it
("nemeses"), with their current talent.
"""
import argparse, collections, datetime, json, os, sqlite3, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession

ACCOUNTS = {'main': {'AdaLovelace': 20443, 'EdsgerDijkstra': 129288, 'KurtGodel': 129295, 'MargaretHamilton': 129296},
            'cure': {'LeekRain': 19703, 'DawnFall': 21175, 'DuskHope': 129801, 'ProdigalSon': 130236}}
CACHE = os.path.join(ROOT, 'data', 'ladder', 'opponent_cache.json')
CACHE_DAYS = 7


def archetype(l):
    s = {k: l.get('total_' + k, l.get(k, 0)) or 0 for k in ('strength', 'magic', 'agility', 'science')}
    return {'strength': 'STR', 'magic': 'MAG', 'agility': 'AGI', 'science': 'SCI'}[max(s, key=s.get)]


def opponent_info(lw, ids, rate=6.0):
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    now = time.time(); todo = [i for i in ids if str(i) not in cache or now - cache[str(i)]['t'] > CACHE_DAYS * 86400]
    for n, i in enumerate(todo):
        time.sleep(1.0 / rate)
        try:
            l = lw.get('/leek/get/%d' % i); l = l.get('leek', l) if isinstance(l, dict) else {}
        except Exception:
            l = {}
        if l.get('name'):
            cache[str(i)] = {'t': now, 'name': l['name'], 'arch': archetype(l), 'talent': l.get('talent'), 'level': l.get('level')}
        if (n + 1) % 100 == 0:
            print('  fetched %d/%d opponents' % (n + 1, len(todo)), flush=True)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(cache, open(CACHE, 'w'))
    return cache


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--account', default='main', choices=sorted(ACCOUNTS))
    ap.add_argument('--since', default='2026-09-29T09:00', help='ISO date/time (default: the V10 switch)')
    ap.add_argument('--min-fights', type=int, default=3)
    ap.add_argument('--top', type=int, default=10)
    a = ap.parse_args()
    lw = LWSession(a.account)
    data = {}
    for name, lid in ACCOUNTS[a.account].items():
        p = os.path.join(HERE, 'fight_history_%d.db' % lid)
        if not os.path.exists(p):
            continue
        rows = sqlite3.connect(p).execute('SELECT opponent_id, opponent_name, result, timestamp FROM fight_history').fetchall()
        rows = [r for r in rows if (r[3] or '').replace(' ', 'T') >= a.since]
        data[name] = rows
    ids = sorted({r[0] for rows in data.values() for r in rows})
    print('%d distinct opponents since %s' % (len(ids), a.since), flush=True)
    info = opponent_info(lw, ids)
    for name, rows in data.items():
        by_arch = collections.defaultdict(collections.Counter); per = collections.defaultdict(collections.Counter)
        for oid, oname, res, _ in rows:
            arch = (info.get(str(oid)) or {}).get('arch', '?')
            by_arch[arch][res] += 1; per[oid][res] += 1; per[oid]['_name'] = 0
        tot = collections.Counter(r[2] for r in rows)
        print('\n== %s: %d fights  %dW/%dL/%dD (%.0f%%)' % (name, len(rows), tot['WIN'], tot['LOSS'], tot['DRAW'],
                                                        100.0 * tot['WIN'] / max(1, len(rows))))
        for arch in ('STR', 'MAG', 'SCI', 'AGI', '?'):
            c = by_arch.get(arch)
            if c:
                n = sum(c.values())
                print('   vs %-3s %4d fights (%2.0f%% of all)  %3dW/%3dL/%2dD  win %2.0f%%' % (
                    arch, n, 100.0 * n / max(1, len(rows)), c['WIN'], c['LOSS'], c['DRAW'], 100.0 * c['WIN'] / n))
        rec = [(oid, c['WIN'], c['LOSS'], c['DRAW']) for oid, c in per.items() if c['WIN'] + c['LOSS'] + c['DRAW'] >= a.min_fights]
        def line(oid, w, l, d):
            i = info.get(str(oid)) or {}
            return '%-18s %-3s talent %-5s %dW/%dL/%dD' % (i.get('name', oid), i.get('arch', '?'), i.get('talent', '?'), w, l, d)
        farm = sorted([r for r in rec if r[1] / (r[1] + r[2] + r[3]) >= 0.75], key=lambda r: (-r[1], r[2]))[:a.top]
        nem = sorted([r for r in rec if r[1] / (r[1] + r[2] + r[3]) <= 0.25], key=lambda r: (-r[2], r[1]))[:a.top]
        print('   farm (>=75%% wins, >=%d fights): %d opponents' % (a.min_fights, len(farm)))
        for r in farm:
            print('      ' + line(*r))
        print('   nemeses (<=25%% wins, >=%d fights): %d opponents' % (a.min_fights, len(nem)))
        for r in nem:
            print('      ' + line(*r))


if __name__ == '__main__':
    main()
