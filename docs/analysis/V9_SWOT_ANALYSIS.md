# V9 — SWOT Analysis (Strategy & Code Quality)

**Date:** 2026-09-21
**Scope:** `V9_modules/` (47 LeekScript modules, ≈35.7K lines), `V9_baseline/` snapshot, `docs/v9_scope.md`, `docs/matchup_doctrine.md`, `docs/fennel_boss.md`, `docs/analysis/value_model_final_report.md`, git history through `b65af7e`, plus uncommitted worktree changes.
**Method:** Read-only inspection (file reads, greps, git log/diff). No files modified during analysis.
**Caveat:** Live server state (leek assignments, current results) was not verified; all performance numbers are cited from the repository's own commits, docs, and harnesses, not independently reproduced.

---

## 1. What V9 Actually Is (verified snapshot)

**Shape.** `V9_modules/` is a working copy of the V8 pipeline that has evolved independently — 47 LeekScript modules, **≈35.7K lines**, plus ~3K lines of dev copies (`enemy_model_data_iso.lk`, `enemy_model_data.lk.test.lk`, two `.bisecttest` files). It is deployed side-by-side as `9.0/V9/` via `tools/upload_v9.py`; V8 stays at `8.0/V8/` (rollback = reassign a leek). Per `docs/fennel_boss.md` (Sept 9), Cure's four leeks run V9.

**Architecture.** The V8 core is intact: generate (combos + beam) → quick-score prune → mutate → simulate → 23-dim score → 2-ply → alt-target → execute → TP recovery. V9 adds a decision layer on top:

- `enemy_sim.lk` + `enemy_model.lk` + per-opponent memory (`enemy_model_data.lk`, ~397 opponents: archetype, engagement distance, T1–T3 modal actions) — a kite/range/LoS-aware enemy response estimate.
- `eval.lk` — a *single* 16-weight outcome evaluator (GA-managed via `ga_weights.lk`), isolated by design.
- `rollout_veto.lk` — catastrophe veto (predicted death / race-bleed / mostly-dropped plans) with fully simulated defensive alternatives.
- `rollout_rerank.lk` — every-turn re-rank of the retained top-5, in two variants: hand-built (disabled) and **learned** (`_v9RerankLearnedEnabled = true`, flip threshold P(win) delta 0.005).
- `value_model.lk` + generated `value_model_data.lk` — an embedded MLP (32 raw + derived features → 16 → 8 → sigmoid), bit-exact against sklearn, test AUC 0.766 vs 0.659 hp-diff baseline.
- `lethal_solver.lk` — lethal/mortal checks (lethal forcing disabled; mortal-poison cleanse enabled).
- `boss_context.lk` — 6,962 lines of Fennel King doctrine.

**Headline evidence.** Commit `4e78ea5` (Sept 21): learned re-rank enabled — mirror A/B, pre-committed n=220, both sides seeded/alternating: MargaretHamilton 134-85 (61.2%, p=0.001), EdsgerDijkstra 120-89 (57.4%, p=0.038), ops *down* 10.21M → 9.87M, regression 58/60. The same campaign measured beam width 20→28 as **neutral** (113-107, 51.4%, p=0.736) and reverted it.

---

## 2. SWOT — Strategy

### Strengths

- **Simulation-first decisions with a real measurement loop.** The repo built the missing instrument before trusting claims: `mirror_ab.py` (same-leek head-to-head, paired binomial, calibration 20-20 p=1.000), `matchup_stability.py` (determinism + variance checks before a matchup becomes a testbed), `matchup_ab.py` (paired McNemar), and a GA pipeline with independent-matrix validation and guard opponents.
- **A rare, correctly-measured strategic finding:** more *search* does nothing (beam-width null, reverted honestly even after an n=60 temptation at 56.7%); better *evaluation* of the same candidates is worth +7–11pp. That is a genuine, falsifiable result, not a narrative.
- **Opponent modeling is data-backed, not hand-waved.** Enemy response sim uses their real weapons/stats, predicted kite distance from memory, LoS, and poison from their actual chips. The rebuild comment records *why*: the old always-full-TP estimator was a systematic overestimate that broke ED's reflect bait (documented −24 in A/B).
- **Safety by construction.** Status-quo thresholds on every override (400 score / 0.005 P(win) / alt-target 15%), catastrophe veto as a backstop, ops watchdog gates (`_ops50`…`_ops96`) everywhere, degrade-by-cores, and the 13M hard fallback to simple move+attack.
- **Doctrine discipline with recorded negatives.** `docs/matchup_doctrine.md` states the rule — "negative results are what stop the same idea being re-tried" — and follows it: three independent chip routes to the board (weight cut 415→10 flipped **0 of 120** fights), poison ignores shields/reflect, antidote pinned at cooldown, "no surplus TP to harvest".
- **Cultural falsification both directions.** `value_model_final_report.md` is an explicit honest-negative (all three integration seats failed, project terminated); the later re-enablement came only with a stronger harness and a named mechanism (threshold sat above the model's typical gap). Conclusions in comments carry fight IDs as receipts.

### Weaknesses

- **The boss campaign is a measured dead end at current resources.** ~245 fights, 0 wins; puzzle clears ~30% (lure + reserve), graal deaths ~29%, and **phase 2 never converted** — the attrition math (army ~1600–2000/turn focus fire; winners hold 4 resurrection chips vs our 2, TP 27–29 vs 19–22) is structural. Campaign formally stopped by the user (Sept 9).
- **Team fights are heuristic, not simulated.** `simulateEnemyResponseMulti` taxes non-target enemies at 70% and bulbs at 40% weapon pressure — no multi-agent rollout. M4's depth-2/multi-enemy stretch is undelivered.
- **The live win is one constant away from invisibility.** The learned re-rank was shipped disabled *and* mis-thresholded for weeks: it ran every turn, disagreed on 3 of 4 turns (gaps 0.003/0.005/0.018), and was overruled every time. The veto was likewise dead code in production for weeks (a 50% ops gate; "GA v2 proof: zero V9_VETO in any fight log").
- **Two rival mechanisms for one job.** Hand re-rank (disabled, untestable in the main harness: ENEMY_MODEL blind spot, and its old verdict is suspect — the `simulateEnemyResponseMulti` crash was live in both call sites) sits beside the learned re-rank with overlapping purpose. Strategic ambiguity about which is the path.
- **Proposal ceiling.** Re-rank can only reorder what the pipeline proposes; V9's own candidate generator (`generators.lk`) is unwired, so "ceiling breakers" are exactly two hand-built defensive shapes.
- **Verification asymmetry:** the fleet-wide enablement rests on mirror A/B alone — the calibrated prod pool (which said −6) was never re-run at threshold 0.005. Two harnesses disagreeing is an open question, not a settled win.

### Opportunities

- **The learned model has unused seats.** It already beats hp-diff offline; options: replace the hand enemy-term entirely, feed it per-opponent features, or use it to rank *generated* candidates, not just reorder pipeline ones.
- **Widen the breaker set.** "V9 plays turns V8 never proposed" is explicitly the lever; today it is 2 shapes. Generator + rollout looked abandoned (`rollout.lk`, `generators.lk`) but is the natural home for more.
- **Enemy model gate.** `tools/enemy_model_accuracy.py` exists for the ≥60% top-1 gate; clearing it unlocks the hand path and richer predictions — or justifies deleting the hand path for good.
- **Fresh ops headroom.** Memoization freed ~8.4M ops/turn (adversarial threat cache 8.4M → 0.84M). Search width is proven useless, but *candidate quality/simulation depth* is not.
- **Doctrine-driven matchup work** now has a stable testbed (`ladder_eleeksire`, paired harness) — the poison/sustain wall (ED 23.3%) is documented with per-turn diagnostics and next steps.

### Threats

- **Magic-number fragility persists.** ~50 hand constants in the V8 scorer + 16 EW + 7 `GA_TUNE` + 7×23 profiles. The doctrine's own evidence shows weight changes can be silently inert (three routes); a "suspiciously perfect null" is now a known failure mode.
- **Structural, not decisional, losses.** The value-model report's diagnosis — "every candidate's P(win) is low and close; the model's ranking of nearly-equal losing states is noise" — remains true for the matchups that move talent. Estimator upgrades (0.75 → 0.77 AUC) changed nothing there.
- **Sim-fidelity gaps and local/server divergence.** The simulator approximates crits/shields/launch legality; local compile tolerates constructs the server crashes on (method-as-value incident, 2026-08-19). A local A/B pass is not proof of live safety.
- **Harness blind spots + saturation.** ladder self-corrects to 50%; bots saturate at 100%; mirror can't see ENEMY_MODEL-gated code. Optimizing for measurable-not-mattering is a live failure mode; HP-broken draws in the harness is a methodology choice the real ladder doesn't share.
- **Meta drift.** The counters that decide talent shift; doctrine notes winners' edges (chips, capital) are partly unattainable, and nothing in V9 changes the resource asymmetry.

---

## 3. SWOT — Code Quality

### Strengths

- **Documentation density is exceptional for a game AI.** Every non-obvious constant carries a reason and a fight ID (`53593096`, `53302621`, …); incidents are recorded in-code (64KB method cap, NO_BLOC_TO_CLOSE, server runtime crash). A new maintainer can reconstruct *why*.
- **Clean seams where it matters.** `eval.lk` centralizes the rollout weights ("Do not scatter weights elsewhere"); `ga_weights.lk`, `value_model_data.lk`, `enemy_model_data.lk`, `item_database.lk` are generated with provenance headers and regenerate scripts.
- **Numerical rigour on the model path:** MLP parity required bit-exact against sklearn (5/5 vectors); weights emitted as string literals with a documented workaround for javac's per-method cap (double-hit and fixed).
- **Graceful degradation as a first-class pattern:** every expensive path is ops-gated; the pipeline has fallbacks at `_ops93` (defensive floor + move/fire) and a documented watchdog contract.
- **Tooling depth:** ~100 tools — harvesters, decoders with self-tests (`lw_decode.Decoder.self_test`), GA runner with warm-up serialization (avoiding compile-cache races), A/B harnesses, boss batch runners.
- **Commit hygiene:** small, atomic, message carries the experiment (n, seeds, p-values, ops deltas, revert decisions).

### Weaknesses

- **Monoliths.** `boss_context.lk` 6,962 lines, `scenario_combos.lk` 3,920, `base_strategy.lk` 3,181, `scenario_scorer.lk` 2,671, `unified_strategy.lk` 1,927. The campaign's own history shows the cost: a duplicated block broke braces and "masked the solve for 4 batches".
- **Dead and artifact code in the deploy tree.** `rollout.lk` (32) + `generators.lk` (219) are included by nothing; `main_iso.lk` (2), `enemy_model_data_iso.lk` (402), `enemy_model_data.lk.test.lk` (402), two `.bisecttest` copies (~2.3K) remain. Worse, **`upload_v9.py` filters only names containing `BACKUP`** — so the `.test.lk`/`_iso` files are uploaded to the server AI tree.
- **Three tuning surfaces + one hardcoded bypass.** `weight_profiles` (23-dim), `EW_*` (rollout eval), `GA_TUNE` (landscape constants) — plus `quickRecoveryChipValue`'s hardcoded values that ignore weights entirely. That last one is not inferred; the doctrine documents it as a measured trap (0/120 flips).
- **Feature-flag sprawl as the shipping mechanism.** 10 `_v9*` booleans (4 on / 6 off) plus debug flags on in the worktree (`_zdProbe = true`, `_v9RerankLog`, `_v9VetoLog`, cover-heatmap painting). The recurring failure mode is systemic: inert-enabled code (veto, rerank), temp debug firing in production (documented), dead branches costing ops and attention.
- **Comments as spec, no tests.** Rationale lives in comments; there is no unit-test layer for LS logic, no lint/brace check in any gate. Verification = generator compile + local fights + A/B. A stale comment misleads silently.
- **Doc drift at the top level.** `docs/v9_scope.md` still says "Status: scoping" with M0–M4 milestones while the shipped reality is Path A + veto + boss doctrine; `README.md`/`CLAUDE.md` describe V8 only, and even CLAUDE.md's file map is stale (boss_context "~1071" vs 5,000+ actual across trees).
- **Perf sensitivity near the cliff.** Pre-memoization, MH ran at 97% of budget with an 8.4M ops/turn hot spot; regressions silently flip the AI into a *different behavioral mode* (fallback path).
- **Duplication across trees.** V8_modules ↔ V9_modules divergence is managed by hand (boss_context 3,435 vs 6,962); `V9_baseline/` is a gitignored regenerated snapshot (fine, but another copy to reason about), plus `ga_local/v2_baseline_modules` in the GA loop.

### Opportunities

- **Rot removal + upload filter:** delete or wire `rollout.lk`/`generators.lk`, retire `_iso`/`.test`/`.bisecttest`, exclude them in `upload_v9.py`.
- **Automated gates cheaply:** a compile smoke test per commit, a brace/undefined-name lint for LS, and a replay regression set — the repo already cites canonical replays (52984834, fennel seeds 12345/777, `repro_*.py`).
- **Turn the fight-ID comments into structured regression cases.** They are already a latent test corpus.
- **Consolidate tunables** behind one generated config; fold `EW_RR_REPLY` into the GA genome (the file itself flags this as a TODO); audit the three chip routes with a permanent test.
- **Split `boss_context.lk`** into solve / combat / diagnostics modules; it grows monotonically per campaign.
- **Re-run the calibrated prod pool at threshold 0.005** to reconcile the two harnesses before the next promotion decision.
- **Write the V9 section** in README/CLAUDE (deployment, rollback, harnesses) and archive/update `v9_scope.md`.

### Threats

- **The one-constant failure mode is recurrent, not anecdotal:** veto dead by gate; rerank inert by threshold; debug trace live in production; `_zdProbe=true` in the working tree today. Without an "is this feature actually firing?" check (log assertion in CI or a fight-log scan), the next one ships too.
- **File-size growth vs the platform:** the javac 64KB cap has already been hit (enemy model, value model) and worked around; further growth pushes more code into opaque literal-parsing patterns.
- **Copy drift:** iso/test/baseline variants in the same tree invite both stale-tooling confusion and accidental uploads.
- **Knowledge concentration:** dense comments + docs are the only spec; docs are already drifting, and server semantics can differ from local ones. Losing the authorial context is a real continuity risk.
- **GA overfitting:** tunables are fitted on a 16-fight local corpus; "rebalancing does nothing" (today's commit) suggests flat/inert regions where the optimizer may be chasing noise; validation gates mitigate but don't eliminate.
- **Ops governance:** 14–20M budgets with multiple leeks at 70%+ usage; any new feature (or a memo miss) can push a leek across the 13M cliff into fallback behavior.

---

## 4. Bottom Line

**Strategy: B+.** V9's central wager — simulate the opponent, rank by an outcome model, keep the pipeline as the floor — is now partially validated with honest stats, and the project's measurement discipline (mirror A/B, doctrine ledger, GA gates, honest negatives) is the strongest part of the work. The unresolved issues are structural: boss phase 2 at current resources, team-fight modeling, and the fact that the matchups that cost talent may be decided by resources, not decisions.

**Code quality: B−/C+.** Excellent in documentation, generated-data discipline, and degradation design; weak in monolith size, dead/artifact code in the deploy path, three-plus tuning surfaces with a measured bypass, and verification that depends on human diligence rather than automated gates. The single highest-value structural change is not more AI features — it is *firing verification* (does each enabled path actually run?) plus rot removal, because both documented high-cost failures were inert-enabled code, not bad algorithms.

---

## 5. Solo Fight Soundness (addendum, 2026-09-21)

**Verdict: sound as a decision architecture; sound-but-not-sufficient as a solo fighter.** Solo is the native shape — enemy sim is single-target first (multi-enemy is the 70%/40% weapon-pressure bolt-on), the race model is 1v1 attrition, and counter-strategy and doctrine are ladder-solo work. The qualified part is results, not design.

### What is sound

- **The race model is the right instrument.** `race_model.lk` builds analytic turns-to-kill in both directions, blends toward observed net rates as evidence accumulates (obsWeight ramps to 0.7), confirms verdict changes over two consecutive turns with instant LOSING publish, and has an explicit STALL verdict for the draw signature (STALL↔WINNING flapping vs smart_tank was observed and handled).
- **The live feature has credible incremental evidence.** Mirror A/B (pre-committed n=220, paired, alternating sides): learned re-rank +11pp MH (p=0.001), +7pp ED (p=0.038), ops down 10.21M → 9.87M, regression 58/60. The same harness correctly killed a no-op (beam width 20→28, 51.4%, p=0.736).
- **Safety nets.** Status-quo thresholds on every override, catastrophe veto, ops gates at every stage, documented fallback floor; memoization restored headroom (MH at 73% of budget).

### What is not yet sound

- **The re-rank is not aimed at the fights that cap rank.** Project loss analysis: the deciding matchups are sustain bruisers/tanks with near-even, nearly-lost states — where the value-model report's own diagnosis holds ("the model's ranking of nearly-equal losing states is noise"). The +7–11pp was measured in mirror matches (near-even *winning* states). The structural matchup (ED vs Éleeksire, 23.3% over n=120) has survived GA weights, counter multipliers, the lethal solver, and three model-integration seats — all measured null.
- **Defensive playbooks are partly a decoy — verified in code.** `healValue` has exactly one read site, `scenario_scorer.lk:2663`, inside `scorePuzzle` (boss fights only). Every `adapted['healValue'] *= …` vs-kiter / vs-burst / vs-reflect adaptation in `strategic_depth.lk` therefore does nothing outside boss fights. Combined with the measured ~1350:1 damage:heal scoring ratio, the combat scorer is a damage maximiser regardless of profile. Doctrine note: "connect it or delete it."
- **Known scoring defects in the solo path.** DoT double-counted (composite damage ratio at `scenario_scorer.lk:110-112` plus standalone `dotScore` at `:748`); close-out gap persists (KG 48% near-miss losses; lethal force disabled).

- **Two of this section's open items were closed on 2026-09-21 — both negative:**
  - *Liberation vs poison* is **measured and null**. Self-cast was genuinely
    mis-modelled (the simulator applied every Liberation as an enemy shield
    strip regardless of target, and the scorer had no self-cast branch), but
    fixing both moved 3 of 120 paired fights, p=1.00. A ceiling test — a
    50,000,000 forcing bonus plus a relaxed gate — did **not** raise the cast
    rate (0.111 → 0.101/turn): usage is capped in scenario generation, and
    gate-passing turns are only ~1.75/fight, so the whole lever is worth
    ~576 HP/fight against ~6,800 poison absorbed. Reverted.
  - *"32% of turns deal no damage"* was **inflated, and is now diagnosed**. The
    true figure is 22% of all our turns (96/435, ED vs Éleeksire, n=40), and
    **64% of it is the unavoidable opening approach** — fights start 28 cells
    apart and take two turns to close (T1: 37, T2: 20, T3+: only 4). The
    addressable remainder is ~9% of turns, not 32%, which is well short of the
    ~30% damage increase the race arithmetic demands. Largest addressable
    bucket: 27 turns (28%) where the chosen scenario predicted damage and **no
    attack execution was attempted at all** — actions dropped between selection
    and execution, most likely in `validateAndFilterActions`. 8 turns (8%) were
    "could fire from a reachable cell, didn't".
  - *Method warning for anyone re-running this:* on ladder testbeds **both
    sides run V9**, and the generator's log carries no entity attribution
    (`logs[*][*][1]` is a severity level, not an id), so an untagged probe
    averages our decisions with the opponent's. Turn numbers also cannot be
    joined naively — the first `LEEK_TURN` pair precedes the first `NEW_TURN`.
    Three of four intermediate answers here were wrong from that join alone.
- **Evidence coverage limits.** Mirror A/B covers 2 of 4 leeks, same-kit only; the calibrated prod pool was never re-run at the enabled threshold (0.005); ENEMY_MODEL-gated code is unmeasurable by the main harness. There is no clean "V9 vs V8" solo number anywhere — bots saturate, the ladder self-corrects to ~50%, and mirror measures V9-vs-V9 feature deltas. The +11pp is an increment *within* V9, not proof V9 beats V8 live.
- **Methodology caveat.** Mirror A/B breaks draws by HP; the ladder does not. Real draw-rate effects are not captured.

### Cheapest paths to "fully sound"

1. Connect-or-delete `healValue` in the combat scorer (and fix the DoT double count) — both verified present.
2. Re-run the calibrated prod pool at threshold 0.005 to reconcile the two harnesses before the enablement is treated as permanent.
3. Extend mirror A/B coverage to KurtGodel and AdaLovelace (the untested builds).
