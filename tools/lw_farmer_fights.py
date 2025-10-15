#!/usr/bin/env python3
"""
LeekWars Farmer Fight Script
Allows fighting against other farmers in garden mode or challenge mode
Usage: 
  python3 lw_farmer_fights.py garden <num_fights> [--quick]
  python3 lw_farmer_fights.py challenge <farmer_id> <num_fights> [--seed N] [--side L/R] [--quick]

Garden Mode:
- Fights against random farmer opponents from the garden
- Uses /garden/get-farmer-opponents to find available opponents
- Uses /garden/start-farmer-fight to initiate fights

Challenge Mode:
- Fights against a specific farmer ID
- Uses /garden/get-farmer-challenge/{farmer_id} to get challenge details
- Uses /garden/start-farmer-challenge with optional seed and side parameters
- Supports reproducible fights with seed parameter
- Supports side selection (L for left, R for right)
"""

import requests
import json
import random
import time
from datetime import datetime
# from getpass import getpass  # Not needed with hard-coded credentials
import os
import sys
import argparse
from config_loader import load_credentials

BASE_URL = "https://leekwars.com/api"

class LeekWarsFarmerFighter:
    def __init__(self):
        """Initialize session and variables"""
        self.session = requests.Session()
        self.farmer = None
        self.token = None
        self.total_fights = 0
        self.fights_run = []
        self.fight_ids = []  # Store fight IDs for later log retrieval
        
    def login(self, email, password):
        """Login to LeekWars and get session cookies"""
        print("🔐 Logging in...")
        
        try:
            # Login to get session cookies
            login_url = f"{BASE_URL}/farmer/login-token"
            login_data = {
                "login": email,
                "password": password
            }
            
            response = self.session.post(login_url, data=login_data)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    if "farmer" in data:
                        self.farmer = data["farmer"]
                        self.token = data.get("token")
                        self.total_fights = self.farmer.get("fights", 0)
                        
                        print("✅ Connected successfully!")
                        print(f"   👤 Farmer: {self.farmer.get('name')} (ID: {self.farmer.get('id')})")
                        print(f"   💰 Habs: {self.farmer.get('habs', 0):,}")
                        ratio = float(self.farmer.get('ratio', 0.0)) if isinstance(self.farmer.get('ratio'), (str, int, float)) else 0.0
                        print(f"   📊 Stats: {self.farmer.get('victories', 0)}V / {self.farmer.get('draws', 0)}D / {self.farmer.get('defeats', 0)}L (Ratio: {ratio:.2f})")
                        print(f"   🗡️ Available fights: {self.total_fights}")
                        
                        # Show session cookies
                        cookies = list(self.session.cookies.keys())
                        print(f"   🍪 Session cookies: {cookies}")
                        
                        return True
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
            
    def get_farmer_opponents(self, verbose=False):
        """Get available farmer opponents from the garden"""
        url = f"{BASE_URL}/garden/get-farmer-opponents"
        
        response = self.session.get(url)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if "opponents" in data:
                    opponents = data.get("opponents", [])
                    if opponents and verbose:
                        print(f"   ✅ Found {len(opponents)} farmer opponents")
                    return opponents
                elif data.get("success") == False:
                    error = data.get("error", "Unknown error")
                    if verbose:
                        print(f"   ❌ API error: {error}")
                else:
                    if verbose:
                        print(f"   ⚠️ No farmer opponents available")
            except json.JSONDecodeError:
                if verbose:
                    print(f"   ❌ Invalid JSON response")
        elif response.status_code == 429:
            if verbose:
                print(f"   ⚠️ Rate limited - waiting 2 seconds...")
            time.sleep(2)
            return self.get_farmer_opponents(verbose)  # Retry after wait
        else:
            if verbose:
                print(f"   ❌ HTTP Error: {response.status_code}")
        
        return []
    
    def get_farmer_challenge(self, farmer_id, verbose=False):
        """Get challenge details for a specific farmer"""
        url = f"{BASE_URL}/garden/get-farmer-challenge/{farmer_id}"
        
        response = self.session.get(url)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if "farmer" in data and "challenges" in data:
                    if verbose:
                        farmer = data["farmer"]
                        challenges = data["challenges"]
                        print(f"   ✅ Challenge available for farmer {farmer.get('name')} (ID: {farmer.get('id')})")
                        # Handle challenges that might be int or list
                        if isinstance(challenges, list):
                            print(f"   📊 Challenges: {len(challenges)} available")
                        else:
                            print(f"   📊 Challenges: {challenges} available")
                    return data
                else:
                    if verbose:
                        print(f"   ❌ Challenge not available")
                        print(f"   Response: {data}")
            except json.JSONDecodeError:
                if verbose:
                    print(f"   ❌ Invalid JSON response")
        else:
            if verbose:
                print(f"   ❌ HTTP Error: {response.status_code}")
        
        return None
    
    def start_farmer_fight(self, target_farmer, test_number=None, verbose=True):
        """Start a garden fight against a farmer opponent"""
        if verbose:
            if test_number:
                print(f"\n🎮 Fight {test_number}:")
                print("-" * 40)
            print(f"   🎯 Target: {target_farmer.get('name')} (Level {target_farmer.get('level', '?')})")
            print(f"      ID: {target_farmer.get('id')}")
            print(f"      Stats: {target_farmer.get('victories', 0)}V / {target_farmer.get('draws', 0)}D / {target_farmer.get('defeats', 0)}L")
            ratio = float(target_farmer.get('ratio', 0.0)) if isinstance(target_farmer.get('ratio'), (str, int, float)) else 0.0
            print(f"      Ratio: {ratio:.2f}")
        
        # Start the fight
        url = f"{BASE_URL}/garden/start-farmer-fight"
        fight_data = {
            "target_id": target_farmer.get("id")
        }
        
        response = self.session.post(url, data=fight_data)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if "fight" in data:
                    fight_id = data["fight"]
                    self.fight_ids.append(fight_id)
                    
                    fight_result = {
                        'test_number': test_number,
                        'fight_id': fight_id,
                        'timestamp': datetime.now().isoformat(),
                        'target_farmer': {
                            'id': target_farmer.get('id'),
                            'name': target_farmer.get('name'),
                            'level': target_farmer.get('level'),
                            'ratio': target_farmer.get('ratio', 0.0)
                        },
                        'url': f"https://leekwars.com/fight/{fight_id}"
                    }
                    
                    if verbose:
                        print(f"   ✅ Fight started! ID: {fight_id}")
                        print(f"   🔗 URL: https://leekwars.com/fight/{fight_id}")
                    
                    return fight_result
                    
                else:
                    error_msg = data.get('error', 'Failed to start fight')
                    if verbose:
                        print(f"   ❌ {error_msg}")
                    return {
                        'test_number': test_number,
                        'timestamp': datetime.now().isoformat(),
                        'error': error_msg
                    }
            except json.JSONDecodeError:
                if verbose:
                    print(f"   ❌ Invalid JSON response")
                return {
                    'test_number': test_number,
                    'timestamp': datetime.now().isoformat(),
                    'error': 'Invalid JSON response'
                }
        else:
            error_msg = f"HTTP Error {response.status_code}"
            if verbose:
                print(f"   ❌ {error_msg}")
            return {
                'test_number': test_number,
                'timestamp': datetime.now().isoformat(),
                'error': error_msg
            }
    
    def start_farmer_challenge(self, challenge_data, test_number=None, seed=None, side=None, verbose=True):
        """Start a challenge fight against a specific farmer"""
        farmer = challenge_data["farmer"]
        
        if verbose:
            if test_number:
                print(f"\n🎮 Challenge {test_number}:")
                print("-" * 40)
            print(f"   🎯 Target: {farmer.get('name')} (Level {farmer.get('level', '?')})")
            print(f"      ID: {farmer.get('id')}")
            print(f"      Stats: {farmer.get('victories', 0)}V / {farmer.get('draws', 0)}D / {farmer.get('defeats', 0)}L")
            ratio = float(farmer.get('ratio', 0.0)) if isinstance(farmer.get('ratio'), (str, int, float)) else 0.0
            print(f"      Ratio: {ratio:.2f}")
            if seed is not None:
                print(f"      Seed: {seed}")
            if side is not None:
                print(f"      Side: {'Left' if side == 0 else 'Right'}")
        
        # Start the challenge fight
        url = f"{BASE_URL}/garden/start-farmer-challenge"
        fight_data = {
            "target_id": farmer.get("id"),
            "seed": seed or 0,
            "side": side or 0
        }
        
        response = self.session.post(url, data=fight_data)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if "fight" in data:
                    fight_id = data["fight"]
                    self.fight_ids.append(fight_id)
                    
                    fight_result = {
                        'test_number': test_number,
                        'fight_id': fight_id,
                        'timestamp': datetime.now().isoformat(),
                        'target_farmer': {
                            'id': farmer.get('id'),
                            'name': farmer.get('name'),
                            'level': farmer.get('level'),
                            'ratio': farmer.get('ratio', 0.0)
                        },
                        'seed': seed,
                        'side': side,
                        'url': f"https://leekwars.com/fight/{fight_id}"
                    }
                    
                    if verbose:
                        print(f"   ✅ Challenge started! ID: {fight_id}")
                        print(f"   🔗 URL: https://leekwars.com/fight/{fight_id}")
                    
                    return fight_result
                    
                else:
                    error_msg = data.get('error', 'Failed to start challenge')
                    if verbose:
                        print(f"   ❌ {error_msg}")
                    return {
                        'test_number': test_number,
                        'timestamp': datetime.now().isoformat(),
                        'error': error_msg
                    }
            except json.JSONDecodeError:
                if verbose:
                    print(f"   ❌ Invalid JSON response")
                return {
                    'test_number': test_number,
                    'timestamp': datetime.now().isoformat(),
                    'error': 'Invalid JSON response'
                }
        else:
            error_msg = f"HTTP Error {response.status_code}"
            if verbose:
                print(f"   ❌ {error_msg}")
            return {
                'test_number': test_number,
                'timestamp': datetime.now().isoformat(),
                'error': error_msg
            }
    
    def download_fight_logs(self, verbose=True):
        """Download logs for all fights"""
        if not self.fight_ids:
            if verbose:
                print("No fights to download logs for.")
            return
        
        if verbose:
            print(f"\n📥 Downloading logs for {len(self.fight_ids)} farmer fights...")
            print(f"   Farmer: {self.farmer.get('name')} (ID: {self.farmer.get('id')})")
        
        success_count = 0
        failed_count = 0
        
        for fight_id in self.fight_ids:
            try:
                # Download fight data
                fight_url = f"{BASE_URL}/fight/get/{fight_id}"
                response = self.session.get(fight_url)
                
                if response.status_code == 200:
                    fight_data = response.json()
                    
                    # Create logs directory
                    os.makedirs("fight_logs/farmer", exist_ok=True)
                    
                    # Save fight data
                    with open(f"fight_logs/farmer/{fight_id}_data.json", 'w') as f:
                        json.dump(fight_data, f, indent=2)
                    
                    success_count += 1
                    
                else:
                    failed_count += 1
                    if verbose:
                        print(f"   ❌ Failed to download fight {fight_id}: HTTP {response.status_code}")
                        
            except Exception as e:
                failed_count += 1
                if verbose:
                    print(f"   ❌ Failed to download fight {fight_id}: {e}")
        
        if verbose:
            print(f"✅ Downloaded logs: {success_count}/{len(self.fight_ids)}")
            if failed_count > 0:
                print(f"❌ Failed: {failed_count} fights")
    
    def update_farmer_info(self):
        """Update farmer information to get current stats"""
        url = f"{BASE_URL}/farmer/get/{self.farmer['id']}"
        response = self.session.get(url)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if "farmer" in data:
                    # Update key stats
                    self.farmer["fights"] = data["farmer"].get("fights", self.farmer.get("fights", 0))
                    self.farmer["victories"] = data["farmer"].get("victories", self.farmer.get("victories", 0))
                    self.farmer["defeats"] = data["farmer"].get("defeats", self.farmer.get("defeats", 0))
                    self.farmer["draws"] = data["farmer"].get("draws", self.farmer.get("draws", 0))
                    self.farmer["ratio"] = data["farmer"].get("ratio", self.farmer.get("ratio", 0.0))
                    
            except (json.JSONDecodeError, KeyError):
                pass  # Keep old stats if update fails
    
    def run_garden_fights(self, num_fights, quick_mode=False):
        """Run farmer fights in garden mode"""
        print(f"\n{'='*60}")
        print("STARTING FARMER GARDEN FIGHTS")
        if quick_mode:
            print("⚡ QUICK MODE ENABLED - Minimal output")
        print(f"{'='*60}")
        
        # Get available farmer opponents
        opponents = self.get_farmer_opponents(verbose=not quick_mode)
        
        if not opponents:
            print("❌ No farmer opponents available in the garden!")
            return False
        
        if not quick_mode:
            print(f"\n📋 Found {len(opponents)} farmer opponents available")
            print(f"🎯 Target: Random farmers from garden")
            print(f"🎮 Running {num_fights} farmer fights...")
        
        start_time = time.time()
        
        # Run the fights
        for i in range(1, num_fights + 1):
            if quick_mode:
                print(".", end="", flush=True)
            
            # Select random opponent
            target_farmer = random.choice(opponents)
            
            # Start fight
            result = self.start_farmer_fight(target_farmer, i, verbose=not quick_mode)
            self.fights_run.append(result)
            
            # Delay between fights (longer delay to avoid rate limiting)
            if i < num_fights:
                time.sleep(1.0)  # Increased from 0.5 to 1.0 second
            
            # Update farmer info periodically
            if i % 5 == 0:
                self.update_farmer_info()
        
        if quick_mode:
            print()  # New line after dots
        
        end_time = time.time()
        time_taken = end_time - start_time
        
        print(f"\n\n{'='*60}")
        print("FARMER GARDEN FIGHTS COMPLETE")
        print(f"{'='*60}")
        # Calculate success/failure statistics
        successful_fights = [f for f in self.fights_run if 'fight_id' in f]
        failed_fights = [f for f in self.fights_run if 'error' in f]
        
        print(f"✅ Total successful fights: {len(successful_fights)}/{num_fights}")
        if failed_fights:
            print(f"❌ Failed fights: {len(failed_fights)}")
        print(f"⏱️ Time taken: {time_taken:.1f} seconds")
        if len(successful_fights) > 0:
            print(f"⚡ Average: {time_taken/len(successful_fights):.1f} seconds per successful fight")
        
        # Show fight URLs
        if successful_fights:
            print(f"\n🔗 Fight URLs:")
            for fight in successful_fights[:10]:  # Show first 10
                print(f"   https://leekwars.com/fight/{fight['fight_id']}")
            if len(successful_fights) > 10:
                print(f"   ... and {len(successful_fights) - 10} more fights")
        
        # Show error summary if there were failures
        if failed_fights and not quick_mode:
            print(f"\n❌ Error Summary:")
            error_counts = {}
            for fight in failed_fights:
                error = fight.get('error', 'Unknown error')
                error_counts[error] = error_counts.get(error, 0) + 1
            for error, count in error_counts.items():
                print(f"   {error}: {count} times")
        
        return True
    
    def run_challenge_fights(self, farmer_id, num_fights, seed=None, side=None, quick_mode=False):
        """Run farmer fights in challenge mode"""
        print(f"\n{'='*60}")
        print("STARTING FARMER CHALLENGE FIGHTS")
        if quick_mode:
            print("⚡ QUICK MODE ENABLED - Minimal output")
        print(f"{'='*60}")
        
        # Get challenge details
        challenge_data = self.get_farmer_challenge(farmer_id, verbose=not quick_mode)
        
        if not challenge_data:
            print(f"❌ No challenge available for farmer ID {farmer_id}!")
            return False
        
        farmer = challenge_data["farmer"]
        
        if not quick_mode:
            print(f"\n📋 Challenge target: {farmer.get('name')} (Level {farmer.get('level', '?')})")
            print(f"   ID: {farmer.get('id')}")
            print(f"   Stats: {farmer.get('victories', 0)}V / {farmer.get('draws', 0)}D / {farmer.get('defeats', 0)}L")
            ratio = float(farmer.get('ratio', 0.0)) if isinstance(farmer.get('ratio'), (str, int, float)) else 0.0
            print(f"   Ratio: {ratio:.2f}")
            if seed is not None:
                print(f"   Seed: {seed}")
            if side is not None:
                print(f"   Side: {'Left' if side == 0 else 'Right'}")
            print(f"🎮 Running {num_fights} challenge fights...")
        
        start_time = time.time()
        
        # Run the fights
        for i in range(1, num_fights + 1):
            if quick_mode:
                print(".", end="", flush=True)
            
            # Start challenge fight
            result = self.start_farmer_challenge(challenge_data, i, seed, side, verbose=not quick_mode)
            self.fights_run.append(result)
            
            # Delay between fights (longer delay to avoid rate limiting)
            if i < num_fights:
                time.sleep(1.0)  # Increased from 0.5 to 1.0 second
            
            # Update farmer info periodically
            if i % 5 == 0:
                self.update_farmer_info()
        
        if quick_mode:
            print()  # New line after dots
        
        end_time = time.time()
        time_taken = end_time - start_time
        
        print(f"\n\n{'='*60}")
        print("FARMER CHALLENGE FIGHTS COMPLETE")
        print(f"{'='*60}")
        # Calculate success/failure statistics
        successful_fights = [f for f in self.fights_run if 'fight_id' in f]
        failed_fights = [f for f in self.fights_run if 'error' in f]
        
        print(f"✅ Total successful challenge fights: {len(successful_fights)}/{num_fights}")
        if failed_fights:
            print(f"❌ Failed fights: {len(failed_fights)}")
        print(f"🎯 Target: {farmer.get('name')} (ID: {farmer.get('id')})")
        print(f"⏱️ Time taken: {time_taken:.1f} seconds")
        if len(successful_fights) > 0:
            print(f"⚡ Average: {time_taken/len(successful_fights):.1f} seconds per successful fight")
        
        # Show fight URLs
        if successful_fights:
            print(f"\n🔗 Fight URLs:")
            for fight in successful_fights[:10]:  # Show first 10
                print(f"   https://leekwars.com/fight/{fight['fight_id']}")
            if len(successful_fights) > 10:
                print(f"   ... and {len(successful_fights) - 10} more fights")
        
        # Show error summary if there were failures
        if failed_fights and not quick_mode:
            print(f"\n❌ Error Summary:")
            error_counts = {}
            for fight in failed_fights:
                error = fight.get('error', 'Unknown error')
                error_counts[error] = error_counts.get(error, 0) + 1
            for error, count in error_counts.items():
                print(f"   {error}: {count} times")
        
        return True

def main():
    print("=" * 60)
    print("LEEKWARS FARMER FIGHT SCRIPT")
    print("=" * 60)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="LeekWars Farmer Fight Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fight 10 random farmers from garden
  python3 lw_farmer_fights.py garden 10
  
  # Fight farmer ID 12345 five times
  python3 lw_farmer_fights.py challenge 12345 5
  
  # Challenge with specific seed and side
  python3 lw_farmer_fights.py challenge 12345 3 --seed 42 --side R
  
  # Quick mode for minimal output
  python3 lw_farmer_fights.py garden 20 --quick
        """
    )
    
    subparsers = parser.add_subparsers(dest='mode', help='Fight mode')
    
    # Garden mode
    garden_parser = subparsers.add_parser('garden', help='Fight random farmers from garden')
    garden_parser.add_argument('num_fights', type=int, help='Number of fights to run')
    garden_parser.add_argument('--quick', action='store_true', help='Quick mode (minimal output)')
    
    # Challenge mode
    challenge_parser = subparsers.add_parser('challenge', help='Fight specific farmer')
    challenge_parser.add_argument('farmer_id', type=int, help='Target farmer ID')
    challenge_parser.add_argument('num_fights', type=int, help='Number of fights to run')
    challenge_parser.add_argument('--seed', type=int, help='Seed for reproducible fights')
    challenge_parser.add_argument('--side', choices=['L', 'R'], help='Side (L=Left, R=Right)')
    challenge_parser.add_argument('--quick', action='store_true', help='Quick mode (minimal output)')
    
    args = parser.parse_args()
    
    if not args.mode:
        parser.print_help()
        return 1
    
    # Convert side to numeric
    side = None
    if hasattr(args, 'side') and args.side:
        side = 0 if args.side == 'L' else 1
    
    print(f"Mode: {'Garden' if args.mode == 'garden' else 'Challenge'}")
    if args.mode == 'challenge':
        print(f"Target Farmer ID: {args.farmer_id}")
    print(f"Fights to run: {args.num_fights}")
    if hasattr(args, 'seed') and args.seed:
        print(f"Seed: {args.seed}")
    if side is not None:
        print(f"Side: {'Left' if side == 0 else 'Right'}")
    if args.quick:
        print("Mode: Quick (minimal output)")
    print()
    
    # Initialize fighter
    fighter = LeekWarsFarmerFighter()
    
    # Hard-coded credentials for testing
    email, password = load_credentials()
    
    # Login
    if not fighter.login(email, password):
        print("Failed to login. Exiting.")
        return 1
    
    # Check if we have enough fights
    if fighter.total_fights < args.num_fights:
        print(f"\n⚠️ Warning: You have {fighter.total_fights} fights available, but requested {args.num_fights}.")
        if input("Continue anyway? (y/N): ").lower() != 'y':
            return 1
    
    print(f"\n🎮 You have {fighter.total_fights} fights available.")
    
    # Run fights based on mode
    success = False
    if args.mode == 'garden':
        success = fighter.run_garden_fights(args.num_fights, args.quick)
    elif args.mode == 'challenge':
        seed = args.seed if hasattr(args, 'seed') else None
        success = fighter.run_challenge_fights(args.farmer_id, args.num_fights, seed, side, args.quick)
    
    if success:
        # Download fight logs
        fighter.download_fight_logs(verbose=not args.quick)
        
        # Update final stats
        if not args.quick:
            print(f"\n📊 Updating final stats...")
            fighter.update_farmer_info()
            print(f"   💰 Habs: {fighter.farmer.get('habs', 0):,}")
            print(f"   🗡️ Remaining fights: {fighter.farmer.get('fights', 0)}")
    
    print("\n👋 Disconnected from LeekWars")
    return 0

if __name__ == "__main__":
    exit(main())