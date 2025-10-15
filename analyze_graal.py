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

# Find crystal assignments and target cells
print("="*80)
print("CRYSTAL ASSIGNMENT ANALYSIS")
print("="*80)

for log in all_logs:
    msg = log['message']
    if 'My assigned crystal' in msg or 'Target cell for' in msg or 'checkCrystalAlignment' in msg:
        leek_name = entity_names.get(log['leek_id'], f"Entity_{log['leek_id']}")
        print(f"[{leek_name}] {msg}")

print("\n" + "="*80)
print("FIRST PUSH ATTEMPTS")
print("="*80)

push_count = 0
for log in all_logs:
    msg = log['message']
    if 'Using BOXING_GLOVE' in msg or 'Push direction' in msg or 'moveCrystalToAlignment' in msg:
        if push_count < 30:
            leek_name = entity_names.get(log['leek_id'], f"Entity_{log['leek_id']}")
            print(f"[{leek_name}] {msg}")
            push_count += 1
