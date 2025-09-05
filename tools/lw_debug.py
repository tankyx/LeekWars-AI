#!/usr/bin/env python3
"""
Debug Fight Start - Test starting a solo fight
"""

import requests
import json
from getpass import getpass

BASE_URL = "https://leekwars.com/api"

def test_fight_start():
    """Test starting a fight with different methods"""
    
    # Create session
    session = requests.Session()
    
    # Login
    print("🔐 Logging in...")
    email = input("Email [tanguy.pedrazzoli@gmail.com]: ").strip() or "tanguy.pedrazzoli@gmail.com"
    password = getpass("Password: ")
    
    login_url = f"{BASE_URL}/farmer/login-token"
    login_data = {"login": email, "password": password}
    
    response = session.post(login_url, data=login_data)
    print(f"Login status: {response.status_code}")
    
    if response.status_code != 200:
        print("Login failed!")
        return
    
    data = response.json()
    token = data.get("token", "")
    farmer = data.get("farmer", {})
    leeks = farmer.get("leeks", {})
    
    print(f"✅ Logged in as: {farmer.get('login')}")
    print(f"Session cookies: {list(session.cookies.keys())}")
    
    if not leeks:
        print("No leeks found!")
        return
        
    leek_id = list(leeks.keys())[0]
    leek_name = leeks[leek_id].get("name")
    print(f"Using leek: {leek_name} (ID: {leek_id})")
    
    # Get opponents
    print("\nGetting opponents...")
    url = f"{BASE_URL}/garden/get-leek-opponents/{leek_id}"
    response = session.get(url)
    
    if response.status_code != 200:
        print(f"Failed to get opponents: {response.status_code}")
        return
    
    opponents = response.json().get("opponents", [])
    if not opponents:
        print("No opponents found!")
        return
    
    opponent = opponents[0]
    opponent_id = opponent["id"]
    opponent_name = opponent["name"]
    print(f"Selected opponent: {opponent_name} (ID: {opponent_id})")
    
    print("\n" + "="*60)
    print("TESTING FIGHT START METHODS")
    print("="*60)
    
    # Test 1: POST with no token
    print("\n1. POST /garden/start-solo-fight (no token)")
    url = f"{BASE_URL}/garden/start-solo-fight"
    data = {
        "leek_id": str(leek_id),
        "target_id": str(opponent_id)
    }
    response = session.post(url, data=data)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   Full response: {json.dumps(result, indent=2)}")
        if result.get("success"):
            print(f"   ✅ Fight started! ID: {result.get('fight')}")
        else:
            print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
    
    # Test 2: POST with token in data
    print("\n2. POST /garden/start-solo-fight (token in data)")
    url = f"{BASE_URL}/garden/start-solo-fight"
    data = {
        "leek_id": str(leek_id),
        "target_id": str(opponent_id),
        "token": token
    }
    response = session.post(url, data=data)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   Success: {result.get('success')}")
        print(f"   Error: {result.get('error', 'None')}")
        if result.get("success"):
            print(f"   ✅ Fight started! ID: {result.get('fight')}")
    
    # Test 3: GET with parameters
    print("\n3. GET /garden/start-solo-fight/{leek_id}/{opponent_id}")
    url = f"{BASE_URL}/garden/start-solo-fight/{leek_id}/{opponent_id}"
    response = session.get(url)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   Success: {result.get('success')}")
        print(f"   Error: {result.get('error', 'None')}")
    
    # Test 4: POST with different parameter names
    print("\n4. POST /garden/start-solo-fight (alternative params)")
    url = f"{BASE_URL}/garden/start-solo-fight"
    data = {
        "leek": str(leek_id),
        "target": str(opponent_id)
    }
    response = session.post(url, data=data)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   Success: {result.get('success')}")
        print(f"   Error: {result.get('error', 'None')}")
    
    # Test 5: Try numeric IDs instead of strings
    print("\n5. POST /garden/start-solo-fight (numeric IDs)")
    url = f"{BASE_URL}/garden/start-solo-fight"
    data = {
        "leek_id": int(leek_id),
        "target_id": int(opponent_id)
    }
    response = session.post(url, json=data)  # Using json instead of data
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   Success: {result.get('success')}")
        print(f"   Error: {result.get('error', 'None')}")
    
    print("\n" + "="*60)
    print("Testing complete!")

if __name__ == "__main__":
    test_fight_start()
