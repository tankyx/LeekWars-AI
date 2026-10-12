# ---- 30_rules: expected effect of one item use (engine formulas) ----------
# damage = (v1 + jet v2)(1 + STR/100)(1 + power/100) x crit, minus rel% and abs
# shields, capped at life; erosion 5% (+10% on crit) of damage dealt; life
# steal = dmg x WIS/1000; nova (1 + SCI/100) capped at max - life; poison
# (1 + MAG/100); heal / vitality (1 + WIS/100); shields (1 + RES/100);
# shackles (1 + MAG/100); non-raw buffs (1 + SCI/100); crit chance AGI/1000 x1.3.
NONRAW_BUFF = {E_BUFF_STR: 'strength', E_BUFF_AGI: 'agility', E_BUFF_RES: 'resistance', E_BUFF_WIS: 'wisdom'}
RAW_BUFF = {E_RAW_STR: 'strength', E_RAW_MAG: 'magic', E_RAW_AGI: 'agility', E_RAW_RES: 'resistance',
            E_RAW_WIS: 'wisdom', E_RAW_SCI: 'science'}


def g_add(side, t, v):
    g = VN_GROUP_OF.get(t)
    if g is not None:
        side['groups'][g] += v


def _replaces(it, t, T, S):
    """Non-stackable effect already applied by this item on this target this
    turn: the new cast replaces it (no extra value). Only called for
    non-stackable lasting effects (Item.fx flag)."""
    key = (it.id, t, id(T))
    done = S.setdefault('applied', {})
    if key in done:
        return True
    done[key] = 1
    return False


HOSTILE = {E_DAMAGE, E_POISON, E_NOVA, E_VULN, E_VULN_ABS, E_SHK_MP, E_SHK_TP, E_SHK_STR, E_SHK_MAG, E_SHK_AGI}


def self_harm(t, a, turns, C, pw, critf):
    """A hostile effect flagged on-caster hits the caster itself (engine
    MODIFIER_ON_CASTER): damage through its own shields, vulnerability,
    poison or shackles on its own state. Never counts as damage dealt."""
    cur = C['cur']
    if t == E_DAMAGE:
        d = a * (1 + max(0, cur['strength']) / 100.0) * pw * critf
        d = max(0.0, d - d * C['rel'] / 100.0 - C['abs'])
        d = min(d, max(0, C['life']))
        C['life'] -= d; C['max'] -= d * 0.05; C['burn'] += d * 0.05
    elif t == E_VULN:
        g_add(C, t, a); C['rel'] -= a
    elif t == E_VULN_ABS:
        g_add(C, t, a); C['abs'] -= a
    elif t == E_POISON:
        p = a * (1 + max(0, cur['magic']) / 100.0) * pw
        g_add(C, t, p); C['pf'] += p * max(1, turns)
    elif t == E_NOVA:
        n = min(a * (1 + max(0, cur['science']) / 100.0) * pw, max(0, C['max'] - C['life']))
        C['max'] -= n; C['burn'] += n
    else:
        g_add(C, t, a * (1 + max(0, cur['magic']) / 100.0))


def apply_item(it, C, T, S, f=1.0):
    """Apply item `it` cast by side C on target side T (T is C for self casts).
    S = sim scalars (tp/mp) mutated for TP/MP buffs; f = area power factor on
    T (1 - 0.2 x distance to the aimed cell). Returns direct damage."""
    cur = C['cur']; pw = 1 + C['power'] / 100.0
    crit_p = min(1.0, max(0, cur['agility']) / 1000.0)
    critf = 1 + 0.3 * crit_p
    dealt = 0.0
    scaled = f != 1.0 and T is not C
    prev = 0.0                      # value of the previous effect (steal-shield copies it)
    for t, a, turns, nonstack, on_caster in it.fx:
        if on_caster and t in HOSTILE:
            self_harm(t, a, turns, C, pw, critf)
            continue
        if nonstack and _replaces(it, t, T, S):
            continue
        if scaled:
            a = a * f
        if t == E_DAMAGE and T is not C:
            raw = a * (1 + max(0, cur['strength']) / 100.0) * pw * critf
            # engine EffectDamage: return = RAW damage (before the target's shields) x return %,
            # hitting the caster's life directly (no shields), only capped at its life
            ret = T['groups'].get('dmg_return', 0)
            back = min(max(0.0, C['life']), raw * ret / 100.0) if ret > 0 else 0.0
            d = max(0.0, raw - raw * T['rel'] / 100.0 - T['abs'])
            d = min(d, max(0, T['life']))
            T['life'] -= d; dealt += d
            pa = T.get('pas')
            if pa and d > 0:
                # target passives (e.g. mysterious electrisor): % of direct damage
                # taken -> permanent raw abs shield / STR / RES
                if pa[0]:
                    v = d * pa[0] / 100.0
                    T['abs'] += v; T['groups']['abs_shield'] += v
                if pa[1] and 'strength' in T['cur']:
                    T['cur']['strength'] += d * pa[1] / 100.0
                if pa[2] and 'resistance' in T['cur']:
                    T['cur']['resistance'] += d * pa[2] / 100.0
            ero = d * (0.05 + 0.10 * crit_p)
            T['max'] -= ero; T['burn'] += ero
            steal = d * max(0, cur['wisdom']) / 1000.0
            C['life'] = min(C['max'], C['life'] + steal)
            if back > 0:
                C['life'] -= back; C['max'] -= back * 0.05; C['burn'] += back * 0.05
        elif t == E_POISON and T is not C:
            p = a * (1 + max(0, cur['magic']) / 100.0) * pw
            g_add(T, t, p); T['pf'] += p * max(1, turns)
        elif t == E_ADD_STATE and int(a) == ST_UNHEALABLE and T is not C:
            T['unheal'] = True         # their next turn: no healing at all (engine EffectHeal & co)
        elif t == E_SUPERINF and T is not C:
            # engine EffectSuperinfection: value1% (x1.3 on crit) of the sum of the target's
            # poisons' per-turn values, now, as poison damage (10% erosion); each poison then
            # loses one turn, i.e. one tick comes off the queued total. Half a tick now for a
            # full tick later: only worth it to finish a kill or to beat an antidote.
            tick = T['groups'].get('poison', 0)
            if tick > 0:
                d = min(tick * min(1.0, a / 100.0 * critf), max(0, T['life']))
                T['life'] -= d; T['pf'] = max(0.0, T['pf'] - tick)
                T['max'] -= d * 0.10; T['burn'] += d * 0.10
                dealt += d
        elif t == E_NOVA and T is not C:
            n = min(a * (1 + max(0, cur['science']) / 100.0) * pw, max(0, T['max'] - T['life']))
            T['max'] -= n; T['burn'] += n
        elif t in (E_SHK_MP, E_SHK_TP, E_SHK_STR, E_SHK_MAG, E_SHK_AGI) and T is not C:
            g_add(T, t, a * (1 + max(0, cur['magic']) / 100.0))
        elif t == E_DEBUFF and T is not C:
            # liberation: every effect on the target x (1 - value%): its shields,
            # buffs, damage return, heal over time, but also our poison / shackles
            k = max(0.0, 1.0 - a * critf / 100.0)
            T['abs'] *= k; T['rel'] *= k; T['pf'] *= k; T['power'] *= k
            g = T['groups']
            for key in g:
                g[key] *= k
            cur_t = T['cur']
            for key in cur_t:
                base = T.get(key)
                if isinstance(base, (int, float)):
                    cur_t[key] = base + (cur_t[key] - base) * k
        elif t == E_VULN and T is not C:
            g_add(T, t, a); T['rel'] -= a
        elif t == E_VULN_ABS and T is not C:
            g_add(T, t, a); T['abs'] -= a; prev = a
        elif t == E_STEAL_ABS:
            # engine EffectStealAbsoluteShield: the caster gains the previous effect's value as abs shield
            if prev > 0:
                C['abs'] += prev; C['groups']['abs_shield'] += prev
        elif t == E_HEAL:
            h = a * (1 + max(0, cur['wisdom']) / 100.0)
            if turns > 0:
                g_add(C, t, h)
            else:
                C['life'] = min(C['max'], C['life'] + h)
        elif t in (E_ABS_SHIELD, E_RAW_ABS):
            v = a * (1 + max(0, cur['resistance']) / 100.0) if t == E_ABS_SHIELD else a
            g_add(C, t, v); C['abs'] += v
        elif t in (E_REL_SHIELD, E_RAW_REL):
            v = a * (1 + max(0, cur['resistance']) / 100.0) if t == E_REL_SHIELD else a
            g_add(C, t, v); C['rel'] += v
        elif t == E_VITALITY:
            v = a * (1 + max(0, cur['wisdom']) / 100.0)
            C['max'] += v; C['life'] += v
        elif t in NONRAW_BUFF or t in (E_BUFF_TP, E_BUFF_MP):
            v = a * (1 + max(0, cur['science']) / 100.0)
            g_add(C, t, v)
            if t in NONRAW_BUFF:
                cur[NONRAW_BUFF[t]] += v
            elif t == E_BUFF_TP:
                S['tp'] += int(v)
            else:
                S['mp'] += int(v)
        elif t in RAW_BUFF or t in (E_RAW_TP, E_RAW_MP, E_RAW_POW):
            g_add(C, t, a)
            if t in RAW_BUFF:
                cur[RAW_BUFF[t]] += a
            elif t == E_RAW_TP:
                S['tp'] += int(a)
            elif t == E_RAW_MP:
                S['mp'] += int(a)
            else:
                C['power'] += a
        elif t == E_RETURN:
            g_add(C, t, a * (1 + max(0, cur['agility']) / 100.0))
    return dealt
