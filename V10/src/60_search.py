# ---- 60_search: two-ply plan search ----------------------------------------
# Our plan (moves + item uses) -> each candidate end cell -> the enemy's best
# reply (their poison tick, their TP/MP/STR after our shackles, move to their
# best reachable cell, best packing of their own kit on our end cell) -> our
# poison tick -> value model from OUR side at the start of our next turn.
DMG_BUFFS = {E_BUFF_STR, E_RAW_STR, E_RAW_MAG, E_RAW_SCI, E_RAW_POW, E_BUFF_TP, E_RAW_TP}
MAX_ATTACK_CELLS = 32
MAX_END_CELLS = 10
MAX_ENEMY_CELLS = 40
MAX_SPLASH_CELLS = 12   # cells per side tried for an area shot aimed next to the target
ANTIDOTE_TRIGGER = 250   # queued poison (HP) at which a rational enemy spends its antidote
FOLLOW_KILL = 0.9
CHASE_KILL = 0.95
AGGR = 0.3        # value of certain damage now, per full enemy HP bar
STALL_W = 0.01     # per cell beyond our attack range, ramping over the first 8 turns (draws are losses of talent)
# draw breaking: at turn 64 both alive = draw, so waiting loses value as the
# fight drags on. Pressure multiplies the damage-now and anti-stall terms:
# 1 until PRESSURE_T0, then +1 per 10 turns (x5 at turn 60), +0.5 per idle turn
PRESSURE_T0 = 20
IDLE = [0]          # consecutive turns in which neither side lost HP (set in turn())
STANDOFF_W = 0.05  # hidden, no damage, while a standoff lasts: extra cost x pressure
# leaf LoS: in prod data LoS at the actor's turn start rewards the actor (usually the
# opponent's positioning mistake); in V10 it is our own end-cell choice, already
# charged by the enemy-reply simulation. True = leaf scored at the average LoS.
LOS_NEUTRAL = False
HEALABLE_W = 0.6   # share of healable direct damage discounted (their ready heals would undo it)
ENGAGE_W = 0.03   # standoff (3+ idle turns, out of range): per cell closed toward the enemy x pressure


def pressure(t):
    return 1.0 + max(0.0, (t - PRESSURE_T0) / 10.0) + 0.5 * min(IDLE[0], 6)
FOLLOW_W = 0.3     # weight of the ply-3 follow-up (it is never answered: horizon effect)
# team fights: the enemy leeks other than the focus also shoot. Their threat on a
# cell (best packing of the items whose range + their MP reach it, LoS ignored) is
# taken off our HP after the focus' reply; they spread over our team, so only a share
OTHERS_W = 0.6
MAX_SAFE_CELLS = 6
DIAG = False
LAST_CX = None     # Ctx of the last search (read by leftover spending)


def quick_value(it, C, T):
    """HP-equivalent of one use of `it` by C on T (packing order only)."""
    c = copy_side(C); t = copy_side(T); s = {'tp': 0, 'mp': 0}
    d = apply_item(it, c, t, s)
    shk = sum(t['groups'][k] - T['groups'][k] for k in ('shk_str', 'shk_mag'))
    # TP / MP shackles: the damage they deny - target's damage per TP (kit: direct +
    # discounted poison) x TP removed x duration; MP denies movement, valued at a
    # quarter of that per MP point
    turns = max([e[3] or 1 for e in it.effects if e[0] in (E_SHK_TP, E_SHK_MP)] + [1])
    tk = T.get('kit') or (0, 0.0, 0.0, 0.0)
    t_dpt = tk[1] + 0.55 * tk[3]
    per_tp = t_dpt / max(1.0, T.get('tp_live') or T.get('tp') or 1)
    d_tp = t['groups']['shk_tp'] - T['groups']['shk_tp']
    d_mp = t['groups']['shk_mp'] - T['groups']['shk_mp']
    denied = turns * (per_tp * max(0.0, d_tp) + 0.25 * per_tp * max(0.0, d_mp))
    # shields / damage return taken off the target (liberation): abs shield blocks
    # each hit (~4 hits), rel % of ~2 turns of damage, return % of the same
    stripped = 4.0 * max(0.0, T['abs'] - t['abs']) + 20.0 * max(0.0, T['rel'] - t['rel']) \
        + 10.0 * max(0.0, T['groups'].get('dmg_return', 0) - t['groups'].get('dmg_return', 0))
    # vulnerability: the extra damage it enables over its ~2 turns, from the
    # caster's direct damage potential (kit) - % vuln and absolute vuln per hit
    kd = C['kit'][1] if C.get('kit') else 0.0
    dv = t['groups'].get('vuln', 0) - T['groups'].get('vuln', 0)
    dva = t['groups'].get('vuln_abs', 0) - T['groups'].get('vuln_abs', 0)
    stripped += 2.0 * (kd * max(0.0, dv) / 100.0 + 4.0 * max(0.0, dva))
    return d + (t['burn'] - T['burn']) + 0.55 * (t['pf'] - T['pf']) + 2.0 * shk + denied + stripped


def usable_from(cell, tcell, items):
    d, los, line, diag = geo(cell, tcell)
    if d is None:
        return []
    out = []
    for it in items:
        if d < it.minr or d > it.maxr:
            continue
        if cell != tcell and not launch_geo(it.launch, line, diag):
            continue
        if it.los and not los:
            continue
        if has_area(it) and in_area(it.area, tcell, cell) > 0:   # the area would hit the caster
            continue
        out.append(it)
    return out


_PACKS = {}    # geometry-keyed pack cache, cleared every turn


def pack(cell, tcell, items, tp, weapon, vals, key, tag=None):
    """Greedy packing of `items` usable from `cell` on `tcell` under `tp`.
    With `tag` the result is cached by geometry (usability only depends on
    distance, LoS and line/diagonal), shared across cells."""
    if tag is not None:
        g = geo(cell, tcell)
        ck = (tag, key, tp, weapon, g[0], g[1], g[2], g[3], cell == tcell)
        r = _PACKS.get(ck)
        if r is None:
            r = _pack(cell, tcell, items, tp, weapon, vals, key)
            _PACKS[ck] = r
        return r
    return _pack(cell, tcell, items, tp, weapon, vals, key)


def _pack(cell, tcell, items, tp, weapon, vals, key):
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
        self.b_antidote = [it for it in B0['items'] if not it.weapon and it.current_cooldown() <= 1
                           and any(e[0] == E_ANTIDOTE for e in it.effects)]
        self.b_maxr = max([it.maxr for it in self.b_off] + [0])
        # their healing capacity next turn: ready heal / vitality chips (cooldown
        # <= 1, from the engine), wisdom-scaled, best HP per TP within their TP.
        # Values our damage by what survives it (burst when their heals are down).
        wis = 1 + max(0, B0['cur'].get('wisdom', 0)) / 100.0
        hl = []
        for it in B0['items']:
            if it.weapon or it.offensive or it.special or it.current_cooldown() > 1:
                continue
            if it.cooldown < 0:          # once per fight (regeneration...): no window to play around
                continue
            amt = sum(avg(e) for e in it.effects if e[0] in (E_HEAL, E_VITALITY)) * wis
            if amt > 0:
                hl.append((amt, it.cost))
        tp = B0['tp_live']; hn = 0.0
        for amt, cost in sorted(hl, key=lambda x: -x[0] / max(1, x[1])):
            if cost <= tp:
                hn += amt; tp -= cost
        self.b_heal_next = hn
        # heals they would actually cast next turn (reply simulation): once-per-fight ones
        # (regeneration) included while unused - the big heal hemorrhage exists to deny
        self.b_heals = []
        for it in B0['items']:
            if it.weapon or it.offensive or it.special:
                continue
            if it.current_cooldown() > (0 if it.cooldown < 0 else 1):
                continue
            amt = sum(avg(e) for e in it.effects if e[0] == E_HEAL) * wis
            if amt > 0:
                self.b_heals.append((amt, it.cost))
        self.b_heals.sort(key=lambda x: -x[0] / max(1, x[1]))
        self.b_heal_full = sum(x[0] for x in self.b_heals)
        self.b_area = [it for it in self.b_off if has_area(it)]   # enemy items that splash
        self.b_reach = {}
        self.replies = {}
        self.b_opts = {}       # (our cell, tp, mp) -> enemy attack options
        self.fu = {}           # (tp, need) -> our follow-up attack sequence
        self.last_reply = 0.0
        self.others = []       # (snapshot, offensive items) of the non-focus enemy leeks
        self.oth = {}          # (enemy index, distance, our abs, our rel) -> threat
        self.oth_dm = {}       # (enemy index, our abs, our rel) -> {item id: damage on us}
        self.last_leaf: object = None
        self.best_leaf: object = None
        self.best_atk: tuple = (-1.0, 0.0, '')   # best plan that deals damage: (value, dealt, desc)
        self.n_atk = 0                    # attacking plans evaluated
        self.plen = {}         # (from, to) -> path length
        self.ends: list = []   # (near, far, hidden) end cells, independent of the plan
        self.a_off = [it for it in A0['items'] if it.offensive and not it.special]
        self.a_vals = {it.id: quick_value(it, A0, B0) for it in self.a_off}
        # one turn of DIRECT damage (chase mode / kill reach): queued poison and
        # shackles in a_vals are not damage this turn
        direct = {}
        for it in self.a_off:
            c = copy_side(A0); t = copy_side(B0)
            direct[it.id] = apply_item(it, c, t, {'tp': 0, 'mp': 0})
        tp = A0['tp_live']; kd = 0.0
        for it in sorted(self.a_off, key=lambda i: -direct[i.id] / max(1, i.cost)):
            n = 0
            while n < it.max_uses and it.cost <= tp and direct[it.id] > 0:
                kd += direct[it.id]; tp -= it.cost; n += 1
        self.kill_dmg = kd

    def enemy_cells(self, mp):
        """[(cell, x, y)] the enemy reaches with `mp`, nearest (in steps) first."""
        if mp not in self.b_reach:
            r = reachable(self.B0['cell'], mp)
            self.b_reach[mp] = [(c,) + cxy(c) for c, st in sorted(r.items(), key=lambda kv: kv[1])]
        return self.b_reach[mp]


def others_threat(cx, a, cell):
    """Expected damage the non-focus enemy leeks put on `cell` next turn (x OTHERS_W).
    Per enemy: items whose max range + its MP reach the cell, packed greedily by
    damage per TP (direct damage + one poison tick) under its TP. 0 in solo fights."""
    if not cx.others:
        return 0.0
    tot = 0.0
    ab, rl = int(a['abs']), int(a['rel'])
    for k, (O, offs) in enumerate(cx.others):
        d = dist(O['cell'], cell)
        key = (k, d, ab, rl)
        v = cx.oth.get(key)
        if v is None:
            dk = (k, ab, rl)
            dm = cx.oth_dm.get(dk)
            if dm is None:
                dm = {}
                for it in offs:
                    ta = copy_side(a); to = copy_side(O)
                    hit = apply_item(it, to, ta, {'tp': 0, 'mp': 0})
                    dm[it.id] = hit + max(0.0, ta['groups'].get('poison', 0) - a['groups'].get('poison', 0))
                cx.oth_dm[dk] = dm
            v = 0.0; tp = O['tp_live']; mp = O['mp_live']
            for it in sorted([i for i in offs if d <= mp + i.maxr and dm.get(i.id, 0) > 0],
                             key=lambda i: -dm[i.id] / max(1, i.cost)):
                n = 0
                while n < it.max_uses and it.cost <= tp and (n == 0 or it.weapon or it.cooldown == 0):
                    v += dm[it.id]; tp -= it.cost; n += 1
            cx.oth[key] = v
        tot += v
    return OTHERS_W * tot


def enemy_options(cx, our_cell, tp, mp):
    """Distinct attacks the enemy can make on `our_cell` with `tp` / `mp`:
    [(signature, from cell, items)], nearest cell kept per signature. Only
    geometry matters, so it is cached per (our cell, tp, mp)."""
    ok = (our_cell, tp, mp)
    opts = cx.b_opts.get(ok)
    if opts is not None:
        return opts
    opts = []; tried = {}; seen_geo = {}; n = 0; ns = 0
    ox, oy = cxy(our_cell); maxr = cx.b_maxr
    area = cx.b_area
    reach = maxr + (2 if area else 0)
    for ec, ex, ey in cx.enemy_cells(mp):
        if n >= MAX_ENEMY_CELLS or (n & 7 == 0 and over()):
            break
        d = abs(ex - ox) + abs(ey - oy)
        if d > reach:
            continue
        n += 1
        acts = None; f = 1.0
        if d <= maxr:
            g = geo(ec, our_cell)
            if g not in seen_geo:          # same distance / LoS / line: same attack
                seen_geo[g] = 1
                acts = pack(ec, our_cell, cx.b_off, tp, cx.B0['weapon'], cx.b_vals, 'raw', tag='enemy')
        if not acts and area and ns < MAX_SPLASH_CELLS:
            # no direct shot: an area item aimed next to us still catches us
            ns += 1
            sp = splash_pack(ec, our_cell, area, tp, cx.B0['weapon'], cx.b_vals, 'raw', 'esplash')
            if sp:
                f, acts = sp[1], sp[2]
        if not acts:
            continue
        sig = (f,) + tuple(it.id for it in acts)
        if sig in tried:           # same attack from a farther cell
            continue
        tried[sig] = 1
        opts.append((sig, ec, acts, f))
    cx.b_opts[ok] = opts
    return opts


def acts_cost(acts, weapon):
    """TP of using `acts` in order, weapon switches included."""
    c = 0; held = weapon
    for it in acts:
        c += it.cost
        if it.weapon and it.id != held:
            c += 1; held = it.id
    return c


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
    # antidote: clears every poison on them (+ its heal) when enough is queued
    anti_cost = 0
    if cx.b_antidote and b['pf'] >= ANTIDOTE_TRIGGER:
        it = cx.b_antidote[0]
        apply_item(it, b, b, {'tp': 0, 'mp': 0})
        b['groups']['poison'] = 0.0; b['pf'] = 0.0
        anti_cost = it.cost
    d_tp = b['groups']['shk_tp'] - B0['groups']['shk_tp']
    d_mp = b['groups']['shk_mp'] - B0['groups']['shk_mp']
    d_str = b['groups']['shk_str'] - B0['groups']['shk_str']
    tp = max(0, int(B0['tp_live'] - d_tp - anti_cost)); mp = max(0, int(B0['mp_live'] - d_mp))
    # a damaged enemy heals first (ready heal chips, best HP per TP, no overheal), with the TP
    # it would otherwise attack with; Unhealable (our hemorrhage) blocks it for this turn
    uh = bool(b.get('unheal'))
    if not uh:
        for amt, cost in cx.b_heals:
            missing = b['max'] - b['life']
            if missing <= 0.5 * amt or cost > tp:
                continue
            b['life'] += min(amt, missing); tp -= cost
    b['unheal'] = False
    b['cur']['strength'] -= d_str
    ret = int(a['groups'].get('dmg_return', 0))
    key = (our_cell, tp, mp, int(d_str), ret, int(a['abs']), int(a['rel']), int(b['life'] // 100), uh)
    rep = cx.replies.get(key)
    if rep is None:
        # rational enemy: maximise (HP they take off us) - (HP they lose to our
        # damage return / our life steal); not attacking (net 0) is always allowed
        best = (0.0, B0['cell'], [], 1.0)       # (net, enemy cell, items, area factor)
        sab = (state_sig(a), state_sig(b))
        for sig, ec, acts, f in enemy_options(cx, our_cell, tp, mp):
            nk = (sig, sab)
            net = _NETS.get(nk)
            if net is None:
                ta = copy_side(a); tb = copy_side(b); ts = {'tp': 0, 'mp': 0}
                for it in acts:
                    if it.offensive:
                        apply_item(it, tb, ta, ts, f)
                net = (a['life'] - ta['life']) - (b['life'] - tb['life'])
                _NETS[nk] = net
            if net > best[0]:
                best = (net, ec, acts, f)
        rep = (best[1], best[2], best[3])
        cx.replies[key] = rep
    ec, acts, f = rep
    s = {'tp': 0, 'mp': 0}
    for it in acts:
        if it.offensive:
            apply_item(it, b, a, s, f)
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
    d = dist(our_cell, ec)
    need = max(0, d - mp)
    # the attack sequence only depends on (tp, need): cached per turn
    fk = (tp, need)
    fu = cx.fu.get(fk)
    if fu is None:
        usable = [it for it in cx.a_off if it.minr <= max(need, it.minr) <= it.maxr and cx.a_vals.get(it.id, 0) > 0
                  and need <= it.maxr and not any(e[0] == E_SUPERINF for e in it.effects)]
        # superinfection next turn: off cooldown by then and in range -> keep its TP and cast it
        # LAST, after the poisons (a nuke follow-up), whatever its start-of-turn value
        si_f = [it for it in cx.a_off if any(e[0] == E_SUPERINF for e in it.effects)
                and it.current_cooldown() <= 1 and it.minr <= max(need, it.minr) <= it.maxr and need <= it.maxr]
        si_f = si_f[:1] if si_f and si_f[0].cost <= tp else []
        if si_f:
            tp -= si_f[0].cost
        if not usable and not si_f:
            fu = ([], -1)
        else:
            order = sorted(usable, key=lambda it: -cx.a_vals[it.id] / max(1, it.cost))
            steps = []; used = {}; held = A0['weapon']
            for it in order:
                while used.get(it.id, 0) < it.max_uses:
                    if not it.weapon and it.cooldown > 0 and used.get(it.id, 0) > 0:
                        break
                    cost = it.cost + (1 if it.weapon and held != it.id else 0)
                    if cost > tp:
                        break
                    steps.append(it); tp -= cost
                    used[it.id] = used.get(it.id, 0) + 1
                    if it.weapon:
                        held = it.id
            steps += si_f
            fu = (steps, max(need, min(it.minr for it in (usable + si_f))))
        cx.fu[fk] = fu
    if fu[1] < 0:
        return d
    s = {'tp': 0, 'mp': 0}
    for it in fu[0]:
        apply_item(it, a, b, s)
    return fu[1]


# fields the leaf reads (not our plan's cell or held weapon: the leaf uses the
# end cell, the follow-up starts from the turn's weapon)
_SIGK = ('life', 'max', 'burn', 'pf', 'abs', 'rel', 'tp', 'mp', 'power', 'strength',
         'magic', 'agility', 'wisdom', 'science', 'resistance', 'summons')
_R3 = [3] * 64
_NETS = {}     # (enemy attack signature, (our state, their state)) -> net HP swing; cleared every turn
_LEAVES = {}   # (our state, their state, our end cell) -> (value, reply damage); cleared every turn


def state_sig(S):
    """Hashable state, rounded to 3 decimals so the same attacks applied in
    another order (float noise) share an entry."""
    return (tuple(map(round, map(S.__getitem__, _SIGK), _R3)), tuple(map(round, S['groups'].values(), _R3)),
            tuple(map(round, S['cur'].values(), _R3)))


def leaf(cx, A1, B1, our_cell, turn):
    """Memoised: different plans often reach the same state (same attacks
    from different cells) and share end cells."""
    k = (state_sig(A1), state_sig(B1), B1['cell'], our_cell, bool(B1.get('unheal')))
    r = _LEAVES.get(k)
    if r is None:
        v = _leaf(cx, A1, B1, our_cell, turn)
        r = (v, cx.last_reply, cx.last_leaf)
        _LEAVES[k] = r
    cx.last_reply = r[1]; cx.last_leaf = r[2]
    return r[0]


def _leaf(cx, A1, B1, our_cell, turn):
    """Ply 2: enemy reply; ply 3: our follow-up attack; value at the start of
    the enemy's next turn (1 - their P(win))."""
    a, b, ec = enemy_reply(cx, A1, B1, our_cell)
    if b['life'] <= 0:
        cx.last_reply = A1['life'] - a['life']
        return 1.0
    oth = others_threat(cx, A1, our_cell)
    if oth > 0:
        a['life'] -= min(a['life'], oth)
    cx.last_reply = A1['life'] - a['life']
    if a['life'] <= 0:
        return 0.0
    tick = a['groups'].get('poison', 0)
    if tick > 0:
        dmg = min(a['life'], tick)
        a['life'] -= dmg; a['max'] -= dmg * 0.10; a['burn'] += dmg * 0.10
    if a['life'] <= 0:
        return 0.0
    d0 = dist(our_cell, ec)
    los0 = geo(our_cell, ec)[1]
    # after the enemy's reply it is OUR turn: score from our side as the actor
    lq0 = 0.5 if LOS_NEUTRAL else los0
    v_no = value(features(turn + 1, d0, lq0, a, b), key=('o', d0, lq0))
    # chase mode: the enemy is within our one-turn damage -> the follow-up
    # counts fully and a follow-up kill is (nearly) a win
    chase = b['life'] <= cx.kill_dmg
    w = 1.0 if chase else FOLLOW_W
    if w <= 0:
        return v_no
    a2 = copy_side(a); b2 = copy_side(b)
    d = follow_up(cx, a2, b2, our_cell, ec)
    los = los0 if d == d0 else True
    # one-turn kill through poison: their poisons tick at the START of their turn, before they
    # can act or cleanse, so life <= next tick after our follow-up is a kill
    otk = b2['life'] > 0 and b2['life'] - b2['groups'].get('poison', 0) <= 0
    if otk:
        w = 1.0
    if (b2['life'] <= 0 and chase) or otk:
        v_f = CHASE_KILL
    else:
        # outside chase mode a follow-up "kill" is optimistic: clamp at 1 HP
        if b2['life'] <= 0:
            b2['life'] = 1.0
        lq = 0.5 if LOS_NEUTRAL else los
        v_f = 1.0 - value(features(turn + 1, d, lq, b2, a2), key=('f', d, lq))
    if DIAG:
        cx.last_leaf = (a['life'], b['life'], d0, los0, v_no, v_f, b2['life'])
    return w * v_f + (1.0 - w) * v_no


def end_cells(cx, from_cell, reach, ecell):
    """Stay, approach (nearest to the enemy), retreat (farthest) and hidden
    cells; validated later by real path length."""
    if not cx.ends:
        by_d = sorted(reach, key=lambda c: dist(c, ecell))
        hidden = [c for c in by_d[::-1][:60] if not Field.lineOfSight(c, ecell)][:8]
        cx.ends = by_d[:10] + by_d[::-1][:8] + hidden
        if cx.others:
            # the cells the other enemy leeks threaten least (nearest to the focus first on ties)
            safe = sorted(reach, key=lambda c: (others_threat(cx, cx.A0, c), dist(c, ecell)))[:MAX_SAFE_CELLS]
            cx.ends += [c for c in safe if c not in cx.ends]
    out = [from_cell]
    for c in cx.ends:
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
    if E_REMOVE_SHK in types:
        # a cleanse (manumission / liberation-style) only matters when shackled
        return sum(v for k, v in A['groups'].items() if k.startswith('shk_')) > 0
    if types <= {E_BUFF_TP, E_RAW_TP}:
        # TP for this turn only is a loss unless it returns more than it costs
        gain = sum(avg(e) for e in it.effects if (e[3] or 0) > 1)
        return gain * 2 > it.cost
    if types & {E_RETURN, E_ABS_SHIELD, E_REL_SHIELD, E_RAW_ABS, E_RAW_REL}:
        d = Field.cellDistance(A['cell'], B['cell']) or 0
        return d <= B['mp_live'] + cx.b_maxr or others_threat(cx, A, A['cell']) > 0
    return True


MAX_BULB_TARGETS = 3
MAX_BULB_CELLS = 8


def choose_plan(A, B, cell0, tp0, mp0, weapon0, items, bulbs=None, others=None):
    t = Fight.turn
    cx = Ctx(A, B)
    cx.others = [(O, [it for it in O['items'] if it.offensive and not it.special and it.current_cooldown() <= 1])
                 for O in (others or [])]
    global LAST_CX
    LAST_CX = cx
    if DIAG and t <= 2:
        d0 = Field.cellDistance(A['cell'], B['cell']) or 0
        log('V10REACH T%d d=%s our_mp=%s their_mp=%s their_maxr=%s' % (t, d0, A['mp_live'], B['mp_live'], cx.b_maxr))
    offensive = [it for it in items if it.offensive and not it.special and it.current_cooldown() == 0]
    # superinfection only ever fires as the finale of a nuke combo (below), never as filler
    si_all = [it for it in items if any(e[0] == E_SUPERINF for e in it.effects)]
    offensive = [it for it in offensive if it not in si_all]
    selfish = [it for it in items if it.self_cast and not it.special and it.current_cooldown() == 0
               and useful_now(it, A, B, cx)]
    buffs = [it for it in selfish if any(e[0] in DMG_BUFFS for e in it.effects)]
    vals = {it.id: quick_value(it, A, B) for it in offensive}
    for it in offensive:            # hemorrhage: worth the heal it denies on their next turn
        if any(e[0] == E_ADD_STATE and int(e[1] or 0) == ST_UNHEALABLE for e in it.effects):
            vals[it.id] = min(cx.b_heal_full, max(0.0, B['max'] - B['life']) + 0.3 * B['max'])
    reach = reachable(cell0, mp0)
    ecell = B['cell']
    maxr = max([it.maxr for it in offensive] + [0])
    # attack cells: only cells from which some attack is really usable (range,
    # launch line, LoS); the nearest ones plus the ones with the strongest shot
    ex, ey = cxy(ecell)
    cand = []
    for c, st in sorted(reach.items(), key=lambda kv: kv[1]):
        cx_, cy_ = cxy(c)
        if abs(cx_ - ex) + abs(cy_ - ey) > maxr:
            continue
        us = usable_from(c, ecell, offensive)
        if us:
            cand.append((c, st, max(vals.get(i.id, 0) for i in us)))
    cells = [x[0] for x in cand[:MAX_ATTACK_CELLS - 10]]
    for x in sorted(cand, key=lambda x: (-x[2], x[1])):
        if len(cells) >= MAX_ATTACK_CELLS:
            break
        if x[0] not in cells:
            cells.append(x[0])
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
    plans = []; groups = []
    pcache = {}

    def packed(c, key, tp):
        k = (c, key, tp)
        if k not in pcache:
            pcache[k] = pack(c, ecell, offensive, tp, weapon0, vals, key, tag='ours')
        return pcache[k]
    area_all = [it for it in offensive if has_area(it)]
    # positions for long-range area items (e.g. plutonium bazooka: diagonal 8-12,
    # circle 3): cell c we can reach and aim cell t near the enemy with the launch
    # rule and range met (coordinates first, LoS only on survivors)
    far_shots = []
    for it in area_all:
        if it.maxr < 8:
            continue
        found = []
        for t_, m_ in aim_cells(ecell) + [(ecell, 0)]:
            fct = in_area(it.area, t_, ecell)
            if fct <= 0:
                continue
            tx, ty = cxy(t_)
            for c_, st_ in reach.items():
                qx, qy = cxy(c_)
                dx = abs(qx - tx); dy = abs(qy - ty); dd = dx + dy
                if dd < it.minr or dd > it.maxr or not launch_geo(it.launch, dx == 0 or dy == 0, dx == dy):
                    continue
                if in_area(it.area, t_, c_) > 0:          # would hit ourselves
                    continue
                found.append((-fct, st_, c_, t_))
        found.sort()
        n_ok = 0
        for nf, st_, c_, t_ in found:
            if n_ok >= 6 or over(0.4):
                break
            if it.los and not geo(c_, t_)[1]:
                continue
            far_shots.append((c_, t_, it)); n_ok += 1
    for gi, pre in enumerate(prefixes):
        pre_cost = sum(st[1].cost for st in pre)
        for c in cells:
            if over(0.5):
                break
            for key in ('ratio', 'raw', 'weapons'):
                att = packed(c, key, tp0 - pre_cost)
                base = pre + ([('move', c)] if c != cell0 else []) + [('use', it, ecell) for it in att]
                plans.append(base)
                groups.append(gi)
                # top up with an area shot aimed near the enemy (e.g. a diagonal-only
                # bazooka whose circle-3 splash still catches it) with the TP left
                rest = [it for it in area_all if it not in att]
                if rest:
                    left = tp0 - pre_cost - acts_cost(att, weapon0)
                    if left >= min(it.cost for it in rest):
                        held = next((it.id for it in reversed(att) if it.weapon), weapon0)
                        sp = splash_pack(c, ecell, rest, left, held, vals, 'ratio', 'topup')
                        if sp:
                            plans.append(base + [('use', it, sp[0]) for it in sp[2]])
                            groups.append(gi)
            # (far area shots are planned below, from their own cells)
            # splash shot first, then the best direct attacks with the TP left
            if area_all:
                sp = splash_pack(c, ecell, area_all, tp0 - pre_cost, weapon0, vals, 'ratio', 'first')
                if sp:
                    held = next((it.id for it in reversed(sp[2]) if it.weapon), weapon0)
                    rest_tp = tp0 - pre_cost - acts_cost(sp[2], weapon0)
                    att = [it for it in packed(c, 'ratio', rest_tp) if it not in sp[2]]
                    plans.append(pre + ([('move', c)] if c != cell0 else []) + [('use', it, sp[0]) for it in sp[2]]
                                 + [('use', it, ecell) for it in att])
                    groups.append(gi)
    for c_, t_, it in far_shots:
        for gi, pre in enumerate(prefixes[:2]):
            pre_cost = sum(st[1].cost for st in pre)
            if it.cost + (1 if it.weapon and it.id != weapon0 else 0) > tp0 - pre_cost:
                continue
            rest_tp = tp0 - pre_cost - acts_cost([it], weapon0)
            att = [x for x in packed(c_, 'ratio', rest_tp) if x is not it]
            plans.append(pre + ([('move', c_)] if c_ != cell0 else []) + [('use', it, t_)] + [('use', x, ecell) for x in att])
            groups.append('far')
    # split plans: chips from one cell, weapons from another (ranges differ)
    chips_off = [it for it in offensive if not it.weapon]
    weap_off = [it for it in offensive if it.weapon]
    if chips_off and weap_off:
        top = cells[:6]
        for c1 in top:
            if over(0.5):
                break
            p1 = pack(c1, ecell, chips_off, tp0, weapon0, vals, 'ratio', tag='chips')
            if not p1:
                continue
            left = tp0 - sum(it.cost for it in p1)
            for c2 in top:
                if c2 == c1:
                    continue
                p2 = pack(c2, ecell, weap_off, left, weapon0, vals, 'ratio', tag='weapons')
                if p2:
                    plans.append([('move', c1)] + [('use', it, ecell) for it in p1]
                                 + [('move', c2)] + [('use', it, ecell) for it in p2])
                    groups.append('split')
    # area items aimed next to the enemy from cells with no direct shot
    # (behind an obstacle or a summon, the splash still reaches it)
    area_ours = [it for it in offensive if has_area(it)]
    if area_ours:
        direct = {c: 1 for c in cells}; tries = 0
        for c, st in sorted(reach.items(), key=lambda kv: kv[1]):
            if tries >= MAX_SPLASH_CELLS or over(0.5):
                break
            if c in direct or dist(c, ecell) > maxr + 2:
                continue
            tries += 1
            for pre in prefixes[:2]:
                pre_cost = sum(s_[1].cost for s_ in pre)
                sp = splash_pack(c, ecell, area_ours, tp0 - pre_cost, weapon0, vals, 'ratio', 'splash')
                if sp:
                    plans.append(pre + ([('move', c)] if c != cell0 else []) + [('use', it, sp[0]) for it in sp[2]])
                    groups.append('splash')
    # nuke combo (superinfection), owner's rules (2026-10-10):
    #  - never on turn 1 (turn 1 = the max-HP buff);
    #  - superinfection reachable THIS turn: boost (TP / MAG buffs, the TP-buff usefulness rule
    #    does not apply), move in, stack the strongest poisons, detonate LAST;
    #  - reachable only NEXT turn (our MP now + next turn + its range) and off cooldown by then:
    #    setup turn = boost, move toward the enemy, stack poisons (no detonation yet);
    #  - otherwise no combo.
    if si_all and t > 1:
        s_it = si_all[0]
        poisons = [it for it in offensive if any(e[0] == E_POISON for e in it.effects)]
        boost = [it for it in items if it.self_cast and not it.special and it.current_cooldown() == 0
                 and any(e[0] in (E_BUFF_TP, E_RAW_TP, E_RAW_MAG) for e in it.effects)]
        gain = sum(int(e[1]) for it in boost for e in it.fx if e[0] in (E_BUFF_TP, E_RAW_TP))
        # MP buffs extend "a cell in range can be reached" (leather boots: raw +2 MP)
        mp_boost = [it for it in items if it.self_cast and not it.special and it.current_cooldown() == 0
                    and any(e[0] in (E_BUFF_MP, E_RAW_MP) for e in it.effects)]
        sci = max(0, A['cur'].get('science', 0))
        mp_gain = sum(int(e[1]) if e[0] == E_RAW_MP else int(e[1] * (1 + sci / 100.0))
                      for it in mp_boost for e in it.fx if e[0] in (E_BUFF_MP, E_RAW_MP))
        mp_boost = mp_boost if mp_gain > 0 else []
        reach_b = reachable(cell0, mp0 + mp_gain) if mp_boost else reach
        now_cells = []; need_mp = {}
        if s_it.current_cooldown() == 0:
            for c, st_ in sorted(reach_b.items(), key=lambda kv: kv[1]):
                if dist(c, ecell) <= s_it.maxr and usable_from(c, ecell, [s_it]):
                    now_cells.append(c); need_mp[c] = c not in reach
                    if len(now_cells) >= 10:
                        break
        closest = min((dist(c, ecell) for c in reach_b), default=99)
        next_turn = (not now_cells and s_it.current_cooldown() <= 1
                     and closest <= A['mp_live'] + s_it.maxr)
        if now_cells or next_turn:
            if now_cells:
                cells_c = now_cells
            else:
                # setup: the cells nearest the enemy from which some poison lands
                cells_c = sorted([c for c in reach if usable_from(c, ecell, poisons)],
                                 key=lambda c: (dist(c, ecell), reach[c]))[:8]
            pre_mp = [('use', it, cell0) for it in mp_boost]
            for pre in ([], [('use', it, cell0) for it in boost]):
                for c in cells_c:
                    if over(0.5):
                        break
                    full = (pre_mp if need_mp.get(c) else []) + pre
                    pre_cost = sum(st_[1].cost for st_ in full)
                    budget = tp0 - pre_cost + (gain if pre else 0) - (s_it.cost if now_cells else 0)
                    if budget < 0 or not poisons:
                        continue
                    att = pack(c, ecell, poisons, budget, weapon0, vals, 'raw')
                    if not att:
                        continue
                    plan = full + ([('move', c)] if c != cell0 else []) + [('use', it, ecell) for it in att]
                    if now_cells:
                        plan = plan + [('use', s_it, ecell)]
                    plans.append(plan)
                    groups.append('nuke' if now_cells else 'nuke_setup')
    # enemy summons as targets: they block LoS to the summoner and hit us
    bulb_map = {}
    if bulbs:
        by_steps = sorted(reach.items(), key=lambda kv: kv[1])
        for bs in sorted(bulbs, key=lambda s: dist(cell0, s['cell']))[:MAX_BULB_TARGETS]:
            bc = bs['cell']; bulb_map[bc] = bs; n = 0
            for c, st in by_steps:
                if n >= MAX_BULB_CELLS or over(0.5):
                    break
                if dist(c, bc) > maxr:
                    continue
                att = pack(c, bc, offensive, tp0, weapon0, vals, 'ratio', tag='bulb')
                if not att:
                    continue
                n += 1
                plans.append(([('move', c)] if c != cell0 else []) + [('use', it, bc) for it in att])
                groups.append('bulb')
    if selfish:
        tp = tp0; st = []
        for it in sorted(selfish, key=lambda i: i.cost):
            if it.cost <= tp:
                st.append(('use', it, cell0)); tp -= it.cost
        plans.append(st); groups.append('self')
    plans.append([]); groups.append('none')
    if t == 1:
        vit = [it for it in items if it.self_cast and not it.special and it.current_cooldown() == 0
               and any(e[0] == E_VITALITY for e in it.effects)]
        if vit:
            v_it = vit[0]
            plans = [p if any(st_[0] == 'use' and st_[1] is v_it for st_ in p) else [('use', v_it, cell0)] + p
                     for p in plans]
    # phase 1: simulate every plan (cheap); phase 2: leaf-evaluate them
    # round-robin across groups, each group kills first then by damage dealt,
    # so a tight budget still sees the best plan of every kind
    seen = {}; by_g = {}
    p1_stop = ops() + OPS_STOP * 0.2
    for i, plan in enumerate(plans):
        sig = tuple((s[0], s[1] if s[0] == 'move' else s[1].id) for s in plan)
        if sig in seen:
            continue
        seen[sig] = 1
        if ops() > p1_stop and groups[i] != 'none':
            continue
        r = run_plan(plan, A, B, cell0, tp0, mp0, weapon0, bulb_map)
        if r is None:
            continue
        by_g.setdefault(groups[i], []).append((0 if r[1]['life'] <= 0 else 1, -r[3], i, plan, r))
    for g in by_g:
        by_g[g].sort(key=lambda x: (x[0], x[1], x[2]))
    order = []
    k = 0
    while True:
        added = False
        for g in by_g:
            if k < len(by_g[g]):
                order.append(by_g[g][k]); added = True
        if not added:
            break
        k += 1
    best = (-1.0, None, None); evaluated = 0
    pr = pressure(t)
    d_now = dist(cell0, ecell)
    diag_best = None
    setup_reach = (A['mp_live'] + max([it.maxr for it in si_all] + [0])) if si_all else 0
    for _, _, gi, plan, r in order:
        if over():
            break
        A1, B1, c1, dealt, sim = r
        is_setup = groups[gi] == 'nuke_setup'
        for e in end_cells(cx, c1, reach, ecell):
            if over():
                break
            if is_setup and dist(e, ecell) > setup_reach:
                continue           # a setup turn must leave the detonation reachable next turn
            if e != c1:
                if c1 == cell0:
                    pl = reach.get(e)
                elif dist(c1, e) > sim['mp']:
                    continue
                else:
                    pk = (c1, e)
                    if pk not in cx.plen:
                        cx.plen[pk] = Field.pathLength(c1, e)
                    pl = cx.plen[pk]
                if pl is None or pl < 0 or pl > sim['mp']:
                    continue
            v = 1.1 if B1['life'] <= 0 else leaf(cx, A1, B1, e, t)
            # certain damage now is worth more than the model's uncertain future
            # play our strengths: lasting damage counts too (queued poison at half,
            # max HP burned by nova / erosion in full), not only direct hits
            # queued poison REMOVED by our plan (superinfection burns a tick of every poison,
            # liberation shrinks them) is lost future damage: no clip at 0 on pf
            lasting = 0.5 * (B1['pf'] - B['pf']) + max(0.0, B1['burn'] - B['burn'])
            # direct damage their ready heals can undo next turn counts less
            healable = 0.0 if B1.get('unheal') else min(dealt, cx.b_heal_next)
            v += AGGR * pr * (dealt - HEALABLE_W * healable + lasting) / max(1.0, B['max'])
            # anti-stall: ending far outside our attack range costs a little, more as the fight drags
            de = dist(e, ecell)
            if de > maxr:
                v -= STALL_W * pr * (de - maxr) * min(1.0, t / 8.0)
            # standoff (nobody lost HP for 2+ turns): hiding without dealing damage costs more
            if IDLE[0] >= 2 and dealt <= 0 and not geo(e, ecell)[1]:
                v -= STANDOFF_W * pr
            # engagement drive: a standoff that lasts (3+ idle turns) while we are
            # out of range is broken by closing in, more strongly as the fight drags on
            if IDLE[0] >= 3 and d_now > maxr:
                v += ENGAGE_W * pr * (d_now - de)
            evaluated += 1
            if dealt > 0:
                cx.n_atk += 1
                if v > cx.best_atk[0]:
                    cx.best_atk = (v, dealt, ' '.join((s[0] == 'move' and 'M%d' % s[1]) or s[1].name[:6] for s in plan) + (' M%d' % e if e != c1 else ''))
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
