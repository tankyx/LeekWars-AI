# CLAUDE.md - LeekWars AI V8 Development Guide

## Overview
Development guide for LeekWars AI V8 system - modular, strategy-based combat AI with build-specific optimizations.

## Project Structure
```
LeekWars-AI/
├── V8_modules/          # V8 AI (10 modules, ~3,300 lines)
│   ├── main.lk         # Main entry point & strategy selection
│   ├── game_entity.lk  # Player & enemy state tracking
│   ├── field_map.lk    # Damage zones & tactical positioning
│   ├── item.lk         # Weapon/chip definitions & damage calculations
│   └── strategy/       # Build-specific strategies
│       ├── action.lk            # Action type definitions
│       ├── base_strategy.lk     # Base combat logic & action executor
│       ├── strength_strategy.lk # Strength builds (weapon-focused)
│       ├── magic_strategy.lk    # Magic builds (DoT kiting)
│       ├── agility_strategy.lk  # Agility builds (damage return)
│       └── boss_strategy.lk     # Boss fight strategy
└── tools/              # Python automation
    ├── lw_test_script.py # Testing with log retrieval
    └── upload_v8.py     # V8 deployment
```

## V8 System Architecture

### Core Philosophy: Action Queue Pattern

V8 uses a **two-phase execution model**:
1. **Planning Phase** - Strategy creates actions and queues them in `this._actions`
2. **Execution Phase** - `executeScenario()` iterates through queue and executes via action executors

**Key Principle:** Strategies NEVER call `useChip()`, `useWeapon()`, or `moveTowardCell()` directly during planning. All game-modifying operations happen in the execution phase.

**Why This Architecture?**
- Separation of concerns (planning vs execution)
- Testability (inspect actions before execution)
- Consistency (all strategies follow same flow)
- Debugging (actions visible in logs)
- State management (TP/MP/position updated correctly)

### Module Breakdown

#### **main.lk** - Entry Point & Strategy Selection
Detects build type and instantiates appropriate strategy:
- Strength: `STR > MAG && STR > AGI`
- Magic: `MAG > STR && MAG > AGI`
- Agility: `AGI > STR && AGI > MAG`
- Boss: `BossFightStrategy.detectBossFight() == true`

#### **game_entity.lk** - State Tracking
Entity state management (`Player`, `Enemy`, `Chest` classes):
- Tracks HP, TP, MP, position, effects, shields
- `updateEntity()` refreshes state from game API
- `hasEffect()` / `getEffectRemaining()` for effect tracking

#### **field_map.lk** - Tactical Positioning
Pre-calculates damage zones and optimal attack positions:
- **Damage Map**: Cells showing weapon/chip damage potential
- **Hit Cells**: Positions from which player can attack target
- **Star Pattern**: Line/diagonal weapons (lightninger, rifle, laser)
- **Circle Pattern**: AoE weapons (grenade launcher, electrisor)
- Uses `getCellDistance()` for accurate range validation

#### **item.lk** - Arsenal Management
`Arsenal` class manages equipped weapons & chips:
- Damage calculations with stat scaling
- Shield penetration logic
- `getNetDamageAgainstTarget()` for final damage calculation
- `getPoisonChipsSorted()` auto-detects all poison chips via `EFFECT_POISON`

#### **strategy/action.lk** - Action Types
Defines action types for queue system:
- `ACTION_DIRECT` (0), `ACTION_BUFF` (1), `ACTION_DEBUFF` (2), `ACTION_MOVEMENT` (3), `ACTION_WEAPON_SWAP` (4)
- `MOVEMENT_APPROACH` (10), `MOVEMENT_KITE` (11), `MOVEMENT_HNS` (12)
- Action captures `targetCell` at creation time (prevents stale position bugs)

#### **strategy/base_strategy.lk** - Base Combat Logic
Abstract base class providing:
- Action queue management & execution
- `executeWeaponFocusedOffensive()` - Shared by Strength & Agility
- `findHideAndSeekCell()` - Post-combat repositioning
- `checkAoESafety()` / `findSafeCellForAoE()` - Prevents self-damage
- `executeAndFlushActions()` - Mid-scenario execution for immediate state updates

#### **strategy/strength_strategy.lk** - Strength Builds
**Philosophy:** Maximize weapon damage output

**Combat Flow:**
1. Apply CHIP_STEROID buff (strength boost)
2. Apply CHIP_LIBERATION (remove debuffs / strip enemy shields)
3. Check OTKO opportunity (enemy HP < 35% or < 500 HP → teleport + weapon spam)
4. Move to best weapon damage cell from field map
5. Execute weapon-focused offensive (spam weapons, then damage chips)
6. Hide-and-seek repositioning

**Special Features:**
- OTKO teleportation for low HP enemies
- CHIP_ADRENALINE for TP boost when short by 1-4 TP
- Proper weapon spam: `while (uses < maxUse && TP >= cost)`

#### **strategy/agility_strategy.lk** - Agility Builds
**Philosophy:** Strength strategy + damage return buffs

**Combat Flow:**
1. Apply CHIP_WARM_UP (agility buff)
2. Apply damage return buff (CHIP_MIRROR or CHIP_THORN)
   - CHIP_MIRROR: 35.75% return, 3 turns, 5 TP
   - CHIP_THORN: 22.75% return, 2 turns, 4 TP
3. Execute weapon-focused offensive (shared with strength)
4. Hide-and-seek repositioning

**Key Differences:** Adds damage return layer before combat, uses CHIP_WARM_UP instead of CHIP_STEROID

#### **strategy/magic_strategy.lk** - Magic Builds
**Philosophy:** DoT kiting, burst combos, and poison attrition

**Combat Flow:**
1. **Antidote Detection** - Track enemy antidote usage via poison duration changes
   - Bait mode: Use weak poisons (TOXIN, FLAME_THROWER, DOUBLE_GUN) to burn antidote
   - Full offensive: After antidote on cooldown, apply strong poisons (COVID, PLAGUE)
2. **Poison Attrition Mode** - Hide when poison will secure kill (enemy HP < 30%, or poison damage > HP before antidote available)
3. **GRAPPLE-COVID Combo** (range 3-8, requires H/V alignment, 14-19 TP):
   - GRAPPLE (4 TP): Pull enemy to distance 2
   - COVID (8 TP): Apply uncleansable poison (~450 damage over 7 turns)
   - BOXING_GLOVE (2 TP): Push enemy away (range 2-8)
   - BALL_AND_CHAIN (5 TP): Optional MP debuff
4. **Weapon Spam** → **Poison Chips** → **Opportunistic Debuffs** → **Kite/Hide**

**Special Features:**
- **GRAPPLE-COVID Combo**: Pull → poison → push sequence with immediate execution (not queued)
- **Antidote Baiting**: Tracks `prevPoisonRemaining` to detect early cleanses, escalates when cooldown detected
- **Poison Attrition**: Hides when poison will kill (avoids counterattack damage)
- **Nova Chips**: CHIP_MUTATION (+HP buff), CHIP_DESINTEGRATION, CHIP_ALTERATION (max HP reduction)
- **AoE Safety**: Auto-repositions to avoid self-damage from TOXIN/PLAGUE/BALL_AND_CHAIN/FRACTURE

#### **strategy/boss_strategy.lk** - Boss Fight Strategy
**Philosophy:** INVERSION-priority strategy with 3-step decision tree for crystal puzzle solving

**Boss Fight Mechanics:**
- **Grail** (center): Boss with 4 colored gems
- **4 Crystals**: Movable entities projecting colored rays (must align with matching grail gems)
  - Red → SOUTH of grail (below, same X)
  - Blue → EAST of grail (right, same Y)
  - Yellow → WEST of grail (left, same Y)
  - Green → NORTH of grail (above, same X)

**Combat Flow (3-Step Decision Tree):**
1. **INVERSION Check** (even turns): Swap positions if player 3+ cells closer to target
2. **GRAPPLE/BOXING_GLOVE Check**: Use chips if on axis and in range 1-8
3. **Smart Positioning**: Move toward TARGET (odd turns) or AXIS cells (even turns)

**Available Chips:**
- **CHIP_GRAPPLE** (range 1-8, 4 TP): `useChipOnCell(CHIP_GRAPPLE, destinationCell)` - Target the DESTINATION cell where you want to pull the crystal TO (between player and crystal on same line)
- **CHIP_BOXING_GLOVE** (range 2-8, 3 TP): `useChipOnCell(CHIP_BOXING_GLOVE, destinationCell)` - Target the DESTINATION cell where you want to push the crystal TO (beyond crystal, away from player on same line)
- **CHIP_INVERSION** (range 1-14, 4 TP): `useChipOnCell(CHIP_INVERSION, crystalCell)` - Target the crystal's CURRENT cell to swap positions with it
- **CHIP_TELEPORTATION** (5 TP): Emergency repositioning

**CRITICAL:** GRAPPLE and BOXING_GLOVE target the **destination cell** (where crystal will move TO), NOT the crystal's current position. INVERSION targets the crystal's current cell.

**Team Coordination:** Uses `getEntityTurnOrder()` to assign crystals (0→red, 1→blue, 2→yellow, 3→green)

---

## Critical Bug Fixes

### Field Map & Positioning
**Star Pattern Distance Validation:** Added `getCellDistance()` validation to prevent marking out-of-range cells for star pattern weapons (lightninger, rifle, laser)

**Dead Entity Targeting:** Added `isDead()` checks in `getClosestEnemy()` and `getClosestChest()` to prevent targeting destroyed entities

**Unreachable Damage Cells:** Added `findBestReachableDamageCell()` to find highest damage cell within MP budget, preventing wasted turns moving to unreachable positions

**Fighting Retreat:** Added `findBestDamageCellOnPath()` to attack from damage cells along flee path, maximizing TP usage during retreat

### Action Queue & Execution
**Stale Target Position:** Changed attack execution to use `a.targetCell` (captured at creation) instead of `a.targetEntity._cellPos` (can become stale after movement)

**Mid-Scenario Execution:** Added `executeAndFlushActions()` for immediate movement execution when game state needs updating before continuing planning

**Chip Spam:** Changed from pre-calculated uses to `while (uses < maxUse && TP >= cost)` loop in all strategies

### Magic Strategy
**GRAPPLE-COVID Combo:**
- Added combo positioning system (`findGrappleCovidCell()` at range 3-8, H/V alignment)
- Immediate chip execution (not queued) to handle position updates: GRAPPLE → COVID → BOXING_GLOVE → BALL_AND_CHAIN (optional)
- TP preservation (skip LEATHER_BOOTS when combo available)
- H/V alignment detection for BOXING_GLOVE push calculation

**Antidote Baiting:**
- Removed time-based escalation (was forcing full offensive after 2 turns)
- Bait mode exits only when: antidote on cooldown, cleanse detected, no antidote equipped, or repeated natural expiry
- Added antidote safety checks to combo positioning and execution
- Fixed weapon spam in bait mode (was using plan's conservative estimate instead of spamming to maxUse)

**Poison Attrition:** Added defensive mode when poison will secure kill (hides to avoid counterattack damage)

**AoE Self-Damage Prevention:**
- Added `checkAoESafety()` and `findSafeCellForAoE()` methods
- Auto-repositions before using TOXIN/PLAGUE/BALL_AND_CHAIN/FRACTURE to avoid self-damage
- Fixed bait offensive to use action queue pattern instead of direct `moveTowardCell()` (was causing reposition → queued movement → back in AoE)

**Nova Chips:** Added CHIP_MUTATION (+HP buff), CHIP_DESINTEGRATION, CHIP_ALTERATION (max HP reduction) for attrition synergy

### Boss Strategy
**INVERSION Priority Refactor:**
- Removed 403 lines of complex fallback code
- Replaced with clean 3-step decision tree: INVERSION check → GRAPPLE/BOXING_GLOVE → Smart positioning
- Fixed chip availability check (was using `canUseChipOnCell()` incorrectly)
- Result: 0% chip usage → 78 chip uses per fight, TELEPORTATION reduced from 42 to 3

**Chip Targeting Fix:**
- Fixed BOXING_GLOVE and GRAPPLE to target DESTINATION cell (where crystal will move TO), not crystal's current position
- Was targeting `crystalPos + direction` for BOXING_GLOVE, changed to target the actual destination cell
- GRAPPLE now correctly targets the cell between player and crystal (pull destination)
- INVERSION correctly targets crystal's current cell to swap with entity on that cell
- Error -4 (invalid target) eliminated → chips now execute successfully

---

## Development Workflow

**Automated Testing (January 2026):**
1. Edit files in `/V8_modules/` → Upload: `python3 tools/upload_v8.py`
2. Run tests: `python3 tools/lw_test_script.py <num_fights> <script_id> <opponent>` or `--scenario graal`
3. Analyze logs (saved to `fight_logs_*.json` and `log_analysis_*.txt`)
4. Iterate on fixes

**Available Test Opponents:** domingo (strength), betalpha (magic), tisma/guj/hachess/rex (various builds)

---

## Week 1 Implementation Summary (Completed)

### Changes Deployed

**Base Strategy (base_strategy.lk)**
1. **projectTotalDamageOutput()** (lines 415-545)
   - Accurate damage projection with optional buff inclusion
   - Validates range/LOS for each weapon/chip from specified cell
   - Used by Strength OTKO to determine if teleport will secure kill

2. **selectBestTarget()** (lines 347-400)
   - Strategy-specific target prioritization
   - Strength/Agility: Lowest HP first (finish kills)
   - Magic: Targets without DoT preferred (fresh targets)
   - Universal distance penalty (prefer closer enemies)

3. **findAlternativeMovementCell()** (lines 1429-1456)
   - Finds fallback cells when primary target unreachable
   - Strategy 1: Best reachable damage cell within MP budget
   - Strategy 2: Furthest reachable cell on path to target

4. **detectFightType()** (lines 611-660)
   - Detects fight type: PvP, Boss, Chest, PvE
   - Boss: Skips all buffs (need TP for GRAPPLE/INVERSION)
   - Chest: Skips all buffs (pure damage spam)
   - PvP: Applies all buffs (long fights)
   - PvE: Skips universal buffs (save TP)

5. **Enhanced validateAndFilterActions()** (lines 1458-1591)
   - Adds fallback movements instead of removing invalid actions
   - Tracks fallbacks added for debugging
   - Prevents empty action queues

**Strength Strategy (strength_strategy.lk)**
- Improved OTKO check (lines 704-737)
  - Uses projectTotalDamageOutput() instead of HP threshold
  - Includes STEROID buff (+160 STR) in damage calculation
  - Only triggers teleport when kill is guaranteed

**Magic Strategy (magic_strategy.lk)**
- Static antidote state (lines 13-34)
  - Persists _prevPoisonRemaining, _recentAntidoteTurn, _baitMode, _baitStartTurn
  - Resets on turn 1 or first initialization
  - Enables accurate tracking across multiple turns

- Burst mode (lines 97-105)
  - Forces full offensive after 3 turns of unsuccessful baiting
  - Prevents infinite bait loops vs persistent antidote users

**Magic Combo System (magic_combo_system.lk)**
- Path validation (lines 104-127)
  - Checks getPath() between player and target
  - Validates pull destination is not obstacle/occupied
  - Prevents GRAPPLE failures due to blocked paths

### Bug Fixes
1. **Map iteration in detectFightType()** - Converted maps to arrays for proper iteration
2. **Subclass method calls** - Replaced this.shouldUseSteroid() with direct availability checks

### Testing Results
- All modules compile without errors
- No type incompatibility warnings
- Ready for combat testing

---

## Week 2 Implementation Summary (Completed)

### Changes Deployed

**Field Map Tactical (field_map_tactical.lk)**
1. **Enemy Threat Map System** (lines 311-558)
   - Movement-aware threat calculation (enemy can MOVE then ATTACK)
   - Builds threat map from all reachable positions within enemy MP budget
   - Caches threat map per turn with enemy position validation
   - `getThreatAtCell()` returns total damage threat at any cell
   - `getSafeCells()` finds zero-threat cells within MP budget
   - `findBestTacticalCell()` balances damage vs threat with weight parameter

2. **Field Map Core** (field_map_core.lk)
   - Changed `x_offset` and `y_offset` from `private static` to `static` (public)
   - Allows subclass FieldMap to access coordinate system for threat calculations

**Base Strategy (base_strategy.lk)**
1. **Threat-Based Emergency Mode** (lines 1372-1417)
   - Priority 1: Immediate lethal threat (current threat ≥ player HP)
   - Priority 2: Two-turn lethal (threat × 2 > player HP)
   - Priority 3: High threat + medium HP (threat > 30% max HP and HP < 50%)
   - Always skips emergency if lethal opportunity exists (hasLethalOpportunity)

**Magic Strategy (magic_strategy.lk)**
1. **Safe Kiting System** (lines 40-80)
   - `findSafeKitingCell()` finds zero-threat cells with attack capability
   - Prioritizes safe cells over standard hide-and-seek
   - Allows attacking while completely safe from retaliation

2. **Integration** (lines 336-350)
   - Safe kiting used before standard kiting/hiding
   - Falls back to hide-and-seek if no safe cells found

**Agility Strategy (agility_strategy.lk)**
1. **CHIP_LIBERATION Support** (lines 72-119)
   - Removes critical player debuffs (SHACKLE_TP, SHACKLE_STRENGTH, etc.)
   - Removes significant poison (≥3 turns remaining)
   - Strips enemy shields (relative > 15% or absolute > 30)
   - Counters enemy damage return buffs (Mirror vs Mirror)

2. **Hit-and-Run Tactics** (lines 197-221)
   - Threat-weighted cell scoring: `damage - (threat × weight)`
   - Default 40% threat weight balances offense and defense
   - Uses `findBestTacticalCell()` from field map

**Strength Strategy (strength_strategy.lk)**
1. **GRAPPLE-HEAVY_SWORD Path Validation** (lines 593-630)
   - Validates clear path between player and target using `getPath()`
   - Checks pull destination is not obstacle or occupied by another entity
   - Prevents combo failures due to blocked paths

2. **GRAPPLE Targeting Fix** (lines 662-690)
   - **CRITICAL FIX:** Target opposite side of player from enemy
   - GRAPPLE pulls first entity on line TOWARD target cell
   - OLD: Targeted between player and enemy → no entity on short line → error -4
   - NEW: Targets opposite side → pulls enemy toward that cell → brings enemy adjacent
   - Example: Player (0,0), enemy (5,0) right → target (-2,0) left → pulls enemy toward (-2,0)

**Main Entry Point (main.lk)**
1. **Threat Map Build** (line 79)
   - Calls `fieldMap.buildEnemyThreatMap()` after damage map build
   - Provides threat data to all strategies for tactical positioning

### Bug Fixes
1. **LeekScript 4 API compatibility** - Replaced `getCellsInRadius()` with manual grid iteration
2. **LeekScript 4 weapon effects** - Replaced `getWeaponMinScope/MaxScope` with `getWeaponEffects()`
3. **Private static field access** - Made FieldMapCore coordinate offsets public for subclass access
4. **GRAPPLE targeting** - Fixed to target opposite side of player (pulls enemy toward target)

### Testing Results
- All modules compile without errors
- Fixed 5 compilation/runtime errors during implementation
- GRAPPLE now successfully pulls enemies adjacent to player
- Threat map provides accurate movement-aware positioning data

---

## December 2025 Bug Fixes (Completed)

### Critical Combat Bugs Fixed

**Bug #1: Weapon Swap Validation Too Strict**
- **Problem:** Validation was checking if player had full weapon cost (e.g., 9 TP for enhanced_lightninger) for weapon swap actions, instead of just 1 TP
- **Impact:** After using FORTRESS (6 TP), weapon attacks were incorrectly removed during validation even when 16 TP remained
- **Fix:** `base_strategy.lk:1671-1690`
  - Separated weapon swap validation (requires 1 TP) from weapon attack validation (requires full cost)
  - Added explicit check: `if (action.type == Action.ACTION_WEAPON_SWAP)`
- **Result:** AI now correctly attacks after using defensive buffs

**Bug #2: GRAPPLE-HEAVY_SWORD Syntax Error**
- **Problem:** Used incorrect LeekScript API `useWeapon(weaponId, targetId)` which caused INVALID_PARAMETER_COUNT error
- **Impact:** Combo failed to execute, causing script crashes
- **Fix:** `strength_strategy.lk:645-646, 699-700`
  - Changed from `useWeapon(WEAPON_HEAVY_SWORD, target._id)`
  - To `setWeapon(WEAPON_HEAVY_SWORD)` + `useWeaponOnCell(target._cellPos)`
- **Result:** Combo now executes successfully

**Bug #3: Fighting Retreat Stranding**
- **Problem:** `findBestReachableDamageCell()` picked highest damage cell without checking if escape route to safety was preserved
- **Impact:** AI moved to high-damage cells (e.g., cell 170 with 1274 damage) but couldn't reach safe cell afterward, getting stranded in enemy threat zone
- **Example:** Cell 136 → move to 170 (2 MP) → attack → 5 MP remaining, but safe cell 157 requires 13+ MP
- **Fix:** `base_strategy.lk:620-674, 1367`
  - Created new method `findDamageCellOnEscapeRoute(safeCell, maxMP)`
  - Gets path from current position to safe cell
  - Only considers damage cells ON this path
  - Validates: `remainingMP >= distToSafeFromHere` before selecting cell
  - Ensures escape route is preserved after stopping to attack
- **Result:** AI now attacks from cells that maintain path to safety, preventing tactical stranding

**Bug #4: Magic Strategy Validation Failure (MP=-1)**
- **Problem:** Magic strategy's `createAndExecuteDotKite()` never initialized `this._originalTP` and `this._originalMP`, leaving them at default value -1
- **Impact:** Validation system read MP=-1, causing all actions to fail validation checks with "requires X MP but only have -1" errors. Magic AI couldn't move or attack - completely broken.
- **Fix:** `magic_strategy.lk:90-91`
  - Added initialization at start of `createAndExecuteDotKite()`: `this._originalTP = player._currTp` and `this._originalMP = player._currMp`
  - Removed obsolete manual restoration code that was trying to work around the missing initialization
- **Result:** Magic strategy validation now works correctly, actions execute as planned

**Bug #5: Strength Strategy updateEntity() Parameter Error**
- **Problem:** Called `target.updateEntity(target._id)` with parameter, but `updateEntity()` method takes no parameters
- **Impact:** Script crashed with "NoSuchFieldException: updateEntity" error after GRAPPLE-HEAVY_SWORD combo execution
- **Fix:** `strength_strategy.lk:696, 786`
  - Changed from `target.updateEntity(target._id)` to `target.updateEntity()`
  - Fixed both occurrences in GRAPPLE-HEAVY_SWORD combo execution
- **Result:** Combo executes without errors, enemy position updates correctly after GRAPPLE pull

### Changes Made

**File: V8_modules/strategy/base_strategy.lk**
1. **Weapon Swap Validation** (lines 1671-1690)
   - Split validation logic for weapon swaps vs weapon attacks
   - Weapon swaps now correctly require 1 TP instead of full weapon cost

2. **Fighting Retreat Escape Route** (lines 620-674)
   - New method `findDamageCellOnEscapeRoute(safeCell, maxMP)`
   - Replaced `findBestReachableDamageCell()` call with escape-route-aware version
   - Validates remaining MP can reach safe cell after attacking

**File: V8_modules/strategy/strength_strategy.lk**
1. **GRAPPLE-HEAVY_SWORD API Fix** (lines 645-646, 699-700)
   - Fixed `useWeapon()` syntax to use correct LeekScript 4 API
   - Changed to `setWeapon() + useWeaponOnCell()` pattern

2. **updateEntity() Parameter Error** (lines 696, 786)
   - Removed incorrect parameter from `updateEntity()` calls
   - Changed from `target.updateEntity(target._id)` to `target.updateEntity()`
   - Method signature takes no parameters

**File: V8_modules/strategy/magic_strategy.lk**
1. **Validation Initialization** (lines 90-91)
   - Added `this._originalTP = player._currTp` and `this._originalMP = player._currMp` at start of `createAndExecuteDotKite()`
   - Ensures validation system has correct starting resources
   - Removed obsolete manual restoration attempt (lines 389-391 deleted)

### Testing Results
- All modules compile without errors
- GRAPPLE-HEAVY_SWORD combo executes successfully without crashes
- Weapon attacks now trigger after FORTRESS/defensive buffs
- Fighting retreat preserves escape route to safety
- No tactical stranding in emergency scenarios
- Magic strategy validation now works correctly (actions no longer removed)
- Magic AI can move, attack, and execute full combat strategy

### Enhancement: CHIP_REMISSION TP Dump (December 3, 2025)

**Feature:** Added CHIP_REMISSION as automatic TP dump across all strategies
- **Purpose:** Spend remaining TP productively on instant healing instead of wasting it
- **Cost:** 5 TP per use
- **Benefit:** ~100-150 HP instant heal (scales with wisdom)
- **Trigger:** Applied at end of combat actions when TP >= 5 and chip off cooldown

**Files Modified:**
1. **base_strategy.lk (line ~1278):** Added CHIP_REMISSION to `executeWeaponFocusedOffensive()` before return statement
   - Benefits: Strength and Agility strategies automatically
   - Executes after all weapon spam and chip usage, before HNS movement returns

2. **magic_strategy.lk (line ~681):** Added CHIP_REMISSION to `createFullOffensiveDoT()` after debuffs
   - Executes after weapon spam, poison chips, nova chips, and debuffs
   - Queued as action for validation

3. **boss_strategy.lk (line ~806):** Added CHIP_REMISSION to `executeTurn()` after crystal placement
   - Uses direct execution (not queued) since boss strategy doesn't use action queue
   - Ensures remaining TP is spent on healing in puzzle fights

**Result:** All strategies now automatically use excess TP for healing, improving survivability without manual intervention

---

## V8 Strategy Analysis & Improvement Plan

### Strategy Performance Matrix

| Strategy | Strengths | Critical Weaknesses | Priority Fixes |
|----------|-----------|-------------------|----------------|
| **Strength** | OTKO system, GRAPPLE-HS combo, defensive chips | OTKO threshold too simple, combo blocks OTKO, post-combo limited | Fix OTKO calculation, reorder combo logic |
| **Magic** | Antidote baiting, GRAPPLE-COVID, poison attrition, AoE safety | Antidote state not persisted, no combo path validation, stuck in bait loop | Persist state, validate pull path, add burst mode |
| **Agility** | Clean implementation, proper buff priority, TP validation | No unique tactics, doesn't leverage agility advantages | Add mobility tactics, evasive positioning |
| **Base** | Validation system, fighting retreat, lethal detection | Validation removes without fallback, blind turn 1 buffs | Add fallback suggestions, smart buff detection |

---

### Strength Strategy Improvements

**Critical Issues:**

| Issue | Impact | Line Reference |
|-------|--------|----------------|
| OTKO threshold too simple (35% HP or 500 HP) | Wastes teleport CD when can't actually kill | strength_strategy.lk:706 |
| Combo blocks OTKO even when viable | Logic order causes positioning → miss kill | strength_strategy.lk:721-764 |
| Post-combo only checks LIGHTNINGER | Ignores other secondary weapons | strength_strategy.lk:862-888 |
| INVERSION skipped if combo attempted | Misses heal+vulnerability opportunity | strength_strategy.lk:790 |
| THERAPY limited to <25% HP | Too restrictive for safe healing | strength_strategy.lk:776 |

**Implementation Priority:**

```
PRIORITY 1 (High Impact, Low Risk):
✅ Fix OTKO damage calculation: Include STEROID buff in projection (COMPLETED Week 1)
□ Reorder combo vs OTKO: Check OTKO FIRST, only combo if OTKO fails
□ Add post-combo secondary weapon loop (not just LIGHTNINGER)

PRIORITY 2 (Medium Impact):
□ INVERSION conditional: Allow even after failed combo attempt
□ Expand THERAPY threshold: 25-40% HP with threat assessment
□ Add target selection: Prioritize lowest HP enemy (finish kills)

PRIORITY 3 (Polish):
□ FORTRESS/WALL threat-based: Check if enemy can attack this turn
□ Validate combo pull path: Check obstacles before GRAPPLE
```

---

### Magic Strategy Improvements

**Critical Issues:**

| Issue | Impact | Line Reference |
|-------|--------|----------------|
| Antidote state not persisted | Resets baiting logic every turn | magic_strategy.lk:14-17 |
| Combo doesn't validate pull path | GRAPPLE fails if obstacles present | magic_strategy.lk:357-360 |
| No burst mode vs persistent antidote | Stuck in bait loop against smart opponents | magic_strategy.lk:243-247 |
| Kiting distance not optimized | Uses hide cells but not safe range calculation | magic_strategy.lk:268-292 |
| DESINTEGRATION/ALTERATION thresholds arbitrary | 75%/100% thresholds ignore fight state | magic_strategy.lk:545-568 |

**Implementation Priority:**

```
PRIORITY 1 (High Impact):
✅ Persist antidote state: Use static variables across turns (COMPLETED Week 1)
✅ Add combo path validation: Check getPath() before GRAPPLE (COMPLETED Week 1)
✅ Implement burst mode: Switch to damage after 3+ bait turns (COMPLETED Week 1)

PRIORITY 2 (Medium Impact):
□ Calculate optimal kite range: Use base.calculateOptimalKiteDistance()
□ Improve poison attrition: Compare (poison DPT * turns) vs enemy HP
□ Add weapon-only fallback: Play like strength if poison chips on CD

PRIORITY 3 (Optimization):
□ Nova chip thresholds: Tie to remaining poison turns
□ LEATHER_BOOTS reservation: Only skip if combo executes THIS turn
```

---

### Agility Strategy Improvements

**Critical Issues:**

| Issue | Impact | Line Reference |
|-------|--------|----------------|
| No unique tactics | Just "strength + return buff" | agility_strategy.lk:4-162 |
| Doesn't leverage agility advantages | Ignores dodge, mobility bonuses | agility_strategy.lk:75-161 |
| Return buff timing conservative | Reapplies at ≤1 turn, could optimize | agility_strategy.lk:52-70 |
| No threat-based buff decisions | Always applies regardless of enemy damage | agility_strategy.lk:106-123 |
| Missing multi-target synergy | Return buff wasted in 1v1 | agility_strategy.lk:14-36 |

**Implementation Priority:**

```
PRIORITY 1 (High Impact - Make Agility Unique):
□ Add mobility advantage: LEATHER_BOOTS + MP for hit-and-run
□ Implement evasive positioning: Prefer diagonal movements
□ Return buff optimization: Apply BEFORE damage, track enemy TP

PRIORITY 2 (Medium Impact):
□ Smart buff timing: Apply when enemy has TP for attack
□ Add ADRENALINE bridge: Use when 1-4 TP short of buff+spam
□ Multi-enemy detection: Boost return priority in 2v1/3v1

PRIORITY 3 (Polish):
□ Return buff duration math: Don't reapply if fight ends in 1 turn
□ Aggressive repositioning: Circle enemies to maximize return
```

---

### Base Strategy Improvements

**Critical Issues:**

| Issue | Impact | Line Reference |
|-------|--------|----------------|
| Validation removes without fallback | Leaves strategies with no actions | base_strategy.lk:1290-1401 |
| Turn 1 buffs applied blindly | Wastes buffs in wrong fight types | base_strategy.lk:463-513 |
| Emergency mode fixed at 35% HP | Ignores lethal threats at higher HP | base_strategy.lk:1147-1167 |
| Defensive always flees | Sometimes standing ground is better | base_strategy.lk:993-1100 |
| Kiting distance unused | Calculated but no strategy uses it | base_strategy.lk:308-335 |

**Implementation Priority:**

```
PRIORITY 1 (High Impact):
✅ Validation with fallback: Suggest reachable alternatives (COMPLETED Week 1)
✅ Smart turn 1 buffs: Detect fight type before applying (COMPLETED Week 1)
□ Threat-based emergency: Enter defensive if (damage * 2) > HP

PRIORITY 2 (Core Improvements):
□ Integrate kiting distance: Magic should use calculateOptimalKiteDistance()
□ Defensive stance option: Stand ground if damage > enemy HP
□ TP/MP simulation: Track consumed resources in validation

PRIORITY 3 (Polish):
□ Healing verification caching: Don't recalculate every check
□ Ally coordination hooks: Static variables for target assignment
```

---

### Cross-Strategy Improvements

**1. Target Selection System** (affects ALL strategies)

Add to `base_strategy.lk` around line 337:

```leekscript
selectBestTarget() {
    var enemies = fieldMap.getEnemySubMap()
    var best = null
    var bestScore = -1

    for (var e in enemies) {
        if (isDead(e._id)) continue
        var score = 0

        // Strength/Agility: Prioritize lowest HP (finish kills)
        if (this.getStrategyName() == "STR" || this.getStrategyName() == "AGI") {
            score = 10000 - e._currHealth
        }
        // Magic: Prioritize no DoT (fresh targets)
        else if (this.getStrategyName() == "MAGIC") {
            if (!e.hasEffect(EFFECT_POISON)) score += 5000
            score += (10000 - e._currHealth)
        }

        // Universal: Prefer closer enemies
        var dist = getCellDistance(player._cellPos, e._cellPos)
        if (dist != null) score -= dist * 10

        if (score > bestScore) {
            bestScore = score
            best = e
        }
    }
    return best
}
```

**2. Resource Reservation System** (affects buffing logic)

Add to `base_strategy.lk` around line 305:

```leekscript
calculateRequiredTPForTurn() {
    var required = 0

    // Reserve TP for known combos
    if (this.getStrategyName() == "STR") {
        if (mapContainsKey(arsenal.playerEquippedChips, CHIP_GRAPPLE) &&
            mapContainsKey(arsenal.playerEquippedWeapons, WEAPON_HEAVY_SWORD)) {
            required = 18  // GRAPPLE + HEAVY_SWORD
        }
    }
    else if (this.getStrategyName() == "MAGIC") {
        // Check if GRAPPLE-COVID combo available
        if (mapContainsKey(arsenal.playerEquippedChips, CHIP_GRAPPLE) &&
            mapContainsKey(arsenal.playerEquippedChips, CHIP_COVID)) {
            required = 13
        }
    }

    // Always reserve minimum weapon cost
    required += this.calculateMinimumAttackTP()

    return required
}
```

**3. Damage Projection Accuracy**

Add to `base_strategy.lk` around line 411:

```leekscript
projectTotalDamageOutput(includeBuffs = false) {
    var totalDamage = 0
    var playerTP = player._currTp
    var buffBonus = 0

    // Include pending buff effects if requested
    if (includeBuffs) {
        if (this.getStrategyName() == "STR" && this.shouldUseSteroid()) {
            buffBonus = 160  // STEROID average boost
            playerTP -= 7
        }
        else if (this.getStrategyName() == "AGI" && this.shouldUseWarmUp()) {
            buffBonus = 180  // WARM_UP average boost (agility)
            playerTP -= 7
        }
    }

    // Calculate weapon spam damage from current position
    if (mapContainsKey(fieldMap.damageMap, player._cellPos)) {
        var cell = fieldMap.damageMap[player._cellPos]
        for (var w in cell._weaponsList) {
            var uses = min(w._maxUse, floor(playerTP / w._cost))
            var bd = arsenal.getDamageBreakdown(
                player._strength + buffBonus,
                player._magic,
                player._wisdom,
                w._id
            )
            totalDamage += bd['total'] * uses
            playerTP -= w._cost * uses
        }
    }

    // Add chip damage
    for (var c in arsenal.playerEquippedChips) {
        if (playerTP < c._cost) continue
        if (getCooldown(c._id, player._id) > 0) continue
        if (!mapContainsKey(c._effects, EFFECT_DAMAGE) &&
            !mapContainsKey(c._effects, EFFECT_POISON)) continue
        var bd = arsenal.getDamageBreakdown(player._strength, player._magic, player._wisdom, c._id)
        totalDamage += bd['total']
        playerTP -= c._cost
    }

    return totalDamage
}
```

---

### Implementation Roadmap

**Week 1: Critical Fixes (January 27-31, 2026) - ✅ COMPLETE**
- [x] Fix strength OTKO damage calculation (include buffs)
- [x] Add magic antidote state persistence (static vars)
- [x] Implement base target selection system
- [x] Add validation with fallback suggestions
- [x] Smart turn 1 buff detection
- [x] Fix map iteration bug in detectFightType()
- [x] Fix subclass method call in projectTotalDamageOutput()

**Week 2: Strategy-Specific (February 3-7, 2026) - ✅ COMPLETE**
- [x] Magic burst mode vs persistent antidote (completed in Week 1)
- [x] Magic combo path validation (GRAPPLE obstacles - completed in Week 1)
- [x] Enemy threat map system (movement-aware threat calculation)
- [x] Threat-based emergency mode (lethal detection, two-turn kill)
- [x] Safe kiting for magic (zero-threat cell positioning)
- [x] CHIP_LIBERATION support for agility
- [x] Agility hit-and-run tactics (threat-weighted cell scoring)
- [x] Strength GRAPPLE-HEAVY_SWORD path validation
- [x] Fixed GRAPPLE targeting (target opposite side to pull enemy)

**Week 3: Cross-Strategy Enhancements (February 10-14, 2026)**
- [ ] Resource reservation system
- [ ] Damage projection accuracy
- [ ] Kiting distance integration for magic
- [ ] Post-combo secondary weapon loop (strength)
- [ ] Return buff optimization (agility)

**Week 4: Polish & Testing (February 17-21, 2026)**
- [ ] INVERSION conditional logic (strength)
- [ ] Nova chip threshold optimization (magic)
- [ ] Multi-enemy detection (agility)
- [ ] Defensive stance option (base)
- [ ] Comprehensive integration testing

**Testing Protocol:**
- 20 fights per opponent per change
- Compare win rate, average damage, survival rate
- Log analysis for action validation rates
- Regression testing on all 4 strategies

---

## Areas for Improvement (Legacy Notes)

**Action Queue Validation:** ✅ COMPLETE - Implemented with validation system and fallback suggestions (Week 1)

**Emergency Mode:** ✅ COMPLETE - Threat-based triggers implemented (immediate lethal, two-turn kill) (Week 2)

**Target Selection:** ✅ COMPLETE - Strategy-specific prioritization (lowest HP for STR/AGI, fresh targets for MAGIC) (Week 1)

**Magic Kiting Distance:** ✅ COMPLETE - Safe kiting with zero-threat cell positioning (Week 2)

**OTKO Improvements:** ✅ COMPLETE - Damage projection includes buff effects (Week 1)

**Ally Coordination:** Add static variables for target assignments in multi-leek fights

**Resource Management:** ✓ Implemented with calculateMinimumAttackTP(), needs reservation system

**Hide-and-Seek Selection:** Add cover score (obstacles, LOS, escape routes) to distance metric

**Weapon Swap Optimization:** Track current weapon, skip swap if already optimal

**Field Map Caching:** Cache damage map with key `enemyID_position`, invalidate on movement

---

## Key Commands

**Upload:** `python3 tools/upload_v8.py`

**Test:** `python3 tools/lw_test_script.py <num_fights> <script_id> <opponent>`
- Example: `python3 tools/lw_test_script.py 20 447461 domingo`
- Opponents: domingo (strength), betalpha (magic), tisma/guj/hachess/rex (various)
- Boss: `--scenario graal`

**Logs:** Saved locally to `fight_logs_*.json` and `log_analysis_*.txt` (NOT accessible via URL/CURL)

---

## LeekScript Programming Notes

**Built-in Constants:** All `WEAPON_*`, `CHIP_*`, `EFFECT_*` constants are part of LeekScript language (no need to define)

**Coordinate System:** Map center [0,0], corners [-17,0] to [17,0], total 612 cells (35x35 grid)

**Debugging:** Use `debug()` for AI output, check local log files for analysis

---

## Development Best Practices

1. Run 10-20 fights per opponent for statistical significance
2. Test after each modification (incremental changes)
3. NEVER call `useChip()`, `useWeapon()`, `moveTowardCell()` directly in strategies (use action queue)
4. Update player state (TP/MP/position) after queuing actions
5. Capture `targetEntity._cellPos` at action creation time (prevents stale position bugs)

---

**Script ID:** 447626 (V8 main.lk - Current production, December 2025)

*Document Version: 28.0 | Last Updated: December 3, 2025 - CHIP_REMISSION TP Dump Enhancement*
