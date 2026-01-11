#!/usr/bin/env python3
"""
Migrate JSON-based opponent tracker to SQLite database
Usage: python3 migrate_json_to_db.py <leek_id> [json_file]
"""

import json
import sys
from fight_db import FightDatabase
from datetime import datetime

def migrate_json_to_db(leek_id, json_file=None):
    """Migrate JSON opponent tracker to database"""
    if json_file is None:
        json_file = f"opponent_tracker_{leek_id}.json"

    print(f"📦 Migrating {json_file} to database...")

    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {json_file}")
        return False
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON file: {json_file}")
        return False

    # Initialize database
    db = FightDatabase(leek_id)

    # Migrate opponent data
    migrated = 0
    for opponent_id_str, opp_data in data.items():
        try:
            opponent_id = int(opponent_id_str)

            # Extract data (handle different JSON formats)
            if isinstance(opp_data, dict):
                opponent_name = opp_data.get('name', f'Opponent_{opponent_id}')
                opponent_level = opp_data.get('level', 0)
                wins = opp_data.get('wins', 0)
                losses = opp_data.get('losses', 0)
                draws = opp_data.get('draws', 0)
                fights = opp_data.get('fights', [])

                # Import individual fights if available
                if isinstance(fights, list):
                    for fight in fights:
                        if isinstance(fight, dict):
                            fight_data = {
                                'fight_id': fight.get('fight_id', 0),
                                'opponent_id': opponent_id,
                                'opponent_name': opponent_name,
                                'opponent_level': opponent_level,
                                'result': fight.get('result', 'UNKNOWN'),
                                'duration': fight.get('duration'),
                                'actions_count': fight.get('actions_count', 0),
                                'fight_url': fight.get('fight_url', f'https://leekwars.com/fight/{fight.get("fight_id", 0)}')
                            }
                            db.record_fight(fight_data)
                            migrated += 1
                else:
                    # No individual fights, just create aggregate stats
                    print(f"   ⚠️ No fight details for {opponent_name}, skipping...")

        except Exception as e:
            print(f"   ⚠️ Error migrating opponent {opponent_id_str}: {e}")
            continue

    db.close()

    print(f"✅ Migration complete: {migrated} fights imported")

    # Offer to backup/delete old JSON file
    response = input(f"\nBackup and remove {json_file}? (y/n): ")
    if response.lower() == 'y':
        import shutil
        backup_file = f"{json_file}.backup"
        shutil.move(json_file, backup_file)
        print(f"✅ Backed up to {backup_file}")

    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 migrate_json_to_db.py <leek_id> [json_file]")
        sys.exit(1)

    leek_id = int(sys.argv[1])
    json_file = sys.argv[2] if len(sys.argv) > 2 else None

    migrate_json_to_db(leek_id, json_file)
