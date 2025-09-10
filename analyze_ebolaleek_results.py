#!/usr/bin/env python3

import json
import os
import glob

def analyze_ebolaleek_fights():
    fight_dir = "/home/ubuntu/LeekWars-AI/fight_logs/129288/"
    data_files = glob.glob(os.path.join(fight_dir, "*_data.json"))
    
    wins = 0
    losses = 0
    total_ops = 0
    fight_count = 0
    operation_samples = []
    
    for data_file in data_files:
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
                fight_count += 1
                if ebolaleek_dead:
                    losses += 1
                else:
                    wins += 1
                
                # Get operation count for EbolaLeek (player 0)
                if '0' in data['data']['ops']:
                    ops = data['data']['ops']['0']
                    total_ops += ops
                    operation_samples.append(ops)
                    
        except Exception as e:
            print(f"Error processing {data_file}: {e}")
    
    win_rate = (wins / fight_count * 100) if fight_count > 0 else 0
    avg_ops = total_ops / fight_count if fight_count > 0 else 0
    
    print(f"🎯 EbolaLeek Fight Analysis (100 Fights)")
    print(f"=" * 50)
    print(f"✅ Wins: {wins}")
    print(f"❌ Losses: {losses}")  
    print(f"📊 Total Fights: {fight_count}")
    print(f"🏆 Win Rate: {win_rate:.1f}%")
    print(f"")
    print(f"⚡ Operation Usage Analysis:")
    print(f"📈 Average Operations: {avg_ops:,.0f}")
    print(f"💡 Operations Range: {min(operation_samples):,} - {max(operation_samples):,}")
    print(f"🎯 Target Budget: 7,000,000 operations")
    print(f"📊 Usage Percentage: {(avg_ops / 7000000 * 100):.1f}%")
    
    # Operation usage distribution
    if len(operation_samples) >= 5:
        operation_samples.sort()
        print(f"")
        print(f"Operation Usage Quartiles:")
        print(f"• Q1 (25%): {operation_samples[len(operation_samples)//4]:,}")
        print(f"• Q2 (50%): {operation_samples[len(operation_samples)//2]:,}")
        print(f"• Q3 (75%): {operation_samples[3*len(operation_samples)//4]:,}")

if __name__ == "__main__":
    analyze_ebolaleek_fights()