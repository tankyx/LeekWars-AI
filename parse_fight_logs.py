import json

# Load the logs
with open("fight_logs_49596248_method1.json", "r") as f:
    logs_data = json.load(f)

# Load fight data to get entity names
with open("fight_data_49596248_full.json", "r") as f:
    fight_data = json.load(f)

# Build entity name map
entity_names = {}
for leek in fight_data.get('leeks1', []) + fight_data.get('leeks2', []):
    entity_names[leek['id']] = leek['name']

print("="*80)
print("BOSS FIGHT - GRAAL SCENARIO LOG ANALYSIS")
print("="*80)

# Parse logs structure: {farmer_id: {action_id: [log_entries]}}
all_logs = []

for farmer_id, farmer_logs in logs_data.items():
    for action_id, action_logs in farmer_logs.items():
        for log in action_logs:
            if isinstance(log, list) and len(log) >= 3:
                all_logs.append({
                    'action_id': int(action_id),
                    'farmer_id': farmer_id,
                    'leek_id': log[0],
                    'type': log[1],
                    'message': log[2],
                    'raw': log
                })

# Sort by action_id
all_logs.sort(key=lambda x: x['action_id'])

# Print logs
current_turn = 0
for log in all_logs:
    message = str(log['message'])
    leek_id = log['leek_id']
    leek_name = entity_names.get(leek_id, f"Entity_{leek_id}")
    
    # Detect turn changes
    if "===" in message and "TURN" in message.upper():
        print(f"\n{'='*80}")
        print(f"{message}")
        print(f"{'='*80}\n")
    else:
        print(f"[{leek_name}] {message}")

print("\n" + "="*80)
print("END OF LOGS")
print("="*80)
