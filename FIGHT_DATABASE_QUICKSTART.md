# Fight Database - Quick Start Guide

## What You Need to Know

### ✅ YES - Results Are Automatically Saved!

Every fight you run is **automatically saved** to a SQLite database:
- Database file: `fight_history_{your_leek_id}.db`
- No manual saving required
- All fight details preserved (timestamp, result, opponent, duration, etc.)

## Running Fights

```bash
# Basic usage (25 fights with your first leek)
python3 tools/lw_solo_fights_db.py 1 25

# With specific strategy
python3 tools/lw_solo_fights_db.py 1 50 --strategy adaptive
```

## What You'll See

### During Fights

The script shows **colored status indicators** for each opponent:

```
   ✅ Fight #1: WIN vs OpponentName (Level 95) [🟢 3W-0L-0D, 100%, diff:15]
      🔗 https://leekwars.com/fight/49658897
```

**Color Meanings:**
- 🟢 **Beatable** - Win rate ≥ 70% (easy opponent)
- 🟡 **Even** - Win rate 30-70% (medium difficulty)
- 🔴 **Dangerous** - Win rate ≤ 30% (hard opponent)
- ⚪ **Unknown** - Less than 2 fights (no data yet)

**Status Format:** `[🟢 3W-0L-0D, 100%, diff:15]`
- `3W-0L-0D`: Your record (3 wins, 0 losses, 0 draws)
- `100%`: Your win rate against this opponent
- `diff:15`: Difficulty rating (0=easiest, 100=hardest)

### Example Output

```
============================================================
LEEKWARS SMART SOLO FIGHTER (DATABASE EDITION)
============================================================
Selected: Leek #1
Fights to run: 25
Strategy: smart

💾 Auto-saves: All fight results saved to SQLite database
📊 Stats viewer: python3 tools/fight_stats_viewer.py <leek_id>

Strategy descriptions:
  • safe: Only fight beatable/unknown opponents
  • smart: Prefer beatable > unknown > few risky (default)
  • aggressive: Fight all, but prefer beatable first
  • adaptive: Learn from recent trends, adjust dynamically
  • confident: Only fight opponents with high confidence data
  • random: No opponent filtering

🔐 Logging in...

✅ Connected successfully!
   👤 Farmer: YourName (ID: 12345)
   💰 Habs: 123,456
   📊 Stats: 150V / 5D / 45L (Ratio: 3.33)
   🗡️ Available fights: 100
   🥬 Leeks found: 3

   Your leeks:
     - MyLeek (Level 100)

💾 Initializing database for MyLeek...

📊 Fight Statistics for MyLeek:
   Total fights tracked: 50
   Overall win rate: 72.0%
   Opponents tracked: 25
   🟢 Beatable opponents: 12
   🔴 Dangerous opponents: 3

============================================================
STARTING SMART SOLO FIGHTS (DATABASE MODE)
Strategy: SMART
============================================================

💾 All fight results automatically saved to database!
   Database: fight_history_123456.db

Opponent Status Colors:
   🟢 Beatable (win rate ≥ 70%)
   🟡 Even (30-70% win rate)
   🔴 Dangerous (win rate ≤ 30%)
   ⚪ Unknown (< 2 fights)

🎯 Running 25 smart fights with MyLeek...
   🧠 Smart selection: 35/40 opponents (avoided 5)
   ✅ Fight #1: WIN vs EasyOpponent (Level 90) [🟢 5W-0L-0D, 100%, diff:10]
      🔗 https://leekwars.com/fight/49658897
   ✅ Fight #2: WIN vs UnknownPlayer (Level 95) [⚪ 1W-0L-0D, 100%, diff:50]
      🔗 https://leekwars.com/fight/49658898
   ❌ Fight #3: LOSS vs ToughGuy (Level 100) [🔴 0W-2L-0D, 0%, diff:95]
      🔗 https://leekwars.com/fight/49658899
   ✅ Fight #4: WIN vs MediumEnemy (Level 92) [🟡 2W-1L-0D, 67%, diff:45]
   ✅ Fight #5: WIN vs FriendlyOpponent (Level 88) [🟢 4W-1L-0D, 80%, diff:25]
   ...

============================================================
SMART FIGHT SESSION COMPLETE
============================================================
✅ Total fights completed: 25/25
⏱️ Time taken: 2.5 minutes
⚡ Average: 6.0 seconds per fight

📊 Updated Stats:
   Total fights tracked: 75
   Overall win rate: 74.7%
   Opponents tracked: 32
   🟢 Beatable opponents: 15
   🔴 Dangerous opponents: 3

🔗 Last 3 fights:
   ✅ https://leekwars.com/fight/49658920
   ✅ https://leekwars.com/fight/49658921
   ❌ https://leekwars.com/fight/49658922

📊 Updating final stats...
   💰 Habs: 125,789
   🗡️ Remaining fights: 75

👋 Disconnected from LeekWars
```

## Viewing Statistics

After running fights, view your stats:

```bash
# View overall statistics
python3 tools/fight_stats_viewer.py 123456

# View only beatable opponents (easy targets)
python3 tools/fight_stats_viewer.py 123456 --status beatable

# View recent fight history
python3 tools/fight_stats_viewer.py 123456 --recent

# View detailed info about specific opponent
python3 tools/fight_stats_viewer.py 123456 --opponent 789012

# Generate full report
python3 tools/fight_stats_viewer.py 123456 --report

# Export to CSV
python3 tools/fight_stats_viewer.py 123456 --export my_fights.csv
```

## Strategies Explained

### Smart (Default) ⭐
Best balance of winning and variety
- Fights mostly beatable opponents
- Includes unknowns for exploration
- Occasionally fights a few risky opponents

### Safe
Maximum win rate
- Only fights beatable and unknown opponents
- Avoids all dangerous opponents
- Best for farming wins

### Adaptive 🧠
Learn from trends
- Prioritizes opponents with improving win rates
- Adjusts based on recent performance
- Good for dynamic adaptation

### Aggressive
Test your limits
- Fights all opponents
- Prefers easier matchups first
- Good for testing strategy changes

### Confident
High-confidence data only
- Only fights opponents with 5+ past fights
- Avoids unknowns and risky matchups
- Most predictable results

### Random
No filtering
- Completely random opponent selection
- Good for warming up or testing

## Migration from JSON

First time running the script with an existing JSON tracker?

The script will **automatically detect** and offer to migrate:

```
📦 Found existing JSON tracker file: opponent_tracker_123456.json
   Migrate to database? (y/n): y

🔄 Migrating opponent_tracker_123456.json to SQLite database...
✅ Migration complete:
   📊 Migrated 25 opponents
   🥊 Total fights tracked: 150
   💾 Database: fight_history_123456.db
   📦 Backed up JSON to: opponent_tracker_123456.json.backup
```

Your old data is preserved, and the JSON file is backed up!

## Database File Location

Your fight database is saved as:
- **File**: `fight_history_{leek_id}.db`
- **Location**: Same directory where you run the script
- **Size**: ~50 KB per 100 fights
- **Backup**: Copy the `.db` file to backup your data

## Key Points

✅ **Automatic Saving** - Every fight saved immediately
✅ **Color Indicators** - Easy to see opponent difficulty
✅ **Smart Selection** - Avoid hard opponents automatically
✅ **Detailed Stats** - Complete fight history preserved
✅ **Easy Migration** - Converts old JSON files seamlessly
✅ **No Manual Work** - Everything automated

## Need Help?

See full documentation: `FIGHT_DATABASE.md`

Common commands:
```bash
# Run fights
python3 tools/lw_solo_fights_db.py 1 25 --strategy smart

# View stats
python3 tools/fight_stats_viewer.py 123456

# Export data
python3 tools/fight_stats_viewer.py 123456 --export history.csv
```

---

**Version**: 1.0
**Created**: January 2026
