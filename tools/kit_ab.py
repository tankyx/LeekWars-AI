#!/usr/bin/env python3
"""
Paired A/B of two LEEK CONFIGS (same AI, same opponent, same seeds).

matchup_ab.py compares two AI trees on one config; this compares two configs
on one AI -- the tool for kit / stat / weapon changes, which are config-only
and never touch V9_modules. Both configs must exist in tools/leek_configs.json.
Verdict is McNemar on flipped fights, HP-lead as the continuous signal.

    python3 tools/kit_ab.py KurtGodel KurtGodel_KIT ladder_eleeksire -n 60 -j 8
"""
import argparse, math, os, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import local_test as lt
from matchup_ab import hp_lead, mcnemar_p

def _one(args):
    leek_cfg, opp_cfg, seed, ai = args
    lt.AI_PATH = ai
    scn = lt.build_scenario(leek_cfg, opp_cfg, seed=seed)
    for team in scn['entities']:
        for e in team:
            if e['team'] == 1: e['ai'] = ai
    r = lt.run_fight(scn)
    if r.get('error'):
        return {'seed': seed, 'result': 'ERR', 'hp': 0, 'err': r['error']}
    return {'seed': seed, 'result': r['result'], 'hp': hp_lead(r)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('base'); ap.add_argument('variant'); ap.add_argument('opponent')
    ap.add_argument('-n', type=int, default=60); ap.add_argument('-j', type=int, default=8)
    ap.add_argument('--seed0', type=int, default=7000)
    ap.add_argument('--ai', default='V9_modules/main.lk')
    a = ap.parse_args()
    cfg = lt.load_configs()
    A, B, O = cfg['leeks'][a.base], cfg['leeks'][a.variant], cfg['opponents'][a.opponent]
    seeds = [a.seed0 + i for i in range(a.n)]
    jobs = [(A, O, s, a.ai) for s in seeds] + [(B, O, s, a.ai) for s in seeds]
    out = []
    with ProcessPoolExecutor(max_workers=a.j) as ex:
        for r in ex.map(_one, jobs): out.append(r)
    base = {r['seed']: r for r in out[:a.n]}; var = {r['seed']: r for r in out[a.n:]}
    ok = [s for s in seeds if base[s]['result'] != 'ERR' and var[s]['result'] != 'ERR']
    bw = sum(1 for s in ok if base[s]['result'] == 'WIN'); vw = sum(1 for s in ok if var[s]['result'] == 'WIN')
    lost = [s for s in ok if base[s]['result'] == 'WIN' and var[s]['result'] != 'WIN']
    gained = [s for s in ok if var[s]['result'] == 'WIN' and base[s]['result'] != 'WIN']
    p = mcnemar_p(len(lost), len(gained))
    diffs = [var[s]['hp'] - base[s]['hp'] for s in ok]
    md = sum(diffs) / max(len(diffs), 1)
    sd = math.sqrt(sum((x - md) ** 2 for x in diffs) / max(len(diffs) - 1, 1)) if len(diffs) > 1 else 0
    t = md / (sd / math.sqrt(len(diffs))) if sd else 0
    print('=== %s -> %s   vs %s   (n=%d paired) ===' % (a.base, a.variant, a.opponent, len(ok)))
    print('BASE    wins %3d/%d = %5.1f%%' % (bw, len(ok), 100 * bw / max(len(ok), 1)))
    print('VARIANT wins %3d/%d = %5.1f%%' % (vw, len(ok), 100 * vw / max(len(ok), 1)))
    print('flipped: %d gained, %d lost   McNemar p = %.4f' % (len(gained), len(lost), p))
    print('HP-lead diff %+.1f (sd %.1f, t=%.2f)' % (md, sd, t))
    v = 'VARIANT BETTER' if (p < 0.05 and len(gained) > len(lost)) else ('VARIANT WORSE' if p < 0.05 else 'not distinguishable from noise')
    print('VERDICT: %s' % v)

if __name__ == '__main__':
    main()
