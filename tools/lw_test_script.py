#!/usr/bin/env python3
"""
LeekWars Script Testing Tool
Tests a specific script ID against standard test opponents (bots)
Usage: python3 lw_test_script.py <script_id> <num_tests> [opponent]
Example: python3 lw_test_script.py 445124 10 domingo
         python3 lw_test_script.py 445124 10 betalpha

Available opponents:
  domingo  (-1): Balanced stats, 600 strength, 300 wisdom
  betalpha (-2): Magic focused, 600 magic, 300 wisdom  
  tisma    (-3): Wisdom/Science, 600 wisdom, 300 science
  guj      (-4): Tank, 5000 life
  hachess  (-5): Resistance focused, 600 resistance
  rex      (-6): Agility focused, 600 agility
"""

import requests
import json
import time
import sys
import os
from datetime import datetime

BASE_URL = "https://leekwars.com/api"

# Bot opponent definitions
BOTS = {
    "domingo": {"id": -1, "name": "Domingo", "desc": "Balanced, 600 strength"},
    "betalpha": {"id": -2, "name": "Betalpha", "desc": "Magic build, 600 magic"},
    "tisma": {"id": -3, "name": "Tisma", "desc": "Wisdom/Science, 600 wisdom"},
    "guj": {"id": -4, "name": "Guj", "desc": "Tank, 5000 life"},
    "hachess": {"id": -5, "name": "Hachess", "desc": "Defensive, 600 resistance"},
    "rex": {"id": -6, "name": "Rex", "desc": "Agile, 600 agility"}
}

class LeekWarsScriptTester:
    def __init__(self):
        self.session = requests.Session()
        self.farmer = None
        self.token = None
        self.scenarios = {}
        self.test_leeks = {}
        self.fights_run = []
        
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
                
                print(f"✅ Connected as: {self.farmer.get('login')}")
                return True
            else:
                print("❌ Login failed")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
    
    def get_script_info(self, script_id):
        """Get information about a specific script/AI"""
        url = f"{BASE_URL}/ai/get/{script_id}"
        response = self.session.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if "ai" in data:
                ai_info = data["ai"]
                print(f"📝 Script: {ai_info.get('name')} (ID: {script_id})")
                return ai_info
        return None
    
    def setup_test_scenario(self, script_id, bot_opponent):
        """Create or get a test scenario for the script with specific bot opponent"""
        # First, get all existing test scenarios
        url = f"{BASE_URL}/test-scenario/get-all"
        response = self.session.get(url)
        
        if response.status_code == 200:
            data = response.json()
            self.scenarios = data.get('scenarios', {})
            self.test_leeks = data.get('leeks', [])
            
            # Look for an existing scenario for this AI with this bot
            for scenario_id, scenario in self.scenarios.items():
                if scenario.get('ai') == script_id:
                    # Check if it has the right bot opponent
                    team2 = scenario.get('team2', [])
                    if team2 and len(team2) > 0 and team2[0].get('id') == bot_opponent['id']:
                        print(f"📋 Using existing scenario: {scenario.get('name')} vs {bot_opponent['name']}")
                        return scenario_id
            
            # Create a new scenario if none exists
            print(f"📋 Creating new test scenario vs {bot_opponent['name']}...")
            
            # Find the first available leek
            farmer_leeks = self.farmer.get('leeks', {})
            if not farmer_leeks:
                print("❌ No leeks found in your account")
                return None
            
            first_leek = list(farmer_leeks.values())[0]
            
            # Create scenario with specific bot opponent
            scenario_name = f"Test_{script_id}_vs_{bot_opponent['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            response = self.session.post(f"{BASE_URL}/test-scenario/new", data={
                "name": scenario_name
            })
            
            if response.status_code == 200:
                result = response.json()
                scenario_id = result.get('id')
                
                # Configure the scenario
                scenario_data = {
                    "type": 0,  # Solo fight
                    "map": None,  # Random map
                    "ai": script_id
                }
                
                self.session.post(f"{BASE_URL}/test-scenario/update", data={
                    "id": scenario_id,
                    "data": json.dumps(scenario_data)
                })
                
                # Add player's leek with the script to team 1
                time.sleep(0.3)  # Avoid rate limiting
                resp1 = self.session.post(f"{BASE_URL}/test-scenario/add-leek", data={
                    "scenario_id": scenario_id,
                    "leek": first_leek['id'],
                    "team": 0,
                    "ai": script_id
                })
                
                if resp1.status_code == 429:  # Rate limited
                    print("   Rate limited, waiting 2 seconds...")
                    time.sleep(2)
                    resp1 = self.session.post(f"{BASE_URL}/test-scenario/add-leek", data={
                        "scenario_id": scenario_id,
                        "leek": first_leek['id'],
                        "team": 0,
                        "ai": script_id
                    })
                
                if resp1.status_code != 200:
                    print(f"⚠️ Failed to add player leek: {resp1.text}")
                
                # Add the specific bot opponent to team 2
                time.sleep(0.3)  # Avoid rate limiting
                resp2 = self.session.post(f"{BASE_URL}/test-scenario/add-leek", data={
                    "scenario_id": scenario_id,
                    "leek": bot_opponent['id'],  # Specific bot leek
                    "team": 1,
                    "ai": -2  # Use normal AI for bots (-1=lambda, -2=normal, -3=confirmed, -4=expert)
                })
                
                if resp2.status_code == 429:  # Rate limited
                    print("   Rate limited, waiting 2 seconds...")
                    time.sleep(2)
                    resp2 = self.session.post(f"{BASE_URL}/test-scenario/add-leek", data={
                        "scenario_id": scenario_id,
                        "leek": bot_opponent['id'],  # Specific bot leek
                        "team": 1,
                        "ai": -2  # Use normal AI for bots (-1=lambda, -2=normal, -3=confirmed, -4=expert)
                    })
                
                if resp2.status_code != 200:
                    print(f"⚠️ Failed to add bot: {resp2.text}")
                
                print(f"✅ Created scenario ID: {scenario_id}")
                
                # Verify the scenario was created properly
                time.sleep(0.3)  # Give the server time to process
                verify_url = f"{BASE_URL}/test-scenario/get-all"
                verify_resp = self.session.get(verify_url)
                if verify_resp.status_code == 200:
                    verify_data = verify_resp.json()
                    scenarios = verify_data.get('scenarios', {})
                    if str(scenario_id) in scenarios:
                        scenario = scenarios[str(scenario_id)]
                        print(f"   Scenario verified: {len(scenario.get('team1', []))} vs {len(scenario.get('team2', []))} leeks")
                
                return scenario_id
        
        return None
    
    def run_test(self, scenario_id, script_id):
        """Run a single test fight"""
        url = f"{BASE_URL}/ai/test-scenario"
        
        # Try with string IDs as the frontend does
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
            except Exception as e:
                print(f"\n❌ Error parsing response: {e}")
        else:
            print(f"\n❌ HTTP error {response.status_code}: {response.text}")
        return None
    
    def get_fight_result(self, fight_id):
        """Get the result of a fight"""
        time.sleep(0.3)  # Reduced wait time for fight to complete
        
        url = f"{BASE_URL}/fight/get/{fight_id}"
        
        # Retry a few times as fight might still be processing
        for attempt in range(3):
            if attempt > 0:
                time.sleep(0.3)
            
            response = self.session.get(url)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # The fight data IS the response (no wrapper)
                    fight_data = data
                    winner = fight_data.get("winner")
                    leeks = fight_data.get("leeks1", []) + fight_data.get("leeks2", [])
                    
                    # If winner is not set, fight might still be processing
                    if winner is None:
                        print("Winner not set yet, retrying...")
                        continue
                    
                    # Determine if we won (team 1 is our team)
                    our_team = 1  # Team IDs are 1 and 2
                    result = "DRAW" if winner == 0 else ("WIN" if winner == our_team else "LOSS")
                    
                    return {
                        "fight_id": fight_id,
                        "result": result,
                        "url": f"https://leekwars.com/fight/{fight_id}",
                        "date": fight_data.get("date"),
                        "leeks": leeks
                    }
                except Exception as e:
                    print(f"\n❌ Error getting fight result: {e}")
        return None
    
    def run_tests(self, script_id, num_tests, bot_opponent):
        """Run multiple test fights against specific bot opponent"""
        print(f"\n🎯 Running {num_tests} test fights for script {script_id} vs {bot_opponent['name']}...")
        print(f"🤖 Opponent: {bot_opponent['name']} - {bot_opponent['desc']}")
        
        # Get script info
        ai_info = self.get_script_info(script_id)
        if not ai_info:
            print("❌ Could not find script")
            return
        
        # Setup test scenario with specific bot
        scenario_id = self.setup_test_scenario(script_id, bot_opponent)
        if not scenario_id:
            print("❌ Could not create test scenario")
            return
        
        # Run tests
        results = {"wins": 0, "losses": 0, "draws": 0}
        fight_urls = []
        
        print("\n🚀 Starting tests...")
        print("Progress: ", end="", flush=True)
        
        for i in range(num_tests):
            # Small delay to avoid rate limiting
            if i > 0:
                time.sleep(0.3)  # Reduced to 0.3 seconds
            
            # Run test
            fight_id = self.run_test(scenario_id, script_id)
            
            if fight_id:
                # Get result
                fight_result = self.get_fight_result(fight_id)
                
                if fight_result:
                    # Map results properly (LOSS -> losses, not losss)
                    result_key = fight_result["result"].lower()
                    if result_key == "loss":
                        result_key = "losses"
                    elif result_key == "win":
                        result_key = "wins"
                    elif result_key == "draw":
                        result_key = "draws"
                    results[result_key] += 1
                    fight_urls.append(fight_result["url"])
                    
                    # Progress indicator
                    if i > 0 and i % 10 == 0:
                        print(f"[{i}]", end="", flush=True)
                    else:
                        print(".", end="", flush=True)
                else:
                    print("x", end="", flush=True)
            else:
                print("!", end="", flush=True)
            
            # Small delay to avoid overwhelming the server
            time.sleep(0.3)
        
        print()  # New line after progress
        
        # Display results
        total = results["wins"] + results["losses"] + results["draws"]
        win_rate = (results["wins"] / total * 100) if total > 0 else 0
        
        print("\n" + "="*60)
        print("TEST RESULTS")
        print("="*60)
        print(f"✅ Wins: {results['wins']}")
        print(f"❌ Losses: {results['losses']}")
        print(f"🤝 Draws: {results['draws']}")
        print(f"📊 Win Rate: {win_rate:.1f}%")
        print(f"🎯 Total Tests: {total}")
        
        # Show some fight URLs
        if fight_urls:
            print("\n🔗 Sample fight URLs:")
            for url in fight_urls[:5]:
                print(f"   {url}")
            
            if len(fight_urls) > 5:
                print(f"   ... and {len(fight_urls) - 5} more")
        
        # Save results to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f"test_results_{script_id}_{timestamp}.json"
        
        with open(results_file, "w") as f:
            json.dump({
                "script_id": script_id,
                "script_name": ai_info.get('name'),
                "opponent": bot_opponent['name'],
                "opponent_desc": bot_opponent['desc'],
                "timestamp": timestamp,
                "num_tests": num_tests,
                "results": results,
                "win_rate": win_rate,
                "fight_urls": fight_urls
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {results_file}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 lw_test_script.py <script_id> <num_tests> [opponent]")
        print("Example: python3 lw_test_script.py 445124 10")
        print("         python3 lw_test_script.py 445124 10 domingo")
        print("\nAvailable opponents:")
        for name, bot in BOTS.items():
            print(f"  {name:8} - {bot['desc']}")
        print("\nDefault: domingo (if not specified)")
        return 1
    
    try:
        script_id = int(sys.argv[1])
        num_tests = int(sys.argv[2])
    except ValueError:
        print("❌ Invalid arguments. Script ID and number of tests must be integers.")
        return 1
    
    # Get bot opponent (default to domingo)
    opponent_name = sys.argv[3].lower() if len(sys.argv) > 3 else "domingo"
    
    if opponent_name not in BOTS:
        print(f"❌ Unknown opponent: {opponent_name}")
        print("\nAvailable opponents:")
        for name, bot in BOTS.items():
            print(f"  {name:8} - {bot['desc']}")
        return 1
    
    bot_opponent = BOTS[opponent_name]
    
    if num_tests < 1:
        print("❌ Number of tests must be at least 1")
        return 1
    
    print("="*60)
    print("LEEKWARS SCRIPT TESTING TOOL")
    print("="*60)
    print(f"Script ID: {script_id}")
    print(f"Number of tests: {num_tests}")
    print(f"Opponent: {bot_opponent['name']} - {bot_opponent['desc']}")
    
    # Create tester instance
    tester = LeekWarsScriptTester()
    
    # Login credentials
    email = "tanguy.pedrazzoli@gmail.com"
    password = "tanguy0211"
    
    # Login
    if not tester.login(email, password):
        print("\n❌ Failed to login")
        return 1
    
    try:
        # Run tests with specific opponent
        tester.run_tests(script_id, num_tests, bot_opponent)
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
    
    return 0

if __name__ == "__main__":
    exit(main())