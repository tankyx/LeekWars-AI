#!/usr/bin/env python3
"""
Per-matchup behavioural diagnostic: run N seeds of <leek> vs <opponent> and
report what each SIDE actually did - chips cast, weapons fired, damage by
source, healing, cleanses - split by whether we won or lost.

The point is to answer "why do we lose this matchup" with observed behaviour
rather than with the win/loss number alone.

Chip/weapon names come from tools/lw_decode.Decoder, which maps the generator's
`template` field. Do NOT look these ids up in item_get-all.json - that file is
keyed by a different id space and silently returns the wrong item.

    python3 tools/matchup_diag.py EdsgerDijkstra ladder_eleeksire -n 40 -j 8
"""
import argparse
import os
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import local_test as lt
from lw_decode import Decoder, parse_fight

DEC = Decoder()

# TP costs, keyed by name, from the same generator data the fight ran on.
def _costs():
    import json
    out = {}
    for f in ('chips.json', 'weapons.json'):
        try:
            data = json.load(open(os.path.join('/home/ubuntu/leek-wars-generator/data', f)))
        except OSError:
            continue
        for it in (data.values() if isinstance(data, dict) else data):
            if isinstance(it, dict) and 'name' in it:
                out[it['name']] = it.get('cost', 0)
    return out

COST = _costs()


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
        return {'error': r['error'], 'seed': seed}
    stats = parse_fight({'leeks': r['leeks'], 'actions': r['actions']}, DEC)
    return {'result': r['result'], 'seed': seed, 'turns': r['total_turns'],
            'ops': r['our_ops'], 'bug': r['has_bug'], 'stats': stats,
            'leeks': r['leeks'], 'trace': trace_chip(r, stats)}


def trace_chip(r, stats):
    """Turn numbers on which each of our entities cast each chip, plus the
    poison damage we took on each turn. Lets a cast gap be compared against the
    chip's cooldown."""
    ours = {k for k, e in stats.items() if k != '_meta' and e.get('team') == 1}
    turn, cur = 0, None
    casts, poison = [], {}
    for a in r['actions']:
        if not isinstance(a, list) or not a:
            continue
        if a[0] == 6:
            turn += 1
        elif a[0] == 7:
            cur = a[1] if len(a) > 1 else None
        elif a[0] == 12 and len(a) > 2 and cur in ours:
            casts.append((turn, DEC.chip(a[1])))
        elif a[0] == 110 and len(a) > 2 and a[1] in ours:
            poison[turn] = poison.get(turn, 0) + a[2]
    return {'casts': casts, 'poison': poison}


def fold(runs, side_team):
    """Sum per-entity stats across runs for one team."""
    acc = {'chips': defaultdict(int), 'weapons': defaultdict(int),
           'tp_chip': 0, 'tp_weapon': 0,
           'taken': defaultdict(int), 'dealt': defaultdict(int),
           'healed': 0, 'cleansed': 0, 'crits': 0, 'moves': 0, 'turns': 0,
           'deaths': 0, 'n': 0}
    for run in runs:
        acc['n'] += 1
        for k, e in run['stats'].items():
            if k == '_meta' or e.get('team') != side_team:
                continue
            for c, v in e['chips'].items():
                acc['chips'][c] += v
                acc['tp_chip'] += COST.get(c, 0) * v
            for w, v in e['weapons'].items():
                acc['weapons'][w] += v
                acc['tp_weapon'] += COST.get(w, 0) * v
            for t, v in e['taken'].items():
                acc['taken'][t] += v
            for t, v in e['dealt'].items():
                acc['dealt'][t] += v
            acc['healed'] += e['healed']
            acc['cleansed'] += e['poisons_cleansed']
            acc['crits'] += e['crits']
            acc['moves'] += e['moves']
            acc['turns'] += e['turns']
            acc['deaths'] += 1 if e['died'] else 0
    return acc


def show(label, acc):
    n = max(acc['n'], 1)
    print('  %-6s  n=%-3d turns/fight %.1f  deaths %d' %
          (label, acc['n'], acc['turns'] / n, acc['deaths']))
    tk = acc['taken']
    print('     damage taken/fight: %6.0f  (direct %.0f poison %.0f nova %.0f return %.0f life %.0f)'
          % (sum(tk.values()) / n, tk['direct'] / n, tk['poison'] / n,
             tk['nova'] / n, tk['return'] / n, tk['life'] / n))
    print('     healed/fight: %6.0f   heal:damage ratio %.2f   cleanses %.2f/fight'
          % (acc['healed'] / n,
             acc['healed'] / max(sum(tk.values()), 1),
             acc['cleansed'] / n))
    t = max(acc['turns'], 1)
    print('     TP/turn: %.1f on chips + %.1f on weapons = %.1f   weapon uses/turn %.2f'
          % (acc['tp_chip'] / t, acc['tp_weapon'] / t,
             (acc['tp_chip'] + acc['tp_weapon']) / t,
             sum(acc['weapons'].values()) / t))
    print('     damage dealt/turn: %.0f   moves/turn %.2f'
          % (sum(acc['dealt'].values()) / t, acc['moves'] / t))
    top = sorted(acc['chips'].items(), key=lambda x: -x[1])[:8]
    print('     chips/turn: ' + ', '.join('%s %.2f(%dtp)' % (k, v / t, COST.get(k, 0))
                                          for k, v in top))
    topw = sorted(acc['weapons'].items(), key=lambda x: -x[1])[:5]
    print('     weapons/turn: ' + ', '.join('%s %.2f(%dtp)' % (k, v / t, COST.get(k, 0))
                                            for k, v in topw))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('leek')
    ap.add_argument('opponent')
    ap.add_argument('-n', type=int, default=40)
    ap.add_argument('-j', type=int, default=8)
    ap.add_argument('--seed0', type=int, default=7000)
    ap.add_argument('--ai', default='V9_modules/main.lk')
    ap.add_argument('--trace-chip', default=None,
                    help='report the turn numbers on which our side casts this chip, '
                         'so cooldown-limited can be told apart from under-valued')
    a = ap.parse_args()

    cfg = lt.load_configs()
    leek_cfg = cfg['leeks'][a.leek]
    opp_cfg = cfg['opponents'][a.opponent]

    jobs = [(leek_cfg, opp_cfg, a.seed0 + i, a.ai) for i in range(a.n)]
    runs = []
    with ProcessPoolExecutor(max_workers=a.j) as ex:
        for i, r in enumerate(ex.map(_one, jobs)):
            runs.append(r)
            if (i + 1) % 10 == 0:
                print('  ... %d/%d' % (i + 1, a.n), flush=True)

    errs = [r for r in runs if r.get('error')]
    ok = [r for r in runs if not r.get('error')]
    wins = [r for r in ok if r['result'] == 'WIN']
    losses = [r for r in ok if r['result'] == 'LOSS']
    draws = [r for r in ok if r['result'] == 'DRAW']
    bugs = [r for r in ok if r['bug']]

    print('\n=== %s vs %s (%s) ===' % (a.leek, a.opponent, a.ai))
    print('%dW %dL %dD   errors %d  AI-crashes %d' %
          (len(wins), len(losses), len(draws), len(errs), len(bugs)))
    if errs:
        print('  first error: %s' % errs[0]['error'][:200])

    if a.trace_chip:
        print('\n--- cast trace for %r (our side) ---' % a.trace_chip)
        gaps, poisoned_idle = [], 0
        for r in ok:
            t = r['trace']
            ts = [tn for tn, c in t['casts'] if c == a.trace_chip]
            gaps += [b - x for x, b in zip(ts, ts[1:])]
            # turns where we were taking poison and the chip was (by cooldown)
            # castable but was not cast
            last = -99
            for tn in sorted(t['poison']):
                if tn in ts:
                    last = tn
                elif tn - last > 4 and any(x <= tn for x in ts + [0]):
                    poisoned_idle += 1
                    last = max(last, tn - 4)
            for x in ts:
                last = max(last, x)
        import statistics as st
        print('  casts: %d over %d fights (%.2f/fight, %.3f/turn)' %
              (sum(len([1 for tn, c in r['trace']['casts'] if c == a.trace_chip]) for r in ok),
               len(ok),
               sum(len([1 for tn, c in r['trace']['casts'] if c == a.trace_chip]) for r in ok) / max(len(ok), 1),
               sum(len([1 for tn, c in r['trace']['casts'] if c == a.trace_chip]) for r in ok) /
               max(sum(r['turns'] for r in ok), 1)))
        if gaps:
            print('  gap between consecutive casts: median %.1f turns, min %d, max %d' %
                  (st.median(gaps), min(gaps), max(gaps)))
            print('  (compare to the chip cooldown: a median gap at the cooldown means '
                  'cooldown-limited; a larger gap means the scorer is under-valuing it)')
        else:
            print('  never cast twice in one fight -> not cooldown-limited')
        print('  turns spent taking poison with the chip off cooldown and unused: %d' % poisoned_idle)

    for bucket, name in ((wins, 'WINS'), (losses, 'LOSSES')):
        if not bucket:
            continue
        print('\n--- %s (%d fights) ---' % (name, len(bucket)))
        show('US', fold(bucket, 1))
        show('THEM', fold(bucket, 2))


if __name__ == '__main__':
    main()
