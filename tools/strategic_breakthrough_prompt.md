# Strategic Breakthrough Analysis — LeekWars AI V8

## Task
Analyze a competitive AI for LeekWars (turn-based 1v1 combat, diamond grid, 613 cells, 64-turn limit). The AI is mature (~20K lines). Find 3-5 **high-impact strategic breakthroughs** to improve win rates. Read the codebase before proposing. Each proposal needs: exact files, mechanism, impact estimate, ops cost (budget: 14M/turn, ~10-12M used).

## Game Mechanics
- 64-turn limit. Draw if both alive. Per turn: 10-12 TP (actions), 3-5 MP (movement). **TP/MP reset to max each turn — unspent TP does NOT carry over** (verified: generator `Entity.endTurn()` zeroes usedTP). The only inter-turn resources are chip cooldowns and effect durations.
- **Damage**: Direct (STR/MAG scaled), Poison (MAG, ticks N turns), Nova (SCI, permanent max HP reduction).
- **Defense**: Absolute shield (flat), Relative shield (%), Resistance stat (flat), Healing (WIS scaled), Damage Return (reflects %).
- **Key chips**: Antidote (removes poisons, CD~4), Liberation (strips buffs from target), Vulnerability (amplifies damage taken).
- Cooldowns per chip (1-5 turns). Weapons have none. 6 stats: STR, MAG, AGI (crit+dodge), SCI (nova), RES (reduction), WIS (heal).

## Our Builds (same AI code, different stats → weight profiles)
| Leek | HP | STR | MAG | AGI | WIS | RES | SCI | Role |
|---|---|---|---|---|---|---|---|---|
| EdsgerDijkstra | 2380 | 500 | 0 | 550 | 400 | -40 | 90 | STR/AGI burst (flagship) |
| AdaLovelace | 2725 | 590 | 0 | 0 | 500 | 300 | 80 | STR burst |
| KurtGodel | 2442 | 400 | 0 | 50 | 400 | 400 | 400 | Tank/SCI (Nova attrition) |
| MargaretHamilton | 2857 | 300 | 600 | 70 | 300 | 150 | 70 | Magic/Poison |

## V8 vs V8 Baselines (both sides run same AI, different stats)
| Matchup | W% | L% | D% | Turns | Insight |
|---|---|---|---|---|---|
| Dijkstra mirror | 53 | 47 | 0 | 1.9 | Coin flip, slight first-mover edge |
| Dijkstra vs v8_kurt | **100** | 0 | 0 | 5.3 | Burst demolishes tank |
| Dijkstra vs v8_ada | 70 | 30 | 0 | 4.9 | AGI edge over pure STR |
| Dijkstra vs v8_margaret | 80 | 20 | 0 | 4.2 | STR crushes magic |
| **KurtGodel vs v8_dijkstra** | **7** | **93** | 0 | 5.9 | **Tank unplayable vs burst** |
| KurtGodel mirror | 60 | 33 | 7 | 17.0 | Only matchup with draws |
| **Margaret vs v8_dijkstra** | **3** | **97** | 0 | 3.4 | **Magic unplayable vs burst** |
| Margaret vs v8_kurt | 57 | 43 | 0 | 8.2 | Poison > regen |
| Margaret mirror | 43 | 57 | 0 | 4.5 | Coin flip |
| Ada vs v8_dijkstra | 47 | 53 | 0 | 4.6 | Close, AGI decides |

## The Problems (Ranked)
1. **KurtGodel 7% W vs burst** — Has 400 RES, 400 SCI, shields, heals, Nova. Dies in ~6 turns anyway. Nova never gets to matter.
2. **Margaret 3% W vs burst** — Has 600 MAG, poison state machine (BAIT→DUMP→SUSTAIN). Dead in ~3 turns before poisons tick.
3. **Mirror 50/50** — No systematic edge with identical code. Room for strategic differentiation.
4. **KurtGodel mirror 7% draws** — Two tanks can't kill each other in 64 turns.

**Core question: Why do builds with shields, heals, kiting, and damage return still die in 3-6 turns to burst? The tools exist — the AI isn't using them effectively.**

## Architecture

### Files included (read these — listed by priority for this analysis)
```
CRITICAL (read first — these determine how tank/magic builds play):
  weight_profiles.lk        — 7 build profiles × 23 weights (are TANK/MAGIC tuned for survival?)
  scenario_generator.lk     — State machine → template dispatch (what scenarios do defensive builds get?)
  scenario_helpers.lk       — State detection, action construction (FLEE/SUSTAIN thresholds)
  scenario_scorer.lk        — 23-dimension scoring (how is survival vs damage weighted?)
  strategic_depth.lk        — Counter-strategy multipliers (vs_burst handling)
  strategy/unified_strategy.lk — Main loop, TP recovery

IMPORTANT (read next):
  scenario_combos.lk        — 38 scenario templates (defensive templates exist?)
  strategy/base_strategy.lk — Scenario execution, movement guards (~3000 lines)
  tactical_awareness.lk     — Adversarial threat cache
  enemy_predictor.lk        — 1-turn lookahead
  enemy_intelligence.lk     — Enemy profiling

SUPPORTING (skim if needed):
  scenario_simulator.lk     — Damage/effect projection
  beam_search.lk            — Bottom-up action discovery (width 20, depth 10)
  field_map_tactical.lk     — Threat maps, positioning
  item.lk                   — Arsenal, damage calc
  field_map_core.lk         — Pathfinding, cell utilities
  scenario_quick_scorer.lk  — Fast pruning
  scenario_mutation.lk      — Scenario mutations
  main.lk                   — Entry point
  strategy/action.lk        — Action class (17 types)
  game_entity.lk            — Entity model (stats, effects)
  kill_planning.lk          — Kill calculation
  cooldown_tracker.lk       — CD tracking
  reachable_graph.lk        — Movement graph
  game_context.lk           — Context setup
  item_roles.lk             — Chip classification helpers
```

### Files NOT included (irrelevant to PvP burst-survival problem)
```
  boss_context.lk           — Fennel King boss fight only
  item_database.lk          — Pure data tables (weapon/chip stats)
  field_map_patterns.lk     — AoE geometry detail
  performance_infra.lk      — Debug logging
  cache_manager.lk          — Cache utilities
  bulb_ai.lk                — Summoning logic
```

**Pipeline**: Reset → Profile enemies → Threat map → Generate scenarios (templates + beam) → Quick-score → Mutate top seeds → Simulate & score → 2-ply planning → Lookahead → Execute best → TP recovery

**Weight examples**: STRENGTH: burstDamage=300, shieldValue=80 | TANK_SCI: shieldValue=400, healValue=200, novaEffects=400 | MAGIC: dotEffects=500, kiteDistance=200

**States**: KILL → AGGRO → ATTRITION → SUSTAIN → FLEE (evaluated per turn)

**Counter-strategies**: Hardcoded multipliers for vs_kiter, vs_burst, vs_tank, vs_reflect, cooldown_windows. No runtime learning beyond HP trend + shield frequency.

## Known Gaps (already identified — don't re-discover, focus on solutions)
- Enemy profiling one-shot, never updated
- Only 2 observation signals for adaptation
- 7 dead scenario templates
- No counter for magic/poison enemies
- No TP-banking/deliberate-pass template
- State machine flip-flops (no hysteresis)

## What "Breakthrough" Means
**NOT**: weight tuning, null checks, enabling dead templates
**YES**: Novel mechanisms changing how the AI reasons. Think:
- Survival-first turn sequencing for defensive builds
- Whether opening turns are optimal (shields before or after movement?)
- Positional asymmetry (fragile builds need distance — does the AI know this?)
- Proactive vs reactive defense (shield on turn 1 vs shield after taking damage)
- Cooldown-window scheduling (TP can't be banked — but chip cooldowns and enemy shield/heal gaps are the real inter-turn resource)
- Whether TANK/MAGIC weight profiles are even correct for survival

## Constraints
- LeekScript (JS-like). `include()` + globals only. Maps: `map['key']` not `map.key`.
- 14M ops/turn budget, ~2-4M headroom.
- Changes within existing pipeline. No new files.
- Must not regress Dijkstra's 70-100% win rates.

## Deliverable
Per breakthrough:
1. **Name** (3-5 words)
2. **Target matchup** (specific: "KurtGodel vs burst")
3. **Root cause** (read the code — why does current AI fail here?)
4. **Mechanism** (what changes, game mechanics exploited)
5. **Implementation** (file, function, ~20 lines pseudocode)
6. **Impact** (estimated win% change)
7. **Risk** (regressions, verification)
