#!/usr/bin/env python3

import json
import os
import glob
from datetime import datetime

def analyze_ops_per_turn():
    fight_dir = "/home/ubuntu/LeekWars-AI/fight_logs/129288/"
    data_files = glob.glob(os.path.join(fight_dir, "*_data.json"))
    
    # Sort by modification time to get recent fights first
    data_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    print("🎯 EbolaLeek Operations Per Turn Analysis")
    print("=" * 70)
    
    fight_analysis = []
    
    for data_file in data_files[:25]:  # Analyze most recent 25 fights
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
            
            # Find EbolaLeek in the fight results
            ebolaleek_dead = None
            for leek in data['report']['leeks1']:
                if leek['id'] == 129288:  # EbolaLeek ID
                    ebolaleek_dead = leek['dead']
                    break
            
            if ebolaleek_dead is not None:
                # Get operation count for EbolaLeek (player 0)
                ops = 0
                if '0' in data['data']['ops']:
                    ops = data['data']['ops']['0']
                
                # Calculate fight duration (turns)
                # The fight duration is in the report
                duration = data['report']['duration'] if 'duration' in data['report'] else 0
                
                if duration > 0:
                    ops_per_turn = ops / duration
                    
                    fight_info = {
                        'file': os.path.basename(data_file)[:12],
                        'ops': ops,
                        'turns': duration,
                        'ops_per_turn': ops_per_turn,
                        'won': not ebolaleek_dead,
                        'ops_percentage': ops_per_turn / 7000000 * 100  # vs 7M budget per turn
                    }
                    fight_analysis.append(fight_info)
                    
        except Exception as e:
            print(f"Error processing {data_file}: {e}")
    
    if not fight_analysis:
        print("No fights found for analysis")
        return
    
    # Sort by ops per turn for analysis
    fight_analysis.sort(key=lambda x: x['ops_per_turn'], reverse=True)
    
    print(f"📊 OPERATIONS PER TURN ANALYSIS ({len(fight_analysis)} fights)")
    print("=" * 70)
    
    # Calculate statistics
    ops_per_turn_values = [f['ops_per_turn'] for f in fight_analysis]
    avg_ops_per_turn = sum(ops_per_turn_values) / len(ops_per_turn_values)
    max_ops_per_turn = max(ops_per_turn_values)
    min_ops_per_turn = min(ops_per_turn_values)
    avg_percentage = avg_ops_per_turn / 7000000 * 100
    
    print(f"📈 Average Ops/Turn: {avg_ops_per_turn:,.0f} ({avg_percentage:.1f}% of 7M budget)")
    print(f"🔥 Maximum Ops/Turn: {max_ops_per_turn:,.0f} ({max_ops_per_turn/7000000*100:.1f}% of budget)")
    print(f"📉 Minimum Ops/Turn: {min_ops_per_turn:,.0f} ({min_ops_per_turn/7000000*100:.1f}% of budget)")
    print()
    
    # Performance correlation analysis
    wins = [f for f in fight_analysis if f['won']]
    losses = [f for f in fight_analysis if not f['won']]
    
    if wins:
        avg_win_ops = sum(f['ops_per_turn'] for f in wins) / len(wins)
        print(f"✅ WINS ({len(wins)} fights): Avg {avg_win_ops:,.0f} ops/turn ({avg_win_ops/7000000*100:.1f}%)")
    
    if losses:
        avg_loss_ops = sum(f['ops_per_turn'] for f in losses) / len(losses)
        print(f"❌ LOSSES ({len(losses)} fights): Avg {avg_loss_ops:,.0f} ops/turn ({avg_loss_ops/7000000*100:.1f}%)")
    
    if wins and losses:
        correlation = avg_win_ops / avg_loss_ops if avg_loss_ops > 0 else 1
        print(f"📊 Win/Loss Ops Ratio: {correlation:.2f}x")
    
    print()
    print("🔥 TOP OPERATION USAGE FIGHTS:")
    print("-" * 70)
    print(f"{'Fight ID':<12} {'Total Ops':<12} {'Turns':<6} {'Ops/Turn':<12} {'Usage %':<8} {'Result'}")
    print("-" * 70)
    
    for fight in fight_analysis[:15]:  # Top 15 fights
        status = "WIN" if fight['won'] else "LOSS"
        print(f"{fight['file']:<12} {fight['ops']:<12,} {fight['turns']:<6} {fight['ops_per_turn']:<12,.0f} {fight['ops_percentage']:<7.1f}% {status}")
    
    # Usage distribution analysis
    print()
    print("📊 OPERATION USAGE DISTRIBUTION:")
    print("-" * 40)
    
    usage_ranges = [
        (0, 20, "Very Low (0-20%)"),
        (20, 40, "Low (20-40%)"),
        (40, 60, "Medium (40-60%)"),
        (60, 80, "High (60-80%)"),
        (80, 100, "Very High (80-100%)"),
        (100, 200, "Extreme (100-200%)"),
        (200, 1000, "Ultra (200%+)")
    ]
    
    for min_pct, max_pct, label in usage_ranges:
        count = sum(1 for f in fight_analysis if min_pct <= f['ops_percentage'] < max_pct)
        if count > 0:
            print(f"{label:<20}: {count:>3} fights ({count/len(fight_analysis)*100:.1f}%)")
    
    # Best performing ops/turn range
    print()
    print("🎯 PERFORMANCE BY OPERATION USAGE:")
    print("-" * 50)
    
    high_ops_fights = [f for f in fight_analysis if f['ops_percentage'] >= 80]
    medium_ops_fights = [f for f in fight_analysis if 40 <= f['ops_percentage'] < 80]
    low_ops_fights = [f for f in fight_analysis if f['ops_percentage'] < 40]
    
    for category, fights, label in [
        (high_ops_fights, high_ops_fights, "High Usage (80%+)"),
        (medium_ops_fights, medium_ops_fights, "Medium Usage (40-80%)"),
        (low_ops_fights, low_ops_fights, "Low Usage (<40%)")
    ]:
        if fights:
            wins = sum(1 for f in fights if f['won'])
            win_rate = wins / len(fights) * 100
            avg_ops = sum(f['ops_per_turn'] for f in fights) / len(fights)
            print(f"{label:<18}: {len(fights):>2} fights, {win_rate:>5.1f}% win rate, avg {avg_ops:>8,.0f} ops/turn")

if __name__ == "__main__":
    analyze_ops_per_turn()