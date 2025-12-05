# LeekWars Probability Distribution System

## Overview

This module implements a complete probability density function system for accurate damage calculations in LeekWars, based on mathematical convolution theory.

## Why This Matters

The old system calculated **average** damage, which is inaccurate for:
- **OTKO decisions**: "Can I kill this enemy?" needs probability, not just average
- **Critical hits**: 40% chance of 1.3x damage creates complex distributions
- **Absolute armor**: Creates discrete probability mass at 0 damage
- **Damage combos**: Multiple attacks create bell curves, not flat ranges

## Mathematical Foundation

Based on the French LeekWars probability theory document, implementing:

1. **Polynomial manipulation** - Coefficients, primitives, translation
2. **Piecewise functions** - Functions defined by polynomial segments
3. **Probability distributions** - Atoms (discrete masses) + density (continuous)
4. **Convolution** - Combining multiple random variables (damage sources)

## Module Structure

```
V8_modules/math/
├── polynomial.lk              # Polynomial arithmetic
├── piecewise_function.lk      # Functions defined by segments
├── probability_distribution.lk # Main distribution class
├── damage_probability.lk      # Integration with LeekWars Arsenal
└── README.md                  # This file
```

## Usage Examples

### Example 1: Single Item Distribution

```leekscript
include("math/damage_probability");

// Calculate damage distribution for a weapon
var dist = DamageProbability.getItemDistribution(
    WEAPON_RIFLE,           // item ID
    400,                    // player strength
    0,                      // player magic
    0,                      // player wisdom
    50,                     // target absolute armor
    20,                     // target relative armor (%)
    300,                    // player agility (for crit)
    arsenal                 // arsenal instance
);

// Query probabilities
var killProb = dist.getProbabilityAtLeast(500);  // P(damage >= 500)
debug("Kill probability: " + (killProb * 100) + "%");
```

### Example 2: Combo Kill Probability

```leekscript
// Build combo: GRAPPLE + 3x HEAVY_SWORD
var combo = [
    CHIP_GRAPPLE,
    WEAPON_HEAVY_SWORD,
    WEAPON_HEAVY_SWORD,
    WEAPON_HEAVY_SWORD
];

var killProb = DamageProbability.getKillProbability(
    combo,
    target._currHealth,
    player._strength,
    player._magic,
    player._wisdom,
    target._absShield,
    target._relShield,
    player._agility,
    arsenal
);

if (killProb >= 0.85) {
    debug("OTKO highly likely (" + round(killProb * 100) + "%)");
    // Execute combo
}
```

### Example 3: Weapon Spam Distribution

```leekscript
// Calculate distribution for 5 rifle shots
var spamDist = DamageProbability.getWeaponSpamDistribution(
    WEAPON_RIFLE,
    5,                      // number of uses
    player._strength,
    player._magic,
    player._wisdom,
    target._absShield,
    target._relShield,
    player._agility,
    arsenal
);

// Get damage range with 90% confidence
var minDmg = DamageProbability.getMinimumGuaranteedDamage(...);
var maxDmg = DamageProbability.getMaximumPossibleDamage(...);

debug("90% of outcomes: " + minDmg + " - " + maxDmg + " damage");
```

## Integration with Strategies

### Strength Strategy - OTKO Check

Replace simple HP threshold with probability:

```leekscript
// OLD (inaccurate):
if (target._currHealth < player._currHealth * 0.35) {
    // Attempt OTKO
}

// NEW (accurate):
var killProb = arsenal.getAccurateKillProbability(
    comboItems,
    player._strength,
    player._magic,
    player._wisdom,
    player._agility,
    target
);

if (killProb >= 0.85) {
    // High confidence OTKO - execute
}
```

### Magic Strategy - Poison Damage Certainty

```leekscript
// Calculate guaranteed poison damage (minimum)
var poisonDist = DamageProbability.getComboDistribution(
    poisonChips,
    player._strength,
    player._magic,
    player._wisdom,
    0,  // poison bypasses armor
    0,
    player._agility,
    arsenal
);

var minPoisonDmg = DamageProbability.getMinimumGuaranteedDamage(...);

if (minPoisonDmg >= target._currHealth) {
    // Enemy will die to poison - hide and wait
}
```

## Performance Considerations

### Operations Limit

The LeekWars operations limit (10,000 per turn) can be exceeded with complex calculations. Optimize by:

1. **Cache distributions** - Don't recalculate same combo multiple times
2. **Limit combo size** - Convolution complexity grows with items
3. **Use simple estimates** for low-priority decisions

### When to Use Full System

**Use accurate probability for:**
- ✅ OTKO decisions (high impact)
- ✅ Critical tactical choices (teleport usage, etc.)
- ✅ End-game kill opportunities

**Use simple averages for:**
- ❌ Routine damage cell calculations
- ❌ Field map building (too many calculations)
- ❌ Low-stakes positioning

## Mathematical Details

### Convolution Formula

For two independent random variables X and Y with densities f and g:

```
(f * g)(s) = ∫ f(t) · g(s - t) dt
```

In LeekWars context:
- X = damage from item 1
- Y = damage from item 2
- X + Y = total combo damage
- Density of (X + Y) = f * g

### Critical Hits

Item with crit probability p and crit factor c:

```
density = (1 - p) · rectangle[min, max] + p · rectangle[min·c, max·c]
```

### Absolute Armor

Armor value a creates Dirac delta at 0:

```
P(damage = 0) = P(raw_damage ≤ a)
remaining_density = shifted and truncated at 0
```

## Testing

Run unit tests (when implemented):

```bash
# Test polynomial arithmetic
python3 tools/test_probability.py polynomial

# Test convolution
python3 tools/test_probability.py convolution

# Test full integration
python3 tools/test_probability.py integration
```

## References

- Original French probability theory document (included in project)
- CLAUDE.md - V8 development guide
- LeekWars damage formula documentation

## Future Enhancements

- [ ] Cache distribution calculations for common combos
- [ ] Add variance/standard deviation queries
- [ ] Optimize convolution for long weapon spam chains
- [ ] Add visualization for debugging (plot density functions)
- [ ] Implement general piecewise convolution (currently optimized for rectangles)

---

**Last Updated:** December 2025
**Author:** AI-assisted development based on mathematical specification
