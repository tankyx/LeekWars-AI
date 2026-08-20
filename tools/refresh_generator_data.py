#!/usr/bin/env python3
"""
Refresh leek-wars-generator data files from our market_data.json.

The generator ships with incomplete weapons.json (24 entries) and chips.json.
Our market_data.json has the full set (36 weapons, 109 chips) from the live API.

This script converts raw_data.weapons and raw_data.chips to the generator's format
and writes them to the generator's data/ directory.

Usage:
    python3 tools/refresh_generator_data.py
"""

import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
MARKET_DATA = PROJECT_DIR / "data" / "market_data.json"
GENERATOR_DIR = Path("/home/ubuntu/leek-wars-generator")
GENERATOR_WEAPONS = GENERATOR_DIR / "data" / "weapons.json"
GENERATOR_CHIPS = GENERATOR_DIR / "data" / "chips.json"


def main():
    if not MARKET_DATA.exists():
        print(f"ERROR: {MARKET_DATA} not found")
        return 1

    if not GENERATOR_DIR.exists():
        print(f"ERROR: Generator directory {GENERATOR_DIR} not found")
        return 1

    with open(MARKET_DATA) as f:
        market = json.load(f)

    raw = market.get("raw_data", {})
    raw_weapons = raw.get("weapons", {})
    raw_chips = raw.get("chips", {})

    if not raw_weapons:
        print("ERROR: No weapons in raw_data")
        return 1

    # Weapons: generator keys by template ID, same schema as raw_data
    # The generator's existing format uses template ID as the key
    # raw_data weapons are keyed by weapon ID but also have a 'template' field
    # The generator expects keys to match the weapon's own 'id' field (which equals template)
    weapons_out = {}
    for wid, wdata in raw_weapons.items():
        # Key by the weapon's id (template number)
        key = str(wdata.get("id", wid))
        # Include all fields the generator expects
        entry = {
            "id": wdata["id"],
            "name": wdata.get("name", ""),
            "level": wdata.get("level", 1),
            "min_range": wdata.get("min_range", 1),
            "max_range": wdata.get("max_range", 1),
            "launch_type": wdata.get("launch_type", 1),
            "effects": wdata.get("effects", []),
            "cost": wdata.get("cost", 1),
            "area": wdata.get("area", 1),
            "los": wdata.get("los", 1),
            "template": wdata.get("template", wdata["id"]),
            "passive_effects": wdata.get("passive_effects", []),
            "forgotten": wdata.get("forgotten", False),
            "item": wdata.get("item", 0),
            "max_uses": wdata.get("max_uses", -1),
        }
        weapons_out[key] = entry

    # Chips: generator keys by chip ID
    chips_out = {}
    for cid, cdata in raw_chips.items():
        key = str(cdata.get("id", cid))
        entry = {
            "id": cdata["id"],
            "name": cdata.get("name", ""),
            "level": cdata.get("level", 1),
            "min_range": cdata.get("min_range", 0),
            "max_range": cdata.get("max_range", 0),
            "launch_type": cdata.get("launch_type", 7),
            "effects": cdata.get("effects", []),
            "cost": cdata.get("cost", 1),
            "area": cdata.get("area", 1),
            "los": cdata.get("los", True),
            "template": cdata.get("template", 0),
            "type": cdata.get("type", 1),
            "cooldown": cdata.get("cooldown", 0),
            "team_cooldown": cdata.get("team_cooldown", False),
            "initial_cooldown": cdata.get("initial_cooldown", 0),
            "max_uses": cdata.get("max_uses", -1),
        }
        chips_out[key] = entry

    # Write
    with open(GENERATOR_WEAPONS, "w") as f:
        json.dump(weapons_out, f, separators=(",", ":"))
    print(f"Wrote {len(weapons_out)} weapons to {GENERATOR_WEAPONS}")

    with open(GENERATOR_CHIPS, "w") as f:
        json.dump(chips_out, f, separators=(",", ":"))
    print(f"Wrote {len(chips_out)} chips to {GENERATOR_CHIPS}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
