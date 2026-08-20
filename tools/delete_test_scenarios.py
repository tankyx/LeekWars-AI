#!/usr/bin/env python3
"""
Delete all test scenarios from LeekWars account.

Usage:
  python3 tools/delete_test_scenarios.py [--account <name>] [--dry-run]

Options:
  --account <name>  Account to use (default: main)
  --dry-run         List scenarios without deleting
"""

import requests
import time
import sys
import argparse
from config_loader import load_credentials

BASE_URL = "https://leekwars.com/api"


def main():
    parser = argparse.ArgumentParser(description="Delete all test scenarios")
    parser.add_argument("--account", default="main", help="Account name (default: main)")
    parser.add_argument("--dry-run", action="store_true", help="List scenarios without deleting")
    args = parser.parse_args()

    email, password = load_credentials(args.account)

    session = requests.Session()

    # Login
    print(f"Logging in as {email}...")
    resp = session.post(f"{BASE_URL}/farmer/login-token", data={
        "login": email,
        "password": password,
    })
    if resp.status_code != 200 or "token" not in resp.json():
        print(f"Login failed: {resp.status_code} {resp.text[:200]}")
        sys.exit(1)

    token = resp.json()["token"]
    farmer = resp.json().get("farmer", {})
    print(f"Logged in as {farmer.get('login', '?')}")

    # Get all test scenarios
    print("\nFetching test scenarios...")
    resp = session.get(f"{BASE_URL}/test-scenario/get-all")
    if resp.status_code != 200:
        print(f"Failed to fetch scenarios: {resp.status_code}")
        sys.exit(1)

    data = resp.json()
    scenarios = data.get("scenarios", {})

    if not scenarios:
        print("No test scenarios found.")
        return

    print(f"Found {len(scenarios)} test scenario(s):\n")
    for sid, scenario in scenarios.items():
        name = scenario.get("name", "(unnamed)")
        team1 = [l.get("name", "?") for l in scenario.get("team1", [])]
        team2 = [l.get("name", "?") for l in scenario.get("team2", [])]
        print(f"  [{sid}] {name}  |  {', '.join(team1) or '-'} vs {', '.join(team2) or '-'}")

    if args.dry_run:
        print(f"\nDry run — {len(scenarios)} scenario(s) would be deleted.")
        return

    print(f"\nDeleting {len(scenarios)} scenario(s)...")
    deleted = 0
    failed = 0

    for sid, scenario in scenarios.items():
        name = scenario.get("name", "(unnamed)")
        resp = session.delete(f"{BASE_URL}/test-scenario/delete", data={"id": sid})
        if resp.status_code == 200:
            deleted += 1
            print(f"  Deleted [{sid}] {name}")
        elif resp.status_code == 429:
            # Rate limited — wait and retry
            print(f"  Rate limited, waiting 3s...")
            time.sleep(3)
            resp = session.delete(f"{BASE_URL}/test-scenario/delete", data={"id": sid})
            if resp.status_code == 200:
                deleted += 1
                print(f"  Deleted [{sid}] {name}")
            else:
                failed += 1
                print(f"  Failed [{sid}] {name}: {resp.status_code}")
        else:
            failed += 1
            print(f"  Failed [{sid}] {name}: {resp.status_code}")
        time.sleep(0.3)  # Be gentle with the API

    print(f"\nDone: {deleted} deleted, {failed} failed.")


if __name__ == "__main__":
    main()
