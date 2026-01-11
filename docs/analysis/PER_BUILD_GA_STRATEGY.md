# Per-Build GA Optimization Strategy

## The Concept

Instead of finding universal weights that work for all stat profiles, **optimize separately for each leek** and use build detection to load appropriate weights.

```
┌─────────────────────────────────────────────────────────┐
│ Universal Weights (Multi-Leek GA)                       │
│ ❌ Compromise: 75% WR weak, 80% balanced, 85% strong    │
│ ❌ One size fits all = mediocre for everyone            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Specialized Weights (Per-Build GA)                      │
│ ✅ Optimized: 85% WR weak, 88% balanced, 90% strong     │
│ ✅ Each build plays to its strengths perfectly          │
└─────────────────────────────────────────────────────────┘
```

---

## Architecture

### Single AI Script with Build Detection

```javascript
// weight_profiles.lk
class WeightProfiles {
    static function getProfile(player) {
        var primaryStat = max(str, max(mag, agi))

        if (primaryStat < 500) return WEAK_BUILD
        else if (primaryStat < 700) return BALANCED_BUILD
        else return STRONG_BUILD
    }

    static var WEAK_BUILD = {...}      // GA-optimized for 400 stats
    static var BALANCED_BUILD = {...}  // GA-optimized for 600 stats
    static var STRONG_BUILD = {...}    // GA-optimized for 800 stats
}

// scenario_scorer.lk (modified)
constructor(player, target, fieldMap) {
    this._profile = WeightProfiles.getProfile(player)

    // Use profile-specific weights
    this._killMult70 = WeightProfiles.getWeight(this._profile, 'kill_mult_70', 5.0)
    this._otkoBonus = WeightProfiles.getWeight(this._profile, 'otko_cell_bonus', 5000)
    // ... etc
}
```

---

## Workflow

### Phase 1: Train 3 Genomes (27 hours total)

Run GA separately for each stat profile:

```bash
# 1. Weak Build (400 STR, 1800 HP, 8 TP)
python3 tools/genetic_optimizer.py \
  --generations 10 \
  --population 15 \
  --fights-per-genome 60 \
  --opponents domingo betalpha rex hachess \
  --account weak_leek_account

# Save checkpoint: genome_weak_gen10.json
# Time: ~9 hours

# 2. Balanced Build (600 STR, 2500 HP, 10 TP)
python3 tools/genetic_optimizer.py \
  --generations 10 \
  --population 15 \
  --fights-per-genome 60 \
  --opponents domingo betalpha rex hachess \
  --account main

# Save checkpoint: genome_balanced_gen10.json
# Time: ~9 hours

# 3. Strong Build (800 STR, 3200 HP, 12 TP)
python3 tools/genetic_optimizer.py \
  --generations 10 \
  --population 15 \
  --fights-per-genome 60 \
  --opponents domingo betalpha rex hachess \
  --account strong_leek_account

# Save checkpoint: genome_strong_gen10.json
# Time: ~9 hours
```

**Total Time: 27 hours** (can run overnight)

---

### Phase 2: Generate weight_profiles.lk

Combine all 3 genomes into one file:

```bash
python3 tools/create_profile_weights.py \
  --weak genome_weak_gen10.json \
  --balanced genome_balanced_gen10.json \
  --strong genome_strong_gen10.json \
  --output V8_modules/weight_profiles.lk
```

**Output:**
```javascript
// V8_modules/weight_profiles.lk
class WeightProfiles {
    static var WEAK_BUILD = {
        'kill_mult_70': 4.2,          // Conservative (from GA)
        'otko_cell_bonus': 3500,      // Lower burst potential
        'threat_penalty_mult': 0.7,   // More cautious
        // ... 20+ optimized params
    }

    static var BALANCED_BUILD = {
        'kill_mult_70': 5.0,          // Standard (from GA)
        'otko_cell_bonus': 5000,      // Medium burst
        'threat_penalty_mult': 0.5,   // Balanced
        // ... 20+ optimized params
    }

    static var STRONG_BUILD = {
        'kill_mult_70': 6.2,          // Aggressive (from GA)
        'otko_cell_bonus': 6500,      // High burst potential
        'threat_penalty_mult': 0.3,   // Less cautious
        // ... 20+ optimized params
    }
}
```

---

### Phase 3: Integrate into scenario_scorer.lk

Modify scorer to use profile-specific weights:

```javascript
// scenario_scorer.lk (modified)
include("weight_profiles")

class ScenarioScorer {
    _player = null
    _target = null
    _fieldMap = null
    _profile = null          // NEW: Weight profile

    constructor(player, target, fieldMap) {
        this._player = player
        this._target = target
        this._fieldMap = fieldMap

        // NEW: Detect and load profile
        this._profile = WeightProfiles.getProfile(player)
        debug("[SCORER] Using profile for " + player._strength + " STR leek")
    }

    score(simResult) {
        var score = 0

        // Use profile-specific weights
        var killMult70 = WeightProfiles.getWeight(this._profile, 'kill_mult_70', 5.0)
        var otkoBonus = WeightProfiles.getWeight(this._profile, 'otko_cell_bonus', 5000)

        if (killProbability >= 0.70) {
            damageWeight *= killMult70  // Profile-specific!
        }

        if (finalPos is OTKO cell) {
            score += otkoBonus  // Profile-specific!
        }

        // ... rest of scoring
    }
}
```

---

### Phase 4: Test & Upload

```bash
# Test with weak leek
python3 tools/lw_test_script.py 50 447626 domingo --leek WeakLeek
# Expected: 80-85% WR (vs 75% with universal weights)

# Test with balanced leek
python3 tools/lw_test_script.py 50 447626 domingo --leek BalancedLeek
# Expected: 85-88% WR (vs 80% with universal weights)

# Test with strong leek
python3 tools/lw_test_script.py 50 447626 domingo --leek StrongLeek
# Expected: 88-92% WR (vs 85% with universal weights)

# Upload single AI (works for all leeks)
python3 tools/upload_v8.py
```

---

## Cost-Benefit Analysis

### Multi-Leek GA (Universal Weights)
- **Training:** 9 hours (1 run, 3 leeks tested together)
- **Result:** Compromised weights (75-85% WR range)
- **Maintenance:** 1 AI script
- **Best for:** Quick iteration, similar stat profiles

### Per-Build GA (Specialized Weights)
- **Training:** 27 hours (3 runs, each optimized separately)
- **Result:** Optimized weights (80-92% WR range)
- **Maintenance:** 1 AI script (with profile detection)
- **Best for:** Production use, diverse stat profiles

---

## Expected Performance Gains

### Weak Build (400 STR)
| Approach | Win Rate | Improvement |
|----------|----------|-------------|
| Baseline (V1) | 60% | - |
| Multi-Leek GA | 75% | +15pp |
| **Per-Build GA** | **82%** | **+22pp** ✅ |

### Balanced Build (600 STR)
| Approach | Win Rate | Improvement |
|----------|----------|-------------|
| Baseline (V1) | 80% | - |
| Multi-Leek GA | 82% | +2pp |
| **Per-Build GA** | **88%** | **+8pp** ✅ |

### Strong Build (800 STR)
| Approach | Win Rate | Improvement |
|----------|----------|-------------|
| Baseline (V1) | 70% | - |
| Multi-Leek GA | 85% | +15pp |
| **Per-Build GA** | **92%** | **+22pp** ✅ |

**Key Insight:** Biggest gains for weak/strong builds (edge cases that universal weights struggle with).

---

## Practical Considerations

### Do You Need All 3 Profiles?

**Minimum Viable:**
```bash
# Just 2 profiles (weak + strong)
python3 create_profile_weights.py \
  --weak genome_weak.json \
  --balanced genome_weak.json \  # Reuse weak
  --strong genome_strong.json

# Profile detection: <600 = weak, >=600 = strong
```

**Recommended:**
- 3 profiles (weak/balanced/strong) - Covers 95% of cases
- Takes 27 hours total (3 overnight runs)

**Overkill:**
- 5+ profiles (extreme specialization) - Diminishing returns

### Can You Run Them In Parallel?

**Yes, with multiple accounts:**
```bash
# Terminal 1 (Account: weak_leeks)
python3 genetic_optimizer.py --account weak --leek WeakLeek

# Terminal 2 (Account: main)
python3 genetic_optimizer.py --account main --leek BalancedLeek

# Terminal 3 (Account: cure)
python3 genetic_optimizer.py --account cure --leek StrongLeek

# Total time: 9 hours (parallel) vs 27 hours (sequential)
```

---

## Alternative: Separate AI Scripts

Instead of one AI with profiles, upload 3 separate AIs:

### Workflow
```bash
# 1. Train 3 genomes (same as above)

# 2. Apply and upload separately
python3 apply_best_genome.py genome_weak.json
python3 upload_v8.py --name "V8_Weak"

python3 apply_best_genome.py genome_balanced.json
python3 upload_v8.py --name "V8_Balanced"

python3 apply_best_genome.py genome_strong.json
python3 upload_v8.py --name "V8_Strong"

# 3. In LeekWars UI: Assign each AI to appropriate leeks
```

**Pros:**
- Simpler (no profile detection needed)
- Easy to debug per build
- Can A/B test different versions

**Cons:**
- 3 AI uploads to maintain
- Manual assignment in UI
- Code duplication

---

## Recommendation

### For Your 4 Leeks

If you have 4 leeks with different stats:

**Option 1: 3-Profile System (Recommended)**
```
Leek 1 (Weak)      → WEAK_BUILD profile
Leek 2 (Balanced)  → BALANCED_BUILD profile
Leek 3 (Balanced)  → BALANCED_BUILD profile
Leek 4 (Strong)    → STRONG_BUILD profile
```

Single AI, 3 profiles, covers all cases.

**Option 2: 4 Separate AIs**
```
Leek 1 → V8_Weak_Build
Leek 2 → V8_Balanced_Build
Leek 3 → V8_Balanced_Build
Leek 4 → V8_Strong_Build
```

More work to maintain, but maximum control.

---

## Next Steps

1. **Decide approach:**
   - 3-profile system (1 AI, auto-detect) ← Recommended
   - 4 separate AIs (manual assignment)

2. **Run GA training:**
   - Sequential: 27 hours (3 runs × 9h each)
   - Parallel: 9 hours (with 3 accounts)

3. **Test results:**
   - Validate each profile gets 80%+ WR
   - Compare to baseline (should see +5-20pp gains)

4. **Deploy:**
   - Upload single AI (with profiles)
   - OR upload 3-4 separate AIs

**Ready to start? Which approach do you prefer?**
