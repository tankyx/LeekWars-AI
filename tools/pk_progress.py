#!/usr/bin/env python3
"""Pumpkin farming progress (owner 2026-11-03: the Pumpkin is permanent - farm it until every leek has the
components it needs). Targets: the slots a Pumpkin part improves (no TP / MP / RAM / cores in them today).

    python3 tools/pk_progress.py                 # needs vs stock, per account and component
    python3 tools/pk_progress.py --log batch_end # also append an inventory snapshot to data/ladder/pumpkin_inventory.jsonl
    python3 tools/pk_progress.py --rates         # drop rates per Pumpkin fight from the logged snapshots

Recipes come from /scheme/get-all; every ingredient short in stock is expanded through the schemes the farmer OWNS
(kirabo, sand <- rock + pebble, orange <- apple <- leaf / branch / ice_cube, motherboard -> motherboard2, ...).
Crafting + equipping: tools/pk_craft.py.
"""
import argparse, csv, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession

LOG = os.path.join(ROOT, 'data', 'ladder', 'pumpkin_inventory.jsonl')
# component -> [(leek, component it replaces)], per account
TARGETS = {
    'main': {'quince': [('Kirby54', 'soursop'), ('GTGabi', 'gyroscope')]},
    'cure': {'quince': [('LeekRain', 'strawberry'), ('DawnFall', 'soursop'), ('DuskHope', 'hylocereus')],
             'motherboard3': [('DawnFall', 'amethyst_ring'), ('DuskHope', 'amethyst_ring')],
             'chestnut': [('ProdigalSon', 'nephelium')]},
}
WATCH = ('pumpkin_seeds', 'lantern', 'sand', 'orange', 'gold_nugget', 'obsidian', 'nephelium', 'acorn', 'kirabo',
         'aquamarine', 'topaze')


def inventory(lw, nm):
    f = lw.get('/farmer/get-from-token'); f = f.get('farmer', f)
    inv = {}
    for key in ('resources', 'components'):
        for x in f.get(key) or []:
            if key == 'components' and x.get('stats'):
                continue                     # altered parts can't be crafting ingredients
            n = nm.get(x['template'])
            inv[n] = inv.get(n, 0) + (x.get('quantity') or 0)
    return inv


def owned_recipes(lw, nm, I=None):
    """({result name: [(ingredient, qty)]}, {result name: scheme id}) for the schemes this farmer owns."""
    if I is None:
        I = lw.get('/item/get-all'); I = I.get('items', I)
    s = lw.get('/scheme/get-all'); sc = s.get('schemes', s); sc = list(sc.values()) if isinstance(sc, dict) else sc
    f = lw.get('/farmer/get-from-token'); f = f.get('farmer', f)
    owned = set(x['template'] for x in f.get('schemes') or [])
    item_of = {int(v['params']): int(k) for k, v in I.items() if v.get('type') == 9 and str(v.get('params', '')).isdigit()}
    recipes, ids = {}, {}
    for r in sc:
        if item_of.get(r['id']) in owned:
            n = nm.get(r['result'])
            recipes[n] = [(nm.get(t), q) for t, q in (it for it in r['items'] if it)]
            ids[n] = r['id']
    return recipes, ids


def needs(recipes, comp, n, inv):
    """Raw ingredients still missing for n more `comp`: stock first, then anything short is crafted through the
    owned recipes (depth-limited)."""
    tot = {}
    stock = dict(inv)

    def add(item, q, depth):
        have = stock.get(item, 0)
        use = min(have, q); stock[item] = have - use; q -= use
        if q <= 0:
            return
        if item in recipes and depth < 5:
            for ing, k in recipes[item]:
                add(ing, k * q, depth + 1)
        else:
            tot[item] = tot.get(item, 0) + q
    for ing, k in recipes[comp]:
        add(ing, k * n, 1)
    return tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log', default=None, help='append an inventory snapshot with this tag')
    ap.add_argument('--rates', action='store_true')
    a = ap.parse_args()
    if a.rates:
        rows = [json.loads(l) for l in open(LOG)] if os.path.exists(LOG) else []
        for acct in ('main', 'cure'):
            S = [r for r in rows if r['acct'] == acct]
            pairs = [(S[i], S[i + 1]) for i in range(len(S) - 1) if S[i]['tag'].startswith('batch_start') and S[i + 1]['tag'].startswith('batch_end')]
            fights = sum(p[1].get('fights', 0) for p in pairs)
            if not fights:
                print(acct, 'no complete batches logged yet'); continue
            print('%s: %d fights in %d batches' % (acct, fights, len(pairs)))
            for k in WATCH:
                gain = sum(p[1]['inv'].get(k, 0) - p[0]['inv'].get(k, 0) for p in pairs)
                if gain:
                    print('   %-14s +%4d  (%.3f a fight)' % (k, gain, gain / fights))
        return
    for acct in ('main', 'cure'):
        lw = LWSession(acct)
        I = lw.get('/item/get-all'); I = I.get('items', I)
        nm = {int(k): v['name'] for k, v in I.items()}
        recipes, _ = owned_recipes(lw, nm, I)
        inv = inventory(lw, nm)
        if a.log:
            rec = {'time': int(time.time()), 'acct': acct, 'tag': a.log, 'inv': {k: inv.get(k, 0) for k in WATCH}}
            if a.log.startswith('batch_end:'):
                rec['fights'] = int(a.log.split(':')[1]); rec['tag'] = 'batch_end'
            with open(LOG, 'a') as fh:
                fh.write(json.dumps(rec) + '\n')
            continue
        print('== %s  (%s)' % (acct, ', '.join('%s %d' % (k, inv.get(k, 0)) for k in WATCH)))
        for comp, slots in TARGETS.get(acct, {}).items():
            n = len(slots)
            short = needs(recipes, comp, n, inv)       # shortfall after the stock (sub-parts in stock count)
            one = needs(recipes, comp, 1, inv)
            print('   %-13s x%d for %s' % (comp, n, ', '.join('%s (%s)' % s for s in slots)))
            print('       next one: %s' % ('CRAFTABLE NOW' if not one else 'short ' + ', '.join('%s %d' % kv for kv in one.items())))
            print('       all %d  : short %s' % (n, ', '.join('%s %d' % kv for kv in short.items()) or 'nothing'))


if __name__ == '__main__':
    main()
