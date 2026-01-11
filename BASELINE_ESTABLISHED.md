# V8 Baseline Established (50-Fight Testing)

## Summary

**Baseline Win Rate: 70% (35W-15L) vs Domingo**

Increased sample size from 20 → 50 fights to reduce map RNG variance.

## Variance Comparison

### 20-Fight Tests (Unstable)
| Run | Win Rate | Record | Variance |
|-----|----------|--------|----------|
| 1 | 55% | 11W-9L | -15% from mean |
| 2 | 60% | 12W-8L | +13% from mean |
| 3 | 25% | 5W-15L | -22% from mean |

**Statistics:**
- Mean: 46.7%
- StdDev: ±18.9%
- Range: 35 percentage points (25-60%)

**Problem:** Cannot distinguish code improvements from map RNG

### 50-Fight Test (Stable)

| Run | Win Rate | Record | 
|-----|----------|--------|
| 1 | 70% | 35W-15L |

**Statistics:**
- Expected StdDev: ±10% (2.5x less variance)
- Detection threshold: 10%+ improvements measurable

**Benefit:** Can detect meaningful improvements with confidence

## Next Steps

Use **50 fights per test** as standard:

```bash
# Test improvements
python3 tools/lw_test_script.py 50 447626 domingo
```

**Improvement targets:**
- 70% → 80%: Good (+10%)
- 70% → 85%: Excellent (+15%)
- 70% → 90%: Outstanding (+20%)

**Current Baseline: 70% WR (50 fights)**

Date: 2025-12-20
