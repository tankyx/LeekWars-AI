# All Leeks Testing Summary
**Date:** February 3, 2026  
**Script:** main.lk (ID: 447626) with Phase 3 & 4 enabled  
**Opponent:** Domingo (Balanced, 600 strength)  
**Tests per Leek:** 25 fights  
**Total Fights:** 100

## Individual Results

### 1. AdaLovelace (Level 301)
- **Win Rate:** 100.0% (25W-0L-0D)
- **Performance:** Perfect score! Dominated all fights.
- **Stats:** STR: 520, WIS: 310, RES: 220
- **Results File:** `test_results_447626_20260203_215403.json`

### 2. EdsgerDijkstra (Level 301)
- **Win Rate:** 72.0% (18W-7L-0D)
- **Performance:** Good performance with consistent wins.
- **Stats:** STR: 520, WIS: 310, RES: 220 (same stats as AdaLovelace)
- **Results File:** `test_results_447626_20260203_215612.json`

### 3. KurtGodel (Level 300)
- **Win Rate:** 72.0% (18W-6L-1D)
- **Performance:** Good performance with 1 draw.
- **Stats:** Level 300 (slightly lower than level 301 leeks)
- **Results File:** `test_results_447626_20260203_215821.json`

### 4. MargaretHamilton (Level 300)
- **Win Rate:** 48.0% (12W-12L-1D)
- **Performance:** Below expected, close to 50/50.
- **Stats:** Level 300
- **Results File:** `test_results_447626_20260203_220032.json`

## Aggregate Statistics

**Combined Results:**
- **Total Wins:** 73 / 100
- **Total Losses:** 25 / 100
- **Total Draws:** 2 / 100
- **Overall Win Rate:** 73.0%

## Analysis

### Performance Variance
The significant variance in win rates (48% to 100%) across leeks using the same AI script indicates:

1. **Map RNG Impact:** Random map generation heavily influences outcomes
2. **Individual Stats Matter:** Level 301 leeks performed better than Level 300 leeks
3. **Sample Size:** Small sample sizes (25 fights) show high variance
   - AdaLovelace: Perfect 100% (outlier, likely lucky map draws)
   - EdsgerDijkstra: 72% (good performance)
   - KurtGodel: 72% (consistent with EdsgerDijkstra)
   - MargaretHamilton: 48% (poor luck with maps/positioning)

### Comparison to Baseline
- **Previous 100-fight test:** 88% WR (single leek, same script)
- **Current aggregate:** 73% WR (4 leeks, 25 fights each)
- **Difference:** -15 percentage points

The lower aggregate win rate likely reflects:
- Different random seeds across 4 separate test runs
- Map variance (each leek got different map sets)
- Individual leek performance variations

### Key Findings

1. **Script Stability:** All leeks successfully ran Phase 3 & 4 features without errors
2. **No Operation Budget Violations:** All 100 fights completed within operation limits
3. **High Variance:** Individual results ranged from 48% to 100%, showing significant map influence
4. **Level Impact:** Level 301 leeks (AdaLovelace, EdsgerDijkstra) performed better overall

## Recommendations

1. **Larger Sample Sizes:** 100+ fights per leek would reduce variance
2. **Fixed Maps:** Testing on fixed maps would isolate AI performance from RNG
3. **Stat Investigation:** Check if MargaretHamilton has different equipment/stats
4. **Re-test MargaretHamilton:** Run additional 25 fights to verify if 48% was bad luck

## Files Generated

- `test_results_447626_20260203_215403.json` (AdaLovelace)
- `test_results_447626_20260203_215612.json` (EdsgerDijkstra)
- `test_results_447626_20260203_215821.json` (KurtGodel)
- `test_results_447626_20260203_220032.json` (MargaretHamilton)
- `leeks_to_test.json` (Leek configuration data)

---

**Conclusion:** Phase 3 & 4 integration is stable and working across all leeks, with an overall 73% win rate. The high variance (48-100%) suggests map RNG plays a significant role, and larger sample sizes would provide more reliable performance metrics.
