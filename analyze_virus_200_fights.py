#!/usr/bin/env python3
"""Analyze 200 fight logs from VirusLeek with proper log structure"""

import json
import os
import re
from collections import defaultdict
from datetime import datetime

def analyze_fights():
    log_dir = "fight_logs/20443"
    virus_farmer_id = "18035"  # Virus farmer ID
    
    # Stats to track
    stats = {
        'total_fights': 0,
        'wins': 0,
        'losses': 0,
        'draws': 0,
        'total_turns': 0,
        'turns_in_wins': [],
        'turns_in_losses': [],
        'turns_in_draws': [],
        'opponents': defaultdict(lambda: {'count': 0, 'wins': 0, 'losses': 0, 'draws': 0, 'levels': []}),
        'panic_mode_activations': 0,
        'fights_with_panic': 0,
        'fights_with_errors': 0,
        'error_types': defaultdict(int),
        'turn_1_actions': defaultdict(int),
        'avg_operations_used': []
    }
    
    # Process each fight
    fight_ids = set()
    for filename in os.listdir(log_dir):
        if filename.endswith('_data.json'):
            fight_id = filename.replace('_data.json', '')
            fight_ids.add(fight_id)
    
    print(f"Found {len(fight_ids)} fights to analyze\n")
    
    for fight_id in sorted(fight_ids):
        # Load fight data
        data_file = f"{log_dir}/{fight_id}_data.json"
        logs_file = f"{log_dir}/{fight_id}_logs.json"
        
        if not os.path.exists(data_file):
            continue
            
        with open(data_file, 'r') as f:
            fight_data = json.load(f)
        
        stats['total_fights'] += 1
        
        # Determine winner (1 = team1 wins, 2 = team2 wins, 0 = draw)
        winner = fight_data.get('winner', -1)
        leeks1 = fight_data.get('leeks1', [])
        leeks2 = fight_data.get('leeks2', [])
        
        # Find VirusLeek and opponent
        virus_team = 0
        opponent = None
        
        # Check which team VirusLeek is on
        for leek in leeks1:
            if leek.get('name') == 'VirusLeek':
                virus_team = 1
                if leeks2:
                    opponent = leeks2[0]
                break
        
        if virus_team == 0:
            for leek in leeks2:
                if leek.get('name') == 'VirusLeek':
                    virus_team = 2
                    if leeks1:
                        opponent = leeks1[0]
                    break
        
        if virus_team == 0 or not opponent:
            continue
            
        opponent_name = opponent.get('name', 'Unknown')
        opponent_level = opponent.get('level', 0)
        
        # Update opponent stats
        stats['opponents'][opponent_name]['count'] += 1
        stats['opponents'][opponent_name]['levels'].append(opponent_level)
        
        # Determine result
        result = 'unknown'
        if winner == 0:
            result = 'draw'
            stats['draws'] += 1
            stats['opponents'][opponent_name]['draws'] += 1
        elif winner == virus_team:
            result = 'win'
            stats['wins'] += 1
            stats['opponents'][opponent_name]['wins'] += 1
        else:
            result = 'loss'
            stats['losses'] += 1
            stats['opponents'][opponent_name]['losses'] += 1
        
        # Analyze logs if available
        if os.path.exists(logs_file):
            with open(logs_file, 'r') as f:
                logs_data = json.load(f)
            
            # Get logs for Virus farmer
            if virus_farmer_id in logs_data:
                farmer_logs = logs_data[virus_farmer_id]
                
                # Process logs for each leek (usually just "1" for solo fights)
                for leek_key, log_entries in farmer_logs.items():
                    if not isinstance(log_entries, list):
                        continue
                    
                    max_turn = 0
                    has_panic = False
                    has_errors = False
                    operations_used = 0
                    
                    for entry in log_entries:
                        if isinstance(entry, list) and len(entry) >= 3:
                            turn = entry[0] if len(entry) > 0 else 0
                            log_type = entry[1] if len(entry) > 1 else 0
                            message = entry[2] if len(entry) > 2 else ""
                            
                            # Track max turn
                            if isinstance(turn, int) and turn > max_turn:
                                max_turn = turn
                            
                            # Convert message to string if needed
                            if isinstance(message, (int, float)):
                                message = str(message)
                            elif not isinstance(message, str):
                                continue
                            
                            # Check for panic mode
                            if "PANIC MODE" in message:
                                has_panic = True
                                stats['panic_mode_activations'] += 1
                            
                            # Check for errors (log_type 4 or 5)
                            if log_type in [4, 5]:
                                has_errors = True
                                # Categorize error
                                if "No A* path" in message:
                                    stats['error_types']['No A* path found'] += 1
                                elif "UNKNOWN_VARIABLE" in message:
                                    stats['error_types']['UNKNOWN_VARIABLE'] += 1
                                elif "operation" in message.lower():
                                    stats['error_types']['Operation limit'] += 1
                                    # Extract operation count if possible
                                    op_match = re.search(r'(\d+)\s*operations', message)
                                    if op_match:
                                        operations_used = int(op_match.group(1))
                            
                            # Track Turn 1 actions
                            if turn == 1 and log_type == 3:  # Info messages
                                if "TELEPORT" in message:
                                    stats['turn_1_actions']['Teleport'] += 1
                                elif "Armoring" in message:
                                    stats['turn_1_actions']['Armoring'] += 1
                                elif "Knowledge" in message:
                                    stats['turn_1_actions']['Knowledge'] += 1
                                elif "ATTACK" in message:
                                    stats['turn_1_actions']['Attack'] += 1
                    
                    # Update stats
                    if max_turn > 0:
                        stats['total_turns'] += max_turn
                        if result == 'win':
                            stats['turns_in_wins'].append(max_turn)
                        elif result == 'loss':
                            stats['turns_in_losses'].append(max_turn)
                        else:
                            stats['turns_in_draws'].append(max_turn)
                    
                    if has_panic:
                        stats['fights_with_panic'] += 1
                    
                    if has_errors:
                        stats['fights_with_errors'] += 1
                    
                    if operations_used > 0:
                        stats['avg_operations_used'].append(operations_used)
    
    # Calculate averages
    avg_turns = stats['total_turns'] / stats['total_fights'] if stats['total_fights'] > 0 else 0
    avg_turns_win = sum(stats['turns_in_wins']) / len(stats['turns_in_wins']) if stats['turns_in_wins'] else 0
    avg_turns_loss = sum(stats['turns_in_losses']) / len(stats['turns_in_losses']) if stats['turns_in_losses'] else 0
    avg_turns_draw = sum(stats['turns_in_draws']) / len(stats['turns_in_draws']) if stats['turns_in_draws'] else 0
    
    # Print analysis
    print("="*60)
    print("VIRUS LEEK - 200 FIGHTS ANALYSIS")
    print("="*60)
    
    win_rate = (stats['wins'] / stats['total_fights'] * 100) if stats['total_fights'] > 0 else 0
    print(f"\n📊 Overall Performance:")
    print(f"   Total Fights: {stats['total_fights']}")
    print(f"   Wins: {stats['wins']} ({win_rate:.1f}%)")
    print(f"   Losses: {stats['losses']} ({stats['losses']/stats['total_fights']*100:.1f}%)")
    print(f"   Draws: {stats['draws']} ({stats['draws']/stats['total_fights']*100:.1f}%)")
    
    print(f"\n⏱️ Turn Statistics:")
    print(f"   Average turns per fight: {avg_turns:.1f}")
    print(f"   Average turns in wins: {avg_turns_win:.1f}")
    print(f"   Average turns in losses: {avg_turns_loss:.1f}")
    print(f"   Average turns in draws: {avg_turns_draw:.1f}")
    
    print(f"\n🚨 Panic Mode & Errors:")
    print(f"   Panic mode activations: {stats['panic_mode_activations']} times")
    print(f"   Fights with panic mode: {stats['fights_with_panic']} ({stats['fights_with_panic']/stats['total_fights']*100:.1f}%)")
    print(f"   Fights with errors: {stats['fights_with_errors']} ({stats['fights_with_errors']/stats['total_fights']*100:.1f}%)")
    
    if stats['error_types']:
        print(f"\n   Error breakdown:")
        for error_type, count in sorted(stats['error_types'].items(), key=lambda x: x[1], reverse=True):
            print(f"     - {error_type}: {count} occurrences")
    
    if stats['avg_operations_used']:
        avg_ops = sum(stats['avg_operations_used']) / len(stats['avg_operations_used'])
        print(f"\n   Average operations when hitting limit: {avg_ops:,.0f}")
    
    print(f"\n🎯 Turn 1 Actions:")
    for action, count in sorted(stats['turn_1_actions'].items(), key=lambda x: x[1], reverse=True):
        print(f"   {action}: {count} times ({count/stats['total_fights']*100:.1f}%)")
    
    print(f"\n👥 Top 10 Opponents Faced:")
    top_opponents = sorted(stats['opponents'].items(), key=lambda x: x[1]['count'], reverse=True)[:10]
    for opp_name, opp_stats in top_opponents:
        total = opp_stats['count']
        wins = opp_stats['wins']
        win_rate_vs = (wins / total * 100) if total > 0 else 0
        avg_level = sum(opp_stats['levels']) / len(opp_stats['levels']) if opp_stats['levels'] else 0
        print(f"   {opp_name} (Lvl {avg_level:.0f}): {total} fights, {wins}W/{opp_stats['losses']}L/{opp_stats['draws']}D ({win_rate_vs:.1f}% WR)")
    
    # Find hardest opponents (min 2 fights)
    print(f"\n💀 Hardest Opponents (2+ fights):")
    hard_opponents = [(name, data) for name, data in stats['opponents'].items() if data['count'] >= 2]
    hard_opponents.sort(key=lambda x: x[1]['wins']/x[1]['count'] if x[1]['count'] > 0 else 0)
    for opp_name, opp_stats in hard_opponents[:5]:
        total = opp_stats['count']
        wins = opp_stats['wins']
        win_rate_vs = (wins / total * 100) if total > 0 else 0
        avg_level = sum(opp_stats['levels']) / len(opp_stats['levels']) if opp_stats['levels'] else 0
        print(f"   {opp_name} (Lvl {avg_level:.0f}): {win_rate_vs:.1f}% WR ({wins}W/{opp_stats['losses']}L)")
    
    print(f"\n✅ Summary:")
    print(f"   - Overall win rate: {win_rate:.1f}%")
    print(f"   - Average fight duration: {avg_turns:.1f} turns")
    print(f"   - Panic mode usage: {stats['fights_with_panic']/stats['total_fights']*100:.1f}% of fights")
    print(f"   - Error rate: {stats['fights_with_errors']/stats['total_fights']*100:.1f}% of fights")
    print(f"   - Win fights last {avg_turns_win-avg_turns_loss:.1f} turns longer than losses")

if __name__ == "__main__":
    analyze_fights()