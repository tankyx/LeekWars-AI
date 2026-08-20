#!/usr/bin/env python3
"""Challenge specific opponents for each leek on the main account."""
import requests, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_credentials

BASE_URL = "https://leekwars.com/api"

CHALLENGES = [
    # (leek_name, leek_id, opponent_name, opponent_id)
    ("EdsgerDijkstra", 129288, "mamax49poireau", 97),
    ("KurtGodel",       129295, "Leek@14785",       14785),
    ("MargaretHamilton",129296, "TheBuche",         39459),
    ("AdaLovelace",     20443, "mamax49poireau",    97),
]

email, password = load_credentials(account="main")
session = requests.Session()

# Login
r = session.post(f"{BASE_URL}/farmer/login-token", data={"login": email, "password": password})
if r.status_code != 200:
    print(f"Login failed: {r.status_code}")
    sys.exit(1)
token = r.json()["token"]
farmer = r.json()["farmer"]
print(f"Logged in as {farmer['login']}")

for leek_name, leek_id, opp_name, opp_id in CHALLENGES:
    print(f"\n{'='*60}")
    print(f"🦗 {leek_name} (ID {leek_id}) vs {opp_name} (ID {opp_id}) — 5 challenges")
    print(f"{'='*60}")
    for i in range(5):
        r = session.post(f"{BASE_URL}/garden/start-solo-challenge",
                        data={"leek_id": leek_id, "target_id": opp_id, "seed": i + 1, "side": 0, "token": token})
        if r.status_code == 200:
            data = r.json()
            fight_id = data if isinstance(data, int) else data.get("fight", data.get("fight_id", data))
            print(f"  #{i+1}: fight_id={fight_id}")
        else:
            print(f"  #{i+1}: FAILED ({r.status_code}) - {r.text[:100]}")
        time.sleep(1.5)  # rate limit
    time.sleep(1)
print("\n✅ Done")
