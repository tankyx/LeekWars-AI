#!/usr/bin/env python3
"""
LeekWars Auto Solo Fighter - Cookie-Based Authentication
Automatically runs specified number of solo fights for all leeks
Uses session cookies for authentication (no token in URLs)
Features:
- Choose number of fights to run
- Quick mode for faster execution
- Detailed logging
"""

import requests
import json
import random
import time
from datetime import datetime
from getpass import getpass
import os

BASE_URL = "https://leekwars.com/api"

class LeekWarsAutoFighter:
    def __init__(self):
        """Initialize session and variables"""
        self.session = requests.Session()
        self.farmer = None
        self.token = None
        self.leeks = {}
        self.total_fights = 0
        self.fights_run = []
        
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
            
    def get_leek_opponents(self, leek_id, verbose=False):
        """Get available opponents for a leek using session cookies"""
        # Use cookies only - no token in URL (as shown by debug test #4)
        url = f"{BASE_URL}/garden/get-leek-opponents/{leek_id}"
        
        response = self.session.get(url)
        
        if response.status_code == 200:
            try:
                data = response.json()
                # The API doesn't return a 'success' field for this endpoint
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
            return self.get_leek_opponents(leek_id, verbose)  # Retry after wait
        else:
            if verbose:
                print(f"   ❌ HTTP Error: {response.status_code}")
            
        return []
        
    def start_solo_fight(self, leek_id, opponent_id):
        """Start a solo fight between leek and opponent using session cookies"""
        url = f"{BASE_URL}/garden/start-solo-fight"
        
        # Use session cookies for auth - no token in data
        data = {
            "leek_id": str(leek_id),
            "target_id": str(opponent_id)
        }
        
        response = self.session.post(url, data=data)
        
        if response.status_code == 200:
            result = response.json()
            # The API returns just {"fight": fight_id} on success
            if "fight" in result:
                return result["fight"]
            # Check for error responses
            elif result.get("success") == False:
                error = result.get("error", "Unknown error")
                print(f"   ❌ Failed to start fight: {error}")
            else:
                print(f"   ❌ Unexpected response: {result}")
        elif response.status_code == 429:
            print(f"   ⚠️ Rate limited - waiting 2 seconds...")
            time.sleep(2)
            return self.start_solo_fight(leek_id, opponent_id)  # Retry
        else:
            print(f"   ❌ HTTP Error starting fight: {response.status_code}")
        return None
        
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
        
    def run_solo_fights(self, num_fights=None, quick_mode=False):
        """Run specified number of solo fights for the first leek only"""
        if not self.leeks:
            print("\n❌ No leeks found in your account!")
            print("   Please create at least one leek on the LeekWars website.")
            return
            
        if self.total_fights == 0:
            print("\n❌ No fights available. Try again tomorrow!")
            print("   Fights reset daily at midnight (French time).")
            return
        
        # Use specified number of fights or all available
        if num_fights is None:
            fights_to_run = self.total_fights
        else:
            fights_to_run = min(num_fights, self.total_fights)
            
        print("\n" + "="*60)
        print("STARTING AUTOMATIC SOLO FIGHTS")
        if quick_mode:
            print("⚡ QUICK MODE ENABLED - Minimal output")
        print("="*60)
        
        start_time = datetime.now()
        
        # Create logs directory
        os.makedirs("logs", exist_ok=True)
        log_filename = f"logs/solo_fights_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        log_file = open(log_filename, "w")
        log_file.write(f"LeekWars Auto Solo Fighter - {datetime.now()}\n")
        log_file.write(f"Account: {self.farmer.get('login')}\n")
        log_file.write(f"Initial fights available: {self.total_fights}\n")
        log_file.write(f"Fights to run: {fights_to_run}\n")
        log_file.write("="*60 + "\n\n")
        
        # Convert leeks dict to list for easier handling
        leek_list = list(self.leeks.values())
        
        # Use only the second leek
        if len(leek_list) >= 2:
            leek_list = [leek_list[1]]
            print(f"\n📋 Using only the second leek:")
            print(f"   2. {leek_list[0]['name']} (Level {leek_list[0]['level']})")
        elif len(leek_list) == 1:
            print(f"\n⚠️ Only one leek found. Cannot use second leek!")
            return
        else:
            print(f"\n⚠️ No leeks found!")
            return
        
        fights_completed = 0
        leek_index = 0
        consecutive_failures = 0
        
        print(f"\n🎯 Running {fights_to_run} fights...")
        if quick_mode:
            print("   Progress: ", end="", flush=True)
        else:
            print("   Progress will be shown every 10 fights\n")
        
        while fights_completed < fights_to_run and consecutive_failures < 5:
            # Cycle through leeks
            current_leek = leek_list[leek_index % len(leek_list)]
            leek_id = current_leek['id']
            leek_name = current_leek['name']
            
            # Show progress based on mode
            if quick_mode:
                # In quick mode, just show dots
                if fights_completed > 0 and fights_completed % 10 == 0:
                    print(f"[{fights_completed}]", end="", flush=True)
                else:
                    print(".", end="", flush=True)
            else:
                # Normal mode - show details every 10 fights or for first fight
                if fights_completed == 0 or fights_completed % 10 == 0:
                    print(f"\n🥬 Fighting with: {leek_name} (Fight {fights_completed + 1}/{fights_to_run})")
            
            # Get opponents for this leek
            opponents = self.get_leek_opponents(leek_id, verbose=False)
            
            if not opponents:
                if consecutive_failures == 0 and not quick_mode:
                    print(f"   ⚠️ No opponents available for {leek_name}")
                leek_index += 1
                consecutive_failures += 1
                
                # If we've tried all leeks multiple times and none have opponents, break
                if consecutive_failures >= len(leek_list) * 2:
                    print("\n⚠️ No opponents available for any leek!")
                    break
                continue
                
            # Reset failure counter on successful opponent fetch
            consecutive_failures = 0
            
            # Choose random opponent
            opponent = random.choice(opponents)
            opponent_name = opponent.get('name', 'Unknown')
            opponent_level = opponent.get('level', 0)
            
            # Start the fight
            fight_id = self.start_solo_fight(leek_id, opponent['id'])
            
            if fight_id:
                fights_completed += 1
                fight_url = f"https://leekwars.com/fight/{fight_id}"
                timestamp = datetime.now().strftime('%H:%M:%S')
                
                # Show detailed info based on mode
                if not quick_mode:
                    if fights_completed <= 3:
                        print(f"   ✅ Fight #{fights_completed} vs {opponent_name} (Level {opponent_level})")
                        print(f"   🔗 {fight_url}")
                    elif fights_completed % 10 == 0:
                        print(f"   ✅ Completed {fights_completed}/{fights_to_run} fights")
                
                # Log the fight
                log_file.write(f"Fight #{fights_completed}\n")
                log_file.write(f"Time: {timestamp}\n")
                log_file.write(f"Leek: {leek_name} (Level {current_leek['level']})\n")
                log_file.write(f"Opponent: {opponent_name} (Level {opponent_level})\n")
                log_file.write(f"URL: {fight_url}\n")
                log_file.write("-"*40 + "\n")
                log_file.flush()
                
                self.fights_run.append({
                    'id': fight_id,
                    'url': fight_url,
                    'leek': leek_name,
                    'opponent': opponent_name,
                    'time': timestamp
                })
                
                # Small delay to avoid overwhelming the server
                if fights_completed < fights_to_run:
                    time.sleep(0.3 if quick_mode else 0.5)
            else:
                if not quick_mode:
                    print(f"   ❌ Failed to start fight against {opponent_name}")
                consecutive_failures += 1
                
            # Don't move to next leek - always use the first one
            
            # Update farmer info periodically to check remaining fights
            if fights_completed > 0 and fights_completed % 20 == 0:
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
        print("FIGHT SESSION COMPLETE")
        print("="*60)
        print(f"✅ Total fights completed: {fights_completed}/{fights_to_run}")
        
        if fights_completed > 0:
            if duration < 60:
                print(f"⏱️ Time taken: {duration:.1f} seconds")
            else:
                print(f"⏱️ Time taken: {duration/60:.1f} minutes")
            print(f"⚡ Average: {duration/fights_completed:.1f} seconds per fight")
        
        if self.fights_run:
            print(f"\n📄 Fight log saved to: {log_filename}")
            
            # Show last few fight URLs if not too many
            if fights_completed <= 5:
                print("\n🔗 Fight URLs:")
                for fight in self.fights_run:
                    print(f"   {fight['url']}")
            elif not quick_mode:
                print(f"\n🔗 Last 3 fights:")
                for fight in self.fights_run[-3:]:
                    print(f"   {fight['url']}")
            
            # Write summary to log
            log_file.write("\n" + "="*60 + "\n")
            log_file.write("SUMMARY\n")
            log_file.write(f"Total fights completed: {fights_completed}/{fights_to_run}\n")
            log_file.write(f"End time: {datetime.now()}\n")
        
        log_file.close()
        
        # Update and show final stats
        print("\n📊 Updating final stats...")
        self.update_farmer_info()
        if self.farmer:
            print(f"   💰 Habs: {self.farmer.get('habs', 0):,}")
            print(f"   🗡️ Remaining fights: {self.farmer.get('fights', 0)}")
            
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
    print("="*60)
    print("LEEKWARS AUTO SOLO FIGHTER")
    print("="*60)
    print("This script will automatically run all available solo fights")
    print("for all your leeks using the LeekWars API.\n")
    
    # Create fighter instance
    fighter = LeekWarsAutoFighter()
    
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
            
            # Run only 35 fights with the second leek
            fights_to_run = min(35, fighter.total_fights)
           
            # Ask for quick mode if running many fights
            quick_mode = True
            
            # Calculate estimated time
            estimated_seconds = fights_to_run * 0.5
            if estimated_seconds < 60:
                estimated_time = f"{int(estimated_seconds)} seconds"
            else:
                estimated_minutes = estimated_seconds / 60
                estimated_time = f"{estimated_minutes:.1f} minutes"
            
            fighter.run_solo_fights(fights_to_run, quick_mode=quick_mode)
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
