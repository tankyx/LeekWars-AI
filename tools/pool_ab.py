#!/usr/bin/env python3
"""
Pool several matchup_ab.py outputs into one verdict.

A per-opponent A/B at n=60 cannot resolve a small effect on its own; a panel
of them can. This sums the discordant pairs across runs (McNemar on the
pooled flips), averages the HP-lead and behavioural-proxy deltas weighted by
n, and prints one table plus the pooled verdict. Runs are read from the
saved matchup_ab text output (tee it when running the panel).

    python3 tools/pool_ab.py /tmp/panel_ab_*.txt
"""
import math
import re
import sys


def parse(path):
    t = open(path).read()
    g = lambda rx, cast=float: (cast(re.search(rx, t).group(1)) if re.search(rx, t) else None)
    return {
        'label': (re.search(r'=== (.+?) \(n=(\d+) paired\)', t) or [None, path, '0'])[1],
        'n': int((re.search(r'\(n=(\d+) paired\)', t) or [None, '0'])[1]),
        'new_w': g(r'NEW\s+wins\s+(\d+)', int), 'base_w': g(r'BASELINE wins\s+(\d+)', int),
        'gained': g(r'flipped fights: (\d+) gained', int), 'lost': g(r'(\d+) lost by NEW', int),
        'hp': g(r'paired diff ([+-][\d.]+)'), 'hp_sd': g(r'\(sd ([\d.]+)'),
        'hnh': g(r'fire-then-move rate.*?diff ([+-][\d.]+)'),
        'deny': g(r'denied a shot next turn.*?diff ([+-][\d.]+)'),
    }


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def main():
    runs = []
    for path in sys.argv[1:]:
        r = parse(path)
        if not r['n'] or r['gained'] is None or r['lost'] is None:
            # A grep-filtered save loses the '=== ... (n=N paired)' header and
            # the flip counts; refuse quietly-wrong pooling.
            print('WARNING: %s is not a full matchup_ab output (missing header or flip counts) -- skipped' % path)
            continue
        runs.append(r)
    if not runs:
        sys.exit('no parsable runs')
    print('%-46s %5s %8s %8s %9s %8s %8s %8s' % ('run', 'n', 'NEW', 'BASE', 'gain/lost', 'HP', 'hnh', 'deny'))
    G = L = N = 0
    hp_num = hp_w = 0.0
    hnh = deny = 0.0
    for r in runs:
        print('%-46s %5d %8d %8d %4d/%-4d %+8.1f %+8.3f %+8.3f' % (
            r['label'][:46], r['n'], r['new_w'], r['base_w'], r['gained'], r['lost'],
            r['hp'] or 0, r['hnh'] or 0, r['deny'] or 0))
        G += r['gained']; L += r['lost']; N += r['n']
        if r['hp'] is not None and r['hp_sd']:
            w = r['n'] / (r['hp_sd'] ** 2)
            hp_num += w * r['hp']; hp_w += w
        hnh += (r['hnh'] or 0) * r['n']; deny += (r['deny'] or 0) * r['n']
    p = mcnemar(L, G)
    hp = hp_num / hp_w if hp_w else 0.0
    se = math.sqrt(1 / hp_w) if hp_w else 0.0
    nw = sum(r['new_w'] for r in runs); bw = sum(r['base_w'] for r in runs)
    print('-' * 100)
    print('POOLED  n=%d  NEW %d (%.1f%%) vs BASELINE %d (%.1f%%)   gained %d / lost %d   McNemar p = %.4f'
          % (N, nw, 100 * nw / N, bw, 100 * bw / N, G, L, p))
    print('        HP-lead diff %+.1f (se %.1f, t=%.2f)   fire-then-move %+.3f   shot-denial %+.3f'
          % (hp, se, (hp / se) if se else 0, hnh / N, deny / N))
    if p < 0.05:
        print('VERDICT: NEW is %s across the panel (p=%.4f).' % ('BETTER' if G > L else 'WORSE', p))
    else:
        print('VERDICT: not distinguishable from noise across the panel (p=%.4f).' % p)


if __name__ == '__main__':
    main()
