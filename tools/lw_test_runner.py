#!/usr/bin/env python3
"""
LeekWars Test Runner Script - Cookie Session Based
Runs 10 tests against Domingo and saves results to file
"""

import json
import time
import getpass
from datetime import datetime
import requests
from config_loader import load_credentials

BASE_URL = "https://leekwars.com/api"

class LeekWarsTestRunner:
    def __init__(self):
        # Use a session to maintain cookies
        self.session = requests.Session()
        self.farmer_id = None
        self.farmer_name = None
        self.leeks = {}
        
    def login(self, email, password):
        """Login and maintain session cookies"""
        print("🔐 Logging in...")
        
        login_url = f"{BASE_URL}/farmer/login-token"
        login_data = {
            "login": email,
            "password": password
        }
        
        # Login - this sets cookies in the session
        response = self.session.post(login_url, data=login_data)
        
        if response.status_code == 200:
            data = response.json()
            
            if "farmer" in data:
                farmer = data["farmer"]
                self.farmer_id = farmer.get("id")
                self.farmer_name = farmer.get("login")
                
                # Store leeks
                if "leeks" in farmer:
                    self.leeks = farmer["leeks"]
                    print(f"✅ Logged in as {self.farmer_name}")
                    print(f"   Found {len(self.leeks)} leek(s)")
                    
                    # Show available leeks
                    for leek_id, leek_data in self.leeks.items():
                        print(f"   - {leek_data['name']} (Level {leek_data['level']})")
                    
                    return True
                    
        print("❌ Login failed")
        return False
    
    def get_garden_enemies(self):
        """Get available enemies from the garden"""
        url = f"{BASE_URL}/garden/get"
        response = self.session.get(url)
        
        if response.status_code == 200:
            data = response.json()
            return data
        return None
    
    def get_solo_opponents(self, leek_id):
        """Get solo opponents for a specific leek"""
        url = f"{BASE_URL}/garden/get-leek-opponents/{leek_id}"
        response = self.session.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("opponents"):
                return data["opponents"]
        return None
    
    def start_solo_fight(self, leek_id, target_id):
        """Start a solo fight"""
        url = f"{BASE_URL}/garden/start-solo-fight"
        data = {
            "leek_id": leek_id,
            "target_id": target_id
        }
        
        response = self.session.post(url, data=data)
        
        if response.status_code == 200:
            result = response.json()
            return result
        return None
    
    def get_fight_result(self, fight_id):
        """Get the result of a fight"""
        url = f"{BASE_URL}/fight/get/{fight_id}"
        response = self.session.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if "fight" in data:
                return data["fight"]
        return None
    
    def find_domingo(self):
        """Try to find Domingo's ID"""
        print("\n🔍 Looking for Domingo...")
        
        # First, try to get test enemies/bots
        # Domingo might be a special test bot
        
        # Method 1: Check if there's a specific test endpoint
        test_url = f"{BASE_URL}/garden/get-solo-challenge/1"
        response = self.session.get(test_url)
        if response.status_code == 200:
            data = response.json()
            if "enemies" in data:
                for enemy in data["enemies"]:
                    if "Domingo" in str(enemy.get("name", "")):
                        print(f"   Found Domingo in challenges: ID {enemy.get('id')}")
                        return enemy.get("id")
        
        # Method 2: Search in regular opponents
        if self.leeks:
            first_leek_id = list(self.leeks.keys())[0]
            opponents = self.get_solo_opponents(first_leek_id)
            
            if opponents:
                for opponent in opponents:
                    if "Domingo" in str(opponent.get("name", "")):
                        print(f"   Found Domingo in opponents: ID {opponent.get('id')}")
                        return opponent.get("id")
        
        # Method 3: Try known bot IDs (Domingo might have a fixed ID)
        # Common test bot IDs in LeekWars
        known_bot_ids = [1, 2, 3, 4, 5, 11, 12, 13, 14, 15]  # Common bot IDs
        
        for bot_id in known_bot_ids:
            url = f"{BASE_URL}/leek/get/{bot_id}"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                if "leek" in data:
                    leek = data["leek"]
                    if "Domingo" in str(leek.get("name", "")):
                        print(f"   Found Domingo: ID {bot_id}")
                        return bot_id
        
        print("   ⚠️ Could not find Domingo automatically")
        return None
    
    def run_test_fight(self, leek_id, enemy_id, test_number):
        """Run a single test fight"""
        print(f"\n🎮 Test {test_number}/10:")
        print("-" * 40)
        
        try:
            # Start the fight
            result = self.start_solo_fight(leek_id, enemy_id)
            
            if result and "fight" in result:
                fight_id = result["fight"]
                print(f"   ✓ Fight started! ID: {fight_id}")
                
                # Wait for fight to complete
                print("   ⏳ Waiting for fight to complete...")
                time.sleep(3)
                
                # Get fight details
                fight_data = self.get_fight_result(fight_id)
                
                if fight_data:
                    # Parse results
                    winner = fight_data.get("winner")
                    leeks1 = fight_data.get("leeks1", [])
                    leeks2 = fight_data.get("leeks2", [])
                    
                    # Determine which team we are
                    our_team = None
                    our_leek_name = self.leeks[str(leek_id)]["name"]
                    
                    for leek in leeks1:
                        if leek.get("name") == our_leek_name:
                            our_team = 1
                            break
                    
                    if not our_team:
                        for leek in leeks2:
                            if leek.get("name") == our_leek_name:
                                our_team = 2
                                break
                    
                    won = (winner == our_team)
                    
                    # Get more fight stats
                    duration = fight_data.get("duration", 0)
                    
                    print(f"   Result: {'🏆 Victory!' if won else '💀 Defeat'}")
                    print(f"   Duration: {duration} turns")
                    print(f"   URL: https://leekwars.com/fight/{fight_id}")
                    
                    return {
                        'test_number': test_number,
                        'fight_id': fight_id,
                        'timestamp': datetime.now().isoformat(),
                        'our_leek': our_leek_name,
                        'won': won,
                        'winner': 'We won!' if won else 'Enemy won',
                        'duration': duration,
                        'url': f"https://leekwars.com/fight/{fight_id}",
                        'fight_data': fight_data
                    }
                else:
                    print("   ❌ Could not get fight details")
                    return {
                        'test_number': test_number,
                        'fight_id': fight_id,
                        'timestamp': datetime.now().isoformat(),
                        'error': 'Could not retrieve fight details'
                    }
            else:
                error_msg = result.get('error', 'Failed to start fight') if result else 'No response'
                print(f"   ❌ {error_msg}")
                return {
                    'test_number': test_number,
                    'timestamp': datetime.now().isoformat(),
                    'error': error_msg
                }
                
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")
            return {
                'test_number': test_number,
                'timestamp': datetime.now().isoformat(),
                'error': f'Exception: {str(e)}'
            }

def main():
    print("=" * 50)
    print("🎮 LEEKWARS TEST RUNNER - DOMINGO BATTLES")
    print("=" * 50)
    
    # Initialize runner
    runner = LeekWarsTestRunner()
    
    # Get credentials
    email = input("Email [tanguy.pedrazzoli@gmail.com]: ").strip() or "tanguy.pedrazzoli@gmail.com"
    password = getpass.getpass("Password: ")
    
    # Login
    if not runner.login(email, password):
        print("Failed to login. Exiting.")
        return 1
    
    # Select leek
    if not runner.leeks:
        print("No leeks found! Exiting.")
        return 1
    
    # Use first leek
    leek_id = list(runner.leeks.keys())[0]
    leek_data = runner.leeks[leek_id]
    print(f"\n📋 Using leek: {leek_data['name']}")
    print(f"   Level: {leek_data['level']}")
    print(f"   Stats: {leek_data.get('strength', 0)} STR, {leek_data.get('tp', 0)} TP, {leek_data.get('mp', 0)} MP")
    
    # Find Domingo
    domingo_id = runner.find_domingo()
    
    if not domingo_id:
        # Ask user for Domingo's ID if we can't find it
        print("\n⚠️ Could not find Domingo automatically.")
        print("You can find Domingo's ID by:")
        print("  1. Going to LeekWars website")
        print("  2. Looking at Domingo's profile or a fight with Domingo")
        print("  3. The ID is in the URL")
        
        domingo_input = input("\nEnter Domingo's ID (or press Enter to try ID 11): ").strip()
        domingo_id = int(domingo_input) if domingo_input else 11
    
    print(f"\n🎯 Target: Domingo (ID: {domingo_id})")
    
    # Confirm before running tests
    input("\nPress Enter to start 10 test battles...")
    
    # Run tests
    print(f"\n{'='*50}")
    print("🚀 STARTING TEST BATTLES")
    print(f"{'='*50}")
    
    test_results = []
    
    for i in range(1, 11):
        result = runner.run_test_fight(leek_id, domingo_id, i)
        test_results.append(result)
        
        # Small delay between tests
        if i < 10:
            time.sleep(2)
    
    # Calculate statistics
    print(f"\n{'='*50}")
    print("📊 SUMMARY")
    print(f"{'='*50}")
    
    victories = sum(1 for r in test_results if r.get('won') == True)
    defeats = sum(1 for r in test_results if r.get('won') == False)
    errors = sum(1 for r in test_results if 'error' in r)
    
    print(f"Total tests: 10")
    print(f"✅ Victories: {victories}")
    print(f"❌ Defeats: {defeats}")
    print(f"⚠️ Errors: {errors}")
    
    if victories + defeats > 0:
        win_rate = (victories / (victories + defeats)) * 100
        print(f"📈 Win rate: {win_rate:.1f}%")
    
    # Calculate average duration
    durations = [r.get('duration', 0) for r in test_results if 'duration' in r]
    if durations:
        avg_duration = sum(durations) / len(durations)
        print(f"⏱️ Average fight duration: {avg_duration:.1f} turns")
    
    # Save results to file
    output_filename = f"leekwars_domingo_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    output_data = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'farmer': runner.farmer_name,
            'leek': leek_data['name'],
            'leek_level': leek_data['level'],
            'opponent': 'Domingo',
            'opponent_id': domingo_id
        },
        'summary': {
            'total_tests': 10,
            'victories': victories,
            'defeats': defeats,
            'errors': errors,
            'win_rate': f"{win_rate:.1f}%" if victories + defeats > 0 else "N/A",
            'average_duration': f"{avg_duration:.1f} turns" if durations else "N/A"
        },
        'detailed_results': test_results,
        'fight_urls': [r.get('url') for r in test_results if 'url' in r]
    }
    
    # Save to file
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Results saved to: {output_filename}")
    print("\n📝 You can now send this file for analysis!")
    print("The file contains all fight data and URLs to review each battle.")
    
    return 0

if __name__ == "__main__":
    exit(main())
