#!/usr/bin/env python3
"""Walk recent fight ids and keep every boss fight (type 4) — ours and other
farmers' — to data/boss_fights/<id>.json, so we can study how winning squads
beat the Fennel King / Evil Pumpkin (composition, builds, turn-by-turn play).

    python3 tools/boss_walk.py --start 53891000 --count 120000 --threads 3 --rate 9
    python3 tools/boss_walk.py --summary

Resumable: data/boss_fights/walk_state.json keeps the lowest id reached.
"""
import argparse, collections, json, os, sys, threading, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession
OUT = os.path.join(ROOT, 'data', 'boss_fights')
STATE = os.path.join(OUT, 'walk_state.json')


def summary():
    c = collections.Counter(); wins = collections.defaultdict(list)
    for fn in os.listdir(OUT):
        if not fn[0].isdigit():
            continue
        f = json.load(open(os.path.join(OUT, fn)))
        boss = next((l['name'] for l in f.get('leeks2') or [] if l.get('name') in ('nasu_samurai', 'fennel_king', 'evil_pumpkin')), '?')
        c[(boss, f.get('winner'))] += 1
        if f.get('winner') == 1:
            wins[boss].append(f['id'])
    for k, v in sorted(c.items()):
        print('%-14s winner %s: %d' % (k[0], k[1], v))
    for b, ids in wins.items():
        print('%s wins: %s' % (b, ids[:30]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--start', type=int, default=53891000)
    ap.add_argument('--count', type=int, default=120000)
    ap.add_argument('--threads', type=int, default=3)
    ap.add_argument('--rate', type=float, default=9.0)
    ap.add_argument('--summary', action='store_true')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.summary:
        return summary()
    st = json.load(open(STATE)) if os.path.exists(STATE) else {'next': a.start, 'end': a.start - a.count}
    lock = threading.Lock(); nxt = [st['next']]; end = st['end']; found = [0]; seen = [0]
    gap = [time.time()]
    lw = LWSession('main')

    def take():
        with lock:
            now = time.time(); w = gap[0] - now; gap[0] = max(now, gap[0]) + 1.0 / a.rate
            if nxt[0] <= end:
                return None, w
            fid = nxt[0]; nxt[0] -= 1
            return fid, w

    def run():
        while True:
            fid, w = take()
            if fid is None:
                return
            if w > 0:
                time.sleep(w)
            f = lw.get('/fight/get/%d' % fid); f = f.get('fight', f) if isinstance(f, dict) else {}
            with lock:
                seen[0] += 1
                if f.get('type') == 4 and f.get('status') == 2:
                    json.dump(f, open(os.path.join(OUT, '%d.json' % fid), 'w')); found[0] += 1
                if seen[0] % 2000 == 0:
                    json.dump({'next': nxt[0], 'end': end}, open(STATE, 'w'))
                    print('%d scanned, %d boss fights, at %d' % (seen[0], found[0], nxt[0]), flush=True)

    th = [threading.Thread(target=run) for _ in range(a.threads)]
    [t.start() for t in th]; [t.join() for t in th]
    json.dump({'next': nxt[0], 'end': end}, open(STATE, 'w'))
    summary()


if __name__ == '__main__':
    main()
