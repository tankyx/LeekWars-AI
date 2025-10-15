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

print("="*80)
print("BLUE CRYSTAL DIRECTION CALCULATION")
print("="*80)

for log in all_logs:
    msg = log['message']
    if 'blue' in msg.lower() and ('Push direction' in msg or 'Working on blue' in msg or
                                    'calculateCrystalTargetPosition: color=blue' in msg or
                                    'BLUE: Right' in msg or 'Using BOXING_GLOVE' in msg):
        leek_name = entity_names.get(log['leek_id'], f"Entity_{log['leek_id']}")
        print(f"[{leek_name}] {msg}")
        if 'Using BOXING_GLOVE' in msg:
            break  # Stop after first push

print("\n" + "="*80)
print("RED CRYSTAL STUCK MESSAGES")
print("="*80)

count = 0
for log in all_logs:
    msg = log['message']
    if 'red' in msg.lower() and ('Working on red' in msg or 'Push direction' in msg or
                                   'Using BOXING_GLOVE' in msg or 'Distance ' in msg):
        leek_name = entity_names.get(log['leek_id'], f"Entity_{log['leek_id']}")
        print(f"[{leek_name}] {msg}")
        count += 1
        if count >= 30:
            break
