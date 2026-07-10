#!/usr/bin/env python3
"""Pull recent solo fights of top-ladder leeks and compress each into a
per-turn strategy trace (casts, damage flow, heals, movement) plus summary
metrics. Used to reverse-engineer top-meta play patterns per archetype.

Usage:
    python3 tools/analyze_top_fights.py <leek_id> [n_fights]
"""
import json
import sys
import time
from collections import Counter, defaultdict

import requests

sys.path.insert(0, "/home/ubuntu/LeekWars-AI/tools")
from config_loader import load_credentials

GEN_DATA = "/home/ubuntu/leek-wars-generator/data"


def load_templates():
    chips = json.load(open(f"{GEN_DATA}/chips.json"))
    weapons = json.load(open(f"{GEN_DATA}/weapons.json"))
    return ({c["template"]: c["name"] for c in chips.values()},
            {w["template"]: w["name"] for w in weapons.values()})


def analyze_fight(session, fid, focus_id, chip_tpl, weap_tpl):
    d = session.get(f"https://leekwars.com/api/fight/get/{fid}").json()
    data = d.get("data")
    if isinstance(data, str):
        data = json.loads(data)
    if not data:
        return None
    leeks = data.get("leeks", [])
    names = {l["id"]: l.get("name", "?") for l in leeks}
    # entity id of the focus leek: match by name is unreliable; server fight
    # 'leeks' entries carry the real leek id in 'id'? They carry FIGHT entity
    # ids. leeks1/leeks2 in the outer fight give real ids in order.
    focus_ent = None
    for l in leeks:
        if l.get("owner_name") or True:
            pass
    # outer fight: leeks1/leeks2 are lists of dicts with real leek ids
    ent_order = [l["id"] for l in leeks]
    real_ids = []
    for side in ("leeks1", "leeks2"):
        for e in d.get(side, []):
            real_ids.append(e["id"] if isinstance(e, dict) else e)
    # fight entities appear in same order as leeks1+leeks2
    for ent, rid in zip(ent_order, real_ids):
        if rid == focus_id:
            focus_ent = ent
    if focus_ent is None:
        return None

    winner = d.get("winner")
    on_side1 = any((e["id"] if isinstance(e, dict) else e) == focus_id
                   for e in d.get("leeks1", []))
    res = "D" if winner == 0 else ("W" if (winner == 1) == on_side1 else "L")

    turns = defaultdict(lambda: {"casts": [], "wpn": 0, "moves": 0,
                                 "dmg_out": 0, "dmg_in": 0, "heal": 0,
                                 "poison_out": 0})
    cur = None
    turn = 0
    opp_names = [n for e, n in names.items() if e != focus_ent]
    for a in data.get("actions", []):
        if not isinstance(a, list):
            continue
        code = a[0]
        if code == 6:
            turn = a[1]
        elif code == 7:
            cur = a[1]
        elif code == 12 and cur == focus_ent:
            turns[turn]["casts"].append(chip_tpl.get(a[1], f"chip#{a[1]}"))
        elif code == 8 and cur == focus_ent:
            turns[turn]["wpn"] += 1
        elif code == 10 and cur == focus_ent:
            turns[turn]["moves"] += 1
        elif code == 101:
            victim, dmg = a[1], a[2]
            if victim == focus_ent:
                turns[turn]["dmg_in"] += dmg
            elif cur == focus_ent:
                turns[turn]["dmg_out"] += dmg
        elif code == 110:
            victim, dmg = a[1], a[2]
            if victim != focus_ent:
                turns[turn]["poison_out"] += dmg
            else:
                turns[turn]["dmg_in"] += dmg
        elif code == 302 and cur == focus_ent and len(a) > 6:
            # heal effect on self: effect id 3? decode_server_fight maps 3=HEAL
            if a[5] == 3 and a[2] == focus_ent:
                turns[turn]["heal"] += a[6] or 0

    n_turns = max(turns) if turns else 0
    all_casts = Counter()
    for t in turns.values():
        all_casts.update(t["casts"])
    return {
        "fight": fid, "result": res, "turns": n_turns,
        "opp": "/".join(opp_names),
        "trace": {t: turns[t] for t in sorted(turns)},
        "casts": dict(all_casts.most_common()),
    }


def main():
    leek_id = int(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    email, pw = load_credentials(account="main")
    s = requests.Session()
    s.post("https://leekwars.com/api/farmer/login-token",
           data={"login": email, "password": pw})
    chip_tpl, weap_tpl = load_templates()

    hist = s.get(f"https://leekwars.com/api/history/get-leek-history/{leek_id}"
                 ).json().get("fights", [])
    solo = [f for f in hist
            if len(f.get("leeks1", [])) == 1 and len(f.get("leeks2", [])) == 1]
    print(f"leek {leek_id}: {len(solo)} recent solo fights")
    for f in solo[:n]:
        time.sleep(0.3)
        r = analyze_fight(s, f["id"], leek_id, chip_tpl, weap_tpl)
        if not r:
            continue
        print(f"\n### F{r['fight']} {r['result']} in {r['turns']}T vs {r['opp']}")
        print(f"  casts: {r['casts']}")
        for t, tr in r["trace"].items():
            if not (tr["casts"] or tr["wpn"] or tr["dmg_out"] or tr["dmg_in"]):
                continue
            line = (f"  T{t:2}: out={tr['dmg_out']:4} psn={tr['poison_out']:4} "
                    f"in={tr['dmg_in']:4} heal={tr['heal']:4} wpn={tr['wpn']} "
                    f"mv={tr['moves']} " + ",".join(tr["casts"]))
            print(line[:150])


if __name__ == "__main__":
    main()
