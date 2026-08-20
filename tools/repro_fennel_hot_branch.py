#!/usr/bin/env python3
"""Force the fight-52984834 'hot' branch: KG at 55, yellow at 253, passive
army leeks ringing the whole enclave so every teleport stand is hot.
Pre-fix expectation: KG frozen ('closing on ... hot d=' says, zero moves).
Post-fix expectation: KG walks out of the cul-de-sac toward the crystal."""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import local_test as lt

PLAYER_CELLS = {"KurtGodel": 55, "AdaLovelace": 566, "EdsgerDijkstra": 404, "MargaretHamilton": 228}
BOSS_CELLS = {"graal": 102, "blue_crystal": 303, "green_crystal": 242, "yellow_crystal": 253, "red_crystal": 329}
# Passive army ring: covers every stand within ~12 of KG's pocket so that
# nearestArmyDistFrom(stand, army) <= 10 everywhere (all stands hot).
ARMY_CELLS = [30, 66, 84, 117, 119, 157, 193, 235, 270, 318, 342, 411]

configs = lt.load_configs()
scenario = lt.build_boss_scenario(configs, seed=12345)
for e in scenario["entities"][0]:
    if e["name"] in PLAYER_CELLS:
        e["cell"] = PLAYER_CELLS[e["name"]]
for e in scenario["entities"][1]:
    if e["name"] in BOSS_CELLS:
        e["cell"] = BOSS_CELLS[e["name"]]

# Append passive army entities to team 2
next_id = max(e["id"] for t in scenario["entities"] for e in t) + 1
farmer_id = scenario["entities"][1][0]["farmer"]
for i, cell in enumerate(ARMY_CELLS):
    # army0 keeps Divine Protection up so the AI stays in PUZZLE phase
    # (armyHasDivineProtection(): no type-59 effect on army => graal declared dead)
    is_caster = (i == 0)
    scenario["entities"][1].append({
        "id": next_id + i,
        "ai": "test/ai/cast_divine.lk" if is_caster else "test/ai/do_nothing.lk",
        "name": f"army{i}",
        "type": 0,
        "farmer": farmer_id,
        "team": 2,
        "level": 301,
        "life": 10000,
        "cores": 1, "ram": 1,
        "tp": 10 if is_caster else 0,
        "mp": 0,
        "strength": 0, "magic": 0, "agility": 0, "wisdom": 0,
        "resistance": 500, "science": 0, "frequency": 100,
        "weapons": [], "chips": [419] if is_caster else [],
        "cell": cell,
    })
scenario["map"]["team1"] = [e["cell"] for e in scenario["entities"][0]]
scenario["map"]["team2"] = [e["cell"] for e in scenario["entities"][1]]

result = lt.run_fight(scenario, verbose=True)
if "error" in result:
    print("ERROR:", result["error"])
    sys.exit(1)

turn = 0
kg_moves = []
kg_says = []
for a in result["actions"]:
    if not isinstance(a, list) or not a:
        continue
    if a[0] == 6:
        turn += 1
    elif a[0] == 10 and a[1] == 2:
        kg_moves.append((turn, a[2]))
    elif a[0] == 203:
        m = str(a[1])
        if "closing on" in m or "DONE" in m or "INV" in m or "ALL DONE" in m:
            kg_says.append((turn, m))

print("KG moves:", kg_moves[:20])
print("KG say stream (first 20):")
for t, m in kg_says[:20]:
    print(f"  T{t:2d} {m[:130]}")
frozen_turns = turn - len(kg_moves)
print(f"total turns={turn}, KG moved {len(kg_moves)} times")
