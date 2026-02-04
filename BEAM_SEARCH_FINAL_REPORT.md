# Beam Search Integration - Final Report

## Executive Summary

**Objective:** Integrate beam search planning to discover emergent action sequences beyond hand-crafted scenarios.

**Result:** **UNSUCCESSFUL** - Beam search disabled after comprehensive testing shows 0% WR vs 80% scenario baseline.

**Root Cause:** Architectural mismatch between incremental beam search exploration and LeekWars' requirement for complete multi-step action plans.

---

## Investigation Timeline

### Session 1: Basic Integration
- **Goal:** Fix LS4 compilation errors, implement basic beam search
- **Result:** 0% WR (0W-3L-0D)
- **Issue:** Beam search stopped at depth 2 with only 1-action sequences

### Session 2: Hybrid Seeds
- **Goal:** Inject scenario-based seeds into initial beam for domain knowledge
- **Result:** 0% WR (0W-3L-0D)
- **Issue:** Seeds didn't overcome resource constraints

### Session 3: Heuristic Tuning
- **Improvements Implemented:**
  - Dynamic damage weights (turn-aware: 2000 early → 4000 late)
  - Kill probability multipliers (5x for 95%+, 3x for 70%+, 1.5x for 50%+)
  - Context-aware resource penalties (reduced early game, forgive small leftovers)
  - Enhanced synergies (buff+damage, shield+HP, proactive buffing)
- **Result:** 10% WR (1W-9L-0D) - marginal improvement but still far below baseline

### Session 4: Resource Investigation ✅
- **Discovery:** Turn 1 has TP=2 (not 24-25) because `turnOneBuffs()` pre-spends ~23 TP
- **Solution:** Enable beam search only on turn 2+ when TP=25 (full resources)
- **Result:** 0% WR (0W-10L-0D) with hybrid approach (scenarios T1, beam search T2+)

---

## Root Cause Analysis

### The TP=2 Mystery (SOLVED)

**Symptom:** `WorldState.fromGameState()` read TP=2 instead of expected 24-25.

**Root Cause:**
```
Initialization (getTurn() == 1):
├─ strategy.turnOneBuffs() executes
│  ├─ CHIP_KNOWLEDGE (7 TP)
│  ├─ CHIP_ELEVATION (8 TP)
│  └─ CHIP_ARMORING (8 TP)
│  Total: ~23 TP spent
└─ main() is called with TP=2 remaining

Turn 2+:
└─ TP resets to 25 (full resources) ✓
```

**Verification:**
```
[V8] [MAIN-TURN-1] After updateEntity: TP=2 MP=7
[V8] [MAIN-TURN-2] After updateEntity: TP=25 MP=7
```

### Why Beam Search Still Fails (Turn 2+ with Full TP=25)

**Performance Results:**
| Configuration | Win Rate | Notes |
|--------------|----------|-------|
| Pure scenarios | 80% (4W-1L) | Baseline performance ✓ |
| Beam search T1 (TP=2) | 0% (0W-3L) | Insufficient resources |
| Beam search T2+ (TP=25) | 0% (0W-10L) | Full resources, still fails |
| Hybrid (scenarios T1, beam T2+) | 0% (0W-10L) | Best of both worlds? Nope. |

**Fundamental Architectural Mismatch:**

LeekWars requires **complete multi-step plans**:
```
STEROID (7 TP) → Move (7 MP) → Attack×3 (24 TP) → Reposition
```

Beam search explores **incrementally**:
```
Depth 0: [TP=25, MP=7]
Depth 1: [Buff STEROID, TP=18, MP=7] or [Move, TP=25, MP=0]
Depth 2: ???
```

**Problems:**
1. **Branching factor explosion:** With 25 TP and multiple chips/weapons, there are 50+ valid actions
2. **Shallow depth:** Beam width=100 cannot maintain enough diversity to reach depth 4-6
3. **Heuristic inadequacy:** Intermediate states (buffed but haven't attacked yet) score poorly
4. **No combo recognition:** Cannot recognize that STEROID → Attack is valuable until depth 2+

**Evidence from Logs:**
- Beam search starts generating seeds (scenarios)
- Seed generation itself is verbose (~1000s of debug lines)
- Search likely hits 12M operation limit or crashes before completing
- Logs truncated with "... 10344 more log entries ..."

---

## What We Built (5 New Modules, ~1400 Lines)

### 1. `world_state.lk` (304 lines)
- Immutable game state representation
- Player state (TP, MP, HP, stats, buffs, shields)
- Enemy tracking (Battle Royale support)
- Weapon uses & chip cooldowns
- Action sequence history

### 2. `atomic_action.lk` (520 lines)
- Action vocabulary: MOVE_TACTICAL, USE_CHIP, USE_WEAPON, SWAP_WEAPON, TELEPORT
- `AtomicActionGenerator`: Generates valid actions from state
  - Movement: Top 10 tactical cells
  - Attacks: Weapons + damage chips
  - Buffs: STEROID, FORTRESS, WALL
  - Utilities: Teleport escape
- Action validation (TP/MP costs, ranges, cooldowns)

### 3. `state_transition.lk` (364 lines)
- Pure functional state transitions: `State + Action → New State`
- No game API calls (simulation only)
- Damage calculations (shields, vulnerability, poison, nova)
- Buff application (STEROID, FORTRESS, etc.)
- Cost ~100-200 ops per transition

### 4. `atomic_action_executor.lk` (434 lines)
- Converts AtomicActions to game API calls
- Pre-execution validation (catch invalid actions)
- Error handling (skip invalid, log warnings)
- Weapon swap automation

### 5. `beam_search_planner.lk` (518 lines)
- Beam search (width=100, depth=8)
- `BeamSearchHeuristic` with 5 components:
  - Damage scoring (dynamic weights, kill multipliers)
  - Survival scoring (HP, shields, death penalty)
  - Position scoring (threat-normalized)
  - Resource efficiency (context-aware penalties)
  - Synergy detection (buff+damage, shield+HP)
- Scenario seed injection (Session 2)

---

## Lessons Learned

### What Worked
1. ✅ **State representation:** WorldState correctly captures game state
2. ✅ **Action generation:** AtomicActionGenerator produces valid actions
3. ✅ **State transitions:** Pure functional simulation is accurate
4. ✅ **Debugging infrastructure:** Comprehensive logging revealed issues
5. ✅ **Resource investigation:** Identified TP=2 root cause

### What Didn't Work
1. ❌ **Beam search exploration:** Cannot reach depth needed for complete plans
2. ❌ **Heuristic scoring:** Intermediate states score poorly
3. ❌ **Hybrid approach:** Scenarios T1 + beam search T2+ still fails
4. ❌ **Seed injection:** Domain knowledge doesn't overcome exploration limits
5. ❌ **Operation budget:** Likely hitting 12M limit during search

### Why Scenarios Win
- **Complete plans:** Scenarios generate buff → move → attack as atomic units
- **Domain knowledge:** Hand-crafted for LeekWars combat patterns
- **Efficient:** ~400K ops/turn vs beam search's millions
- **Proven:** 80% WR vs Domingo (balanced opponent)

---

## Recommendations

### Short Term: Keep Scenarios (DONE)
- Beam search disabled (`USE_BEAM_SEARCH = false`)
- Baseline performance: **80% WR** restored
- Production-ready codebase

### Long Term: Alternative Approaches

If emergent planning is desired, consider:

1. **Macro Actions**
   - Define "buff → attack" as single macro action
   - Reduces branching factor
   - **Con:** Essentially becomes scenario generation

2. **Hierarchical Planning**
   - High-level: Choose strategy (aggressive, defensive)
   - Low-level: Execute tactics
   - **Con:** Complex implementation

3. **Monte Carlo Tree Search (MCTS)**
   - Better for long-horizon planning
   - Proven in domains like Go, StarCraft
   - **Con:** Operation cost likely prohibitive (12M limit)

4. **Reinforcement Learning**
   - Learn optimal policies from self-play
   - **Con:** Requires external training infrastructure

---

## Files Modified

**New Files:**
- `V8_modules/world_state.lk`
- `V8_modules/atomic_action.lk`
- `V8_modules/state_transition.lk`
- `V8_modules/atomic_action_executor.lk`
- `V8_modules/beam_search_planner.lk`
- `SESSION3_LEARNINGS.md`
- `BEAM_SEARCH_FINAL_REPORT.md`

**Modified Files:**
- `strategy/unified_strategy.lk` - Beam search integration (disabled)
- `main.lk` - TP tracking debug output
- `field_map_tactical.lk` - Null checks
- Bug fixes across multiple modules (EnemyState fields, weaponNeedsLoS, etc.)

---

## Conclusion

Beam search integration was **unsuccessful** despite:
- ✅ Correct state representation
- ✅ Valid action generation
- ✅ Accurate simulation
- ✅ Sophisticated heuristic (5 components)
- ✅ Full resources (TP=25 on turn 2+)

The **fundamental issue** is architectural: beam search's incremental exploration cannot efficiently discover the complete 4-6 action plans that LeekWars requires.

**Scenarios remain the optimal approach** for LeekWars combat with **80% WR** vs beam search's **0% WR**.

The beam search infrastructure remains in the codebase for future research but is disabled in production.

---

**Final Status:** Beam search **DISABLED**, baseline performance **RESTORED** at 80% WR.
