#!/usr/bin/env python3
"""Ladder A/B of two server AI paths with real garden fights (talent moves): blocks of
fights alternate between the arms (A B B A A B B A ...), every leek on the block's AI.

    python3 tools/ladder_ab.py --a 10.0/V10/v10.py --b 10.0/V10/v10_test.py --blocks 10 --per-leek 12 \
        --out data/ladder/ladder_ab.jsonl

Each block: set the AI on the four main leeks, play --per-leek fights per leek through
tools/garden_fast.py (smart selector), then read the new fights back (result, talent gain,
opponent talent) and append one JSON line per fight with its arm. The leeks always go back
to arm A's AI at the end. Guard: stops when arm B trails arm A by --stop-gap talent in total
(after 96 fights per arm).
"""
import argparse, json, os, sqlite3, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession
LEEKS = {20443: 'Kirby54', 129288: 'GTGabi', 129295: 'Zoulman', 129296: 'Payou'}


def set_ai(lw, path):
    for lid in LEEKS:
        for _ in range(5):
            lw.s.post('https://leekwars.com/api/leek/set-ai', data={'leek_id': lid, 'ai_path': path}, timeout=30)
            l = lw.leek(lid)
            if (l.get('ai') or {}).get('path') == path:
                break
            time.sleep(2)
        else:
            raise RuntimeError('could not set %s on %d' % (path, lid))


def last_id(lid):
    db = sqlite3.connect(os.path.join(HERE, 'fight_history_%d.db' % lid))
    return db.execute('select coalesce(max(fight_id), 0) from fight_history').fetchone()[0]


def new_fights(lid, since):
    db = sqlite3.connect(os.path.join(HERE, 'fight_history_%d.db' % lid))
    return [r[0] for r in db.execute('select fight_id from fight_history where fight_id > ? order by fight_id', (since,))]


def fight_row(lw, fid, lid):
    for _ in range(20):
        f = lw.get('/fight/get/%d' % fid); f = f.get('fight', f) if isinstance(f, dict) else {}
        if f.get('status') == 2 and f.get('report'):
            side = 1 if any(l['id'] == lid for l in f.get('leeks1') or []) else 2
            rep = f['report']; me = next(l for l in rep['leeks%d' % side] if l['id'] == lid); op = rep['leeks%d' % (3 - side)][0]
            return {'fight': fid, 'leek': lid, 'res': 1.0 if f['winner'] == side else (0.5 if f['winner'] == 0 else 0.0),
                    'gain': me.get('talent_gain'), 'talent': me.get('talent'), 'opp': op.get('id'), 'opp_talent': op.get('talent'),
                    'rounds': rep.get('duration')}
        time.sleep(3)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--a', required=True); ap.add_argument('--b', required=True)
    ap.add_argument('--blocks', type=int, default=10); ap.add_argument('--per-leek', type=int, default=12)
    ap.add_argument('--out', required=True); ap.add_argument('--stop-gap', type=float, default=200.0)
    a = ap.parse_args()
    lw = LWSession('main')
    tot = {'A': [0, 0.0, 0.0], 'B': [0, 0.0, 0.0]}      # fights, wins, talent gain
    try:
        for i in range(a.blocks):
            arm = 'AB'[(i + 1) // 2 % 2]                 # A B B A A B B A ...
            path = a.a if arm == 'A' else a.b
            set_ai(lw, path)
            since = {lid: last_id(lid) for lid in LEEKS}
            r = subprocess.run([sys.executable, os.path.join(HERE, 'garden_fast.py'), '--per-leek', str(a.per_leek)],
                               capture_output=True, text=True, cwd=ROOT, timeout=3600)
            tail = [l for l in r.stdout.splitlines() if l.strip()][-6:]
            time.sleep(20)
            n = 0
            with open(a.out, 'a') as fo:
                for lid in LEEKS:
                    for fid in new_fights(lid, since[lid]):
                        row = fight_row(lw, fid, lid)
                        if row is None:
                            continue
                        row.update(arm=arm, ai=path, block=i, date=int(time.time()))
                        fo.write(json.dumps(row) + '\n'); n += 1
                        tot[arm][0] += 1; tot[arm][1] += row['res']; tot[arm][2] += row['gain'] or 0
            print('block %d arm %s (%s): %d fights | A %d fights %.1f wins %+.0f talent | B %d fights %.1f wins %+.0f talent' % (
                i, arm, path, n, tot['A'][0], tot['A'][1], tot['A'][2], tot['B'][0], tot['B'][1], tot['B'][2]), flush=True)
            for l in tail:
                print('     ' + l, flush=True)
            if n == 0:
                print('no fight played in this block - stopping', flush=True); break
            if min(tot['A'][0], tot['B'][0]) >= 96 and tot['B'][2] - tot['A'][2] < -a.stop_gap:
                print('arm B trails by more than %.0f talent - stopping' % a.stop_gap, flush=True); break
    finally:
        set_ai(lw, a.a)
        print('leeks back on: ' + ', '.join('%s %s' % (n, (lw.leek(l).get('ai') or {}).get('path')) for l, n in LEEKS.items()), flush=True)


if __name__ == '__main__':
    main()
