#!/usr/bin/env python3
"""What can this account craft right now, and which crafts would upgrade its leeks?

    python3 tools/craft_check.py --account cure
    python3 tools/craft_check.py --account main

For every component recipe the farmer owns: how many it can craft from its stock (sub-components crafted
along the way). For every leek: the best swap (craftable or spare component in, weakest equipped part out),
scored with role weights (alterations on equipped parts included). TP/MP weigh like ~150/120 stat points, a RAM point (a chip slot) like 15, and a
component already on the leek is skipped (the server refuses duplicates). Read-only: crafts nothing.
Data: the public /data/get-all (cached in data/lw_data_all.json for a day).
"""
import argparse, collections, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession

CACHE = os.path.join(ROOT, 'data', 'lw_data_all.json')
ROLE = {   # per-point value by leek (rough, for ranking only)
    'str': dict(strength=1, tp=150, mp=120, life=0.25, wisdom=0.4, resistance=0.5, agility=0.2, science=0.1, ram=15, cores=1, frequency=0.1),
    'mag': dict(magic=1, tp=150, mp=120, life=0.25, wisdom=0.5, resistance=0.3, agility=0.2, science=0.2, ram=15, cores=1, frequency=0.1),
    'tank': dict(resistance=1, life=0.4, tp=150, mp=120, science=0.5, wisdom=0.4, strength=0.2, ram=15, cores=1, frequency=0.1),
}
ROLE_OF = {'Kirby54': 'str', 'GTGabi': 'str', 'Zoulman': 'tank', 'Payou': 'mag',
           'LeekRain': 'str', 'DawnFall': 'mag', 'DuskHope': 'mag', 'ProdigalSon': 'str'}


def data(lw):
    if not os.path.exists(CACHE) or time.time() - os.path.getmtime(CACHE) > 86400:
        json.dump(lw.get('/data/get-all'), open(CACHE, 'w'))
    return json.load(open(CACHE))['data']


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--account', default='cure', choices=['main', 'cure'])
    ap.add_argument('--min-gain', type=float, default=20)
    a = ap.parse_args()
    lw = LWSession(a.account); D = data(lw)
    items = {int(k): v for k, v in D['items'].items()}; nm = lambda t: items.get(t, {}).get('name', str(t))
    comps = {v['template']: dict(v['stats']) for v in D['components'].values()}
    schemes = {int(k): v for k, v in D['schemes'].items()}
    by_result = collections.defaultdict(list)
    for rid, s in schemes.items():
        by_result[s['result']].append(rid)
    f = lw.get('/farmer/get-from-token'); f = f.get('farmer', f)
    stock = collections.Counter()
    for k in ('resources', 'components', 'chips', 'weapons', 'potions'):
        for x in f.get(k) or []:
            stock[x['template']] += x.get('quantity') or 1
    sch_item = {t: int(v['params']) for t, v in items.items() if v['type'] == 9 and str(v.get('params') or '').isdigit()}
    owned = {sch_item[x['template']] for x in f.get('schemes') or [] if x['template'] in sch_item}

    def make(t, n, st, depth=0):
        if st[t] >= n:
            st[t] -= n; return True
        need = n - st[t]; st[t] = 0
        if depth > 5: return False
        for rid in by_result.get(t, []):
            if rid not in owned: continue
            q = schemes[rid].get('quantity') or 1; runs = -(-need // q)
            tr = st.copy()
            if all(make(i, c * runs, tr, depth + 1) for i, c in (x for x in schemes[rid]['items'] if x)):
                st.clear(); st.update(tr); st[t] += runs * q - need; return True
        return False

    def craftable(t):
        k = 0; st = stock.copy()
        while k < 9 and make(t, 1, st):
            k += 1
        return k

    spare = {x['template'] for x in f.get('components') or []}
    cand = {}
    for t in comps:
        if t not in by_result and t not in spare: continue
        n = craftable(t) if any(r in owned for r in by_result.get(t, [])) else 0
        if t in spare and stock[t] > 0:
            n = max(n, 1)
        if n:
            cand[t] = n
    leeks = [lw.leek(int(lid)) for lid in (lw.farmer.get('leeks') or {})]
    print('%s: %d components craftable or spare now' % (a.account, len(cand)))
    for l in leeks:
        w = ROLE[ROLE_OF.get(l['name'], 'str')]
        score = lambda t, extra=None: sum(w.get(k, 0) * v for k, v in comps.get(t, {}).items()) + \
            sum(w.get(k, 0) * v for k, v in (extra or {}).items())
        eq = [c['template'] for c in l['components'] if c]
        alt = {c['template']: (c.get('stats') or {}) for c in l['components'] if c}      # alteration deltas
        best = []
        for t, n in cand.items():
            if t in eq or (items[t].get('level') or 0) > l['level'] or nm(t).startswith('recovery_'):
                continue           # owner: never equip recovery_core / recovery_ram (2 slots each)
            # parts giving RAM (chip slots) or cores (the AI's ops budget) only make way for one giving as much
            outs = [e for e in eq if comps[t].get('ram', 0) >= comps.get(e, {}).get('ram', 0)
                    and comps[t].get('cores', 0) >= comps.get(e, {}).get('cores', 0)]
            if not outs:
                continue
            out = min(outs, key=lambda e: score(e, alt.get(e)) - score(t))      # the part this one beats by the most
            gain = score(t) - score(out, alt.get(out))
            if gain >= a.min_gain:
                cur = dict(comps[out]); [cur.__setitem__(k, cur.get(k, 0) + v) for k, v in alt.get(out, {}).items()]
                d = {k: comps[t].get(k, 0) - cur.get(k, 0) for k in set(comps[t]) | set(cur)}
                best.append((gain, nm(t), n, nm(out), {k: v for k, v in sorted(d.items()) if v}))
        best.sort(reverse=True)
        print('  %-12s %s' % (l['name'], ('; '.join('%s (x%d) for %s +%.0f %s' % (b[1], b[2], b[3], b[0], b[4]) for b in best[:3])) or '-'))


if __name__ == '__main__':
    main()
