# CLAUDE.md - LeekWars AI V8 Development Guide

## Overview
Development guide for LeekWars AI V8 system - modular, strategy-based combat AI with build-specific optimizations.

## Project Structure
```
LeekWars-AI/
├── V8_modules/          # V8 AI (30 modules, ~5,800 lines)
│   ├── main.lk         # Main entry point & strategy selection
│   ├── game_entity.lk  # Player & enemy state tracking
│   ├── field_map_*.lk  # Damage zones & tactical positioning (3 modules)
│   ├── item.lk         # Weapon/chip definitions & damage calculations
│   ├── operation_tracker.lk   # Operation profiling (startOp/stopOp)
│   ├── debug_config.lk        # Tiered DEBUG_LEVEL system (0-3)
│   ├── cache_manager.lk       # Path length memoization
│   ├── reachable_graph.lk     # BFS-based reachability precomputation
│   ├── scenario_generator.lk  # State-based scenario generation
│   ├── scenario_simulator.lk  # Simulates scenarios without execution
│   ├── scenario_scorer.lk     # Build-specific scenario scoring
│   ├── scenario_quick_scorer.lk # Fast heuristic scoring
│   ├── performance_infra.lk   # Multi-enemy damage caching
│   ├── tactical_awareness.lk  # Threat maps & positioning
│   ├── weight_profiles.lk     # Build-specific weight sets
│   ├── strategic_depth.lk     # Weight adaptation system
│   ├── monte_carlo_sim.lk     # Kill probability simulation (Phase 3)
│   ├── kill_planning.lk       # 2-turn kill detection (Phase 3)
│   ├── cooldown_tracker.lk    # Enemy chip cooldown tracking (Phase 3)
│   ├── enemy_predictor.lk     # Enemy response simulation (Phase 4)
│   ├── math/           # Mathematical modeling (4 modules)
│   │   ├── polynomial.lk
│   │   ├── piecewise_function.lk
│   │   ├── probability_distribution.lk
│   │   └── damage_probability.lk
│   └── strategy/       # Build-specific strategies (4 modules)
│       ├── action.lk            # Action type definitions
│       ├── base_strategy.lk     # Base combat logic & action executor
│       ├── unified_strategy.lk  # Weight-driven unified strategy
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
- LeekScript operations budget: ~6M ops/turn (no fight-wide limit, only per-turn limit)
- State-based cost: ~350-400K ops/turn (~6% of budget)
- **cache_manager.lk**: Memoizes `getPathLength()` calls (50K ops → 2 ops per lookup)
- **operation_tracker.lk**: Profiles operation costs with `startOp()`/`stopOp()`

**OTKO Cell System (Full Integration):**
- Pre-calculates kill opportunities during field map generation (~10-20K ops)
- Reuses field map data (avoids redundant damage calculations)
- Visual marking: Gold cells with "OTKO" text (max 3 cells marked)
- Only runs when enemy HP < 70% and sufficient TP

**OTKO Cell Integration (Three-Layer Decision System):**
1. **Scenario Scoring** (scenario_scorer.lk): +5000 bonus for scenarios ending on OTKO cells
   - Massive score advantage drives scenario selection toward kill positions
   - Example: Kill prob 470% → guaranteed selection of OTKO positioning scenario

2. **Movement Prioritization** (scenario_generator.lk): `getMoveToOptimalCell()` prioritizes OTKO cells
   - Checks OTKO cells first before fallback to high-damage cells
   - Scoring: `killProbability * 10000 + damage - distance * 10`
   - AI actively moves toward confirmed kill positions

3. **KILL State Teleportation** (scenario_generator.lk): `createOTKOTeleportScenario()`
   - When KILL state triggers + OTKO cells available + TELEPORTATION ready
   - Teleports to best OTKO cell (highest kill probability)
   - Spams 100% TP on weapons/chips from optimal position

**Key Implementation Details:**
- Scenarios track **simulated position** after movement for accurate weapon range checks
- Weapon spam uses simulated position, not starting position
- All `getPathLength()` calls replaced with `getCachedPathLength()`
- All `getChipCost()` calls replaced with `getCachedChipCost()`
- OTKO cells stored in field map: `_isOTKOCell`, `_otkoDamage`, `_otkoKillProbability`, `_otkoTPRequired`

**Performance:**
- Average per-turn cost: ~370K ops (6% of 6M budget) ✅
- Generates 2-4 scenarios per turn (vs 12 previously)
- Scores range from 0 to 15,000+ (OTKO bonus adds 5000) ✅

### Phase 3: Probabilistic Lethality (February 2026)

**V8 now uses Monte Carlo simulation and kill planning for improved decision-making.**

**System Components:**
- **MonteCarloSimulator** (`monte_carlo_sim.lk`): Runs 100 iterations of attack sequences to calculate actual kill probability with crit variance
- **KillPlanner** (`kill_planning.lk`): Detects 2-turn kill opportunities and reserves TP for finisher
- **CooldownTracker** (`cooldown_tracker.lk`): Tracks enemy chip cooldowns (Antidote, Shield, etc.) to optimize timing

**How It Works:**
1. **Cooldown Tracking** (~5K ops): Monitor enemy chip usage, track remaining cooldown turns
2. **2-Turn Kill Detection** (~10K ops): Calculate if enemy can be killed across 2 turns, reserve TP if needed
3. **Monte Carlo Simulation** (~20-50K ops): Run 100 damage roll iterations for top scenarios to calculate actual kill probability

**Key Features:**

#### **Monte Carlo Kill Probability**
- Samples damage variance (min/max rolls + crit chance) across 100 iterations
- Returns kill probability, average damage, min/max damage bounds
- Complements analytical damage calculations for complex scenarios
- Operation safety valve at 12M ops

#### **2-Turn Kill Planning**
- Calculates max damage possible this turn and next turn
- If 2-turn kill is possible but 1-turn kill is not, reserves TP for finisher
- Prevents wasting TP on buffs when kill is available next turn
- Example: Enemy at 1500 HP, can deal 800 this turn + 900 next turn → reserve TP

#### **Enemy Cooldown Tracking**
- Tracks Antidote (14 turn CD), Shield chips (varied CD), buff chips
- Enables poison timing optimization when Antidote is on cooldown
- Records last usage turn, calculates remaining cooldown
- Persists across turns using global state

**Performance Impact:**
- Monte Carlo: 100 iterations ≈ 20-50K ops (vs 500 iterations ≈ 100-250K ops)
- Kill Planning: ~10K ops per turn
- Cooldown Tracking: ~5K ops per turn
- Total Phase 3 cost: ~35-65K ops per turn

### Phase 4: Strategic Lookahead (February 2026)

**V8 now simulates enemy responses to evaluate scenario outcomes one turn ahead.**

**System Components:**
- **EnemyPredictor** (`enemy_predictor.lk`): Simulates one "average" enemy response turn for scenario evaluation
- **Lookahead Evaluation**: Applies 0.7 discount factor to next-turn value
- **Integration**: Runs on top 1 scenario (reduced from 3) when operations < 10M

**How It Works:**
1. **Enemy Weapon Prediction** (~5K ops): Estimate enemy's best weapon based on equipped arsenal
2. **Enemy Movement Prediction** (~2K ops): Simplified movement estimation (straight-line approach)
3. **Damage Calculation** (~3K ops): Estimate enemy damage output next turn
4. **Value Discounting** (instant): Apply 0.7 multiplier to next-turn value
5. **Score Update** (instant): `finalScore = currentTurnValue + discountedNextTurn`

**Key Features:**

#### **Enemy Response Simulation**
- Predicts enemy's best weapon (damage estimate based on TP cost)
- Estimates enemy movement (simplified: move closer if distance > 3)
- Calculates potential weapon uses based on enemy TP regen (assume +6 TP)
- Returns estimated damage, TP used, enemy end position

#### **Outcome Discounting**
- Evaluates player HP after enemy response
- Survival penalties: Death = -10,000, Critical HP (<30%) = -2,000, Low HP (<50%) = -1,000
- Applies 0.7 discount factor to next-turn value (standard temporal discounting)
- Combines with current turn score for final evaluation

#### **Optimized Integration**
- Only runs if operation count < 10M (2M safety margin)
- Evaluates top 1 scenario only (vs original 3 scenarios)
- Re-evaluates best scenario selection with lookahead scores
- Can change scenario selection if lookahead reveals better long-term option

**Performance Impact:**
- Enemy prediction: ~10K ops per scenario
- Lookahead on 1 scenario: ~10K ops total (vs 30K for 3 scenarios)
- Operation gate: Only runs if <10M ops used
- Total Phase 4 cost: ~10K ops per turn (when triggered)

**Lookahead Example:**
```
Scenario A: currentScore=8000, enemyDamage=400 → survival=0 → nextTurn=0 → final=8000
Scenario B: currentScore=7500, enemyDamage=200 → survival=-1000 → nextTurn=-1000 → discounted=-700 → final=6800

Selection: Scenario A wins (8000 > 6800) despite lower immediate value
```

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

**Nova Damage Mechanics:**
- Nova damage reduces enemy **max HP** (cannot go below current HP)
- Scales with **SCI only**: `base damage × (1 + SCI / 100)`
- Bypasses shields completely (like poison)
- **Capped by HP deficit**: `min(maxHP - currentHP, calculated nova damage)`
- **Useless at 100% HP** (no gap to reduce)
- **WEAPON_QUANTUM_RIFLE**: Dual-effect weapon (direct damage scales STR, nova damage scales SCI)
- **Nova chips**: CHIP_ALTERATION, CHIP_DESINTEGRATION, CHIP_MUTATION, CHIP_TRANSMUTATION

#### **debug_config.lk** - Tiered Debugging System
Provides DEBUG_LEVEL global (0-3) with wrapper functions:
- **Level 0** (PRODUCTION): Critical errors only (~200K ops saved)
- **Level 1** (INFO): Important state changes, strategy decisions
- **Level 2** (DEBUG): Detailed execution traces, loop iterations
- **Level 3** (VERBOSE): All debug output, high-frequency logs
- Functions: `debugCritical()`, `debugInfo()`, `debugDetail()`, `debugVerbose()`
- Conditional operation tracking: `startOpDebug()`, `stopOpDebug()`

#### **monte_carlo_sim.lk** - Kill Probability Simulation (Phase 3)
`MonteCarloSimulator` class for probabilistic kill calculations:
- Runs 100 iterations of attack sequences with damage variance
- Rolls min/max damage + crit chance (AGI/1000, 30% damage multiplier)
- Returns kill probability, average damage, min/max bounds
- `calculateKillProbability(attackSequence, targetHP)` - Main entry point
- `extractAttackSequence(scenario)` - Build sequence from scenario actions
- Operation safety valve at 12M ops

#### **kill_planning.lk** - 2-Turn Kill Detection (Phase 3)
`KillPlanner` class for multi-turn kill planning:
- `detect2TurnKill()` - Checks if enemy killable across 2 turns
- `calculateMaxDamageThisTurn(tp)` - Estimates max damage with current resources
- `calculateMinTPForDamage(targetDamage)` - Calculates TP needed for finisher
- `updateGlobalKillPlan()` - Returns kill plan with TP reservation amount
- Prevents wasting TP on buffs when kill is available next turn

#### **cooldown_tracker.lk** - Enemy Chip Cooldown Tracking (Phase 3)
`CooldownTracker` class for enemy ability tracking:
- Tracks Antidote (14t CD), Shield chips, buff chips
- `recordChipUse(enemyId, chipId)` - Record enemy chip usage
- `updateCooldowns(enemyId)` - Decrement cooldown counters
- `isChipAvailable(enemyId, chipId)` - Check if chip is off cooldown
- Global state persistence: `COOLDOWN_STATE` map
- Enables poison timing optimization for magic builds

#### **enemy_predictor.lk** - Enemy Response Simulation (Phase 4)
`EnemyPredictor` class for lookahead evaluation:
- `predictEnemyBestWeapon()` - Estimate enemy's strongest weapon
- `predictEnemyMovement(playerEndPos, enemyMP)` - Simplified movement prediction
- `simulateEnemyResponse(playerEndPos, playerEndHP, playerEndTP)` - Full turn simulation
- `evaluateScenarioWithLookahead(scenarioResult, discountFactor)` - Apply 0.7 discount
- Returns damage estimate, survival penalties, final discounted score
- Only runs when operations < 10M (2M safety margin)

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

## Recent Improvements (December 2025 - February 2026)

### Phase 3 & 4 Integration (February 3, 2026)

**Enabled probabilistic lethality and strategic lookahead systems for improved decision-making.**

**Phase 3: Probabilistic Lethality (ENABLED)**
1. **Cooldown Tracker** - Track enemy chip cooldowns (Antidote, Shield, etc.)
   - `cooldown_tracker.lk` - 169 lines
   - Enables poison timing optimization for magic builds
   - Global state persistence across turns

2. **Kill Planning** - Detect 2-turn kill opportunities, reserve TP for finisher
   - `kill_planning.lk` - 193 lines
   - Prevents wasting TP on buffs when kill is available
   - Calculates min TP needed for finisher

3. **Monte Carlo Simulator** - Kill probability with damage variance
   - `monte_carlo_sim.lk` - 165 lines
   - Reduced from 500 → 100 iterations for efficiency (~5x faster)
   - Runs 100 damage roll iterations with crit variance

**Phase 4: Strategic Lookahead (ENABLED)**
1. **Enemy Predictor** - Simulate enemy response for scenario evaluation
   - `enemy_predictor.lk` - 182 lines
   - Optimized: 1 scenario only (reduced from 3) (~3x faster)
   - 0.7 discount factor for next-turn value
   - Only runs if operation count < 10M (2M safety margin)

**Optimization Applied:**
- Monte Carlo: 500 → 100 iterations (~5x faster, ~20-50K ops)
- Lookahead: 3 → 1 scenario (~3x faster, ~10K ops)
- Operation gate: 11M → 10M threshold (more conservative)

**Performance Impact:**
- Test Results: 88% WR (88W-11L-1D) over 100 fights vs Domingo
- Baseline: 64% WR (before Phase 3 & 4)
- Improvement: +24 percentage points
- No operation budget violations
- Total Phase 3 & 4 cost: ~45-75K ops per turn (within 12M budget)

### Multi-Scenario System Fixes (December 22, 2025)

**Critical bug fixes that restored multi-scenario functionality:**

1. **Scorer Function Signature** - Fixed mismatch preventing scenario evaluation
   - Added `scenario` parameter to `score()` function
   - `scenario_scorer.lk:17`

2. **Checkpoint Bonus** - Two-phase scenarios now competitive
   - Added +2500 score bonus for ACTION_CHECKPOINT scenarios
   - Compensates for phase 2 value unseen during simulation
   - `scenario_scorer.lk:87-102`

3. **Infinite Loop Bug** - Fixed 10% draw rate from timeout
   - Added `getHideAndSeekCell()` wrapper function
   - Added approach movement when weapons out of range
   - `field_map_tactical.lk:740-746`, `base_strategy.lk:2888-2901`

### Defensive Tactical Improvements (December 22)

**Implemented to reduce damage taken (was 38% higher in losses):**

1. **Threat-Aware Positioning** - HP-based tactical cell selection
   - HP >70%: threatWeight = 0.3 (mostly offensive)
   - HP 40-70%: threatWeight = 0.5 (balanced)
   - HP <40%: threatWeight = 0.8 (mostly defensive)
   - Uses `findBestTacticalCell()` instead of pure damage cells
   - `scenario_generator.lk:906-938`

2. **Defensive TELEPORT Escape** - Emergency evacuation when HP critical
   - Triggers in FLEE state (HP < 30%) when current cell threat > 200
   - Teleports to safest reachable cell
   - Follows with REMISSION heal + FORTRESS shield
   - `scenario_generator.lk:219-234, 621-687`

3. **Narrowed SUSTAIN Threshold** - Stay aggressive longer
   - Changed from HP 30-70% to HP 30-50%
   - Prevents premature defensive play
   - Analysis showed losses spammed REMISSION 5.6x more than wins
   - `scenario_generator.lk:277-283`

4. **Lowered OTKO Threshold** - More aggressive finisher
   - Changed from 85% to 75% kill probability
   - Closes fights faster (losses lasted 1.2 turns longer)
   - `scenario_generator.lk:272-276`

**Performance Impact:**
- Starting: 47% WR (broken multi-scenario)
- Bug fixes: 50% WR baseline
- Tactical fixes: 54.8% WR (230 fights), latest test 64% WR
- Total improvement: +7.8 to +17 percentage points

### Combat Performance Enhancement (December 8)

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

### Hide & Seek Algorithm Overhaul (December 17)
**Replaced LOS-counting danger system with threat map integration for intelligent tactical positioning**

**Key Improvements:**
1. **Threat Map Integration** - Uses actual enemy damage potential instead of line-of-sight exposure counts
   - `getThreatAtCell()` replaces `computeDangerForCell()`
   - Normalized by player HP percentage for better comparison
   - ~50K operation savings per turn (removed expensive LOS calculations)
   - `field_map_tactical.lk:147, 990`

2. **Intelligent Cover Evaluation** - Obstacles must actually block enemy LOS to count as cover
   - Checks if obstacles are between cell and enemy positions
   - Distance-weighted scoring (closer enemies = cover matters more)
   - Returns 0-10 score (vs previous 0-8 adjacent obstacle count)
   - `field_map_tactical.lk:234-295`

3. **Escape Route Scoring** - Detects corners and dead-ends to avoid getting trapped
   - Counts accessible adjacent directions (8 total)
   - 0-1 directions = trapped (0-1 points)
   - 6-8 directions = excellent mobility (8-10 points)
   - `field_map_tactical.lk:297-334`

4. **Smart Distance Logic** - Context-aware positioning based on threat level
   - **Safe cells (threat=0)**: Prefer CLOSER to maintain combat range
   - **Dangerous cells (threat>0)**: Prefer FURTHER to escape
   - Prevents hiding in far corners when no threat exists
   - `field_map_tactical.lk:174-206`

**Scoring Priority (Defensive Mode):**
1. Lower threat (always prioritize safety)
2. Higher escape routes (avoid getting cornered)
3. Distance (closer if safe, further if dangerous)
4. Higher cover (tiebreaker)

**Removed:**
- `getEnemyAccess()` cache (no longer needed)
- `computeDangerForCell()` LOS counting (replaced with threat map)
- Simplistic adjacent obstacle counting (replaced with actual LOS blocking checks)

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

**Script ID:** 447626 (V8 main.lk - Production, February 2026)

**Current Performance:** 88% WR vs Domingo (600 STR balanced) - 100 fight sample with Phase 3 & 4 enabled

**Performance History:**
- Baseline (pre-Phase 3 & 4): 64% WR
- Phase 1 & 2 only: 98% WR (100 fights, smaller sample variance)
- Phase 3 & 4 enabled: 88% WR (100 fights, +24pp vs baseline)

*Document Version: 36.0 | Last Updated: February 3, 2026 - Phase 3 & 4 Integration: Probabilistic Lethality + Strategic Lookahead (Monte Carlo simulation, 2-turn kill planning, cooldown tracking, enemy response prediction)*
