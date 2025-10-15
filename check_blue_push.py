import requests
import json

fight_id = 49596810

session = requests.Session()
session.post("https://leekwars.com/api/farmer/login-token", data={"login": "tanguy.pedrazzoli@gmail.com", "password": "tanguy0211"})

# Get logs
url = f"https://leekwars.com/api/fight/get-logs/{fight_id}"
resp = session.get(url)
logs = resp.json()

# Get fight data
url2 = f"https://leekwars.com/api/fight/get/{fight_id}"
resp2 = session.get(url2)
fight_data = resp2.json()

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

def getCellX(cell):
    return (cell % 18) - 17

def getCellY(cell):
    return 17 - (cell // 18)

print("="*80)
print("BLUE CRYSTAL FIRST PUSH DETAILS")
print("="*80)

# Find the first blue crystal push
found_push = False
for i, log in enumerate(all_logs):
    msg = log['message']

    # Find the push
    if 'Using BOXING_GLOVE to push crystal toward 100' in msg:
        leek_name = entity_names.get(log['leek_id'], f"Entity_{log['leek_id']}")
        print(f"\n[{leek_name}] {msg}")

        # Look backwards for moveCrystalToAlignment message
        for j in range(i-1, max(0, i-20), -1):
            prev_msg = all_logs[j]['message']
            if 'moveCrystalToAlignment' in prev_msg or 'Distance to crystal' in prev_msg or 'Push direction' in prev_msg:
                prev_leek = entity_names.get(all_logs[j]['leek_id'], f"Entity_{all_logs[j]['leek_id']}")
                print(f"[{prev_leek}] {prev_msg}")

        found_push = True
        break

if found_push:
    print("\n" + "="*80)
    print("COORDINATE ANALYSIS")
    print("="*80)
    print(f"Blue crystal at 134: ({getCellX(134)}, {getCellY(134)})")
    print(f"Blue crystal moved to 100: ({getCellX(100)}, {getCellY(100)})")
    print(f"Blue target 297: ({getCellX(297)}, {getCellY(297)})")
    print(f"Push target cell 100: ({getCellX(100)}, {getCellY(100)})")
    print(f"\nDirection from 134 to 100:")
    print(f"  ΔX = {getCellX(100) - getCellX(134)} (should be +17)")
    print(f"  ΔY = {getCellY(100) - getCellY(134)} (should be -19)")
