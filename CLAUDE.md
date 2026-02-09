# LeekWars AI ? Multi-Paradigm Fix Plan

## Problem Statement

The AI (16,136 lines, 14M ops budget, 7 MP, 24?26 TP per turn) works well for **STR/WIS-AGI burst** builds but fails for two other paradigms:

| Leek | Build | Stats | Issue |
|---|---|---|---|
| **MargaretHamilton** | Magic / Poison / Sustain | 600 MAG, 500 WIS, 0 STR, 150 FREQ | AI treats her like a burst-damage leek, ignoring magic scaling |
| **KurtGodel** | STR / Science / Resistance Tank | 400 STR, 400 SCI, 400 RES, 400 WIS, 220 FREQ | AI plays him as pure Strength, ignoring Science/Nova win condition |

## Root Cause: Structural Bias

The AI was architected for a **Burst** paradigm where the win condition is immediate damage and kiting. Both Margaret and Kurt fail because the AI forces them into that same pattern.

### Three Identified Failures

1. **Build Detection Failure** ? `detectBuildType` is too narrow. Kurt (400 STR / 400 SCI) gets misclassified as pure Strength; Margaret (600 MAG) gets forced into weapon-based attack patterns.
2. **Weapon Bias** ? The "Best Attack" search prioritizes weapons. For Margaret (0 STR), this selects a ~10-damage weapon swing over a ~300-damage Meteorite chip.
3. **Scaling Errors** ? The internal simulator scales all direct damage by Strength, failing to account for Magic scaling on chips or Science scaling on Nova damage.

### Weapon Loadouts

#### MargaretHamilton (0 STR, 600 MAG)

| Weapon | Range | TP | Max/Round | Direct Damage | Special |
|---|---|---|---|---|---|
| **Destroyer** | 1?6 | 6 | 2 | 40?60 | Removes 17 STR for 2 turns (stackable) |
| **Flame Thrower** | 2?8 line | 6 | 2 | 35?40 | **Poison 24?30 for 2 turns** (stackable), AoE line |
| **Axe** | 1 | 6 | 2 | 55?77 | Removes 0.70?0.80 MP for 1 turn (stackable) |
| **Gazor** | 2?7 line | 8 | 2 | ? | **Poison 27?32 for 3 turns** (stackable), AoE circle 3 |

**Key insight:** Flame Thrower and Gazor deal **poison damage that scales with Magic, not Strength**. With 600 MAG, Margaret's poison weapons hit extremely hard. The AI must:
- Prioritize Flame Thrower and Gazor as **primary** weapons for Margaret ? their poison scales off her 600 MAG, making them far more effective than direct-damage weapons at 0 STR.
- Value Destroyer for its **STR debuff** (scales with Magic ? weakens enemy damage significantly at 600 MAG).
- Value Axe for **MP removal** (scales with Magic ? at 600 MAG the fractional MP removal becomes devastating).
- The simulator must use `poison = base * (1 + magic / 100)` for poison-dealing weapons, and `debuff = base * (1 + magic / 100)` for debuff effects, not `base * (1 + strength / 100)`.

##### MargaretHamilton Chips

| Chip | Range | TP | Cooldown | Effect |
|---|---|---|---|---|
| **Armoring** | 0?3 | 5 | 5 turns | +25?30 Max HP & heal |
| **Regeneration** | 0?3 | 8 | ? (once) | Restores 500 HP |
| **Remission** | 0?7 | 5 | 1 turn | Restores 66?77 HP |
| **Elevation** | 0?5 | 6 | ? (once) | +80 Max HP & heal |
| **Leather Boots** | 0?5 | 3 | 5 turns | +2 MP, 2 turns |
| **Knowledge** | 0?7 | 5 | 4 turns | +250?270 Wisdom, 2 turns |
| **Adrenaline** | 0?3 | 1 | 7 turns | +5 TP, 1 turn |
| **Wizardry** | 0?6 | 6 | 4 turns | +150?170 Magic, 2 turns |
| **Toxin** | 1?7 | 5 | 2 turns | Poison 25?35, 3 turns (stackable, AoE circle 2) |
| **Plague** | 1?5 | 6 | 4 turns | Poison 40?50, 4 turns (stackable, AoE circle 3) |
| **COVID-19** | 0?2 | 8 | 7 turns | Poison 69?79, 7 turns (propagates to neighbors ?2 cells at end of turn, non-replaceable) |
| **Arsenic** | 3?4 (through) | 8 | 2 turns | Poison 62?67, 2 turns (stackable) |
| **Soporific** | 1?6 | 5 | 1 turn | ?0.40?0.50 TP, 3 turns (stackable, AoE circle 3) |
| **Ball and Chain** | 1?6 | 5 | 2 turns | ?0.40?0.50 MP, 2 turns (stackable, AoE circle 2) |
| **Antidote** | 0?4 | 3 | 4 turns | Removes all poisons, restores 25?35 HP |
| **Grapple** | 1?8 line | 3 | ? (4/round) | Pulls target, +30?40 WIS, ?15?20 AGI (1 turn, stackable) |
| **Teleportation** | 1?12 (through) | 9 | 10 turns (1 initial) | Teleports, +15?20 Max HP to caster |

**Chip strategy for Margaret:** The loadout is a **poison stacking + denial** engine:

- **Poison arsenal (4 chips + 2 weapons = 6 poison sources):** This is Margaret's primary damage. The AI must calculate **total poison DPS across all active stacks**, not individual chip damage.
  - **COVID-19** is the highest-value single cast: 69?79 poison/turn for 7 turns = ~520 total damage, and it **spreads** to nearby entities. The AI must prioritize landing this.
  - **Arsenic** (62?67 for 2 turns) is the **burst poison** ? high per-turn but short. Best for finishing or when cooldowns align.
  - **Plague** (40?50 for 4 turns, AoE circle 3) and **Toxin** (25?35 for 3 turns, AoE circle 2) are the **sustain poison stackers**.
  - Combined with Flame Thrower and Gazor weapons, Margaret can have **6+ poison stacks ticking simultaneously**.

- **Wizardry is Margaret's Prism:** +150?170 Magic for 2 turns is a massive spike. The AI should **time poison dumps during Wizardry windows** ? if magic scaling applies to poison chip values, this amplifies everything.

- **Denial tools (Magic-scaled):** Soporific (?TP, stackable, spammable every turn) and Ball and Chain (?MP, stackable) both **scale with Magic**. At 600 MAG + Wizardry buff, these debuffs are devastating ? multiple Soporific stacks can strip most of an enemy's TP. The AI should weave these between poison applications ? **a poisoned enemy that can't move or attack is the ideal state**.

- **Survivability:** Armoring + Elevation (both permanent Max HP increases) should be cast early. Remission is the per-turn heal. Regeneration is the emergency button. With 500 WIS and Knowledge (+250 WIS), healing is heavily amplified.

- **Positioning:** Grapple pulls enemies into close range for COVID-19 (range 0?2) or Axe (range 1). Teleportation is the escape valve.

**Margaret's ideal turn sequence:**
1. Wizardry (if available) ? 2. COVID-19 / Plague / Arsenic (biggest available poison) ? 3. Gazor / Flame Thrower (weapon poison) ? 4. Soporific (deny TP) ? 5. Remission (heal if needed)

#### KurtGodel (400 STR, 400 SCI, 400 RES)

| Weapon | Range | TP | Max/Round | Direct Damage | Special |
|---|---|---|---|---|---|
| **Illicit Grenade Launcher** | 4?7 | 6 | 2 | 4×10 | Passive: +10% received poison as Science (permanent, stackable) |
| **Rhino** | 2?4 | 5 | 3 | 54?60 | ? |
| **Lightninger** | 6?10 star | 9 | 2 | 99?107 | AoE X 1 |
| **Quantum Rifle** | 5?10 | 10 | 1 | 68?75 | **68?75 Nova damage** (reduces enemy Max HP), AoE X 2 |

##### KurtGodel Chips

| Chip | Range | TP | Cooldown | Effect |
|---|---|---|---|---|
| **Armoring** | 0?3 | 5 | 5 turns | +25?30 Max HP & heal |
| **Regeneration** | 0?3 | 8 | ? (once) | Restores 500 HP |
| **Remission** | 0?7 | 5 | 1 turn | Restores 66?77 HP |
| **Transmutation** | 1?6 line | 8 | 9 turns | +40?44 Max HP (AoE square 1) |
| **Wall** | 0?3 | 3 | 3 turns | ?4?5% damage taken, 2 turns |
| **Fortress** | 0?3 | 6 | 4 turns | ?7?8% damage taken, 3 turns |
| **Leather Boots** | 0?5 | 3 | 5 turns | +2 MP, 2 turns |
| **Knowledge** | 0?7 | 5 | 4 turns | +250?270 Wisdom, 2 turns |
| **Prism** | 0?6 inv. star | 6 | 6 turns | +60 STR/WIS/AGI/RES/SCI/MAG, 2 turns |
| **Adrenaline** | 0?3 | 1 | 7 turns | +5 TP, 1 turn |
| **Liberation** | 0?6 | 5 | 5 turns | ?40% all effects |
| **Antidote** | 0?4 | 3 | 4 turns | Removes all poisons, restores 25?35 HP |
| **Grapple** | 1?8 line | 3 | ? (4/round) | Pulls target, +30?40 WIS, ?15?20 AGI (1 turn, stackable) |
| **Boxing Glove** | 2?8 line | 3 | ? (4/round) | Pushes target, +30?40 RES, ?10?15 STR (1 turn, stackable) |
| **Teleportation** | 1?12 (through) | 9 | 10 turns (1 initial) | Teleports, +15?20 Max HP to caster |

**Chip strategy for Kurt:** The chip loadout is built for **sustained tanking and positioning control**:
- **Survivability loop**: Fortress/Wall for damage reduction ? Armoring/Transmutation for Max HP growth ? Remission for per-turn healing ? Regeneration as a one-time emergency 500 HP burst.
- **Buff stacking**: Prism (+60 to all stats including Science) and Knowledge (+250 WIS) amplify both Nova damage and wisdom-based returns. **Prism turns are power spikes** ? the AI should time Quantum Rifle shots to coincide with Prism's +60 SCI.
- **Positioning**: Grapple (pull + WIS buff + AGI debuff) and Boxing Glove (push + RES buff + STR debuff) let Kurt control range while stacking defensive stats. The AI should use these to keep enemies in Quantum Rifle range (5?10) while debuffing their STR.
- **Anti-poison**: Antidote + Liberation give Kurt tools to cleanse DoTs, critical against poison-heavy opponents.
- **Adrenaline**: At only 1 TP cost, this gives +5 TP for burst turns ? the AI should combo this with Quantum Rifle (10 TP) + Rhino fills.

**Key insight:** Quantum Rifle is Kurt's **strategic centerpiece** ? it deals Nova damage that permanently reduces enemy Max HP, scaled by Science. The AI must:
- Prioritize Quantum Rifle usage **every turn** (1 use/round, 10 TP ? fits the budget).
- Use Rhino as the **TP-efficient filler** (5 TP, 3 uses/round) for remaining TP after Quantum Rifle.
- Recognize Illicit Grenade Launcher's passive as a **Science scaling engine** ? getting poisoned makes Kurt stronger.
- Use Lightninger situationally for AoE or when range forces it.
- The win condition is **attrition via Nova**: shield up, tank hits, and let Max HP drain close out the fight.

### Poison-Dealing Weapons ? AI Implications

The AI must tag weapons by **damage type** (`DIRECT`, `POISON`, `NOVA`, `DEBUFF`, `UTILITY`) and score them per build profile:

- **Poison weapons** (Flame Thrower, Gazor): **scale with Magic, not Strength**. Valued by `base * (1 + magic / 100)` × duration × remaining turns. Critical for Magic/Sustain builds ? with 600 MAG, Margaret's poison weapons deal 7× base values.
- **Nova weapons** (Quantum Rifle): valued by cumulative Max HP reduction. Critical for Tank/Science builds.
- **Debuff weapons** (Destroyer ? STR removal, Axe ? MP removal): **scale with Magic**. At 600 MAG, these debuffs are massively amplified ? the AI must value them by their strategic impact on the enemy's stats, not by their negligible direct damage.
- The `findBestAvailable` and Quick Scoring heuristics must weight these categories according to the detected build profile, not uniformly by Strength scaling.

### Additional Bugs

- **Antidote Tracking** ? `PREV_ENEMY_POISON` likely stores a boolean/1 instead of the actual duration, causing miscalculated poison dump timing on Margaret's build.
- **Nova Logic Missing** ? The Scenario Generator has no Nova-specific logic. For Kurt, Science-based Nova damage (reduces Max HP) is a primary win condition the AI doesn't recognize.
- **Quick Scoring Bias** ? The heuristic used to prune the search tree heavily weights Strength, so Science and Magic scenarios get discarded before simulation.

---

## Action Plan

### Phase 1: Build Detection & Weighting (Foundation) -- DONE

1. **Redefine `detectBuildType`** -- DONE
   - If `abs(STR - MAG) < 100` ? classify as **Hybrid** (BUILD_HYBRID = 6)
   - Add explicit Magic-primary detection (`MAG > STR + 100`)
   - Priority-ordered: Tank/Sci > STR/SCI > Magic-primary > Hybrid > Agility > Magic > Strength

2. **Add Tank Detection** -- DONE
   - If `Resistance > 300` AND `Science > 300` ? assign **BUILD_TANK_SCI** (= 5) profile

3. **Adjust Weight Profiles** -- DONE

   | Profile | Key Weights |
   |---|---|
   | **Magic** | `weaponUses: 0`, `dotEffects: 500`, `poisonStacks: 400`, `kiteDistance: 200` |
   | **Tank/Sci** | `shieldValue: 400`, `threatReduction: 300`, `novaEffects: 400`, `healValue: 200` |
   | **Hybrid** | `burstDamage: 200`, `dotEffects: 250`, `poisonStacks: 200` |

4. **Fix Action class field errors** -- DONE
   - Added `weapon = null` field to Action class (used by weapon swap in scenario_combos)
   - Removed dead `.damage`/`.description` reads from scenario_mutation clone function

### Phase 2: Fix Simulator Math (The "Lying" Problem) -- DONE

1. **Stat-Based Scaling** -- DONE
   - `getDamageBreakdown()` + `computeEffectsBaseDamage()`: `EFFECT_DAMAGE` now uses `isChip ? mag : str`
   - `EFFECT_POISON` already scaled with Magic (was correct)
   - `EFFECT_NOVA_DAMAGE` already scaled with Science (was correct)

2. **Nova Integration** -- DONE (was already correct)
   - `EFFECT_NOVA_DAMAGE` scales with `1 + science / 100` in both `getDamageBreakdown` and `computeEffectsBaseDamage`

3. **Fix Quick Scoring** -- DONE
   - Weapon damage estimates now scale by `(1 + STR/200)`, chip estimates by `(1 + MAG/200)`
   - Margaret's 600 MAG chip scenarios no longer pruned before simulation

4. **Buff Simulation Fixes** -- DONE
   - PRISM: now boosts `simMagic`, `simWisdom`, `simScience` (+60 all stats, was STR only)
   - WIZARDRY: added `simMagic += 160` (was completely untracked)
   - KNOWLEDGE: added `simWisdom += 260` (was completely untracked)
   - ELEVATION: added `hpGained += 80` (was untracked)

### Phase 3: Behavioral Logic -- DONE

1. **Margaret Fix** -- DONE
   - `findBestAvailableAttack`: added `weaponDamageMultiplier = 0.3` when `MAG > STR + 100` (poison weapons exempt)
   - Added `CHIP_SOPORIFIC` and `CHIP_BALL_AND_CHAIN` to damage chip lists (denial tools for MAG builds)
   - Added Magic build detection in `checkCriticalBuffsExpired` (Wizardry expiry triggers AGGRO)
   - Removed STR-only gate on `getDebuffAction` (Liberation now usable by all builds)
2. **Kurt Fix** -- DONE
   - New `createNovaAttritionScenario` in scenario_combos.lk: shields → Prism/Knowledge → heal → move → Nova weapon → filler → cover
   - Registered in AGGRO, ATTRITION, SUSTAIN scenario builders
   - New synergy bonuses: Prism+Shield (+300), Wizardry+Denial (+350), Poison+Denial (+300)
3. **Poison Fix** -- DONE
   - `PREV_ENEMY_POISON` now stores `target.getEffectRemaining(EFFECT_POISON)` (actual duration) instead of `1` (boolean)
   - Fixed `this._target` scope error: extracts target entity from executed actions in `executeScenario`

### Phase 4: Validation

- Test each build independently against known opponent archetypes.
- Confirm the burst build (STR/WIS-AGI) is **not regressed** after changes.
- Monitor ops budget ? ensure new logic paths stay within the 14M ops ceiling.
