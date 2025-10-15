import requests
import json

fight_id = 49596721

session = requests.Session()
session.post("https://leekwars.com/api/farmer/login-token", data={"login": "tanguy.pedrazzoli@gmail.com", "password": "tanguy0211"})

# Get fight data
url = f"https://leekwars.com/api/fight/get/{fight_id}"
resp = session.get(url)
fight_data = resp.json()

# Get logs
url2 = f"https://leekwars.com/api/fight/get-logs/{fight_id}"
resp2 = session.get(url2)
logs = resp2.json()

# Helper functions
def getCellX(cell):
    return (cell % 18) - 17

def getCellY(cell):
    return 17 - (cell // 18)

def getCellFromXY(x, y):
    return (17 - y) * 18 + (x + 17)

# Parse entity names
entity_names = {}
for leek in fight_data.get('leeks1', []) + fight_data.get('leeks2', []):
    entity_names[leek['id']] = leek['name']

# Parse logs
all_logs = []
for farmer_id, farmer_logs in logs.items():
    for action_id, action_logs in farmer_logs.items():
        for log in action_logs:
            if isinstance(log, list) and len(log) >= 3:
                all_logs.append({
                    'action_id': int(action_id),
                    'leek_id': log[0],
                    'message': str(log[2])
                })

all_logs.sort(key=lambda x: x['action_id'])

# Get grail position from logs
grail_pos = 243
grail_x, grail_y = getCellX(grail_pos), getCellY(grail_pos)

print("="*80)
print(f"GRAIL POSITION: {grail_pos} ({grail_x},{grail_y})")
print("="*80)

# Expected target positions for each crystal
print("\nEXPECTED TARGET POSITIONS:")
print("-" * 80)
colors = ['red', 'blue', 'yellow', 'green']
for color in colors:
    if color == 'red':
        # Below grail (same X, Y-3)
        tx, ty = grail_x, grail_y - 3
        print(f"{color.upper()}: Below grail → ({tx},{ty}) = cell {getCellFromXY(tx, ty)} [same X, Y<grail]")
    elif color == 'blue':
        # Right of grail (X+3, same Y)
        tx, ty = grail_x + 3, grail_y
        print(f"{color.upper()}: Right of grail → ({tx},{ty}) = cell {getCellFromXY(tx, ty)} [X>grail, same Y]")
    elif color == 'yellow':
        # Left of grail (X-3, same Y)
        tx, ty = grail_x - 3, grail_y
        print(f"{color.upper()}: Left of grail → ({tx},{ty}) = cell {getCellFromXY(tx, ty)} [X<grail, same Y]")
    elif color == 'green':
        # Above grail (same X, Y+3)
        tx, ty = grail_x, grail_y + 3
        print(f"{color.upper()}: Above grail → ({tx},{ty}) = cell {getCellFromXY(tx, ty)} [same X, Y>grail]")

# Find assignments
print("\n" + "="*80)
print("LEEK ASSIGNMENTS AND ACTUAL TARGETS")
print("="*80)

for log in all_logs:
    msg = log['message']
    if 'Assigned' in msg and 'crystal' in msg:
        leek_name = entity_names.get(log['leek_id'], f"Entity_{log['leek_id']}")
        print(f"[{leek_name}] {msg}")

print("\n" + "="*80)
print("ACTUAL PUSH TARGETS FROM LOGS")
print("="*80)

for log in all_logs[:100]:  # First 100 logs
    msg = log['message']
    if 'moveCrystalToAlignment' in msg:
        leek_name = entity_names.get(log['leek_id'], f"Entity_{log['leek_id']}")
        print(f"[{leek_name}] {msg}")
