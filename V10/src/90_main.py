# ---- 90_main: turn loop -----------------------------------------------------
def main_enemy():
    best = None; bd = 9999
    for e in Fight.getAliveEnemies():
        if e.summoned:
            continue
        d = me().distance(e)
        if d is not None and d < bd:
            best, bd = e, d
    return best


ALLY_SUPPORT = False   # step 2 / 2b: neutral in A/B (13 vs 14, 12 vs 14 of 20) - kept off
MAG_FOCUS_W = 1.0      # 1.5 tested neutral


def focus_enemy():
    """Team focus target (farmer / team fights): every one of our leeks picks the same enemy so the
    damage lands on one leek at a time. Score = effective HP (life + absolute shield, relative shield
    applied) / (1 + 0.5 x our leeks that reach it this turn) / (1 + its STR+MAG / 1000); lowest wins,
    ties by id. A leek that cannot reach the focus this turn keeps its nearest enemy. Solo fights
    (one leek on our side) are unchanged."""
    mine = [a for a in Fight.getAliveAllies() if not a.summoned and a.cell is not None]
    foes = [e for e in Fight.getAliveEnemies() if not e.summoned and e.cell is not None and (e.life or 0) > 0]
    if len(mine) <= 1 or len(foes) <= 1:
        return main_enemy()
    best = None; bs = None
    for e in foes:
        eff = (e.life or 0) + (e.absoluteShield or 0)
        rel = min(max(e.relativeShield or 0, 0), 80)
        eff = eff / max(0.2, 1.0 - rel / 100.0)
        reach = sum(1 for a in mine if dist(a.cell.id, e.cell.id) <= (a.maxMP or 6) + 10)
        # poison ignores our shields: losses had 1.4 magic leeks per fight vs 0.5 in wins
        dmg = (e.strength or 0) + MAG_FOCUS_W * (e.magic or 0)
        sc = eff / (1.0 + 0.5 * reach) / (1.0 + dmg / 1000.0)
        if bs is None or sc < bs - 1e-9 or (abs(sc - bs) <= 1e-9 and e.id < best.id):
            bs, best = sc, e
    m = me()
    if best is not None and dist(m.cell.id, best.cell.id) <= (m.maxMP or 6) + 12:
        return best
    near = main_enemy()
    if near is not None and near.cell is not None and dist(m.cell.id, near.cell.id) <= (m.maxMP or 6) + 12:
        return near
    return best          # nobody in reach yet: everyone walks toward the same enemy


def _poison_of(ent):
    p = 0
    for e in (ent.effects or []):
        if e.type == E_POISON:
            p += e.value or 0
    return p


def _ally_castable(it):
    """Chip whose effects may target allies (targets bit 2), never offensive or a move."""
    if it.weapon or it.offensive or it.special:
        return False
    return any((e[4] or 0) & 2 for e in it.effects)


def ally_support(items):
    """Team layer step 2: before planning its own turn, the leek spends up to a third of its TP
    on an ally who needs it more: antidote on the most poisoned (>= 200/turn), a heal on the most
    hurt (< 50%), a shield on the most endangered (< 70% with enemies near). Multi-leek fights only."""
    m = me()
    allies = [a for a in Fight.getAliveAllies() if not a.summoned and a.id != m.id and a.cell is not None and (a.life or 0) > 0]
    if not allies:
        return ''
    budget = max(0, (m.tp or 0) // 3)
    if budget <= 0:
        return ''
    foes = [e for e in Fight.getAliveEnemies() if not e.summoned and e.cell is not None]
    trace = []

    def frac(a):
        return (a.life or 0) / float(max(1, a.maxLife or 1))

    def near(a):
        return sum(1 for e in foes if dist(a.cell.id, e.cell.id) <= 8)

    def cast(kind, target):
        nonlocal budget
        for it in sorted([i for i in items if _ally_castable(i)], key=lambda i: i.cost):
            types = {e[0] for e in it.effects}
            if kind == 'antidote' and E_ANTIDOTE not in types:
                continue
            if kind == 'heal' and E_HEAL not in types:
                continue
            if kind == 'shield' and not (types & {E_ABS_SHIELD, E_REL_SHIELD, E_RAW_ABS, E_RAW_REL}):
                continue
            if it.cost > budget or it.cost > (m.tp or 0) or it.current_cooldown() != 0:
                continue
            try:
                if not m.canUseChip(it.obj, target):
                    continue
                r = m.useChip(it.obj, target)
            except Exception:
                continue
            if r is not None and r > 0:
                budget -= it.cost
                trace.append('%s>%s' % (it.name[:6], target.name[:5]))
                return True
        return False

    # step 2b: only serious poison on an ally (>= 300/turn or >= 15% of its current life); routine
    # heals / shields cost shots and did not win more fights (13/20 vs 14/20)
    pois = sorted(allies, key=lambda a: -_poison_of(a))
    if pois:
        p0 = _poison_of(pois[0])
        if (p0 >= 300 or p0 >= 0.15 * (pois[0].life or 1)) and p0 > _poison_of(m):
            cast('antidote', pois[0])
    return ' '.join(trace)


def execute(plan):
    """Run the plan; returns a compact trace of engine return codes
    (1 success, 2 critical, 0 failed, negatives = invalid)."""
    m = me(); trace = []
    for st in plan:
        if st[0] == 'move':
            r = m.moveToward(Cell.get(st[1]))
            trace.append('M%s' % r)
        else:
            it, tgt = st[1], st[2]
            if it.weapon:
                w = m.weapon
                if w is None or w.id != it.id:
                    m.setWeapon(it.obj)
                r = m.useWeaponOnCell(tgt)
            else:
                r = m.useChipOnCell(it.obj, tgt)
            trace.append('%s:%s' % (it.name[:6], r))
    return ' '.join(trace)


def plan_uses(plan):
    used = {}
    for st in plan:
        if st[0] == 'use':
            used[st[1].id] = used.get(st[1].id, 0) + 1
    return used


def spend_leftover(enemy, items, A=None, B=None, cx=None, used=None):
    """Leftover TP after the plan: attacks the engine says are legal from the
    final cell, then ready self chips. Returns a compact trace."""
    m = me(); trace = []
    if enemy.cell is None or (enemy.life or 0) <= 0:
        return 'enemy dead'
    _GEO.clear()                       # we moved: LoS between cells may have changed
    # the main enemy first, then its summons (nearest first)
    targets = [enemy] + sorted([x for x in Fight.getAliveEnemies() if x.summoned and x.cell is not None],
                               key=lambda x: me().distance(x) or 99)
    for tgt_ent in targets:
        ecell = tgt_ent.cell.id
        for _ in range(12):
            done = False
            for it in sorted([i for i in items if i.offensive and not i.special], key=lambda i: -i.cost):
                if it.cost > m.tp:
                    continue
                # range / launch line / LoS / self-hit first: a weapon switch costs 1 TP
                if not usable_from(m.cell.id, ecell, [it]):
                    continue
                if used is not None and used.get(it.id, 0) >= it.max_uses:
                    continue
                if it.weapon:
                    if (m.weapon is None or m.weapon.id != it.id):
                        if it.cost + 1 > m.tp:
                            continue
                        m.setWeapon(it.obj)
                    if m.canUseWeapon(tgt_ent):
                        r = m.useWeapon(tgt_ent)
                        if used is not None:
                            used[it.id] = used.get(it.id, 0) + 1
                        if r is not None and r > 0:
                            trace.append('+%s:%s' % (it.name[:6], r)); done = True
                            break
                elif it.current_cooldown() == 0 and m.canUseChip(it.obj, tgt_ent):
                    r = m.useChip(it.obj, tgt_ent)
                    if r is not None and r > 0:
                        trace.append('+%s:%s' % (it.name[:6], r)); done = True
                        break
            if not done:
                break
    for it in [i for i in items if i.self_cast and not i.special]:
        if A is not None and not useful_now(it, A, B, cx):
            continue
        if it.cost <= m.tp and it.current_cooldown() == 0:
            r = m.useChipOnCell(it.obj, m.cell.id) if not it.weapon else None
            if r is not None and r > 0:
                trace.append('+%s:%s' % (it.name[:6], r))
    return ' '.join(trace)


def fallback(enemy):
    m = me()
    try:
        m.moveToward(enemy)
        ws = m.weapons or []
        if ws and (m.weapon is None or m.weapon.id != ws[0].id):
            m.setWeapon(ws[0])
        for _ in range(4):
            r = m.useWeapon(enemy)
            if r is None or r <= 0:
                break
    except Exception as ex:
        log('V10 fallback error ' + type(ex).__name__ + ': ' + str(ex)[:200])


LAST_LIVES = (-1, -1)      # (our life, enemy life) at our previous turn; -1 = none yet


def turn():
    global LAST_LIVES
    enemy = focus_enemy()
    if enemy is None:
        return
    try:
        refresh_budget()
        _ctx_cache.clear(); _GEO.clear(); _PACKS.clear(); _LEAVES.clear(); _NETS.clear()
        m = me()
        mine = [x for x in Fight.getAliveAllies()]
        theirs = [x for x in Fight.getAliveEnemies()]
        track_burn(m); track_burn(enemy)
        # standoff tracker: turns in a row where neither we nor the enemy lost HP
        lives = (m.life, enemy.life)
        if LAST_LIVES[0] >= 0 and lives[0] >= LAST_LIVES[0] and lives[1] >= LAST_LIVES[1]:
            IDLE[0] += 1
        else:
            IDLE[0] = 0
        LAST_LIVES = lives
        sup = ally_support(items_of(m)) if ALLY_SUPPORT and len([a for a in mine if not a.summoned]) > 1 else ''
        # formation: cells of our other living leeks, for the cohesion term in choose_plan
        TEAM_CELLS[:] = [a.cell.id for a in mine if not a.summoned and a.id != m.id and a.cell is not None]
        if sup:
            log('V10S T%d ally support: %s' % (Fight.turn, sup))
        A = snapshot(m, mine)
        B = snapshot(enemy, theirs)
        w = m.weapon
        bulbs = [bulb_side(x) for x in theirs if x.summoned and (x.life or 0) > 0 and x.cell is not None]
        best, n = choose_plan(A, B, A['cell'], m.tp, m.mp, w.id if w is not None else -1, A['items'], bulbs)
        v, plan, info = best
        if plan is None:
            fallback(enemy)
            return
        desc = ' '.join((s[0] == 'move' and 'M%d' % s[1]) or s[1].name for s in plan)
        if len([a for a in mine if not a.summoned]) > 1:
            log('V10F T%d focus %s (%d)' % (Fight.turn, enemy.name, enemy.life or 0))
        log('V10 T%d V=%.3f plans=%d ops=%d dealt=%.0f end_d=%s los=%s reply=%.0f | %s' % (
            Fight.turn, v, n, ops(), info[0], info[1], info[2], info[3] if len(info) > 3 else -1, desc))
        cxl = LAST_CX
        if cxl is not None:
            log('V10H T%d their heal capacity next turn %.0f' % (Fight.turn, cxl.b_heal_next))
        if cxl is not None and info and info[0] <= 0:
            log('V10A T%d no damage chosen; attacking plans evaluated=%d best=%.3f dealt=%.0f | %s' % (
                Fight.turn, cxl.n_atk, cxl.best_atk[0], cxl.best_atk[1], cxl.best_atk[2]))
        tr = execute(plan)
        tr += ' | left: ' + spend_leftover(enemy, A['items'], A, B, LAST_CX, plan_uses(plan))
        log('V10X T%d %s | cell %s tp %s mp %s' % (Fight.turn, tr, m.cell.id, m.tp, m.mp))
    except Exception as ex:
        log('V10 error ' + type(ex).__name__ + ': ' + str(ex)[:300])
        fallback(enemy)
