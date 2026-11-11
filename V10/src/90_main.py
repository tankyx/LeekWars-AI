# ---- 90_main: turn loop -----------------------------------------------------
def invincible(e):
    try:
        return any(f.type == E_ADD_STATE and int(f.value or 0) == ST_INVINCIBLE for f in (e.effects or []))
    except Exception:
        return False


def main_enemy():
    best = None; bd = 9999
    foes = [e for e in Fight.getAliveEnemies() if not e.summoned]
    vul = [e for e in foes if not invincible(e)]
    for e in (vul or foes):
        if e.summoned:
            continue
        d = me().distance(e)
        if d is not None and d < bd:
            best, bd = e, d
    return best


def focus_enemy():
    """Team focus target (farmer / team fights): every one of our leeks picks the same enemy so the
    damage lands on one leek at a time. Score = effective HP (life + absolute shield, relative shield
    applied) / (1 + 0.5 x our leeks that reach it this turn) / (1 + its STR+MAG / 1000); lowest wins,
    ties by id. A leek that cannot reach the focus this turn keeps its nearest enemy. Solo fights
    (one leek on our side) are unchanged."""
    mine = [a for a in Fight.getAliveAllies() if not a.summoned and a.cell is not None]
    foes = [e for e in Fight.getAliveEnemies() if not e.summoned and e.cell is not None and (e.life or 0) > 0]
    vul = [e for e in foes if not invincible(e)]     # boss phases: an invincible enemy is never the focus
    if vul:
        foes = vul
    if len(mine) <= 1 or len(foes) <= 1:
        return main_enemy()
    best = None; bs = None
    for e in foes:
        eff = (e.life or 0) + (e.absoluteShield or 0)
        rel = min(max(e.relativeShield or 0, 0), 80)
        eff = eff / max(0.2, 1.0 - rel / 100.0)
        reach = sum(1 for a in mine if dist(a.cell.id, e.cell.id) <= (a.maxMP or 6) + 10)
        dmg = (e.strength or 0) + (e.magic or 0)
        sc = eff / (1.0 + 0.5 * reach) / (1.0 + dmg / 1000.0)
        if best is None or bs is None or sc < bs - 1e-9 or (abs(sc - bs) <= 1e-9 and e.id < best.id):
            bs, best = sc, e
    m = me()
    if best is not None and dist(m.cell.id, best.cell.id) <= (m.maxMP or 6) + 12:
        return best
    return main_enemy()


def alive(e):
    return e is not None and e.cell is not None and (e.life or 0) > 0


def return_kills(it, tgt_ent):
    """Live guard: would this attack's WORST-case damage return (max roll, crit) kill us?
    Engine: return = raw damage before the target's shields x its damage return %."""
    try:
        ret = (tgt_ent.damageReturn or 0) if tgt_ent is not None else 0
    except Exception:
        ret = 0
    if ret <= 0:
        return False
    m = me()
    raw = 0.0
    for e in it.effects:
        if e[0] == E_DAMAGE and not ((e[5] or 0) & 4):
            raw += (e[2] or e[1] or 0) * (1 + max(0, m.strength or 0) / 100.0) * (1 + (m.power or 0) / 100.0) * 1.3
    return raw * ret / 100.0 >= (m.life or 0)


def execute(plan, enemy=None):
    """Run the plan; returns a compact trace of engine return codes
    (1 success, 2 critical, 0 failed, negatives = invalid). An attack is skipped
    ('x') when the enemy standing on its target cell at plan start has died, or
    when the planned enemy is dead and no living enemy stands on the cell."""
    m = me(); trace = []
    on_cell = {x.cell.id: x for x in Fight.getAliveEnemies() if x.cell is not None}
    for st in plan:
        if st[0] == 'move':
            r = m.moveToward(Cell.get(st[1]))
            trace.append('M%s' % r)
        else:
            it, tgt = st[1], st[2]
            if it.offensive and return_kills(it, on_cell.get(tgt)):
                trace.append('%s:R' % it.name[:6])      # skipped: the return would kill us
                continue
            if it.offensive:
                f = on_cell.get(tgt)
                if (f is not None and not alive(f)) or (f is None and enemy is not None and not alive(enemy)):
                    trace.append('%s:x' % it.name[:6])
                    continue
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
    if not alive(enemy):
        return 'enemy dead'
    _GEO.clear(); _GEO_E.clear()       # we moved: LoS between cells may have changed
    # the main enemy first, then its summons (nearest first)
    targets = [enemy] + sorted([x for x in Fight.getAliveEnemies() if x.summoned and x.cell is not None],
                               key=lambda x: me().distance(x) or 99)
    attacks = sorted([i for i in items if i.offensive and not i.special and not i.is_si], key=lambda i: -i.cost)
    for tgt_ent in targets:
        if not alive(tgt_ent):
            continue
        ecell = tgt_ent.cell.id
        for _ in range(12):
            if not alive(tgt_ent):
                break
            done = False
            for it in attacks:
                if it.cost > m.tp:
                    continue
                # range / launch line / LoS / self-hit first: a weapon switch costs 1 TP
                if not usable_from(m.cell.id, ecell, [it]):
                    continue
                if used is not None and used.get(it.id, 0) >= it.max_uses:
                    continue
                if return_kills(it, tgt_ent):
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
                elif it.cooldown_now() == 0 and m.canUseChip(it.obj, tgt_ent):   # live: the plan cast chips
                    r = m.useChip(it.obj, tgt_ent)
                    if r is not None and r > 0:
                        trace.append('+%s:%s' % (it.name[:6], r)); done = True
                        break
            if not done:
                break
    for it in [i for i in items if i.self_cast and not i.special]:
        if A is not None and not useful_now(it, A, B, cx, leftover=True, cell=m.cell.id):
            continue
        if it.cost <= m.tp and it.cooldown_now() == 0:
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
            if not alive(enemy):
                break
            r = m.useWeapon(enemy)
            if r is None or r <= 0:
                break
    except Exception as ex:
        log('V10 fallback error ' + type(ex).__name__ + ': ' + str(ex)[:200])


LAST_LIVES = (-1, -1)      # (our life, enemy life) at our previous turn; -1 = none yet
LAMA = [False]             # lama() once per fight, with leftover TP only (cosmetic, 1 TP)


def turn():
    global LAST_LIVES
    boss = boss_on()
    if not boss and pumpkin_on():
        try:
            r = pumpkin_turn()
        except Exception as ex:
            log('PUMPKIN error ' + str(ex)[:200]); r = 'search'
        boss_flush()
        if r is None:
            return
    if boss:
        # Fennel boss: every role is played by 80_boss (boss_turn returns None); if it raises, the combat
        # phase falls back to the boss focus and the normal search below
        try:
            enemy = boss_turn()
        except Exception as ex:
            log('BOSS error ' + type(ex).__name__ + ': ' + str(ex)[:300])
            enemy = None
            try:
                if BOSS['combat']:
                    enemy = boss_focus()
            except Exception:
                enemy = None
        boss_flush()
    else:
        enemy = focus_enemy()
    if enemy is None:
        return
    try:
        refresh_budget()
        for c in (_ctx_cache, _GEO, _GEO_E, _PL, _SPL, _PACKS, _LEAVES, _NETS, _RK):
            c.clear()
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
        others = [snapshot(x, theirs) for x in theirs if not x.summoned and x.id != enemy.id and alive(x)
                  and (not boss or is_army(x))]        # boss: graal / crystals / chests do not attack
        best, n = choose_plan(A, B, A['cell'], m.tp, m.mp, w.id if w is not None else -1, A['items'], bulbs, others)
        v, plan, info = best
        if plan is None:
            fallback(enemy)
            return
        desc = ' '.join((s[0] == 'move' and 'M%d' % s[1]) or s[1].name for s in plan)
        if len([a for a in mine if not a.summoned]) > 1:
            log('V10F T%d focus %s (%d)' % (Fight.turn, enemy.name, enemy.life or 0))
        if others and LAST_CX is not None and plan:
            end = next((s[1] for s in reversed(plan) if s[0] == 'move'), A['cell'])
            log('V10D T%d others %d threat here %.0f at end %.0f' % (
                Fight.turn, len(others), others_threat(LAST_CX, A, A['cell']), others_threat(LAST_CX, A, end)))
        log('V10 T%d V=%.3f plans=%d ops=%d dealt=%.0f end_d=%s los=%s reply=%.0f | %s' % (
            Fight.turn, v, n, ops(), info[0], info[1], info[2], info[3] if len(info) > 3 else -1, desc))
        cxl = LAST_CX
        if REPLY_LOG and cxl is not None:
            try:
                rr = run_plan(plan, A, B, A['cell'], m.tp, m.mp, w.id if w is not None else -1)
                if rr is not None and rr[1]['life'] > 0:
                    a2, b2, ec2 = enemy_reply(cxl, rr[0], rr[1], rr[2])
                    g = cxl.dbg
                    log('V10R T%d end %d them %d tp %d mp %d opts %d cells %d -> from %d f %.2f [%s] dmg %.0f amp %s ret %d over %s' % (
                        Fight.turn, rr[2], B['cell'], g[0], g[1], g[2], len(cxl.enemy_cells(g[1])), g[3], g[4], g[5],
                        rr[0]['life'] - a2['life'], g[6], g[7], over()))
            except Exception as ex:
                log('V10R error ' + str(ex)[:200])
        if cxl is not None:
            log('V10H T%d their heal capacity next turn %.0f' % (Fight.turn, cxl.b_heal_next))
        if cxl is not None and info and info[0] <= 0:
            log('V10A T%d no damage chosen; attacking plans evaluated=%d best=%.3f dealt=%.0f | %s' % (
                Fight.turn, cxl.n_atk, cxl.best_atk[0], cxl.best_atk[1], cxl.best_atk[2]))
        tr = execute(plan, enemy)
        tgt = enemy
        if not alive(tgt):
            # focus died during the plan: spend what is left on the next one
            tgt = focus_enemy()
            if tgt is not None and alive(tgt):
                tr += ' | retarget %s' % tgt.name
        tr += ' | left: ' + (spend_leftover(tgt, A['items'], A, B, LAST_CX, plan_uses(plan))
                             if tgt is not None else 'no enemy')
        if not LAMA[0] and (m.tp or 0) >= 1:
            try:
                m.lama(); LAMA[0] = True; tr += ' | lama'
            except Exception:
                LAMA[0] = True          # not available here: never retry
        log('V10X T%d %s | cell %s tp %s mp %s' % (Fight.turn, tr, m.cell.id, m.tp, m.mp))
    except Exception as ex:
        log('V10 error ' + type(ex).__name__ + ': ' + str(ex)[:300])
        fallback(enemy)
