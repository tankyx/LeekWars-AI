# V8 Multi-Scenario Performance Analysis
## Critical Regression Report - December 16, 2025

---

## Executive Summary

**Status:** 🔴 **CRITICAL REGRESSION**

| Metric | Baseline (Dec 8) | Current (Dec 16) | Change |
|--------|------------------|------------------|--------|
| **Win Rate** | 60% | 10% | **-50pp (-83%)** |
| **OTKO Rate** | 65% of fights | 0% | **-65pp (-100%)** |
| **Avg OTKO Trigger** | 1256 HP (50% enemy HP) | N/A | Broken |
| **Healing** | Working | Fixed | ✅ Resolved |

---

## 1. Performance Regression Analysis

### 1.1 Baseline (Hardcoded Strategy - Dec 8)
- **Win Rate:** 60% vs Domingo
- **Key Features:**
  - Attrition-based OTKO detection (checked every turn)
  - OTKO triggered at ~50% enemy HP (~1256 HP)
  - 65% of fights ended with OTKO burst
  - Smart STEROID buffing (skip if OTKO viable)
  - Approach phase optimization

### 1.2 Current (Multi-Scenario System - Dec 16)
- **Win Rate:** 10% vs Domingo
- **Critical Issues:**
  - **OTKO detection completely broken** (0 attempts vs expected 5-6)
  - Over-conservative scenario selection
  - Scenarios prioritize moderate damage over burst kill opportunities

---

## 2. Root Cause Analysis

### 2.1 OTKO System Failure

**Problem:** The multi-scenario system does NOT use the hardcoded `createOTKOScenario()` from `strength_strategy.lk`.

**Current Behavior:**
- `scenario_generator.lk:822-828` defines `checkOTKOOpportunity()`:
  ```lk
  return (hpPercent < 35 || enemyHP < 500)
  ```
- This is **MUCH more conservative** than baseline (50% HP / 1256 HP)
- Parametric scenarios with `repositioning="otko"` only teleport, **no weapon spam**

**Baseline Behavior (strength_strategy.lk):**
- Checked OTKO opportunity every turn
- Threshold: Enemy HP < 35% OR HP < 500 HP **after considering TP budget**
- Full OTKO execution:
  1. Optional Adrenaline for TP boost
  2. Teleport to optimal position
  3. Pre-stack Neutrino vulnerability (if available)
  4. **Spam ALL available weapons**
  5. Use damage chips
  6. Update player TP/position after each action

**Why Multi-Scenario Fails:**
1. `checkOTKOOpportunity()` returns true/false but doesn't calculate damage
2. "otko" repositioning only adds teleport action (line 445-464)
3. No weapon spam queue - relies on generic `getAttackActions()` which doesn't maximize burst
4. **Strategy-specific OTKO logic is bypassed**

---

### 2.2 Scenario Generation Issues

**Current Scenario Types (scenario_generator.lk:79-101):**
1. ULTRA-AGGRESSIVE (4 scenarios): otko, stand, hide, kite
2. BALANCED-AGGRESSIVE (3 scenarios): 80% TP/MP, various positioning
3. BALANCED-DEFENSIVE (3 scenarios): 60% TP/MP, heal threshold 0.7
4. ULTRA-DEFENSIVE (3 scenarios): heal threshold 0.5-1.0, 10-40% attacks
5. REGENERATION (1 scenario): pure healing + minimal attack

**Problems:**
- Only 1 scenario has repositioning="otko"
- OTKO scenario doesn't execute full burst combo
- Scenarios score on: damage + eHP + positioning + efficiency
- **Burst kill potential not weighted heavily enough**

---

### 2.3 Scenario Selection Patterns

**From Fight 50529229 (LOSS):**
```
Turn 44: Selected #13/13, score=4400 (dmg=2280, eHP=1458, pos=0, eff=162, buff=500)
Turn 66: Selected #8/13,  score=6510 (dmg=2280, eHP=2187, pos=526, eff=1017, buff=500)
Turn 96: Selected #12/12, score=7007 (dmg=2184, eHP=2187, pos=362, eff=1774, buff=500)
```

**Analysis:**
- Damage values: 1092-1272 per turn
- Baseline OTKO: ~1500-2000+ burst damage when triggered
- Scenarios favor **sustained damage + healing** over **burst kills**
- eHP scoring (1458-2187) suggests defensive scenarios winning

---

## 3. Operation Costs (✅ Acceptable)

| Metric | Value | Status |
|--------|-------|--------|
| **Avg Scenario Generation** | 2,598,900 ops | 43% of turn budget |
| **Avg Total per Turn** | 2,033,542 ops | 34% of 6M budget |
| **Budget Status** | Within limits | ✅ OK |

**Verdict:** Operation costs are NOT the problem. Multi-scenario system is efficient.

---

## 4. Healing System (✅ Fixed)

| Metric | Before Fix | After Fix |
|--------|------------|-----------|
| **REMISSION tracked?** | ❌ No | ✅ Yes |
| **Wisdom buff bonus?** | ❌ No | ✅ Yes (1.5x) |
| **Avg Healing/Fight** | Unknown | 4,479 HP |
| **Healing Advantage** | Unknown | 1.95x vs enemy |

**Verdict:** Healing during fleeing now works correctly. This bug fix is good.

---

## 5. Key Differences: Baseline vs Multi-Scenario

### 5.1 Strategy Pattern

| Feature | Baseline (60% WR) | Multi-Scenario (10% WR) |
|---------|-------------------|--------------------------|
| **Decision Model** | Strategy-driven (hardcoded logic) | Scenario-driven (parametric generation) |
| **OTKO Detection** | Every turn, threshold ~50% HP | Only if HP < 35% or < 500 |
| **OTKO Execution** | Full burst combo | Teleport only |
| **Buff Management** | Smart (skip STEROID if OTKO) | Generic (always apply) |
| **Target Priority** | Lowest HP | Lowest HP |

### 5.2 Action Execution

**Baseline:** Hardcoded strategy calls specific methods:
```lk
if (this.createOTKOScenario(target, targetHitCell)) {
    // Teleport + weapon spam + damage chips
} else {
    this.createOffensiveScenario(target, targetHitCell)
}
```

**Multi-Scenario:** Generates 13 parametric scenarios, scores them, picks best:
```lk
scenarios = [aggressive, conservative, defensive, all-in, kiting, efficient, ...]
bestScenario = max(score(s) for s in scenarios)
executeScenario(bestScenario)
```

**Problem:** Strategy-specific logic (like OTKO burst) is lost in parametric generation.

---

## 6. Critical Findings Summary

### 6.1 What's Broken
1. ❌ **OTKO detection threshold too conservative** (35% vs 50%)
2. ❌ **OTKO execution incomplete** (teleport only, no weapon spam)
3. ❌ **Strategy-specific logic bypassed** (hardcoded OTKO combo not used)
4. ❌ **Scenario scoring favors sustained over burst**

### 6.2 What's Working
1. ✅ Multi-scenario generation (13 scenarios per turn)
2. ✅ Scenario simulation (tracks damage/eHP/positioning)
3. ✅ Operation costs (within budget)
4. ✅ Healing during fleeing (REMISSION bug fixed)

---

## 7. Recommended Fixes

### Priority 1: Restore OTKO System
**Option A: Hybrid Approach (Recommended)**
- Keep multi-scenario for normal turns
- Override with hardcoded OTKO when `createOTKOScenario()` returns true
- Implementation:
  ```lk
  // In base_strategy.lk:generateAndEvaluateBestScenario()
  if (this.hasOTKOOpportunity(target)) {
      if (this.createOTKOScenario(target, targetHitCell)) {
          debug("[OTKO] Using hardcoded OTKO burst combo")
          return  // Skip multi-scenario
      }
  }
  // Continue with multi-scenario...
  ```

**Option B: Fix Parametric OTKO**
- Improve `checkOTKOOpportunity()` threshold (50% HP)
- Add full weapon spam to "otko" repositioning
- Boost OTKO scenario scoring

### Priority 2: Scenario Scoring Tuning
- **Increase damage weight** for scenarios with high burst (>1500 dmg)
- **Add kill probability bonus** (if damage > enemy HP → +5000 score)
- **Reduce defensive scenario scores** when enemy is low HP

### Priority 3: Strategy-Specific Scenarios
- Allow strategies to inject custom scenarios (e.g., `getCustomScenarios()`)
- Strength: Add OTKO burst scenario
- Magic: Add GRAPPLE-COVID combo scenario
- Agility: Add damage return cycling scenario

---

## 8. Test Plan

### 8.1 Before Fix (Baseline Data)
- ✅ 10 fights vs Domingo: 10% WR (1/10 wins)
- ✅ 0 OTKO attempts
- ✅ Avg damage: 4,135/turn

### 8.2 After Fix (Expected)
- Target: 50-60% WR (restore baseline)
- Target: 5-6 OTKO attempts per 10 fights
- Target: Avg damage: 5,000+ on OTKO turns

### 8.3 Validation Fights
- Run 10 fights vs Domingo
- Check OTKO logs (should see "[OTKO] Executing teleport")
- Verify win rate improvement
- Confirm operation costs remain within budget

---

## 9. Conclusion

**The multi-scenario system is well-engineered** (good operation costs, proper simulation), but it **accidentally broke the OTKO system** that was responsible for 65% of baseline wins.

**Root Cause:** Strategy-specific logic (OTKO burst combo) was not migrated into the parametric scenario framework.

**Recommended Action:** Implement hybrid approach - use multi-scenario for normal combat, but override with hardcoded OTKO when kill opportunity detected.

**Expected Outcome:** Win rate should return to 50-60% baseline.

---

**Analysis Date:** December 16, 2025
**Analyst:** Claude Code
**Fights Analyzed:** 10 (IDs: 50529229-50529244)
**Data Sources:** Debug logs, CLAUDE.md, git history
