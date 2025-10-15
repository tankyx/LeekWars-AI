import requests
import json

fight_id = 49611081

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
print(f"TOTAL LOGS: {len(all_logs)}")
print("="*80)

print("\nFIRST 20 LOGS (any message):")
for log in all_logs[:20]:
    msg = log['message']
    leek_name = entity_names.get(log['leek_id'], f"Entity_{log['leek_id']}")
    print(f"[{leek_name}] {msg}")

print("\n" + "="*80)
print("BOSS STRATEGY MESSAGES")
print("="*80)

for log in all_logs[:500]:  # First 500 logs
    msg = log['message']
    if ('PUZZLE' in msg or 'Working on' in msg or 'Using BOXING' in msg or
        'Using GRAPPLE' in msg or 'moveCrystalToAlignment' in msg or
        'needsRepositioning' in msg or 'Player at' in msg or
        'Strategy: PUSH' in msg or 'Strategy: PULL' in msg or
        'Searching for push' in msg or 'Found valid push' in msg):
        leek_name = entity_names.get(log['leek_id'], f"Entity_{log['leek_id']}")
        print(f"[{leek_name}] {msg}")
