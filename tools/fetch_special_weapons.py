#!/usr/bin/env python3
"""
Fetch weapon data for special/seasonal weapons not in market API.
Uses the LeekWars game constants API.
"""

import json
import requests
from config_loader import load_credentials

def fetch_special_weapons():
    """Fetch weapon data from LeekWars constants API"""
    print("=" * 60)
    print("LEEKWARS SPECIAL WEAPONS FETCHER")
    print("=" * 60)

    # Missing weapon IDs from KurtGodel
    missing_ids = [41, 42, 43, 44, 45, 46, 47, 48, 60, 107, 108, 109,
                   115, 116, 117, 118, 119, 151, 153, 175, 180, 182,
                   184, 187, 225, 226, 277, 278, 408, 409, 410, 428]

    print(f"\n📥 Fetching data for {len(missing_ids)} special weapons...")

    # Load credentials
    email, password = load_credentials(account='main')

    # Login
    session = requests.Session()
    base_url = "https://leekwars.com/api"

    print("🔐 Logging in...")
    login_response = session.post(
        f"{base_url}/farmer/login-token",
        data={"login": email, "password": password}
    )

    if login_response.status_code != 200:
        print("❌ Login failed")
        return None

    farmer = login_response.json().get('farmer', {})
    print(f"✅ Logged in as: {farmer.get('login')}")

    # Fetch constants
    print("\n📥 Fetching game constants...")
    constants_response = session.get(f"{base_url}/constant/get-all")

    if constants_response.status_code != 200:
        print("❌ Failed to fetch constants")
        return None

    constants = constants_response.json()

    # Navigate nested structure
    if 'constants' in constants:
        constants_data = constants['constants']
        print(f"📋 Type of constants: {type(constants_data)}")

        if isinstance(constants_data, list):
            print(f"📋 List length: {len(constants_data)}")
            if len(constants_data) > 0:
                print(f"📋 Sample entry: {constants_data[0] if len(constants_data) > 0 else 'empty'}")
            # Constants might be effect names, etc. Not weapon data.
            weapons_data = {}
        elif isinstance(constants_data, dict):
            print(f"📋 Available categories: {list(constants_data.keys())}")
            weapons_data = constants_data.get('weapons', {})
        else:
            weapons_data = {}
    else:
        weapons_data = constants.get('weapons', {})

    print(f"✅ Found {len(weapons_data)} total weapons")

    # Filter for missing IDs
    special_weapons = {}
    found_ids = []

    for weapon_id_str, weapon_data in weapons_data.items():
        weapon_id = int(weapon_id_str)
        if weapon_id in missing_ids:
            special_weapons[weapon_id_str] = weapon_data
            found_ids.append(weapon_id)

    print(f"\n✅ Found {len(special_weapons)} special weapons")
    print(f"📋 IDs found: {sorted(found_ids)}")

    missing_from_api = set(missing_ids) - set(found_ids)
    if missing_from_api:
        print(f"⚠️  Still missing: {sorted(missing_from_api)}")

    # Load existing market data
    market_data_path = '/home/ubuntu/LeekWars-AI/data/market_data.json'
    with open(market_data_path, 'r') as f:
        market_data = json.load(f)

    # Merge special weapons
    original_count = len(market_data['weapons'])
    market_data['weapons'].update(special_weapons)
    new_count = len(market_data['weapons'])

    # Save updated data
    with open(market_data_path, 'w') as f:
        json.dump(market_data, f, indent=2)

    print(f"\n💾 Updated market_data.json")
    print(f"   Weapons: {original_count} → {new_count} (+{new_count - original_count})")

    return special_weapons

if __name__ == '__main__':
    fetch_special_weapons()
