#!/usr/bin/env python3
"""
LeekWars Script Testing Tool
Tests a specific script ID against standard test opponents (bots) or custom scenarios

Usage:
  Regular mode:  python3 lw_test_script.py <num_tests> <script_id> [opponent] [--leek <name>]
  Scenario mode: python3 lw_test_script.py <num_tests> --scenario <name>

Examples:
  python3 lw_test_script.py 10 445124 domingo
  python3 lw_test_script.py 10 445124 betalpha --leek RabiesLeek
  python3 lw_test_script.py 1 --scenario graal

Available opponents:
  domingo  (-1): Balanced stats, 600 strength, 300 wisdom
  betalpha (-2): Magic focused, 600 magic, 300 wisdom
  tisma    (-3): Wisdom/Science, 600 wisdom, 300 science
  guj      (-4): Tank, 5000 life
  hachess  (-5): Resistance focused, 600 resistance
  rex      (-6): Agility focused, 600 agility

Note: When using --scenario, the scenario must be pre-configured with map, leeks, AI, and opponents
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
        self.scenario_ai_id = None
        
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
    
    def setup_test_scenario(self, script_id, bot_opponent, preferred_leek_name=None, scenario_name=None):
        """Create or get a test scenario for the script with specific bot opponent"""
        # First, get all existing test scenarios
        url = f"{BASE_URL}/test-scenario/get-all"
        response = self.session.get(url)

        if response.status_code == 200:
            data = response.json()
            self.scenarios = data.get('scenarios', {})
            self.test_leeks = data.get('leeks', [])

            # If scenario_name is specified, look for it first
            if scenario_name:
                for scenario_id, scenario in self.scenarios.items():
                    if scenario.get('name') == scenario_name:
                        # Extract AI ID from scenario
                        scenario_ai = scenario.get('ai')

                        # If scenario doesn't have global AI, try to get from first leek in team1
                        if not scenario_ai:
                            team1 = scenario.get('team1', [])
                            if team1 and len(team1) > 0:
                                # Get AI from first leek
                                scenario_ai = team1[0].get('ai')

                        print(f"📋 Using scenario by name: {scenario_name} (ID: {scenario_id}, AI: {scenario_ai})")
                        # Store the scenario's AI ID for later use
                        self.scenario_ai_id = scenario_ai
                        return scenario_id

                print(f"❌ Scenario '{scenario_name}' not found")
                return None

            # script_id required for non-scenario mode
            if script_id is None:
                print("❌ Script ID required when not using scenario name")
                return None

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
    
    def run_test(self, scenario_id, script_id=None):
        """Run a single test fight"""
        url = f"{BASE_URL}/ai/test-scenario"

        # Build request data
        request_data = {"scenario_id": str(scenario_id)}

        # If script_id provided, use it; otherwise scenario has AI pre-configured
        if script_id:
            request_data["ai_id"] = str(script_id)

        response = self.session.post(url, data=request_data)

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
        time.sleep(1.0)  # Initial wait for fight to complete

        url = f"{BASE_URL}/fight/get/{fight_id}"

        # Retry more times with longer delays as fight might still be processing
        for attempt in range(10):
            if attempt > 0:
                time.sleep(1.0)  # Wait 1 second between retries

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
        # Prepare headers with Bearer token
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        # Method 1: Try the official logs endpoint (requires authentication)
        try:
            url = f"{BASE_URL}/fight/get-logs/{fight_id}"
            response = self.session.get(url, headers=headers)
            print(f"   [DEBUG] get-logs status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   [DEBUG] get-logs data type: {type(data)}, len: {len(data) if isinstance(data, (list, dict)) else 'N/A'}")
                if isinstance(data, dict):
                    print(f"   [DEBUG] get-logs data keys: {list(data.keys())[:10]}")
                    # Save raw response for debugging
                    debug_file = f"debug_logs_{fight_id}.json"
                    with open(debug_file, "w") as f:
                        json.dump(data, f, indent=2)
                    print(f"   [DEBUG] Saved raw logs to {debug_file}")
                elif isinstance(data, list):
                    print(f"   [DEBUG] get-logs returned a list with {len(data)} entries")
                    if len(data) == 0:
                        print(f"   [DEBUG] Empty list - possibly fight still processing or no debug() calls in AI")
                    # Save raw response for debugging
                    debug_file = f"debug_logs_{fight_id}.json"
                    with open(debug_file, "w") as f:
                        json.dump(data, f, indent=2)
                    print(f"   [DEBUG] Saved raw logs to {debug_file}")

                # The response is directly the logs object
                if data and isinstance(data, dict):
                    parsed = self.parse_logs(data)
                    print(f"   [DEBUG] Parsed {len(parsed) if parsed else 0} log entries from get-logs")
                    return parsed
                elif data and isinstance(data, list) and len(data) > 0:
                    return data
        except Exception as e:
            print(f"   [DEBUG] get-logs exception: {e}")

        # Method 2: Try get-report endpoint (for scenario fights)
        try:
            url = f"{BASE_URL}/fight/get-report/{fight_id}"
            response = self.session.get(url, headers=headers)
            print(f"   [DEBUG] get-report status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   [DEBUG] get-report data type: {type(data)}, keys: {list(data.keys())[:10] if isinstance(data, dict) else 'N/A'}")

                # Check for logs in report response
                if isinstance(data, dict) and "logs" in data:
                    logs = data["logs"]
                    print(f"   [DEBUG] Found logs in get-report, type: {type(logs)}, len: {len(logs) if isinstance(logs, (list, dict)) else 'N/A'}")
                    if isinstance(logs, dict):
                        parsed = self.parse_logs(logs)
                        print(f"   [DEBUG] Parsed {len(parsed) if parsed else 0} log entries from get-report")
                        return parsed
                    elif isinstance(logs, list):
                        print(f"   [DEBUG] get-report logs is list with {len(logs)} entries")
                        return logs
        except Exception as e:
            print(f"   [DEBUG] get-report exception: {e}")
        
        # Method 3: Get from fight data - check report field
        try:
            url = f"{BASE_URL}/fight/get/{fight_id}"
            response = self.session.get(url)
            print(f"   [DEBUG] fight/get status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   [DEBUG] fight/get top-level keys: {list(data.keys())[:15]}")

                # Save full fight data for inspection
                debug_file = f"debug_fight_{fight_id}.json"
                with open(debug_file, "w") as f:
                    json.dump(data, f, indent=2)
                print(f"   [DEBUG] Saved full fight data to {debug_file}")

                # Check for logs in different locations
                if "logs" in data and data["logs"]:
                    print(f"   [DEBUG] Found logs in data.logs")
                    return data["logs"]

                # Check report field (might contain logs)
                if "report" in data:
                    report = data["report"]
                    print(f"   [DEBUG] report field exists, type: {type(report)}, truthiness: {bool(report)}, len: {len(report) if isinstance(report, (list, str, dict)) else 'N/A'}")
                    # Report is the action list, not the logs. Logs are separate

                fight_data = data.get("data", {})
                print(f"   [DEBUG] fight_data keys: {list(fight_data.keys())[:15]}")
                if "logs" in fight_data and fight_data["logs"]:
                    print(f"   [DEBUG] Found logs in data.data.logs")
                    return fight_data["logs"]

                # Check in ops field (operations/debug info)
                if "ops" in fight_data:
                    ops_data = fight_data["ops"]
                    print(f"   [DEBUG] ops field type: {type(ops_data)}, keys: {list(ops_data.keys())[:5] if isinstance(ops_data, dict) else 'N/A'}")
                    if isinstance(ops_data, dict):
                        # Sample first entity to see structure
                        first_key = list(ops_data.keys())[0] if ops_data else None
                        if first_key:
                            sample_value = ops_data[first_key]
                            print(f"   [DEBUG] Sample ops['{first_key}'] type: {type(sample_value)}, value: {sample_value if not isinstance(sample_value, (list, dict)) else f'{type(sample_value)} len={len(sample_value)}'}")
                            if isinstance(sample_value, list) and len(sample_value) > 0:
                                print(f"   [DEBUG] First item in list: {sample_value[0]}")

                        logs = []
                        for entity_id, entity_logs in ops_data.items():
                            if isinstance(entity_logs, list) and entity_logs:
                                for log_entry in entity_logs:
                                    if isinstance(log_entry, list):
                                        logs.append([int(entity_id), *log_entry])
                        print(f"   [DEBUG] Extracted {len(logs)} logs from ops")
                        if logs:
                            return logs
                else:
                    print(f"   [DEBUG] No ops field in fight_data")
        except Exception as e:
            print(f"   [DEBUG] fight/get exception: {e}")

        print(f"   [DEBUG] No logs found for fight {fight_id}")
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

    def analyze_logs(self, logs, fight_result):
        """Analyze fight logs to extract useful insights"""
        analysis = {
            'fight_id': fight_result['fight_id'],
            'result': fight_result['result'],
            'url': fight_result['url'],
            'turns': [],
            'errors': [],
            'warnings': [],
            'debug_messages': [],
            'actions_taken': [],
            'strategy_info': None
        }

        current_turn = None
        turn_data = None

        for log_entry in logs:
            if isinstance(log_entry, dict):
                message = str(log_entry.get('message', ''))
            elif isinstance(log_entry, list) and len(log_entry) >= 3:
                message = str(log_entry[2])
            else:
                continue

            # Track turns
            turn_match = re.search(r'[Tt]urn (\d+)', message)
            if turn_match:
                if turn_data:
                    analysis['turns'].append(turn_data)
                current_turn = int(turn_match.group(1))
                turn_data = {
                    'turn': current_turn,
                    'actions': [],
                    'tp_spent': 0,
                    'mp_spent': 0
                }

            # Extract strategy type
            if 'Strategy:' in message or 'Using' in message and 'strategy' in message.lower():
                analysis['strategy_info'] = message

            # Track errors
            if 'ERROR' in message.upper() or 'FAILED' in message.upper():
                analysis['errors'].append({'turn': current_turn, 'message': message})

            # Track warnings
            if 'WARNING' in message.upper() or 'WARN' in message.upper():
                analysis['warnings'].append({'turn': current_turn, 'message': message})

            # Track debug messages (V8 specific patterns)
            if any(keyword in message for keyword in ['[DEBUG]', 'TP:', 'MP:', 'HP:', 'Damage:', 'Range:', 'Cell:']):
                analysis['debug_messages'].append({'turn': current_turn, 'message': message})

            # Track actions
            if any(action in message for action in ['useWeapon', 'useChip', 'moveToward', 'setWeapon']):
                if turn_data:
                    turn_data['actions'].append(message)

            # Track TP/MP expenditure
            tp_match = re.search(r'TP[:\s]+(\d+)', message)
            if tp_match and turn_data:
                turn_data['tp_spent'] += int(tp_match.group(1))

            mp_match = re.search(r'MP[:\s]+(\d+)', message)
            if mp_match and turn_data:
                turn_data['mp_spent'] += int(mp_match.group(1))

        # Add last turn
        if turn_data:
            analysis['turns'].append(turn_data)

        return analysis
    
    def run_tests(self, script_id, num_tests, bot_opponent, save_logs=True, scenario_name=None):
        """Run multiple test fights against specific bot opponent or scenario"""
        if scenario_name:
            print(f"\n🎯 Running {num_tests} test fights...")
            print(f"📋 Scenario: {scenario_name} (pre-configured)")
        else:
            print(f"\n🎯 Running {num_tests} test fights for script {script_id} vs {bot_opponent['name']}...")
            print(f"🤖 Opponent: {bot_opponent['name']} - {bot_opponent['desc']}")
        if save_logs:
            print("📜 Log retrieval: ENABLED")

        # Get script info (optional for scenario mode)
        ai_info = None
        if script_id:
            ai_info = self.get_script_info(script_id)
            if not ai_info and not scenario_name:
                print("❌ Could not find script")
                return

        # Setup test scenario with specific bot
        scenario_id = self.setup_test_scenario(script_id, bot_opponent, scenario_name=scenario_name)
        if not scenario_id:
            print("❌ Could not create/find test scenario")
            return

        # If using scenario mode and no script_id, use the scenario's AI ID
        ai_id_to_use = script_id if script_id else self.scenario_ai_id

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
            fight_id = self.run_test(scenario_id, ai_id_to_use)
            
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
                        time.sleep(2.0)  # Longer delay to ensure fight is fully processed
                        logs = self.get_fight_logs(fight_id)
                        if not logs and i == 0:  # Debug first fight only
                            print(f"\n   ⚠️ No logs retrieved for fight {fight_id}")
                            print(f"   [INFO] If AI doesn't use debug() calls, logs will be empty")
                    else:
                        logs = None

                    if logs:
                        # Analyze the logs
                        analysis = self.analyze_logs(logs, fight_result)

                        fight_logs.append({
                            "fight_id": fight_id,
                            "result": fight_result["result"],
                            "url": fight_result["url"],
                            "logs": logs,
                            "analysis": analysis
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
        file_suffix = scenario_name if scenario_name else f"{script_id}"
        results_file = f"test_results_{file_suffix}_{timestamp}.json"

        result_data = {
            "timestamp": timestamp,
            "num_tests": num_tests,
            "results": results,
            "win_rate": win_rate,
            "fight_urls": fight_urls
        }

        if scenario_name:
            result_data["scenario_name"] = scenario_name
        if script_id:
            result_data["script_id"] = script_id
        if ai_info:
            result_data["script_name"] = ai_info.get('name')
        if not scenario_name:
            result_data["opponent"] = bot_opponent['name']
            result_data["opponent_desc"] = bot_opponent['desc']

        with open(results_file, "w") as f:
            json.dump(result_data, f, indent=2)

        print(f"\n💾 Results saved to: {results_file}")

        # Save fight logs to separate file if we have them
        if fight_logs:
            opponent_suffix = scenario_name if scenario_name else bot_opponent['name'].lower()
            logs_file = f"fight_logs_{file_suffix}_{opponent_suffix}_{timestamp}.json"

            log_data = {
                "timestamp": timestamp,
                "fights": fight_logs
            }

            if scenario_name:
                log_data["scenario_name"] = scenario_name
            if script_id:
                log_data["script_id"] = script_id
            if ai_info:
                log_data["script_name"] = ai_info.get('name')
            if not scenario_name:
                log_data["opponent"] = bot_opponent['name']

            with open(logs_file, "w") as f:
                json.dump(log_data, f, indent=2)

            print(f"📜 Fight logs saved to: {logs_file}")

            # Also create a simplified log analysis
            analysis_file = f"log_analysis_{file_suffix}_{opponent_suffix}_{timestamp}.txt"
            with open(analysis_file, "w") as f:
                f.write(f"Fight Log Analysis\n")
                f.write(f"==================\n")
                if scenario_name:
                    f.write(f"Scenario: {scenario_name}\n")
                if script_id and ai_info:
                    f.write(f"Script: {ai_info.get('name')} (ID: {script_id})\n")
                elif script_id:
                    f.write(f"Script ID: {script_id}\n")
                if not scenario_name:
                    f.write(f"Opponent: {bot_opponent['name']} - {bot_opponent['desc']}\n")
                f.write(f"Date: {timestamp}\n")
                f.write(f"Total Fights: {len(fight_logs)}\n\n")

                for fight_data in fight_logs:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"Fight {fight_data['fight_id']} - {fight_data['result']}\n")
                    f.write(f"URL: {fight_data['url']}\n")
                    f.write(f"{'='*60}\n\n")

                    # Show analysis summary if available
                    if 'analysis' in fight_data:
                        analysis = fight_data['analysis']

                        # Strategy info
                        if analysis.get('strategy_info'):
                            f.write(f"Strategy: {analysis['strategy_info']}\n\n")

                        # Errors
                        if analysis.get('errors'):
                            f.write(f"⚠️ ERRORS ({len(analysis['errors'])}):\n")
                            for err in analysis['errors']:
                                f.write(f"  Turn {err['turn']}: {err['message']}\n")
                            f.write("\n")

                        # Warnings
                        if analysis.get('warnings'):
                            f.write(f"⚠️ WARNINGS ({len(analysis['warnings'])}):\n")
                            for warn in analysis['warnings']:
                                f.write(f"  Turn {warn['turn']}: {warn['message']}\n")
                            f.write("\n")

                        # Turn-by-turn summary
                        if analysis.get('turns'):
                            f.write(f"Turn Summary:\n")
                            for turn in analysis['turns']:
                                f.write(f"\n  Turn {turn['turn']}:\n")
                                f.write(f"    TP spent: {turn['tp_spent']}\n")
                                f.write(f"    MP spent: {turn['mp_spent']}\n")
                                if turn['actions']:
                                    f.write(f"    Actions: {len(turn['actions'])}\n")
                                    for action in turn['actions'][:5]:  # Show first 5
                                        f.write(f"      - {action}\n")
                                    if len(turn['actions']) > 5:
                                        f.write(f"      ... and {len(turn['actions']) - 5} more\n")
                            f.write("\n")

                    # Parse and display key log events
                    if fight_data['logs']:
                        f.write(f"\n{'='*40}\n")
                        f.write(f"DETAILED LOGS\n")
                        f.write(f"{'='*40}\n\n")

                        current_turn = 0
                        logs_to_show = fight_data['logs'][:200]  # Show more logs

                        for log_entry in logs_to_show:
                            if isinstance(log_entry, dict):
                                # Parsed log format
                                message = str(log_entry.get('message', ''))
                                opponent_display = bot_opponent['name'] if not scenario_name else "Opponent"
                                entity_name = "V8" if log_entry.get('farmer_id') == str(self.farmer.get('id')) else opponent_display

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
                                entity_name = "V8"  # Default

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

                        if len(fight_data['logs']) > 200:
                            f.write(f"\n... {len(fight_data['logs']) - 200} more log entries ...\n")

            print(f"📊 Log analysis saved to: {analysis_file}")

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Regular mode:  python3 lw_test_script.py <num_tests> <script_id> [opponent] [--leek <name>]")
        print("  Scenario mode: python3 lw_test_script.py <num_tests> --scenario <name>")
        print("\nExamples:")
        print("  python3 lw_test_script.py 10 445124 domingo")
        print("  python3 lw_test_script.py 10 445124 betalpha --leek RabiesLeek")
        print("  python3 lw_test_script.py 1 --scenario graal")
        print("\nAvailable opponents:")
        for name, bot in BOTS.items():
            print(f"  {name:8} - {bot['desc']}")
        print("\nDefault: domingo (if opponent not specified in regular mode)")
        print("Note: Scenario mode uses pre-configured scenario (map, leeks, AI, opponents)")
        return 1

    try:
        num_tests = int(sys.argv[1])
    except ValueError:
        print("❌ Invalid argument. Number of tests must be an integer.")
        return 1

    # Parse optional args: script_id, opponent, --leek <name>, and --scenario <name>
    script_id = None
    opponent_name = None
    preferred_leek_name = None
    scenario_name = None
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--leek" and i + 1 < len(sys.argv):
            preferred_leek_name = sys.argv[i + 1]
            i += 2
        elif arg == "--scenario" and i + 1 < len(sys.argv):
            scenario_name = sys.argv[i + 1]
            i += 2
        else:
            # Try to parse as script_id first (integer)
            if script_id is None:
                try:
                    script_id = int(arg)
                    i += 1
                    continue
                except ValueError:
                    pass

            # Otherwise treat as opponent name
            if opponent_name is None:
                opponent_name = arg.lower()
            i += 1

    # Validate arguments based on mode
    if scenario_name:
        # Scenario mode: script_id optional, opponent optional
        bot_opponent = BOTS.get("domingo")  # Dummy opponent, won't be used
    else:
        # Regular mode: script_id required, opponent optional (default domingo)
        if script_id is None:
            print("❌ Script ID required when not using --scenario")
            return 1

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
    if script_id:
        print(f"Script ID: {script_id}")
    print(f"Number of tests: {num_tests}")
    if scenario_name:
        print(f"Scenario: {scenario_name} (pre-configured)")
    else:
        print(f"Opponent: {bot_opponent['name']} - {bot_opponent['desc']}")
    
    # Create tester instance
    tester = LeekWarsScriptTester()

    # Login credentials from config
    email, password = load_credentials()

    # Login
    if not tester.login(email, password):
        print("\n❌ Failed to login")
        return 1
    
    try:
        # Run tests with specific opponent, preferred leek, and scenario
        # Temporarily wrap to pass preferred_leek_name and scenario_name down to setup
        # (Monkey-patch setup_test_scenario to include these parameters)
        original_setup = tester.setup_test_scenario
        def setup_with_params(script_id_p, bot_opponent_p, **kwargs):
            return original_setup(script_id_p, bot_opponent_p, preferred_leek_name, **kwargs)
        tester.setup_test_scenario = setup_with_params
        tester.run_tests(script_id, num_tests, bot_opponent, scenario_name=scenario_name)
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
    
    return 0

if __name__ == "__main__":
    exit(main())
