import json

with open("fight_logs_49596448.json") as f:
    logs = json.load(f)

with open("fight_data_49596448.json") as f:
    fight_data = json.load(f)

entity_names = {}
for leek in fight_data.get('leeks1', []) + fight_data.get('leeks2', []):
    entity_names[leek['id']] = leek['name']

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

# Check for chip usage (GRAPPLE, BOXING_GLOVE)
for log in all_logs:
    msg = str(log['message'])
    if 'GRAPPLE' in msg or 'BOXING' in msg or 'Using chip' in msg or 'pull' in msg.lower() or 'push' in msg.lower():
        leek_name = entity_names.get(log['leek_id'], f"Entity_{log['leek_id']}")
        print(f"[{leek_name}] {msg}")
