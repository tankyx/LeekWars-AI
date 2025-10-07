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
│       └── boss_strategy.lk     # Boss fight strategy (skeleton)
└── tools/              # Python automation
    ├── lw_test_script.py # Testing with log retrieval
    └── upload_v8.py     # V8 deployment
```

---

## V8 System Architecture

### Core Philosophy: Action Queue Pattern

V8 uses a **two-phase execution model**:

1. **Planning Phase** - Strategy creates actions and queues them in `this._actions`
2. **Execution Phase** - `executeScenario()` iterates through queue and executes via action executors

**Key Principle:** Strategies NEVER call `useChip()`, `useWeapon()`, or `moveTowardCell()` directly during planning. All game-modifying operations happen in the execution phase.

#### Why This Architecture?

**Benefits:**
- **Separation of Concerns**: Planning logic separate from execution
- **Testability**: Action queues can be inspected before execution
- **Consistency**: All strategies follow the same execution flow
- **Debugging**: Actions visible in debug logs before execution
- **State Management**: Player state (TP/MP/position) updated consistently

**Example Flow:**
```
Strategy Planning:
1. calculateBestCell() → finds optimal position
2. createMovementAction() → queues movement
3. createAttackAction() → queues weapon attack
4. createAttackAction() → queues chip attack

Execution Phase:
5. executeScenario() loops through queue:
   - ACTION_MOVEMENT → moveTowardCell()
   - ACTION_DIRECT (weapon) → setWeapon() + useWeapon()
   - ACTION_DIRECT (chip) → useChip()
```

### Module Breakdown

#### **main.lk** - Entry Point & Strategy Selection
- Detects build type (Strength/Magic/Agility/Boss)
- Instantiates appropriate strategy class
- Delegates all combat decisions to strategy

**Build Detection:**
```
Strength: STR > MAG && STR > AGI
Magic:    MAG > STR && MAG > AGI
Agility:  AGI > STR && AGI > MAG
Boss:     BossFightStrategy.detectBossFight() == true
```

#### **game_entity.lk** - State Tracking
- `Player` class: Current leek stats (HP, TP, MP, position, effects)
- `Enemy` class: Enemy stats with shield/effect tracking
- `Chest` class: Treasure chest entities
- `updateEntity()`: Refreshes entity state from game API

**Critical Methods:**
- `hasEffect()` / `getEffectRemaining()` - Effect tracking
- `hasDamageReturn()` - Agility strategy buff tracking
- `updateEntity()` - Refreshes position/stats from game state

#### **field_map.lk** - Tactical Positioning
- Calculates damage zones for all equipped weapons/chips
- Builds hit maps showing optimal attack positions
- Tracks obstacles, entities, and line-of-sight

**Key Concepts:**
- **Damage Map**: Pre-calculated cells showing weapon/chip damage potential
- **Hit Cells**: Positions from which player can attack target
- **Star Pattern**: Line/diagonal weapons (lightninger, rifle, laser)
- **Circle Pattern**: AoE weapons (grenade launcher, electrisor)

**Critical Bug Fix (October 2025):**
- Star pattern distance validation using `getCellDistance()` (lines 542-543, 569-570)
- Prevents marking cells as in-range when they're beyond weapon max range

#### **item.lk** - Arsenal Management
- `Arsenal` class: Manages equipped weapons & chips
- Damage calculations with stat scaling
- Shield penetration logic

**Key Methods:**
- `getNetDamageAgainstTarget()` - Calculates final damage after shields
- `getDamageReturnValue()` - Agility damage return % calculation
- `getHighestDamageWeapon()` - Fallback weapon selection

#### **strategy/action.lk** - Action Types
Defines all action types for the queue system:
```
ACTION_DIRECT        = 0  // Direct weapon/chip attack
ACTION_BUFF          = 1  // Buff chip (MIRROR, THORN, STEROID, etc.)
ACTION_DEBUFF        = 2  // Debuff chip (LIBERATION, INVERSION, etc.)
ACTION_MOVEMENT      = 3  // Movement actions
ACTION_WEAPON_SWAP   = 4  // Weapon switching
ACTION_TELEPORT      = 14 // Teleportation (special handling)

MOVEMENT_APPROACH    = 10 // Move toward target
MOVEMENT_KITE        = 11 // Move away from target
MOVEMENT_HNS         = 12 // Hide and seek positioning
```

**Action Structure:**
```
class Action {
    type         // Action type (see constants above)
    weaponID     // Weapon ID (if weapon attack)
    chip         // Chip ID (if chip attack)
    targetCell   // Target cell (captured at creation time)
    targetEntity // Target entity (reference only)
}
```

#### **strategy/base_strategy.lk** - Base Combat Logic
Abstract base class providing:
- Action queue management (`this._actions`)
- Action executors (converts actions to API calls)
- Shared combat logic (weapon-focused offensive, HNS positioning)
- Movement planning

**Core Methods:**

**Action Creation:**
- `createAttackAction(type, target, targetCell, weaponOrChip)` - Queue attack
- `createMovementAction(type, targetCell, target)` - Queue movement

**Execution:**
- `executeScenario()` - Main executor loop
- `executeAndFlushActions()` - Mid-scenario execution for immediate state updates

**Shared Combat Logic:**
- `executeWeaponFocusedOffensive()` - Used by Strength & Agility strategies
- `findHideAndSeekCell()` - Post-combat repositioning
- `moveTowardCell()` / `moveAwayFromEnemy()` - Movement helpers

**Critical Bug Fix (October 2025):**
- Attack execution uses `a.targetCell` instead of `a.targetEntity._cellPos` (lines 550, 553)
- Prevents stale position bugs after `executeAndFlushActions()`

#### **strategy/strength_strategy.lk** - Strength Builds
**Philosophy:** Maximize weapon damage output

**Combat Flow:**
1. Check for CHIP_STEROID buff (apply if needed)
2. Check for CHIP_LEATHER_BOOTS (mobility buff if target unreachable)
3. Check for CHIP_LIBERATION (remove debuffs/enemy shields)
4. Check for OTKO opportunity (low HP enemies)
5. Select best weapon damage cell from field map
6. Execute weapon-focused offensive:
   - Move to weapon cell
   - Spam primary weapon (highest damage) to max uses
   - Use secondary weapons
   - Spend leftover TP on damage chips (sorted by damage)
7. Hide-and-seek repositioning

**Special Features:**
- **OTKO Teleportation**: When enemy HP < 35% or < 500 HP, teleport + weapon spam
- **CHIP_LIBERATION**: Tactical debuff removal (player) or shield stripping (enemy)
- **CHIP_ADRENALINE**: +4 TP when short by 1-4 TP for attacks
- **Weapon Spam**: Uses `while (actualUses < maxUse && TP >= cost)` for proper chip spam

**Files:**
- `/V8_modules/strategy/strength_strategy.lk` (397 lines)

#### **strategy/agility_strategy.lk** - Agility Builds
**Philosophy:** Strength strategy + damage return buffs

**Combat Flow:**
1. Check for CHIP_WARM_UP (agility buff, apply if needed)
2. Check for CHIP_LEATHER_BOOTS (mobility buff if target unreachable)
3. **Check for damage return buff (CHIP_MIRROR or CHIP_THORN)**:
   - CHIP_MIRROR: 35.75% damage return (5-6% base * agility scaling), 3 turns, 5 TP
   - CHIP_THORN: 22.75% damage return (3-4% base * agility scaling), 2 turns, 4 TP
   - Reapply if no active buff or remaining ≤ 1 turn
4. Select best weapon damage cell (same as strength strategy)
5. Check for CHIP_ADRENALINE (TP boost if needed)
6. Execute weapon-focused offensive (shared with strength)
7. Hide-and-seek repositioning

**Key Differences from Strength:**
- Adds damage return buff layer before combat
- Uses CHIP_WARM_UP instead of CHIP_STEROID
- 95% code reuse with strength strategy

**Refactoring (October 2025):**
- Complete rewrite using strength_strategy.lk as template
- Eliminated custom cell selection logic (was ignoring pre-calculated best cells)
- Fixed weapon sorting (was by maxUse instead of damage)
- Reduced from 237 lines to 222 lines (6% reduction)

**Files:**
- `/V8_modules/strategy/agility_strategy.lk` (222 lines)

#### **strategy/magic_strategy.lk** - Magic Builds
**Philosophy:** DoT kiting, burst combos, and poison attrition

**Combat Flow:**
1. **Antidote Detection**: Track enemy antidote usage via poison duration changes
   - Bait mode: Use weak poisons (TOXIN, FLAME_THROWER) to burn antidote cooldown
   - Full offensive: After antidote used, apply strong poisons (COVID, PLAGUE)
2. **Poison Attrition Mode**: If poison active and enemy vulnerable, hide instead of fighting
   - Triggers when: poison will kill before antidote available, OR enemy HP < 30%, OR enemy HP < 50% with antidote on cooldown
   - Skips all attacks, moves to Hide & Seek cell to avoid counterattack damage
3. **GRAPPLE-COVID Combo** (range 3-8, requires horizontal/vertical alignment):
   - GRAPPLE (4 TP): Pull enemy to range 1-2
   - COVID (8 TP): Apply uncleansable poison (~450 damage over 7 turns)
   - BOXING_GLOVE (2 TP): Push enemy away (max range 2-8 cells)
   - BALL_AND_CHAIN (5 TP): Optional MP debuff if available
   - Total: 14-19 TP burst combo
4. **Weapon Spam First**: Use all weapon attacks before spending TP on chips
5. **Poison Chips**: Apply remaining DoT chips (TOXIN, PLAGUE, VENOM)
6. **Opportunistic Debuffs**: BALL_AND_CHAIN, FRACTURE with leftover TP
7. **Kite/Hide**: Reposition to safe distance after attacks

**Special Features:**
- **GRAPPLE-COVID Combo**: High-damage burst with pull → poison → push mechanics
  - Immediate execution pattern (not queued) to handle position updates between chips
  - BOXING_GLOVE only works on horizontal/vertical lines (NOT diagonals)
  - Uses `lineOfSight()` to find valid push cells without obstacles
  - BALL_AND_CHAIN optional (executes if equipped + off cooldown + 19 TP available)
- **Antidote Baiting System**: Detects when enemy uses CHIP_ANTIDOTE by tracking poison duration
  - Bait phase: Conserve strong poisons, use only TOXIN + FLAME_THROWER + DOUBLE_GUN
  - Escalation: Switch to full offensive when antidote cooldown detected
  - Smart detection: Tracks `prevPoisonRemaining` to catch early cleanses
- **Poison Attrition Mode**: Defensive play when poison will secure kill
  - Calculates `turnsBeforeAntidote = min(poisonRemaining, antidoteCooldown)`
  - Estimates poison damage: `poisonDamagePerTurn * turnsBeforeAntidote`
  - Hides if poison will kill before antidote can cleanse
- **Weapon-First Execution**: Spams weapons to max uses BEFORE using chips
  - Ignores poison plan's conservative weapon use estimates
  - Ensures maximum TP expenditure on repeatable attacks
- **Effect Tracking**: Uses `getEffects()` API for intelligent DoT management

**Files:**
- `/V8_modules/strategy/magic_strategy.lk` (~1,300 lines)

#### **strategy/boss_strategy.lk** - Boss Fight Strategy (Skeleton)
**Status:** Skeleton with TODO placeholders

**Planned Features:**
- Boss fight detection (Grail + 4 crystals)
- Crystal puzzle solving (align colored rays to Grail gems)
- Team coordination (1 puzzle solver + 3 distraction team)
- CHIP_TELEPORTATION, CHIP_GRAPPLE, CHIP_BOXING_GLOVE, CHIP_INVERSION usage

**Current State:**
- All methods stubbed with TODO comments
- Falls back to `super.createOffensiveScenario()` for combat
- Ready for future implementation

**Files:**
- `/V8_modules/strategy/boss_strategy.lk` (162 lines)

---

## Critical Bug Fixes (October 2025)

### 1. Star Pattern Distance Calculation Bug
**Problem:**
- `getLineHits()` and `getDiagonalHits()` used arithmetic cell offsets without validating actual game distance
- Cells marked as in-range when actually out of range (e.g., cell 181 at distance 12 for lightninger max range 10)
- Arithmetic offset `cell + x_offset * dist` doesn't guarantee correct Chebyshev distance

**Solution:**
- Added `getCellDistance()` validation in both methods (field_map.lk lines 542-543, 569-570)
- Filters cells to only those at actual weapon range before marking as damage cells
- Code: `if (actualDist == null || actualDist < minR || actualDist > maxR) continue`

**Impact:** Star pattern weapons (lightninger, rifle) now correctly identify all valid shooting positions

### 2. Stale Target Position Bug
**Problem:**
- Attack execution used `a.targetEntity._cellPos` which becomes stale after `executeAndFlushActions()`
- Target entity state not refreshed when player state is updated mid-scenario
- Caused weapon attacks to fail silently (wrong cell position)

**Solution:**
- Changed attack execution to use `a.targetCell` (captured at action creation time)
- Modified base_strategy.lk lines 550, 553 from `a.targetEntity._cellPos` to `a.targetCell`

**Impact:** Weapon and chip attacks now execute correctly after immediate movement

### 3. Chest Targeting After Destruction Bug
**Problem:**
- `getClosestChest()` returned dead chests (`isDead()` == true)
- AI continued targeting destroyed chests instead of switching back to enemies
- Infinite loop on dead chest entity

**Solution:**
- Added `isDead()` check in `getClosestChest()` (field_map.lk line 379)
- Code: `if (isDead(c._id)) continue`
- Returns null when all chests destroyed, strategies fall back to enemy targeting

**Impact:** All strategies (Strength, Agility, Magic) properly resume enemy combat after chest loot collected

### 4. Unreachable Position Handling
**Problem:**
- When optimal weapon cell was unreachable, agility strategy applied buff then stopped
- No TP spent on attacks from current position
- Early return prevented any combat actions

**Solution:**
- Added `executeAndFlushActions()` method for mid-scenario execution (base_strategy.lk lines 567-571)
- Executes movement immediately, updates game state, continues with weapons/chips from actual position
- Tracks weapon state (`currentWeaponId`) to avoid unnecessary swaps

**Impact:** Agility builds now properly spend TP on attacks even when optimal cell unreachable

### 5. Chip Spam Bug
**Problem:**
- Pre-calculated `usesC = min(maxUse, floor(TP/cost))` limited chip spam
- Chips used exactly once instead of spamming until TP exhausted

**Solution:**
- Changed to `while (actualUsesC < maxUse && playerTP >= cost)` loop
- Fixed in 3 locations:
  - strength_strategy.lk main offensive (lines 377-383)
  - strength_strategy.lk OTKO (lines 149-155)
  - agility_strategy.lk (already fixed)

**Impact:** All strategies now properly spam chips until max uses or TP exhausted

### 6. Magic Strategy Antidote Bait Loop Bug
**Problem:**
- Antidote detection logic reset to bait mode when antidote cooldown returned to 0 (lines 224-227)
- Created infinite bait loop: bait → antidote used → detect cooldown ready → reset to bait mode
- GRAPPLE-COVID combo never executed because strategy stayed in bait mode forever
- PLAGUE incorrectly used in bait mode instead of being saved for full offensive

**Solution:**
- Removed reset-to-bait logic (lines 224-227) that forced `_baitMode[enemyId] = true` when `antidoteCD == 0`
- Initialize bait mode only on first encounter, rely on escalation logic (lines 231-247) to exit
- Removed CHIP_PLAGUE from `isBaitAllowedChip()` and bait mode logic
- Bait mode now uses only: FLAME_THROWER + DOUBLE_GUN + TOXIN
- Full offensive mode priorities: GRAPPLE-COVID combo FIRST (19 TP), then PLAGUE + weapons

**Impact:** Magic strategy now correctly baits antidote, then executes GRAPPLE-COVID combo after antidote is detected on cooldown

### 7. GRAPPLE-COVID Combo Implementation (December 2025)
**Problem:**
- GRAPPLE-COVID combo was planned but never executed correctly
- Multiple issues: API function errors, stale position bugs, TP starvation, chip targeting failures

**Solution - Multi-phase implementation:**

**Phase 1: Combo Positioning System**
- Added `findGrappleCovidCell()` to find optimal cells at range 3-8, on same line, with LOS
- Uses `fieldMap.getAccessibleCells(player)` to get reachable cells within MP range
- Scores cells preferring range 5-6 (middle of 3-8) and proximity to current position

**Phase 2: Immediate Movement Execution**
- Problem: Combo check happened from OLD position before movement executed
- Solution: Added `executeAndFlushActions()` to move immediately when `shouldPrioritizeCombo = true`
- Updates player position after movement, then checks combo availability from NEW position

**Phase 3: TP Preservation**
- Problem: LEATHER_BOOTS consumed 3 TP, leaving only 16/19 TP for combo
- Solution: Skip LEATHER_BOOTS when `shouldPrioritizeCombo = true` to reserve full 19 TP

**Phase 4: Optional BALL_AND_CHAIN**
- Problem: BALL_AND_CHAIN cooldown blocked entire combo execution
- Solution: Made BALL_AND_CHAIN optional
  - Core combo: GRAPPLE + COVID + BOXING_GLOVE (14 TP minimum)
  - Include BALL_AND_CHAIN only if equipped + off cooldown + 19 TP available
  - Dynamically check at execution time, skip with debug log if unavailable

**Phase 5: Immediate Chip Execution Pattern**
- Problem: Queued actions had stale target positions after GRAPPLE moved enemy
- Solution: Changed from queue pattern to immediate execution
  - Execute GRAPPLE → update enemy position with `target.updateEntity()`
  - Execute COVID on new position → Execute BOXING_GLOVE → Execute BALL_AND_CHAIN
  - Each chip executes immediately, ensuring correct target cells

**Phase 6: BOXING_GLOVE Horizontal/Vertical Alignment**
- Problem: BOXING_GLOVE only works on horizontal OR vertical lines (NOT diagonals)
- Solution: Added alignment detection
  - Check `enemyY == playerY` (horizontal) or `enemyX == playerX` (vertical)
  - Calculate push direction: away from player along same line
  - Find furthest valid cell (8 cells max) with `lineOfSight()` to avoid obstacles
  - Logs error if enemy not on horizontal/vertical line after GRAPPLE

**Phase 7: Weapon Spam Execution Order**
- Problem: Poison plan limited weapons to 1 use, then spent TP on chips, leaving 10 TP unused
- Solution: Reordered execution in `createFullOffensiveDoT()`
  - Spam weapons FIRST to max uses (ignore poison plan's conservative values)
  - THEN use poison chips with remaining TP
  - Ensures maximum TP expenditure on repeatable attacks before one-time chips

**Phase 8: Poison Attrition Mode**
- Problem: AI continued fighting even when poison would secure kill, taking unnecessary damage
- Solution: Added defensive play when poison will win
  - Calculate `turnsBeforeAntidote = min(poisonRemaining, antidoteCooldown)`
  - Estimate `poisonDamageBeforeAntidote = poisonDamagePerTurn * turnsBeforeAntidote`
  - Enter attrition mode if:
    1. Poison will kill before antidote available OR
    2. Enemy HP < 30% (very low) OR
    3. Enemy HP < 50% AND antidote on cooldown
  - Skip all attacks, move to Hide & Seek cell, let poison finish enemy

**Impact:**
- GRAPPLE-COVID combo now executes reliably (14-19 TP burst)
- Weapons spam to max uses before chips
- AI plays defensively when poison will secure kill, improving survival rate

### 8. Battle Royale Dead Enemy Targeting Bug (January 2026)
**Problem:**
- `getClosestEnemy()` returned dead enemies in Battle Royale mode
- AI continued targeting destroyed enemies with `_cellPos = null`
- Caused null target cell errors and wasted TP on invalid attacks

**Solution:**
- Added `isDead()` check in `getClosestEnemy()` (field_map.lk line 377)
- Code: `if (isDead(e._id)) continue`
- Mirrors existing dead chest check in `getClosestChest()`

**Impact:** AI correctly switches to alive enemies in Battle Royale, preventing null target bugs

### 9. Unreachable Damage Cell Bug (January 2026)
**Problem:**
- When optimal weapon cell unreachable, AI moved toward it blindly
- Ended up at intermediate position with no weapons in range
- Wasted entire turn (TP unused) due to positional failure

**Solution:**
- Added `findBestReachableDamageCell(maxMP)` method (base_strategy.lk lines 20-47)
- Finds highest damage cell within MP budget from damage map
- Falls back to this cell when optimal cell unreachable
- Added LEATHER_BOOTS emergency movement boost (+3 MP) when no reachable cells

**Impact:** AI always moves to positions where attacks are guaranteed, eliminating "flee turns"

### 10. Fighting Retreat Implementation (January 2026)
**Problem:**
- Defensive flee moved directly to safest cell (danger=0)
- Safe cell often out of weapon range (e.g., distance 12 for range 1-4 weapon)
- AI wasted TP trying to attack from unreachable position

**Solution:**
- Added `findBestDamageCellOnPath(targetCell, maxMP)` method (base_strategy.lk lines 49-95)
- Gets full flee path, finds best damage cell along path within MP range
- Stops at damage cell, validates weapons from actual position after movement
- Attacks with correct weapon for current distance, then continues fleeing with remaining MP

**Flow:**
```
Low HP → Use REGENERATION
→ Find safe cell (e.g., 268, danger=0)
→ Check flee path for damage cells
→ Found cell 218 with weapons (4 cells away)
→ Move to 218 → Attack with rifle (range 3-10, enemy at dist=7)
→ Continue fleeing to 268 with remaining MP
```

**Impact:**
- Maximizes TP usage during retreat (15+ TP spent on attacks instead of wasted)
- Maximizes MP usage (moves toward safety after attacking)
- Correct weapon selection based on actual post-movement distance

---

## Development Workflow

**IMPORTANT:** Code updates and testing are performed manually by the user:
1. User edits files in `/V8_modules/` directory locally
2. User manually uploads updated code to LeekWars website (AI editor)
3. User runs test fights through LeekWars interface
4. User reviews fight logs and provides feedback to Claude
5. Claude analyzes logs and suggests fixes, user implements changes

**Note:** Python automation scripts (`upload_v8.py`, `lw_test_script.py`) are NOT used. All uploads and testing done manually through LeekWars web interface.

---

## Areas for Improvement

### 1. **Action Queue Validation**
**Issue:** No validation that queued actions are still valid before execution
**Impact:** Actions may fail silently if enemy moves or dies
**Proposed Fix:**
- Add `validateAction(action)` method in base_strategy.lk
- Check range, line-of-sight, TP/MP availability before execution
- Skip invalid actions with debug warnings

### 2. **Emergency Mode / Low HP Behavior**
**Issue:** No dedicated low HP survival logic
**Impact:** AI fights aggressively even when critically wounded
**Proposed Fix:**
- Add `createEmergencyScenario()` in base_strategy.lk
- Prioritize CHIP_CURE, CHIP_BANDAGE, CHIP_REGENERATION
- Defensive positioning (maximize distance from enemies)
- Only attack if enemy is killable with remaining TP

### 3. **Target Selection**
**Issue:** Strategies attack first enemy found, no priority system
**Impact:** May focus wrong targets (e.g., tank instead of squishy DPS)
**Proposed Fix:**
- Add `selectOptimalTarget()` method considering:
  - Enemy HP (prioritize low HP for kills)
  - Enemy threat (damage output, debuffs)
  - Accessibility (range, line-of-sight)
- Strength: Prioritize lowest HP
- Magic: Prioritize targets without DoT
- Agility: Prioritize high-HP targets (damage return scales with incoming damage)

### 4. **Ally Coordination**
**Issue:** No team coordination in multi-leek fights
**Impact:** Allies may target same enemy, waste damage
**Proposed Fix:**
- Add static variables in main.lk for ally coordination:
  - `static _targetPriority = [:]` - Map: enemyID → priority score
  - `static _targetAssignments = [:]` - Map: allyID → targetID
- Each leek claims target at turn start, others adjust accordingly

### 5. **Resource Management Optimization**
**Issue:** Strategies use buffs/teleport without checking if TP budget allows meaningful attacks after
**Impact:** Turn wasted on buff with no follow-up damage
**Proposed Fix:**
- Add `calculateMinimumAttackTP()` method
- Check `playerTP >= buffCost + minimumAttackTP` before applying buffs
- Skip buffs if insufficient TP for attacks

### 6. **Magic Strategy Kiting Distance**
**Issue:** Kiting distance hardcoded, may move too close or too far
**Impact:** Still in enemy weapon range or too far for follow-up attacks
**Proposed Fix:**
- Calculate optimal kite distance based on:
  - Enemy weapon ranges (max range of all equipped weapons)
  - Player weapon ranges (stay within attack range)
- Target: `enemyMaxRange + 1` to `playerMaxRange - 1`

### 7. **OTKO Teleportation Improvements**
**Issue:** OTKO only considers weapon damage, ignores chip damage potential
**Impact:** Misses OTKO opportunities when chip burst could secure kill
**Proposed Fix:**
- Modify `findOptimalTeleportCell()` to consider:
  - Total burst damage (weapons + chips)
  - AOE chip overlap (multiple enemies in range)
- Execute OTKO if `totalBurst >= enemyHP`

### 8. **Hide-and-Seek Cell Selection**
**Issue:** HNS cell selection prioritizes distance, may choose cells with no cover
**Impact:** Post-combat positioning provides minimal defensive benefit
**Proposed Fix:**
- Add `evaluateCoverScore(cell)` considering:
  - Adjacent obstacles (higher = better cover)
  - Line-of-sight to enemies (fewer visible = better)
  - Escape routes (multiple paths away = better)
- Weight: `score = distance * 0.5 + coverScore * 0.5`

### 9. **Weapon Swap Optimization**
**Issue:** Strategies swap weapons even when current weapon is already optimal
**Impact:** Wastes 1 TP per unnecessary swap
**Proposed Fix:**
- Track `currentWeaponId` in base_strategy.lk
- Skip `createAttackAction(ACTION_WEAPON_SWAP)` if `getWeapon() == targetWeapon`
- Already partially implemented in `executeAndFlushActions()`, extend to all scenarios

### 10. **Field Map Caching**
**Issue:** Damage map recalculated every turn even if enemy didn't move
**Impact:** Unnecessary operations consumed, slower turn execution
**Proposed Fix:**
- Cache damage map with key: `enemyID_position`
- Invalidate cache when enemy moves or weapons change
- Reduces operations by ~30% in static positioning scenarios

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

## LeekScript Programming Notes

### Built-in Constants
- **All WEAPON_* constants are built-in**: `WEAPON_M_LASER`, `WEAPON_RIFLE`, `WEAPON_ENHANCED_LIGHTNINGER`, etc.
- **All CHIP_* constants are built-in**: `CHIP_TOXIN`, `CHIP_VENOM`, `CHIP_SPARK`, `CHIP_LIGHTNING`, etc.
- **Effect constants available**: `EFFECT_POISON`, `EFFECT_BUFF_STRENGTH`, `EFFECT_SHACKLE_TP`, etc.
- **No need to define constants** - they're part of the LeekScript language

### Coordinate System
- **Map center**: [0, 0]
- **Map corners**: [-17, 0], [17, 0], [0, -17], [0, 17]
- **Total cells**: 0-612 in a 35x35 grid
- **Built-in functions**: `getCellX()`, `getCellY()`, `getCellFromXY()` handle coordinate conversion

### Debugging & Logs
- **Console logs**: Use `debug()` for AI debug output
- **Fight logs location**: Saved locally by Python scripts, NOT accessible via URL/CURL
- **Log files**: Check `fight_logs/` directory and root analysis files

---

## Development Best Practices

1. **Testing**: Run 10-20 fights per opponent for statistical significance
2. **Incremental Changes**: Test after each modification
3. **Log Analysis**: Use combat logs to identify win/loss patterns
4. **Action Queue Discipline**: NEVER call `useChip()`, `useWeapon()`, `moveTowardCell()` directly in strategies
5. **State Management**: Update player state variables (TP/MP/position) after queuing actions
6. **Target Cell Capture**: Always capture `targetEntity._cellPos` at action creation time (prevents stale position bugs)

---

## Script ID
- **V8**: 446029 (main.lk) - Current production

---

*Document Version: 18.0*
*Last Updated: January 2026*
*Status: V8 System Active - Fighting Retreat & Emergency Movement Implemented*
