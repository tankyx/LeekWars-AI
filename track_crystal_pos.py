import requests
import json

fight_id = 49596874

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

# Track crystal positions through "Working on" messages
crystal_history = {
    'red': [],
    'blue': [],
    'yellow': [],
    'green': []
}

targets = {
    'red': 192,
    'blue': 297,
    'yellow': 189,
    'green': 294
}

for log in all_logs:
    msg = log['message']
    for color in ['red', 'blue', 'yellow', 'green']:
        if f'Working on {color} crystal: current=' in msg:
            # Extract current position
            parts = msg.split('current=')[1].split(',')[0]
            current_pos = int(parts)
            if len(crystal_history[color]) == 0 or crystal_history[color][-1] != current_pos:
                crystal_history[color].append(current_pos)

print("="*80)
print("CRYSTAL MOVEMENT HISTORY")
print("="*80)

for color in ['red', 'blue', 'yellow', 'green']:
    print(f"\n{color.upper()} crystal (target={targets[color]}):")
    print(f"  Positions: {crystal_history[color]}")
    if len(crystal_history[color]) > 0:
        final_pos = crystal_history[color][-1]
        print(f"  Final: {final_pos}, Target: {targets[color]}, Match: {final_pos == targets[color]}")
        if len(crystal_history[color]) > 1 and crystal_history[color][-1] == crystal_history[color][-2]:
            print(f"  ⚠️  STUCK - same position for last 2 readings")
