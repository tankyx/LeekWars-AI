# Integration Guide - Probability Distribution System

## How to Use in V8 Strategies

### Step 1: Include the Math Module (Optional - Advanced Usage Only)

The probability distribution system is **already integrated** into Arsenal's `getDamageBreakdown()` method, which now returns `min` and `max` damage values.

For **advanced probability calculations**, you can optionally include:

```leekscript
include("math/damage_probability");
```

### Step 2: Use Arsenal Methods (Recommended)

The Arsenal class now has built-in probability support:

```leekscript
// Simple kill probability estimate (no includes needed)
var killProb = arsenal.getKillProbability(
    [WEAPON_RIFLE, WEAPON_RIFLE, WEAPON_RIFLE],
    player._strength,
    player._magic,
    player._wisdom,
    player._agility,
    targetEntity
);

// Returns 0.0 to 1.0 probability
if (killProb >= 0.8) {
    debug("High kill probability!");
}
```

### Step 3: Update OTKO Logic in Strength Strategy

**Location:** `V8_modules/strategy/strength_strategy.lk`

**Before (inaccurate):**
```leekscript
// Line ~706: Old OTKO check
var lowHpThreshold = min(player._currHealth * 0.35, 500)
if (target._currHealth <= lowHpThreshold) {
    // Attempt OTKO
}
```

**After (accurate with probability):**
```leekscript
// Calculate available TP after STEROID
var tpForCombo = player._currTp - 7  // STEROID cost

// Build combo items list
var comboItems = [];
push(comboItems, CHIP_TELEPORTATION);  // 5 TP

// Add weapons we can afford
var remainingTP = tpForCombo - 5;
for (var wid in mapKeys(arsenal.playerEquippedWeapons)) {
    var w = arsenal.playerEquippedWeapons[wid];
    var uses = min(w._maxUse, floor(remainingTP / w._cost));

    for (var i = 0; i < uses; i++) {
        push(comboItems, wid);
        remainingTP -= w._cost;
    }
}

// Calculate kill probability with STEROID buff
var buffedStr = player._strength + 160;
var killProb = arsenal.getKillProbability(
    comboItems,
    buffedStr,
    player._magic,
    player._wisdom,
    player._agility,
    target
);

if (killProb >= 0.85) {
    debug("OTKO probability: " + round(killProb * 100) + "%");
    // Execute STEROID → TELEPORTATION → weapon spam
}
```

### Step 4: Integrate Min/Max Damage in projectTotalDamageOutput()

**Location:** `V8_modules/strategy/base_strategy.lk:415-545`

**Enhancement:**
```leekscript
public projectTotalDamageOutput(fromCell, targetEntity, includeBuffs) {
    // ... existing code ...

    // For each weapon, use min/max from breakdown
    for (var w in cell._weaponsList) {
        var uses = min(w._maxUse, floor(playerTP / w._cost));

        var bd = arsenal.getDamageBreakdown(
            buffedStr,
            player._magic,
            player._wisdom,
            w._id
        );

        // Use min for conservative estimate, max for optimistic
        var dmgPerUse = bd['total'];  // Average (current behavior)
        // var dmgPerUse = bd['min'];  // Conservative (guaranteed)
        // var dmgPerUse = bd['max'];  // Optimistic (best case)

        totalDamage += dmgPerUse * uses;
        playerTP -= w._cost * uses;
    }

    // ... rest of method ...
}
```

## Arsenal Integration - What's Already Available

### Enhanced `getDamageBreakdown()`

**Now returns:**
```leekscript
{
    'direct': 45.5,      // Average direct damage
    'dot': 120.0,        // Average poison damage
    'total': 165.5,      // Average total
    'min': 140.0,        // Minimum possible damage (NEW)
    'max': 191.0         // Maximum possible damage (NEW)
}
```

**Usage:**
```leekscript
var bd = arsenal.getDamageBreakdown(
    player._strength,
    player._magic,
    player._wisdom,
    WEAPON_RIFLE
);

debug("Rifle damage: " + bd['min'] + " - " + bd['max']);
```

### New Method: `getKillProbability()`

Simple probability estimate based on damage thresholds.

**Returns:**
- `0.9` if average damage ≥ target HP (high confidence)
- `0.5` if average damage ≥ 80% target HP (medium confidence)
- `0.1` otherwise (low confidence)

### Future Method: `getAccurateKillProbability()`

Will use full probability distribution system when `include("math/damage_probability")` is added.

**Currently:** Falls back to simple `getKillProbability()`
**Future:** Exact probability using convolution mathematics

## Gradual Migration Path

### Phase 1: Use Enhanced getDamageBreakdown() (Current)

✅ **Done** - All strategies can now access min/max damage
- No code changes required
- Backward compatible (existing code uses 'total' field)

### Phase 2: Update OTKO Logic (Recommended Next Step)

Update `strength_strategy.lk` OTKO check to use `getKillProbability()`:
```leekscript
var killProb = arsenal.getKillProbability(...);
if (killProb >= 0.85) { /* OTKO logic */ }
```

### Phase 3: Add Full Probability System (Advanced - Optional)

Only if needed for high-precision calculations:
1. Include `math/damage_probability.lk` in main.lk
2. Update Arsenal methods to use ProbabilityDistribution
3. Replace simple estimates with exact probability calculations

**Trade-off:**
- ✅ **Pro:** Extremely accurate kill probability
- ❌ **Con:** Higher operations cost (may hit 10k limit)

## Performance Notes

### Operations Cost Estimates

| Operation | Cost (ops) | When to Use |
|-----------|-----------|-------------|
| `getDamageBreakdown()` | ~50 | Always (already used) |
| `getKillProbability()` | ~200 | OTKO checks, critical decisions |
| Full probability distribution | ~1000-2000 | Only for critical, high-impact decisions |

### Optimization Tips

1. **Cache results** - Don't recalculate same combo multiple times
2. **Limit combo size** - Convolution cost grows with items
3. **Use thresholds** - Only calculate probability when average damage is close to target HP

Example:
```leekscript
// Quick reject: way too little damage
if (avgDamage < target._currHealth * 0.5) {
    return;  // Skip expensive calculation
}

// Quick accept: way more than enough
if (avgDamage > target._currHealth * 1.5) {
    // Execute combo without probability check
    return;
}

// Close call: use probability
var killProb = arsenal.getKillProbability(...);
```

## Testing the Integration

### Test 1: Verify Min/Max in Damage Breakdown

```leekscript
var bd = arsenal.getDamageBreakdown(400, 0, 0, WEAPON_RIFLE);
debug("Rifle with 400 STR:");
debug("  Min: " + bd['min']);
debug("  Max: " + bd['max']);
debug("  Avg: " + bd['total']);
```

**Expected output:** Min < Avg < Max (reasonable damage range)

### Test 2: Kill Probability Check

```leekscript
var combo = [WEAPON_RIFLE, WEAPON_RIFLE, WEAPON_RIFLE];
var prob = arsenal.getKillProbability(
    combo, 400, 0, 0, 300, targetEntity
);
debug("3x Rifle kill probability: " + (prob * 100) + "%");
```

**Expected:** Probability between 0-100%

## Troubleshooting

### Issue: "min/max fields undefined"

**Cause:** Old cached Arsenal instance
**Fix:** Restart fight or upload fresh V8 code

### Issue: Operations limit exceeded

**Cause:** Too many probability calculations
**Fix:** Use simple `getKillProbability()` instead of full distribution

### Issue: Kill probability always 0.1

**Cause:** Combo damage way below target HP
**Fix:** Check if combo is actually viable (add more items or stronger items)

## Next Steps

1. ✅ **Completed:** Math module implementation
2. ✅ **Completed:** Arsenal integration (min/max in getDamageBreakdown)
3. ⏭️ **TODO:** Update strength_strategy.lk OTKO logic
4. ⏭️ **TODO:** Test in real fights against domingo/betalpha
5. ⏭️ **Optional:** Add full probability distribution for advanced cases

---

**Questions?** Check `V8_modules/math/README.md` for detailed examples.
