#!/usr/bin/env python3
"""
Recycle surplus components into resources + alterations (LeekWars 2026-09 feature).

API (discovered 2026-09-14, no public docs):
  POST /api/item/recycle {item_id}  -> destroys ONE unit from that stack.
  Response: {"destroyed": 1, "count": N,
             "resources":   {resource_template: qty, ...},
             "alterations": {alteration_PARAMS: qty, ...}}
  There is NO preview/dry-run endpoint and NO undo: the only way to learn a
  yield is to destroy a unit. `item_id` is the STACK id; each call consumes 1.

Yield model (measured): you get back roughly 25% of the component's RECIPE
input units, drawn from that recipe's own ingredients, plus alterations
(type-10 items: vitamins/metals) scaling the same way. So expected value is a
function of the recipe cost, NOT of the component's stats:
    rgb   (recipe 134 units) -> 30-36 resource units + 2-3 alterations
    fan   (recipe  12 units) -> 0-5  resource units + 0-1 alterations
    apple (recipe  10 units) -> 3    resource units + 0   alterations
NB: the alterations dict is keyed by the alteration's `params` number, not its
template id (params 25 = supercapacitor, 20 = nitinol).

Safety: DRY RUN unless --execute. Never recycles a component equipped on any
leek, never touches PROTECTED premium components, and always leaves --keep of
each template.

Usage:
  python3 tools/recycle_components.py                          # dry run, main
  python3 tools/recycle_components.py --account cure
  python3 tools/recycle_components.py --keep 20 --min-value 30
  python3 tools/recycle_components.py --execute --max 200
  python3 tools/recycle_components.py --template rgb --execute
"""
import argparse
import json
import os
import sys
import time
from collections import defaultdict

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_credentials  # noqa: E402

BASE = 'https://leekwars.com/api'
HERE = os.path.dirname(os.path.abspath(__file__))

# Premium/crafted components we never want turned back into raw materials,
# regardless of how many we hold. These are the payoff of the crafting chain.
PROTECTED = {
    'obsidian_plate', 'amazonite_plate', 'chestnut', 'hylocereus', 'nephelium',
    'strawberry', 'neural_core_pro', 'motherboard2', 'motherboard3', 'ram2',
    'ram3', 'core2', 'core3', 'power_supply', 'recovery_core', 'recovery_ram',
    'nuclear_core', 'blue_mango', 'thokozani', 'chiyembekezo', 'uzoma',
    'kirabo', 'limbani', 'propulsor2', 'switch2', 'neural_core',
}

# Measured fraction of recipe input units returned when recycling.
YIELD_RATIO = 0.25


def api(session, method, path, **data):
    """Call the API, retrying through the 5-req/sec limiter AND network faults.

    A long recycling run WILL hit a read timeout eventually; an unhandled one
    loses the whole in-memory tally, so every network exception is retried with
    backoff rather than raised.
    """
    for attempt in range(8):
        try:
            r = session.request(method, f'{BASE}{path}',
                                data=data if method != 'GET' else None,
                                params=data if method == 'GET' else None, timeout=25)
            try:
                d = r.json()
            except ValueError:
                d = {'error': 'bad_json', 'body': r.text[:200]}
        except requests.exceptions.RequestException as ex:
            # timeout / connection reset / DNS blip: back off and retry
            time.sleep(min(2 ** attempt, 20))
            d = {'error': 'network', 'detail': type(ex).__name__}
            continue
        if isinstance(d, dict) and d.get('error') == 'rate_limit':
            time.sleep(float(d.get('retry_after', 1)) + 0.3)
            continue
        return d
    return d if isinstance(d, dict) else {'error': 'retries_exhausted'}


def login(account):
    email, pw = load_credentials(account)
    s = requests.Session()
    j = s.post(f'{BASE}/farmer/login-token',
               data={'login': email, 'password': pw}, timeout=25).json()
    if 'farmer' not in j:
        sys.exit(f'login failed for {account}: {str(j)[:200]}')
    s.headers['Authorization'] = 'Bearer ' + j['token']
    return s, j['farmer']


def load_items():
    with open(os.path.join(HERE, 'item_get-all.json')) as f:
        raw = json.load(f)
    by_id, by_params = {}, {}
    for v in raw.values():
        by_id[int(v['id'])] = v
        if v.get('type') == 10 and str(v.get('params', '')).isdigit():
            by_params[int(v['params'])] = v['name']
    return by_id, by_params


def build_graph(session, by_id):
    """Returns (recipe, consumers, units) over ALL craftables.

    recipe[t]    = [(ingredient_template, qty), ...]
    consumers[t] = [results that consume t]
    units[t]     = total input units of t's recipe (drives the yield estimate)
    """
    schemes = api(session, 'GET', '/scheme/get-all')
    recipe, consumers, units = {}, defaultdict(list), {}
    if isinstance(schemes, dict) and 'error' not in schemes:
        for sc in schemes.values():
            if not isinstance(sc, dict) or 'result' not in sc:
                continue
            ings = [(i[0], i[1]) for i in sc.get('items', []) if i]
            recipe[sc['result']] = ings
            units[sc['result']] = sum(q for _, q in ings)
            for t, _ in ings:
                consumers[t].append(sc['result'])
    return recipe, consumers, units


def crafting_reserve(recipe, consumers, by_id, crafts):
    """Recursive component bill-of-materials to craft `crafts` of every target.

    Targets are the things we'd actually want to own:
      * terminal components  - craftable type-8 consumed by nothing
      * PROTECTED premium components (obsidian_plate etc.) - these ARE consumed
        by potions, so they are never "terminal", but we still want to craft them
      * craftable weapons (desert_saber / sun_spear eat iron_plate)
    Potions/skins are deliberately excluded: they burn premium components.
    """
    def is_comp(t):
        return by_id.get(t, {}).get('type') == 8

    def is_weapon(t):
        return by_id.get(t, {}).get('type') == 1

    targets = {t for t in recipe if is_comp(t) and t not in consumers}
    targets |= {t for t in recipe if by_id.get(t, {}).get('name') in PROTECTED}
    targets |= {t for t in recipe if is_weapon(t)}

    reserve = defaultdict(int)

    def expand(t, n, seen):
        if t in seen:          # guard against a cyclic recipe graph
            return
        for ing, q in recipe.get(t, []):
            if is_comp(ing):
                reserve[ing] += q * n
                expand(ing, q * n, seen | {t})

    for t in targets:
        expand(t, crafts, set())
    return reserve, targets


def equipped_templates(session, farmer):
    """template -> [leek names] for every component currently equipped."""
    eq = defaultdict(list)
    leeks = farmer.get('leeks', {})
    leeks = leeks.values() if isinstance(leeks, dict) else leeks
    for l in leeks:
        L = api(session, 'GET', f"/leek/get/{l['id']}")
        L = L.get('leek', L) if isinstance(L, dict) else {}
        for c in L.get('components', []) or []:
            eq[c.get('template')].append(L.get('name', '?'))
        time.sleep(0.25)
    return eq


def plan(farmer, eq, units, reserve, by_id, args):
    rows = []
    for c in farmer.get('components', []) or []:
        tpl, qty, sid = c['template'], c.get('quantity', 1), c['id']
        name = by_id.get(tpl, {}).get('name', str(tpl))
        if args.template and name != args.template:
            continue
        if tpl in eq:
            continue                      # equipped: never touch
        if name in PROTECTED:
            continue
        # keep the recursive crafting demand, plus a flat safety buffer
        keep = reserve.get(tpl, 0) + args.keep
        avail = qty - keep
        if avail <= 0:
            continue
        ru = units.get(tpl, 0)
        if ru < args.min_value:
            continue
        rows.append(dict(id=sid, tpl=tpl, name=name, qty=qty, take=avail,
                         keep=keep, craft=reserve.get(tpl, 0),
                         recipe=ru, each=ru * YIELD_RATIO))
    rows.sort(key=lambda r: -r['each'] * r['take'])
    if args.max:
        total, capped = 0, []
        for r in rows:
            if total >= args.max:
                break
            r = dict(r, take=min(r['take'], args.max - total))
            total += r['take']
            capped.append(r)
        rows = capped
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--account', default='main', choices=['main', 'cure'])
    ap.add_argument('--execute', action='store_true', help='actually recycle (default: dry run)')
    ap.add_argument('--keep', type=int, default=10,
                    help='safety buffer kept ON TOP of the crafting reserve (default 10)')
    ap.add_argument('--crafts', type=int, default=4,
                    help='reserve enough to craft N of every higher-tier target (default 4)')
    ap.add_argument('--min-value', type=int, default=20,
                    help='skip components whose recipe costs fewer than N input units (default 20)')
    ap.add_argument('--max', type=int, default=0, help='cap total units recycled (0 = no cap)')
    ap.add_argument('--template', help='only this component, by name (e.g. rgb)')
    ap.add_argument('--delay', type=float, default=0.28, help='seconds between calls (default 0.28)')
    args = ap.parse_args()

    by_id, alt_names = load_items()
    s, farmer = login(args.account)
    print(f"account={args.account} farmer={farmer.get('name')}")
    recipe, consumers, units = build_graph(s, by_id)
    reserve, targets = crafting_reserve(recipe, consumers, by_id, args.crafts)
    eq = equipped_templates(s, farmer)
    rows = plan(farmer, eq, units, reserve, by_id, args)

    if not rows:
        print('Nothing to recycle under these filters '
              f'(crafts={args.crafts}, keep={args.keep}, min-value={args.min_value}).')
        return

    total = sum(r['take'] for r in rows)
    print(f"\nReserving enough to craft {args.crafts} of each of {len(targets)} higher-tier "
          f"targets, +{args.keep} buffer.\n")
    print(f"{'component':<20}{'have':>6}{'craftRsv':>9}{'keep':>6}{'recycle':>9}"
          f"{'recipe':>8}{'~yield ea':>11}{'~total':>9}")
    for r in rows:
        print(f"{r['name']:<20}{r['qty']:>6}{r['craft']:>9}{r['keep']:>6}{r['take']:>9}"
              f"{r['recipe']:>8}{r['each']:>11.1f}{r['each'] * r['take']:>9.0f}")
    print(f"{'TOTAL':<20}{'':>6}{'':>9}{'':>6}{total:>9}{'':>8}{'':>11}"
          f"{sum(r['each'] * r['take'] for r in rows):>9.0f}")
    print(f"\nProtected (never recycled): equipped components, {len(PROTECTED)} premium templates, "
          f"the recursive crafting reserve above, and a {args.keep} buffer on every stack.")

    if not args.execute:
        print('\nDRY RUN — nothing destroyed. Re-run with --execute to perform it.')
        return

    print(f'\nRecycling {total} units... (irreversible)')
    got_res, got_alt = defaultdict(int), defaultdict(int)
    done = fails = 0
    t0 = time.time()

    def summary():
        print(f'\nDone: {done} recycled, {fails} failed, {time.time() - t0:.0f}s')
        print(f'Resources gained ({sum(got_res.values())} units):')
        for k, v in sorted(got_res.items(), key=lambda x: -x[1]):
            print(f'   {k:<22}+{v}')
        print(f'Alterations gained ({sum(got_alt.values())}):')
        for k, v in sorted(got_alt.items(), key=lambda x: -x[1]):
            print(f'   {k:<22}+{v}')

    # The tally lives in got_res/got_alt, so ANY exit path (crash, Ctrl-C,
    # too many failures) still reports what was actually gained.
    try:
        for r in rows:
            stop = False
            for _ in range(r['take']):
                d = api(s, 'POST', '/item/recycle', item_id=r['id'])
                if not isinstance(d, dict) or 'error' in d or not d.get('destroyed'):
                    fails += 1
                    if fails <= 5:
                        print(f"  ! {r['name']}: {str(d)[:120]}")
                    if fails > 25:
                        print('  too many failures, stopping.')
                        stop = True
                        break
                    continue
                done += 1
                for k, v in (d.get('resources') or {}).items():
                    got_res[by_id.get(int(k), {}).get('name', k)] += v
                for k, v in (d.get('alterations') or {}).items():
                    got_alt[alt_names.get(int(k), f'params:{k}')] += v
                if done % 100 == 0:
                    print(f'  {done}/{total} recycled ({time.time() - t0:.0f}s)', flush=True)
                time.sleep(args.delay)
            if stop:
                break
    except KeyboardInterrupt:
        print('\ninterrupted by user')
    finally:
        summary()


if __name__ == '__main__':
    main()
