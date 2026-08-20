# V9 Scope — Simulator-First Decision Layer

**Status**: scoping (2026-08-12). V8 remains the production AI; V9 ships milestone-by-milestone, each independently shippable, with V8 as the permanent fallback.

## Why V9

V8 is a one-turn greedy heuristic: a beam search scoring candidate turns with ~50 hand-tuned magic numbers. Its documented failure modes this campaign (Aug 2026):

- no lookahead — can't plan "deny now → dump next turn" as a sequence (the rotation is a bolt-on);
- no opponent model — plays the same against a 600-STR bruiser and a poison kiter;
- magic-number fragility — fixes are new constants interacting with old ones (denial treadmill, burst escape dead for 2 months, recovery firing into shields for 0 damage, caster-blind race model);
- consequence: talent plateau at rank 400-800 at level 301 with meta-par builds.

**Design rule #1: V9 is a clean implementation, deployed side-by-side with V8.** There is NO in-AI fallback to a V8 decision — the user reassigns leeks back to `8.0/V8/main.lk` manually if V9 underperforms. This frees the entire per-turn ops budget (no V8 precompute, which would have cost 60-80% of it) for V9's own rollout, and makes cure's 8-core leeks V9-viable from day one.

## Deployment & rollback (side-by-side guarantee)

- **Upload isolation**: V9 deploys to `9.0/V9/main.lk` as a separate AI entity. V8 stays at `8.0/V8/main.lk`, byte-identical and assigned. (Precedent: the Python variant already lives side-by-side at `8.0/V8_python/main.py` with zero assignment changes.)
- **Assignment isolation**: no leek moves to V9 at upload time. Trials are per-leek opt-in via `leekwars_set_leek_ai` or manual assignment in-game. Rollback = reassign to V8 — instant, no rebuild, no re-upload.
- **Ops watchdog**: the rollout completes within budget or returns the best fully-simulated candidate computed so far — a graceful degrade *inside* V9, never an escape to V8 code.
- **Promotion gate**: bots (Domingo/Hachess) → single-leek trial → 2-day talent hold → full assignment. V8 remains assigned on ≥3 of 4 leeks until V9 earns it.

## Ops budget reality

`_opsBudget = cores × 1M ops` (main.lk:85). Main leeks: 14-20 cores → 14-20M ops/turn. Cure leeks: 8 cores → 8M ops. V8 currently consumes ~60-80% of budget. V9 gets the remaining headroom (~4-5M ops on main), and **degrades by core count**: full rollout at ≥12 cores, reduced K at 10-11, heuristic-only (V8 behavior) at ≤9 — cure stays V8 until its cores grow or V9 proves cheap.

## Pillar 1 — Simulation-based turns (SIM-FIRST)

Current flow: generators (beam + combos) propose action lists → heuristic scorer picks one → execute → recovery pass.

V9 inserts a **rollout verifier** between proposal and execution:

1. V8 computes its normal heuristic decision first (guaranteed decision, unchanged code path).
2. Generators also yield the top-K candidate turns (K=5-8 on main, K=2-3 at low cores).
3. For each candidate: simulate our turn (existing `ScenarioSimulator.simulate(actions)` — already models damage/shields/heals/buffs/dropped actions) → **simulate the enemy's response** (new, driven by Pillar 2) → score the 1.5-turn outcome with the heuristic scorer as evaluation function.
4. Re-rank; winner executes only if it beats the V8 candidate by a margin (status-quo bias, same pattern as the alt-target pass).
5. Ops watchdog: rollout window is a fixed slice of the remaining budget; on overrun → V8 decision executes.

Scoring under uncertainty: 0.7 × expected outcome + 0.3 × worst-case (mirrors the adversarial-threat philosophy already in field_map).

Depth: 1.5 turns (ours + enemy + our TP-remainder) at launch; depth 2 is M4 stretch.

## Pillar 2 — Opponent-turn prediction (ENEMY MODEL)

Two layers:

- **Archetype prior** (exists, thin): enemy_intelligence classifies bruiser / kiter / magic_poison / summoner / tank. Extend to produce a concrete next-turn action-set per archetype: opener-buffs (turn ≤ 2), max-damage weapon sequence given their weapons + our post-move position, poison casts for kiters, summon+buff for summoners. Reuses simulator mechanics in reverse from their entity data (weapons, stats, chips are all readable).
- **Per-opponent memory** (new, offline): the fight history DBs already store every fight vs ~1300 opponents. An offline pipeline extracts per-opponent tendencies — opener style, weapon usage rates, kite distance, antidote timing, shield cadence — into `enemy_model.json` per account, refreshed by cron. Live, the top-3 likely action sets + probabilities feed Pillar 1's enemy sim.

**Accuracy gate**: the model runs in shadow (log-only) first. It must hit ≥60% top-1 action-class accuracy on fresh fights before any decision consumes it. Below gate: enemy sim falls back to the archetype prior only.

## Pillar 3 — Self-tuning loop (GA v2)

The evaluation function's ~50 weights become GA-tunable on outcomes, not proxies.

- **Harness**: existing local generator (leek-wars-generator) + opponent corpus: the `live_*` ladder builds (top-100 scrape) + our counter bracket (PrototypeA01, metallic-bulb summoners, WiseMan-class burst).
- **Fitness**: win rate of V9 vs corpus across seeded fights, plus decision-quality metrics from M0 (wasted TP, zero-damage actions, disengage failures) as tiebreakers.
- **Cadence**: weekly offline run → candidate weight sets → bot A/B → 25-fight shadow sample → promote if talent-neutral-or-better over 2 days. Weight sets live in ga_tunables.lk (already versioned); rollback = previous file.
- **Safety**: GA never touches control flow — only evaluation weights. The fallback structure is untouchable.

## Milestones

| # | Deliverable | Ships when | Est. |
|---|---|---|---|
| M0 | **Harness & scoreboard**: local replay metrics (wasted TP, 0-dmg actions, disengage failures) + talent/rank dashboard | first | ~1 day |
| M1 | **Enemy model v1** (archetype prior + offline per-opponent memory), shadow-logged, accuracy gate ≥60% | after M0 | ~2 days |
| M2 | **Rollout verifier v1**: top-K re-rank via our-turn + enemy-turn sim, V8 fallback under cap | after M1 gate | ~3-4 days |
| M3 | **GA v2** on evaluation weights, weekly cadence + A/B promotion | after M2 stable | ~2 days + ongoing |
| M4 | **Depth-2 rollout + multi-enemy** (team fights) | stretch | later |

## Validation

- Local battery before every upload (existing): boss_fennel seeds 12345/777, hot-branch repro, 52984834 replay, lk2py --check — plus M0 metrics must not regress.
- Live A/B ladder: bots (Domingo/Hachess) → 25-fight shadow sample → 2-day talent hold → promote.
- Rollback story at every milestone: V8 untouched underneath, weight files versioned, uploads are additive.

## Risks

- **Ops blowout on cure (8 cores)** — mitigated by degrade-by-cores; cure stays V8 until V9 proves cheap.
- **Enemy model mispredicts** — accuracy gate + pessimism weighting; heuristic scorer stays the floor.
- **Magic-number debt migrates into the eval function** — GA v2 owns the weights from M3 onward.
- **Sim fidelity gaps** (simulator already approximates crit/shields/launch legality) — measured by M0 replay metrics; fidelity fixes land as ordinary bugs.
