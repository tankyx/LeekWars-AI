#!/usr/bin/env python3
"""
LeekWars Leeks Information Retriever
Connects to LeekWars and retrieves detailed information about all leeks
"""

import requests
import json
import sys
from datetime import datetime
from tabulate import tabulate

BASE_URL = "https://leekwars.com/api"

class LeekWarsInfoRetriever:
    def __init__(self):
        """Initialize session and variables"""
        self.session = requests.Session()
        self.farmer = None
        self.token = None
        self.leeks = {}
        
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
                    
                    if "farmer" in data and "token" in data:
                        self.farmer = data["farmer"]
                        self.token = data["token"]
                        self.leeks = self.farmer.get("leeks", {})
                        
                        farmer_name = self.farmer.get("login", "Unknown")
                        farmer_id = self.farmer.get("id", "Unknown")
                        
                        print(f"\n✅ Connected successfully!")
                        print(f"   👤 Farmer: {farmer_name} (ID: {farmer_id})")
                        
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
    
    def get_detailed_leek_info(self, leek_id):
        """Get detailed information about a specific leek"""
        url = f"{BASE_URL}/leek/get/{leek_id}"
        
        try:
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if "leek" in data:
                    return data["leek"]
            
            return None
            
        except Exception as e:
            print(f"   ⚠️ Error getting detailed info for leek {leek_id}: {e}")
            return None
    
    def display_farmer_stats(self):
        """Display farmer statistics"""
        print("\n" + "="*60)
        print("FARMER STATISTICS")
        print("="*60)
        
        info = [
            ["Name", self.farmer.get("login", "N/A")],
            ["ID", self.farmer.get("id", "N/A")],
            ["Level", self.farmer.get("talent", "N/A")],
            ["Habs (Money)", f"{self.farmer.get('habs', 0):,}"],
            ["Crystals", f"{self.farmer.get('crystals', 0):,}"],
            ["Total Leeks", len(self.leeks)],
            ["Available Fights", self.farmer.get("fights", 0)],
            ["Tournament Fights", self.farmer.get("tournament_fights", 0)]
        ]
        
        print(tabulate(info, headers=["Property", "Value"], tablefmt="grid"))
        
        # Battle statistics
        victories = self.farmer.get("victories", 0)
        draws = self.farmer.get("draws", 0) 
        defeats = self.farmer.get("defeats", 0)
        total_battles = victories + draws + defeats
        
        print("\n📊 Battle Statistics:")
        ratio = self.farmer.get('ratio', 0)
        if isinstance(ratio, str):
            ratio = float(ratio) if ratio else 0
        
        battle_info = [
            ["Victories", victories, f"{(victories/total_battles*100):.1f}%" if total_battles > 0 else "0%"],
            ["Draws", draws, f"{(draws/total_battles*100):.1f}%" if total_battles > 0 else "0%"],
            ["Defeats", defeats, f"{(defeats/total_battles*100):.1f}%" if total_battles > 0 else "0%"],
            ["Total Battles", total_battles, "100%"],
            ["Ratio", f"{ratio:.2f}", "-"]
        ]
        
        print(tabulate(battle_info, headers=["Type", "Count", "Percentage"], tablefmt="grid"))
    
    def display_leeks_info(self):
        """Display information about all leeks"""
        if not self.leeks:
            print("\n❌ No leeks found!")
            return
        
        print("\n" + "="*60)
        print("LEEKS INFORMATION")
        print("="*60)
        
        for leek_id, leek_data in self.leeks.items():
            print(f"\n🥬 {leek_data.get('name', 'Unknown')} (ID: {leek_id})")
            print("-" * 40)
            
            # Get detailed info
            detailed_info = self.get_detailed_leek_info(leek_id)
            
            if detailed_info:
                leek_data = detailed_info
            
            # Basic info
            basic_info = [
                ["Level", leek_data.get("level", "N/A")],
                ["XP", f"{leek_data.get('xp', 0):,} / {leek_data.get('next_xp', 0):,}"],
                ["Talent Points", leek_data.get("talent", 0)],
                ["Capital (Unused Points)", leek_data.get("capital", 0)]
            ]
            
            print("\n📋 Basic Information:")
            print(tabulate(basic_info, headers=["Property", "Value"], tablefmt="simple"))
            
            # Combat stats
            print("\n⚔️ Combat Statistics:")
            stats_info = [
                ["Life (HP)", leek_data.get("life", 0)],
                ["Strength", leek_data.get("strength", 0)],
                ["Wisdom", leek_data.get("wisdom", 0)],
                ["Agility", leek_data.get("agility", 0)],
                ["Resistance", leek_data.get("resistance", 0)],
                ["Science", leek_data.get("science", 0)],
                ["Magic", leek_data.get("magic", 0)],
                ["Frequency", leek_data.get("frequency", 0)],
                ["TP (Turn Points)", leek_data.get("tp", 0)],
                ["MP (Movement Points)", leek_data.get("mp", 0)]
            ]
            
            print(tabulate(stats_info, headers=["Stat", "Value"], tablefmt="simple"))
            
            # Battle record
            if detailed_info:
                victories = detailed_info.get("victories", 0)
                draws = detailed_info.get("draws", 0)
                defeats = detailed_info.get("defeats", 0)
                total = victories + draws + defeats
                
                if total > 0:
                    print("\n🏆 Battle Record:")
                    ratio = detailed_info.get('ratio', 0)
                    if isinstance(ratio, str):
                        ratio = float(ratio) if ratio else 0
                    
                    battle_record = [
                        ["Victories", victories, f"{(victories/total*100):.1f}%"],
                        ["Draws", draws, f"{(draws/total*100):.1f}%"],
                        ["Defeats", defeats, f"{(defeats/total*100):.1f}%"],
                        ["Total", total, "100%"],
                        ["Ratio", f"{ratio:.2f}", "-"]
                    ]
                    print(tabulate(battle_record, headers=["Type", "Count", "Percentage"], tablefmt="simple"))
            
            # Weapons
            if "weapons" in leek_data and leek_data["weapons"]:
                print("\n🔫 Equipped Weapons:")
                for weapon_id in leek_data["weapons"]:
                    weapon_name = self.get_item_name("weapon", weapon_id)
                    print(f"   - {weapon_name}")
            
            # Chips
            if "chips" in leek_data and leek_data["chips"]:
                print("\n💎 Equipped Chips:")
                for chip_id in leek_data["chips"]:
                    chip_name = self.get_item_name("chip", chip_id)
                    print(f"   - {chip_name}")
            
            print()
    
    def get_item_name(self, item_type, item_id):
        """Get the name of a weapon or chip by ID"""
        # Common weapon/chip names (you can expand this)
        weapons = {
            1: "Pistol",
            2: "Machine Gun", 
            3: "Double Gun",
            4: "Shotgun",
            5: "Magnum",
            6: "Laser",
            7: "Grenade Launcher",
            8: "Flame Thrower",
            9: "Destroyer",
            10: "Gauss",
            11: "Sniper",
            12: "Broadsword",
            13: "Katana",
            14: "Axe",
            15: "J-Laser",
            16: "Ilicit Laser",
            17: "B-Laser",
            18: "Neutrino",
            19: "Lightning Gun",
            20: "Electrisor",
            21: "Ion",
            22: "Pheme",
            23: "Rhino"
        }
        
        chips = {
            1: "Shock",
            2: "Spark",
            3: "Flame",
            4: "Flash",
            5: "Lightning",
            6: "Iceberg",
            7: "Meteorite",
            8: "Rock",
            9: "Rockfall",
            10: "Pebble",
            11: "Ice",
            12: "Stalactite",
            13: "Cure",
            14: "Drip",
            15: "Vaccine",
            16: "Regeneration",
            17: "Armor",
            18: "Shield",
            19: "Wall",
            20: "Helmet",
            21: "Protein",
            22: "Steroid",
            23: "Warm Up",
            24: "Stretching",
            25: "Reflexes",
            26: "Doping",
            27: "Adrenaline",
            28: "Rage",
            29: "Liberation",
            30: "Teleportation",
            31: "Inversion",
            32: "Resurrection",
            33: "Devil Strike",
            34: "Punishment",
            35: "Serum",
            36: "Tranquilizer",
            37: "Soporific",
            38: "Fracture",
            39: "Solidification",
            40: "Venom",
            41: "Toxin",
            42: "Plague",
            43: "Horn",
            44: "Collar",
            45: "Cortex",
            46: "Burning",
            47: "Antidote",
            48: "Motivation",
            49: "Slow Down",
            50: "Ball and Chain",
            51: "Tranquilizer",
            52: "Acceleration",
            53: "Winged Boots",
            54: "Seven-League Boots",
            55: "Leather Boots",
            56: "Remission",
            57: "Carapace",
            58: "Fertilizer",
            59: "Acceleration"
        }
        
        if item_type == "weapon":
            return weapons.get(item_id, f"Weapon #{item_id}")
        else:
            return chips.get(item_id, f"Chip #{item_id}")
    
    def export_to_json(self, filename=None):
        """Export all data to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"leekwars_data_{timestamp}.json"
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "farmer": self.farmer,
            "leeks": {}
        }
        
        # Get detailed info for each leek
        for leek_id in self.leeks:
            detailed = self.get_detailed_leek_info(leek_id)
            if detailed:
                data["leeks"][leek_id] = detailed
            else:
                data["leeks"][leek_id] = self.leeks[leek_id]
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Data exported to: {filename}")
        return filename
    
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
    print("="*60)
    print("LEEKWARS LEEKS INFORMATION RETRIEVER")
    print("="*60)
    
    # Create retriever instance
    retriever = LeekWarsInfoRetriever()
    
    # Get credentials
    email = "tanguy.pedrazzoli@gmail.com"
    password = "tanguy0211"
    
    # Login
    if not retriever.login(email, password):
        print("\n❌ Failed to login. Please check your credentials.")
        return 1
    
    try:
        # Display farmer statistics
        retriever.display_farmer_stats()
        
        # Display leeks information
        retriever.display_leeks_info()
        
        # Automatically export data to JSON
        print("\n" + "="*60)
        retriever.export_to_json()
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        # Always disconnect properly
        retriever.disconnect()
    
    return 0

if __name__ == "__main__":
    exit(main())