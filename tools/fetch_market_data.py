#!/usr/bin/env python3
"""
Fetch weapons and chips data from LeekWars market API
Saves comprehensive data to JSON file for reference

Usage:
    python3 fetch_market_data.py [--account <name>]
"""

import requests
import json
import sys
import argparse
from pathlib import Path
from config_loader import load_credentials

BASE_URL = "https://leekwars.com/api"

def login(email, password):
    """Login to LeekWars and return session + token"""
    print("🔐 Logging in...")

    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/farmer/login-token",
        data={"login": email, "password": password}
    )

    if response.status_code == 200:
        data = response.json()
        if "farmer" in data and "token" in data:
            print(f"✅ Logged in as: {data['farmer'].get('login')}")
            return session, data["token"]

    print("❌ Login failed")
    return None, None

def fetch_weapons(session, token):
    """Fetch all weapons data"""
    print("\n📥 Fetching weapons data...")
    headers = {"Authorization": f"Bearer {token}"}
    response = session.get(f"{BASE_URL}/weapon/get-all", headers=headers)

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Retrieved weapons data")
        return data.get("weapons", {})
    else:
        print(f"   ❌ Failed: {response.status_code}")
        return {}

def fetch_chips(session, token):
    """Fetch all chips data"""
    print("\n📥 Fetching chips data...")
    headers = {"Authorization": f"Bearer {token}"}
    response = session.get(f"{BASE_URL}/chip/get-all", headers=headers)

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Retrieved chips data")
        return data.get("chips", {})
    else:
        print(f"   ❌ Failed: {response.status_code}")
        return {}

def format_weapon_data(weapon):
    """Format weapon data for easy reference"""
    return {
        "id": weapon.get("template"),
        "name": weapon.get("name"),
        "level": weapon.get("level"),
        "min_range": weapon.get("min_range"),
        "max_range": weapon.get("max_range"),
        "launch_type": weapon.get("launch_type"),
        "tp_cost": weapon.get("cost"),
        "min_damage": weapon.get("min_damage"),
        "max_damage": weapon.get("max_damage"),
        "cooldown": weapon.get("cooldown", 0),
        "effects": weapon.get("effects", []),
        "team_cooldown": weapon.get("team_cooldown", 0),
        "area": weapon.get("area", 0),
        "los": weapon.get("los", False),
        "purchasable": weapon.get("template") in weapon.get("purchasable", [])
    }

def format_chip_data(chip):
    """Format chip data for easy reference"""
    return {
        "id": chip.get("template"),
        "name": chip.get("name"),
        "level": chip.get("level"),
        "min_range": chip.get("min_range"),
        "max_range": chip.get("max_range"),
        "launch_type": chip.get("launch_type"),
        "tp_cost": chip.get("cost"),
        "cooldown": chip.get("cooldown", 0),
        "effects": chip.get("effects", []),
        "team_cooldown": chip.get("team_cooldown", 0),
        "area": chip.get("area", 0),
        "los": chip.get("los", False),
        "purchasable": chip.get("template") in chip.get("purchasable", [])
    }

def main():
    parser = argparse.ArgumentParser(description='Fetch LeekWars market data')
    parser.add_argument('--account', default='main', choices=['main', 'cure'],
                        help='Account to use (main or cure, default: main)')
    args = parser.parse_args()

    print("="*60)
    print("LEEKWARS MARKET DATA FETCHER")
    print("="*60)
    print(f"👤 Account: {args.account}")

    # Login
    email, password = load_credentials(account=args.account)
    session, token = login(email, password)

    if not session:
        sys.exit(1)

    try:
        # Fetch weapons and chips separately
        weapons_data = fetch_weapons(session, token)
        chips_data = fetch_chips(session, token)

        if not weapons_data and not chips_data:
            print("❌ Failed to fetch any data")
            sys.exit(1)

        # Process and format data
        print("\n📊 Processing data...")

        formatted_data = {
            "weapons": {},
            "chips": {},
            "raw_data": {
                "weapons": weapons_data,
                "chips": chips_data
            }
        }

        # Format weapons
        for weapon_id, weapon in weapons_data.items():
            formatted_data["weapons"][weapon_id] = format_weapon_data(weapon)
        print(f"   ✅ Processed {len(formatted_data['weapons'])} weapons")

        # Format chips
        for chip_id, chip in chips_data.items():
            formatted_data["chips"][chip_id] = format_chip_data(chip)
        print(f"   ✅ Processed {len(formatted_data['chips'])} chips")

        # Save to file in data/ folder
        script_dir = Path(__file__).parent.parent
        data_dir = script_dir / "data"
        data_dir.mkdir(exist_ok=True)

        output_file = data_dir / "market_data.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(formatted_data, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Data saved to: {output_file}")

        # Print summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Total Weapons: {len(formatted_data['weapons'])}")
        print(f"Total Chips: {len(formatted_data['chips'])}")

        # Sample weapons
        print("\n🔫 Sample Weapons:")
        for weapon_id, weapon in list(formatted_data["weapons"].items())[:5]:
            print(f"   {weapon['name']} (ID: {weapon_id})")
            print(f"      Range: {weapon['min_range']}-{weapon['max_range']}, TP: {weapon['tp_cost']}, Damage: {weapon['min_damage']}-{weapon['max_damage']}")

        # Sample chips
        print("\n💊 Sample Chips:")
        for chip_id, chip in list(formatted_data["chips"].items())[:5]:
            print(f"   {chip['name']} (ID: {chip_id})")
            print(f"      Range: {chip['min_range']}-{chip['max_range']}, TP: {chip['tp_cost']}, Cooldown: {chip['cooldown']}")

    finally:
        # Logout
        if token:
            session.post(f"{BASE_URL}/farmer/disconnect/{token}")
            print("\n👋 Disconnected")

if __name__ == "__main__":
    main()
