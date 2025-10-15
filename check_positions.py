import requests
import json

fight_id = 49596721

session = requests.Session()
session.post("https://leekwars.com/api/farmer/login-token", data={"login": "tanguy.pedrazzoli@gmail.com", "password": "tanguy0211"})

# Get fight data
url = f"https://leekwars.com/api/fight/get/{fight_id}"
resp = session.get(url)
fight_data = resp.json()

# Helper function to convert cell to X,Y (LeekWars formula)
def getCellX(cell):
    return (cell % 18) - 17

def getCellY(cell):
    return 17 - (cell // 18)

# Analyze the crystal movements
print("="*80)
print("CRYSTAL POSITION ANALYSIS")
print("="*80)

movements = [
    ("Entity_0", 328, 192, 277),  # crystal, target, pushed_to
    ("Entity_2", 134, 297, 100),
    ("Entity_1", 102, 189, 192),
]

for entity, crystal, target, pushed_to in movements:
    cx, cy = getCellX(crystal), getCellY(crystal)
    tx, ty = getCellX(target), getCellY(target)
    px, py = getCellX(pushed_to), getCellY(pushed_to)

    print(f"\n{entity}:")
    print(f"  Crystal: {crystal} ({cx},{cy})")
    print(f"  Target:  {target} ({tx},{ty})")
    print(f"  Pushed:  {pushed_to} ({px},{py})")

    # Calculate directions
    dir_to_target_x = 1 if tx > cx else (-1 if tx < cx else 0)
    dir_to_target_y = 1 if ty > cy else (-1 if ty < cy else 0)

    dir_pushed_x = 1 if px > cx else (-1 if px < cx else 0)
    dir_pushed_y = 1 if py > cy else (-1 if py < cy else 0)

    print(f"  Direction to target: X={dir_to_target_x}, Y={dir_to_target_y}")
    print(f"  Direction pushed:    X={dir_pushed_x}, Y={dir_pushed_y}")
    print(f"  Match: {dir_to_target_x == dir_pushed_x and dir_to_target_y == dir_pushed_y}")

# Now let's check what the grail position should be
print("\n" + "="*80)
print("GRAIL AND CRYSTAL ALIGNMENT")
print("="*80)

# Get logs to find grail position
url2 = f"https://leekwars.com/api/fight/get-logs/{fight_id}"
resp2 = session.get(url2)
logs = resp2.json()

all_logs = []
for farmer_id, farmer_logs in logs.items():
    for action_id, action_logs in farmer_logs.items():
        for log in action_logs:
            if isinstance(log, list) and len(log) >= 3:
                msg = str(log[2])
                if 'grail' in msg.lower() or 'Graal' in msg:
                    print(f"  {msg}")
