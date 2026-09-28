# ---- 60_search: two-ply plan search ----------------------------------------
# Our plan (moves + item uses) -> each candidate end cell -> the enemy's best
# reply (their poison tick, their TP/MP/STR after our shackles, move to their
# best reachable cell, best packing of their own kit on our end cell) -> our
# poison tick -> value model from OUR side at the start of our next turn.
DMG_BUFFS = {E_BUFF_STR, E_RAW_STR, E_RAW_MAG, E_RAW_SCI, E_RAW_POW, E_BUFF_TP, E_RAW_TP}
MAX_ATTACK_CELLS = 18
MAX_END_CELLS = 10
MAX_ENEMY_CELLS = 24


def quick_value(it, C, T):
    """HP-equivalent of one use of `it` by C on T (packing order only)."""
    c = copy_side(C); t = copy_side(T); s = {'tp': 0, 'mp': 0}
    d = apply_item(it, c, t, s)
    shk = sum(t['groups'][k] - T['groups'][k] for k in ('shk_str', 'shk_mag', 'shk_tp', 'shk_mp'))
    return d + (t['burn'] - T['burn']) + 0.55 * (t['pf'] - T['pf']) + 2.0 * shk


def usable_from(cell, tcell, items):
    out = []
    d = Field.cellDistance(cell, tcell)
    if d is None:
        return out
    los = None
    for it in items:
        if d < it.minr or d > it.maxr:
            continue
        if cell != tcell and not launch_ok(it, cell, tcell):
            continue
        if it.los and cell != tcell:
            if los is None:
                los = bool(Field.lineOfSight(cell, tcell))
            if not los:
                continue
        if self_hit(it, cell, tcell):
            continue
        out.append(it)
    return out


def pack(cell, tcell, items, tp, weapon, vals, key):
    """Greedy packing of `items` usable from `cell` on `tcell` under `tp`."""
    usable = [it for it in usable_from(cell, tcell, items) if vals.get(it.id, 0) > 0]
    if key == 'ratio':
        order = sorted(usable, key=lambda it: -vals[it.id] / max(1, it.cost))
    elif key == 'raw':
        order = sorted(usable, key=lambda it: -vals[it.id])
    else:
        order = sorted([it for it in usable if it.weapon], key=lambda it: -vals[it.id] / max(1, it.cost))
    steps = []; held = weapon; used = {}
    for it in order:
        while used.get(it.id, 0) < it.max_uses:
            if not it.weapon and (it.cooldown > 0 and used.get(it.id, 0) > 0):
                break
            cost = it.cost + (1 if it.weapon and held != it.id else 0)
            if cost > tp:
                break
            steps.append(it); tp -= cost
            used[it.id] = used.get(it.id, 0) + 1
            if it.weapon:
                held = it.id
    return steps


class Ctx:
    """Per-turn caches."""
    def __init__(self, A0, B0):
        self.A0 = A0; self.B0 = B0
        self.b_off = [it for it in B0['items'] if it.offensive and not it.special]
        self.b_vals = {it.id: quick_value(it, B0, A0) for it in self.b_off}
        self.b_maxr = max([it.maxr for it in self.b_off] + [0])
        self.b_reach = {}
        self.replies = {}

    def enemy_cells(self, mp):
        if mp not in self.b_reach:
            self.b_reach[mp] = reachable(self.B0['cell'], mp)
        return self.b_reach[mp]


def enemy_reply(cx, A1, B1, our_cell):
    """Apply the enemy's best reply to copies; returns (A2, B2, enemy_cell)."""
    a = copy_side(A1); b = copy_side(B1)
    B0 = cx.B0
    # their turn start: poison ticks (erosion 10%)
    tick = b['groups'].get('poison', 0)
    if tick > 0:
        dmg = min(b['life'], tick)
        b['life'] -= dmg; b['max'] -= dmg * 0.10; b['burn'] += dmg * 0.10
    if b['life'] <= 0:
        return a, b, b['cell']
    d_tp = b['groups']['shk_tp'] - B0['groups']['shk_tp']
    d_mp = b['groups']['shk_mp'] - B0['groups']['shk_mp']
    d_str = b['groups']['shk_str'] - B0['groups']['shk_str']
    tp = max(0, int(B0['tp_live'] - d_tp)); mp = max(0, int(B0['mp_live'] - d_mp))
    b['cur']['strength'] -= d_str
    key = (our_cell, tp, mp, int(d_str))
    rep = cx.replies.get(key)
    if rep is None:
        best = (-1.0, B0['cell'], [])
        cells = sorted(cx.enemy_cells(mp).items(), key=lambda kv: kv[1])
        n = 0
        for ec, steps in cells:
            if n >= MAX_ENEMY_CELLS or ops() > OPS_STOP:
                break
            dd = Field.cellDistance(ec, our_cell)
            if dd is None or dd > cx.b_maxr:
                continue
            n += 1
            acts = pack(ec, our_cell, cx.b_off, tp, B0['weapon'], cx.b_vals, 'raw')
            if not acts:
                continue
            est = sum(cx.b_vals[it.id] for it in acts)
            if est > best[0]:
                best = (est, ec, acts)
        rep = (best[1], best[2])
        cx.replies[key] = rep
    ec, acts = rep
    s = {'tp': 0, 'mp': 0}
    for it in acts:
        if it.offensive:
            apply_item(it, b, a, s)
        else:
            apply_item(it, b, b, s)
    b['cell'] = ec
    return a, b, ec


def leaf(cx, A1, B1, our_cell, turn):
    a, b, ec = enemy_reply(cx, A1, B1, our_cell)
    if b['life'] <= 0:
        return 1.0
    tick = a['groups'].get('poison', 0)
    if tick > 0:
        dmg = min(a['life'], tick)
        a['life'] -= dmg; a['max'] -= dmg * 0.10; a['burn'] += dmg * 0.10
    if a['life'] <= 0:
        return 0.0
    d = Field.cellDistance(our_cell, ec) or 0
    los = bool(Field.lineOfSight(our_cell, ec))
    return value(features(turn + 1, d, los, a, b), key=(d, los))


def end_cells(from_cell, reach, ecell):
    far = sorted(reach, key=lambda c: -(Field.cellDistance(c, ecell) or 0))
    hidden = [c for c in far[:40] if not Field.lineOfSight(c, ecell)]
    return [from_cell] + far[:MAX_END_CELLS] + hidden[:4]


def choose_plan(A, B, cell0, tp0, mp0, weapon0, items):
    t = Fight.turn
    cx = Ctx(A, B)
    offensive = [it for it in items if it.offensive and not it.special and it.current_cooldown() == 0]
    selfish = [it for it in items if it.self_cast and not it.special and it.current_cooldown() == 0]
    buffs = [it for it in selfish if any(e[0] in DMG_BUFFS for e in it.effects)]
    vals = {it.id: quick_value(it, A, B) for it in offensive}
    reach = reachable(cell0, mp0)
    ecell = B['cell']
    maxr = max([it.maxr for it in offensive] + [0])
    cells = [c for c, st in sorted(reach.items(), key=lambda kv: kv[1])
             if (Field.cellDistance(c, ecell) or 99) <= maxr][:MAX_ATTACK_CELLS]
    if cell0 not in cells:
        cells.insert(0, cell0)
    prefixes = [[]]
    if buffs:
        prefixes.append([('use', it, cell0) for it in buffs])
    plans = []
    for pre in prefixes:
        pre_cost = sum(st[1].cost for st in pre)
        for c in cells:
            for key in ('ratio', 'raw', 'weapons'):
                att = pack(c, ecell, offensive, tp0 - pre_cost, weapon0, vals, key)
                plans.append(pre + ([('move', c)] if c != cell0 else []) + [('use', it, ecell) for it in att])
    if selfish:
        tp = tp0; st = []
        for it in sorted(selfish, key=lambda i: i.cost):
            if it.cost <= tp:
                st.append(('use', it, cell0)); tp -= it.cost
        plans.append(st)
    plans.append([])
    best = (-1.0, None, None); evaluated = 0; seen = {}
    for plan in plans:
        sig = tuple((s[0], s[1] if s[0] == 'move' else s[1].id) for s in plan)
        if sig in seen:
            continue
        seen[sig] = 1
        if ops() > OPS_STOP:
            break
        r = run_plan(plan, A, B, cell0, tp0, mp0, weapon0)
        if r is None:
            continue
        A1, B1, c1, dealt, sim = r
        for e in end_cells(c1, reach, ecell):
            if ops() > OPS_STOP:
                break
            if e != c1:
                pl = Field.pathLength(c1, e)
                if pl is None or pl < 0 or pl > sim['mp']:
                    continue
            v = 1.0 if B1['life'] <= 0 else leaf(cx, A1, B1, e, t)
            evaluated += 1
            if v > best[0]:
                best = (v, plan + ([('move', e)] if e != c1 else []),
                        (dealt, Field.cellDistance(e, ecell), bool(Field.lineOfSight(e, ecell))))
    return best, evaluated
