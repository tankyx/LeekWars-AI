#!/usr/bin/env python3
"""
Plan (and optionally apply) component alterations — LeekWars 2026-09 feature.

API (from /api/service/get-all):
  POST /component/alteration-preview {component_id, alterations}  -> free, non-destructive
  POST /component/alter             {component_id, alterations}   -> APPLIES, can BREAK the component
`alterations` is a JSON dict {alteration_PARAMS: quantity}, max 8 total.

Preview returns:
  rolls{stat:{points}}  what you'd gain
  probability           chance the alteration succeeds
  break_probability     chance the component is DESTROYED
  fits / overfilled     capacity flags
  dose / power          load model
  habs_cost             cost in habs

Mechanics learned by probing (2026-09-14):
  * Alteration families must match the component family. Organic components
    (apple/strawberry/hylocereus) take cast_iron..nitinol + supercapacitor..
    oscillator; metal (iron_plate/obsidian_plate/propulsor) take the vitamins
    plus electrum/magnalium/zircaloy/invar; electronic (core/ram/motherboard/cd)
    take the vitamins plus clock/servomotor/coprocessor/register. Mismatch =>
    "indivisible_wrong_family" or probability 0.
  * Probability rises when the alteration's stat matches a stat the component
    already has (life alteration on a life component ~0.95 vs ~0.54 off-stat).
  * Higher-tier components absorb higher-power alterations: vitamin_d (+50 life,
    power 50) is impossible on apple but 0.95 on obsidian_plate.
Because the rules are fiddly, this tool does NOT model them — it asks the
server via preview and keeps whatever scores best.

Usage:
  python3 tools/alter_components.py --list
  python3 tools/alter_components.py --component obsidian_plate
  python3 tools/alter_components.py --component obsidian_plate --max-break 0.02
  python3 tools/alter_components.py --component obsidian_plate --apply
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lw_api import LWSession  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# Stat weights for scoring a roll. Tuned for this project's builds: survival and
# damage matter, frequency/science far less. Override with --weights.
DEFAULT_WEIGHTS = {
    'life': 1.0, 'strength': 4.0, 'resistance': 3.0, 'wisdom': 1.5,
    'magic': 4.0, 'agility': 2.0, 'science': 1.0, 'frequency': 0.3,
    'tp': 120.0, 'mp': 120.0, 'cores': 20.0, 'ram': 20.0,
}


def load_items():
    with open(os.path.join(HERE, 'item_get-all.json')) as f:
        raw = json.load(f)
    by_id = {int(v['id']): v for v in raw.values()}
    params2 = {int(v['params']): v for v in raw.values()
               if v.get('type') == 10 and str(v.get('params', '')).isdigit()}
    return by_id, params2


def score(rolls, weights):
    return sum(weights.get(k, 1.0) * (v.get('points', 0) or 0) for k, v in (rolls or {}).items())


def preview(lw, cid, combo):
    return lw.post('/component/alteration-preview', component_id=cid,
                   alterations=json.dumps({str(k): v for k, v in combo.items()}))


def greedy_plan(lw, cid, stock, weights, max_break, max_alts, verbose=True):
    """Greedily add the alteration that most improves expected score.

    Expected score = score(rolls) * probability, rejecting any combo whose
    break_probability exceeds max_break. The server scores every candidate, so
    no family/capacity rules are hardcoded here.
    """
    combo, best_prev, tried = {}, None, 0
    while sum(combo.values()) < max_alts:
        best, best_ev, best_res = None, (best_prev['ev'] if best_prev else 0.0), None
        for p, have in sorted(stock.items()):
            if combo.get(p, 0) >= have:
                continue
            cand = dict(combo)
            cand[p] = cand.get(p, 0) + 1
            r = preview(lw, cid, cand)
            tried += 1
            time.sleep(0.32)
            if not isinstance(r, dict) or 'error' in r:
                continue
            if r.get('break_probability', 1) > max_break:
                continue
            ev = score(r.get('rolls'), weights) * r.get('probability', 0)
            if ev > best_ev + 1e-9:
                best, best_ev, best_res = p, ev, r
        if best is None:
            break
        combo[best] = combo.get(best, 0) + 1
        best_prev = dict(res=best_res, ev=best_ev)
        if verbose:
            print(f"   + {best:<3} -> ev={best_ev:.1f} prob={best_res['probability']:.3f} "
                  f"break={best_res['break_probability']:.4f} rolls="
                  f"{ { k: v.get('points') for k, v in (best_res.get('rolls') or {}).items() } }",
                  flush=True)
    return combo, best_prev, tried


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--account', default='main', choices=['main', 'cure'])
    ap.add_argument('--list', action='store_true', help='list components and alteration stock')
    ap.add_argument('--component', help='component name to plan for (e.g. obsidian_plate)')
    ap.add_argument('--max-break', type=float, default=0.01,
                    help='reject any plan whose break chance exceeds this (default 0.01 = 1%%)')
    ap.add_argument('--max-alts', type=int, default=8, help='max alterations per component (server cap 8)')
    ap.add_argument('--apply', action='store_true', help='APPLY the plan (gamble: can destroy the component)')
    args = ap.parse_args()

    by_id, params2 = load_items()
    lw = LWSession(args.account)
    comps = lw.farmer.get('components', []) or []
    stock = {}
    for a in lw.farmer.get('alterations', []) or []:
        it = by_id.get(a['template'])
        if it and str(it.get('params', '')).isdigit():
            stock[int(it['params'])] = a['quantity']

    if args.list or not args.component:
        print('COMPONENTS:')
        for c in sorted(comps, key=lambda x: -x['quantity']):
            print(f"   {by_id.get(c['template'], {}).get('name', c['template']):<20}"
                  f"x{c['quantity']:<6} id={c['id']}")
        print('\nALTERATION STOCK (params, name, qty):')
        for p, q in sorted(stock.items(), key=lambda x: -x[1]):
            print(f"   {p:>3} {params2.get(p, {}).get('name', '?'):<18} x{q}")
        return

    target = next((c for c in comps
                   if by_id.get(c['template'], {}).get('name') == args.component), None)
    if not target:
        sys.exit(f'no component named {args.component} in inventory (try --list)')

    print(f"Planning alterations for {args.component} (id={target['id']}, "
          f"x{target['quantity']}), max_break={args.max_break}, max {args.max_alts} alterations")
    combo, best, tried = greedy_plan(lw, target['id'], stock, DEFAULT_WEIGHTS,
                                     args.max_break, args.max_alts)
    if not combo:
        print('No alteration improves this component within the break limit '
              '(family mismatch, or every candidate is too risky).')
        return

    r = best['res']
    named = {params2.get(p, {}).get('name', p): q for p, q in combo.items()}
    print(f"\nBEST PLAN: {named}")
    print(f"   gains      : { { k: v.get('points') for k, v in (r.get('rolls') or {}).items() } }")
    print(f"   success    : {r['probability']:.3f}")
    print(f"   break risk : {r['break_probability']:.4f}")
    print(f"   habs cost  : {r['habs_cost']}   (fits={r.get('fits')}, overfilled={r.get('overfilled')})")
    print(f"   previews evaluated: {tried}")

    if not args.apply:
        print('\nPREVIEW ONLY — nothing applied. Re-run with --apply to gamble on it.')
        return

    print('\nApplying...')
    d = lw.post('/component/alter', component_id=target['id'],
                alterations=json.dumps({str(k): v for k, v in combo.items()}))
    print('result:', json.dumps(d)[:400])


if __name__ == '__main__':
    main()
