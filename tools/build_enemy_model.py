#!/usr/bin/env python3
"""Build per-opponent behavioral enemy models from local fight history.

Phase M1 Deliverable 1. Reads the solo fight-history DBs
(tools/fight_history_<leek_id>.db), decodes up to 3 most recent server fights
per opponent via https://leekwars.com/api/fight/get/<fight_id>, and writes
per-opponent tendency features to data/enemy_model_<account>.json.

Weekly refresh design: entries carry their own `built` timestamp; opponents
whose entry is < 7 days old are skipped, so a weekly cron run only re-decodes
stale or new opponents. `--rebuild` forces a full refresh. `--max-fights`
caps HTTP fetches per account per run, so a long refresh can be split across
several resumable invocations, e.g.:

    # weekly cron, polite incremental refresh of both accounts
    python3 tools/build_enemy_model.py --max-fights 400

Action format (verified against live data): within data["actions"],
[7, entity] starts that entity's turn; [10, entity, cell, [path]] move;
[12, chipTpl, cell, ?] chip cast; [13, weaponTpl] set weapon;
[16, cell, success] weapon fire (attributed to the entity's most recent
[13]; "unknown" if it never switched weapon); [8, entity, tp, mp] end-of-turn
resources; [5, victim, killer] death;
[6, n] new global turn; [302, effectTpl, idx, ?, ?, effectType, value, turns]
applied effect (effect types: 5/6 shields, 13 poison, 17/18 MP/TP shackles,
20 damage return, 38/41/39/44 raw str/agi/mag/wis buffs).
"""
import argparse
import json
import sqlite3
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
GEN_DATA = Path("/home/ubuntu/leek-wars-generator/data")
OUT_DIR = ROOT / "data"

ACCOUNTS = {
    "main": {20443: "AdaLovelace", 129295: "KurtGodel",
             129296: "MargaretHamilton", 129288: "EdsgerDijkstra"},
    "cure": {19703: "LeekRain", 21175: "DawnFall",
             129801: "DuskHope", 130236: "ProdigalSon"},
}

GRID_WIDTH = 18
FIGHTS_PER_OPPONENT = 3
FRESH_DAYS = 7
FETCH_SLEEP = 0.35
RETRY_429_SLEEP = 2.0
HTTP_TIMEOUT = 20

POISON_CHIPS = {"venom", "toxin", "arsenic", "plague", "covid", "serum"}
SHIELD_CHIPS = {"armor", "wall", "fortress", "shield", "rampart", "armoring"}
HEAL_CHIPS = {"heal", "regeneration", "vaccine", "bandage", "cure", "antidote"}
BUFF_EFFECTS = {5, 6, 20, 38, 39, 41, 44}   # shields, dmg return, raw buffs
DENY_EFFECTS = {17, 18}                      # MP / TP shackles
POISON_EFFECT = 13
DAMAGE_EFFECT = 1
HEAL_EFFECT = 3

KITE_MIN_DIST = 6
SUMMONER_FIGHT_RATIO = 0.30
POISON_FIGHT_RATIO = 0.30
KITER_TURN_RATIO = 0.40
TANK_TURN_RATIO = 0.40


def parse_ts(ts):
    """History timestamps come in two formats; normalize to aware UTC."""
    if not ts:
        return datetime.min.replace(tzinfo=timezone.utc)
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def load_templates():
    """Return (chip name by template id, weapon name by template id,
    effect-type ids by chip name)."""
    with open(GEN_DATA / "chips.json") as f:
        chips = json.load(f)
    with open(GEN_DATA / "weapons.json") as f:
        weapons = json.load(f)
    chip_tpl = {c["template"]: c["name"] for c in chips.values()}
    weap_tpl = {w["template"]: w["name"] for w in weapons.values()}
    chip_effects = {c["name"]: {e["id"] for e in c.get("effects", [])}
                    for c in chips.values()}
    return chip_tpl, weap_tpl, chip_effects


def classify_chip(name, chip_effects):
    """Map a chip to a template class: summon/poison/deny/heal/buff/damage.

    Returns None for unrecognized chips (excluded from first_turn_template;
    the class list there is limited to buff/move/weapon/poison/summon/heal/
    deny by design).
    """
    if name is None:
        return None
    if name.endswith("_bulb"):
        return "summon"
    effects = chip_effects.get(name, set())
    if name in POISON_CHIPS or POISON_EFFECT in effects:
        return "poison"
    if effects & DENY_EFFECTS:
        return "deny"
    if name in HEAL_CHIPS or HEAL_EFFECT in effects:
        return "heal"
    if name in SHIELD_CHIPS or effects & BUFF_EFFECTS:
        return "buff"
    if DAMAGE_EFFECT in effects:
        return "damage"
    return None


def cell_distance(a, b):
    """Manhattan distance between two cells on a width-18 grid."""
    ax, ay = a % GRID_WIDTH, a // GRID_WIDTH
    bx, by = b % GRID_WIDTH, b // GRID_WIDTH
    return abs(ax - bx) + abs(ay - by)


def gather_opponents(account):
    """Read all history DBs of an account, grouped by opponent_id."""
    opponents = {}
    for leek_id, leek_name in ACCOUNTS[account].items():
        db = ROOT / "tools" / f"fight_history_{leek_id}.db"
        if not db.exists():
            continue
        con = sqlite3.connect(db)
        rows = con.execute(
            "SELECT fight_id, opponent_id, opponent_name, opponent_level,"
            " timestamp FROM fight_history").fetchall()
        con.close()
        for fight_id, opp_id, opp_name, opp_level, ts in rows:
            if opp_id is None:
                continue
            o = opponents.setdefault(opp_id, {
                "id": opp_id, "name": opp_name, "levels": [],
                "leeks": set(), "fights": [],
                "_latest": datetime.min.replace(tzinfo=timezone.utc),
            })
            o["levels"].append(opp_level)
            o["leeks"].add(leek_name)
            ts = parse_ts(ts)
            o["fights"].append((ts, fight_id))
            # keep the most recent known name (renames happen)
            if ts >= o["_latest"]:
                o["_latest"] = ts
                o["name"] = opp_name
    for o in opponents.values():
        # dedup + keep the N most recent fights
        seen, fights = set(), []
        for ts, fid in sorted(o["fights"], key=lambda f: f[0], reverse=True):
            if fid not in seen:
                seen.add(fid)
                fights.append((ts, fid))
            if len(fights) == FIGHTS_PER_OPPONENT:
                break
        o["fights"] = fights
    return opponents


def fetch_fight_data(fight_id):
    """Fetch and normalize one fight; one retry on HTTP 429. None on failure."""
    url = f"https://leekwars.com/api/fight/get/{fight_id}"
    for attempt in range(2):
        try:
            r = requests.get(url, timeout=HTTP_TIMEOUT)
        except requests.RequestException:
            return None
        if r.status_code == 429:
            if attempt == 0:
                time.sleep(RETRY_429_SLEEP)
                continue
            return None
        if r.status_code != 200:
            return None
        try:
            d = r.json()
        except ValueError:
            return None
        data = d.get("data")
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except ValueError:
                return None
        if isinstance(data, dict) and "leeks" in data and "actions" in data:
            return data
        return None
    return None


def find_entities(leeks, enemy_name, our_name):
    """Identify the enemy entity and our leek among fight entities."""
    mains = [l for l in leeks if not l.get("summon") and l.get("type", 0) == 0]
    enemy = next((l for l in mains if l.get("name") == enemy_name), None)
    ours = next((l for l in mains if l.get("name") == our_name), None)
    if enemy is None:
        rest = [l for l in mains if ours is None or l["id"] != ours["id"]]
        if len(rest) == 1:
            enemy = rest[0]
    if ours is None:
        rest = [l for l in mains if enemy is None or l["id"] != enemy["id"]]
        if len(rest) == 1:
            ours = rest[0]
    if enemy is None or ours is None or enemy["id"] == ours["id"]:
        return None, None
    return enemy, ours


def analyze_fight(data, enemy_name, our_name, chip_tpl, weap_tpl, chip_effects):
    """Extract enemy behavior from one decoded fight. None if undecodable."""
    enemy, ours = find_entities(data["leeks"], enemy_name, our_name)
    if enemy is None:
        return None
    eid, oid = enemy["id"], ours["id"]
    pos = {l["id"]: l.get("cellPos") for l in data["leeks"]}
    held = {}  # entity -> weapon template currently held

    stats = {
        "weapon_fires": Counter(),
        "enemy_turns": 0,
        "kite_turns": 0,       # cast-or-fired while ending turn at dist >= 6
        "tank_turns": 0,       # turns with >= 1 shield cast
        "dist_sum": 0, "dist_n": 0,
        "shield_casts": 0,
        "bulb_casts": 0,
        "poison_casts": 0,
        "antidote_turn": None,
        "buff_first": False,
        "t1_classes": [],
        "per_turn": {1: [], 2: [], 3: []},  # raw class list per early turn
    }

    cur = None
    turn_no = 1
    # per-enemy-turn accumulators
    t_cast_fire = False
    t_shield = False
    # opener tracking
    buffs_before_hostile = 0
    hostile_seen = False
    # first-enemy-turn template tracking
    t1_seen = False
    in_t1 = False

    def end_enemy_turn():
        nonlocal t_cast_fire, t_shield
        stats["enemy_turns"] += 1
        ep, op = pos.get(eid), pos.get(oid)
        if ep is not None and op is not None:
            dist = cell_distance(ep, op)
            stats["dist_sum"] += dist
            stats["dist_n"] += 1
            if t_cast_fire and dist >= KITE_MIN_DIST:
                stats["kite_turns"] += 1
        if t_shield:
            stats["tank_turns"] += 1
        t_cast_fire = t_shield = False

    for a in data["actions"]:
        code = a[0]
        if code == 6:
            if cur == eid:
                end_enemy_turn()
            cur = None
            in_t1 = False
            turn_no = a[1] if len(a) > 1 and isinstance(a[1], int) else turn_no + 1
        elif code == 7:
            if cur == eid:
                end_enemy_turn()
            cur = a[1]
            in_t1 = cur == eid and not t1_seen
            if cur == eid:
                t1_seen = True
        elif code == 10:
            ent, cell = a[1], a[2]
            if isinstance(cell, int):
                pos[ent] = cell
            if cur == eid:
                if turn_no <= 3:
                    stats["per_turn"][turn_no].append("move")
                if in_t1:
                    stats["t1_classes"].append("move")
        elif code == 13:
            if cur is not None and len(a) > 1:
                held[cur] = a[1]
                if cur == eid and turn_no <= 3:
                    stats["per_turn"][turn_no].append("weapon")
                if cur == eid and in_t1:
                    stats["t1_classes"].append("weapon")
        elif code == 8:  # [8, entity, tp, mp]: end-of-turn resources, not weapon
            pass
        elif code == 16:
            if cur == eid:
                t_cast_fire = True
                if not hostile_seen:
                    hostile_seen = True
                    stats["buff_first"] = buffs_before_hostile >= 2
                name = weap_tpl.get(held.get(eid), "unknown")
                stats["weapon_fires"][name] += 1
                if turn_no <= 3:
                    stats["per_turn"][turn_no].append("weapon")
                if in_t1:
                    stats["t1_classes"].append("weapon")
        elif code == 12:
            if cur == eid:
                t_cast_fire = True
                cname = chip_tpl.get(a[1])
                cls = classify_chip(cname, chip_effects)
                if cls == "summon":
                    stats["bulb_casts"] += 1
                elif cls == "poison":
                    stats["poison_casts"] += 1
                elif cls == "buff":
                    stats["shield_casts"] += 1 if (cname in SHIELD_CHIPS) else 0
                    t_shield = t_shield or cname in SHIELD_CHIPS
                    if not hostile_seen:
                        buffs_before_hostile += 1
                if cname == "antidote" and stats["antidote_turn"] is None:
                    stats["antidote_turn"] = turn_no
                if cls in ("poison", "damage") and not hostile_seen:
                    hostile_seen = True
                    stats["buff_first"] = buffs_before_hostile >= 2
                if turn_no <= 3 and cls:
                    stats["per_turn"][turn_no].append(cls)
                if in_t1 and cls in ("buff", "poison", "summon", "heal", "deny"):
                    stats["t1_classes"].append(cls)
    if cur == eid:
        end_enemy_turn()

    # modal class per early turn, by tactical priority (highest present):
    # a turn with a summon cast is a summon turn, regardless of move counts.
    PRIORITY = ["summon", "poison", "weapon", "buff", "heal", "deny", "move"]
    for t in (1, 2, 3):
        present = set(stats["per_turn"][t])
        stats["t%d_modal" % t] = next((c for c in PRIORITY if c in present), None)
    del stats["per_turn"]

    # collapse consecutive duplicate classes for a robust template signature
    collapsed = []
    for c in stats["t1_classes"]:
        if not collapsed or collapsed[-1] != c:
            collapsed.append(c)
    stats["t1_classes"] = collapsed
    return stats


def merge_opponent(opp, fight_stats):
    """Aggregate per-fight stats into the opponent's model entry."""
    n = len(fight_stats)
    weapon = Counter()
    turns = kite = tank = shield_casts = bulbs = 0
    dist_sum = dist_n = 0
    poison_fights = bulb_fights = 0
    antidote_turns = []
    buff_first_votes = 0
    t1_templates = Counter()
    for s in fight_stats:
        weapon.update(s["weapon_fires"])
        turns += s["enemy_turns"]
        kite += s["kite_turns"]
        tank += s["tank_turns"]
        shield_casts += s["shield_casts"]
        bulbs += s["bulb_casts"]
        dist_sum += s["dist_sum"]
        dist_n += s["dist_n"]
        if s["poison_casts"] >= 2:
            poison_fights += 1
        if s["bulb_casts"] >= 1:
            bulb_fights += 1
        if s["antidote_turn"] is not None:
            antidote_turns.append(s["antidote_turn"])
        if s["buff_first"]:
            buff_first_votes += 1
        if s["t1_classes"]:
            t1_templates[tuple(s["t1_classes"])] += 1

    if bulb_fights / n >= SUMMONER_FIGHT_RATIO:
        archetype = "summoner"
    elif poison_fights / n >= POISON_FIGHT_RATIO:
        archetype = "magic_poison"
    elif turns and kite / turns >= KITER_TURN_RATIO:
        archetype = "kiter"
    elif turns and tank / turns >= TANK_TURN_RATIO:
        archetype = "tank"
    else:
        archetype = "bruiser"

    top_weapons = sorted(weapon.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    template = []
    if t1_templates:
        best = max(sorted(t1_templates), key=lambda t: t1_templates[t])
        template = list(best)

    turn_modals = {}
    for t in (1, 2, 3):
        votes = Counter(s["t%d_modal" % t] for s in fight_stats
                        if s.get("t%d_modal" % t))
        turn_modals["t%d_modal" % t] = (votes.most_common(1)[0][0] if votes else None)

    return {
        "built": iso_now(),
        "opponent_id": opp["id"],
        "fights_analyzed": n,
        "leek_names_fought": sorted(opp["leeks"]),
        "level_range": [min(opp["levels"]), max(opp["levels"])],
        "archetype": archetype,
        "opener_style": "buff_first" if buff_first_votes * 2 > n else "rush",
        "weapon_usage": dict(top_weapons),
        "mean_engagement_distance": round(dist_sum / dist_n, 2) if dist_n else None,
        "antidote_timing": (round(sum(antidote_turns) / len(antidote_turns), 2)
                            if antidote_turns else None),
        "shield_cadence": round(shield_casts / turns, 3) if turns else 0.0,
        "summon_usage": round(bulbs / n, 2),
        "first_turn_template": template,
        **turn_modals,
    }


def is_fresh(entry):
    built = entry.get("built")
    if not built:
        return False
    age = datetime.now(timezone.utc) - parse_ts(built)
    return age.days < FRESH_DAYS


def build_account(account, max_fights, rebuild, chip_tpl, weap_tpl, chip_effects):
    out_path = OUT_DIR / f"enemy_model_{account}.json"
    model = {}
    if out_path.exists() and not rebuild:
        try:
            model = json.loads(out_path.read_text())
        except (ValueError, OSError):
            model = {}
    else:
        model = {}
    model.pop("_meta", None)

    opponents = gather_opponents(account)
    # recent opponents first, deterministic tie-break on id
    order = sorted(opponents.values(),
                   key=lambda o: (-o["fights"][0][0].timestamp(), o["id"]))

    fetched = decoded = skipped_fresh = 0
    for opp in order:
        if fetched >= max_fights:
            break
        if not rebuild and opp["name"] in model and is_fresh(model[opp["name"]]):
            skipped_fresh += 1
            continue
        fight_stats = []
        for _ts, fid in opp["fights"]:
            if fetched >= max_fights:
                break
            fetched += 1
            data = fetch_fight_data(fid)
            time.sleep(FETCH_SLEEP)
            if data is None:
                continue
            # try each of our leeks that faced this opponent until one decodes
            for leek_name in sorted(opp["leeks"]):
                s = analyze_fight(data, opp["name"], leek_name, chip_tpl,
                                  weap_tpl, chip_effects)
                if s is not None:
                    break
            if s is not None:
                fight_stats.append(s)
                decoded += 1
        if fight_stats:
            model[opp["name"]] = merge_opponent(opp, fight_stats)

    total_analyzed = sum(e.get("fights_analyzed", 0) for e in model.values())
    output = {"_meta": {"built": iso_now(), "account": account,
                        "fights_analyzed": total_analyzed}}
    for name in sorted(model):
        output[name] = model[name]
    OUT_DIR.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, sort_keys=False) + "\n")

    # summary
    dist = Counter(e["archetype"] for e in model.values())
    coverage = 100.0 * len(model) / len(opponents) if opponents else 0.0
    print(f"\n=== {account} -> {out_path} ===")
    print(f"opponents in history DBs : {len(opponents)}")
    print(f"opponents modeled        : {len(model)} "
          f"(fresh-skip {skipped_fresh}, fetches {fetched}, decoded {decoded})")
    print(f"coverage (>=1 decoded)   : {coverage:.1f}%")
    print("archetype distribution   : " +
          (", ".join(f"{k}={v}" for k, v in sorted(dist.items())) or "none"))
    return output


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--account", choices=["main", "cure", "both"],
                    default="both", help="which account model(s) to build")
    ap.add_argument("--max-fights", type=int, default=400,
                    help="max server fights to fetch per account (default 400)")
    ap.add_argument("--rebuild", action="store_true",
                    help="ignore entry freshness, re-decode everything")
    args = ap.parse_args(argv)

    chip_tpl, weap_tpl, chip_effects = load_templates()
    accounts = ["main", "cure"] if args.account == "both" else [args.account]
    for account in accounts:
        build_account(account, args.max_fights, args.rebuild,
                      chip_tpl, weap_tpl, chip_effects)


if __name__ == "__main__":
    main()
