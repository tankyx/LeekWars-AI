#!/usr/bin/env python3
"""
Head-to-head A/B: run the WORKING-TREE V9 against a BASELINE V9 (a git ref),
same leek on both sides, and report whether the change actually plays better.

Why this exists: neither existing measurement can detect an improvement.
  * local_test.py vs the smart_* bots is saturated at 100% - no headroom.
  * the ladder self-corrects to ~50% as talent rises, so a better AI climbs
    talent and returns to 50%.
A mirror match has no such ceiling: both sides are the same leek with the same
stats and kit, so the ONLY difference is the AI code.

How it works: checks the baseline ref out into V9_baseline/ (git archive, so
the working tree is never touched), symlinks it into the generator, then runs N
fights alternating which side starts - first-move advantage is real and would
otherwise bias the result.

Result reporting is deliberately conservative: a 2-sided binomial test on
decisive games, because at N=40 a 55% score is indistinguishable from noise and
acting on it would be worse than not measuring at all.

LIMITATION - per-opponent memory. Code paths gated on ENEMY_MODEL cannot be
measured here. rolloutRerank early-returns (gap 0, same pick) unless the target
is one of the ~397 known ladder opponents in enemy_model_data_iso.lk, and
neither the smart_* bots nor our own leeks are in it - so a mirror A/B of that
feature returns ~50% and looks like "no effect" when it simply never ran. The
LEARNED re-rank has no such gate (by design) and is measurable. Check for a
confidence gate before trusting a null result from this harness.

Calibration (identical code both sides, MargaretHamilton, n=40): 20-20, p=1.000
with draw-breaking; 12-15 (p=0.701) with --strict-draws. The harness is
unbiased. Detection power, roughly: 40 decisive games catches ~68%+ win rates,
100 catches ~62%, 250 catches ~57%. Subtle tuning needs the larger runs.

Usage:
  python3 tools/mirror_ab.py --leek MargaretHamilton -n 40
  python3 tools/mirror_ab.py --leek KurtGodel -n 60 --baseline HEAD~1
  python3 tools/mirror_ab.py --leek AdaLovelace -n 150 --strict-draws
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import local_test as lt  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE_DIR = os.path.join(REPO, 'V9_baseline')
GEN_LINK = os.path.join(str(lt.GENERATOR_DIR), 'V9_baseline')


def materialise_baseline(ref):
    """Export V9_modules at `ref` into V9_baseline/ and link it for the generator."""
    if os.path.islink(BASELINE_DIR) or os.path.isfile(BASELINE_DIR):
        os.remove(BASELINE_DIR)
    shutil.rmtree(BASELINE_DIR, ignore_errors=True)
    os.makedirs(BASELINE_DIR, exist_ok=True)
    # git archive keeps the working tree untouched (a checkout would not)
    tar = subprocess.run(['git', 'archive', ref, 'V9_modules'],
                         cwd=REPO, capture_output=True)
    if tar.returncode != 0:
        sys.exit(f'git archive {ref} failed: {tar.stderr.decode()[:200]}')
    with tempfile.NamedTemporaryFile(suffix='.tar', delete=False) as f:
        f.write(tar.stdout)
        tarpath = f.name
    subprocess.run(['tar', 'xf', tarpath, '-C', BASELINE_DIR, '--strip-components=1'], check=True)
    os.remove(tarpath)
    if os.path.islink(GEN_LINK):
        os.remove(GEN_LINK)
    if not os.path.exists(GEN_LINK):
        os.symlink(BASELINE_DIR, GEN_LINK)
    return BASELINE_DIR


def clear_cache():
    for pat in ('*.class', '*.java', '*.lines', '*.sig'):
        for f in __import__('glob').glob(str(lt.GENERATOR_DIR / 'ai' / pat)):
            try:
                os.remove(f)
            except OSError:
                pass


def one_fight(args):
    leek_cfg, seed, new_first, break_draws = args
    # mirror: identical leek on both sides, only the AI path differs
    a_ai = 'V9_modules/main.lk' if new_first else 'V9_baseline/main.lk'
    b_ai = 'V9_baseline/main.lk' if new_first else 'V9_modules/main.lk'
    scn = lt.build_scenario(leek_cfg, leek_cfg, seed=seed, opponent_ai=b_ai)
    for e in scn['entities'][0]:
        e['ai'] = a_ai
    path = None
    try:
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, dir='/tmp') as f:
            json.dump(scn, f)
            path = f.name
        cp = open(str(lt.GENERATOR_DIR / 'runtime_classpath.txt')).read().strip()
        env = dict(os.environ, JAVA_HOME=lt.JAVA_HOME)
        r = subprocess.run([os.path.join(lt.JAVA_HOME, 'bin', 'java'), '-cp', cp,
                            'com.leekwars.Main', path],
                           capture_output=True, text=True, timeout=300,
                           cwd=str(lt.GENERATOR_DIR), env=env)
        out = r.stdout
        i = out.find('{"')
        if i < 0:
            return None
        d = json.loads(out[i:], strict=False)
        w = d.get('winner')
        if w in (1, 2):
            # winner 1 = team1 = a_ai side
            return 'W' if (w == 1) == new_first else 'L'
        # Draw. Mirror matches stalemate ~1/3 of the time, which throws away a
        # third of the sample. Break it on remaining HP: the side that came out
        # further ahead played better, which is exactly what we are measuring.
        if not break_draws:
            return 'D'
        fight = d.get('fight', d)
        init = {l['id']: l.get('life', 0) for l in fight.get('leeks', [])}
        team = {l['id']: l.get('team') for l in fight.get('leeks', [])}
        lost = {k: 0 for k in init}
        for a in fight.get('actions', []):
            if isinstance(a, list) and a and a[0] == 101 and len(a) > 2 and a[1] in lost:
                lost[a[1]] += a[2]
        hp = {1: 0, 2: 0}
        for eid, v in init.items():
            t = team.get(eid)
            if t in hp:
                hp[t] += max(0, v - lost.get(eid, 0))
        if hp[1] == hp[2]:
            return 'D'
        t1_ahead = hp[1] > hp[2]
        return 'W' if t1_ahead == new_first else 'L'
    except Exception:
        return None
    finally:
        if path and os.path.exists(path):
            os.remove(path)


def binom_p(k, n):
    """2-sided exact binomial p-value against a fair coin."""
    if n == 0:
        return 1.0
    from math import comb
    def tail(x):
        return sum(comb(n, i) for i in range(x + 1)) / (2 ** n)
    lo = min(k, n - k)
    return min(1.0, 2 * tail(lo))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--leek', default='MargaretHamilton')
    ap.add_argument('-n', '--fights', type=int, default=40)
    ap.add_argument('--baseline', default='HEAD', help='git ref for the baseline AI (default HEAD)')
    ap.add_argument('--seed', type=int, default=1000)
    ap.add_argument('--parallel', type=int, default=3)
    ap.add_argument('--strict-draws', action='store_true',
                    help='count stalemates as draws instead of breaking them on '
                         'remaining HP (loses ~1/3 of the sample)')
    args = ap.parse_args()

    cfg = lt.load_configs()
    if args.leek not in cfg['leeks']:
        sys.exit(f'unknown leek {args.leek}; have {sorted(cfg["leeks"])}')
    leek_cfg = cfg['leeks'][args.leek]

    materialise_baseline(args.baseline)
    clear_cache()
    print(f'mirror A/B: working tree vs {args.baseline}  leek={args.leek}  n={args.fights}')
    print('(sides alternate each fight to cancel first-move advantage)\n')

    jobs = [(leek_cfg, args.seed + i, i % 2 == 0, not args.strict_draws) for i in range(args.fights)]
    res = []
    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        for i, r in enumerate(ex.map(one_fight, jobs), 1):
            res.append(r)
            if i % 10 == 0:
                w = res.count('W'); l = res.count('L')
                print(f'  {i}/{args.fights}  new {w} - {l} baseline', flush=True)

    w, l, d = res.count('W'), res.count('L'), res.count('D')
    err = res.count(None)
    dec = w + l
    print(f'\nNEW (working tree): {w}   BASELINE ({args.baseline}): {l}   draws: {d}   errors: {err}')
    if dec == 0:
        print('no decisive games - inconclusive')
        return
    rate = 100.0 * w / dec
    p = binom_p(w, dec)
    print(f'decisive: {dec}, new wins {rate:.1f}%   2-sided binomial p = {p:.3f}')
    if p >= 0.05:
        print('VERDICT: not distinguishable from noise - do NOT adopt on this evidence.')
        need = 0
        for nn in range(dec, 1000):
            if binom_p(round(nn * max(rate, 100 - rate) / 100), nn) < 0.05:
                need = nn
                break
        if need:
            print(f'         at this win rate you would need ~{need} decisive games to call it.')
    elif w > l:
        print('VERDICT: the working tree is genuinely better (p < 0.05).')
    else:
        print('VERDICT: the working tree is genuinely WORSE (p < 0.05) - revert.')


if __name__ == '__main__':
    main()
