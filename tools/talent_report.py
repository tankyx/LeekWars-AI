#!/usr/bin/env python3
"""Talent tracker (Phase M0): snapshot leek + farmer talent into data/talent_log.jsonl.

Logs in via /api/farmer/login-token using tools/config.json credentials
(config_loader.load_credentials), appends one JSON line per leek plus one farmer
summary line, and prints a table.

Usage:
  python3 tools/talent_report.py [--account main|cure|both]   (default: both)
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_credentials  # noqa: E402

LOGIN_URL = "https://leekwars.com/api/farmer/login-token"
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "data", "talent_log.jsonl")


def snapshot(account):
    """Fetch farmer data, append log lines, return rows for the table."""
    login, password = load_credentials(account)
    r = requests.post(LOGIN_URL, data={"login": login, "password": password},
                      timeout=30)
    r.raise_for_status()
    farmer = r.json().get("farmer", {})
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    lines = []
    rows = []
    leeks = farmer.get("leeks", {})
    for leek_id, leek in sorted(leeks.items(),
                                key=lambda kv: kv[1].get("talent", 0),
                                reverse=True):
        entry = {
            "ts": ts,
            "account": account,
            "leek": leek.get("name"),
            "talent": leek.get("talent"),
            "ranking": leek.get("ranking"),
            "level": leek.get("level"),
        }
        lines.append(entry)
        rows.append(entry)

    history = farmer.get("talent_history") or []
    farmer_talent = history[-1] if history else farmer.get("talent")
    lines.append({"ts": ts, "account": account, "farmer_talent": farmer_talent})

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")

    return farmer.get("name", account), farmer_talent, farmer.get("talent"), rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--account", choices=["main", "cure", "both"], default="both")
    args = ap.parse_args()

    accounts = ["main", "cure"] if args.account == "both" else [args.account]
    for account in accounts:
        farmer_name, farmer_talent, talent_field, rows = snapshot(account)
        print(f"=== {account} ({farmer_name}) — farmer talent {farmer_talent} ===")
        print(f"  {'leek':<20} {'talent':>6} {'ranking':>8} {'level':>6}")
        for row in rows:
            print(f"  {row['leek']:<20} {row['talent']:>6} "
                  f"{str(row['ranking']):>8} {row['level']:>6}")
        print(f"  logged {len(rows) + 1} lines -> {LOG_FILE}")


if __name__ == "__main__":
    main()
