# LeekWars Fight Database System

## Overview

The Fight Database System provides intelligent opponent tracking and statistics for LeekWars solo fights. It uses SQLite to store detailed fight history, enabling smarter opponent selection and performance analysis.

## Features

- **Per-Leek Databases**: Separate database for each leek
- **Detailed Fight History**: Every fight recorded with timestamp, result, duration
- **Opponent Statistics**: Win/loss/draw records, win rates, difficulty ratings
- **Smart Opponent Selection**: Multiple strategies based on historical performance
- **Trend Analysis**: Detect improving/declining performance against opponents
- **Easy Migration**: Convert existing JSON tracker files to database
- **Statistics Viewer**: Analyze fight data with comprehensive reports
- **CSV Export**: Export fight history for external analysis

## Quick Start

### Running Fights with Database Tracking

```bash
# Run 25 fights with your first leek using smart strategy
python3 tools/lw_solo_fights_db.py 1 25 --strategy smart

# Run fights with adaptive strategy (learns from trends)
python3 tools/lw_solo_fights_db.py 2 50 --strategy adaptive
```

### Viewing Statistics

```bash
# View overall statistics for leek ID 123456
python3 tools/fight_stats_viewer.py 123456

# View only beatable opponents
python3 tools/fight_stats_viewer.py 123456 --status beatable

# View recent fight history
python3 tools/fight_stats_viewer.py 123456 --recent

# View detailed stats for specific opponent
python3 tools/fight_stats_viewer.py 123456 --opponent 789012

# Generate comprehensive report
python3 tools/fight_stats_viewer.py 123456 --report

# Export fight history to CSV
python3 tools/fight_stats_viewer.py 123456 --export history.csv
```

### Migrating from JSON

```bash
# Migrate specific leek
python3 tools/migrate_json_to_db.py 123456

# Migrate all JSON tracker files in current directory
python3 tools/migrate_json_to_db.py --all
```

## Database Schema

### Tables

**`leeks`**: Your leeks
- `id` (PRIMARY KEY): Leek ID
- `name`: Leek name
- `level`: Current level
- `first_seen`, `last_updated`: Timestamps

**`opponents`**: All opponents encountered
- `id` (PRIMARY KEY): Opponent ID
- `name`: Opponent name
- `level`: Last known level
- `first_seen`, `last_updated`: Timestamps

**`fights`**: Complete fight history
- `id` (AUTOINCREMENT): Internal ID
- `fight_id` (UNIQUE): LeekWars fight ID
- `leek_id`, `opponent_id`: Foreign keys
- `result`: WIN/LOSS/DRAW
- `timestamp`: When fight occurred
- `duration`: Fight duration (turns)
- `actions_count`: Number of actions
- `fight_url`: Link to fight

**`opponent_stats`**: Aggregate statistics per leek-opponent pair
- `leek_id`, `opponent_id`: Composite primary key
- `wins`, `losses`, `draws`: Fight counts
- `total_fights`: Total encounters
- `win_rate`: Win percentage
- `status`: beatable/dangerous/even/unknown
- `first_fought`, `last_fought`: Timestamps

## Opponent Selection Strategies

### `safe`
Only fights beatable and unknown opponents. Avoids all dangerous opponents.
- **Use when**: You want to maximize win rate
- **Risk level**: Low

### `smart` (default)
Prefers beatable opponents, includes unknowns, and occasionally fights a few risky opponents for variety.
- **Use when**: Balanced win rate and opponent diversity
- **Risk level**: Medium

### `aggressive`
Fights all opponents but prefers easier matchups first.
- **Use when**: You want to test against all skill levels
- **Risk level**: High

### `adaptive`
Learns from recent performance trends. Prioritizes opponents with improving win rates and high-confidence data.
- **Use when**: You want dynamic strategy based on recent results
- **Risk level**: Medium
- **Special**: Adjusts to recent win/loss streaks

### `confident`
Only fights opponents with high confidence data (many past fights).
- **Use when**: You want to avoid unknowns and risky encounters
- **Risk level**: Very Low

### `random`
No filtering, random opponent selection.
- **Use when**: Testing or warming up
- **Risk level**: Variable

## Opponent Status Classification

Opponents are automatically classified based on fight history:

- **`beatable`** (🟢): Win rate ≥ 70% with at least 2 wins
- **`dangerous`** (🔴): Win rate ≤ 30% with at least 2 losses
- **`even`** (🟡): Between 30-70% win rate
- **`unknown`** (⚪): Insufficient data (< 2 total fights)

## Difficulty Rating

Each opponent receives a difficulty rating (0-100):
- **0-30**: Easy opponents
- **31-60**: Medium difficulty
- **61-100**: Hard opponents

The rating considers:
- Historical win rate
- Number of fights (confidence)
- Recent performance trend

## Statistics

### Global Stats

```python
{
    'total_fights': int,        # Total fights recorded
    'wins': int,                # Total wins
    'losses': int,              # Total losses
    'draws': int,               # Total draws
    'win_rate': float,          # Overall win percentage
    'opponents_tracked': int,   # Number of unique opponents
    'beatable_opponents': int,  # Count of beatable opponents
    'dangerous_opponents': int  # Count of dangerous opponents
}
```

### Opponent Stats

```python
{
    'opponent_id': int,
    'name': str,
    'level': int,
    'wins': int,
    'losses': int,
    'draws': int,
    'total_fights': int,
    'win_rate': float,
    'status': str,              # beatable/dangerous/even/unknown
    'first_fought': timestamp,
    'last_fought': timestamp
}
```

### Win Rate Trend

```python
{
    'recent_fights': int,       # Number of recent fights analyzed
    'recent_win_rate': float,   # Win rate in recent fights
    'trending': str,            # improving/declining/stable/unknown
    'results': list             # Chronological results (WIN/LOSS/DRAW)
}
```

## File Locations

- **Databases**: `fight_history_{leek_id}.db`
- **JSON Backups**: `opponent_tracker_{leek_id}.json.backup`
- **CSV Exports**: `fight_history_{leek_id}.csv`
- **Reports**: `fight_report_{leek_id}_{timestamp}.txt`

## API Reference

### FightDatabase Class

```python
from fight_db import FightDatabase

# Initialize database for a leek
db = FightDatabase(leek_id=123456)

# Record a fight
db.record_fight({
    'fight_id': 49658897,
    'opponent_id': 789012,
    'opponent_name': 'EnemyLeek',
    'opponent_level': 100,
    'result': 'WIN',
    'duration': 15,
    'actions_count': 120,
    'fight_url': 'https://leekwars.com/fight/49658897'
})

# Get opponent statistics
stats = db.get_opponent_stats(opponent_id=789012)

# Get all opponents with specific status
beatable = db.get_all_opponent_stats(status='beatable')

# Get global statistics
global_stats = db.get_global_stats()

# Get win rate trend for opponent
trend = db.get_win_rate_trend(opponent_id=789012, last_n=10)

# Calculate opponent difficulty
difficulty = db.calculate_opponent_difficulty(opponent_id=789012)

# Get preferred opponents based on strategy
available_opponents = [{'id': 1, 'name': 'Opp1', 'level': 50}, ...]
preferred = db.get_preferred_opponents(available_opponents, strategy='smart')

# Get recent fight history
recent = db.get_recent_fights(limit=20)

# Export to CSV
filename = db.export_to_csv('my_fights.csv')

# Close database
db.close()
```

## Example Workflow

### 1. First Time Setup

```bash
# Run fights with your leek (auto-creates database)
python3 tools/lw_solo_fights_db.py 1 25 --strategy smart
```

The script will:
- Check for existing JSON tracker files
- Offer to migrate if found
- Create new database if needed
- Start tracking fights

### 2. Regular Fighting Sessions

```bash
# Morning session
python3 tools/lw_solo_fights_db.py 1 50 --strategy adaptive

# Evening session
python3 tools/lw_solo_fights_db.py 1 50 --strategy smart
```

### 3. Review Statistics

```bash
# View overall performance
python3 tools/fight_stats_viewer.py 123456

# Check which opponents to target
python3 tools/fight_stats_viewer.py 123456 --status beatable --limit 10

# Review recent fights
python3 tools/fight_stats_viewer.py 123456 --recent --limit 20
```

### 4. Analyze Specific Opponents

```bash
# Get detailed stats for tough opponent
python3 tools/fight_stats_viewer.py 123456 --opponent 789012
```

Output shows:
- Overall record against opponent
- Win rate trend
- Recent fight results
- Difficulty rating

### 5. Generate Reports

```bash
# Weekly performance report
python3 tools/fight_stats_viewer.py 123456 --report weekly_report.txt
```

## Migration Notes

### Converting from JSON

The migration tool converts existing JSON tracker files to SQLite:

**What's Preserved:**
- Opponent IDs, names, levels
- Win/loss/draw counts
- Win rates and status classifications
- First/last fought timestamps

**What's Lost:**
- Individual fight IDs (not stored in JSON)
- Fight timestamps (only first/last preserved)
- Fight durations and action counts

**After Migration:**
- Original JSON file backed up to `.json.backup`
- All future fights tracked in full detail
- Statistics seamlessly continue from JSON data

## Troubleshooting

### Database Locked Error

If you get a "database is locked" error:
```bash
# Close any running scripts
pkill -f lw_solo_fights_db.py

# Manually close database connections in Python:
from fight_db import FightDatabase
db = FightDatabase(123456)
db.close()
```

### Corrupted Database

If database becomes corrupted:
```bash
# Backup current database
cp fight_history_123456.db fight_history_123456.db.backup

# Remove corrupted database
rm fight_history_123456.db

# Restart from JSON (if available)
python3 tools/migrate_json_to_db.py 123456
```

### Performance Issues

For leeks with 1000+ fights:
```bash
# Vacuum database to reclaim space and improve performance
sqlite3 fight_history_123456.db "VACUUM;"
```

## Advanced Usage

### Custom Opponent Filtering

```python
from fight_db import FightDatabase

db = FightDatabase(123456)

# Get all opponents with win rate > 80%
db.cursor.execute('''
    SELECT * FROM opponent_stats
    WHERE leek_id = ? AND win_rate > 0.8
    ORDER BY total_fights DESC
''', (123456,))

strong_matchups = [dict(row) for row in db.cursor.fetchall()]
```

### Recent Performance Analysis

```python
# Get fights from last 7 days
from datetime import datetime, timedelta

cutoff = (datetime.now() - timedelta(days=7)).isoformat()
db.cursor.execute('''
    SELECT * FROM fights
    WHERE leek_id = ? AND timestamp > ?
    ORDER BY timestamp DESC
''', (123456, cutoff))

recent_week = [dict(row) for row in db.cursor.fetchall()]
```

## Credits

Created for LeekWars AI V8 development. Part of the enhanced opponent tracking system.

## Version

- **Database Version**: 1.0
- **Schema Version**: 1
- **Created**: January 2026
