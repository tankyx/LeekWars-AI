#!/usr/bin/env python3
"""Analyze 200 fight logs from VirusLeek"""

import json
import os
from collections import defaultdict
from datetime import datetime

def analyze_fights():
    log_dir = "fight_logs/20443"
    
    # Stats to track
    stats = {
        'total_fights': 0,
        'wins': 0,
        'losses': 0,
        'draws': 0,
        'total_turns': 0,
        'turns_in_wins': 0,
        'turns_in_losses': 0,
        'opponents': defaultdict(lambda: {'count': 0, 'wins': 0, 'losses': 0, 'draws': 0}),
        'error_patterns': defaultdict(int),
        'panic_mode_activations': 0,
        'fights_with_errors': 0,
        'common_errors': defaultdict(int)
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
        
        # Determine result
        if winner == 0:
            stats['draws'] += 1
            stats['opponents'][opponent_name]['draws'] += 1
        elif winner == virus_team:
            stats['wins'] += 1
            stats['opponents'][opponent_name]['wins'] += 1
        else:
            stats['losses'] += 1
            stats['opponents'][opponent_name]['losses'] += 1
        
        # Get turn count - we'll estimate from logs or use a default
        # Since the report structure is different, we'll check the logs for turn info
        turns = 0  # Will be updated from logs if available
        
        # Analyze logs if available
        if os.path.exists(logs_file):
            with open(logs_file, 'r') as f:
                logs_data = json.load(f)
            
            if logs_data and isinstance(logs_data, list):
                has_errors = False
                max_turn = 0
                for log_entry in logs_data:
                    if isinstance(log_entry, list) and len(log_entry) >= 4:
                        leek_id = log_entry[0]
                        log_type = log_entry[1]
                        message = log_entry[2]
                        
                        # Track turn number (4th element if present)
                        if len(log_entry) > 3:
                            turn_num = log_entry[3]
                            if isinstance(turn_num, int) and turn_num > max_turn:
                                max_turn = turn_num
                        
                        # Check for errors (type 4 is error, 5 is warning)
                        if log_type in [4, 5]:
                            has_errors = True
                            if isinstance(message, str):
                                # Extract error type
                                if "PANIC MODE" in message:
                                    stats['panic_mode_activations'] += 1
                                elif "No A* path found" in message:
                                    stats['common_errors']['No A* path found'] += 1
                                elif "UNKNOWN_VARIABLE" in message:
                                    stats['common_errors']['UNKNOWN_VARIABLE'] += 1
                                elif "operations" in message.lower():
                                    stats['common_errors']['Operation limit'] += 1
                                else:
                                    stats['common_errors']['Other'] += 1
                
                if has_errors:
                    stats['fights_with_errors'] += 1
                
                # Update turn count
                if max_turn > 0:
                    turns = max_turn
                    stats['total_turns'] += turns
                    
                    if winner == virus_team:
                        stats['turns_in_wins'] += turns
                    elif winner != 0:
                        stats['turns_in_losses'] += turns
    
    # Print analysis
    print("="*60)
    print("FIGHT ANALYSIS REPORT - 200 FIGHTS")
    print("="*60)
    
    win_rate = (stats['wins'] / stats['total_fights'] * 100) if stats['total_fights'] > 0 else 0
    print(f"\n📊 Overall Statistics:")
    print(f"   Total Fights: {stats['total_fights']}")
    print(f"   Wins: {stats['wins']} ({win_rate:.1f}%)")
    print(f"   Losses: {stats['losses']} ({stats['losses']/stats['total_fights']*100:.1f}%)")
    print(f"   Draws: {stats['draws']} ({stats['draws']/stats['total_fights']*100:.1f}%)")
    
    avg_turns = stats['total_turns'] / stats['total_fights'] if stats['total_fights'] > 0 else 0
    avg_turns_win = stats['turns_in_wins'] / stats['wins'] if stats['wins'] > 0 else 0
    avg_turns_loss = stats['turns_in_losses'] / stats['losses'] if stats['losses'] > 0 else 0
    
    print(f"\n⏱️ Turn Statistics:")
    print(f"   Average turns per fight: {avg_turns:.1f}")
    print(f"   Average turns in wins: {avg_turns_win:.1f}")
    print(f"   Average turns in losses: {avg_turns_loss:.1f}")
    
    print(f"\n⚠️ Error Analysis:")
    print(f"   Fights with errors: {stats['fights_with_errors']} ({stats['fights_with_errors']/stats['total_fights']*100:.1f}%)")
    print(f"   Panic mode activations: {stats['panic_mode_activations']}")
    
    if stats['common_errors']:
        print(f"\n   Common errors:")
        for error_type, count in sorted(stats['common_errors'].items(), key=lambda x: x[1], reverse=True):
            print(f"     - {error_type}: {count} occurrences")
    
    print(f"\n🎯 Top Opponents Faced:")
    top_opponents = sorted(stats['opponents'].items(), key=lambda x: x[1]['count'], reverse=True)[:10]
    for opp_name, opp_stats in top_opponents:
        total = opp_stats['count']
        wins = opp_stats['wins']
        win_rate_vs = (wins / total * 100) if total > 0 else 0
        print(f"   {opp_name}: {total} fights, {wins}W/{opp_stats['losses']}L/{opp_stats['draws']}D ({win_rate_vs:.1f}% win rate)")
    
    print(f"\n✅ Summary:")
    print(f"   - Overall win rate: {win_rate:.1f}%")
    print(f"   - Average fight duration: {avg_turns:.1f} turns")
    print(f"   - Panic mode usage: {stats['panic_mode_activations']/stats['total_fights']*100:.1f}% of fights")
    print(f"   - Error rate: {stats['fights_with_errors']/stats['total_fights']*100:.1f}% of fights had errors")

if __name__ == "__main__":
    analyze_fights()