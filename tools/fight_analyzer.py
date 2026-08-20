#!/usr/bin/env python3
"""
Turn-by-Turn Fight Behavior Analyzer for LeekWars V8 AI.

Reconstructs entity state (HP/TP/MP/cell/effects) turn by turn from the
actions stream, correlates V8 debug logs with turns, and flags anomalies
like wasted TP, wrong weapon for build, or movement contradictions.

Usage:
    # Run a fight and analyze
    python3 tools/fight_analyzer.py smart_str --leek MargaretHamilton
    # Replay with deterministic seed
    python3 tools/fight_analyzer.py smart_str --leek KurtGodel --seed 42
    # Analyze saved fight JSON
    python3 tools/fight_analyzer.py --file fight_data.json
    # Show only anomalies
    python3 tools/fight_analyzer.py smart_str --leek AdaLovelace --anomalies-only
    # Filter turns
    python3 tools/fight_analyzer.py smart_str --leek KurtGodel --turns 5-10
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent
GENERATOR_DIR = Path("/home/ubuntu/leek-wars-generator")

# Import local_test infrastructure
sys.path.insert(0, str(SCRIPT_DIR))
from local_test import build_scenario, run_fight, load_configs

# ── Action constants (generator format) ──
ACT_START_FIGHT = 0
ACT_USE_WEAPON_OLD = 1
ACT_USE_CHIP_OLD = 2
ACT_SET_WEAPON_OLD = 3
ACT_END_FIGHT = 4
ACT_PLAYER_DEAD = 5
ACT_NEW_TURN = 6
ACT_LEEK_TURN = 7
ACT_END_TURN = 8
ACT_SUMMON = 9
ACT_MOVE_TO = 10
ACT_USE_CHIP = 12
ACT_SET_WEAPON = 13
ACT_USE_WEAPON = 16
ACT_TP_LOST = 100
ACT_LIFE_LOST = 101
ACT_MP_LOST = 102
ACT_CARE = 103
ACT_VITALITY = 104
ACT_NOVA_DAMAGE = 107
ACT_POISON_DAMAGE = 110
ACT_ADD_WEAPON_EFFECT = 301
ACT_ADD_CHIP_EFFECT = 302
ACT_REMOVE_EFFECT = 303
ACT_REMOVE_POISON = 307
ACT_AI_ERROR = 1002

EFFECT_NAMES = {
    1: "DMG", 2: "HEAL", 3: "BUFF_STR", 4: "BUFF_AGI",
    5: "REL_SHIELD", 6: "ABS_SHIELD", 7: "BUFF_MP", 8: "BUFF_TP",
    9: "LIBERATION", 10: "TELEPORT", 11: "INVERSION", 12: "VITALITY",
    13: "POISON", 14: "SUMMON", 15: "RESURRECT", 16: "KILL",
    17: "SHACKLE_MP", 18: "SHACKLE_TP", 19: "SHACKLE_STR",
    20: "DMG_RETURN", 21: "BUFF_RES", 22: "BUFF_WIS",
    23: "ANTIDOTE", 24: "SHACKLE_MAG", 25: "AFTEREFFECT",
    26: "VULNERABILITY", 27: "DEBUFF_RES", 28: "LIFE_STEAL",
    30: "NOVA_DMG", 31: "BUFF_MP2", 32: "BUFF_TP2",
    38: "BUFF_STR2", 39: "BUFF_MAG", 40: "BUFF_SCI",
    41: "BUFF_FREQ", 42: "BUFF_RES2", 43: "COVID_SPREAD",
    44: "BUFF_WIS2", 45: "VITALITY2",
    46: "GRAPPLE", 47: "SHACKLE_AGI", 48: "BRAINWASH",
    49: "MANUMISSION", 51: "BOXING_GLOVE", 61: "QUANTUM_COPY",
}

# Effect IDs for magic-friendly weapon checks
EFF_POISON = 13
EFF_SHACKLE_MP = 17
EFF_SHACKLE_TP = 18
EFF_SHACKLE_STR = 19
EFF_SHACKLE_MAG = 24


# ── ItemResolver ──
class ItemResolver:
    """Resolves weapon db_ids and chip template_ids to names/costs/metadata.

    Generator action formats:
    - SET_WEAPON [13, weapon_db_id] — weapons use db_id (== template for weapons)
    - USE_CHIP [12, chip_template_id, ...] — chips use template field
    - ADD_CHIP_EFFECT [302, chip_db_id, ...] — effects use chip db_id
    """

    def __init__(self):
        self.weapons = {}             # db_id -> weapon info
        self.chips_by_id = {}         # db_id -> chip info
        self.chips_by_template = {}   # template -> chip info
        self._load_data()

    def _load_data(self):
        weapons_path = GENERATOR_DIR / "data" / "weapons.json"
        chips_path = GENERATOR_DIR / "data" / "chips.json"

        if weapons_path.exists():
            with open(weapons_path) as f:
                data = json.load(f)
            for _, w in data.items():
                info = {
                    "id": w["id"],
                    "item": w.get("item", w["id"]),
                    "name": w["name"],
                    "cost": w.get("cost", 0),
                    "min_range": w.get("min_range", 0),
                    "max_range": w.get("max_range", 0),
                    "effects": w.get("effects", []),
                    "passive_effects": w.get("passive_effects", []),
                    "template": w.get("template", w["id"]),
                }
                self.weapons[w["id"]] = info

        if chips_path.exists():
            with open(chips_path) as f:
                data = json.load(f)
            for _, c in data.items():
                info = {
                    "id": c["id"],
                    "name": c["name"],
                    "cost": c.get("cost", 0),
                    "min_range": c.get("min_range", 0),
                    "max_range": c.get("max_range", 0),
                    "effects": c.get("effects", []),
                    "cooldown": c.get("cooldown", 0),
                    "type": c.get("type", 0),
                    "template": c.get("template", c["id"]),
                }
                self.chips_by_id[c["id"]] = info
                self.chips_by_template[c.get("template", c["id"])] = info

    def weapon_name(self, db_id):
        w = self.weapons.get(db_id)
        return w["name"] if w else f"weapon_{db_id}"

    def weapon_cost(self, db_id):
        w = self.weapons.get(db_id)
        return w["cost"] if w else 0

    def weapon_info(self, db_id):
        return self.weapons.get(db_id)

    def chip_name_by_template(self, template_id):
        """Resolve chip name from template ID (used in USE_CHIP actions)."""
        c = self.chips_by_template.get(template_id)
        return c["name"] if c else f"chip_t{template_id}"

    def chip_cost_by_template(self, template_id):
        c = self.chips_by_template.get(template_id)
        return c["cost"] if c else 0

    def chip_name_by_id(self, chip_id):
        """Resolve chip name from db_id (used in ADD_CHIP_EFFECT actions)."""
        c = self.chips_by_id.get(chip_id)
        return c["name"] if c else f"chip_{chip_id}"

    def weapon_is_magic_friendly(self, db_id):
        """Check if weapon has poison or debuff effects (magic-scaled)."""
        w = self.weapons.get(db_id)
        if not w:
            return False
        magic_ids = {EFF_POISON, EFF_SHACKLE_MP, EFF_SHACKLE_TP, EFF_SHACKLE_STR, EFF_SHACKLE_MAG}
        for eff in w.get("effects", []):
            if eff.get("id") in magic_ids:
                return True
        return False


# ── EntityState ──
@dataclass
class EntityState:
    entity_id: int
    name: str
    team: int
    hp: int
    max_hp: int
    tp: int
    mp: int
    cell: int
    current_weapon: Optional[int] = None  # weapon db_id
    alive: bool = True
    strength: int = 0
    magic: int = 0
    agility: int = 0
    wisdom: int = 0
    resistance: int = 0
    science: int = 0
    frequency: int = 0
    active_effects: list = field(default_factory=list)
    # Per-turn accumulators
    damage_dealt: int = 0
    damage_taken: int = 0
    healing: int = 0
    poison_taken: int = 0
    nova_dealt: int = 0
    # Cumulative totals
    total_damage_dealt: int = 0
    total_damage_taken: int = 0
    total_healing: int = 0
    total_poison_taken: int = 0
    total_nova_dealt: int = 0

    def reset_turn(self):
        self.damage_dealt = 0
        self.damage_taken = 0
        self.healing = 0
        self.poison_taken = 0
        self.nova_dealt = 0

    def snapshot(self):
        return {
            "hp": self.hp, "max_hp": self.max_hp, "tp": self.tp, "mp": self.mp,
            "cell": self.cell, "weapon": self.current_weapon, "alive": self.alive,
            "effects": list(self.active_effects),
        }


# ── BuildDetector ──
def detect_build(stats):
    """Mirror of V8's detectBuildType from weight_profiles.lk."""
    s = stats.get("strength", 0)
    m = stats.get("magic", 0)
    a = stats.get("agility", 0)
    sci = stats.get("science", 0)
    res = stats.get("resistance", 0)
    if res >= 300 and sci >= 300: return "TANK_SCI"
    if s >= m and s >= a and sci >= 200: return "STR_SCI"
    if m > s + 100: return "MAGIC"
    if abs(s - m) < 100 and m >= 100 and s >= 100: return "HYBRID"
    if a >= s and a >= m: return "AGILITY"
    if m >= s: return "MAGIC"
    return "STRENGTH"


# ── Cell Distance ──
def cell_distance(c1, c2, map_width=18):
    """Approximate cell distance on the LeekWars rotated-square grid."""
    y1, x1 = divmod(c1, map_width)
    y2, x2 = divmod(c2, map_width)
    return max(abs(x1 - x2), abs(y1 - y2))


# ── FightStateTracker ──
class FightStateTracker:
    """Processes actions stream and maintains per-entity state.

    Generator action formats (verified against actual output):
    - [6, turn_number] — NEW_TURN
    - [7, entity_id] — LEEK_TURN (sets active entity)
    - [8, entity_id, remaining_tp, remaining_mp] — END_TURN
    - [10, entity_id, dest_cell, [path_cells]] — MOVE_TO
    - [12, chip_template_id, target_cell, success] — USE_CHIP (caster=active)
    - [13, weapon_db_id] — SET_WEAPON (caster=active)
    - [16, target_cell, flag] — USE_WEAPON (caster=active, weapon=current_weapon)
    - [101, entity_id, amount, ?] — LIFE_LOST
    - [103, entity_id, amount] — CARE/HEAL
    - [104, entity_id, amount] — VITALITY (max_hp + hp)
    - [107, entity_id, amount] — NOVA_DAMAGE (reduce max_hp)
    - [110, entity_id, amount, ?] — POISON_DAMAGE
    - [302, chip_db_id, eff_idx, caster, target, eff_type, value, turns, ...] — ADD_CHIP_EFFECT
    - [301, wpn_db_id, eff_idx, caster, target, eff_type, value, turns, ...] — ADD_WEAPON_EFFECT
    - [303, eff_idx] — REMOVE_EFFECT
    - [5, entity_id, ?] — PLAYER_DEAD
    - [1002, entity_id] — AI_ERROR
    """

    def __init__(self, leeks, resolver: ItemResolver):
        self.resolver = resolver
        self.entities = {}
        self.turn_number = 0
        self.active_entity_id = None
        self.turn_actions = {}     # entity_id -> list of action desc strings (current turn)
        self.turn_snapshots = {}   # turn_number -> {entity_id: snapshot dict}
        # Per-turn history (saved at end of each turn)
        self.history_actions = {}  # turn_number -> {entity_id: [action_descs]}
        self.history_stats = {}    # turn_number -> {entity_id: {dealt, taken, healed, poison, nova}}

        for leek in leeks:
            eid = leek["id"]
            self.entities[eid] = EntityState(
                entity_id=eid,
                name=leek.get("name", f"Entity_{eid}"),
                team=leek.get("team", 0),
                hp=leek.get("life", 0),
                max_hp=leek.get("life", 0),
                tp=leek.get("tp", 0),
                mp=leek.get("mp", 0),
                cell=leek.get("cellPos", leek.get("cell", 0)),
                strength=leek.get("strength", 0),
                magic=leek.get("magic", 0),
                agility=leek.get("agility", 0),
                wisdom=leek.get("wisdom", 0),
                resistance=leek.get("resistance", 0),
                science=leek.get("science", 0),
                frequency=leek.get("frequency", 0),
            )

    def process_actions(self, actions):
        for action in actions:
            if action and isinstance(action, list) and len(action) > 0:
                self._process(action)
        self.finalize()

    def _process(self, a):
        code = a[0]

        if code == ACT_NEW_TURN:
            # Save previous turn's history before reset
            if self.turn_number > 0:
                self._save_turn_history()
            self.turn_number = a[1] if len(a) > 1 else self.turn_number + 1
            self.turn_snapshots[self.turn_number] = {
                eid: e.snapshot() for eid, e in self.entities.items()
            }
            for e in self.entities.values():
                e.reset_turn()
            self.turn_actions = {eid: [] for eid in self.entities}

        elif code == ACT_LEEK_TURN:
            eid = a[1] if len(a) > 1 else None
            self.active_entity_id = eid
            # Handle implicit turn 1 (no [6,1] NEW_TURN action exists)
            if self.turn_number == 0:
                self.turn_number = 1
                self.turn_snapshots[1] = {
                    eid2: e.snapshot() for eid2, e in self.entities.items()
                }
                self.turn_actions = {eid2: [] for eid2 in self.entities}
            # Ensure entity has action list for this turn (may be a summon)
            if eid is not None and eid not in self.turn_actions:
                self.turn_actions[eid] = []

        elif code == ACT_END_TURN:
            # [8, entity_id, remaining_tp, remaining_mp]
            if len(a) >= 4:
                eid = a[1]
                e = self.entities.get(eid)
                if e:
                    e.tp = a[2]
                    e.mp = a[3]

        elif code == ACT_MOVE_TO:
            # [10, entity_id, dest_cell, [path_cells]]
            if len(a) >= 4:
                eid = a[1]
                dest = a[2]
                path = a[3] if isinstance(a[3], list) else [dest]
                e = self.entities.get(eid)
                if e:
                    old_cell = e.cell
                    e.cell = dest
                    steps = len(path)
                    self._log(eid, f"MOVE → cell {dest} ({steps} steps, from {old_cell})")

        elif code == ACT_SET_WEAPON:
            # [13, weapon_db_id] — caster = active entity
            if len(a) >= 2:
                weapon_id = a[1]
                eid = self.active_entity_id
                e = self.entities.get(eid) if eid is not None else None
                if e:
                    e.current_weapon = weapon_id
                wname = self.resolver.weapon_name(weapon_id)
                self._log(eid, f"SET_WEAPON {wname}")

        elif code == ACT_USE_CHIP:
            # [12, chip_template_id, target_cell, success]
            if len(a) >= 4:
                template_id = a[1]
                target_cell = a[2]
                success = a[3]
                eid = self.active_entity_id
                cname = self.resolver.chip_name_by_template(template_id)
                # Determine target entity from cell
                target_name = self._entity_at_cell(target_cell, exclude=None)
                e = self.entities.get(eid) if eid is not None else None
                if target_name and e and target_name == e.name:
                    target_name = "self"
                status = "" if success >= 1 else " [FAILED]"
                self._log(eid, f"USE_CHIP {cname} → {target_name or f'cell_{target_cell}'}{status}")

        elif code == ACT_USE_WEAPON:
            # [16, target_cell, flag] — weapon = active entity's current_weapon
            if len(a) >= 2:
                target_cell = a[1]
                eid = self.active_entity_id
                e = self.entities.get(eid) if eid is not None else None
                wname = self.resolver.weapon_name(e.current_weapon) if e and e.current_weapon else "weapon_?"
                target_name = self._entity_at_cell(target_cell, exclude=eid)
                self._log(eid, f"USE_WEAPON {wname} → {target_name or f'cell_{target_cell}'}")

        elif code == ACT_LIFE_LOST:
            # [101, entity_id, amount, ?]
            if len(a) >= 3:
                eid = a[1]
                amount = a[2]
                e = self.entities.get(eid)
                if e:
                    e.hp -= amount
                    e.damage_taken += amount
                    e.total_damage_taken += amount
                attacker = self.active_entity_id
                if attacker is not None and attacker != eid:
                    ae = self.entities.get(attacker)
                    if ae:
                        ae.damage_dealt += amount
                        ae.total_damage_dealt += amount
                self._annotate(attacker, f"→ {amount} dmg")

        elif code == ACT_CARE:
            # [103, entity_id, amount]
            if len(a) >= 3:
                eid = a[1]
                amount = a[2]
                e = self.entities.get(eid)
                if e:
                    e.hp = min(e.hp + amount, e.max_hp)
                    e.healing += amount
                    e.total_healing += amount
                self._annotate(self.active_entity_id, f"→ +{amount} HP")

        elif code == ACT_VITALITY:
            # [104, entity_id, amount]
            if len(a) >= 3:
                eid = a[1]
                amount = a[2]
                e = self.entities.get(eid)
                if e:
                    e.max_hp += amount
                    e.hp += amount

        elif code == ACT_NOVA_DAMAGE:
            # [107, entity_id, amount]
            if len(a) >= 3:
                eid = a[1]
                amount = a[2]
                e = self.entities.get(eid)
                if e:
                    e.max_hp -= amount
                    e.hp = min(e.hp, e.max_hp)
                attacker = self.active_entity_id
                if attacker is not None and attacker != eid:
                    ae = self.entities.get(attacker)
                    if ae:
                        ae.nova_dealt += amount
                        ae.total_nova_dealt += amount
                self._annotate(attacker, f"→ {amount} nova")

        elif code == ACT_POISON_DAMAGE:
            # [110, entity_id, amount, ?]
            if len(a) >= 3:
                eid = a[1]
                amount = a[2]
                e = self.entities.get(eid)
                if e:
                    e.hp -= amount
                    e.poison_taken += amount
                    e.total_poison_taken += amount

        elif code == ACT_TP_LOST:
            if len(a) >= 3:
                e = self.entities.get(a[1])
                if e:
                    e.tp -= a[2]

        elif code == ACT_MP_LOST:
            if len(a) >= 3:
                e = self.entities.get(a[1])
                if e:
                    e.mp -= a[2]

        elif code in (ACT_ADD_CHIP_EFFECT, ACT_ADD_WEAPON_EFFECT):
            # [302, chip_db_id, eff_idx, caster, target, eff_type, value, turns, ...]
            # [301, wpn_db_id, eff_idx, caster, target, eff_type, value, turns, ...]
            if len(a) >= 8:
                target_id = a[4]
                eff_type = a[5]
                value = a[6]
                turns = a[7]
                caster_id = a[3]
                e = self.entities.get(target_id)
                if e:
                    e.active_effects.append((eff_type, value, turns, caster_id))
                eff_name = EFFECT_NAMES.get(eff_type, f"eff_{eff_type}")
                turn_str = f" x{turns}t" if turns > 0 else ""
                self._annotate(self.active_entity_id, f"[{eff_name} {value}{turn_str}]")

        elif code == ACT_PLAYER_DEAD:
            if len(a) >= 2:
                e = self.entities.get(a[1])
                if e:
                    e.alive = False
                    e.hp = 0

        elif code == ACT_AI_ERROR:
            if len(a) >= 2:
                self._log(a[1], "!! AI_ERROR (crash/bug) !!")

        elif code == ACT_SUMMON:
            if len(a) >= 3:
                eid = self.active_entity_id
                summon_id = a[1]
                if summon_id not in self.entities:
                    owner = self.entities.get(eid)
                    self.entities[summon_id] = EntityState(
                        entity_id=summon_id, name=f"Summon_{summon_id}",
                        team=owner.team if owner else 0,
                        hp=a[3] if len(a) > 3 else 0,
                        max_hp=a[3] if len(a) > 3 else 0,
                        tp=0, mp=0, cell=a[2] if len(a) > 2 else 0,
                    )
                self._log(eid, f"SUMMON entity {summon_id}")

    def finalize(self):
        """Save the last turn's history after all actions are processed."""
        if self.turn_number > 0:
            self._save_turn_history()

    def _save_turn_history(self):
        """Save current turn's actions and stats to history."""
        t = self.turn_number
        self.history_actions[t] = {
            eid: list(acts) for eid, acts in self.turn_actions.items()
        }
        self.history_stats[t] = {
            eid: {
                "dealt": e.damage_dealt, "taken": e.damage_taken,
                "healed": e.healing, "poison": e.poison_taken,
                "nova": e.nova_dealt, "tp": e.tp, "mp": e.mp,
            }
            for eid, e in self.entities.items()
        }

    def get_turn_actions(self, turn, eid):
        return self.history_actions.get(turn, {}).get(eid, [])

    def get_turn_stats(self, turn, eid):
        return self.history_stats.get(turn, {}).get(eid, {})

    def _log(self, eid, desc):
        if eid is not None and eid in self.turn_actions:
            self.turn_actions[eid].append(desc)

    def _annotate(self, eid, text):
        if eid is not None and eid in self.turn_actions and self.turn_actions[eid]:
            self.turn_actions[eid][-1] += f" {text}"

    def _entity_at_cell(self, cell, exclude=None):
        """Find entity name at a given cell."""
        for eid, e in self.entities.items():
            if eid != exclude and e.cell == cell and e.alive:
                return e.name
        return None

    def get_enemy_of(self, eid):
        e = self.entities.get(eid)
        if not e:
            return None
        for oid, o in self.entities.items():
            if o.team != e.team and o.alive:
                return oid
        return None


# ── LogCorrelator ──
class LogCorrelator:
    """Maps V8 debug logs to turn boundaries."""

    def __init__(self, logs, actions, v8_farmer_id):
        self.turn_logs = {}  # turn_number -> list of log message strings
        self._correlate(logs, actions, v8_farmer_id)

    def _correlate(self, logs, actions, v8_farmer_id):
        if not logs:
            return

        # Build action_index -> turn mapping
        turn_map = {}
        current_turn = 0
        for i, a in enumerate(actions):
            if a and isinstance(a, list) and a[0] == ACT_NEW_TURN:
                current_turn = a[1] if len(a) > 1 else current_turn + 1
            turn_map[i] = current_turn

        # Logs keyed by farmer_id (0-indexed, string keys)
        farmer_logs = logs.get(str(v8_farmer_id), {})

        for action_idx_str, entries in farmer_logs.items():
            try:
                idx = int(action_idx_str)
            except (ValueError, TypeError):
                continue
            turn = turn_map.get(idx, 0)
            if turn not in self.turn_logs:
                self.turn_logs[turn] = []
            for entry in entries:
                # entry: [entity_id, type, message, ?, ?, ?]
                # type=1 means text log, type=10 is separator
                if isinstance(entry, list) and len(entry) >= 3 and entry[1] == 1:
                    self.turn_logs[turn].append(str(entry[2]))

    def get_turn_logs(self, turn):
        return self.turn_logs.get(turn, [])

    def extract_state(self, turn):
        for msg in self.get_turn_logs(turn):
            if "[STATE]" in msg and "Strategic state:" in msg:
                return msg.split("Strategic state:")[-1].strip()
        return None

    def extract_target(self, turn):
        for msg in self.get_turn_logs(turn):
            if "[TARGET-SELECTION]" in msg:
                return msg.split("]", 1)[-1].strip()
        return None

    def extract_best_scenario(self, turn):
        for msg in self.get_turn_logs(turn):
            if "[UNIFIED-BEST]" in msg:
                return msg.split("]", 1)[-1].strip()
        return None

    def extract_build_type(self, turn):
        for msg in self.get_turn_logs(turn):
            if "[BUILD]" in msg:
                return msg.split("]", 1)[-1].strip()
        return None

    def extract_scenario_plan(self, turn):
        for msg in self.get_turn_logs(turn):
            if "[SCENARIO-PLAN]" in msg:
                return msg.split("]", 1)[-1].strip()
        return None

    def extract_fallback(self, turn):
        return any("[UNIFIED-FALLBACK]" in msg for msg in self.get_turn_logs(turn))


# ── AnomalyDetector ──
@dataclass
class Anomaly:
    severity: str  # ERROR, WARNING, INFO
    turn: int
    entity_id: int
    code: str
    message: str


class AnomalyDetector:
    """Detects behavioral anomalies in V8's fight actions."""

    def __init__(self, tracker: FightStateTracker, correlator: LogCorrelator,
                 resolver: ItemResolver, v8_id: int, build_type: str):
        self.tracker = tracker
        self.correlator = correlator
        self.resolver = resolver
        self.v8_id = v8_id
        self.build_type = build_type

    def detect_all(self, actions) -> list:
        anomalies = []
        current_turn = 0
        turn_start_snaps = {}

        for a in actions:
            if not a or not isinstance(a, list):
                continue
            if a[0] == ACT_LEEK_TURN and current_turn == 0:
                # Handle implicit turn 1 (no [6,1] action)
                current_turn = 1
                turn_start_snaps = {
                    eid: e.snapshot() for eid, e in self.tracker.entities.items()
                }
            elif a[0] == ACT_NEW_TURN:
                if current_turn > 0:
                    anomalies.extend(self._check_turn(current_turn, turn_start_snaps))
                current_turn = a[1] if len(a) > 1 else current_turn + 1
                turn_start_snaps = {
                    eid: e.snapshot() for eid, e in self.tracker.entities.items()
                }
            elif a[0] == ACT_AI_ERROR and len(a) >= 2 and a[1] == self.v8_id:
                anomalies.append(Anomaly("ERROR", current_turn, self.v8_id,
                                        "AI_ERROR", "AI runtime error/crash"))

        if current_turn > 0:
            anomalies.extend(self._check_turn(current_turn, turn_start_snaps))
        return anomalies

    def _check_turn(self, turn, start_snaps) -> list:
        anomalies = []
        v8 = self.tracker.entities.get(self.v8_id)
        if not v8 or not v8.alive:
            return anomalies

        enemy_id = self.tracker.get_enemy_of(self.v8_id)
        enemy = self.tracker.entities.get(enemy_id) if enemy_id else None
        v8_snap = self.tracker.turn_snapshots.get(turn, {}).get(self.v8_id)
        if not v8_snap:
            return anomalies

        state = self.correlator.extract_state(turn) or ""
        acts = self.tracker.get_turn_actions(turn, self.v8_id)
        stats = self.tracker.get_turn_stats(turn, self.v8_id)

        # ── WASTED_TP ──
        end_tp = stats.get("tp", 0)
        if enemy and enemy.alive and end_tp >= 3:
            # Get weapon from end-of-turn snapshot
            wpn = v8_snap.get("weapon")
            cheapest = self.resolver.weapon_cost(wpn) if wpn else 5
            if cheapest > 0 and end_tp >= cheapest:
                anomalies.append(Anomaly(
                    "WARNING", turn, self.v8_id, "WASTED_TP",
                    f"Ended with {end_tp} TP (cheapest attack={cheapest}), enemy alive"))

        # ── NO_DAMAGE ──
        dealt = stats.get("dealt", 0)
        nova = stats.get("nova", 0)
        if turn > 1 and enemy and enemy.alive and dealt == 0 and nova == 0:
            if "FLEE" not in state and "SUSTAIN" not in state:
                applied_poison = any("POISON" in a for a in acts)
                if not applied_poison:
                    anomalies.append(Anomaly(
                        "WARNING", turn, self.v8_id, "NO_DAMAGE",
                        "Dealt 0 damage (direct+nova) with enemy alive"))

        # ── WRONG_WEAPON ──
        if self.build_type == "MAGIC":
            for act in acts:
                if "USE_WEAPON" in act and "SET_WEAPON" not in act:
                    # Extract weapon name from "USE_WEAPON name → target"
                    wpart = act.split("USE_WEAPON ", 1)
                    if len(wpart) > 1:
                        wname = wpart[1].split(" →")[0].strip()
                        # Find weapon db_id by name
                        wid = self._weapon_id_by_name(wname)
                        if wid is not None and not self.resolver.weapon_is_magic_friendly(wid):
                            anomalies.append(Anomaly(
                                "WARNING", turn, self.v8_id, "WRONG_WEAPON",
                                f"Magic build used {wname} (no poison/debuff effects)"))
                            break

        # ── MOVEMENT_CONTRA ──
        if enemy and acts:
            v8s = start_snaps.get(self.v8_id, {})
            es = start_snaps.get(enemy_id, {})
            if v8s and es:
                d0 = cell_distance(v8s.get("cell", 0), es.get("cell", 0))
                d1 = cell_distance(v8.cell, enemy.cell)
                if "FLEE" in state and d1 < d0 and d0 - d1 >= 2:
                    anomalies.append(Anomaly(
                        "WARNING", turn, self.v8_id, "MOVEMENT_CONTRA",
                        f"Moved TOWARD enemy in FLEE state ({d0}→{d1})"))
                elif ("KILL" in state or "AGGRO" in state) and d1 > d0 and d1 - d0 >= 2:
                    anomalies.append(Anomaly(
                        "WARNING", turn, self.v8_id, "MOVEMENT_CONTRA",
                        f"Moved AWAY from enemy in {state.split('|')[0].strip()} ({d0}→{d1})"))

        # ── HEAL_WHEN_FULL ──
        if v8_snap:
            hp_pct = v8_snap["hp"] / max(v8_snap["max_hp"], 1)
            if hp_pct > 0.9:
                heal_names = {"remission", "regeneration", "cure", "bandage",
                              "drip", "vaccine", "therapy", "fertilizer", "loam"}
                for act in acts:
                    act_lower = act.lower()
                    if "use_chip" in act_lower and "self" in act_lower:
                        for h in heal_names:
                            if h in act_lower:
                                anomalies.append(Anomaly(
                                    "INFO", turn, self.v8_id, "HEAL_WHEN_FULL",
                                    f"Heal at {v8_snap['hp']}/{v8_snap['max_hp']} HP ({hp_pct*100:.0f}%)"))
                                break

        return anomalies

    def _weapon_id_by_name(self, name):
        for wid, w in self.resolver.weapons.items():
            if w["name"] == name:
                return wid
        return None


# ── TurnRenderer ──
class TurnRenderer:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    def __init__(self, use_color=True):
        self.use_color = use_color

    def c(self, color, text):
        return f"{color}{text}{self.RESET}" if self.use_color else text

    def render_turn(self, turn, tracker, correlator, v8_id, anomalies, resolver):
        lines = [self.c(self.BOLD + self.WHITE, f"═══ TURN {turn} ═══")]

        for eid, entity in tracker.entities.items():
            snap = tracker.turn_snapshots.get(turn, {}).get(eid)
            if not snap or not snap.get("alive", True):
                continue

            acts = tracker.get_turn_actions(turn, eid)
            stats = tracker.get_turn_stats(turn, eid)
            is_v8 = (eid == v8_id)
            label = f"V8 ({entity.name})" if is_v8 else entity.name
            color = self.CYAN if is_v8 else self.MAGENTA
            wpn = resolver.weapon_name(snap["weapon"]) if snap.get("weapon") else "none"

            lines.append(self.c(color + self.BOLD, f"--- {label} --- ") +
                f"HP: {snap['hp']}/{snap['max_hp']}  TP: {snap['tp']}  MP: {snap['mp']}  "
                f"Cell: {snap['cell']}  Wpn: {wpn}")

            # V8 debug logs
            if is_v8:
                parts = []
                for tag, extractor, clr in [
                    ("BUILD", correlator.extract_build_type, self.DIM),
                    ("STATE", correlator.extract_state, self.YELLOW),
                    ("TARGET", correlator.extract_target, self.DIM),
                    ("BEST", correlator.extract_best_scenario, self.GREEN),
                    ("PLAN", correlator.extract_scenario_plan, self.DIM),
                ]:
                    val = extractor(turn)
                    if val:
                        parts.append(self.c(clr, f"  [{tag}] {val}"))
                if correlator.extract_fallback(turn):
                    parts.append(self.c(self.RED, "  [FALLBACK] Using fallback scenario"))
                lines.extend(parts)

            # Actions
            if acts:
                lines.append(self.c(self.DIM, "  Actions:"))
                for act in acts:
                    if "AI_ERROR" in act:
                        lines.append(self.c(self.RED + self.BOLD, f"    {act}"))
                    elif "MOVE" in act:
                        lines.append(self.c(self.BLUE, f"    {act}"))
                    elif "SET_WEAPON" in act:
                        lines.append(self.c(self.DIM, f"    {act}"))
                    elif "dmg" in act or "nova" in act:
                        lines.append(self.c(self.GREEN if is_v8 else self.RED, f"    {act}"))
                    elif "→ +" in act and "HP" in act:
                        lines.append(self.c(self.GREEN, f"    {act}"))
                    else:
                        lines.append(f"    {act}")

            # End-of-turn stats from history
            end_tp = stats.get("tp", snap["tp"])
            end_mp = stats.get("mp", snap["mp"])
            parts = []
            if stats.get("dealt"): parts.append(f"Dealt: {stats['dealt']}")
            if stats.get("nova"): parts.append(f"Nova: {stats['nova']}")
            if stats.get("taken"): parts.append(f"Took: {stats['taken']}")
            if stats.get("poison"): parts.append(f"Poison: {stats['poison']}")
            if stats.get("healed"): parts.append(f"Healed: {stats['healed']}")
            if parts or acts:
                lines.append(self.c(self.DIM,
                    f"  End: TP={end_tp} MP={end_mp}" +
                    (f"  {'  '.join(parts)}" if parts else "")))

        # Per-turn anomalies
        for anom in anomalies:
            if anom.turn == turn:
                icon = {"ERROR": "✖", "WARNING": "⚠", "INFO": "ℹ"}.get(anom.severity, "?")
                clr = {"ERROR": self.RED, "WARNING": self.YELLOW, "INFO": self.DIM}.get(anom.severity, "")
                lines.append(self.c(clr, f"  {icon} {anom.code}: {anom.message}"))

        lines.append("")
        return "\n".join(lines)

    def render_summary(self, tracker, anomalies, v8_id, fight_data, resolver):
        lines = []
        v8 = tracker.entities.get(v8_id)
        result = fight_data.get("result", "?")
        turns = fight_data.get("total_turns", "?")
        seed = fight_data.get("seed", "?")
        ops = fight_data.get("our_ops", 0)

        rclr = {"WIN": self.GREEN, "LOSS": self.RED, "DRAW": self.YELLOW}.get(result, "")
        lines.append(self.c(self.BOLD + self.WHITE, "═══ FIGHT SUMMARY ═══"))
        lines.append(self.c(rclr + self.BOLD, f"Result: {result}") + f" in {turns} turns (seed={seed})")
        if ops:
            lines.append(f"V8 ops: {ops:,} / 14,000,000")

        if v8:
            nova = f", {v8.total_nova_dealt} nova" if v8.total_nova_dealt else ""
            lines.append(f"V8 total: {v8.total_damage_dealt} dmg dealt, "
                         f"{v8.total_damage_taken} taken, {v8.total_healing} healed{nova}")

        enemy_id = tracker.get_enemy_of(v8_id)
        enemy = tracker.entities.get(enemy_id) if enemy_id else None
        if enemy:
            psn = f", {enemy.total_poison_taken} poison" if enemy.total_poison_taken else ""
            lines.append(f"Enemy total: {enemy.total_damage_dealt} dmg dealt, "
                         f"{enemy.total_damage_taken} taken, {enemy.total_healing} healed{psn}")

        if anomalies:
            errs = sum(1 for a in anomalies if a.severity == "ERROR")
            warns = sum(1 for a in anomalies if a.severity == "WARNING")
            infos = sum(1 for a in anomalies if a.severity == "INFO")
            lines.append("")
            lines.append(self.c(self.YELLOW + self.BOLD,
                f"⚠ ANOMALIES ({len(anomalies)}):") +
                f" {errs} errors, {warns} warnings, {infos} info")
            for anom in anomalies:
                icon = {"ERROR": "✖", "WARNING": "⚠", "INFO": "ℹ"}.get(anom.severity, "?")
                clr = {"ERROR": self.RED, "WARNING": self.YELLOW, "INFO": self.DIM}.get(anom.severity, "")
                lines.append(self.c(clr, f"  Turn {anom.turn}: {icon} {anom.code} — {anom.message}"))
        else:
            lines.append(self.c(self.GREEN, "\n✓ No anomalies detected"))

        return "\n".join(lines)


# ── Analysis ──
def analyze_fight(fight_data, resolver, use_color=True, anomalies_only=False,
                  turn_range=None):
    actions = fight_data.get("actions", [])
    leeks = fight_data.get("leeks", [])
    logs = fight_data.get("logs", {})

    if not actions:
        print("ERROR: No actions in fight data")
        return 2

    # Identify V8 entity (team 1)
    v8_id = None
    v8_leek = None
    for leek in leeks:
        if leek.get("team") == 1:
            v8_id = leek["id"]
            v8_leek = leek
            break
    if v8_id is None:
        print("ERROR: Could not identify V8 entity")
        return 2

    build_type = detect_build(v8_leek)

    # Process actions
    tracker = FightStateTracker(leeks, resolver)
    tracker.process_actions(actions)

    # Correlate logs (farmer_id is 0-indexed: farmer 0 = our V8)
    correlator = LogCorrelator(logs, actions, v8_farmer_id=0)

    # Detect anomalies (uses tracker's final state per turn)
    detector = AnomalyDetector(tracker, correlator, resolver, v8_id, build_type)
    anomalies = detector.detect_all(actions)

    # Check for zero-ops crash (only if ops data is available)
    ops = fight_data.get("ops", {})
    if isinstance(ops, dict) and ops:
        v8_ops = ops.get(str(v8_id), ops.get(v8_id, 0))
        if v8_ops == 0:
            anomalies.insert(0, Anomaly("ERROR", 0, v8_id, "ZERO_OPS",
                                       "V8 entity ops=0 (script crash)"))

    # Render
    renderer = TurnRenderer(use_color=use_color)
    logged_build = correlator.extract_build_type(0) or correlator.extract_build_type(1)

    v8_name = v8_leek.get("name", "V8")
    enemy_names = [l.get("name", "?") for l in leeks if l.get("team") != 1]
    print(renderer.c(renderer.BOLD, f"\n{'='*60}"))
    print(renderer.c(renderer.BOLD,
        f"  FIGHT ANALYZER: {v8_name} ({build_type}) vs {', '.join(enemy_names)}"))
    print(renderer.c(renderer.BOLD, f"{'='*60}"))
    if logged_build:
        print(renderer.c(renderer.DIM, f"  V8 logged build: {logged_build}"))
    print()

    if not anomalies_only:
        max_turn = max(tracker.turn_snapshots.keys()) if tracker.turn_snapshots else 0
        for turn in range(1, max_turn + 1):
            if turn_range and (turn < turn_range[0] or turn > turn_range[1]):
                continue
            print(renderer.render_turn(turn, tracker, correlator, v8_id, anomalies, resolver))

    print(renderer.render_summary(tracker, anomalies, v8_id, fight_data, resolver))

    if any(a.severity == "ERROR" for a in anomalies):
        return 2
    return 1 if anomalies else 0


def parse_turn_range(s):
    if not s:
        return None
    if "-" in s:
        parts = s.split("-", 1)
        return (int(parts[0]), int(parts[1]))
    n = int(s)
    return (n, n)


def main():
    parser = argparse.ArgumentParser(
        description="Turn-by-turn fight behavior analyzer for V8 AI",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    parser.add_argument("opponent", nargs="?", default=None,
                        help="Opponent key (smart_str, dummy_mag, etc.)")
    parser.add_argument("--leek", default=None, help="Leek name from leek_configs.json")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--file", default=None, help="Path to saved fight JSON")
    parser.add_argument("--anomalies-only", action="store_true",
                        help="Only show anomaly summary")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    parser.add_argument("--turns", default=None, help="Turn range, e.g. '5-10'")
    parser.add_argument("--save", default=None, help="Save fight data to JSON")

    args = parser.parse_args()
    resolver = ItemResolver()
    turn_range = parse_turn_range(args.turns)
    use_color = not args.no_color and sys.stdout.isatty()

    if args.file:
        with open(args.file) as f:
            raw = json.load(f)
        if "fight" in raw:
            fight_data = raw["fight"]
            fight_data["logs"] = raw.get("logs", {})
            fight_data["result"] = {0: "WIN", 1: "LOSS"}.get(raw.get("winner", -1), "DRAW")
            fight_data["seed"] = raw.get("seed", "?")
            fight_data["our_ops"] = 0
            fight_data["total_turns"] = sum(
                1 for a in fight_data.get("actions", [])
                if isinstance(a, list) and a[0] == ACT_NEW_TURN)
        else:
            fight_data = raw
        return analyze_fight(fight_data, resolver, use_color, args.anomalies_only, turn_range)

    if not args.opponent:
        print("ERROR: Must specify opponent or --file")
        parser.print_usage()
        return 2
    if not args.leek:
        print("ERROR: Must specify --leek when running fights")
        return 2

    configs = load_configs()
    leek_cfg = configs.get("leeks", {}).get(args.leek)
    if not leek_cfg:
        print(f"ERROR: Leek '{args.leek}' not found. Available: {list(configs['leeks'].keys())}")
        return 2

    if args.opponent == "mirror":
        opponent_cfg = leek_cfg.copy()
        opponent_cfg["name"] = f"{leek_cfg['name']}_Mirror"
        opponent_ai = "V8_modules/main.lk"
    else:
        opponent_cfg = configs.get("opponents", {}).get(args.opponent)
        if not opponent_cfg:
            avail = list(configs.get("opponents", {}).keys()) + ["mirror"]
            print(f"ERROR: Opponent '{args.opponent}' not found. Available: {avail}")
            return 2
        opponent_ai = None

    import random
    seed = args.seed if args.seed is not None else random.randint(1, 2**31 - 1)

    print(f"Running fight: {args.leek} vs {args.opponent} (seed={seed})...")
    scenario = build_scenario(leek_cfg, opponent_cfg, seed=seed, opponent_ai=opponent_ai)
    result = run_fight(scenario, fight_index=0, verbose=True)

    if "error" in result:
        print(f"ERROR: Fight failed — {result['error']}")
        return 2

    fight_data = {
        "actions": result.get("actions", []),
        "leeks": result.get("leeks", []),
        "logs": result.get("logs", {}),
        "ops": result.get("ops", {}),
        "result": result.get("result", "?"),
        "seed": result.get("seed", seed),
        "our_ops": result.get("our_ops", 0),
        "total_turns": result.get("total_turns", 0),
    }

    if args.save:
        with open(args.save, "w") as f:
            json.dump(fight_data, f, indent=2)
        print(f"Fight data saved to: {args.save}")

    return analyze_fight(fight_data, resolver, use_color, args.anomalies_only, turn_range)


if __name__ == "__main__":
    sys.exit(main())
