# ---- 10_items: item rules read from the engine's own item data -----------
# Effect type ids (engine Effect.TYPE_*)
E_DAMAGE, E_HEAL, E_BUFF_STR, E_BUFF_AGI, E_REL_SHIELD, E_ABS_SHIELD = 1, 2, 3, 4, 5, 6
E_BUFF_MP, E_BUFF_TP, E_DEBUFF, E_TELEPORT, E_VITALITY, E_POISON = 7, 8, 9, 10, 12, 13
E_SUMMON, E_SHK_MP, E_SHK_TP, E_SHK_STR, E_RETURN, E_BUFF_RES, E_BUFF_WIS = 14, 17, 18, 19, 20, 21, 22
E_ANTIDOTE, E_SHK_MAG, E_VULN, E_VULN_ABS, E_NOVA = 23, 24, 26, 27, 30
E_RAW_MP, E_RAW_TP, E_RAW_ABS, E_RAW_STR, E_RAW_MAG, E_RAW_SCI, E_RAW_AGI, E_RAW_RES = 31, 32, 37, 38, 39, 40, 41, 42
E_RAW_WIS, E_ATTRACT, E_SHK_AGI, E_REMOVE_SHK, E_PUSH, E_RAW_POW, E_RAW_REL = 44, 46, 47, 49, 51, 52, 54
E_STEAL_ABS = 29   # caster gains, as absolute shield, the value of the item's previous effect (j_laser)
E_SUPERINF = 64    # superinfection: value1% of the target's per-turn poison sum now, every poison loses one turn
E_ADD_STATE, ST_UNHEALABLE = 59, 2
ST_INVINCIBLE = 3   # Divine Protection (bosses): damage, poison, nova and aftereffects do nothing (engine EffectDamage & co)   # hemorrhage: state 2 = Unhealable (no heal, life steal, vitality, regen) for 1 turn
T_ENEMY, T_ALLY, T_CASTER, T_LEEK, T_SUMMON = 1, 2, 4, 8, 16   # effect target flags (engine Effect.TARGET_*)
ST_AMPUTATED = 13   # glowing saber: the target drops its weapon and cannot use or re-equip one until the
                    # state ends (start of the caster's next turn); chips still work (engine State.useWeapon)

OFFENSIVE = {E_DAMAGE, E_POISON, E_SUPERINF, E_NOVA, E_SHK_MP, E_SHK_TP, E_SHK_STR, E_SHK_MAG, E_SHK_AGI, E_VULN, E_VULN_ABS, E_DEBUFF}
SELF_ONLY = {E_HEAL, E_BUFF_STR, E_BUFF_AGI, E_REL_SHIELD, E_ABS_SHIELD, E_BUFF_MP, E_BUFF_TP, E_VITALITY,
             E_RETURN, E_BUFF_RES, E_BUFF_WIS, E_RAW_MP, E_RAW_TP, E_RAW_ABS, E_RAW_STR, E_RAW_MAG, E_RAW_SCI,
             E_RAW_AGI, E_RAW_RES, E_RAW_WIS, E_RAW_POW, E_RAW_REL, E_ANTIDOTE, E_REMOVE_SHK}
MOVE_EFFECTS = {E_TELEPORT, E_ATTRACT, E_PUSH, E_SUMMON, 11, 15, 16, 53}   # handled later / never generic
SPLASH_AREAS = (3, 4, 5, 6, 7, 8, 9, 10, 11, 12)   # circle / plus / x / square areas (radius >= 1)


class Item:
    """One weapon or chip, rules read once from the engine (features, cost...)."""
    def __init__(self, obj, is_weapon, owner=None):
        self.obj = obj
        self.owner = owner
        self.id = obj.id
        self.weapon = is_weapon
        self.name = obj.name
        self.cost = obj.cost or 0
        self.minr = obj.minRange or 0
        self.maxr = obj.maxRange or 0
        self.los = bool(obj.needsLos)
        self.area = obj.area or 1
        self.max_uses = obj.maxUses if (obj.maxUses and obj.maxUses > 0) else 99
        self.cooldown = 0 if is_weapon else (obj.cooldown or 0)
        try:
            self.launch = obj.launchType or 7
        except Exception:
            self.launch = 7
        self.effects = [(f.type, f.minValue, f.maxValue, f.turns, f.targets, f.modifiers) for f in obj.features]
        # (type, average value, turns, non-stackable lasting effect, on caster) for the
        # simulator; modifier bit 4 = MODIFIER_ON_CASTER (e.g. dark katana's self damage)
        self.fx = [(e[0], (e[1] + e[2]) / 2.0, e[3] or 0, (e[3] or 0) > 0 and not ((e[5] or 0) & 1),
                    bool((e[5] or 0) & 4)) for e in self.effects]
        # engine Attack.filterTarget: an effect only lands on targets its flags allow (1 enemies, 2 allies,
        # 4 caster, 8 non-summons, 16 summons). burning (17) only hits summons; on-caster effects always apply
        tg = [(e[4] if e[4] is not None else 31) for e in self.effects]
        self.fx_leek = [x for x, g in zip(self.fx, tg) if x[4] or ((g & T_ENEMY) and (g & T_LEEK))]
        self.fx_bulb = [x for x, g in zip(self.fx, tg) if x[4] or ((g & T_ENEMY) and (g & T_SUMMON))]
        self.fx_self = [x for x, g in zip(self.fx, tg) if x[4] or (g & T_CASTER)]
        self.types = types = {e[0] for e in self.effects}
        self.unheal = any(e[0] == E_ADD_STATE and int(e[1] or 0) == ST_UNHEALABLE for e in self.effects)
        self.offensive = bool(types & OFFENSIVE) or self.unheal
        self.self_cast = bool(types) and types <= SELF_ONLY
        self.special = bool(types & MOVE_EFFECTS)
        # read once instead of re-scanning the effects in the hot loops
        self.harms = bool(types & {E_DAMAGE, E_POISON})          # what a self-hit would cost
        self.is_si = E_SUPERINF in types
        self.splash = self.area in SPLASH_AREAS
        # a repeat of an item made only of non-stackable lasting effects only replaces them
        self.rep_cap = 1 if all(e[0] != E_DAMAGE and (e[3] or 0) > 0 and not ((e[5] or 0) & 1)
                                for e in self.effects) else self.max_uses
        self._cd = None

    def current_cooldown(self):
        """Cooldown at snapshot time, read once per turn (nothing is cast while planning)."""
        if self._cd is None:
            self._cd = self.cooldown_now()
        return self._cd

    def cooldown_now(self):
        """Live cooldown of this chip for its OWNER (enemy chips via currentCooldownOf)."""
        if self.weapon:
            return 0
        try:
            if self.owner is not None and self.owner != Fight.me.id:
                return self.obj.currentCooldownOf(self.owner) or 0
            return self.obj.currentCooldown or 0
        except Exception:
            return 0


def items_of(entity):
    return ([Item(w, True, entity.id) for w in (entity.weapons or []) if w is not None]
            + [Item(c, False, entity.id) for c in (entity.chips or []) if c is not None])


def avg(e):
    return (e[1] + e[2]) / 2.0
