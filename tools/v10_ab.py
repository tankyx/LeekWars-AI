#!/usr/bin/env python3
"""Paired local A/B of two V10 bundles (same leek, opponent and seed per pair).

    python3 tools/v10_ab.py V10/v10_a.py V10/v10_b.py --seeds 5 -j 6
    python3 tools/v10_ab.py A.py B.py --leeks EdsgerDijkstra --opps clone_topac --seeds 20

Prints wins per arm, per leek / opponent, and the discordant pairs with an
exact two-sided sign test (the only fights that tell the arms apart).
"""
import argparse, itertools, math, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEEKS = ['EdsgerDijkstra', 'KurtGodel', 'MargaretHamilton', 'AdaLovelace']
# local clones of real ladder opponents (run V8), strongest testbeds first
OPPS = ['clone_topac', 'clone_rotulet', 'clone_TheLeaker', 'clone_Yongyong', 'clone_grinhaire', 'clone_HerculeNsjtt']


def fight(ai, leek, opp, seed):
    """1 = win, 0.5 = draw, 0 = loss, None = error."""
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'local_test.py'), '1', opp, '--leek', leek,
                        '--ai', ai, '--seed', str(seed)], capture_output=True, text=True, cwd=ROOT, timeout=1800)
    m = re.search(r'Wins: (\d+)\s+Losses: (\d+)\s+Draws: (\d+)', r.stdout)
    if not m:
        return None
    w, l, d = (int(v) for v in m.groups())
    return 1.0 if w else (0.5 if d else (0.0 if l else None))


def sign_test(k, n):
    """Two-sided exact binomial p-value for k successes out of n at p=0.5."""
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(0, min(k, n - k) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a'); ap.add_argument('b')
    ap.add_argument('--leeks', default=','.join(LEEKS))
    ap.add_argument('--opps', default=','.join(OPPS))
    ap.add_argument('--seeds', type=int, default=5)
    ap.add_argument('--seed0', type=int, default=1)
    ap.add_argument('-j', type=int, default=6)
    a = ap.parse_args()
    leeks, opps = a.leeks.split(','), a.opps.split(',')
    seeds = range(a.seed0, a.seed0 + a.seeds)
    jobs = [(arm, ai, l, o, s) for (l, o, s) in itertools.product(leeks, opps, seeds)
            for arm, ai in (('A', a.a), ('B', a.b))]
    res = {}
    with ThreadPoolExecutor(max_workers=a.j) as ex:
        futs = {ex.submit(fight, ai, l, o, s): (arm, l, o, s) for arm, ai, l, o, s in jobs}
        for n, f in enumerate(futs, 1):
            res[futs[f]] = f.result()
            if n % 20 == 0:
                print('  %d/%d fights' % (n, len(jobs)), flush=True)
    pairs = [(l, o, s, res[('A', l, o, s)], res[('B', l, o, s)]) for l, o, s in itertools.product(leeks, opps, seeds)]
    ok = [p for p in pairs if p[3] is not None and p[4] is not None]
    print('\n%d pairs (%d with an error dropped)' % (len(ok), len(pairs) - len(ok)))
    print('A %s: %.1f wins   B %s: %.1f wins' % (a.a, sum(p[3] for p in ok), a.b, sum(p[4] for p in ok)))
    for key, idx in (('leek', 0), ('opponent', 1)):
        for v in (leeks if idx == 0 else opps):
            sub = [p for p in ok if p[idx] == v]
            print('  %-8s %-20s A %4.1f  B %4.1f  / %d' % (key, v, sum(p[3] for p in sub), sum(p[4] for p in sub), len(sub)))
    bw = sum(1 for p in ok if p[4] > p[3]); aw = sum(1 for p in ok if p[3] > p[4])
    for p in ok:
        if p[3] != p[4]:
            print('  discordant: %s vs %s seed %d  A %.1f  B %.1f' % p)
    print('discordant pairs: B better %d, A better %d  -> sign test p = %.3f' % (bw, aw, sign_test(bw, bw + aw)))


if __name__ == '__main__':
    main()
