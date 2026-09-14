#!/usr/bin/env python3
"""
Alter every equipped component across the fleet, then equip the altered copies.

For each leek, for each component it has equipped, this takes ONE spare unit of
that template, pumps it with alterations (see alter_components.pump), and then
rewrites the leek's loadout so the altered variant is the one equipped.

EQUIPPING AN ALTERED COMPONENT (the non-obvious part):
  There is no "assign component instance to leek" endpoint. Components are
  equipped through `loadout/apply`, whose component entries look like
  {index, template, stats}. The `id` field is IGNORED, but **`stats` selects the
  altered variant** - set it to the altered item's stats map (e.g.
  {"resistance": 15}) and the server equips that exact instance. stats=null
  picks an arbitrary plain one.

Per-leek stat weights matter: buying `magic` for a STR bruiser is wasted habs
(that mistake cost 1.6M habs on a strawberry), so each leek gets weights derived
from its own build.

Usage:
  python3 tools/alter_fleet.py --dry-run
  python3 tools/alter_fleet.py --budget 4000000
  python3 tools/alter_fleet.py --budget 4000000 --only EdsgerDijkstra
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lw_api import LWSession            # noqa: E402
from alter_components import pump, load_items, score  # noqa: E402

# leek -> its Solo loadout id (loadout/get-all)
LOADOUTS = {'KurtGodel': 466, 'AdaLovelace': 786,
            'EdsgerDijkstra': 787, 'MargaretHamilton': 789}


def stat(leek, key):
    """TOTAL stat (capital + components + alterations), not the base.

    /leek/get exposes both `science` (base) and `total_science`. Reading the
    base mis-weighted KurtGodel: base SCI 290 fell under the >=300 gate so
    science scored 0.2 and wisdom (0.3) won, even though his real SCI is 500
    and his quantum_rifle's nova scales off it.
    """
    v = leek.get('total_' + key)
    return v if v is not None else (leek.get(key) or 0)


def weights_for(leek):
    """Weight stats by what this leek's build actually uses."""
    w = {'life': 1.0, 'wisdom': 0.3, 'science': 0.2, 'frequency': 0.0,
         'tp': 120.0, 'mp': 120.0, 'cores': 20.0, 'ram': 20.0,
         'strength': 0.0, 'magic': 0.0, 'agility': 0.0, 'resistance': 3.0}
    if stat(leek, 'strength') >= 300:
        w['strength'] = 5.0
    if stat(leek, 'magic') >= 300:
        w['magic'] = 5.0
    if stat(leek, 'agility') >= 300:
        w['agility'] = 2.5
    if stat(leek, 'science') >= 300:
        w['science'] = 1.0
    return w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--account', default='main', choices=['main', 'cure'])
    ap.add_argument('--budget', type=int, default=4000000, help='total habs to spend')
    ap.add_argument('--max-break', type=float, default=0.02)
    ap.add_argument('--max-total-break', type=float, default=0.30)
    ap.add_argument('--min-eff', type=float, default=0.00005)
    ap.add_argument('--only', help='restrict to one leek name')
    ap.add_argument('--dry-run', action='store_true', help='show the plan, alter nothing')
    args = ap.parse_args()

    by_id, params2 = load_items()
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'component_stats.json')) as f:
        cstats = json.load(f)
    lw = LWSession(args.account)
    stock = {}
    for a in lw.farmer.get('alterations', []) or []:
        it = by_id.get(a['template'])
        if it and str(it.get('params', '')).isdigit():
            stock[int(it['params'])] = a['quantity']

    leeks = lw.farmer.get('leeks', {})
    leeks = list(leeks.values()) if isinstance(leeks, dict) else list(leeks)
    spent_total = 0
    results = []

    for meta in leeks:
        name = meta.get('name')
        if args.only and name != args.only:
            continue
        if name not in LOADOUTS:
            print(f'-- {name}: no known loadout, skipping')
            continue
        L = lw.leek(meta['id'])
        w = weights_for(L)
        print(f"\n=== {name} (STR{L.get('strength')} MAG{L.get('magic')} "
              f"AGI{L.get('agility')} RES{L.get('resistance')}) "
              f"weights={ {k: v for k, v in w.items() if v} }")
        lo = next((x for x in lw.get('/loadout/get-all').get('loadouts', [])
                   if x['id'] == LOADOUTS[name]), None)
        if not lo:
            print('   no loadout, skipping')
            continue
        slots = [{k: v for k, v in c.items() if k in ('index', 'template', 'stats')}
                 for c in lo['components']]

        def push(trial):
            """Write `trial` slots to the loadout, apply, and report (filled, equipped)."""
            lw.call('PUT', '/loadout/update', set_id=lo['id'], name=lo['name'],
                    icon=lo.get('icon', ''), weapons=json.dumps(lo['weapons']),
                    chips=json.dumps(lo['chips']), components=json.dumps(trial),
                    stats=json.dumps(lo['stats']))
            time.sleep(0.5)
            lw.post('/loadout/apply', set_id=lo['id'], leek_id=meta['id'], use_restat='false')
            time.sleep(0.9)
            cur = [x for x in (lw.leek(meta['id']).get('components') or []) if x]
            return len(cur), {x['template']: x.get('stats') for x in cur if x.get('altered_power')}

        # COMPONENT SELECTION + PUSH THE WHOLE PROFILE.
        # Two separate questions:
        #  1) WHICH components to spend on - rank by how well the component's
        #     whole native profile matches this build (sum of weight x amount).
        #     Probability also rises with how much of a stat the component
        #     already has (obsidian_plate life 300 -> 0.950, strength 20 ->
        #     0.589), so a high-match component is both more valuable AND more
        #     reliable to alter.
        #  2) WHAT to boost on it - every stat it natively has, i.e. push the
        #     component beyond its own values rather than bolting on new ones.
        #     Stats the build does not value score 0 EV and are dropped by the
        #     efficiency floor inside pump(), so passing them all is safe.
        ranked = []
        for comp in (L.get('components') or []):
            if not comp:
                continue
            base = dict(cstats.get(str(comp['template']), {}).get('stats', []))
            on_stat = {k for k, v in base.items() if v > 0}
            if not on_stat:
                continue
            match = sum(w.get(k, 0) * v for k, v in base.items() if v > 0)
            if match <= 0:
                continue          # nothing this build cares about
            ranked.append((match, comp['template'], comp, on_stat, base))
        ranked.sort(key=lambda x: -x[0])

        for match, tpl, comp, on_stat, base in ranked:
            cname = by_id.get(tpl, {}).get('name', str(tpl))
            cur_stats = comp.get('stats') if comp.get('altered_power') else None
            valued = {k: base[k] for k in on_stat if w.get(k, 0) > 0}
            print(f'   {cname}: push {valued} (match {match:.0f})')
            stack = next((c for c in lw.farmer.get('components', [])
                          if c['template'] == tpl and not c.get('altered_power')
                          and c.get('quantity', 0) > 0), None)
            if not stack:
                print(f'   {cname}: no spare unit, keeping {cur_stats}')
                continue
            if spent_total >= args.budget:
                print('   budget exhausted.')
                break
            if args.dry_run:
                print(f'   {cname}: would push (spare x{stack["quantity"]})')
                continue
            print(f'   {cname}: pumping...', flush=True)
            cid, steps, spent, broke = pump(
                lw, stack['id'], stock, params2, w, args.max_break,
                budget=args.budget - spent_total, min_eff=args.min_eff,
                max_total_break=args.max_total_break, on_stat=on_stat)
            spent_total += spent
            lw = LWSession(args.account)
            it = next((c for c in lw.farmer.get('components', []) if c['id'] == cid), None)
            new_stats = it.get('stats') if it else None
            if not new_stats:
                # TP/MP/cores/ram alterations are "indivisible" and sit at
                # probability 0 on every component tested, so a high-weight
                # target can yield nothing. Do NOT consume the component -
                # let it fall through to its next-best stat.
                print(f'      -> nothing achievable ({spent} habs)')
                continue
            if cur_stats and score(
                    {k: {'points': v} for k, v in new_stats.items()}, w) <= score(
                    {k: {'points': v} for k, v in cur_stats.items()}, w):
                print(f'      -> {new_stats} not better than equipped {cur_stats}, leaving as is')
                continue
            trial = [dict(c) for c in slots]
            for c in trial:
                if c['template'] == tpl:
                    c['stats'] = new_stats
            filled, eq = push(trial)
            if filled == 8 and eq.get(tpl) == new_stats:
                slots = trial
                print(f'      -> EQUIPPED {new_stats} ({spent} habs)')
                results.append((name, cname, new_stats, spent))
            else:
                push(slots)      # revert; never leave a slot empty
                print(f'      -> {new_stats} would not bind (slots={filled}), reverted')

    print(f'\n===== TOTAL habs spent: {spent_total} =====')
    for n, c, st, sp in results:
        print(f'   {n:<18}{c:<18}{str(st):<34}{sp} habs')


if __name__ == '__main__':
    main()
