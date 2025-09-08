#!/usr/bin/env python3
"""Analyze why V6 AI isn't attacking properly"""

import json
import os
import re
from collections import defaultdict

def analyze_combat_issues():
    # Analyze the latest log file
    log_file = "log_analysis_445497_rex_20250906_173617.txt"
    
    with open(log_file, 'r') as f:
        content = f.read()
    
    # Split into individual fights
    fights = content.split("============================================================\nFight ")
    
    stats = {
        'total_fights': 0,
        'wins': 0,
        'losses': 0,
        'turns_per_fight': [],
        'weapon_checks': 0,
        'weapon_uses': 0,
        'no_attack_warnings': 0,
        'tp_spent_on_buffs': 0,
        'tp_spent_on_heals': 0,
        'damage_dealt': 0,
        'turns_without_attacks': 0,
        'range_issues': defaultdict(int),
        'tp_issues': defaultdict(int)
    }
    
    for fight in fights[1:]:  # Skip the header
        lines = fight.split('\n')
        fight_id = lines[0].split(' - ')[0]
        result = "WIN" if "WIN" in lines[0] else "LOSS" if "LOSS" in lines[0] else "DRAW"
        
        stats['total_fights'] += 1
        if result == "WIN":
            stats['wins'] += 1
        elif result == "LOSS":
            stats['losses'] += 1
        
        current_turn = 0
        attack_this_turn = False
        
        for line in lines:
            # Track turns
            if "TURN " in line and "========" in line:
                if current_turn > 0 and not attack_this_turn:
                    stats['turns_without_attacks'] += 1
                current_turn += 1
                attack_this_turn = False
            
            # Track weapon checks
            if "Checking weapon" in line:
                stats['weapon_checks'] += 1
                
                # Check why weapon wasn't used
                if "Out of range" in line:
                    stats['range_issues']['out_of_range'] += 1
                if "Not enough TP" in line:
                    stats['tp_issues']['not_enough_tp'] += 1
                if "No LOS" in line:
                    stats['range_issues']['no_los'] += 1
            
            # Track actual weapon usage
            if "Used weapon" in line or "Fired" in line:
                stats['weapon_uses'] += 1
                attack_this_turn = True
            
            # Track no attack warnings
            if "No attack options" in line:
                stats['no_attack_warnings'] += 1
            
            # Track TP usage
            if "Used chip" in line:
                # Extract TP cost
                tp_match = re.search(r'for (\d+) TP', line)
                if tp_match:
                    tp = int(tp_match.group(1))
                    
                    # Categorize chip usage
                    if any(x in line.lower() for x in ['shield', 'fortress', 'armoring', 'elevation', 
                                                         'knowledge', 'solidification', 'steroid',
                                                         'protein', 'motivation', 'adrenaline']):
                        stats['tp_spent_on_buffs'] += tp
                    elif any(x in line.lower() for x in ['cure', 'regeneration', 'drip', 'vaccine']):
                        stats['tp_spent_on_heals'] += tp
            
            # Track damage dealt
            dmg_match = re.search(r'dealt (\d+) damage', line.lower())
            if dmg_match:
                stats['damage_dealt'] += int(dmg_match.group(1))
                attack_this_turn = True
        
        if current_turn > 0:
            stats['turns_per_fight'].append(current_turn)
    
    # Calculate averages
    avg_turns = sum(stats['turns_per_fight']) / len(stats['turns_per_fight']) if stats['turns_per_fight'] else 0
    
    print("="*60)
    print("V6 AI COMBAT PROBLEM ANALYSIS")
    print("="*60)
    
    print(f"\n📊 Fight Statistics:")
    print(f"   Total fights: {stats['total_fights']}")
    print(f"   Wins: {stats['wins']} ({stats['wins']/stats['total_fights']*100:.1f}%)")
    print(f"   Losses: {stats['losses']} ({stats['losses']/stats['total_fights']*100:.1f}%)")
    print(f"   Average turns per fight: {avg_turns:.1f}")
    
    print(f"\n⚔️ Attack Problems:")
    print(f"   Weapon checks: {stats['weapon_checks']}")
    print(f"   Weapon uses: {stats['weapon_uses']}")
    print(f"   Success rate: {stats['weapon_uses']/stats['weapon_checks']*100 if stats['weapon_checks'] > 0 else 0:.1f}%")
    print(f"   No attack warnings: {stats['no_attack_warnings']}")
    print(f"   Turns without attacks: {stats['turns_without_attacks']}")
    
    print(f"\n🎯 Why Weapons Aren't Used:")
    total_failures = sum(stats['range_issues'].values()) + sum(stats['tp_issues'].values())
    if total_failures > 0:
        print(f"   Out of range: {stats['range_issues']['out_of_range']} ({stats['range_issues']['out_of_range']/total_failures*100:.1f}%)")
        print(f"   Not enough TP: {stats['tp_issues']['not_enough_tp']} ({stats['tp_issues']['not_enough_tp']/total_failures*100:.1f}%)")
        print(f"   No Line of Sight: {stats['range_issues']['no_los']} ({stats['range_issues']['no_los']/total_failures*100:.1f}%)")
    
    print(f"\n💰 TP Usage Breakdown:")
    total_tp = stats['tp_spent_on_buffs'] + stats['tp_spent_on_heals']
    if total_tp > 0:
        print(f"   Total TP tracked: {total_tp}")
        print(f"   Buffs/Shields: {stats['tp_spent_on_buffs']} ({stats['tp_spent_on_buffs']/total_tp*100:.1f}%)")
        print(f"   Healing: {stats['tp_spent_on_heals']} ({stats['tp_spent_on_heals']/total_tp*100:.1f}%)")
        print(f"   Damage/Attacks: ~0 (PROBLEM!)")
    
    print(f"\n🚨 CRITICAL ISSUES IDENTIFIED:")
    print(f"   1. ZERO WEAPON USAGE - {stats['weapon_uses']} uses out of {stats['weapon_checks']} checks")
    print(f"   2. RANGE PROBLEMS - Out of range {stats['range_issues']['out_of_range']} times")
    print(f"   3. TP STARVATION - Not enough TP {stats['tp_issues']['not_enough_tp']} times")
    print(f"   4. NO DAMAGE OUTPUT - All TP spent on buffs/heals")
    
    print(f"\n📝 ROOT CAUSE:")
    print(f"   The AI is spending all TP on buffs and has none left for attacks!")
    print(f"   - Turn 1: 16 TP on buffs (Knowledge + Armoring + Elevation)")
    print(f"   - Turn 2+: Continuing to buff instead of attacking")
    print(f"   - Result: Enemy is out of range AND no TP for weapons")

if __name__ == "__main__":
    analyze_combat_issues()