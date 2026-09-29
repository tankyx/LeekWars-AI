# ---- 10_items: item rules read from the engine's own item data -----------
# Effect type ids (engine Effect.TYPE_*)
E_DAMAGE, E_HEAL, E_BUFF_STR, E_BUFF_AGI, E_REL_SHIELD, E_ABS_SHIELD = 1, 2, 3, 4, 5, 6
E_BUFF_MP, E_BUFF_TP, E_DEBUFF, E_TELEPORT, E_VITALITY, E_POISON = 7, 8, 9, 10, 12, 13
E_SUMMON, E_SHK_MP, E_SHK_TP, E_SHK_STR, E_RETURN, E_BUFF_RES, E_BUFF_WIS = 14, 17, 18, 19, 20, 21, 22
E_ANTIDOTE, E_SHK_MAG, E_VULN, E_VULN_ABS, E_NOVA = 23, 24, 26, 27, 30
E_RAW_MP, E_RAW_TP, E_RAW_ABS, E_RAW_STR, E_RAW_MAG, E_RAW_SCI, E_RAW_AGI, E_RAW_RES = 31, 32, 37, 38, 39, 40, 41, 42
E_RAW_WIS, E_ATTRACT, E_SHK_AGI, E_REMOVE_SHK, E_PUSH, E_RAW_POW, E_RAW_REL, E_STEAL = 44, 46, 47, 49, 51, 52, 54, 61

OFFENSIVE = {E_DAMAGE, E_POISON, E_NOVA, E_SHK_MP, E_SHK_TP, E_SHK_STR, E_SHK_MAG, E_SHK_AGI, E_VULN, E_VULN_ABS}
SELF_ONLY = {E_HEAL, E_BUFF_STR, E_BUFF_AGI, E_REL_SHIELD, E_ABS_SHIELD, E_BUFF_MP, E_BUFF_TP, E_VITALITY,
             E_RETURN, E_BUFF_RES, E_BUFF_WIS, E_RAW_MP, E_RAW_TP, E_RAW_ABS, E_RAW_STR, E_RAW_MAG, E_RAW_SCI,
             E_RAW_AGI, E_RAW_RES, E_RAW_WIS, E_RAW_POW, E_RAW_REL, E_ANTIDOTE, E_REMOVE_SHK}
MOVE_EFFECTS = {E_TELEPORT, E_ATTRACT, E_PUSH, E_SUMMON, 11, 15, 16, 53}   # handled later / never generic
# area -> radius for the self-hit check (circle/plus/x/square approximated by radius)
AREA_RADIUS = {1: 0, 2: 0, 3: 1, 4: 2, 5: 3, 6: 2, 7: 3, 8: 1, 9: 2, 10: 3, 11: 1, 12: 2, 13: 0}


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
        self.effects = []
        for f in obj.features:
            self.effects.append((f.type, f.minValue, f.maxValue, f.turns, f.targets, f.modifiers))
        # (type, average value, turns, non-stackable lasting effect) for the simulator
        self.fx = [(e[0], (e[1] + e[2]) / 2.0, e[3] or 0, (e[3] or 0) > 0 and not ((e[5] or 0) & 1))
                   for e in self.effects]
        types = {e[0] for e in self.effects}
        self.offensive = bool(types & OFFENSIVE)
        self.self_cast = bool(types) and types <= SELF_ONLY
        self.special = bool(types & MOVE_EFFECTS)

    def current_cooldown(self):
        """Cooldown of this chip for its OWNER (enemy chips via currentCooldownOf)."""
        if self.weapon:
            return 0
        try:
            if self.owner is not None and self.owner != Fight.me.id:
                return self.obj.currentCooldownOf(self.owner) or 0
            return self.obj.currentCooldown or 0
        except Exception:
            return 0


def items_of(entity):
    out = []
    for w in (entity.weapons or []):
        if w is not None:
            out.append(Item(w, True, entity.id))
    for c in (entity.chips or []):
        if c is not None:
            out.append(Item(c, False, entity.id))
    return out


def avg(e):
    return (e[1] + e[2]) / 2.0
