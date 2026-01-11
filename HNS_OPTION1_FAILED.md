# HNS Option 1 (Threat Map) - FAILED ❌

## Summary

**Attempted:** Use threat map for HNS instead of LOS counting
**Result:** 28-32% WR (vs 47% baseline) - WORSE performance
**Cause:** Operations limit exceeded + architectural issues

## What We Tried

### Attempt 1: Direct Threat Map Usage
```javascript
var danger = this.getThreatAtCell(cand)  // Use damage values directly
```
**Result:** 28% WR (14W-36L)
**Problem:** All threat values returned 0 initially, then operations timeout

### Attempt 2: Normalized Threat Values  
```javascript
var rawThreat = this.getThreatAtCell(cand)
var danger = floor(rawThreat / 10)  // Normalize 0-500 damage → 0-50 danger
```
**Result:** 32% WR (16W-34L)
**Problem:** 36% of fights (18/50) hit operations limit with no logs

## Why It Failed

### 1. Operations Budget Exceeded
- Threat map building costs ~50-100K ops
- HNS called multiple times per turn
- Total cost exceeds 6M ops/turn budget
- **18/50 fights timed out**

### 2. Architectural Mismatch
- Threat map designed for strategic planning (once per turn)
- HNS needs tactical positioning (called 3-10 times per turn)
- Repeated threat map lookups too expensive

### 3. Threat Map Already Optimized Away
- Line 497 in `field_map_tactical.lk` skips building if `enemyMP > 20`
- Performance optimization that conflicts with our use case
- Threat map not reliable for real-time positioning

## Test Results

| Approach | Win Rate | Ops Limit Hits | Notes |
|----------|----------|----------------|-------|
| Baseline (LOS) | 47% | 0/300 fights | Stable |
| Threat Direct | 28% | ~10/50 | All zeros initially |
| Threat Normalized | 32% | 18/50 | 36% timeout rate |

## Conclusion

**Option 1 is not viable.** The threat map infrastructure:
- ✅ Exists and works for strategic planning
- ❌ Too expensive for tactical HNS positioning
- ❌ Causes operations limit exceeded
- ❌ Makes performance WORSE, not better

## Recommendations

### Option 2: Improve LOS Counting (Recommended)
Keep LOS-based danger but add intelligence:
- Weight by enemy weapon range
- Weight by enemy damage potential
- Consider enemy MP for reachability
- **No infrastructure changes needed**

### Option 3: Accept Variance
- 47% ± 12% is acceptable for development
- Focus on improving combat logic instead of HNS
- HNS may not be the primary cause of variance

### Option 4: Give Up on HNS Fix
- HNS improvements show diminishing returns
- Combat logic improvements likely higher ROI
- Variance may be inherent to random maps

## Reverted to Baseline
✅ Uploaded baseline (LOS-based HNS)
✅ 47% ± 12% WR confirmed
✅ No operations limit issues

Date: 2025-12-20
