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

# Track crystal positions
crystal_positions = {
    'red': [],
    'blue': [],
    'yellow': [],
    'green': []
}

print("="*80)
print("CRYSTAL MOVEMENT HISTORY")
print("="*80)

for log in all_logs:
    msg = log['message']

    # Track position updates
    if 'Cell pos was' in msg and 'crystal' in msg:
        leek_name = entity_names.get(log['leek_id'], f"Entity_{log['leek_id']}")
        print(f"[{leek_name}] {msg}")

    # Track chip usage
    if 'Using BOXING_GLOVE' in msg or 'Using GRAPPLE' in msg:
        leek_name = entity_names.get(log['leek_id'], f"Entity_{log['leek_id']}")
        print(f"[{leek_name}] {msg}")

print("\n" + "="*80)
print("FAILURE MESSAGES (why we can't push)")
print("="*80)

for log in all_logs:
    msg = log['message']

    if ('Failed to move' in msg or 'Too far' in msg or
        'Player on wrong side' in msg or 'No valid push' in msg or
        'Could not move crystal' in msg or 'already aligned' in msg):
        leek_name = entity_names.get(log['leek_id'], f"Entity_{log['leek_id']}")
        print(f"[{leek_name}] {msg}")

print("\n" + "="*80)
print("TARGET CALCULATIONS")
print("="*80)

for log in all_logs:
    msg = log['message']
    if 'Working on' in msg and 'target=' in msg:
        leek_name = entity_names.get(log['leek_id'], f"Entity_{log['leek_id']}")
        print(f"[{leek_name}] {msg}")
        break  # Just show first one
