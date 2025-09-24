#!/usr/bin/env python3
"""
LeekWars Auto Boss Fighter
Allows selection of specific boss and number of fights via command-line arguments
Usage: python3 lw_boss_fights.py <boss_number> <num_fights> [--quick]
Example: python3 lw_boss_fights.py 2 10 --quick

Boss types:
- Boss 1: nasu_samurai (Level 100, difficulty 1)
- Boss 2: fennel_king (Level 200, difficulty 2)  
- Boss 3: evil_pumpkin (Level 300, difficulty 3)

Note: Boss fights are squad-based multiplayer events using WebSocket connections.
"""

import requests
import json
import random
import time
from datetime import datetime
from getpass import getpass
import os
import sys
import argparse
import websocket
import threading
import ssl

BASE_URL = "https://leekwars.com/api"
WS_URL = "wss://leekwars.com/ws"

class LeekWarsBossFighter:
    def __init__(self):
        """Initialize session and variables"""
        self.session = requests.Session()
        self.farmer = None
        self.token = None
        self.leeks = {}
        self.total_fights = 0
        self.fights_run = []
        self.fight_ids = []  # Store fight IDs for later log retrieval
        
        # WebSocket related
        self.ws = None
        self.ws_connected = False
        self.squad_id = None
        self.boss_squads = {}
        self.current_squad = None
        self.fight_started = False
        
        # Boss definitions from frontend code
        self.BOSSES = {
            1: {"id": 1, "name": "nasu_samurai", "level": 100, "difficulty": 1},
            2: {"id": 2, "name": "fennel_king", "level": 200, "difficulty": 2},
            3: {"id": 3, "name": "evil_pumpkin", "level": 300, "difficulty": 3}
        }
        
        # WebSocket message types (from frontend)
        self.SocketMessage = {
            'GARDEN_BOSS_CREATE_SQUAD': 66,
            'GARDEN_BOSS_JOIN_SQUAD': 67,
            'GARDEN_BOSS_ADD_LEEK': 68,
            'GARDEN_BOSS_REMOVE_LEEK': 69,
            'GARDEN_BOSS_ATTACK': 71,
            'GARDEN_BOSS_LISTEN': 72,
            'GARDEN_BOSS_SQUADS': 73,
            'GARDEN_BOSS_SQUAD_JOINED': 74,
            'GARDEN_BOSS_LEAVE_SQUAD': 75,
            'GARDEN_BOSS_SQUAD': 76,
            'GARDEN_BOSS_NO_SUCH_SQUAD': 77,
            'GARDEN_BOSS_STARTED': 78,
            'GARDEN_BOSS_LEFT': 82
        }
        
    def login(self, email, password):
        """Login using email and password, maintain session cookies"""
        print("🔐 Logging in...")
        
        login_url = f"{BASE_URL}/farmer/login-token"
        login_data = {
            "login": email,
            "password": password
        }
        
        try:
            response = self.session.post(login_url, data=login_data)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # The API returns farmer data directly on successful login
                    # It doesn't have a 'success' field when login is successful
                    if "farmer" in data and "token" in data:
                        self.farmer = data["farmer"]
                        self.token = data["token"]
                        
                        # Extract leeks - they are in the farmer object
                        self.leeks = self.farmer.get("leeks", {})
                        
                        # Extract fight count
                        self.total_fights = self.farmer.get("fights", 0)
                        
                        # Display farmer info
                        farmer_name = self.farmer.get("login", "Unknown")
                        farmer_id = self.farmer.get("id", "Unknown")
                        victories = self.farmer.get("victories", 0)
                        draws = self.farmer.get("draws", 0)
                        defeats = self.farmer.get("defeats", 0)
                        ratio = self.farmer.get("ratio", 0)
                        money = self.farmer.get("habs", 0)
                        
                        print(f"\n✅ Connected successfully!")
                        print(f"   👤 Farmer: {farmer_name} (ID: {farmer_id})")
                        print(f"   💰 Habs: {money:,}")
                        print(f"   📊 Stats: {victories}V / {draws}D / {defeats}L (Ratio: {ratio})")
                        print(f"   🗡️ Available fights: {self.total_fights}")
                        print(f"   🥬 Leeks found: {len(self.leeks)}")
                        
                        # Debug: Show cookies
                        cookies = list(self.session.cookies.keys())
                        if cookies:
                            print(f"   🍪 Session cookies: {cookies}")
                        
                        # Show leek details
                        if self.leeks:
                            print("\n   Your leeks:")
                            for leek_id, leek_data in self.leeks.items():
                                print(f"     - {leek_data.get('name', 'Unknown')} (Level {leek_data.get('level', 0)})")
                                print(f"       Stats: {leek_data.get('strength', 0)} STR, {leek_data.get('life', 0)} HP")
                        
                        return True
                    
                    # Check for error response (when login fails)
                    elif "success" in data and not data["success"]:
                        error_msg = data.get("error", "Unknown error")
                        print(f"   ❌ Login failed: {error_msg}")
                        return False
                    
                    else:
                        print(f"   ❌ Unexpected response structure")
                        print(f"   Keys found: {list(data.keys())}")
                        return False
                        
                except json.JSONDecodeError as e:
                    print(f"   ❌ Failed to parse JSON response: {e}")
                    return False
                    
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {e}")
            return False
    
    def connect_websocket(self):
        """Connect to LeekWars WebSocket for boss fights"""
        print("🔌 Connecting to WebSocket...")
        
        try:
            # Get session cookies for WebSocket authentication
            cookies = "; ".join([f"{name}={value}" for name, value in self.session.cookies.items()])
            
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    self.handle_websocket_message(data)
                except json.JSONDecodeError:
                    pass
            
            def on_error(ws, error):
                print(f"   ❌ WebSocket error: {error}")
            
            def on_close(ws, close_status_code, close_msg):
                print("   🔌 WebSocket disconnected")
                self.ws_connected = False
            
            def on_open(ws):
                print("   ✅ WebSocket connected")
                self.ws_connected = True
                # Listen for boss squad updates
                self.send_websocket_message([self.SocketMessage['GARDEN_BOSS_LISTEN']])
            
            # Create WebSocket connection with cookies
            websocket.enableTrace(False)
            self.ws = websocket.WebSocketApp(
                WS_URL,
                header={"Cookie": cookies},
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            
            # Start WebSocket in a separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever, kwargs={'sslopt': {"cert_reqs": ssl.CERT_NONE}})
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            # Wait for connection
            timeout = 10
            while not self.ws_connected and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1
            
            if not self.ws_connected:
                print("   ❌ Failed to connect to WebSocket")
                return False
                
            return True
            
        except Exception as e:
            print(f"   ❌ WebSocket connection failed: {e}")
            return False
    
    def send_websocket_message(self, message):
        """Send a message via WebSocket"""
        if self.ws and self.ws_connected:
            try:
                self.ws.send(json.dumps(message))
            except Exception as e:
                print(f"   ❌ Failed to send WebSocket message: {e}")
    
    def handle_websocket_message(self, data):
        """Handle incoming WebSocket messages"""
        if not isinstance(data, list) or len(data) < 1:
            return
        
        message_type = data[0]
        
        if message_type == self.SocketMessage['GARDEN_BOSS_SQUADS']:
            # Boss squads list received
            if len(data) > 1:
                self.boss_squads = data[1]
                print(f"   📋 Received boss squads data")
                
        elif message_type == self.SocketMessage['GARDEN_BOSS_SQUAD_JOINED']:
            # Successfully joined a squad
            if len(data) > 1:
                self.current_squad = data[1]
                self.squad_id = self.current_squad.get('id')
                print(f"   ✅ Joined squad: {self.squad_id}")
                
        elif message_type == self.SocketMessage['GARDEN_BOSS_SQUAD']:
            # Squad update received
            if len(data) > 1:
                self.current_squad = data[1]
                print(f"   📊 Squad updated")
                
        elif message_type == self.SocketMessage['GARDEN_BOSS_STARTED']:
            # Boss fight started
            if len(data) > 1:
                fight_id = data[1]
                self.fight_ids.append(fight_id)
                self.fight_started = True
                print(f"   🎮 Boss fight started: {fight_id}")
                
        elif message_type == self.SocketMessage['GARDEN_BOSS_NO_SUCH_SQUAD']:
            print(f"   ❌ Squad not found")
            
        elif message_type == self.SocketMessage['GARDEN_BOSS_LEFT']:
            print(f"   👋 Left squad")
            self.current_squad = None
            self.squad_id = None
            
    def create_boss_squad(self, boss_level):
        """Create a new boss squad for the specified boss"""
        boss = self.BOSSES.get(boss_level)
        if not boss:
            print(f"   ❌ Invalid boss level: {boss_level}")
            return False
            
        print(f"   🎯 Creating squad for {boss['name']} (Level {boss['level']})")
        
        # Get all leek IDs for the squad
        leek_ids = list(self.leeks.keys())
        if not leek_ids:
            print(f"   ❌ No leeks available for squad")
            return False
        
        # Create squad: [message_type, boss_id, locked, leek_ids]
        message = [
            self.SocketMessage['GARDEN_BOSS_CREATE_SQUAD'],
            boss['id'],
            False,  # Not locked (public squad)
            [int(leek_id) for leek_id in leek_ids]  # All available leeks
        ]
        
        self.send_websocket_message(message)
        
        # Wait for squad creation response
        timeout = 10
        while not self.squad_id and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1
        
        if self.squad_id:
            print(f"   ✅ Squad created: {self.squad_id}")
            return True
        else:
            print(f"   ❌ Failed to create squad")
            return False
    
    def add_leeks_to_squad(self):
        """Add all available leeks to the current squad"""
        if not self.current_squad:
            return False
            
        # Add each leek to the squad
        for leek_id, leek_data in self.leeks.items():
            message = [self.SocketMessage['GARDEN_BOSS_ADD_LEEK'], int(leek_id)]
            self.send_websocket_message(message)
            time.sleep(0.1)  # Small delay between additions
            
        return True
    
    def start_boss_attack(self):
        """Start the boss attack with current squad"""
        if not self.current_squad:
            print(f"   ❌ No squad available for attack")
            return False
            
        print(f"   ⚔️ Starting boss attack...")
        message = [self.SocketMessage['GARDEN_BOSS_ATTACK']]
        self.send_websocket_message(message)
        
        # Wait for fight to start
        timeout = 30  # Boss fights may take longer to start
        self.fight_started = False
        
        while not self.fight_started and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1
        
        if self.fight_started:
            print(f"   ✅ Boss fight started!")
            return True
        else:
            print(f"   ❌ Boss fight failed to start")
            return False
    
    def leave_squad(self):
        """Leave the current squad"""
        if self.current_squad:
            message = [self.SocketMessage['GARDEN_BOSS_LEAVE_SQUAD']]
            self.send_websocket_message(message)
            time.sleep(0.5)  # Wait for leave confirmation
        
    def get_fight_log(self, fight_id):
        """Get the detailed log of a fight"""
        url = f"{BASE_URL}/fight/get/{fight_id}"
        
        # Retry mechanism instead of fixed wait
        for attempt in range(3):
            if attempt > 0:
                time.sleep(0.5)  # Short wait between retries
            
            response = self.session.get(url)
            
            if response.status_code == 200:
                break
        else:
            response = self.session.get(url)  # Final attempt
        
        if response.status_code == 200:
            try:
                data = response.json()
                if "fight" in data:
                    fight_data = data["fight"]
                    # Extract relevant fight information
                    fight_log = {
                        "fight_id": fight_id,
                        "date": fight_data.get("date"),
                        "winner": fight_data.get("winner"),
                        "leeks": fight_data.get("leeks", []),
                        "duration": None,
                        "actions_count": 0,
                        "type": "boss"
                    }
                    
                    # Parse report to get duration and action count
                    report = fight_data.get("report")
                    if report:
                        try:
                            actions = json.loads(report) if isinstance(report, str) else report
                            if isinstance(actions, list) and len(actions) > 0:
                                fight_log["actions_count"] = len(actions)
                                last_action = actions[-1]
                                if isinstance(last_action, list) and len(last_action) > 0:
                                    fight_log["duration"] = last_action[0]  # Turn number
                        except:
                            pass
                    
                    return fight_log
            except:
                pass
        
        return None
    
    def download_fight_data(self, fight_id):
        """Download full fight data including replay"""
        url = f"{BASE_URL}/fight/get/{fight_id}"
        
        try:
            response = self.session.get(url)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    def download_fight_logs(self, fight_id):
        """Download debug logs for a fight"""
        url = f"{BASE_URL}/fight/get-logs/{fight_id}"
        
        try:
            response = self.session.get(url)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    def download_all_fight_logs(self, leek_id, leek_name, boss_level):
        """Download all fight logs after battles are complete"""
        if not self.fight_ids:
            return
        
        print(f"\n📥 Downloading logs for {len(self.fight_ids)} boss fights...")
        print(f"   Leek: {leek_name} (ID: {leek_id})")
        print(f"   Boss Level: {boss_level}")
        
        # Create directory for logs using leek ID and boss level
        log_dir = f"fight_logs/boss_{boss_level}/{leek_id}"
        os.makedirs(log_dir, exist_ok=True)
        print(f"   Directory: {log_dir}/")
        
        successful = 0
        failed = []
        
        for i, fight_id in enumerate(self.fight_ids):
            # Rate limiting - 0.3 seconds between requests
            if i > 0:
                time.sleep(0.3)
            
            # Progress indicator
            if i > 0 and i % 10 == 0:
                print(f"   Progress: {i}/{len(self.fight_ids)} ({i*100/len(self.fight_ids):.1f}%)")
            
            # Download fight data
            fight_data = self.download_fight_data(fight_id)
            if fight_data:
                # Save fight data
                data_file = f"{log_dir}/{fight_id}_data.json"
                with open(data_file, "w") as f:
                    json.dump(fight_data, f, indent=2)
                
                # Download debug logs
                logs = self.download_fight_logs(fight_id)
                if logs:
                    logs_file = f"{log_dir}/{fight_id}_logs.json"
                    with open(logs_file, "w") as f:
                        json.dump(logs, f, indent=2)
                
                successful += 1
            else:
                failed.append(fight_id)
        
        print(f"✅ Downloaded logs: {successful}/{len(self.fight_ids)}")
        if failed:
            print(f"❌ Failed: {len(failed)} fights")
        
    def update_farmer_info(self):
        """Update farmer info using session cookies"""
        # Use cookies only - no token in URL
        url = f"{BASE_URL}/farmer/get"
        response = self.session.get(url)
        
        if response.status_code == 200:
            data = response.json()
            # The API might return farmer data directly without success field
            if "farmer" in data:
                self.farmer = data["farmer"]
                self.total_fights = self.farmer.get("fights", 0)
                self.leeks = self.farmer.get("leeks", {})
                return True
        elif response.status_code == 429:
            print("   ⚠️ Rate limited - waiting 2 seconds...")
            time.sleep(2)
            return self.update_farmer_info()
        return False
        
    def run_boss_fights(self, num_fights=None, quick_mode=False, boss_level=1):
        """Run specified number of boss fights at the specified boss level"""
        if not self.leeks:
            print("\n❌ No leeks found in your account!")
            print("   Please create at least one leek on the LeekWars website.")
            return
            
        if self.total_fights == 0:
            print("\n❌ No fights available. Try again tomorrow!")
            print("   Fights reset daily at midnight (French time).")
            return
        
        # Connect to WebSocket first
        if not self.connect_websocket():
            print("\n❌ Failed to connect to WebSocket. Boss fights require WebSocket connection.")
            return
        
        # Use specified number of fights or all available
        if num_fights is None:
            fights_to_run = self.total_fights
        else:
            fights_to_run = min(num_fights, self.total_fights)
            
        boss = self.BOSSES.get(boss_level)
        if not boss:
            print(f"\n❌ Invalid boss level: {boss_level}")
            return
            
        boss_name = boss['name']
        boss_display_name = f"{boss_name} (Level {boss['level']}, Difficulty {boss['difficulty']})"
            
        print("\n" + "="*60)
        print("STARTING AUTOMATIC BOSS FIGHTS")
        if quick_mode:
            print("⚡ QUICK MODE ENABLED - Minimal output")
        print("="*60)
        
        start_time = datetime.now()
        
        print(f"\n📋 Available leeks: {len(self.leeks)}")
        for leek_id, leek_data in self.leeks.items():
            print(f"   - {leek_data.get('name', 'Unknown')} (Level {leek_data.get('level', 0)})")
        print(f"🎯 Target: {boss_display_name}")
        
        fights_completed = 0
        consecutive_failures = 0
        
        print(f"\n🎯 Running {fights_to_run} boss fights...")
        if quick_mode:
            print("   Progress: ", end="", flush=True)
        else:
            print("   Progress will be shown for each fight\n")
        
        while fights_completed < fights_to_run and consecutive_failures < 3:
            # Show progress based on mode
            if quick_mode:
                # In quick mode, just show dots
                if fights_completed > 0 and fights_completed % 5 == 0:
                    print(f"[{fights_completed}]", end="", flush=True)
                else:
                    print(".", end="", flush=True)
            else:
                # Normal mode - show details for each fight
                print(f"\n🥬 Boss Fight #{fights_completed + 1}/{fights_to_run} vs {boss_display_name}")
            
            # Create a new squad for this boss fight
            if not self.create_boss_squad(boss_level):
                consecutive_failures += 1
                if not quick_mode:
                    print(f"   ❌ Failed to create squad for {boss_name}")
                continue
                
            # Add leeks to the squad (they should be added automatically on creation)
            time.sleep(1)  # Wait for squad to be fully created
            
            # Start the boss attack
            if self.start_boss_attack():
                fights_completed += 1
                
                # Get the fight ID from the last started fight
                if self.fight_ids:
                    fight_id = self.fight_ids[-1]
                    fight_url = f"https://leekwars.com/fight/{fight_id}"
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    
                    if not quick_mode:
                        print(f"   ✅ Boss fight started: {fight_id}")
                        print(f"   🔗 {fight_url}")
                    
                    self.fights_run.append({
                        'id': fight_id,
                        'url': fight_url,
                        'boss': boss_name,
                        'boss_level': boss_level,
                        'time': timestamp,
                        'squad_id': self.squad_id
                    })
                
                consecutive_failures = 0
                
            else:
                consecutive_failures += 1
                if not quick_mode:
                    print(f"   ❌ Failed to start boss attack")
            
            # Leave the squad after the fight
            self.leave_squad()
            
            # Small delay between fights
            if fights_completed < fights_to_run:
                time.sleep(2.0 if quick_mode else 3.0)
            
            # Update farmer info periodically to check remaining fights
            if fights_completed > 0 and fights_completed % 5 == 0:
                self.update_farmer_info()
                if self.total_fights == 0:
                    if not quick_mode:
                        print("   ⚠️ No more fights available!")
                    break
        
        if quick_mode:
            print()  # New line after progress dots
        
        # Final summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "="*60)
        print("BOSS FIGHT SESSION COMPLETE")
        print("="*60)
        print(f"✅ Total boss fights completed: {fights_completed}/{fights_to_run}")
        print(f"🎯 Boss: {boss_display_name}")
        
        if fights_completed > 0:
            if duration < 60:
                print(f"⏱️ Time taken: {duration:.1f} seconds")
            else:
                print(f"⏱️ Time taken: {duration/60:.1f} minutes")
            print(f"⚡ Average: {duration/fights_completed:.1f} seconds per fight")
        
        if self.fights_run:
            # Show fight URLs
            if fights_completed <= 5:
                print("\n🔗 Fight URLs:")
                for fight in self.fights_run:
                    print(f"   {fight['url']} (Squad: {fight['squad_id']})")
            elif not quick_mode:
                print(f"\n🔗 Last 3 fights:")
                for fight in self.fights_run[-3:]:
                    print(f"   {fight['url']} (Squad: {fight['squad_id']})")
        
        # Download all fight logs after battles are complete
        if self.fight_ids:
            # Use first leek for log directory
            first_leek = list(self.leeks.values())[0]
            self.download_all_fight_logs(first_leek['id'], first_leek['name'], boss_level)
        
        # Update and show final stats
        print("\n📊 Updating final stats...")
        self.update_farmer_info()
        if self.farmer:
            print(f"   💰 Habs: {self.farmer.get('habs', 0):,}")
            print(f"   🗡️ Remaining fights: {self.farmer.get('fights', 0)}")
        
        # Close WebSocket connection
        if self.ws:
            self.ws.close()
            
    def disconnect(self):
        """Disconnect from LeekWars"""
        if self.token:
            # Try with token first
            url = f"{BASE_URL}/farmer/disconnect/{self.token}"
            response = self.session.post(url)
            if response.status_code == 401:
                # Try without token (using session cookies)
                url = f"{BASE_URL}/farmer/disconnect"
                self.session.post(url)
            print("\n👋 Disconnected from LeekWars")

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='LeekWars Auto Boss Fighter')
    parser.add_argument('boss_level', type=int, help='Boss level to fight (1=Easy, 2=Medium, 3=Hard)')
    parser.add_argument('num_fights', type=int, help='Number of fights to run')
    parser.add_argument('--quick', action='store_true', help='Enable quick mode (minimal output)')
    
    args = parser.parse_args()
    
    # Validate boss level
    if args.boss_level < 1 or args.boss_level > 3:
        print("❌ Error: Boss level must be between 1 and 3")
        print("   1 = Easy Boss")
        print("   2 = Medium Boss") 
        print("   3 = Hard Boss")
        return 1
    
    # Validate fight count
    if args.num_fights < 1:
        print("❌ Error: Number of fights must be at least 1")
        return 1
    
    boss_names = {1: "Easy Boss", 2: "Medium Boss", 3: "Hard Boss"}
    boss_name = boss_names.get(args.boss_level)
    
    print("="*60)
    print("LEEKWARS AUTO BOSS FIGHTER")
    print("="*60)
    print(f"Selected: {boss_name} (Level {args.boss_level})")
    print(f"Fights to run: {args.num_fights}")
    if args.quick:
        print("Mode: Quick (minimal output)")
    print()
    
    # Create fighter instance
    fighter = LeekWarsBossFighter()
    
    # Get credentials
    email = "tanguy.pedrazzoli@gmail.com"   
    password = "tanguy0211"
    
    # Login
    if not fighter.login(email, password):
        print("\n❌ Failed to login. Please check your credentials.")
        return 1
        
    try:
        # Check if we have leeks before asking to run fights
        if not fighter.leeks:
            print("\n⚠️ No leeks found in your account!")
            print("Please create at least one leek on https://leekwars.com")
            return 1
            
        # Ask if user wants to proceed with fights
        if fighter.total_fights > 0:
            print(f"\n🎮 You have {fighter.total_fights} fights available.")
            
            # Run the specified number of fights
            fights_to_run = min(args.num_fights, fighter.total_fights)
           
            # Use quick mode from command-line argument
            quick_mode = args.quick
            
            # Calculate estimated time
            estimated_seconds = fights_to_run * 0.5
            if estimated_seconds < 60:
                estimated_time = f"{int(estimated_seconds)} seconds"
            else:
                estimated_minutes = estimated_seconds / 60
                estimated_time = f"{estimated_minutes:.1f} minutes"
            
            fighter.run_boss_fights(fights_to_run, quick_mode=quick_mode, boss_level=args.boss_level)
        else:
            print("\n⚠️ No fights available right now.")
            print("Fights reset daily at midnight (French time).")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Always disconnect properly
        fighter.disconnect()
        
    return 0

if __name__ == "__main__":
    exit(main())