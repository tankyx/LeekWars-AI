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

## Areas for Improvement

**Action Queue Validation:** Validate queued actions before execution (range, LOS, TP/MP availability)

**Emergency Mode:** Add dedicated low HP survival logic (prioritize healing, defensive positioning)

**Target Selection:** Implement priority system (Strength: lowest HP, Magic: no DoT, Agility: high HP)

**Ally Coordination:** Add static variables for target assignments in multi-leek fights

**Resource Management:** Check TP budget allows meaningful attacks after buffs/teleport

**Magic Kiting Distance:** Calculate optimal distance based on enemy/player weapon ranges

**OTKO Improvements:** Consider total burst damage (weapons + chips) instead of weapon-only

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

**Script ID:** 447461 (V8 main.lk - Current production, January 2026)

*Document Version: 23.1 | Last Updated: January 2026*
