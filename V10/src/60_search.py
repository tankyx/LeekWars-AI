# ---- 60_search: two-ply plan search ----------------------------------------
# Our plan (moves + item uses) -> each candidate end cell -> the enemy's best
# reply (their poison tick, their TP/MP/STR after our shackles, move to their
# best reachable cell, best packing of their own kit on our end cell) -> our
# poison tick -> value model from OUR side at the start of our next turn.
DMG_BUFFS = {E_BUFF_STR, E_RAW_STR, E_RAW_MAG, E_RAW_SCI, E_RAW_POW, E_BUFF_TP, E_RAW_TP}
MAX_ATTACK_CELLS = 32
# 2026-11-09 burst timing (owner: STR leeks should prep, then burst): damage buffs (STR / MAG / SCI / power / TP)
# only on a turn with an attack in reach (the burst), or as prep when the enemy can be in reach next turn and the
# buff still runs then (2+ turns); never with nothing coming (V10 fired every buff on T1, out of reach - Zoulman with
# doping + whip lost 34-44 / 60 locally)
BURST_TIMING = False
# 2026-11-09 jump / teleportation for reach (review blind spot; 77% of top-2900 STR leeks carry both): plans that walk,
# jump or teleport onto a cell no walk reaches, then shoot. V10 left them out of the search ("special") - Kirby,
# GTGabi and Zoulman carried teleportation and never used it on the ladder
JUMP_REACH = False
PREP_BURST = False       # prep plans (long damage buffs + a staging cell out of their reach, in ours next turn
                         # with jump / teleport) and a follow-up that counts that reach
PREP_CELLS = 4
JUMP_CELLS = 5           # landing cells per teleport item (best attack value first)
JUMP_LAUNCH = 4          # walk cells (nearest the enemy) a jump may start from, besides the current cell
BURST_SLACK = 2          # cells of margin on "in reach next turn" (our MP + their MP + our max range)
MAX_ENEMY_CELLS = 40
MAX_SPLASH_CELLS = 12   # cells per side tried for an area shot aimed next to the target
ANTIDOTE_TRIGGER = 250   # queued poison (HP) at which a rational enemy spends its antidote
CHASE_KILL = 0.95
AGGR = 0.3        # value of certain damage now, per full enemy HP bar
# 2026-11-09 aggression switch: vs real 2900+ leeks (96 challenges) we spent 74% of our TP (they 98%), attacked on
# 48% of turns (they 71%), ended at distance 10 (they 8) and dealt half their damage - V10's leaf prices the reply
# far above certain damage now. AGGRO multiplies the damage-now, anti-stall and engagement terms (1.0 = live V10)
AGGRO = 1.0
# 2026-11-09 edge discipline: in the live challenges vs 2900+ leeks we walked into their range on our round-2 turn
# (-8.4 cells, 39% firing) and they struck first (78% firing, 1192 dmg) - the fight was lost by round 3. A turn that
# deals nothing must not END inside their next-turn reach (their MP + their longest ready attack range): stop at
# the edge and make them cross into ours. A large penalty, not a value-model term the leaf can outweigh
EDGE = False
EDGE_W = 0.5
# 2026-11-10 buff sync: in the 192 live challenges vs 2900+ leeks a STR buff was up on 40% of our hits (theirs 73%)
# and 52-67% of our steroid / protein / motivation casts landed on an idle turn followed by another idle turn (theirs
# 3-5%: they buff on the strike turn or the turn before it); per firing turn they had 2.6 TP more and dealt x1.6.
# Damage buffs (STR / MAG / SCI / power / TP) only in a plan that deals damage now, or as prep (2+ turns) when the
# turn ends within our strike reach next turn (our MP + longest range); the leftover spender follows the same rule
BUFF_SYNC = False
# commitment: a prep buff only pays if we strike while it runs - with our STR / MAG buffed at the start of the
# turn, the damage-now term is multiplied by 1 + BUFF_COMMIT (0 = off)
BUFF_COMMIT = 0.0
# 2026-11-10 review of the enemy-reply model (95 live fights vs 2900+ leeks, 554 garden fights, 56 instrumented local
# fights): the predicted reply was 0 on 81% of our turns vs 2900+ while we took 847 HP per turn. Causes found, each
# behind its own switch (all off = live V10):
# TELE_REPLY  their jump / teleportation ready next turn: landing cells around our end cell (with LoS, per distinct
#             range band and line / diagonal / other), their TP minus the chip; shields are offered inside that reach.
#             46% of fights vs 2900+ had a teleport-then-shoot (mean 2213 HP, round 2), invisible to a walking BFS
# REPLY_FULL  every geometry their walk reaches (distance / line / diagonal classes, LoS tried on the nearest cells
#             of each class) instead of the 40 cells nearest in steps: a full-MP walk to a diagonal was cut
# REPLY_LOS   their shots' LoS ignores their own current body (they have left that cell when they fire)
# REPLY_RET_W weight of the HP they lose to our damage return / gain by life steal in THEIR choice (1 = live: with
#             a mirror / thorn / bramble up the reply was "no attack"; real opponents shoot anyway)
# REPLY_CUT   a leaf whose enemy options were cut by the budget is discarded (it was scored as "no reply", the
#             most optimistic leaf of the turn) and the search stops there
# END_LOCAL   end cells per firing cell: hidden cells within the MP left after the shot (the turn-wide list is
#             built from the start cell; 29-36% of our firing turns ended exposed with a hidden cell in reach)
TELE_REPLY = False
REPLY_FULL = False
REPLY_LOS = False
REPLY_RET_W = 1.0
REPLY_CUT = False
END_LOCAL = False
END_LOCAL_N = 4          # per firing cell: 2 nearest in steps + 2 farthest from the enemy
END_LOCAL_SCAN = 30      # reachable cells checked for LoS per firing cell
LOS_TRIES = 3            # REPLY_FULL: cells per geometry class tried for LoS
STALL_W = 0.01     # per cell beyond our attack range, ramping over the first 8 turns (draws are losses of talent)
# draw breaking: at turn 64 both alive = draw, so waiting loses value as the
# fight drags on. Pressure multiplies the damage-now and anti-stall terms:
# 1 until PRESSURE_T0, then +1 per 10 turns (x5 at turn 60), +0.5 per idle turn
PRESSURE_T0 = 20
IDLE = [0]          # consecutive turns in which neither side lost HP (set in turn())
STANDOFF_W = 0.05  # hidden, no damage, while a standoff lasts: extra cost x pressure
HEALABLE_W = 0.6   # share of healable direct damage discounted (their ready heals would undo it)
POISON_REPLY_W = 0.5   # enemy reply choice: queued poison beyond the next tick, at the weight of our own lasting poison
ENGAGE_W = 0.03   # standoff (3+ idle turns, out of range): per cell closed toward the enemy x pressure


def pressure(t):
    return 1.0 + max(0.0, (t - PRESSURE_T0) / 10.0) + 0.5 * min(IDLE[0], 6)
FOLLOW_W = 0.3     # weight of the ply-3 follow-up (it is never answered: horizon effect)
# team fights: the enemy leeks other than the focus also shoot. Their threat on a
# cell (best packing of the items whose range + their MP reach it, LoS ignored) is
# taken off our HP after the focus' reply; they spread over our team, so only a share
OTHERS_W = 0.6
MAX_SAFE_CELLS = 6
LAST_CX = None     # Ctx of the last search (read by leftover spending)
REPLY_LOG = False  # diagnostics: one 'V10R' line per turn with the reply predicted for the chosen plan


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
    out = []
    for it in items:
        if d < it.minr or d > it.maxr:
            continue
        if cell != tcell and not launch_geo(it.launch, line, diag):
            continue
        if it.los and not los:
            continue
        if it.splash and in_area(it.area, tcell, cell) > 0:   # the area would hit the caster
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


def _cap(it):
    return 1 if (not it.weapon and it.cooldown > 0) else it.rep_cap


def _dp_pack(usable, tp, weapon, vals):
    """Exact packing: per item a use count (0..cap; chips on a cooldown at most once), each weapon other
    than the held one paying its +1 TP switch once, maximising the summed one-use values under `tp` (group
    knapsack, ~items x TP x uses steps). None when greedy is already exact: one item, or everything fits."""
    if len(usable) < 2:
        return None
    full = sum(it.cost * _cap(it) + (1 if it.weapon and it.id != weapon else 0) for it in usable)
    if full <= tp:
        return None
    val = [0.0] * (tp + 1)
    pick = [()] * (tp + 1)
    for it in usable:
        v = vals[it.id]; c = it.cost; cap = _cap(it)
        f = 1 if (it.weapon and it.id != weapon) else 0
        nv = val[:]; npk = pick[:]
        for t in range(tp + 1):
            for n in range(1, cap + 1):
                k = n * c + f
                if k > t:
                    break
                cand = val[t - k] + n * v
                if cand > nv[t] + 1e-9:
                    nv[t] = cand; npk[t] = pick[t - k] + ((it, n),)
        val, pick = nv, npk
    best = max(range(tp + 1), key=lambda t: val[t])
    chosen = sorted(pick[best], key=lambda x: -vals[x[0].id] / max(1, x[0].cost))
    # the held weapon fires before any switch, so each other weapon pays its switch exactly once
    held_first = [x for x in chosen if x[0].weapon and x[0].id == weapon]
    rest = [x for x in chosen if not (x[0].weapon and x[0].id == weapon)]
    wi = next((i for i, x in enumerate(rest) if x[0].weapon), len(rest))
    order = rest[:wi] + held_first + rest[wi:]
    steps = []
    for it, n in order:
        steps += [it] * n
    return steps


def _pack(cell, tcell, items, tp, weapon, vals, key):
    usable = [it for it in usable_from(cell, tcell, items) if vals.get(it.id, 0) > 0]
    if key == 'dp':
        steps = _dp_pack(usable, tp, weapon, vals)
        if steps is not None and acts_cost(steps, weapon) <= tp:
            return steps
        key = 'ratio'
    if key == 'ratio':
        order = sorted(usable, key=lambda it: -vals[it.id] / max(1, it.cost))
    elif key == 'raw':
        order = sorted(usable, key=lambda it: -vals[it.id])
    else:
        order = sorted([it for it in usable if it.weapon], key=lambda it: -vals[it.id] / max(1, it.cost))
    steps = []; held = weapon; used = {}
    for it in order:
        cap = it.rep_cap
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
        self.b_off_nw = [it for it in self.b_off if not it.weapon]        # amputated: chips only
        self.b_antidote = [it for it in B0['items'] if not it.weapon and it.current_cooldown() <= 1
                           and E_ANTIDOTE in it.types]
        self.b_maxr = max([it.maxr for it in self.b_off] + [0])
        # their healing capacity next turn: ready heal / vitality chips (cooldown
        # <= 1, from the engine), wisdom-scaled, best HP per TP within their TP.
        # Values our damage by what survives it (burst when their heals are down).
        # self.b_heals = the heals they would actually cast next turn (reply simulation): once-per-
        # fight ones (regeneration) included while unused - the big heal hemorrhage exists to deny
        wis = 1 + max(0, B0['cur'].get('wisdom', 0)) / 100.0
        hl = []; self.b_heals = []
        for it in B0['items']:
            if it.weapon or it.offensive or it.special:
                continue
            cd = it.current_cooldown()
            if cd <= 1 and it.cooldown >= 0:   # once per fight (regeneration...): no window to play around
                amt = sum(avg(e) for e in it.effects if e[0] in (E_HEAL, E_VITALITY)) * wis
                if amt > 0:
                    hl.append((amt, it.cost))
            if cd <= (0 if it.cooldown < 0 else 1):
                amt = sum(avg(e) for e in it.effects if e[0] == E_HEAL) * wis
                if amt > 0:
                    self.b_heals.append((amt, it.cost))
        tp = B0['tp_live']; hn = 0.0
        for amt, cost in sorted(hl, key=lambda x: -x[0] / max(1, x[1])):
            if cost <= tp:
                hn += amt; tp -= cost
        self.b_heal_next = hn
        self.b_heals.sort(key=lambda x: -x[0] / max(1, x[1]))
        self.b_heal_full = sum(x[0] for x in self.b_heals)
        self.b_area = [it for it in self.b_off if it.splash]   # enemy items that splash
        self.b_reach = {}
        self.b_xy = {}         # mp -> {(x, y): 1} of their walk cells (TELE_REPLY)
        self.b_tele = sorted([it for it in B0['items'] if E_TELEPORT in it.types and it.current_cooldown() <= 1],
                             key=lambda i: i.cost) if TELE_REPLY else []
        self.b_tele_r = max([it.maxr for it in self.b_tele] + [0])
        self.rings = {}        # amputated -> landing distances worth trying (TELE_REPLY)
        self.cut = False       # an enemy_options call ran out of budget (REPLY_CUT)
        self.lends = {}        # (cell, mp) -> hidden end cells near it (END_LOCAL)
        self.replies = {}
        self.b_opts = {}       # (our cell, tp, mp) -> enemy attack options
        self.fu = {}           # (tp, need) -> our follow-up attack sequence
        self.tele_next = []    # (range, cost) of jump / teleport ready next turn (set by choose_plan)
        self.last_reply = 0.0
        self.others = []       # (snapshot, offensive items) of the non-focus enemy leeks
        self.oth = {}          # (enemy index, distance, our abs, our rel) -> threat
        self.oth_dm = {}       # (enemy index, our abs, our rel) -> {item id: damage on us}
        self.best_atk: tuple = (-1.0, 0.0, '')   # best plan that deals damage: (value, dealt, desc)
        self.n_atk = 0                    # attacking plans evaluated
        self.ends: list = []   # (near, far, hidden) end cells, independent of the plan, deduplicated
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

    def walk_xy(self, mp):
        r = self.b_xy.get(mp)
        if r is None:
            r = self.b_xy[mp] = {(x, y): 1 for c, x, y in self.enemy_cells(mp)}
        return r


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


def enemy_options(cx, our_cell, tp, mp, amp=False):
    """Distinct attacks the enemy can make on `our_cell` with `tp` / `mp`:
    [(signature, from cell, items)], nearest cell kept per signature. Only
    geometry matters, so it is cached per (our cell, tp, mp, amputated)."""
    ok = (our_cell, tp, mp, amp)
    opts = cx.b_opts.get(ok)
    if opts is not None:
        return opts
    opts = []; tried = {}
    off = cx.b_off_nw if amp else cx.b_off
    maxr = max([it.maxr for it in off] + [0]) if amp else cx.b_maxr
    area = [it for it in cx.b_area if not it.weapon] if amp else cx.b_area
    _EV[0] = cx.B0['id'] if REPLY_LOS else None
    try:
        if REPLY_FULL:
            _options_full(cx, our_cell, tp, mp, amp, off, maxr, area, opts, tried)
        else:
            _options_near(cx, our_cell, tp, mp, amp, off, maxr, area, opts, tried)
        if cx.b_tele and not cx.cut:
            _options_tele(cx, our_cell, tp, mp, amp, off, maxr, opts, tried)
    finally:
        _EV[0] = None
    cx.b_opts[ok] = opts
    return opts


def _options_near(cx, our_cell, tp, mp, amp, off, maxr, area, opts, tried):
    """Live V10: the 40 cells nearest (in steps) the enemy within range of our cell."""
    seen_geo = {}; n = 0; ns = 0
    ox, oy = cxy(our_cell)
    reach = maxr + (2 if area else 0)
    for ec, ex, ey in cx.enemy_cells(mp):
        if n >= MAX_ENEMY_CELLS:
            break
        if n & 7 == 0 and over():
            cx.cut = True
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
                acts = pack(ec, our_cell, off, tp, cx.B0['weapon'], cx.b_vals, 'raw', tag=('enemy', amp))
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


def _options_full(cx, our_cell, tp, mp, amp, off, maxr, area, opts, tried):
    """REPLY_FULL: every cell of their walk, grouped by geometry class (distance, line, diagonal - coordinates
    only). Per class the nearest cells are tried for LoS (an engine call) until one sees us; a class without LoS
    packs its no-LoS items once. Cells with no direct shot feed the area shots aimed next to us."""
    cls = {}; n = 0; nos = []
    ox, oy = cxy(our_cell)
    reach = maxr + (2 if area else 0)
    wpn = cx.B0['weapon']
    if over():
        cx.cut = True
        return
    for ec, ex, ey in cx.enemy_cells(mp):
        dx = abs(ex - ox); dy = abs(ey - oy); d = dx + dy
        if d > reach:
            continue
        if d <= maxr:
            k = (d, dx == 0 or dy == 0, dx == dy)
            st = cls.get(k, 0)
            if st >= 9:
                continue                   # this geometry already shoots us from a nearer cell
            if st < LOS_TRIES:
                n += 1
                if n & 7 == 0 and over():
                    cx.cut = True
                    return
                g = geo(ec, our_cell)
                acts = None
                if g[1]:
                    cls[k] = 9
                    acts = pack(ec, our_cell, off, tp, wpn, cx.b_vals, 'raw', tag=('enemy', amp))
                else:
                    cls[k] = st + 1
                    if st == 0:
                        acts = pack(ec, our_cell, off, tp, wpn, cx.b_vals, 'raw', tag=('enemy', amp))
                if acts:
                    sig = (1.0,) + tuple(it.id for it in acts)
                    if sig not in tried:
                        tried[sig] = 1
                        opts.append((sig, ec, acts, 1.0))
                    continue
        nos.append(ec)
    if area and nos:
        step = max(1, len(nos) // MAX_SPLASH_CELLS)
        for ec in nos[::step][:MAX_SPLASH_CELLS]:
            if over():
                cx.cut = True
                return
            sp = splash_pack(ec, our_cell, area, tp, wpn, cx.b_vals, 'raw', 'esplash')
            if sp:
                sig = (sp[1],) + tuple(it.id for it in sp[2])
                if sig not in tried:
                    tried[sig] = 1
                    opts.append((sig, ec, sp[2], sp[1]))


def _tele_rings(cx, off, maxr, amp):
    """Landing distances worth trying: one per distinct set of their items in range (the middle of the band),
    plus an even distance of the band (diagonal cells only exist at even distances: neutrino)."""
    r = cx.rings.get(amp)
    if r is None:
        bands = {}; order = []
        for d in range(1, maxr + 1):
            k = tuple(it.id for it in off if it.minr <= d <= it.maxr)
            if k:
                if k not in bands:
                    bands[k] = []; order.append(k)
                bands[k].append(d)
        r = []
        for k in order:
            ds = bands[k]; m = ds[len(ds) // 2]
            r.append(m)
            if m & 1:
                ev = [d for d in ds if not d & 1]
                if ev:
                    r.append(min(ev, key=lambda d: abs(d - m)))
        cx.rings[amp] = r
    return r


def _ring_cells(d):
    """Offsets at distance d: (line cells, diagonal cells, other cells)."""
    line = ((d, 0), (-d, 0), (0, d), (0, -d))
    diag = ()
    if not d & 1:
        h = d // 2
        diag = ((h, h), (h, -h), (-h, h), (-h, -h))
    oth = ()
    if d >= 3:
        b = max(1, d // 3); a = d - b
        oth = ((a, b), (a, -b), (-a, b), (-a, -b), (b, a), (b, -a), (-b, a), (-b, -a))
    return (line, diag, oth)


_DIAMONDS = {}


def _tele_near(r):
    dm = _DIAMONDS.get(r)
    if dm is None:
        dm = _DIAMONDS[r] = [(x, y) for x in range(-r, r + 1) for y in range(-(r - abs(x)), r - abs(x) + 1)]
    return dm


def _options_tele(cx, our_cell, tp, mp, amp, off, maxr, opts, tried):
    """TELE_REPLY: they jump / teleport (ready next turn) onto a cell their walk does not reach, then shoot with
    the TP left. Landing = a free cell within the chip's range of their walk (short chips: exact, against the
    walk cells; long ones: their MP + the range from where they stand), with LoS on our cell."""
    if over():
        cx.cut = True
        return
    B0 = cx.B0; wpn = B0['weapon']
    bx, by = cxy(B0['cell']); ox, oy = cxy(our_cell)
    d0 = abs(bx - ox) + abs(by - oy)
    wxy = cx.walk_xy(mp)
    for T in cx.b_tele:
        tpl = tp - T.cost
        span = mp + T.maxr
        if tpl <= 0 or d0 > span + maxr:
            continue
        near = _tele_near(T.maxr) if T.maxr <= 4 else None
        for d in _tele_rings(cx, off, maxr, amp):
            for cand in _ring_cells(d):
                for dx, dy in cand:
                    lx = ox + dx; ly = oy + dy
                    if abs(lx - bx) + abs(ly - by) > span or (lx, ly) in wxy:
                        continue
                    if near is not None and not any((lx + ax, ly + ay) in wxy for ax, ay in near):
                        continue
                    c = Field.cellFromXY(lx, ly)
                    if c is None or c.obstacle or not c.empty:
                        continue
                    if not geo(c.id, our_cell)[1]:
                        continue
                    acts = pack(c.id, our_cell, off, tpl, wpn, cx.b_vals, 'raw', tag=('enemy', amp))
                    if acts:
                        sig = (1.0,) + tuple(it.id for it in acts)
                        if sig not in tried:       # the same attack on foot keeps the chip's TP
                            tried[sig] = 1
                            opts.append((sig, c.id, acts, 1.0))
                    break                          # this class has its cell in sight


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
    a['amputated'] = False          # an amputation on us ends as its caster's (their) turn starts
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
    amp = bool(b.get('amputated'))  # our glowing saber: their weapon is dropped for this whole reply
    b['amputated'] = False
    b['cur']['strength'] -= d_str
    ret = int(a['groups'].get('dmg_return', 0))
    key = (our_cell, tp, mp, int(d_str), ret, int(a['abs']), int(a['rel']), int(b['life'] // 100), uh, amp)
    rep = cx.replies.get(key)
    if rep is None:
        # rational enemy: maximise (HP they take off us) - (HP they lose to our
        # damage return / our life steal); not attacking (net 0) is always allowed
        best = (0.0, B0['cell'], [], 1.0)       # (net, enemy cell, items, area factor)
        sab = (state_sig(a), state_sig(b))
        for sig, ec, acts, f in enemy_options(cx, our_cell, tp, mp, amp):
            nk = (sig, sab)
            net = _NETS.get(nk)
            if net is None:
                ta = copy_side(a); tb = copy_side(b); ts = {'tp': 0, 'mp': 0}
                for it in acts:
                    if it.offensive:
                        apply_item(it, tb, ta, ts, f)
                net = (a['life'] - ta['life']) - REPLY_RET_W * (b['life'] - tb['life'])
                if tb['life'] <= 0:
                    net = -1.0                 # they never shoot themselves dead on our return
                # poison they stack on us counts: the next tick lands at the START of our turn (certain), the rest
                # of the queue at half. Without this a mage's 'best' reply was its direct damage only
                # (2026-10-15 final 54138737: predicted 390, real ~1650 - three poisons + superinfection)
                t_add = ta['groups'].get('poison', 0) - a['groups'].get('poison', 0)
                if t_add > 0:
                    net += t_add + POISON_REPLY_W * max(0.0, (ta['pf'] - a['pf']) - t_add)
                _NETS[nk] = net
            if net > best[0]:
                best = (net, ec, acts, f)
        rep = (best[1], best[2], best[3])
        cx.replies[key] = rep
    ec, acts, f = rep
    if REPLY_LOG:
        o = cx.b_opts.get((our_cell, tp, mp, amp))
        cx.dbg = (tp, mp, -1 if o is None else len(o), ec, f, ' '.join(it.name for it in acts), amp, ret)
    s = {'tp': 0, 'mp': 0}
    for it in acts:
        if it.offensive:
            apply_item(it, b, a, s, f)
        else:
            apply_item(it, b, b, s)
    b['cell'] = ec
    b['used'] = frozenset(it.id for it in acts)
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
    if PREP_BURST and need > 0 and cx.tele_next:
        # jump / teleport next turn (ready by then): the landing closes the gap, its TP comes off the attack
        for tr, tc in cx.tele_next:
            if need <= tr + 0 and tp > tc:
                need = 0; tp -= tc
                break
    # the attack sequence only depends on (tp, need): cached per turn
    amp = bool(a.get('amputated'))   # their reply amputated us: our next turn has no weapon
    fk = (tp, need, amp)
    fu = cx.fu.get(fk)
    if fu is None:
        usable = [it for it in cx.a_off if it.minr <= max(need, it.minr) <= it.maxr and cx.a_vals.get(it.id, 0) > 0
                  and need <= it.maxr and not it.is_si and not (amp and it.weapon)]
        # superinfection next turn: off cooldown by then and in range -> keep its TP and cast it
        # LAST, after the poisons (a nuke follow-up), whatever its start-of-turn value
        si_f = [it for it in cx.a_off if it.is_si
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


def leaf(cx, A1, B1, our_cell, turn, sig):
    """Memoised: different plans often reach the same state (same attacks
    from different cells) and share end cells. `sig` = the plan's
    (state_sig(A1), state_sig(B1), B1 cell, unhealable), computed once per plan."""
    k = (sig, our_cell)
    r = _LEAVES.get(k)
    if r is None:
        r = _LEAVES[k] = (_leaf(cx, A1, B1, our_cell, turn), cx.last_reply)
    cx.last_reply = r[1]
    return r[0]


def _leaf(cx, A1, B1, our_cell, turn):
    """Ply 2: enemy reply; ply 3: our follow-up attack; value at the start of
    the enemy's next turn (1 - their P(win))."""
    a, b, ec = enemy_reply(cx, A1, B1, our_cell)
    if READY_ON:
        # cooldowns at the start of our next turn: what our plan and their reply used
        a['rk'] = ready_vec(cx.A0, A1.get('used', frozenset()), 'me')
        b['rk'] = ready_vec(cx.B0, b.get('used', frozenset()), 'op')
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
    v_no = value(features(turn + 1, d0, los0, a, b), key=('o', d0, los0))
    # chase mode: the enemy is within our one-turn damage -> the follow-up
    # counts fully and a follow-up kill is (nearly) a win
    chase = b['life'] <= cx.kill_dmg
    w = 1.0 if chase else FOLLOW_W
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
        v_f = 1.0 - value(features(turn + 1, d, los, b2, a2), key=('f', d, los))
    return w * v_f + (1.0 - w) * v_no


def end_cells(cx, from_cell, reach, ecell):
    """Stay, approach (nearest to the enemy), retreat (farthest) and hidden
    cells; validated later by real path length."""
    if not cx.ends:
        by_d = sorted(reach, key=lambda c: dist(c, ecell))
        hidden = [c for c in by_d[::-1][:60] if not Field.lineOfSight(c, ecell)][:8]
        ends = by_d[:10] + by_d[::-1][:8] + hidden
        if cx.others:
            # the cells the other enemy leeks threaten least (nearest to the focus first on ties)
            safe = sorted(reach, key=lambda c: (others_threat(cx, cx.A0, c), dist(c, ecell)))[:MAX_SAFE_CELLS]
            ends += [c for c in safe if c not in ends]
        cx.ends = []                 # deduplicated, first occurrence kept (dict / set builtins are bridged in prod)
        for c in ends:
            if c not in cx.ends:
                cx.ends.append(c)
    return [from_cell] + [c for c in cx.ends if c != from_cell]


def local_ends(cx, c1, mp, ecell):
    """END_LOCAL: hidden cells (no LoS to the enemy) within `mp` steps of the firing cell `c1` - the 2 nearest
    in steps and the 2 farthest from the enemy among the first END_LOCAL_SCAN reachable cells."""
    k = (c1, mp)
    r = cx.lends.get(k)
    if r is None:
        hid = []; n = 0
        for c, st in sorted(reachable(c1, min(mp, 5)).items(), key=lambda kv: kv[1]):
            if c == c1:
                continue
            n += 1
            if n > END_LOCAL_SCAN:
                break
            if not geo(c, ecell)[1]:
                hid.append(c)
        h = END_LOCAL_N // 2
        r = hid[:h] + sorted(hid[h:], key=lambda c: -dist(c, ecell))[:END_LOCAL_N - h]
        cx.lends[k] = r
    return r


def tp_gain(it, A):
    """TP an item gives back the turn it is cast (raw TP buffs as they are, TP buffs science-scaled)."""
    g = 0.0
    for e in it.effects:
        if e[0] == E_RAW_TP:
            g += avg(e)
        elif e[0] == E_BUFF_TP:
            g += avg(e) * (1 + max(0, A['cur'].get('science', 0)) / 100.0)
    if FIX_CRIT_ALL:
        g *= 1 + 0.3 * min(1.0, max(0, A['cur'].get('agility', 0)) / 1000.0)
    return _n(g)


FIX_LEFTOVER_MP = True   # 2026-11-05 (review): spend_leftover cast MP buffs (leather boots) after the last move -
                         # wasted, and on cooldown when the superinfection combo needs the reach


def sync_buff(it):
    """A damage buff BUFF_SYNC times (not a cleanse that also gives TP: manumission)."""
    return it.self_cast and bool(it.types & DMG_BUFFS) and E_REMOVE_SHK not in it.types


def buff_turns(it):
    return max([e[3] or 1 for e in it.effects] + [1])


def strike_reach(A, cx):
    """Distance from which we can attack next turn: our MP + longest attack range."""
    return A['mp_live'] + max([it.maxr for it in cx.a_off] + [0])


def useful_now(it, A, B, cx, leftover=False, cell=None):
    """A self item is only offered when it can matter now: heals when HP is
    missing, antidote when poisoned, reflect / shields when the enemy can
    reach our current cell next turn (their MP + range)."""
    types = it.types
    if leftover and FIX_LEFTOVER_MP and types <= {E_BUFF_MP, E_RAW_MP}:
        return False                # no move left this turn: an MP buff now is wasted
    if BUFF_SYNC and leftover and cx is not None and sync_buff(it):
        # after the plan: only a buff still running next turn, with the enemy within our strike reach
        if buff_turns(it) < 2 or dist(A['cell'] if cell is None else cell, B['cell']) > strike_reach(A, cx):
            return False
    burst = getattr(cx, 'burst', None) if cx is not None else None
    if BURST_TIMING and burst is not None and types & DMG_BUFFS:
        now, nxt = burst
        dur = max([e[3] or 1 for e in it.effects] + [1])
        if leftover or not now:
            # end of turn, or nothing in reach this turn: only a prep buff that still runs when they come
            if not (nxt and dur >= 2):
                return False
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
        # v18: TP buffs pay out THIS turn (the engine adds the TP at once; adrenaline +5 for 1, motivation +2
        # now and for 2 more turns for 4): offered when they return their cost now or over their duration
        now = tp_gain(it, A)
        return now >= it.cost or now * max([e[3] or 1 for e in it.effects] + [1]) > it.cost
    if types & {E_RETURN, E_ABS_SHIELD, E_REL_SHIELD, E_RAW_ABS, E_RAW_REL}:
        d = Field.cellDistance(A['cell'], B['cell']) or 0
        return d <= B['mp_live'] + cx.b_maxr + cx.b_tele_r or others_threat(cx, A, A['cell']) > 0
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
    # superinfection only ever fires as the finale of a nuke combo (below), never as filler
    si_all = [it for it in items if it.is_si]
    offensive = [it for it in items if it.offensive and not it.special and it.current_cooldown() == 0 and not it.is_si]
    ready_self = [it for it in items if it.self_cast and not it.special and it.current_cooldown() == 0]
    selfish = [it for it in ready_self if useful_now(it, A, B, cx)]
    buffs = [it for it in selfish if it.types & DMG_BUFFS]
    vals = {it.id: quick_value(it, A, B) for it in offensive}
    for it in offensive:            # hemorrhage: worth the heal it denies on their next turn
        if it.unheal:
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
    # jump / teleport ready at our next turn (cooldown <= 1): (range, cost), shortest first (PREP_BURST follow-up)
    cx.tele_next = sorted((it.maxr, it.cost) for it in items if E_TELEPORT in it.types and it.current_cooldown() <= 1)
    if BURST_TIMING:
        cx.burst = (bool(cand), dist(cell0, ecell) <= mp0 + B.get('mp_live', 0) + maxr + BURST_SLACK)
        selfish = [it for it in selfish if useful_now(it, A, B, cx)]
        buffs = [it for it in buffs if it in selfish]
    heals = [it for it in selfish if it.types & {E_HEAL, E_VITALITY}]
    shields = [it for it in selfish if it.types & {E_ABS_SHIELD, E_REL_SHIELD, E_RAW_ABS, E_RAW_REL, E_RETURN}]
    best_heal = sorted(heals, key=lambda i: -sum(avg(e) for e in i.effects if e[0] in (E_HEAL, E_VITALITY)) / max(1, i.cost))[:1]
    prefixes = [[]]
    if buffs:
        prefixes.append([('use', it, cell0) for it in buffs])
        if len(buffs) > 1:
            # v18: each buff alone too (a 7-TP steroid with every TP buff is not always the best opener)
            for it in buffs[:4]:
                prefixes.append([('use', it, cell0)])
    if best_heal:
        prefixes.append([('use', it, cell0) for it in best_heal])
        if buffs:
            prefixes.append([('use', it, cell0) for it in best_heal + buffs])
    if shields:
        prefixes.append([('use', it, cell0) for it in shields[:2]])
    # net TP: a TP buff in the prefix pays its TP back before the attack is packed
    pre_costs = [sum(st[1].cost - tp_gain(st[1], A) for st in pre) for pre in prefixes]
    plans = []; groups = []
    pcache = {}

    def mv(c):                     # move step, unless we are already there
        return [('move', c)] if c != cell0 else []

    def at(its, tgt):              # use steps
        return [('use', it, tgt) for it in its]

    def add(plan, g):
        plans.append(plan); groups.append(g)

    def packed(c, key, tp):
        k = (c, key, tp)
        if k not in pcache:
            pcache[k] = pack(c, ecell, offensive, tp, weapon0, vals, key, tag='ours')
        return pcache[k]
    area_all = [it for it in offensive if it.splash]
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
        pre_cost = pre_costs[gi]
        for c in cells:
            if over(0.5):
                break
            for key in ('ratio', 'raw', 'weapons', 'dp'):
                att = packed(c, key, tp0 - pre_cost)
                base = pre + mv(c) + at(att, ecell)
                add(base, gi)
                # top up with an area shot aimed near the enemy (e.g. a diagonal-only
                # bazooka whose circle-3 splash still catches it) with the TP left
                rest = [it for it in area_all if it not in att]
                if rest:
                    left = tp0 - pre_cost - acts_cost(att, weapon0)
                    if left >= min(it.cost for it in rest):
                        held = next((it.id for it in reversed(att) if it.weapon), weapon0)
                        sp = splash_pack(c, ecell, rest, left, held, vals, 'ratio', 'topup')
                        if sp:
                            add(base + at(sp[2], sp[0]), gi)
            # (far area shots are planned below, from their own cells)
            # splash shot first, then the best direct attacks with the TP left
            if area_all:
                sp = splash_pack(c, ecell, area_all, tp0 - pre_cost, weapon0, vals, 'ratio', 'first')
                if sp:
                    held = next((it.id for it in reversed(sp[2]) if it.weapon), weapon0)
                    rest_tp = tp0 - pre_cost - acts_cost(sp[2], weapon0)
                    att = [it for it in packed(c, 'ratio', rest_tp) if it not in sp[2]]
                    add(pre + mv(c) + at(sp[2], sp[0]) + at(att, ecell), gi)
    if JUMP_REACH and offensive:
        tele = [it for it in items if E_TELEPORT in it.types and it.current_cooldown() == 0 and it.cost < tp0]
        walk_set = set(reach)
        launches = [cell0] + [c for c, _ in sorted(reach.items(), key=lambda kv: (dist(kv[0], ecell), kv[1]))
                              if c != cell0][:JUMP_LAUNCH]
        for T in tele:
            found = []; seen_l = set()
            for lc in launches:
                if over(0.45):
                    break
                lx, ly = cxy(lc)
                for dx in range(-T.maxr, T.maxr + 1):
                    for dy in range(-(T.maxr - abs(dx)), T.maxr - abs(dx) + 1):
                        if abs(dx) + abs(dy) < max(1, T.minr):
                            continue
                        n = Field.cellFromXY(lx + dx, ly + dy)
                        if n is None or n.obstacle or not n.empty:
                            continue
                        L = n.id
                        if L in walk_set or L in seen_l or dist(L, ecell) > maxr:
                            continue
                        us = usable_from(L, ecell, offensive)
                        if not us:
                            continue
                        g = geo(lc, L)
                        if not launch_geo(T.launch, g[2], g[3]) or (T.los and not g[1]):
                            continue
                        seen_l.add(L)
                        found.append((-max(vals.get(i.id, 0) for i in us), reach.get(lc, 0), lc, L))
            found.sort()
            for _, _, lc, L in found[:JUMP_CELLS]:
                for gi, pre in enumerate(prefixes[:3]):
                    rest = tp0 - pre_costs[gi] - T.cost
                    if rest <= 0:
                        continue
                    for key in ('ratio', 'raw'):
                        att = packed(L, key, rest)
                        if att:
                            add(pre + mv(lc) + [('use', T, L)] + at(att, ecell), 'jump')
    if PREP_BURST and not cand:
        # nothing in reach this turn: long damage buffs (still on next turn) + a staging cell they cannot hit next
        # turn but we can reach (MP + jump / teleport + our range); the leaf's follow-up scores the burst
        longb = [it for it in ready_self if it.types & DMG_BUFFS and max([e[3] or 1 for e in it.effects] + [1]) >= 2]
        b_thr = B.get('mp_live', 0) + cx.b_maxr
        our_next = mp0 + max([r for r, c in cx.tele_next] + [0]) + maxr
        stage = sorted([c for c in reach if b_thr < dist(c, ecell) <= our_next], key=lambda c: (dist(c, ecell), reach[c]))
        tp_ = tp0; pre = []
        for it in sorted(longb, key=lambda i: -i.cost):
            if it.cost <= tp_:
                pre.append(('use', it, cell0)); tp_ -= it.cost
        for c in stage[:PREP_CELLS]:
            add(pre + mv(c), 'prep')
            add(mv(c), 'prep')
    for c_, t_, it in far_shots:
        for gi, pre in enumerate(prefixes[:2]):
            pre_cost = pre_costs[gi]
            if it.cost + (1 if it.weapon and it.id != weapon0 else 0) > tp0 - pre_cost:
                continue
            rest_tp = tp0 - pre_cost - acts_cost([it], weapon0)
            att = [x for x in packed(c_, 'ratio', rest_tp) if x is not it]
            add(pre + mv(c_) + [('use', it, t_)] + at(att, ecell), 'far')
    # v18 enabler-first plans: shield strip (liberation) or a vulnerability hit (neutrino, heavy sword, j_laser)
    # BEFORE the damage it boosts, then the best pack of the other items with the TP left. Packing by value per
    # TP puts the enabler wherever its own value lands (Kirby fired neutrino after his other weapons in 33% of
    # the turns he fired both); the plan simulator scores the interaction exactly once the order is right.
    enablers = [it for it in offensive if it.types & {E_DEBUFF, E_VULN, E_VULN_ABS} and vals.get(it.id, 0) > 0]
    if enablers:
        for gi, pre in enumerate(prefixes[:2]):
            for c in cells[:12]:
                if over(0.5):
                    break
                for en in enablers:
                    if not usable_from(c, ecell, [en]):
                        continue
                    tp_left = tp0 - pre_costs[gi] - acts_cost([en], weapon0)
                    if tp_left < 0:
                        continue
                    held = en.id if en.weapon else weapon0
                    rest = [it for it in offensive if it is not en or _cap(en) > 1]
                    att = pack(c, ecell, rest, tp_left, held, vals, 'dp', tag=('ena', en.id, held))
                    extra = en.max_uses - 1                 # the enabler's own later uses this turn
                    att = [it for it in att if it is not en or (extra := extra - 1) >= 0]
                    add(pre + mv(c) + at([en] + att, ecell), 'enabler')
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
                    add([('move', c1)] + at(p1, ecell) + [('move', c2)] + at(p2, ecell), 'split')
    # area items aimed next to the enemy from cells with no direct shot
    # (behind an obstacle or a summon, the splash still reaches it)
    if area_all:
        direct = {c: 1 for c in cells}; tries = 0
        for c, st in sorted(reach.items(), key=lambda kv: kv[1]):
            if tries >= MAX_SPLASH_CELLS or over(0.5):
                break
            if c in direct or dist(c, ecell) > maxr + 2:
                continue
            tries += 1
            for gi, pre in enumerate(prefixes[:2]):
                sp = splash_pack(c, ecell, area_all, tp0 - pre_costs[gi], weapon0, vals, 'ratio', 'splash')
                if sp:
                    add(pre + mv(c) + at(sp[2], sp[0]), 'splash')
    # nuke combo (superinfection), owner's rules (2026-10-10):
    #  - never on turn 1 (turn 1 = the max-HP buff);
    #  - superinfection reachable THIS turn: boost (TP / MAG buffs, the TP-buff usefulness rule
    #    does not apply), move in, stack the strongest poisons, detonate LAST;
    #  - reachable only NEXT turn (our MP now + next turn + its range) and off cooldown by then:
    #    setup turn = boost, move toward the enemy, stack poisons (no detonation yet);
    #  - otherwise no combo.
    if si_all and t > 1:
        s_it = si_all[0]
        poisons = [it for it in offensive if E_POISON in it.types]
        boost = [it for it in ready_self if it.types & {E_BUFF_TP, E_RAW_TP, E_RAW_MAG}]
        gain = sum(tp_gain(it, A) for it in boost) if FIX_TP_ROUND else \
            sum(int(e[1]) for it in boost for e in it.fx if e[0] in (E_BUFF_TP, E_RAW_TP))
        # MP buffs extend "a cell in range can be reached" (leather boots: raw +2 MP)
        mp_boost = [it for it in ready_self if it.types & {E_BUFF_MP, E_RAW_MP}]
        sci = max(0, A['cur'].get('science', 0))
        mp_gain = sum(_n(e[1]) if e[0] == E_RAW_MP else _n(e[1] * (1 + sci / 100.0))
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
                    add(full + mv(c) + at(att, ecell) + ([('use', s_it, ecell)] if now_cells else []),
                        'nuke' if now_cells else 'nuke_setup')
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
                add(mv(c) + at(att, bc), 'bulb')
    for sel in ([selfish, [it for it in selfish if not sync_buff(it)]] if BUFF_SYNC else [selfish]):
        if sel:
            tp = tp0; st = []
            for it in sorted(sel, key=lambda i: i.cost):
                if it.cost <= tp:
                    st.append(('use', it, cell0)); tp -= it.cost
            add(st, 'self')
    add([], 'none')
    if t == 1:
        vit = [it for it in ready_self if E_VITALITY in it.types]
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
    order = []; k = 0
    while any(k < len(v) for v in by_g.values()):
        order += [v[k] for v in by_g.values() if k < len(v)]; k += 1
    best = (-1.0, None, None); evaluated = 0
    pr = pressure(t)
    k_aggr = AGGR * pr * AGGRO
    if BUFF_COMMIT and (A['cur'].get('strength', 0) > A['strength'] or A['cur'].get('magic', 0) > A['magic']):
        k_aggr *= 1.0 + BUFF_COMMIT
    b_max = max(1.0, B['max']); a_max = max(1.0, A['max'])
    stall = STALL_W * pr * AGGRO; ramp = min(1.0, t / 8.0)
    d_now = dist(cell0, ecell)
    b_reach = B.get('mp_live', 0) + cx.b_maxr        # EDGE: their next-turn reach (distance only, LoS ignored)
    setup_reach = (A['mp_live'] + max([it.maxr for it in si_all] + [0])) if si_all else 0
    a_reach = strike_reach(A, cx)                      # BUFF_SYNC: where a prep buff still pays next turn
    for _, _, gi, plan, r in order:
        if over() or (REPLY_CUT and cx.cut):
            break
        A1, B1, c1, dealt, sim = r
        is_setup = groups[gi] == 'nuke_setup'
        # buff sync: a plan that deals nothing may only carry damage buffs that last into next turn (prep),
        # and must end within our strike reach (the nuke combo keeps the owner's own rules)
        prep = False
        if BUFF_SYNC and dealt <= 0 and groups[gi] not in ('nuke', 'nuke_setup'):
            db = [s_[1] for s_ in plan if s_[0] == 'use' and sync_buff(s_[1])]
            if db:
                if min(buff_turns(it) for it in db) < 2:
                    continue
                prep = True
        sig = None                 # memo key part shared by the plan's end cells, built at the first leaf
        # plan-level terms: the same for every end cell of this plan
        lasting = 0.5 * (B1['pf'] - B['pf']) + max(0.0, B1['burn'] - B['burn'])
        healable = 0.0 if B1.get('unheal') else min(dealt, cx.b_heal_next)
        self_lost = max(0.0, A['life'] - A1['life'])
        n_end = 0
        ends = end_cells(cx, c1, reach, ecell)
        if END_LOCAL and sim['mp'] > 0:
            ends = ends + [c for c in local_ends(cx, c1, sim['mp'], ecell) if c not in ends]
        for e in ends:
            n_end += 1
            if n_end & 3 == 0 and over():      # the budget check is an engine call: every 4th cell
                break
            de = dist(e, ecell)
            if is_setup and de > setup_reach:
                continue           # a setup turn must leave the detonation reachable next turn
            if prep and de > a_reach:
                continue           # a prep buff with no strike next turn is wasted
            if e != c1:
                if c1 == cell0:
                    pl = reach.get(e)
                elif dist(c1, e) > sim['mp']:
                    continue
                else:
                    pl = path_len(c1, e)
                if pl is None or pl < 0 or pl > sim['mp']:
                    continue
            if B1['life'] <= 0:
                v = 1.1
            else:
                if sig is None:
                    sig = (state_sig(A1), state_sig(B1), B1['cell'], bool(B1.get('unheal')), bool(B1.get('amputated')),
                           A1.get('used') if READY_ON else None)
                v = leaf(cx, A1, B1, e, t, sig)
                if REPLY_CUT and cx.cut:
                    break              # their options were cut by the budget: this leaf saw no reply
            # certain damage now is worth more than the model's uncertain future; lasting damage
            # counts too (queued poison at half - REMOVED poison (superinfection, liberation) is
            # lost future damage, so no clip at 0 -, max HP burned by nova / erosion in full);
            # direct damage their ready heals can undo next turn counts less
            v += k_aggr * (dealt - HEALABLE_W * healable + lasting) / b_max
            # our own HP lost during our turn (damage return - e.g. a bramble at ~260% -, self-harm)
            # weighs like the damage we deal: attacking into a reflect is not "free"
            if self_lost > 0:
                v -= k_aggr * self_lost / a_max
            # anti-stall: ending far outside our attack range costs a little, more as the fight drags
            if de > maxr:
                v -= stall * (de - maxr) * ramp
            # edge discipline: dealing nothing this turn, never end inside their next-turn reach
            if EDGE and dealt <= 0 and de <= b_reach:
                v -= EDGE_W
            # standoff (nobody lost HP for 2+ turns): hiding without dealing damage costs more
            if IDLE[0] >= 2 and dealt <= 0 and not geo(e, ecell)[1]:
                v -= STANDOFF_W * pr
            # engagement drive: a standoff that lasts (3+ idle turns) while we are
            # out of range is broken by closing in, more strongly as the fight drags on
            if IDLE[0] >= (3 if AGGRO <= 1.0 else 1) and d_now > maxr:
                v += ENGAGE_W * pr * AGGRO * (d_now - de)
            evaluated += 1
            if dealt > 0:
                cx.n_atk += 1
                if v > cx.best_atk[0]:
                    cx.best_atk = (v, dealt, ' '.join((s[0] == 'move' and 'M%d' % s[1]) or s[1].name[:6] for s in plan) + (' M%d' % e if e != c1 else ''))
            if v > best[0]:
                best = (v, plan + ([('move', e)] if e != c1 else []),
                        (dealt, Field.cellDistance(e, ecell), bool(Field.lineOfSight(e, ecell)), cx.last_reply))
    return best, evaluated
