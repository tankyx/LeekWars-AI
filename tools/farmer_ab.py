#!/usr/bin/env python3
"""Interleaved A/B of two AI paths in garden farmer fights (4 v 4) on the main account.
Fight i uses arm A if i is even, B if odd; before each fight all four leeks are switched to that
arm's AI path; each fight is finished before the next switch (the AI is read at generation).
The opponent is a random pick among the garden's farmer opponents (same rule for both arms).
Leeks go back to --restore at the end, whatever happens.

    python3 tools/farmer_ab.py --a 10.0/V10/v10_team.py --b 10.0/V10/v10.py --n 40
"""
import argparse, json, random, sys, time, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lw_api import LWSession
LEEKS = [20443, 129288, 129295, 129296]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--a', required=True); ap.add_argument('--b', required=True)
    ap.add_argument('--n', type=int, default=40); ap.add_argument('--restore', default='10.0/V10/v10.py')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--batch', type=int, default=0,
                    help='fights per block: switch the AI, queue the block at --rate, wait for all of it; blocks run ABBA')
    ap.add_argument('--rate', type=float, default=9.0)
    ap.add_argument('--log', default=None, help='JSON lines: arm, fight id, opponent, result')
    a = ap.parse_args()
    lw = LWSession('main'); rng = random.Random(a.seed)
    res = {'A': [], 'B': []}
    if a.batch > 0:
        return run_batched(a, lw, rng, res)
    try:
        for i in range(a.n):
            arm = 'A' if i % 2 == 0 else 'B'; path = a.a if arm == 'A' else a.b
            for lid in LEEKS:
                lw.post('/leek/set-ai', leek_id=lid, ai_path=path)
            opps = (lw.get('/garden/get-farmer-opponents') or {}).get('opponents') or []
            if not opps:
                print('no opponents'); break
            o = rng.choice(opps)
            r = lw.post('/garden/start-farmer-fight', target_id=o['id'])
            fid = r if isinstance(r, int) else (r.get('fight') if isinstance(r, dict) else None)
            if not fid:
                print('start failed', r); break
            g = {}
            for _ in range(120):
                time.sleep(2)
                g = lw.get('/fight/get/%d' % fid); g = g.get('fight', g)
                if g.get('status') == 2:
                    break
            ours = 1 if any(str(f) == str(lw.farmer['id']) for f in (g.get('farmers1') or {})) else 2
            w = g.get('winner'); out = 1.0 if w == ours else (0.5 if w == 0 else 0.0)
            res[arm].append(out)
            print('%2d %s vs %-20s (talent %s) -> %s  turns %s' % (i, arm, o['name'], o.get('talent'), {1.0: 'WIN', 0.5: 'draw', 0.0: 'loss'}[out],
                                                                (g.get('report') or {}).get('duration')), flush=True)
    finally:
        for lid in LEEKS:
            lw.post('/leek/set-ai', leek_id=lid, ai_path=a.restore)
        print('leeks back on', a.restore)
    for arm in ('A', 'B'):
        v = res[arm]
        print('%s %s: %.1f / %d' % (arm, a.a if arm == 'A' else a.b, sum(v), len(v)))


def outcome(lw, g):
    ours = 1 if any(str(f) == str(lw.farmer['id']) for f in (g.get('farmers1') or {})) else 2
    w = g.get('winner')
    return 1.0 if w == ours else (0.5 if w == 0 else 0.0)


def run_batched(a, lw, rng, res):
    logf = open(a.log, 'a') if a.log else None
    t0 = time.time(); done = 0; blk = 0
    try:
        while done < a.n:
            arm = 'ABBA'[blk % 4]; path = a.a if arm == 'A' else a.b; blk += 1
            for lid in LEEKS:
                lw.post('/leek/set-ai', leek_id=lid, ai_path=path)
            k = min(a.batch, a.n - done); pend = {}
            for _ in range(k):
                opps = (lw.get('/garden/get-farmer-opponents') or {}).get('opponents') or []
                if not opps:
                    break
                o = rng.choice(opps)
                r = lw.post('/garden/start-farmer-fight', target_id=o['id'])
                fid = r if isinstance(r, int) else (r.get('fight') if isinstance(r, dict) else None)
                if fid:
                    pend[fid] = o
                else:
                    print('start failed', r, flush=True)
                time.sleep(1.0 / a.rate)
            if not pend:
                print('nothing started, stopping', flush=True); break
            for _ in range(600):
                if not pend:
                    break
                time.sleep(3)
                for fid in list(pend):
                    g = lw.get('/fight/get/%d' % fid); g = g.get('fight', g)
                    if g.get('status') == 2:
                        o = pend.pop(fid); out = outcome(lw, g); res[arm].append(out); done += 1
                        if logf:
                            logf.write(json.dumps({'arm': arm, 'path': path, 'fight': fid, 'opp': o.get('name'),
                                                   'opp_talent': o.get('talent'), 'result': out}) + '\n'); logf.flush()
            for fid in pend:     # never finished: dropped from the tally
                print('fight %s never finished' % fid, flush=True)
            sa, sb = res['A'], res['B']
            print('block %d %s: A %.1f/%d  B %.1f/%d  (%d s)' % (blk, arm, sum(sa), len(sa), sum(sb), len(sb), time.time() - t0), flush=True)
    finally:
        for lid in LEEKS:
            lw.post('/leek/set-ai', leek_id=lid, ai_path=a.restore)
        print('leeks back on', a.restore)
    for arm in ('A', 'B'):
        v = res[arm]
        print('%s %s: %.1f / %d = %.1f%%' % (arm, a.a if arm == 'A' else a.b, sum(v), len(v), 100.0 * sum(v) / max(1, len(v))))


if __name__ == '__main__':
    main()
