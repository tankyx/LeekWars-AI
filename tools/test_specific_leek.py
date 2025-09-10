#!/usr/bin/env python3
"""
LeekWars Specific Leek Tester
Tests V6 AI with specific leeks against opponents
Usage: python3 test_specific_leek.py <leek_id> <num_tests> <opponent>
"""

import requests
import json
import time
import sys
from datetime import datetime

BASE_URL = "https://leekwars.com/api"

class LeekWarsTester:
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

    def get_leek_info(self, leek_id):
        """Get specific leek information"""
        leeks = self.farmer.get('leeks', {})
        return leeks.get(str(leek_id))

    def get_existing_scenarios(self):
        """Get existing test scenarios"""
        url = f"{BASE_URL}/test-scenario/get-all"
        response = self.session.get(url)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('scenarios', {}), data.get('leeks', [])
        return {}, []

    def find_scenario_for_opponent(self, scenarios, opponent_id):
        """Find an existing scenario for the given opponent"""
        for scenario_id, scenario in scenarios.items():
            team2 = scenario.get('team2', [])
            if team2 and len(team2) > 0 and team2[0].get('id') == opponent_id:
                return scenario_id, scenario
        return None, None

    def run_test(self, scenario_id, script_id, leek_id):
        """Run a test using ai/test-scenario endpoint"""
        url = f"{BASE_URL}/ai/test-scenario"
        
        # The working script assigns the AI to a scenario that uses specific leeks
        response = self.session.post(url, data={
            "scenario_id": str(scenario_id),
            "ai_id": str(script_id)
        })
        
        if response.status_code == 200:
            try:
                data = response.json()
                fight_id = data.get('fight')
                if fight_id:
                    return fight_id
            except:
                pass
        
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

def main():
    if len(sys.argv) != 4:
        print("Usage: python3 test_specific_leek.py <leek_id> <num_tests> <opponent>")
        print("Available leeks:")
        print("  20443  - VirusLeek (Level 300)")
        print("  129288 - EbolaLeek (B_Laser loadout)")  
        print("  129295 - RabiesLeek (DESTROYER/NEUTRINO/LASER)")
        print("  129296 - SmallPoxLeek (DESTROYER/NEUTRINO/LASER)")
        print("Available opponents:")
        print("  domingo, betalpha, tisma, guj, hachess, rex")
        sys.exit(1)

    leek_id = int(sys.argv[1])
    num_tests = int(sys.argv[2])
    opponent = sys.argv[3].lower()
    
    # Opponent mapping
    opponent_map = {
        "domingo": -1,
        "betalpha": -2, 
        "tisma": -3,
        "guj": -4,
        "hachess": -5,
        "rex": -6
    }
    
    if opponent not in opponent_map:
        print(f"❌ Unknown opponent: {opponent}")
        sys.exit(1)
    
    opponent_id = opponent_map[opponent]
    
    print("============================================================")
    print("LEEKWARS SPECIFIC LEEK TESTER")
    print("============================================================")
    print(f"Leek ID: {leek_id}")
    print(f"Number of tests: {num_tests}")
    print(f"Opponent: {opponent}")
    
    tester = LeekWarsTester()
    
    # Login
    if not tester.login("tanguy.pedrazzoli@gmail.com", "tanguy0211"):
        sys.exit(1)
    
    # Get leek info
    leek = tester.get_leek_info(leek_id)
    if not leek:
        print(f"❌ Leek {leek_id} not found")
        sys.exit(1)
    
    print(f"🥬 Testing with: {leek['name']} (Level {leek['level']})")
    
    # Get existing scenarios
    print(f"📋 Looking for existing test scenario vs {opponent}...")
    scenarios, test_leeks = tester.get_existing_scenarios()
    
    scenario_id, scenario = tester.find_scenario_for_opponent(scenarios, opponent_id)
    if not scenario_id:
        print("❌ No existing scenario found for this opponent")
        print("Available scenarios:")
        for sid, s in list(scenarios.items())[:3]:
            team2 = s.get('team2', [])
            opponent_name = team2[0].get('name', 'Unknown') if team2 else 'No opponent'
            print(f"  {sid}: {s.get('name', 'Unnamed')} vs {opponent_name}")
        sys.exit(1)
    
    print(f"✅ Using scenario: {scenario.get('name', 'Unnamed')} (ID: {scenario_id})")
    
    # Run tests
    print(f"\n🚀 Starting {num_tests} tests...")
    wins = 0
    losses = 0
    draws = 0
    fight_urls = []
    
    for i in range(num_tests):
        print(f"Test {i+1}/{num_tests}...", end=" ")
        
        # The V6 script is already assigned (445497)
        script_id = 445497
        fight_id = tester.run_test(scenario_id, script_id, leek_id)
        if not fight_id:
            print("❌ Failed")
            continue
        
        # Wait for fight to complete
        time.sleep(2)
        
        # Get result
        fight_result = tester.get_fight_result(fight_id)
        if not fight_result:
            print("❌ No result")
            continue
        
        fight_url = f"https://leekwars.com/fight/{fight_id}"
        fight_urls.append(fight_url)
        
        # Check winner
        winner = fight_result.get("winner")
        if winner == 1:  # Team 1 (our leek)
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
    print(f"✅ Wins: {wins}")
    print(f"❌ Losses: {losses}")
    print(f"🤝 Draws: {draws}")
    print(f"📊 Win Rate: {win_rate:.1f}%")
    print(f"🎯 Total Tests: {total_tests}")
    
    if fight_urls:
        print(f"\n🔗 Sample fight URLs:")
        for i, url in enumerate(fight_urls[:5]):
            print(f"   {url}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {
        "leek_id": leek_id,
        "leek_name": leek['name'],
        "opponent": opponent,
        "total_tests": total_tests,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate": win_rate,
        "fight_urls": fight_urls,
        "timestamp": timestamp
    }
    
    filename = f"test_results_leek_{leek_id}_{opponent}_{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {filename}")

if __name__ == "__main__":
    main()