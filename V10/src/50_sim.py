# ---- 50_sim: geometry + applying a plan to a state copy -------------------
_XY = {}
_GEO = {}      # (from, to) -> (dist, los, line, diag); cleared every turn (LoS depends on entities)


def cxy(c):
    xy = _XY.get(c)
    if xy is None:
        cell = Cell.get(c)
        xy = (cell.x, cell.y)
        _XY[c] = xy
    return xy


def dist(a, b):
    """Cell distance = Manhattan distance on the cell coordinates (checked
    against Field.cellDistance on 4144 pairs)."""
    ax, ay = cxy(a); bx, by = cxy(b)
    return abs(ax - bx) + abs(ay - by)


def geo(a, b):
    g = _GEO.get((a, b))
    if g is None:
        ax, ay = cxy(a); bx, by = cxy(b)
        dx, dy = abs(ax - bx), abs(ay - by)
        g = (dx + dy, a == b or bool(Field.lineOfSight(a, b)), dx == 0 or dy == 0, dx == dy)
        _GEO[(a, b)] = g
    return g


def launch_geo(lt, line, diag):
    if lt == 7:
        return True
    if lt == 1:
        return line
    if lt == 2:
        return diag
    if lt == 3:
        return line or diag
    if lt == 4:
        return not (line or diag)
    if lt == 5:
        return not diag
    if lt == 6:
        return not line
    return True


def launch_ok(it, a, b):
    if it.launch == 7:
        return True
    g = geo(a, b)
    return launch_geo(it.launch, g[2], g[3])


def reachable(start, mp):
    """BFS over walkable empty cells: {cell: steps} within mp steps."""
    seen = {start: 0}
    frontier = [start]
    for step in range(1, mp + 1):
        nxt = []
        for c in frontier:
            x, y = cxy(c)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = Field.cellFromXY(x + dx, y + dy)
                if n is None:
                    continue
                nid = n.id
                if nid in seen or n.obstacle or not n.empty:
                    continue
                seen[nid] = step
                nxt.append(nid)
        frontier = nxt
        if not frontier:
            break
    return seen


def can_use(it, frm, tgt, sim):
    """Range / launch / LoS / TP / uses / cooldown check for using `it` from
    cell `frm` on cell `tgt` in sim state `sim`."""
    cost = it.cost + (1 if it.weapon and sim['weapon'] != it.id else 0)
    if cost > sim['tp']:
        return False
    if sim['uses'].get(it.id, 0) >= it.max_uses:
        return False
    if not it.weapon and (it.current_cooldown() > 0 or (it.cooldown > 0 and sim['uses'].get(it.id, 0) > 0)):
        return False
    d, los, line, diag = geo(frm, tgt)
    if d is None or d < it.minr or d > it.maxr:
        return False
    if frm != tgt and not launch_geo(it.launch, line, diag):
        return False
    if it.los and not los:
        return False
    return True


def in_area(area, t, c):
    """Power factor of cell `c` in the area of an item aimed at `t` (engine:
    1 - 0.2 x distance to the aimed cell), 0 when `c` is outside the area.
    Laser lines and special areas count as single-cell here."""
    tx, ty = cxy(t); qx, qy = cxy(c)
    dx = abs(tx - qx); dy = abs(ty - qy); m = dx + dy
    if area in (3, 4, 5):
        ok = m <= area - 2
    elif area in (6, 7):
        ok = (dx == 0 or dy == 0) and m <= area - 4
    elif area in (8, 9, 10):
        ok = dx == dy and dx <= area - 7
    elif area in (11, 12):
        ok = max(dx, dy) <= area - 10
    else:
        ok = m == 0
    return max(0.0, 1.0 - 0.2 * m) if ok else 0.0


_AIMS = {}     # cell -> [(aim cell, distance)] within 2 cells, walls excluded (static per fight)


def aim_cells(c):
    """Cells an area item could be aimed at to catch `c` (distance 1-3 - circle 3
    / plus 3 / X 3 areas reach 3 cells -, nearest first, obstacles excluded)."""
    r = _AIMS.get(c)
    if r is None:
        x, y = cxy(c); r = []
        for dx in (-3, -2, -1, 0, 1, 2, 3):
            for dy in (-3, -2, -1, 0, 1, 2, 3):
                m = abs(dx) + abs(dy)
                if m == 0 or m > 3:
                    continue
                n = Field.cellFromXY(x + dx, y + dy)
                if n is None or n.obstacle:
                    continue
                _XY[n.id] = (x + dx, y + dy)
                r.append((n.id, m))
        r.sort(key=lambda p: p[1])
        _AIMS[c] = r
    return r


def splash_pack(frm, target, items, tp, weapon, vals, key, tag):
    """Best area attack on `target` aimed at a nearby cell from `frm` (used when
    no direct shot exists): (aim cell, factor, items) or None."""
    for t, m in aim_cells(target):
        its = [it for it in items if in_area(it.area, t, target) > 0]
        if not its or dist(frm, t) > max(it.maxr for it in its):
            continue
        att = pack(frm, t, its, tp, weapon, vals, key, tag=(tag, tuple(i.id for i in its)))
        if att:
            return t, in_area(att[0].area, t, target), att
    return None


def has_area(it):
    return it.area in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12)


def self_hit(it, frm, tgt):
    r = AREA_RADIUS.get(it.area, 0)
    return r > 0 and has_area(it) and in_area(it.area, tgt, frm) > 0


BULB_W = 0.5    # damage to a summon counts half as "damage dealt" (a kill also lowers their summon count)


def run_plan(plan, A0, B0, cell0, tp0, mp0, weapon0, bulbs=None):
    """Apply plan steps to copies. Returns (A, B, end_cell, dealt) or None if
    any step is illegal."""
    A = copy_side(A0); B = copy_side(B0)
    sim = {'tp': tp0, 'mp': mp0, 'weapon': weapon0, 'uses': {}}
    cell = cell0; dealt = 0.0; hit = {}
    for st in plan:
        if st[0] == 'move':
            if st[1] == cell:
                continue
            pl = Field.pathLength(cell, st[1])
            if pl is None or pl < 0 or pl > sim['mp']:
                return None
            sim['mp'] -= pl; cell = st[1]
        else:
            it, tgt = st[1], st[2]
            if not can_use(it, cell, tgt, sim):
                return None
            if it.weapon and sim['weapon'] != it.id:
                sim['tp'] -= 1; sim['weapon'] = it.id
            sim['tp'] -= it.cost
            sim['uses'][it.id] = sim['uses'].get(it.id, 0) + 1
            if tgt == B['cell'] and it.offensive:
                if B['life'] <= 0:
                    continue               # enemy already dead: execution skips the shot
                if self_hit(it, cell, tgt) and any(e[0] in (E_DAMAGE, E_POISON) for e in it.effects):
                    return None
                dealt += apply_item(it, A, B, sim)
                if A['life'] <= 0 and B['life'] > 0:
                    return None            # damage return would kill us on our own turn
            elif bulbs and tgt in bulbs and it.offensive:
                if self_hit(it, cell, tgt) and any(e[0] in (E_DAMAGE, E_POISON) for e in it.effects):
                    return None
                bs = hit.get(tgt)
                if bs is None:
                    bs = copy_side(bulbs[tgt]); hit[tgt] = bs
                if bs['life'] <= 0:
                    return None            # already dead: the shot would be wasted
                before = bs['life']
                apply_item(it, A, bs, sim)
                dealt += BULB_W * (before - bs['life'])
                if bs['life'] <= 0:
                    B['summons'] = max(0, B['summons'] - 1)
            elif it.offensive and has_area(it):
                # aimed next to the enemy: the area catches it at reduced power
                f = in_area(it.area, tgt, B['cell'])
                if f <= 0:
                    return None
                if self_hit(it, cell, tgt) and any(e[0] in (E_DAMAGE, E_POISON) for e in it.effects):
                    return None
                dealt += apply_item(it, A, B, sim, f)
                if A['life'] <= 0 and B['life'] > 0:
                    return None
            else:
                apply_item(it, A, A, sim)
    A['cell'] = cell
    return A, B, cell, dealt, sim
