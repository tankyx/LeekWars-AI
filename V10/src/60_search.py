# ---- 60_search: two-ply plan search ----------------------------------------
# Our plan (moves + item uses) -> each candidate end cell -> the enemy's best
# reply (their poison tick, their TP/MP/STR after our shackles, move to their
# best reachable cell, best packing of their own kit on our end cell) -> our
# poison tick -> value model from OUR side at the start of our next turn.
DMG_BUFFS = {E_BUFF_STR, E_RAW_STR, E_RAW_MAG, E_RAW_SCI, E_RAW_POW, E_BUFF_TP, E_RAW_TP}
MAX_ATTACK_CELLS = 18
MAX_END_CELLS = 10
MAX_ENEMY_CELLS = 24
FOLLOW_KILL = 0.9
AGGR = 0.3        # value of certain damage now, per full enemy HP bar
STALL_W = 0.01     # per cell beyond our attack range, ramping over the first 8 turns (draws are losses of talent)
FOLLOW_W = 0.3     # weight of the ply-3 follow-up (it is never answered: horizon effect)
DIAG = False
LAST_CX = [None]


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
        cap = it.max_uses
        if all(e[0] != E_DAMAGE and (e[3] or 0) > 0 and not ((e[5] or 0) & 1) for e in it.effects):
            cap = 1        # a repeat only replaces the same non-stackable effect
        while used.get(it.id, 0) < cap:
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
        # enemy chips ready at the start of their next turn (cooldowns tick then)
        self.b_off = [it for it in B0['items'] if it.offensive and not it.special and it.current_cooldown() <= 1]
        self.b_vals = {it.id: quick_value(it, B0, A0) for it in self.b_off}
        self.b_maxr = max([it.maxr for it in self.b_off] + [0])
        self.b_reach = {}
        self.replies = {}
        self.a_off = [it for it in A0['items'] if it.offensive and not it.special]
        self.a_vals = {it.id: quick_value(it, A0, B0) for it in self.a_off}

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
    ret = int(a['groups'].get('dmg_return', 0))
    key = (our_cell, tp, mp, int(d_str), ret, int(a['abs']), int(a['rel']))
    rep = cx.replies.get(key)
    if rep is None:
        # rational enemy: maximise (HP they take off us) - (HP they lose to our
        # damage return / our life steal); not attacking (net 0) is always allowed
        best = (0.0, B0['cell'], [])
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
            ta = copy_side(a); tb = copy_side(b); ts = {'tp': 0, 'mp': 0}
            for it in acts:
                if it.offensive:
                    apply_item(it, tb, ta, ts)
            net = (a['life'] - ta['life']) - (b['life'] - tb['life'])
            if net > best[0]:
                best = (net, ec, acts)
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


def follow_up(cx, a, b, our_cell, ec):
    """Our best attack next turn if we can reach the enemy (MP + range after
    their shackles on us); applied to copies. Returns the new distance."""
    A0 = cx.A0
    d_tp = a['groups']['shk_tp'] - A0['groups']['shk_tp']
    d_mp = a['groups']['shk_mp'] - A0['groups']['shk_mp']
    tp = max(0, int(A0['tp_live'] - d_tp)); mp = max(0, int(A0['mp_live'] - d_mp))
    dist = Field.cellDistance(our_cell, ec) or 0
    need = max(0, dist - mp)
    usable = [it for it in cx.a_off if it.minr <= max(need, it.minr) <= it.maxr and cx.a_vals.get(it.id, 0) > 0
              and need <= it.maxr]
    if not usable:
        return dist
    order = sorted(usable, key=lambda it: -cx.a_vals[it.id] / max(1, it.cost))
    s = {'tp': 0, 'mp': 0}; used = {}; held = A0['weapon']
    for it in order:
        while used.get(it.id, 0) < it.max_uses:
            if not it.weapon and it.cooldown > 0 and used.get(it.id, 0) > 0:
                break
            cost = it.cost + (1 if it.weapon and held != it.id else 0)
            if cost > tp:
                break
            apply_item(it, a, b, s); tp -= cost
            used[it.id] = used.get(it.id, 0) + 1
            if it.weapon:
                held = it.id
    return max(need, min(it.minr for it in usable))


def leaf(cx, A1, B1, our_cell, turn):
    """Ply 2: enemy reply; ply 3: our follow-up attack; value at the start of
    the enemy's next turn (1 - their P(win))."""
    a, b, ec = enemy_reply(cx, A1, B1, our_cell)
    cx.last_reply = A1['life'] - a['life']
    if b['life'] <= 0:
        return 1.0
    tick = a['groups'].get('poison', 0)
    if tick > 0:
        dmg = min(a['life'], tick)
        a['life'] -= dmg; a['max'] -= dmg * 0.10; a['burn'] += dmg * 0.10
    if a['life'] <= 0:
        return 0.0
    d0 = Field.cellDistance(our_cell, ec) or 0
    los0 = bool(Field.lineOfSight(our_cell, ec))
    # after the enemy's reply it is OUR turn: score from our side as the actor
    v_no = value(features(turn + 1, d0, los0, a, b), key=('o', d0, los0))
    if FOLLOW_W <= 0:
        return v_no
    a2 = copy_side(a); b2 = copy_side(b)
    d = follow_up(cx, a2, b2, our_cell, ec)
    # a follow-up "kill" is optimistic (no LoS / movement / reply): clamp the
    # enemy at 1 HP and let the model score it, so plans stay differentiated
    if b2['life'] <= 0:
        b2['life'] = 1.0
    los = los0 if d == d0 else True
    v_f = 1.0 - value(features(turn + 1, d, los, b2, a2), key=('f', d, los))
    if DIAG:
        cx.last_leaf = (a['life'], b['life'], d0, los0, v_no, v_f, b2['life'])
    return FOLLOW_W * v_f + (1.0 - FOLLOW_W) * v_no


def end_cells(from_cell, reach, ecell):
    """Stay, approach (nearest to the enemy), retreat (farthest) and hidden
    cells; validated later by real path length."""
    by_d = sorted(reach, key=lambda c: (Field.cellDistance(c, ecell) or 0))
    near = by_d[:6]
    far = by_d[::-1][:6]
    hidden = [c for c in by_d[::-1][:40] if not Field.lineOfSight(c, ecell)][:4]
    out = [from_cell]
    for c in near + far + hidden:
        if c not in out:
            out.append(c)
    return out


def useful_now(it, A, B, cx):
    """A self item is only offered when it can matter now: heals when HP is
    missing, antidote when poisoned, reflect / shields when the enemy can
    reach our current cell next turn (their MP + range)."""
    types = {e[0] for e in it.effects}
    missing = A['max'] - A['life']
    if E_HEAL in types and not (types - {E_HEAL}):
        amt = sum(avg(e) for e in it.effects if e[0] == E_HEAL) * (1 + max(0, A['cur']['wisdom']) / 100.0)
        return missing > 0.3 * amt
    if E_ANTIDOTE in types:
        return A['groups'].get('poison', 0) > 0
    if types & {E_RETURN, E_ABS_SHIELD, E_REL_SHIELD, E_RAW_ABS, E_RAW_REL}:
        d = Field.cellDistance(A['cell'], B['cell']) or 0
        return d <= B['mp_live'] + cx.b_maxr
    return True


def choose_plan(A, B, cell0, tp0, mp0, weapon0, items):
    t = Fight.turn
    cx = Ctx(A, B)
    LAST_CX[0] = cx
    if DIAG and t <= 2:
        d0 = Field.cellDistance(A['cell'], B['cell']) or 0
        log('V10REACH T%d d=%s our_mp=%s their_mp=%s their_maxr=%s' % (t, d0, A['mp_live'], B['mp_live'], cx.b_maxr))
    offensive = [it for it in items if it.offensive and not it.special and it.current_cooldown() == 0]
    selfish = [it for it in items if it.self_cast and not it.special and it.current_cooldown() == 0
               and useful_now(it, A, B, cx)]
    buffs = [it for it in selfish if any(e[0] in DMG_BUFFS for e in it.effects)]
    vals = {it.id: quick_value(it, A, B) for it in offensive}
    reach = reachable(cell0, mp0)
    ecell = B['cell']
    maxr = max([it.maxr for it in offensive] + [0])
    cells = [c for c, st in sorted(reach.items(), key=lambda kv: kv[1])
             if (Field.cellDistance(c, ecell) or 99) <= maxr][:MAX_ATTACK_CELLS]
    if cell0 not in cells:
        cells.insert(0, cell0)
    heals = [it for it in selfish if any(e[0] in (E_HEAL, E_VITALITY) for e in it.effects)]
    shields = [it for it in selfish if any(e[0] in (E_ABS_SHIELD, E_REL_SHIELD, E_RAW_ABS, E_RAW_REL, E_RETURN) for e in it.effects)]
    best_heal = sorted(heals, key=lambda i: -sum(avg(e) for e in i.effects if e[0] in (E_HEAL, E_VITALITY)) / max(1, i.cost))[:1]
    prefixes = [[]]
    if buffs:
        prefixes.append([('use', it, cell0) for it in buffs])
    if best_heal:
        prefixes.append([('use', it, cell0) for it in best_heal])
        if buffs:
            prefixes.append([('use', it, cell0) for it in best_heal + buffs])
    if shields:
        prefixes.append([('use', it, cell0) for it in shields[:2]])
    plans = []
    for pre in prefixes:
        pre_cost = sum(st[1].cost for st in pre)
        for c in cells:
            for key in ('ratio', 'raw', 'weapons'):
                att = pack(c, ecell, offensive, tp0 - pre_cost, weapon0, vals, key)
                plans.append(pre + ([('move', c)] if c != cell0 else []) + [('use', it, ecell) for it in att])
    # split plans: chips from one cell, weapons from another (ranges differ)
    chips_off = [it for it in offensive if not it.weapon]
    weap_off = [it for it in offensive if it.weapon]
    if chips_off and weap_off:
        top = cells[:6]
        for c1 in top:
            p1 = pack(c1, ecell, chips_off, tp0, weapon0, vals, 'ratio')
            if not p1:
                continue
            left = tp0 - sum(it.cost for it in p1)
            for c2 in top:
                if c2 == c1:
                    continue
                p2 = pack(c2, ecell, weap_off, left, weapon0, vals, 'ratio')
                if p2:
                    plans.append([('move', c1)] + [('use', it, ecell) for it in p1]
                                 + [('move', c2)] + [('use', it, ecell) for it in p2])
    if selfish:
        tp = tp0; st = []
        for it in sorted(selfish, key=lambda i: i.cost):
            if it.cost <= tp:
                st.append(('use', it, cell0)); tp -= it.cost
        plans.append(st)
    plans.append([])
    best = (-1.0, None, None); evaluated = 0; seen = {}
    diag_best = None
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
            v = 1.1 if B1['life'] <= 0 else leaf(cx, A1, B1, e, t)
            # certain damage now is worth more than the model's uncertain future
            v += AGGR * dealt / max(1.0, B['max'])
            # anti-stall: ending far outside our attack range costs a little, more as the fight drags
            de = Field.cellDistance(e, ecell) or 0
            if de > maxr:
                v -= STALL_W * (de - maxr) * min(1.0, t / 8.0)
            evaluated += 1
            if DIAG and (diag_best is None or dealt > diag_best[1] or (dealt == diag_best[1] and v > diag_best[0])):
                diag_best = (v, dealt, e, len(plan), getattr(cx, 'last_leaf', None))
            if DIAG and v > best[0]:
                cx.best_leaf = getattr(cx, 'last_leaf', None)
            if v > best[0]:
                best = (v, plan + ([('move', e)] if e != c1 else []),
                        (dealt, Field.cellDistance(e, ecell), bool(Field.lineOfSight(e, ecell)), getattr(cx, 'last_reply', 0)))
    if DIAG and diag_best is not None:
        fmt = lambda L: 'none' if L is None else 'ourHP %.0f enHP %.0f d %s los %s v_no %.3f v_f %.3f enHP_after_follow %.0f' % L
        log('V10DIAG T%d MAXDMG V=%.3f dealt=%.0f [%s] || CHOSEN V=%.3f dealt=%.0f [%s]' % (
            t, diag_best[0], diag_best[1], fmt(diag_best[4]), best[0], best[2][0] if best[2] else -1, fmt(getattr(cx, 'best_leaf', None))))
    return best, evaluated
