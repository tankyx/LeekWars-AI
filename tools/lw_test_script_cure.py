#!/usr/bin/env python3
"""
LeekWars Script Testing Tool - CURE ACCOUNT
Tests a specific script ID against standard test opponents (bots)
Usage: python3 lw_test_script_cure.py <script_id> <num_tests> [opponent] [--leek <name>]
Example: python3 lw_test_script_cure.py 447356 10 domingo
         python3 lw_test_script_cure.py 447356 10 betalpha --leek CureLeek

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
import re
from datetime import datetime
from html.parser import HTMLParser
from config_loader import load_credentials

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
    
    def setup_test_scenario(self, script_id, bot_opponent, preferred_leek_name=None):
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
            
            # Find the chosen leek (by name) or fall back to the first available leek
            farmer_leeks = self.farmer.get('leeks', {})
            if not farmer_leeks:
                print("❌ No leeks found in your account")
                return None
            # Try to find a leek by name
            selected_leek = None
            if preferred_leek_name:
                for leek in farmer_leeks.values():
                    if leek.get('name') == preferred_leek_name:
                        selected_leek = leek
                        break
                if not selected_leek:
                    print(f"⚠️ Leek named '{preferred_leek_name}' not found. Falling back to first leek.")
            if not selected_leek:
                selected_leek = list(farmer_leeks.values())[0]
            
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
                    "leek": selected_leek['id'],
                    "team": 0,
                    "ai": script_id
                })
                
                if resp1.status_code == 429:  # Rate limited
                    print("   Rate limited, waiting 2 seconds...")
                    time.sleep(2)
                    resp1 = self.session.post(f"{BASE_URL}/test-scenario/add-leek", data={
                        "scenario_id": scenario_id,
                        "leek": selected_leek['id'],
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
                    leeks1 = fight_data.get("leeks1", [])
                    leeks2 = fight_data.get("leeks2", [])
                    leeks = leeks1 + leeks2

                    # If winner is not set, fight might still be processing
                    if winner is None:
                        print("Winner not set yet, retrying...")
                        continue

                    # Determine which team we're on by checking our farmer's leeks
                    farmer_leek_ids = [int(lid) for lid in self.farmer.get('leeks', {}).keys()]
                    our_team = None
                    for leek in leeks1:
                        if leek['id'] in farmer_leek_ids:
                            our_team = 1
                            break
                    if our_team is None:
                        for leek in leeks2:
                            if leek['id'] in farmer_leek_ids:
                                our_team = 2
                                break

                    # Determine result
                    if our_team is None:
                        result = "UNKNOWN"  # Shouldn't happen
                    else:
                        result = "DRAW" if winner == 0 else ("WIN" if winner == our_team else "LOSS")

                    return {
                        "fight_id": fight_id,
                        "result": result,
                        "url": f"https://leekwars.com/fight/{fight_id}",
                        "date": fight_data.get("date"),
                        "leeks": leeks,
                        "fight_data": fight_data  # Store full fight data for log extraction
                    }
                except Exception as e:
                    print(f"\n❌ Error getting fight result: {e}")
        return None
    
    def get_fight_logs(self, fight_id):
        """Get the logs of a fight - try multiple methods"""
        # Method 1: Try the official logs endpoint (requires authentication)
        try:
            url = f"{BASE_URL}/fight/get-logs/{fight_id}"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                # The response is directly the logs object
                if data:
                    return self.parse_logs(data)
        except Exception as e:
            pass
        
        # Method 2: Get from fight data
        try:
            url = f"{BASE_URL}/fight/get/{fight_id}"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                
                # Check for logs in different locations
                if "logs" in data and data["logs"]:
                    return data["logs"]
                
                fight_data = data.get("data", {})
                if "logs" in fight_data and fight_data["logs"]:
                    return fight_data["logs"]
                
                # Check in ops field (operations/debug info)
                if "ops" in fight_data:
                    ops_data = fight_data["ops"]
                    if isinstance(ops_data, dict):
                        logs = []
                        for entity_id, entity_logs in ops_data.items():
                            if isinstance(entity_logs, list) and entity_logs:
                                for log_entry in entity_logs:
                                    if isinstance(log_entry, list):
                                        logs.append([int(entity_id), *log_entry])
                        if logs:
                            return logs
        except Exception as e:
            pass
        
        return None
    
    def parse_logs(self, logs_data):
        """Parse the logs data structure from LeekWars API"""
        parsed_logs = []
        
        # The logs are structured as {farmer_id: {action_id: [log_entries]}}
        for farmer_id, farmer_logs in logs_data.items():
            for action_id, action_logs in farmer_logs.items():
                for log in action_logs:
                    # Log format: [leek_id, type, message/line, color, ai_id, line_number, ...]
                    if isinstance(log, list) and len(log) >= 3:
                        parsed_logs.append({
                            'farmer_id': farmer_id,
                            'action_id': action_id,
                            'leek_id': log[0],
                            'type': log[1],
                            'message': log[2],  # The actual log message is at index 2
                            'color': log[3] if len(log) > 3 else None,
                            'ai_id': log[4] if len(log) > 4 else None,
                            'line_number': log[5] if len(log) > 5 else None,
                            'raw': log
                        })
        
        # Sort by action_id to get chronological order
        parsed_logs.sort(key=lambda x: int(x['action_id']))
        return parsed_logs
    
    def run_tests(self, script_id, num_tests, bot_opponent, save_logs=True):
        """Run multiple test fights against specific bot opponent"""
        print(f"\n🎯 Running {num_tests} test fights for script {script_id} vs {bot_opponent['name']}...")
        print(f"🤖 Opponent: {bot_opponent['name']} - {bot_opponent['desc']}")
        if save_logs:
            print("📜 Log retrieval: ENABLED")
        
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
        fight_logs = []  # Store logs for each fight
        
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
                    
                    # Get logs for this fight if enabled
                    if save_logs:
                        time.sleep(0.5)  # Small delay to ensure fight is processed
                        logs = self.get_fight_logs(fight_id)
                        if not logs and i == 0:  # Debug first fight only
                            print(f"\n   ⚠️ No logs retrieved for fight {fight_id}")
                    else:
                        logs = None
                    
                    if logs:
                        fight_logs.append({
                            "fight_id": fight_id,
                            "result": fight_result["result"],
                            "url": fight_result["url"],
                            "logs": logs
                        })
                    else:
                        # Try alternative: extract logs from fight data if available
                        if 'actions' in fight_result.get('fight_data', {}):
                            # Convert actions to readable logs
                            actions = fight_result['fight_data']['actions']
                            readable_logs = []
                            # Basic action parsing (can be expanded)
                            for action in actions[:100]:  # First 100 actions
                                readable_logs.append(str(action))
                            if readable_logs:
                                fight_logs.append({
                                    "fight_id": fight_id,
                                    "result": fight_result["result"],
                                    "url": fight_result["url"],
                                    "logs": readable_logs
                                })
                    
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
        
        # Save fight logs to separate file if we have them
        if fight_logs:
            logs_file = f"fight_logs_{script_id}_{bot_opponent['name'].lower()}_{timestamp}.json"
            with open(logs_file, "w") as f:
                json.dump({
                    "script_id": script_id,
                    "script_name": ai_info.get('name'),
                    "opponent": bot_opponent['name'],
                    "timestamp": timestamp,
                    "fights": fight_logs
                }, f, indent=2)
            
            print(f"📜 Fight logs saved to: {logs_file}")
            
            # Also create a simplified log analysis
            analysis_file = f"log_analysis_{script_id}_{bot_opponent['name'].lower()}_{timestamp}.txt"
            with open(analysis_file, "w") as f:
                f.write(f"Fight Log Analysis\n")
                f.write(f"==================\n")
                f.write(f"Script: {ai_info.get('name')} (ID: {script_id})\n")
                f.write(f"Opponent: {bot_opponent['name']} - {bot_opponent['desc']}\n")
                f.write(f"Date: {timestamp}\n")
                f.write(f"Total Fights: {len(fight_logs)}\n\n")
                
                for fight_data in fight_logs:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"Fight {fight_data['fight_id']} - {fight_data['result']}\n")
                    f.write(f"URL: {fight_data['url']}\n")
                    f.write(f"{'='*60}\n\n")
                    
                    # Parse and display key log events
                    if fight_data['logs']:
                        current_turn = 0
                        logs_to_show = fight_data['logs'][:200]  # Show more logs
                        
                        for log_entry in logs_to_show:
                            if isinstance(log_entry, dict):
                                # Parsed log format
                                message = str(log_entry.get('message', ''))
                                entity_name = "V6" if log_entry.get('farmer_id') == str(self.farmer.get('id')) else bot_opponent['name']
                                
                                # Check for turn markers
                                if "Turn" in str(message) or "turn" in str(message).lower():
                                    turn_match = re.search(r'[Tt]urn (\d+)', str(message))
                                    if turn_match:
                                        new_turn = int(turn_match.group(1))
                                        if new_turn != current_turn:
                                            current_turn = new_turn
                                            f.write(f"\n{'='*40}\n")
                                            f.write(f"TURN {current_turn}\n")
                                            f.write(f"{'='*40}\n")
                                
                                # Format the log message
                                if message:
                                    f.write(f"[{entity_name}] {message}\n")
                            elif isinstance(log_entry, list) and len(log_entry) >= 4:
                                # Raw log format [leek_id, type, line, message, ...]
                                message = log_entry[3] if len(log_entry) > 3 else ""
                                entity_name = "V6"  # Default
                                
                                # Check for turn markers
                                if "Turn" in str(message) or "turn" in str(message).lower():
                                    turn_match = re.search(r'[Tt]urn (\d+)', str(message))
                                    if turn_match:
                                        new_turn = int(turn_match.group(1))
                                        if new_turn != current_turn:
                                            current_turn = new_turn
                                            f.write(f"\n{'='*40}\n")
                                            f.write(f"TURN {current_turn}\n")
                                            f.write(f"{'='*40}\n")
                                
                                # Format the log message
                                if message:
                                    f.write(f"[{entity_name}] {message}\n")
                        
                        if len(fight_data['logs']) > 100:
                            f.write(f"\n... {len(fight_data['logs']) - 100} more log entries ...\n")
            
            print(f"📊 Log analysis saved to: {analysis_file}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 lw_test_script.py <script_id> <num_tests> [opponent] [--leek <name>]")
        print("Example: python3 lw_test_script.py 445124 10")
        print("         python3 lw_test_script.py 445124 10 domingo --leek RabiesLeek")
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
    
    # Parse optional args: opponent and --leek <name>
    opponent_name = None
    preferred_leek_name = None
    i = 3
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--leek" and i + 1 < len(sys.argv):
            preferred_leek_name = sys.argv[i + 1]
            i += 2
        else:
            if opponent_name is None:
                opponent_name = arg.lower()
            i += 1
    if opponent_name is None:
        opponent_name = "domingo"
    
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

    # Login credentials from config - Cure account
    email, password = load_credentials(account="cure")

    # Login
    if not tester.login(email, password):
        print("\n❌ Failed to login")
        return 1
    
    try:
        # Run tests with specific opponent and preferred leek
        # Temporarily wrap to pass preferred_leek_name down to setup
        # (Monkey-patch run_tests to include the leek parameter)
        original_setup = tester.setup_test_scenario
        def setup_with_leek(script_id_p, bot_opponent_p):
            return original_setup(script_id_p, bot_opponent_p, preferred_leek_name)
        tester.setup_test_scenario = setup_with_leek
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
