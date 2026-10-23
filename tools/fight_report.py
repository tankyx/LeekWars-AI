"""Fight diagnostics over a batch of fights, real or local: per leek damage dealt and taken (direct / poison / nova /
return, taken by source), heals, absolute shields, TP spent by category, item use, kills, deaths, AI errors.

    python3 tools/fight_report.py csv:last-pumpkin                          # last Pumpkin batch of boss_slot.csv
    python3 tools/fight_report.py csv:last-pumpkin --vs 'data/sim_pumpkin/d2_*.json'   # real vs simulated
    python3 tools/fight_report.py garden:20443:20 --by fight                # 20 newest solo garden fights of a leek
    python3 tools/fight_report.py 54297638 54297639 --rounds 1-8 --team them --summons --check

Selections (several may be mixed): fight ids (data/fight_cache/<id>.json, then data/boss_fights/v10_<id>.json and
<id>.json), file globs, csv:last | csv:last-<boss> | csv:<boss>:<rows|all> (data/ladder/boss_slot.csv, boss = pumpkin,
fennel or its number), garden:<leek id|name|any>:<n> (newest solo garden fights in data/fight_cache). In a worktree
the main checkout's data/ is searched first. Local files only, no network.

Values are per-fight means (--total: sums). --team us (default) = the side with our farmers' leeks, else team 1;
them = the other side; 1 / 2 = that team. Entities sharing a name (mobs, bulbs) are summed into one column; summons
count in TEAM and in their owner's "by summons" row (--summons: their own columns too).
Attribution: direct, nova and heals go to the acting entity (a plant while awake); damage return (108) to the entity
whose hit triggered it; poison/aftereffect and heal-over-time ticks at a turn start to the effect's caster (matched
to the target's periodic effects in insertion order, as Entity.startTurn applies them). Chip (12) and weapon (13) ids
are template ids in current logs, item ids in older ones: detected per fight from the effects that follow each use.
Real fights' winner is 1/2/0 (team 1 / team 2 / draw); local generator outputs carry a 0-based top-level winner.
"""
import argparse, csv, glob, json, os, re, statistics, sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = ROOT.split(os.sep + os.path.join('.claude', 'worktrees') + os.sep)[0]     # untracked data lives there
DATA = [d for d in dict.fromkeys((os.path.join(MAIN, 'data'), os.path.join(ROOT, 'data'))) if os.path.isdir(d)]
GEN = '/home/ubuntu/leek-wars-generator/data'
OURS = {18035, 17389}                    # farmers Virus (Brocanteur) and Cure
BOSSES = {'fennel': 2, 'pumpkin': 3}
CATS = ('attack', 'shield', 'heal', 'buff', 'debuff', 'summon', 'mobility', 'other')
KINDS = ('direct', 'poison', 'nova', 'return')

# ---- items: name, TP cost, category, item id ----
_EC = (('summon', {14, 15}), ('mobility', {10, 11, 46, 51, 53}), ('attack', {1, 13, 16, 25, 28, 30, 61, 64}),
       ('shield', {5, 6, 20, 29, 37, 54, 59}), ('heal', {2, 12, 23, 45, 49, 57}), ('mobility', {7, 31}),
       ('buff', {3, 4, 8, 21, 22, 32, 38, 39, 40, 41, 42, 44, 52, 62}),
       ('debuff', {9, 17, 18, 19, 24, 26, 27, 47, 48, 60}))      # first match wins (effect types, Effect.java)


def chip_cat(c):
    ids = {e['id'] for e in c['effects']}
    return next((cat for cat, s in _EC if ids & s), 'other')


_C = json.load(open(os.path.join(GEN, 'chips.json')))
_W = json.load(open(os.path.join(GEN, 'weapons.json')))
CHIP_I = {int(k): (v['name'], v['cost'], chip_cat(v), int(k)) for k, v in _C.items()}
CHIP_T = {v['template']: (v['name'], v['cost'], chip_cat(v), int(k)) for k, v in _C.items()}
WEAP_T = {int(k): (v['name'], v['cost'], 'attack', v['item']) for k, v in _W.items()}
WEAP_T[43] = ('glowing_saber', 12, 'attack', 609)          # server-only weapon, missing from the generator data
WEAP_I = {v[3]: v for v in WEAP_T.values()}
PERIODIC_DMG = {13, 25, 64}                                 # poison, aftereffect, superinfection
ACTING = {8, 9, 10, 12, 13, 16, 201, 203, 205}              # the entity has started acting (turn-start ticks are over)


def _int(x, default=None):
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def _data(j):
    f = j.get('fight', j)
    d = f.get('data', f)
    return f, (json.loads(d) if isinstance(d, str) else d)


# ---- selections ----
def _find(rel):
    return next((p for p in (os.path.join(d, rel) for d in DATA) if os.path.exists(p)), None)


def _fight_file(fid):
    return next((p for p in (_find('fight_cache/%s.json' % fid), _find('boss_fights/v10_%s.json' % fid),
                             _find('boss_fights/%s.json' % fid)) if p), None)


def _csv_ids(spec):
    m = re.fullmatch(r'csv:last(?:-(\w+))?|csv:(\w+):(\d+|all)', spec)
    if not m:
        sys.exit('bad csv selector %r (csv:last, csv:last-pumpkin, csv:pumpkin:3)' % spec)
    boss = m.group(1) or m.group(2)
    boss = BOSSES.get(boss, _int(boss)) if boss else None
    path = _find('ladder/boss_slot.csv')
    rows = [r for r in csv.DictReader(open(path)) if boss is None or _int(r.get('boss')) == boss]
    if not rows:
        sys.exit('no boss_slot.csv row for %r' % spec)
    k = 1 if m.group(1) is not None or m.group(3) is None else (len(rows) if m.group(3) == 'all' else int(m.group(3)))
    return [i for r in rows[-k:] for i in r['ids'].split()]


def _garden(spec):
    _, leek, n = spec.split(':')
    n = int(n); key = None if leek in ('', 'any') else leek.lower()
    d = _find('fight_cache')
    ids = sorted((int(f[:-5]) for f in os.listdir(d) if f[:-5].isdigit()), reverse=True)
    out = []; lid = _int(key)
    for fid in ids:
        try:
            f, _ = _data(json.load(open(os.path.join(d, '%d.json' % fid))))
        except Exception:
            continue
        if _int(f.get('type')) != 0 or _int(f.get('context')) != 2:
            continue
        ls = (f.get('leeks1') or []) + (f.get('leeks2') or [])
        if key is None:
            ok = any(l.get('farmer') in OURS for l in ls)
        else:
            hit = [l for l in ls if l.get('id') == lid or str(l.get('name', '')).lower() == key]
            ok = bool(hit)
            if hit and lid is None:
                lid = hit[0].get('id')               # a name found once: follow the leek id through renames
        if ok:
            out.append(os.path.join(d, '%d.json' % fid))
            if len(out) >= n:
                break
    return out[::-1]


def select(items):
    paths = []

    def by_id(fid):
        p = _fight_file(fid)
        if p:
            paths.append(p)
        else:
            print('missing fight %s' % fid, file=sys.stderr)
    for s in items:
        if s.startswith('csv:'):
            for fid in _csv_ids(s):
                by_id(fid)
        elif s.startswith('garden:'):
            paths += _garden(s)
        elif re.fullmatch(r'\d+', s):
            by_id(s)
        else:
            hits = glob.glob(s) or (glob.glob(os.path.join(MAIN, s)) + glob.glob(os.path.join(ROOT, s))
                                    if not os.path.isabs(s) else [])
            if not hits:
                print('no file matches %s' % s, file=sys.stderr)
            paths += sorted(hits, key=lambda p: [_int(t, t) for t in re.split(r'(\d+)', os.path.basename(p))])
    return list(dict.fromkeys(paths))


# ---- one fight ----
def detect(acts):
    """'t' (template) or 'i' (item) id space for chips (12) and weapons (13): vote with the item ids carried by the
    effects (302 / 301) that follow each use; without votes, the space that knows every id."""
    cv = Counter(); wv = Counter(); held = {}; cur = last = lastw = None; chips = set(); weps = set()
    for a in acts:
        c = a[0]
        if c == 7:
            cur = a[1]; last = lastw = None
        elif c == 12:
            last = a[1]; lastw = None; chips.add(a[1])
        elif c == 13:
            held[cur] = a[1]; weps.add(a[1]); last = lastw = None
        elif c == 16:
            lastw = held.get(cur); last = None
        elif c in (8, 10):
            last = lastw = None
        elif c == 302 and last is not None:
            cv['t'] += (CHIP_T.get(last) or (0,) * 4)[3] == a[1]; cv['i'] += last == a[1]
        elif c == 301 and lastw is not None:
            wv['t'] += (WEAP_T.get(lastw) or (0,) * 4)[3] == a[1]; wv['i'] += lastw == a[1]

    def pick(v, ids, T, I):
        if v['t'] or v['i']:
            return 't' if v['t'] >= v['i'] else 'i'
        return 'i' if ids and not ids <= set(T) and ids <= set(I) else 't'
    return pick(cv, chips, CHIP_T, CHIP_I), pick(wv, weps, WEAP_T, WEAP_I)


def _new():
    return {'n': Counter(), 'dealt': Counter(), 'taken': Counter(), 'from': Counter(), 'tp': Counter(),
            'uses': Counter(), 'deaths': []}


def parse(path, team='us', rounds=(1, 10 ** 9)):
    """One fight -> {'id', 'src', 'res', 'rounds', 'team', 'ents', 'stats', 'check', 'unknown'}."""
    j = json.load(open(path))
    f, d = _data(j)
    acts = d['actions']
    local = 'winner' in j and 'id' not in f
    fid = f.get('id') or os.path.splitext(os.path.basename(path))[0]
    E = {e['id']: {'name': e['name'], 'team': e['team'], 'summon': bool(e.get('summon')), 'farmer': e.get('farmer'),
                   'owner': None} for e in d['leeks']}
    real = {l['name']: l['id'] for k in ('leeks1', 'leeks2') for l in (f.get(k) or []) if isinstance(l, dict)}
    us = next((e['team'] for e in E.values() if e['farmer'] in OURS and not e['summon']), 1)
    T = {'us': us, 'them': 2 if us == 1 else 1}.get(str(team), _int(team, 1))
    win = _int(j.get('winner'), -1) + 1 if local else _int(f.get('winner'), 0)    # 1 / 2 team, 0 draw
    cs, ws = detect(acts)
    CH = CHIP_T if cs == 't' else CHIP_I; WP = WEAP_T if ws == 't' else WEAP_I
    S = defaultdict(_new); unknown = Counter(); chk = Counter()
    eff = {}; per = defaultdict(list); ticked = set(); held = {}; stack = []; last = {}    # last: victim -> dealer
    spent = Counter()                                       # TP spent by each entity this turn
    rnd = 1; cur = actor = lasthit = None; start = False; rmin, rmax = rounds

    def side(i):
        return (E.get(i) or {}).get('team')

    def dmg(kind, src, dst, v):
        if not (rmin <= rnd <= rmax):
            return
        S[dst]['taken'][kind] += v
        if side(dst) != T:
            chk['unattributed' if src is None else 'ours' if side(src) == T else 'theirs'] += v
        if src is None:
            S[dst]['from']['?'] += v
            return
        last[dst] = src
        if side(src) != side(dst):
            S[src]['dealt'][kind] += v
        else:
            S[src]['n']['ff'] += v
        name = (E.get(src) or {}).get('name', '?') + ('+' if side(src) == side(dst) else '')
        S[dst]['from']['self' if src == dst else name] += v

    def tick(typs, v):
        """Caster of the periodic effect on `cur` that produced this turn-start tick (in effect order)."""
        cand = [u for u in per[cur] if u not in ticked and u in eff and eff[u][2] in typs]
        if typs is PERIODIC_DMG:          # diagnostics: a tick above its effect's value means the list drifted
            chk['tick_none' if not cand else 'tick_eq' if eff[cand[0]][3] == v else
                'tick_lt' if v < eff[cand[0]][3] else 'tick_gt'] += 1
        if not cand:
            return None
        ticked.add(cand[0])
        return eff[cand[0]][0]

    def spend(cat, cost, use=None):
        spent[actor] += cost
        if w:
            S[actor]['tp'][cat] += cost
            if use:
                S[actor]['uses'][use] += 1

    for a in acts:
        c = a[0]
        w = rmin <= rnd <= rmax
        if c == 6:
            rnd = a[1]; continue
        if c == 7:
            cur = actor = a[1]; start = True; lasthit = None; ticked.clear(); stack = []; spent.clear()
            S[cur]['n']['turns'] += w
            continue
        if c == 17:
            stack.append(actor); actor = a[1]; continue
        if c == 18:
            actor = stack.pop() if stack else cur; continue
        if c in ACTING:
            start = False
        if c == 12:
            it = CH.get(a[1])
            if it is None:
                unknown['chip#%s' % a[1]] += 1; it = ('chip#%s' % a[1], 0, 'other', None)
            spend(it[2], it[1], it[0])
        elif c == 13:
            held[actor] = a[1]; spend('other', 1)
        elif c == 16:
            it = WP.get(held.get(actor))
            if it is None:
                unknown['weapon#%s' % held.get(actor)] += 1; it = ('weapon#%s' % held.get(actor), 0, 'attack', None)
            spend('attack', it[1], it[0])
        elif c == 203:
            spend('other', 1)                                  # say() costs 1 TP
        elif c == 10:
            if w and a[1] == actor and len(a) > 3 and isinstance(a[3], list):
                S[actor]['n']['mp'] += len(a[3])
        elif c == 8 and len(a) > 2:                            # [8, id, TP, MP]: totals, used TP reset
            chk['tp_turns'] += 1; chk['tp_over'] += spent[a[1]] > a[2]
            if w:
                S[a[1]]['n']['tp_avail'] += a[2]
        elif c in (101, 109):
            lasthit = a[1]; dmg('direct', actor, a[1], a[2])
        elif c == 107:
            dmg('nova', actor, a[1], a[2])
        elif c == 108:
            dmg('return', lasthit, a[1], a[2])
        elif c == 110:
            dmg('poison', tick(PERIODIC_DMG, a[2]) if start and a[1] == cur else actor, a[1], a[2])
        elif c == 103:
            src = actor
            if start and a[1] == cur:                      # heal-over-time tick (else the target's own effect)
                src = tick({2}, a[2])
                src = a[1] if src is None else src
            if w:
                S[src]['n']['heal_done'] += a[2]; S[a[1]]['n']['heal_recv'] += a[2]
        elif c in (301, 302) and len(a) > 7:
            eff[a[2]] = [a[3], a[4], a[5], a[6]]                 # caster, target, type, value
            if a[5] in PERIODIC_DMG or (a[5] == 2 and a[7] != 0):
                per[a[4]].append(a[2])
            if a[5] in (6, 37) and w:
                S[a[3]]['n']['shield_cast'] += a[6]; S[a[4]]['n']['shield_recv'] += a[6]
        elif c == 14 and a[1] in eff:
            e = eff[a[1]]; e[3] += a[2]
            if e[2] in (6, 37) and w:
                S[e[0]]['n']['shield_cast'] += a[2]; S[e[1]]['n']['shield_recv'] += a[2]
        elif c == 304 and a[1] in eff:
            eff[a[1]][3] = a[2]
        elif c == 303 and a[1] in eff:
            e = eff.pop(a[1])
            if a[1] in per[e[1]]:
                per[e[1]].remove(a[1])
        elif c == 5:
            if w:                     # killer = last damage dealer (the log names the victim itself on poison kills)
                S[a[1]]['deaths'].append(rnd)
                k = last.get(a[1], a[2] if len(a) > 2 else None)
                if k is not None and side(k) != side(a[1]):
                    S[k]['n']['kills_summ' if (E.get(a[1]) or {}).get('summon') else 'kills'] += 1
        elif c == 9 and len(a) > 2:
            e = E.setdefault(a[2], {'name': '?', 'team': side(a[1]), 'summon': True, 'farmer': None})
            e['owner'] = a[1]; e['summon'] = True
        elif c == 1002:
            if w and len(a) > 1:
                S[a[1]]['n']['err'] += 1
    for i, e in E.items():                           # summons' damage also shows on their owner
        if e['summon'] and e.get('owner') is not None:
            S[e['owner']]['n']['summ'] += sum(S[i]['dealt'].values())
    res = 'D' if win == 0 else 'W' if win == T else 'L'
    return {'id': fid, 'path': path, 'src': 'local' if local else 'real', 'res': res, 'rounds': rnd, 'team': T,
            'ents': E, 'real': real, 'stats': S, 'check': chk, 'unknown': unknown}


# ---- aggregation ----
def _merge(dst, src):
    for k in ('n', 'dealt', 'taken', 'from', 'tp', 'uses'):
        dst[k].update(src[k])
    dst['deaths'] += src['deaths'][:1]


def columns(F, summons=False):
    """{key: [per-fight records]} for our side's columns + 'TEAM', with display names and column order."""
    cols = defaultdict(list); names = {}; order = {}
    for fi, fr in enumerate(F):
        per = defaultdict(_new); team = _new()
        for i, e in fr['ents'].items():
            if e['team'] != fr['team']:
                continue
            s = fr['stats'].get(i) or _new()
            leek = not e['summon']
            r = _new(); _merge(r, s); r['n']['leeks'] = leek; r['n']['died'] = leek and bool(s['deaths'])
            if not leek:
                r['deaths'] = []
            _merge(team, r)
            if leek or summons:
                key = fr['real'].get(e['name']) if leek and (e['farmer'] or 0) > 0 else None
                key = key if key is not None else e['name'] + ('' if leek else '*')
                _merge(per[key], r); names[key] = e['name'] + ('' if leek else '*')
                order.setdefault(key, (not leek, i))
        for k, r in per.items():
            cols[k].append(r)
        cols['TEAM'].append(team)
    keys = sorted((k for k in cols if k != 'TEAM'), key=lambda k: order[k]) + ['TEAM']
    names['TEAM'] = 'TEAM'
    return keys, names, cols


def _mean(F, g, total):
    v = sum(g(r) for r in F)
    return v if total else v / len(F) if F else None


def _ratio(F, num, den):
    a = sum(num(r) for r in F); b = sum(den(r) for r in F)
    return 100.0 * a / b if b else None


ROWS = [('fights', lambda F, t: len(F), ''),
        ('turns', lambda F, t: _mean(F, lambda r: r['n']['turns'], t), ''),
        ('died %', lambda F, t: _ratio(F, lambda r: r['n']['died'], lambda r: r['n']['leeks']), '%'),
        ('death rnd med', lambda F, t: statistics.median([x for r in F for x in r['deaths']])
         if any(r['deaths'] for r in F) else None, ''),
        ('dealt', lambda F, t: _mean(F, lambda r: sum(r['dealt'].values()), t), '')] + \
       [('  ' + k, (lambda k: lambda F, t: _mean(F, lambda r: r['dealt'][k], t))(k), '') for k in KINDS] + \
       [('  by summons', lambda F, t: _mean(F, lambda r: r['n']['summ'], t), ''),
        ('friendly fire', lambda F, t: _mean(F, lambda r: r['n']['ff'], t), ''),
        ('taken', lambda F, t: _mean(F, lambda r: sum(r['taken'].values()), t), '')] + \
       [('  ' + k, (lambda k: lambda F, t: _mean(F, lambda r: r['taken'][k], t))(k), '') for k in KINDS] + \
       [(lbl, (lambda k: lambda F, t: _mean(F, lambda r: r['n'][k], t))(k), '') for lbl, k in
        (('heal done', 'heal_done'), ('heal recv', 'heal_recv'), ('abs shield cast', 'shield_cast'),
         ('abs shield recv', 'shield_recv'))] + \
       [('TP used %', lambda F, t: _ratio(F, lambda r: sum(r['tp'].values()), lambda r: r['n']['tp_avail']), '%'),
        ('TP spent', lambda F, t: _mean(F, lambda r: sum(r['tp'].values()), t), '')] + \
       [('  ' + k, (lambda k: lambda F, t: _mean(F, lambda r: r['tp'][k], t))(k), '') for k in CATS] + \
       [(lbl, (lambda k: lambda F, t: _mean(F, lambda r: r['n'][k], t))(k), '') for lbl, k in
        (('MP used', 'mp'), ('kills', 'kills'), ('kills (summons)', 'kills_summ'), ('AI errors (1002)', 'err'))]


def fmt(v, unit=''):
    if v is None:
        return '-'
    if unit == '%':
        return '%.0f%%' % v
    return '%.1f' % v if abs(v) < 100 and v != int(v) else '%d' % round(v)


def fmt_d(a, b, unit=''):
    if a is None or b is None:
        return '-'
    d = b - a
    s = ('%+.0f' % d) if unit == '%' or abs(d) >= 100 or d == int(d) else ('%+.1f' % d)
    return s + ('pp' if unit == '%' else '')


def header(label, F):
    res = Counter(fr['res'] for fr in F); src = Counter(fr['src'] for fr in F)
    rn = [fr['rounds'] for fr in F]
    return ('%s: %d fights (%s), team %s, W/L/D %d/%d/%d, rounds mean %.1f med %g' %
            (label, len(F), ' '.join('%s %d' % kv for kv in sorted(src.items())),
             '/'.join(sorted({str(fr['team']) for fr in F})), res['W'], res['L'], res['D'],
             statistics.mean(rn), statistics.median(rn))) if F else '%s: no fights' % label


def _top(c, n, F, total):
    k = 1 if total else max(1, len(F))
    return ', '.join('%s %s' % (name, fmt(v / k)) for name, v in c.most_common(n)) or '-'


def report_leek(A, B, la, lb, a):
    ka, na, ca = columns(A, a.summons)
    keys, names, cb = list(ka), dict(na), {}
    if B is not None:
        kb, nb, cb0 = columns(B, a.summons)
        byname = {na[k]: k for k in ka}
        for k in kb:
            m = k if k in na else byname.get(nb[k], k)
            cb[m] = cb0[k]
            if m not in names:
                names[m] = nb[k]; keys.insert(len(keys) - 1, m)
    w = [max(8, len(names[k]) + 1) for k in keys]
    lw = 17
    print(' ' * lw + ''.join(names[k].rjust(x) for k, x in zip(keys, w)))
    hidden = []; parent = ''
    for lbl, g, unit in ROWS:
        parent = parent if lbl.startswith(' ') else lbl.split()[0]
        va = [g(ca[k], a.total) if ca.get(k) else None for k in keys]
        vb = [g(cb[k], a.total) if cb.get(k) else None for k in keys] if B is not None else []
        if not any(va + vb) and lbl != 'fights':
            hidden.append(parent + ' ' + lbl.strip() if lbl.startswith(' ') else lbl); continue
        print(lbl.ljust(lw) + ''.join(fmt(v, unit).rjust(x) for v, x in zip(va, w)))
        if B is not None:
            print(('  ' + lb).ljust(lw)[:lw] + ''.join(fmt(v, unit).rjust(x) for v, x in zip(vb, w)))
            print('  delta'.ljust(lw) + ''.join(fmt_d(p, q, unit).rjust(x) for p, q, x in zip(va, vb, w)))
    if hidden:
        print('(0 everywhere: %s)' % ', '.join(hidden))
    per = 'total' if a.total else 'per fight'
    for title, fld in (('uses', 'uses'), ('taken from (+ = ally)', 'from')):
        print('\n%s, %s (top %d):' % (title, per, a.top))
        for k in keys:
            for lab, C in ((la, ca), (lb, cb)) if B is not None else (('', ca),):
                if C.get(k):
                    agg = Counter()
                    for r in C[k]:
                        agg.update(r[fld])
                    print('  %-16s %s' % ((names[k] + ' ' + lab).strip(), _top(agg, a.top, C[k], a.total)))


def report_fight(F, a):
    print('%-12s %-5s %3s %4s %8s %8s %7s %5s  %s' % ('fight', 'src', 'res', 'rnds', 'dealt', 'taken', 'heal',
                                                      'kills', 'deaths (name@round)'))
    for fr in F:
        S = fr['stats']; ours = [i for i, e in fr['ents'].items() if e['team'] == fr['team']]
        tot = lambda f: sum(f(S[i]) for i in ours if i in S)
        deaths = sorted((S[i]['deaths'][0], fr['ents'][i]['name']) for i in ours
                        if i in S and S[i]['deaths'] and not fr['ents'][i]['summon'])
        print('%-12s %-5s %3s %4d %8d %8d %7d %5d  %s' % (
            str(fr['id'])[:12], fr['src'], fr['res'], fr['rounds'], tot(lambda s: sum(s['dealt'].values())),
            tot(lambda s: sum(s['taken'].values())), tot(lambda s: s['n']['heal_done']),
            tot(lambda s: s['n']['kills']), ' '.join('%s@%d' % (n, r) for r, n in deaths) or '-'))


def check(label, F, rounds):
    """Independent recount of 101/107/108/109/110 values on the other side's entities, against the attribution:
    = our side's dealt (also summed from the TEAM column) + their own side (self / friendly AoE) + unattributed."""
    tot = Counter(); bad = []
    for fr in F:
        T = fr['team']; E = fr['ents']; raw = 0; rnd = 1
        for x in _data(json.load(open(fr['path'])))[1]['actions']:
            if x[0] == 6:
                rnd = x[1]
            elif x[0] in (101, 107, 108, 109, 110) and rounds[0] <= rnd <= rounds[1] and \
                    (E.get(x[1]) or {}).get('team') != T:
                raw += x[2]
        team = sum(sum(s['dealt'].values()) for i, s in fr['stats'].items() if (E.get(i) or {}).get('team') == T)
        c = fr['check']
        tot.update(raw=raw, team=team, **c)
        if raw != c['ours'] + c['theirs'] + c['unattributed'] or team != c['ours'] or c['unattributed']:
            bad.append('%s: raw %d, ours %d (TEAM %d), theirs %d, unattributed %d' % (
                fr['id'], raw, c['ours'], team, c['theirs'], c['unattributed']))
    print('check %s: other side took %d = our side %d + their own side %d (self / friendly AoE) + unattributed %d'
          '  [%s]' % (label, tot['raw'], tot['ours'], tot['theirs'], tot['unattributed'],
                      'OK' if not bad else '%d fights off' % len(bad)))
    for b in bad[:10]:
        print('   ' + b)
    print('  poison ticks: %d match their effect, %d lower (life-capped), %d higher (drift), %d without effect; '
          'turns spending more TP than the end-of-turn total %d/%d' % (
              tot['tick_eq'], tot['tick_lt'], tot['tick_gt'], tot['tick_none'], tot['tp_over'], tot['tp_turns']))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('sel', nargs='+', help='fight ids, globs, csv:..., garden:<leek>:<n>')
    p.add_argument('--vs', nargs='+', help='second selection, shown side by side with deltas (B - A)')
    p.add_argument('--by', choices=('leek', 'fight'), default='leek')
    p.add_argument('--rounds', default='', help='round window, e.g. 1-8, 10-, -5 or 3')
    p.add_argument('--team', default='us', help='us (default), them, 1 or 2')
    p.add_argument('--top', type=int, default=6, help='items / damage sources listed per leek')
    p.add_argument('--summons', action='store_true', help='summons get their own columns')
    p.add_argument('--total', action='store_true', help='sums instead of per-fight means')
    p.add_argument('--check', action='store_true', help='recount damage on the other side vs the attribution')
    a = p.parse_args()
    m = re.fullmatch(r'(\d*)(-?)(\d*)', a.rounds.strip())
    if not m:
        sys.exit('bad --rounds %r' % a.rounds)
    a.rmin = int(m.group(1) or 1)
    a.rmax = int(m.group(3)) if m.group(3) else (a.rmin if m.group(1) and not m.group(2) else 10 ** 9)
    sides = [('A', a.sel)] + ([('B', a.vs)] if a.vs else [])
    out = []
    for lab, items in sides:
        F = []
        for path in select(items):
            try:
                F.append(parse(path, a.team, (a.rmin, a.rmax)))
            except Exception as e:
                print('skip %s: %s' % (path, e), file=sys.stderr)
        out.append((lab, items, F))
    for lab, items, F in out:
        print(header('%s %s' % (lab, ' '.join(items)[:60]), F))
    if a.rounds:
        print('rounds %d-%s only' % (a.rmin, a.rmax if a.rmax < 10 ** 9 else 'end'))
    print()
    if a.by == 'fight':
        for lab, items, F in out:
            if len(out) > 1:
                print('[%s]' % lab)
            report_fight(F, a)
            print()
    else:
        A = out[0][2]; B = out[1][2] if len(out) > 1 else None
        if A:
            report_leek(A, B, 'A', 'B', a)
    unk = Counter()
    for _, _, F in out:
        for fr in F:
            unk.update(fr['unknown'])
    if unk:
        print('\nunknown item ids (no name / TP cost): ' + ', '.join('%s x%d' % kv for kv in unk.most_common()))
    if a.check:
        print()
        for lab, items, F in out:
            check(lab, F, (a.rmin, a.rmax))


if __name__ == '__main__':
    main()
