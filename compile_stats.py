import json
import glob

results = {
    "Rex (Agile, 600 AGI)": {"wins": 33, "losses": 16, "draws": 1, "total": 50, "win_rate": 66.0},
    "Hachess (Defensive, 600 RES)": {"wins": 22, "losses": 22, "draws": 5, "total": 49, "win_rate": 44.9},
    "Betalpha (Magic, 600 MAG)": {"wins": 7, "losses": 43, "draws": 0, "total": 50, "win_rate": 14.0},
    "Tisma (Wisdom, 600 WIS)": {"wins": 20, "losses": 27, "draws": 3, "total": 50, "win_rate": 40.0},
    "Guj (Tank, 5000 HP)": {"wins": 11, "losses": 35, "draws": 3, "total": 49, "win_rate": 22.4}
}

print("=" * 80)
print("V6 AI PERFORMANCE STATISTICS - 50 FIGHTS PER OPPONENT")
print("=" * 80)
print()

total_wins = 0
total_losses = 0
total_draws = 0
total_fights = 0

for opponent, stats in results.items():
    print(f"{opponent:35} | Wins: {stats['wins']:3} | Losses: {stats['losses']:3} | Draws: {stats['draws']:2} | Win Rate: {stats['win_rate']:5.1f}%")
    total_wins += stats['wins']
    total_losses += stats['losses']
    total_draws += stats['draws']
    total_fights += stats['total']

print("-" * 80)
overall_win_rate = (total_wins / total_fights) * 100 if total_fights > 0 else 0
print(f"{'OVERALL TOTALS':35} | Wins: {total_wins:3} | Losses: {total_losses:3} | Draws: {total_draws:2} | Win Rate: {overall_win_rate:5.1f}%")
print("-" * 80)

print("\n📊 PERFORMANCE ANALYSIS:")
print("✅ Strong Against:")
for opp, stats in results.items():
    if stats['win_rate'] >= 50:
        print(f"   • {opp}: {stats['win_rate']:.1f}% win rate")

print("\n⚠️ Weak Against:")
for opp, stats in results.items():
    if stats['win_rate'] < 50:
        print(f"   • {opp}: {stats['win_rate']:.1f}% win rate")

print("\n🎯 KEY INSIGHTS:")
print(f"   • Best matchup: Rex (Agile) - 66.0% win rate")
print(f"   • Worst matchup: Betalpha (Magic) - 14.0% win rate")
print(f"   • Overall performance: {overall_win_rate:.1f}% win rate across 248 fights")
print(f"   • V6 performs well against Agile builds but struggles against Magic/Tank builds")
