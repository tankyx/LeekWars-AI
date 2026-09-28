#!/usr/bin/env python3
"""How do top mages play a long fight against a STR leek, turn by turn?

Target pattern for a multi-turn planner (2026-09-28). Same metrics over:
  TOP   data/ladder/solo_fights_wide.json, owner = top-300 MAG leek, enemy STR
  OURS  data/fight_cache (V9 era, id >= 53740000), MargaretHamilton vs STR

Per fight: length, result. Per own turn: TP by category, chips cast, own HP%
at turn start, distance at end of turn. Per enemy turn: which of our effects
are live on the enemy (exact: effect adds 301/302 by instance id, removals
303 / 307 remove-poisons / 308 remove-shackles) -> uptime per effect type.

    python3 tools/siege_rotation.py            # tables
    python3 tools/siege_rotation.py --json out.json
"""
import argparse, glob, json, os, statistics as st, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_decode import Decoder
from lw_geometry import Geometry

D = Decoder()
# effect type -> uptime family
FAM = {13: 'poison', 19: 'str_shackle', 18: 'tp_shackle', 17: 'mp_shackle', 24: 'mag_shackle',
       47: 'agi_shackle', 26: 'vuln', 27: 'vuln'}
CAT = {1: 'damage', 28: 'damage', 30: 'nova', 13: 'poison', 2: 'heal', 12: 'heal',
       5: 'shield', 6: 'shield', 21: 'shield', 3: 'buff', 4: 'buff', 7: 'buff', 8: 'buff',
       22: 'buff', 31: 'buff', 32: 'buff', 38: 'buff', 39: 'buff', 40: 'buff', 41: 'buff',
       42: 'buff', 43: 'buff', 44: 'buff', 17: 'mp_shackle', 18: 'tp_shackle', 19: 'str_shackle',
       24: 'mag_shackle', 14: 'summon', 10: 'move', 11: 'move', 23: 'cleanse', 49: 'cleanse',
       26: 'vuln', 27: 'vuln', 20: 'return', 9: 'debuff'}


def chip_cat(name):
    for e in D.info(name).get('effects', []):
        c = CAT.get(e.get('id'))
        if c:
            return c
    return 'other'


def build(l):
    s, m, a = l.get('strength', 0), l.get('magic', 0), l.get('agility', 0)
    if m > max(s, a) + 50:
        return 'MAG'
    if a > max(s, m) + 50:
        return 'AGI'
    return 'STR'


def analyse(f, owner_name=None, owner_id=None):
    data = f.get('data') or {}
    if isinstance(data, str):
        data = json.loads(data)
    leeks = data.get('leeks') or []
    me = None
    for l in leeks:
        if l.get('summon'):
            continue
        if owner_name and l.get('name') == owner_name:
            me = l
        elif owner_id is not None and any(x.get('id') == owner_id and x.get('name') == l.get('name')
                                           for x in (f.get('leeks1') or []) + (f.get('leeks2') or [])):
            me = l
    if not me or build(me) != 'MAG':
        return None
    ens = [l for l in leeks if l.get('team') != me['team'] and not l.get('summon')]
    if len(ens) != 1 or build(ens[0]) != 'STR':
        return None
    en = ens[0]; mid, eid = me['id'], en['id']
    try:
        geo = Geometry(obstacles=(data.get('map') or {}).get('obstacles') or {})
    except Exception:
        geo = None
    pos = {l['id']: l.get('cellPos') for l in leeks}
    hp = {mid: me.get('life', 1), eid: en.get('life', 1)}
    maxhp = dict(hp)
    win = f.get('winner') == me['team']
    live = {}                    # effect instance id -> family (effects of ours on the enemy)
    turns = []                   # our turns
    enemy_turns = []             # families live at the start of each enemy turn
    contact = None
    cur = None; T = 1; t = None; held = {}
    acts = data.get('actions', [])
    for a in acts:
        if not isinstance(a, list) or not a:
            continue
        c = a[0]
        if c == 6:
            T = a[1] if len(a) > 1 else T + 1
        elif c == 7:
            if t is not None:
                if geo and pos.get(mid) is not None and pos.get(eid) is not None:
                    try:
                        t['end_dist'] = geo.dist(pos[mid], pos[eid])
                    except Exception:
                        pass
                turns.append(t); t = None
            cur = a[1] if len(a) > 1 else None
            if cur == mid:
                t = {'T': T, 'hp': hp[mid] / max(1, maxhp[mid]), 'ehp': hp[eid] / max(1, maxhp[eid]),
                     'tp': Counter(), 'chips': [], 'end_dist': None}
            elif cur == eid:
                enemy_turns.append({'T': T, 'fams': set(live.values())})
        elif c == 10 and len(a) > 2:
            if cur is not None:
                pos[cur] = a[2]
        elif c == 13 and len(a) > 1 and cur is not None:
            if cur == mid and t is not None and held.get(cur) != a[1]:
                t['tp']['swap'] += 1
            held[cur] = a[1]
        elif c == 12 and len(a) > 2 and cur == mid and t is not None:
            name = D.chip(a[1])
            info = D.info(name)
            t['tp'][chip_cat(name)] += info.get('cost', 0) or 0
            t['chips'].append(name)
        elif c == 16 and cur == mid and t is not None:
            w = D.weapon(held.get(mid, -1))
            t['tp']['weapon'] += D.info(w).get('cost', 0) or 0
        elif c in (101, 110, 111) and len(a) > 2:
            if a[1] in hp:
                hp[a[1]] -= a[2]
            if contact is None and a[1] in (mid, eid) and c == 101:
                contact = T
        elif c == 103 and len(a) > 2 and a[1] in hp:
            hp[a[1]] = min(maxhp[a[1]], hp[a[1]] + a[2])
        elif c in (301, 302) and len(a) > 7:
            # [30x, item, instance, idx, target, type, value, turns, ...]
            if a[4] == eid and cur == mid and a[5] in FAM:
                live[a[2]] = FAM[a[5]]
        elif c == 303 and len(a) > 1:
            live.pop(a[1], None)
        elif c == 307 and len(a) > 1 and a[1] == eid:
            for k in [k for k, v in live.items() if v == 'poison']:
                live.pop(k)
        elif c == 308 and len(a) > 1 and a[1] == eid:
            for k in [k for k, v in live.items() if v.endswith('shackle')]:
                live.pop(k)
    if t is not None:
        turns.append(t)
    return {'win': win, 'len': T, 'contact': contact, 'turns': turns, 'enemy_turns': enemy_turns,
            'me': {k: me.get(k, 0) for k in ('magic', 'wisdom', 'life', 'tp', 'resistance')},
            'en': {k: en.get(k, 0) for k in ('strength', 'life', 'tp', 'mp')}}


def load_top():
    d = json.load(open(os.path.join(ROOT, 'data/ladder/solo_fights_wide.json')))
    for f in d.values():
        r = analyse(f, owner_id=f.get('owner_leek_id'))
        if r:
            yield r


def load_ours(name='MargaretHamilton', min_id=53740000):
    seen = set()
    for p in glob.glob(os.path.join(ROOT, 'data/fight_cache/*.json')):
        try:
            fid = int(os.path.basename(p).split('.')[0])
        except ValueError:
            continue
        if fid < min_id or fid in seen:
            continue
        try:
            f = json.load(open(p))
        except Exception:
            continue
        f = f.get('fight', f)
        if f.get('type', 0) != 0:
            continue
        seen.add(fid)
        r = analyse(f, owner_name=name)
        if r:
            yield r


def summarise(rows, label):
    out = {'label': label, 'n': len(rows)}
    if not rows:
        return out
    out['win'] = st.mean(r['win'] for r in rows)
    out['len'] = st.mean(r['len'] for r in rows)
    et = [e for r in rows for e in r['enemy_turns'] if r['contact'] and e['T'] >= r['contact']]
    fams = ['poison', 'str_shackle', 'tp_shackle', 'mp_shackle', 'mag_shackle', 'vuln']
    out['uptime'] = {f: (sum(1 for e in et if f in e['fams']) / len(et) if et else 0) for f in fams}
    out['uptime']['any_shackle'] = sum(1 for e in et if any(x.endswith('shackle') for x in e['fams'])) / max(1, len(et))
    tt = [t for r in rows for t in r['turns'] if r['contact'] and t['T'] >= r['contact']]
    tot = Counter()
    for t in tt:
        tot.update(t['tp'])
    s = max(1, sum(tot.values()))
    out['tp_share'] = {k: v / s for k, v in tot.most_common()}
    out['tp_per_turn'] = sum(tot.values()) / max(1, len(tt))
    # heal share by own HP bucket
    hb = {}
    for lo, hi in ((0, .4), (.4, .7), (.7, 1.01)):
        g = [t for t in tt if lo <= t['hp'] < hi]
        hb['%.1f-%.1f' % (lo, min(hi, 1))] = (len(g), sum(1 for t in g if t['tp'].get('heal')) / max(1, len(g)))
    out['heal_by_hp'] = hb
    d = [t['end_dist'] for t in tt if t['end_dist'] is not None]
    out['end_dist_median'] = st.median(d) if d else None
    # rotation: chips by turns since contact
    rot = defaultdict(Counter); rn = Counter()
    for r in rows:
        if not r['contact']:
            continue
        for t in r['turns']:
            k = t['T'] - r['contact']
            if -2 <= k <= 12:
                rn[k] += 1
                rot[k].update(set(t['chips']))
    out['rotation'] = {k: [(c, n / rn[k]) for c, n in rot[k].most_common(7)] for k in sorted(rot)}
    # refresh behaviour: at our turn start, is a STR/TP shackle live; do we cast one anyway?
    return out


def show(o):
    print('\n=== %s  n=%d  win %.0f%%  turns/fight %.1f  TP/turn after contact %.1f  end dist median %s' % (
        o['label'], o['n'], 100 * o.get('win', 0), o.get('len', 0), o.get('tp_per_turn', 0), o.get('end_dist_median')))
    if not o['n']:
        return
    print('  uptime on enemy turns after contact:', '  '.join('%s %.0f%%' % (k, 100 * v) for k, v in o['uptime'].items()))
    print('  TP share:', '  '.join('%s %.0f%%' % (k, 100 * v) for k, v in o['tp_share'].items() if v >= 0.02))
    print('  heal turns by own HP:', '  '.join('%s: %.0f%% (n=%d)' % (k, 100 * v[1], v[0]) for k, v in o['heal_by_hp'].items()))
    print('  rotation (turns since contact: share of turns casting chip)')
    for k, lst in o['rotation'].items():
        print('    %+3d  %s' % (k, '  '.join('%s %.0f%%' % (c, 100 * p) for c, p in lst)))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--json'); a = ap.parse_args()
    top = list(load_top())
    ours = list(load_ours())
    res = [summarise(top, 'TOP-300 MAG vs STR (all)'),
           summarise([r for r in top if r['len'] >= 12], 'TOP-300 MAG vs STR, fights >= 12 turns'),
           summarise([r for r in top if r['win']], 'TOP-300 MAG vs STR, wins'),
           summarise([r for r in top if not r['win']], 'TOP-300 MAG vs STR, losses'),
           summarise(ours, 'MARGARET (V9) vs STR'),
           summarise([r for r in ours if r['win']], 'MARGARET (V9) vs STR, wins'),
           summarise([r for r in ours if not r['win']], 'MARGARET (V9) vs STR, losses')]
    for o in res:
        show(o)
    if a.json:
        json.dump(res, open(a.json, 'w'), indent=1, default=str)


if __name__ == '__main__':
    main()
