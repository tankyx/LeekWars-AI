#!/usr/bin/env python3
"""Build a production-shaped opponent pool for local validation/GA.

Why: local validation vs template bots (smart_*) kept failing to transfer to
the 301 ladder meta (2026-08-17: GA champion 20/20 vs smart_str locally,
production-neutral). This pool holds the REAL builds of the opponents who
actually beat us, extracted from fight JSONs + the public leek API, driven by
a strong generic AI (V8) locally.

Sources:
  - tools/fight_history_<leek_id>.db  (top loss offenders per leek)
  - /api/fight/get/<fight_id>         (their stats snapshot in-fight)
  - /api/leek/get/<leek_id>           (full weapons/chips/total stats)

Writes prod_<Name> entries into tools/leek_configs.json 'opponents'.

Usage: python3 tools/build_prod_pool.py [--per-leek 6] [--account main]
"""
import argparse
import json
import re
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from config_loader import load_credentials  # noqa: E402

BASE = "https://leekwars.com/api"
PACE = 0.36
LEEKS = {20443: "AdaLovelace", 129295: "KurtGodel",
         129296: "MargaretHamilton", 129288: "EdsgerDijkstra"}
_last = 0.0


def api_get(path, headers):
    global _last
    dt = time.time() - _last
    if dt < PACE:
        time.sleep(PACE - dt)
    _last = time.time()
    req = urllib.request.Request(f"{BASE}{path}", headers=headers)
    return json.loads(urllib.request.urlopen(req).read())


def top_loss_opponents(leek_id, per_leek):
    con = sqlite3.connect(ROOT / "tools" / f"fight_history_{leek_id}.db")
    rows = con.execute("""
        SELECT opponent_id, opponent_name,
               SUM(CASE WHEN result='LOSS' THEN 1 ELSE 0 END) AS L,
               SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) AS W,
               MAX(timestamp) AS last_ts
        FROM fight_history
        WHERE timestamp >= '2026-06-01'
        GROUP BY opponent_id
        HAVING L >= 3
        ORDER BY L DESC, last_ts DESC
        LIMIT ?""", (per_leek,)).fetchall()
    con.close()
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-leek", type=int, default=6)
    ap.add_argument("--account", default="main")
    args = ap.parse_args()

    login, password = load_credentials(args.account)
    import requests
    r = requests.post(f"{BASE}/farmer/login-token", data={"login": login, "password": password})
    headers = {"Authorization": f"Bearer {r.json()['token']}"}

    # Union of top loss offenders across leeks (keep count of who loses to them)
    picks = {}  # opp_id -> {name, losses, leeks}
    for lid, lname in LEEKS.items():
        for oid, oname, L, W, ts in top_loss_opponents(lid, args.per_leek):
            p = picks.setdefault(oid, {"name": oname, "losses": 0, "leeks": []})
            p["losses"] += L
            p["leeks"].append(lname[:3])
    print(f"{len(picks)} unique loss-offenders selected")

    cfg_path = ROOT / "tools" / "leek_configs.json"
    cfg = json.load(open(cfg_path))
    added = []
    for oid, p in sorted(picks.items(), key=lambda kv: -kv[1]["losses"]):
        try:
            d = api_get(f"/leek/get/{oid}", headers)
        except Exception as e:
            print(f"  {p['name']}: fetch failed ({e})")
            continue
        if "level" not in d:
            print(f"  {p['name']}: no data (private?)")
            continue
        key = "prod_" + re.sub(r"[^A-Za-z0-9]", "_", p["name"])[:24]
        entry = {
            "name": key,
            "type": 1,
            "level": d["level"],
            "life": d.get("total_life", d["life"]),
            "cores": d.get("total_cores", d.get("cores", 10)),
            "ram": d.get("total_ram", d.get("ram", 10)),
            "tp": d.get("total_tp", d["tp"]),
            "mp": d.get("total_mp", d["mp"]),
            "strength": d.get("total_strength", 0),
            "magic": d.get("total_magic", 0),
            "agility": d.get("total_agility", 0),
            "wisdom": d.get("total_wisdom", 0),
            "resistance": d.get("total_resistance", 0),
            "science": d.get("total_science", 0),
            "frequency": d.get("total_frequency", 100),
            "weapons": [w["template"] for w in d.get("weapons", [])],
            "chips": [c["template"] for c in d.get("chips", [])],
            "ai_relative": "V8_modules/main.lk",
        }
        cfg["opponents"][key] = entry
        added.append((key, p["losses"], ",".join(p["leeks"]),
                      f"STR{entry['strength']} MAG{entry['magic']} AGI{entry['agility']} "
                      f"WIS{entry['wisdom']} RES{entry['resistance']} SCI{entry['science']} HP{entry['life']}"))
        print(f"  {key:26s} losses={p['losses']:3d} [{','.join(p['leeks'])}] {added[-1][3]}")

    json.dump(cfg, open(cfg_path, "w"), indent=1)
    print(f"wrote {len(added)} prod_* opponents into {cfg_path}")


if __name__ == "__main__":
    main()
