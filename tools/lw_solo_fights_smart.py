#!/usr/bin/env python3
"""
LeekWars Auto Solo Fighter - Smart Opponent Selection
Tracks wins/losses against opponents and avoids those who have beaten us
Usage: python3 lw_solo_fights_smart.py <leek_number> <num_fights>
Example: python3 lw_solo_fights_smart.py 2 25
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

BASE_URL = "https://leekwars.com/api"

class OpponentTracker:
    def __init__(self, leek_id):
        """Initialize opponent tracking for a specific leek"""
        self.leek_id = leek_id
        self.data_file = f"opponent_tracker_{leek_id}.json"
        self.data = self.load_data()
        
    def load_data(self):
        """Load opponent tracking data from file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default structure
        return {
            "leek_id": self.leek_id,
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "opponents": {},
            "stats": {
                "total_fights": 0,
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "opponents_beaten": 0,
                "opponents_lost_to": 0,
                "avoided_opponents": 0
            }
        }
    
    def save_data(self):
        """Save opponent tracking data to file"""
        self.data["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Warning: Could not save opponent data: {e}")
    
    def record_fight(self, opponent_id, opponent_name, result):
        """Record a fight result against an opponent"""
        opponent_key = str(opponent_id)
        
        if opponent_key not in self.data["opponents"]:
            self.data["opponents"][opponent_key] = {
                "id": opponent_id,
                "name": opponent_name,
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "first_fought": datetime.now().isoformat(),
                "last_fought": datetime.now().isoformat(),
                "win_rate": 0.0,
                "status": "unknown"  # "beatable", "dangerous", "even"
            }
        
        opponent = self.data["opponents"][opponent_key]
        opponent["name"] = opponent_name  # Update name in case it changed
        opponent["last_fought"] = datetime.now().isoformat()
        
        # Record the result
        if result == "WIN":
            opponent["wins"] += 1
            self.data["stats"]["wins"] += 1
        elif result == "LOSS":
            opponent["losses"] += 1
            self.data["stats"]["losses"] += 1
        elif result == "DRAW":
            opponent["draws"] += 1
            self.data["stats"]["draws"] += 1
        
        self.data["stats"]["total_fights"] += 1
        
        # Calculate win rate
        total_fights = opponent["wins"] + opponent["losses"] + opponent["draws"]
        if total_fights > 0:
            opponent["win_rate"] = opponent["wins"] / total_fights
            
            # Update status based on performance
            if opponent["wins"] >= 2 and opponent["win_rate"] >= 0.7:
                opponent["status"] = "beatable"
            elif opponent["losses"] >= 2 and opponent["win_rate"] <= 0.3:
                opponent["status"] = "dangerous"
            else:
                opponent["status"] = "even"
        
        # Update global stats
        self.update_global_stats()
        self.save_data()
    
    def update_global_stats(self):
        """Update global statistics"""
        beatable = 0
        dangerous = 0
        
        for opponent in self.data["opponents"].values():
            if opponent["status"] == "beatable":
                beatable += 1
            elif opponent["status"] == "dangerous":
                dangerous += 1
        
        self.data["stats"]["opponents_beaten"] = beatable
        self.data["stats"]["opponents_lost_to"] = dangerous
    
    def should_avoid_opponent(self, opponent_id, avoid_strategy="dangerous"):
        """Check if we should avoid fighting this opponent"""
        opponent_key = str(opponent_id)
        
        if opponent_key not in self.data["opponents"]:
            return False  # Unknown opponent, don't avoid
        
        opponent = self.data["opponents"][opponent_key]
        
        if avoid_strategy == "dangerous":
            # Avoid opponents who have beaten us consistently
            return opponent["status"] == "dangerous"
        elif avoid_strategy == "conservative":
            # Avoid opponents with any losses or low win rate
            return opponent["losses"] > 0 or opponent["win_rate"] < 0.5
        elif avoid_strategy == "strict":
            # Only fight opponents we've consistently beaten
            return opponent["status"] != "beatable"
        
        return False
    
    def get_preferred_opponents(self, available_opponents, strategy="smart"):
        """Filter and sort opponents based on our strategy"""
        if strategy == "random":
            return available_opponents
        
        # Separate opponents into categories
        beatable = []
        unknown = []
        risky = []
        
        for opp in available_opponents:
            opp_id = str(opp["id"])
            
            if opp_id in self.data["opponents"]:
                opponent_data = self.data["opponents"][opp_id]
                if opponent_data["status"] == "beatable":
                    beatable.append((opp, opponent_data["win_rate"]))
                elif opponent_data["status"] == "dangerous":
                    risky.append((opp, opponent_data["win_rate"]))
                else:
                    unknown.append((opp, opponent_data["win_rate"]))
            else:
                unknown.append((opp, 0.5))  # Neutral win rate for unknown
        
        # Sort each category by win rate (highest first)
        beatable.sort(key=lambda x: x[1], reverse=True)
        unknown.sort(key=lambda x: x[1], reverse=True)
        risky.sort(key=lambda x: x[1], reverse=True)
        
        if strategy == "safe":
            # Prefer beatable > unknown > avoid risky
            result = [x[0] for x in beatable] + [x[0] for x in unknown]
        elif strategy == "smart":
            # Prefer beatable > unknown > risky (but include some risky for variety)
            result = [x[0] for x in beatable] + [x[0] for x in unknown] + [x[0] for x in risky[:2]]
        elif strategy == "aggressive":
            # Include all, but prefer beatable first
            result = [x[0] for x in beatable] + [x[0] for x in unknown] + [x[0] for x in risky]
        else:
            result = available_opponents
        
        return result if result else available_opponents
    
    def get_stats_summary(self):
        """Get a summary of our opponent tracking stats"""
        stats = self.data["stats"]
        return {
            "total_fights": stats["total_fights"],
            "win_rate": stats["wins"] / max(stats["total_fights"], 1),
            "opponents_tracked": len(self.data["opponents"]),
            "beatable_opponents": stats["opponents_beaten"],
            "dangerous_opponents": stats["opponents_lost_to"]
        }

class LeekWarsSmartFighter:
    def __init__(self):
        """Initialize session and variables"""
        self.session = requests.Session()
        self.farmer = None
        self.token = None
        self.leeks = {}
        self.total_fights = 0
        self.fights_run = []
        self.fight_ids = []
        self.opponent_tracker = None
        
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
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    if "farmer" in data and "token" in data:
                        self.farmer = data["farmer"]
                        self.token = data["token"]
                        self.leeks = self.farmer.get("leeks", {})
                        self.total_fights = self.farmer.get("fights", 0)
                        
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
                        
                        if self.leeks:
                            print("\n   Your leeks:")
                            for leek_id, leek_data in self.leeks.items():
                                print(f"     - {leek_data.get('name', 'Unknown')} (Level {leek_data.get('level', 0)})")
                        
                        return True
                    
                    elif "success" in data and not data["success"]:
                        error_msg = data.get("error", "Unknown error")
                        print(f"   ❌ Login failed: {error_msg}")
                        return False
                    
                    else:
                        print(f"   ❌ Unexpected response structure")
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
    
    def get_leek_opponents(self, leek_id, verbose=False):
        """Get available opponents for a leek using session cookies"""
        url = f"{BASE_URL}/garden/get-leek-opponents/{leek_id}"
        
        response = self.session.get(url)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if "opponents" in data:
                    opponents = data.get("opponents", [])
                    if opponents and verbose:
                        print(f"   ✅ Found {len(opponents)} opponents")
                    return opponents
                elif data.get("success") == False:
                    error = data.get("error", "Unknown error")
                    if verbose:
                        print(f"   ❌ API error: {error}")
                else:
                    if verbose:
                        print(f"   ⚠️ No opponents available")
            except json.JSONDecodeError:
                if verbose:
                    print(f"   ❌ Invalid JSON response")
        elif response.status_code == 429:
            if verbose:
                print(f"   ⚠️ Rate limited - waiting 2 seconds...")
            time.sleep(2)
            return self.get_leek_opponents(leek_id, verbose)
        else:
            if verbose:
                print(f"   ❌ HTTP Error: {response.status_code}")
            
        return []
    
    def start_solo_fight(self, leek_id, opponent_id):
        """Start a solo fight between leek and opponent using session cookies"""
        url = f"{BASE_URL}/garden/start-solo-fight"
        
        data = {
            "leek_id": str(leek_id),
            "target_id": str(opponent_id)
        }
        
        response = self.session.post(url, data=data)
        
        if response.status_code == 200:
            result = response.json()
            if "fight" in result:
                return result["fight"]
            elif result.get("success") == False:
                error = result.get("error", "Unknown error")
                print(f"   ❌ Failed to start fight: {error}")
            else:
                print(f"   ❌ Unexpected response: {result}")
        elif response.status_code == 429:
            print(f"   ⚠️ Rate limited - waiting 2 seconds...")
            time.sleep(2)
            return self.start_solo_fight(leek_id, opponent_id)
        else:
            print(f"   ❌ HTTP Error starting fight: {response.status_code}")
        return None
    
    def get_fight_log(self, fight_id):
        """Get the detailed log of a fight"""
        url = f"{BASE_URL}/fight/get/{fight_id}"
        
        for attempt in range(3):
            if attempt > 0:
                time.sleep(0.5)
            
            response = self.session.get(url)
            
            if response.status_code == 200:
                break
        else:
            response = self.session.get(url)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if "fight" in data:
                    fight_data = data["fight"]
                    fight_log = {
                        "fight_id": fight_id,
                        "date": fight_data.get("date"),
                        "winner": fight_data.get("winner"),
                        "leeks": fight_data.get("leeks", []),
                        "duration": None,
                        "actions_count": 0
                    }
                    
                    report = fight_data.get("report")
                    if report:
                        try:
                            actions = json.loads(report) if isinstance(report, str) else report
                            if isinstance(actions, list) and len(actions) > 0:
                                fight_log["actions_count"] = len(actions)
                                last_action = actions[-1]
                                if isinstance(last_action, list) and len(last_action) > 0:
                                    fight_log["duration"] = last_action[0]
                        except:
                            pass
                    
                    return fight_log
            except:
                pass
        
        return None
    
    def update_farmer_info(self):
        """Update farmer info using session cookies"""
        url = f"{BASE_URL}/farmer/get"
        response = self.session.get(url)
        
        if response.status_code == 200:
            data = response.json()
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
    
    def run_smart_fights(self, num_fights=None, leek_number=1, strategy="smart"):
        """Run fights with smart opponent selection"""
        if not self.leeks:
            print("\n❌ No leeks found in your account!")
            return
            
        if self.total_fights == 0:
            print("\n❌ No fights available. Try again tomorrow!")
            return
        
        # Get the selected leek
        leek_list = list(self.leeks.values())
        if len(leek_list) < leek_number:
            print(f"\n❌ Leek #{leek_number} not found! You only have {len(leek_list)} leek(s).")
            return
        
        selected_leek = leek_list[leek_number - 1]
        leek_id = selected_leek['id']
        leek_name = selected_leek['name']
        
        # Initialize opponent tracker for this leek
        self.opponent_tracker = OpponentTracker(leek_id)
        
        # Show existing stats
        stats = self.opponent_tracker.get_stats_summary()
        print(f"\n📊 Opponent Tracking Stats for {leek_name}:")
        print(f"   Total fights tracked: {stats['total_fights']}")
        if stats['total_fights'] > 0:
            print(f"   Overall win rate: {stats['win_rate']:.1%}")
            print(f"   Opponents tracked: {stats['opponents_tracked']}")
            print(f"   🟢 Beatable opponents: {stats['beatable_opponents']}")
            print(f"   🔴 Dangerous opponents: {stats['dangerous_opponents']}")
        
        fights_to_run = min(num_fights or self.total_fights, self.total_fights)
        
        print("\n" + "="*60)
        print("STARTING SMART SOLO FIGHTS")
        print(f"Strategy: {strategy.upper()}")
        print("="*60)
        
        start_time = datetime.now()
        fights_completed = 0
        consecutive_failures = 0
        
        print(f"\n🎯 Running {fights_to_run} smart fights with {leek_name}...")
        
        while fights_completed < fights_to_run and consecutive_failures < 5:
            # Get all available opponents
            all_opponents = self.get_leek_opponents(leek_id, verbose=False)
            
            if not all_opponents:
                print(f"   ⚠️ No opponents available")
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    break
                time.sleep(2)
                continue
            
            # Apply smart opponent selection
            preferred_opponents = self.opponent_tracker.get_preferred_opponents(all_opponents, strategy)
            
            # Show opponent selection info
            if fights_completed < 3:
                avoided = len(all_opponents) - len(preferred_opponents)
                if avoided > 0:
                    print(f"   🧠 Smart selection: {len(preferred_opponents)}/{len(all_opponents)} opponents (avoided {avoided})")
            
            if not preferred_opponents:
                print(f"   ⚠️ No suitable opponents found")
                consecutive_failures += 1
                continue
            
            # Choose opponent (weighted towards better matchups)
            if len(preferred_opponents) >= 3:
                # Prefer first 3 (best matchups) with higher probability
                weights = [3, 2, 1] + [1] * (len(preferred_opponents) - 3)
                opponent = random.choices(preferred_opponents, weights=weights[:len(preferred_opponents)])[0]
            else:
                opponent = random.choice(preferred_opponents)
            
            opponent_name = opponent.get('name', 'Unknown')
            opponent_level = opponent.get('level', 0)
            opponent_id = opponent['id']
            
            # Check our history with this opponent
            opp_key = str(opponent_id)
            history = ""
            if opp_key in self.opponent_tracker.data["opponents"]:
                opp_data = self.opponent_tracker.data["opponents"][opp_key]
                w, l, d = opp_data["wins"], opp_data["losses"], opp_data["draws"]
                win_rate = opp_data["win_rate"]
                status = opp_data["status"]
                history = f" [{w}W-{l}L-{d}D, {win_rate:.0%}, {status}]"
            
            # Start the fight
            fight_id = self.start_solo_fight(leek_id, opponent_id)
            
            if fight_id:
                fights_completed += 1
                fight_url = f"https://leekwars.com/fight/{fight_id}"
                timestamp = datetime.now().strftime('%H:%M:%S')
                
                self.fight_ids.append(fight_id)
                
                # Get fight result
                fight_log = self.get_fight_log(fight_id)
                result = "UNKNOWN"
                
                if fight_log:
                    winner = fight_log.get("winner", -1)
                    duration = fight_log.get("duration", "N/A")
                    
                    for leek in fight_log.get("leeks", []):
                        if leek.get("name") == leek_name:
                            if winner == 0:
                                result = "DRAW"
                            elif leek.get("team") == winner:
                                result = "WIN"
                            else:
                                result = "LOSS"
                            break
                    
                    # Record the fight result
                    self.opponent_tracker.record_fight(opponent_id, opponent_name, result)
                
                # Show progress
                result_icon = {"WIN": "✅", "LOSS": "❌", "DRAW": "🤝"}.get(result, "❓")
                if fights_completed <= 5 or fights_completed % 10 == 0:
                    print(f"   {result_icon} Fight #{fights_completed}: {result} vs {opponent_name} (Level {opponent_level}){history}")
                    if fights_completed <= 3:
                        print(f"      🔗 {fight_url}")
                
                self.fights_run.append({
                    'id': fight_id,
                    'url': fight_url,
                    'leek': leek_name,
                    'opponent': opponent_name,
                    'result': result,
                    'time': timestamp,
                    'log': fight_log
                })
                
                consecutive_failures = 0
                time.sleep(1.0)
            else:
                print(f"   ❌ Failed to start fight against {opponent_name}")
                consecutive_failures += 1
            
            # Update farmer info periodically
            if fights_completed > 0 and fights_completed % 20 == 0:
                self.update_farmer_info()
                if self.total_fights == 0:
                    print("   ⚠️ No more fights available!")
                    break
        
        # Final summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "="*60)
        print("SMART FIGHT SESSION COMPLETE")
        print("="*60)
        print(f"✅ Total fights completed: {fights_completed}/{fights_to_run}")
        
        if fights_completed > 0:
            if duration < 60:
                print(f"⏱️ Time taken: {duration:.1f} seconds")
            else:
                print(f"⏱️ Time taken: {duration/60:.1f} minutes")
            print(f"⚡ Average: {duration/fights_completed:.1f} seconds per fight")
        
        # Show updated stats
        final_stats = self.opponent_tracker.get_stats_summary()
        print(f"\n📊 Updated Stats:")
        print(f"   Total fights tracked: {final_stats['total_fights']}")
        if final_stats['total_fights'] > 0:
            print(f"   Overall win rate: {final_stats['win_rate']:.1%}")
            print(f"   Opponents tracked: {final_stats['opponents_tracked']}")
            print(f"   🟢 Beatable opponents: {final_stats['beatable_opponents']}")
            print(f"   🔴 Dangerous opponents: {final_stats['dangerous_opponents']}")
        
        # Show recent fight URLs
        if fights_completed <= 5:
            print("\n🔗 Fight URLs:")
            for fight in self.fights_run[-fights_completed:]:
                result_icon = {"WIN": "✅", "LOSS": "❌", "DRAW": "🤝"}.get(fight['result'], "❓")
                print(f"   {result_icon} {fight['url']}")
        elif fights_completed > 0:
            print(f"\n🔗 Last 3 fights:")
            for fight in self.fights_run[-3:]:
                result_icon = {"WIN": "✅", "LOSS": "❌", "DRAW": "🤝"}.get(fight['result'], "❓")
                print(f"   {result_icon} {fight['url']}")
        
        # Update final farmer stats
        print("\n📊 Updating final stats...")
        self.update_farmer_info()
        if self.farmer:
            print(f"   💰 Habs: {self.farmer.get('habs', 0):,}")
            print(f"   🗡️ Remaining fights: {self.farmer.get('fights', 0)}")
    
    def disconnect(self):
        """Disconnect from LeekWars"""
        if self.token:
            url = f"{BASE_URL}/farmer/disconnect/{self.token}"
            response = self.session.post(url)
            if response.status_code == 401:
                url = f"{BASE_URL}/farmer/disconnect"
                self.session.post(url)
            print("\n👋 Disconnected from LeekWars")

def main():
    parser = argparse.ArgumentParser(description='LeekWars Smart Solo Fighter - Avoids opponents who beat you')
    parser.add_argument('leek_number', type=int, help='Leek number to use (1, 2, or 3)')
    parser.add_argument('num_fights', type=int, help='Number of fights to run')
    parser.add_argument('--strategy', choices=['safe', 'smart', 'aggressive', 'random'], default='smart',
                       help='Opponent selection strategy (default: smart)')
    
    args = parser.parse_args()
    
    if args.leek_number < 1 or args.leek_number > 4:
        print("❌ Error: Leek number must be between 1 and 4")
        return 1
    
    if args.num_fights < 1:
        print("❌ Error: Number of fights must be at least 1")
        return 1
    
    print("="*60)
    print("LEEKWARS SMART SOLO FIGHTER")
    print("="*60)
    print(f"Selected: Leek #{args.leek_number}")
    print(f"Fights to run: {args.num_fights}")
    print(f"Strategy: {args.strategy}")
    print("\nStrategy descriptions:")
    print("  • safe: Only fight beatable/unknown opponents")
    print("  • smart: Prefer beatable > unknown > few risky (default)")  
    print("  • aggressive: Fight all, but prefer beatable first")
    print("  • random: No opponent filtering")
    print()
    
    fighter = LeekWarsSmartFighter()
    
    # Get credentials
    email, password = load_credentials()
    
    if not fighter.login(email, password):
        print("\n❌ Failed to login. Please check your credentials.")
        return 1
        
    try:
        if not fighter.leeks:
            print("\n⚠️ No leeks found in your account!")
            return 1
            
        if fighter.total_fights > 0:
            fights_to_run = min(args.num_fights, fighter.total_fights)
            fighter.run_smart_fights(fights_to_run, leek_number=args.leek_number, strategy=args.strategy)
        else:
            print("\n⚠️ No fights available right now.")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
from config_loader import load_credentials
        traceback.print_exc()
        
    finally:
        fighter.disconnect()
        
    return 0

if __name__ == "__main__":
    exit(main())