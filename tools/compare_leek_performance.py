#!/usr/bin/env python3

import json
import os
import glob
from collections import defaultdict

def analyze_leek_logs(log_directory, leek_name):
    """Analyze fight logs for a specific leek"""
    print(f"\n🥬 Analyzing {leek_name} logs from {log_directory}")
    
    # Get all data files (contain fight results)
    data_files = glob.glob(os.path.join(log_directory, "*_data.json"))
    
    if not data_files:
        print(f"   ❌ No data files found in {log_directory}")
        return None
    
    wins = 0
    losses = 0
    draws = 0
    total_damage_dealt = 0
    total_damage_taken = 0
    survival_turns = []
    weapon_usage = defaultdict(int)
    errors = 0
    
    for data_file in data_files:
        try:
            with open(data_file, 'r') as f:
                fight_data = json.load(f)
            
            # Determine winner
            winner = fight_data.get('winner', 0)
            if winner == 1:
                wins += 1
            elif winner == 2:
                losses += 1
            else:
                draws += 1
            
            # Get leek stats
            leeks = fight_data.get('leeks', [])
            if len(leeks) >= 2:
                my_leek = leeks[0]  # First leek should be ours
                enemy_leek = leeks[1]
                
                # Calculate damage dealt/taken
                my_initial_life = my_leek.get('life', 0)
                my_final_life = my_leek.get('life_end', 0)
                enemy_initial_life = enemy_leek.get('life', 0) 
                enemy_final_life = enemy_leek.get('life_end', 0)
                
                damage_dealt = enemy_initial_life - enemy_final_life
                damage_taken = my_initial_life - my_final_life
                
                total_damage_dealt += damage_dealt
                total_damage_taken += damage_taken
                
                # Count survival turns
                turns = fight_data.get('turn', 0)
                survival_turns.append(turns)
                
                # Check for weapons used (from my_leek)
                weapons = my_leek.get('weapons', [])
                for weapon in weapons:
                    weapon_usage[weapon] += 1
        
        except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            errors += 1
            continue
    
    total_fights = wins + losses + draws
    win_rate = (wins / total_fights * 100) if total_fights > 0 else 0
    avg_survival = sum(survival_turns) / len(survival_turns) if survival_turns else 0
    avg_damage_dealt = total_damage_dealt / total_fights if total_fights > 0 else 0
    avg_damage_taken = total_damage_taken / total_fights if total_fights > 0 else 0
    
    results = {
        'leek_name': leek_name,
        'total_fights': total_fights,
        'wins': wins,
        'losses': losses,
        'draws': draws,
        'win_rate': win_rate,
        'avg_survival_turns': avg_survival,
        'avg_damage_dealt': avg_damage_dealt,
        'avg_damage_taken': avg_damage_taken,
        'weapon_usage': dict(weapon_usage),
        'errors': errors
    }
    
    print(f"   📊 Results: {wins}W-{losses}L-{draws}D ({win_rate:.1f}% win rate)")
    print(f"   ⏱️ Average survival: {avg_survival:.1f} turns")
    print(f"   🗡️ Damage dealt: {avg_damage_dealt:.0f} per fight")
    print(f"   🛡️ Damage taken: {avg_damage_taken:.0f} per fight")
    
    return results

def main():
    print("============================================================")
    print("LEEK PERFORMANCE COMPARISON")
    print("============================================================")
    
    # Define leeks to analyze
    leeks_to_analyze = [
        ("fight_logs/129288/", "EbolaLeek (B_LASER/MAGNUM/GRENADE)"),
        ("fight_logs/129295/", "RabiesLeek (DESTROYER/NEUTRINO/LASER)"), 
        ("fight_logs/129296/", "SmallpoxLeek (DESTROYER/NEUTRINO/LASER)")
    ]
    
    all_results = []
    
    for log_dir, leek_name in leeks_to_analyze:
        if os.path.exists(log_dir):
            result = analyze_leek_logs(log_dir, leek_name)
            if result:
                all_results.append(result)
        else:
            print(f"❌ Directory not found: {log_dir}")
    
    # Comparison table
    if all_results:
        print(f"\n📋 PERFORMANCE COMPARISON SUMMARY")
        print("=" * 80)
        print(f"{'Leek':<35} {'Win Rate':<10} {'Avg Turns':<10} {'Dmg Dealt':<10} {'Dmg Taken':<10}")
        print("-" * 80)
        
        for result in all_results:
            leek_name = result['leek_name'].split(' (')[0]  # Remove weapon loadout from name
            win_rate = f"{result['win_rate']:.1f}%"
            avg_turns = f"{result['avg_survival_turns']:.1f}"
            dmg_dealt = f"{result['avg_damage_dealt']:.0f}"
            dmg_taken = f"{result['avg_damage_taken']:.0f}"
            
            print(f"{leek_name:<35} {win_rate:<10} {avg_turns:<10} {dmg_dealt:<10} {dmg_taken:<10}")
        
        # Best performer analysis
        best_win_rate = max(all_results, key=lambda x: x['win_rate'])
        best_survival = max(all_results, key=lambda x: x['avg_survival_turns'])
        best_damage = max(all_results, key=lambda x: x['avg_damage_dealt'])
        
        print(f"\n🏆 PERFORMANCE LEADERS:")
        print(f"   🥇 Highest Win Rate: {best_win_rate['leek_name'].split('(')[0].strip()} ({best_win_rate['win_rate']:.1f}%)")
        print(f"   🛡️ Best Survival: {best_survival['leek_name'].split('(')[0].strip()} ({best_survival['avg_survival_turns']:.1f} turns)")
        print(f"   ⚔️ Highest Damage: {best_damage['leek_name'].split('(')[0].strip()} ({best_damage['avg_damage_dealt']:.0f} dmg/fight)")
        
        # Weapon loadout analysis
        print(f"\n🔫 WEAPON LOADOUT ANALYSIS:")
        for result in all_results:
            weapons = result['weapon_usage']
            if weapons:
                leek_name = result['leek_name'].split(' (')[0]
                print(f"   {leek_name}: {list(weapons.keys())}")
        
        # Save detailed results
        with open('leek_performance_comparison.json', 'w') as f:
            json.dump(all_results, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: leek_performance_comparison.json")

if __name__ == "__main__":
    main()