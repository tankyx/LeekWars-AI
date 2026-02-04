# Session 3: Heuristic Tuning - Learnings

## Goal
Improve beam search performance through heuristic tuning to match or exceed baseline (66.7% WR).

## Improvements Implemented

### 1. Dynamic Weight Adaptation
- **Before:** Static 3000 damage weight
- **After:** Turn-aware weights (2000 early, 3000 mid, 4000 late game)
- **Location:** `beam_search_planner.lk:387-406`

### 2. Kill Probability Multipliers
- **Implementation:** 5x multiplier for 95%+ kill chance, 3x for 70%+, 1.5x for 50%+
- **Rationale:** Matches scenario scorer behavior
- **Location:** `beam_search_planner.lk:368-375`

### 3. Context-Aware Resource Penalties
- **Before:** Harsh penalties (-5 TP, -2 MP per unused)
- **After:** Reduced early game (turn 1-3), forgives small leftovers (< 3 TP, < 2 MP)
- **Location:** `beam_search_planner.lk:453-479`

### 4. Enhanced Synergy Detection
- **Improvements:**
  - Buff+damage bonus: 300 → 500
  - Shield+low HP: 400 → 600
  - Added proactive buffing bonus (+200)
  - Added shield stacking bonus
- **Location:** `beam_search_planner.lk:485-516`

### 5. Turn 1 Skip Logic
- **Rationale:** STR builds start with TP=2 (insufficient for meaningful sequences)
- **Implementation:** Only enable beam search on turn 2+
- **Location:** `unified_strategy.lk:61-67`

## Performance Results

| Configuration | Win Rate | Notes |
|--------------|----------|-------|
| Baseline (scenarios only) | 66.7% (2W-1L) | Target performance |
| Session 1 (pure beam search) | 0% (0W-3L) | No heuristic tuning |
| Session 3 (tuned heuristic) | 10% (1W-9L) | Improved but insufficient |
| Session 3 + turn 1 skip | 10% (1W-9L) | No significant change |

## Root Cause Analysis

### Why Beam Search Fails

**Symptom:** Beam search stops at depth 2, generating only 1-action sequences.

**Causes:**
1. **Low initial resources:** Turn 1 TP=2, insufficient for buffs (cost 5-7 TP) or attacks (cost 8+ TP)
2. **Short action sequences:** Only explores 1-2 actions before running out of valid moves
3. **Movement doesn't reach range:** Moving closer costs 7 MP but doesn't get into attack range yet
4. **No buff generation after movement:** After spending MP, still can't attack and has no TP for buffs

### Fundamental Architectural Mismatch

**LeekWars combat pattern:**
```
STEROID (7 TP) → Move (7 MP) → Attack × 3 (24 TP) → Reposition (optional)
```
This is a **complete 4-step plan** that scenarios generate as a single unit.

**Beam search explores:**
```
Depth 0: [empty state, TP=2, MP=7]
Depth 1: [Move action, TP=2, MP=0] ← Out of MP, still out of range
Depth 2: [No valid actions] ← Can't attack (out of range), can't buff (TP=2 < 7), can't move (MP=0)
→ SEARCH TERMINATES
```

**Why heuristic tuning can't fix this:**
- No amount of weight adjustment helps when there are literally 0 valid actions to score
- The problem is action generation, not action valuation
- Beam search needs to see 4+ action sequences to compete with scenarios

## Alternative Approaches (Not Implemented)

### 1. Macro Actions
**Idea:** Define "buff → attack" as a single macro action
- **Pro:** Would allow beam search to explore complete combos
- **Con:** Reduces to scenario generation (defeats purpose of emergent planning)

### 2. Hierarchical Search
**Idea:** Plan at two levels (high-level strategy, low-level execution)
- **Pro:** Could handle multi-step combos
- **Con:** Complex implementation, unclear if better than scenarios

### 3. Monte Carlo Tree Search (MCTS)
**Idea:** Replace beam search with MCTS for better long-horizon planning
- **Pro:** Proven in domains with long action sequences
- **Con:** High operation cost (12M limit would constrain search depth)

## Conclusion

**Beam search is unsuitable for LeekWars combat** in its current form because:
1. Low starting resources prevent meaningful early exploration
2. Action sequences too short (1-2 actions vs 4-6 needed)
3. Incremental exploration doesn't capture buff → attack synergies
4. Scenarios already solve this problem well (66.7% WR)

**Recommendation:** Disable beam search, continue with scenario-based planning.

## Files Modified

- `beam_search_planner.lk` - Improved heuristic scoring
- `atomic_action.lk` - Added debug output, cleaned up verbose logs
- `unified_strategy.lk` - Added turn 1 skip logic, disabled beam search
- `world_state.lk` - Added debug output for state creation
- `state_transition.lk` - Fixed EnemyState field naming
- `atomic_action_executor.lk` - Fixed weaponNeedsLoS checks

## Beam Search Status: DISABLED

Beam search remains in codebase for future exploration but is disabled (`USE_BEAM_SEARCH = false`) due to insufficient performance (10% vs 66.7% baseline).
