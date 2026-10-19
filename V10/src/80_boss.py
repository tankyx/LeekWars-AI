# ---- 80_boss: Fennel King boss mode (ported from BOSS/fennel.lk) ------------
# PUZZLE (graal alive, army under Divine Protection): scripted kill+resurrect doctrine - every leek
#   holding resurrection solves ONE crystal per turn: [adrenaline] -> spark the crystal -> teleport or
#   walk next to a cell on its graal axis -> resurrect it there; dead crystals are revived first (the
#   graal casts Apocalypse on a dead crystal). Never damages the (invulnerable) army.
# COMBAT (graal dead): tank / buffer / healer keep their scripted roles; strikers run the V10 search on
#   the boss focus (scribe -> knights -> king -> squires, lowest life first; crystals once the army is
#   dead), the rest of the army feeding the danger map.
AXIS = {'red_crystal': 'south', 'blue_crystal': 'east', 'yellow_crystal': 'west', 'green_crystal': 'north'}
BOSS = {'on': None, 'combat': False, 'gcell': None, 'gx': 0, 'gy': 0, 'crystals': {}, 'regen': False,
        'in_reach': 0, 'fer': None, 'tank_cell': None, 'mine': None, 'claims': {}}
BOSS_PZ_DISARM = True       # disarm also during the puzzle (after the dive): 15/20 wins with it vs 6/20 without (2026-10-18)
BOSS_PRE_DISARM = False      # pre-dive disarm with unspent TP: 8/18 vs 8/22 without (2026-10-18) - no effect, off
BOSS_DISARM = True      # glowing saber on the King / scribe (puzzle after the dive, and combat): 10/11 wins with it vs 1/9 without (2026-10-18, p=0.0006)
CLAIM_MSG = 13          # MESSAGE_CUSTOM: params [CLAIM_TAG, crystal entity id or -1]
CLAIM_TAG = 7101
BLOG = []
# Fennel castle articulation cells (Tarjan on the map, 2026-09-07): an ally stopped on one walls the team out
CORRIDOR = frozenset([109, 123, 126, 140, 143, 158, 160, 175, 193, 263, 266, 280, 283, 298, 300, 315, 333, 351, 354, 357, 369,
                      372, 374, 387, 390, 391, 408, 418, 425, 435, 442, 452, 459, 461, 479, 497, 513, 516, 518, 520, 530, 531,
                      549, 557, 567, 574, 585, 586, 587, 588, 589, 590, 591, 603, 604, 605, 606, 607, 608])
_ARMY_RANK = {'fennel_scribe': 0, 'fennel_knight': 1, 'fennel_king': 2, 'fennel_squire': 3}


def bnote(s):
    BLOG.append(s)


def ename(e):
    try:
        return e.name or ''
    except Exception:
        return ''


def boss_on():
    """A Fennel boss fight (graal / crystals among the enemies), decided once per fight."""
    if BOSS['on'] is None:
        try:
            names = {ename(e) for e in Fight.getEnemies()}
            BOSS['on'] = 'graal' in names or any(n in AXIS for n in names)
        except Exception:
            BOSS['on'] = False
    return BOSS['on']


def is_army(e):
    n = ename(e)
    return n != 'graal' and n not in AXIS and 'chest' not in n


def army():
    return [e for e in Fight.getAliveEnemies() if is_army(e) and e.cell is not None]


def army_protected():
    """Divine Protection: the army carries an add-state effect while the graal lives."""
    seen = False
    for e in army():
        seen = True
        for f in (e.effects or []):
            if f.type == E_ADD_STATE:
                return True
    return not seen


def boss_scan():
    cr = {}; graal = None
    for e in Fight.getEnemies():
        n = ename(e)
        if n == 'graal':
            graal = e
        elif n in AXIS:
            cr[e.id] = (e, AXIS[n])
    BOSS['crystals'] = cr
    g = None
    try:
        # ghost-graal guard: after self-destructing it can linger with no cell
        if graal is not None and graal.alive and (graal.life or 0) > 0 and graal.cell is not None and graal.cell.id >= 0:
            g = graal.cell.id
    except Exception:
        g = None
    BOSS['gcell'] = g
    if g is not None:
        BOSS['gx'], BOSS['gy'] = cxy(g)
    if g is None:
        BOSS['combat'] = True
    elif not BOSS['combat'] and Fight.turn > 1 and not army_protected():
        BOSS['combat'] = True
    tk = squad('tank')
    BOSS['tank_cell'] = tk[0].cell.id if tk and my_role() != 'tank' else None


# ---- kit helpers ---------------------------------------------------------------
def my_chips():
    return {c.name: c for c in (me().chips or [])}


def has(n):
    return n in my_chips()


def ready(n):
    c = my_chips().get(n)
    return c is not None and (c.currentCooldown or 0) == 0


def ccost(n):
    c = my_chips().get(n)
    return (c.cost or 0) if c is not None else 99


def ok(r):
    return r is not None and r > 0


def cast_self(n):
    c = my_chips().get(n)
    if c is not None and (c.currentCooldown or 0) == 0 and (me().tp or 0) >= (c.cost or 0):
        return ok(me().useChip(c, me()))
    return False


def cast_on(n, a):
    c = my_chips().get(n)
    if c is None or (c.currentCooldown or 0) > 0 or (me().tp or 0) < (c.cost or 0):
        return False
    try:
        if not me().canUseChip(c, a):
            return False
    except Exception:
        return False
    return ok(me().useChip(c, a))


def role_of(a):
    try:
        cs = {c.name for c in (a.chips or [])}
    except Exception:
        return 'striker'
    if 'dome' in cs:
        return 'tank'
    if 'ferocity' in cs:
        return 'buffer'
    return 'striker'


def my_role():
    return role_of(me())


def squad(role):
    return [a for a in Fight.getAliveAllies() if not a.summoned and a.cell is not None and role_of(a) == role]


# ---- geometry ------------------------------------------------------------------
def cell_at(x, y):
    c = Field.cellFromXY(x, y)
    if c is not None:
        _XY[c.id] = (x, y)
    return c


def alive_ids():
    return [e for e in Fight.getAliveEnemies()] + [a for a in Fight.getAliveAllies()]


def on_axis(cell, axis):
    x, y = cxy(cell); gx, gy = BOSS['gx'], BOSS['gy']
    if axis == 'north':
        return x == gx and y < gy
    if axis == 'south':
        return x == gx and y > gy
    if axis == 'east':
        return y == gy and x > gx
    if axis == 'west':
        return y == gy and x < gx
    return False


def solved(cid):
    e, axis = BOSS['crystals'][cid]
    if not e.alive or e.cell is None:
        return False
    c = e.cell.id
    # the crystal ray passes through entities: only obstacles block it
    return on_axis(c, axis) and bool(Field.lineOfSight(c, BOSS['gcell'], alive_ids()))


def chest_cells():
    out = []
    for e in list(Fight.getAliveEnemies()) + list(Fight.getAliveAllies()):
        if 'chest' in ename(e) and e.cell is not None:
            out.append(e.cell.id)
    return out


def goal_cells_raw(axis):
    out = []; gx, gy = BOSS['gx'], BOSS['gy']
    for d in range(1, 21):
        x, y = gx, gy
        if axis == 'north':
            y = gy - d
        elif axis == 'south':
            y = gy + d
        elif axis == 'east':
            x = gx + d
        elif axis == 'west':
            x = gx - d
        c = cell_at(x, y)
        if c is None or c.obstacle:
            break
        if c.empty:
            out.append(c.id)
    return out


def goal_cells(axis):
    """Revive cells on the axis, nearest the graal first; out of a chest's reach (7) first."""
    allc = goal_cells_raw(axis)
    chests = chest_cells()
    if not chests:
        return allc
    safe = [c for c in allc if all(dist(c, k) > 7 for k in chests)]
    return safe + [c for c in allc if c not in safe]


def threat_at(cell):
    n = 0.0
    for e in army():
        d = dist(cell, e.cell.id)
        if d <= 11:
            # the King is half the army's damage (Excalibur ~750 + ~750 poison x2, chip 108 ~1000)
            n += (12 - d) / 6.0 * (3 if ename(e) == 'fennel_king' else 1)
    return n


def stand_cells(g):
    """Cells 1-2 from g (resurrection range) I can stand on to revive onto g."""
    out = []; gx, gy = cxy(g); mine = me().cell.id
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            t = cell_at(gx + dx, gy + dy)
            if t is None or t.id == g or t.obstacle:
                continue
            d = dist(t.id, g)
            if d < 1 or d > 2:
                continue
            if t.id != mine and not t.empty:
                continue
            if not Field.lineOfSight(t.id, g, [me()]):
                continue
            out.append(t.id)
    return out


def path_ok(a, b, mp):
    if a == b:
        return 0
    pl = Field.pathLength(a, b)
    return pl if (pl is not None and 0 <= pl <= mp) else None


# ---- the kill + resurrect solve --------------------------------------------------
def revive_plan(cid, tp_budget, frm, used):
    """Best way to put crystal cid back on its axis this turn: (stand, goal, teleport?) or None."""
    best = None; bs = 1e18
    tele = my_chips().get('teleportation')
    tele_ready = tele is not None and (tele.currentCooldown or 0) == 0
    tr = (tele.maxRange or 12) if tele is not None else 0
    for g in goal_cells(BOSS['crystals'][cid][1]):
        for t in stand_cells(g):
            walk = 0 if t == frm else Field.pathLength(frm, t)
            jump = False
            if walk is None or walk < 0 or walk + used > (me().mp or 0):
                if not tele_ready:
                    continue
                td = dist(frm, t)
                if td < 1 or td > tr or t == frm:
                    continue
                jump = True
            cost = ccost('resurrection') + (ccost('teleportation') if jump else 0)
            if cost > tp_budget:
                continue
            sc = threat_at(t) * 10 + (5 if jump else 0) + dist(g, BOSS['gcell']) * 0.1
            if sc < bs:
                bs, best = sc, (t, g, jump)
    return best


def exec_revive(cid, plan):
    e, axis = BOSS['crystals'][cid]
    t, g, jump = plan
    m = me()
    if jump:
        if not ok(m.useChipOnCell(my_chips()['teleportation'], t)):
            bnote('tele fail %d' % t)
    elif t != m.cell.id:
        m.moveToward(Cell.get(t))
    if ok(m.resurrect(e, g)) and e.alive:
        bnote('revived %s@%d' % (ename(e), g)); return True
    for g2 in goal_cells(axis):           # fallback: any goal cell reachable from where I ended
        if dist(m.cell.id, g2) <= 2 and Field.lineOfSight(m.cell.id, g2, [m]):
            if ok(m.resurrect(e, g2)) and e.alive:
                bnote('revived2 %s@%d' % (ename(e), g2)); return True
    bnote('revive FAILED %s' % ename(e))
    return False


def adrenaline_if(need):
    if (me().tp or 0) < need and ready('adrenaline'):
        cast_self('adrenaline')


def save_dead_crystals():
    """Revive a crystal that died before our turn (Apocalypse guard)."""
    if not ready('resurrection'):
        return
    m = me()
    for cid, (e, axis) in BOSS['crystals'].items():
        if e.alive:
            continue
        tp = (m.tp or 0) + (4 if ready('adrenaline') else 0)
        plan = revive_plan(cid, tp, m.cell.id, 0)
        if plan is None:
            # teleport to F, walk to a revive cell t, resurrect onto its goal
            tele = my_chips().get('teleportation')
            if tele is None or (tele.currentCooldown or 0) > 0 or tp < ccost('teleportation') + ccost('resurrection'):
                continue
            opts = []; tr = tele.maxRange or 12; mp = m.mp or 0
            for g in goal_cells(axis):
                for t in stand_cells(g):
                    tx, ty = cxy(t)
                    for dx in range(-mp, mp + 1):
                        for dy in range(-mp + abs(dx), mp - abs(dx) + 1):
                            f = cell_at(tx + dx, ty + dy)
                            if f is None or f.id == m.cell.id or f.obstacle or not f.empty:
                                continue
                            dm = dist(m.cell.id, f.id)
                            if 1 <= dm <= tr:
                                opts.append((dist(f.id, t), f.id, t, g))
            opts.sort()
            for _, f, t, g in opts[:6]:
                if path_ok(f, t, m.mp or 0) is None:
                    continue
                adrenaline_if(ccost('teleportation') + ccost('resurrection'))
                if not ok(m.useChipOnCell(tele, f)):
                    break
                bnote('SAVE %s tele %d walk %d' % (ename(e), f, t))
                exec_revive(cid, (t, g, False))
                return
            continue
        adrenaline_if(ccost('resurrection') + (ccost('teleportation') if plan[2] else 0))
        exec_revive(cid, plan)
        return


def try_solve_one():
    if not ready('resurrection') or not has('spark'):
        return False
    m = me(); spark = my_chips()['spark']
    tp_avail = (m.tp or 0) + (4 if ready('adrenaline') else 0)
    budget = tp_avail - ccost('spark')
    rc = reachable(m.cell.id, m.mp or 0)
    sr = spark.maxRange or 10
    best = None; bs = 1e18
    for cid, (e, axis) in BOSS['crystals'].items():
        if not e.alive or e.cell is None or solved(cid):
            continue
        if (e.life or 0) > 8 or (e.absoluteShield or 0) > 0:
            bnote('%s tough %s' % (ename(e), e.life)); continue
        cc = e.cell.id
        goals = goal_cells(axis)
        cc_ = claim_cost(cid)
        if cc_ is None or not goals:
            continue
        # direct walk-dive: a stand cell reachable now and within spark range - walk, spark, revive there
        for g in goals:
            for t in stand_cells(g):
                if t in rc and dist(t, cc) <= sr and budget >= ccost('resurrection'):
                    sc = threat_at(t) * 10 + rc[t] * 0.2 + cc_ - 1
                    if sc < bs:
                        bs, best = sc, (cid, (t, g, False), t)
        froms = [c for c in rc if dist(c, cc) <= sr]
        if not froms:
            continue
        for f in sorted(froms, key=lambda f: min(dist(f, g) for g in goals) * 10 + rc[f])[:10]:
            plan = revive_plan(cid, budget, f, rc[f])
            if plan is None:
                continue
            sc = threat_at(plan[0]) * 10 + (5 if plan[2] else 0) + rc[f] * 0.2 + cc_
            if sc < bs:
                bs, best = sc, (cid, plan, f)
            break
    if best is None:
        return tele_first(tp_avail)
    cid, plan, frm = best
    e = BOSS['crystals'][cid][0]
    need = ccost('spark') + ccost('resurrection') + (ccost('teleportation') if plan[2] else 0)
    adrenaline_if(need)
    if (m.tp or 0) < need:
        return False
    if frm != m.cell.id:
        m.moveToward(Cell.get(frm))
    if dist(m.cell.id, e.cell.id) > sr:
        bnote('could not reach spark range'); return False
    if not plan[2] and plan[0] != m.cell.id and path_ok(m.cell.id, plan[0], m.mp or 0) is None:
        bnote('walk plan broke'); return False
    r = m.useChip(spark, e)
    if e.alive:
        bnote('spark did not kill %s r=%s' % (ename(e), r)); return False
    bnote('KR %s from %d %s %d -> %d' % (ename(e), frm, 'tele' if plan[2] else 'walk', plan[0], plan[1]))
    exec_revive(cid, plan)
    return True


def tele_walk_options(cid, mp, check=False):
    """(F, t, g, |F-t|): teleport to F within spark range of the crystal, walk to t, revive onto g.
    check=True (diving now): F must pass the engine's teleport check from here and t must be walkable
    from F within mp - several landing cells are tried per revive cell, not only the closest."""
    out = []; m = me(); e, axis = BOSS['crystals'][cid]
    if e.cell is None:
        return out
    cc = e.cell.id
    sr = my_chips()['spark'].maxRange or 10
    tele = my_chips().get('teleportation'); tr = (tele.maxRange or 12) if tele else 0
    if tele is None or (tele.currentCooldown or 0) > (0 if check else 1):
        return out                  # no teleport now (check) / by next turn: no tele-walk dive
    for g in goal_cells(axis):
        for t in stand_cells(g):
            tx, ty = cxy(t); fs = []
            for dx in range(-mp, mp + 1):
                for dy in range(-mp + abs(dx), mp - abs(dx) + 1):
                    f = cell_at(tx + dx, ty + dy)
                    if f is None or f.id == m.cell.id or f.obstacle or not f.empty:
                        continue
                    dm = dist(m.cell.id, f.id)
                    if dm < 1 or dm > tr or dist(f.id, cc) > sr:
                        continue
                    fs.append((dist(f.id, t), f))
            fs.sort(key=lambda k: k[0])
            for d_, f in fs[:6 if check else 1]:
                if check:
                    try:
                        if tele is None or not m.canUseChipOnCell(tele, f):
                            continue
                    except Exception:
                        continue
                    if f.id != t and path_ok(f.id, t, mp) is None:
                        continue
                out.append((f.id, t, g, d_))
                break
    return out


def tele_first(tp_avail):
    if not ready('teleportation') or not has('spark'):
        return False
    need = ccost('teleportation') + ccost('spark') + ccost('resurrection')
    if tp_avail < need:
        return False
    m = me(); cands = []
    for cid, (e, axis) in BOSS['crystals'].items():
        if not e.alive or e.cell is None or solved(cid) or (e.life or 0) > 8 or (e.absoluteShield or 0) > 0:
            continue
        cc_ = claim_cost(cid)
        if cc_ is None:
            continue
        for o in tele_walk_options(cid, m.mp or 0, True):
            cands.append((threat_at(o[1]) * 10 + o[3] * 0.5 + dist(o[2], BOSS['gcell']) * 0.1 + cc_, cid, o))
    cands.sort(key=lambda k: k[0])
    for _, cid, (f, t, g, _d) in cands[:15]:
        if f != t and path_ok(f, t, m.mp or 0) is None:
            continue
        adrenaline_if(need)
        if (m.tp or 0) < need:
            return False
        e = BOSS['crystals'][cid][0]
        if not ok(m.useChipOnCell(my_chips()['teleportation'], f)) or m.cell.id != f:
            bnote('tele failed %d' % f); return False
        r = m.useChip(my_chips()['spark'], e)
        if e.alive:
            bnote('tele-walk spark did not kill %s r=%s' % (ename(e), r)); return False
        bnote('KR-TW %s tele %d walk %d -> %d' % (ename(e), f, t, g))
        exec_revive(cid, (t, g, False))
        return True
    return False


def nearest_stand(cid):
    best = None; bd = 999; mine = me().cell.id
    for g in goal_cells(BOSS['crystals'][cid][1]):
        for t in stand_cells(g):
            d = dist(mine, t)
            if d < bd:
                bd, best = d, t
    return best


def read_claims():
    """Crystal claims of the allies who played since my last turn (messages are cleared after each of
    my turns, so the batch holds every ally's latest word): author id -> crystal id (-1 = released)."""
    cl = {}
    try:
        for msg in Network.getMessages() or []:
            if msg.type != CLAIM_MSG:
                continue
            p = msg.params
            if p is None or len(p) < 2 or int(p[0]) != CLAIM_TAG:
                continue
            a = msg.author
            if a is not None:
                cl[a.id] = int(p[1])
    except Exception as ex:
        bnote('claims read failed %s' % ex)
    BOSS['claims'] = cl
    return cl


def send_claim(cid):
    try:
        Network.sendAll(CLAIM_MSG, [CLAIM_TAG, -1 if cid is None else cid])
    except Exception as ex:
        bnote('claim send failed %s' % ex)


def claim_cost(cid):
    """Solve preference: my crystal first, then unclaimed ones; an ally's claimed crystal is never taken
    (None) - stealing it sent the ally across the map in 3 of 10 local replays."""
    if cid == BOSS['mine']:
        return 0
    al = set(a.id for a in Fight.getAliveAllies())
    if any(c == cid and a in al and a != me().id for a, c in BOSS['claims'].items()):
        return None
    return 2


def _crystal_open(cid):
    c = BOSS['crystals'].get(cid)
    return c is not None and c[0].alive and c[0].cell is not None and not solved(cid)


def eta(l, cid):
    """Turns until leek l can solve crystal cid: one dive covers teleport (12) + spark (10) when its
    teleport is ready, walk + spark otherwise; the rest is walked at its MP; teleport opens on turn 2."""
    e = BOSS['crystals'][cid][0]
    d = dist(l.cell.id, e.cell.id)
    mp = max(3, l.maxMP or l.mp or 5)
    tele = next((c for c in (l.chips or []) if c.name == 'teleportation'), None)
    try:
        tcd = (tele.currentCooldownOf(l) or 0) if tele is not None else 99
    except Exception:
        tcd = 0
    reach = 22 if tcd <= 1 else mp + 10
    walk = max(0, d - reach)
    t = 1 + (walk + mp - 1) // mp
    if Fight.turn == 1 and tcd <= 1 and walk == 0 and d > mp + 10:
        t = 2                     # teleport still cooling down on turn 1
    return t


def assign(leeks, crys):
    """Leek -> crystal minimizing the slowest solve (then the total), over every pairing (<= 4 x 4)."""
    if not leeks or not crys:
        return {}
    E = {(l.id, c): eta(l, c) for l in leeks for c in crys}
    ids = [l.id for l in leeks]
    best = [None, None]

    def rec(i, used, acc):
        if i == len(ids):
            key = (-len(acc), max([v for _, _, v in acc] or [0]), sum(v for _, _, v in acc))
            if best[0] is None or key < best[0]:
                best[0] = key; best[1] = list(acc)
            return
        rec(i + 1, used, acc)                      # this leek takes no crystal
        for c in crys:
            if c not in used:
                rec(i + 1, used | {c}, acc + [(ids[i], c, E[(ids[i], c)])])

    rec(0, frozenset(), [])
    # every crystal must be covered when there are enough leeks: prefer pairings covering more crystals
    out = {}
    if best[1]:
        for lid, c, _ in best[1]:
            out[lid] = c
    return out


def my_crystal():
    """My crystal, sticky until it is solved: allies announce their crystal every turn (Network
    messages), so a crystal claimed by another leek is never chased twice and leeks no longer swap
    targets mid-route. A free leek picks by greedy closest (leek, crystal) pairs over unclaimed
    crystals and unclaimed leeks whose resurrection is ready (within spark range counts as 0)."""
    if BOSS.get('mine_turn') == Fight.turn:
        return BOSS['mine']
    BOSS['mine_turn'] = Fight.turn
    claims = read_claims()
    alive = set(a.id for a in Fight.getAliveAllies())
    taken = set(c for a, c in claims.items() if c >= 0 and a in alive and _crystal_open(c))
    mid = me().id
    cur = BOSS['mine']
    if cur is not None and (not _crystal_open(cur) or cur in taken or not ready('resurrection')):
        bnote('release %s' % ename(BOSS['crystals'][cur][0]) if cur in BOSS['crystals'] else 'release')
        cur = None
    if cur is None:
        leeks = []
        for a in Fight.getAliveAllies():
            if a.summoned or a.cell is None:
                continue
            if a.id != mid and claims.get(a.id, -1) in taken:
                continue
            rez = next((c for c in (a.chips or []) if c.name == 'resurrection'), None)
            if rez is None:
                continue
            try:
                if (rez.currentCooldownOf(a) or 0) > 0:
                    continue
            except Exception:
                pass
            leeks.append(a)
        crys = [cid for cid in BOSS['crystals'] if cid not in taken and _crystal_open(cid)]
        cur = assign(leeks, crys).get(mid)
        if cur is not None:
            bnote('claim %s (eta %d)' % (ename(BOSS['crystals'][cur][0]), eta(me(), cur)))
    BOSS['mine'] = cur
    return cur


def go_to(dest):
    m = me()
    if dest is None or m.cell.id == dest:
        return
    mp0 = m.mp or 0
    if dist(m.cell.id, dest) > 1:
        m.moveToward(Cell.get(dest))
    if (m.mp or 0) == mp0 and mp0 > 0:
        rc = reachable(m.cell.id, mp0); bc = m.cell.id; bd = dist(bc, dest)
        for c in rc:
            if c not in CORRIDOR and dist(c, dest) < bd:
                bd, bc = dist(c, dest), c
        if bc != m.cell.id:
            m.moveToward(Cell.get(bc))


def unpark():
    """Never end a turn on a corridor cell: step to the nearest reachable non-corridor cell."""
    m = me()
    if m.cell is None or m.cell.id not in CORRIDOR or (m.mp or 0) <= 0:
        return
    if not BOSS['combat'] and ready('resurrection'):
        return                      # still on my way to a dive: corridors are the way through
    rc = reachable(m.cell.id, m.mp or 0)
    cand = [c for c in rc if c not in CORRIDOR]
    if cand:
        frm = m.cell.id
        best = min(cand, key=lambda c: (rc[c], threat_at(c)))
        m.moveToward(Cell.get(best))
        bnote('unpark %d -> %d' % (frm, m.cell.id))


def tele_stage(cid):
    """(unused: 4 of 4 server fights where it fired put the leek next to the King - dead by T6, lost)
    No dive this turn and the walk is long: teleport (walls do not matter) to a cell from which NEXT
    turn's walk-dive works - a stand cell t within spark range of the crystal reachable within my MP."""
    if not ready('teleportation') or (me().tp or 0) < ccost('teleportation') or not has('spark'):
        return False
    m = me(); e, axis = BOSS['crystals'][cid]
    if e.cell is None:
        return False
    cc = e.cell.id
    tele = my_chips()['teleportation']; tr = tele.maxRange or 12
    sr = my_chips()['spark'].maxRange or 10
    mp = max(1, m.maxMP or m.mp or 5)
    best = None; bs = 1e9
    for g in goal_cells(axis):
        for t in stand_cells(g):
            if dist(t, cc) > sr:
                continue
            tx, ty = cxy(t)
            for dx in range(-mp, mp + 1):
                for dy in range(-mp + abs(dx), mp - abs(dx) + 1):
                    f = cell_at(tx + dx, ty + dy)
                    if f is None or f.obstacle or not f.empty or f.id in CORRIDOR:
                        continue
                    dm = dist(m.cell.id, f.id)
                    if dm < 1 or dm > tr:
                        continue
                    sc = threat_at(f.id) * 10 + dist(f.id, t)
                    if sc >= bs:
                        continue
                    try:
                        if not m.canUseChipOnCell(tele, f):
                            continue
                    except Exception:
                        continue
                    if f.id != t and path_ok(f.id, t, max(0, mp - 2)) is None:
                        continue            # 2 MP of slack: allies moving into the path broke the follow-up dive
                    bs, best = sc, f.id
    if best is None:
        return False
    if ok(m.useChipOnCell(tele, Cell.get(best))) and m.cell.id == best:
        bnote('tele-stage %s -> %d' % (ename(e), best))
        return True
    return False


def approach():
    """Stage for next turn's solve: within teleport + walk reach of a revive cell of my crystal."""
    cid = my_crystal()
    if cid is None:
        return
    e = BOSS['crystals'][cid][0]
    t = nearest_stand(cid)
    if t is None:
        bnote('no revive cell for %s' % ename(e)); return
    if tele_walk_options(cid, me().maxMP or 0) and BOSS['in_reach'] < 1:
        BOSS['in_reach'] += 1; bnote('in reach %s' % ename(e)); return
    if BOSS['in_reach'] >= 1:
        bnote('in reach but no dive, closing in on %d' % t); go_to(t); return
    cc = e.cell.id
    dest = cc if dist(me().cell.id, cc) > 9 else t
    go_to(dest)
    bnote('stage %s toward %d (d=%d)' % (ename(e), dest, dist(me().cell.id, dest)))


# ---- sustain / roles -------------------------------------------------------------
def poison_on(a):
    return sum((f.value or 0) for f in (a.effects or []) if f.type == E_POISON)


def cleanse():
    if not ready('antidote') or (me().tp or 0) < ccost('antidote'):
        return False
    best = None; bp = 150
    for a in Fight.getAliveAllies():
        if a.summoned:
            continue
        p = poison_on(a) * ((3 if poison_on(a) >= 300 else 1.2) if a.id == me().id else 1)
        if p > bp:
            try:
                if not me().canUseChip(my_chips()['antidote'], a):
                    continue
            except Exception:
                continue
            bp, best = p, a
    if best is None:
        return False
    r = cast_on('antidote', best)
    if r:
        bnote('antidote %s (%d/turn)' % (ename(best), bp))
    return r


def sustain():
    m = me()
    cleanse()
    life = m.life or 0; tot = m.maxLife or 1
    if life < tot * 0.5 and not BOSS['regen'] and cast_self('regeneration'):
        BOSS['regen'] = True
    if life < tot * 0.6:
        cast_self('elevation')
    if tot - (m.life or 0) > 250:
        cast_self('remission')
    if any(dist(m.cell.id, e.cell.id) <= 10 for e in army()):
        for n in ('fortress', 'wall', 'armor', 'solidification'):
            cast_self(n)
        if ready('rampart') and (m.tp or 0) >= ccost('rampart'):
            tgt = None; worst = 1.0
            for a in Fight.getAliveAllies():
                if a.id == m.id or a.summoned:
                    continue
                fr = (a.life or 0) / max(1, a.maxLife or 1)
                if fr < worst:
                    try:
                        if me().canUseChip(my_chips()['rampart'], a):
                            worst, tgt = fr, a
                    except Exception:
                        pass
            if tgt is not None:
                cast_on('rampart', tgt)
    if tot - (m.life or 0) > 400:
        cast_self('serum')


def self_stack():
    for n in ('rage', 'seven_league_boots', 'fortress', 'wall', 'armor', 'solidification', 'knowledge'):
        cast_self(n)


def king_cell():
    for e in Fight.getAliveEnemies():
        if ename(e) == 'fennel_king' and e.cell is not None:
            return e.cell.id
    return None


def threat_on(a):
    return sum(1 for e in army() if dist(a.cell.id, e.cell.id) <= 8)


def protect_score(a):
    return (40 if (a.resistance or 0) < 200 else 0) + threat_on(a) * 10 + (1 - (a.life or 0) / max(1, a.maxLife or 1)) * 5


def fragile_ally():
    best = None; bs = -1
    for a in Fight.getAliveAllies():
        if a.id == me().id or a.summoned or a.cell is None or (a.resistance or 0) >= 200:
            continue
        s = protect_score(a)
        if s > bs:
            bs, best = s, a
    return best


def has_effect_from(a, n):
    c = my_chips().get(n)
    if c is None:
        return False
    for f in (a.effects or []):
        try:
            if f.raw[5] == c.id:
                return True
        except Exception:
            pass
    return False


def tank_self_first():
    kc = king_cell()
    if (kc is not None and dist(me().cell.id, kc) <= 7) or threat_on(me()) >= 2:
        cast_self('fortress'); cast_self('wall')


def tank_step_back():
    """Leftover MP: out of the king's reach (6), within rampart range (7) of the fragile ally."""
    m = me(); kc = king_cell()
    if kc is None or (m.mp or 0) <= 0 or dist(m.cell.id, kc) > 6:
        return
    fa = fragile_ally(); best = m.cell.id; bs = -999
    for c in reachable(m.cell.id, m.mp or 0):
        if c in CORRIDOR or (fa is not None and dist(c, fa.cell.id) > 7):
            continue
        s = min(dist(c, kc), 9) * 3 - threat_at(c)
        if s > bs:
            bs, best = s, c
    if best != m.cell.id:
        m.moveToward(Cell.get(best))


def allies_by_protect():
    return sorted([a for a in Fight.getAliveAllies() if a.id != me().id and not a.summoned and a.cell is not None],
                  key=lambda a: -protect_score(a))


def tank_shields_only():
    cleanse(); tank_self_first()
    m = me(); fa = fragile_ally()
    if fa is not None and (m.mp or 0) > 0 and dist(m.cell.id, fa.cell.id) > 6:
        m.moveToward(fa, max(0, dist(m.cell.id, fa.cell.id) - 6))
    keyed = allies_by_protect()
    for n in ('carapace', 'rampart', 'fortress'):
        for a in keyed:
            if cast_on(n, a):
                break
    cast_self('wall'); cast_self('armor')
    place_wall()
    tank_step_back()


def shield_diver_first():
    if my_role() != 'tank':
        return
    fa = fragile_ally()
    if fa is None:
        return
    rez = next((c for c in (fa.chips or []) if c.name == 'resurrection'), None)
    try:
        if rez is None or (rez.currentCooldownOf(fa) or 0) > 0:
            return
    except Exception:
        return
    m = me()
    if dist(m.cell.id, fa.cell.id) > 7 and (m.mp or 0) > 0:
        m.moveToward(fa, dist(m.cell.id, fa.cell.id) - 6)
    if cast_on('rampart', fa):
        bnote('pre-dive rampart %s' % ename(fa))
    if cast_on('carapace', fa):
        bnote('pre-dive carapace %s' % ename(fa))


def striker_stage():
    """After its dive: out of the king's reach (> 6) but within weapon range (<= 10) of the scribe."""
    m = me()
    if (m.mp or 0) <= 0:
        return
    kc = king_cell()
    sc = next((e.cell.id for e in Fight.getAliveEnemies() if ename(e) == 'fennel_scribe' and e.cell is not None), None)
    if sc is None:
        a = army()
        if a:
            m.moveAwayFromEntities(a)
        return
    best = m.cell.id; bs = -9999
    for c, st in reachable(m.cell.id, m.mp or 0).items():
        if c in CORRIDOR:
            continue
        ds = dist(c, sc); dk = 20 if kc is None else dist(c, kc)
        v = (50 - abs(ds - 8) if ds <= 10 else -ds * 3) + min(dk, 9) * 4 - threat_at(c) * 2
        if v > bs:
            bs, best = v, c
    if best != m.cell.id:
        m.moveToward(Cell.get(best))


def puzzle_turn():
    my_crystal()            # reads the allies' claims once per turn
    try:
        puzzle_play()
        unpark()
    finally:
        cur = BOSS['mine']
        send_claim(cur if cur is not None and _crystal_open(cur) and ready('resurrection') else None)


def puzzle_play():
    save_dead_crystals()
    m = me()
    if Fight.turn == 1:
        cast_self('motivation'); cast_self('leather_boots')
        if not try_solve_one():
            cast_self('armor'); cast_self('wall'); cast_self('shield')
            approach()
        self_stack()
        return
    # (the tank dives first when it can: its pre-dive shields on the fragile ally left it short of the
    # 30 TP a dive needs, turn after turn)
    solved_now = my_role() == 'tank' and try_solve_one()
    if not solved_now:
        shield_diver_first()
    # (the old buffer hold - dive only once the tank's shields are on her - made her the late solver in
    # 8 of 10 server fights; she dives as soon as she can)
    solved_now = solved_now or try_solve_one()
    if not solved_now and ready('resurrection'):
        approach()
        if pre_disarm_on():
            disarm()        # no dive this turn: the TP would go unspent - disarm the King if he is in reach
        if my_role() == 'buffer':
            cast_self('rage'); cast_self('seven_league_boots')
    sustain()
    if not ready('resurrection'):
        role = my_role()
        pzd = pz_disarm_on()
        if role == 'tank':
            tank_shields_only()
            if pzd:
                disarm(('fennel_king',))
        elif role == 'striker':
            if pzd:
                disarm()
            striker_stage()
        elif role == 'buffer' and BOSS['tank_cell'] is not None:
            if pzd:
                disarm()
            if dist(m.cell.id, BOSS['tank_cell']) > 3:
                go_to(BOSS['tank_cell'])
        else:
            a = army()
            if a and (m.mp or 0) > 0:
                m.moveAwayFromEntities(a)


# ---- combat ----------------------------------------------------------------------
def boss_focus():
    """Squad focus: scribe -> knights -> king -> squires, lowest life + shield first; crystals once the
    army is dead. The first of the top 3 I can reach this turn, else the head of the order."""
    cands = army()
    if not cands:
        cands = [e for e in Fight.getAliveEnemies() if ename(e) in AXIS and e.cell is not None]
    if not cands:
        cands = [e for e in Fight.getAliveEnemies() if e.cell is not None]
    order = sorted(cands, key=lambda e: _ARMY_RANK.get(ename(e), 4) * 100000 + (e.life or 0) + (e.absoluteShield or 0))
    m = me()
    for e in order[:3]:
        if dist(m.cell.id, e.cell.id) <= (m.mp or 0) + 12:
            return e
    return order[0] if order else None


# ---- combat: strikers + plants (fennel.lk) -------------------------------------------
def focus_order():
    cands = army()
    if not cands:
        cands = [e for e in Fight.getAliveEnemies() if ename(e) in AXIS and e.cell is not None]
    if not cands:
        cands = [e for e in Fight.getAliveEnemies() if e.cell is not None and ename(e) != 'graal']
    return sorted(cands, key=lambda e: _ARMY_RANK.get(ename(e), 4) * 100000 + (e.life or 0) + (e.absoluteShield or 0))


def area_hits_ally(cells):
    if not cells:
        return False
    occ = set(a.cell.id for a in Fight.getAliveAllies() if a.cell is not None)
    return any(c is not None and c.id in occ for c in cells)


def offensive(item):
    try:
        return any(f.type in (E_DAMAGE, E_POISON, E_NOVA) for f in (item.features or []))
    except Exception:
        return False


def weapon_reach(t):
    """(cell, steps, weapon): shortest walk to a cell from which a weapon hits t, preferring cells
    inside the tank's shield range (3); None when no weapon reaches this turn."""
    m = me(); mp = m.mp or 0; tc = BOSS['tank_cell']
    rc = reachable(m.cell.id, mp); best = None; bk = 1e9
    for w in (m.weapons or []):
        try:
            cells = m.weaponCells(t, w) or []
        except Exception:
            cells = []
        for c in cells:
            d = rc.get(c.id)
            if d is None:
                continue
            pen = 3 if (tc is not None and dist(c.id, tc) > 3) else 0
            if d + pen < bk:
                bk, best = d + pen, (c.id, d, w)
    return best


def pick_target():
    """The squad focus if I can hit it this turn, else the first of the top 3 I can hit."""
    order = focus_order()
    m = me()
    for e in order[:3]:
        if dist(m.cell.id, e.cell.id) > (m.mp or 0) + 12:
            continue
        if weapon_reach(e) is not None:
            return e
    return order[0] if order else None


def _held(m):
    try:
        return m.weapon.id if m.weapon is not None else None
    except Exception:
        return None


def fire(w, t, n=8):
    """Every shot of weapon w at t (switching costs 1 TP); never when the area hits an ally."""
    m = me(); shots = 0
    if (w.cost or 0) + (0 if _held(m) == w.id else 1) > (m.tp or 0):
        return 0
    try:
        if not m.canUseWeapon(t, w) or area_hits_ally(w.effectiveArea(t.cell)):
            return 0
    except Exception:
        return 0
    if _held(m) != w.id:
        m.setWeapon(w)
    for _ in range(n):
        if not t.alive or not m.canUseWeapon(t) or not ok(m.useWeapon(t)):
            break
        shots += 1
    return shots


def strip(t):
    if ((t.absoluteShield or 0) > 100 or (t.relativeShield or 0) > 15) and ready('liberation'):
        cast_on('liberation', t)


def attack(t):
    m = me()
    cast_self('steroid'); cast_self('protein')
    strip(t)
    # hemorrhage (unhealable 1 turn): the army's remissions saved the scribe / knights 10-20k per fight
    if ready('hemorrhage') and (m.tp or 0) >= ccost('hemorrhage') + 8 and _ARMY_RANK.get(ename(t), 4) <= 1:
        if dist(m.cell.id, t.cell.id) > 2 and (m.mp or 0) > 0:
            try:
                hc = m.chipCells(my_chips()['hemorrhage'], t) or []
            except Exception:
                hc = []
            rc = reachable(m.cell.id, m.mp or 0)
            cand = [c.id for c in hc if c.id in rc]
            if cand:
                bh = min(cand, key=lambda c: rc[c])
                if bh != m.cell.id:
                    m.moveToward(Cell.get(bh))
        if cast_on('hemorrhage', t):
            bnote('hemorrhage %s' % ename(t))
    r = weapon_reach(t)
    if r is None:
        m.moveToward(t)
        strip(t)
    else:
        if r[0] != m.cell.id:
            m.moveToward(Cell.get(r[0]))
        fire(r[2], t)
    for w in (m.weapons or []):
        if not t.alive:
            break
        fire(w, t)
    for ch in (m.chips or []):
        if not t.alive:
            break
        if ch.name == 'spark' or not offensive(ch) or (ch.currentCooldown or 0) > 0 or (m.tp or 0) < (ch.cost or 0):
            continue
        try:
            if not m.canUseChip(ch, t) or area_hits_ally(ch.effectiveArea(t.cell)):
                continue
        except Exception:
            continue
        m.useChip(ch, t)


def pre_disarm_on():
    if BOSS_PRE_DISARM == 'parity':
        try:
            return Fight.id % 2 == 1
        except Exception:
            return True
    return bool(BOSS_PRE_DISARM)


def pz_disarm_on():
    if BOSS_PZ_DISARM == 'parity':
        try:
            return Fight.id % 2 == 1
        except Exception:
            return True
    return bool(BOSS_PZ_DISARM)


def disarm_on():
    if BOSS_DISARM == 'parity':
        try:
            return Fight.id % 2 == 1
        except Exception:
            return True
    return bool(BOSS_DISARM)


def amputated(e):
    try:
        return any(f.type == E_ADD_STATE and int(f.value or 0) == ST_AMPUTATED for f in (e.effects or []))
    except Exception:
        return False


def saber():
    for w in (me().weapons or []):
        try:
            if 'glowing_saber' in (w.name or ''):
                return w
        except Exception:
            pass
    return None


def disarm(names=('fennel_king', 'fennel_scribe'), reserve=0):
    """Glowing saber on the King (Excalibur: ~750 a swing + ~750 poison for 2 turns), else the scribe
    (heavy sword): amputated, no weapon until my next turn. States are not damage, so it lands through
    Divine Protection too. Melee: walk next to the target within MP; skip a target already disarmed."""
    if not disarm_on():
        return False
    m = me(); w = saber()
    if w is None:
        return False
    cost = (w.cost or 12) + (0 if _held(m) == w.id else 1)
    if (m.tp or 0) - reserve < cost:
        return False
    rc = None
    for n in names:
        t = next((e for e in army() if ename(e) == n), None)
        if t is None or amputated(t):
            continue
        try:
            if t.weapon is None:
                continue
        except Exception:
            continue
        if rc is None:
            rc = reachable(m.cell.id, m.mp or 0)
        try:
            cells = m.weaponCells(t, w) or []
        except Exception:
            cells = []
        cand = [c.id for c in cells if c.id in rc]
        if not cand:
            continue
        best = min(cand, key=lambda c: (rc[c], threat_at(c)))
        if best != m.cell.id:
            m.moveToward(Cell.get(best))
        if _held(m) != w.id:
            m.setWeapon(w)
        try:
            if m.canUseWeapon(t) and ok(m.useWeapon(t)):
                bnote('DISARM %s' % n)
                return True
        except Exception:
            pass
    return False


def striker_turn():
    """Shots first (inside the tank's dome radius when possible), then sustain, then back to the tank."""
    cleanse()
    m = me()
    if (m.life or 0) < (m.maxLife or 1) * 0.35 and not BOSS['regen'] and cast_self('regeneration'):
        BOSS['regen'] = True
    disarm()
    t = pick_target()
    if t is not None:
        bnote('focus %s %d' % (ename(t), t.life or 0))
        attack(t)
    sustain()
    tk = squad('tank')
    if tk and (m.mp or 0) > 0 and dist(m.cell.id, tk[0].cell.id) > 3:
        m.moveToward(tk[0].cell, m.mp)


def plant_ai():
    """Summons (Corn heals, Prototaxite has no chips): heal the most hurt ally in range, else self."""
    m = me(); best = None; bf = 1.0
    for a in Fight.getAliveAllies():
        if a.summoned:
            continue
        f = (a.life or 0) / max(1, a.maxLife or 1)
        if f < bf:
            bf, best = f, a
    for ch in (m.chips or []):
        if (ch.currentCooldown or 0) > 0 or (m.tp or 0) < (ch.cost or 0):
            continue
        try:
            if best is not None and m.canUseChip(ch, best):
                m.useChip(ch, best)
            elif m.canUseChip(ch, m):
                m.useChip(ch, m)
        except Exception:
            pass


def place_wall():
    """Tank: a Prototaxite wall on the line between the king and the ally it threatens most."""
    if not ready('prototaxite') or (me().tp or 0) < ccost('prototaxite'):
        return False
    kc = king_cell()
    if kc is None:
        kc = next((e.cell.id for e in Fight.getAliveEnemies() if ename(e) == 'evil_pumpkin' and e.cell is not None), None)
    if kc is None:
        return False
    prot = None; bd = 99
    for a in Fight.getAliveAllies():
        if a.summoned or a.cell is None:
            continue
        d = dist(a.cell.id, kc) - (3 if (a.resistance or 0) < 200 else 0)
        if d < bd:
            bd, prot = d, a
    if prot is None or dist(prot.cell.id, kc) > 12:
        return False
    pc = prot.cell.id; x, y = cxy(pc); best = None; bs = 999
    chip = my_chips()['prototaxite']
    for dx in range(-4, 5):
        for dy in range(-4 + abs(dx), 5 - abs(dx)):
            c = cell_at(x + dx, y + dy)
            if c is None or c.obstacle or not c.empty:
                continue
            dp = dist(c.id, pc)
            if dp < 1 or dp > 3:
                continue
            try:
                if not me().canUseChipOnCell(chip, c):
                    continue
            except Exception:
                continue
            sc = dist(c.id, kc) + dp - dist(pc, kc)      # 0 when c sits on the king-ally line
            if sc < bs:
                bs, best = sc, c
    if best is None:
        return False
    if ok(me().summon(chip, best, plant_ai)):
        bnote('wall at %d for %s' % (best.id, ename(prot)))
        return True
    return False


def place_corn():
    """Buffer: a Corn where its popcorn (radius 3) covers the most allies."""
    if not ready('corn') or (me().tp or 0) < ccost('corn'):
        return False
    m = me(); x, y = cxy(m.cell.id); best = None; bs = 0
    chip = my_chips()['corn']
    mates = [a for a in Fight.getAliveAllies() if not a.summoned and a.cell is not None]
    for dx in range(-5, 6):
        for dy in range(-5 + abs(dx), 6 - abs(dx)):
            c = cell_at(x + dx, y + dy)
            if c is None or c.obstacle or not c.empty:
                continue
            n = sum(1 for a in mates if dist(c.id, a.cell.id) <= 3)
            if n < 2:
                continue
            sc = n * 10 - threat_at(c.id)
            if sc > bs:
                try:
                    if not m.canUseChipOnCell(chip, c):
                        continue
                except Exception:
                    continue
                bs, best = sc, c
    if best is None:
        return False
    if ok(m.summon(chip, best, plant_ai)):
        bnote('corn at %d' % best.id)
        return True
    return False


def tank_turn():
    cleanse()
    m = me(); mates = [a for a in Fight.getAliveAllies() if not a.summoned and a.id != m.id and a.cell is not None]
    if mates and (m.mp or 0) > 0:
        best = m.cell.id; bs = -999
        for c, st in reachable(m.cell.id, m.mp or 0).items():
            if c in CORRIDOR:
                continue
            cov = sum((3 if role_of(a) == 'striker' else 1) for a in mates if dist(c, a.cell.id) <= 3)
            s = cov * 10 - threat_at(c) * 2 - st * 0.1
            if s > bs:
                bs, best = s, c
        if best != m.cell.id:
            m.moveToward(Cell.get(best))
    cast_self('solidification')
    covered = sum(1 for a in mates if dist(m.cell.id, a.cell.id) <= 3)
    if covered >= min(2, len(mates)) and army() and cast_self('dome'):
        bnote('flip DOME covers %d' % covered)
    keyed = sorted(mates, key=lambda a: -(protect_score(a) + (3 if role_of(a) == 'striker' else 0)))
    tank_self_first()
    disarm(('fennel_king',))
    for n in ('rampart', 'carapace', 'fortress'):
        for a in keyed:
            if cast_on(n, a):
                break
    cast_self('wall'); cast_self('armor'); cast_self('shield')
    place_wall()
    tank_step_back()
    if (m.life or 0) < (m.maxLife or 1) * 0.35 and not BOSS['regen'] and cast_self('regeneration'):
        BOSS['regen'] = True
    tg = pick_target()
    if tg is not None and ready('liberation') and ((tg.absoluteShield or 0) > 100 or (tg.relativeShield or 0) > 15):
        cast_on('liberation', tg)
    disarm(('fennel_king',))


def buffer_turn():
    cleanse()
    disarm()                    # a disarmed King cannot Excalibur anyone (the army's poison source)
    m = me(); st = squad('striker'); tanks = squad('tank')
    if st and (m.mp or 0) > 0:
        best = m.cell.id; bs = -999
        for c in reachable(m.cell.id, m.mp or 0):
            if c in CORRIDOR:
                continue
            s = 0
            for a in st:
                d = dist(c, a.cell.id); s += 10 if d <= 5 else -d
            for t in tanks:
                dt = dist(c, t.cell.id); s += 15 if dt <= 3 else (6 if dt <= 6 else 0)
            s -= threat_at(c) * 3
            if s > bs:
                bs, best = s, c
        if best != m.cell.id:
            m.moveToward(Cell.get(best))
    for t in tanks:
        cast_on('bark', t)
    fer = BOSS['fer']
    if fer is None or not any(a.id == fer for a in st):
        fer = max(st, key=lambda a: a.maxLife or 0).id if st else None
        BOSS['fer'] = fer
    if fer is not None:
        tgt = next((a for a in st if a.id == fer), None)
        if tgt is not None:
            cast_on('ferocity', tgt)
    centre = None; cn = -1
    for a in st:
        n = sum(1 for b in Fight.getAliveAllies() if not b.summoned and b.cell is not None and dist(b.cell.id, a.cell.id) <= 2)
        if n > cn:
            cn, centre = n, a
    if centre is not None:
        for n in ('doping', 'rage', 'seven_league_boots'):
            cast_on(n, centre)
        for a in st:
            for n in ('steroid', 'protein', 'acceleration'):
                cast_on(n, a)
    place_corn()
    cast_self('wall'); cast_self('armor')
    if (m.life or 0) < (m.maxLife or 1) * 0.35 and not BOSS['regen'] and cast_self('regeneration'):
        BOSS['regen'] = True
    a2 = army()
    if a2 and (m.mp or 0) > 0 and threat_at(m.cell.id) > 2:
        m.moveAwayFromEntities(a2)


def is_healer():
    return (me().magic or 0) > (me().strength or 0)


def healer_turn():
    m = me()
    allies = [a for a in Fight.getAliveAllies() if not a.summoned and a.cell is not None]

    def hurt(a):
        return (1 - (a.life or 0) / max(1, a.maxLife or 1)) * 10 + sum(1 for e in army() if dist(a.cell.id, e.cell.id) <= 7)
    keyed = sorted(allies, key=lambda a: -hurt(a))
    t = keyed[0] if keyed else m
    if t.id != m.id and dist(m.cell.id, t.cell.id) > 3:
        m.moveToward(t, max(0, dist(m.cell.id, t.cell.id) - 3))
    if (m.life or 0) < (m.maxLife or 1) * 0.35 and not BOSS['regen'] and cast_self('regeneration'):
        BOSS['regen'] = True
    lost = (t.maxLife or 0) - (t.life or 0)
    if lost > 250:
        cast_on('remission', t)
    if lost > 400:
        cast_on('serum', t)
    for n in ('fortress', 'wall', 'armor', 'shield'):
        cast_on(n, t)
    if len(keyed) > 1:
        t2 = keyed[1]
        if (t2.maxLife or 0) - (t2.life or 0) > 250:
            cast_on('remission', t2)
        cast_on('wall', t2); cast_on('armor', t2)
    if army():
        cast_self('wall'); cast_self('fortress')
    # leftover TP: whatever the weapons reach
    tg = pick_target()
    if tg is not None and (m.tp or 0) >= 4:
        for w in (m.weapons or []):
            fire(w, tg, 4)


def boss_turn():
    """Run the boss mode for this turn (fennel.lk doctrine, every role scripted). Returns None (the turn
    was played here)."""
    boss_scan()
    if Fight.turn == 1:
        bnote('arm %s pz%s pre%s' % ('disarm' if disarm_on() else 'nodisarm', 'on' if pz_disarm_on() else 'off',
                                     'on' if pre_disarm_on() else 'off'))
    if not BOSS['combat']:
        puzzle_turn()
        return None
    r = my_role()
    if r == 'tank':
        tank_turn()
    elif r == 'buffer':
        buffer_turn()
    elif squad('tank'):
        striker_turn()
    elif is_healer():
        healer_turn()
    else:
        m = me()
        if (m.life or 0) < (m.maxLife or 1) * 0.35 and not BOSS['regen'] and cast_self('regeneration'):
            BOSS['regen'] = True
        t = pick_target()
        if t is not None:
            attack(t)
        sustain()
    unpark()
    return None


def boss_flush():
    if BLOG:
        log('BOSS T%d %s %s: %s' % (Fight.turn, 'combat' if BOSS['combat'] else 'puzzle', ename(me()), ' | '.join(BLOG)))
        del BLOG[:]


# ---- Evil Pumpkin (boss 3) ---------------------------------------------------------------------
# The pumpkin and its minions open under Divine Protection (state 3, cast by the pumpkin, permanent);
# a mob loses it when its own exasperation crits or when the mob that cast it dies, one target at a
# time. The pumpkin teleports next to a leek and scythes it (~2.8k, the winners take it with 3.3k
# life + T0 shields). Doctrine v1: disarm the pumpkin with the glowing saber whenever reachable (a
# state lands through Divine Protection), shield/heal while every enemy is invincible, the V10
# search on the vulnerable focus otherwise.
PUMPKIN = {'on': None}
PK_SHIELDS = ('solidification', 'fortress', 'wall', 'armor', 'helmet', 'shield', 'armoring', 'elevation')


def pumpkin_on():
    if PUMPKIN['on'] is None:
        try:
            PUMPKIN['on'] = any(ename(e) == 'evil_pumpkin' for e in Fight.getEnemies())
        except Exception:
            PUMPKIN['on'] = False
    return PUMPKIN['on']


def is_invincible(e):
    try:
        return any(f.type == E_ADD_STATE and int(f.value or 0) == ST_INVINCIBLE for f in (e.effects or []))
    except Exception:
        return False


def pk_vulnerable():
    return [e for e in Fight.getAliveEnemies() if not e.summoned and e.cell is not None and (e.life or 0) > 0
            and not is_invincible(e)]


def bulb_ai():
    """Decoy bulbs: hit the nearest vulnerable enemy with whatever reaches, else stand (the minions
    spend their chips on summons in the winners' fights)."""
    m = me()
    tgt = PK_TARGET.get('cell')
    if tgt is not None:
        PK_TARGET['cell'] = None
        try:
            c = Cell.get(tgt)
            if c is not None and c.empty and (m.mp or 0) > 0:
                m.moveToward(c)
        except Exception:
            pass
        if m.cell is not None and m.cell.id == tgt:
            return                  # standing on the rez cell: the resurrection fails, the mob drops its protection
    vul = pk_vulnerable() if pumpkin_on() else [e for e in Fight.getAliveEnemies() if e.cell is not None]
    if not vul:
        return
    t = min(vul, key=lambda e: dist(m.cell.id, e.cell.id))
    for ch in (m.chips or []):
        if (ch.currentCooldown or 0) > 0 or (m.tp or 0) < (ch.cost or 0):
            continue
        try:
            if offensive(ch) and m.canUseChip(ch, t):
                m.useChip(ch, t)
        except Exception:
            pass
    if (m.mp or 0) > 0:
        m.moveToward(t, m.mp)


def place_decoy():
    """A puny bulb on a free cell 2-4 from me, on the army's side."""
    if not ready('puny_bulb') or (me().tp or 0) < ccost('puny_bulb'):
        return False
    m = me(); a = army()
    if not a:
        return False
    ax = sum(cxy(e.cell.id)[0] for e in a) / len(a); ay = sum(cxy(e.cell.id)[1] for e in a) / len(a)
    x, y = cxy(m.cell.id); chip = my_chips()['puny_bulb']; best = None; bs = 1e9
    for dx in range(-4, 5):
        for dy in range(-4 + abs(dx), 5 - abs(dx)):
            c = cell_at(x + dx, y + dy)
            if c is None or c.obstacle or not c.empty or c.id in CORRIDOR:
                continue
            d = dist(c.id, m.cell.id)
            if d < 2:
                continue
            cx, cy = cxy(c.id)
            sc = abs(cx - ax) + abs(cy - ay)
            if sc < bs:
                try:
                    if not m.canUseChipOnCell(chip, c):
                        continue
                except Exception:
                    continue
                bs, best = sc, c
    if best is None:
        return False
    if ok(m.summon(chip, best, bulb_ai)):
        bnote('decoy at %d' % best.id)
        return True
    return False


PK_DEBUFF = (E_VULN, E_VULN_ABS, E_POISON, E_SHK_MP, E_SHK_TP, E_SHK_STR, E_SHK_MAG, E_SHK_AGI)


def debuffing(item):
    try:
        return any(f.type in PK_DEBUFF for f in (item.features or []))
    except Exception:
        return False


def pk_provoke():
    """Divine Protection drops when the mob cleanses itself (exasperation), and the mobs cleanse the
    debuffs players put on them: winners' mobs exasperate 54% of the turns after being hit (20% when
    not), ours 0.5% - V10 never hit an invincible mob. Leftover TP: debuffing shots (neutrino
    vulnerability, poisons, shackles) on the invincible mobs in reach, minions first."""
    m = me()
    tg = [e for e in army() if is_invincible(e)]
    if not tg:
        return 0
    tg.sort(key=lambda e: (ename(e) == 'evil_pumpkin', dist(m.cell.id, e.cell.id)))
    shots = 0
    for w in (m.weapons or []):
        if not debuffing(w):
            continue
        for t in tg:
            n = fire(w, t)
            if n:
                shots += n
                break
    for ch in (m.chips or []):
        if not debuffing(ch) or (ch.currentCooldown or 0) > 0 or (m.tp or 0) < (ch.cost or 0):
            continue
        for t in tg:
            try:
                if m.canUseChip(ch, t) and not area_hits_ally(ch.effectiveArea(t.cell)) and ok(m.useChip(ch, t)):
                    shots += 1
                    break
            except Exception:
                pass
    if shots:
        bnote('provoke x%d' % shots)
    return shots


# ---- the pumpkin riddle (forum topic 11152, Pilow's hints: Glagolitic, Concatenation, Factorization) ----
# The squashes announce the next resurrection cell in Glagolitic numerals, one part per mob, at the start
# of their turns. Cell = max over the orderings of the last 3 numbers of the largest divisor <= 612 of
# their concatenation (7643/7643 community triples, 320/320 of our resurrections, known before the
# resurrecting mob's turn). Occupying the cell blocks the resurrection: the mob shouts "kopile!!"
# ("bastard!!") and drops its Divine Protection (86% of the winners' drops).
_GLAG = {}
for _i in range(9):
    _GLAG[0x2C00 + _i] = _i + 1
_GLAG[0x2C09] = 10; _GLAG[0x2C0A] = 10
for _i, _o in enumerate(range(0x2C0B, 0x2C13)):
    _GLAG[_o] = (_i + 2) * 10
for _i, _o in enumerate(range(0x2C13, 0x2C1A)):
    _GLAG[_o] = (_i + 1) * 100
_GLAG[0x2C1B] = 800; _GLAG[0x2C1C] = 900; _GLAG[0x2C1D] = 1000
PK_STREAM = []
PK_TARGET = {'cell': None}     # rez cell the bulb I just summoned must walk onto (its turn comes before the mob's)


def glag_num(txt):
    try:
        t = 0
        for ch in txt:
            o = ord(ch)
            if 0x2C30 <= o <= 0x2C5E:
                o -= 0x30
            if o not in _GLAG:
                return None
            t += _GLAG[o]
        return t if t > 0 else None
    except Exception:
        return None


def _best_div(n, cap=612):
    for c in range(min(cap, n), 0, -1):
        if n % c == 0:
            return c
    return 0


def _perms(xs):
    if len(xs) <= 1:
        return [list(xs)]
    out = []
    for i in range(len(xs)):
        for rest in _perms(xs[:i] + xs[i + 1:]):
            out.append([xs[i]] + rest)
    return out


def riddle_cell(nums):
    best = 0
    for p in _perms(list(nums)):
        best = max(best, _best_div(int(''.join(str(x) for x in p))))
    return best or None


def pk_listen():
    """Append the enemies' numeric says heard since my last turn to the shared stream."""
    try:
        heard = Fight.listen() or []
    except Exception:
        heard = []
    foes = set(e.id for e in Fight.getEnemies())
    for h in heard:
        try:
            who, msg = h[0], h[1]
            wid = who.id if hasattr(who, 'id') else int(who)
        except Exception:
            continue
        if wid not in foes or not isinstance(msg, str):
            continue
        v = glag_num(msg.strip())
        if v:
            PK_STREAM.append(v)


def resurrection_due():
    """The next mob to act will resurrect: it carries awakening off cooldown and an enemy lies dead.
    Blocking on any other turn wasted the teleports (188 useless blocks vs 80 missed resurrections)."""
    try:
        nxt = Fight.getNextPlayer()
    except Exception:
        return True
    if nxt is None:
        return False
    foes = set(e.id for e in Fight.getEnemies())
    if nxt.id not in foes:
        return False
    try:
        dead = [e for e in Fight.getDeadEnemies() if not e.summoned]
    except Exception:
        dead = []
    if not dead:
        return False
    awk = next((c for c in (nxt.chips or []) if c.name == 'awakening'), None)
    if awk is None:
        return False
    try:
        return (awk.currentCooldownOf(nxt) or 0) == 0
    except Exception:
        return True


def pk_block():
    """Block the predicted resurrection cell: a summon on it if one reaches, else my own body - only
    when the next mob to act is about to resurrect."""
    if len(PK_STREAM) < 1 or not resurrection_due():
        return False
    c = riddle_cell(PK_STREAM[-3:])
    if c is None:
        return False
    cell = Cell.get(c) if hasattr(Cell, 'get') else None
    if cell is None or cell.obstacle:
        return False
    if not cell.empty:
        bnote('rez cell %d already blocked' % c)
        return False
    m = me()
    # 1) a summon on it: Prototaxite reaches 10, a puny bulb 3
    for n in ('prototaxite', 'puny_bulb', 'corn'):
        if not ready(n) or (m.tp or 0) < ccost(n):
            continue
        try:
            if m.canUseChipOnCell(my_chips()[n], cell) and ok(m.summon(my_chips()[n], cell, bulb_ai if n == 'puny_bulb' else plant_ai)):
                bnote('BLOCK rez cell %d with %s' % (c, n))
                return True
        except Exception:
            pass
    # 2) my own body: walk, else jump (3, no LoS), else teleport (12, no LoS)
    rc = reachable(m.cell.id, m.mp or 0)
    if c in rc:
        m.moveToward(cell)
        if m.cell.id == c:
            bnote('BLOCK rez cell %d by walking onto it' % c)
            return True
    mates = [a.cell.id for a in Fight.getAliveAllies() if not a.summoned and a.cell is not None and a.id != m.id]
    for n in ('jump', 'teleportation'):
        if not ready(n) or (m.tp or 0) < ccost(n):
            continue
        if n == 'teleportation' and not any(dist(c, x) <= 5 for x in mates):
            continue                # a lone teleport into the army cost the leek (v7)
        try:
            if m.canUseChipOnCell(my_chips()[n], cell) and ok(m.useChipOnCell(my_chips()[n], cell)) and m.cell.id == c:
                bnote('BLOCK rez cell %d with %s' % (c, n))
                return True
        except Exception:
            pass
    # 3) Jace's way: boots for MP, walk as close as possible, summon a bulb next to the cell - the bulb
    #    plays right after me (before the mob) and walks onto it (its own 6-8 MP)
    bulbs = [n for n in ('wizard_bulb', 'savant_bulb', 'lightning_bulb', 'puny_bulb', 'tactician_bulb') if ready(n)]
    if not bulbs:
        return False
    for n in ('seven_league_boots', 'leather_boots'):
        if dist(m.cell.id, c) > 4 and ready(n) and (m.tp or 0) >= ccost(n) + min(ccost(b) for b in bulbs):
            cast_self(n)
    rc = reachable(m.cell.id, m.mp or 0)
    near = min(rc, key=lambda x: (dist(x, c), rc[x])) if rc else m.cell.id
    if near != m.cell.id:
        m.moveToward(Cell.get(near))
    for n in bulbs:
        if (m.tp or 0) < ccost(n):
            continue
        chip = my_chips()[n]
        x, y = cxy(c); best = None; bd = 99
        for dx in range(-3, 4):
            for dy in range(-3 + abs(dx), 4 - abs(dx)):
                cc = cell_at(x + dx, y + dy)
                if cc is None or cc.obstacle or not cc.empty:
                    continue
                d = dist(cc.id, c)
                if d < bd:
                    try:
                        if not m.canUseChipOnCell(chip, cc):
                            continue
                    except Exception:
                        continue
                    bd, best = d, cc
        if best is None:
            continue
        PK_TARGET['cell'] = c if best.id != c else None
        if ok(m.summon(chip, best, bulb_ai)):
            bnote('BLOCK rez cell %d: %s at %d (d=%d), walks the rest' % (c, n, best.id, bd))
            return True
        PK_TARGET['cell'] = None
    bnote('rez cell %d out of reach (d=%d)' % (c, dist(m.cell.id, c)))
    return False


def pk_defend():
    """Every enemy invincible: shields on myself, rampart / carapace on the ally the pumpkin is closest
    to, heals, then out of the army's reach with the MP left."""
    m = me()
    cleanse()
    life = m.life or 0; tot = m.maxLife or 1
    if life < tot * 0.5 and not BOSS['regen'] and cast_self('regeneration'):
        BOSS['regen'] = True
    if tot - life > 250:
        cast_self('remission')
    for n in PK_SHIELDS:
        cast_self(n)
    place_wall()
    place_decoy()
    pk_provoke()
    pk = next((e for e in Fight.getAliveEnemies() if ename(e) == 'evil_pumpkin' and e.cell is not None), None)
    mates = [a for a in Fight.getAliveAllies() if not a.summoned and a.cell is not None and a.id != m.id]
    if pk is not None and mates:
        mates.sort(key=lambda a: dist(a.cell.id, pk.cell.id))
        for n in ('rampart', 'carapace'):
            for a in mates:
                if cast_on(n, a):
                    break
    a2 = army()
    if a2 and (m.mp or 0) > 0:
        m.moveAwayFromEntities(a2)


def pumpkin_turn():
    """Returns the focus enemy when V10's search should play (a vulnerable enemy exists), else None
    (the turn was played here)."""
    if Fight.turn == 1:
        bnote('pumpkin v8')
    pk_listen()
    # v7 blocked first and died by T8 (median): the core shields go up first when the army is near
    if any(dist(me().cell.id, e.cell.id) <= 10 for e in army()):
        for n in ('solidification', 'fortress', 'wall'):
            cast_self(n)
    pk_block()
    if disarm(('evil_pumpkin',)):
        pass
    place_wall()
    vul = pk_vulnerable()
    if not vul:
        pk_defend()
        return None
    return 'search'
