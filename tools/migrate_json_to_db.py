#!/usr/bin/env python3
"""
Migration tool: JSON opponent tracker → SQLite database
Converts existing opponent_tracker_{leek_id}.json files to SQLite database
"""

import json
import os
import sys
from datetime import datetime
from fight_db import FightDatabase

def migrate_json_to_db(leek_id: int, json_file: str = None, verbose: bool = True) -> bool:
    """
    Migrate JSON opponent tracker to SQLite database

    Args:
        leek_id: Leek ID
        json_file: Path to JSON file (default: opponent_tracker_{leek_id}.json)
        verbose: Print progress messages

    Returns:
        True if migration succeeded, False otherwise
    """
    if not json_file:
        json_file = f"opponent_tracker_{leek_id}.json"

    if not os.path.exists(json_file):
        if verbose:
            print(f"❌ JSON file not found: {json_file}")
        return False

    if verbose:
        print(f"🔄 Migrating {json_file} to SQLite database...")

    # Load JSON data
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        if verbose:
            print(f"❌ Failed to load JSON: {e}")
        return False

    # Validate JSON structure
    if 'leek_id' not in data or 'opponents' not in data:
        if verbose:
            print(f"❌ Invalid JSON structure")
        return False

    if int(data['leek_id']) != leek_id:
        if verbose:
            print(f"⚠️ Warning: JSON leek_id ({data['leek_id']}) doesn't match target ({leek_id})")

    # Initialize database
    db = FightDatabase(leek_id)

    migrated_opponents = 0
    migrated_fights = 0

    try:
        # Migrate opponents
        for opp_id_str, opp_data in data['opponents'].items():
            opp_id = int(opp_id_str)
            opp_name = opp_data.get('name', f"Opponent_{opp_id}")
            opp_level = opp_data.get('level', 1)

            # Update opponent info
            db.update_opponent_info(opp_id, opp_name, opp_level)

            # Create synthetic fight records from aggregate stats
            # Note: We can't restore individual fight history from JSON,
            # so we create the opponent_stats entry directly
            wins = opp_data.get('wins', 0)
            losses = opp_data.get('losses', 0)
            draws = opp_data.get('draws', 0)
            total_fights = wins + losses + draws

            if total_fights > 0:
                win_rate = wins / total_fights
                status = opp_data.get('status', 'unknown')

                # Parse timestamps
                first_fought = opp_data.get('first_fought')
                last_fought = opp_data.get('last_fought')

                # Insert opponent_stats directly
                db.cursor.execute('''
                    INSERT OR REPLACE INTO opponent_stats
                    (leek_id, opponent_id, wins, losses, draws, total_fights, win_rate, status, first_fought, last_fought)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (leek_id, opp_id, wins, losses, draws, total_fights, win_rate, status, first_fought, last_fought))

                migrated_opponents += 1
                migrated_fights += total_fights

        db.conn.commit()

        if verbose:
            print(f"✅ Migration complete:")
            print(f"   📊 Migrated {migrated_opponents} opponents")
            print(f"   🥊 Total fights tracked: {migrated_fights}")
            print(f"   💾 Database: {db.db_file}")

        # Backup JSON file
        backup_file = f"{json_file}.backup"
        try:
            os.rename(json_file, backup_file)
            if verbose:
                print(f"   📦 Backed up JSON to: {backup_file}")
        except Exception as e:
            if verbose:
                print(f"   ⚠️ Could not backup JSON: {e}")

        db.close()
        return True

    except Exception as e:
        if verbose:
            print(f"❌ Migration failed: {e}")
        db.close()
        return False


def migrate_all_json_files(verbose: bool = True):
    """Find and migrate all opponent_tracker JSON files in current directory"""
    import glob

    json_files = glob.glob("opponent_tracker_*.json")

    if not json_files:
        if verbose:
            print("ℹ️ No opponent tracker JSON files found in current directory")
        return

    if verbose:
        print(f"Found {len(json_files)} JSON file(s) to migrate")
        print("=" * 60)

    migrated_count = 0
    for json_file in json_files:
        # Extract leek ID from filename
        try:
            leek_id = int(json_file.split('_')[-1].split('.')[0])
        except:
            if verbose:
                print(f"⚠️ Could not parse leek ID from {json_file}, skipping")
            continue

        if migrate_json_to_db(leek_id, json_file, verbose):
            migrated_count += 1

        if verbose:
            print()  # Blank line between migrations

    if verbose:
        print("=" * 60)
        print(f"✅ Migration complete: {migrated_count}/{len(json_files)} files migrated")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Migrate JSON opponent tracker to SQLite database')
    parser.add_argument('leek_id', type=int, nargs='?', help='Leek ID to migrate (omit to migrate all)')
    parser.add_argument('--json-file', help='Path to JSON file (default: opponent_tracker_{leek_id}.json)')
    parser.add_argument('--all', action='store_true', help='Migrate all opponent tracker JSON files')

    args = parser.parse_args()

    print("=" * 60)
    print("OPPONENT TRACKER MIGRATION TOOL")
    print("JSON → SQLite Database")
    print("=" * 60)
    print()

    if args.all or args.leek_id is None:
        migrate_all_json_files()
    elif args.leek_id:
        success = migrate_json_to_db(args.leek_id, args.json_file)
        return 0 if success else 1
    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
