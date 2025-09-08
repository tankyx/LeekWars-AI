# CLAUDE.md - LeekWars V6 AI Development Guide

## Overview
This document provides context for Claude Code when working on the LeekWars V6 AI system. It covers the development workflow, testing procedures, and current performance analysis.

## Project Structure
```
LeekWars-AI/
├── V6_modules/          # Core AI modules (41 total)
│   ├── V6_main.ls      # Main entry point
│   ├── core/           # Core systems (4 modules: globals, initialization, operations, state)
│   ├── combat/         # Combat execution (12 modules including damage_sequences, m_laser_tactics)
│   ├── movement/       # Movement & positioning (7 modules)
│   ├── strategy/       # Tactical decisions (9 modules including multi_enemy)
│   ├── ai/             # AI decision making (5 modules)
│   └── utils/          # Utilities & helpers (4 modules)
└── tools/              # Python automation tools
    ├── lw_test_script.py       # Automated testing with log retrieval
    ├── upload_v6_complete.py   # Full deployment script
    └── analyze_combat_logs.py  # Log analysis tool
```

## Key Commands & Workflows

### 1. Upload V6 AI to LeekWars
```bash
python3 tools/upload_v6_complete.py
```
This uploads all 41 modules to LeekWars under the 6.0/V6/ folder structure (includes multi-enemy support).

### 2. Run Test Fights with Log Retrieval
```bash
# Test against specific opponent (with automatic log retrieval)
python3 tools/lw_test_script.py <script_id> <num_tests> <opponent>

# Example: 20 fights against Domingo
python3 tools/lw_test_script.py 445497 20 domingo

# Available opponents:
# - domingo: Balanced, 600 strength
# - betalpha: Magic build, 600 magic  
# - tisma: Wisdom/Science, 600 wisdom
# - guj: Tank, 5000 life
# - hachess: Defensive, 600 resistance
# - rex: Agile, 600 agility
```

The test script now automatically:
- Retrieves fight logs from the API endpoint `/fight/get-logs/{fight_id}`
- Saves results to `test_results_<script_id>_<timestamp>.json`
- Saves fight logs to `fight_logs_<script_id>_<opponent>_<timestamp>.json`
- Creates readable analysis in `log_analysis_<script_id>_<opponent>_<timestamp>.txt`

### 3. Analyze Combat Logs
```bash
python3 analyze_combat_logs.py
```
This analyzes all fight log files and identifies patterns in wins/losses.

## Current V6 AI Performance (December 2024)

### Test Results vs Standard Opponents - WITH NEW WEAPONS
| Opponent | Win Rate | Previous (Sept 2024) | Status |
|----------|----------|----------|--------|
| Rex (Agile, 600 AGI) | **80.0%** | 70.0% | ✅ Excellent performance! |
| Hachess (Defensive, 600 RES) | TBD | 44.9% | 🔄 Testing pending |
| Tisma (Wisdom, 600 WIS) | TBD | 40.0% | 🔄 Testing pending |
| Guj (Tank, 5000 HP) | TBD | 22.4% | 🔄 Testing pending |
| Betalpha (Magic, 600 MAG) | **40.0%** | 14.0% | ✅ Significant improvement |
| Domingo (Balanced, 600 STR) | **0.0%** | 5.0% | 🔴 Critical weakness |

**New Weapon Loadout (September 2024):**
- **Rifle**: 7-9 range, 73-79 damage, 7 TP
- **Dark Katana**: 1 range, 99 damage, -15% vulnerability, 44 self-damage, 7 TP
- **M-Laser**: 5-12 range line attack, 90-100 damage, 8 TP
- **Grenade Launcher**: 4-7 range AoE (unchanged)

## Key Issues Identified

### 1. ~~Pathfinding Bug~~ (FIXED)
- **Issue**: "No A* path found" appeared in nearly every fight at turns 1-2
- **Root Cause**: Algorithm blocked pathfinding TO enemy cell
- **Fix Applied**: Modified `V6_modules/movement/pathfinding.ls:65` to allow pathfinding TO enemy (as goal) but not THROUGH enemy
- **Status**: ✅ RESOLVED

### 2. ~~Operation Overuse~~ (FIXED)
- **Issue**: AI spending too many operations on analysis instead of combat
- **Root Cause**: Influence map processing 40 cells, EID precomputing 30 cells
- **Fixes Applied**:
  - Reduced influence map range: 10→5 cells
  - Reduced cells processed: 40→10 cells
  - Skip influence map in turns 1-3
  - Reduced EID precomputation: 30→10 cells
- **Status**: ✅ RESOLVED - Significant performance improvements

### 3. Poor Performance vs Domingo (5.0% win rate)
- **Issue**: Dies extremely quickly (avg 6.1 turns) to balanced STR builds
- **Root Cause**: Still too passive against high-damage builds
- **Fix Strategy**: Need even more aggressive early game and better damage trading

### 4. ~~Panic Mode Not Activating~~ (FIXED)
- **Issue**: 0% panic mode activation, AI was crashing when triggered
- **Root Cause**: Used deprecated `getLeek()` instead of `getEntity()` in LeekScript 3
- **Fix Applied**: 
  - Changed to `getEntity()` in `V6_modules/combat/execute_combat.ls:1380`
  - Added HP-based trigger: <20% HP AND <500 absolute HP
  - Simplified panic combat to just heal + attack
- **Status**: ✅ RESOLVED - No more crashes, panic mode functional

### 5. ~~Teleportation Issues~~ (FIXED - COMPLETELY REWRITTEN)
- **Issue**: Multiple problems with teleportation system
  - Teleporting to walkable cells (1-2 cell distances)
  - Not moving after teleporting to reach attack positions
  - Using wrong weapon ranges (checking old weapon values)
  - Teleporting without checking if walking + attacking would be better
- **Root Cause**: Fundamental flaws in teleport logic and validation
- **Fixes Applied**:
  - **Complete rewrite of teleportation.ls** with proper validation
  - Uses `getPath()` to check actual MP cost, not Manhattan distance
  - Post-teleport movement to reach attack positions
  - Updated all weapon ranges (Rifle 7-9, M-Laser 5-12, Grenade 4-7, Dark Katana 1)
  - Added visual debugging with colored markers
  - Blocks teleport if target is walkable in available MP
  - Considers teleport+walk combinations for damage opportunities
- **Status**: ✅ RESOLVED - No more wasted TP on short teleports

### 6. ~~M-Laser Alignment~~ (FIXED)
- **Issue**: M-Laser failing with error -4 (not in line)
- **Root Cause**: Not checking line alignment before using M-Laser
- **Fix Applied**: Added `isOnSameLine()` check before adding M-Laser to attack options
- **Status**: ✅ RESOLVED

### 7. ~~Multi-Enemy Support~~ (IMPLEMENTED)
- **Enhancement**: Full multi-enemy battle support with multi-hit optimization
- **Features**:
  - Smart target selection based on threat and killability
  - **M-Laser multi-hit**: Pierces through all enemies in a line
  - **Grenade AoE multi-hit**: Optimizes target cell for maximum splash damage
  - Multi-hit damage calculation multiplies effectiveness
  - Dynamic weapon prioritization based on multi-hit potential
  - Multi-enemy EID calculation for positioning
  - Maintains backward compatibility with 1v1
- **Implementation**:
  - New module: `V6_modules/strategy/multi_enemy.ls`
  - `getBestLaserTarget()`: Finds optimal line for M-Laser multi-hits
  - `getBestAoETarget()`: Finds optimal cell for grenade multi-hits
  - `calculateMultiHitValue()`: Calculates total damage across all enemies
  - Combat execution automatically targets multi-hit opportunities
- **Status**: ✅ IMPLEMENTED - Multiplies damage output in team battles

### 8. ~~Weapon Prioritization Issues~~ (FIXED)
- **Issue**: AI heavily favoring Grenade Launcher over better weapons
- **Root Cause**: Insufficient penalties for grenade when better options available
- **Fixes Applied**:
  - Heavy penalties (-200 to -500) for grenade when Rifle/M-Laser available
  - Dark Katana prioritized in close range (2-4 cells)
  - Edge case handling for map boundaries
  - Proper damage scaling with strength formula
- **Status**: ✅ RESOLVED - Correct weapon selection

### 9. ~~Damage Scaling~~ (FIXED)
- **Issue**: Hard-coded damage values not scaling with strength
- **Root Cause**: Missing strength scaling formula
- **Fix Applied**: All damage calculations now use `BaseDamage * (1 + Strength/100)`
  - Applies to all weapons (Rifle, M-Laser, Grenade, Dark Katana)
  - Applies to all damage chips
  - Dark Katana self-damage also scales with strength
- **Status**: ✅ RESOLVED - Proper damage scaling

### 10. ~~TP Waste from Weapon Switching~~ (FIXED)
- **Issue**: Equipping same weapon multiple times, wasting TP
- **Fix Applied**: Using `setWeaponIfNeeded()` instead of `setWeapon()`
- **Status**: ✅ RESOLVED - No redundant weapon switches

### 11. ~~Debug Log Spam~~ (FIXED)
- **Issue**: Too many verbose debug messages flooding logs
- **Fixes Applied**:
  - Removed EID calculation logs
  - Removed "Calculating" logs from influence map
  - Removed cell processing logs
- **Status**: ✅ RESOLVED - Cleaner, more readable logs

### 12. ~~B-Laser Weapon Support~~ (IMPLEMENTED)
- **Enhancement**: Full support for alternative weapon loadouts
- **Features**:
  - Automatic weapon detection in initialization
  - B-Laser dual damage/heal functionality (50-60 damage + 50-60 heal)
  - Magnum (1-8 range, 2 uses/turn) and Destroyer (1-6 range, 2 uses/turn) support
  - Generic laser tactics module for all laser weapons (M-Laser, B-Laser, future lasers)
  - Multi-hit optimization for B-Laser piercing through enemies
  - Weapon use tracking per turn
- **Implementation**:
  - V6_main.ls auto-detects weapons and loads appropriate tactics
  - New modules: `laser_tactics_generic.ls`, `b_laser_tactics.ls`
  - B-Laser specific modules in `blaser/` folder for specialized tactics
  - All weapon constants consolidated in `core/globals.ls`
- **Status**: ✅ IMPLEMENTED - V6_main.ls works with any weapon loadout

### 13. ~~Teleportation Chip Detection~~ (FIXED)
- **Issue**: AI attempted to use teleportation without checking if chip was equipped
- **Root Cause**: Missing chip equipped verification before cooldown check
- **Fix Applied**:
  - Added `inArray(getChips(), CHIP_TELEPORTATION)` check in initialization
  - Added safety check before `useChipOnCell()` in teleportation.ls
  - Logs "No teleportation chip equipped" when missing
- **Status**: ✅ RESOLVED - No crashes when teleportation chip not equipped

### 14. ~~Dynamic Operations Budget~~ (FIXED)
- **Issue**: Hardcoded operation limits didn't account for different core counts
- **Root Cause**: Used fixed 7,000,000 operations instead of calculating from cores
- **Fix Applied**:
  - Added `maxOperations = getCores(entity) * 1000000` calculation
  - Replaced all hardcoded operation checks with dynamic calculations
  - Now properly scales with each leek's core count
- **Status**: ✅ RESOLVED - Operations budget adapts to leek configuration

### 15. ~~Excessive Weapon Switching~~ (FIXED)
- **Issue**: AI wasting 2+ TP per turn switching between Magnum and B-Laser repeatedly
- **Root Cause**: Attack options included multiple viable weapons processed sequentially
- **Fix Applied**:
  - Added weapon switching prevention when already dealing damage
  - Skip weapon switches when insufficient TP for switch + attack
  - Prioritize using current weapon before considering switches
- **Status**: ✅ RESOLVED - No more unnecessary weapon switching

### 16. ~~B-Laser Targeting Errors~~ (FIXED)
- **Issue**: B-Laser consistently failing with result -4 (invalid target/position)
- **Root Cause**: B-Laser treated as AoE weapon using `useWeaponOnCell()` instead of direct targeting
- **Fix Applied**:
  - Removed B-Laser from AoE weapon list
  - B-Laser now uses direct `useWeapon(enemy)` targeting
  - Proper line-of-sight validation for direct attacks
- **Status**: ✅ RESOLVED - B-Laser should work consistently

### 17. ~~Poor Grenade Launcher Usage~~ (FIXED)
- **Issue**: AI never moved from range 8 to 7 to access grenade launcher (range 4-7)
- **Root Cause**: Positioning logic blocked movement when in "optimal range" 7-9
- **Fix Applied**:
  - Added exception for range 8→7 movement to access grenade launcher
  - Increased grenade launcher priority when no other weapons available (2000→5000 score)
  - Fixed positioning logic to consider weapon accessibility, not just range optimality
- **Status**: ✅ RESOLVED - AI now repositions to use all available weapons

### 18. ~~AoE Splash Over Direct Shots Priority~~ (FIXED)
- **Issue**: AI using weak AoE splash attacks instead of moving for direct weapon hits
- **Root Cause**: Immediate fallback to AoE without aggressive line-of-sight seeking
- **Fix Applied**:
  - Added aggressive LOS seeking (searches up to 50 reachable cells)
  - Prioritizes direct weapon hits before AoE fallback
  - Smart range scoring: Range 4-7 (8000), Range 2-8 (7000), Any LOS (5000)
  - Direct attacks attempted immediately after finding LOS position
- **Status**: ✅ RESOLVED - Direct hits prioritized over AoE splash

## Recent Modifications (Recalibration)

### Threat Thresholds (in `V6_modules/core/globals.ls`)
```leekscript
// Balanced aggression settings
global THREAT_HIGH_RATIO = 0.8;      // Was 1.2 (too aggressive)
global THREAT_SAFE_RATIO = 0.4;      // Was 0.7
global PKILL_COMMIT = 0.7;           // Was 0.6
global PKILL_SETUP = 0.5;            // Was 0.4
global TP_DEFENSIVE_RATIO = 0.6;     // Was 0.8
```

### Teleportation Logic (COMPLETELY REWRITTEN in `V6_modules/movement/teleportation.ls`)
- Complete rewrite with proper validation using `getPath()` for MP cost checking
- Post-teleport movement to reach attack positions
- Blocks teleports to walkable cells (saves TP)
- Visual debugging with colored markers
- Tactical repositioning scenarios
- Kill opportunity detection with teleport+walk combos
- Emergency escape conditions
- Gap-closing for finishing blows

### Shield/Heal Strategy (in `V6_modules/combat/execute_combat.ls`)
- Adaptive defense based on threat level
- Shields when attacking (high threat)
- Heals when fleeing (low threat)
- Critical HP always triggers healing

### Turn 1 Strategy
- Always uses Armoring for HP buff
- Knowledge for wisdom boost
- Maintains defensive opening

## Strengths
1. **Strong vs Most Builds**: Now above baseline for 5/6 opponent types
2. **Excellent vs Agile**: 80% win rate vs Rex (massive improvement)
3. **Strong vs Defensive**: 65% win rate vs Hachess (high resistance)
4. **Good Survivability**: Averages 16.7 turns in wins
5. **Effective Operation Management**: Fixed overuse allows more combat actions
6. **Multi-Enemy Ready**: Supports team battles and FFA modes with multi-hit optimization
7. **Smart Teleportation**: Considers teleport+walk combinations for optimal positioning
8. **Multi-Hit Mastery**: M-Laser pierces multiple enemies, Grenade optimizes AoE for multi-hits

## Recommended Next Steps

1. **Fix Domingo Matchup** [CRITICAL - 0% win rate]
   - Still dying too quickly to balanced STR builds
   - Need ultra-aggressive opening with new weapons
   - Consider M-Laser/Rifle burst at turn 1 instead of buffs
   - Implement Dark Katana rush strategy when health permits

2. **Optimize New Weapon Usage**
   - M-Laser line targeting needs improvement
   - Dark Katana health threshold management
   - Rifle positioning for consistent damage
   - Better weapon switching logic

3. **Test Against Remaining Opponents**
   - Need data for Hachess, Tisma, and Guj
   - Verify improvements hold across all matchups
   - Fine-tune based on opponent type

4. **Leverage Weapon Strengths**
   - M-Laser: Maximize line damage with positioning
   - Dark Katana: Use for finishing blows when safe
   - Rifle: Consistent mid-range pressure
   - Grenade: Still best for AoE situations

## Testing Best Practices

1. **Always run at least 10-20 fights** per opponent for statistical significance
2. **Check logs for patterns** in losses using the analysis tools
3. **Test after each modification** to measure impact
4. **Save baseline results** before making changes
5. **Use log retrieval** to understand AI decision-making

## Important Files to Monitor

- `V6_modules/V6_main.ls` - Main entry point
- `V6_modules/ai/decision_making.ls` - Core decision logic
- `V6_modules/movement/teleportation.ls` - Teleport strategy
- `V6_modules/combat/execute_combat.ls` - Combat execution
- `V6_modules/core/globals.ls` - Global constants and thresholds
- `V6_modules/strategy/phase_management.ls` - Game phase adaptation

## Notes for Future Development

- The V6 AI uses a WIS-tank build focusing on healing and survivability
- It has 41 interconnected modules that must be uploaded together
- Performance varies significantly by opponent type
- ~~Pathfinding issues~~ FIXED - Was blocking TO enemy cell
- ~~Panic mode crashes~~ FIXED - Used deprecated getLeek() function
- ~~Teleportation issues~~ FIXED - Complete rewrite with proper validation
- ~~Weapon prioritization~~ FIXED - Now correctly prioritizes Rifle/M-Laser over Grenade
- ~~Multi-enemy support~~ IMPLEMENTED - Full support with multi-hit optimization
- ~~Damage scaling~~ FIXED - All damage now scales with strength
- The AI tends to be too defensive and needs more aggression against high-STR opponents

## Contact & Resources

- LeekWars Game: https://leekwars.com
- Main Script ID: 445497 (V6_main)
- Test Farmer Account: Virus (ID: 18035)

---
*Last Updated: January 27, 2025*
*Document Version: 1.9*
*Latest Updates:*
- *Fixed excessive weapon switching wasting TP by prioritizing current weapon*
- *Fixed B-Laser targeting issues by using direct useWeapon() instead of useWeaponOnCell()*
- *Improved repositioning logic to access grenade launcher at range 8→7*
- *Added aggressive line-of-sight seeking before falling back to AoE splash attacks*
- *Enhanced movement prioritization over chip usage when better weapon positions available*
- *Fixed movement logic to reposition when hasLOS=false even at optimal range*
*Previous Updates:*
- *Fixed damage_sequences.ls to check equipped weapons before using them*
- *Added movement logic when out of attack range*
- *Added teleportation chip equipped verification*
- *Implemented dynamic operations budget based on core count*
- *V6_main.ls is now universal - automatically detects and adapts to any weapon loadout*
- *B-Laser dual functionality: damage enemies while healing self (scales with STR/WIS)*
- *Consolidated all globals into core/globals.ls*
- *Fixed variable redefinitions across multiple modules*
*Latest Results: 80% vs Rex, 40% vs Betalpha, 0% vs Domingo*