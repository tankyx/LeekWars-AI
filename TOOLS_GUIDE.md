# Tools Guide

## Most Important Tools

### 1. Upload & Deployment
```bash
# Upload complete V6 system
python3 tools/upload_v6_complete.py

# Update single script
python3 tools/lw_update_script.py V6_modules/ai/decision_making.ls 445527
```

### 2. Testing & Combat
```bash
# Test against specific opponent
python3 tools/lw_test_script.py 445497 15 hachess

# Run ranked solo fights
python3 tools/lw_solo_fights_flexible.py 1 10        # 10 fights with leek 1
python3 tools/lw_solo_fights_flexible.py 1 50 --quick # Quick mode

# Test runner for continuous testing
python3 tools/lw_test_runner.py
```

### 3. Fight Analysis
```bash
# Get detailed fight info with actions
python3 tools/lw_get_fight_auth.py 49159572

# Get fight logs
python3 tools/lw_get_fight.py 49159572

# Retrieve script from LeekWars
python3 tools/lw_retrieve_script.py 445497
```

### 4. Leek Management
```bash
# Get leek characteristics
python3 tools/lw_charateristics.py

# Get leek info
python3 tools/lw_leeks_info.py
```

### 5. Structure & Validation
```bash
# Check V6 structure
python3 tools/lw_check_structure.py

# Create V6 folder structure
python3 tools/lw_create_v6_structure.py

# Fix V6 paths
python3 tools/lw_fix_v6_paths.py
```

### 6. Debugging
```bash
# Debug script issues
python3 tools/lw_debug.py
```

## Quick Commands

### Run from LeekWars-AI folder:

**Test and see results:**
```bash
# Quick test
python3 tools/lw_test_script.py 445497 1 rex

# Full test suite
for op in hachess rex betalpha tisma guj; do
    echo "Testing vs $op..."
    python3 tools/lw_test_script.py 445497 5 $op
done
```

**Daily workflow:**
```bash
# 1. Make changes to V6_modules/
# 2. Upload changes
python3 tools/upload_v6_complete.py
# 3. Test
python3 tools/lw_test_script.py 445497 3 rex
# 4. Run ranked fights
python3 tools/lw_solo_fights_flexible.py 1 20 --quick
```

## Tool Categories

### Upload Tools
- `upload_v6_complete.py` - Full V6 deployment
- `upload_v6_fixed.py` - Fixed version uploader
- `upload_v6_leekwars.py` - Direct LeekWars upload
- `upload_v6_modules.py` - Module-specific upload
- `upload_v6_to_leekwars.py` - Alternative uploader

### Test Tools  
- `lw_test_script.py` - Main testing tool
- `lw_test_runner.py` - Continuous test runner
- `lw_solo_fights_flexible.py` - Ranked solo fights
- `lw_solo_fights_leek_1.py` - Leek 1 specific
- `lw_solo_fights_leek_2.py` - Leek 2 specific

### Analysis Tools
- `lw_get_fight.py` - Basic fight info
- `lw_get_fight_auth.py` - Detailed fight analysis
- `lw_debug.py` - Debug helper

### Management Tools
- `lw_update_script.py` - Update individual scripts
- `lw_retrieve_script.py` - Download scripts from LeekWars
- `lw_leeks_info.py` - Leek information
- `lw_charateristics.py` - Characteristics viewer

### Structure Tools
- `lw_check_structure.py` - Validate structure
- `lw_create_v6_structure.py` - Create folders
- `lw_fix_v6_paths.py` - Fix path issues
- `lw_fix_v6_complete.py` - Complete fixes
- `lw_cleanup_and_fix_v6.py` - Cleanup tool
- `lw_cleanup_root.py` - Root cleanup

## Environment Variables

Some tools use these environment variables:
```bash
export LEEKWARS_EMAIL="your_email@example.com"
export LEEKWARS_PASSWORD="your_password"
```

Or store in `~/.config/leekwars/config.json`:
```json
{
    "username": "your_email@example.com",
    "password": "your_password"
}
```