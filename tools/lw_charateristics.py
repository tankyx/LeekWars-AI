#!/usr/bin/env python3
"""
LeekWars Stats Viewer - Display your leek's characteristics
"""

import requests
import json
from getpass import getpass
from datetime import datetime
from config_loader import load_credentials

BASE_URL = "https://leekwars.com/api"

class LeekWarsStats:
    def __init__(self):
        self.session = requests.Session()
        self.farmer_data = None
        self.leeks = {}
        
    def login(self, email, password):
        """Login and get farmer/leek data"""
        print("🔐 Logging in...")
        
        login_url = f"{BASE_URL}/farmer/login-token"
        login_data = {
            "login": email,
            "password": password
        }
        
        response = self.session.post(login_url, data=login_data)
        
        if response.status_code == 200:
            data = response.json()
            
            if "farmer" in data:
                self.farmer_data = data["farmer"]
                farmer_name = self.farmer_data.get("login")
                
                if "leeks" in self.farmer_data:
                    self.leeks = self.farmer_data["leeks"]
                    print(f"✅ Logged in as {farmer_name}")
                    return True
                    
        print("❌ Login failed")
        return False
    
    def display_farmer_stats(self):
        """Display farmer (account) statistics"""
        if not self.farmer_data:
            return
            
        print("\n" + "="*60)
        print("📊 FARMER STATISTICS")
        print("="*60)
        
        print(f"👤 Name: {self.farmer_data.get('login', 'Unknown')}")
        print(f"🆔 ID: {self.farmer_data.get('id', 'Unknown')}")
        print(f"🏆 Talent: {self.farmer_data.get('talent', 0)}")
        print(f"💰 Habs: {self.farmer_data.get('habs', 0)}")
        print(f"💎 Crystals: {self.farmer_data.get('crystals', 0)}")
        print(f"🎖️ Trophies: {self.farmer_data.get('trophies', 0)}")
        print(f"⚔️ Total Fights: {self.farmer_data.get('fights', 0)}")
        print(f"✅ Victories: {self.farmer_data.get('victories', 0)}")
        print(f"❌ Defeats: {self.farmer_data.get('defeats', 0)}")
        print(f"🤝 Draws: {self.farmer_data.get('draws', 0)}")
        
        # Calculate win rate
        total_fights = self.farmer_data.get('fights', 0)
        victories = self.farmer_data.get('victories', 0)
        if total_fights > 0:
            win_rate = (victories / total_fights) * 100
            print(f"📈 Win Rate: {win_rate:.1f}%")
        
        # Team info
        if "team" in self.farmer_data and self.farmer_data["team"]:
            team = self.farmer_data["team"]
            print(f"\n👥 Team: {team.get('name', 'Unknown')} (ID: {team.get('id')})")
    
    def display_leek_stats(self, leek_id, leek_data):
        """Display detailed leek statistics"""
        print("\n" + "="*60)
        print(f"🥬 LEEK: {leek_data.get('name', 'Unknown')}")
        print("="*60)
        
        # Basic info
        print("\n📋 BASIC INFO:")
        print(f"  ID: {leek_id}")
        print(f"  Level: {leek_data.get('level', 0)}")
        print(f"  Talent: {leek_data.get('talent', 0)}")
        print(f"  AI: {leek_data.get('ai', 'None')}")
        print(f"  Skin: {leek_data.get('skin', 1)}")
        print(f"  Hat: {leek_data.get('hat', 'None')}")
        print(f"  Metal: {'Yes' if leek_data.get('metal') else 'No'}")
        print(f"  Face: {leek_data.get('face', 0)}")
        
        # Capital points
        capital = leek_data.get('capital', 0)
        if capital > 0:
            print(f"\n💰 Unspent Capital: {capital} points")
        
        # Combat stats
        print("\n⚔️ COMBAT STATS:")
        print(f"  HP: {leek_data.get('life', 0)} (Total: {leek_data.get('total_life', 0)})")
        print(f"  Strength: {leek_data.get('strength', 0)} (Total: {leek_data.get('total_strength', 0)})")
        print(f"  Wisdom: {leek_data.get('wisdom', 0)} (Total: {leek_data.get('total_wisdom', 0)})")
        print(f"  Agility: {leek_data.get('agility', 0)} (Total: {leek_data.get('total_agility', 0)})")
        print(f"  Resistance: {leek_data.get('resistance', 0)} (Total: {leek_data.get('total_resistance', 0)})")
        print(f"  Science: {leek_data.get('science', 0)} (Total: {leek_data.get('total_science', 0)})")
        print(f"  Magic: {leek_data.get('magic', 0)} (Total: {leek_data.get('total_magic', 0)})")
        print(f"  Frequency: {leek_data.get('frequency', 0)} (Total: {leek_data.get('total_frequency', 0)})")
        
        # Resource stats
        print("\n📊 RESOURCE STATS:")
        print(f"  Turn Points (TP): {leek_data.get('tp', 0)} (Total: {leek_data.get('total_tp', 0)})")
        print(f"  Movement Points (MP): {leek_data.get('mp', 0)} (Total: {leek_data.get('total_mp', 0)})")
        print(f"  Cores: {leek_data.get('cores', 0)} (Total: {leek_data.get('total_cores', 0)})")
        print(f"  RAM: {leek_data.get('ram', 0)} (Total: {leek_data.get('total_ram', 0)})")
        
        # Weapons (if available in data)
        if "weapon" in leek_data and leek_data["weapon"]:
            print(f"\n🔫 Weapon: {leek_data['weapon']}")
        
        # Calculate some useful metrics
        print("\n📈 CALCULATED METRICS:")
        
        # Damage potential with 380 strength
        strength = leek_data.get('strength', 0)
        stalactite_damage = 80 + round(strength * 0.25)
        rockfall_damage = 60 + round(strength * 0.22)
        magnum_damage = 60 + round(strength * 0.20)
        laser_damage = 45 + round(strength * 0.15)
        
        print(f"  Stalactite Damage: ~{stalactite_damage}")
        print(f"  Rockfall Damage: ~{rockfall_damage}")
        print(f"  Magnum Damage: ~{magnum_damage}")
        print(f"  Laser Damage: ~{laser_damage}")
        
        # Max burst damage with 15 TP
        tp = leek_data.get('tp', 0)
        if tp >= 15:
            max_burst = stalactite_damage + rockfall_damage + magnum_damage
            print(f"\n  Max Burst (15 TP): ~{max_burst} damage")
            print(f"  (Stalactite + Rockfall + Magnum)")
        elif tp >= 11:
            max_burst = stalactite_damage + rockfall_damage
            print(f"\n  Max Burst (11 TP): ~{max_burst} damage")
            print(f"  (Stalactite + Rockfall)")
        
        # Critical chance
        agility = leek_data.get('agility', 0)
        frequency = leek_data.get('frequency', 0)
        base_crit = agility / 10
        total_crit = (agility + frequency) / 10
        print(f"\n  Base Crit Chance: ~{base_crit:.1f}%")
        print(f"  Total Crit Chance: ~{total_crit:.1f}%")
        
        # Dodge chance
        dodge = agility / 10
        print(f"  Dodge Chance: ~{dodge:.1f}%")
    
    def export_to_json(self):
        """Export all data to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"leekwars_stats_{timestamp}.json"
        
        export_data = {
            "timestamp": timestamp,
            "farmer": self.farmer_data,
            "leeks": self.leeks
        }
        
        with open(filename, "w") as f:
            json.dump(export_data, f, indent=2)
        
        print(f"\n💾 Data exported to: {filename}")
        return filename

def main():
    print("=== LeekWars Stats Viewer ===\n")
    
    # Create stats viewer
    lw = LeekWarsStats()
    
    # Login
    email, password = load_credentials()  # Changed from input prompt
    password = getpass("Password: ")
    
    if not lw.login(email, password):
        print("Failed to login")
        return 1
    
    # Display farmer stats
    lw.display_farmer_stats()
    
    # Display each leek's stats
    if lw.leeks:
        for leek_id, leek_data in lw.leeks.items():
            lw.display_leek_stats(leek_id, leek_data)
    else:
        print("\n❌ No leeks found in account")
        return 1
    
    # Ask if user wants to export data
    print("\n" + "="*60)
    export = input("\n📁 Export data to JSON? (y/n): ")
    if export.lower() == 'y':
        lw.export_to_json()
    
    print("\n✅ Done!")
    return 0

if __name__ == "__main__":
    exit(main())
