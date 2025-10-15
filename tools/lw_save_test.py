#!/usr/bin/env python3
"""
Direct test of the AI save endpoint
"""

import requests
import json
from getpass import getpass
from config_loader import load_credentials

BASE_URL = "https://leekwars.com/api"

def test_save_methods(token, ai_id, code):
    """Test different ways to save AI code"""
    session = requests.Session()
    
    print(f"\n🔍 Testing AI save with ID: {ai_id}")
    print(f"Token (first 30 chars): {token[:30]}...")
    print(f"Code length: {len(code)} chars\n")
    
    # Method 1: Standard form data
    print("1️⃣ Testing standard form data...")
    url = f"{BASE_URL}/ai/save"
    data = {
        "ai_id": str(ai_id),  # As string
        "code": code,
        "token": token
    }
    response = session.post(url, data=data)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ SUCCESS!")
        print(f"   Response: {response.json()}")
        return True
    else:
        print(f"   Response: {response.text[:200]}")
    
    # Method 2: Try with integer conversion using json
    print("\n2️⃣ Testing JSON format...")
    data_json = {
        "ai_id": int(ai_id),  # As integer
        "code": code,
        "token": token
    }
    response = session.post(url, json=data_json)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ SUCCESS!")
        print(f"   Response: {response.json()}")
        return True
    else:
        print(f"   Response: {response.text[:200]}")
    
    # Method 3: Token in URL
    print("\n3️⃣ Testing token in URL...")
    url_with_token = f"{BASE_URL}/ai/save/{token}"
    data_minimal = {
        "ai_id": str(ai_id),
        "code": code
    }
    response = session.post(url_with_token, data=data_minimal)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ SUCCESS!")
        return True
    else:
        print(f"   Response: {response.text[:200]}")
    
    # Method 4: Get the AI first to check format
    print("\n4️⃣ Getting AI details first...")
    get_url = f"{BASE_URL}/ai/get/{ai_id}/{token}"
    response = session.get(get_url)
    print(f"   Get AI Status: {response.status_code}")
    if response.status_code == 200:
        ai_data = response.json()
        print(f"   AI exists: {ai_data.get('ai', {}).get('name', 'Unknown')}")
        
        # Now try saving with confirmed AI
        print("   Trying save with confirmed AI...")
        save_data = {
            "ai_id": str(ai_id),
            "code": code,
            "token": token
        }
        response = session.post(f"{BASE_URL}/ai/save", data=save_data)
        print(f"   Save Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ SUCCESS after getting AI!")
            return True
    
    return False

def main():
    print("=== LeekWars Save Test ===\n")
    
    # Login first
    email, password = load_credentials()  # Changed from input prompt
    password = getpass("Password: ")
    
    session = requests.Session()
    login_url = f"{BASE_URL}/farmer/login-token"
    login_data = {"login": email, "password": password}
    
    response = session.post(login_url, data=login_data)
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("token")
        farmer = data.get("farmer", {})
        
        print(f"\n✅ Logged in as {farmer.get('login')}")
        
        # Get leek info
        leeks = farmer.get("leeks", {})
        if leeks:
            leek_data = list(leeks.values())[0]
            ai_id = leek_data.get("ai")
            leek_name = leek_data.get("name")
            
            if ai_id:
                print(f"Found leek: {leek_name} with AI ID: {ai_id}")
                
                # Simple test code
                test_code = """
// Test script
var enemy = getNearestEnemy();
if (enemy) {
    if (getWeapon() !== WEAPON_MAGNUM) {
        setWeapon(WEAPON_MAGNUM);
    }
    useWeapon(enemy);
}
"""
                
                # Test saving
                success = test_save_methods(token, ai_id, test_code)
                
                if not success:
                    print("\n❌ All methods failed")
                    print("\nTrying to create a new AI instead...")
                    
                    # Try creating a new AI
                    create_url = f"{BASE_URL}/ai/new"
                    create_data = {
                        "folder_id": 0,
                        "v2": 1,
                        "token": token
                    }
                    response = session.post(create_url, data=create_data)
                    
                    if response.status_code == 200:
                        new_ai = response.json().get("ai", {})
                        new_ai_id = new_ai.get("id")
                        print(f"✅ Created new AI with ID: {new_ai_id}")
                        
                        # Try saving to new AI
                        test_save_methods(token, new_ai_id, test_code)
            else:
                print("❌ No AI found for leek")
        else:
            print("❌ No leeks found")
    else:
        print(f"❌ Login failed: {response.status_code}")

if __name__ == "__main__":
    main()
