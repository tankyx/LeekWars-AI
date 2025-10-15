import requests
import json

fight_id = 49596636

session = requests.Session()

# Login
login_url = "https://leekwars.com/api/farmer/login-token"
login_data = {
    "login": "tanguy.pedrazzoli@gmail.com",
    "password": "tanguy0211"
}

response = session.post(login_url, data=login_data)
if response.status_code == 200:
    print(f"✅ Logged in")

# Get logs
url = f"https://leekwars.com/api/fight/get-logs/{fight_id}"
resp = session.get(url)
if resp.status_code == 200:
    logs = resp.json()
    with open(f"fight_logs_{fight_id}.json", "w") as f:
        json.dump(logs, f, indent=2)
    print(f"✅ Saved logs")

# Get fight data
url2 = f"https://leekwars.com/api/fight/get/{fight_id}"
resp2 = session.get(url2)
if resp2.status_code == 200:
    fight_data = resp2.json()
    with open(f"fight_data_{fight_id}.json", "w") as f:
        json.dump(fight_data, f, indent=2)
    
    # Build entity names
    entity_names = {}
    for leek in fight_data.get('leeks1', []) + fight_data.get('leeks2', []):
        entity_names[leek['id']] = leek['name']
    
    # Parse logs
    with open(f"fight_logs_{fight_id}.json", "r") as f:
        logs_data = json.load(f)
    
    all_logs = []
    for farmer_id, farmer_logs in logs_data.items():
        for action_id, action_logs in farmer_logs.items():
            for log in action_logs:
                if isinstance(log, list) and len(log) >= 3:
                    all_logs.append({
                        'action_id': int(action_id),
                        'leek_id': log[0],
                        'message': log[2]
                    })
    
    all_logs.sort(key=lambda x: x['action_id'])
    
    # Print first 200 lines with findOptimalMoveChipPosition logs
    count = 0
    for log in all_logs:
        message = str(log['message'])
        leek_name = entity_names.get(log['leek_id'], f"Entity_{log['leek_id']}")
        
        if count < 300 and ('findOptimalMoveChipPosition' in message or 'Candidate' in message or 'Best cell' in message or 'Total candidates' in message):
            print(f"[{leek_name}] {message}")
            count += 1

