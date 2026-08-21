# Fennel King Boss — State of the System

*Last updated: 2026-07-17 evening (fight 52984834: graal-alive wipe — KG frozen 17 turns in a manhattan-lure cul-de-sac; path-aware walk fix verified locally).*
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
- **The iron chest (team 3) is a live hazard**: it attacks entities in range — *including crystals* (fight 53011171: chest killed red_crystal at T2 → graal Apocalypse wiped all 8 leeks + the chest at T3). Environmental RNG, not caused by us; killing the chest preemptively costs more than the ~1-in-15 catastrophe rate. Not worth counter-play.

### Engine facts that bit us (all verified in generator source or fight data)
| Fact | Consequence |
|---|---|
| GRAPPLE/BOXING are `FIRST_IN_LINE` area: the cast cell is the slide **destination**; the first entity in line slides to it | Cast at the future cell; verify LoS to the crystal at cast time or you drag a knight onto yourself |
| Boxing min range 2: standing adjacent to the crystal makes it block LoS (cast → -4) | Boxing stands must be ≥2 from the crystal |
| Grapple/boxing deal **zero damage** (secondary effects are caster self-buffs) | They're pure displacement — crystals die to real damage chips |
| INVERSION (range 14, line, real LoS) **swaps caster and crystal** | Wall-jump tool for the solver; mid-route swaps drop the solver on the crystal's old cell — army-safety gated |
| **The graal is immovable** — it sits on a non-walkable pedestal cell (0 MP), and every cast whose LoS passes through or ends at that cell fails (`canUseAttack` → `isWalkable` check). Verified three ways live in sandbox: inversion/boxing/grapple on the graal all return invalid-position (-4) | The goal geometry follows its live cell each turn (`_graalX/_graalY` recomputed), but it never changes — don't build anything on moving the graal |
| COVID = poison 69 ×7 turns + **PROPAGATION 2** (`Entity.java:806`): re-infects everything within 2 every turn, chains onward | The epidemic payload (~3,400/unit at MAG 600) — must be the FIRST chip cast in a dump (see §4) |
| PLASMA is `MULTIPLIED_BY_TARGETS` + STR-scaled | Each target takes dmg × targets hit: a 3-cluster at STR 270 ≈ 1,250 total for 9 TP |
| Heals scale with caster **WIS**; vitality buffs scale with caster **WIS**; shields scale with caster **RES** (1+RES/100); TP/MP buffs scale with caster **SCI**; damage always **STR** | Drives all respec math below |
| `getCooldown(chip)` returns 0 for **unequipped** chips | Equipment checks must use `inArray(getChips(e), chip)` (`allyHasChip`) |
| `getAliveAllies()` **includes self**; summons inherit summoner stats | Dedupe self in ally loops; exclude summons from carrier counts |
| Dead graal can linger in entity queries with valid name/cell/life | Phase flip uses `isAlive(id)` + Divine-Protection sweep (effect 59) + one-way COMBAT latch |
| **Buffs do not apply to summons** (verified sandbox AND live 53019207/209: adrenaline on the bulb cast ok=1, zero effect row, TP unchanged; self-cast covetousness same) | Never TP-boost a bulb — the tactician's teleport (cost 9 > its 7 TP) is unreachable; mobility is JUMP chains. Don't re-add boost attempts: they waste TP and a cooldown every time |
| `getLeekOnCell` removed in LS4 | Use `getEntityOnCell` |
| `moveTowardCell(<occupied cell>)` can silently move ZERO (destination = crystal's own cell) | Walk toward crystals via `solverWalkToward` (falls back to reachable cell minimizing remaining distance). Fight 52984811: both solvers stalled at constant distance for 6–30 turns |
| `getPathLength` treats **entities as blockers** — returns null when every route is body-walled; manhattan-greedy walking is a cul-de-sac lure (cell can be manhattan-close with the real path wrapping a castle wall) | Score walk/teleport candidates by real path (`getPathLength`), never manhattan alone; when the target region is entity-sealed, still move (manhattan-closest reachable cell) and re-evaluate next turn. Fight 52984834: KG frozen 17 turns at cell 55 saying `closing on c=12 hot d=11`, wipe with graal alive |
| Memoryless walk scoring **ping-pongs** (fights 53009902/918: KG 38↔20 ×10 turns, Ada 472↔489 ×9 — movement, zero progress) | `_walkVisited` penalizes cells stood on in the last 6 turns: the solver sweeps the pocket instead of bouncing, catching any gap the turn the army shifts |
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
2. **Landing-zone teleport rule**: the route teleport fires only onto **cold** stands (nearest army > 10) — a cold jump keeps tempo AND escapes the hunt. Hot stands → walk (`solverWalkToward`, never the raw crystal cell) with teleport banked. Both the walk fallback and the teleport-stand ranking score by **real path distance** (`getPathLength`), not manhattan — fight 52984834: the manhattan-greedy fallback lured KG into a cul-de-sac behind a castle wall (cell 55, every exit manhattan-worse) and froze him 17 turns; and when the army body-walls every route (proxy unresolvable), the walk still moves to the manhattan-closest reachable cell instead of standing still. **Graceful degradation**: after 3 consecutive hot-walk turns without beating the BEST distance (`_hotNoProg`), the cold rule relaxes from >10 to >5 — walking under fire is losing anyway (fight 53010589: KG herded 14→20, dead T13, teleport banked). Best-distance tracking, not last-turn: an oscillating d 8↔12 resets a last-turn counter forever while never converging (fight 53011918: 14 turns at d 8-12, relaxed teleport never armed).
3. **Emergency blink** (`puzzleEmergencyBlink`, `PZ BLINK dN`): shared escape for solvers and the scatter path. Triggers on **projected focus** — 3+ army units within reach 9 = jump at any HP; fewer units = jump when life < 900 × units. +3 distance gain minimum. Runs BEFORE the shield rotation (which could starve its 9 TP). Server-proven: 4 blinks in each of fights 52984808/811, KG survived to T16+/T64.
4. **Inversion escape** (`puzzleInversionEscape`, `PZ INV-ESC dN`): teleport's 10-turn cooldown vs the king's ~3-turn kill envelope left a fatal gap — KG died T7 two turns after blinking, Ada T11 eight after, both with teleport on cooldown (fight 53010428). When the blink can't fire and the focus projection is lethal (2+ hunters in reach 9, or life < 2,200 — the king's solo Excalibur envelope), swap with the focus crystal (cooldown 4) — but only if its cell is ≥4 farther from the army: never dive into the hunt zone to escape it. Server-proven T7 in 53010541 (KG escaped → solved 2 crystals in the next 4 turns).
5. **Approach inversion** (`PZ INV-APPROACH c=X`): the same swap used *deliberately* — when the stall is armed (3+ no-beat hot turns) OR opportunistically whenever the crystal is in range 14 with LoS and its cell isn't a kill zone (army ≥ 6). The crystal slides backward (re-pushable — and the solver lands on the goal side, perfectly placed for grapple); the solver arrives TODAY instead of in 4 turns. The 53011079/53013437 pattern turned into doctrine. The puzzle is ~20% execution, ~80% arrival — every solve of the campaign had arrival ≤ T10.
6. **Early relaxed teleport**: the cold-stand rule (>10) relaxes to >5 from **T4 routinely** (not just after a stall) — one shield turn, then the dive onto a stand at army d 6-10 with decoys soaking and INV-ESC/blink covering. Watch for the 52984720 shape (T2 mid-castle landing, dead T3-7) — the T4 gate is designed to stay clear of it.
7. **Enemy-swap taxi** (`puzzleEnemySwapApproach`, `PZ INV-TAXI g=N`): inversion on the hunt's isolated spearhead (< 2 army within 3) when the swap lands the solver ≥5 cells closer to the focus crystal. Their aggression is our mobility: solver rides forward, the hunter taxis backward into empty backfield and walks all the way back — and unlike the crystal swap, the crystal doesn't slide back. Fires before INV-APPROACH when the trade is good.
5. **Dual solvers** (Ada + KG) with message crystal claims (`[901, eid]`); solo fallback repeatedly proven (KG finished alone 4×). Escorts hold the 2-3 band, STR carries buff from spawn then scatter forever. **Focus abandonment**: the sticky focus is banned for 10 turns after 8 turns without beating its best distance (`PZ RETARGET c=X`) — fight 53010703: KG held c=12 for 32 turns at d 16-24 (army-walled corridor) while c=10 sat solvable; the escape swap that finally moved him onto c=10 solved it in one turn. **Only when truly walled out (best d ≥ 10)** — fight 53013148: Ada reached best d=3, couldn't complete the push in the crowd, and the ban walked her away from the best position of the fight; at d < 10 it's a work problem, not an approach problem — stay and grind.
5. **Solving**: BFS route planner over crystal slides + inversion edges; route/target commitment; cast-time LoS guards; proactive shield rotation + antidote. **PIN fallback** (`PZ INV-PUSH c=X`): when the slide stand is body-blocked (why=PIN) and the solver's cell is on the goal side, inversion-swap the crystal toward its goal — no stand needed (fight 53010903: KG PINned 6 turns at cr=286 with the king on the stand, pushed T27, died T28). **PIN backoff** (`PZ BACKOFF d=N`): after 2 consecutive PIN turns on the same crystal, retreat to max army distance for the turn instead of hovering in the kill zone — the army chases (opening the stand) or holds (safe re-approach). Ada died hovering at the PIN four straight fights (53020347-359).
6. Everyone else scatters (army-distance-dominant kiting). If both solvers die → all scatter → draw insurance (held twice: 52984415, 52984808).
7. **Tactician bulb = the disposable third solver** (`maybeCastTacticianBulb`, `tacticianBulbAI` in `bulb_ai.lk`): its kit IS the solver kit (grapple/boxing/inversion, 6 TP/6 MP, ~500 HP, **no weapon** — cannot trigger the Apocalypse). Cast T2+ by buffers/supports (never solvers — their TP is for pushes), spawned at range 3 toward the graal; `team_cooldown` caps it at one per 7 turns team-wide. **Ops split (bulbs get ~50k ops/turn — user-verified)**: the SUMMONER coaches via `runBulbCoach` — runs the full BFS route planner for the bulb's position and broadcasts `[905, eid, crystalCell, stand, chip, target]`; the bulb just walks to the stand and casts (`PZ BULB PUSH` / `PZ BULB INV`), with a cheap fixed-offset local fallback (jump chaining, axis-push geometry — no map scans, no getPathLength) when no message arrives. **Command commitment** (`_bulbCmd*`): the stored instruction beats fresh replans until the cast fires, the crystal moves, or 3 turns pass — fight 53011272: per-turn replans ping-ponged a bulb 140→263→387→442 for 21 turns, zero casts; and `stand=-1` (coach has no push) must fall to local logic, never walk to the crystal's own occupied cell. **Work division with the solvers**: the coach skips crystals the solvers claimed on `[901]` and announces the bulb's pick on `[906]` (`_pzBulbClaims`, 3-turn expiry); solver focus picks exclude [906]-claimed crystals — the bulb takes what's left, never the solvers' target. LeekScript note: **no optional parameters** — a 3-arg function called with 2 args is INVALID_PARAMETER_COUNT and bugs every leek at T0 (caught by the geometry replay). COMBAT phase = pure decoy body. Bulbs never run `main.lk` — the engine wraps the function passed to `summon()` in a `BulbAI`, so the behavior must live in the AI function, not the main flow.
8. **Decoy bulbs** (`maybeCastDecoyBulb` → `decoyBulbAI`): low-tier puny/rocky/iced bulbs (level 48-130 — the cure leeks can equip them) cast T2+ toward the nearest army unit. Team cooldowns are **per chip**, so puny+rocky stack with the tactician casts. NEVER summoned with the ladder's `attackerBulbAI` — its damage chips are a latent Apocalypse trigger in the puzzle phase (this also covers DuskHope's pre-existing puny/rocky, which used to be summoned risky). COMBAT phase they attack freely (crystals are free 1-HP kills).
7. MAG carriers bank teleport for the phase-2 dive — but the emergency blink overrides: dying with the chip is strictly worse (fight 52984207: MH dead T4, teleport unused, phase 2 toothless).

### Phase 2 — COMBAT (after graal suicide; hardened triple-signal phase flip)
- **Flip-time escape** (`_combatLatchTurn`, in `main.lk`): the solver finishes the puzzle deep in the castle, adjacent to the army, exactly when Divine Protection drops (fights 53011079/53013437/53019695: KG died T15/T17/T19 — one or two turns after EVERY graal death). First COMBAT turn inside army reach 6: blink/INV-ESC before anything else.
- **Kill priority**: scribe +200 → squires +25 → knights 0 → **king −125** (soft veto; covid exempt). The scribe outranks every scribe-less cluster up to size 3 — fight 53011079: he repaired 81% of 5,048 and never dropped below 45%.
- **Crystals LAST** (user doctrine): inert 1-HP targets are never a cast/weapon target while any army unit lives — `swatCrystals`, weapon targeting, and `selectCombatTarget` all gate on army-dead. Killing crystals is the victory lap, not the fight.
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

# Hot-branch / cul-de-sac regression (fight 52984834 repro: KG at cell 55, yellow at 253,
# passive army ring makes every teleport stand hot + keeps PUZZLE phase via a Divine
# Protection stub at /home/ubuntu/leek-wars-generator/test/ai/cast_divine.lk).
# Pass = KG moves every turn (post-fix 64 moves; pre-fix froze with 1 move in 63 turns).
python3 tools/repro_fennel_hot_branch.py

# Phase-2 sandbox (graal-less → starts in COMBAT; 8 fennel-named fighter bots + 1-HP crystals)
# scenario at /tmp/phase2_scen.json — re-stamp entity stats from tools/leek_configs.json
# after any respec (weapons must be converted item-id → weapon-id via weapons.json)
cd /home/ubuntu/leek-wars-generator && java -cp $(cat runtime_classpath.txt) com.leekwars.Main /tmp/phase2_scen.json
# Reference (real builds): 12 kills / 37 turns / zero deaths / 24 dumps

# After ANY .lk edit: clear the generator compile cache, then test
# (stale cache silently runs the OLD code — invalidated one A/B already)
rm -f /home/ubuntu/leek-wars-generator/ai/*.class /home/ubuntu/leek-wars-generator/ai/*.java /home/ubuntu/leek-wars-generator/ai/*.lines /home/ubuntu/leek-wars-generator/ai/*.sig

# Rebuild the Python port after any .lk change
python3 tools/lk2py.py --check

# Deploy to BOTH accounts (Cure leeks must have main.lk assigned)
# MCP: leekwars_upload_v8 {account: main} + {account: cure}

# Launch a cross-farmer fennel fight (main creates lobby, cure joins from a
# browser/phone, main attacks). MCP tool (restart MCP host to register):
#   1. leekwars_boss_lobby { action: "open" }   → returns the join link
#   2. open the link as CURE, join the lobby (must come from your IP —
#      LeekWars allows ONE WebSocket per IP and squads die on owner disconnect)
#   3. leekwars_boss_lobby { action: "start" }  → attacks, returns fight link
#   abort anytime: leekwars_boss_lobby { action: "close" }
# Caveat: opening main's garden in a browser kills the server-held lobby WS.
# Node note: wss://leekwars.com/ws 404s default Node/curl TLS handshakes (JA3
# filter) — the Python/OpenSSL cipher list in server.js openWs is required.

# After a user respec: refresh configs, then re-stamp the sandbox scenario
python3 tools/fetch_leek_configs.py
```

**Reading a fight quickly** (fetch `/fight/get/<id>` authenticated; says are action code **203**, attributed via the last LEEK_TURN code 7; `USE_CHIP` raw is `[12, marker, cell, result]` — ground truth for chip identity is the 302 effect rows `[302, chip_db_id, ...]`):
- `B1 PH=... G=<id>/<alive>/<life>/<cell>` every leek turn.
- Puzzle: `PZ SOLVER: skip wait, army d=N` → `closing on c=X d=N` (d must DECREASE — constant d = the walk stall, A↔B pairs = oscillation) → `PZ BLINK dN` / `PZ INV-ESC dN` → `PZ RETARGET c=X` (focus abandoned after 8 no-progress turns) → `PZ DONE c=X` → graal death → `PH=COMBAT`. `PZ f=0 cr=X dst=Y me=C mp=N why=W` repeated = solver at the crystal but the route failing — why: **NOPLAN** no route found, **WALK** en route to stand, **PIN** body-blocked (mp=N > 0 = pinned harder; expect `PZ INV-PUSH` when geometry favors the swap), **LOS** knight on the cast line, **CASTn/INVn** chip error code.
- Phase 2: `PZQ` (quorum, debug only), `PZ DIVE c<score>` → `PZ DUMP xN` → recovery silence → second dive; `PZ GUARDSHOT xN` / `PZ GUARD plasma` (Ada); `PZ POKE none d= tp=` = carrier blocked, check distances.
- Damage audit: sum 101/110 actions into fennel-named victims; healing = 103 rows. Compare vs the scribe's repair to see if the treadmill broke.

## 6. Open items

- **Solver survival is the binding constraint** (last 3 fights: KG T11/T21/T7, Ada T4/T60/T11). Inversion escape deployed for the teleport-cooldown gap — watch for `PZ INV-ESC dN` and whether solvers live past T10.
- **Scribe-kill sprint and recovery retreat are deployed but unobserved live** — first thing to check in the next fights.
- Cul-de-sac walk fix (52984834) + anti-oscillation visit memory (53009902/918) verified locally via `tools/repro_fennel_hot_branch.py` (freeze → sweep); 53009902 solved 1 crystal (KG `DONE c=13` T10) but both solvers died ≤T21 in both fights — watch solver survival + `closing` distances next.
- Blink landing-zone quality: 53009918 dropped KG at cell 38 (a dead-end corner — max-army-distance loves pockets). If solvers blink into corners again, weight landing cells by escape routes, not just distance.
- Phase-2 damage ceiling: if fights still cap at ~9k with the sprint live, add KG's desintegration (nova ~400/cast at SCI 500) to the striker rotation, and consider a second-dive cycle audit.
- Crystals spawning outside the castle walls may be walk-unreachable pockets — `solverWalkToward` mitigates but inversion-only access is untested.
- Ladder cleanup owed when the campaign pauses: Ada respec restore (numbers in §2), remove boss chips from KG if slots are needed.

## 7. Winning reference builds (2026-08-19, from replays 53142219 + 52693107)

The puzzle is NOT the bottleneck — the winning 4-leek team solved it in ~50
turns with 14 casts / 2 solvers (same pace as us). The entire gap is
**survivability**: they took ~130 effective dmg/turn (SCI720 shields + RES450
bruisers + WIS400 heals) while we take the full ~2500/turn and die. Both
reference teams CONCENTRATE stats (bruiser = STR+RES+WIS only; support =
SCI+RES), never spread.

**4-leek clear (farmer temakisushi), 53142219** — no leek died all fight:
- *Inupi* (shield-bot, NO weapon): base WIS230/RES400/SCI500/HP2060/TP18 →
  total WIS400/RES480/**SCI720**/HP2900/TP24. Casts: every shield (fortress,
  rampart, wall, armor, dome, armoring, solidification, shield, carapace) +
  remission/therapy/serum heals + knowledge/elevation.
- *Kazutora/Kokonoi/Izana* (3 identical bruisers): base STR450/WIS190/RES240/
  HP2060/TP23 → total **STR600/RES450**/WIS400/HP3090/TP29. Casts: protein/
  rage/steroid buffs + spark/flame/lightning damage + remission self-heal +
  grapple/boxing (2 of them solved the puzzle).

**Solo clear (Pilow's Gorglucks), 52693107**: fight-time STR780/AGI480/RES340/
WIS290/HP1890 — took 20090 raw but shields+RES+AGI-reflect absorbed ~18k.
Casts: remission x69, protein x54, covetousness, fortress/rampart/armor/dome
+ grapple/inversion/boxing (solved solo) + jump/teleport mobility.

**Must-have chips we mostly lack**: protein (id 8, lvl 6, +80 STR buff — the
bruiser amp), remission (id 80, lvl 170, WIS heal cd1 — the sustain backbone),
solidification (id 96, +180 shield), carapace (id 81, absolute shield 55+15),
dome (id 173, lvl 243, 11% self shield). Method: stack 150+ shield/heal casts
so the army's 2500/turn becomes ~130, then STR-buffed bruisers grind 36k down.

**Mapping to our squad**: KG→shield-bot (SCI→700, RES→450, keep buffer chips);
ED→bruiser (STR500/AGI500 reflect already = solo template, ADD RES→400 +
protein + remission); MH needs RES≥300 before MAG540 matters; Ada→healer-tank
(WIS500/RES400 right, add remission + solidification). Principle: no damage
stat below the survival line — a leek that can't tank 3 turns of focus wastes
its offense. Equipping solver chips on MH/ED (done) + the 4-solver AI
(auto-activates via isNamedSolver+iHaveChips, deterministic spatial crystal
division) gives us the solve; these builds give us the combat.

## 8. The bruiser rebuild + kill+resurrect solve (2026-08-19, fights 53368484+)

*Supersedes the tank+solver+healer doctrines. All 4 leeks rebuilt from zero
(loadouts 794-797, reproducible via `tools/build_boss_bruisers.py`).*

### The confirmed winning formula (boss-2 leaderboard replays)

**Legumatore 52821555 (graal suicides at R3)**: all 4 leeks teleport into the
zone at R1-2, then per crystal: spark the 1-HP crystal dead, **resurrect its
body straight onto the goal**. Four resurrections at R2, graal down at R3,
then the 36k army is ground down with STR-bruiser weapons + WIS self-heals.
The damage is the defense; there is no glass solver.

**Engine mechanics (verified in generator source + sandbox):**
- `resurrect(entity, cell)` is the ONLY working call — `useChip` /
  `useChipOnCell(CHIP_RESURRECTION)` return -1 (the generic `applyOnCell`
  path filters to ALIVE entities). Range 1-2 from caster, LoS, target cell
  must be `available()` (walkable + empty). Body revives on the chosen cell.
- Chip facts: resurrection cost 18 cd 15 (per leek), NOT purchasable
  (`purchasable: false`) — we own exactly 2. Spark cost 3, range 0-10,
  NO LoS. Apocalypse = a crystal dead at the graal's turn (chest kills
  count: 53369486 wipe at R4).
- **Attack LoS is blocked by entities on middle cells** (`Map.verifyLoS`) —
  the engine pre-flight (`isEmptyCell` + `canUseChipOnCell`) is mandatory:
  a kill without a guaranteed landing is an Apocalypse (53369249/53369415).
- A "solved" crystal = on its goal axis with an obstacle-free ray to the
  graal (entities are transparent to the ray) — NOT a single cell.
- Ops budget = cores × 1M per turn. `core3` component = +10 cores — the
  puzzle BFS blew 1M constantly (`too_much_ops` turn-kills until core3).
- `getWeapons()` returns ITEM ids on the server (scythe 410, odachi 408,
  sun_spear 440, lightninger 180) — NOT weapon ids (39/37/42/25). The local
  generator diverges (returns weapon ids) — weapon checks are live-only.

### Builds (loadouts 794-797, 1780 capital each, 0 leftover)

| Leek | Totals | Role |
|---|---|---|
| KurtGodel | HP 2660 · RES 675 · WIS 665 · SCI 500 · TP 20 · RAM 16 | Support shield-bot (RES-scaled shields cast on allies, SCI buffs ferocity/bark, remission, chase-anchor) |
| EdsgerDijkstra | HP 4030 · STR 600 · WIS 350+50 · RES 400 · TP 22 | Resolver #1 (spark+resurrect) + bruiser |
| MargaretHamilton | HP 3150 · STR 600 · WIS 400 · RES 400 · TP 22 | Resolver #2 + bruiser |
| AdaLovelace | HP 3510 · STR 600 · WIS 400 · RES 400 · TP 20 · RAM 18 | 3rd solver (slides/inversion) + bruiser |

All 4: scythe + odachi + sun_spear + lightninger; solver kit (grapple/boxing/
inversion/teleport); remission + carapace + dome + fortress + wall +
solidification + antidote; core3 (+10 cores, +1 TP). KG: shield/buff kit +
tactician_bulb; ADA: 2nd tactician_bulb. `leekwars_apply_loadout` works from
zero; `tools/build_boss_bruisers.py` re-applies the whole thing.

### What the solve is now (V9 boss_context.lk)

- `tryKillResurrectSolve` (perch-KR): resolver perches within 2 of a goal,
  sparks the crystal from ≤10, `resurrect()` the body onto the goal —
  engine pre-flight before every kill. REVIVE-first: revives any crystal
  the chest/army kills (the Apocalypse save AND a solve).
- `tryOpenerSwapSolve`: teleport onto a solved-position cell + inversion —
  the 3rd/4th instant solve (we own only 2 resurrection chips).
- Slide solving (route planner + INV-APPROACH) for the rest; tactician
  bulbs roam with the summoner coach (50k-ops-safe).
- Doctrines tried and measured (17 fights): fast-dive solves 2-3 crystals
  by R7-12 but divers die; static turtle survives to R20+ but never solves;
  focus-kite rotates but the king out-runs it. Current: fast-dive with
  army-safe teleport landings.
- **First graal death: 53370125 R12** (2 KR + 2 ADA slides) — but with only
  ADA alive. The combat phase is the next wall.

### The remaining wall (2026-08-19 end of day)

The solve costs ~3 leeks by R10-12; the graal must fall with 2-3 alive.
The army focus-fires one leek to death every ~3 rounds (king ~800/hit +
poison, knights, scribe nuke) — a lone diver dies in 2-3 regardless of
shields. Open: swap-solve has never fired live (geometry instrumented);
re-killed revived crystals re-arm the Apocalypse (need the 4-solve inside
a ~3-round window); combat phase untested with the new builds (weapon
table now covers scythe/odachi/sun_spear as item ids).

## 9. Campaign status (2026-08-19 late, ~245 boss fights, 0 wins, 22 graal deaths)

**All mechanics work; the attrition race is unwinnable at our resources with
the current formulas.** Honest root-cause after ~25 doctrine variants and 6
build overhauls (bruiser / shield-bot / tanky MH+ADA / reflect-solo ED /
WIS-max ED / decoy+intercept+shadow+kite anchors):

- **The solve works**: 2 kill+resurrect (spark + resurrect(), engine
  pre-flight) + 1 inversion swap-solve + slides. 4 crystals solved in ~15%
  of fights (53374779, 53375804, 53375853). First graal suicides: 53370125,
  53370313, and 16 more since.
- **The attrition is the wall**: the army focus-fires the NEAREST leek for
  ~1600-2000/turn (king Excalibur ~800 + poison, knights, scribe nuke).
  A lone solver dies in 2-3 turns regardless of shields. The graal falls
  ~R10-15 with 1-2 leeks left; the 36k army then mops up.
- **KG's sustain is proven**: RES 500-675 + remission + shields + kite — he
  solo-kited the army 23+ rounds post-graal (53374357). The sustain exists
  for ONE leek; capital (1780) can't give it to four.
- **The winners' edges we can't match**: 4 resurrection chips (we own 2,
  `purchasable:false`); TP 27-29 remission spam (we have 19-22); the
  temakisushi formation needs a clustered spawn (ours is scattered
  228/458/491/563).
- **Bugs found & fixed along the way**: resurrect() is the only working call
  (useChip=-1); engine pre-flight mandatory (mid-cell entities block attack
  LoS); core3 = +10M ops budget (BFS blew 1M); a duplicated TRANQ block broke
  boss_context.lk braces (NO_BLOC_TO_CLOSE, masked the solve for 4 batches);
  `getWeapons()` returns ITEM ids on the server.

**The remaining options** (need user decision):
1. **More resurrection chips** (need 2 more — loot-only, from boss/chest
  drops). With 4, the Legumatore formula (4 instant solves at R2, graal R3,
  combat at 4v8) is directly achievable.
2. **Grind favorable spawns** (crystals within ~12 of spawn → teleport-solve
   R2-4 before the army engages). ~5-10% of spawns. Needs the combat phase
   to hold with 3-4 alive (untested — flip-time escape under-fires at
   graal death; survivors get executed mid-zone R12).
3. **Out-stat the sustain race**: the army's 2500/turn vs our ~1300-1800
   sustain. Winners out-sustain (TP 27-29, RES 450-510). We can't at 1780.
4. Accept the boss-2 wall for now; the builds + mechanics are banked and
   winnable with 1-2 more resurrection chips.

## 10. The 2-leek and final verdict (2026-08-21, ~290 boss fights, 0 wins)

**Everything was tried.** 4-leek (every doctrine: fast-dive, turtle, ball,
decoy, intercept, shadow, hit-and-run; every anchor variant) AND 2-leek
(fujiwar-style tanky bruisers, ED+MH). ~25 doctrine variants, 6 build
overhauls. The result is invariant:

- The solve WORKS (2 KR + swap + slides); the graal suicides in ~15% of
  fights (4 crystals done).
- The army focus-fires the nearest leek ~1600-2000/turn. Whatever config, the
  resolvers die R3-9 (MH/ADA first — deepest divers), KG/ED last (tanky).
- Graal falls with 1-2 leeks; the 36k army mops up. Combat phase never
  reached with 3+ alive.
- 2-leek (53382790+): MH dies R3-6 every fight, ED alone can't solve 4.

**Why Legumatore's clear took ~0-2027 damage TOTAL and ours take that PER
TURN**: they solved at R2-3 (crystals within ~12 of goals, teleport-solvable
before the army engages). Ours spawn 11-25 from goals — the resolver must
walk PAST the crystal into the goal-side, through the army, and dies on the
walk. The boss-2 leaderboard is each farmer's best (favorable-spawn) fight.

**Unlock conditions** (any one converts the work):
- Crystals spawning within ~12 of their goals (RNG — grind enough and it
  lands, but our graal deaths show even those need the combat phase fixed).
- The combat phase surviving the flip (survivors executed mid-zone at graal
  death — flip-time escape hardened but untested with 3+ alive).
- A team composition that out-sustains the 2500/turn army focus at 1780
  capital (winners: TP 27-29 remission spam + RES 450-510; we cap at 19-24).

The builds, loadouts, solve mechanics, and this autopsy are all committed.
The boss is genuinely hard for our account level — not for lack of effort.
