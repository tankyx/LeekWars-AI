#!/usr/bin/env python3
"""
V6 Weapon Pattern Analyzer - Focus on debug logs to understand weapon usage
"""

import json
import os
import re
from collections import defaultdict, Counter

def analyze_debug_logs(directory, leek_name):
    """Analyze debug logs for weapon usage patterns"""
    fight_dir = f"/home/ubuntu/LeekWars-AI/fight_logs/{directory}"
    
    if not os.path.exists(fight_dir):
        return None
    
    stats = {
        'total_fights': 0,
        'mlaser_usage': 0,
        'rifle_usage': 0,
        'mlaser_success': 0,
        'rifle_success': 0,
        'mlaser_failures': 0,
        'rifle_failures': 0,
        'alignment_issues': 0,
        'weapon_switches': 0,
        'fight_durations': [],
        'wins': 0,
        'losses': 0
    }
    
    for filename in os.listdir(fight_dir):
        if filename.endswith("_logs.json"):
            stats['total_fights'] += 1
            
            try:
                with open(os.path.join(fight_dir, filename), 'r') as f:
                    log_data = json.load(f)
                
                fight_mlaser_used = False
                fight_rifle_used = False
                max_turn = 0
                
                # Parse debug logs
                for farmer_id, leek_logs in log_data.items():
                    for leek_id, log_entries in leek_logs.items():
                        for entry in log_entries:
                            if len(entry) >= 3:
                                log_text = str(entry[2]).lower()
                                turn_match = re.search(r'\[turn (\d+)\]', log_text)
                                if turn_match:
                                    max_turn = max(max_turn, int(turn_match.group(1)))
                                
                                # Check for weapon usage patterns
                                if 'm-laser' in log_text or 'mlaser' in log_text:
                                    if not fight_mlaser_used:
                                        stats['mlaser_usage'] += 1
                                        fight_mlaser_used = True
                                    
                                    if 'success' in log_text or 'fired' in log_text or 'critical' in log_text:
                                        stats['mlaser_success'] += 1
                                    elif 'failed' in log_text or 'error' in log_text:
                                        stats['mlaser_failures'] += 1
                                
                                elif 'rifle' in log_text:
                                    if not fight_rifle_used:
                                        stats['rifle_usage'] += 1
                                        fight_rifle_used = True
                                    
                                    if 'success' in log_text or 'fired' in log_text or 'critical' in log_text:
                                        stats['rifle_success'] += 1
                                    elif 'failed' in log_text or 'error' in log_text:
                                        stats['rifle_failures'] += 1
                                
                                # Check for alignment issues
                                if 'line' in log_text and ('align' in log_text or 'same' in log_text):
                                    stats['alignment_issues'] += 1
                                
                                # Check for weapon switching
                                if 'weapon' in log_text and ('switch' in log_text or 'set' in log_text):
                                    stats['weapon_switches'] += 1
                
                stats['fight_durations'].append(max_turn)
                
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
    print("V6 AI WEAPON USAGE ANALYSIS - DEBUG LOG BASED")
    print("=" * 80)
    
    overall_stats = {
        'total_fights': 0,
        'total_wins': 0,
        'mlaser_fights': 0,
        'rifle_fights': 0,
        'total_alignment_issues': 0,
        'total_weapon_switches': 0
    }
    
    for leek_name, directory in leek_dirs.items():
        print(f"\n📊 ANALYZING {leek_name.upper()} (Directory: {directory})")
        print("-" * 60)
        
        stats = analyze_debug_logs(directory, leek_name)
        if not stats:
            print(f"❌ No data found for {leek_name}")
            continue
        
        # Calculate rates
        win_rate = stats['wins'] / stats['total_fights'] * 100 if stats['total_fights'] > 0 else 0
        mlaser_rate = stats['mlaser_usage'] / stats['total_fights'] * 100 if stats['total_fights'] > 0 else 0
        rifle_rate = stats['rifle_usage'] / stats['total_fights'] * 100 if stats['total_fights'] > 0 else 0
        avg_duration = sum(stats['fight_durations']) / len(stats['fight_durations']) if stats['fight_durations'] else 0
        
        print(f"🎯 FIGHT OUTCOMES:")
        print(f"   Total Fights: {stats['total_fights']}")
        print(f"   Win Rate: {win_rate:.1f}% ({stats['wins']}/{stats['total_fights']})")
        print(f"   Avg Duration: {avg_duration:.1f} turns")
        
        print(f"\n⚔️ WEAPON USAGE:")
        print(f"   M-Laser Usage: {mlaser_rate:.1f}% ({stats['mlaser_usage']} fights)")
        print(f"   Rifle Usage: {rifle_rate:.1f}% ({stats['rifle_usage']} fights)")
        
        if stats['mlaser_usage'] > 0:
            print(f"   M-Laser Success Events: {stats['mlaser_success']}")
            print(f"   M-Laser Failure Events: {stats['mlaser_failures']}")
        
        if stats['rifle_usage'] > 0:
            print(f"   Rifle Success Events: {stats['rifle_success']}")  
            print(f"   Rifle Failure Events: {stats['rifle_failures']}")
        
        print(f"\n🔧 TECHNICAL ISSUES:")
        print(f"   Line Alignment Issues: {stats['alignment_issues']}")
        print(f"   Weapon Switches: {stats['weapon_switches']}")
        
        # Weapon preference analysis
        if stats['mlaser_usage'] > stats['rifle_usage']:
            preference = "✅ M-Laser PREFERRED"
        elif stats['rifle_usage'] > stats['mlaser_usage']:
            preference = "⚠️ Rifle PREFERRED"
        else:
            preference = "🔄 Equal Usage"
        
        print(f"\n🎯 WEAPON PREFERENCE: {preference}")
        
        # Update overall stats
        overall_stats['total_fights'] += stats['total_fights']
        overall_stats['total_wins'] += stats['wins']
        overall_stats['mlaser_fights'] += stats['mlaser_usage']
        overall_stats['rifle_fights'] += stats['rifle_usage']
        overall_stats['total_alignment_issues'] += stats['alignment_issues']
        overall_stats['total_weapon_switches'] += stats['weapon_switches']
    
    # Overall summary
    print("\n" + "=" * 80)
    print("📈 OVERALL V6 AI PERFORMANCE SUMMARY")
    print("=" * 80)
    
    overall_winrate = overall_stats['total_wins'] / overall_stats['total_fights'] * 100 if overall_stats['total_fights'] > 0 else 0
    mlaser_adoption = overall_stats['mlaser_fights'] / overall_stats['total_fights'] * 100 if overall_stats['total_fights'] > 0 else 0
    rifle_adoption = overall_stats['rifle_fights'] / overall_stats['total_fights'] * 100 if overall_stats['total_fights'] > 0 else 0
    
    print(f"🎯 Combined Results:")
    print(f"   Total Fights: {overall_stats['total_fights']}")
    print(f"   Overall Win Rate: {overall_winrate:.1f}% ({overall_stats['total_wins']}/{overall_stats['total_fights']})")
    print(f"   M-Laser Adoption: {mlaser_adoption:.1f}% ({overall_stats['mlaser_fights']} fights)")  
    print(f"   Rifle Adoption: {rifle_adoption:.1f}% ({overall_stats['rifle_fights']} fights)")
    
    print(f"\n🔧 Overall Technical Issues:")
    print(f"   Total Line Alignment Issues: {overall_stats['total_alignment_issues']}")
    print(f"   Total Weapon Switches: {overall_stats['total_weapon_switches']}")
    
    print(f"\n✅ M-LASER PRIORITIZATION FIX ASSESSMENT:")
    if mlaser_adoption > rifle_adoption * 1.5:
        print(f"   ✅ EXCELLENT: M-Laser strongly preferred over Rifle")
        ratio = mlaser_adoption / rifle_adoption if rifle_adoption > 0 else float('inf')
        print(f"   📊 M-Laser used {ratio:.1f}x more than Rifle")
    elif mlaser_adoption > rifle_adoption:
        print(f"   ✅ SUCCESS: M-Laser preferred over Rifle")
        print(f"   📊 M-Laser: {mlaser_adoption:.1f}% vs Rifle: {rifle_adoption:.1f}%")
    elif abs(mlaser_adoption - rifle_adoption) < 5:
        print(f"   ⚠️  MIXED: Similar usage of both weapons")
        print(f"   📊 M-Laser: {mlaser_adoption:.1f}% vs Rifle: {rifle_adoption:.1f}%")
    else:
        print(f"   ❌ ISSUE: Rifle still preferred over M-Laser")  
        print(f"   📊 Rifle: {rifle_adoption:.1f}% vs M-Laser: {mlaser_adoption:.1f}%")
        print(f"   🔍 Check alignment issues: {overall_stats['total_alignment_issues']} detected")

if __name__ == "__main__":
    main()