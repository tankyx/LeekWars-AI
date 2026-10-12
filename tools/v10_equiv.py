#!/usr/bin/env python3
"""Behaviour-equivalence check for V10 refactors.

Both builds get an UNLIMITED internal budget (OPS_STOP huge, so every turn runs the whole
search) and the engine a 500M-operation turn limit, then play the same seeded local fights.
Every action of every fight must be identical; the operations each build used for those
identical decisions measure the speed-up.

    python3 tools/v10_equiv.py OLD.py NEW.py [--leeks A,B] [--opps x,y] [--seeds 2] [-j 4]
"""
import argparse, copy, itertools, json, os, re, sys
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import local_test as lt

# the local polyglot runtime cuts a Python turn after 5 s of wall clock (like prod): with an unlimited
# budget and parallel fights a heavy turn can cross it on one run and not the other -> lift it here
os.environ['JAVA_TOOL_OPTIONS'] = (os.environ.get('JAVA_TOOL_OPTIONS', '') + ' -Dlw.polyglot.turnWallClockMs=600000').strip()

UNLIMITED = 'OPS_STOP = 10 ** 15  # v10_equiv: unlimited budget\n'


def unlimited_copy(src, tag):
    code = open(src).read()
    new, n = re.subn(r'^(\s*)OPS_STOP = int\(System\.maxOperations \* frac\)\n',
                     lambda m: m.group(1) + UNLIMITED, code, flags=re.M)
    new, n2 = re.subn(r'^(\s*)OPS_STOP = int\(14000000 \* frac\)\n', lambda m: m.group(1) + UNLIMITED, new, flags=re.M)
    assert n == 1 and n2 == 1, 'budget lines not found in %s' % src
    os.makedirs(os.path.join(ROOT, 'V10', 'ab'), exist_ok=True)
    out = os.path.join(ROOT, 'V10', 'ab', 'equiv_%s.py' % tag)
    open(out, 'w').write(new)
    return os.path.relpath(out, ROOT)


def one(job):
    ai, leek, opp, seed = job
    cfgs = lt.load_configs()
    lc = copy.deepcopy(cfgs['leeks'][leek]); lc['cores'] = 500
    oc = copy.deepcopy(cfgs['opponents'][opp])
    sc = lt.build_scenario(lc, oc, seed=seed)
    sc['entities'][0][0]['ai'] = ai            # same form as local_test --ai (repo-relative)
    r = lt.run_fight(sc, 0, False)
    acts = r.get('actions') if isinstance(r, dict) else None
    ops = r.get('ops') if isinstance(r, dict) else None
    return job, json.dumps(acts, sort_keys=True) if acts is not None else None, ops, r.get('error') if isinstance(r, dict) else 'no result'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('old'); ap.add_argument('new')
    ap.add_argument('--leeks', default='EdsgerDijkstra,MargaretHamilton,KurtGodel')
    ap.add_argument('--opps', default='clone_topac,prod_feeddageek')
    ap.add_argument('--seeds', type=int, default=2); ap.add_argument('-j', type=int, default=4)
    a = ap.parse_args()
    A = unlimited_copy(a.old, 'old'); B = unlimited_copy(a.new, 'new')
    combos = list(itertools.product(a.leeks.split(','), a.opps.split(','), range(1, a.seeds + 1)))
    jobs = [(ai, l, o, 100 + s) for (l, o, s) in combos for ai in (A, B)]
    res = {}
    with ProcessPoolExecutor(a.j) as ex:
        for job, acts, ops, err in ex.map(one, jobs):
            res[job] = (acts, ops, err)
    same = diff = bad = 0; ops_a = ops_b = 0
    for l, o, s in combos:
        ra = res[(A, l, o, 100 + s)]; rb = res[(B, l, o, 100 + s)]
        if ra[0] is None or rb[0] is None:
            bad += 1; print('ERROR %s vs %s seed %d: %s / %s' % (l, o, s, ra[2], rb[2])); continue
        if ra[0] == rb[0]:
            same += 1
            # our entity only (local_test: entity "0"); the opponent's ops would dilute the comparison
            oa = (ra[1] or {}).get('0', 0) if isinstance(ra[1], dict) else (ra[1] or 0)
            ob = (rb[1] or {}).get('0', 0) if isinstance(rb[1], dict) else (rb[1] or 0)
            ops_a += oa; ops_b += ob
            print('same  %-17s vs %-16s seed %d  ops %s -> %s' % (l, o, s, oa, ob))
        else:
            diff += 1; print('DIFF  %-17s vs %-16s seed %d' % (l, o, s))
    print('identical %d / %d fights (%d errors)%s' % (same, same + diff, bad,
          '' if not ops_a else ' | ops on identical fights %d -> %d (%.1f%%)' % (ops_a, ops_b, 100.0 * (ops_b - ops_a) / ops_a)))
    sys.exit(0 if diff == 0 and bad == 0 else 1)


if __name__ == '__main__':
    main()
