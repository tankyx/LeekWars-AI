#!/usr/bin/env python3
"""Analyze damage efficiency and TP usage patterns in VirusLeek fights"""

import json
import os
import re
from collections import defaultdict
from datetime import datetime

def analyze_combat_efficiency():
    log_dir = "fight_logs/20443"
    virus_farmer_id = "18035"
    
    # Stats to track
    stats = {
        'total_fights': 0,
        'wins': 0,
        'losses': 0,
        'draws': 0,
        'action_counts': defaultdict(int),
        'damage_actions': [],
        'heal_actions': [],
        'shield_actions': [],
        'buff_actions': [],
        'teleport_count': [],
        'turn_1_actions': defaultdict(int),
        'panic_mode_fights': 0,
        'fights_analyzed': 0
    }
    
    # Process each fight
    fight_ids = set()
    for filename in os.listdir(log_dir):
        if filename.endswith('_data.json'):
            fight_id = filename.replace('_data.json', '')
            fight_ids.add(fight_id)
    
    print(f"Analyzing {len(fight_ids)} fights for combat efficiency...\n")
    
    sample_fights = 0
    max_samples = 50  # Analyze first 50 fights in detail
    
    for fight_id in sorted(fight_ids):
        if sample_fights >= max_samples:
            break
            
        # Load fight data
        data_file = f"{log_dir}/{fight_id}_data.json"
        logs_file = f"{log_dir}/{fight_id}_logs.json"
        
        if not os.path.exists(data_file) or not os.path.exists(logs_file):
            continue
            
        with open(data_file, 'r') as f:
            fight_data = json.load(f)
        
        # Determine winner
        winner = fight_data.get('winner', -1)
        leeks1 = fight_data.get('leeks1', [])
        leeks2 = fight_data.get('leeks2', [])
        
        # Find VirusLeek team
        virus_team = 0
        for leek in leeks1:
            if leek.get('name') == 'VirusLeek':
                virus_team = 1
                break
        if virus_team == 0:
            for leek in leeks2:
                if leek.get('name') == 'VirusLeek':
                    virus_team = 2
                    break
        
        if virus_team == 0:
            continue
        
        # Determine result
        if winner == 0:
            stats['draws'] += 1
            result = 'draw'
        elif winner == virus_team:
            stats['wins'] += 1
            result = 'win'
        else:
            stats['losses'] += 1
            result = 'loss'
        
        stats['total_fights'] += 1
        
        # Analyze logs
        with open(logs_file, 'r') as f:
            logs_data = json.load(f)
        
        if virus_farmer_id not in logs_data:
            continue
        
        farmer_logs = logs_data[virus_farmer_id]
        
        # Analyze log entries
        fight_damage_count = 0
        fight_heal_count = 0
        fight_shield_count = 0
        fight_buff_count = 0
        fight_teleport_count = 0
        has_panic = False
        
        for leek_key, log_entries in farmer_logs.items():
            if not isinstance(log_entries, list):
                continue
            
            for entry in log_entries:
                if isinstance(entry, list) and len(entry) >= 3:
                    turn = entry[0] if len(entry) > 0 else 0
                    log_type = entry[1] if len(entry) > 1 else 0
                    message = str(entry[2]) if len(entry) > 2 else ""
                    
                    # Skip non-info messages
                    if log_type != 3:
                        continue
                    
                    # Analyze Turn 1 actions
                    if turn == 1:
                        if "Armoring" in message:
                            stats['turn_1_actions']['Armoring'] += 1
                        elif "Knowledge" in message:
                            stats['turn_1_actions']['Knowledge'] += 1
                        elif "GRENADE" in message or "Grenade" in message:
                            stats['turn_1_actions']['Grenade'] += 1
                        elif "ATTACK" in message:
                            stats['turn_1_actions']['Attack'] += 1
                        elif "TELEPORT" in message:
                            stats['turn_1_actions']['Teleport'] += 1
                    
                    # Count actions
                    if "PANIC MODE" in message:
                        has_panic = True
                    
                    # Damage actions
                    if any(x in message for x in ["GRENADE", "Lightning", "Flame", "Meteorite", "Rock", 
                                                   "Ice", "Flash", "Spark", "dmg", "damage"]):
                        fight_damage_count += 1
                        stats['action_counts']['damage'] += 1
                        
                        # Try to extract damage values
                        dmg_match = re.search(r'(\d+)\s*(?:dmg|damage)', message.lower())
                        if dmg_match:
                            damage = int(dmg_match.group(1))
                            stats['damage_actions'].append(damage)
                    
                    # Healing actions
                    if any(x in message for x in ["Cure", "CURE", "Regeneration", "REGENERATION", 
                                                   "Drip", "heal", "Vaccine"]):
                        fight_heal_count += 1
                        stats['action_counts']['heal'] += 1
                        stats['heal_actions'].append(1)
                    
                    # Shield actions
                    if any(x in message for x in ["Shield", "SHIELD", "Fortress", "Armor", 
                                                   "Rampart", "Wall", "Carapace"]):
                        fight_shield_count += 1
                        stats['action_counts']['shield'] += 1
                        stats['shield_actions'].append(1)
                    
                    # Buff actions
                    if any(x in message for x in ["Protein", "Steroid", "Warm Up", "Stretching",
                                                   "Reflexes", "Doping", "Adrenaline", "Rage",
                                                   "Motivation", "Knowledge", "Armoring"]):
                        fight_buff_count += 1
                        stats['action_counts']['buff'] += 1
                        stats['buff_actions'].append(1)
                    
                    # Teleport actions
                    if "TELEPORT" in message or "Teleport" in message:
                        fight_teleport_count += 1
                        stats['action_counts']['teleport'] += 1
        
        if has_panic:
            stats['panic_mode_fights'] += 1
        
        # Store per-fight counts
        stats['teleport_count'].append(fight_teleport_count)
        
        sample_fights += 1
        stats['fights_analyzed'] += 1
    
    # Calculate statistics
    print("="*60)
    print("COMBAT EFFICIENCY ANALYSIS")
    print("="*60)
    
    print(f"\n📊 Sample Size: {stats['fights_analyzed']} fights analyzed")
    print(f"   Results: {stats['wins']}W / {stats['losses']}L / {stats['draws']}D")
    
    print(f"\n⚔️ Action Distribution:")
    total_actions = sum(stats['action_counts'].values())
    if total_actions > 0:
        for action, count in sorted(stats['action_counts'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_actions) * 100
            per_fight = count / stats['fights_analyzed'] if stats['fights_analyzed'] > 0 else 0
            print(f"   {action.capitalize()}: {count} ({percentage:.1f}% of actions, {per_fight:.1f} per fight)")
    
    # Calculate damage vs healing ratio
    damage_count = stats['action_counts'].get('damage', 0)
    heal_count = stats['action_counts'].get('heal', 0)
    shield_count = stats['action_counts'].get('shield', 0)
    buff_count = stats['action_counts'].get('buff', 0)
    
    offensive_actions = damage_count
    defensive_actions = heal_count + shield_count
    
    print(f"\n💥 Offensive vs Defensive Balance:")
    if offensive_actions + defensive_actions > 0:
        offensive_ratio = (offensive_actions / (offensive_actions + defensive_actions)) * 100
        defensive_ratio = (defensive_actions / (offensive_actions + defensive_actions)) * 100
        print(f"   Offensive actions: {offensive_actions} ({offensive_ratio:.1f}%)")
        print(f"   Defensive actions: {defensive_actions} ({defensive_ratio:.1f}%)")
        print(f"   Buff actions: {buff_count}")
        
        if offensive_ratio < 40:
            print(f"   ⚠️ WARNING: Too defensive! Only {offensive_ratio:.1f}% offensive actions")
        elif offensive_ratio > 70:
            print(f"   ⚠️ WARNING: Too aggressive! {offensive_ratio:.1f}% offensive actions")
        else:
            print(f"   ✅ Balanced approach")
    
    print(f"\n🎯 Turn 1 Strategy:")
    for action, count in sorted(stats['turn_1_actions'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / stats['fights_analyzed']) * 100 if stats['fights_analyzed'] > 0 else 0
        print(f"   {action}: {count} times ({percentage:.1f}%)")
    
    # Teleport usage
    if stats['teleport_count']:
        avg_teleports = sum(stats['teleport_count']) / len(stats['teleport_count'])
        max_teleports = max(stats['teleport_count'])
        min_teleports = min(stats['teleport_count'])
        print(f"\n🌀 Teleport Usage:")
        print(f"   Average per fight: {avg_teleports:.1f}")
        print(f"   Range: {min_teleports} - {max_teleports}")
        
        # Count fights with no teleports
        no_tp_fights = sum(1 for x in stats['teleport_count'] if x == 0)
        no_tp_percentage = (no_tp_fights / len(stats['teleport_count'])) * 100
        print(f"   Fights with no teleports: {no_tp_fights} ({no_tp_percentage:.1f}%)")
    
    # Estimated TP efficiency
    print(f"\n💰 Estimated TP Efficiency:")
    if damage_count > 0:
        # Assume average 5 TP per damage action (Grenade)
        estimated_damage_tp = damage_count * 5
        if stats['damage_actions']:
            avg_damage = sum(stats['damage_actions']) / len(stats['damage_actions'])
            damage_per_tp = avg_damage / 5
            print(f"   Avg damage per action: {avg_damage:.1f}")
            print(f"   Estimated damage per TP: {damage_per_tp:.1f}")
    
    if heal_count > 0:
        # Assume average 6 TP per heal (mix of Cure and Regeneration)
        estimated_heal_tp = heal_count * 6
        heals_per_fight = heal_count / stats['fights_analyzed'] if stats['fights_analyzed'] > 0 else 0
        print(f"   Heals per fight: {heals_per_fight:.1f}")
        print(f"   Estimated TP on healing: {estimated_heal_tp/stats['fights_analyzed']:.1f} per fight")
    
    # Panic mode analysis
    panic_percentage = (stats['panic_mode_fights'] / stats['fights_analyzed']) * 100 if stats['fights_analyzed'] > 0 else 0
    print(f"\n🚨 Panic Mode:")
    print(f"   Fights with panic: {stats['panic_mode_fights']} ({panic_percentage:.1f}%)")
    
    # Recommendations
    print(f"\n📝 Recommendations:")
    if offensive_ratio < 40:
        print("   1. ⚠️ INCREASE DAMAGE OUTPUT - Too much TP spent on defense")
        print("   2. Consider more aggressive opening (damage on turn 1)")
        print("   3. Reduce healing frequency, focus on burst damage")
    elif offensive_ratio > 70:
        print("   1. Add more defensive actions for survivability")
    
    if avg_teleports < 1:
        print("   2. ⚠️ USE MORE TELEPORTS - Currently underutilized")
        print("      - Teleport for positioning advantages")
        print("      - Use for gap closing to land damage")
    
    if 'Grenade' not in stats['turn_1_actions'] or stats['turn_1_actions'].get('Grenade', 0) < stats['fights_analyzed'] * 0.2:
        print("   3. ⚠️ CONSIDER TURN 1 DAMAGE - Currently too passive")
        print("      - Try Grenade instead of double buffs")
        print("      - Early damage pressure is important")
    
    if panic_percentage > 50:
        print("   4. ⚠️ PANIC MODE TOO FREQUENT - Improve early game")
        print("      - Better positioning to avoid damage")
        print("      - More aggressive to prevent enemy snowball")

if __name__ == "__main__":
    analyze_combat_efficiency()