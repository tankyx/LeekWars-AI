# Phase 2 Mutation System - Status Report

**Date:** February 4, 2026
**Status:** Phase 1 Complete ✅ | Phase 2 Blocked 🔴

---

## Phase 1: Foundation (COMPLETE ✅)

### Implementation
1. **TARGET_SELF Chip Validation** (`atomic_action.lk:130-147, 213-235`)
   - Added `isSelfTargetingChip()` method to identify self-buffs
   - Beam Search can now generate buff actions (STEROID, FORTRESS, REMISSION)
   - Skips range/target validation for self-targeting chips

2. **State Hashing** (`world_state.lk:239-254`)
   - Format: `"cell:roundedTP:roundedTargetHP"`
   - Rounds to nearest 10 for fuzzy matching
   - Enables transposition table pruning

3. **Transposition Table** (`beam_search_planner.lk:43, 59, 154-173`)
   - Tracks best score seen for each state hash
   - Prunes duplicate states with lower scores
   - Logs pruned count with `debugDetail()`

### Test Results
- **Baseline (no changes):** 80% WR (4W-1L over 5 fights)
- **Phase 1 only:** 66.7% WR (2W-1L over 3 fights)
- **Status:** Working, slight performance variance within normal range

### Files Modified
- `V8_modules/atomic_action.lk` - TARGET_SELF validation
- `V8_modules/world_state.lk` - State hashing
- `V8_modules/beam_search_planner.lk` - Transposition table
- `tools/upload_v8.py` - Module list updates

---

## Phase 2: Mutation System (BLOCKED 🔴)

### Implementation Status

**Working Components:**
- ✅ `MutationResult` class - Result container
- ✅ `ScenarioMutator` class - Mutation generator
- ✅ `HybridMutationPlanner` - Orchestrator
- ✅ `isAoEAction()` - Detects AoE weapons/chips
- ✅ `getAdjacentCells()` - Cell neighbor calculation
- ✅ `generateMutations()` - Main entry point

**Blocked Component:**
- 🔴 `cloneScenario()` - **ROOT CAUSE OF FAILURE**

### Root Cause Analysis

**Problem:** Creating new `Action` objects breaks execution (0% WR)

**Evidence:**
```
- Stub cloneScenario (returns original): 66.7% WR (2W-1L)
- Full cloneScenario (new Action objects): 0% WR (0W-4L-1D)
```

**Hypothesis:**
Action objects have internal state or circular references that aren't copied by simple field assignment. The execution system (base_strategy.lk) expects the original action objects created by ScenarioGenerator.

**Failed Implementation:**
```javascript
cloneScenario(scenario) {
    var cloned = []
    for (var action in scenario) {
        var newAction = new Action(action.type)
        newAction.chip = action.chip
        newAction.weaponId = action.weaponId
        newAction.targetEntity = action.targetEntity
        newAction.targetCell = action.targetCell
        push(cloned, newAction)
    }
    return cloned
}
```

**What's Missing:**
- Action objects may have additional internal fields not being copied
- The `targetEntity` reference may need special handling
- Execution system may rely on object identity, not just field values

---

## Mutation Operators Design

### 1. Aim Cell Optimization (Not Implemented)
**Goal:** Test ±1 cell shifts for AoE attacks

**Design:**
- Identify AoE actions (weapons with `_areaOfEffect > 0`)
- Generate 4 variants (±1 horizontal/vertical)
- Modify `action.targetCell` field
- Score each variant using ScenarioSimulator

### 2. Action Reordering (Not Implemented)
**Goal:** Try different action orderings (buff before damage)

**Design:**
- Identify buff, damage, movement actions
- Swap adjacent actions (buff↔damage, buff↔movement)
- Test if reordering improves score

### 3. Micro-Movement (Not Implemented)
**Goal:** Test adjacent cells for better positioning

**Design:**
- Find movement actions
- Generate 4 adjacent cell variants
- Filter by reachability and LoS
- Score positioning improvements

---

## Next Steps

### Option 1: In-Place Mutation (Recommended)
Instead of cloning, mutate the original scenario actions:

```javascript
generateAimCellMutations(scenario) {
    var mutations = []

    for (var i = 0; i < count(scenario); i++) {
        var action = scenario[i]

        if (this.isAoEAction(action)) {
            var originalCell = action.targetCell
            var adjacentCells = this.getAdjacentCells(originalCell)

            for (var adjCell in adjacentCells) {
                // Mutate in-place
                action.targetCell = adjCell

                // Evaluate
                var simResult = this._simulator.simulate(scenario)
                var score = this._scorer.score(simResult, scenario)

                // Store result
                push(mutations, ['cell': adjCell, 'score': score])

                // Revert mutation
                action.targetCell = originalCell
            }
        }
    }

    return mutations
}
```

**Pros:**
- No cloning required
- Preserves all internal state
- Mutations are temporary (reverted after scoring)

**Cons:**
- Must carefully revert all mutations
- Can't evaluate multiple mutations in parallel

### Option 2: Deep Clone Investigation
Investigate what fields are missing from the clone:

1. Read `strategy/action.lk` to see full Action class structure
2. Identify all fields and internal references
3. Implement proper deep clone

### Option 3: Disable Mutations (Fallback)
Keep Phase 1, disable mutation system entirely:
- Set `USE_MUTATIONS = false` in unified_strategy.lk
- Phase 1 improvements still active (TARGET_SELF + state hashing)

---

## Performance Summary

| Configuration | Win Rate | Sample Size |
|--------------|----------|-------------|
| Baseline (HEAD) | 80.0% | 5 fights |
| Phase 1 Only | 66.7% | 3 fights |
| Phase 1 + Stub Mutation | 66.7% | 3 fights |
| Phase 1 + Full Mutation (broken) | 0.0% | 5 fights |

**Conclusion:** Phase 1 is production-ready. Phase 2 requires in-place mutation approach.

---

## Files

**Phase 1 (Working):**
- `V8_modules/atomic_action.lk`
- `V8_modules/world_state.lk`
- `V8_modules/beam_search_planner.lk`

**Phase 2 (Blocked):**
- `V8_modules/scenario_mutation.lk` (stub implementation)
- `V8_modules/strategy/unified_strategy.lk` (mutation hooks disabled)

**Documentation:**
- `PHASE2_MUTATION_STATUS.md` (this file)
