# Stat-Normalized Scoring Weights

## Problem
Current GA evolves FIXED weights optimized for one leek's stat profile. These don't generalize to leeks with different stats.

## Solution: Normalize Critical Parameters

### 1. Kill Multipliers (Scale with Damage Consistency)

**Current (Fixed):**
```javascript
if (killProbability >= 0.70) {
    damageWeight *= 4.707  // Same for all leeks
}
```

**Proposed (Normalized):**
```javascript
// Normalize by damage output reliability
var damageReliability = this.calculateDamageReliability()  // 0.5 - 1.5

if (killProbability >= 0.70) {
    var baseKillMult = 5.0  // GA-tuned base
    damageWeight *= baseKillMult * damageReliability
}

calculateDamageReliability() {
    // High primary stat → more reliable damage
    var primaryStat = max(this._player._strength, this._player._magic, this._player._agility)

    // 400 stat → 0.8x (less reliable)
    // 600 stat → 1.0x (baseline)
    // 800 stat → 1.2x (very reliable)
    return 0.6 + (primaryStat / 1500.0)
}
```

**Impact:** Prevents weak leeks from overcommitting to OTKO attempts, allows strong leeks to be more aggressive.

---

### 2. Threat Penalty (Scale with HP Pool)

**Current (Fixed):**
```javascript
threatPenalty = -threatAtPos * 0.429  // Same penalty for 1500 HP and 3000 HP
```

**Proposed (Normalized):**
```javascript
// Normalize by effective HP
var ehpRatio = this._player._currHealth / 2000.0  // Baseline 2000 HP

var baseThreatPenalty = 0.5  // GA-tuned base
var normalizedPenalty = baseThreatPenalty * (2000.0 / this._player._maxHealth)

threatPenalty = -threatAtPos * normalizedPenalty

// 1500 HP leek → 0.5 * (2000/1500) = 0.67 penalty (more cautious)
// 3000 HP leek → 0.5 * (2000/3000) = 0.33 penalty (more brave)
```

**Impact:** Tanks can afford to be aggressive, glass cannons stay safe.

---

### 3. OTKO Cell Bonus (Scale with Burst Potential)

**Current (Fixed):**
```javascript
otkoBonus = 5000  // Same for all burst potentials
```

**Proposed (Normalized):**
```javascript
// Normalize by burst damage potential
var burstPotential = this.calculateBurstPotential()  // 500-2000 range

var baseOTKOBonus = 5000  // GA-tuned base
var normalizedBonus = baseOTKOBonus * (burstPotential / 1000.0)

otkoBonus = normalizedBonus

calculateBurstPotential() {
    // Estimate max damage in one turn
    var primaryStat = max(this._player._strength, this._player._magic, this._player._agility)
    var tp = this._player._tp

    // Rough estimate: Primary stat * TP efficiency
    return primaryStat * (tp / 6.0)  // Avg 6 TP per strong attack
}
```

**Impact:** High-burst leeks prioritize OTKO positioning more, low-burst leeks focus on sustained damage.

---

### 4. Buff Weight (Scale with Available TP)

**Current (Fixed):**
```javascript
if (buffChip == CHIP_STEROID) value += 200  // Same regardless of TP pool
```

**Proposed (Normalized):**
```javascript
// Normalize by TP economy
var tpRatio = this._player._maxTP / 10.0  // Baseline 10 TP

var baseSteroidValue = 200  // GA-tuned base
var normalizedValue = baseSteroidValue * tpRatio

if (buffChip == CHIP_STEROID) value += normalizedValue

// 8 TP leek → 200 * 0.8 = 160 (buffs less valuable)
// 12 TP leek → 200 * 1.2 = 240 (buffs more valuable)
```

**Impact:** TP-rich leeks value buffs more (can afford the cost), TP-poor leeks prioritize direct damage.

---

## Implementation Strategy

### Phase 1: Add Normalization Layer (1 hour)
```javascript
class ScenarioScorer {
    // ... existing code ...

    // NEW: Calculate normalization factors once per scorer instance
    constructor(player, target, fieldMap) {
        this._player = player
        this._target = target
        this._fieldMap = fieldMap

        // Pre-calculate normalization factors
        this._damageReliability = this.calculateDamageReliability()
        this._hpNormalization = 2000.0 / player._maxHealth
        this._burstPotential = this.calculateBurstPotential()
        this._tpNormalization = player._maxTP / 10.0
    }

    calculateDamageReliability() {
        var primaryStat = max(this._player._strength, this._player._magic, this._player._agility)
        return 0.6 + (primaryStat / 1500.0)
    }

    calculateBurstPotential() {
        var primaryStat = max(this._player._strength, this._player._magic, this._player._agility)
        return primaryStat * (this._player._maxTP / 6.0)
    }
}
```

### Phase 2: Normalize Critical Parameters (2 hours)
Apply normalization to:
1. Kill multipliers (`kill_mult_70`, `kill_mult_50`)
2. Threat penalty (`threat_penalty_mult`)
3. OTKO bonus (`otko_cell_bonus`)
4. Buff values (top 5-10 important buffs)

### Phase 3: GA Re-Training (10 hours)
Re-run GA with normalized weights to tune the BASE values.

---

## Expected Benefits

| Benefit | Impact |
|---------|--------|
| **Generalization** | Weights work across different stat profiles |
| **Robustness** | No catastrophic failures on weak/strong leeks |
| **Fairness** | GA training data includes diverse stat ranges |
| **Performance** | Each leek plays to its strengths |

---

## Testing Protocol

1. **Baseline Test**: Current leek vs domingo (80% win rate)
2. **Implement Normalization**: Add layer to scenario_scorer.lk
3. **Validation Test**: Same leek vs domingo (should be ~80% still)
4. **Generalization Test**:
   - Create weak leek (400 stats) → should play cautiously
   - Create strong leek (800 stats) → should play aggressively
   - Both should win at reasonable rates vs appropriate opponents

---

## Alternative: Multi-Profile GA

Instead of stat normalization, train GA with multiple leek profiles:

```python
# Create 3 test leeks with different stat profiles
leek_profiles = [
    {'str': 400, 'mag': 200, 'agi': 100, 'hp': 1800},  # Weak
    {'str': 600, 'mag': 300, 'agi': 200, 'hp': 2500},  # Medium
    {'str': 800, 'mag': 400, 'agi': 300, 'hp': 3200},  # Strong
]

# Evaluate each genome on all 3 profiles
fitness = avg([test_profile(genome, profile) for profile in leek_profiles])
```

**Pros:** Simple, no code changes needed
**Cons:** 3x longer training time, might average to mediocre performance

---

**Recommendation:** Implement stat normalization first (3 hours work), then re-run GA. This is more elegant and likely more effective than multi-profile training.
