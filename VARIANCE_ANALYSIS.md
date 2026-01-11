# LeekWars V8 Variance Analysis

## Problem Statement
Identical code (baseline) shows 25-60% win rate variance across test runs:
- Run 1: 55% WR (11W-9L)
- Run 2: 60% WR (12W-8L)  
- Run 3: 25% WR (5W-15L)

**35 percentage point variance makes it impossible to measure improvement.**

## Root Cause: Random Map Generation

### Evidence
1. **Test script creates NEW scenario each run**
   - File: `tools/lw_test_script.py`, line 437
   - Code: `"map": None,  # Random map`
   
2. **Each scenario has different fight IDs**
   - 55% run: fights 50660350-50660385
   - 60% run: fights 50661564-50661619
   - 25% run: fights 50661832-50661936

3. **Different scenario IDs per run**
   - 55% run: scenario 37650
   - 60% run: scenario 37652
   - 25% run: scenario 37654

### Why Maps Matter
- **Spawn positions**: Close spawns favor aggro, far spawns favor kiting
- **Obstacles**: Affect line-of-sight, movement, positioning strategies
- **Map size**: Impacts weapon range effectiveness, hide-and-seek viability

## Solutions

### Option 1: Use Fixed Map (Recommended)
**Modify test script to specify map ID instead of random**
```python
# Current (line 437)
"map": None,  # Random map

# Fixed
"map": 12345,  # Specific map ID (need to identify good test maps)
```

**Pros:**
- Consistent results across runs
- Can identify code improvements with confidence
- Faster testing (20 fights sufficient)

**Cons:**
- Need to find/identify map IDs
- May not generalize to all map types

### Option 2: Large Sample Size
**Run 100+ fights per test instead of 20**

**Pros:**
- Averages out map RNG
- Tests robustness across map variations

**Cons:**
- 5x slower testing (100 vs 20 fights)
- Still some variance remaining

### Option 3: Reuse Existing Scenario
**Modify script to lookup/reuse scenario instead of creating new**

**Pros:**
- Same map for all tests
- No API changes needed

**Cons:**
- Manual scenario creation required
- Scenario cleanup needed between runs

## Recommended Action Plan

1. **Short-term: Increase sample size to 50 fights**
   - Reduces variance from 35% to ~15%
   - Only 2.5x slower than current

2. **Long-term: Implement fixed map testing**
   - Research LeekWars map IDs
   - Modify test script to support `--map <id>` parameter
   - Select 2-3 representative maps for testing

3. **Metrics: Track multiple dimensions**
   - Win rate (primary)
   - Average HP remaining (survivability)
   - Average damage dealt/taken ratio (efficiency)
   - Average fight duration (aggression)

## Current Status
- ✅ Root cause identified: Random maps
- ⏳ Solution selection needed
- ⏳ Test script modification required
