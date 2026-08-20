#!/usr/bin/env python3
"""
Extract Fennel Castle map data from LeekWars API.

Connects to the LeekWars API, fetches available test scenario maps,
identifies the Fennel Castle map, and saves it to boss_map_data.json.

Usage:
    python3 tools/extract_boss_map.py
"""

import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config_loader import load_credentials

BASE_URL = "https://leekwars.com/api"
OUTPUT_FILE = Path(__file__).parent / "boss_map_data.json"


def login(session):
    """Login and return token."""
    email, password = load_credentials()
    resp = session.post(f"{BASE_URL}/farmer/login-token", data={
        "login": email,
        "password": password,
    })
    if resp.status_code != 200:
        print(f"Login failed: HTTP {resp.status_code}")
        sys.exit(1)
    data = resp.json()
    if "token" not in data:
        print(f"Login failed: {data}")
        sys.exit(1)
    print(f"Logged in as: {data['farmer']['login']}")
    return data["token"]


def fetch_test_scenarios(session, token):
    """Fetch all test scenarios including maps."""
    resp = session.get(f"{BASE_URL}/test-scenario/get-all", params={"token": token})
    if resp.status_code != 200:
        print(f"Failed to fetch test scenarios: HTTP {resp.status_code}")
        sys.exit(1)
    return resp.json()


def main():
    session = requests.Session()
    token = login(session)

    print("Fetching test scenarios...")
    data = fetch_test_scenarios(session, token)

    # The response should have a 'maps' dict keyed by map ID
    maps = data.get("maps", {})
    if not maps:
        # Try alternate response formats
        print(f"Response keys: {list(data.keys())}")
        # Save raw response for inspection
        raw_path = Path(__file__).parent / "boss_api_raw.json"
        with open(raw_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Raw API response saved to {raw_path}")
        print("No 'maps' field found. Inspect the raw response to find the map data.")
        return 1

    print(f"Found {len(maps)} maps")
    print()

    # List all maps to find the Fennel Castle
    for map_id, map_data in maps.items():
        name = map_data.get("name", "unnamed")
        # Map data may be nested under "data" key
        inner = map_data.get("data", map_data)
        obs_count = len(inner.get("obstacles", {}))
        print(f"  Map {map_id}: {name} ({obs_count} obstacles)")

    # Try to find Fennel Castle by name
    fennel_raw = None
    fennel_id = None
    for map_id, map_data in maps.items():
        name = map_data.get("name", "").lower()
        if "fennel" in name or "fenouil" in name or "castle" in name or "chateau" in name or "boss" in name:
            fennel_raw = map_data
            fennel_id = int(map_id)
            print(f"\nFound Fennel Castle: Map {map_id} ({map_data.get('name')})")
            break

    if not fennel_raw:
        print("\nCould not identify Fennel Castle map automatically.")
        print("Saving all maps for manual inspection.")
        with open(OUTPUT_FILE, "w") as f:
            json.dump({"all_maps": maps}, f, indent=2)
        print(f"Saved to {OUTPUT_FILE}")
        return 1

    # Extract the actual map data (may be nested under "data")
    inner = fennel_raw.get("data", fennel_raw)
    fennel_map = {
        "id": fennel_id,
        "obstacles": inner.get("obstacles", {}),
        "team1": inner.get("team1", []),
        "team2": inner.get("team2", []),
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(fennel_map, f, indent=2)
    print(f"Saved Fennel Castle map to {OUTPUT_FILE}")

    # Print summary
    obstacles = fennel_map["obstacles"]
    print(f"  Obstacles: {len(obstacles)} cells")
    if obstacles:
        obs_cells = sorted(int(k) for k in obstacles.keys())
        print(f"  First few: {obs_cells[:20]}")
        print(f"  Last few: {obs_cells[-20:]}")
    print(f"  Team 1 spawns: {fennel_map['team1']}")
    print(f"  Team 2 spawns: {fennel_map['team2']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
