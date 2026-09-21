#!/usr/bin/env python3
"""
Decode generator fight actions into readable names.

THE TRAP this exists to close: a fight action references a chip/weapon by the
generator's `template` field, NOT by the item-template id that
tools/item_get-all.json is keyed on. The two numbering schemes overlap, so
naively looking an action id up in item_get-all.json silently returns a
DIFFERENT item - a diagnostic run reported `hat_fedora` and `potion_skin_white`
as chips being cast. Verified in ActionUseChip.java / ActionSetWeapon.java,
both of which call getTemplate(); e.g. divine_protection is id=419 template=113.

There are THREE id spaces in play. Use the right accessor for the right source:
    chip   action  -> `template`   (Chip.getTemplate, e.g. antidote 70)
    chip   config  -> `id`         (Chips registry keys on getId, antidote 110)
    weapon action  -> `template`   (Weapon.getTemplate, heavy_sword 36)
    weapon config  -> `item`       (Generator.java builds Weapon with the `item`
                                    field as its id, so heavy_sword is 278 in
                                    tools/leek_configs.json and in loadouts)

SERVER fights use the same template space for USE_CHIP / SET_WEAPON as the
local generator, so chip() and weapon() apply to both -- verified 2026-09-21 on
ladder fight 53748910 (template decode yields a coherent kit, config-space
decode yields garbage). Only the packaging differs: the server returns the
action stream under fight['data'], not at top level. Leek stat sheets from
/leek/get are a different matter: top-level `strength` etc. are BASE values,
and the simulation-relevant totals (including components) are `total_*`.

Action shapes (generator src/main/java/com/leekwars/generator/action/):
    [7,  entity]                     LEEK_TURN   - sets the acting entity
    [12, chip_template, cell, result]  USE_CHIP  - result 1=ok 2=critical
    [13, weapon_template]            SET_WEAPON  - applies to acting entity
    [16, cell, result]               USE_WEAPON  - carries NO weapon id; you
                                                   must track the last
                                                   SET_WEAPON per entity
    [code, target, pv, erosion]      damage, where code is a DamageType:
        101 DIRECT  107 NOVA  108 RETURN  109 LIFE  110 POISON/AFTEREFFECT
    [103, target, life]              HEAL

    from lw_decode import Decoder, parse_fight
    d = Decoder(); d.chip(113) -> 'divine_protection'
"""
import json
import os
from collections import defaultdict

GEN = '/home/ubuntu/leek-wars-generator/data'
HERE = os.path.dirname(os.path.abspath(__file__))

# Effect ids (generator effect/Effect.java) - the ones worth naming in traces.
EFFECTS = {
    1: 'DAMAGE', 2: 'HEAL', 13: 'POISON', 19: 'DEBUFF', 27: 'ABSOLUTE_VULNERABILITY',
    30: 'NOVA_DAMAGE', 57: 'SHACKLE_MP', 59: 'ADD_STATE', 60: 'STEAL_LIFE_PCT',
    61: 'STEAL_LIFE',
}

# Fight action codes, transcribed from action/Action.java (do not guess these -
# 104 is VITALITY, not TP_LOST; TP loss is 100).
ACTIONS = {
    0: 'START_FIGHT', 4: 'END_FIGHT', 5: 'PLAYER_DEAD', 6: 'NEW_TURN',
    7: 'LEEK_TURN', 8: 'END_TURN', 9: 'SUMMON', 10: 'MOVE_TO', 11: 'KILL',
    12: 'USE_CHIP', 13: 'SET_WEAPON', 14: 'STACK_EFFECT', 15: 'CHEST_OPENED',
    16: 'USE_WEAPON',
    100: 'LOST_TP', 101: 'LOST_LIFE', 102: 'LOST_MP', 103: 'HEAL',
    104: 'VITALITY', 105: 'RESURRECT', 106: 'LOSE_STRENGTH', 107: 'NOVA_DAMAGE',
    108: 'DAMAGE_RETURN', 109: 'LIFE_DAMAGE', 110: 'POISON_DAMAGE',
    111: 'AFTEREFFECT', 112: 'NOVA_VITALITY',
    201: 'LAMA', 203: 'SAY', 205: 'SHOW_CELL',
    301: 'ADD_WEAPON_EFFECT', 302: 'ADD_CHIP_EFFECT', 303: 'REMOVE_EFFECT',
    304: 'UPDATE_EFFECT', 306: 'REDUCE_EFFECTS', 307: 'REMOVE_POISONS',
    308: 'REMOVE_SHACKLES',
    1000: 'ERROR', 1001: 'MAP', 1002: 'AI_ERROR',
}

# [code, target, pv, erosion] - every DamageType shares this shape.
DAMAGE_CODES = {101: 'direct', 107: 'nova', 108: 'return', 109: 'life', 110: 'poison'}


def _load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except OSError:
        return {}


class Decoder:
    def __init__(self):
        chips = _load(os.path.join(GEN, 'chips.json'))
        weapons = _load(os.path.join(GEN, 'weapons.json'))
        chips = chips.values() if isinstance(chips, dict) else chips
        weapons = weapons.values() if isinstance(weapons, dict) else weapons
        # template -> name, which is what local fight actions actually carry
        self._chip = {c['template']: c['name'] for c in chips
                      if isinstance(c, dict) and 'template' in c}
        self._weapon = {w['template']: w['name'] for w in weapons
                        if isinstance(w, dict) and 'template' in w}
        # config/loadout space: chips key on `id`, weapons key on `item`
        self._chip_cfg = {c['id']: c['name'] for c in chips
                          if isinstance(c, dict) and 'id' in c}
        self._weapon_cfg = {w['item']: w['name'] for w in weapons
                            if isinstance(w, dict) and 'item' in w}
        self._chip_full = {c['name']: c for c in chips if isinstance(c, dict)}
        self._weapon_full = {w['name']: w for w in weapons if isinstance(w, dict)}

    def chip(self, t):
        """Name for a chip id as it appears in a FIGHT ACTION (template space)."""
        return self._chip.get(t, 'chip?%s' % t)

    def weapon(self, t):
        """Name for a weapon id as it appears in a SET_WEAPON action (template)."""
        return self._weapon.get(t, 'weapon?%s' % t)

    def chip_cfg(self, i):
        """Name for a chip id as it appears in leek_configs.json / loadouts."""
        return self._chip_cfg.get(i, 'chip_cfg?%s' % i)

    def weapon_cfg(self, i):
        """Name for a weapon id as it appears in leek_configs.json / loadouts."""
        return self._weapon_cfg.get(i, 'weapon_cfg?%s' % i)

    def info(self, name):
        """Full generator record (cost, cooldown, range, effects) by name."""
        return self._chip_full.get(name) or self._weapon_full.get(name) or {}

    def effect(self, e):
        return EFFECTS.get(e, 'effect?%s' % e)

    def action(self, a):
        return ACTIONS.get(a, 'action?%s' % a)

    def self_test(self):
        """Known-good anchors; raises if the mapping regresses."""
        assert self.chip(113) == 'divine_protection', self.chip(113)
        assert self.chip(112) == 'apocalypse', self.chip(112)
        assert self.weapon(12) == 'm_laser', self.weapon(12)
        # the exact collision that produced the garbage output: these templates
        # mean something entirely different in item_get-all.json's id space.
        assert self.chip(1) == 'bandage', self.chip(1)
        # config space must NOT agree with action space, or the split is broken
        assert self.chip_cfg(110) == 'antidote', self.chip_cfg(110)
        assert self.chip(70) == 'antidote', self.chip(70)
        assert self.weapon_cfg(278) == 'heavy_sword', self.weapon_cfg(278)
        assert self.weapon(36) == 'heavy_sword', self.weapon(36)
        assert self.info('antidote')['cost'] == 3
        return True


def parse_fight(fight, decoder=None):
    """Roll a local generator fight up into per-entity usage/damage totals.

    Returns {entity_id: {...}} plus a '_meta' key. Damage is recorded against
    the entity that TOOK it (that is what the action carries); use the
    attribution fields for who dealt it where the action allows it.
    """
    d = decoder or Decoder()
    ents = {}
    for l in fight.get('leeks', []):
        ents[l['id']] = {
            'name': l.get('name'), 'team': l.get('team'), 'chips': defaultdict(int),
            'weapons': defaultdict(int), 'crits': 0, 'moves': 0, 'turns': 0,
            'taken': defaultdict(int), 'healed': 0, 'dealt': defaultdict(int),
            'poisons_cleansed': 0, 'died': False, 'switches': 0,
        }

    def ent(i):
        if i not in ents:
            ents[i] = {'name': 'summon/%s' % i, 'team': None, 'chips': defaultdict(int),
                       'weapons': defaultdict(int), 'crits': 0, 'moves': 0, 'turns': 0,
                       'taken': defaultdict(int), 'healed': 0, 'dealt': defaultdict(int),
                       'poisons_cleansed': 0, 'died': False, 'switches': 0}
        return ents[i]

    cur = None
    held = {}          # entity -> weapon template currently equipped
    turns = 0
    errors = 0
    for a in fight.get('actions', []):
        if not isinstance(a, list) or not a:
            continue
        c = a[0]
        if c == 6:
            turns += 1
        elif c == 7:
            cur = a[1] if len(a) > 1 else None
            if cur is not None and cur >= 0:
                ent(cur)['turns'] += 1
        elif c == 10:
            if cur is not None:
                ent(cur)['moves'] += 1
        elif c == 13 and len(a) > 1 and cur is not None:
            # A weapon switch costs 1 TP (State.setWeapon -> entity.useTP(1)),
            # which is easy to miss and understates TP spend on a 4-weapon leek.
            if held.get(cur) != a[1]:
                ent(cur)['switches'] += 1
            held[cur] = a[1]
        elif c == 12 and len(a) > 2 and cur is not None:
            e = ent(cur)
            e['chips'][d.chip(a[1])] += 1
            if len(a) > 3 and a[3] == 2:
                e['crits'] += 1
        elif c == 16 and cur is not None:
            e = ent(cur)
            e['weapons'][d.weapon(held.get(cur, -1))] += 1
            if len(a) > 2 and a[2] == 2:
                e['crits'] += 1
        elif c in DAMAGE_CODES and len(a) > 2:
            kind = DAMAGE_CODES[c]
            ent(a[1])['taken'][kind] += a[2]
            # direct/nova/life are dealt by whoever is acting; poison and
            # return damage are not attributable to the acting entity.
            if cur is not None and kind in ('direct', 'nova', 'life') and cur != a[1]:
                ent(cur)['dealt'][kind] += a[2]
        elif c == 103 and len(a) > 2:
            ent(a[1])['healed'] += a[2]
        elif c == 307 and len(a) > 1:
            ent(a[1])['poisons_cleansed'] += 1
        elif c == 5 and len(a) > 1:
            ent(a[1])['died'] = True
        elif c == 1002:
            errors += 1
    return {'_meta': {'turns': turns, 'ai_errors': errors}, **ents}


if __name__ == '__main__':
    d = Decoder()
    d.self_test()
    print('decoder self-test OK')
    print('  chips known: %d  weapons known: %d' % (len(d._chip), len(d._weapon)))
    # show the collisions, so the trap stays visible
    items = _load(os.path.join(HERE, 'item_get-all.json'))
    by_id = {int(v['id']): v.get('name') for v in items.values()} if items else {}
    print('\n  template -> real chip        (vs what item_get-all.json id space says)')
    for t in (1, 12, 30, 35, 98, 112, 113):
        print('   %4d -> %-22s (id-space: %s)' % (t, d.chip(t), by_id.get(t, '-')))
