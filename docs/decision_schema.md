# V8 AI Decision-Making Schema

Visual reference for what the V8 AI does each turn. All diagrams are Mermaid
(viewable in GitHub, VS Code with the Mermaid extension, or any Mermaid live
editor). Line numbers reference the current `V8_modules/` source.

---

## 1. Per-Turn Pipeline (high level)

What runs from `main()` every turn, in order. Reference: `main.lk:154-321`.

```mermaid
flowchart TD
    A[Turn starts<br/>main.lk:154] --> B[resetTurnState<br/>clear caches]
    B --> C{Turn == 1?}
    C -->|yes| D[initializeAdjacency<br/>warmLosCacheFromCell<br/>~30-70k ops]
    C -->|no| E
    D --> E[player.updateEntity<br/>fieldMap.updateMapEntities]
    E --> F[profileAllEnemies<br/>observeEnemyBehavior]
    F --> G{Boss fight?}
    G -->|yes| H[updateBossContext<br/>+ PUZZLE/COMBAT branch]
    G -->|no| I
    H --> I[Select target<br/>selectOptimalTarget → closestEnemy]
    I --> J[updateGameContext<br/>cooldownTracker.updateCooldowns<br/>killPlanner.updateGlobalKillPlan]
    J --> K[buildReachableGraph<br/>initializeCaches<br/>buildEnemyThreatMap]
    K --> L{Ops < _ops64?<br/>~9M of 14M}
    L -->|yes| M[buildAdversarialThreatCache<br/>predicts enemy max damage<br/>at each reachable cell]
    L -->|no| N
    M --> N[paintCoverHeatmap]
    N --> O[__nearestFireTurn<br/>turns-until-shot classifier]
    O --> P{Build damage map?}
    P -->|yes| Q[fieldMap.buildHitMap<br/>getBestWeaponOrChipCell]
    P -->|no| R
    Q --> R{Ops > _ops93?<br/>~13M / 14M}
    R -->|yes| S[FALLBACK<br/>moveToward + greedy fire<br/>main.lk:251-296]
    R -->|no| T[strategy.createAndExecuteScenario<br/>main scenario pipeline]
    T --> U[extendLosCache<br/>background fill]
    U --> V[Turn ends]
    S --> V
```

**Key gates by ops budget** (init in `main.lk:80-118`):

| Gate | % of budget | Behavior |
|---|---|---|
| `_ops50` | 50% | alt-target counterfactual cutoff |
| `_ops64` | 64% | adversarial threat cache cutoff |
| `_ops71` | 71% | nearestFireTurn cutoff |
| `_ops93` | 93% | hard fallback (skip scenario pipeline) |
| `_opsBudget` | 100% | crash boundary — must finish under this |

---

## 2. Strategic State Decision (per turn)

Determined inside `scenario_generator.generateScenarios` via
`determineStrategicState()` (`scenario_helpers.lk:67`). Drives which family
of scenario templates is built.

```mermaid
flowchart TD
    S[determineStrategicState] --> B0{Boss fight<br/>& PUZZLE phase?}
    B0 -->|yes| PZ[PUZZLE<br/>buildPuzzleScenarios]
    B0 -->|no| B1{HP < 40%?}
    B1 -->|yes| FL[FLEE<br/>buildFleeScenarios<br/>emergency retreat + heal]
    B1 -->|no| B2{Est. damage ≥ 95% enemy HP<br/>AND in weapon range?}
    B2 -->|yes| KL[KILL<br/>buildKillScenarios<br/>all-in, skip buffs]
    B2 -->|no| B3{Time pressure?<br/>+ turn > 30}
    B3 -->|yes - force| AT[ATTRITION<br/>never sit back]
    B3 -->|no| B4{Turn > 45<br/>+ enemy > 50% HP?}
    B4 -->|yes| AG[AGGRO<br/>force closing]
    B4 -->|no| B5{HP 40-60%<br/>+ enemy > 40% HP<br/>+ no time pressure?}
    B5 -->|yes| SU[SUSTAIN<br/>heal + position]
    B5 -->|no| B6{Early game<br/>OR buffs expired<br/>OR late time-pressure?}
    B6 -->|yes| AG2[AGGRO<br/>buff → approach → attack]
    B6 -->|no| AT2[ATTRITION<br/>default combat]
```

After state selection, **beam search** (`beam_search.lk`) runs additionally if
state ∉ {PUZZLE, FLEE} and ops < _ops64 — adds discovered novel sequences to
the scenario pool. See `scenario_generator.lk:107-112`.

---

## 3. Scenario Pipeline (the main brain)

What `strategy.createAndExecuteScenario` actually does
(`strategy/unified_strategy.lk:42-121` and `generateAndEvaluateBestScenario`
at line 123). This is where the 23-dimension scoring lives.

```mermaid
flowchart TD
    G[generator.generateScenarios<br/>state-based templates<br/>+ beam search] --> Z{≥1 scenario?}
    Z -->|no| FB[createFallbackScenario]
    Z -->|yes| QS[ScenarioQuickScorer<br/>fast pruning heuristic<br/>family classification]
    QS --> SORT[Sort by quickScore<br/>pin top 3 raw scores]
    SORT --> DIV[Family-diversity reorder<br/>14 best + 3 defensive + 3 utility]
    DIV --> MUT[Mutation pass<br/>top 6 seeds<br/>×4 mutation types]
    MUT --> SIM[ScenarioSimulator<br/>project damage + effects]
    SIM --> SCR[ScenarioScorer<br/>23-dimension evaluation]
    SCR --> TPL[2-ply planning<br/>top 5 scenarios<br/>discount 40%]
    TPL --> LK[Enemy response lookahead<br/>top 3 scenarios]
    LK --> ALT{Alt-target<br/>beats primary +200?}
    ALT -->|yes| SWAP[Swap target<br/>use alt scenario]
    ALT -->|no| EXEC
    SWAP --> EXEC[executeScenario]
    EXEC --> KILLED{Target died?}
    KILLED -->|yes| RT[Re-target next enemy<br/>repeat lighter pipeline]
    KILLED -->|no| REC[recoverRemainingTP<br/>greedy spend leftover TP]
    RT --> REC
    REC --> DONE[Turn complete]
```

### Mutation types (`scenario_mutation.lk`)
1. **Aim optimization** — shift AoE target ±1 for splash coverage
2. **Swap** — reorder adjacent actions for better sequencing
3. **Substitution** — replace chip with same-type alternative
4. **Insertion** — add unused chips into gaps

---

## 4. The 23 Scoring Dimensions

The scorer (`scenario_scorer.lk`) aggregates these into a single score per
scenario. Grouped by purpose:

```mermaid
flowchart LR
    OFF[OFFENSE]
    OFF --> O1[1 Burst damage]
    OFF --> O2[2 Kill probability<br/>≥70%: 5x, ≥50%: 2.5x]
    OFF --> O3[3 DoT damage]
    OFF --> O4[4 Poison compounding<br/>duration-weighted]
    OFF --> O5[5 Poison stacking]
    OFF --> O6[6 Nova damage<br/>Max-HP reduction]
    OFF --> O7[7 Vulnerability stacking]
    OFF --> O8[8 Denial cascade<br/>TP/MP × DPT × 3]

    DEF[DEFENSE]
    DEF --> D1[9 Shield value]
    DEF --> D2[10 Healing value]
    DEF --> D3[11 Lifesteal]
    DEF --> D4[12 Position score]
    DEF --> D5[13 Adversarial threat<br/>death prediction]

    EFF[EFFICIENCY & MISC]
    EFF --> E1[14 TP efficiency]
    EFF --> E2[15 Buff value]
    EFF --> E3[16 Debuff value]
    EFF --> E4[17 Crit bonus]
    EFF --> E5[18 OTKO bonus<br/>+5000 one-turn-kill]
    EFF --> E6[19 Synergy matrix<br/>9+ combos]
    EFF --> E7[20 Continuation value<br/>buff/poison carry-fwd]
    EFF --> E8[21 Time pressure<br/>phased escalation]
    EFF --> E9[22 No-damage penalty<br/>-2000 to -14000]
    EFF --> E10[23 2-ply planning]
```

**Build-specific weighting:** Each leek build (STR / Magic / Agility / STR-SCI
/ Tank-SCI / Hybrid / Bruiser-Reflect) loads a different weight profile from
`weight_profiles.lk` (~303 lines, 7 profiles × 23 weights). Same scorer code,
different multipliers — no build-specific branching in the scoring engine.

---

## 5. Poison State Machine (Magic builds only)

`scenario_generator.lk:15-60`. Drives MH's behavior against enemies that
carry Antidote.

```mermaid
stateDiagram-v2
    [*] --> BAIT: turn 1, has poison capability
    BAIT --> DUMP: antidoteCD ≥ 2 AND ≥2 stacks applied
    BAIT --> DUMP: 8 turns elapsed (timeout)
    BAIT --> DUMP: enemy has NO antidote at all
    DUMP --> SUSTAIN: dump executed
    SUSTAIN --> BAIT: antidoteCD == 0 AND ≥3 turns since last dump
    DUMP --> [*]
```

- **BAIT**: light poisons + denial → trigger enemy's Antidote use
- **DUMP**: all-in poison (COVID, Arsenic, Plague, weapons) while Antidote on CD
- **SUSTAIN**: maintain stacks, heal, position; wait for next BAIT window

Checkpoint bonuses applied by scorer:
- `POISON_DUMP` mandatory: **+10,000**
- `POISON_BAIT` recommended: **+4,000**

---

## 6. Counter-Strategy Adaptation

`strategic_depth.lk` (~407 lines) — adapts the 23 weights based on enemy
profile after observation accumulates.

| Enemy archetype | Weight changes |
|---|---|
| **Kiter** | +distance, +heal, +DoT; −kiting penalty |
| **Burst** | +shields, +healing, +threat-awareness |
| **Tank** | Nova ×1.64, denial ×1.30, DoT ×1.20 |
| **Reflect (active)** | burst ×0.47, +shields, +healing |
| **HP trending up** (≥5 obs) | burst ×1.3, denial ×1.5 |
| **Never shields** (≥5 obs) | burst ×1.2, shieldValue ×0.8 |

Cooldown-aware: when enemy's shield/heal is on CD, burst weight gets boosted
to exploit the window.

---

## 7. Boss Fight Branch (Fennel King)

Only active when `_isBossFight` is true (`main.lk:129-131, 179-192,
298-300`).

```mermaid
flowchart TD
    BOSS[Boss fight detected] --> BP{_bossPhase}
    BP -->|PUZZLE| PZ[executePuzzleTurn<br/>Apocalypse guard blocks damage]
    PZ --> PZA[Align crystals to graal axes<br/>via GRAPPLE / BOXING_GLOVE]
    PZA --> PZB[Mutations DISABLED<br/>position-critical]
    PZB --> PZC[BOSS_PUZZLE_WEIGHTS]
    BP -->|COMBAT| CB[selectCombatTarget<br/>standard combat]
    CB --> CB1[BOSS_COMBAT_WEIGHTS]
```

---

## 8. Fallback Path

Triggered when ops > `_ops93` (≥93% of budget consumed before scenario
pipeline) — `main.lk:251-296`.

```mermaid
flowchart TD
    F[FALLBACK triggered] --> F1[Compute weapon-range envelope<br/>min/max across equipped weapons]
    F1 --> F2{LoS missing<br/>OR distance > maxR<br/>OR distance < minR?}
    F2 -->|yes| F3[moveToward target]
    F2 -->|no| F4[Stay put<br/>avoid closing into kiters]
    F3 --> F5[Greedy fire pass]
    F4 --> F5
    F5 --> F6[For each equipped weapon:<br/>if range valid AND TP ≥ cost,<br/>setWeapon + useWeaponOnCell<br/>fire 2nd shot if maxUse ≥ 2]
    F6 --> F7[Return]
```

---

## 9. Module Dependency Order (include chain)

Order matters in `main.lk`. Anything earlier in this list can be used by
anything later, not the other way around.

```mermaid
flowchart LR
    GE[game_entity] --> FMT[field_map_tactical]
    FMT --> IT[item]
    IT --> IR[item_roles]
    IR --> GC[game_context]
    GC --> KP[kill_planning]
    KP --> CT[cooldown_tracker]
    CT --> EP[enemy_predictor]
    EP --> RG[reachable_graph]
    RG --> PI[performance_infra]
    PI --> CM[cache_manager]
    CM --> TA[tactical_awareness]
    TA --> WP[weight_profiles]
    WP --> EI[enemy_intelligence]
    EI --> SD[strategic_depth]
    SD --> BC[boss_context]
    BC --> AC[strategy/action]
    AC --> BU[bulb_ai]
    BU --> BS[beam_search]
    BS --> SG[scenario_generator]
    SG --> SS[scenario_simulator]
    SS --> SCR[scenario_scorer]
    SCR --> QSC[scenario_quick_scorer]
    QSC --> MUT[scenario_mutation]
    MUT --> BST[strategy/base_strategy]
    BST --> US[strategy/unified_strategy]
```

---

## 10. Where to look when

Quick navigation when debugging a specific behavior:

| Symptom / question | First file to open |
|---|---|
| "Why did it choose this state?" | `scenario_helpers.lk:67` (determineStrategicState) |
| "Why this scenario over another?" | `scenario_scorer.lk` (scoring), enable scenario debug |
| "Why didn't it use chip X?" | `scenario_combos.lk` (templates), `scenario_generator.lk` (build*Scenarios) |
| "Why did it stand still?" | `main.lk:251` fallback, or `unified_strategy.lk` no-scenario branch |
| "Why poison/heal at wrong time?" | `scenario_generator.lk:15-60` POISON state machine |
| "Wrong weapon at wrong range?" | `field_map_tactical.lk` buildHitMap, `scenario_simulator.lk` |
| "Boss puzzle stuck?" | `boss_context.lk` (1071 lines) |
| "Burned ops budget?" | check `_ops*` gates above + `performance_infra.lk` |
