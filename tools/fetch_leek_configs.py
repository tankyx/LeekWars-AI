#!/usr/bin/env python3
"""
Fetch leek configurations from the LeekWars API and save to leek_configs.json.

Retrieves exact stats (HP, TP, MP, all stats, weapon IDs, chip IDs) for each
leek in the account. Also defines dummy opponents for local testing.

Usage:
    python3 tools/fetch_leek_configs.py [--account main]
"""

import json
import sys
import time
import argparse
import requests
from pathlib import Path
from config_loader import load_credentials


BASE_URL = "https://leekwars.com/api"
SCRIPT_DIR = Path(__file__).parent
OUTPUT_FILE = SCRIPT_DIR / "leek_configs.json"



def fetch_leek_details(session, leek_id):
    """Fetch full leek details including weapons and chips."""
    url = f"{BASE_URL}/leek/get/{leek_id}"
    resp = session.get(url)
    if resp.status_code != 200:
        print(f"  WARNING: Failed to fetch leek {leek_id}: HTTP {resp.status_code}")
        return None
    data = resp.json()
    return data.get("leek", data)


def extract_weapon_ids(weapons_list):
    """Extract weapon item IDs from API weapon list.

    API format: [{'template': <item_id>, 'id': <instance_id>}, ...]
    The API's 'template' field IS the item ID. The generator's Weapon class
    uses item IDs as lookup keys, so we pass them through directly.
    """
    ids = []
    for w in weapons_list:
        if isinstance(w, dict):
            ids.append(w["template"])
        elif isinstance(w, int):
            ids.append(w)
    return ids


def extract_chip_ids(chips_list):
    """Extract chip IDs from API chip list.

    API format: [{'template': <chip_id>, 'id': <instance_id>}, ...]
    The API's 'template' field for chips IS the chip ID used by the generator.
    """
    ids = []
    for c in chips_list:
        if isinstance(c, dict):
            ids.append(c["template"])
        elif isinstance(c, int):
            ids.append(c)
    return ids


def main():
    parser = argparse.ArgumentParser(description="Fetch leek configs from LeekWars API")
    parser.add_argument("--account", default="main", help="Account name (default: main)")
    args = parser.parse_args()

    email, password = load_credentials(account=args.account)

    session = requests.Session()
    print(f"Logging in as {args.account}...")
    resp = session.post(f"{BASE_URL}/farmer/login-token", data={
        "login": email,
        "password": password,
    })
    if resp.status_code != 200:
        print(f"ERROR: Login failed: HTTP {resp.status_code}")
        return 1

    login_data = resp.json()
    if "farmer" not in login_data:
        print("ERROR: Login failed: no farmer data")
        return 1

    farmer = login_data["farmer"]
    token = login_data.get("token", "")
    print(f"Connected as: {farmer.get('login')} (ID: {farmer.get('id')})")

    leeks_map = farmer.get("leeks", {})
    if not leeks_map:
        print("ERROR: No leeks found")
        return 1

    print(f"Found {len(leeks_map)} leek(s), fetching details...")

    leek_configs = {}
    for leek_id, leek_summary in leeks_map.items():
        name = leek_summary.get("name", f"Leek_{leek_id}")
        print(f"  Fetching {name} (ID: {leek_id})...")

        detail = fetch_leek_details(session, leek_id)
        if not detail:
            continue
        time.sleep(0.5)  # Rate limit protection

        # Convert API format to generator IDs
        raw_weapons = detail.get("weapons", [])
        raw_chips = detail.get("chips", [])
        weapon_ids = extract_weapon_ids(raw_weapons)
        chip_ids = extract_chip_ids(raw_chips)

        config = {
            "name": name,
            "id": int(leek_id),
            "type": 1,
            "level": detail.get("level", 301),
            "life": detail.get("total_life", detail.get("life", 5000)),
            # Server 'cores' field doesn't map to generator ops budget.
            # Generator uses cores * 1M ops. Our AI needs ~14M ops.
            "cores": detail.get("total_cores", 14),
            "ram": 50,  # Max RAM for the generator (50 * 8M = 400M quads)
            "tp": detail.get("total_tp", detail.get("tp", 20)),
            "mp": detail.get("total_mp", detail.get("mp", 6)),
            "strength": detail.get("total_strength", detail.get("strength", 0)),
            "magic": detail.get("total_magic", detail.get("magic", 0)),
            "agility": detail.get("total_agility", detail.get("agility", 0)),
            "wisdom": detail.get("total_wisdom", detail.get("wisdom", 0)),
            "resistance": detail.get("total_resistance", detail.get("resistance", 0)),
            "science": detail.get("total_science", detail.get("science", 0)),
            "frequency": detail.get("total_frequency", detail.get("frequency", 100)),
            "weapons": weapon_ids,
            "chips": chip_ids,
        }
        leek_configs[name] = config

    # Define dummy opponents using the generator's bundled basic.leek AI
    opponents = {
        "dummy_str": {
            "name": "DummySTR",
            "type": 1,
            "level": 301,
            "life": 5000,
            "cores": 14,
            "tp": 26,
            "mp": 7,
            "strength": 600,
            "magic": 0,
            "agility": 0,
            "wisdom": 300,
            "resistance": 0,
            "science": 0,
            "frequency": 100,
            "weapons": [37],
            "chips": [29],
            "ram": 50,
            "ai_relative": "test/ai/simple.leek",
        },
        "dummy_mag": {
            "name": "DummyMAG",
            "type": 1,
            "level": 301,
            "life": 5000,
            "cores": 14,
            "tp": 26,
            "mp": 7,
            "strength": 0,
            "magic": 600,
            "agility": 0,
            "wisdom": 300,
            "resistance": 0,
            "science": 0,
            "frequency": 100,
            "weapons": [37],
            "chips": [29],
            "ram": 50,
            "ai_relative": "test/ai/simple.leek",
        },
        "dummy_tank": {
            "name": "DummyTank",
            "type": 1,
            "level": 301,
            "life": 8000,
            "cores": 14,
            "tp": 26,
            "mp": 7,
            "strength": 200,
            "magic": 0,
            "agility": 0,
            "wisdom": 300,
            "resistance": 400,
            "science": 0,
            "frequency": 100,
            "weapons": [37],
            "chips": [29],
            "ram": 50,
            "ai_relative": "test/ai/simple.leek",
        },
        "dummy_agi": {
            "name": "DummyAGI",
            "type": 1,
            "level": 301,
            "life": 5000,
            "cores": 14,
            "tp": 26,
            "mp": 7,
            "strength": 0,
            "magic": 0,
            "agility": 600,
            "wisdom": 300,
            "resistance": 0,
            "science": 0,
            "frequency": 100,
            "weapons": [37],
            "chips": [29],
            "ram": 50,
            "ai_relative": "test/ai/simple.leek",
        },
    }

    # Preserve existing opponents not in our dummy set (e.g. smart_* opponents)
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            existing = json.load(f)
        for key, val in existing.get("opponents", {}).items():
            if key not in opponents:
                opponents[key] = val

    output = {
        "leeks": leek_configs,
        "opponents": opponents,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nWrote {len(leek_configs)} leek(s) and {len(opponents)} opponent(s) to {OUTPUT_FILE}")

    # Summary
    for name, cfg in leek_configs.items():
        stats = f"STR:{cfg['strength']} MAG:{cfg['magic']} AGI:{cfg['agility']} WIS:{cfg['wisdom']} RES:{cfg['resistance']} SCI:{cfg['science']}"
        print(f"  {name}: L{cfg['level']} HP:{cfg['life']} TP:{cfg['tp']} MP:{cfg['mp']} {stats}")
        print(f"    Weapons: {cfg['weapons']}")
        print(f"    Chips: {cfg['chips']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
