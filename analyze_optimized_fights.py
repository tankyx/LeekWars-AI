#!/usr/bin/env python3

import json
import os
import glob
from datetime import datetime

def analyze_optimized_fights():
    fight_dir = "/home/ubuntu/LeekWars-AI/fight_logs/129288/"
    data_files = glob.glob(os.path.join(fight_dir, "*_data.json"))
    
    # Sort by modification time to get recent fights first
    data_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    print("🎯 EbolaLeek Operation Usage Analysis - Recent Fights")
    print("=" * 60)
    
    recent_fights = []
    old_fights = []
    
    # Get file modification times to separate before/after optimization
    optimization_time = datetime.fromtimestamp(1725896280)  # Approximate optimization time
    
    for data_file in data_files[:20]:  # Analyze most recent 20 fights
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
            
            # Get file modification time
            mod_time = datetime.fromtimestamp(os.path.getmtime(data_file))
            
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
                
                fight_info = {
                    'file': os.path.basename(data_file),
                    'ops': ops,
                    'won': not ebolaleek_dead,
                    'time': mod_time
                }
                
                if mod_time > optimization_time:
                    recent_fights.append(fight_info)
                else:
                    old_fights.append(fight_info)
                    
        except Exception as e:
            print(f"Error processing {data_file}: {e}")
    
    # Analyze recent fights (post-optimization)
    if recent_fights:
        recent_ops = [f['ops'] for f in recent_fights]
        recent_wins = sum(1 for f in recent_fights if f['won'])
        
        print(f"📈 POST-OPTIMIZATION FIGHTS ({len(recent_fights)} fights)")
        print(f"✅ Wins: {recent_wins}/{len(recent_fights)} ({recent_wins/len(recent_fights)*100:.1f}%)")
        print(f"⚡ Average Operations: {sum(recent_ops)/len(recent_ops):,.0f}")
        print(f"📊 Operation Range: {min(recent_ops):,} - {max(recent_ops):,}")
        print(f"🎯 Usage vs 7M Budget: {sum(recent_ops)/len(recent_ops)/7000000*100:.1f}%")
        
        print(f"\n📊 Individual Fight Breakdown:")
        for fight in recent_fights[:10]:  # Show top 10 recent
            status = "✅ WIN" if fight['won'] else "❌ LOSS"
            print(f"  {fight['file'][:12]}: {fight['ops']:>8,} ops - {status}")
    
    # Analyze old fights (pre-optimization) for comparison
    if old_fights:
        old_ops = [f['ops'] for f in old_fights]
        old_wins = sum(1 for f in old_fights if f['won'])
        
        print(f"\n📉 PRE-OPTIMIZATION BASELINE ({len(old_fights)} fights)")
        print(f"✅ Wins: {old_wins}/{len(old_fights)} ({old_wins/len(old_fights)*100:.1f}%)")
        print(f"⚡ Average Operations: {sum(old_ops)/len(old_ops):,.0f}")
        print(f"📊 Operation Range: {min(old_ops):,} - {max(old_ops):,}")
        print(f"🎯 Usage vs 7M Budget: {sum(old_ops)/len(old_ops)/7000000*100:.1f}%")
    
    # Calculate improvement
    if recent_fights and old_fights:
        recent_avg = sum(f['ops'] for f in recent_fights) / len(recent_fights)
        old_avg = sum(f['ops'] for f in old_fights) / len(old_fights)
        improvement = (recent_avg / old_avg)
        
        print(f"\n🚀 OPTIMIZATION IMPACT:")
        print(f"📈 Operation Usage Increase: {improvement:.1f}x")
        print(f"💫 Additional Operations per Fight: {recent_avg - old_avg:+,.0f}")

if __name__ == "__main__":
    analyze_optimized_fights()