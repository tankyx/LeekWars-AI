#!/usr/bin/env python3
"""Winner-side decision mining: contrast what high-talent opponents DO in
fights they WIN vs fights they LOSE (to us). The contrast is the playbook.

Mines our 18.6k cached fight JSONs (data/fight_cache) — no new downloads.
Outputs per-turn-class cast patterns, engagement distances, shield/buff timing.

Usage: python3 tools/winner_mining.py [--min-talent 2000]
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
CACHE = ROOT / "data" / "fight_cache"
GEN = Path("/home/ubuntu/leek-wars-generator/data")
OURS = {"AdaLovelace", "KurtGodel", "MargaretHamilton", "EdsgerDijkstra",
        "LeekRain", "DawnFall", "DuskHope", "ProdigalSon"}

A_DEAD, A_TURN, A_LEEKTURN = 5, 6, 7
A_MOVE = 10
A_CHIP, A_CHIP2, A_WEAPON = 2, 12, 16
A_SETWEAPON = 13

MAP_W = 17


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


def chip_class(name):
    for k, v in (("shield", "shield"), ("heal", "heal"), ("buff", "buff"),
                 ("damage", "damage"), ("poison", "poison"), ("denial", "denial"),
                 ("mobility", "mobility"), ("summon", "summon")):
        if k in name:
            return v
    return "other"


def load_chip_classes():
    chips = json.load(open(GEN / "chips.json"))
    m = {}
    for c in chips.values():
        n = c["name"]
        effects = {e["id"] for e in c.get("effects", [])}
        if 5 in effects or 6 in effects or 37 in effects or 54 in effects:
            cls = "shield"
        elif 2 in effects:
            cls = "heal"
        elif 13 in effects:
            cls = "poison"
        elif 14 in effects:
            cls = "summon"
        elif effects & {17, 18, 19, 24, 47, 48}:
            cls = "denial"
        elif effects & {3, 4, 7, 8, 21, 22, 31, 32, 38, 39, 40, 41, 42, 44, 52}:
            cls = "buff"
        elif effects & {10, 46, 50, 51, 53}:
            cls = "mobility"
        elif effects & {1, 28, 30}:
            cls = "damage"
        else:
            cls = "other"
        m[c["template"]] = cls
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-talent", type=int, default=2000)
    args = ap.parse_args()
    cls_of = load_chip_classes()

    # per turn bucket (1-2, 3-5, 6-9, 10+): class counts split by outcome
    won = defaultdict(Counter)
    lost = defaultdict(Counter)
    eng_won = defaultdict(list)
    eng_lost = defaultdict(list)
    n_won = n_lost = 0
    talents = []

    files = sorted(CACHE.glob("*.json"))
    for p in files:
        try:
            d = json.load(open(p))
        except Exception:
            continue
        data = d.get("data")
        if isinstance(data, str):
            data = json.loads(data)
        rep = d.get("report") or {}
        leeks = [l for l in data.get("leeks", []) if not l.get("summon")]
        if len(leeks) != 2:
            continue
        ours = [l for l in leeks if l["name"] in OURS]
        if not ours:
            continue
        us, foe = ours[0], [l for l in leeks if l["team"] != ours[0]["team"]][0]
        # talent from report
        foe_talent = None
        for side in ("leeks1", "leeks2"):
            for l in rep.get(side, []):
                if l.get("name") == foe["name"]:
                    foe_talent = l.get("talent")
        if foe_talent is None or foe_talent < args.min_talent:
            continue
        talents.append(foe_talent)
        w = d.get("winner")
        foe_won = (w == foe["team"])
        if w not in (1, 2):
            continue
        if foe_won:
            n_won += 1
        else:
            n_lost += 1

        turn = 0
        cells = {us["id"]: us.get("cellPos"), foe["id"]: foe.get("cellPos")}
        cur = None
        for a in data.get("actions", []):
            c = a[0]
            if c == A_TURN:
                turn = a[1]
            elif c == A_LEEKTURN:
                cur = a[1]
            elif c == A_MOVE and a[1] in cells:
                cells[a[1]] = a[2]
                if cur == foe["id"]:
                    dd = dist(cells[us["id"]], cells[foe["id"]])
                    if dd is not None:
                        (eng_won if foe_won else eng_lost)[min(turn, 10)].append(dd)
            elif c in (A_CHIP, A_CHIP2) and cur == foe["id"]:
                bucket = 1 if turn <= 2 else (2 if turn <= 5 else (3 if turn <= 9 else 4))
                cls = cls_of.get(a[1], "other")
                (won if foe_won else lost)[bucket][cls] += 1
            elif c == A_SETWEAPON and cur == foe["id"]:
                bucket = 1 if turn <= 2 else (2 if turn <= 5 else (3 if turn <= 9 else 4))
                (won if foe_won else lost)[bucket]["weaponplay"] += 1

    print(f"opponents >= {args.min_talent} talent: they WON {n_won} fights, LOST {n_lost} (vs us)")
    labels = {1: "T1-2", 2: "T3-5", 3: "T6-9", 4: "T10+"}
    classes = ["shield", "heal", "buff", "damage", "poison", "denial", "mobility", "summon", "weaponplay", "other"]
    print(f"\n{'turn':<6}{'class':<12}{'won%':>8}{'lost%':>8}{'delta':>8}")
    for b in (1, 2, 3, 4):
        tw = sum(won[b].values()) or 1
        tl = sum(lost[b].values()) or 1
        for cls in classes:
            wp = 100 * won[b][cls] / tw
            lp = 100 * lost[b][cls] / tl
            if wp + lp > 0.5:
                flag = " <<<" if abs(wp - lp) >= 3 else ""
                print(f"{labels[b]:<6}{cls:<12}{wp:>7.1f}%{lp:>7.1f}%{wp-lp:>+7.1f}{flag}")
    print(f"\nengagement distance by turn (median, foe won vs lost):")
    for t in sorted(set(eng_won) | set(eng_lost)):
        wv = sorted(eng_won.get(t, []))
        lv = sorted(eng_lost.get(t, []))
        wm = wv[len(wv) // 2] if wv else "-"
        lm = lv[len(lv) // 2] if lv else "-"
        print(f"  T{t:>2}: {wm} vs {lm}  (n={len(wv)}/{len(lv)})")


if __name__ == "__main__":
    main()
