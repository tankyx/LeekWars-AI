#!/usr/bin/env python3
"""
Component & scheme audit: parses the leek-wars client catalog (items/prices,
component stats, scheme recipes), fetches both farmers' inventories, and
reports per-leek 8-slot upgrade opportunities from three sources:
  1. owned-but-unequipped components
  2. craftable schemes (owned scheme + resources available)
  3. habs-buyable components (catalog price <= habs balance)
"""
import requests, json, re, sys
from config_loader import load_credentials

CLIENT = '/home/ubuntu/leek-wars'

# ---------- parse client data ----------
items_src = open(f'{CLIENT}/src/model/items.ts').read()
items = {}  # template id -> dict
for m in re.finditer(r"'(\d+)': \{ id: \d+, name: '([a-z0-9_]+)', type: (\d+), price: (null|\d+)[^}]*?level: (\d+)[^}]*?rarity: (\d+) \}", items_src):
    price = 0 if m.group(4) == 'null' else int(m.group(4))
    items[int(m.group(1))] = {'name': m.group(2), 'type': int(m.group(3)),
                              'price': price, 'level': int(m.group(5)), 'rarity': int(m.group(6))}

comp_src = open(f'{CLIENT}/src/model/components.ts').read()
comp_stats = {}  # template id -> stats dict
for m in re.finditer(r"'(\d+)': \{ id: \d+, name: '([a-z0-9_]+)', stats: \[ (.*?) \], template: (\d+) \}", comp_src):
    stats = {}
    for sm in re.finditer(r"\[ '([a-z_]+)', (-?\d+) \]", m.group(3)):
        stats[sm.group(1)] = int(sm.group(2))
    comp_stats[int(m.group(4))] = {'name': m.group(2), 'stats': stats}

schemes_src = open(f'{CLIENT}/src/model/schemes.ts').read()
recipes = {}  # recipe id -> {result template, ingredients {resource tpl: qty}}
for m in re.finditer(r"'(\d+)': \{\s*id: \d+,\s*result: (\d+),\s*items: \[(.*?)\],\s*comment: '([a-z0-9_]+)'", schemes_src, re.S):
    ing = {}
    for im in re.finditer(r"\[ (\d+), (\d+) \]", m.group(3)):
        ing[int(im.group(1))] = int(im.group(2))
    recipes[int(m.group(1))] = {'result': int(m.group(2)), 'ing': ing, 'comment': m.group(4)}

# scheme items (type 9) link to recipes via their params field
scheme_item_to_recipe = {}  # scheme item template -> recipe id
for m in re.finditer(r"'(\d+)': \{ id: \d+, name: '(scheme_[a-z0-9_]+)', type: 9, price: [^,]*, level: [^,]*, params: '(\d+)'", items_src):
    scheme_item_to_recipe[int(m.group(1))] = int(m.group(3))

lang_comp = json.load(open(f'{CLIENT}/src/lang/en/component.json'))
lang_res = json.load(open(f'{CLIENT}/src/lang/en/resource.json'))

# equipped components per leek (from MCP get_leek, names resolved to templates)
EQUIPPED = {
    'AdaLovelace': [307, 314, 300, 381, 374, 303, 296, 292],
    'KurtGodel': [292, 306, 300, 381, 301, 315, 305, 307],
    'MargaretHamilton': [309, 314, 319, 308, 381, 300, 320, 292],
    'EdsgerDijkstra': [292, 381, 314, 307, 365, 295, 322, 298],
    'LeekRain': [381, 314, 383, 319, 303, 290, 295, 322],
    'DawnFall': [290, 314, 381, 321, 319, 297, 302, 304],
    'DuskHope': [321, 313, 319, 290, 317, 381, 295, 370],
    'ProdigalSon': [290, 381, 321, 311, 313, 295, 304, 298],
}
# hard constraint: total RAM = chip slots; every leek sits at its cap.
# (total RAM, chips equipped) — a swap may never drop RAM below chip count.
RAM_CHIPS = {
    'AdaLovelace': (18, 17), 'KurtGodel': (19, 19),
    'MargaretHamilton': (17, 17), 'EdsgerDijkstra': (16, 16),
    'LeekRain': (16, 16), 'DawnFall': (15, 15),
    'DuskHope': (13, 13), 'ProdigalSon': (13, 13),
}

def disp_comp(tpl):
    nm = comp_stats.get(tpl, {}).get('name', f'tpl{tpl}')
    return lang_comp.get(nm, nm)

def disp_res(tpl):
    # resource templates: item name lookup via items.ts then lang
    nm = items.get(tpl, {}).get('name', f'res{tpl}')
    return lang_res.get(nm, nm)

# ---------- fetch inventories ----------
def get_farmer(account):
    login, password = load_credentials(account=account)
    s = requests.Session()
    j = s.post("https://leekwars.com/api/farmer/login-token",
               data={"login": login, "password": password}).json()
    return j["farmer"]

farmers = {acc: get_farmer(acc) for acc in ("main", "cure")}

# ---------- value functions per leek build ----------
BUILDS = {
    # main
    'AdaLovelace':      {'tp': 200, 'strength': 1.6, 'life': 0.55, 'wisdom': 1.0, 'resistance': 0.5, 'science': 0.3, 'frequency': 0.2, 'mp': 120, 'agility': 0.0, 'magic': 0.0, 'cores': 50, 'ram': 2},
    'KurtGodel':        {'tp': 200, 'science': 1.6, 'life': 0.55, 'wisdom': 1.0, 'resistance': 0.5, 'frequency': 0.4, 'mp': 120, 'strength': 0.0, 'agility': 0.0, 'magic': 0.0, 'cores': 50, 'ram': 2},
    'MargaretHamilton': {'tp': 200, 'magic': 1.8, 'life': 0.55, 'wisdom': 1.0, 'resistance': 0.4, 'mp': 120, 'agility': 0.3, 'science': 0.0, 'strength': 0.0, 'frequency': 0.0, 'cores': 50, 'ram': 2},
    'EdsgerDijkstra':   {'tp': 200, 'strength': 1.2, 'agility': 1.0, 'life': 0.6, 'resistance': 0.6, 'mp': 100, 'wisdom': 0.5, 'science': 0.0, 'magic': 0.0, 'frequency': 0.1, 'cores': 50, 'ram': 2},
    # cure
    'LeekRain':         {'tp': 200, 'magic': 1.8, 'life': 0.55, 'wisdom': 1.0, 'resistance': 0.5, 'mp': 120, 'science': 0.3, 'agility': 0.0, 'strength': 0.0, 'frequency': 0.1, 'cores': 50, 'ram': 2},
    'DawnFall':         {'tp': 200, 'magic': 1.8, 'life': 0.55, 'wisdom': 1.0, 'resistance': 0.5, 'mp': 120, 'science': 0.0, 'agility': 0.0, 'strength': 0.0, 'frequency': 0.2, 'cores': 50, 'ram': 2},
    'DuskHope':         {'tp': 200, 'magic': 1.8, 'life': 0.55, 'wisdom': 1.0, 'resistance': 0.5, 'mp': 120, 'science': 0.0, 'agility': 0.0, 'strength': 0.0, 'frequency': 0.1, 'cores': 50, 'ram': 2},
    'ProdigalSon':      {'tp': 200, 'strength': 1.6, 'life': 0.55, 'resistance': 0.6, 'mp': 120, 'wisdom': 0.5, 'agility': 0.3, 'science': 0.0, 'magic': 0.0, 'frequency': 0.1, 'cores': 50, 'ram': 2},
}

def value_of(stats, weights):
    v = 0.0
    for k, n in stats.items():
        v += weights.get(k, 0.0) * n
    return v

# ---------- main analysis ----------
for acc, f in farmers.items():
    print("=" * 70)
    print(f"ACCOUNT: {acc} ({f['login']})  habs={f['habs']:,}  crystals={f['crystals']}")
    print("=" * 70)
    owned = {c['template']: c['quantity'] for c in f['components'] if c['quantity'] > 0}
    resources = {r['template']: r['quantity'] for r in f.get('resources', []) if r['quantity'] > 0}
    schemes = [s['template'] for s in f.get('schemes', [])]
    habs = f['habs']
    # recipe ingredients can be resources, components, chips or weapons —
    # availability is the union of all inventories (nothing is buyable)
    avail = dict(resources)
    for t, q in owned.items():
        avail[t] = avail.get(t, 0) + q
    for c in f.get('chips', []):
        if c['quantity'] > 0:
            avail[c['template']] = avail.get(c['template'], 0) + c['quantity']
    for w_ in f.get('weapons', []):
        if w_['quantity'] > 0:
            avail[w_['template']] = avail.get(w_['template'], 0) + w_['quantity']

    # leek equipped components: the leeks list in farmer payload carries component ids
    leeks_info = f.get('leeks', {})
    if isinstance(leeks_info, dict):
        leek_iter = leeks_info.values()
    else:
        leek_iter = leeks_info

    # craftable analysis
    craftable = []
    for stpl in schemes:
        rid = scheme_item_to_recipe.get(stpl)
        if rid is None or rid not in recipes:
            continue
        rec = recipes[rid]
        missing = {disp_res(k): (q - avail.get(k, 0)) for k, q in rec['ing'].items() if avail.get(k, 0) < q}
        res_tpl = rec['result']
        if res_tpl not in comp_stats:
            continue  # recipe produces an intermediate resource, not a component
        if not missing:
            craftable.append((res_tpl, stpl))

    print("\n-- CRAFTABLE NOW (scheme owned + resources available) --")
    if not craftable:
        print("  (none)")
    for res_tpl, stpl in sorted(craftable, key=lambda x: x[0]):
        st = comp_stats.get(res_tpl, {}).get('stats', {})
        print(f"  {disp_comp(res_tpl):28s} {st}  (scheme {items.get(stpl,{}).get('name','?')})")

    # near-miss schemes (missing <= 2 ingredient types)
    print("\n-- SCHEMES CLOSE TO CRAFTABLE --")
    shown = 0
    for stpl in schemes:
        rid = scheme_item_to_recipe.get(stpl)
        if rid is None or rid not in recipes:
            continue
        rec = recipes[rid]
        missing = {disp_res(k): (q - avail.get(k, 0)) for k, q in rec['ing'].items() if avail.get(k, 0) < q}
        if 0 < len(missing) <= 2:
            res_tpl = rec['result']
            st = comp_stats.get(res_tpl, {}).get('stats', {})
            print(f"  {disp_comp(res_tpl):28s} {st}  missing: {missing}")
            shown += 1
            if shown >= 10:
                break

    # per-leek audit (equipped templates from the MCP-resolved map)
    print("\n-- PER-LEEK SLOT AUDIT --")
    for lk in leek_iter:
        name = lk.get('name')
        if name not in BUILDS:
            continue
        w = BUILDS[name]
        eq_tpls = EQUIPPED.get(name, [])
        if not eq_tpls:
            continue
        equipped = []
        for t in eq_tpls:
            st = comp_stats.get(t, {}).get('stats', {})
            equipped.append((t, st, value_of(st, w)))
        equipped.sort(key=lambda x: x[2])
        weakest = equipped[:3]
        cur_total = sum(v for _, _, v in equipped)

        # candidate pool: owned (unequipped) + craftable
        cands = {}
        for t, q in owned.items():
            if t not in eq_tpls and t in comp_stats:
                cands[t] = 'owned x%d' % q
        for res_tpl, _ in craftable:
            if res_tpl not in eq_tpls:
                cands[res_tpl] = 'craftable'

        # feasible swaps only: never drop total RAM below equipped chip count
        ram_total, chip_count = RAM_CHIPS.get(name, (99, 0))
        swaps = []
        for t_out, st_out, v_out in equipped:
            ram_out = st_out.get('ram', 0)
            for t_in, src in cands.items():
                st_in = comp_stats[t_in]['stats']
                ram_in = st_in.get('ram', 0)
                if ram_total - ram_out + ram_in < chip_count:
                    continue
                gain = value_of(st_in, w) - v_out
                if gain > 20:
                    swaps.append((gain, t_out, st_out, v_out, t_in, st_in, src))
        swaps.sort(reverse=True)

        if not swaps:
            print(f"\n  {name}: optimal-ish (no feasible upgrade)")
            continue
        print(f"\n  {name}  (RAM {ram_total}, chips {chip_count}; gain = candidate value - slot value)")
        seen = set()
        shown = 0
        for gain, t_out, st_out, v_out, t_in, st_in, src in swaps:
            key = (t_out, t_in)
            if key in seen:
                continue
            seen.add(key)
            print(f"    out {disp_comp(t_out):24s} v={v_out:5.0f}  ->  in {disp_comp(t_in):24s} v={value_of(st_in, w):5.0f} (+{gain:4.0f}) [{src}]")
            shown += 1
            if shown >= 4:
                break
print("\nDONE")
