# Quick Start Guide

## Setup (First Time Only)

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/LeekWars-AI.git
cd LeekWars-AI
```

2. **Install dependencies and configure:**
```bash
./run.sh
# Choose option 5 (setup)
```

## Daily Usage

### From the LeekWars-AI folder:

**Interactive Menu:**
```bash
./run.sh
```

**Direct Commands:**
```bash
# Upload V6 to LeekWars
python3 tools/upload_v6_complete.py

# Test against specific opponent (15 rounds)
python3 tools/lw_test_script.py 445497 15 rex

# Test against all opponents (5 rounds each)
for op in hachess rex betalpha tisma guj; do
    python3 tools/lw_test_script.py 445497 5 $op
done
```

## Common Tasks

### After Making Changes

1. **Test locally:**
```bash
python3 tools/lw_test_script.py 445497 3 rex
```

2. **Upload to LeekWars:**
```bash
python3 tools/upload_v6_complete.py
```

3. **Push to GitHub:**
```bash
git add .
git commit -m "Your commit message"
git push origin main
```

### Debugging

View fight details:
```bash
python3 tools/lw_get_fight_auth.py FIGHT_ID
```

## File Structure

- `V6_modules/` - All AI source code
- `tools/` - Python automation scripts
- `run.sh` - Interactive management script

## Current Performance

- **Rex (Agile):** 60% win rate
- **Hachess (Defensive):** 33% win rate
- **Others:** Testing in progress

## Troubleshooting

If upload fails:
1. Check credentials in `~/.config/leekwars/config.json`
2. Ensure you're in the LeekWars-AI folder
3. Run `pip3 install -r requirements.txt`