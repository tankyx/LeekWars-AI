# Value Model Project — Final Report (2026-08-18)

## Outcome: HONEST NEGATIVE (goal terminated per its own gate)

The learned value model is real, accurate, and correctly deployed — and it
cannot beat the hand-tuned V9 scorer in-engine. Three integration seats were
built and A/B-tested; all three failed on the decisive matchup pool. The
project is terminated without shipping, per the goal's evidence standard.

## What was built (all kept, all useful independently)

| Component | Path | Status |
|---|---|---|
| Fight harvester | `tools/fight_harvester.py` | 18,633 fights cached in `data/fight_cache/` |
| State extractor | `tools/extract_states.py` | 159,902 labeled turn-states → `data/dataset_v1.jsonl` |
| Value model v1 | `tools/train_value_model.py` | MLP 40→16→8→1, **test AUC 0.766** (baseline hp-diff 0.659), calibrated |
| LeekScript emitter | `tools/emit_value_model_lk.py` | string-literal weights, fixed-point only |
| LeekScript MLP | `V9_modules/value_model_data.lk` | **bit-exact parity** with sklearn (5/5 vectors) |
| Feature assembler | `V9_modules/value_model.lk` | mirrors extractor; flags `_v9ValueModelEnabled=false` |
| Learned re-rank | `V9_modules/rollout_rerank.lk` | `rolloutRerankLearned`, flag `_v9RerankLearnedEnabled=false` |
| Calibrated prod pool | `tools/build_prod_pool.py`, `calibrate_prod_pool.py` | 8/24 honestly-reproducible hard matchups |
| Harnesses | `ab_valuemodel_*.py`, `ab_rerank_learned*.py`, `ab_prod_pool.py` | reusable |

All flags are OFF. Production AI is unaffected.

## Timeline of evidence

1. **W1**: 18,633 fights harvested; extractor validated (HP trajectories, effect
   tracking, hex distance from generator source). Two data bugs fixed
   (hp-dead-state `or 1`, relu order in my own parity reference).
2. **W2**: AUC 0.695 → 0.727 → 0.754 → **0.766** as data grew (650 → 14k fights);
   every turn bucket beats the hp-diff baseline (early game 0.69 vs 0.52).
   Calibration audit found and fixed the tank-subset weakness (0.717 → 0.767
   via archetype-flag features). **Offline gate: PASS.**
3. **W3 seat 1 — additive scorer bonus** (`score += (p−0.5)·scale`):
   identical outcomes at scales 500/2000/8000. Disproven — fixed
   high-magnitude terms (otkoBonus ~5-6k) freeze the scenario argmax.
4. **W3 seat 2 — multiplicative** (`score *= 0.5+p`): moves picks (KG −2, MH +2),
   nets exactly zero (90/30 both ways).
5. **W3 seat 3 — learned re-rank** (model replaces the hand-built enemyTerm):
   neutral on the bot matrix (89/31 vs 90/30); **NEGATIVE on the calibrated
   pool: 26W/54L vs 32W/47L (−6)**, driven by ED vs tank_sci (3/7 vs 7/3).
   Re-tested after the tank-calibration fix (AUC 0.766): **identical −6.**

## Why it failed (the consistent diagnosis of the whole week)

The losses that matter are **structural, not decisional**. The same wall hit
every independent attempt: ED GA weights (production-neutral), counter
multipliers (fire but flip nothing), lethal solver (neutral), and now three
model-integration seats. On the matchups that decide our talent (sustain
bruisers/tanks, ~50-80% of losses), every candidate's P(win) is low and
close — the model's ranking of nearly-equal losing states is noise, and its
aggressive-tilted flips are systematically the losing line vs sustain.

A better model (AUC 0.75→0.77) did not change any of these outcomes. The
constraint is the decision structure and the matchups themselves, not
estimator fidelity.

## What DID pay this week (for contrast)

- Model-driven opponent **selection**: +11pts aggregate in the interleaved
  production A/B (shipped to all grind crons).
- Mortal-poison cleanse path (shipped).
- The measurement infrastructure itself (fast runners, calibrated pool,
  A/B harnesses, 18.6k-fight dataset).

## Files changed but NOT shipped (flagged off)

- `V9_modules/scenario_scorer.lk` — the multiplicative line sits behind
  `_v9ValueModelEnabled=false`.
- `V9_modules/rollout_rerank.lk` — `rolloutRerankLearned` behind
  `_v9RerankLearnedEnabled=false`.
- `V9_modules/value_model.lk`, `value_model_data.lk` — inert while flags off.

To re-enable any of this for a future retry: flip the flag and re-run the
matching harness before any upload.
