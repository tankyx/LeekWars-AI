#!/usr/bin/env python3
"""Compare simulated Pumpkin fights (tools/local_pumpkin.py) with our real 8-leek Pumpkin fights.

    python3 tools/pumpkin_calibrate.py --sim 'data/sim_pumpkin/v10_*.json'            # vs the last 20 real (v16)
    python3 tools/pumpkin_calibrate.py --sim 'data/sim_pumpkin/v10_*.json' --real all  # vs all 100 real

Prints, real vs sim: fight length, resurrections, kopile drops, damage dealt / taken, our deaths by round,
damage taken per round, and per mob type the damage, chips and MP per turn over rounds 1-8 (the part of a
fight both have; later rounds depend on who is still alive).
"""
import argparse, collections, glob, os, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from pumpkin_fights import load, turns, MOBS  # noqa: E402

V16 = range(54241261, 54241303)


def real_ids(which):
    ids = []
    for line in open(os.path.join(ROOT, 'data', 'ladder', 'boss_slot.csv')):
        p = line.strip().split(',')
        if len(p) >= 5 and p[1] == '3':
            ids += [int(x) for x in p[4].split()]
    return set(ids if which == 'all' else [i for i in ids if i in V16])


def stats(fights):
    S = collections.defaultdict(list)
    M = collections.defaultdict(lambda: collections.defaultdict(list))
    for d in fights:
        T = turns(d)
        if not T:
            continue
        teams = T[0]['teams']; names = T[0]['names']
        ours = [i for i, t in teams.items() if t == 1 and not any(e['id'] == i and e.get('summon') for e in d['leeks'])
                and not str(names.get(i)).endswith(('bulb', 'prototaxite'))]
        S['turns'].append(max(r['turn'] for r in T))
        S['rez'].append(sum(1 for r in T if r['rez'] and teams.get(r['id']) == 2))
        S['kopile'].append(sum(1 for r in T if r['kopile']))
        S['dealt'].append(sum(v for r in T if r['team'] == 1 for k, v in r['dmg'].items() if teams.get(k) == 2))
        S['taken'].append(sum(v for r in T if r['team'] == 2 for k, v in r['dmg'].items() if teams.get(k) == 1))
        rnd = 1; dead_by = collections.Counter(); taken_r = collections.Counter()
        for a in d['actions']:
            if a[0] == 6:
                rnd = a[1]
            elif a[0] == 5 and a[1] in ours:
                dead_by[rnd] += 1
        for r in T:
            if r['team'] == 2:
                taken_r[r['turn']] += sum(v for k, v in r['dmg'].items() if teams.get(k) == 1)
        cum = 0
        for R in range(1, 21):
            cum += dead_by[R]
            S['dead_by_%02d' % R].append(cum)
        for R in range(1, 11):
            S['taken_r%02d' % R].append(taken_r[R])
        for r in T:
            if r['team'] != 2 or r['summon'] or r['turn'] > 8:
                continue
            m = M[r['name']]
            m['dmg'].append(sum(v for k, v in r['dmg'].items() if teams.get(k) == 1))
            m['mp'].append(sum(x[2] for x in r['moves']))
            m['chips'].append(len(r['chips']) + len(r['shots']))
            m['idle'].append(int(not r['chips'] and not r['moves'] and not r['shots']))
    return S, M


def fmt(xs):
    if not xs:
        return '-'
    return '%7.1f (med %6.1f)' % (statistics.mean(xs), statistics.median(xs))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sim', required=True, help='glob of simulated fight JSONs')
    ap.add_argument('--real', default='v16', choices=['v16', 'all'])
    a = ap.parse_args()
    ids = real_ids(a.real)
    real = [d for _, fid, f, d in load('ours') if fid in ids]
    sim = [d for _, fid, f, d in load(a.sim)]
    print('real %d fights (%s), sim %d fights (%s)' % (len(real), a.real, len(sim), a.sim))
    (RS, RM), (SS, SM) = stats(real), stats(sim)
    print('%-14s %-24s %-24s' % ('', 'real', 'sim'))
    for k in sorted(RS):
        if k.startswith('dead_by') and int(k[-2:]) not in (2, 3, 4, 5, 6, 8, 10, 12, 15, 20):
            continue
        print('%-14s %-24s %-24s' % (k, fmt(RS[k]), fmt(SS[k])))
    print('per mob turn, rounds 1-8:')
    for nm in MOBS:
        for k in ('dmg', 'chips', 'mp', 'idle'):
            print('  %-12s %-6s %-24s %-24s' % (nm, k, fmt(RM[nm][k]), fmt(SM[nm][k])))


if __name__ == '__main__':
    main()
