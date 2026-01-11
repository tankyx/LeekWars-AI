# Genetic Algorithm V2 - Critical Improvements

## What Went Wrong in V1

| Issue | Impact | Result |
|-------|--------|--------|
| **2 opponents only** (domingo, betalpha) | No AGI training data | AGI weight collapsed -71% |
| **20 fights/genome** | ±14% confidence interval | Lucky streaks mistaken for skill |
| **No parameter bounds** | Catastrophic drift | Weights went to extremes |
| **No validation split** | Overfitting undetected | 82% training → 41% real |
| **Binary fitness** (win/loss) | No gradient signal | Can't distinguish "close loss" from "stomped" |

## V2 Improvements

### 1. Opponent Diversity ✅
```python
# OLD (V1)
opponents = ['domingo', 'betalpha']  # 2 bots, STR+MAG only

# NEW (V2)
opponents = ['domingo', 'betalpha', 'rex', 'hachess']  # 4 bots, covers all builds
train_opponents = ['domingo', 'betalpha']  # Training set
val_opponents = ['rex', 'hachess']         # Validation set (held-out)
```

**Impact:**
- Prevents build-specific overfitting
- Cross-validation detects generalization gaps
- AGI/RESIST strategies remain viable

### 2. Parameter Bounds ✅
```python
bounds = {
    'str_damage_base': (1.0, 3.0),   # Baseline: 1.5
    'mag_damage_base': (0.5, 1.5),   # Baseline: 0.8
    'agi_damage_base': (0.8, 2.0),   # Baseline: 1.3 (PROTECTED!)
    'kill_mult_70': (3.0, 7.0),      # Baseline: 5.0
    'threat_penalty_mult': (0.2, 1.0),  # Baseline: 0.5
    # ... 13 total bounded parameters
}
```

**Impact:**
- Prevents AGI collapse (0.378 → bounded to 0.8-2.0)
- Keeps parameters in reasonable ranges
- Faster convergence (less wasted exploration)

### 3. Cross-Validation Split ✅
```python
# Training: 2 bots × 20 fights = 40 fights/genome (GA fitness)
train_opponents = ['domingo', 'betalpha']

# Validation: 2 bots × 20 fights = 40 fights (every new best genome)
val_opponents = ['rex', 'hachess']

# Overfitting detection
if (train_fitness - val_fitness) > 0.15:
    print("⚠️ OVERFITTING DETECTED!")
```

**Impact:**
- Early detection of overfitting
- Prevents catastrophic deployment (41% disaster avoided)
- Real-time feedback during training

### 4. Increased Sample Size (Recommended)
```python
# OLD (V1)
fights_per_genome = 20  # ±14% confidence interval

# NEW (V2 - Recommended)
fights_per_genome = 40  # ±10% confidence interval
# Training: 2 bots × 20 = 40 fights
# Validation: 2 bots × 20 = 40 fights (separate)
```

**Impact:**
- More reliable fitness estimates
- Fewer false positives (lucky genomes)
- Better gradient signal for evolution

---

## Training Cost Comparison

| Configuration | Opponents | Fights/Genome | Total Fights | Time |
|--------------|-----------|---------------|--------------|------|
| **V1 (Failed)** | 2 | 20 | 3,000 | ~5h |
| **V2 (Recommended)** | 4 (2 train + 2 val) | 40+40 | 12,000 | ~18h |
| **V2 (Fast)** | 4 (2 train + 2 val) | 20+20 | 6,000 | ~9h |

*Assumes: 15 population, 10 generations, 0.3s delay*

---

## Example Output (V2)

```
============================================================
GENERATION 1 - EVALUATION
============================================================
Training opponents: domingo, betalpha
Validation opponents: rex, hachess

🧪 Evaluating genome 1/15...
  🎯 Testing vs domingo (20 fights)...
  ✅ domingo: 16/20 wins (80.0%)
  🎯 Testing vs betalpha (20 fights)...
  ✅ betalpha: 14/20 wins (70.0%)
  📊 Genome 1 fitness: 0.750 (30/40 wins)

[... 14 more genomes ...]

🎉 NEW BEST GENOME! Training fitness: 0.850

🔍 Validating best genome on held-out opponents...
  🧪 Validation vs rex (20 fights)...
  ✅ rex: 17/20 wins (85.0%)
  🧪 Validation vs hachess (20 fights)...
  ✅ hachess: 16/20 wins (80.0%)
  📊 Validation fitness: 0.825 (33/40 wins)

📊 Generation 1 Summary:
  Training Best:    0.850
  Training Average: 0.687
  Training Worst:   0.425
  Validation Best:  0.825
  Overfitting Gap:  2.5% ✅
```

---

## Fixed Random Map? ❌ NO

**Question:** Should we use a fixed seed for consistent maps?

**Answer:** **NO** - This would cause severe map-specific overfitting.

**Why:**
- LeekWars maps are randomly generated (obstacles, spawn positions, terrain)
- Training on one map → AI learns that specific layout
- Tournament uses different maps → AI fails catastrophically

**Example Failure:**
- Fixed map: Open terrain (no walls)
- GA learns: Aggressive rushing wins
- Tournament map: Tight corridors
- Result: AI rushes into choke points → death

**Correct Approach:**
- Random maps every fight (current behavior)
- GA learns general tactics that work across layouts
- Slightly higher variance, but robust performance

---

## Usage

### Quick Test (9 hours)
```bash
python3 tools/genetic_optimizer.py \
  --generations 10 \
  --population 15 \
  --fights-per-genome 20 \
  --opponents domingo betalpha rex hachess
```

### Full Training (18 hours)
```bash
python3 tools/genetic_optimizer.py \
  --generations 15 \
  --population 20 \
  --fights-per-genome 40 \
  --opponents domingo betalpha rex hachess
```

### Resume From Checkpoint
```bash
python3 tools/genetic_optimizer.py \
  --resume ga_checkpoint_gen10.json \
  --generations 5  # Run 5 more generations
```

---

## Expected Results

With V2 improvements, we should see:

✅ **No catastrophic collapses** (parameter bounds prevent AGI disaster)
✅ **Overfitting detection** (train-val gap monitored)
✅ **Generalizable improvements** (4 diverse opponents)
✅ **Realistic expectations** (larger sample sizes = accurate fitness)

**Conservative Estimate:**
- Training: 75-85% win rate (on train set)
- Validation: 70-80% win rate (on val set)
- Real performance: 72-82% win rate (similar to validation)

**Target:**
- Beat baseline 80% by +5-10pp → 85-90% final win rate
- Validation gap < 10% (no overfitting)
- Consistent performance across all 4 bot types

---

**Document Version:** 2.0
**Last Updated:** December 17, 2025
**Status:** Ready for testing
