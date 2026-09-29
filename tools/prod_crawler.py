#!/usr/bin/env python3
"""Crawl production solo fights for value / policy learning (2026-09-28).

Real fights carry what the local simulator cannot: real opponents with their
real AIs. This builds a resumable dataset under data/prod/:

  leeks.json            ranked leeks {id: {talent, level, name, rank}}
  index.jsonl           one line per solo fight seen in any history
  fights/<id//10000>/<id>.json.gz   stripped fight (header + leeks/actions/map)

Stages (each resumable, skip what is already on disk):
  python3 tools/prod_crawler.py leeks --pages 1-40      # ranking, 50 per page
  python3 tools/prod_crawler.py index --min-level 301 --talent 1500-5000
  python3 tools/prod_crawler.py fetch --max 60000
  python3 tools/prod_crawler.py stats

Rate: a shared token bucket (default 9 req/s, LW+ allows 10) over a few
threads; LWSession retries rate_limit and network faults on top.
"""
import argparse, gzip, json, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession

OUT = os.path.join(ROOT, 'data', 'prod')
LEEKS = os.path.join(OUT, 'leeks.json')
INDEX = os.path.join(OUT, 'index.jsonl')
FIGHTS = os.path.join(OUT, 'fights')


class Bucket:
    def __init__(self, rate):
        self.rate, self.lock, self.next = rate, threading.Lock(), time.time()

    def take(self):
        with self.lock:
            now = time.time()
            wait = self.next - now
            self.next = max(now, self.next) + 1.0 / self.rate
        if wait > 0:
            time.sleep(wait)


class API:
    def __init__(self, rate, account='main'):
        self.lw = LWSession(account)
        self.b = Bucket(rate)
        self.n = 0

    def get(self, path):
        self.b.take()
        self.n += 1
        return self.lw.get(path)


def rng(s):
    a, b = s.split('-')
    return int(a), int(b)


def fight_path(fid):
    return os.path.join(FIGHTS, str(fid // 10000), '%d.json.gz' % fid)


# ------------------------------------------------------------------ stages
def st_leeks(a):
    api = API(a.rate)
    lo, hi = rng(a.pages)
    leeks = json.load(open(LEEKS)) if os.path.exists(LEEKS) else {}
    for p in range(lo, hi + 1):
        r = api.get('/ranking/get/leek/talent/%d/null' % p)
        for l in (r or {}).get('ranking', []):
            leeks[str(l['id'])] = {'talent': l['talent'], 'level': l['level'], 'name': l['name'], 'rank': l['rank']}
        print('page %d: %d leeks total' % (p, len(leeks)), flush=True)
    json.dump(leeks, open(LEEKS, 'w'))


def st_index(a):
    api = API(a.rate)
    leeks = json.load(open(LEEKS))
    tlo, thi = rng(a.talent)
    todo = [int(i) for i, l in leeks.items() if l['level'] >= a.min_level and tlo <= l['talent'] <= thi]
    done_leeks = set()
    seen = set()
    if os.path.exists(INDEX):
        for line in open(INDEX):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            seen.add(r['id'])
            done_leeks.add(r.get('src'))
    if not a.rescan:
        todo = [i for i in todo if i not in done_leeks]
    print('index: %d leeks to scan, %d fights already indexed' % (len(todo), len(seen)), flush=True)
    lock = threading.Lock()
    out = open(INDEX, 'a')
    stats = {'leeks': 0, 'new': 0}

    def one(lid):
        h = api.get('/history/get-leek-history/%d' % lid)
        rows = []
        for f in (h or {}).get('fights', []):
            if f.get('type') != 0 or f.get('status') != 2:
                continue            # solo, finished (context 2 = garden/ladder, 1 = challenge)
            rows.append({'id': f['id'], 'src': lid, 'date': f.get('date'), 'context': f.get('context'),
                         'leeks1': f.get('leeks1'), 'leeks2': f.get('leeks2'), 'winner': f.get('winner')})
        with lock:
            stats['leeks'] += 1
            for r in rows:
                if r['id'] not in seen:
                    seen.add(r['id']); stats['new'] += 1
                    out.write(json.dumps(r) + '\n')
            if not rows:           # mark the leek as scanned
                out.write(json.dumps({'id': -lid, 'src': lid}) + '\n')
            if stats['leeks'] % 100 == 0:
                out.flush()
                print('  %d/%d leeks, %d fights indexed' % (stats['leeks'], len(todo), len(seen)), flush=True)

    with ThreadPoolExecutor(max_workers=a.threads) as ex:
        list(ex.map(one, todo))
    out.close()
    print('index done: %d fights' % len(seen), flush=True)


def strip(f):
    d = f.get('data') or {}
    if isinstance(d, str):
        d = json.loads(d)
    return {k: f.get(k) for k in ('id', 'date', 'context', 'type', 'winner', 'seed', 'starter', 'leeks1', 'leeks2',
                                  'farmers1', 'farmers2', 'status')} | {
        'data': {'leeks': d.get('leeks'), 'actions': d.get('actions'), 'map': d.get('map'), 'dead': d.get('dead')}}


def st_fetch(a):
    api = API(a.rate)
    ids = []
    for line in open(INDEX):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r['id'] > 0 and (a.all_contexts or r.get('context') == a.context):
            ids.append(r['id'])
    ids = sorted(set(ids), reverse=True)            # newest first
    todo = [i for i in ids if not os.path.exists(fight_path(i))][:a.max]
    print('fetch: %d indexed, %d to fetch' % (len(ids), len(todo)), flush=True)
    t0 = time.time(); done = [0]; lock = threading.Lock()

    bad = [0]

    def one(fid):
        try:
            f = api.get('/fight/get/%d' % fid)
            if isinstance(f, dict):
                f = f.get('fight', f)
            if not isinstance(f, dict) or not isinstance(f.get('data'), dict) or not f['data'].get('actions'):
                with lock:
                    bad[0] += 1
                return
        except Exception:
            with lock:
                bad[0] += 1
            return
        p = fight_path(fid)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with gzip.open(p + '.tmp', 'wt') as g:
            json.dump(strip(f), g)
        os.replace(p + '.tmp', p)
        with lock:
            done[0] += 1
            if done[0] % 500 == 0:
                el = time.time() - t0
                print('  %d/%d fetched  %.1f/s  eta %.0f min' % (done[0], len(todo), done[0] / el,
                      (len(todo) - done[0]) / max(0.1, done[0] / el) / 60), flush=True)

    with ThreadPoolExecutor(max_workers=a.threads) as ex:
        list(ex.map(one, todo))
    print('fetch done: %d new fights in %.0f min (%d unusable responses skipped)' % (done[0], (time.time() - t0) / 60, bad[0]), flush=True)


def st_opponents(a):
    """Add leeks met in stored fights but absent from the ranking pages
    (talent / level from the fight headers, latest fight wins)."""
    leeks = json.load(open(LEEKS)) if os.path.exists(LEEKS) else {}
    found = {}
    for dp, _, fs in os.walk(FIGHTS):
        for fn in fs:
            if not fn.endswith('.json.gz'):
                continue
            try:
                f = json.load(gzip.open(os.path.join(dp, fn), 'rt'))
            except Exception:
                continue
            for l in (f.get('leeks1') or []) + (f.get('leeks2') or []):
                k = str(l.get('id'))
                if k in leeks or l.get('talent') is None:
                    continue
                if k not in found or (f.get('date') or 0) > found[k][0]:
                    found[k] = (f.get('date') or 0, {'talent': l['talent'], 'level': l.get('level', 0),
                                                      'name': l.get('name'), 'rank': None})
    for k, (_, v) in found.items():
        leeks[k] = v
    json.dump(leeks, open(LEEKS, 'w'))
    print('opponents: %d leeks added, %d total' % (len(found), len(leeks)))


def st_walk(a):
    """Walk fight ids backwards (histories only reach ~1 week back) and keep
    finished solo fights whose leeks are all level >= --min-level. Resumable:
    data/prod/walk_state.json holds the next id to try."""
    state_p = os.path.join(OUT, 'walk_state.json')
    nxt = json.load(open(state_p))['next'] if os.path.exists(state_p) else a.start
    stop = nxt - a.count
    api = API(a.rate)
    lock = threading.Lock(); st = {'kept': 0, 'seen': 0, 'lo': nxt}
    t0 = time.time()
    out = open(INDEX, 'a')

    def one(fid):
        if os.path.exists(fight_path(fid)):
            return
        try:
            f = api.get('/fight/get/%d' % fid)
            if isinstance(f, dict):
                f = f.get('fight', f)
        except Exception:
            f = None
        keep = False
        if isinstance(f, dict) and f.get('type') == 0 and f.get('status') == 2 and f.get('context') in (1, 2, 3) \
                and isinstance(f.get('data'), dict) \
                and f['data'].get('actions'):
            ls = (f.get('leeks1') or []) + (f.get('leeks2') or [])
            keep = bool(ls) and all((l.get('level') or 0) >= a.min_level for l in ls)
        if keep:
            p = fight_path(fid)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with gzip.open(p + '.tmp', 'wt') as g:
                json.dump(strip(f), g)
            os.replace(p + '.tmp', p)
        with lock:
            st['seen'] += 1
            if keep:
                st['kept'] += 1
                out.write(json.dumps({'id': fid, 'src': 'walk', 'date': f.get('date'), 'context': f.get('context'),
                                      'leeks1': f.get('leeks1'), 'leeks2': f.get('leeks2'), 'winner': f.get('winner')}) + '\n')
            if st['seen'] % 1000 == 0:
                out.flush()
                el = time.time() - t0
                print('  walk %d ids, kept %d (%.1f%%)  %.1f ids/s' % (st['seen'], st['kept'], 100.0 * st['kept'] / st['seen'],
                                                                   st['seen'] / el), flush=True)

    # chunks so the state file only moves past fully processed ids
    cur = nxt
    with ThreadPoolExecutor(max_workers=a.threads) as ex:
        while cur > stop:
            lo = max(stop, cur - 2000)
            list(ex.map(one, range(cur, lo, -1)))
            cur = lo
            json.dump({'next': cur}, open(state_p, 'w'))
    out.close()
    print('walk done: %d ids, kept %d, next %d' % (st['seen'], st['kept'], cur), flush=True)


def st_stats(a):
    n = sum(1 for _ in open(INDEX)) if os.path.exists(INDEX) else 0
    files = 0; size = 0
    for dp, _, fs in os.walk(FIGHTS):
        for f in fs:
            if f.endswith('.json.gz'):
                files += 1; size += os.path.getsize(os.path.join(dp, f))
    leeks = json.load(open(LEEKS)) if os.path.exists(LEEKS) else {}
    print('leeks %d  index lines %d  fights on disk %d (%.0f MB)' % (len(leeks), n, files, size / 1e6))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rate', type=float, default=9.0)
    ap.add_argument('--threads', type=int, default=4)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('leeks'); s.add_argument('--pages', default='1-40')
    s = sub.add_parser('index'); s.add_argument('--talent', default='1500-5000'); s.add_argument('--min-level', type=int, default=301)
    s.add_argument('--rescan', action='store_true', help='scan leeks again for fights played since the last scan')
    s = sub.add_parser('opponents')
    s = sub.add_parser('walk'); s.add_argument('--start', type=int, default=53700000); s.add_argument('--count', type=int, default=300000)
    s.add_argument('--min-level', type=int, default=301)
    s = sub.add_parser('fetch'); s.add_argument('--max', type=int, default=60000); s.add_argument('--context', type=int, default=2)
    s.add_argument('--all-contexts', action='store_true')
    sub.add_parser('stats')
    a = ap.parse_args()
    os.makedirs(FIGHTS, exist_ok=True)
    {'leeks': st_leeks, 'index': st_index, 'fetch': st_fetch, 'stats': st_stats, 'opponents': st_opponents, 'walk': st_walk}[a.cmd](a)


if __name__ == '__main__':
    main()
