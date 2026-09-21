#!/usr/bin/env python3
"""
Paired A/B of the working tree against a baseline ref, on ONE named opponent.

Paired, not two independent runs: both arms fight the SAME seeds, and the
verdict comes from McNemar's test on the fights that changed outcome. That is
valid only because the generator replays a seed identically - verify with
    python3 tools/matchup_stability.py <leek> <opponent>
before trusting a result here. Paired costs ~3-6x fewer fights than comparing
two separate win rates for the same power.

This complements tools/mirror_ab.py, which plays the AI against itself. Use
mirror_ab to ask "is the AI better in general"; use this to ask "is the AI
better in THIS matchup", which is the question doctrine work actually poses.

    python3 tools/matchup_ab.py EdsgerDijkstra ladder_eleeksire -n 120 \
        --baseline HEAD -j 8
"""
import argparse
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import local_test as lt
from mirror_ab import materialise_baseline, clear_cache
from lw_decode import Decoder, parse_fight

DEC = Decoder()


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
        return {'seed': seed, 'result': 'ERR', 'turns': 0, 'hp': 0, 'err': r['error']}
    return {'seed': seed, 'result': r['result'], 'turns': r['total_turns'],
            'hp': hp_lead(r)}


def hp_lead(r):
    """End-of-fight HP% lead, ours minus theirs.

    fight['leeks'] holds the STARTING state (its `life` is max life), so end HP
    has to be reconstructed from the action stream: start - damage taken +
    healing applied. Win/loss alone is a coarse signal in a matchup we lose
    ~77% of the time; the margin is where most of the information is.
    """
    start = {l['id']: (max(l.get('life', 1), 1), l.get('team')) for l in r['leeks']}
    stats = parse_fight({'leeks': r['leeks'], 'actions': r['actions']}, DEC)
    ours = them = 0.0
    for eid, (mx, team) in start.items():
        e = stats.get(eid)
        if not e:
            continue
        hp = mx - sum(e['taken'].values()) + e['healed']
        pct = 100.0 * min(max(hp, 0), mx) / mx
        if e['died']:
            pct = 0.0
        if team == 1:
            ours += pct
        else:
            them += pct
    return ours - them


def mcnemar_p(b, c):
    """Exact two-sided binomial on the discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tot = 0.0
    for i in range(0, k + 1):
        tot += math.comb(n, i)
    p = 2 * tot / (2 ** n)
    return min(p, 1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('leek')
    ap.add_argument('opponent')
    ap.add_argument('-n', type=int, default=120)
    ap.add_argument('-j', type=int, default=8)
    ap.add_argument('--seed0', type=int, default=7000)
    ap.add_argument('--baseline', default='HEAD')
    a = ap.parse_args()

    cfg = lt.load_configs()
    leek_cfg = cfg['leeks'][a.leek]
    opp_cfg = cfg['opponents'][a.opponent]

    materialise_baseline(a.baseline)
    clear_cache()

    seeds = [a.seed0 + i for i in range(a.n)]
    jobs = ([(leek_cfg, opp_cfg, s, 'V9_modules/main.lk') for s in seeds]
            + [(leek_cfg, opp_cfg, s, 'V9_baseline/main.lk') for s in seeds])

    print('paired A/B: working tree vs %s   %s vs %s   n=%d'
          % (a.baseline, a.leek, a.opponent, a.n), flush=True)
    out = []
    with ProcessPoolExecutor(max_workers=a.j) as ex:
        for i, r in enumerate(ex.map(_one, jobs)):
            out.append(r)
            if (i + 1) % 40 == 0:
                print('  ... %d/%d' % (i + 1, len(jobs)), flush=True)

    new = {r['seed']: r for r in out[:a.n]}
    old = {r['seed']: r for r in out[a.n:]}

    errs = [s for s in seeds if new[s]['result'] == 'ERR' or old[s]['result'] == 'ERR']
    ok = [s for s in seeds if s not in errs]
    if errs:
        print('\n%d seeds errored and are excluded; first: %s'
              % (len(errs), (new[errs[0]].get('err') or old[errs[0]].get('err'))[:160]))

    nw = sum(1 for s in ok if new[s]['result'] == 'WIN')
    ow = sum(1 for s in ok if old[s]['result'] == 'WIN')
    # b = baseline won, new lost; c = new won, baseline lost
    b = [s for s in ok if old[s]['result'] == 'WIN' and new[s]['result'] != 'WIN']
    c = [s for s in ok if new[s]['result'] == 'WIN' and old[s]['result'] != 'WIN']
    p = mcnemar_p(len(b), len(c))

    print('\n=== %s vs %s   (n=%d paired) ===' % (a.leek, a.opponent, len(ok)))
    print('NEW      wins %3d / %d  = %5.1f%%' % (nw, len(ok), 100 * nw / max(len(ok), 1)))
    print('BASELINE wins %3d / %d  = %5.1f%%   (%s)'
          % (ow, len(ok), 100 * ow / max(len(ok), 1), a.baseline))
    print('\nflipped fights: %d gained by NEW, %d lost by NEW   (%d unchanged)'
          % (len(c), len(b), len(ok) - len(b) - len(c)))
    print('McNemar exact two-sided p = %.4f' % p)

    hp_new = sum(new[s]['hp'] for s in ok) / max(len(ok), 1)
    hp_old = sum(old[s]['hp'] for s in ok) / max(len(ok), 1)
    diffs = [new[s]['hp'] - old[s]['hp'] for s in ok]
    md = sum(diffs) / max(len(diffs), 1)
    if len(diffs) > 1:
        sd = math.sqrt(sum((x - md) ** 2 for x in diffs) / (len(diffs) - 1))
        t = md / (sd / math.sqrt(len(diffs))) if sd else 0.0
    else:
        sd = t = 0.0
    print('\nHP%%-lead at end: NEW %+.1f  BASELINE %+.1f   paired diff %+.1f'
          ' (sd %.1f, t=%.2f)' % (hp_new, hp_old, md, sd, t))

    if p < 0.05 and len(c) > len(b):
        print('\nVERDICT: NEW is better in this matchup (p=%.4f). Adopt.' % p)
    elif p < 0.05:
        print('\nVERDICT: NEW is WORSE in this matchup (p=%.4f). Do not adopt.' % p)
    else:
        print('\nVERDICT: not distinguishable from noise (p=%.4f).' % p)
        print('  The HP-lead diff above is the more sensitive signal; a consistent'
              ' sign there with |t| > 2 is worth a larger n before giving up.')

    if c or b:
        print('\n  seeds gained: %s' % ', '.join(str(s) for s in c[:15]))
        print('  seeds lost:   %s' % ', '.join(str(s) for s in b[:15]))


if __name__ == '__main__':
    main()
