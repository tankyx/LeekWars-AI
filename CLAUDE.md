# CLAUDE.md - LeekWars AI V8 Development Guide

## Overview
Development guide for LeekWars AI V8 system - modular, strategy-based combat AI with build-specific optimizations.

## Project Structure
```
LeekWars-AI/
├── V8_modules/          # V8 AI (17 modules, ~4,500 lines)
│   ├── main.lk         # Main entry point & strategy selection
│   ├── game_entity.lk  # Player & enemy state tracking
│   ├── field_map_*.lk  # Damage zones & tactical positioning (3 modules)
│   ├── item.lk         # Weapon/chip definitions & damage calculations
│   ├── operation_tracker.lk   # Operation profiling (startOp/stopOp)
│   ├── cache_manager.lk       # Path length memoization
│   ├── scenario_generator.lk # Generates 6 scenario variants
│   ├── scenario_simulator.lk # Simulates scenarios without execution
│   ├── scenario_scorer.lk     # Build-specific scenario scoring
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

### State-Based Multi-Scenario System (December 2025)

**V8 uses strategic state detection to generate 2-4 optimized scenarios per turn.**

**System Components:**
- **ScenarioGenerator**: State-based scenario generation (KILL, AGGRO, ATTRITION, SUSTAIN, FLEE)
- **ScenarioSimulator**: Simulates each scenario without executing (tracks TP/MP/damage/positioning)
- **ScenarioScorer**: Scores scenarios using build-specific weights (STR favors damage, MAG favors DoT, AGI favors positioning)

**How It Works:**
1. **State Detection** (~10-20K ops): Analyze HP, buffs, turn number, OTKO opportunity
2. **Generation** (~300K ops): Create 2-4 scenarios for detected state only
3. **Simulation** (~30K ops): Run each scenario in sandbox (no game state changes)
4. **Scoring** (~30K ops): Apply build-specific weights to metrics
5. **Execution**: Execute the highest-scoring scenario

**Strategic States:**
- **KILL** (enemy HP < 40% + can OTKO): 2 burst scenarios (teleport OTKO, direct burst)
- **AGGRO** (early game OR buffs expired): 3 buff scenarios (build-specific, offensive, pure damage)
- **ATTRITION** (balanced combat, turn 5+): 3 balanced scenarios (mixed resources 60-100%)
- **SUSTAIN** (our HP 30-60%): 3 healing scenarios (heal+shield, heal+kite, mixed buffs)
- **FLEE** (our HP < 30%): 2 survival scenarios (REGENERATION-aware lifesteal strategy)

**FLEE State Lifesteal Strategy:**
- **If REGENERATION available**: REMISSION + REGENERATION + minimal attack + hide
- **If REGENERATION on cooldown**: REMISSION + spam ENHANCED_LIGHTNINGER (100% TP lifesteal) + kite
- Leverages lifesteal healing when multi-turn heal unavailable

**Buff Cycling Integration:**
- **Shield Cycling** (all builds): FORTRESS (3t) / WALL (2t) alternation, reapplies when `remainingTurns <= 1`
- **Damage Return** (agility): MIRROR (3t) / THORN (2t) / BRAMBLE (1t), TP-aware selection, close-range BRAMBLE priority

**Optimization - Path Length Caching:**
- LeekScript operations budget: ~6M ops/turn (10M total per fight)
- State-based cost: ~350-400K ops/turn (~6% of budget)
- **cache_manager.lk**: Memoizes `getPathLength()` calls (50K ops → 2 ops per lookup)
- **operation_tracker.lk**: Profiles operation costs with `startOp()`/`stopOp()`

**OTKO Cell Marking (Optimized):**
- Pre-calculates kill opportunities during field map generation (~10-20K ops)
- Reuses field map data (avoids redundant damage calculations)
- Visual marking: Gold cells with "OTKO" text (max 3 cells marked)
- Only runs when enemy HP < 70% and sufficient TP

**Key Implementation Details:**
- Scenarios track **simulated position** after movement for accurate weapon range checks
- Weapon spam uses simulated position, not starting position
- All `getPathLength()` calls replaced with `getCachedPathLength()`
- All `getChipCost()` calls replaced with `getCachedChipCost()`

**Performance:**
- Average per-turn cost: ~370K ops (6% of 6M budget) ✅
- Generates 2-4 scenarios per turn (vs 12 previously)
- Scores range from 0 to 10,000+ (higher = better)
- Win rate: 60% vs domingo (baseline restored) ✅

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

## Recent Improvements (December 2025)

### Combat Performance Enhancement (December 8)
**Win Rate: 10% → 60% (6x improvement)**

**Key Changes:**
1. **Attrition-Based OTKO** - Check kill opportunity every turn instead of once at start
   - 65% of fights end with OTKO (avg trigger at 1256 HP / 50% enemy HP)
   - `strength_strategy.lk:700-732`

2. **Intelligent Buff Management**
   - Smart STEROID: Skip if OTKO viable, recheck after application
   - Defensive sustain: REMISSION + FORTRESS/WALL when HP < 50%
   - Enhanced LIBERATION: Strip enemy resistance buffs
   - `strength_strategy.lk:734-804`

3. **GRAPPLE-HEAVY_SWORD TP Fix** - Dynamic TP cost (18-19) based on weapon swap need
   - `strength_strategy.lk:523-532`

4. **Approach Phase Optimization** - Use long-range chips while moving to target
   - `base_strategy.lk:622-700`

### Threat-Based Positioning (December 4)
- Enemy threat map with movement prediction
- Safe kiting for magic strategy (zero-threat cells)
- Hit-and-run tactics for agility
- Threat-weighted emergency mode

### Core System Improvements
- **Target Selection**: Strategy-specific prioritization (STR/AGI: lowest HP, MAGIC: fresh targets)
- **Action Validation**: Fallback suggestions prevent empty queues
- **Fight Type Detection**: Auto-adjusts buffs for PvP/Boss/Chest/PvE
- **Path Validation**: GRAPPLE combos check for obstacles

### Critical Bug Fixes
- Weapon swap validation (1 TP vs full cost)
- GRAPPLE targeting (target opposite side to pull enemy)
- Fighting retreat escape route preservation
- Magic strategy validation initialization (MP/TP tracking)
- LeekScript 4 API compatibility

---

## Development Workflow

**Upload & Test:**
```bash
python3 tools/upload_v8.py
python3 tools/lw_test_script.py <num_fights> <script_id> <opponent>
```

**Test Opponents:** domingo (strength), betalpha (magic), tisma/guj/hachess/rex (various)
**Boss Testing:** `--scenario graal`
**Logs:** Saved to `fight_logs_*.json` and `log_analysis_*.txt`


---

## LeekScript Programming Notes

**Built-in Constants:** All `WEAPON_*`, `CHIP_*`, `EFFECT_*` constants are part of LeekScript (no need to define)
**Coordinate System:** Map center [0,0], corners [-17,0] to [17,0], total 612 cells (35x35 grid)
**Debugging:** Use `debug()` for AI output, check local log files for analysis

**Action Queue Pattern (CRITICAL):**
- NEVER call `useChip()`, `useWeapon()`, `moveTowardCell()` directly in strategies
- All game operations happen via action queue → execution phase
- Update player state (TP/MP/position) after queuing actions
- Capture `targetEntity._cellPos` at action creation time (prevents stale positions)

---

**Script ID:** 447626 (V8 main.lk - Production, December 2025)

*Document Version: 32.0 | Last Updated: December 16, 2025 - State-Based Scenario Filtering + Shield/Damage Return Cycling + OTKO Cell Marking + FLEE Lifesteal Strategy*
