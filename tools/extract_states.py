#!/usr/bin/env python3
"""W1b: extract per-turn states from cached fight JSONs into a labeled dataset
(data/dataset_v1.jsonl) for the learned value model.

One row per turn of OUR leek (decision points). Label: 1 = we won, 0 = lost.
Draws excluded in v1.

Usage: python3 tools/extract_states.py [--limit N] [--self-test]
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
CACHE = ROOT / "data" / "fight_cache"
OUT = ROOT / "data" / "dataset_v1.jsonl"

MAP_W = 17  # standard ladder map width

OUR_NAMES = {"AdaLovelace", "KurtGodel", "MargaretHamilton", "EdsgerDijkstra",
             "LeekRain", "DawnFall", "DuskHope", "ProdigalSon"}

# server action codes
A_DEAD, A_TURN, A_LEEKTURN = 5, 6, 7
A_MOVE = 10
A_LIFE_LOST, A_HEAL, A_NOVA, A_LIFE_DMG, A_POISON, A_AFTER, A_NOVA_VIT = 101, 103, 107, 109, 110, 111, 112
A_ADD_EFF, A_REM_EFF = 302, 303
# effect types
T_REL_SH, T_ABS_SH, T_POISON = 5, 6, 13
T_STR, T_AGI, T_MAG, T_WIS, T_RES, T_SCI = 38, 41, 39, 44, 42, 40


def cell_xy(cid):
    row, xr = divmod(cid, 2 * MAP_W - 1)
    y = row - xr % MAP_W
    x = (cid - (MAP_W - 1) * y) // MAP_W
    return x, y


def dist(c1, c2):
    if c1 is None or c2 is None:
        return None
    x1, y1 = cell_xy(c1)
    x2, y2 = cell_xy(c2)
    return abs(x1 - x2) + abs(y1 - y2)


def extract(path):
    d = json.load(open(path))
    data = d.get("data")
    if isinstance(data, str):
        data = json.loads(data)
    if not data or "leeks" not in data:
        return []
    leeks = [l for l in data["leeks"] if not l.get("summon")]
    ours = [l for l in leeks if l["name"] in OUR_NAMES]
    if len(ours) != 1 or len(leeks) != 2:
        return []  # solo fights only in v1
    us, foe = ours[0], [l for l in leeks if l["team"] != ours[0]["team"]][0]
    winner = d.get("winner")
    if winner not in (1, 2):
        return []  # skip draws
    label = 1 if winner == us["team"] else 0

    ents = {us["id"]: {"cur": us["life"], "max": us["life"], "cell": us.get("cellPos"),
                       "eff": {}, "base": us},
            foe["id"]: {"cur": foe["life"], "max": foe["life"], "cell": foe.get("cellPos"),
                        "eff": {}, "base": foe}}

    rows = []
    turn = 0

    def snapshot():
        u, f = ents[us["id"]], ents[foe["id"]]
        def agg(e, types):
            return sum(v["value"] for v in e["eff"].values() if v["type"] in types)
        def pstacks(e):
            return sum(1 for v in e["eff"].values() if v["type"] == T_POISON)
        row = {
            "fight": d.get("id", path.stem), "leek": us["name"], "turn": turn,
            "hp_us": round(u["cur"] / max(1, u["max"]), 3), "hp_foe": round(f["cur"] / max(1, f["max"]), 3),
            "maxhp_us": u["max"], "maxhp_foe": f["max"],
            "dist": dist(u["cell"], f["cell"]),
            "abssh_us": agg(u, (T_ABS_SH,)), "abssh_foe": agg(f, (T_ABS_SH,)),
            "relsh_us": agg(u, (T_REL_SH,)), "relsh_foe": agg(f, (T_REL_SH,)),
            "pois_us": pstacks(u), "pois_foe": pstacks(f),
            "poisdpt_us": agg(u, (T_POISON,)), "poisdpt_foe": agg(f, (T_POISON,)),
            "str_us": u["base"].get("strength", 0), "str_foe": f["base"].get("strength", 0),
            "mag_us": u["base"].get("magic", 0), "mag_foe": f["base"].get("magic", 0),
            "agi_us": u["base"].get("agility", 0), "agi_foe": f["base"].get("agility", 0),
            "wis_us": u["base"].get("wisdom", 0), "wis_foe": f["base"].get("wisdom", 0),
            "res_us": u["base"].get("resistance", 0), "res_foe": f["base"].get("resistance", 0),
            "sci_us": u["base"].get("science", 0), "sci_foe": f["base"].get("science", 0),
            "tp_us": u["base"].get("tp", 0), "tp_foe": f["base"].get("tp", 0),
            "mp_us": u["base"].get("mp", 0), "mp_foe": f["base"].get("mp", 0),
            "lvl_us": u["base"].get("level", 0), "lvl_foe": f["base"].get("level", 0),
            "y": label,
        }
        rows.append(row)

    for a in data.get("actions", []):
        c = a[0]
        if c == A_TURN:
            turn = a[1]
        elif c == A_LEEKTURN and a[1] == us["id"]:
            snapshot()
        elif c == A_MOVE and a[1] in ents:
            ents[a[1]]["cell"] = a[2]
        elif c in (A_LIFE_LOST, A_POISON, A_LIFE_DMG, A_AFTER) and a[1] in ents:
            ents[a[1]]["cur"] = max(0, ents[a[1]]["cur"] - a[2])
        elif c == A_NOVA and a[1] in ents:
            e = ents[a[1]]
            e["max"] = max(0, e["max"] - a[2])
            e["cur"] = min(e["cur"], e["max"])
        elif c == A_NOVA_VIT and a[1] in ents:
            ents[a[1]]["max"] += a[2]
        elif c == A_HEAL and a[1] in ents:
            e = ents[a[1]]
            e["cur"] = min(e["max"], e["cur"] + a[2])
        elif c == A_ADD_EFF and len(a) >= 8:
            _, tpl, uid, target, caster, etype, value, turns = (list(a) + [0] * 8)[:8]
            if target in ents:
                ents[target]["eff"][uid] = {"type": etype, "value": value, "turns": turns}
        elif c == A_REM_EFF and len(a) >= 2:
            for e in ents.values():
                e["eff"].pop(a[1], None)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    files = sorted(CACHE.glob("*.json"), key=lambda p: -int(p.stem) if p.stem.isdigit() else 0)
    if args.limit:
        files = files[:args.limit]
    n_rows = n_fights = 0
    with open(OUT, "w") as out:
        for p in files:
            try:
                rows = extract(p)
            except Exception:
                continue
            if rows:
                n_fights += 1
                for r in rows:
                    out.write(json.dumps(r) + "\n")
                    n_rows += 1
            if n_fights % 500 == 0 and n_fights:
                print(f"  {n_fights} fights -> {n_rows} rows", flush=True)
    print(f"done: {n_fights} fights -> {n_rows} rows -> {OUT}")


if __name__ == "__main__":
    main()
