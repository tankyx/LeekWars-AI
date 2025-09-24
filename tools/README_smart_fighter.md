# LeekWars Smart Solo Fighter

An enhanced version of the LeekWars auto fighter that tracks opponent performance and intelligently selects fights to maximize win rate.

## Features

### 🧠 Smart Opponent Selection
- **Tracks fight history** against every opponent
- **Categorizes opponents** based on performance:
  - 🟢 **Beatable**: Consistent wins (≥70% win rate, ≥2 fights)
  - 🔴 **Dangerous**: Consistent losses (≤30% win rate, ≥2 fights)  
  - 🟡 **Even**: Mixed results or insufficient data

### 📊 Persistent Data Storage
- **Per-leek tracking**: Each leek has its own opponent database
- **JSON storage**: Data saved in `opponent_tracker_{leek_id}.json`
- **Statistics tracking**: Win rates, fight counts, opponent categories

### 🎯 Multiple Strategies
- **Safe**: Only fight beatable/unknown opponents
- **Smart**: Prefer beatable > unknown > few risky opponents (default)
- **Aggressive**: Fight all opponents but prioritize good matchups
- **Random**: No filtering (like original script)

## Usage

```bash
# Basic usage - smart strategy (default)
python3 lw_solo_fights_smart.py 1 20

# Safe strategy - avoid all risky opponents
python3 lw_solo_fights_smart.py 1 20 --strategy safe

# Aggressive strategy - fight everyone but prefer good matchups
python3 lw_solo_fights_smart.py 1 20 --strategy aggressive

# Random strategy - no opponent filtering
python3 lw_solo_fights_smart.py 1 20 --strategy random
```

### Parameters
- `leek_number`: Which leek to use (1, 2, 3, or 4)
- `num_fights`: Number of fights to run
- `--strategy`: Opponent selection strategy (safe/smart/aggressive/random)

## How It Works

### 1. **Initial Learning Phase**
When you first use the tool, it fights random opponents to gather data about who you can beat.

### 2. **Data Collection**
After each fight, the tool records:
- Opponent ID and name
- Fight result (WIN/LOSS/DRAW)
- Win rate calculation
- Opponent status classification

### 3. **Smart Selection**
Before each fight, the tool:
- Gets all available opponents
- Filters based on strategy
- Prioritizes good matchups
- Avoids consistently dangerous opponents

### 4. **Continuous Learning**
The tool continuously updates opponent data, so strategies improve over time.

## Example Output

```
📊 Opponent Tracking Stats for EbolaLeek:
   Total fights tracked: 45
   Overall win rate: 73.3%
   Opponents tracked: 23
   🟢 Beatable opponents: 8
   🔴 Dangerous opponents: 3

🧠 Smart selection: 12/15 opponents (avoided 3)
   ✅ Fight #1: WIN vs GoodOpponent (Level 42) [3W-0L-0D, 100%, beatable]
   ❌ Fight #2: LOSS vs ToughOpponent (Level 45) [1W-2L-0D, 33%, dangerous]
```

## Data Storage

Each leek gets its own tracking file: `opponent_tracker_{leek_id}.json`

```json
{
  "leek_id": 12345,
  "created": "2025-01-15T10:30:00",
  "last_updated": "2025-01-15T11:45:00",
  "opponents": {
    "67890": {
      "id": 67890,
      "name": "EnemyLeek",
      "wins": 3,
      "losses": 1,
      "draws": 0,
      "win_rate": 0.75,
      "status": "beatable",
      "first_fought": "2025-01-15T10:30:00",
      "last_fought": "2025-01-15T11:30:00"
    }
  },
  "stats": {
    "total_fights": 45,
    "wins": 33,
    "losses": 10,
    "draws": 2,
    "opponents_beaten": 8,
    "opponents_lost_to": 3
  }
}
```

## Strategy Comparison

| Strategy | Description | Best For |
|----------|-------------|----------|
| **Safe** | Avoid all dangerous opponents | Maximizing win rate |
| **Smart** | Balanced approach with learning | Most users (default) |
| **Aggressive** | Fight everyone, prefer good matchups | Gaining experience |
| **Random** | No filtering | Testing/debugging |

## Benefits

1. **Higher Win Rates**: By avoiding bad matchups and prioritizing good ones
2. **Efficient Learning**: Quickly identifies which opponents to avoid
3. **Data-Driven**: Makes decisions based on actual fight history
4. **Flexible**: Multiple strategies for different goals
5. **Persistent**: Remembers opponent data across sessions

## Migration from Original

The smart fighter is a drop-in replacement for `lw_solo_fights_flexible.py`:

```bash
# Old way
python3 lw_solo_fights_flexible.py 1 20

# New way  
python3 lw_solo_fights_smart.py 1 20
```

The smart version will start learning immediately and improve your win rate over time!