#!/usr/bin/env python3
"""
V6 Actual Weapon Usage Analyzer - Analyze the weapons these leeks actually use
"""

import json
import os
import re
from collections import defaultdict, Counter

def extract_weapon_usage(directory, leek_name):
    """Extract actual weapon usage from debug logs"""
    fight_dir = f"/home/ubuntu/LeekWars-AI/fight_logs/{directory}"
    
    if not os.path.exists(fight_dir):
        return None
    
    stats = {
        'total_fights': 0,
        'weapons_detected': Counter(),
        'weapon_success': Counter(),
        'weapon_failures': Counter(),
        'chips_used': Counter(),
        'fight_durations': [],
        'wins': 0,
        'losses': 0,
        'total_damage_dealt': [],
        'operations_used': []
    }
    
    for filename in os.listdir(fight_dir):
        if filename.endswith("_logs.json"):
            stats['total_fights'] += 1
            
            try:
                with open(os.path.join(fight_dir, filename), 'r') as f:
                    log_data = json.load(f)
                
                max_turn = 0
                fight_damage = 0
                fight_ops = 0
                
                # Parse debug logs
                for farmer_id, leek_logs in log_data.items():
                    for leek_id, log_entries in leek_logs.items():
                        for entry in log_entries:
                            if len(entry) >= 3:
                                log_text = str(entry[2]).lower()
                                turn_match = re.search(r'\[turn (\d+)\]', log_text)
                                if turn_match:
                                    max_turn = max(max_turn, int(turn_match.group(1)))
                                
                                # Extract weapon usage
                                weapon_match = re.search(r'used weapon (\w+)', log_text)
                                if weapon_match:
                                    weapon = weapon_match.group(1)
                                    stats['weapons_detected'][weapon] += 1
                                
                                # Extract weapon success/failure
                                if 'weapon attack failed' in log_text:
                                    weapon_match = re.search(r'for (\w+)', log_text)
                                    if weapon_match:
                                        weapon = weapon_match.group(1)
                                        stats['weapon_failures'][weapon] += 1
                                elif 'weapon attack' in log_text and 'success' in log_text:
                                    weapon_match = re.search(r'(\w+)', log_text)
                                    if weapon_match:
                                        weapon = weapon_match.group(1)
                                        stats['weapon_success'][weapon] += 1
                                
                                # Extract chip usage
                                chip_match = re.search(r'(\w+) chip used', log_text)
                                if chip_match:
                                    chip = chip_match.group(1)
                                    stats['chips_used'][chip] += 1
                                
                                # Extract damage dealt
                                damage_match = re.search(r'(\d+\.?\d*) total damage', log_text)
                                if damage_match:
                                    damage = float(damage_match.group(1))
                                    fight_damage = max(fight_damage, damage)
                                
                                # Extract operation usage
                                ops_match = re.search(r'operation budget: (\d+)', log_text)
                                if ops_match:
                                    ops = int(ops_match.group(1))
                                    fight_ops = max(fight_ops, ops)
                
                stats['fight_durations'].append(max_turn)
                if fight_damage > 0:
                    stats['total_damage_dealt'].append(fight_damage)
                if fight_ops > 0:
                    stats['operations_used'].append(fight_ops)
                
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    
    # Check corresponding data files for win/loss info
    for filename in os.listdir(fight_dir):
        if filename.endswith("_data.json"):
            try:
                with open(os.path.join(fight_dir, filename), 'r') as f:
                    fight_data = json.load(f)
                    if fight_data.get('winner') == 1:
                        stats['wins'] += 1
                    else:
                        stats['losses'] += 1
            except:
                pass
    
    return stats

def main():
    leek_dirs = {
        'EbolaLeek': '129288',
        'RabiesLeek': '129295', 
        'SmallPoxLeek': '129296'
    }
    
    print("=" * 80)
    print("V6 AI ACTUAL WEAPON USAGE ANALYSIS")
    print("=" * 80)
    
    overall_stats = {
        'total_fights': 0,
        'total_wins': 0,
        'all_weapons': Counter(),
        'all_chips': Counter(),
        'all_damage': []
    }
    
    for leek_name, directory in leek_dirs.items():
        print(f"\n📊 ANALYZING {leek_name.upper()} (Directory: {directory})")
        print("-" * 60)
        
        stats = extract_weapon_usage(directory, leek_name)
        if not stats:
            print(f"❌ No data found for {leek_name}")
            continue
        
        # Calculate rates
        win_rate = stats['wins'] / stats['total_fights'] * 100 if stats['total_fights'] > 0 else 0
        avg_duration = sum(stats['fight_durations']) / len(stats['fight_durations']) if stats['fight_durations'] else 0
        avg_damage = sum(stats['total_damage_dealt']) / len(stats['total_damage_dealt']) if stats['total_damage_dealt'] else 0
        avg_ops = sum(stats['operations_used']) / len(stats['operations_used']) if stats['operations_used'] else 0
        
        print(f"🎯 FIGHT OUTCOMES:")
        print(f"   Total Fights: {stats['total_fights']}")
        print(f"   Win Rate: {win_rate:.1f}% ({stats['wins']}/{stats['total_fights']})")
        print(f"   Avg Duration: {avg_duration:.1f} turns")
        print(f"   Avg Damage Dealt: {avg_damage:.1f}")
        if avg_ops > 0:
            print(f"   Avg Operations Used: {avg_ops:,.0f}")
        
        print(f"\n⚔️ WEAPON LOADOUT:")
        if stats['weapons_detected']:
            for weapon, count in stats['weapons_detected'].most_common():
                usage_rate = count / stats['total_fights'] * 100
                success_rate = 0
                if weapon in stats['weapon_success']:
                    total_attempts = count
                    successes = stats['weapon_success'][weapon]
                    success_rate = successes / total_attempts * 100 if total_attempts > 0 else 0
                
                failures = stats['weapon_failures'].get(weapon, 0)
                print(f"   {weapon.upper()}: {count} uses ({usage_rate:.1f}% of fights)")
                if success_rate > 0:
                    print(f"      Success Rate: {success_rate:.1f}%")
                if failures > 0:
                    print(f"      Failures: {failures}")
        else:
            print("   No weapons detected in logs")
        
        print(f"\n💊 CHIP USAGE:")
        if stats['chips_used']:
            for chip, count in stats['chips_used'].most_common():
                usage_rate = count / stats['total_fights'] * 100
                print(f"   {chip.upper()}: {count} uses ({usage_rate:.1f}% of fights)")
        else:
            print("   No chips detected in logs")
        
        # Update overall stats
        overall_stats['total_fights'] += stats['total_fights']
        overall_stats['total_wins'] += stats['wins']
        overall_stats['all_weapons'] += stats['weapons_detected']
        overall_stats['all_chips'] += stats['chips_used']
        overall_stats['all_damage'].extend(stats['total_damage_dealt'])
    
    # Overall summary
    print("\n" + "=" * 80)
    print("📈 OVERALL V6 AI PERFORMANCE SUMMARY")
    print("=" * 80)
    
    overall_winrate = overall_stats['total_wins'] / overall_stats['total_fights'] * 100 if overall_stats['total_fights'] > 0 else 0
    overall_avg_damage = sum(overall_stats['all_damage']) / len(overall_stats['all_damage']) if overall_stats['all_damage'] else 0
    
    print(f"🎯 Combined Results:")
    print(f"   Total Fights: {overall_stats['total_fights']}")
    print(f"   Overall Win Rate: {overall_winrate:.1f}% ({overall_stats['total_wins']}/{overall_stats['total_fights']})")
    print(f"   Average Damage Per Fight: {overall_avg_damage:.1f}")
    
    print(f"\n⚔️ WEAPON DISTRIBUTION ACROSS ALL LEEKS:")
    for weapon, count in overall_stats['all_weapons'].most_common():
        percentage = count / overall_stats['total_fights'] * 100
        print(f"   {weapon.upper()}: {count} total uses ({percentage:.1f}% of all fights)")
    
    print(f"\n💊 CHIP DISTRIBUTION ACROSS ALL LEEKS:")
    for chip, count in overall_stats['all_chips'].most_common():
        percentage = count / overall_stats['total_fights'] * 100
        print(f"   {chip.upper()}: {count} total uses ({percentage:.1f}% of all fights)")
    
    print(f"\n✅ V6 AI PERFORMANCE ASSESSMENT:")
    if overall_winrate >= 50:
        print(f"   ✅ EXCELLENT: Win rate above 50%")
    elif overall_winrate >= 45:
        print(f"   ✅ GOOD: Win rate above 45%")
    elif overall_winrate >= 40:
        print(f"   ⚠️  ACCEPTABLE: Win rate above 40%")
    else:
        print(f"   ❌ NEEDS IMPROVEMENT: Win rate below 40%")
    
    print(f"\n🔧 RECOMMENDED ACTIONS:")
    if overall_stats['all_weapons']:
        dominant_weapon = overall_stats['all_weapons'].most_common(1)[0][0]
        print(f"   Primary weapon appears to be: {dominant_weapon.upper()}")
        print(f"   Consider optimizing {dominant_weapon} usage and positioning")
    else:
        print(f"   Unable to detect weapon usage patterns from logs")

if __name__ == "__main__":
    main()