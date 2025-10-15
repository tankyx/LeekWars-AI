import requests
import json

fight_id = 49596721

session = requests.Session()
session.post("https://leekwars.com/api/farmer/login-token", data={"login": "tanguy.pedrazzoli@gmail.com", "password": "tanguy0211"})

# Get logs
url = f"https://leekwars.com/api/fight/get-logs/{fight_id}"
resp = session.get(url)
logs = resp.json()

# Parse logs to find actual debug output from LeekScript
all_logs = []
for farmer_id, farmer_logs in logs.items():
    for action_id, action_logs in farmer_logs.items():
        for log in action_logs:
            if isinstance(log, list) and len(log) >= 3:
                msg = str(log[2])
                # Look for target cell calculations
                if 'target=' in msg or 'Target cell for' in msg:
                    print(msg)

print("\n" + "="*80)
print("Looking for Working on messages with target cells:")
print("="*80)

for farmer_id, farmer_logs in logs.items():
    for action_id, action_logs in farmer_logs.items():
        for log in action_logs:
            if isinstance(log, list) and len(log) >= 3:
                msg = str(log[2])
                if 'Working on' in msg and 'target=' in msg:
                    print(msg)
                    break  # Only show first one per entity
