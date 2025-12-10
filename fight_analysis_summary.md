# Fight Analysis Summary - EbolaLeek vs Domingo (35% Win Rate)

## Test Results
- **20 fights total:** 7 wins, 11 losses, 2 draws
- **Win rate:** 35%
- **Fight duration:** ~5.6 turns average (both wins and losses)

## Critical Problems Found

### Problem 1: CHIP_WARM_UP Applied Twice (ROOT CAUSE)
**Location:** `base_strategy.lk:930-936` and `agility_strategy.lk:138-143`

**Issue:** WARM_UP is being applied in two places:
1. `turnOneBuffs()` in base_strategy uses `useChip(CHIP_WARM_UP)` directly (7 TP)
2. `createOffensiveScenario()` in agility_strategy tries to apply it again (7 TP)

**Result:** Turn 1 sequence uses all TP on buffs:
- CHIP_KNOWLEDGE (2 TP)
- CHIP_ELEVATION (2 TP)
- CHIP_ARMORING (2 TP)
- CHIP_WARM_UP (7 TP)
- **Total: 13 TP spent on buffs, 0 TP remaining for combat**

**Impact:**
- No TP left for MIRROR/THORN damage return chips
- Turn 1 ends with "WARNING: Ended at position with no attacks available!"
- 19 out of 20 fights show this warning

### Problem 2: Low Damage Output
**Losses:** We deal only **70%** of the damage we take
- Average damage dealt: 2,656 per fight
- Average damage taken: 3,805 per fight
- Enemy healing: 2,473 per fight

**Wins:** We deal **124%** of the damage we take
- Average damage dealt: 3,159 per fight
- Average damage taken: 2,548 per fight
- Enemy healing: 1,850 per fight

**Analysis:** When we can't apply damage return buffs on Turn 1, we lose the damage race throughout the fight.

### Problem 3: Turn 1 Positioning Failures
Multiple fights show: "Ended at position X with no attacks available"
- After spending all TP on buffs, we use ADRENALINE to get 4 TP back
- Then we move toward weapon cells but can't reach them
- Turn ends with 0 TP, no attacks executed
- Damage return never applied, putting us at disadvantage

## Recommended Fixes

### Fix 1: Remove WARM_UP from turnOneBuffs() (CRITICAL)
**File:** `V8_modules/strategy/base_strategy.lk:930-936`

**Remove these lines:**
```leekscript
// Agility build: Apply CHIP_WARM_UP before damage return buffs
if (player._agility >= player._strength && player._agility >= player._magic) {
    if (mapContainsKey(arsenal.playerEquippedChips, CHIP_WARM_UP)) {
        debug("Using CHIP_WARM_UP (agility build) - +170-190 Agility for 3 turns (attrition boost)")
        useChip(CHIP_WARM_UP, player._id)
    }
}
```

**Reason:** AgilityStrategy already handles WARM_UP intelligently at line 138-143, checking TP budget and ensuring enough TP remains for combat. Let the strategy control its own buffs.

### Fix 2: Reduce HP Buff Costs on Turn 1
**File:** `V8_modules/strategy/base_strategy.lk:862-874`

**Consider:** Make HP buffs conditional or skip some in PvP:
- KNOWLEDGE (2 TP) - Science/Magic boost
- ELEVATION (2 TP) - Wisdom boost
- ARMORING (2 TP) - Resistance boost

**Total saved if all removed:** 6 TP, allowing damage return + attacks on Turn 1

**Option:** Only apply these buffs when distance > 15 (very far start)

### Fix 3: Validate TP Budget in Agility Strategy
**File:** `V8_modules/strategy/agility_strategy.lk:155-171`

The check on line 162 is good:
```leekscript
if (playerTP >= chipObj._cost + minAttackTP)
```

But it's not being reached because TP is already spent in turnOneBuffs().

## Expected Improvement
After Fix 1 alone:
- Turn 1 will have 7 TP available for damage return chips (MIRROR/THORN)
- Agility strategy can properly apply its buffs in correct order
- Should eliminate the "No return chip available" warnings
- Expected win rate improvement: **35% → 55-60%**

## Next Steps
1. Apply Fix 1 immediately (remove WARM_UP duplication)
2. Test 20 fights to verify improvement
3. If needed, apply Fix 2 to further optimize Turn 1 TP usage
4. Monitor damage ratios to confirm combat effectiveness
