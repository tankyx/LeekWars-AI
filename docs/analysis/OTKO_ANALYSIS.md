# OTKO Implementation Analysis
## December 16, 2025 - Calculated Burst Damage Detection

---

## Implementation Summary

### Changes Made
1. **Added `calculateBurstDamage(target, position, availableTP)` to base_strategy.lk**
   - Calculates actual damage from all equipped weapons
   - Accounts for weapon ranges, TP costs, max uses
   - Includes damage chips if TP remains
   - Considers enemy shields via `arsenal.getNetDamageAgainstTarget()`

2. **Added `hasOTKOOpportunity(target)` to base_strategy.lk**
   - Uses `calculateBurstDamage()` to get actual damage potential
   - Compares damage vs enemy HP
   - Threshold: 85% kill probability (damage / HP >= 0.85)
   - Minimum: 10 TP required

3. **Added OTKO Override in `generateAndEvaluateBestScenario()`**
   - Checks OTKO opportunity BEFORE multi-scenario evaluation
   - Calls strategy's `createOTKOScenario()` if viable
   - Falls back to multi-scenario if OTKO fails
   - Priority: OTKO > Emergency > Multi-Scenario

---

## Test Results (10 Fights vs Domingo)

### Performance Metrics
| Metric | Value | vs Baseline |
|--------|-------|-------------|
| **Win Rate** | 10% (1/10) | Same (no improvement yet) |
| **OTKO Triggers** | 1/10 fights | vs expected 5-6 (65%) |
| **Avg Damage Dealt** | 3,226 | -47% from baseline |
| **Avg Damage Taken** | 6,050 | Higher (worse) |
| **Damage Efficiency** | 0.53x | Taking 2x more than dealing |
| **Avg Fight Length** | 21.5 turns | Longer (attrition) |

### OTKO Trigger Analysis
**Single OTKO Event:**
- **Fight:** 50529636 (Turn 534)
- **Calculation:** `damage=1092 vs HP=915 (119% kill probability)`
- **Result:** ✅ WIN (only win in 10 fights)
- **Execution:** Teleport OTKO to cell 8, projected damage 1026

**Key Finding:** OTKO worked when triggered! But it only triggered once.

---

## Root Cause: Low OTKO Trigger Rate

### Why Only 1 OTKO?

#### 1. Fights End Too Quickly (Before OTKO Range)
```
Fight 50529644: 5 turns,  862 dmg dealt, 4724 taken  → Died early
Fight 50529635: 6 turns, 4817 dmg dealt, 3392 taken  → Enemy still healthy
Fight 50529639: 8 turns, 4043 dmg dealt, 7547 taken  → Died mid-fight
```

**Problem:** We're dying in 5-14 turns before enemy HP drops to OTKO range (~900-1200 HP).

#### 2. Damage Efficiency Too Low (0.53x)
- **We deal:** 3,226 avg damage/fight
- **We take:** 6,050 avg damage/fight
- **Ratio:** We're taking nearly **2x** the damage we deal

**Root Cause:** Multi-scenario system is selecting **conservative/defensive scenarios** instead of **aggressive damage scenarios**.

#### 3. 85% Kill Probability May Be Too Strict
- Baseline used 85% threshold
- But baseline also had higher damage output
- With current low damage, we rarely reach 85%

---

## Comparison: Baseline vs Current

### Baseline (60% WR)
**Strategy:**
- Every turn: Check OTKO at ~50% enemy HP
- OTKO triggered: 65% of fights
- Aggressive damage focus
- Smart STEROID buffing (skip if OTKO imminent)

**Execution:**
```lk
if (enemyHP < 50% || killProb >= 85%) {
    teleport()
    spam_ALL_weapons()
    use_damage_chips()
}
```

### Current (10% WR)
**Strategy:**
- Every turn: Calculate burst damage, check if >= 85% enemy HP
- OTKO triggered: 10% of fights (1/10)
- Multi-scenario favors sustained damage + healing
- Missing aggressive focus

**Problem:** Multi-scenario scores favor:
- eHP (healing): 1458-14580 points
- Positioning: 0-526 points
- Efficiency: 0-2060 points
- Damage: Only 1092-2544 points

**Damage is underweighted** compared to defensive metrics.

---

## Why Multi-Scenario Underperforms

### Scenario Scoring Bias
From fight 50529229:
```
Turn 44: Selected scenario score=4400
  → dmg=2280, eHP=1458, pos=0, eff=162, buff=500

Turn 66: Selected scenario score=6510
  → dmg=2280, eHP=2187, pos=526, eff=1017, buff=500
```

**Analysis:**
- Damage: 2280 (constant across scenarios)
- eHP: 1458-2187 (varies significantly)
- **Scenarios with higher eHP win**, even if damage is the same

**Conclusion:** Scorer is prioritizing healing/survival over damage output.

### Missing OTKO in Multi-Scenario
- Only 1 scenario has `repositioning="otko"`
- That scenario only adds teleport, **no weapon spam**
- Weapon spam happens in generic `getAttackActions(tpBudget * 0.8)`
- **Not maximizing burst potential**

---

## Recommended Fixes

### Priority 1: Boost Damage Scoring
**Current:**
- Damage weight: 1.0-1.5x
- eHP weight: 0.5-4.5x (urgency multiplier)
- Damage is equal or **lower** than defensive metrics

**Fix:**
Increase damage weight when enemy is killable:
```lk
// In scenario_scorer.lk:scoreScenario()
var damageWeight = this.calculateDamageWeight()

// BOOST: If enemy HP < burst damage potential, prioritize damage heavily
var enemyHP = this._target._currHealth
var burstDamage = simulationResult.damageDealt  // Immediate damage this turn

if (burstDamage >= enemyHP * 0.7) {  // Within kill range
    damageWeight *= 3.0  // Triple damage weight for kill opportunities
    debug("[SCORER-BOOST] Kill opportunity - tripling damage weight")
}
```

### Priority 2: Lower OTKO Threshold
**Current:** 85% kill probability
**Baseline:** 85% kill probability (but with higher damage output)

**Options:**
- A) Keep 85% but improve damage output first
- B) Lower to 75% (more aggressive)
- C) Add TP-dependent threshold:
  ```lk
  var threshold = 0.85
  if (playerTP >= 25) threshold = 0.75  // High TP = more aggressive
  if (playerTP >= 20) threshold = 0.80
  ```

### Priority 3: OTKO Scenario Improvements
**Current OTKO Scenario Issues:**
- Only checks from current position
- Doesn't check teleport positions
- Only adds teleport action, relies on generic attack actions

**Fix:**
- Use `fieldMap.findOptimalTeleportCell()` (already exists!)
- This calculates best teleport position WITH projected damage
- Already used in baseline strength_strategy.lk

---

## Next Steps

### Immediate Action
1. **Boost damage weight** when kill opportunity exists (Priority 1)
2. **Test with damage boost** - expect 30-40% WR improvement
3. **If still low,** lower OTKO threshold to 75%

### Expected Outcome
- **OTKO triggers:** 10% → 50-65%
- **Win rate:** 10% → 40-50%
- **Damage efficiency:** 0.53x → 0.8-1.0x

### Test Plan
```bash
python3 tools/upload_v8.py
python3 tools/lw_test_script.py 10 447626 domingo
```

---

## Conclusion

**What's Working:**
- ✅ Calculated burst damage detection (accurate)
- ✅ OTKO override system (triggers correctly)
- ✅ Healing system (fixed from before)

**What's Broken:**
- ❌ Multi-scenario favors defense over offense
- ❌ Damage scoring too low
- ❌ OTKO triggering only 10% vs expected 65%

**Core Issue:** Multi-scenario system is **risk-averse** - it picks scenarios that maximize survival (eHP) over kill opportunities (damage). This leads to low damage output, which prevents OTKO opportunities from arising.

**Solution:** Make scenario scorer **opportunistic** - when kill is possible, heavily prioritize damage over defense.

---

**Analysis Date:** December 16, 2025
**Analyst:** Claude Code
**Fights Analyzed:** 10 (IDs: 50529627-50529651)
**OTKO Triggers:** 1 (Fight 50529636 ✅ WIN)
