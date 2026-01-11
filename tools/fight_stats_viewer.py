#!/usr/bin/env python3
"""
Fight Statistics Viewer - View detailed stats from fight database
Usage: python3 fight_stats_viewer.py <leek_id>
"""

import sys
import os
from fight_db import FightDatabase
from datetime import datetime

def format_timestamp(ts_str):
    """Format timestamp for display"""
    if not ts_str:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return ts_str

def display_stats(leek_id):
    """Display comprehensive fight statistics"""
    db_path = f"fight_history_{leek_id}.db"

    if not os.path.exists(db_path):
        print(f"❌ No database found for leek ID {leek_id}")
        print(f"   Expected: {db_path}")
        return

    print("="*70)
    print(f"FIGHT STATISTICS - LEEK ID {leek_id}")
    print("="*70)

    db = FightDatabase(leek_id)

    # Get leek info
    db.cursor.execute('SELECT * FROM leek_info WHERE leek_id = ?', (leek_id,))
    leek_info = db.cursor.fetchone()
    if leek_info:
        print(f"\n🥬 Leek: {leek_info['leek_name']} (Level {leek_info['leek_level']})")
        print(f"   Last updated: {format_timestamp(leek_info['last_updated'])}")

    # Global stats
    stats = db.get_global_stats()
    print(f"\n📊 OVERALL STATISTICS")
    print(f"   Total fights: {stats['total_fights']}")
    if stats['total_fights'] > 0:
        print(f"   Win rate: {stats['win_rate']:.1%}")
        print(f"   Opponents tracked: {stats['opponents_tracked']}")
        print(f"   🟢 Beatable: {stats['beatable_opponents']}")
        print(f"   🔴 Dangerous: {stats['dangerous_opponents']}")

    # Recent fights
    print(f"\n📜 RECENT FIGHTS (Last 10)")
    print("-" * 70)
    db.cursor.execute('''
        SELECT * FROM fight_history
        ORDER BY timestamp DESC LIMIT 10
    ''')
    recent_fights = db.cursor.fetchall()

    if recent_fights:
        for fight in recent_fights:
            result_icon = {"WIN": "✅", "LOSS": "❌", "DRAW": "🤝"}.get(fight['result'], "❓")
            duration = fight['duration'] if fight['duration'] else "N/A"
            print(f"{result_icon} {fight['result']:<4} vs {fight['opponent_name']:<20} L{fight['opponent_level']} "
                  f"(Duration: {duration}, Actions: {fight['actions_count']})")
            print(f"   {format_timestamp(fight['timestamp'])} - {fight['fight_url']}")
    else:
        print("   No fights recorded yet")

    # Top opponents (by number of fights)
    print(f"\n🎯 MOST FOUGHT OPPONENTS")
    print("-" * 70)
    db.cursor.execute('''
        SELECT * FROM opponent_stats
        ORDER BY total_fights DESC LIMIT 10
    ''')
    top_opponents = db.cursor.fetchall()

    if top_opponents:
        for i, opp in enumerate(top_opponents, 1):
            status_icons = {
                'beatable': '🟢',
                'dangerous': '🔴',
                'even': '🟡',
                'unknown': '⚪'
            }
            stats = db.get_opponent_stats(opp['opponent_id'])
            icon = status_icons.get(stats['status'], '⚪')
            difficulty = db.calculate_opponent_difficulty(opp['opponent_id'])

            print(f"{i:>2}. {icon} {opp['opponent_name']:<25} L{opp['opponent_level']} → "
                  f"{opp['wins']}W-{opp['losses']}L-{opp['draws']}D "
                  f"({opp['win_rate']:.0%}, {opp['total_fights']} fights, diff:{difficulty})")
            print(f"    Last fought: {format_timestamp(opp['last_fought'])}")
    else:
        print("   No opponent data yet")

    # Best matchups
    print(f"\n🟢 BEST MATCHUPS (Win rate ≥ 70%, min 3 fights)")
    print("-" * 70)
    db.cursor.execute('''
        SELECT * FROM opponent_stats
        WHERE win_rate >= 0.7 AND total_fights >= 3
        ORDER BY win_rate DESC, total_fights DESC
        LIMIT 10
    ''')
    best_matchups = db.cursor.fetchall()

    if best_matchups:
        for i, opp in enumerate(best_matchups, 1):
            difficulty = db.calculate_opponent_difficulty(opp['opponent_id'])
            print(f"{i:>2}. {opp['opponent_name']:<25} L{opp['opponent_level']} → "
                  f"{opp['wins']}W-{opp['losses']}L-{opp['draws']}D "
                  f"({opp['win_rate']:.0%}, diff:{difficulty})")
    else:
        print("   No strong matchups yet (need more fights)")

    # Worst matchups
    print(f"\n🔴 WORST MATCHUPS (Win rate ≤ 30%, min 3 fights)")
    print("-" * 70)
    db.cursor.execute('''
        SELECT * FROM opponent_stats
        WHERE win_rate <= 0.3 AND total_fights >= 3
        ORDER BY win_rate ASC, total_fights DESC
        LIMIT 10
    ''')
    worst_matchups = db.cursor.fetchall()

    if worst_matchups:
        for i, opp in enumerate(worst_matchups, 1):
            difficulty = db.calculate_opponent_difficulty(opp['opponent_id'])
            print(f"{i:>2}. {opp['opponent_name']:<25} L{opp['opponent_level']} → "
                  f"{opp['wins']}W-{opp['losses']}L-{opp['draws']}D "
                  f"({opp['win_rate']:.0%}, diff:{difficulty})")
    else:
        print("   No problematic matchups yet")

    db.close()
    print("\n" + "="*70)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 fight_stats_viewer.py <leek_id>")
        print("\nExample: python3 fight_stats_viewer.py 123456")
        sys.exit(1)

    try:
        leek_id = int(sys.argv[1])
        display_stats(leek_id)
    except ValueError:
        print("❌ Invalid leek ID - must be a number")
        sys.exit(1)
