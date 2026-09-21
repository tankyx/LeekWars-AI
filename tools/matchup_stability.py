#!/usr/bin/env python3
"""
Establish whether a matchup is a usable testbed before any doctrine is measured
against it.

Answers two independent questions:

 1. DETERMINISM - does the same seed replay to the same result? If not, seeds
    are not a control variable and every A/B needs far more samples.
 2. SEED VARIANCE - how far does the win rate move between blocks of seeds?
    This is what tells you the minimum n at which a measured change is real
    rather than a different draw of starting positions.

    python3 tools/matchup_stability.py EdsgerDijkstra ladder_eleeksire -n 120 -j 8
"""
import argparse
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import local_test as lt


def _one(args):
    leek_cfg, opp_cfg, seed, ai = args
    lt.AI_PATH = ai
    scn = lt.build_scenario(leek_cfg, opp_cfg, seed=seed)
    for team in scn['entities']:
        for e in team:
            if e['team'] == 1:
                e['ai'] = ai
    r = lt.run_fight(scn)
    if r.get('error'):
        return (seed, 'ERR', 0, 0)
    return (seed, r['result'], r['total_turns'], r['our_ops'])


def wilson(k, n, z=1.96):
    """Wilson score interval - honest at small n, unlike the normal approx."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    s = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - s) / d, (c + s) / d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('leek')
    ap.add_argument('opponent')
    ap.add_argument('-n', type=int, default=120)
    ap.add_argument('-j', type=int, default=8)
    ap.add_argument('--seed0', type=int, default=7000)
    ap.add_argument('--ai', default='V9_modules/main.lk')
    ap.add_argument('--block', type=int, default=20)
    ap.add_argument('--replay', type=int, default=12,
                    help='how many seeds to run twice as a determinism check')
    a = ap.parse_args()

    cfg = lt.load_configs()
    leek_cfg = cfg['leeks'][a.leek]
    opp_cfg = cfg['opponents'][a.opponent]

    jobs = [(leek_cfg, opp_cfg, a.seed0 + i, a.ai) for i in range(a.n)]
    # replay the first --replay seeds a second time, interleaved so any drift in
    # machine state would show up rather than being masked by running them back to back
    jobs += [(leek_cfg, opp_cfg, a.seed0 + i, a.ai) for i in range(a.replay)]

    out = []
    with ProcessPoolExecutor(max_workers=a.j) as ex:
        for i, r in enumerate(ex.map(_one, jobs)):
            out.append(r)
            if (i + 1) % 20 == 0:
                print('  ... %d/%d' % (i + 1, len(jobs)), file=sys.stderr, flush=True)

    first = out[:a.n]
    replays = out[a.n:]

    print('\n=== %s vs %s  (%s) ===' % (a.leek, a.opponent, a.ai))

    # --- determinism
    base = {s: (res, t) for s, res, t, _ in first}
    mismatch = [(s, base[s], (res, t)) for s, res, t, _ in replays
                if s in base and base[s] != (res, t)]
    print('\nDETERMINISM: replayed %d seeds, %d diverged' % (len(replays), len(mismatch)))
    for s, b, r in mismatch[:6]:
        print('   seed %d: %s -> %s' % (s, b, r))
    if not mismatch:
        print('   same seed replays identically -> seeds ARE a control variable,'
              ' so paired A/B on the same seed set is valid')

    # --- overall
    w = sum(1 for _, r, _, _ in first if r == 'WIN')
    l = sum(1 for _, r, _, _ in first if r == 'LOSS')
    d = sum(1 for _, r, _, _ in first if r == 'DRAW')
    e = sum(1 for _, r, _, _ in first if r == 'ERR')
    n = w + l + d
    lo, hi = wilson(w, n)
    print('\nOVERALL: %dW %dL %dD (errors %d)   win rate %.1f%%  95%% CI [%.1f%%, %.1f%%]'
          % (w, l, d, e, 100 * w / max(n, 1), 100 * lo, 100 * hi))

    # --- block variance
    print('\nPER-BLOCK win rate (block = %d seeds):' % a.block)
    rates = []
    for i in range(0, a.n, a.block):
        blk = first[i:i + a.block]
        bw = sum(1 for _, r, _, _ in blk if r == 'WIN')
        bn = sum(1 for _, r, _, _ in blk if r != 'ERR')
        if not bn:
            continue
        rates.append(bw / bn)
        print('   seeds %d-%d: %2d/%2d = %5.1f%%  %s'
              % (a.seed0 + i, a.seed0 + i + len(blk) - 1, bw, bn, 100 * bw / bn,
                 '#' * int(20 * bw / bn)))
    if len(rates) > 1:
        m = sum(rates) / len(rates)
        sd = math.sqrt(sum((x - m) ** 2 for x in rates) / (len(rates) - 1))
        exp_sd = math.sqrt(max(m * (1 - m), 1e-9) / a.block)
        print('   block sd %.3f  vs %.3f expected from binomial noise alone  -> %s'
              % (sd, exp_sd,
                 'consistent with pure chance' if sd <= 1.6 * exp_sd
                 else 'EXCESS variance: blocks are not interchangeable'))

    # --- how big must n be
    #
    # Two designs, and the difference is large. UNPAIRED compares two
    # independent seed sets and pays for between-seed variance. PAIRED runs both
    # arms on the SAME seeds and tests only the fights that flipped (McNemar) -
    # valid only because the determinism check above passed. Quote the paired
    # numbers; they are the design we can actually run.
    p = w / max(n, 1)
    print('\nSAMPLE SIZE (80%% power, 5%% two-sided):')
    print('   %-8s %-12s %-12s' % ('change', 'unpaired n', 'paired n (per arm)'))
    for delta in (0.05, 0.10, 0.15):
        unpaired = int(math.ceil(2 * p * (1 - p) * (1.96 + 0.84) ** 2 / (delta ** 2)))
        # McNemar: psi = proportion of seeds whose outcome flips. Unknown in
        # advance, so bracket it - a change that helps `delta` net will usually
        # disturb somewhere between delta and 3*delta of fights.
        row = []
        for psi_mult in (1.2, 2.0, 3.0):
            psi = min(delta * psi_mult, 0.9)
            if psi <= delta:
                row.append('-')
                continue
            need = ((1.96 * math.sqrt(psi) + 0.84 * math.sqrt(psi - delta ** 2)) ** 2
                    / (delta ** 2))
            row.append(str(int(math.ceil(need))))
        print('   %+5.0f pp %-12d %s   (for flip-rate %.0f%%/%.0f%%/%.0f%% of fights)'
              % (100 * delta, unpaired, '/'.join(row),
                 100 * min(delta * 1.2, 0.9), 100 * min(delta * 2.0, 0.9),
                 100 * min(delta * 3.0, 0.9)))
    print('   -> run both arms on the SAME seeds and compare fight-by-fight;'
          ' report McNemar on the flipped fights, not two separate win rates.')

    turns = [t for _, r, t, _ in first if r != 'ERR']
    print('\nturns/fight: mean %.1f  min %d  max %d'
          % (sum(turns) / max(len(turns), 1), min(turns), max(turns)))
    ops = [o for _, r, _, o in first if r != 'ERR']
    print('ops/fight: mean %s  max %s' % (format(int(sum(ops) / max(len(ops), 1)), ','),
                                          format(max(ops), ',')))


if __name__ == '__main__':
    main()
