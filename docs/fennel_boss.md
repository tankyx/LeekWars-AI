# Fennel King Boss — State of the System

*Last updated: 2026-07-17 (after the 17-fight iteration day: fights 52984011 → 52984811).*
*All logic lives in `V8_modules/boss_context.lk`, hooked from `main.lk` (puzzle branch + COMBAT branch). Everything is gated on `_isBossFight` — zero ladder impact.*

---

## 1. Real fight mechanics (server-verified)

- **Roster**: Fennel King 10,000 HP · Scribe 6,000 · 4 Knights 4,000 · 2 Squires 2,000 · Graal 1,000 · 4 crystals **1 HP** · a wood chest (team 3). ~36,000 HP of killable army.
- **Divine Protection** (graal, T1, permanent): the whole army is **invulnerable except the crystals**. The army attacks freely during the puzzle (~2,500/turn focused). Damaging crystals at the graal's turn ⇒ **Apocalypse** (instant kill) — hence the blanket damage block in PUZZLE.
- **Puzzle**: push/swap crystals so each color's ray hits the graal's matching gem. The ray **passes through entities** (only obstacles block) — all beam LoS checks must ignore entities. Crystal spawns are **randomized per fight**, sometimes outside the castle walls.
- On the graal's turn with all crystals aligned it **casts "Tuer" on itself** → Divine Protection drops → COMBAT. **Crystals must also be killed to win.**
- **The army heals**: the scribe repairs ~200-1,000/turn (3,170 into himself alone in fight 52984546) and the king self-heals. **Kill order: scribe → squires → knights → king last.**
- The king wields Excalibur (heavy damage + strong poison) — antidote matters.
- **The army alpha**: focused output on one target is 2,300–2,700/turn from ~3 units. A buffed solver (~4,300 maxHP) dies inside two focused turns. The alpha targets whoever is reachable in the approach corridor — 5 of our 8 leeks spawn in the 490–590 block, straight down the army's opening walk.
- The graal itself occasionally attacks (~250-320/turn observed).

### Engine facts that bit us (all verified in generator source or fight data)
| Fact | Consequence |
|---|---|
| GRAPPLE/BOXING are `FIRST_IN_LINE` area: the cast cell is the slide **destination**; the first entity in line slides to it | Cast at the future cell; verify LoS to the crystal at cast time or you drag a knight onto yourself |
| Boxing min range 2: standing adjacent to the crystal makes it block LoS (cast → -4) | Boxing stands must be ≥2 from the crystal |
| Grapple/boxing deal **zero damage** (secondary effects are caster self-buffs) | They're pure displacement — crystals die to real damage chips |
| INVERSION (range 14, line, real LoS) **swaps caster and crystal** | Wall-jump tool for the solver; mid-route swaps drop the solver on the crystal's old cell — army-safety gated |
| COVID = poison 69 ×7 turns + **PROPAGATION 2** (`Entity.java:806`): re-infects everything within 2 every turn, chains onward | The epidemic payload (~3,400/unit at MAG 600) — must be the FIRST chip cast in a dump (see §4) |
| PLASMA is `MULTIPLIED_BY_TARGETS` + STR-scaled | Each target takes dmg × targets hit: a 3-cluster at STR 270 ≈ 1,250 total for 9 TP |
| Heals scale with caster **WIS**; vitality buffs scale with caster **WIS**; shields scale with caster **RES** (1+RES/100); TP/MP buffs scale with caster **SCI**; damage always **STR** | Drives all respec math below |
| `getCooldown(chip)` returns 0 for **unequipped** chips | Equipment checks must use `inArray(getChips(e), chip)` (`allyHasChip`) |
| `getAliveAllies()` **includes self**; summons inherit summoner stats | Dedupe self in ally loops; exclude summons from carrier counts |
| Dead graal can linger in entity queries with valid name/cell/life | Phase flip uses `isAlive(id)` + Divine-Protection sweep (effect 59) + one-way COMBAT latch |
| `getLeekOnCell` removed in LS4 | Use `getEntityOnCell` |
| `moveTowardCell(<occupied cell>)` can silently move ZERO (destination = crystal's own cell) | Walk toward crystals via `solverWalkToward` (falls back to reachable cell minimizing remaining distance). Fight 52984811: both solvers stalled at constant distance for 6–30 turns |
| `say()` output beyond the first per turn can be dropped | Diagnostics: put the load-bearing marker first |
| Current-HP triggers can't catch between-turn burst | The alpha lands between the victim's turns — escape logic must project incoming focus, not read own HP |

---

## 2. Current squad configuration

**Main (Virus)** — all boss respecs are reversible; *Ada's ladder restore: base STR 520 / WIS 310 / RES 220 / MP 6 / life 2,045 / TP 20 (= exactly 1,780 capital)*:

| Leek | Build (totals) | Boss role |
|---|---|---|
| **AdaLovelace** | STR 240 / WIS 500 / RES 400 / HP 3,325 / TP 25 / MP 8 · bazooka + enhanced lightninger + m_laser + heavy sword · plasma + full solver & guardian kit | **Solver-tank** (grapple+boxing+inversion) → phase-2 **guardian-with-teeth** (top damage 3,919 in fight 52984546). Keep total STR < 300 or she flips to the striker orbit |
| **KurtGodel** | STR 410 / SCI 500 / RES 300 (ladder spec) + solver kit + plasma | **Second solver** — the proven solo finisher (4 crystals by T8 in 52984073), phase-2 STR striker |
| **EdsgerDijkstra** | STR 500 / AGI 490 + mirror/thorn/bramble (bruiser) + plasma | T1 spawn-range buffer → scatter; phase-2 striker |
| **MargaretHamilton** | MAG 600 / HP 3,390 / TP 26 + covid/plague/toxin/arsenic/venom + teleport + gazor/flame thrower/double gun | **Poison carry**: dive → covid-first dump → recovery retreat → repeat |

**Cure (level 150 — too low for covid/plasma)**: LeekRain + DawnFall (MAG 440, toxin+venom → secondary dumpers), DuskHope (support), ProdigalSon (STR 480 striker). Join via cross-farmer boss lobby (8 leeks). All 8 leeks run `main.lk`.

---

## 3. The doctrine (as implemented)

### Phase 1 — PUZZLE (survival race, damage blocked)
1. **Exposed-spawn wait bypass**: solvers skip the buff wait entirely when the army is within distance 15 at T1-3 (`PZ SOLVER: skip wait, army d=N`) — self-buff and solve on the move. Waiting bought ~1,000 maxHP against a 2,500/turn alpha and killed Ada T4-5 in four straight fights. Waiting is preserved for safe spawns (army > 15).
2. **Landing-zone teleport rule**: the route teleport fires only onto **cold** stands (nearest army > 10) — a cold jump keeps tempo AND escapes the hunt. Hot stands → walk (`solverWalkToward`, never the raw crystal cell) with teleport banked.
3. **Emergency blink** (`puzzleEmergencyBlink`, `PZ BLINK dN`): shared escape for solvers and the scatter path. Triggers on **projected focus** — 3+ army units within reach 9 = jump at any HP; fewer units = jump when life < 900 × units. +3 distance gain minimum. Runs BEFORE the shield rotation (which could starve its 9 TP). Server-proven: 4 blinks in each of fights 52984808/811, KG survived to T16+/T64.
4. **Dual solvers** (Ada + KG) with message crystal claims (`[901, eid]`); solo fallback repeatedly proven (KG finished alone 4×). Escorts hold the 2-3 band, STR carries buff from spawn then scatter forever.
5. **Solving**: BFS route planner over crystal slides + inversion edges; route/target commitment; cast-time LoS guards; proactive shield rotation + antidote.
6. Everyone else scatters (army-distance-dominant kiting). If both solvers die → all scatter → draw insurance (held twice: 52984415, 52984808).
7. MAG carriers bank teleport for the phase-2 dive — but the emergency blink overrides: dying with the chip is strictly worse (fight 52984207: MH dead T4, teleport unused, phase 2 toothless).

### Phase 2 — COMBAT (after graal suicide; hardened triple-signal phase flip)
- **Kill priority**: scribe +60 → squires +25 → knights 0 → **king −125** (soft veto; covid exempt).
- **Scribe-kill sprint**: when the scribe drops below 45% HP, the approach commit overrides to HIS cell for every striker/carrier — he out-healed 70% of our input in 52984546 and survived at ~2,650/6,000 while the team died around him. His death permanently breaks the treadmill.
- **Poison carriers (MAG ≥ 300)** — *strike-cycle doctrine*:
  - Coordinated strike quorum (`[903, turn]`): hold the big four until `ready ≥ min(2, MAG carriers alive)`.
  - **Dive**: teleport to ring 1 of the scribe's cluster (ring-2 fallback when ring 1 is beyond range 12 — a delayed dive cost 3 full-TP idle turns in 52984012).
  - **Dump in value order: COVID → arsenic → plague → toxin → venom.** Range-order casting let the cheap chips starve covid's 8 TP after the 9-TP teleport (52984012: the dive delivered 430 of one-shot poison instead of the ~3,400/unit epidemic).
  - **Recovery retreat**: big kit all on cooldown → blink if focused, run to army distance 18, return when the kit is up. Standing at venom range during cooldowns killed MH the turn after her dumps (52984301/305). Sandbox: the cycle *increased* total dumps (24) and cleared with zero deaths.
- **STR strikers (STR ≥ 300)**: poke orbit; plasma on 2+ clusters; stat-aware weapon table covering ALL equipped variants (illicit GL, plain lightninger, quantum rifle, unstable destroyer, rhino — a missing variant makes its carrier a spectator).
- **Guardian (STR < 300 + boxing, i.e. tank-Ada)**: carry antidote-cleanse/heals/shields, crystal swats, then **shoots** — plasma on in-range clusters (no chasing), bazooka/lightninger/m_laser from the guard post, heavy sword point-blank (her only sub-range-5 option). `PZ GUARDSHOT xN` / `PZ GUARD plasma`. Weapons before peel pushes — damage beats displacement.

---

## 4. Where it stands (end of 2026-07-17)

**Server-proven**, each in real fights:
- Puzzle completion **T5–T8** whenever a solver survives the opening (graal died T5 in 52984301 — fastest ever; T6-T8 in five other fights).
- Solo-solve under fire (KG 4×, including 4 crystals by T8), dual-solve, crystal cleanup.
- Emergency blink + walk fallback: solvers now survive to T15-T64 in the fights where they used to die T4-7.
- Dive → covid-first dump (`DUMP x4/x5` back-to-back), strike quorum, secondary dumpers.
- Guardian-with-teeth: Ada topped the team damage chart (3,919) in 52984546.
- Draw insurance: two 64-turn draws from solver-wipe branches.

**Best fight (52984546)**: puzzle T8, 9,160 into the army at **509/turn** (previous ~300), scribe at ~2,650/6,000 when the team ran out of bodies — two focused turns from breaking the heal treadmill.

**The remaining wall**: phase-2 attrition. The army (36k HP, 2,500/turn output) runs our leeks down one by one from T8 onward; output caps at 4–9k. The win needs the scribe dead (sprint now deployed, untested live) and then sustained poison cycles on a cureless army. Levers not yet pulled: KG's desintegration (nova, SCI 500) in the striker rotation; Cure leeks leveling into covid; a second dive cycle actually completing (recovery retreat is deployed, untested live).

**Iteration method that worked all day**: every fight trace converted one structural death cause into a system — read the says (`skip wait` → `BLINK` → `DONE` → `DIVE` → `DUMP` → `GUARDSHOT`), find the leek that died with a tool unused, fix that.

---

## 5. Runbook

```bash
# Local puzzle regression (multi-seed; local map IS the real castle, but has NO army —
# threat-gated paths (skip-wait, blink, landing-zone rule) do NOT exercise locally)
python3 tools/local_test.py 1 boss_fennel --seed 12345
python3 tools/local_test.py 1 boss_fennel --seed 777

# Phase-2 sandbox (graal-less → starts in COMBAT; 8 fennel-named fighter bots + 1-HP crystals)
# scenario at /tmp/phase2_scen.json — re-stamp entity stats from tools/leek_configs.json
# after any respec (weapons must be converted item-id → weapon-id via weapons.json)
cd /home/ubuntu/leek-wars-generator && java -cp $(cat runtime_classpath.txt) com.leekwars.Main /tmp/phase2_scen.json
# Reference (real builds): 12 kills / 37 turns / zero deaths / 24 dumps

# After ANY .lk edit: clear the generator compile cache, then test
rm -f /home/ubuntu/leek-wars-generator/ai/*.class /home/ubuntu/leek-wars-generator/ai/*.java /home/ubuntu/leek-wars-generator/ai/*.lines

# Rebuild the Python port after any .lk change
python3 tools/lk2py.py --check

# Deploy to BOTH accounts (Cure leeks must have main.lk assigned)
# MCP: leekwars_upload_v8 {account: main} + {account: cure}

# After a user respec: refresh configs, then re-stamp the sandbox scenario
python3 tools/fetch_leek_configs.py
```

**Reading a fight quickly** (fetch `/fight/get/<id>` authenticated; says are action code **203**, attributed via the last LEEK_TURN code 7; `USE_CHIP` raw is `[12, marker, cell, result]` — ground truth for chip identity is the 302 effect rows `[302, chip_db_id, ...]`):
- `B1 PH=... G=<id>/<alive>/<life>/<cell>` every leek turn.
- Puzzle: `PZ SOLVER: skip wait, army d=N` → `closing on c=X d=N` (d must DECREASE — constant d = the walk stall) → `PZ BLINK dN` → `PZ DONE c=X` → graal death → `PH=COMBAT`.
- Phase 2: `PZQ` (quorum, debug only), `PZ DIVE c<score>` → `PZ DUMP xN` → recovery silence → second dive; `PZ GUARDSHOT xN` / `PZ GUARD plasma` (Ada); `PZ POKE none d= tp=` = carrier blocked, check distances.
- Damage audit: sum 101/110 actions into fennel-named victims; healing = 103 rows. Compare vs the scribe's repair to see if the treadmill broke.

## 6. Open items

- **Scribe-kill sprint and recovery retreat are deployed but unobserved live** — first thing to check in the next fights.
- Walk-stall fix (52984811) deployed but unobserved — verify `closing` distances decrease.
- Phase-2 damage ceiling: if fights still cap at ~9k with the sprint live, add KG's desintegration (nova ~400/cast at SCI 500) to the striker rotation, and consider a second-dive cycle audit.
- Crystals spawning outside the castle walls may be walk-unreachable pockets — `solverWalkToward` mitigates but inversion-only access is untested.
- Ladder cleanup owed when the campaign pauses: Ada respec restore (numbers in §2), remove boss chips from KG if slots are needed.
