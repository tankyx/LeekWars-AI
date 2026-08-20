#!/usr/bin/env python3
"""Re-analyze with correct turn-based entity tracking."""
import requests, sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_credentials

BASE_URL = "https://leekwars.com/api"
FIGHT_ID = 52609193

email, password = load_credentials(account="main")
session = requests.Session()
session.post(f"{BASE_URL}/farmer/login-token", data={"login": email, "password": password})

r = session.get(f"{BASE_URL}/fight/get/{FIGHT_ID}")
data = r.json()
actions = data['data']['actions']

current_entity = 0  # track whose turn
our_chips = []
our_weapons = []
their_chips = []
their_weapons = []
our_dmg = 0
their_dmg = 0
our_moves = 0
their_moves = 0

for act in actions:
    if not isinstance(act, list) or len(act) < 2: continue
    atype = act[0]
    if atype == 7:  # LEEK_TURN
        current_entity = act[1]
    elif atype == 10:  # MOVE
        if current_entity == 1: our_moves += 1
        else: their_moves += 1
    elif atype == 12:  # USE_CHIP
        chip_id = act[1]
        if current_entity == 1: our_chips.append(chip_id)
        else: their_chips.append(chip_id)
    elif atype == 16:  # USE_WEAPON
        if current_entity == 1: our_weapons.append(act[1])
        else: their_weapons.append(act[1])
    elif atype == 101:  # LIFE_LOST
        dmg = act[2] if len(act) > 2 else 0
        entity = act[1]
        if entity == 1: their_dmg += dmg  # damage to us
        else: our_dmg += dmg  # damage to them
    elif atype == 110:  # POISON_DAMAGE
        entity = act[1]
        dmg = act[2] if len(act) > 2 else 0
        if entity == 1: their_dmg += dmg

print(f"Fight {FIGHT_ID} — {len(actions)} actions")
print(f"\nOur actions: {our_moves} moves, {len(our_chips)} chips, {len(our_weapons)} weapons")
print(f"  Chip IDs: {our_chips}")
print(f"  Weapon IDs: {our_weapons}")
print(f"\nTheir actions: {their_moves} moves, {len(their_chips)} chips, {len(their_weapons)} weapons")
print(f"  Chip IDs: {their_chips[:30]}")
print(f"  Weapon IDs: {their_weapons}")
print(f"\nDamage dealt: {our_dmg}, Damage taken: {their_dmg}")

# Look at first few turns
print("\n=== TURN-BY-TURN ===")
turn = 0
our_turn_actions = []
their_turn_actions = []
current_entity = 0
for act in actions:
    if not isinstance(act, list) or len(act) < 2: continue
    atype = act[0]
    if atype == 6:  # NEW_TURN
        if turn > 0:
            our_str = f"{len([a for a in our_turn_actions if a[0]==12])}C/{len([a for a in our_turn_actions if a[0]==16])}W"
            their_str = f"{len([a for a in their_turn_actions if a[0]==12])}C/{len([a for a in their_turn_actions if a[0]==16])}W"
            print(f"  T{turn}: us={our_str}, them={their_str}")
        turn += 1
        our_turn_actions = []
        their_turn_actions = []
    elif atype == 7:
        current_entity = act[1]
    else:
        if current_entity == 1: our_turn_actions.append(act)
        else: their_turn_actions.append(act)

# Print last turn
if turn > 0:
    our_str = f"{len([a for a in our_turn_actions if a[0]==12])}C/{len([a for a in our_turn_actions if a[0]==16])}W"
    their_str = f"{len([a for a in their_turn_actions if a[0]==12])}C/{len([a for a in their_turn_actions if a[0]==16])}W"
    print(f"  T{turn}: us={our_str}, them={their_str}")
