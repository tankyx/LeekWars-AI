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
    enemy = main_enemy()
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
        log('V10 T%d V=%.3f plans=%d ops=%d dealt=%.0f end_d=%s los=%s reply=%.0f | %s' % (
            Fight.turn, v, n, ops(), info[0], info[1], info[2], info[3] if len(info) > 3 else -1, desc))
        cxl = LAST_CX
        if cxl is not None and info and info[0] <= 0:
            log('V10A T%d no damage chosen; attacking plans evaluated=%d best=%.3f dealt=%.0f | %s' % (
                Fight.turn, cxl.n_atk, cxl.best_atk[0], cxl.best_atk[1], cxl.best_atk[2]))
        tr = execute(plan)
        tr += ' | left: ' + spend_leftover(enemy, A['items'], A, B, LAST_CX, plan_uses(plan))
        log('V10X T%d %s | cell %s tp %s mp %s' % (Fight.turn, tr, m.cell.id, m.tp, m.mp))
    except Exception as ex:
        log('V10 error ' + type(ex).__name__ + ': ' + str(ex)[:300])
        fallback(enemy)
