#!/usr/bin/env python3
"""
LeekWars Fight Action Parser
Parses fight actions from the fight/get API using the detailed action format documentation

Based on LeekWars API documentation for fight.data.actions
"""

import json
import requests
from typing import List, Dict, Any, Optional

# Action Type Constants
ACTION_START_FIGHT = 0
ACTION_USE_WEAPON_OLD = 1
ACTION_USE_CHIP_OLD = 2
ACTION_SET_WEAPON = 3
ACTION_END_FIGHT = 4
ACTION_PLAYER_DEAD = 5
ACTION_NEW_TURN = 6
ACTION_LEEK_TURN = 7
ACTION_END_TURN = 8
ACTION_SUMMON = 9
ACTION_MOVE_TO = 10
ACTION_USE_CHIP = 12
ACTION_SET_WEAPON_NEW = 13
ACTION_STACK_EFFECT = 14
ACTION_USE_WEAPON = 16
ACTION_TP_LOST = 100
ACTION_LIFE_LOST = 101
ACTION_MP_LOST = 102
ACTION_CARE = 103
ACTION_BOOST_VITA = 104
ACTION_RESURRECTION = 105
ACTION_NOVA_DAMAGE = 107
ACTION_DAMAGE_RETURN = 108
ACTION_LIFE_DAMAGE = 109
ACTION_POISON_DAMAGE = 110
ACTION_AFTEREFFECT = 111
ACTION_NOVA_VITALITY = 112
ACTION_SAY = 200
ACTION_LAMA = 201
ACTION_SHOW = 202
ACTION_ADD_WEAPON_EFFECT = 301
ACTION_ADD_CHIP_EFFECT = 302
ACTION_REMOVE_EFFECT = 303
ACTION_UPDATE_EFFECT = 304
ADD_STACKED_EFFECT = 305
REDUCE_EFFECTS = 306
REMOVE_POISONS = 307
REMOVE_SHACKLES = 308
ACTION_BUG = 1002

# Weapon IDs
WEAPONS = {
    1: "Pistol", 2: "MachineGun", 3: "DoubleGun", 4: "Shotgun", 5: "Magnum",
    6: "Laser", 7: "GrenadeLauncher", 8: "FlameThrower", 9: "Destroyer",
    10: "Gazor", 11: "Electrisor", 12: "MLaser", 13: "BLaser",
    14: "Katana", 15: "Broadsword", 16: "Axe"
}

# Chip IDs
CHIPS = {
    1: "Bandage", 2: "Cure", 3: "Drip", 4: "Regeneration", 5: "Vaccine",
    6: "Shock", 7: "Flash", 8: "Lightning", 9: "Spark", 10: "Flame",
    11: "Meteorite", 12: "Pebble", 13: "Rock", 14: "Rockfall", 15: "Ice",
    16: "Stalactite", 17: "Iceberg", 18: "Shield", 19: "Helmet", 20: "Armor",
    21: "Wall", 22: "Rampart", 23: "Fortress", 24: "Protein", 25: "Steroid",
    26: "Doping", 27: "Stretching", 28: "WarmUp", 29: "Reflexes",
    30: "LeatherBoots", 31: "WingedBoots", 32: "SevenLeagueBoots",
    33: "Motivation", 34: "Adrenaline", 35: "Rage", 36: "Liberation",
    37: "Teleportation", 38: "Armoring", 39: "Inversion", 47: "Remission",
    48: "Carapace", 50: "DevilStrike", 51: "Whip", 52: "Loam",
    53: "Fertilizer", 54: "Acceleration", 55: "SlowDown", 56: "BallAndChain",
    57: "Tranquilizer", 58: "Soporific", 59: "Fracture", 60: "Solidification",
    61: "Venom", 62: "Toxin", 63: "Plague", 64: "Thorn", 65: "Mirror",
    66: "Ferocity", 67: "Collar", 68: "Bark", 69: "Burning", 70: "Antidote"
}

# Effect Types
EFFECTS = {
    1: "DAMAGE", 2: "HEAL", 3: "BUFF_STRENGTH", 4: "BUFF_AGILITY",
    5: "RELATIVE_SHIELD", 6: "ABSOLUTE_SHIELD", 7: "BUFF_MP", 8: "BUFF_TP",
    13: "POISON", 14: "SUMMON", 17: "SHACKLE_MP", 18: "SHACKLE_TP",
    19: "SHACKLE_STRENGTH", 20: "DAMAGE_RETURN", 21: "BUFF_RESISTANCE",
    22: "BUFF_WISDOM", 23: "ANTIDOTE", 24: "SHACKLE_MAGIC", 25: "AFTEREFFECT",
    26: "VULNERABILITY"
}


class FightActionParser:
    def __init__(self):
        self.turn_number = 0
        self.current_entity = None
        self.entity_names = {}  # entity_id -> name mapping

    def set_entity_names(self, fight_data: Dict[str, Any]):
        """Extract entity names from fight data"""
        for leek in fight_data.get("leeks1", []):
            self.entity_names[leek["id"]] = leek["name"]
        for leek in fight_data.get("leeks2", []):
            self.entity_names[leek["id"]] = leek["name"]

    def get_entity_name(self, entity_id: int) -> str:
        """Get entity name or ID as fallback"""
        return self.entity_names.get(entity_id, f"Entity_{entity_id}")

    def parse_action(self, action: List[Any]) -> Optional[Dict[str, Any]]:
        """Parse a single action from the actions array"""
        if not action or len(action) == 0:
            return None

        action_type = action[0]

        # START_FIGHT [action_type, leek, turn]
        if action_type == ACTION_START_FIGHT:
            self.turn_number = action[2] if len(action) > 2 else 1
            entity = action[1] if len(action) > 1 else None
            self.current_entity = entity
            return {
                "type": "START_FIGHT",
                "turn": self.turn_number,
                "starter": self.get_entity_name(entity) if entity else "Unknown",
                "raw": action
            }

        # NEW_TURN [action_type, turn]
        elif action_type == ACTION_NEW_TURN:
            self.turn_number = action[1] if len(action) > 1 else self.turn_number + 1
            return {
                "type": "NEW_TURN",
                "turn": self.turn_number,
                "raw": action
            }

        # LEEK_TURN [action_type, leek, tp, mp]
        elif action_type == ACTION_LEEK_TURN:
            entity = action[1] if len(action) > 1 else None
            self.current_entity = entity
            return {
                "type": "LEEK_TURN",
                "turn": self.turn_number,
                "entity": self.get_entity_name(entity) if entity else "Unknown",
                "entity_id": entity,
                "tp": action[2] if len(action) > 2 else 0,
                "mp": action[3] if len(action) > 3 else 0,
                "raw": action
            }

        # END_TURN [action_type, leek, tp, mp, strength, magic]
        elif action_type == ACTION_END_TURN:
            entity = action[1] if len(action) > 1 else None
            return {
                "type": "END_TURN",
                "turn": self.turn_number,
                "entity": self.get_entity_name(entity) if entity else "Unknown",
                "entity_id": entity,
                "tp": action[2] if len(action) > 2 else 0,
                "mp": action[3] if len(action) > 3 else 0,
                "strength": action[4] if len(action) > 4 else 0,
                "magic": action[5] if len(action) > 5 else 0,
                "raw": action
            }

        # USE_WEAPON (new format) [action_type, cell, result]
        elif action_type == ACTION_USE_WEAPON:
            return {
                "type": "USE_WEAPON",
                "turn": self.turn_number,
                "entity": self.get_entity_name(self.current_entity) if self.current_entity else "Unknown",
                "entity_id": self.current_entity,
                "cell": action[1] if len(action) > 1 else None,
                "result": action[2] if len(action) > 2 else None,
                "raw": action
            }

        # USE_WEAPON_OLD [action_type, launcher, cell, weapon, result, leeksID]
        elif action_type == ACTION_USE_WEAPON_OLD:
            launcher = action[1] if len(action) > 1 else None
            weapon_id = action[3] if len(action) > 3 else None
            return {
                "type": "USE_WEAPON_OLD",
                "turn": self.turn_number,
                "entity": self.get_entity_name(launcher) if launcher else "Unknown",
                "entity_id": launcher,
                "cell": action[2] if len(action) > 2 else None,
                "weapon": WEAPONS.get(weapon_id, f"Weapon_{weapon_id}"),
                "weapon_id": weapon_id,
                "result": action[4] if len(action) > 4 else None,
                "targets": action[5] if len(action) > 5 else [],
                "raw": action
            }

        # USE_CHIP [action_type, chip, cell, result]
        elif action_type == ACTION_USE_CHIP:
            chip_id = action[1] if len(action) > 1 else None
            return {
                "type": "USE_CHIP",
                "turn": self.turn_number,
                "entity": self.get_entity_name(self.current_entity) if self.current_entity else "Unknown",
                "entity_id": self.current_entity,
                "chip": CHIPS.get(chip_id, f"Chip_{chip_id}"),
                "chip_id": chip_id,
                "cell": action[2] if len(action) > 2 else None,
                "result": action[3] if len(action) > 3 else None,
                "raw": action
            }

        # USE_CHIP_OLD [action_type, launcher, cell, chip, result, leeksID]
        elif action_type == ACTION_USE_CHIP_OLD:
            launcher = action[1] if len(action) > 1 else None
            chip_id = action[3] if len(action) > 3 else None
            return {
                "type": "USE_CHIP_OLD",
                "turn": self.turn_number,
                "entity": self.get_entity_name(launcher) if launcher else "Unknown",
                "entity_id": launcher,
                "cell": action[2] if len(action) > 2 else None,
                "chip": CHIPS.get(chip_id, f"Chip_{chip_id}"),
                "chip_id": chip_id,
                "result": action[4] if len(action) > 4 else None,
                "targets": action[5] if len(action) > 5 else [],
                "raw": action
            }

        # SET_WEAPON [action_type, launcher, weapon]
        elif action_type in [ACTION_SET_WEAPON, ACTION_SET_WEAPON_NEW]:
            launcher = action[1] if len(action) > 1 else None
            weapon_id = action[2] if len(action) > 2 else None
            return {
                "type": "SET_WEAPON",
                "turn": self.turn_number,
                "entity": self.get_entity_name(launcher) if launcher else "Unknown",
                "entity_id": launcher,
                "weapon": WEAPONS.get(weapon_id, f"Weapon_{weapon_id}"),
                "weapon_id": weapon_id,
                "raw": action
            }

        # MOVE_TO [action_type, leek, cell, path]
        elif action_type == ACTION_MOVE_TO:
            entity = action[1] if len(action) > 1 else None
            return {
                "type": "MOVE_TO",
                "turn": self.turn_number,
                "entity": self.get_entity_name(entity) if entity else "Unknown",
                "entity_id": entity,
                "cell": action[2] if len(action) > 2 else None,
                "path": action[3] if len(action) > 3 else [],
                "distance": len(action[3]) if len(action) > 3 and isinstance(action[3], list) else 0,
                "raw": action
            }

        # LIFE_LOST [action_type, leek, life, erosion]
        elif action_type == ACTION_LIFE_LOST:
            entity = action[1] if len(action) > 1 else None
            return {
                "type": "LIFE_LOST",
                "turn": self.turn_number,
                "entity": self.get_entity_name(entity) if entity else "Unknown",
                "entity_id": entity,
                "damage": action[2] if len(action) > 2 else 0,
                "erosion": action[3] if len(action) > 3 else 0,
                "raw": action
            }

        # TP_LOST [action_type, leek, tp]
        elif action_type == ACTION_TP_LOST:
            entity = action[1] if len(action) > 1 else None
            return {
                "type": "TP_LOST",
                "turn": self.turn_number,
                "entity": self.get_entity_name(entity) if entity else "Unknown",
                "entity_id": entity,
                "tp_lost": action[2] if len(action) > 2 else 0,
                "raw": action
            }

        # MP_LOST [action_type, leek, mp]
        elif action_type == ACTION_MP_LOST:
            entity = action[1] if len(action) > 1 else None
            return {
                "type": "MP_LOST",
                "turn": self.turn_number,
                "entity": self.get_entity_name(entity) if entity else "Unknown",
                "entity_id": entity,
                "mp_lost": action[2] if len(action) > 2 else 0,
                "raw": action
            }

        # CARE (healing) [action_type, leek, life]
        elif action_type == ACTION_CARE:
            entity = action[1] if len(action) > 1 else None
            return {
                "type": "CARE",
                "turn": self.turn_number,
                "entity": self.get_entity_name(entity) if entity else "Unknown",
                "entity_id": entity,
                "healing": action[2] if len(action) > 2 else 0,
                "raw": action
            }

        # PLAYER_DEAD [action_type, entity]
        elif action_type == ACTION_PLAYER_DEAD:
            entity = action[1] if len(action) > 1 else None
            return {
                "type": "PLAYER_DEAD",
                "turn": self.turn_number,
                "entity": self.get_entity_name(entity) if entity else "Unknown",
                "entity_id": entity,
                "raw": action
            }

        # POISON_DAMAGE [action_type, leek, life, erosion]
        elif action_type == ACTION_POISON_DAMAGE:
            entity = action[1] if len(action) > 1 else None
            return {
                "type": "POISON_DAMAGE",
                "turn": self.turn_number,
                "entity": self.get_entity_name(entity) if entity else "Unknown",
                "entity_id": entity,
                "damage": action[2] if len(action) > 2 else 0,
                "erosion": action[3] if len(action) > 3 else 0,
                "raw": action
            }

        # DAMAGE_RETURN [action_type, leek, life, erosion]
        elif action_type == ACTION_DAMAGE_RETURN:
            entity = action[1] if len(action) > 1 else None
            return {
                "type": "DAMAGE_RETURN",
                "turn": self.turn_number,
                "entity": self.get_entity_name(entity) if entity else "Unknown",
                "entity_id": entity,
                "damage": action[2] if len(action) > 2 else 0,
                "erosion": action[3] if len(action) > 3 else 0,
                "raw": action
            }

        # ADD_CHIP_EFFECT [action_type, chip, id, caster, target, effect, value, duration]
        elif action_type == ACTION_ADD_CHIP_EFFECT:
            chip_id = action[1] if len(action) > 1 else None
            caster = action[3] if len(action) > 3 else None
            target = action[4] if len(action) > 4 else None
            effect_id = action[5] if len(action) > 5 else None
            return {
                "type": "ADD_CHIP_EFFECT",
                "turn": self.turn_number,
                "chip": CHIPS.get(chip_id, f"Chip_{chip_id}"),
                "chip_id": chip_id,
                "effect_id": action[2] if len(action) > 2 else None,
                "caster": self.get_entity_name(caster) if caster else "Unknown",
                "caster_id": caster,
                "target": self.get_entity_name(target) if target else "Unknown",
                "target_id": target,
                "effect": EFFECTS.get(effect_id, f"Effect_{effect_id}"),
                "effect_type_id": effect_id,
                "value": action[6] if len(action) > 6 else 0,
                "duration": action[7] if len(action) > 7 else 0,
                "raw": action
            }

        # ADD_WEAPON_EFFECT [action_type, weapon, id, caster, target, effect, value, duration]
        elif action_type == ACTION_ADD_WEAPON_EFFECT:
            weapon_id = action[1] if len(action) > 1 else None
            caster = action[3] if len(action) > 3 else None
            target = action[4] if len(action) > 4 else None
            effect_id = action[5] if len(action) > 5 else None
            return {
                "type": "ADD_WEAPON_EFFECT",
                "turn": self.turn_number,
                "weapon": WEAPONS.get(weapon_id, f"Weapon_{weapon_id}"),
                "weapon_id": weapon_id,
                "effect_id": action[2] if len(action) > 2 else None,
                "caster": self.get_entity_name(caster) if caster else "Unknown",
                "caster_id": caster,
                "target": self.get_entity_name(target) if target else "Unknown",
                "target_id": target,
                "effect": EFFECTS.get(effect_id, f"Effect_{effect_id}"),
                "effect_type_id": effect_id,
                "value": action[6] if len(action) > 6 else 0,
                "duration": action[7] if len(action) > 7 else 0,
                "raw": action
            }

        # SAY [action_type, leek, message]
        elif action_type == ACTION_SAY:
            entity = action[1] if len(action) > 1 else None
            return {
                "type": "SAY",
                "turn": self.turn_number,
                "entity": self.get_entity_name(entity) if entity else "Unknown",
                "entity_id": entity,
                "message": action[2] if len(action) > 2 else "",
                "raw": action
            }

        # REMOVE_EFFECT [action_type, chip, id, caster, target, effect, value]
        elif action_type == ACTION_REMOVE_EFFECT:
            return {
                "type": "REMOVE_EFFECT",
                "turn": self.turn_number,
                "effect_id": action[2] if len(action) > 2 else None,
                "raw": action
            }

        # Unknown action type
        else:
            return {
                "type": f"UNKNOWN_{action_type}",
                "turn": self.turn_number,
                "raw": action
            }

    def parse_all_actions(self, actions: List[List[Any]]) -> List[Dict[str, Any]]:
        """Parse all actions from a fight"""
        parsed = []
        for action in actions:
            parsed_action = self.parse_action(action)
            if parsed_action:
                parsed.append(parsed_action)
        return parsed

    def generate_fight_summary(self, parsed_actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a summary of the fight from parsed actions"""
        summary = {
            "total_turns": 0,
            "entities": {},
            "total_damage_dealt": {},
            "total_damage_taken": {},
            "chips_used": {},
            "weapons_used": {},
            "deaths": []
        }

        for action in parsed_actions:
            action_type = action["type"]

            # Track turns
            if action_type == "NEW_TURN":
                summary["total_turns"] = action["turn"]

            # Track entity stats
            if "entity_id" in action and action["entity_id"]:
                entity_id = action["entity_id"]
                if entity_id not in summary["entities"]:
                    summary["entities"][entity_id] = {
                        "name": action.get("entity", f"Entity_{entity_id}"),
                        "actions": 0,
                        "chips_used": 0,
                        "weapons_used": 0,
                        "damage_dealt": 0,
                        "damage_taken": 0
                    }
                summary["entities"][entity_id]["actions"] += 1

            # Track chip usage
            if action_type in ["USE_CHIP", "USE_CHIP_OLD"]:
                chip = action.get("chip", "Unknown")
                summary["chips_used"][chip] = summary["chips_used"].get(chip, 0) + 1
                if action.get("entity_id"):
                    summary["entities"][action["entity_id"]]["chips_used"] += 1

            # Track weapon usage
            if action_type in ["USE_WEAPON", "USE_WEAPON_OLD"]:
                weapon = action.get("weapon", "Unknown")
                summary["weapons_used"][weapon] = summary["weapons_used"].get(weapon, 0) + 1
                if action.get("entity_id"):
                    summary["entities"][action["entity_id"]]["weapons_used"] += 1

            # Track damage dealt (life lost implies someone dealt it)
            if action_type == "LIFE_LOST":
                damage = action.get("damage", 0)
                entity_id = action.get("entity_id")
                if entity_id:
                    summary["total_damage_taken"][entity_id] = summary["total_damage_taken"].get(entity_id, 0) + damage
                    if entity_id in summary["entities"]:
                        summary["entities"][entity_id]["damage_taken"] += damage

            # Track deaths
            if action_type == "PLAYER_DEAD":
                summary["deaths"].append({
                    "entity": action.get("entity", "Unknown"),
                    "entity_id": action.get("entity_id"),
                    "turn": action.get("turn", 0)
                })

        return summary


def fetch_and_parse_fight(fight_id: int, session: requests.Session = None) -> Optional[Dict[str, Any]]:
    """Fetch fight data and parse actions"""
    if session is None:
        session = requests.Session()

    url = f"https://leekwars.com/api/fight/get/{fight_id}"
    response = session.get(url)

    if response.status_code != 200:
        print(f"Failed to fetch fight {fight_id}: {response.status_code}")
        return None

    fight_data = response.json()

    # Check if we have the data field with actions
    if "data" not in fight_data:
        print(f"Fight {fight_id} has no data field (might still be processing)")
        return None

    data = fight_data["data"]

    # The actions might be in data.actions or in report
    actions = data.get("actions")
    if not actions and "report" in fight_data and fight_data["report"]:
        # Try to parse report if it's JSON
        try:
            if isinstance(fight_data["report"], str):
                report = json.loads(fight_data["report"])
                actions = report.get("actions")
            elif isinstance(fight_data["report"], dict):
                actions = fight_data["report"].get("actions")
        except:
            pass

    if not actions:
        print(f"Fight {fight_id} has no actions data")
        return None

    # Parse the actions
    parser = FightActionParser()
    parser.set_entity_names(fight_data)
    parsed_actions = parser.parse_all_actions(actions)
    summary = parser.generate_fight_summary(parsed_actions)

    return {
        "fight_id": fight_id,
        "fight_data": fight_data,
        "parsed_actions": parsed_actions,
        "summary": summary
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 fight_action_parser.py <fight_id>")
        print("Example: python3 fight_action_parser.py 49611081")
        sys.exit(1)

    fight_id = int(sys.argv[1])

    print(f"Fetching and parsing fight {fight_id}...")
    result = fetch_and_parse_fight(fight_id)

    if not result:
        print("Failed to parse fight")
        sys.exit(1)

    # Save parsed data
    output_file = f"parsed_fight_{fight_id}.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n✅ Parsed fight saved to {output_file}")
    print(f"\n📊 Fight Summary:")
    print(f"  Total turns: {result['summary']['total_turns']}")
    print(f"  Total actions: {len(result['parsed_actions'])}")
    print(f"\n  Entities:")
    for entity_id, stats in result['summary']['entities'].items():
        print(f"    {stats['name']} (ID: {entity_id}):")
        print(f"      Actions: {stats['actions']}")
        print(f"      Chips used: {stats['chips_used']}")
        print(f"      Weapons used: {stats['weapons_used']}")
        print(f"      Damage taken: {stats['damage_taken']}")

    print(f"\n  Chips used:")
    for chip, count in sorted(result['summary']['chips_used'].items(), key=lambda x: -x[1])[:10]:
        print(f"    {chip}: {count}x")

    print(f"\n  Weapons used:")
    for weapon, count in sorted(result['summary']['weapons_used'].items(), key=lambda x: -x[1])[:10]:
        print(f"    {weapon}: {count}x")

    if result['summary']['deaths']:
        print(f"\n  Deaths:")
        for death in result['summary']['deaths']:
            print(f"    {death['entity']} died on turn {death['turn']}")
