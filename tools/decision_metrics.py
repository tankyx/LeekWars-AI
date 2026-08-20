#!/usr/bin/env python3
"""Decision-quality metrics harness for LeekWars fights (Phase M0).

Fetches server fight logs and computes per-fight decision metrics for OUR leek:
  - zero_shield_shots:   attacks that dealt 0 damage to a shielded target
  - denial_spam_turns:   turns with >=3 shackle chips cast (slow_down, tranquilizer,
                         soporific, ball_and_chain) while at least one poison chip
                         in our kit (venom, toxin, arsenic, plague, covid, serum)
                         was NOT cast that turn and was off cooldown (never-cast =
                         available; a cast in the previous `cooldown` rounds = on
                         cooldown). Kit from tools/leek_configs.json (the fight
                         payload carries no chip list); fallback: poisons observed
                         cast in the fight. Cooldowns from chips.json.
  - buff_recast_waste:   steroid/warm_up/knowledge/wizardry recast on self while the
                         matching RAW buff (38/41/44/39) still had >=2 turns left
  - poison_friendly_fire: liberation cast on a target carrying >=2 of OUR poisons
  - disengage_failure:   took >25% max HP in a round while ending the round <=2 cells
                         from our turn-start cell, twice in a row
  - wasted_tp / total_tp / wasted_pct (headline)

Raw action format (verified against leek-wars-generator sources):
  [6, turn] NEW_TURN, [7, entity] LEEK_TURN, [8, entity, tp, mp] END_TURN,
  [10, entity, cell, [path]] MOVE, [12, chipTpl, cell, success] USE_CHIP (caster =
  current turn entity), [13, weaponTpl] SET_WEAPON (costs 1 TP),
  [16, cell, success] USE_WEAPON (with current weapon),
  [101, target, pv, erosion] LOST_LIFE (pv=0 / absent = no damage),
  [110, target, dmg, erosion] POISON tick,
  [301]/[302, itemID, id, caster, target, effectType, value, turns] ADD_*_EFFECT,
  [303, id] REMOVE_EFFECT, [304, id, value] UPDATE_EFFECT,
  [307, entity] REMOVE_POISONS, [308, entity] REMOVE_SHACKLES.
  Effect durations decrement at the start of the CASTER's turn (generator
  Entity.startTurn); turns=-1 means permanent.
  Note: [104] is VITALITY (max-life gain), NOT a TP cost — TP accounting is done
  from chips.json / weapons.json template costs (+1 TP per setWeapon).

Usage:
  python3 tools/decision_metrics.py <fight_id> [<fight_id>...] [--our <name>]
  python3 tools/decision_metrics.py --leek <leek_db_id> --last N [--our <name>]
"""
import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.request
import urllib.error

GEN_DATA = "/home/ubuntu/leek-wars-generator/data"
FIGHT_URL = "https://leekwars.com/api/fight/get/{}"
MAP_WIDTH = 18  # x = cell % 18, y = cell // 18 (verified from [10] move paths)

KNOWN_LEEKS = (
    "AdaLovelace", "KurtGodel", "MargaretHamilton", "EdsgerDijkstra",
    "LeekRain", "DawnFall", "DuskHope", "ProdigalSon",
)

SHACKLE_CHIPS = {"slow_down", "tranquilizer", "soporific", "ball_and_chain"}
POISON_CHIPS = {"venom", "toxin", "arsenic", "plague", "covid", "serum"}
BUFF_RECAST = {"steroid": 38, "warm_up": 41, "knowledge": 44, "wizardry": 39}
SHIELD_TYPES = (5, 6)       # REL_SHIELD, ABS_SHIELD
POISON_TYPE = 13
SHACKLE_TYPES = (17, 18)    # MP / TP shackle (for REMOVE_SHACKLES cleanup)
SET_WEAPON_TP = 1           # generator State.setWeapon: entity.useTP(1)
LEEKS_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "leek_configs.json")

# Action codes that are part of the resolution of the preceding attack
# (damage, heals, applied effects, ...). Anything else ends the attack block.
RESOLUTION_CODES = {
    14, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112,
    203, 205, 301, 302, 303, 304, 306, 307, 308,
}


def load_templates():
    with open(f"{GEN_DATA}/chips.json") as f:
        chips = json.load(f)
    with open(f"{GEN_DATA}/weapons.json") as f:
        weapons = json.load(f)
    chip_by_tpl = {c["template"]: c for c in chips.values()}
    weap_by_tpl = {w["template"]: w for w in weapons.values()}
    chip_by_id = {int(k): c for k, c in chips.items()}
    return chip_by_tpl, weap_by_tpl, chip_by_id


def load_poison_kit(leek_name, chip_by_id):
    """Poison-chip kit (set of chip names) for a leek.

    The fight payload carries no equipped-chip list, so the kit is resolved from
    tools/leek_configs.json (local snapshot; its chip ids match the itemIDs seen
    in fight [302] entries). Returns None if the leek is unknown there.
    """
    try:
        with open(LEEKS_CONFIG) as f:
            cfg = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    entry = cfg.get("leeks", {}).get(leek_name)
    if not entry:
        return None
    kit = set()
    for cid in entry.get("chips", []):
        chip = chip_by_id.get(int(cid))
        if chip and chip.get("name") in POISON_CHIPS:
            kit.add(chip["name"])
    return kit


def load_fight(fight_id):
    last_err = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(FIGHT_URL.format(fight_id), timeout=30) as r:
                d = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code != 429 or attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
    else:
        raise last_err
    data = d["data"]
    if isinstance(data, str):
        data = json.loads(data)
    return d, data


def cell_dist(a, b):
    """Manhattan distance between cells (generator Pathfinding.getCaseDistance)."""
    ax, ay = a % MAP_WIDTH, a // MAP_WIDTH
    bx, by = b % MAP_WIDTH, b // MAP_WIDTH
    return abs(ax - bx) + abs(ay - by)


class EffectTable:
    """Active chip/weapon effects keyed by instance id."""

    def __init__(self):
        self.effects = {}

    def add(self, eid, caster, target, etype, value, turns):
        self.effects[eid] = {
            "caster": caster, "target": target,
            "type": etype, "value": value, "turns": turns,
        }

    def remove(self, eid):
        self.effects.pop(eid, None)

    def update(self, eid, value):
        if eid in self.effects:
            self.effects[eid]["value"] = value

    def tick(self, caster):
        """Start of caster's turn: decrement launched effects (generator semantics)."""
        expired = []
        for eid, e in self.effects.items():
            if e["caster"] == caster and e["turns"] > 0:
                e["turns"] -= 1
                if e["turns"] == 0:
                    expired.append(eid)
        for eid in expired:
            del self.effects[eid]

    def remove_type_on(self, target, types):
        for eid in [k for k, e in self.effects.items()
                    if e["target"] == target and e["type"] in types]:
            del self.effects[eid]

    def has_shield(self, target):
        return any(e["target"] == target and e["type"] in SHIELD_TYPES
                   and e["turns"] != 0 and e["value"] > 0
                   for e in self.effects.values())

    def buff_turns(self, target, etype):
        """Max remaining turns of a RAW buff type on target (0 if absent)."""
        return max((e["turns"] for e in self.effects.values()
                    if e["target"] == target and e["type"] == etype), default=0)

    def count_poisons(self, target, caster):
        return sum(1 for e in self.effects.values()
                   if e["target"] == target and e["caster"] == caster
                   and e["type"] == POISON_TYPE and e["turns"] != 0)


def resolution_hits(actions, i):
    """Collect (target, pv) LOST_LIFE entries belonging to the attack at index i."""
    hits = []
    j = i + 1
    while j < len(actions) and actions[j][0] in RESOLUTION_CODES:
        a = actions[j]
        if a[0] == 101 and len(a) >= 3:
            hits.append((a[1], a[2]))
        j += 1
    return hits


def analyze_fight(fight_id, our_name=None):
    d, data = load_fight(fight_id)
    rep = analyze_data(d, data, our_name=our_name)
    rep["fight_id"] = int(fight_id)
    return rep


def analyze_data(d, data, our_name=None):
    chip_by_tpl, weap_by_tpl, chip_by_id = load_templates()
    leeks = data["leeks"]

    if our_name:
        mine = [l for l in leeks if l.get("name") == our_name]
    else:
        mine = [l for l in leeks if l.get("name") in KNOWN_LEEKS]
    if not mine:
        raise ValueError(
            f"fight {d.get('id', '?')}: our leek not found "
            f"(names: {[l.get('name') for l in leeks]}); pass --our")
    me_leek = mine[0]
    me = me_leek["id"]
    my_team = me_leek.get("team")
    max_hp = me_leek.get("maxHealth") or me_leek.get("life") or 1
    opponents = ", ".join(l.get("name", "?") for l in leeks if l["id"] != me)
    winner = d.get("winner")
    if winner is None:
        winner = data.get("winner")
    result = "DRAW" if winner in (0, None) else ("WIN" if winner == my_team else "LOSS")

    metrics = {
        "zero_shield_shots": 0,
        "denial_spam_turns": 0,
        "buff_recast_waste": 0,
        "poison_friendly_fire": 0,
        "disengage_failure": 0,
    }
    wasted_tp = 0
    total_tp = 0

    effects = EffectTable()
    cells = {l["id"]: l.get("cellPos") for l in leeks}
    cur_weapon = {}                     # entity -> equipped weapon template
    actions = data["actions"]

    # Poison kit + cooldowns for the refined denial_spam rule.
    # Kit comes from tools/leek_configs.json (fight data carries no chip list);
    # fallback: poison chips this leek is observed casting in this fight.
    poison_cd = {c["name"]: c.get("cooldown", 0)
                 for c in chip_by_id.values() if c.get("name") in POISON_CHIPS}
    poison_kit = load_poison_kit(me_leek.get("name"), chip_by_id)
    if not poison_kit:
        poison_kit = set()
        scan_cur = None
        for a in actions:
            if a[0] == 7:
                scan_cur = a[1]
            elif a[0] == 12 and scan_cur == me and len(a) > 3 and a[3] != 0:
                nm = chip_by_tpl.get(a[1], {}).get("name")
                if nm in POISON_CHIPS:
                    poison_kit.add(nm)

    cur = None                          # entity whose turn block we are in
    round_no = 1
    shackle_casts = []                  # chip costs of shackle casts this turn (ours)
    poison_cast_turn = set()            # poison chips we cast this turn
    poison_last_cast = {}               # poison chip name -> last round we cast it
    rounds = {}                         # round -> {"dmg", "start", "end"}

    def rnd(r):
        return rounds.setdefault(r, {"dmg": 0, "start": None, "end": None})

    def poison_available():
        """Any kit poison not cast this turn and off cooldown? (never-cast =
        available; cast in the previous `cooldown` rounds = on cooldown)."""
        for p in poison_kit:
            if p in poison_cast_turn:
                continue
            last = poison_last_cast.get(p)
            if last is None or last <= round_no - poison_cd.get(p, 0) - 1:
                return True
        return False

    def end_turn_block():
        nonlocal wasted_tp
        if cur == me and len(shackle_casts) >= 3 and poison_available():
            metrics["denial_spam_turns"] += 1
            # casts 1-2 are legit denial; only the excess counts as wasted TP
            wasted_tp += sum(shackle_casts[2:])

    i = 0
    while i < len(actions):
        a = actions[i]
        code = a[0]

        if code == 6:                   # NEW_TURN
            round_no = a[1]
        elif code == 7:                 # LEEK_TURN
            cur = a[1]
            shackle_casts = []
            poison_cast_turn = set()
            effects.tick(cur)
            if cur == me:
                rnd(round_no)["start"] = cells.get(me)
                rnd(round_no)["end"] = cells.get(me)
        elif code == 8:                 # END_TURN
            end_turn_block()
            cur = None
        elif code == 10:                # MOVE [entity, cell, path]
            ent, cell = a[1], a[2]
            cells[ent] = cell
            # Only voluntary moves during OUR turn block count as disengaging;
            # [10] entries on us during enemy turns are knockback/attraction.
            if ent == me and cur == me:
                rnd(round_no)["end"] = cell
        elif code == 13:                # SET_WEAPON [tpl] (current entity, 1 TP)
            cur_weapon[cur] = a[1]
            if cur == me:
                total_tp += SET_WEAPON_TP
        elif code == 12:                # USE_CHIP [tpl, cell, success]
            tpl, cell = a[1], a[2]
            chip = chip_by_tpl.get(tpl, {})
            cname = chip.get("name", f"chip#{tpl}")
            cost = chip.get("cost", 0)
            if cur == me:
                total_tp += cost
                # zero-damage shot into an active shield?
                flagged = any(pv == 0 and effects.has_shield(t)
                              for t, pv in resolution_hits(actions, i))
                if flagged:
                    metrics["zero_shield_shots"] += 1
                    wasted_tp += cost
                # denial spam bookkeeping
                if cname in SHACKLE_CHIPS:
                    shackle_casts.append(cost)
                # poison cast bookkeeping (only successful casts trigger cooldown)
                if cname in POISON_CHIPS and (len(a) < 4 or a[3] != 0):
                    poison_cast_turn.add(cname)
                    poison_last_cast[cname] = round_no
                # buff recast onto self while buff still fresh (>=2 turns left)
                if cname in BUFF_RECAST and cell == cells.get(me):
                    if effects.buff_turns(me, BUFF_RECAST[cname]) >= 2:
                        metrics["buff_recast_waste"] += 1
                        wasted_tp += cost
                # liberation wiping >=2 of our own poisons on the target
                if cname == "liberation":
                    target = next((e for e, c in cells.items() if c == cell), None)
                    if target is not None and effects.count_poisons(target, me) >= 2:
                        metrics["poison_friendly_fire"] += 1
                        wasted_tp += cost
        elif code == 16:                # USE_WEAPON [cell, success]
            if cur == me:
                wt = cur_weapon.get(me)
                cost = weap_by_tpl.get(wt, {}).get("cost", 0)
                total_tp += cost
                flagged = any(pv == 0 and effects.has_shield(t)
                              for t, pv in resolution_hits(actions, i))
                if flagged:
                    metrics["zero_shield_shots"] += 1
                    wasted_tp += cost
        elif code in (301, 302):        # ADD_WEAPON/CHIP_EFFECT
            if len(a) >= 8:
                effects.add(a[2], a[3], a[4], a[5], a[6], a[7])
        elif code == 303:               # REMOVE_EFFECT
            effects.remove(a[1])
        elif code == 304:               # UPDATE_EFFECT
            if len(a) >= 3:
                effects.update(a[1], a[2])
        elif code == 307:               # REMOVE_POISONS [entity]
            effects.remove_type_on(a[1], (POISON_TYPE,))
        elif code == 308:               # REMOVE_SHACKLES [entity]
            effects.remove_type_on(a[1], SHACKLE_TYPES)
        elif code in (101, 110):        # damage taken / poison tick
            if a[1] == me:
                rnd(round_no)["dmg"] += a[2]
        i += 1

    # disengage_failure: bursted >25% max HP while ending the round <=2 cells
    # from our turn-start cell, two rounds in a row
    qualifies = {}
    for r, v in rounds.items():
        if v["start"] is None:
            continue                    # we had no turn this round
        moved = cell_dist(v["start"], v["end"]) if v["end"] is not None else 0
        qualifies[r] = v["dmg"] > 0.25 * max_hp and moved <= 2
    for r in sorted(qualifies):
        if qualifies[r] and qualifies.get(r - 1):
            metrics["disengage_failure"] += 1

    wasted_pct = round(100.0 * wasted_tp / total_tp, 1) if total_tp else 0.0
    return {
        "fight_id": 0,
        "opponent": opponents,
        "result": result,
        "our_leek": me_leek.get("name"),
        "metrics": metrics,
        "wasted_tp": wasted_tp,
        "total_tp": total_tp,
        "wasted_pct": wasted_pct,
    }


def print_fight(rep):
    print(f"--- FIGHT {rep['fight_id']}  vs {rep['opponent']}  [{rep['result']}] "
          f"(our: {rep['our_leek']}) ---")
    for k, v in rep["metrics"].items():
        flag = "  <-- FLAG" if v else ""
        print(f"  {k:22s} {v}{flag}")
    print(f"  wasted_tp {rep['wasted_tp']} / total_tp {rep['total_tp']} "
          f"= {rep['wasted_pct']}% wasted")
    print(json.dumps(rep, indent=2))


def last_fight_ids(leek_db_id, n):
    db = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      f"fight_history_{leek_db_id}.db")
    if not os.path.exists(db):
        sys.exit(f"fight history DB not found: {db}")
    con = sqlite3.connect(db)
    rows = con.execute(
        "SELECT fight_id FROM fight_history ORDER BY timestamp DESC LIMIT ?",
        (n,)).fetchall()
    con.close()
    return [r[0] for r in reversed(rows)]  # chronological


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fight_ids", nargs="*", help="fight ids to analyze")
    ap.add_argument("--our", help="our leek name (default: auto-detect from known leeks)")
    ap.add_argument("--leek", type=int, help="leek DB id for aggregate mode "
                    "(reads tools/fight_history_<id>.db)")
    ap.add_argument("--last", type=int, default=20,
                    help="number of recent fights in aggregate mode (default 20)")
    args = ap.parse_args()

    if args.leek:
        fight_ids = last_fight_ids(args.leek, args.last)
        aggregate = True
    elif args.fight_ids:
        fight_ids = args.fight_ids
        aggregate = len(fight_ids) > 1
    else:
        ap.error("pass fight ids or --leek <db_id> --last N")

    reports = []
    for fid in fight_ids:
        try:
            rep = analyze_fight(fid, our_name=args.our)
        except Exception as e:
            print(f"!!! fight {fid}: {e}")
            continue
        reports.append(rep)
        print_fight(rep)

    if aggregate and reports:
        n = len(reports)
        tot = {k: sum(r["metrics"][k] for r in reports) for k in reports[0]["metrics"]}
        wtp = sum(r["wasted_tp"] for r in reports)
        ttp = sum(r["total_tp"] for r in reports)
        wins = sum(1 for r in reports if r["result"] == "WIN")
        agg = {
            "fights": n,
            "wins": wins,
            "metric_totals": tot,
            "metric_avg": {k: round(v / n, 2) for k, v in tot.items()},
            "wasted_tp_total": wtp,
            "total_tp": ttp,
            "wasted_pct_avg": round(sum(r["wasted_pct"] for r in reports) / n, 1),
            "wasted_pct_overall": round(100.0 * wtp / ttp, 1) if ttp else 0.0,
        }
        print(f"=== AGGREGATE over {n} fights ({wins} wins) ===")
        for k, v in tot.items():
            print(f"  {k:22s} total {v:4d}   avg {v / n:5.2f}/fight")
        print(f"  wasted_tp {wtp} / total_tp {ttp} "
              f"(avg wasted_pct {agg['wasted_pct_avg']}%, "
              f"overall {agg['wasted_pct_overall']}%)")
        print(json.dumps(agg, indent=2))


if __name__ == "__main__":
    main()
