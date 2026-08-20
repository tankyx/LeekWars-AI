#!/usr/bin/env python3
"""Fetch challenge fight results with rate-limit handling."""
import requests, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_credentials

BASE_URL = "https://leekwars.com/api"

FIGHTS = {
    "EdsgerDijkstra vs mamax49poireau": [52609193,52609196,52609197,52609198,52609199],
    "KurtGodel vs Leek@14785":         [52609202,52609203,52609205,52609206,52609208],
    "MargaretHamilton vs TheBuche":    [52609210,52609211,52609212,52609215,52609216],
    "AdaLovelace vs mamax49poireau":   [52609217,52609218,52609220,52609222,52609223],
}

email, password = load_credentials(account="main")
session = requests.Session()
session.post(f"{BASE_URL}/farmer/login-token", data={"login": email, "password": password})

for label, ids in FIGHTS.items():
    wins = losses = draws = errors = 0
    for fid in ids:
        time.sleep(1.5)  # rate limit
        r = session.get(f"{BASE_URL}/fight/get/{fid}")
        if r.status_code != 200:
            if r.status_code == 429:
                time.sleep(5)
                r = session.get(f"{BASE_URL}/fight/get/{fid}")
            if r.status_code != 200:
                errors += 1
                continue
        data = r.json()
        winner = data.get("winner", -1)
        status = data.get("status", -1)
        if status != 2:
            errors += 1
        elif winner == 1: wins += 1
        elif winner == 2: losses += 1
        elif winner == 0: draws += 1
        else: errors += 1
    total = wins + losses + draws
    wr = f"{wins/total*100:.0f}%" if total > 0 else "N/A"
    print(f"{label}: {wins}W/{losses}L/{draws}D ({wr}) [{errors} err]")
