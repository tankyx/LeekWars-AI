#!/usr/bin/env python3
"""Real-fight before/after: today's cached fights (data/fight_cache, ids from
tools/fight_history_<leek>.db with timestamp >= DATE) vs the baseline set in
data/ladder/our_solo.json, per leek. Prints win rate, HP-lead, hidden-end
rate (exact LoS from tools/lw_geometry), fire-then-move, damage taken/dealt
per turn, and Margaret's poison wiped/landed.

    python3 tools/real_before_after.py 2026-09-22
"""
import json, sys, sqlite3, glob, os, statistics as st
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(__file__))
from lw_decode import Decoder
from lw_geometry import Geometry
D = Decoder()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEEKS = {20443: 'AdaLovelace', 129288: 'EdsgerDijkstra', 129295: 'KurtGodel', 129296: 'MargaretHamilton'}
DEF = {'wall','fortress','armor','armoring','shield','helmet','rampart','remission','cure','regeneration','vaccine','serum','bandage','drip','mirror','thorn','carapace','elevation','knowledge','steroid','protein','adrenaline','motivation','warm_up','leather_boots','seven_league_boots','stretching','doping','rage','wizardry','solidification','ferocity','precipitation','liberation','manumission','antidote','jump','teleportation','inversion'}

def fight_stats(f, owner):
    data = f['data']; leeks = data['leeks']; m = data['map']
    G = Geometry(m['width'], m['height'], m['obstacles'])
    me = [l for l in leeks if l['name'] == owner]
    if not me: return None
    me = me[0]['id']; myteam = [l for l in leeks if l['id'] == me][0]['team']
    en = [l for l in leeks if l['team'] != myteam]
    if not en: return None
    en = en[0]['id']
    res = 'WIN' if f['winner'] == myteam else ('DRAW' if f['winner'] == 0 else 'LOSS')
    mx = {l['id']: l['life'] for l in leeks}; hp = dict(mx)
    cell = {l['id']: l['cellPos'] for l in leeks if l.get('cellPos') is not None}
    T = 1; cur = None; held = {}
    fired = defaultdict(list); moved_after = 0; fire_turns = 0
    end_los = []; taken = 0; dealt = 0; myturns = 0; active = {}; wiped = 0; landed = 0
    seq = defaultdict(list)
    for a in data['actions']:
        if not isinstance(a, list) or not a: continue
        c = a[0]
        if c == 6: T = a[1]; continue
        if c == 7:
            if cur == me and T in seq:
                pass
            cur = a[1]
            if cur == me: myturns += 1
            continue
        if c == 10 and len(a) > 2:
            cell[cur] = a[2]
            if cur == me: seq[T].append('M')
        elif c == 13 and len(a) > 1: held[cur] = a[1]
        elif c == 12 and len(a) > 1 and cur == me:
            nm = D.chip(a[1])
            if nm not in DEF: seq[T].append('F')
        elif c == 16 and cur == me: seq[T].append('F')
        elif c in (101, 109, 110, 108) and len(a) > 2:
            hp[a[1]] -= a[2]
            if a[1] == me: taken += a[2]
            if a[1] == en: dealt += a[2]
            if c == 110 and a[1] == en: landed += a[2]
        elif c == 107 and len(a) > 2:
            hp[a[1]] -= a[2]; mx[a[1]] -= a[2]
            if a[1] == me: taken += a[2]
            if a[1] == en: dealt += a[2]
        elif c == 103 and len(a) > 2: hp[a[1]] = min(mx[a[1]], hp[a[1]] + a[2])
        elif c in (104, 112) and len(a) > 2: mx[a[1]] += a[2]; hp[a[1]] += a[2]
        elif c in (301, 302) and len(a) > 7 and a[4] == en and cur == me and a[5] == 13:
            active[(c, a[1], T, len(active))] = (a[6], a[7], T)
        elif c == 12 and len(a) > 1 and cur == en and D.chip(a[1]) == 'antidote':
            wiped += sum(v * max(0, t - (T - t0)) for (v, t, t0) in active.values()); active = {}
        # end-of-our-turn LoS snapshot: record on every action while cur==me; last one wins
        if cur == me and me in cell and en in cell:
            occupied = {v for k, v in cell.items() if k != me}
            end_los.append((T, G.los(cell[en], cell[me], occupied)))
    los_by_turn = {}
    for T2, l in end_los: los_by_turn[T2] = l
    hidden = sum(1 for v in los_by_turn.values() if v is False)
    for T2, s in seq.items():
        if 'F' in s:
            fire_turns += 1
            if 'M' in s and max(i for i, x in enumerate(s) if x == 'M') > s.index('F'): moved_after += 1
    lead = 100 * max(0, hp[me]) / max(1, mx[me]) - 100 * max(0, hp[en]) / max(1, mx[en])
    return dict(res=res, turns=myturns, hidden=hidden / max(1, len(los_by_turn)), hnh=moved_after / max(1, fire_turns),
                taken=taken / max(1, myturns), dealt=dealt / max(1, myturns), lead=lead, wiped=wiped, landed=landed)

def summarize(rows, label):
    if not rows: print('  %-8s n=0' % label); return
    n = len(rows); W = sum(1 for r in rows if r['res'] == 'WIN'); L = sum(1 for r in rows if r['res'] == 'LOSS')
    print('  %-8s n=%3d  W %3d (%.0f%%) L %3d  HP-lead %+6.1f  hidden-end %.2f  fire-then-move %.2f  taken/turn %5.0f  dealt/turn %5.0f  turns %.1f  wiped/landed %.0f%%' % (
        label, n, W, 100 * W / n, L, st.mean(r['lead'] for r in rows), st.mean(r['hidden'] for r in rows), st.mean(r['hnh'] for r in rows),
        st.mean(r['taken'] for r in rows), st.mean(r['dealt'] for r in rows), st.mean(r['turns'] for r in rows),
        100 * sum(r['wiped'] for r in rows) / max(1, sum(r['landed'] for r in rows))))

def main():
    date = sys.argv[1] if len(sys.argv) > 1 else '2026-09-22'
    end = sys.argv[2] if len(sys.argv) > 2 else '9999'
    base = json.load(open(os.path.join(ROOT, 'data/ladder/our_solo.json')))
    for lid, name in LEEKS.items():
        db = os.path.join(ROOT, 'tools', 'fight_history_%d.db' % lid)
        ids = [r[0] for r in sqlite3.connect(db).execute("select fight_id from fight_history where timestamp >= ? and timestamp < ?", (date, end))]
        today = []
        for fid in ids:
            p = os.path.join(ROOT, 'data/fight_cache/%d.json' % fid)
            if not os.path.exists(p): continue
            f = json.load(open(p))
            if 'data' not in f or not f['data'].get('actions'): continue
            r = fight_stats(f, name)
            if r: today.append(r)
        before = [fight_stats(f, name) for f in base.values() if f['owner'] == name]
        before = [r for r in before if r]
        print('=== %s' % name)
        summarize(before, 'BEFORE'); summarize(today, 'WINDOW')
        missing = len(ids) - len(today)
        if missing: print('  (%d of today\'s %d fights not in cache yet)' % (missing, len(ids)))

if __name__ == '__main__':
    main()
