#!/usr/bin/env python3
"""Compare two arms of simulated Pumpkin fights run on the same seeds (tools/local_pumpkin.py --tag A / --tag B).

    python3 tools/pumpkin_ab.py abA abB

Per arm: wins, fight length, kopile drops, resurrections, damage dealt / taken, our dead by rounds 8 and 12,
mob kills, V10's BLOCK notes (blocks attempted) and how many of them came right before a slot. Paired by seed: mean
difference and a sign test on kopile drops and damage dealt.
"""
import glob, json, math, os, re, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from pumpkin_fights import _data, turns  # noqa: E402

OUT = os.path.join(ROOT, 'data', 'sim_pumpkin')


def notes(j):
    out = []

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str) and o.startswith('BOSS'):
            out.append(o)
    walk(j.get('logs') or {})
    return out


def fight_stats(path):
    j = json.load(open(path))
    f, d = _data(j)
    T = turns(d)
    teams = T[0]['teams']; names = T[0]['names']
    ours = [i for i, t in teams.items() if t == 1 and not str(names.get(i)).endswith(('bulb', 'prototaxite'))
            and not any(e['id'] == i and e.get('summon') for e in d['leeks'])]
    rnd = 1; dead = []
    for a in d['actions']:
        if a[0] == 6:
            rnd = a[1]
        elif a[0] == 5 and a[1] in ours:
            dead.append(rnd)
    blocks = sum(len(re.findall(r'BLOCK', n)) for n in notes(j))
    # slots: mob turns that resurrect, kopile or umri
    slots = sum(1 for r in T if r['team'] == 2 and (r['rez'] or r['kopile'] or 'ⱆⰿⱃⰻ!' in r['says']))
    return dict(win=int(j.get('winner') == 0), turns=max(r['turn'] for r in T),
                kopile=sum(1 for r in T if r['kopile']),
                rez=sum(1 for r in T if r['rez'] and teams.get(r['id']) == 2),
                dealt=sum(v for r in T if r['team'] == 1 for k, v in r['dmg'].items() if teams.get(k) == 2),
                taken=sum(v for r in T if r['team'] == 2 for k, v in r['dmg'].items() if teams.get(k) == 1),
                dead8=sum(1 for x in dead if x <= 8), dead12=sum(1 for x in dead if x <= 12),
                kills=sum(1 for a in d['actions'] if a[0] == 5 and teams.get(a[1]) == 2),
                blocks=blocks, slots=slots)


def arm(tag):
    out = {}
    for p in glob.glob(os.path.join(OUT, '%s_*.json' % tag)):
        seed = int(p.rsplit('_', 1)[1][:-5])
        out[seed] = fight_stats(p)
    return out


def sign_p(pos, neg):
    n = pos + neg
    if n == 0:
        return 1.0
    k = min(pos, neg)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def main():
    a, b = sys.argv[1], sys.argv[2]
    A, B = arm(a), arm(b)
    seeds = sorted(set(A) & set(B))
    print('%d paired seeds (%s: %d, %s: %d)' % (len(seeds), a, len(A), b, len(B)))
    keys = ['win', 'turns', 'kopile', 'rez', 'kills', 'dealt', 'taken', 'dead8', 'dead12', 'blocks', 'slots']
    print('%-8s %10s %10s %10s' % ('', a, b, 'b - a'))
    for k in keys:
        ma = statistics.mean(A[s][k] for s in seeds); mb = statistics.mean(B[s][k] for s in seeds)
        print('%-8s %10.2f %10.2f %+10.2f' % (k, ma, mb, mb - ma))
    for k in ('kopile', 'kills', 'dealt', 'dead12'):
        pos = sum(1 for s in seeds if B[s][k] > A[s][k]); neg = sum(1 for s in seeds if B[s][k] < A[s][k])
        print('sign test %-7s b>a %d, b<a %d, p=%.3f' % (k, pos, neg, sign_p(pos, neg)))


if __name__ == '__main__':
    main()
