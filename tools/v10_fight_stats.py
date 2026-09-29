#!/usr/bin/env python3
"""Per-leek V10 behaviour metrics on recent garden fights (from the live API).

    python3 tools/v10_fight_stats.py --since 1790680000 [--until T] [--leeks AdaLovelace,KurtGodel]

For each leek, over its solo garden fights in [since, until): W/L, turns
ending within 10 cells with no attacking plan at all (V10A log), share of the
weapon damage we took from shots aimed at another cell (area splash), our
liberation casts, our hits on summons, and damage dealt / taken per turn.
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lw_api import LWSession

LEEKS = {'AdaLovelace': 20443, 'EdsgerDijkstra': 129288, 'KurtGodel': 129295, 'MargaretHamilton': 129296}


def stats(lw, lid, since, until):
    h = lw.get('/history/get-leek-history/%d' % lid) or {}
    fs = [f for f in h.get('fights', []) if f.get('type') == 0 and f.get('context') == 2
          and since <= (f.get('date') or 0) < until]
    m = dict(n=0, w=0, turns=0, near=0, noatk=0, taken_w=0, splash=0, lib=0, bulb_hits=0, dealt=0, taken=0)
    for f0 in fs:
        f = lw.get('/fight/get/%d' % f0['id']); f = f.get('fight', f)
        L = f['data']['leeks']
        team = 1 if any(l['id'] == lid for l in f['leeks1']) else 2
        mine = [l for l in L if l['team'] == team and not l.get('summon')][0]
        foes = {l['id'] for l in L if l['team'] != team}
        bulbs = {l['id'] for l in L if l['team'] != team and l.get('summon')}
        m['n'] += 1; m['w'] += 1 if f['winner'] == team else 0
        pos = {l['id']: l.get('cellPos') for l in L}
        cur = None; aimed_other = None
        for a in f['data']['actions']:
            if a[0] == 7:
                cur = a[1]
            elif a[0] == 10:
                pos[a[1]] = a[2]
            elif a[0] == 16 and cur in foes:
                aimed_other = a[1] != pos.get(mine['id'])
            elif a[0] in (101, 110):
                if a[1] == mine['id']:
                    m['taken'] += a[2]
                    if a[0] == 101 and cur in foes and aimed_other is not None:
                        m['taken_w'] += a[2]
                        if aimed_other:
                            m['splash'] += a[2]
                elif a[1] in foes and cur == mine['id']:
                    m['dealt'] += a[2]
                    if a[1] in bulbs:
                        m['bulb_hits'] += 1
        logs = (lw.get('/fight/get-logs/%d' % f0['id']) or {}).get('18035') or {}
        txt = [str(e[2]) for k in sorted(logs, key=int) for e in logs[k] if len(e) > 2]
        for i, t in enumerate(txt):
            if t.startswith('V10X T'):      # executed actions: 'libera:1' / 'libera:2' = cast (normal / critical)
                m['lib'] += t.count('libera:1') + t.count('libera:2')
            if not t.startswith('V10 T'):
                continue
            m['turns'] += 1
            try:
                d = int(t.split('end_d=')[1].split()[0])
            except Exception:
                continue
            if d <= 10:
                m['near'] += 1
                if i + 1 < len(txt) and 'attacking plans evaluated=0' in txt[i + 1]:
                    m['noatk'] += 1
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--since', type=int, required=True)
    ap.add_argument('--until', type=int, default=2 ** 40)
    ap.add_argument('--leeks', default=','.join(LEEKS))
    a = ap.parse_args()
    lw = LWSession('main')
    for name in a.leeks.split(','):
        m = stats(lw, LEEKS[name], a.since, a.until)
        n, t = max(1, m['n']), max(1, m['turns'])
        print('%-17s %3d fights %5.1f%% W | no attack near %3d/%-3d (%4.1f%%) | splash %4.1f%% of weapon dmg taken | '
              'liberation %3d | bulb hits %3d | dealt/turn %4.0f taken/turn %4.0f' % (
                  name, m['n'], 100.0 * m['w'] / n, m['noatk'], m['near'], 100.0 * m['noatk'] / max(1, m['near']),
                  100.0 * m['splash'] / max(1, m['taken_w']), m['lib'], m['bulb_hits'], m['dealt'] / t, m['taken'] / t))


if __name__ == '__main__':
    main()
