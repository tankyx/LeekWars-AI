# ---- 20_state: snapshot of a leek in the value model's terms --------------
# Stats are the unbuffed (fight-start-like) values the model was trained on:
# current - live buffs + live shackles. "cur_*" keep the live values for the
# damage formulas. burn = max HP lost to erosion / nova since first seen.
_last_max = {}
_burn = {}

BUFF_SUB = {'strength': (E_BUFF_STR, E_RAW_STR), 'magic': (E_RAW_MAG,), 'agility': (E_BUFF_AGI, E_RAW_AGI),
            'resistance': (E_BUFF_RES, E_RAW_RES), 'wisdom': (E_BUFF_WIS, E_RAW_WIS), 'science': (E_RAW_SCI,)}
SHK_ADD = {'strength': (E_SHK_STR,), 'magic': (E_SHK_MAG,), 'agility': (E_SHK_AGI,), 'wisdom': (48,)}


def track_burn(ent):
    cur = ent.maxLife
    last = _last_max.get(ent.id)
    if last is not None and cur < last:
        _burn[ent.id] = _burn.get(ent.id, 0) + (last - cur)
    _last_max[ent.id] = cur


def kit_of(items, st):
    """(max range, best direct / nova / poison per turn) over weapons and
    damage chips: value per use x min(max uses, TP // cost). Mirrors
    tools/value_dataset.kit_stats."""
    rng = 0; kd = kn = kp = 0.0
    tp = max(1, st['tp'])
    for it in items:
        if it.cost <= 0:
            continue
        uses = min(it.max_uses, tp // it.cost)
        dmg = nova = pois = 0.0
        for e in it.effects:
            if e[0] == E_DAMAGE:
                dmg += avg(e)
            elif e[0] == E_NOVA:
                nova += avg(e)
            elif e[0] == E_POISON:
                pois += avg(e) * max(1, e[3] or 1)
        dmg *= 1 + max(0, st['strength']) / 100.0
        nova *= 1 + max(0, st['science']) / 100.0
        pois *= 1 + max(0, st['magic']) / 100.0
        if dmg + nova + pois <= 0:
            continue
        rng = max(rng, it.maxr)
        kd = max(kd, dmg * uses); kn = max(kn, nova * uses); kp = max(kp, pois * uses)
    return (rng, kd, kn, kp)


PASSIVE_ABS, PASSIVE_STR, PASSIVE_RES = 34, 35, 63   # engine: % of direct damage taken -> raw abs shield / STR / RES


def passives_of(ent):
    """(abs %, str %, res %) from the entity's passive effects (the engine adds
    every carried weapon's passives, held or not)."""
    p = [0.0, 0.0, 0.0]
    try:
        for f in (ent.passiveEffects or []):
            t = f.type; v = f.minValue or 0
            if t == PASSIVE_ABS:
                p[0] += v
            elif t == PASSIVE_STR:
                p[1] += v
            elif t == PASSIVE_RES:
                p[2] += v
    except Exception:
        pass
    return tuple(p)


def snapshot(ent, team_alive):
    effs = ent.effects or []
    sums = {}
    groups = {g: 0.0 for g in VN_GROUPS}
    pf = 0.0
    for e in effs:
        t = e.type; v = e.value or 0
        sums[t] = sums.get(t, 0) + v
        g = VN_GROUP_OF.get(t)
        if g is not None:
            groups[g] += v
        if t == E_POISON:
            pf += v * min(max(1, e.turns or 1), 64)
    cur = {'strength': ent.strength, 'magic': ent.magic, 'agility': ent.agility,
           'resistance': ent.resistance, 'wisdom': ent.wisdom, 'science': ent.science}
    st = {}
    for k, v in cur.items():
        b = v - sum(sums.get(t, 0) for t in BUFF_SUB.get(k, ())) + sum(sums.get(t, 0) for t in SHK_ADD.get(k, ()))
        st[k] = b
    st['tp'] = ent.maxTP - sums.get(E_BUFF_TP, 0) - sums.get(E_RAW_TP, 0) + sums.get(E_SHK_TP, 0)
    st['mp'] = ent.maxMP - sums.get(E_BUFF_MP, 0) - sums.get(E_RAW_MP, 0) + sums.get(E_SHK_MP, 0)
    items = items_of(ent)
    # Amputated (glowing saber): no weapon can be used or re-equipped this turn, chips only
    amp = any(e.type == E_ADD_STATE and int(e.value or 0) == ST_AMPUTATED for e in effs)
    rets = [e for e in effs if e.type == E_RETURN]
    ret_short = bool(rets) and all((e.turns or 0) <= 1 for e in rets)   # reflect gone before our next turn
    if amp:
        items = [it for it in items if not it.weapon]
    summons = sum(1 for o in team_alive if o.summoned)
    return {'id': ent.id, 'cell': ent.cell.id, 'life': ent.life, 'max': ent.maxLife, 'level': ent.level,
            'tp': st['tp'], 'mp': st['mp'], 'strength': st['strength'], 'magic': st['magic'],
            'agility': st['agility'], 'resistance': st['resistance'], 'wisdom': st['wisdom'],
            'science': st['science'], 'cur': cur, 'power': ent.power or 0,
            'abs': ent.absoluteShield or 0, 'rel': ent.relativeShield or 0,
            'groups': groups, 'pf': pf, 'burn': _burn.get(ent.id, 0), 'summons': summons,
            'items': items, 'kit': kit_of(items, st), 'pas': passives_of(ent),
            'tp_live': ent.maxTP, 'mp_live': ent.maxMP,
            'weapon': (ent.weapon.id if ent.weapon is not None else -1), 'amputated': amp,
            'ret_short': ret_short}


def bulb_side(ent):
    """Light state of an enemy summon, as a target only (HP, shields, effect
    groups); its own kit is not modelled."""
    return {'id': ent.id, 'cell': ent.cell.id, 'life': ent.life or 0, 'max': ent.maxLife or 1,
            'abs': ent.absoluteShield or 0, 'rel': ent.relativeShield or 0,
            'groups': {g: 0.0 for g in VN_GROUPS}, 'cur': {}, 'pf': 0.0, 'burn': 0.0, 'power': 0, 'pas': (0.0, 0.0, 0.0)}


def copy_side(s):
    c = s.copy()
    c['groups'] = s['groups'].copy()
    c['cur'] = s['cur'].copy()
    return c
