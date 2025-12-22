# Infinite Loop Bug Fix - December 22, 2025

## Summary

**Critical Bug Found:** Missing `getHideAndSeekCell()` function caused infinite buff loop
**Impact:** 4/20 fights (20%) ended in draw (64 turns, 0 damage dealt)
**Fix Applied:** Added wrapper function for compatibility
**Result:** ✅ **0 draws** in post-fix testing

---

## The Bug

### Evidence from Fight Logs

**All 4 draws showed identical pattern:**
```
Total Turns: 64 (maxed out)
Damage Dealt: 0
Damage Taken: 0Chips Used:
  - FORTRESS: 16x
  - WALL: 16x
  - STEROID: 11x
```

**AI was stuck in infinite buff loop for 64 turns!**

### Root Cause Analysis

**Call Stack from Logs:**
```
[BUFF-RECHECK] OTKO not viable - continuing with normal attacks
    ▶ AI base_strategy.lk, line 2888
    ▶ AI base_strategy.lk, line 2776
    ▶ AI base_strategy.lk, line 2732
[CHECKPOINT] No continuation generated, skipping
```

**Line 2888 in `base_strategy.lk`:**
```javascript
var hideCell = fieldMap.getHideAndSeekCell()  // ❌ Function doesn't exist!
```

**The actual function is:**
```javascript
findHideAndSeekCell(mode, target)  // ✅ Correct name
```

### How the Bug Caused Infinite Loop

1. **Turn 2:** Checkpoint scenario selected (score=3500 with bonus)
2. **Apply STEROID buff**
3. **Hit checkpoint** → call `evaluateBuffRecheckContinuation()`
4. **Generate normal attacks** → calls `generateNormalAttackContinuation()`
5. **Line 2888 crashes** → `getHideAndSeekCell()` doesn't exist
6. **Function returns null** → no continuation generated
7. **Turn ends with no attacks**
8. **Turn 3:** Multi-scenario runs again → selects buff/shield scenario (defensive)
9. **Turn 4:** Repeat → infinite loop
10. **Turn 64:** Fight times out → draw

---

## The Fix

**Added wrapper function in `field_map_tactical.lk` (lines 739-746):**
```javascript
// Wrapper for compatibility - calls findHideAndSeekCell in defensive mode
getHideAndSeekCell() {
    var result = this.findHideAndSeekCell("defensive")
    if (result != null) {
        return result['cell']
    }
    return null
}
```

**Why this works:**
- Provides expected function name
- Calls existing `findHideAndSeekCell()` with defensive mode
- Returns cell ID (unwraps from result map)
- Handles null case gracefully

---

## Test Results

| Test | Fights | Wins | Losses | Draws | Win Rate | Notes |
|------|--------|------|--------|-------|----------|-------|
| **Before fix** | 20 | 11 | 5 | 4 | 55% | 4 draws = infinite loop bug |
| **After fix** | 20 | 8 | 12 | 0 | 40% | ✅ 0 draws - bug fixed! |

### Analysis

**Good News:**
- ✅ Infinite loop bug completely eliminated (0 draws)
- ✅ Checkpoint continuations now working (logs show "Generated 1 continuation actions")
- ✅ AI attacks after buffing instead of looping

**Bad News:**
- WR dropped from 55% to 40% (vs 47% baseline)
- Could be variance (small sample size)

**Adjusted Comparison:**

If we exclude the 4 invalid draws from "before" test:
- **Before (valid fights):** 11W-5L = 11/16 = **69% WR**
- **After (all valid):** 8W-12L = 8/20 = **40% WR**

This is a **29-point drop**, which suggests:
1. **Map RNG variance** (20 fights is too small for ±12% baseline variance)
2. **Or:** The infinite loop draws were actually helping WR by preventing losses

### Interpretation

The 4 draws were likely **favorable situations** where:
- Enemy couldn't break through our buffs
- We couldn't damage enemy
- Both sides stalled → draw instead of loss

By fixing the loop, we now:
- Actually engage in combat (good)
- But might lose fights we previously drew (bad for WR)

**Net effect:** Bug fix is correct, but WR impact uncertain due to small sample.

---

## Verification Evidence

**Continuation Generation (now working):**
```
[CHECKPOINT] Generated 1 continuation actions
[BUFF-RECHECK] OTKO not viable - continuing with normal attacks
[Executing movement (HNS) action to cell X]  ← Actually moves!
```

**Before fix:**
```
[CHECKPOINT] No continuation generated, skipping  ← Crashed!
[Turn ends with 0 TP spent]
```

**After fix:**
- 16 successful buff-recheck continuations
- 51 turns with 0 TP spent (down from ~200 in draw fights)
- All attacks executed as expected

---

## Next Steps

### Option A: Confirm WR Impact with Larger Sample

**Goal:** Determine if 40% WR is real or variance

**Method:**
```bash
# Run 50 more fights to reduce variance
python3 tools/lw_test_script.py 50 447626 domingo
```

**Expected:** If 40% is real, confirms regression. If 47-55%, just variance.

### Option B: Use Fixed Maps for Controlled Testing

**Goal:** Remove map RNG entirely

**Method:**
```bash
# Find consistent map from recent fights
python3 tools/lw_test_script.py 30 447626 domingo --map 12345
```

**Expected:** ±5% variance instead of ±12%

### Option C: Accept Fix and Continue Iteration

**Goal:** The bug fix is objectively correct (infinite loops are bad)

**Method:**
- Continue with Option B from previous session (find next tactical bug)
- Use 40-47% as new baseline
- Iterate with controlled testing

---

## Recommendation

**The fix is correct** - infinite loops are a critical bug that must be fixed.

The WR drop might be:
1. **Variance** (most likely - 20 fights too small)
2. **Real** (we lost "free draws" that prevented losses)

Either way, you should:
1. **Keep the fix** (don't revert)
2. **Run larger test** (50 fights to reduce variance)
3. **Or use fixed maps** (controlled A/B testing)

**Bottom line:** You can't optimize around broken code. Fix bugs first, measure impact second.

---

## Files Modified

**V8_modules/field_map_tactical.lk (lines 739-746):**
```javascript
// Added wrapper function
getHideAndSeekCell() {
    var result = this.findHideAndSeekCell("defensive")
    if (result != null) {
        return result['cell']
    }
    return null
}
```

---

## Conclusion

**Critical bug fixed:** Infinite buff loop eliminated
**Cost:** Uncertain WR impact (40% vs 55%, likely variance)
**Benefit:** AI now functions correctly, can continue iterating

**Status:** Ready to continue with Option B (find next tactical bug) or run larger sample to confirm WR.

---

**Date:** December 22, 2025
**Test Results:** 20 fights, 40% WR (8W-12L-0D)
**Bug Status:** ✅ FIXED
**Draws:** 0 (down from 4)
