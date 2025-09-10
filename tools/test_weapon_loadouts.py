#!/usr/bin/env python3
"""
LeekWars Weapon Loadout Tester
Creates test leeks with specific weapon loadouts and tests them
Based on the editor test interface analysis
"""

import requests
import json
import time
import sys
from datetime import datetime

BASE_URL = "https://leekwars.com/api"

class WeaponLoadoutTester:
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
        
        print("❌ Login failed")
        return False

    def create_test_leek(self, name, weapons, chips=None):
        """Create a test leek with specific weapon loadout"""
        print(f"🔧 Creating test leek: {name}")
        
        # Create test leek
        create_url = f"{BASE_URL}/test-leek/new"
        response = self.session.post(create_url, data={"name": name})
        
        if response.status_code != 200:
            print(f"❌ Failed to create test leek")
            return None
            
        data = response.json()
        leek_id = data['id']
        print(f"✅ Created test leek ID: {leek_id}")
        
        # Configure the leek with weapons
        leek_data = {
            'life': 2000,
            'strength': 400, 
            'wisdom': 300,
            'agility': 200,
            'resistance': 200,
            'science': 0,
            'magic': 0,
            'frequency': 100,
            'tp': 20,
            'mp': 6,
            'cores': 20,
            'ram': 20,
            'level': 150,
            'weapons': weapons,
            'chips': chips or []
        }
        
        # Update leek configuration
        update_url = f"{BASE_URL}/test-leek/update"
        response = self.session.post(update_url, data={
            "id": leek_id,
            "data": json.dumps(leek_data)
        })
        
        if response.status_code == 200:
            print(f"✅ Configured leek with weapons: {weapons}")
            return leek_id
        else:
            print(f"❌ Failed to configure leek")
            return None

    def create_test_scenario(self, name, leek_id, opponent_id):
        """Create a test scenario with the test leek vs opponent"""
        print(f"📋 Creating scenario: {name}")
        
        # Create scenario
        create_url = f"{BASE_URL}/test-scenario/new"
        response = self.session.post(create_url, data={"name": name})
        
        if response.status_code != 200:
            print("❌ Failed to create scenario")
            return None
            
        data = response.json()
        scenario_id = data['id']
        
        # Add leeks to scenario
        add_leek_url = f"{BASE_URL}/test-scenario/add-leek"
        
        # Add our test leek (team 1)
        self.session.post(add_leek_url, data={
            "scenario_id": scenario_id,
            "leek": leek_id,
            "team": 0,
            "ai": 445497  # V6 script
        })
        
        # Add opponent (team 2) 
        self.session.post(add_leek_url, data={
            "scenario_id": scenario_id,
            "leek": opponent_id,
            "team": 1,
            "ai": -1  # Bot AI
        })
        
        print(f"✅ Created scenario ID: {scenario_id}")
        return scenario_id

    def run_test(self, scenario_id):
        """Run a test fight"""
        test_url = f"{BASE_URL}/ai/test-scenario"
        
        response = self.session.post(test_url, data={
            "scenario_id": scenario_id,
            "ai_id": 445497  # V6 script
        })
        
        if response.status_code == 200:
            data = response.json()
            return data.get('fight')
        else:
            print(f"❌ Test run failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error: {error_data}")
            except:
                print(f"Response text: {response.text}")
        
        return None

    def get_fight_result(self, fight_id):
        """Get fight result"""
        fight_url = f"{BASE_URL}/fight/get/{fight_id}"
        response = self.session.get(fight_url)
        
        if response.status_code == 200:
            data = response.json()
            if "fight" in data:
                return data["fight"]
        
        return None

# Weapon ID mappings (from game data)
WEAPONS = {
    # Standard weapons
    "RIFLE": 151,
    "M_LASER": 47, 
    "DARK_KATANA": 187,
    "GRENADE_LAUNCHER": 43,
    
    # New weapons to test
    "DESTROYER": 194,  # These IDs need to be verified
    "NEUTRINO": 195,
    "LASER": 196,
    
    # Other weapons
    "MAGNUM": 193,
    "B_LASER": 48,
}

OPPONENTS = {
    "domingo": -1,
    "betalpha": -2,
    "rex": -6
}

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 test_weapon_loadouts.py <loadout> <opponent>")
        print("Available loadouts:")
        print("  standard    - Rifle, M-Laser, Dark Katana, Grenade")
        print("  new_weapons - Destroyer, Neutrino, Laser, Grenade")  
        print("  blaser      - Magnum, B-Laser, Grenade")
        print("Available opponents: domingo, betalpha, rex")
        sys.exit(1)

    loadout = sys.argv[1].lower()
    opponent = sys.argv[2].lower()
    
    if opponent not in OPPONENTS:
        print(f"❌ Unknown opponent: {opponent}")
        sys.exit(1)
    
    # Define weapon loadouts
    loadouts = {
        "standard": [WEAPONS["RIFLE"], WEAPONS["M_LASER"], WEAPONS["DARK_KATANA"], WEAPONS["GRENADE_LAUNCHER"]],
        "new_weapons": [WEAPONS["DESTROYER"], WEAPONS["NEUTRINO"], WEAPONS["LASER"], WEAPONS["GRENADE_LAUNCHER"]],
        "blaser": [WEAPONS["MAGNUM"], WEAPONS["B_LASER"], WEAPONS["GRENADE_LAUNCHER"]]
    }
    
    if loadout not in loadouts:
        print(f"❌ Unknown loadout: {loadout}")
        sys.exit(1)

    weapons = loadouts[loadout]
    opponent_id = OPPONENTS[opponent]
    
    print("============================================================")
    print("LEEKWARS WEAPON LOADOUT TESTER")
    print("============================================================")
    print(f"Testing loadout: {loadout}")
    print(f"Weapons: {weapons}")
    print(f"Opponent: {opponent}")
    
    tester = WeaponLoadoutTester()
    
    # Login
    if not tester.login("tanguy.pedrazzoli@gmail.com", "tanguy0211"):
        sys.exit(1)
    
    # Create test leek
    leek_name = f"TestLeek_{loadout}_{int(time.time())}"
    leek_id = tester.create_test_leek(leek_name, weapons)
    if not leek_id:
        sys.exit(1)
    
    # Create scenario
    scenario_name = f"Test_{loadout}_vs_{opponent}"
    scenario_id = tester.create_test_scenario(scenario_name, leek_id, opponent_id)
    if not scenario_id:
        sys.exit(1)
    
    # Run multiple tests (reduced for rate limiting)
    num_tests = 3
    print(f"\n🚀 Running {num_tests} tests...")
    
    wins = 0
    losses = 0
    draws = 0
    fight_urls = []
    
    for i in range(num_tests):
        print(f"Test {i+1}/{num_tests}...", end=" ")
        
        # Add long delay between requests to avoid rate limiting
        if i > 0:
            print("⏳ Waiting to avoid rate limit...")
            time.sleep(15)  # Wait 15 seconds between tests
        
        fight_id = tester.run_test(scenario_id)
        if not fight_id:
            print("❌ Failed")
            continue
        
        # Wait for fight to complete
        time.sleep(4)
        
        # Get result
        fight_result = tester.get_fight_result(fight_id)
        if not fight_result:
            print("❌ No result")
            continue
        
        fight_url = f"https://leekwars.com/fight/{fight_id}"
        fight_urls.append(fight_url)
        
        # Check winner
        winner = fight_result.get("winner")
        if winner == 1:  # Team 1 (our test leek)
            wins += 1
            print("✅ WIN")
        elif winner == 2:  # Team 2 (opponent)
            losses += 1
            print("❌ LOSS")
        else:
            draws += 1
            print("🤝 DRAW")
    
    # Results
    total_tests = wins + losses + draws
    win_rate = (wins / total_tests * 100) if total_tests > 0 else 0
    
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    print(f"🔧 Loadout: {loadout}")
    print(f"⚔️  Weapons: {weapons}")
    print(f"🤖 Opponent: {opponent}")
    print(f"✅ Wins: {wins}")
    print(f"❌ Losses: {losses}")
    print(f"🤝 Draws: {draws}")
    print(f"📊 Win Rate: {win_rate:.1f}%")
    
    if fight_urls:
        print(f"\n🔗 Fight URLs:")
        for url in fight_urls:
            print(f"   {url}")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {
        "loadout": loadout,
        "weapons": weapons,
        "opponent": opponent,
        "wins": wins,
        "losses": losses, 
        "draws": draws,
        "win_rate": win_rate,
        "fight_urls": fight_urls,
        "timestamp": timestamp
    }
    
    filename = f"weapon_test_{loadout}_{opponent}_{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {filename}")

if __name__ == "__main__":
    main()