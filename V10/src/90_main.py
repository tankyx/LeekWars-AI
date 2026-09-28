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
    m = me()
    for st in plan:
        if st[0] == 'move':
            m.moveToward(Cell(st[1]))
        else:
            it, tgt = st[1], st[2]
            if it.weapon:
                w = m.weapon
                if w is None or w.id != it.id:
                    m.setWeapon(it.obj)
                m.useWeaponOnCell(tgt)
            else:
                m.useChipOnCell(it.obj, tgt)


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


def turn():
    enemy = main_enemy()
    if enemy is None:
        return
    try:
        _ctx_cache.clear()
        m = me()
        mine = [x for x in Fight.getAliveAllies()]
        theirs = [x for x in Fight.getAliveEnemies()]
        track_burn(m); track_burn(enemy)
        A = snapshot(m, mine)
        B = snapshot(enemy, theirs)
        w = m.weapon
        best, n = choose_plan(A, B, A['cell'], m.tp, m.mp, w.id if w is not None else -1, A['items'])
        v, plan, info = best
        if plan is None:
            fallback(enemy)
            return
        desc = ' '.join((s[0] == 'move' and 'M%d' % s[1]) or s[1].name for s in plan)
        log('V10 T%d V=%.3f plans=%d ops=%d dealt=%.0f end_d=%s los=%s | %s' % (
            Fight.turn, v, n, ops(), info[0], info[1], info[2], desc))
        execute(plan)
    except Exception as ex:
        log('V10 error ' + type(ex).__name__ + ': ' + str(ex)[:300])
        fallback(enemy)
