#!/usr/bin/env python3
"""Fetch live ladder opponents' builds from the public API and write them as
opponent configs into tools/leek_configs.json["opponents"] for GA training.

Usage: python3 tools/fetch_ladder_opponents.py <leek_name> [count]
  leek_name: one of our leeks (uses its history DB for worst matchups)
  count: how many worst opponents to fetch (default 8)
Opponent configs get our V8 main.lk as their AI (best generic proxy).
"""
import json
import sqlite3
import sys
import time
import urllib.request

CONFIG_PATH = "tools/leek_configs.json"
LEEK_IDS = {"AdaLovelace": 20443, "KurtGodel": 129295, "MargaretHamilton": 129296, "EdsgerDijkstra": 129288}
API = "https://leekwars.com/api/leek/get/{}"


def fetch_leek(leek_id):
    req = urllib.request.Request(API.format(leek_id), headers={"User-Agent": "LeekWars-AI-GA/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.load(r)
    return d.get("leek", d)


def worst_opponents(leek_id, count):
    con = sqlite3.connect(f"/home/ubuntu/LeekWars-AI/tools/fight_history_{leek_id}.db")
    rows = con.execute(
        """SELECT opponent_id, opponent_name,
                  SUM(CASE WHEN result='LOSS' THEN 1 ELSE 0 END) as losses,
                  SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) as wins
           FROM fight_history GROUP BY opponent_id
           HAVING losses >= 3 AND losses > wins
           ORDER BY losses DESC LIMIT ?""", (count,)).fetchall()
    con.close()
    return rows


def to_config(leek, name):
    weapons = [w["template"] for w in (leek.get("weapons") or [])]
    chips = [c["template"] for c in (leek.get("chips") or [])]
    return {
        "name": name,
        "type": leek.get("type", 0),
        "level": leek.get("level", 301),
        "life": leek.get("life", 3000),
        "cores": leek.get("cores", 14),
        "ram": leek.get("ram", 50),
        "tp": leek.get("tp", 20),
        "mp": leek.get("mp", 6),
        "strength": leek.get("strength", 0),
        "magic": leek.get("magic", 0),
        "agility": leek.get("agility", 0),
        "wisdom": leek.get("wisdom", 0),
        "resistance": leek.get("resistance", 0),
        "science": leek.get("science", 0),
        "frequency": leek.get("frequency", 100),
        "weapons": weapons,
        "chips": chips,
        "ai_relative": "V8_modules/main.lk",
    }


def main():
    leek_name = sys.argv[1] if len(sys.argv) > 1 else "AdaLovelace"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    leek_id = LEEK_IDS[leek_name]
    rows = worst_opponents(leek_id, count)
    if not rows:
        print(f"no worst opponents found for {leek_name}")
        return 1

    cfg = json.load(open(CONFIG_PATH))
    opponents = cfg.setdefault("opponents", {})
    added = []
    for opp_id, opp_name, losses, wins in rows:
        try:
            leek = fetch_leek(opp_id)
        except Exception as e:
            print(f"  skip {opp_name} ({opp_id}): {e}")
            continue
        if not leek:
            print(f"  skip {opp_name} ({opp_id}): empty response")
            continue
        key = f"live_{opp_id}"
        opponents[key] = to_config(leek, opp_name)
        added.append((key, opp_name, f"{losses}L/{wins}W"))
        print(f"  + {key} = {opp_name} ({losses}L/{wins}W) "
              f"STR{leek.get('strength')} MAG{leek.get('magic')} RES{leek.get('resistance')}")
        time.sleep(0.4)

    json.dump(cfg, open(CONFIG_PATH, "w"), indent=2)
    print(f"\nadded {len(added)} opponents: {[a[0] for a in added]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
