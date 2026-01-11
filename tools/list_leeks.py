#!/usr/bin/env python3
"""
List all leeks for a LeekWars account with their stats

Usage:
  python3 list_leeks.py [--account main]
"""

import requests
import argparse
from config_loader import load_credentials

BASE_URL = "https://leekwars.com/api"


def get_leeks(account='main'):
    """Get all leeks for the account"""
    email, password = load_credentials(account=account)

    session = requests.Session()

    # Login
    print(f"🔐 Logging in as {account}...")
    login_url = f"{BASE_URL}/farmer/login-token"
    login_data = {
        "login": email,
        "password": password
    }

    response = session.post(login_url, data=login_data)

    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return None

    data = response.json()

    if "farmer" not in data:
        print("❌ Login failed: No farmer data")
        return None

    farmer = data["farmer"]
    print(f"✅ Connected as: {farmer.get('login')} (ID: {farmer.get('id')})")

    # Get leeks
    leeks = farmer.get('leeks', {})

    if not leeks:
        print("❌ No leeks found")
        return None

    print(f"\n📊 Found {len(leeks)} leek(s):\n")
    print("="*100)

    leek_list = []

    for leek_id, leek in leeks.items():
        name = leek.get('name', 'Unknown')
        level = leek.get('level', 0)

        # Get detailed stats
        stat_url = f"{BASE_URL}/leek/get/{leek_id}"
        stat_response = session.get(stat_url)

        if stat_response.status_code == 200:
            stat_data = stat_response.json()
            leek_detail = stat_data.get('leek', {})

            # Extract stats
            life = leek_detail.get('life', 0)
            strength = leek_detail.get('strength', 0)
            wisdom = leek_detail.get('wisdom', 0)
            agility = leek_detail.get('agility', 0)
            resistance = leek_detail.get('resistance', 0)
            science = leek_detail.get('science', 0)
            magic = leek_detail.get('magic', 0)
            tp = leek_detail.get('tp', 0)
            mp = leek_detail.get('mp', 0)
            frequency = leek_detail.get('frequency', 0)

            # Calculate primary stat
            primary_stat = max(strength, magic, agility)
            build_type = "STR" if strength >= magic and strength >= agility else ("MAG" if magic >= agility else "AGI")

            # Determine profile category
            if primary_stat < 500:
                profile = "WEAK"
            elif primary_stat < 700:
                profile = "BALANCED"
            else:
                profile = "STRONG"

            leek_info = {
                'id': leek_id,
                'name': name,
                'level': level,
                'life': life,
                'strength': strength,
                'magic': magic,
                'agility': agility,
                'wisdom': wisdom,
                'resistance': resistance,
                'science': science,
                'tp': tp,
                'mp': mp,
                'frequency': frequency,
                'primary_stat': primary_stat,
                'build_type': build_type,
                'profile': profile
            }

            leek_list.append(leek_info)

            # Print formatted info
            print(f"🦗 {name} (ID: {leek_id}) - Level {level}")
            print(f"   Profile: {profile} ({build_type} Build)")
            print(f"   HP: {life}  |  TP: {tp}  |  MP: {mp}  |  Frequency: {frequency}")
            print(f"   STR: {strength}  |  MAG: {magic}  |  AGI: {agility}")
            print(f"   WIS: {wisdom}  |  RES: {resistance}  |  SCI: {science}")
            print(f"   Primary Stat: {primary_stat} ({build_type})")
            print("="*100)
        else:
            print(f"⚠️ Could not get detailed stats for {name}")
            print("="*100)

    # Summary
    print(f"\n📈 Profile Summary:")
    weak = sum(1 for l in leek_list if l['profile'] == 'WEAK')
    balanced = sum(1 for l in leek_list if l['profile'] == 'BALANCED')
    strong = sum(1 for l in leek_list if l['profile'] == 'STRONG')

    print(f"   WEAK (< 500 primary stat): {weak}")
    print(f"   BALANCED (500-699): {balanced}")
    print(f"   STRONG (700+): {strong}")

    print(f"\n📈 Build Type Summary:")
    str_count = sum(1 for l in leek_list if l['build_type'] == 'STR')
    mag_count = sum(1 for l in leek_list if l['build_type'] == 'MAG')
    agi_count = sum(1 for l in leek_list if l['build_type'] == 'AGI')

    print(f"   STR builds: {str_count}")
    print(f"   MAG builds: {mag_count}")
    print(f"   AGI builds: {agi_count}")

    # GA Training recommendations
    print(f"\n🧬 GA Training Recommendations:")

    if weak > 0:
        weak_leek = [l for l in leek_list if l['profile'] == 'WEAK'][0]
        print(f"\n   WEAK PROFILE:")
        print(f"   python3 tools/genetic_optimizer.py \\")
        print(f"     --generations 10 --population 15 --fights-per-genome 60 \\")
        print(f"     --test-leeks \"{weak_leek['name']}\" \\")
        print(f"     --opponents domingo betalpha rex hachess")

    if balanced > 0:
        balanced_leek = [l for l in leek_list if l['profile'] == 'BALANCED'][0]
        print(f"\n   BALANCED PROFILE:")
        print(f"   python3 tools/genetic_optimizer.py \\")
        print(f"     --generations 10 --population 15 --fights-per-genome 60 \\")
        print(f"     --test-leeks \"{balanced_leek['name']}\" \\")
        print(f"     --opponents domingo betalpha rex hachess")

    if strong > 0:
        strong_leek = [l for l in leek_list if l['profile'] == 'STRONG'][0]
        print(f"\n   STRONG PROFILE:")
        print(f"   python3 tools/genetic_optimizer.py \\")
        print(f"     --generations 10 --population 15 --fights-per-genome 60 \\")
        print(f"     --test-leeks \"{strong_leek['name']}\" \\")
        print(f"     --opponents domingo betalpha rex hachess")

    return leek_list


def main():
    parser = argparse.ArgumentParser(description='List leeks and their stats')
    parser.add_argument('--account', default='main', help='Account name (default: main)')

    args = parser.parse_args()

    get_leeks(args.account)


if __name__ == '__main__':
    main()
