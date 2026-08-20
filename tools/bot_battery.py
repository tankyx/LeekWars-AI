#!/usr/bin/env python3
"""Run the V9 bot battery: our leeks x the 6 built-in bots via the
test-scenario API. Prints a W/L/D matrix. Mirrors the MCP test_fight flow.

Usage: python3 tools/bot_battery.py [--ai 9.0/V9/main.lk] [--account main] [--leeks 20443,129295,129296,129288] [--bots domingo,betalpha,tisma,guj,hachess,rex]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config_loader import load_credentials  # noqa: E402

BASE = "https://leekwars.com/api"
BOTS = {
    "domingo": -1, "betalpha": -2, "tisma": -3,
    "guj": -4, "hachess": -5, "rex": -6,
}


def post(s, path, payload, retries=4):
    for attempt in range(retries):
        r = s.post(f"{BASE}{path}", json=payload)
        try:
            j = r.json()
        except Exception:
            j = {"_http": r.status_code}
        if isinstance(j, dict) and j.get("error") == "rate_limit":
            time.sleep(float(j.get("retry_after", 1)) + 0.4)
            continue
        return j
    return j


def run_battery(ai_path, account, leeks, bots):
    login, password = load_credentials(account=account)
    s = requests.Session()
    f = s.post(f"{BASE}/farmer/login-token", data={"login": login, "password": password}).json()["farmer"]
    print(f"logged in: {f['login']}")

    scenarios = post(s, "/test-scenario/get-all", {}, retries=2) if False else s.get(f"{BASE}/test-scenario/get-all").json()
    existing = scenarios.get("scenarios", {})

    results = {}
    for leek_id in leeks:
        for bot_name in bots:
            bot_id = BOTS[bot_name]
            sid = None
            for k, sc in existing.items():
                if sc.get("ai") == ai_path and (sc.get("team2") or [{}])[0].get("id") == bot_id \
                        and (sc.get("team1") or [{}])[0].get("id") == leek_id:
                    sid = k
                    break
            if sid is None:
                new = post(s, "/test-scenario/new", {"name": f"bat_{leek_id}_{bot_name}"})
                sid = new.get("id")
                if not sid:
                    results[(leek_id, bot_name)] = f"scenario-err:{new}"
                    continue
                post(s, "/test-scenario/update", {"id": sid, "data": json.dumps({"type": 0, "map": None, "ai": ai_path})})
                post(s, "/test-scenario/add-leek", {"scenario_id": sid, "leek": leek_id, "team": 0, "ai": ai_path})
                post(s, "/test-scenario/add-leek", {"scenario_id": sid, "leek": bot_id, "team": 1, "ai": -2})

            fight = post(s, "/ai/test-scenario", {"scenario_id": sid, "ai_id": ai_path})
            fid = fight.get("fight") or fight.get("id") or (fight.get("fight_id"))
            if not fid:
                results[(leek_id, bot_name)] = f"start-err:{json.dumps(fight)[:120]}"
                continue
            # Poll until the fight resolves: a single fixed 1.2s sleep raced
            # slower fights and read winner=-1 (unresolved) as a fake cell.
            # Server queue can delay resolution past 15s — poll up to ~45s.
            winner = -1
            for wait in (2.0, 3.0, 4.0, 6.0, 8.0, 10.0, 12.0):
                time.sleep(wait)
                fd = s.get(f"{BASE}/fight/get/{fid}").json()
                data = fd.get("data")
                if isinstance(data, str):
                    data = json.loads(data)
                winner = fd.get("fight", fd).get("winner", data.get("winner", 0))
                if winner in (0, 1, 2):
                    break
            results[(leek_id, bot_name)] = {1: "W", 2: "L", 0: "D"}.get(winner, f"?{winner}")

    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", default="9.0/V9/main.lk")
    ap.add_argument("--account", default="main")
    ap.add_argument("--leeks", default="20443,129295,129296,129288")
    ap.add_argument("--bots", default="domingo,betalpha,tisma,guj,hachess,rex")
    args = ap.parse_args()

    leeks = [int(x) for x in args.leeks.split(",")]
    bots = args.bots.split(",")
    names = {20443: "Ada", 129295: "KG", 129296: "MH", 129288: "ED"}

    res = run_battery(args.ai, args.account, leeks, bots)
    wins = sum(1 for v in res.values() if v == "W")
    print(f"\n{'leek':6s}" + "".join(f"{b[:8]:>9s}" for b in bots))
    for lk in leeks:
        row = "".join(f"{res.get((lk, b), '?'):>9s}" for b in bots)
        print(f"{names.get(lk, str(lk)):6s}{row}")
    print(f"\nTOTAL: {wins}/{len(res)} wins")


if __name__ == "__main__":
    main()
