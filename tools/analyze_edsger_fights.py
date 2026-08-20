#!/usr/bin/env python3
"""Analyze EdsgerDijkstra vs mamax49poireau fights with correct data path."""
import requests, sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_credentials

BASE_URL = "https://leekwars.com/api"
FIGHT_IDS = [52609193, 52609196, 52609197, 52609198, 52609199]

email, password = load_credentials(account="main")
session = requests.Session()
session.post(f"{BASE_URL}/farmer/login-token", data={"login": email, "password": password})

# Opponent info
r = session.get(f"{BASE_URL}/leek/get/97")
opp = r.json()
print(f"Opponent: {opp.get('name','?')} L{opp.get('level','?')} T{opp.get('talent','?')}")
print(f"  STR:{opp.get('strength')} MAG:{opp.get('magic')} AGI:{opp.get('agility')} WIS:{opp.get('wisdom')} RES:{opp.get('resistance')} SCI:{opp.get('science')}")
print(f"  Chips: {len(opp.get('chips',[]))}, Weapons: {len(opp.get('weapons',[]))}")

# Our leek info
r = session.get(f"{BASE_URL}/leek/get/129288")
our = r.json()
print(f"\nOur leek: {our.get('name','?')} L{our.get('level','?')} T{our.get('talent','?')}")
print(f"  STR:{our.get('strength')} MAG:{our.get('magic')} AGI:{our.get('agility')} WIS:{our.get('wisdom')} RES:{our.get('resistance')} SCI:{our.get('science')}")

print("\n=== FIGHTS ===")
for fid in FIGHT_IDS:
    time.sleep(0.3)
    r = session.get(f"{BASE_URL}/fight/get/{fid}")
    data = r.json()
    winner = data.get("winner")
    result = "WIN" if winner == 1 else "LOSS"
    
    # Actions are in data.data.actions
    fight_data = data.get("data", {})
    actions = fight_data.get("actions", [])
    duration = fight_data.get("duration", len(actions))
    
    # Get dead info
    dead = fight_data.get("dead", [])
    
    our_acts = {"chip": 0, "weapon": 0, "move": 0, "set_weapon": 0}
    their_acts = {"chip": 0, "weapon": 0, "move": 0, "set_weapon": 0}
    our_dmg = 0
    their_dmg = 0
    bugs = 0
    
    for act in actions:
        if not isinstance(act, list) or len(act) < 2: continue
        atype = act[0]
        entity = act[1] if len(act) > 1 else 0
        if atype == 10:  # MOVE
            if entity == 1: our_acts["move"] += 1
            else: their_acts["move"] += 1
        elif atype == 12:  # USE_CHIP
            chip_id = act[2] if len(act) > 2 else "?"
            if entity == 1: our_acts["chip"] += 1
            else: their_acts["chip"] += 1
        elif atype == 13:  # SET_WEAPON
            if entity == 1: our_acts["set_weapon"] += 1
            else: their_acts["set_weapon"] += 1
        elif atype == 16:  # USE_WEAPON
            if entity == 1: our_acts["weapon"] += 1
            else: their_acts["weapon"] += 1
        elif atype == 1002:  # BUG
            if entity == 1: bugs += 1
        elif atype == 101:  # LIFE_LOST
            dmg = act[2] if len(act) > 2 else 0
            if entity == 1: their_dmg += dmg
            else: our_dmg += dmg
    
    print(f"\nFight {fid}: {result} ({len(actions)} actions)")
    print(f"  Us: {our_acts['chip']} chips, {our_acts['weapon']} weapons, {our_acts['move']} moves, {our_acts['set_weapon']} swaps" + (f", {bugs} BUGS!" if bugs > 0 else ""))
    print(f"  Them: {their_acts['chip']} chips, {their_acts['weapon']} weapons, {their_acts['move']} moves, {their_acts['set_weapon']} swaps")
    print(f"  Dmg dealt: {our_dmg}, Dmg taken: {their_dmg}")
    if dead:
        print(f"  Dead order: {dead}")
