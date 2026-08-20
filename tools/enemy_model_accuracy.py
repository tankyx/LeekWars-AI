#!/usr/bin/env python3
"""Offline accuracy gate for the enemy model (Phase M1, Deliverable 3).

Mirrors V9_modules/enemy_model.lk predictEnemyTurn semantics exactly:
predict the enemy's action-class sequence for T1-T3 from the model JSON
(memory first, archetype prior fallback), compare top-1 against the actual
dominant action class per enemy turn.

Gate: >=60% overall top-1 accuracy on >=30 fights -> prints GATE: PASS/FAIL.

Usage: python3 tools/enemy_model_accuracy.py [--last N] [--account main|cure]
"""
import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_enemy_model import (  # noqa: E402
    fetch_fight_data, load_templates, find_entities, classify_chip,
)

MAIN_LEEKS = [20443, 129295, 129296, 129288]
CURE_LEEKS = [19703, 21175, 129801, 130236]
OUR_NAMES = {"AdaLovelace", "KurtGodel", "MargaretHamilton", "EdsgerDijkstra",
             "LeekRain", "DawnFall", "DuskHope", "ProdigalSon"}

# Archetype prior from live kit, mirroring classifyEnemyArchetype in
# enemy_model.lk. Uses chip names from the fight's 302 entries when kit data
# is unavailable in the payload (it is not), so we approximate with the
# model's recorded archetype; if the opponent is not in the model at all we
# fall back to the coarse prior below.
def prior_archetype(model_entry, chip_names_seen):
    if model_entry:
        return model_entry.get("archetype", "bruiser")
    summon = sum(1 for n in chip_names_seen if n and n.endswith("_bulb"))
    poison = sum(1 for n in chip_names_seen if n in
                 ("venom", "toxin", "arsenic", "plague", "covid", "serum"))
    shield = sum(1 for n in chip_names_seen if n in
                 ("armor", "wall", "fortress", "shield", "rampart", "armoring", "helmet"))
    if summon >= 1:
        return "summoner"
    if poison >= 2:
        return "magic_poison"
    if shield >= 3:
        return "tank"
    return "bruiser"


def predict_primary(mem, arch, turn):
    """Top-1 predicted action class for the enemy's turn (mirror of .lk)."""
    if mem:
        # Per-turn modal class from observed history beats archetype rules.
        modal = mem.get("t%d_modal" % turn)
        if modal:
            return modal
    if turn <= 1:
        return "buff"
    if arch == "magic_poison":
        return "poison"
    if arch == "summoner":
        return "summon" if turn <= 4 else "weapon"
    if arch == "tank":
        return "buff"
    return "weapon"


# Turn class by tactical purpose: the highest-priority class present, not the
# action-count majority (a 3-move + weapon-fire turn is an attack turn).
PRIORITY = ["summon", "poison", "weapon", "buff", "heal", "deny", "move"]


def enemy_turn_classes(data, enemy_name, chip_tpl, chip_effects):
    """Actual action class per enemy turn (turns 1-3), by PRIORITY order."""
    enemy, ours = find_entities(data["leeks"], enemy_name, next(iter(OUR_NAMES)))
    if enemy is None:
        # try any of our names
        for nm in OUR_NAMES:
            enemy, ours = find_entities(data["leeks"], enemy_name, nm)
            if enemy is not None:
                break
    if enemy is None:
        return None, None
    eid = enemy["id"]
    turn = 0
    cur = None
    per_turn = defaultdict(Counter)
    chips_seen = set()
    for a in data.get("actions", []):
        if not isinstance(a, list) or not a:
            continue
        if a[0] == 6:
            turn = a[1]
            continue
        if a[0] == 7:
            cur = a[1]
            continue
        if cur != eid or turn < 1 or turn > 3:
            continue
        if a[0] == 10:
            per_turn[turn]["move"] += 1
        elif a[0] == 12:
            cname = chip_tpl.get(a[1])
            cls = classify_chip(cname, chip_effects)
            if cname:
                chips_seen.add(cname)
            if cls == "damage":
                cls = "weapon"
            if cls:
                per_turn[turn][cls] += 1
        elif a[0] in (16, 13):
            per_turn[turn]["weapon"] += 1
    return per_turn, chips_seen


def recent_fights(db_path, n):
    con = sqlite3.connect(db_path)
    rows = con.execute(
        "SELECT fight_id, opponent_name FROM fight_history ORDER BY timestamp DESC LIMIT ?", (n,)
    ).fetchall()
    con.close()
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--last", type=int, default=10, help="recent fights per leek DB")
    ap.add_argument("--account", default="main", choices=["main", "cure"])
    args = ap.parse_args()

    model_path = Path("data") / f"enemy_model_{args.account}.json"
    model = json.load(open(model_path)) if model_path.exists() else {}
    chip_tpl, weap_tpl, chip_effects = load_templates()

    leeks = MAIN_LEEKS if args.account == "main" else CURE_LEEKS
    fights = []
    seen = set()
    for lid in leeks:
        for fid, opp in recent_fights(f"tools/fight_history_{lid}.db", args.last):
            if fid in seen:
                continue
            seen.add(fid)
            fights.append((fid, opp))

    hits = 0
    total = 0
    per_arch = defaultdict(lambda: [0, 0])
    mispredictions = []
    used = 0
    for fid, opp in fights:
        data = fetch_fight_data(fid)
        if not data:
            continue
        per_turn, chips_seen = enemy_turn_classes(data, opp, chip_tpl, chip_effects)
        if not per_turn:
            continue
        mem = model.get(opp)
        arch = prior_archetype(mem, chips_seen)
        used += 1
        for turn in (1, 2, 3):
            if turn not in per_turn or not per_turn[turn]:
                continue
            present = set(per_turn[turn].keys())
            actual = next((c for c in PRIORITY if c in present), None)
            if actual is None:
                continue
            pred = predict_primary(mem, arch, turn)
            total += 1
            per_arch[arch][1] += 1
            if pred == actual:
                hits += 1
                per_arch[arch][0] += 1
            elif len(mispredictions) < 5:
                mispredictions.append((fid, opp, arch, turn, pred, actual))

    pct = 100.0 * hits / max(1, total)
    print(f"fights evaluated: {used}  turns scored: {total}")
    print(f"overall top-1 accuracy: {pct:.1f}%")
    for arch in sorted(per_arch):
        h, t = per_arch[arch]
        print(f"  {arch:14s} {100.0*h/t:5.1f}%  ({h}/{t})")
    print("\nsample mispredictions:")
    for fid, opp, arch, turn, pred, actual in mispredictions:
        print(f"  {fid} vs {opp} ({arch}) T{turn}: predicted {pred}, actual {actual}")
    gate = "PASS" if pct >= 60.0 and used >= 30 else f"FAIL ({pct:.1f}% {'< 60%' if pct < 60 else 'or <30 fights'})"
    print(f"\nGATE: {gate}")


if __name__ == "__main__":
    main()
