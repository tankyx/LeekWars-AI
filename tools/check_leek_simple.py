#!/usr/bin/env python3
"""
Simple leek info checker
"""

import requests

def check_leek():
    # Login
    session = requests.Session()
    response = session.post("https://leekwars.com/api/farmer/login-token", data={
        "login": "tanguy.pedrazzoli@gmail.com",
        "password": "tanguy0211"
    })
    
    if response.status_code != 200:
        print("❌ Login failed")
        return
    
    token = response.json().get("token")
    farmer = response.json().get("farmer")
    print(f"✅ Logged in as: {farmer.get('login')}")
    
    # Get leek info
    leek_id = 129296  # Your main leek ID
    leek_response = session.get(f"https://leekwars.com/api/leek/get/{leek_id}")
    
    if leek_response.status_code == 200:
        leek_data = leek_response.json()
        leek = leek_data.get("leek", {})
        
        print(f"\n🌱 LEEK INFO - {leek.get('name', 'Unknown')}")
        print("=" * 40)
        print(f"Level: {leek.get('level', 0)}")
        print(f"Life: {leek.get('life', 0)}")
        print(f"Strength: {leek.get('strength', 0)}")
        print(f"Agility: {leek.get('agility', 0)}")
        print(f"Wisdom: {leek.get('wisdom', 0)}")
        print(f"Resistance: {leek.get('resistance', 0)}")
        print(f"Science: {leek.get('science', 0)}")
        print(f"Magic: {leek.get('magic', 0)}")
        print(f"TP: {leek.get('tp', 0)}")
        print(f"MP: {leek.get('mp', 0)}")
        
        # Weapons
        weapons = leek.get("weapons", [])
        print(f"\n⚔️  WEAPONS ({len(weapons)}):")
        for weapon in weapons:
            print(f"  - {weapon}")
            
        # Chips  
        chips = leek.get("chips", [])
        print(f"\n🔧 CHIPS ({len(chips)}):")
        for chip in chips:
            print(f"  - {chip}")
            
        # AI
        ai_id = leek.get("ai", 0)
        print(f"\n🤖 AI: {ai_id}")
        
        # Check if AI is our V8
        if ai_id == 445803:
            print("✅ Using V8_main script")
        elif ai_id == 445497:
            print("✅ Using V6_main script") 
        else:
            print(f"⚠️  Using unknown script ID: {ai_id}")
    else:
        print("❌ Failed to get leek info")
    
    # Disconnect
    session.post(f"https://leekwars.com/api/farmer/disconnect/{token}")
    print("\n👋 Disconnected")

if __name__ == '__main__':
    check_leek()