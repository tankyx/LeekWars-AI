#!/usr/bin/env python3
"""Run N Fennel (or other) boss fights over REST and report each one:
winner, graal death turn, crystal revives (action 105) by turn, our deaths,
damage to the army. Fight JSON saved to data/boss_fights/ours_<id>.json.

    python3 tools/boss_run.py 12 [--boss 2]
"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession
# Participant order = spawn slot: slot 1 -> cell 228 (next to the king's spawn, 170), slot 2 -> 491,
# slot 3 -> 563, slot 4 -> 588 (back pocket). Margaret (RES 12) spawned at 228 and took ~790 from the
# king on turn 2 on average (died turns 4-5 in 23/49 fights): the tank takes slot 1, Margaret the pocket.
LEEKS = [129295, 20443, 129288, 129296]
OURS = {129295: 'Kur', 20443: 'Ada', 129296: 'Mar', 129288: 'Eds'}


def analyze(f):
    d = f['data']
    names = {l['id']: l['name'] for l in d['leeks']}
    team = {l['id']: l['team'] for l in d['leeks']}
    rnd = 1; graal = None; revives = []; dead = []; dmg = 0; cur = None
    for a in d['actions']:
        if a[0] == 6:
            rnd = a[1]
        elif a[0] == 7:
            cur = a[1]
        elif a[0] == 105:
            revives.append('T%d %s' % (rnd, names.get(a[2], '?').split('_')[0]))
        elif a[0] == 5:
            n = names.get(a[1], '')
            if n == 'graal':
                graal = rnd
            elif team.get(a[1]) == 1 and n in ('KurtGodel', 'AdaLovelace', 'MargaretHamilton', 'EdsgerDijkstra'):
                dead.append('T%d %s' % (rnd, n[:3]))
        elif a[0] == 101 and team.get(a[1]) == 2 and 'crystal' not in names.get(a[1], ''):
            dmg += a[2]
    return graal, revives, dead, dmg, rnd


def run_queued(lw, a, out):
    gap = 1.0 / a.rate; last = [0.0]

    def call(fn, *x, **k):
        w = last[0] + gap - time.time()
        if w > 0:
            time.sleep(w)
        last[0] = time.time()
        return fn(*x, **k)
    pending = []; started = 0; wins = 0; graals = 0; done = 0; t0 = time.time(); refused = 0
    while started < a.n or pending:
        if started < a.n:
            r = call(lw.post, '/garden/start-boss-fight', boss_id=a.boss, participants=json.dumps(LEEKS))
            fid = r.get('fight') if isinstance(r, dict) else None
            if fid:
                pending.append(fid); started += 1; refused = 0
                continue
            refused += 1
            if 'not_enough' in str(r) or refused > 30:
                print('start refused (%s): stopping at %d started' % (str(r)[:80], started), flush=True)
                a.n = started
            else:
                time.sleep(2)
        for fid in list(pending)[:20]:
            g = call(lw.get, '/fight/get/%d' % fid); g = g.get('fight', g) if isinstance(g, dict) else {}
            if g.get('status') != 2:
                continue
            pending.remove(fid); done += 1
            json.dump(g, open(os.path.join(out, 'ours_%d.json' % fid), 'w'))
            graal, rev, dead, dmg, turns = analyze(g)
            win = g.get('winner') == 1; wins += win; graals += graal is not None
            print('%d: %s turns %d | graal %s | army dmg %d   [%d done, %d queued, %.0f s]' % (
                fid, 'WIN ' if win else 'loss', turns, ('T%d' % graal) if graal else '-', dmg, done, len(pending), time.time() - t0), flush=True)
        if not pending and started >= a.n:
            break
    print('== %d/%d wins, %d graal deaths (%.0f s)' % (wins, done, graals, time.time() - t0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('n', type=int)
    ap.add_argument('--boss', type=int, default=2)
    ap.add_argument('--queue', action='store_true', help='start fights at --rate requests/s and let the server queue them')
    ap.add_argument('--rate', type=float, default=9.0)
    a = ap.parse_args()
    lw = LWSession('main')
    out = os.path.join(ROOT, 'data', 'boss_fights')
    if a.queue:
        return run_queued(lw, a, out)
    wins = 0; graals = 0
    for i in range(a.n):
        r = lw.post('/garden/start-boss-fight', boss_id=a.boss, participants=json.dumps(LEEKS))
        fid = r.get('fight') if isinstance(r, dict) else None
        if not fid:
            print('start failed:', r, flush=True); break
        f = None
        for _ in range(120):
            time.sleep(2)
            g = lw.get('/fight/get/%d' % fid); g = g.get('fight', g)
            if g.get('status') == 2:
                f = g; break
        if f is None:
            print('%d: not finished' % fid, flush=True); continue
        json.dump(f, open(os.path.join(out, 'ours_%d.json' % fid), 'w'))
        graal, rev, dead, dmg, turns = analyze(f)
        win = f.get('winner') == 1
        wins += win; graals += graal is not None
        print('%d: %s turns %d | graal %s | revives %s | our deaths %s | army dmg %d' % (
            fid, 'WIN ' if win else 'loss', turns, ('T%d' % graal) if graal else '-', rev, dead, dmg), flush=True)
    print('== %d/%d wins, %d graal deaths' % (wins, a.n, graals))


if __name__ == '__main__':
    main()
