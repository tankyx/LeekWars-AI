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


def self_hit(it, frm, tgt):
    r = AREA_RADIUS.get(it.area, 0)
    return r > 0 and dist(frm, tgt) <= r


def run_plan(plan, A0, B0, cell0, tp0, mp0, weapon0):
    """Apply plan steps to copies. Returns (A, B, end_cell, dealt) or None if
    any step is illegal."""
    A = copy_side(A0); B = copy_side(B0)
    sim = {'tp': tp0, 'mp': mp0, 'weapon': weapon0, 'uses': {}}
    cell = cell0; dealt = 0.0
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
                if self_hit(it, cell, tgt) and any(e[0] in (E_DAMAGE, E_POISON) for e in it.effects):
                    return None
                dealt += apply_item(it, A, B, sim)
            else:
                apply_item(it, A, A, sim)
    A['cell'] = cell
    return A, B, cell, dealt, sim
