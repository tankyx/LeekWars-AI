# LeekWars AI V8 — Reference Guide

## Quick Start

```bash
# Upload to LeekWars server
python3 tools/upload_v8.py

# Local test (fast, deterministic)
python3 tools/local_test.py 40 smart_tank --leek EdsgerDijkstra --parallel 2

# Server test (real matchmaking)
python3 tools/lw_test_script.py 10 456711 domingo --leek EdsgerDijkstra

# Debug a specific fight
python3 tools/fight_analyzer.py smart_tank --leek EdsgerDijkstra --seed 1
```

---

## Coding Principles

### Language: LeekScript (.lk)

- JavaScript-like syntax running on LeekWars game server
- **Maps use BRACKET notation** `map['key']`, NOT dot notation `map.key`. Dot notation only works on class instances.
- `global` keyword declares globals; must be declared before use in included files
- `include('file.lk')` — include order matters, dependencies must come first
- LeekWars API functions (`getCell`, `getCellDistance`, `lineOfSight`, `getTP`, `getTurn`, etc.) are always available globally
- No `import`/`require` — everything is via `include()` and globals

### Ops Budget

- **14M operations per turn** (set by `cores=14` in generator config)
- Hard stop at **13M ops** — falls back to simple move+attack
- Each API call (getCellDistance, lineOfSight, etc.) costs ops
- Expensive: pathfinding, threat cache, scenario simulation
- Cheap: math, map lookups, array access

### Architecture Rules

- All builds use **one unified strategy** (`UnifiedStrategy`) — behavior differentiation is via weight profiles, not separate code paths
- New features go into the **scenario pipeline** (generate → quick-score → simulate → score → execute), not into ad-hoc execution logic
- **Never add build-specific if/else chains** in the scorer or simulator — use weights
- Test changes against **multiple leeks and opponents** to avoid regressions

### File Organization

- `V8_modules/main.lk` — entry point, include order, per-turn loop
- `V8_modules/strategy/` — strategy classes (action.lk, base_strategy.lk, unified_strategy.lk)
- All other `.lk` files at `V8_modules/` root — modules included by main.lk
- `tools/` — Python testing/upload utilities (not deployed to server)

---

## Testing

### Local Testing (Preferred)

```bash
python3 tools/local_test.py <num_fights> <opponent> --leek <name> [--parallel N]
```

**Opponents**: `smart_str`, `smart_mag`, `smart_tank`, `smart_agi`, `dummy_str`, `dummy_mag`, `dummy_tank`, `dummy_agi`, `mirror`

**Leeks**: `EdsgerDijkstra` (STR/burst), `KurtGodel` (Tank/SCI), `MargaretHamilton` (Magic/Poison), `AdaLovelace` (STR/burst), `AlanTuring` (AGI/reflect)

**CRITICAL**: After editing ANY `.lk` file, clear the compilation cache before testing:
```bash
rm -f /home/ubuntu/leek-wars-generator/ai/*.class /home/ubuntu/leek-wars-generator/ai/*.java /home/ubuntu/leek-wars-generator/ai/*.lines
```
The generator caches compiled `.lk` files and only checks the root file's timestamp, not included files.

### Standard Test Matrix

```bash
# Primary draw-heavy matchups (target: reduce draws)
python3 tools/local_test.py 40 smart_tank --leek EdsgerDijkstra --parallel 2
python3 tools/local_test.py 40 smart_tank --leek KurtGodel --parallel 2

# Magic build validation
python3 tools/local_test.py 40 smart_mag --leek MargaretHamilton --parallel 2

# Regression checks (must stay 100% or near)
python3 tools/local_test.py 20 smart_str --leek EdsgerDijkstra --parallel 2
python3 tools/local_test.py 20 smart_agi --leek EdsgerDijkstra --parallel 2
python3 tools/local_test.py 20 smart_str --leek AdaLovelace --parallel 2
```

### Baseline Win Rates (local tests)

| Matchup | Win Rate | Notes |
|---|---|---|
| EdsgerDijkstra vs smart_str | ~100% | Strong matchup |
| EdsgerDijkstra vs smart_agi | ~100% | Strong matchup |
| EdsgerDijkstra vs smart_tank | ~40% W / 60% D | Draw-prone, tank has 8000 HP |
| AdaLovelace vs smart_str | ~100% | Strong matchup |
| KurtGodel vs smart_tank | ~35% W / 65% D | Nova attrition vs tank |
| MargaretHamilton vs smart_mag | ~12.5% W | Structurally unfavorable (0 STR/RES) |

### Server Testing

```bash
python3 tools/lw_test_script.py <num_tests> 456711 <opponent> [--leek <name>]
```
Script ID **456711** is the V8 AI `main.lk`. Do NOT use 447461 (old, broken).

### Fight Analysis

```bash
python3 tools/fight_analyzer.py <opponent> --leek <name> [--seed N]
```

Saved to `debug_fight_<id>.json`. Key action codes: 6=NEW_TURN, 7=LEEK_TURN, 10=MOVE, 12=USE_CHIP, 13=SET_WEAPON, 16=USE_WEAPON, 101=LIFE_LOST, 110=POISON_DAMAGE, 5=PLAYER_DEAD, 1002=BUG/CRASH.

If entity 0 has 0 ops and action 1002 every turn, the script has a runtime error.

### Generator Setup

- Generator: `/home/ubuntu/leek-wars-generator/generator.jar`
- Build: `cd /home/ubuntu/leek-wars-generator && JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew jar`
- Symlink: `leek-wars-generator/V8_modules` → our `V8_modules/`
- Config: `cores=14` (ops budget), `ram=50` (memory)
- `tools/refresh_generator_data.py` — syncs market data to generator
- `tools/fetch_leek_configs.py` — fetches leek stats from API

---

## Architecture Overview

### Scenario Pipeline (per turn)

```
Reset caches → Update entities → Profile enemies → Observe enemy behavior
→ Build reachable graph → Initialize caches → Build threat map → Build adversarial threat cache
→ Generate scenarios (state templates + beam search)
→ Quick-score & sort (fast pruning, top-K selection)
→ Mutate top seeds (swap, substitute, insert mutations)
→ Simulate & score (full projection + 23-dimension evaluation)
→ 2-ply planning (project next-turn value for top 5)
→ Enemy response lookahead (top 3)
→ Execute best scenario → TP recovery (greedy spend of leftover TP)
```

### Class Hierarchy

```
ScenarioHelpers → ScenarioCombos → ScenarioGenerator  (scenario construction)
Strategy → UnifiedStrategy                             (execution)
ScenarioSimulator                                       (damage/effect projection)
ScenarioScorer                                          (23-dimension evaluation)
ScenarioQuickScorer                                     (fast pruning)
HybridMutationPlanner                                   (scenario optimization)
EnemyPredictor                                          (lookahead)
```

---

## Build Types (7)

| ID | Type | Detection | Key Weights |
|----|------|-----------|-------------|
| 1 | **Strength** | Default fallback | burstDamage, weaponUses |
| 2 | **Magic** | MAG > STR + 100 | dotEffects: 500, poisonStacks: 400, weaponUses: 0 |
| 3 | **Agility** | AGI >= STR and AGI >= MAG | damageReturn, kiteDistance |
| 4 | **STR/Science** | STR >= MAG, STR >= AGI, SCI >= 200 | burstDamage, novaEffects |
| 5 | **Tank/SCI** | RES >= 300 and SCI >= 300 | shieldValue: 400, novaEffects: 400, healValue: 200 |
| 6 | **Hybrid** | abs(STR - MAG) < 100 | burstDamage: 200, dotEffects: 250 |
| 7 | **Bruiser/Reflect** | STR > 400 and AGI > 400 + reflect chips | damageReturn, burstDamage |

Detection priority: Tank/SCI > Bruiser/Reflect > STR/SCI > Magic > Hybrid > Agility > Strength

---

## Strategic States (6)

Determined per turn by `determineStrategicState()`:

| State | Condition | Behavior |
|-------|-----------|----------|
| **KILL** | Estimated damage >= 95% enemy HP, in weapon range | All-in damage, skip buffs |
| **AGGRO** | Early game, buffs expired, or late time-pressure | Buff → approach → attack |
| **ATTRITION** | Default combat, or kill suppressed (need approach) | Shield → heal → move → attack |
| **SUSTAIN** | HP 40-60%, enemy >40% HP, no time pressure | Conservative: heal + position |
| **FLEE** | HP < 40% | Emergency retreat + heal |
| **PUZZLE** | Boss fight crystal alignment phase | Crystal manipulation only |

### Time Pressure Override
- When `__timePressure` is true and turn > 30: forces ATTRITION (never sit back when drawing)
- When turn > 45 and enemy >50% HP: forces AGGRO

---

## Key Systems

### 1. Poison State Machine (Magic Builds)

```
BAIT → (enemy Antidotes) → SUSTAIN → (Antidote CD expires) → BAIT
BAIT → (5-turn timeout) → DUMP → SUSTAIN
```

- **BAIT**: Apply light poisons + denial to trigger enemy's Antidote
- **DUMP**: All-in poison when Antidote on cooldown (COVID, Arsenic, Plague, weapons)
- **SUSTAIN**: Maintain poison stacks, heal, position
- Checkpoint bonuses: POISON_DUMP +10,000 (mandatory), POISON_BAIT +4,000

### 2. Compound Effect Valuation

- **Poison duration compounding**: Longer-duration poisons score up to 3x more (7-turn COVID vs 2-turn chip)
- **Denial cascade**: TP/MP denial valued by ratio of enemy TP denied × enemy DPT × 3 turns; >50% denial = 1.5x multiplier
- **Vulnerability stacking**: Each Neutrino hit (8% vulnerability) valued as future damage amplification
- **Shield duration awareness**: FORTRESS (3 turns) scored higher than WALL (2 turns) in continuation value
- **Continuation value**: 35% discount factor for multi-turn buff/poison carry-forward

### 3. Draw-Breaking Escalation

Phased urgency when `__timePressure` is true:
- **Phase 1** (turns 10-30): urgency 1.0 → 1.8 (0.04/turn)
- **Phase 2** (turns 30-50): urgency 1.8 → 3.0 (0.06/turn)
- **Phase 3** (turns 50-64): urgency 3.0 → 7.5 (0.32/turn)

**Draw-breaking bonuses** when < 30 turns remaining:
- Nova damage × 5.0 (permanent HP reduction = draw breaker)
- Denial + 500 (deny enemy sustain)

**Stalemate detection**: Both sides >80% HP after turn 15 → triggers time pressure

### 4. 2-Ply Planning

For top 5 scenarios after scoring:
1. Project incoming damage from adversarial threat cache
2. Estimate HP after enemy response (death penalty: -2000 if HP ≤ 0)
3. Estimate next-turn damage potential from final position
4. Add active poison ticks (guaranteed future damage)
5. Add buff amplification bonus (buffs carry into next turn)
6. Apply at 40% discount

### 5. Adaptive Enemy Observation

Per-turn tracking per enemy:
- **HP trend** (EMA smoothed): detects if enemy is out-sustaining us
- **Shield frequency**: detects if enemy lacks defensive chips

**Weight adaptation** (after 5+ observations):
- Enemy HP trending up → boost burst ×1.3, denial ×1.5
- Enemy never shields → boost burst ×1.2, reduce shieldValue ×0.8

### 6. Counter-Strategy System (GA-tuned)

Weights adapted based on enemy profile:
- **vs Kiter**: boost distance, heal, DoT; reduce kiting
- **vs Burst**: boost shields, healing, threat awareness
- **vs Tank**: boost Nova ×1.64, denial ×1.30, DoT ×1.20
- **vs Reflect (active)**: reduce burst ×0.47, boost shields/healing
- **Cooldown windows**: boost burst when enemy shield/heal on CD

### 7. Adversarial Threat Cache

Precomputed for all reachable cells:
- Predicts enemy's maximum damage at each cell next turn
- Used by scorer for survival prediction and position penalty
- Death prediction: -8000 if EHP ≤ 0 at final position

### 8. Mutation System (4 types)

Applied to top 6 seed scenarios:
1. **Aim optimization**: Shift AoE target ±1 for splash coverage
2. **Swap**: Reorder adjacent actions for better sequencing
3. **Substitution**: Replace chip with same-type alternative
4. **Insertion**: Add unused available chips into gaps

### 9. Beam Search (Bottom-Up Discovery)

- Width 20, depth 10 action levels
- Diversity reserve: 14 best + 3 defensive + 3 utility
- Discovers novel action sequences not in templates
- Validates TP/MP, cooldowns, range, LoS

### 10. Boss Fight (Fennel King)

- **PUZZLE phase**: Align crystals to graal axes using GRAPPLE/BOXING_GLOVE
- **COMBAT phase**: Standard combat with `BOSS_COMBAT_WEIGHTS`
- Apocalypse guard blocks all damage during PUZZLE
- Mutations disabled during PUZZLE (position-critical)
- Weight hot-swap between phases

### 11. Battle Royale

- Lobby threat summation (all enemies)
- Kill bonus: +5000 per kill (reduce lobby size)
- AoE bonus: +1000 per additional enemy hit
- Center avoidance in early phase (>4 enemies alive)
- Phase transitions: early (edge play) → mid (tighten) → late (1v1 rules)

### 12. Bulb Targeting

- Classification: HEALER, BUFFER, ATTACKER
- Kill bonuses: Healer +2500, Buffer +1500, Attacker +800
- Bulb race clock: if summoner killable faster → ignore bulbs (0.3x damage)
- Summoning: Metallic (tank) when HP < 50%, Savant (support) otherwise

---

## Scoring Dimensions (23)

The scorer evaluates scenarios across these dimensions:

1. **Burst damage** — direct damage × stat-weighted multiplier
2. **Kill probability** — threshold scaling (≥70%: 5x, ≥50%: 2.5x)
3. **DoT damage** — poison with antidote-aware multiplier
4. **Poison compounding** — duration-weighted bonus
5. **Poison stacking** — multi-source bonus
6. **Nova damage** — Science-scaled Max HP reduction
7. **Vulnerability stacking** — future damage amplification
8. **Denial cascade** — TP/MP denial ratio × enemy DPT
9. **Shield value** — absolute + relative, resistance-scaled
10. **Healing value** — wisdom-scaled, urgency-multiplied
11. **Lifesteal** — wisdom-based healing from damage dealt
12. **Position** — offensive potential + kiting + threat + cover
13. **Adversarial threat** — survival prediction at final position
14. **TP efficiency** — damage per TP spent
15. **Buff value** — individual chip values × kill margin multiplier
16. **Debuff value** — poison/stat reduction scoring
17. **Crit bonus** — AGI-based critical hit expectation
18. **OTKO bonus** — +5000 for one-turn-kill positions
19. **Synergy matrix** — 9+ recognized combo patterns
20. **Continuation value** — multi-turn buff/position/poison carry-forward
21. **Time pressure** — phased escalation (draw-breaking)
22. **No-damage penalty** — -2000 to -14000 for 0-damage turns
23. **2-ply planning** — projected next-turn value

---

## File Map

| File | Lines | Purpose |
|------|-------|---------|
| `main.lk` | ~190 | Entry point, include order, per-turn loop |
| `scenario_combos.lk` | ~2634 | All scenario templates (20+ types) |
| `scenario_helpers.lk` | ~1474 | State detection, buff/heal/attack helpers |
| `item_database.lk` | ~1451 | Weapon + chip database |
| `scenario_scorer.lk` | ~1117 | 23-dimension scoring engine |
| `boss_context.lk` | ~1071 | Fennel King boss fight |
| `field_map_tactical.lk` | ~1005 | Threat maps, target selection, positioning |
| `beam_search.lk` | ~827 | Bottom-up action discovery |
| `field_map_patterns.lk` | ~792 | AoE pattern detection |
| `scenario_generator.lk` | ~585 | State-based scenario generation |
| `item.lk` | ~581 | Arsenal class, damage breakdown |
| `scenario_simulator.lk` | ~530 | Action simulation, effect projection |
| `scenario_mutation.lk` | ~520 | Aim/swap/substitute/insert mutations |
| `field_map_core.lk` | ~480 | Cell access, pathing |
| `tactical_awareness.lk` | ~449 | Adversarial threat cache, TP reservation |
| `strategic_depth.lk` | ~407 | Counter-strategy, weight adaptation, cooldown tracking |
| `weight_profiles.lk` | ~303 | 7 build profiles (23 weights each) |
| `enemy_predictor.lk` | ~287 | Enemy response lookahead |
| `scenario_quick_scorer.lk` | ~250 | Fast pruning heuristic |
| `enemy_intelligence.lk` | ~200 | Enemy profiling, adaptive observation |
| `game_entity.lk` | ~200 | Entity model (stats, effects, position) |
| `strategy/unified_strategy.lk` | ~575 | Main strategy + TP recovery |
| `strategy/base_strategy.lk` | ~3000 | Execution, AoE safety, poison baiting |
| `strategy/action.lk` | ~100 | Action class definition |
| **Total** | **~20,700+** | |
