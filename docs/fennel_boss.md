# Fennel King Boss — State of the System

*Last updated: 2026-07-17 (after ~20 real attempts on 2026-07-16/17).*
*All logic lives in `V8_modules/boss_context.lk`, hooked from `main.lk` (puzzle branch + COMBAT branch). Everything is gated on `_isBossFight` — zero ladder impact.*

---

## 1. Real fight mechanics (server-verified)

- **Roster**: Fennel King 10,000 HP · Scribe 6,000 · 4 Knights 4,000 · 2 Squires 2,000 · Graal 1,000 · 4 crystals **1 HP** · a wood chest (team 3). ~36,000 HP of killable army.
- **Divine Protection** (graal, T1, permanent): the whole army is **invulnerable except the crystals**. The army attacks freely during the puzzle (~2,500/turn focused). Damaging crystals at the graal's turn ⇒ **Apocalypse** (instant kill) — hence the blanket damage block in PUZZLE.
- **Puzzle**: push/swap crystals so each color's ray hits the graal's matching gem. The ray **passes through entities** (only obstacles block) — all beam LoS checks must ignore entities. Crystal spawns are **randomized per fight**, sometimes outside the castle walls.
- On the graal's turn with all crystals aligned it **casts "Tuer" on itself** → Divine Protection drops → COMBAT. **Crystals must also be killed to win.**
- **The army heals**: the scribe repairs ~1,000/turn (measured 1,763–3,691/fight) and the king self-heals (~450–1,100). One attacker is at heal-parity with the scribe. **Kill order: scribe → squires → knights → king last.**
- The king wields Excalibur (heavy damage + strong poison) — antidote matters.

### Engine facts that bit us (all verified in generator source)
| Fact | Consequence |
|---|---|
| GRAPPLE/BOXING are `FIRST_IN_LINE` area: the cast cell is the slide **destination**; the first entity in line slides to it | Cast at the future cell; verify LoS to the crystal at cast time or you drag a knight onto yourself |
| Boxing min range 2: standing adjacent to the crystal makes it block LoS (cast → -4) | Boxing stands must be ≥2 from the crystal |
| Grapple/boxing deal **zero damage** (secondary effects are caster self-buffs) | They're pure displacement — crystals die to real damage chips |
| INVERSION (range 14, line, real LoS) **swaps caster and crystal** | Wall-jump tool for the solver; mid-route swaps drop the solver on the crystal's old cell — army-safety gated |
| COVID = poison 69 ×7 turns + **PROPAGATION 2** (`Entity.java:806`): re-infects everything within 2 every turn, chains onward | The epidemic payload (~3,400/unit at MAG 600) |
| PLASMA is `MULTIPLIED_BY_TARGETS` + STR-scaled | ~1,500–3,000 into a 3–4 cluster at 410–500 STR |
| Heals scale with caster **WIS**; vitality buffs (elevation/armoring) scale with caster **WIS** (not SCI); shields scale with caster **RES** (1+RES/100); TP/MP buffs scale with caster **SCI** | Drives all respec math below |
| `getCooldown(chip)` returns 0 for **unequipped** chips | Equipment checks must use `inArray(getChips(e), chip)` (`allyHasChip`) |
| `getAliveAllies()` **includes self**; summons inherit summoner stats | Dedupe self in ally loops; exclude summons from carrier counts |
| Dead graal can linger in entity queries with valid name/cell/life | Phase flip uses `isAlive(id)` + Divine-Protection sweep (effect 59 on army) + one-way COMBAT latch |
| `getLeekOnCell` removed in LS4 | Use `getEntityOnCell` |

---

## 2. Current squad configuration

**Main (Virus)** — all boss respecs are reversible; *respec Ada + KG back to STR for ladder play when done boss-hunting*:

| Leek | Build (base) | Boss role |
|---|---|---|
| **AdaLovelace** | STR 0 / WIS 310 / RES 420 / MP 8 / life 2,465 (totals: 3,145 HP, RES 500, MP 9) | **Solver-tank** (grapple+boxing+inversion), phase-2 peeler |
| **KurtGodel** | STR 410 / SCI 500 (ladder build) + grapple/boxing/inversion + **plasma** | **Second solver**, phase-2 STR striker |
| **EdsgerDijkstra** | STR 500 (user-tuned) + **plasma** | T1 spawn-range buffer → scatter; phase-2 striker (plasma + enhanced lightninger) |
| **MargaretHamilton** | MAG 600 + **covid**/plague/toxin/venom/arsenic + gazor/flame thrower | **Poison carry**: dump-dive doctrine |

**Cure (level 150 — too low for covid/plasma)**: LeekRain + DawnFall (MAG 440, venom+toxin → secondary dumpers), DuskHope (escort), ProdigalSon (STR 480 → striker w/ grenade launcher). Join via cross-farmer boss lobby (up to 8 leeks).

---

## 3. The doctrine (as implemented)

### Phase 1 — PUZZLE (survival race, damage blocked)
1. **Dual solvers** (Ada + KG by name, self-verified puzzle chip). Coordinate crystal claims via real messages (`sendAll MESSAGE_CUSTOM [901, eid]`) — no duplicated work; only converge on the last crystal. Solo fallback proven (Ada finished alone 3×).
2. **Buff wave T1-2**: escorts hold a 2-3 band (never adjacent — blocking), deliver elevation/armoring; STR carries (ED/ProdigalSon) cast range-5 buffs **from spawn** at their **nearest** solver, then scatter forever. Solvers wait T1-2 (extend T3 only for ≥400 gain), drift ≤3/turn under pressure, then solve.
3. **Solving**: BFS route planner over crystal slides + inversion edges (routes around castle walls); route/target commitment (anti-thrash); pin-escape teleport; cast-time LoS guards; proactive shield rotation + antidote; emergency regen <40%.
4. **Everyone else scatters** (army-distance-dominant kiting, work-zone no-go areas). Proven: multiple 40–64-turn survivals. If both solvers die → no chipless fallback → all scatter → draw insurance.
5. MAG carriers **never spend teleport in the puzzle** (banked for the phase-2 dive).

### Phase 2 — COMBAT (after graal suicide; hardened triple-signal phase flip)
- **Kill priority**: scribe +60 → squires +25 → knights 0 → **king −125** (soft veto: only when nothing else is reachable — he heals back 82% of pokes).
- **Poison carriers (MAG ≥ 300)** — *dump-then-sustain with coordinated strike quorum*:
  - Broadcast READY (`[903, turn]`) when their own equipped big-chip kit (covid/plague/toxin/arsenic, scaled to what they own) is up; **hold/bank** otherwise (only venom + weapons fire while holding).
  - Strike when `ready ≥ min(2, MAG carriers alive)`: teleport **dive** at the scribe's cluster (or the scribe alone), unload everything point-blank, then sustain-kite while it ticks.
  - Movement: poke orbit by **path length** (manhattan lies around walls), approach the **engagement** (army units near an ally are committed/reachable), firing-position bonus for cells with real LoS.
- **STR strikers (STR ≥ 300)**: same orbit; plasma on 2+ clusters, double ranged weapon (stat-aware table: enhanced lightninger / rifle / grenade launcher / magnum / destroyer; MAG carriers use gazor/flame thrower/double gun) from the 6-10 band. Never engage via the normal pipeline (one turn of damage for a life).
- **Peelers (STR < 150 + boxing, i.e. tank-Ada)**: no-cooldown boxing pushes peel the army off the carry, crystal swats (any damage chip kills the 1-HP crystals), carry heals, bodyguard positioning.

---

## 4. Where it stands

**Server-proven**: puzzle completion under fire (graal died T7–T10 in 5 fights), dual + solo solving, phase flip, crystal cleanup, scatter survival (multiple 40–64-turn runs), dive→dump (4,201 poison into the scribe in one fight), peels, scribe-focused casting.

**The remaining gate**: solver survival in T3–T7 (~50% per fight — decided by army alpha-target choice and crystal layout).

**Fight 52983075 (2026-07-17) — the milestone**: puzzle T7, coordinated strike ran live: dive T10 + five dump turns → **scribe DEAD T14** (9,079 in vs 2,599 healed — treadmill broken), **22,041 total into the army** (~10× any prior fight, >60% of its pool), sustained 1,000–2,700/turn through T22. Loss at T27 with ~14k army HP left — ran out of bodies one phase early. The system is win-capable; a modestly better focus-RNG run of the same fight closes it.

**Win path**: puzzle completes (~50%) → banked quorum strike kills the scribe (~6k HP vs 2,500–3,500/turn overlapping dumps) → permanent poison attrition on a cureless army → squires/knights → king last.

**Sandbox reference results** (local, weaker fighter-bot army — directional only):
4-leek: 10 dumps, scribe dead T23, full 8/8 clear T29, zero deaths. 8-leek: 22 coordinated dumps, scribe T25.

---

## 5. Runbook

```bash
# Local puzzle regression (3 known layouts; local map IS the real castle)
python3 tools/local_test.py 1 boss_fennel            # standard template
# hard layouts: override boss_entities cells with a real fight's data.leeks cellPos
# (fight 52975331 geometry: graal 102, red 218, blue 341, green 364, yellow 304)

# Phase-2 sandbox (graal-less → starts in COMBAT; detectBossFight accepts fennel_king)
# scenario cached at /tmp/phase2_scen.json during sessions; rebuild pattern in git log 395d0ed3

# After ANY .lk edit: clear the generator compile cache, then test
rm -f /home/ubuntu/leek-wars-generator/ai/*.class /home/ubuntu/leek-wars-generator/ai/*.java /home/ubuntu/leek-wars-generator/ai/*.lines

# Deploy to BOTH accounts (Cure leeks must have main.lk assigned)
# MCP: leekwars_upload_v8 {account: main} + {account: cure}

# Fight analysis: /fight/get/<id> authenticated (fights with trophies 409 otherwise);
# says carry the diagnostics: B1 (phase/role/graal state), PZ DONE/INV (solve),
# PZ DUMP/DIVE/POKE none (phase 2), PZQ (strike quorum), PZDBG (cast failures)
```

**Reading a fight log quickly**: `B1 PH=... G=<id>/<alive>/<life>/<cell>` every leek turn; `PZ SOLVER: waiting/closing`, `PZ DONE c=X`, `PZ SOLVER: all done` (puzzle); graal death + `PH=COMBAT` (flip); `PZ POKE none d= tp= mp=` (carrier blocked — check distances), `PZ DUMP xN` / `PZ DIVE` (strikes landing).

## 6. Open items

- The coordinated strike has never run in a completed-puzzle real fight — first priority to observe.
- Solver survival is the binary gate; all known levers deployed. Residual ideas (unimplemented): sacrificial bodyguard during T3-6, solver wait relocation beyond drift.
- Ladder cleanup owed: Ada (STR 0) and KG carry boss-specialist specs/chips.
