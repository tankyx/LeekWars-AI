# CLAUDE.md - LeekWars AI Development Guide

## Overview
Development guide for LeekWars AI V8 system - modular, strategy-based combat AI with build-specific optimizations.

## Project Structure
```
LeekWars-AI/
├── V8_modules/          # V8 AI (9 modules, ~3,134 lines)
│   ├── main.lk         # Main entry point
│   ├── game_entity.lk  # Player & enemy state tracking
│   ├── field_map.lk    # Damage zones & tactical positioning
│   ├── item.lk         # Weapon/chip definitions & damage calculations
│   └── strategy/       # Build-specific strategies
│       ├── action.lk           # Action type definitions
│       ├── base_strategy.lk    # Base combat logic
│       ├── strength_strategy.lk # Strength builds (weapon-focused)
│       ├── magic_strategy.lk    # Magic builds (DoT kiting)
│       └── agility_strategy.lk  # Agility builds (damage return)
├── V7_modules/          # V7 AI (10 modules, ~1,180 lines) - LEGACY
└── tools/              # Python automation
    ├── lw_test_script.py # Testing with log retrieval
    └── upload_v8.py     # V8 deployment
```

## 🎉 V8 SYSTEM STATUS - ACTIVE DEVELOPMENT ⚡

**V8 AI - Modular Strategy System** - Build-specific combat strategies with refactored agility support

### Key Features
- **Strategy Pattern**: Separate combat logic for Strength, Magic, and Agility builds
- **Modular Design**: 9 modules, ~3,134 lines of maintainable code
- **Build Detection**: Automatic strategy selection based on stat distribution
- **Advanced Tactics**: Hide-and-seek positioning, OTKO teleportation, damage return mechanics

### Recent Updates (October 2025)
- **Star Pattern Distance Fix**: Fixed lightninger/rifle range calculation using getCellDistance() validation
- **Action Execution Bug Fixed**: Weapon attacks now use captured targetCell instead of stale entity position
- **Chest Prioritization**: All strategies detect and prioritize chests, switching back to enemies after destruction
- **Unreachable Position Handling**: Added executeAndFlushActions() for mid-scenario execution
- **Agility Strategy Refactored**: Complete rewrite using strength strategy template
- **Damage Return Optimization**: CHIP_MIRROR/THORN buff management before combat
- **Chip Spam Bug Fixed**: All strategies now properly spam chips until TP exhausted

---

## Key Commands

### Upload V8 AI System
```bash
python3 tools/upload_v8.py
```

### Test Fights
```bash
# Test V8 AI: python3 tools/lw_test_script.py <leek_id> <fights> <opponent>
python3 tools/lw_test_script.py 446029 20 domingo

# Opponents: domingo, betalpha, tisma, guj, hachess, rex
```

### Accessing Fight Logs
⚠️ **IMPORTANT**: Fight logs cannot be retrieved via URL/CURL. Use Python scripts which save logs locally:
- **Fight logs saved to**: `fight_logs/<leek_id>/` directory
- **Analysis logs**: Root directory with pattern `log_analysis_<leek_id>_<opponent>_<timestamp>.txt`
- **Debug files**: `debug_fight.py`, `debug_fight_simple.py` in root directory

---

# V8 Technical Details

## Build Strategies

### Strength Strategy (strength_strategy.lk)
**Philosophy:** Weapon-focused damage maximization
- **Cell Selection**: Prioritizes highest weapon damage cells from field map
- **Primary Weapon**: Uses cell's highest damage weapon to max uses
- **Secondary Weapons**: Uses other equipped weapons from same cell
- **Chip Usage**: Spends leftover TP on damage chips (sorted by damage)
- **Special Features**: OTKO teleportation for low HP enemies, CHIP_LIBERATION tactical usage
- **Combat Flow**: Move → Primary weapon spam → Secondary weapons → Damage chips → HNS

### Magic Strategy (magic_strategy.lk)
**Philosophy:** DoT kiting and ranged control
- **Cell Selection**: Weighted toward DoT damage (1.5x multiplier)
- **Primary Focus**: Apply poison chips, use DoT weapons
- **Kiting Behavior**: Attack → Reposition away from enemies
- **Special Features**: Multi-cycle DoT application, intelligent effect tracking
- **Combat Flow**: Move → DoT chips → DoT weapons → Kite away

### Agility Strategy (agility_strategy.lk) - REFACTORED OCTOBER 2025
**Philosophy:** Strength strategy + damage return buffs
- **Unique Feature**: CHIP_MIRROR (35.75% return) / CHIP_THORN (22.75% return) management
- **Cell Selection**: Same as strength (highest weapon damage)
- **Combat Flow**: Apply return buff → Strength strategy logic
- **Code Reuse**: 95% shared with strength strategy, only adds buff management

#### Agility Strategy Refactoring (October 2025)

**Problem Identified:**
- Over-engineered cell selection logic (ignored pre-calculated best cells)
- Weapon sorting by maxUse instead of damage (backwards logic)
- Missing HNS-approach cell consideration
- Redundant position tracking variables
- 237 lines vs strength's 196 lines for similar functionality

**Solution Implemented:**
- Complete rewrite using strength_strategy.lk as template
- Removed custom weapon-only cell selection (lines 84-147 old code)
- Removed maxUse-based weapon sorting (lines 168-185 old code)
- Added HNS-approach safer cell checking (from strength strategy)
- Simplified to: Apply CHIP_MIRROR/THORN → Use strength combat logic

**Code Changes:**
```
Before: 237 lines, custom logic throughout
After:  206 lines (13% reduction), strength-based with buff layer

Structure:
1. Apply CHIP_MIRROR/THORN if needed (unique to agility)
2. Select best weapon cell (same as strength)
3. Check HNS-approach for safer cells (same as strength)
4. Movement to weapon cell (same as strength)
5. Primary weapon usage (same as strength)
6. Secondary weapons (same as strength)
7. Damage chips (same as strength)
8. Post-offensive HNS (same as strength)
```

**Bug Fixes Applied:**
- Fixed chip spam bug in agility (already fixed)
- Fixed chip spam bug in strength main offensive (lines 377-383)
- Fixed chip spam bug in strength OTKO (lines 149-155)
- **Issue**: Pre-calculated `usesC = min(maxUse, floor(TP/cost))` limited spam
- **Fix**: Changed to `while (actualUsesC < maxUse && playerTP >= cost)`

**Files Modified:**
- `/V8_modules/strategy/agility_strategy.lk` - Complete `createOffensiveScenario()` rewrite
- `/V8_modules/strategy/strength_strategy.lk` - Chip spam bug fixes (2 locations)

**Testing Status:** ✅ Uploaded and operational (October 2025)

## Critical Bug Fixes (October 2025)

### Star Pattern Distance Calculation Bug
**Problem:**
- `getLineHits()` and `getDiagonalHits()` used arithmetic cell offsets without validating actual game distance
- Cells marked as in-range when they were actually out of range (e.g., cell 181 at distance 12 for lightninger max range 10)
- Arithmetic offset `cell + x_offset * dist` doesn't guarantee correct Chebyshev distance

**Solution:**
- Added `getCellDistance()` validation in both methods (field_map.lk lines 542-543, 569-570)
- Filters cells to only those at actual weapon range before marking as damage cells
- Code: `if (actualDist == null || actualDist < minR || actualDist > maxR) continue`

**Impact:** Star pattern weapons (lightninger, rifle) now correctly identify all valid shooting positions

### Stale Target Position Bug
**Problem:**
- Attack execution used `a.targetEntity._cellPos` which becomes stale after `executeAndFlushActions()`
- Target entity state not refreshed when player state is updated mid-scenario
- Caused weapon attacks to fail silently (wrong cell position)

**Solution:**
- Changed attack execution to use `a.targetCell` (captured at action creation time)
- Modified base_strategy.lk lines 550, 553 from `a.targetEntity._cellPos` to `a.targetCell`

**Impact:** Weapon and chip attacks now execute correctly after immediate movement

### Chest Targeting After Destruction Bug
**Problem:**
- `getClosestChest()` returned dead chests (`isDead()` == true)
- AI continued targeting destroyed chests instead of switching back to enemies
- Infinite loop on dead chest entity

**Solution:**
- Added `isDead()` check in `getClosestChest()` (field_map.lk line 379)
- Code: `if (isDead(c._id)) continue`
- Returns null when all chests destroyed, strategies fall back to enemy targeting

**Impact:** All strategies (Strength, Agility, Magic) properly resume enemy combat after chest loot collected

### Unreachable Position Handling
**Problem:**
- When optimal weapon cell was unreachable, agility strategy applied buff then stopped
- No TP spent on attacks from current position
- Early return prevented any combat actions

**Solution:**
- Added `executeAndFlushActions()` method for mid-scenario execution (base_strategy.lk lines 567-571)
- Executes movement immediately, updates game state, continues with weapons/chips from actual position
- Tracks weapon state (`currentWeaponId`) to avoid unnecessary swaps

**Impact:** Agility builds now properly spend TP on attacks even when optimal cell unreachable

## Script ID
- **V8**: 446029 (main.lk) - Current production
- **V7**: LEGACY - No longer maintained

## Development Best Practices
1. **Testing**: Run 10-20 fights per opponent for statistical significance
2. **Incremental Changes**: Test after each modification
3. **Log Analysis**: Use combat logs to identify win/loss patterns
4. **Constants**: All WEAPON_* and CHIP_* constants are built-in to LeekScript - no need to define them

---

# V7 Technical Details

## Core Features
- **Enemy-Centric Damage Zones**: Calculate all possible damage from enemy perspective
- **A* Pathfinding**: Move toward highest damage potential cells  
- **Scenario-Based Combat**: TP-to-weapon sequence mapping
- **Enhanced Peek-a-Boo Combat**: Iterative attack-reposition cycles with smart resource management
- **Hide and Seek Tactics**: Post-combat repositioning to break line of sight with enemies
- **Smart Teleportation**: Intelligent teleport usage for finishing blows and unreachable positions
- **Smart Emergency Mode**: Tactical positioning with Enhanced Lightninger healing
- **Visual Debugging**: Color-coded damage zones on combat map

## Supported Weapons
- **Enhanced Lightninger**: Range 6-10, Cost 9 TP, Grenade launcher with 3x3 AoE
- **Rifle**: Range 7-9, Cost 7 TP, Standard weapon with diamond zones
- **M-Laser**: Range 5-12, Cost 8 TP, Laser weapon requiring X/Y alignment  
- **Katana**: Range 1, Cost 7 TP, Melee weapon with 20% bonus
- **Electrisor**: Range 7, Cost 7 TP, Max 2 uses/turn, Circle 1 AoE, Damage 70-80
- **Rhino**: Range 2-4, Cost 5 TP, Max 3 uses/turn, Single target
- **B-Laser**: Range 2-8, Cost 5 TP, Max 3 uses/turn, Line weapon
- **Grenade Launcher**: Range 4-7, Cost 6 TP, Max 2 uses/turn, Circle AoE
- **Sword**: Range 1, Cost 6 TP, Max 2 uses/turn, Melee weapon
- **Neutrino**: Range 2-6, Cost 4 TP, Max 3 uses/turn, Diagonal weapon
- **Destroyer**: Range 1-6, Cost 6 TP, Max 2 uses/turn, Debuff weapon
- **Flame Thrower**: Range 2-8, Cost 6 TP, Max 2 uses/turn, DoT weapon

## V7 Architecture
- **Lines**: 1,180 lines of optimized code
- **Modules**: 10 focused modules
- **Architecture**: Enemy-centric streamlined design
- **Debugging**: Visual map marking with color-coded damage zones
- **Performance**: Optimized algorithms for LeekScript constraints

## Major V7 Fixes (September 2025)

### Critical Performance Optimization
- **Issue**: "trop d'opérations consommées" - too many operations consumed
- **Fix**: Optimized damage calculation loops and pathfinding algorithms
- **Result**: Zero crashes, stable execution under LeekScript constraints

### Variable Name Conflicts Fixed
- **Issue**: Reserved names `enemies`, `enemyHP`, `enemyMaxHP` caused compilation errors
- **Fix**: Renamed to `allEnemies`, `currentEnemyHP`, `currentEnemyMaxHP`
- **Result**: Clean compilation with no variable conflicts

### Weapon Switching Bug Eliminated
- **Issue**: AI switching weapons repeatedly without attacking
- **Fix**: Prevented fallback weapon calls during scenario execution
- **Result**: Clean combat execution with proper weapon usage

### Magic Build System (September 2025)

#### Build Detection
- **Magic Threshold**: Magic > Strength (no modifier)
- **Global Variables**: `isMagicBuild`, `isHighMagicBuild` in core/globals.ls
- **Real-time Detection**: Updated each turn during game state refresh

#### Magic Build Weapon Priorities
1. **FLAME_THROWER**: Primary DoT DPS weapon (highest priority)
2. **RHINO**: High DPS backup for sustained damage
3. **ELECTRISOR**: AoE backup for crowd control
4. **DESTROYER**: Tactical debuffing (secondary to main DPS)

#### Optimal Magic Build Combos
- **17 TP**: FLAME_THROWER + FLAME_THROWER + CHIP_TOXIN (optimal DoT combo)
- **16 TP**: FLAME_THROWER + FLAME_THROWER + CHIP_VENOM 
- **15 TP**: FLAME_THROWER + FLAME_THROWER + CHIP_SPARK
- **12 TP**: FLAME_THROWER + FLAME_THROWER (max weapon uses)

#### Implementation
- **Pathfinding**: Magic builds prioritize FLAME_THROWER positioning over DESTROYER
- **Combat Scenarios**: FLAME_THROWER + TOXIN combo checked first in getScenarioForLoadout()
- **Weapon Selection**: All weapon selection algorithms respect magic build priorities
- **Built-in Constants**: Uses WEAPON_* and CHIP_* constants instead of hardcoded IDs

### Advanced Tactical Features (September 2025)

### Enhanced Peek-a-Boo Combat Loop
- **Multi-cycle Combat**: Up to 2 attack-reposition cycles per turn for maximum damage output
- **Smart Repositioning**: Evaluates positions based on attack potential, safety, and cover
- **Resource Management**: Strategic TP/MP allocation across multiple attack phases
- **Guaranteed Execution**: Ensures at least one combat action per turn regardless of conditions

### Hide and Seek Tactics
- **Post-Combat Positioning**: Automatic repositioning after attacks to break enemy line of sight
- **Cover Evaluation**: Scores positions based on adjacent obstacles and distance from enemies
- **MP Conservation**: Reserves movement points for tactical repositioning
- **Survivability Enhancement**: Significantly reduces enemy counterattack opportunities

### Smart Teleportation System
- **Low HP Priority**: Automatically considers teleportation when enemies below 30% HP or 500 HP
- **Unreachable Position Detection**: Activates when pathfinding cannot reach optimal damage zones
- **Resource Validation**: Ensures sufficient TP (15+ total: 9 for teleport + 6+ for weapon)
- **Range Optimization**: Uses CHIP_TELEPORTATION (1-12 range) to access high-damage positions
- **Finishing Blow Strategy**: Prioritizes immediate kill opportunities over conservative movement

### Performance Metrics (Latest Tests)
- **0% win rate vs domingo** (balanced opponent, 600 strength) - Strong defensive opponent
- **0% win rate vs rex** (agile opponent, 600 agility) - High mobility opponent
- **Zero timeout issues** - Stable execution under LeekScript v4+ constraints
- **Advanced tactical behaviors** - Dynamic combat adaptation based on battlefield conditions
- **System stability** - 100% fight completion rate (no crashes or "Invalid AI" errors)

### Combat System Fixes (September 2025)

#### Scenario-Based Combat Implementation
- **Issue**: Combat system used "SIMPLIFIED" approach, bypassing weapon+chip combinations
- **Problem**: AI repeatedly used single FLAME_THROWER attacks instead of optimal 17 TP combo
- **Fix**: Replaced simplified combat with `executePreCalculatedWeapon()` calling `getScenarioForLoadout()`
- **Result**: Magic builds now properly execute FLAME_THROWER + FLAME_THROWER + CHIP_TOXIN combos

#### Combat Execution Flow
1. **Pathfinding**: Recommends optimal weapon for positioning
2. **Scenario Selection**: `getScenarioForLoadout()` returns weapon+chip combination
3. **Combat Execution**: Executes full scenario (weapons + chips) in sequence
4. **Fallback**: Single weapon attack if scenario fails

### Intelligent Effect Tracking System (September 2025)

#### DoT/Debuff Alternation
- **Effect Detection**: Uses `getEffects()` API to track enemy status in real-time
- **Smart Prioritization**: Dynamically selects scenarios based on enemy effects
- **DoT Priority**: Applies CHIP_TOXIN/VENOM when enemy lacks poison or effect expiring (≤1 turn)
- **Debuff Priority**: Uses DESTROYER when enemy lacks strength debuff or effect expiring
- **Turn Tracking**: Monitors remaining turns for both DoT and strength debuff effects

#### Dynamic Scenario Building
- **Effect-Based Selection**: `buildMagicScenario()` creates scenarios based on enemy status
- **High TP Combos**: 
  - 17 TP: FLAME_THROWER + FLAME_THROWER + CHIP_TOXIN (when DoT needed)
  - 18 TP: FLAME_THROWER + FLAME_THROWER + DESTROYER (when debuff needed)
- **Intelligent Alternation**: Maintains both effects on enemies for maximum tactical advantage
- **Built-in Functions**: Uses LeekScript built-in `isChip()` and `isWeapon()` functions

#### Implementation Details
- **core/globals.ls**: Added `hasDoTEffect()`, `hasStrengthDebuff()`, effect turn tracking
- **config/weapons.ls**: Modified `buildMagicScenario()` for dynamic scenario creation
- **Effect Constants**: Uses EFFECT_POISON for DoT tracking (EFFECT_BURNING not available)
- **Debug Output**: Visual feedback showing enemy effects and remaining turns

### Critical Grid System Fix (September 2025)

#### Coordinate System Bug Resolution
- **Issue**: `getCellsAtExactDistance` assumed 18x18 grid (cells 0-323) missing cells 324-612
- **Problem**: AI couldn't find damage zones in upper half of map (cells 407, 408, 390, 373)
- **Fix**: Rewritten to use LeekWars built-in coordinate system (-17 to +17 X/Y)
- **Result**: Now evaluates ALL possible attack positions across entire battlefield

#### Full Damage Zone Coverage
- **Before**: Only evaluated ~25% of battlefield due to grid size assumption
- **After**: Evaluates entire 35x35 coordinate system using `getCellX()`, `getCellY()`, `getCellFromXY()`
- **Impact**: AI now finds reachable attack positions instead of moving to "dead zones"

### Current Technical Status
```
V7 AI vs Strong Opponents:
✅ No crashes: 0/∞ (100% stability)
✅ No compilation errors: Fixed all variable conflicts
✅ Performance optimized: Full 5-8M operation budget utilization
✅ Grid system: Fixed coordinate calculation for complete battlefield coverage
✅ Magic build system: Fully integrated DoT prioritization
✅ Scenario combat: Proper weapon+chip combinations
✅ Effect tracking: Intelligent DoT/debuff alternation
✅ Built-in functions: Proper use of LeekScript isChip/isWeapon
📊 Total fights completed: 100% success rate (no draws/crashes)
```

### Critical Chip ID Filtering Fix (September 2025)

#### Issue Resolution
- **Problem**: "Cette arme 18 n'existe pas" - chip IDs were being passed as weapon IDs to setWeapon()
- **Root Cause**: Damage zone calculation included chip zones with chip IDs that were treated as weapon recommendations
- **Error Flow**: evaluation.ls → pathfinding.ls → combat execution → setWeapon(chipID) ← ERROR

#### Technical Fix
**Files Modified:**
1. **combat/execution.ls**: Added chip ID validation before setWeapon calls
2. **movement/pathfinding.ls**: Filter chip IDs from weapon recommendations

**Key Changes:**
```ls
// Before setWeapon, validate it's actually a weapon
if (weaponId != null && !isWeapon(weaponId)) {
    debugW("PATHFIND: Filtering out non-weapon ID " + weaponId + " (likely chip)");
    weaponId = null; // Don't recommend chips as weapons
}

// In combat execution
if (recommendedWeapon != null && isChip(recommendedWeapon)) {
    debugW("COMBAT: Recommended action is chip, clearing for weapon fallback");
    recommendedWeapon = null;
}
```

**Result**: Zero "weapon X does not exist" errors, maintains chip zone calculations for positioning

## WEAPON_ELECTRISOR Integration ⚡

### Specifications
- **Range**: 7 (exact distance)
- **Cost**: 7 TP per use
- **Max Uses**: 2 per turn
- **Area**: Circle 1 (AoE damage)
- **Damage**: 70-80 per use

### Tactical Integration
- **Priority**: Prioritized over single-target weapons at range 7
- **Scenarios**: 14 TP (double use), 11 TP (single + chip), 7 TP (single use)
- **AoE Classification**: Properly classified as area weapon for tactical targeting
- **Weapon Selection**: Integrated into all weapon selection algorithms

### Implementation Details
- **config/weapons.ls**: Added ELECTRISOR_SCENARIOS with full TP cost mappings
- **Weapon Selection**: Integrated into getScenarioForLoadout() with proper range checking
- **Area Weapon Support**: Added to isAreaWeapon() function for tactical calculations

---

---

## Magic Build Usage Guide

### For Magic Builds (Magic > Strength):
1. **Equip**: FLAME_THROWER + DESTROYER + DoT chips (TOXIN, VENOM)
2. **17 TP Optimal**: FLAME_THROWER + FLAME_THROWER + CHIP_TOXIN
3. **Strategy**: Focus on sustained DoT damage, use DESTROYER for tactical debuffing
4. **Positioning**: AI automatically prioritizes FLAME_THROWER range (2-8) over DESTROYER range (1-6)

### For Strength Builds (Strength > Magic):
1. **Equip**: RHINO + ELECTRISOR + GRENADE_LAUNCHER for high burst DPS
2. **Strategy**: Standard weapon priorities focused on immediate damage output
3. **Positioning**: AI prioritizes high-DPS weapon positioning (RHINO range 2-4)

---

---

## LeekScript Programming Notes

### Built-in Constants
- **All WEAPON_* constants are built-in**: `WEAPON_M_LASER`, `WEAPON_RIFLE`, `WEAPON_ENHANCED_LIGHTNINGER`, etc.
- **All CHIP_* constants are built-in**: `CHIP_TOXIN`, `CHIP_VENOM`, `CHIP_SPARK`, `CHIP_LIGHTNING`, etc.
- **Effect constants available**: `EFFECT_POISON`, etc. (Note: `EFFECT_BURNING` not available)
- **No need to define constants** - they're part of the LeekScript language

### Coordinate System
- **Map center**: [0, 0]
- **Map corners**: [-17, 0], [17, 0], [0, -17], [0, 17]
- **Total cells**: 0-612 in a 35x35 grid
- **Built-in functions**: `getCellX()`, `getCellY()`, `getCellFromXY()` handle coordinate conversion

### Debugging & Logs
- **Console logs**: Use `debugW()` for AI debug output
- **Fight logs location**: Saved locally by Python scripts, NOT accessible via URL/CURL
- **Log files**: Check `fight_logs/` directory and root analysis files

---

# V7 System (LEGACY)

V7 remains in the codebase for reference but is no longer actively developed. See sections above for V7 technical details, including:
- Enemy-centric damage zones
- A* pathfinding
- Scenario-based combat
- Magic build DoT prioritization
- Grid system fixes
- Effect tracking

V7 served as the foundation for V8's strategy pattern architecture.

---

*Document Version: 15.0*
*Last Updated: October 2025*
*Status: V8 System Active - Critical Bug Fixes Deployed (Star Pattern, Action Execution, Chest Targeting)*