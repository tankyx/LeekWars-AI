#!/usr/bin/env python3
"""Loss census: batch-download recent solo losses from the fight history DBs
and classify each by how close it was and what the damage exchange looked like.

API fight reads are FREE (no fight credits). Fights are cached on disk.

Buckets per loss (by enemy HP% remaining at end):
  blowout     >60% left  — outclassed / catastrophic line
  competitive 20-60%     — winnable with better play
  near-miss   <20% left  — small tweaks flip these

Also flags anomaly fights (our damage < 100 = AI stall/crash signature).

Usage:
    python3 tools/loss_census.py [--since 2026-08-01] [--until 2026-08-16T06:00]
                                 [--max-per-leek 40] [--leek AdaLovelace]
"""
import argparse
import json
import sqlite3
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
CACHE = Path("/tmp/loss_census_cache")
CACHE.mkdir(exist_ok=True)

LEEKS = {  # main account
    20443: "AdaLovelace",
    129295: "KurtGodel",
    129296: "MargaretHamilton",
    129288: "EdsgerDijkstra",
}

ACT_LIFE_LOST = 101
ACT_HEAL = 103
ACT_POISON = 110
ACT_NOVA = 107
ACT_LIFE_DAMAGE = 109
ACT_AFTEREFFECT = 111
ACT_NOVA_VITALITY = 112
ACT_PLAYER_DEAD = 5
ACT_NEW_TURN = 6
ACT_LEEK_TURN = 7
DAMAGE_CODES = {ACT_LIFE_LOST, ACT_POISON, ACT_NOVA, ACT_LIFE_DAMAGE, ACT_AFTEREFFECT, ACT_NOVA_VITALITY}
DAMAGE_ACTIONS = {1, 2, 8, 12, 16}  # weapon/chip uses (any variant)


def fetch_fight(fid):
    cache = CACHE / f"{fid}.json"
    if cache.exists():
        return json.load(open(cache))
    url = f"https://leekwars.com/api/fight/get/{fid}"
    with urllib.request.urlopen(url) as r:
        d = json.loads(r.read())
    cache.write_text(json.dumps(d))
    time.sleep(0.35)
    return d


def archetype(stats):
    s, m, a, r, sc, w = (stats.get(k, 0) or 0 for k in
                         ("strength", "magic", "agility", "resistance", "science", "wisdom"))
    if r >= 300 and sc >= 300:
        return "tank_sci"
    if s > 400 and a > 400:
        return "bruiser_reflect"
    if m >= s + 100:
        return "magic"
    if a >= 300 and sc >= 300:
        return "agility"
    if s >= 300:
        return "strength"
    if m >= 300:
        return "magic"
    return "other"


def analyze(d, our_name):
    data = d["data"]
    if isinstance(data, str):
        data = json.loads(data)
    leeks = data["leeks"]
    ours = [l for l in leeks if l["name"] == our_name and not l.get("summon")]
    if not ours:
        return None
    us = ours[0]
    enemy = [l for l in leeks if l["team"] != us["team"] and not l.get("summon")]
    if not enemy:
        return None
    foe = enemy[0]
    us_id, foe_id = us["id"], foe["id"]
    us_hp0, foe_hp0 = us["life"], foe["life"]

    # Track current/max HP properly: nova (107) burns MAX HP, current clamps;
    # heals (103) cap at current max. Bucket on real current HP at fight end.
    cur = {us_id: us_hp0, foe_id: foe_hp0}
    maxhp = {us_id: us_hp0, foe_id: foe_hp0}
    foe_lost = us_lost = 0
    foe_healed = us_healed = 0
    death_turn = None
    turn = 0
    our_turns = 0
    our_dmg_actions = 0
    cur_ent = None
    for a in data["actions"]:
        code = a[0]
        if code == ACT_NEW_TURN:
            turn = a[1]
        elif code == ACT_LEEK_TURN:
            cur_ent = a[1]
            if cur_ent == us_id:
                our_turns += 1
        elif code == ACT_NOVA:
            ent, amt = a[1], a[2]
            if ent in maxhp:
                maxhp[ent] = max(0, maxhp[ent] - amt)
                cur[ent] = min(cur[ent], maxhp[ent])
            if ent == foe_id:
                foe_lost += amt
            elif ent == us_id:
                us_lost += amt
        elif code in (ACT_LIFE_LOST, ACT_POISON, ACT_LIFE_DAMAGE, ACT_AFTEREFFECT, ACT_NOVA_VITALITY):
            ent, amt = a[1], a[2]
            if ent in cur:
                cur[ent] = max(0, cur[ent] - amt)
            if ent == foe_id:
                foe_lost += amt
            elif ent == us_id:
                us_lost += amt
        elif code == ACT_HEAL:
            ent, amt = a[1], a[2]
            if ent in cur:
                cur[ent] = min(maxhp[ent], cur[ent] + amt)
            if ent == foe_id:
                foe_healed += amt
            elif ent == us_id:
                us_healed += amt
        elif code == ACT_PLAYER_DEAD and a[1] == us_id:
            death_turn = turn
        elif code in DAMAGE_ACTIONS and cur_ent == us_id:
            our_dmg_actions += 1

    foe_hp_left = cur[foe_id]
    foe_pct = foe_hp_left / max(1, foe_hp0)
    if foe_pct > 0.6:
        bucket = "blowout"
    elif foe_pct > 0.2:
        bucket = "competitive"
    else:
        bucket = "near_miss"
    return {
        "bucket": bucket,
        "foe_pct_left": round(foe_pct, 2),
        "foe_lost": foe_lost,
        "foe_healed": foe_healed,
        "us_lost": us_lost,
        "us_healed": us_healed,
        "foe_hp0": foe_hp0,
        "duration": turn,
        "death_turn": death_turn,
        "our_dmg_actions": our_dmg_actions,
        "our_turns": our_turns,
        "foe_arch": archetype(foe),
        "foe_name": foe["name"],
        "anomaly": foe_lost < 100,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-08-01")
    ap.add_argument("--until", default="2026-08-16T06:00")
    ap.add_argument("--max-per-leek", type=int, default=40)
    ap.add_argument("--leek", default=None)
    args = ap.parse_args()

    for leek_id, name in LEEKS.items():
        if args.leek and name != args.leek:
            continue
        db = ROOT / "tools" / f"fight_history_{leek_id}.db"
        if not db.exists():
            continue
        con = sqlite3.connect(db)
        rows = con.execute(
            "SELECT fight_id, opponent_name, timestamp FROM fight_history "
            "WHERE result='LOSS' AND timestamp >= ? AND timestamp < ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (args.since, args.until, args.max_per_leek)).fetchall()
        print(f"\n=== {name}: {len(rows)} losses in window ===")
        stats = defaultdict(int)
        arch_buckets = defaultdict(lambda: defaultdict(int))
        death_turns = []
        anomalies = []
        near_misses = []
        for fid, opp, ts in rows:
            try:
                d = fetch_fight(fid)
                m = analyze(d, name)
            except Exception as e:
                print(f"  {fid}: ERR {e}")
                continue
            if not m:
                continue
            stats[m["bucket"]] += 1
            arch_buckets[m["foe_arch"]][m["bucket"]] += 1
            if m["death_turn"]:
                death_turns.append(m["death_turn"])
            if m["anomaly"]:
                anomalies.append((fid, opp, m["foe_lost"]))
            if m["bucket"] == "near_miss":
                near_misses.append((fid, opp, m["foe_arch"], m["foe_pct_left"], m["duration"]))
        n = sum(stats.values())
        if not n:
            continue
        print(f"  buckets: " + ", ".join(f"{b}={stats[b]} ({100*stats[b]/n:.0f}%)" for b in
                                     ("blowout", "competitive", "near_miss") if stats[b]))
        if death_turns:
            death_turns.sort()
            print(f"  death turn: median={death_turns[len(death_turns)//2]} "
                  f"min={death_turns[0]} max={death_turns[-1]} "
                  f"early(<=4)={sum(1 for t in death_turns if t <= 4)}/{len(death_turns)}")
        print("  by archetype:")
        for arch, bk in sorted(arch_buckets.items(), key=lambda kv: -sum(kv[1].values())):
            tot = sum(bk.values())
            print(f"    {arch:16s} {tot:3d}  " +
                  " ".join(f"{b}={bk[b]}" for b in ("blowout", "competitive", "near_miss") if bk[b]))
        if anomalies:
            print(f"  ANOMALIES (our damage <100): {len(anomalies)} -> {anomalies[:5]}")
        if near_misses:
            print(f"  near-misses (flippable): {len(near_misses)}")
            for fid, opp, arch, pct, dur in near_misses[:8]:
                print(f"    {fid} vs {opp} [{arch}] foe {pct*100:.0f}% left, {dur} turns")


if __name__ == "__main__":
    main()
