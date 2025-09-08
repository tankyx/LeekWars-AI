#!/usr/bin/env python3
"""
Analyze V6 AI combat logs to identify performance issues
"""

import json
import glob
import re
from collections import defaultdict, Counter

def analyze_fight_logs(log_file):
    """Analyze a single fight log file"""
    with open(log_file, 'r') as f:
        data = json.load(f)
    
    opponent = data.get('opponent', 'Unknown')
    results = []
    
    for fight in data.get('fights', []):
        fight_result = {
            'result': fight['result'],
            'fight_id': fight['fight_id'],
            'issues': [],
            'turn_count': 0,
            'damage_dealt': 0,
            'damage_taken': 0,
            'tp_usage': [],
            'failed_attacks': 0,
            'panic_mode': False,
            'teleports': 0
        }
        
        logs = fight.get('logs', [])
        current_turn = 0
        
        for log in logs:
            if isinstance(log, dict):
                msg = str(log.get('message', ''))
            else:
                continue
            
            # Track turn count
            if 'Turn' in msg and 'initialized' in msg:
                turn_match = re.search(r'Turn (\d+)', msg)
                if turn_match:
                    current_turn = int(turn_match.group(1))
                    fight_result['turn_count'] = max(fight_result['turn_count'], current_turn)
            
            # Check for common issues
            if 'PANIC MODE' in msg:
                fight_result['panic_mode'] = True
                fight_result['issues'].append(f"Panic mode at turn {current_turn}")
            
            if 'No A* path found' in msg:
                fight_result['issues'].append(f"Pathfinding failed at turn {current_turn}")
            
            if 'FLEE TELEPORT' in msg or 'EMERGENCY TELEPORT' in msg:
                fight_result['teleports'] += 1
                fight_result['issues'].append(f"Emergency teleport at turn {current_turn}")
            
            if 'AGGRESSIVE TELEPORT' in msg or 'KILL TELEPORT' in msg:
                fight_result['teleports'] += 1
            
            if 'Cannot attack' in msg or 'No valid targets' in msg:
                fight_result['failed_attacks'] += 1
            
            if 'damage dealt:' in msg:
                dmg_match = re.search(r'damage dealt: (\d+)', msg)
                if dmg_match:
                    fight_result['damage_dealt'] += int(dmg_match.group(1))
            
            if 'lost' in msg and 'HP' in msg:
                hp_match = re.search(r'lost (\d+) HP', msg)
                if hp_match:
                    fight_result['damage_taken'] += int(hp_match.group(1))
            
            # Track TP usage
            if 'TP:' in msg:
                tp_match = re.search(r'TP: (\d+)', msg)
                if tp_match:
                    fight_result['tp_usage'].append(int(tp_match.group(1)))
        
        results.append(fight_result)
    
    return opponent, results

def main():
    # Find all log files
    log_files = glob.glob('fight_logs_445497_*.json')
    
    all_results = {}
    issue_counter = Counter()
    
    for log_file in log_files:
        # Extract opponent from filename
        match = re.search(r'fight_logs_445497_([^_]+)_', log_file)
        if match:
            opponent = match.group(1)
            _, results = analyze_fight_logs(log_file)
            if opponent not in all_results:
                all_results[opponent] = []
            all_results[opponent].extend(results)
    
    # Analyze results
    print("="*60)
    print("V6 AI COMBAT LOG ANALYSIS")
    print("="*60)
    
    for opponent, fights in all_results.items():
        wins = sum(1 for f in fights if f['result'] == 'WIN')
        losses = sum(1 for f in fights if f['result'] == 'LOSS')
        total = len(fights)
        
        if total == 0:
            continue
            
        win_rate = (wins / total) * 100
        
        print(f"\n{opponent.upper()} - {total} fights")
        print(f"  Win Rate: {win_rate:.1f}% ({wins}W/{losses}L)")
        
        # Analyze losses
        loss_fights = [f for f in fights if f['result'] == 'LOSS']
        if loss_fights:
            avg_turns = sum(f['turn_count'] for f in loss_fights) / len(loss_fights)
            panic_count = sum(1 for f in loss_fights if f['panic_mode'])
            teleport_avg = sum(f['teleports'] for f in loss_fights) / len(loss_fights)
            
            print(f"  Loss Analysis:")
            print(f"    Avg turns survived: {avg_turns:.1f}")
            print(f"    Panic mode triggered: {panic_count}/{len(loss_fights)} ({panic_count/len(loss_fights)*100:.0f}%)")
            print(f"    Avg teleports: {teleport_avg:.1f}")
            
            # Common issues in losses
            all_issues = []
            for f in loss_fights:
                all_issues.extend(f['issues'])
            
            if all_issues:
                issue_freq = Counter(all_issues)
                print(f"    Common issues:")
                for issue, count in issue_freq.most_common(3):
                    print(f"      - {issue}: {count} times")
    
    # Overall patterns
    print("\n" + "="*60)
    print("OVERALL PATTERNS")
    print("="*60)
    
    all_fights = []
    for fights in all_results.values():
        all_fights.extend(fights)
    
    wins = [f for f in all_fights if f['result'] == 'WIN']
    losses = [f for f in all_fights if f['result'] == 'LOSS']
    
    if wins:
        avg_win_turns = sum(f['turn_count'] for f in wins) / len(wins)
        print(f"Average turns in wins: {avg_win_turns:.1f}")
    
    if losses:
        avg_loss_turns = sum(f['turn_count'] for f in losses) / len(losses)
        panic_rate = sum(1 for f in losses if f['panic_mode']) / len(losses) * 100
        print(f"Average turns in losses: {avg_loss_turns:.1f}")
        print(f"Panic mode in losses: {panic_rate:.1f}%")
    
    # Key findings
    print("\n" + "="*60)
    print("KEY FINDINGS")
    print("="*60)
    
    print("1. Performance Summary:")
    for opponent in ['rex', 'hachess', 'betalpha', 'tisma', 'guj', 'domingo']:
        if opponent in all_results:
            fights = all_results[opponent]
            if fights:
                wins = sum(1 for f in fights if f['result'] == 'WIN')
                win_rate = (wins / len(fights)) * 100
                print(f"   {opponent:10} : {win_rate:5.1f}% win rate")

if __name__ == "__main__":
    main()