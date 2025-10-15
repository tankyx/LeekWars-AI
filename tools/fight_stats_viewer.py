#!/usr/bin/env python3
"""
Fight Statistics Viewer
View and analyze fight statistics from database
"""

import sys
import argparse
from fight_db import FightDatabase
from datetime import datetime

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(title.center(60))
    print("="*60)

def print_global_stats(db):
    """Display global statistics"""
    stats = db.get_global_stats()

    print_header("GLOBAL STATISTICS")
    print(f"Total fights: {stats['total_fights']}")
    if stats['total_fights'] > 0:
        print(f"Win rate: {stats['win_rate']:.1%}")
        print(f"Wins: {stats['wins']}")
        print(f"Losses: {stats['losses']}")
        print(f"Draws: {stats['draws']}")
        print(f"\nOpponents tracked: {stats['opponents_tracked']}")
        print(f"🟢 Beatable opponents: {stats['beatable_opponents']}")
        print(f"🔴 Dangerous opponents: {stats['dangerous_opponents']}")
    else:
        print("No fights recorded yet")

def print_opponent_list(db, status=None, limit=20):
    """Display list of opponents with stats"""
    opponents = db.get_all_opponent_stats(status)

    if status:
        print_header(f"{status.upper()} OPPONENTS")
    else:
        print_header("ALL OPPONENTS")

    if not opponents:
        print("No opponents found")
        return

    # Limit display
    display_opponents = opponents[:limit]

    print(f"\n{'Rank':<5} {'Name':<20} {'Level':<6} {'W-L-D':<12} {'Win Rate':<10} {'Difficulty':<10} {'Status':<10}")
    print("-" * 90)

    for idx, opp in enumerate(display_opponents, 1):
        name = opp['name'][:18]
        level = opp.get('level', '?')
        wins = opp['wins']
        losses = opp['losses']
        draws = opp['draws']
        wld = f"{wins}-{losses}-{draws}"
        win_rate = f"{opp['win_rate']:.1%}"
        difficulty = db.calculate_opponent_difficulty(opp['opponent_id'])
        status_icon = {'beatable': '🟢', 'dangerous': '🔴', 'even': '🟡', 'unknown': '⚪'}.get(opp['status'], '?')

        print(f"{idx:<5} {name:<20} {level:<6} {wld:<12} {win_rate:<10} {difficulty:<10} {status_icon} {opp['status']:<10}")

    if len(opponents) > limit:
        print(f"\n... and {len(opponents) - limit} more")

def print_recent_fights(db, limit=20):
    """Display recent fight history"""
    fights = db.get_recent_fights(limit)

    print_header("RECENT FIGHTS")

    if not fights:
        print("No fights recorded yet")
        return

    print(f"\n{'Date/Time':<20} {'Result':<7} {'Opponent':<25} {'Duration':<10} {'URL':<}")
    print("-" * 100)

    for fight in fights:
        timestamp = fight['timestamp'][:19]  # Remove milliseconds
        result = fight['result']
        result_icon = {'WIN': '✅', 'LOSS': '❌', 'DRAW': '🤝'}.get(result, '?')
        opponent = fight['opponent_name'][:23]
        duration = f"{fight['duration']}" if fight['duration'] else 'N/A'
        url = fight['fight_url']

        print(f"{timestamp:<20} {result_icon} {result:<5} {opponent:<25} {duration:<10} {url}")

def print_opponent_detail(db, opponent_id):
    """Display detailed stats for a specific opponent"""
    stats = db.get_opponent_stats(opponent_id)

    if not stats:
        print(f"No data found for opponent ID {opponent_id}")
        return

    print_header(f"OPPONENT DETAILS: {stats['name']}")

    print(f"\nOpponent ID: {opponent_id}")
    print(f"Name: {stats['name']}")
    print(f"Level: {stats.get('level', '?')}")
    print(f"\nFight Statistics:")
    print(f"  Total fights: {stats['total_fights']}")
    print(f"  Wins: {stats['wins']}")
    print(f"  Losses: {stats['losses']}")
    print(f"  Draws: {stats['draws']}")
    print(f"  Win rate: {stats['win_rate']:.1%}")
    print(f"  Status: {stats['status']}")
    print(f"  Difficulty: {db.calculate_opponent_difficulty(opponent_id)}/100")

    # Win rate trend
    trend = db.get_win_rate_trend(opponent_id, last_n=10)
    if trend['recent_fights'] > 0:
        print(f"\nRecent Trend (last {trend['recent_fights']} fights):")
        print(f"  Recent win rate: {trend['recent_win_rate']:.1%}")
        print(f"  Trending: {trend['trending']}")
        print(f"  Results: {' '.join(trend['results'])}")

    print(f"\nFirst fought: {stats['first_fought']}")
    print(f"Last fought: {stats['last_fought']}")

    # Recent fights against this opponent
    db.cursor.execute('''
        SELECT fight_id, result, timestamp, duration, fight_url
        FROM fights
        WHERE leek_id = ? AND opponent_id = ?
        ORDER BY timestamp DESC
        LIMIT 10
    ''', (db.leek_id, opponent_id))

    recent_fights = db.cursor.fetchall()
    if recent_fights:
        print(f"\nRecent Fights:")
        for fight in recent_fights:
            result_icon = {'WIN': '✅', 'LOSS': '❌', 'DRAW': '🤝'}.get(fight['result'], '?')
            timestamp = fight['timestamp'][:19]
            print(f"  {result_icon} {fight['result']:<5} - {timestamp} - {fight['fight_url']}")

def export_data(db, output_file):
    """Export fight data to CSV"""
    try:
        filename = db.export_to_csv(output_file)
        print(f"✅ Data exported to: {filename}")
    except Exception as e:
        print(f"❌ Export failed: {e}")

def generate_report(db, output_file=None):
    """Generate comprehensive statistics report"""
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"fight_report_{db.leek_id}_{timestamp}.txt"

    stats = db.get_global_stats()
    beatable = db.get_all_opponent_stats('beatable')
    dangerous = db.get_all_opponent_stats('dangerous')
    recent = db.get_recent_fights(20)

    with open(output_file, 'w') as f:
        f.write("="*60 + "\n")
        f.write("LEEKWARS FIGHT STATISTICS REPORT\n")
        f.write("="*60 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Leek ID: {db.leek_id}\n")
        f.write(f"Database: {db.db_file}\n\n")

        # Global stats
        f.write("GLOBAL STATISTICS\n")
        f.write("-"*60 + "\n")
        f.write(f"Total fights: {stats['total_fights']}\n")
        if stats['total_fights'] > 0:
            f.write(f"Win rate: {stats['win_rate']:.1%}\n")
            f.write(f"Record: {stats['wins']}W - {stats['losses']}L - {stats['draws']}D\n")
            f.write(f"Opponents tracked: {stats['opponents_tracked']}\n")
            f.write(f"Beatable opponents: {stats['beatable_opponents']}\n")
            f.write(f"Dangerous opponents: {stats['dangerous_opponents']}\n\n")

        # Beatable opponents
        if beatable:
            f.write("\nBEATABLE OPPONENTS (TOP 10)\n")
            f.write("-"*60 + "\n")
            for idx, opp in enumerate(beatable[:10], 1):
                f.write(f"{idx}. {opp['name']} (Level {opp.get('level', '?')})\n")
                f.write(f"   Record: {opp['wins']}W - {opp['losses']}L - {opp['draws']}D ({opp['win_rate']:.1%})\n")
                f.write(f"   Difficulty: {db.calculate_opponent_difficulty(opp['opponent_id'])}/100\n")

        # Dangerous opponents
        if dangerous:
            f.write("\nDANGEROUS OPPONENTS\n")
            f.write("-"*60 + "\n")
            for idx, opp in enumerate(dangerous[:10], 1):
                f.write(f"{idx}. {opp['name']} (Level {opp.get('level', '?')})\n")
                f.write(f"   Record: {opp['wins']}W - {opp['losses']}L - {opp['draws']}D ({opp['win_rate']:.1%})\n")
                f.write(f"   Difficulty: {db.calculate_opponent_difficulty(opp['opponent_id'])}/100\n")

        # Recent fights
        if recent:
            f.write("\nRECENT FIGHTS\n")
            f.write("-"*60 + "\n")
            for fight in recent:
                f.write(f"{fight['timestamp'][:19]} - {fight['result']} vs {fight['opponent_name']}\n")
                f.write(f"   {fight['fight_url']}\n")

    print(f"✅ Report saved to: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='View fight statistics from database')
    parser.add_argument('leek_id', type=int, help='Leek ID to view stats for')
    parser.add_argument('--status', choices=['beatable', 'dangerous', 'even', 'unknown'],
                       help='Filter opponents by status')
    parser.add_argument('--opponent', type=int, help='View detailed stats for specific opponent ID')
    parser.add_argument('--recent', action='store_true', help='Show recent fights')
    parser.add_argument('--export', metavar='FILE', help='Export fight data to CSV')
    parser.add_argument('--report', metavar='FILE', nargs='?', const=True,
                       help='Generate comprehensive report')
    parser.add_argument('--limit', type=int, default=20, help='Limit number of results (default: 20)')

    args = parser.parse_args()

    # Check if database exists
    db_file = f"fight_history_{args.leek_id}.db"
    import os
    if not os.path.exists(db_file):
        print(f"❌ Database not found: {db_file}")
        print(f"   No fight history for leek ID {args.leek_id}")
        return 1

    # Open database
    db = FightDatabase(args.leek_id)

    try:
        # Show global stats by default
        if not any([args.status, args.opponent, args.recent, args.export, args.report]):
            print_global_stats(db)
            print_opponent_list(db, limit=args.limit)

        # Handle specific requests
        if args.opponent:
            print_opponent_detail(db, args.opponent)

        if args.status:
            print_opponent_list(db, args.status, args.limit)

        if args.recent:
            print_recent_fights(db, args.limit)

        if args.export:
            export_data(db, args.export)

        if args.report:
            output_file = args.report if isinstance(args.report, str) else None
            generate_report(db, output_file)

    finally:
        db.close()

    return 0

if __name__ == "__main__":
    exit(main())
