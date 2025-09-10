#!/usr/bin/env python3
"""
V6 Fight Log Analyzer
Analyzes fight logs for all three leeks to determine M-Laser vs Rifle usage and performance
"""

import json
import os
import re
from collections import defaultdict, Counter
from statistics import mean, median

def load_fight_data(directory):
    """Load all fight data from a directory"""
    fights = []
    fight_dir = f"/home/ubuntu/LeekWars-AI/fight_logs/{directory}"
    
    if not os.path.exists(fight_dir):
        return fights
    
    for filename in os.listdir(fight_dir):
        if filename.endswith("_data.json"):
            try:
                with open(os.path.join(fight_dir, filename), 'r') as f:
                    fight_data = json.load(f)
                    fights.append(fight_data)
            except Exception as e:
                print(f"Error loading {filename}: {e}")
    
    return fights

def load_fight_logs(directory):
    """Load all fight logs from a directory"""
    logs = {}
    fight_dir = f"/home/ubuntu/LeekWars-AI/fight_logs/{directory}"
    
    if not os.path.exists(fight_dir):
        return logs
    
    for filename in os.listdir(fight_dir):
        if filename.endswith("_logs.json"):
            fight_id = filename.split("_")[0]
            try:
                with open(os.path.join(fight_dir, filename), 'r') as f:
                    log_data = json.load(f)
                    logs[fight_id] = log_data
            except Exception as e:
                print(f"Error loading {filename}: {e}")
    
    return logs

def analyze_weapon_usage(logs):
    """Analyze weapon usage from fight logs"""
    weapon_stats = {
        'M-Laser': {'uses': 0, 'successes': 0, 'turns_used': []},
        'Rifle': {'uses': 0, 'successes': 0, 'turns_used': []},
        'Grenade': {'uses': 0, 'successes': 0, 'turns_used': []},
        'Dark Katana': {'uses': 0, 'successes': 0, 'turns_used': []}
    }
    
    total_fights = len(logs)
    fights_with_mlaser = 0
    fights_with_rifle = 0
    
    for fight_id, log_data in logs.items():
        fight_used_mlaser = False
        fight_used_rifle = False
        
        if 'logs' in log_data:
            for turn_data in log_data['logs']:
                if 'actions' in turn_data:
                    for action in turn_data['actions']:
                        # Check for weapon usage
                        if action.get('type') == 2:  # USE_WEAPON action type
                            weapon_id = action.get('item')
                            result = action.get('result', 0)
                            turn_num = turn_data.get('turn', 0)
                            
                            # Map weapon IDs to names (standard LeekWars weapon IDs)
                            weapon_name = None
                            if weapon_id == 37:  # M-Laser
                                weapon_name = 'M-Laser'
                                fight_used_mlaser = True
                            elif weapon_id == 1:   # Rifle  
                                weapon_name = 'Rifle'
                                fight_used_rifle = True
                            elif weapon_id == 32: # Grenade Launcher
                                weapon_name = 'Grenade'
                            elif weapon_id == 301: # Dark Katana
                                weapon_name = 'Dark Katana'
                            
                            if weapon_name and weapon_name in weapon_stats:
                                weapon_stats[weapon_name]['uses'] += 1
                                weapon_stats[weapon_name]['turns_used'].append(turn_num)
                                
                                # Check if successful (result codes: 1=success, 2=critical)
                                if result in [1, 2]:
                                    weapon_stats[weapon_name]['successes'] += 1
        
        if fight_used_mlaser:
            fights_with_mlaser += 1
        if fight_used_rifle:
            fights_with_rifle += 1
    
    return weapon_stats, total_fights, fights_with_mlaser, fights_with_rifle

def analyze_fight_outcomes(fights):
    """Analyze fight outcomes and statistics"""
    stats = {
        'total_fights': len(fights),
        'wins': 0,
        'losses': 0,
        'win_rate': 0,
        'fight_durations': [],
        'opponents': Counter()
    }
    
    for fight in fights:
        # Determine if our leek won (winner == 1 means team 1 won, we're usually team 1)
        if fight.get('winner') == 1:
            stats['wins'] += 1
        else:
            stats['losses'] += 1
        
        # Get fight duration
        if 'fight' in fight and 'actions' in fight['fight']:
            max_turn = 0
            for action in fight['fight']['actions']:
                if 'turn' in action:
                    max_turn = max(max_turn, action['turn'])
            stats['fight_durations'].append(max_turn)
        
        # Track opponents
        if 'leeks2' in fight and fight['leeks2']:
            opponent_name = fight['leeks2'][0].get('name', 'Unknown')
            stats['opponents'][opponent_name] += 1
    
    if stats['total_fights'] > 0:
        stats['win_rate'] = stats['wins'] / stats['total_fights'] * 100
    
    return stats

def analyze_debug_logs(logs):
    """Analyze debug logs for weapon selection patterns"""
    weapon_patterns = {
        'mlaser_attempts': 0,
        'rifle_attempts': 0,
        'weapon_switches': 0,
        'positioning_moves': 0,
        'line_alignment_issues': 0
    }
    
    for fight_id, log_data in logs.items():
        if 'logs' in log_data:
            for turn_data in log_data['logs']:
                if 'logs' in turn_data:
                    for log_entry in turn_data['logs']:
                        log_text = log_entry.get('text', '').lower()
                        
                        # Look for weapon-related debug messages
                        if 'm-laser' in log_text:
                            weapon_patterns['mlaser_attempts'] += 1
                        elif 'rifle' in log_text:
                            weapon_patterns['rifle_attempts'] += 1
                        
                        if 'switch' in log_text or 'weapon' in log_text:
                            weapon_patterns['weapon_switches'] += 1
                        
                        if 'position' in log_text or 'move' in log_text:
                            weapon_patterns['positioning_moves'] += 1
                        
                        if 'line' in log_text and ('align' in log_text or 'same' in log_text):
                            weapon_patterns['line_alignment_issues'] += 1
    
    return weapon_patterns

def main():
    leek_dirs = {
        'EbolaLeek': '129288',
        'RabiesLeek': '129295', 
        'SmallPoxLeek': '129296'
    }
    
    print("=" * 80)
    print("V6 AI FIGHT ANALYSIS - M-LASER VS RIFLE PRIORITIZATION")
    print("=" * 80)
    
    overall_stats = {
        'total_fights': 0,
        'total_wins': 0,
        'total_losses': 0,
        'mlaser_usage': 0,
        'rifle_usage': 0
    }
    
    for leek_name, directory in leek_dirs.items():
        print(f"\n📊 ANALYZING {leek_name.upper()} (Directory: {directory})")
        print("-" * 60)
        
        # Load fight data and logs
        fights = load_fight_data(directory)
        logs = load_fight_logs(directory)
        
        if not fights:
            print(f"❌ No fight data found for {leek_name}")
            continue
        
        # Analyze fight outcomes
        outcome_stats = analyze_fight_outcomes(fights)
        
        # Analyze weapon usage
        weapon_stats, total_fights, fights_mlaser, fights_rifle = analyze_weapon_usage(logs)
        
        # Analyze debug patterns
        debug_patterns = analyze_debug_logs(logs)
        
        # Print results
        print(f"🎯 FIGHT OUTCOMES:")
        print(f"   Total Fights: {outcome_stats['total_fights']}")
        print(f"   Wins: {outcome_stats['wins']} ({outcome_stats['win_rate']:.1f}%)")
        print(f"   Losses: {outcome_stats['losses']}")
        
        if outcome_stats['fight_durations']:
            print(f"   Avg Duration: {mean(outcome_stats['fight_durations']):.1f} turns")
        
        print(f"\n⚔️ WEAPON USAGE ANALYSIS:")
        print(f"   Fights with M-Laser: {fights_mlaser}/{total_fights} ({fights_mlaser/total_fights*100:.1f}%)")
        print(f"   Fights with Rifle: {fights_rifle}/{total_fights} ({fights_rifle/total_fights*100:.1f}%)")
        
        for weapon, stats in weapon_stats.items():
            if stats['uses'] > 0:
                success_rate = stats['successes'] / stats['uses'] * 100
                avg_turn = mean(stats['turns_used']) if stats['turns_used'] else 0
                print(f"   {weapon}: {stats['uses']} uses, {stats['successes']} hits ({success_rate:.1f}%), avg turn {avg_turn:.1f}")
        
        print(f"\n🔍 DEBUG PATTERNS:")
        for pattern, count in debug_patterns.items():
            if count > 0:
                print(f"   {pattern.replace('_', ' ').title()}: {count}")
        
        print(f"\n🏆 TOP OPPONENTS:")
        for opponent, count in outcome_stats['opponents'].most_common(5):
            print(f"   {opponent}: {count} fights")
        
        # Update overall stats
        overall_stats['total_fights'] += outcome_stats['total_fights']
        overall_stats['total_wins'] += outcome_stats['wins']
        overall_stats['total_losses'] += outcome_stats['losses']
        overall_stats['mlaser_usage'] += fights_mlaser
        overall_stats['rifle_usage'] += fights_rifle
    
    # Overall summary
    print("\n" + "=" * 80)
    print("📈 OVERALL V6 AI PERFORMANCE SUMMARY")
    print("=" * 80)
    
    overall_winrate = overall_stats['total_wins'] / overall_stats['total_fights'] * 100 if overall_stats['total_fights'] > 0 else 0
    mlaser_adoption = overall_stats['mlaser_usage'] / overall_stats['total_fights'] * 100 if overall_stats['total_fights'] > 0 else 0
    rifle_adoption = overall_stats['rifle_usage'] / overall_stats['total_fights'] * 100 if overall_stats['total_fights'] > 0 else 0
    
    print(f"🎯 Combined Results:")
    print(f"   Total Fights: {overall_stats['total_fights']}")
    print(f"   Overall Win Rate: {overall_winrate:.1f}% ({overall_stats['total_wins']}/{overall_stats['total_fights']})")
    print(f"   M-Laser Adoption: {mlaser_adoption:.1f}% ({overall_stats['mlaser_usage']} fights)")  
    print(f"   Rifle Adoption: {rifle_adoption:.1f}% ({overall_stats['rifle_usage']} fights)")
    
    print(f"\n✅ M-LASER PRIORITIZATION FIX STATUS:")
    if mlaser_adoption > rifle_adoption:
        print(f"   ✅ SUCCESS: M-Laser used more frequently than Rifle")
        print(f"   📊 M-Laser: {mlaser_adoption:.1f}% vs Rifle: {rifle_adoption:.1f}%")
    elif mlaser_adoption == rifle_adoption:
        print(f"   ⚠️  MIXED: Equal usage of M-Laser and Rifle ({mlaser_adoption:.1f}%)")
    else:
        print(f"   ❌ ISSUE: Rifle still preferred over M-Laser")  
        print(f"   📊 Rifle: {rifle_adoption:.1f}% vs M-Laser: {mlaser_adoption:.1f}%")

if __name__ == "__main__":
    main()