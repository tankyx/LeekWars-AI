#!/usr/bin/env python3
"""
LeekWars Authenticated Fight Log Retriever
Fetches complete fight logs including debug messages using authentication
Usage: python3 lw_get_fight_auth.py <fight_id>
"""

import requests
import json
import sys
import argparse
import re
from datetime import datetime

BASE_URL = "https://leekwars.com/api"

class LeekWarsFightRetriever:
    def __init__(self):
        """Initialize session"""
        self.session = requests.Session()
        self.token = None
        self.farmer = None
        
    def login(self, email, password):
        """Login using email and password"""
        print("🔐 Logging in...")
        
        login_url = f"{BASE_URL}/farmer/login-token"
        login_data = {
            "login": email,
            "password": password
        }
        
        try:
            response = self.session.post(login_url, data=login_data)
            
            if response.status_code == 200:
                data = response.json()
                
                if "farmer" in data and "token" in data:
                    self.farmer = data["farmer"]
                    self.token = data["token"]
                    
                    farmer_name = self.farmer.get("login", "Unknown")
                    farmer_id = self.farmer.get("id", "Unknown")
                    
                    print(f"✅ Logged in as {farmer_name} (ID: {farmer_id})")
                    return True
                else:
                    print(f"❌ Login failed: {data.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return False
    
    def get_fight(self, fight_id):
        """Fetch authenticated fight data"""
        url = f"{BASE_URL}/fight/get/{fight_id}"
        
        print(f"📊 Fetching fight data for #{fight_id}...")
        
        try:
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                print(f"❌ Failed to get fight: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def get_fight_logs(self, fight_id):
        """Fetch fight logs from authenticated API"""
        # Try multiple possible endpoints
        endpoints = [
            f"{BASE_URL}/fight/get-logs/{fight_id}",
            f"{BASE_URL}/fight-logs/{fight_id}",
            f"{BASE_URL}/report/get/{fight_id}"
        ]
        
        print(f"📜 Fetching debug logs...")
        
        for endpoint in endpoints:
            try:
                response = self.session.get(endpoint)
                if response.status_code == 200:
                    data = response.json()
                    if data and "logs" in data:
                        return data["logs"]
            except:
                continue
        
        return None
    
    def parse_fight_data(self, data, show_logs=True):
        """Parse and display fight data with debug logs"""
        if not data:
            return
        
        fight_id = data.get("id", "Unknown")
        seed = data.get("seed", "Unknown")
        winner = data.get("winner", -1)
        
        print("\n" + "="*60)
        print(f"FIGHT #{fight_id}")
        print("="*60)
        print(f"🎲 Seed: {seed}")
        print(f"🏆 Winner: {'Team 2' if winner == 2 else 'Team 1' if winner == 1 else 'Draw'}")
        
        # Get fight data
        fight_data = data.get("data", {})
        actions = fight_data.get("actions", [])
        
        # Check for logs in different locations
        logs = None
        
        # Method 1: Check in data.logs
        if "logs" in data and data["logs"]:
            logs = data["logs"]
            print(f"\n📝 Found {len(logs)} debug log entries")
        
        # Method 2: Check in data.data.logs
        elif "logs" in fight_data and fight_data["logs"]:
            logs = fight_data["logs"]
            print(f"\n📝 Found {len(logs)} debug log entries")
        
        # Method 3: Check in ops field (operations/debug info)
        elif "ops" in fight_data:
            ops_data = fight_data["ops"]
            if isinstance(ops_data, dict):
                # Try to extract logs from ops
                for entity_id, entity_logs in ops_data.items():
                    if isinstance(entity_logs, list) and entity_logs:
                        if logs is None:
                            logs = []
                        for log_entry in entity_logs:
                            if isinstance(log_entry, list):
                                logs.append([int(entity_id), *log_entry])
        
        # Display logs if found
        if logs and show_logs:
            print("\n" + "-"*60)
            print("DEBUG LOGS")
            print("-"*60)
            
            current_turn = 0
            for log in logs:
                if isinstance(log, list) and len(log) >= 4:
                    entity_id = log[0]
                    ai_name = log[1]
                    line_num = log[2]
                    message = log[3]
                    
                    # Determine entity name
                    if entity_id == 20443:
                        entity_name = "VirusLeek"
                    elif entity_id == -1:
                        entity_name = "Domingo"
                    else:
                        entity_name = f"Entity_{entity_id}"
                    
                    # Check for turn markers in the message
                    if "Turn" in message and "-" in message:
                        turn_match = re.search(r'Turn (\d+)', message)
                        if turn_match:
                            new_turn = int(turn_match.group(1))
                            if new_turn != current_turn:
                                current_turn = new_turn
                                print(f"\n--- Turn {current_turn} ---")
                    
                    # Format the log message
                    print(f"[{entity_name}] {message} [{ai_name}:{line_num}]")
        else:
            print("\n⚠️ No debug logs found (may not be available for this fight)")
        
        # Parse actions
        print("\n" + "-"*60)
        print("BATTLE ACTIONS")
        print("-"*60)
        
        self.parse_actions(actions)
    
    def parse_actions(self, actions):
        """Parse fight actions"""
        weapon_names = {
            1: "Pistolet", 20: "Fusil à pompe", 37: "Hache", 
            47: "Électriseur", 29: "Broadsword", 11: "Shotgun"
        }
        
        chip_names = {
            1: "Shock", 20: "Helmet", 22: "Casque", 23: "Adrénaline",
            29: "Forteresse", 37: "Stalactite", 39: "Iceberg"
        }
        
        current_turn = 0
        current_entity = None
        
        for action in actions:
            if not action:
                continue
            
            code = action[0]
            
            # New turn
            if code == 7:
                entity = action[1] if len(action) > 1 else "?"
                current_entity = entity
                current_turn += 1
                entity_name = "VirusLeek" if entity == 1 else "Domingo"
                print(f"\n📍 Turn {current_turn} - {entity_name}")
            
            # Movement
            elif code == 10:
                entity = action[1] if len(action) > 1 else "?"
                cells = action[3] if len(action) > 3 else []
                mp_used = len(cells) if isinstance(cells, list) else 0
                entity_name = "VirusLeek" if entity == 1 else "Domingo"
                if mp_used > 0:
                    print(f"  🏃 {entity_name} moves {mp_used} MP")
            
            # Use chip
            elif code == 12:
                chip_id = action[1] if len(action) > 1 else "?"
                chip_name = chip_names.get(chip_id, f"Chip_{chip_id}")
                entity = current_entity
                entity_name = "VirusLeek" if entity == 1 else "Domingo"
                print(f"  💊 {entity_name} uses {chip_name}")
            
            # Set weapon
            elif code == 13:
                weapon_id = action[1] if len(action) > 1 else "?"
                weapon_name = weapon_names.get(weapon_id, f"Weapon_{weapon_id}")
                entity = current_entity
                entity_name = "VirusLeek" if entity == 1 else "Domingo"
                print(f"  🔫 {entity_name} equips {weapon_name}")
            
            # Attack
            elif code == 20:
                entity = action[1] if len(action) > 1 else "?"
                weapon_id = action[3] if len(action) > 3 else "?"
                weapon_name = weapon_names.get(weapon_id, f"Weapon_{weapon_id}")
                entity_name = "VirusLeek" if entity == 1 else "Domingo"
                print(f"  ⚔️ {entity_name} attacks with {weapon_name}")
            
            # Say
            elif code == 203:
                message = action[1] if len(action) > 1 else ""
                entity = current_entity
                entity_name = "VirusLeek" if entity == 1 else "Domingo"
                print(f"  💬 {entity_name} says: \"{message}\"")
            
            # Stat changes (HP, shields, etc)
            elif code in [302, 306]:
                if len(action) >= 5:
                    stat_type = action[1]
                    entity = action[2]
                    value = action[4]
                    entity_name = "VirusLeek" if entity == 1 else "Domingo"
                    
                    if stat_type == 0:  # Life
                        if value < 0:
                            print(f"  💔 {entity_name} loses {-value} HP")
                        else:
                            print(f"  💚 {entity_name} gains {value} HP")
            
            # Death
            elif code == 309:
                entity = action[1] if len(action) > 1 else "?"
                entity_name = "VirusLeek" if entity == 1 else "Domingo"
                print(f"  ☠️ {entity_name} dies!")
            
            # End turn
            elif code == 8:
                entity = action[1] if len(action) > 1 else "?"
                tp_used = action[2] if len(action) > 2 else "?"
                mp_used = action[3] if len(action) > 3 else "?"
                entity_name = "VirusLeek" if entity == 1 else "Domingo"
                print(f"  ⏸️ End turn (TP: {tp_used}, MP: {mp_used})")
    
    def save_fight_data(self, data, fight_id):
        """Save fight data to JSON file"""
        filename = f"fight_{fight_id}_auth_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Fight data saved to {filename}")
        return filename

def main():
    parser = argparse.ArgumentParser(
        description='LeekWars Authenticated Fight Log Retriever',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 lw_get_fight_auth.py 49127883
  python3 lw_get_fight_auth.py 49127883 --save
  python3 lw_get_fight_auth.py 49127883 --no-actions
        """
    )
    
    parser.add_argument('fight_id', type=int, help='The fight ID to retrieve')
    parser.add_argument('--save', action='store_true', help='Save fight data to JSON file')
    parser.add_argument('--no-actions', action='store_true', help='Hide battle actions, only show logs')
    parser.add_argument('--raw', action='store_true', help='Display raw JSON data')
    
    args = parser.parse_args()
    
    # Create retriever and login
    retriever = LeekWarsFightRetriever()
    
    # Use the same credentials as the updater
    email = "tanguy.pedrazzoli@gmail.com"
    password = "tanguy0211"
    
    if not retriever.login(email, password):
        print("❌ Failed to login")
        return 1
    
    # Get fight data
    fight_data = retriever.get_fight(args.fight_id)
    
    if not fight_data:
        print(f"❌ Could not retrieve fight #{args.fight_id}")
        return 1
    
    # Try to get additional logs
    logs = retriever.get_fight_logs(args.fight_id)
    if logs:
        if "data" not in fight_data:
            fight_data["data"] = {}
        fight_data["data"]["logs"] = logs
        print(f"✅ Found {len(logs)} debug log entries")
    
    # Display or save
    if args.raw:
        print("\n" + "="*60)
        print("RAW FIGHT DATA")
        print("="*60)
        print(json.dumps(fight_data, indent=2))
    else:
        retriever.parse_fight_data(fight_data, show_logs=not args.no_actions)
    
    if args.save:
        retriever.save_fight_data(fight_data, args.fight_id)
    
    return 0

if __name__ == "__main__":
    exit(main())