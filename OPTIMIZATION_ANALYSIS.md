# V8 Path Cache Optimization Analysis

## Executive Summary

**Optimization Attempted:** Persistent path length cache across turns  
**Result:** **FAILED** - Caused 10% win rate vs 28-70% baseline  
**Root Cause:** Cached paths become stale when obstacles (entities) move/die  
**Status:** Reverted to baseline (cache cleared every turn)

---

## Technical Analysis

### The Optimization

**Goal:** Reduce operation cost by caching `getPathLength()` results across turns

**Implementation:**
```leekscript
global __pathLengthCache = [:]

function getCachedPathLength(fromCell, toCell) {
    var hash = hashTwoCells(fromCell, toCell)
    if (mapContainsKey(__pathLengthCache, hash)) {
        return __pathLengthCache[hash]  // Return cached value
    }
    var pathLen = getPathLength(fromCell, toCell)
    __pathLengthCache[hash] = pathLen
    return pathLen
}

// Original: clearCaches() cleared __pathLengthCache = [:]
// Optimized: clearCaches() KEPT __pathLengthCache (persistent)
```

**Expected Benefit:**
- Turn 1: 500K-1M ops (build cache)
- Turns 2-10: 50-100K ops (90%+ cache hits)
- Total savings: 3-5M ops per fight

---

## Root Cause: Stale Path Data

### How getPathLength() Works

`getPathLength(fromCell, toCell)` returns:
- **Positive integer:** Path length if route is clear
- **null:** Path is blocked by obstacles (walls, entities)

### The Fatal Flaw

**Scenario:**

**Turn 1:**
```
Player at cell 100, Enemy at cell 200
getPathLength(100, 300) = null  // Blocked by enemy at 200
Cache stores: hash(100,300) = null
```

**Turn 5:**
```
Enemy moved to cell 500 (path now clear!)
getCachedPathLength(100, 300) = null  // STALE! Returns cached value
AI thinks: "Cell 300 unreachable" ✗
Reality: Path is now clear! ✓
```

### Impact on AI Behavior

**Code checks cached paths:**
```leekscript
// base_strategy.lk:154
if (pathLen == null || pathLen > playerMP) continue  // Skip cell

// base_strategy.lk:577  
if (pathLen == null || pathLen > maxMP) continue  // Skip unreachable
```

**With stale cache:**
- ✗ AI skips cells that ARE reachable (thinks they're still blocked)
- ✗ Damage map excludes good tactical positions
- ✗ Movement options artificially limited
- ✗ Suboptimal positioning throughout fight

**Result:** AI performs poorly due to incorrect environmental understanding

---

## Test Results

| Configuration | Tests | Win Rate | Status |
|--------------|-------|----------|--------|
| **Baseline (Dec 20)** | 11 × 50 | **28-70%** | ✅ Working |
| **Persistent Cache (Dec 21)** | 1 × 50 | **10%** | ❌ Broken |
| **Reverted (Dec 21)** | Pending | TBD | Testing |

**Performance degradation:** -72% relative win rate (10% vs 36% baseline average)

---

## Why This Happened

### Incorrect Assumption

**Assumed:** Path lengths between two cells are constant throughout a fight  
**Reality:** Paths change when entities (obstacles) move or die

### LeekWars Map Dynamics

**Static (safe to cache):**
- Map dimensions
- Wall positions
- Cell coordinates

**Dynamic (NOT safe to cache):**
- Entity positions (players, enemies)
- Entity existence (deaths remove obstacles)
- Paths blocked by entities

### The Optimization Was Too Aggressive

Caching geometric data (cell distances) = ✅ Safe  
Caching pathfinding results (with dynamic obstacles) = ❌ Unsafe

---

## Solutions Evaluated

### Option A: Clear Cache Every Turn ✅ CHOSEN

**Implementation:**
```leekscript
function clearCaches() {
    __pathLengthCache = [:]  // Clear every turn
}
```

**Pros:**
- Safe - no stale data possible
- Simple - one line
- Returns to baseline performance

**Cons:**
- No performance gain
- Wastes the optimization work

**Status:** Implemented

---

### Option B: Cache Only Non-Null Paths ❌ REJECTED

**Implementation:**
```leekscript
function getCachedPathLength(fromCell, toCell) {
    var pathLen = getPathLength(fromCell, toCell)
    if (pathLen != null) {
        __pathLengthCache[hash] = pathLen
    }
    return pathLen
}
```

**Problem:** A path that was clear (cached) might become blocked later  
**Example:**
- Turn 1: Path clear, cache: hash(A,B) = 5
- Turn 5: Enemy blocks path, should return null
- Returns: 5 (from cache) - STILL STALE!

**Status:** Does not solve the problem

---

### Option C: Turn-Aware Cache ❌ TOO COMPLEX

**Implementation:**
```leekscript
global __pathLengthCache = [:]
global __cacheCreatedTurn = [:]

function getCachedPathLength(fromCell, toCell) {
    var hash = hashTwoCells(fromCell, toCell)
    var currentTurn = getTurn()
    
    if (mapContainsKey(__cacheCreatedTurn, hash)) {
        if (__cacheCreatedTurn[hash] == currentTurn) {
            return __pathLengthCache[hash]
        }
    }
    
    var pathLen = getPathLength(fromCell, toCell)
    __pathLengthCache[hash] = pathLen
    __cacheCreatedTurn[hash] = currentTurn
    return pathLen
}
```

**Pros:** Technically correct - cache only valid for current turn

**Cons:**
- More complex code
- More memory usage (two maps)
- Equivalent to clearing cache every turn
- No performance benefit

**Status:** Rejected - unnecessary complexity

---

### Option D: Entity-Aware Cache Invalidation ❌ TOO EXPENSIVE

**Idea:** Track entity positions, invalidate cached paths when entities move

**Problems:**
- Need to track all entity positions every turn
- Need to identify which cached paths are affected
- Overhead likely exceeds benefit
- Complex implementation, high bug risk

**Status:** Not worth the complexity

---

## Lessons Learned

### 1. **Caching Requires Deep Understanding**

Must understand:
- What changes between cache reads?
- Are cached values time-dependent?
- What invalidates cached data?

### 2. **Dynamic Environments Are Tricky**

LeekWars combat is HIGHLY dynamic:
- Entities move every turn
- Entities die mid-fight
- Paths change constantly

Static caching assumptions fail in dynamic environments.

### 3. **Test With Representative Scenarios**

10-fight tests showed 10% win rate, but we didn't investigate immediately.  
Should have:
- Compared single fight behavior (before vs after)
- Checked debug logs for movement failures
- Validated cache correctness with assertions

### 4. **Premature Optimization**

Current V8 performance: 370K ops/turn (6% of 6M budget)  
Optimization target: Path caching (save ~500K ops)  

**Was this necessary?**
- NO - AI only uses 6% of available operations
- 94% headroom available for future features
- No performance bottleneck exists

**Better priorities:**
- Improve strategy logic
- Enhance combo detection
- Better scenario scoring

---

## Recommendation

**DO NOT pursue persistent path caching.**

**Instead, focus on:**
1. **Scenario quality** - Better decision-making > faster bad decisions
2. **Strategic improvements** - Combat logic has more impact than ops saved
3. **Win rate optimization** - 28-70% variance from map RNG is the real problem

**If performance becomes critical:**
- Profile actual bottlenecks first
- Consider algorithmic improvements (fewer path calculations needed)
- Optimize high-frequency, non-dynamic calculations only

---

## Status

- ✅ Root cause identified
- ✅ Reverted to baseline
- ⏳ Awaiting test results to confirm reversion success
- ✅ Documented for future reference

**Last Updated:** December 21, 2025
