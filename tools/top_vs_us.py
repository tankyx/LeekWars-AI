#!/usr/bin/env python3
"""What do the top ladder leeks do that ours don't?

Runs one set of per-fight metrics over two real-fight datasets and prints
them side by side, grouped by build:
  TOP  data/ladder/solo_fights_wide.json  (owner = a top-300 leek, talent ~2400-4300)
  OURS data/ladder/our_solo.json + recent data/fight_cache fights of our 4 main leeks

Metrics are owner-side, per own turn unless noted: stats and kit shape,
TP spent (item costs + weapon swaps) vs base TP, MP moved, weapon shots,
chip casts by effect category, share of turns with an attack, fire-then-move,
hidden end of turn (exact LoS via tools/lw_geometry), distance to the enemy
at end of turn, damage dealt / taken / healed, fight length, summons, and
the turn-1 opening.

    python3 tools/top_vs_us.py            # summary tables
    python3 tools/top_vs_us.py --json out.json
"""
import argparse, glob, json, os, statistics as st, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_decode import Decoder
from lw_geometry import Geometry

D = Decoder()
OUR = {'AdaLovelace', 'EdsgerDijkstra', 'KurtGodel', 'MargaretHamilton'}

CAT = {1: 'damage', 28: 'damage', 30: 'nova', 13: 'poison', 2: 'heal', 12: 'heal',
       5: 'shield', 6: 'shield', 21: 'shield', 3: 'buff', 4: 'buff', 7: 'buff', 8: 'buff',
       22: 'buff', 31: 'buff', 32: 'buff', 38: 'buff', 39: 'buff', 40: 'buff', 41: 'buff',
       42: 'buff', 43: 'buff', 44: 'buff', 17: 'shackle', 18: 'shackle', 19: 'shackle',
       24: 'shackle', 47: 'shackle', 48: 'shackle', 14: 'summon', 10: 'move', 11: 'move',
       23: 'cleanse', 49: 'cleanse', 26: 'vuln', 27: 'vuln', 20: 'return', 9: 'debuff'}


def chip_cat(name):
    info = D.info(name)
    for e in info.get('effects', []):
        c = CAT.get(e.get('id'))
        if c:
            return c
    return 'other'


def cost(name):
    return D.info(name).get('cost', 0) or 0


def build_of(l):
    s, m, a = l.get('strength', 0), l.get('magic', 0), l.get('agility', 0)
    if m > max(s, a) + 50:
        b = 'MAG'
    elif a > max(s, m) + 50:
        b = 'AGI'
    else:
        b = 'STR'
    return b + ('+SCI' if l.get('science', 0) >= 300 else '')


def geometry(data):
    obs = (data.get('map') or {}).get('obstacles') or {}
    try:
        return Geometry(obstacles=obs)
    except TypeError:
        return None


def analyse(f, owner):
    data = f.get('data') or {}
    if isinstance(data, str):
        data = json.loads(data)
    leeks = data.get('leeks') or []
    me = [l for l in leeks if l.get('name') == owner and not l.get('summon')]
    if not me:
        return None
    me = me[0]; mid = me['id']
    ens = [l for l in leeks if l.get('team') != me['team'] and not l.get('summon')]
    if not ens:
        return None
    en = ens[0]; eid = en['id']
    geo = geometry(data)
    pos = {l['id']: l.get('cellPos') for l in leeks}
    res = 'W' if f.get('winner') == me['team'] else ('D' if f.get('winner') == 0 else 'L')
    out = {'res': res, 'build': build_of(me), 'stats': {k: me.get(k, 0) for k in
           ('life', 'strength', 'wisdom', 'agility', 'resistance', 'science', 'magic', 'tp', 'mp', 'frequency')},
           'turns': [], 'opening': [], 'summons': 0, 'weapons_seen': set(), 'chips_seen': set()}
    cur = None; held = {}; T = 1; t = None
    for a in data.get('actions', []):
        if not isinstance(a, list) or not a:
            continue
        c = a[0]
        if c == 6:
            T = a[1] if len(a) > 1 else T + 1
        elif c == 7:
            if t is not None:
                out['turns'].append(t); t = None
            cur = a[1] if len(a) > 1 else None
            if cur == mid:
                t = {'T': T, 'tp': 0, 'mp': 0, 'shots': 0, 'cats': Counter(), 'fired': False,
                     'moved_after': False, 'dealt': 0, 'taken_before': 0, 'end_dist': None, 'end_los': None,
                     'mp_pre': 0, 'mp_post': 0, 'fire_dist': None, 'start_dist': None, 'start_los': None}
                if geo and pos.get(mid) is not None and pos.get(eid) is not None:
                    try:
                        t['start_dist'] = geo.dist(pos[mid], pos[eid])
                        t['start_los'] = geo.los(pos[mid], pos[eid], occupied={p for i, p in pos.items() if i not in (mid, eid) and p is not None})
                    except Exception:
                        pass
        elif c == 8 and cur == mid and t is not None:
            if geo and pos.get(mid) is not None and pos.get(eid) is not None:
                try:
                    t['end_dist'] = geo.dist(pos[mid], pos[eid])
                    t['end_los'] = geo.los(pos[mid], pos[eid], occupied={p for i, p in pos.items() if i not in (mid, eid) and p is not None})
                except Exception:
                    pass
        elif c == 10 and len(a) > 3:
            pos[a[1]] = a[2]
            if cur == mid and t is not None and a[1] == mid:
                n_mp = len(a[3]) if isinstance(a[3], list) else 0
                t['mp'] += n_mp
                if t['fired']:
                    t['moved_after'] = True; t['mp_post'] += n_mp
                else:
                    t['mp_pre'] += n_mp
        elif c == 13 and len(a) > 1 and cur is not None:
            if cur == mid and t is not None and held.get(mid) != a[1]:
                t['tp'] += 1
            held[cur] = a[1]
        elif c == 16 and cur == mid and t is not None:
            w = D.weapon(held.get(mid, -1)); out['weapons_seen'].add(w)
            t['tp'] += cost(w); t['shots'] += 1
            if not t['fired'] and geo and pos.get(mid) is not None and pos.get(eid) is not None:
                try: t['fire_dist'] = geo.dist(pos[mid], pos[eid])
                except Exception: pass
            if t['fired']:
                t['mp_post'] = 0
            t['fired'] = True; t['moved_after'] = False
        elif c == 12 and len(a) > 1 and cur is not None:
            name = D.chip(a[1]); cat = chip_cat(name)
            if cur == mid and t is not None:
                out['chips_seen'].add(name)
                t['tp'] += cost(name); t['cats'][cat] += 1
                if cat in ('damage', 'poison', 'nova', 'shackle', 'vuln'):
                    t['fired'] = True; t['moved_after'] = False
                if T == 1:
                    out['opening'].append(name)
                if cat == 'summon':
                    out['summons'] += 1
            if cat == 'move' and len(a) > 2:
                info = D.info(name)
                if any(e.get('id') == 10 for e in info.get('effects', [])):
                    pos[cur] = a[2]
                elif any(e.get('id') == 11 for e in info.get('effects', [])):
                    other = [i for i, p in pos.items() if p == a[2]]
                    if other:
                        pos[other[0]], pos[cur] = pos[cur], a[2]
        elif c in (101, 107, 110, 108) and len(a) > 2:
            if a[1] == eid and cur == mid and t is not None and c != 110:
                t['dealt'] += a[2]
            if a[1] == eid:
                out.setdefault('dealt_total', 0); out['dealt_total'] = out.get('dealt_total', 0) + a[2]
                if c == 110:
                    out['poison_total'] = out.get('poison_total', 0) + a[2]
            elif a[1] == mid:
                out['taken_total'] = out.get('taken_total', 0) + a[2]
        elif c == 103 and len(a) > 2 and a[1] == mid:
            out['healed_total'] = out.get('healed_total', 0) + a[2]
    if t is not None:
        out['turns'].append(t)
    return out


def load_top():
    d = json.load(open(os.path.join(ROOT, 'data/ladder/solo_fights_wide.json')))
    for f in d.values():
        yield f['owner'], f


def load_ours(since_cache=True):
    base = json.load(open(os.path.join(ROOT, 'data/ladder/our_solo.json')))
    seen = set()
    for fid, f in base.items():
        if f.get('owner') in OUR:
            seen.add(int(fid)); yield f['owner'], f
    if since_cache:
        for p in glob.glob(os.path.join(ROOT, 'data/fight_cache/*.json')):
            try:
                fid = int(os.path.basename(p)[:-5])
            except ValueError:
                continue
            if fid in seen or fid < 53740000:
                continue
            try:
                f = json.load(open(p))
            except Exception:
                continue
            if f.get('owner') in OUR and f.get('type', 0) == 0 and f.get('context', 2) == 2:
                yield f['owner'], f


def summarise(rows):
    n = len(rows)
    turns = [t for r in rows for t in r['turns']]
    nt = max(1, len(turns))
    W = sum(1 for r in rows if r['res'] == 'W')
    s = {'fights': n, 'win%': 100 * W / max(1, n),
         'turns/fight': nt / max(1, n)}
    for k in ('life', 'strength', 'wisdom', 'agility', 'resistance', 'science', 'magic', 'tp', 'mp', 'frequency'):
        s['stat_' + k] = st.mean(r['stats'][k] for r in rows)
    s['TP spent/turn'] = st.mean(t['tp'] for t in turns) if turns else 0
    s['TP spent / base TP'] = st.mean(t['tp'] / max(1, r['stats']['tp']) for r in rows for t in r['turns']) if turns else 0
    s['MP moved/turn'] = st.mean(t['mp'] for t in turns) if turns else 0
    s['weapon shots/turn'] = st.mean(t['shots'] for t in turns) if turns else 0
    s['turns with attack %'] = 100 * sum(1 for t in turns if t['fired']) / nt
    s['fire-then-move %'] = 100 * sum(1 for t in turns if t['fired'] and t['moved_after']) / max(1, sum(1 for t in turns if t['fired']))
    los = [t['end_los'] for t in turns if t['end_los'] is not None]
    s['hidden end %'] = 100 * sum(1 for x in los if not x) / max(1, len(los))
    ds = [t['end_dist'] for t in turns if t['end_dist'] is not None]
    s['end distance median'] = st.median(ds) if ds else 0
    for cat in ('damage', 'poison', 'nova', 'shackle', 'vuln', 'buff', 'shield', 'heal', 'cleanse', 'summon', 'move', 'return', 'debuff'):
        s['casts/turn ' + cat] = sum(t['cats'][cat] for t in turns) / nt
    s['dealt/turn'] = sum(r.get('dealt_total', 0) for r in rows) / nt
    s['poison share of dealt %'] = 100 * sum(r.get('poison_total', 0) for r in rows) / max(1, sum(r.get('dealt_total', 0) for r in rows))
    s['taken/turn'] = sum(r.get('taken_total', 0) for r in rows) / nt
    s['healed/turn'] = sum(r.get('healed_total', 0) for r in rows) / nt
    s['summons/fight'] = sum(r['summons'] for r in rows) / max(1, n)
    s['distinct weapons used/fight'] = st.mean(len(r['weapons_seen']) for r in rows) if rows else 0
    s['distinct chips used/fight'] = st.mean(len(r['chips_seen']) for r in rows) if rows else 0
    return s


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--json'); a = ap.parse_args()
    top = defaultdict(list); ours = defaultdict(list); top_owner = defaultdict(set)
    open_top = defaultdict(Counter); open_our = defaultdict(Counter)
    chips_top = defaultdict(Counter); chips_our = defaultdict(Counter)
    weap_top = defaultdict(Counter); weap_our = defaultdict(Counter)
    for owner, f in load_top():
        r = analyse(f, owner)
        if r:
            b = r['build'].split('+')[0]
            top[b].append(r); top_owner[b].add(owner)
            open_top[b][' > '.join(r['opening'][:5])] += 1
            chips_top[b].update(r['chips_seen']); weap_top[b].update(r['weapons_seen'])
    for owner, f in load_ours():
        r = analyse(f, owner)
        if r:
            ours[owner].append(r)
            open_our[owner][' > '.join(r['opening'][:5])] += 1
            chips_our[owner].update(r['chips_seen']); weap_our[owner].update(r['weapons_seen'])
    cols = [('TOP STR', top['STR']), ('TOP MAG', top['MAG']), ('TOP AGI', top['AGI'])] + [(o, ours[o]) for o in sorted(ours)]
    sums = [(lab, summarise(rows)) for lab, rows in cols if rows]
    keys = list(sums[0][1].keys())
    print('%-28s' % '' + ''.join('%14s' % lab[:13] for lab, _ in sums))
    for k in keys:
        print('%-28s' % k + ''.join(('%14.1f' % s[k]) if isinstance(s[k], float) else ('%14s' % s[k]) for _, s in sums))
    print('\nowners: ' + ', '.join('%s %d' % (b, len(v)) for b, v in top_owner.items()))
    for b in ('STR', 'MAG'):
        n = len(top[b])
        print('\n=== TOP %s: chips used in >=25%% of fights (share of fights)' % b)
        print('   ' + ', '.join('%s %.0f%%' % (c, 100 * v / n) for c, v in chips_top[b].most_common(30) if v / n >= 0.25))
        print('    weapons: ' + ', '.join('%s %.0f%%' % (c, 100 * v / n) for c, v in weap_top[b].most_common(10)))
        print('    T1 openings: ' + '; '.join('%s (%.0f%%)' % (o, 100 * v / n) for o, v in open_top[b].most_common(5)))
    for o in sorted(ours):
        n = len(ours[o])
        print('\n=== %s (n=%d): chips used in >=25%% of fights' % (o, n))
        print('   ' + ', '.join('%s %.0f%%' % (c, 100 * v / n) for c, v in chips_our[o].most_common(30) if v / n >= 0.25))
        print('    weapons: ' + ', '.join('%s %.0f%%' % (c, 100 * v / n) for c, v in weap_our[o].most_common(10)))
        print('    T1 openings: ' + '; '.join('%s (%.0f%%)' % (op, 100 * v / n) for op, v in open_our[o].most_common(3)))
    if a.json:
        json.dump({lab: s for lab, s in sums}, open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
