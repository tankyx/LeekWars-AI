#!/usr/bin/env python3
"""
LeekWars Auto Team Fighter - All Compositions Version (Cure Account)
Runs all available team fights for all team compositions automatically
Usage: python3 lw_team_fights_all_cure.py [--quick]
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

class LeekWarsTeamFighter:
    def __init__(self):
        """Initialize session and variables"""
        self.session = requests.Session()
        self.farmer = None
        self.token = None
        self.team = None
        self.compositions = []
        self.total_team_fights = 0
        self.fights_run = []
        self.fight_ids = []  # Store fight IDs for later log retrieval

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
                    if "farmer" in data and "token" in data:
                        self.farmer = data["farmer"]
                        self.token = data["token"]

                        # Extract team fights count
                        self.total_team_fights = self.farmer.get("team_fights", 0)

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
                        print(f"   🛡️  Available team fights: {self.total_team_fights}")

                        # Debug: Show cookies
                        cookies = list(self.session.cookies.keys())
                        if cookies:
                            print(f"   🍪 Session cookies: {cookies}")

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

    def get_team_info(self):
        """Get team information including compositions from garden data"""
        if not self.farmer:
            return False

        team_id = self.farmer.get("team")
        if not team_id:
            print("\n❌ You are not in a team!")
            return False

        print(f"\n🏟️ Fetching garden and team information...")

        # Get garden data which includes team compositions
        url = f"{BASE_URL}/garden/get"
        response = self.session.get(url)

        if response.status_code == 200:
            try:
                data = response.json()
                if "garden" in data:
                    garden_data = data["garden"]

                    # Get team compositions from garden data
                    self.compositions = garden_data.get("my_compositions", [])

                    if self.compositions:
                        print(f"   🥬 Found {len(self.compositions)} team compositions:")
                        for comp in self.compositions:
                            comp_name = comp.get("name", "Unknown")
                            comp_fights = comp.get("fights", 0)
                            leek_count = len(comp.get("leeks", []))
                            comp_level = comp.get("level", 0)
                            print(f"     - {comp_name}: {leek_count} leeks, Level {comp_level}, {comp_fights} fights available")
                        return True
                    else:
                        print("   ❌ No team compositions found in garden data!")
                        return False
                else:
                    print(f"   ❌ Unexpected garden data structure")
                    return False
            except json.JSONDecodeError:
                print(f"   ❌ Failed to parse garden data")
                return False
        else:
            print(f"   ❌ Failed to fetch garden data: {response.status_code}")
            return False

    def get_composition_opponents(self, composition_id, verbose=False):
        """Get available opponents for a team composition"""
        url = f"{BASE_URL}/garden/get-composition-opponents/{composition_id}"

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
            return self.get_composition_opponents(composition_id, verbose)  # Retry after wait
        else:
            if verbose:
                print(f"   ❌ HTTP Error: {response.status_code}")

        return []

    def start_team_fight(self, composition_id, target_composition_id):
        """Start a team fight between compositions"""
        url = f"{BASE_URL}/garden/start-team-fight"

        data = {
            "composition_id": str(composition_id),
            "target_id": str(target_composition_id)
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
            return self.start_team_fight(composition_id, target_composition_id)  # Retry
        else:
            print(f"   ❌ HTTP Error starting team fight: {response.status_code}")
        return None

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
                        "actions_count": 0
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

    def download_all_fight_logs(self, composition_id, composition_name, fight_ids):
        """Download all fight logs for a specific composition"""
        if not fight_ids:
            return

        print(f"\n📥 Downloading logs for {len(fight_ids)} fights...")
        print(f"   Composition: {composition_name} (ID: {composition_id})")

        # Create directory for logs using composition ID
        log_dir = f"fight_logs/team_composition_{composition_id}"
        os.makedirs(log_dir, exist_ok=True)
        print(f"   Directory: {log_dir}/")

        successful = 0
        failed = []

        for i, fight_id in enumerate(fight_ids):
            # Rate limiting - 0.3 seconds between requests
            if i > 0:
                time.sleep(0.3)

            # Progress indicator
            if i > 0 and i % 10 == 0:
                print(f"   Progress: {i}/{len(fight_ids)} ({i*100/len(fight_ids):.1f}%)")

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

        print(f"✅ Downloaded logs: {successful}/{len(fight_ids)}")
        if failed:
            print(f"❌ Failed: {len(failed)} fights")

    def update_farmer_info(self):
        """Update farmer info using session cookies"""
        url = f"{BASE_URL}/farmer/get"
        response = self.session.get(url)

        if response.status_code == 200:
            data = response.json()
            if "farmer" in data:
                self.farmer = data["farmer"]
                self.total_team_fights = self.farmer.get("team_fights", 0)
                return True
        elif response.status_code == 429:
            print("   ⚠️ Rate limited - waiting 2 seconds...")
            time.sleep(2)
            return self.update_farmer_info()
        return False

    def run_team_fights(self, quick_mode=False):
        """Run all available team fights for all compositions"""
        if not self.compositions:
            print("\n❌ No team compositions found!")
            return

        if self.total_team_fights == 0:
            print("\n❌ No team fights available. Try again tomorrow!")
            print("   Team fights reset daily at midnight (French time).")
            return

        print("\n" + "="*60)
        print("STARTING AUTOMATIC TEAM FIGHTS")
        if quick_mode:
            print("⚡ QUICK MODE ENABLED - Minimal output")
        print("="*60)

        start_time = datetime.now()

        # Filter compositions that have fights available
        active_compositions = [comp for comp in self.compositions if comp.get("fights", 0) > 0]

        if not active_compositions:
            print("\n❌ No compositions have fights available!")
            return

        print(f"\n🎯 Found {len(active_compositions)} compositions with fights:")
        for comp in active_compositions:
            comp_name = comp.get("name", "Unknown")
            comp_fights = comp.get("fights", 0)
            print(f"   - {comp_name}: {comp_fights} fights")

        total_fights_completed = 0
        composition_results = {}

        # Process each composition
        for comp_idx, composition in enumerate(active_compositions):
            comp_id = composition["id"]
            comp_name = composition.get("name", "Unknown")
            comp_fights = composition.get("fights", 0)

            print(f"\n🥬 [{comp_idx + 1}/{len(active_compositions)}] Processing: {comp_name}")
            print(f"   Available fights: {comp_fights}")

            composition_results[comp_id] = {
                "name": comp_name,
                "fights_attempted": 0,
                "fights_completed": 0,
                "fight_ids": [],
                "results": {"wins": 0, "losses": 0, "draws": 0}
            }

            fights_completed = 0
            consecutive_failures = 0

            while fights_completed < comp_fights and consecutive_failures < 3:
                # Get opponents for this composition
                opponents = self.get_composition_opponents(comp_id, verbose=False)

                if not opponents:
                    if consecutive_failures == 0 and not quick_mode:
                        print(f"   ⚠️ No opponents available for {comp_name}")
                    consecutive_failures += 1
                    break

                # Reset failure counter on successful opponent fetch
                consecutive_failures = 0

                # Choose random opponent
                opponent = random.choice(opponents)
                opponent_name = opponent.get("name", "Unknown")
                opponent_team_name = opponent.get("team_name", "Unknown")

                # Start the team fight
                fight_id = self.start_team_fight(comp_id, opponent["id"])

                if fight_id:
                    fights_completed += 1
                    total_fights_completed += 1
                    composition_results[comp_id]["fights_completed"] += 1
                    composition_results[comp_id]["fight_ids"].append(fight_id)

                    fight_url = f"https://leekwars.com/fight/{fight_id}"
                    timestamp = datetime.now().strftime('%H:%M:%S')

                    # Store fight ID for later log retrieval
                    self.fight_ids.append(fight_id)

                    if not quick_mode or fights_completed <= 3:
                        print(f"   ✅ Fight #{fights_completed}/{comp_fights} vs {opponent_team_name} - {opponent_name}")
                        if fights_completed <= 3:
                            print(f"   🔗 {fight_url}")
                    elif quick_mode:
                        print(".", end="", flush=True)

                    # Get fight result if not in quick mode (for first few fights)
                    if not quick_mode and fights_completed <= 5:
                        fight_log = self.get_fight_log(fight_id)
                        if fight_log:
                            winner = fight_log.get("winner", -1)
                            # Determine result (simplified)
                            if winner == 0:
                                composition_results[comp_id]["results"]["draws"] += 1
                            elif winner == 1:  # Assuming team 1 is us
                                composition_results[comp_id]["results"]["wins"] += 1
                            else:
                                composition_results[comp_id]["results"]["losses"] += 1

                    self.fights_run.append({
                        'id': fight_id,
                        'url': fight_url,
                        'composition': comp_name,
                        'opponent': opponent_name,
                        'opponent_team': opponent_team_name,
                        'time': timestamp
                    })

                    # Minimal delay to avoid overwhelming the server
                    if fights_completed < comp_fights:
                        time.sleep(0.5 if quick_mode else 1.0)
                else:
                    if not quick_mode:
                        print(f"   ❌ Failed to start fight against {opponent_team_name} - {opponent_name}")
                    consecutive_failures += 1

                composition_results[comp_id]["fights_attempted"] += 1

                # Update farmer info periodically to check remaining fights
                if fights_completed > 0 and fights_completed % 10 == 0:
                    self.update_farmer_info()
                    if self.total_team_fights == 0:
                        if not quick_mode:
                            print("   ⚠️ No more team fights available!")
                        break

            # Download logs for this composition
            if composition_results[comp_id]["fight_ids"]:
                self.download_all_fight_logs(comp_id, comp_name, composition_results[comp_id]["fight_ids"])

            if quick_mode and fights_completed > 5:
                print()  # New line after progress dots

        # Final summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "="*60)
        print("TEAM FIGHT SESSION COMPLETE")
        print("="*60)
        print(f"✅ Total fights completed: {total_fights_completed}")

        # Show results per composition
        print(f"\n📊 Results by composition:")
        for comp_id, results in composition_results.items():
            if results["fights_completed"] > 0:
                name = results["name"]
                completed = results["fights_completed"]
                attempted = results["fights_attempted"]
                print(f"   🥬 {name}: {completed}/{attempted} fights")

                # Show win/loss if available
                res = results["results"]
                total_results = res["wins"] + res["losses"] + res["draws"]
                if total_results > 0:
                    print(f"      Results: {res['wins']}W / {res['losses']}L / {res['draws']}D")

        if total_fights_completed > 0:
            if duration < 60:
                print(f"\n⏱️ Time taken: {duration:.1f} seconds")
            else:
                print(f"\n⏱️ Time taken: {duration/60:.1f} minutes")
            print(f"⚡ Average: {duration/total_fights_completed:.1f} seconds per fight")

        # Show last few fight URLs if not too many
        if total_fights_completed <= 10:
            print("\n🔗 Fight URLs:")
            for fight in self.fights_run:
                print(f"   {fight['url']} ({fight['composition']} vs {fight['opponent_team']})")

        # Update and show final stats
        print("\n📊 Updating final stats...")
        self.update_farmer_info()
        if self.farmer:
            print(f"   💰 Habs: {self.farmer.get('habs', 0):,}")
            print(f"   🛡️  Remaining team fights: {self.farmer.get('team_fights', 0)}")

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
    parser = argparse.ArgumentParser(description='LeekWars Auto Team Fighter - All Compositions (Cure Account)')
    parser.add_argument('--quick', action='store_true', help='Enable quick mode (minimal output)')

    args = parser.parse_args()

    print("="*60)
    print("LEEKWARS AUTO TEAM FIGHTER - ALL COMPOSITIONS (CURE)")
    print("="*60)
    print("This script will run all available team fights for all compositions")
    if args.quick:
        print("Mode: Quick (minimal output)")
    print()

    # Create fighter instance
    fighter = LeekWarsTeamFighter()

    # Get credentials for Cure account
    email, password = load_credentials(account="cure")

    # Login
    if not fighter.login(email, password):
        print("\n❌ Failed to login. Please check your credentials.")
        return 1

    try:
        # Get team information
        if not fighter.get_team_info():
            print("\n❌ Failed to get team information.")
            return 1

        # Check if we have team fights available
        if fighter.total_team_fights > 0:
            print(f"\n🎮 You have {fighter.total_team_fights} team fights available.")

            # Ask for confirmation unless in quick mode
            if not args.quick:
                confirm = input(f"\nProceed with running all available team fights? (y/N): ").lower()
                if confirm not in ['y', 'yes']:
                    print("Cancelled by user.")
                    return 0

            # Use quick mode from command-line argument
            quick_mode = args.quick

            fighter.run_team_fights(quick_mode=quick_mode)
        else:
            print("\n⚠️ No team fights available right now.")
            print("Team fights reset daily at midnight (French time).")

    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")

    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
from config_loader import load_credentials
        traceback.print_exc()

    finally:
        # Always disconnect properly
        fighter.disconnect()

    return 0

if __name__ == "__main__":
    exit(main())
