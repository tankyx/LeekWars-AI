# Multi-Leek Genetic Algorithm Guide

## Overview
Train the GA with multiple leek stat profiles to evolve weights that generalize across different builds.

## The Stat Generalization Problem

### Why Single-Leek Training Fails
```
Your main leek: 600 STR, 300 WIS, 200 AGI, 2500 HP
GA evolves: kill_mult_70 = 4.707, otko_bonus = 5000

Test with weak leek (400 STR, 1800 HP):
❌ Overcommits to OTKO attempts (not enough damage)
❌ Result: 60% win rate (vs 80% baseline)

Test with strong leek (800 STR, 3200 HP):
❌ Plays too conservatively (underestimates burst)
❌ Result: 70% win rate (missed kill opportunities)
```

### Multi-Leek Solution
Train on 3 different stat profiles → GA finds weights that work for ALL of them.

---

## Setup: Create Test Leeks

You need 3 leeks with different stat distributions:

### Option A: Use Existing Leeks
```bash
# If you already have multiple leeks
python3 tools/genetic_optimizer.py \
  --test-leeks "MyMainLeek" "MyWeakLeek" "MyStrongLeek" \
  --generations 10 \
  --population 15 \
  --fights-per-genome 60  # 20 per leek × 3 leeks
```

### Option B: Create New Test Leeks (Recommended)

**1. Weak Build (Early Game)**
- Level: ~50
- Stats: 400 STR, 200 WIS, 100 AGI
- HP: ~1800
- TP: 8-9
- Name: "GA_Weak"

**2. Balanced Build (Mid Game)**
- Level: ~100
- Stats: 600 STR, 300 WIS, 200 AGI
- HP: ~2500
- TP: 10-11
- Name: "GA_Balanced"

**3. Strong Build (Late Game)**
- Level: ~150+
- Stats: 800 STR, 400 WIS, 300 AGI
- HP: ~3200
- TP: 12-13
- Name: "GA_Strong"

---

## Training Cost

### Single Leek (Current)
```
15 pop × 60 fights × 10 gen = 9,000 fights (~12 hours)
```

### Multi-Leek (3 leeks)
```
15 pop × (20 fights × 3 leeks) × 10 gen = 9,000 fights (~12 hours)
                                          SAME TOTAL TIME! ✅
```

**Key Insight:** Total fight count stays constant - you just split fights across leeks instead of repeating fights with one leek.

---

## How It Works

### Evaluation Flow
```
Genome #1:
  🦗 Testing with leek: GA_Weak
    🎯 vs domingo (7 fights) → 5/7 wins (71%)
    🎯 vs betalpha (7 fights) → 4/7 wins (57%)
    📊 GA_Weak fitness: 0.643 (9/14 wins)

  🦗 Testing with leek: GA_Balanced
    🎯 vs domingo (7 fights) → 6/7 wins (86%)
    🎯 vs betalpha (7 fights) → 6/7 wins (86%)
    📊 GA_Balanced fitness: 0.857 (12/14 wins)

  🦗 Testing with leek: GA_Strong
    🎯 vs domingo (7 fights) → 7/7 wins (100%)
    🎯 vs betalpha (7 fights) → 6/7 wins (86%)
    📊 GA_Strong fitness: 0.929 (13/14 wins)

📊 Genome #1 AVERAGE fitness: 0.810 (across 3 leeks)
```

### Selection Pressure
- GA favors genomes that work well across ALL stat profiles
- Prevents overfitting to one build type
- Weights naturally become stat-agnostic

---

## Expected Results

### Without Multi-Leek (V1 Results)
| Leek Type | Win Rate | Issue |
|-----------|----------|-------|
| Training leek | 80% | ✅ Optimized for this |
| Weak leek | 60% | ❌ Too aggressive |
| Strong leek | 70% | ❌ Too conservative |

### With Multi-Leek (Expected V2)
| Leek Type | Win Rate | Status |
|-----------|----------|--------|
| Weak leek | 70-75% | ✅ Conservative play |
| Balanced leek | 80-85% | ✅ Optimal play |
| Strong leek | 85-90% | ✅ Aggressive play |

**Consistency:** All leeks within 10-15pp of each other (generalized weights).

---

## Usage Examples

### Quick Test (3 leeks, 9 hours)
```bash
python3 tools/genetic_optimizer.py \
  --generations 10 \
  --population 15 \
  --fights-per-genome 60 \
  --test-leeks GA_Weak GA_Balanced GA_Strong \
  --opponents domingo betalpha rex hachess
```

### Production Run (3 leeks, 18 hours)
```bash
python3 tools/genetic_optimizer.py \
  --generations 15 \
  --population 20 \
  --fights-per-genome 120 \
  --test-leeks GA_Weak GA_Balanced GA_Strong \
  --opponents domingo betalpha rex hachess
```

### Single Leek (Control - for comparison)
```bash
python3 tools/genetic_optimizer.py \
  --generations 10 \
  --population 15 \
  --fights-per-genome 60 \
  --opponents domingo betalpha rex hachess
# No --test-leeks = uses account's first leek
```

---

## Validation Protocol

After training with multi-leek:

### 1. Test Best Genome on All Profiles
```bash
# Apply best genome
python3 tools/apply_best_genome.py ga_checkpoint_gen10.json

# Test weak leek
python3 tools/lw_test_script.py 50 447626 domingo --leek GA_Weak

# Test balanced leek
python3 tools/lw_test_script.py 50 447626 domingo --leek GA_Balanced

# Test strong leek
python3 tools/lw_test_script.py 50 447626 domingo --leek GA_Strong
```

### 2. Check Generalization Gap
```python
# Good generalization: <10% gap between leeks
weak_wr = 0.72
balanced_wr = 0.82
strong_wr = 0.88

max_gap = max(strong_wr - weak_wr) = 0.16 = 16%
# If gap > 20%, weights still overfitting to strong leeks
```

---

## Comparison: Multi-Leek vs Stat Normalization

| Approach | Pros | Cons | Best For |
|----------|------|------|----------|
| **Multi-Leek** | No code changes, GA handles generalization | Requires 3 leeks, same training time | Quick testing |
| **Stat Normalization** | Cleaner solution, works with 1 leek | Requires code changes, more complex | Production use |
| **Both** | Best generalization, robust across all cases | Most work | Ultimate solution |

---

## Recommended Strategy

### Phase 1: Multi-Leek GA (Now)
1. Create 3 test leeks (weak/balanced/strong)
2. Run multi-leek GA for 10 generations
3. Validate on all 3 profiles
4. Target: All leeks 70-85% win rate

### Phase 2: Stat Normalization (Later)
1. Implement normalization layer in scenario_scorer.lk
2. Re-run single-leek GA with normalized weights
3. Compare to multi-leek approach
4. Use whichever performs better

### Phase 3: Hybrid (Ultimate)
1. Combine both approaches
2. Normalized weights + multi-profile training
3. Should achieve 80-90% across ALL stat ranges

---

## Troubleshooting

### "Leek not found" Error
```bash
# Make sure leek names match exactly (case-sensitive)
python3 tools/lw_test_script.py 10 447626 domingo --leek "MyLeekName"
# If error, check available leeks in LeekWars account
```

### Unbalanced Performance (One leek dominates)
```
If:
- Weak leek: 50% WR
- Balanced leek: 80% WR
- Strong leek: 95% WR

Problem: GA optimizing for strong leek, ignoring weak

Solution:
- Reduce fights_per_genome (force more equal weight)
- Or use weighted fitness: weak_wr * 1.5 + balanced_wr + strong_wr * 0.8
```

### Training Too Long
```bash
# Reduce to 2 leeks instead of 3
--test-leeks GA_Balanced GA_Strong

# Or reduce fights
--fights-per-genome 40  # 20 per leek × 2 leeks
```

---

**Document Version:** 1.0
**Last Updated:** December 17, 2025
**Status:** Ready for testing
