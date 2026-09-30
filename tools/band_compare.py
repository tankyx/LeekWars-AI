#!/usr/bin/env python3
"""Snapshot the leeks of two talent bands (default 2400+ vs 2000-2300, active,
level 301) with their full /leek/get (stats, chips, weapons, components) to
data/ladder/band_compare.json, for comparing our leeks to the ones above us.

    python3 tools/band_compare.py --top 2400 --peer-lo 2000 --peer-hi 2300 --peer-sample 250
"""
import argparse, json, os, random, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession
OUT = os.path.join(ROOT, 'data', 'ladder', 'band_compare.json')
OURS = [20443, 129288, 129295, 129296]


def ranking(lw, lo, hi, rate):
    out, page = [], 1
    while True:
        time.sleep(1.0 / rate)
        r = lw.get('/ranking/get/leek/talent/%d/null' % page).get('ranking') or []
        if not r:
            break
        out += [l for l in r if lo <= l['talent'] <= hi and l.get('active') and l.get('level') == 301]
        if r[-1]['talent'] < lo:
            break
        page += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--top', type=int, default=2400)
    ap.add_argument('--peer-lo', type=int, default=2000); ap.add_argument('--peer-hi', type=int, default=2300)
    ap.add_argument('--peer-sample', type=int, default=250)
    ap.add_argument('--rate', type=float, default=8.0)
    a = ap.parse_args()
    lw = LWSession('main')
    rows = ranking(lw, a.peer_lo, 99999, a.rate)
    top = [l for l in rows if l['talent'] >= a.top]
    peers = [l for l in rows if a.peer_lo <= l['talent'] <= a.peer_hi]
    random.Random(1).shuffle(peers); peers = peers[:a.peer_sample]
    print('top %d, peers %d (sampled)' % (len(top), len(peers)), flush=True)
    data = {'date': time.strftime('%Y-%m-%d'), 'top': [], 'peers': [], 'ours': []}
    for group, ls in (('top', top), ('peers', peers), ('ours', [{'id': i} for i in OURS])):
        for n, l in enumerate(ls):
            time.sleep(1.0 / a.rate)
            d = lw.leek(l['id'])
            if d.get('id'):
                d.pop('fights', None); d.pop('talent_history_long', None); d.pop('tournaments', None)
                data[group].append(d)
            if (n + 1) % 50 == 0:
                print('  %s %d/%d' % (group, n + 1, len(ls)), flush=True)
    json.dump(data, open(OUT, 'w'))
    print('saved %s' % OUT)


if __name__ == '__main__':
    main()
