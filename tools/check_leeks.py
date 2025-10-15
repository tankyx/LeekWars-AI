#!/usr/bin/env python3
"""
LeekWars Leek Information Checker
Displays information about all leeks on the account including weapons and scripts
"""

import requests
import json
from config_loader import load_credentials

BASE_URL = "https://leekwars.com/api"

class LeekWarsChecker:
    def __init__(self):
        self.session = requests.Session()
        self.farmer = None
        self.token = None

    def login(self, email, password):
        """Login to LeekWars"""
        print("🔐 Logging in...")
        
        login_url = f"{BASE_URL}/farmer/login-token"
        login_data = {
            "login": email,
            "password": password
        }
        
        response = self.session.post(login_url, data=login_data)
        
        if response.status_code == 200:
            data = response.json()
            
            if "farmer" in data and "token" in data:
                self.farmer = data["farmer"]
                self.token = data["token"]
                print(f"✅ Connected as: {self.farmer['login']}")
                return True
            else:
                print(f"❌ Login response: {data}")
                return False
        else:
            print(f"❌ Login failed with status code: {response.status_code}")
            return False

    def get_farmer_info(self):
        """Get detailed farmer information including leeks"""
        farmer_url = f"{BASE_URL}/farmer/get"
        response = self.session.get(farmer_url)
        
        if response.status_code == 200:
            data = response.json()
            if "farmer" in data:
                return data["farmer"]
            else:
                print(f"❌ Farmer info response: {data}")
        else:
            print(f"❌ Farmer info failed with status: {response.status_code}")
            print(f"Response: {response.text}")
        return None

def main():
    print("============================================================")
    print("LEEKWARS LEEK INFORMATION CHECKER")
    print("============================================================")
    
    checker = LeekWarsChecker()
    
    # Login credentials (same as uploader)
    email, password = load_credentials()
    
    # Login
    if not checker.login(email, password):
        print("❌ Failed to login")
        return
    
    # Use farmer info from login
    farmer = checker.farmer
    
    print(f"\n📊 Farmer: {farmer['name']} (ID: {farmer['id']})")
    
    leeks = farmer.get('leeks', [])
    if not leeks:
        print("❌ No leeks found in farmer data")
        print(f"Available farmer keys: {list(farmer.keys())}")
        return
    
    print(f"\n🥬 Total Leeks: {len(leeks)}")
    print("============================================================")
    
    # leeks is a dictionary where keys are leek IDs and values are leek objects
    for leek_id, leek in leeks.items():
        print(f"🥬 {leek['name']} (ID: {leek_id})")
        print(f"   📊 Level: {leek.get('level', 'N/A')} | Life: {leek.get('life', 'N/A')}")
        print(f"   🤖 Script: {leek.get('ai', 'No script assigned')}")
        
        weapons = leek.get('weapons', [])
        if weapons:
            print(f"   ⚔️  Weapons ({len(weapons)}): {weapons}")
        else:
            print(f"   ⚔️  Weapons: None")
            
        chips = leek.get('chips', [])
        if chips:
            print(f"   💎 Chips ({len(chips)}): {chips}")
        else:
            print(f"   💎 Chips: None")
        print()

if __name__ == "__main__":
    main()