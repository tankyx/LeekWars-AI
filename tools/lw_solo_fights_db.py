#!/usr/bin/env python3
"""
LeekWars Auto Solo Fighter - Database Edition
Enhanced opponent tracking with SQLite database
Usage: python3 lw_solo_fights_db.py <leek_number> <num_fights> [--strategy <strategy>]
Example: python3 lw_solo_fights_db.py 2 25 --strategy adaptive
"""

import requests
import json
import random
import time
import os
import sys
import argparse
from config_loader import load_credentials
from datetime import datetime
from fight_db import FightDatabase

BASE_URL = "https://leekwars.com/api"

class LeekWarsSmartFighterDB:
    def __init__(self):
        """Initialize session and variables"""
        self.session = requests.Session()
        self.farmer = None
        self.token = None
        self.leeks = {}
        self.total_fights = 0
        self.fights_run = []
        self.fight_ids = []
        self.db = None

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

    def download_fight_data(self, fight_id, max_retries=30):
        """Download full fight data including replay - retries until fight is complete"""
        url = f"{BASE_URL}/fight/get/{fight_id}"

        for attempt in range(max_retries):
            try:
                response = self.session.get(url)

                if response.status_code == 200:
                    data = response.json()

                    # Check if fight is complete
                    winner = data.get("winner", -1)
                    # The API uses leeks1 and leeks2, not leeks array
                    leeks1 = data.get("leeks1", [])
                    leeks2 = data.get("leeks2", [])

                    # Add team information to each leek
                    leeks = []
                    for leek in leeks1:
                        leek_with_team = leek.copy()
                        leek_with_team['team'] = 1
                        leeks.append(leek_with_team)
                    for leek in leeks2:
                        leek_with_team = leek.copy()
                        leek_with_team['team'] = 2
                        leeks.append(leek_with_team)

                    # If winner is -1 or no leeks, fight is still processing
                    if winner == -1 or len(leeks) == 0:
                        if attempt < max_retries - 1:
                            time.sleep(0.5)  # Wait before retry
                            continue
                        else:
                            return None  # Give up after max retries

                    # Parse fight log
                    fight_log = {
                        "fight_id": fight_id,
                        "date": data.get("date"),
                        "winner": winner,
                        "leeks": leeks,
                        "duration": None,
                        "actions_count": 0
                    }

                    # Try to get duration and actions from report
                    report = data.get("report")
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
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue

        return None

    def process_fight_results(self, leek_name):
        """Process all fight results after battles are complete"""
        if not self.fight_ids:
            return

        print(f"   Processing fight results (with retries for completion)...")

        successful = 0
        failed = 0
        failed_fights = []  # Track fights that failed to process

        for i, fight_info in enumerate(self.fight_ids):

            # Progress indicator
            if i > 0 and i % 10 == 0:
                print(f"   Progress: {i}/{len(self.fight_ids)} ({i*100/len(self.fight_ids):.1f}%)")

            fight_id = fight_info['fight_id']
            opponent_id = fight_info['opponent_id']
            opponent_name = fight_info['opponent_name']
            opponent_level = fight_info['opponent_level']
            fight_url = fight_info['fight_url']
            history = fight_info['history']

            # Download fight data
            fight_log = self.download_fight_data(fight_id)

            if fight_log:
                winner = fight_log.get("winner", -1)
                duration = fight_log.get("duration", "N/A")
                actions_count = fight_log.get("actions_count", 0)

                # Determine result
                result = "UNKNOWN"
                for leek in fight_log.get("leeks", []):
                    if leek.get("name") == leek_name:
                        if winner == 0:
                            result = "DRAW"
                        elif leek.get("team") == winner:
                            result = "WIN"
                        else:
                            result = "LOSS"
                        break

                # Record the fight in database
                if result != "UNKNOWN":
                    self.db.record_fight({
                        'fight_id': fight_id,
                        'opponent_id': opponent_id,
                        'opponent_name': opponent_name,
                        'opponent_level': opponent_level,
                        'result': result,
                        'duration': duration,
                        'actions_count': actions_count,
                        'fight_url': fight_url
                    })

                    successful += 1

                    # Store result for summary
                    self.fights_run.append({
                        'id': fight_id,
                        'url': fight_url,
                        'leek': leek_name,
                        'opponent': opponent_name,
                        'result': result,
                        'time': fight_info['timestamp'],
                        'log': fight_log
                    })

                    # Show all fight results
                    result_icon = {"WIN": "✅", "LOSS": "❌", "DRAW": "🤝"}.get(result, "❓")
                    print(f"   {result_icon} Fight #{i+1}: {result} vs {opponent_name} (Level {opponent_level}){history}")
                else:
                    failed += 1
                    failed_fights.append((i, fight_info))
            else:
                failed += 1
                failed_fights.append((i, fight_info))

        print(f"\n✅ Processed results: {successful}/{len(self.fight_ids)} fights recorded")
        if failed > 0:
            print(f"⚠️ Failed to process: {failed} fights")

            # Retry failed fights with longer wait
            if failed_fights:
                print(f"\n🔄 Retrying {len(failed_fights)} failed fights (waiting 10s for processing)...")
                time.sleep(10)

                retry_successful = 0
                for original_idx, fight_info in failed_fights:
                    fight_id = fight_info['fight_id']
                    opponent_id = fight_info['opponent_id']
                    opponent_name = fight_info['opponent_name']
                    opponent_level = fight_info['opponent_level']
                    fight_url = fight_info['fight_url']
                    history = fight_info['history']

                    # Try with more retries
                    fight_log = self.download_fight_data(fight_id, max_retries=60)

                    if fight_log:
                        winner = fight_log.get("winner", -1)
                        duration = fight_log.get("duration", "N/A")
                        actions_count = fight_log.get("actions_count", 0)

                        # Determine result
                        result = "UNKNOWN"
                        for leek in fight_log.get("leeks", []):
                            if leek.get("name") == leek_name:
                                if winner == 0:
                                    result = "DRAW"
                                elif leek.get("team") == winner:
                                    result = "WIN"
                                else:
                                    result = "LOSS"
                                break

                        # Record the fight in database
                        if result != "UNKNOWN":
                            self.db.record_fight({
                                'fight_id': fight_id,
                                'opponent_id': opponent_id,
                                'opponent_name': opponent_name,
                                'opponent_level': opponent_level,
                                'result': result,
                                'duration': duration,
                                'actions_count': actions_count,
                                'fight_url': fight_url
                            })

                            retry_successful += 1

                            # Store result for summary
                            self.fights_run.append({
                                'id': fight_id,
                                'url': fight_url,
                                'leek': leek_name,
                                'opponent': opponent_name,
                                'result': result,
                                'time': fight_info['timestamp'],
                                'log': fight_log
                            })

                            result_icon = {"WIN": "✅", "LOSS": "❌", "DRAW": "🤝"}.get(result, "❓")
                            print(f"   {result_icon} Retry: {result} vs {opponent_name}")

                if retry_successful > 0:
                    print(f"✅ Retry successful: {retry_successful}/{len(failed_fights)} fights recovered")
                    successful += retry_successful
                    failed -= retry_successful

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
        """Run fights with smart opponent selection using database"""
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
        leek_level = selected_leek.get('level', 1)

        # Initialize database for this leek
        print(f"\n💾 Initializing database for {leek_name}...")
        self.db = FightDatabase(leek_id)
        self.db.update_leek_info(leek_name, leek_level)

        # Check for JSON migration
        json_file = f"opponent_tracker_{leek_id}.json"
        if os.path.exists(json_file):
            print(f"📦 Found existing JSON tracker file: {json_file}")
            response = input("   Migrate to database? (y/n): ")
            if response.lower() == 'y':
                from migrate_json_to_db import migrate_json_to_db
                migrate_json_to_db(leek_id, json_file)

        # Show existing stats
        stats = self.db.get_global_stats()
        print(f"\n📊 Fight Statistics for {leek_name}:")
        print(f"   Total fights tracked: {stats['total_fights']}")
        if stats['total_fights'] > 0:
            print(f"   Overall win rate: {stats['win_rate']:.1%}")
            print(f"   Opponents tracked: {stats['opponents_tracked']}")
            print(f"   🟢 Beatable opponents: {stats['beatable_opponents']}")
            print(f"   🔴 Dangerous opponents: {stats['dangerous_opponents']}")

        fights_to_run = min(num_fights or self.total_fights, self.total_fights)

        print("\n" + "="*60)
        print("STARTING SMART SOLO FIGHTS (DATABASE MODE)")
        print(f"Strategy: {strategy.upper()}")
        print("="*60)
        print("\n💾 All fight results automatically saved to database!")
        print("   Database: fight_history_{}.db".format(leek_id))
        print("\nOpponent Status Colors:")
        print("   🟢 Beatable (win rate ≥ 70%)")
        print("   🟡 Even (30-70% win rate)")
        print("   🔴 Dangerous (win rate ≤ 30%)")
        print("   ⚪ Unknown (< 2 fights)")

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

            # Show all available opponents for EVERY API request
            print(f"\n📋 API Request #{fights_completed + 1} - Available opponents: {len(all_opponents)}")
            print("-" * 70)

            # Show ALL opponents with their stats
            for i, opp in enumerate(all_opponents, 1):
                opp_name = opp.get('name', 'Unknown')
                opp_level = opp.get('level', 0)
                opp_id = opp['id']

                # Get history
                stats = self.db.get_opponent_stats(opp_id)
                if stats:
                    status = stats['status']
                    wins = stats['wins']
                    losses = stats['losses']
                    draws = stats['draws']
                    win_rate = stats['win_rate']
                    difficulty = self.db.calculate_opponent_difficulty(opp_id)

                    status_icons = {
                        'beatable': '🟢',
                        'dangerous': '🔴',
                        'even': '🟡',
                        'unknown': '⚪'
                    }
                    icon = status_icons.get(status, '⚪')

                    print(f"{i:>3}. {icon} {opp_name:<25} L{opp_level} → {wins}W-{losses}L-{draws}D ({win_rate:.0%}, diff:{difficulty})")
                else:
                    print(f"{i:>3}. ⚪ {opp_name:<25} L{opp_level} → Never fought")

            print("-" * 70)

            # Apply smart opponent selection using database
            preferred_opponents = self.db.get_preferred_opponents(all_opponents, strategy)

            # Show opponent selection info for EVERY request
            avoided = len(all_opponents) - len(preferred_opponents)
            if avoided > 0:
                print(f"   🧠 {strategy.capitalize()} strategy: Selected {len(preferred_opponents)}/{len(all_opponents)} opponents (avoided {avoided})")

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
            stats_entry = self.db.get_opponent_stats(opponent_id)
            history = ""
            status_icon = "⚪"  # Unknown by default
            if stats_entry:
                w, l, d = stats_entry["wins"], stats_entry["losses"], stats_entry["draws"]
                win_rate = stats_entry["win_rate"]
                status = stats_entry["status"]
                difficulty = self.db.calculate_opponent_difficulty(opponent_id)
                # Status color indicators
                status_icons = {
                    'beatable': '🟢',
                    'dangerous': '🔴',
                    'even': '🟡',
                    'unknown': '⚪'
                }
                status_icon = status_icons.get(status, '⚪')
                history = f" [{status_icon} {w}W-{l}L-{d}D, {win_rate:.0%}, diff:{difficulty}]"

            # Start the fight
            fight_id = self.start_solo_fight(leek_id, opponent_id)

            if fight_id:
                fights_completed += 1
                fight_url = f"https://leekwars.com/fight/{fight_id}"
                timestamp = datetime.now().strftime('%H:%M:%S')

                # Store fight info for later processing
                self.fight_ids.append({
                    'fight_id': fight_id,
                    'opponent_id': opponent_id,
                    'opponent_name': opponent_name,
                    'opponent_level': opponent_level,
                    'fight_url': fight_url,
                    'timestamp': timestamp,
                    'history': history,
                    'start_time': time.time()  # Track when fight was started
                })

                # Show all fights being started
                print(f"   🎲 Fight #{fights_completed}: Started vs {opponent_name} (Level {opponent_level}){history}")
                if fights_completed <= 3:
                    print(f"      🔗 {fight_url}")

                consecutive_failures = 0
                time.sleep(0.3)  # Quick delay between starting fights
            else:
                print(f"   ❌ Failed to start fight against {opponent_name}")
                consecutive_failures += 1

            # Update farmer info periodically
            if fights_completed > 0 and fights_completed % 20 == 0:
                self.update_farmer_info()
                if self.total_fights == 0:
                    print("   ⚠️ No more fights available!")
                    break

        # Process fight results after all fights complete
        print(f"\n📥 Processing {len(self.fight_ids)} fight results...")
        self.process_fight_results(leek_name)

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
        final_stats = self.db.get_global_stats()
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
        """Disconnect from LeekWars and close database"""
        if self.db:
            self.db.close()
        if self.token:
            url = f"{BASE_URL}/farmer/disconnect/{self.token}"
            response = self.session.post(url)
            if response.status_code == 401:
                url = f"{BASE_URL}/farmer/disconnect"
                self.session.post(url)
            print("\n👋 Disconnected from LeekWars")

def main():
    parser = argparse.ArgumentParser(description='LeekWars Smart Solo Fighter (Database Edition)')
    parser.add_argument('leek_number', type=int, help='Leek number to use (1, 2, 3, or 4)')
    parser.add_argument('num_fights', type=int, help='Number of fights to run')
    parser.add_argument('--strategy', choices=['safe', 'smart', 'aggressive', 'random', 'adaptive', 'confident'],
                       default='smart',
                       help='Opponent selection strategy (default: smart)')

    args = parser.parse_args()

    if args.leek_number < 1 or args.leek_number > 4:
        print("❌ Error: Leek number must be between 1 and 4")
        return 1

    if args.num_fights < 1:
        print("❌ Error: Number of fights must be at least 1")
        return 1

    print("="*60)
    print("LEEKWARS SMART SOLO FIGHTER (DATABASE EDITION)")
    print("="*60)
    print(f"Selected: Leek #{args.leek_number}")
    print(f"Fights to run: {args.num_fights}")
    print(f"Strategy: {args.strategy}")
    print("\n💾 Auto-saves: All fight results saved to SQLite database")
    print("📊 Stats viewer: python3 tools/fight_stats_viewer.py <leek_id>")
    print("\nStrategy descriptions:")
    print("  • safe: Only fight beatable/unknown opponents")
    print("  • smart: Prefer beatable > unknown > few risky (default)")
    print("  • aggressive: Fight all, but prefer beatable first")
    print("  • adaptive: Learn from recent trends, adjust dynamically")
    print("  • confident: Only fight opponents with high confidence data")
    print("  • random: No opponent filtering")
    print()

    fighter = LeekWarsSmartFighterDB()

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
        traceback.print_exc()

    finally:
        fighter.disconnect()

    return 0

if __name__ == "__main__":
    exit(main())
