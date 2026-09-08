# Fennel King Boss — State of the System

## ⏭️ SESSION HANDOFF (2026-09-07, evening) — READ THIS FIRST NEXT SESSION

**Where we are:** ~500 total fights. Three measured loops today fixed the
kill+resurrect (KR) layer for real; the outcome metric did not move:
**0 wins, 1 graal death in the last 48 fights** (53570505: 4 crystals by R8,
graal R9, then phase 2 lost 3v8). The two divers now each land exactly one
KR per fight (24/24 on-target in the last batch) and die R3-8. The two other
resurrection chips (KG, MH) never fire. That is the wall, and it is a
resources/geometry wall, not a code wall.

### Today's loops (all deployed on main, `9.0/V9/boss_context.lk`, verified md5)

| Loop | Change | Evidence |
|---|---|---|
| 1 | **Dive landing fix**: the resolver walked ONTO the solved cell S, the range check failed, `krResurrectAnywhere` dropped the crystal on a random neighbour while the say claimed `r1`. New `krWalkToResurrectRange` stops at distance 1-2 with a legal cast; dive candidates need a real path (`getPathLength`) from stand to S. | Batch 2 (pre-fix): 5 of 8 full dives landed off-target (168≠204, 11≠12, 98≠84, 48≠84, 83≠85). Batches 3-5: 0 misses. Says now print the landing (`->cell`). |
| 1 | **Unkillable crystals**: `resurrect()` revives with 5 HP (max 10); `crystalShielded()` now compares spark damage to `getLife(eid)`. | 53569989: ED sparked a revived crystal twice (64, 46 dmg, alive) and died with teleport burned. |
| 1 | **Apocalypse save for every role** (`tryApocalypseRevive`, `_crystalAxisSeen` registry — dead crystals vanish from `getAliveEnemies()` so the old revive-first loop could never see them). From TURN 1 (53570312: chest killed 2 crystals on its T1 turn, wipe on the graal's T2 turn). | 53569997 / 53570312 = 2 wipes in 24 fights. Untested live since (no chest kill occurred in batches 4-5). |
| 2 | **say() costs 1 TP** (engine `EntityClass.say`: `useTP(1)` before the 2/turn limit, dropped says are paid). `pzSay()` caps at 2 and never pays at 0 TP; B1 say skipped on tight-TP puzzle turns. This freed Ada's exact-30-TP dive: she now dives R2 in 12/12 fights (was ~4/12). | Batch 5: 24 KR events / 12 fights. KG's shield rotation was losing 3-4 TP/turn to says. |
| 2 | Ops guard in the solve loop + stale `_crystalMap` cell refresh (a crystal slid to its goal was re-picked forever → `too_much_ops` turn kill). | Local repro on 53569989 geometry. |
| 3 | **Walk-dive** (`DIVE-W`: no teleport, 21 TP, keeps the blink) and the **anchor's own KR** (`_krNoTeleport`; KG has spark+resurrection+adrenaline). Teleport critical returns 2: all `== 1` checks → `>= 1` (a crit teleport was treated as a failure and wasted the turn). | Walk-dive fires locally; live 0/12 for KG (he trails the pack, never within 2+MP of a solved cell with a crystal in spark 10). |

Local harness: `python3 tools/local_boss_v9.py --fight 53569989` (clones a
real fight's graal/crystal/spawn cells, exact live chips, V9 AI, no army) —
all four crystals complete by R6-R8 on 53569989 / 53569999 / 53570489
geometries and the template. `python3 tools/boss_says.py --last 12 --brief`
reads live batches (KR truth = action 105 rows, since the dive say is dropped
at 0 TP).

### Batch ledger (correct loadouts 812/814/817/818 verified applied)

| Batch | Fights | Graal | KR events (on target) | Diver deaths |
|---|---|---|---|---|
| 08:04 pre-fix | 53569985-53570000 | 0 | 13 (8 misses) | Ada R3-5 ×9, ED R4-8 |
| loop 1 | 53570311-53570329 | 0 | 15 (0 misses) | same |
| loop 2 | 53570488-53570505 | **1** (53570505 R9) | 22 (0) | same |
| loop 3 | 53570552-53570565 | 0 | 24 (0) | same |
| loop 4 (KG anchor approach, manhattan) | 53570954-53570969 | 1 (53570955 R8) | 25 | KG now dies R3-5 walking into the wall/army, 0 KG dives |
| loop 5 (**MH Burning→Spark**, support KR) | 53570987-53570999 | **3** (R6, R6, R7) | 40 (KG 3, MH 8) | all four dead R3-8; phase 2 entered with 0-2 alive |
| loop 6 (approach refuses hot stands) | 53571006-53571018 | 0 | 12 | reverted: safety killed the KRs |
| **respec** KG TP 27 / MH TP 26 (loadouts 817/818, user-approved) | 53571210-53571222 | **5** (R6-R7) | KG R2 teleport-dive 12/12 | KG dead R3-4 on the pad |
| support post-dive retreat + MH Adrenaline | 53571235-53571252 | **4** (R5, R6, R6, R7) | all four fire by R2-3 | 0-1 alive at the flip every time |
| 04:56 (solo loadouts by mistake) | 53568638-53568649 | 0 | 0 | ED anchor dead R4 |
| **SUSTAIN TEAM** turtle (no teleport dives) | 53571383-53571395 | 0 | ~18 | Ada (front) R3-5; ED/KG live to R14-31 |
| ball (leader + 2 escorts + KG) | 53571480-53571492 | 2 (R8, R10) | ~20 | fights run to R25-52; 53571491 only Ada died |
| ball + escort slides + leader hold | 53571504-53571515 | 0 | ~18 | leader blinks away, 5-turn holds |
| turtle escape discipline | 53571524-53571538 | 0 | ~20 | KRs land 1-off, chips wasted |
| projected-focus shield stack | 53571556-53571602 | 0 | — | MH (escort) dead R3-6 ×12; ball takes 800-1000/round avg |
| **intercept + bruisers kite until KG has aggro** (T2-6 hold) | 53571628-53571641 | **4** (R9, R10, R12, R13) | 3-4 solves in 7/12 | 53571632: 3 alive at the R10 flip, phase 2 ran to R34 (first real phase-2 sample) |
| **gather builds, intercept flags still on** (MH MAG 680/RES 30, strikers without self-shields) | 53581358-53581371 | 0 | 0-2 | all dead R4-8: KG holds one round, then 3,000+/round on the unshielded strikers; phase 2 never reached |
| spawn order [MH, KG, Ada, ED] (MH at 228, KG at the 491 front) | 53581878-53581891 | 0 | 0-2 | no change: MH at 228 dies R4-8 (the interior is nearest to the army too), everyone dead R4-14 |
| fortress kept for contact, dome only with allies near, T1 gate fixed | 53581844-53581855 | 0 | 0-3 | KG now takes 28-458/round once fortress+armor+shield+wall are up and lives R10-18 — but the army walks past him: MH R5-8, Ada R6-9, ED R5-10 (per-unit reach, not aggro) |
| **tank self-stack fix** (KG in his own pack, gates at d11) | 53581832-53581843 | 2 (R9, R9) | 0-3 | KG stacks wall/armor/shield/solid on himself from R2 but fortress was burned at T1 (cd 4 → missing R3-4): 1,751 taken R4, dead R6-9; phase 2 reached twice with 2 alive — striker idle at 16 TP (plus1, no AoE chips), MH DUMP x3 → ~150 dmg; both dead next round |
| **reconciled builds** (strikers plasma + dome/carapace/wall, MH MAG 680 / RES 230) + intercept with KG pre-stack at d9 | 53581538-53581549 (11) | 0 | 0-3 in 8/11 | KG dead R4-6 in 11/11 even pre-stacked; everyone dead R6-13; phase 2 never reached; 0 credits left |
| **gather builds, column ball (valid rerun after the full re-upload)** | 53581468-53581480 | 0 | **0** | ball holds (four fights to R23-38 with KG's stack) but solves nothing; ED dies R4-5 alone in the spawn pocket in 8/12; phase 2 (the gather doctrine) never reached |
| gather builds, column ball — **INVALID: server compile corrupt** | 53581405-53581423, 53581459-465 | — | — | every leek bugged every turn (`item_roles.lk:2 VARIABLE_NAME_UNAVAILABLE`, `Invalid AI`) after single-file writes; fixed by the full `tools/upload_v9.py` re-upload (53581467 clean). 26 credits lost to it |
| **option 2: intercept-tank with the RES-760 KG, bruisers dive-era** (`_anchorIntercept=true`, `_turtleMode=false`) | 53581046-53581058 | 1 (R10) | 1-3 in 11/12 | KG dead R4-6 in 12/12 — the "near-immune" tank does not survive first contact with the full army; bruisers R5-12 |
| column + cast-before-move + KG capped to 3 cells near the army | 53573100-53573112 | 0 | 0-1 | deaths R5-17 (53573103 to R47); the ball still loses one leek per 1-2 rounds once the full army is on it — the stack covers 1-2 targets per round, the alpha lands on the third |
| **single-file column** (columnMove, KG leads to the path-nearest crystal) | 53573063-53573079 | 0 | 0 | ball forms R7-8 and takes 0 for R2-8; from R9 the army catches it mid-move: 3,828 / 2,926 / 3,212 per round, KG cast NOTHING R9-11 (he walked 6 ahead, pack out of range 3) → cast-before-move + 3-cell cap added |
| **shield-math respec** (KG RES 760, bruisers STR 640 / RES 230) + leashed ball | 53572536-53572548 | 0 | **0** | inside the dome the pack takes ZERO for whole rounds (R7-9 of 53572536); 53572546 three alive to the end; but the ball never reaches a crystal — KG crawls, then a corridor deadlock (KG at 333 with his own ball packed behind him in the 1-wide passage) |
| leashed ball (leader ≤ 3 from KG, KR stands ≤ 4 from KG, no route teleports) | 53572311-53572322 | 0 | 0-1 | fights R9-29; the ball creeps at KG's pace (MP 6) through the corridors, "closing on … hot d=14/15/12" for rounds, 0 solves; ED alone in the pocket dies R5-6 |
| **corridor-aware ball** (rally on KG T1-2, escorts follow KG, never park on articulation cells) | 53572274-53572303 | 0 | 0-2 | **fights run to R13-34** (three to R27-34), ball holds (KG/MH within 1-2 of Ada), intake mostly 0-500/round; the leader steps out of the dome and eats 2,450 bursts; solves collapse → leash added |
| shield-math rotation (`sustainStack`: solidification → dome → rampart/fortress/wall by lowest rel) | 53572039-53572050 | 1 (R8) | 0-3 | stacks of 72-99% landed only on ED (in range); Ada/MH took 1,000-2,050/round at the spawn front R2-4 while KG was 9+ behind → rally on KG at T1-2 added |
| **ball at dive pace** (leader + escorts within 2, KG on the leader, escorts walk-dive) | 53571950-53571964 | 0 | 0-2 | local: 4 crystals by R8-12, escorts within 3 on 116/126 turns; live: MH (escort id 2, glued to the leader) dead R3-4 in 12/12, Ada R4-7, solve stalls; three fights ran to R17-25 with 0 solves |
| **shadow** (KG follows the bruiser the army is on; bruisers dive-era, no hold) | 53571805-53571818 | 0 | 0-3 | focus flips every round across bruisers 10-19 apart; KG (MP 6) ends d5-19 from it with 26 TP unspent; Ada dies R3-5 in the corridor before he arrives |
| KG shield-bot INSIDE the melee pack (`executeSustainBotCombat`) | 53571720-53571733 | 2 (R9, R11) | 3-4 solves in 7/12 | KG dead R5-9 in 12/12 BEFORE the flip (dome burned at R2 on the pack, 0-2 shields at contact, 1,400-2,400/round) — the pack bot never ran |
| contact-timed tank stack (dome + rotation only at army ≤ 5) | 53571755-53571767 | 1 (R9) | 2-4 solves in 8/12 | KG now takes ~100/round at contact and lives R9-12 — but the army kills the bruisers instead (ED 1,967 R5, MH 2,393 R6, Ada 1,687 R8 in 53571756): aggro is per-unit reach, not "nearest body" |
| melee + steroid/protein, no flip retreat | 53571699-53571711 | 1 (R10) | 2-4 solves in 7/12 | **53571702: 2,734 / 1,944 / 1,849 into the scribe on R10-12 (6,527 = his HP pool), he healed 4,874 back**; all dead R11-13 |
| **melee phase 2** (heavy sword/rhino, scribe first) | 53571644-53571689 | 3 (R9, R13, R13) | 3-4 solves in 6/12 | 53571644: 3 alive at R9 flip, sword hits ~650, 1,838 dealt, all dead R12; the flip retreat cost 2 rounds of walking |
| intercept tank (KG holds aggro, bruisers dive-era) | 53571611-53571623 | 0 | — | 53571619: 4 solves by R8, chest re-killed blue R12 → Apocalypse R13; KG takes 100-1,400/round when focused and lives R12-40; Ada hit R0-3 in the corridor |

**Live builds now — SHIELD-MATH RESPEC (user decision 2026-09-08 ~01:30;
verify with `tools/fetch_leek_configs.py`; loadouts 812/814/817/818):**
- **KG 817 shield-caster**: base RES 600 / WIS 200 / SCI 200 / HP 2195 / TP 19
  / MP 6; components core3, ram2, ram, nuclear_core, power_supply,
  neural_core_pro, obsidian_plate ×2 → **RES 760** / TP 26 / HP 2605 / SCI 350
  / WIS 200. Shields ×8.6 (×10.6 under solidification): rampart 77-106 %,
  dome 95-112 % (everyone within 3), fortress 60-85 %, carapace ~470 abs.
- **ED 812 / ADA 814 / MH 818 bruisers**: base STR 600 / RES 200 / WIS 130 /
  HP 2060 / TP 20 / MP 6; same components → **STR 640** / RES 230 / TP 23 /
  MP 7 / HP 2580. Buffed sword ~1,650; three swords + rhino ≈ scribe's 6,000.
- Restat potions consumed today: 10 (KG ×3, MH ×3, ED ×2, ADA ×2).
- Previous line (sustain team, superseded): RES 480 bruisers — RES on a
  non-caster does nothing (see SHIELD MATH).

**(Sustain-team line before the respec, kept for the ledger's context —
loadouts 812/814/817/818 as rebuilt 2026-09-07 evening, 1780 capital
each, 16 chips, RAM 16):**
- **KG 817 shield-bot**: base WIS 230 / RES 400 / SCI 500 / HP 2075 / TP 19 /
  MP 6; components core3, ram2, ram, nuclear_core, power_supply,
  neural_core_pro, amazonite, strawberry → HP 2365 / TP 26 / SCI 650 / RES 460
  / WIS 280. Chips: fortress, wall, dome, solidification, carapace, armor,
  rampart, armoring, shield, remission, therapy, serum, knowledge, elevation,
  rage, resurrection (no spark: never dives; resurrection = Apocalypse save).
- **ED 812 / ADA 814 / MH 818 bruiser-tanks** (identical): base STR 420 / WIS
  250 / RES 450 / HP 2060 / TP 20 / MP 6; components core3, ram2, ram,
  power_supply, amazonite, strawberry, propulsor, limbani → HP 2580 / TP 23 /
  MP 7 / STR 460 / RES 480 / WIS 285. Weapons heavy_sword 278 / rhino 153 /
  bazooka 184. Chips: spark, resurrection, grapple, boxing, inversion,
  teleport, protein, steroid, adrenaline, carapace, wall, fortress,
  solidification, remission, antidote, dome. MH's MAG is gone (no poison).
- AI: `_turtleMode = true` in boss_context.lk — no teleport dives (walk-dive
  / immediate KR only, 21 TP), route teleports only onto stands with army
  > 12; KG anchors/follows the pack with the shield rotation. First batch
  after the rebuild: see ledger.

**Phase-2 audit** (the two earlier graal deaths): survivors dealt 1,175 and
5,871 to the 36k army after the flip; the scribe/knights healed 754 and
3,361 of it back. Phase 2 is unwinnable with what survives the puzzle. The
puzzle now runs at the winners' pace (graal R6-7 in 3/12); the clear needs
a team that (a) reaches the flip with 3-4 alive and (b) can grind 36k HP
through ~1-3k/turn of army healing. Both are build questions (see §7).

### Hard-won engine facts added today
- `say()` = 1 TP per call, even when dropped (limit 2 logged/turn, 100 chars).
- `resurrect(e, cell)`: revived entity gets totalLife = max(10, 50%), life = half → crystals come back at 5 HP; the cell argument IS honored (the misses were our own walk).
- Teleport (any chip) returns 2 on a critical — never test `== 1`.
- A bare un-braced `return` swallows the NEXT LINE (silently: `updateBossContext` aborted from turn 2 when a statement was inserted after `if (!_isBossFight) return`). Brace every return.
- Dead crystals are not in `getAliveEnemies()`; the chest can kill two crystals on its turn-1 turn.
- Resurrection + spark + adrenaline exist on all four leeks; the 4 chips are equipped (inventory has no spare). TP budgets: teleport-dive 30, walk-dive/immediate 21. KG (TP 20+5) and MH (22, no spark, no adrenaline) cannot teleport-dive.

### The remaining wall (honest) and the decisions that need the user
User ruling 2026-09-07: **8-leek lobby is not acceptable — 4-leek clear only.**
Done since: MH loadout 818 Burning→Spark (applied); all 4 chips now fire
(`supportKRTurn`: KG/MH walk-dive or immediate kill, approach stands ranked
by real path and refused when army < 6). Graal R6-7 in 3/12. Everyone dies
R3-8 because the dive window is a walk into the army for the TP 20-22 leeks
(teleport-dive needs 30 TP: only ED 27 / ADA 26 + adrenaline reach it).
**CLOSING VERDICT v3 (2026-09-08 ~03:00, 13 credits left, ~590 boss fights
today, 0 wins).** Everything mechanical is now in place and verified: the
KR layer lands every dive, all four chips fire, the shield math is applied
(zero-damage rounds inside the dome), the corridors are mapped and the
column traverses them single file, the ball forms and moves. What still
loses is the arithmetic of one shield-caster against eight attackers: KG
can put 2-3 casts per round on 1-2 targets (dome 4 of every 8 rounds), the
army spreads over three bruisers, and whoever is uncovered takes 2-3k. The
winners' Inupi did it with TP 24 and 169 casts because his bruisers took
"400-1,300 TOTAL" — i.e. the army was NOT on them: their formation kept the
army on the shield-bot. Ours reaches the army as a blob. Options that remain
are all builds/formation, not mechanics: (a) a SECOND shield caster (Ada:
RES 700 + rampart/fortress/carapace/dome, STR 0) so two casters cover three
bruisers every round; (b) KG solo-intercept WITH the new stack (he is now
near-immune himself: solidification + dome + fortress + wall ≈ 200 %) while
the bruisers solve dive-era — the 4/12-graal doctrine of 53571628-641 with
a KG that no longer dies; (c) accept and bank. I recommend (b) first: it is
a two-line change (`_anchorIntercept = true`, `_turtleMode = false`) on
builds that already exist, and it is the only configuration today that
produced graal deaths at 30 %.

**STATE 2026-09-08 ~06:00 (0 credits):** the reconciled builds restore the
dive tempo (0-3 solves, KR fires) but KG as intercept tank dies R4-6 in
11/11 with the pre-stack — the RES-760 self-stack does not survive first
contact with the full army (it did hold vs a partial army in 53571755+).
Phase 2 / gather has still never executed live. ROOT CAUSE FOUND
(53581542 audit): `sustainStack` built its pack from allies EXCLUDING the
caster, so the intercept tank at d3 with 17 TP cast only solidification —
he never had fortress/wall/armor/shield on himself at contact (R4: 2,546
taken, dead). Fixed and uploaded (full re-upload): the tank is in his own
pack in intercept mode; dome/rotation gates moved to army distance 11
(R2 at d10 was missing by one). UNTESTED LIVE (0 credits). Next session:
one batch of exactly this configuration before changing anything; expected
KG intake at contact well under 1k/round if the fix holds, then the graal
should fall R9-13 with 3 alive and `executeBossGather` finally runs.

**STATE 2026-09-08 ~05:00 (11 credits left, superseded):** the gather doctrine is live
on the server but has never executed in a real fight — with the gather
builds (MH MAG/RES 30, strikers without self-shields) neither puzzle
doctrine converts: intercept → 3k/round on the unshielded strikers, dead
R4-8; ball → survives R7-38, solves 0. The puzzle/phase-2 build tension is
the open problem: the puzzle needs the intercept tempo with self-shielded
RES-230 strikers (graal in ~30 %), phase 2 needs plasma/lightning/meteorite
slots and a MAG covid carrier. Candidate reconciliation for next session:
strikers keep plasma + bazooka + dome/carapace (drop lightning/meteorite/
rockfall), MH keeps the kit + covid but gets RES back through components
(amazonite/obsidian) instead of chiyembekezo, and the puzzle runs the
intercept doctrine with KG pre-stacking at army distance 9.

**PHASE-2 GATHER + BLAST (user doctrine 2026-09-08, built + sandboxed, NOT
yet executed live):** builds: MH back to MAG (818 "BOSS MH covid":
MAG 680 / TP 24 / HP 2930, covid/plague/toxin/arsenic/venom/soporific +
solver kit + spark/resurrection/adrenaline, gazor + flame thrower); ED/ADA
keep STR 640 and swap carapace/wall/solidification/dome for plasma,
lightning, meteorite, rockfall (bazooka/sword/rhino kept). Engine facts:
grapple = "attract directly to the cast cell" (first enemy on the straight
caster→cell ray slides onto the cell; 4/turn, 3 TP); plasma = 37+2j × STR ×
TARGETS-HIT in a plus-2 (self-hit if the caster stands on the centre's
axes within 2); AoE falloff 1 − 0.2·dist; covid 69+10j × MAG × 7 turns,
propagation 2 (≈28k over the army once clustered at MAG 680). Code:
`executeBossGather()` (centre = scribe-first cluster, off-axis approach to
range 2-6, up to 4 grapples onto the plus cells from enemies beyond them,
plasma when 2+ in the plus, lightning ×3 / meteorite / rockfall / bazooka
8-12 otherwise); MH uses the existing dump path (covid-first, dive).
Sandbox `tools/local_phase2.py` (8 passive fennel units, no graal):
2,500-3,400 dmg/round to the army from R3 with pulls of 2 and plasma on
2-3 targets, plus MH's poison ticking 500/round then 2,278 after her dive.
Geometry facts learned in the sandbox: grapple rays are straight lines
only and the ray toward the centre hits the centre first, so from one
position the plus fills with 2-3 targets, not 5 — the real cluster
mechanic is covid's propagation on the army's own formation; LIGHTNING is
a line-launch chip (must be aligned with the target); plus-2 plasma
self-hits when the caster is on the centre's axis within 2. Hence the
strikers stand ON the centre's axis at distance 4-5 (plasma 0-6,
lightning 2-5 aligned, meteorite 5-9, rockfall 5-7, all self-safe), pull
2/turn, and always spend the rest of the TP on AoE at the centre. Sandbox
(passive army): 26,055 dmg in 12 rounds, scribe down by R9, no bugs.
Deployed to the server (md5-verified) but NEVER run live — 1 credit left.
Untested live: the army's movement between our turns (it will not stand in
the plus), and the puzzle phase with MH at RES 30.

**SINGLE-FILE COLUMN (built + local-validated 2026-09-08 ~02:30):**
`columnMove(obj, stopD)` for every ball move — candidates = 12 lowest
manhattan cells within MP, scored by REAL path to the objective
(`pathTo`, falls back to an empty neighbour when the objective is
occupied), corridor cells +25 penalty and only allowed when no ally is on a
corridor cell within 5 (`allyInCorridorNear`), never stop inside unless
already inside, strict path improvement required. KG (acts first, id 0)
leads toward the unsolved crystal with the shortest real path from him
(crystals outside the walls have none and are skipped — local 53570489: KG
aimed at cell 44 for 60 rounds). Local: MH and ED file through 315-263 one
at a time, ball forms by R7, KG leads through 351/369/374/391 R9-14, three
KRs at R16-19, no deadlock, no bugs. Live batch: see ledger.

**CLOSING VERDICT v2 (2026-09-08 ~02:00, 37 credits left):** the shield-math
respec is live and WORKS as mitigation — zero-damage rounds for the whole
pack inside KG's dome (RES 760: dome 95-112 %, rampart 77-106 %). The
remaining problem is purely movement: a 4-leek ball cannot traverse the
castle's 1-wide corridors as a blob (KG parked at 333 with his own ball
behind him = deadlock; ED alone in the 476-590 pocket dies R4-8 every
fight). The next work is a single-file corridor traversal: order the
column (KG first, then the leader, escorts), each member enters a corridor
cell only when the next one is free, nobody stops inside; form the ball
again on the first wide cell past the corridor (cells adjacent to 228 and
the interior). With that, the immune ball reaches the crystals and the
KR/slide layer (all verified) solves them. Phase 2 arithmetic with STR 640
bruisers: buffed sword ~1,650 ×3 + rhino ≈ 6,000 = the scribe in one round
IF all three are adjacent — the melee routine must stage the three
adjacent cells before the burst.

**CLOSING VERDICT (2026-09-08 ~01:00, 49 credits left, ~500 fights today):**
Two durable facts were established tonight and are in memory: (1) target
RES does nothing — shields sum uncapped and are scaled by the CASTER's RES,
so the winners' mitigation is a shield-caster stacking two relative shields
per target, and (2) the castle's single-cell corridors wall the team out
whenever a follower parks on one. With those applied, the ball survives
R20-34 but solves 0-2 (it moves at KG's MP 6 through the corridors while
the leader is leashed to the dome); without the leash the leader solves
3-4 crystals and dies R4-8 with the graal falling R9-13 in ~30% of fights
and 1-3 alive; phase 2 then loses to the scribe's ~1,600/round heal vs our
~2,500/round of buffed sword. The next real step is not another doctrine
loop but a build change guided by the shield math: RES belongs on the
shield-CASTER only (KG RES → 700+ makes rampart/fortress ~100% each), the
bruisers' 400 capital of RES should go to STR/TP/HP, and the scribe needs
a one-round kill (~6,000): 3 bruisers at STR 700+ buffed (~1,700/sword) +
rhino get close. Ask the user before any respec.

**M_LASER BREAKTHROUGH + PLASMA/REFLECT REGRESSIONS (2026-09-08, user-directed):**
- **m_laser (weapon 47, laser-line, range 5-12, ~500/hit) is THE unlock**: it
  hits every entity on the line, so fired down the column it damages the
  scribe THROUGH the knights (the scribe was previously untouchable). First
  scribe kill of the campaign: 53584089 (graal R4, 4 alive, scribe dead R9,
  14,652 dealt / 6,604 net — best fight ever). Wired as the phase-2 primary:
  align on the scribe's row/col within 5-12 with LoS, fire x2.
- **The remaining wall is flip survival**: m_laser needs 3-4 leeks alive to
  laser-focus the scribe faster than its ~1,600/round self-heal; we usually
  reach the flip with 1-2 (die R5-11), so the scribe mostly survives and net
  stays ~500-2,000/fight vs 36k needed.
- **plasma (chip 143) REGRESSED** (swapped for armor → lost a shield → died
  R5-7, plasma rarely fired self-safe): 4/12 graal, net 0-1,616. Reverted.
- **reflect (AGI+mirror+thorn) REGRESSED** (cost HP/STR → died in the puzzle):
  2/12 graal. Reverted (cost 8 restat potions, user re-bought).
- **BEST/CURRENT config**: all-STR clones (STR 420-460 / WIS 450 / RES 270-350
  / TP 26) + covetousness (TP engine) + m_laser through-column (scribe) +
  rhino/neutrino + full shield stack + scribe-first + aggressive stand.
- **MAG covid carrier (MH) REGRESSED** (user idea: covid spreads → poisons the
  hidden scribe unhealably): sound in theory but the MAG leek is too fragile
  in the puzzle dive — MH died R4-5 in 12/12, DUMP=0, covid never cast.
  Survival is the binding constraint on EVERY build change (reflect, plasma,
  MAG all regress by trading the survival that reaches phase 2 with a team).
- **THE WALL (final, 2026-09-08, ~750 boss fights, 0 wins)**: flip survival.
  m_laser makes the scribe killable (proven: 53584089 scribe dead R9, 14,652
  dealt) but only with 3-4 leeks alive to laser-focus it past its ~1,600/round
  self-heal; we reach the flip with 1-2 alive (die R4-11) most fights. No
  build change closes it (all trade survival); the winners concentrate STR
  780 + reflect + TP 29 into 1-2 leeks, which our 1,780-capital-x4 can't match.
  Next lever if resumed: raise flip survival WITHOUT trading the dive speed —
  e.g. one leek reserves teleport for a phase-2 blink, or grind volume for
  the favorable spawn where 4 reach the flip and the m_laser+grind clears.

**BEST CONFIG THIS SESSION (2026-09-08) + COVETOUSNESS + REFLECT RESULT:**
The peak was ALL FOUR as STR clones (STR 420-460 / WIS 450 / RES 270-350 /
TP 26, rhino+neutrino+lightninger, jump) + **covetousness** (chip 120, X-2
area = +1 TP per enemy hit for 2t, the TP engine) + scribe-first phase 2 +
the aggressive stand routine (buff/shield only on a landed shot, close to
range 2): **9/12 graal deaths, once all four alive at the flip, ~3,000/round
phase-2 damage.** The wall there: the scribe (heal engine) sits behind the
knights out of weapon range 2-6, grapple can't pull it through them
(SCRPULL fired 0×), the army heals ~1,600-3,200/round, net ~0-1,400, leeks
die R4-8 — can't clear 36k. REFLECT respec (AGI 350-380, mirror+thorn, ~43%
return) REGRESSED it to 2/12 graal: reflect does NOT reduce damage taken
(engine EffectDamage: returnDamage is separate from the shield subtraction),
so paying AGI cost HP/RES/STR → leeks die FASTER in the puzzle (R2-9) and
never reach phase 2 where reflect's attrition would matter. Reverted KG/ED
to STR clones; ADA/MH stuck as reflect (out of restat potions — buy in UI or
wait). **The proven-best is the all-STR-clone + covetousness + scribe-first
+ aggressive-stand config; restore ADA/MH to it when potions refresh.**

**THE LEGUMATORE FORMULA, DECODED ROUND BY ROUND (52821555, 2026-09-08):**
four identical leeks (fight totals HP 3,282 / TP 26 / MP 6 / STR 600 / RES
500 / WIS 541 / SCI 110 / AGI 50), our exact spawns 228/491/563/588, same army.
- **T1**: leather_boots (+2 MP), walk 8 toward the crystal zone, JUMP (chip
  144: range 3, no LoS, no initial cooldown, we own 3), then
  solidification, motivation, armor/fortress, protein. Figue: 491 → 425
  (walk) → 390 (jump). Nobody engages the army.
- **T2**: adrenaline, spark the crystal (from ≤10), TELEPORT (12), walk 8
  (MP 6 + boots) to within 2 of the solved cell, resurrect. All FOUR
  crystals solved on T2 (res → 85 / 84 / 187 / 138). TP: 26 + 5 − 1 = 30 =
  spark 3 + teleport 9 + resurrect 18. This is exactly our dive code with
  a T1 approach in front of it.
- **R3**: graal dies. From R3 to the end NOBODY MOVES (positions 154 /
  121 / 227 / 296 all fight). Each leek fires 3-5 weapon shots per round:
  RHINO (79 hits, avg 439 at STR 600; 5 TP, 3 uses, range 2-4),
  NEUTRINO (27 hits, avg 225; 4 TP, 3 uses, range 2-6, +8 % vulnerability),
  LIGHTNINGER (5 hits, avg 673) — ~1,300/leek/round, 3.4-6.9k/round team.
  Leftover TP: protein every 3 rounds, wall/fortress/armor/solidification
  on self, dome on the pack, knowledge.
- **Kill order**: KING first (3.5k / 5.2k / 4.1k / 3.2k on R3-6 → dead R6),
  then squires (R7-8), knights (R8-10), SCRIBE LAST (6,000 in one round R11).
- **Sustain**: WIS 541 → lifesteal 54 % of every hit (engine: value ×
  WIS/1000, any direct damage) ≈ 700 heal/leek/round, plus self-shields.
  Damage taken 300-2,900/round team-wide; nobody died.
- We own every piece: rhino 153 ×9, neutrino 182 ×60, lightninger 180 ×4,
  jump 144 ×3, leather_boots, motivation, protein, knowledge, solidification,
  armor, fortress, wall, dome, spark, resurrection ×4, teleport, adrenaline.

**SPAWN SLOTS = PARTICIPANT ORDER (verified 53581862, 2026-09-08):** the
`participants` list of `/garden/start-boss-fight` maps to spawn cells in
order: slot 1 → 228 (interior, closest to the crystals, out of the opening
walk), slot 2 → 491 (corridor front, hit R0-3), slot 3 → 563, slot 4 → 588
(the pocket behind the 315-263 corridor). Entity ids follow the same order
(slot 1 acts first). The whole campaign ran [KG, Ada, MH, ED] — Ada in the
front slot, the tank in the safe interior. `tools/boss_batch.py` now sends
[MH, KG, Ada, ED].

**CASTLE CORRIDORS (map 4562, BFS/Tarjan on tools/boss_map_data.json):** the
spawn pockets (476-590 block) connect to the interior through single-cell
corridors; 59 articulation cells (263, 280, 298, 315, 351, 369, 387, 513,
530-531, 549, 567, 585-591, 603-608 …) — an ally standing on one walls the
rest of the team out (local + live: ED stuck at d14 with mv0 for whole
fights; MH parked at 263 within 2 of KG did it). Deployed:
`_pzCorridorCells` (hardcoded list), `ballMoveTo()` parks only on
non-corridor cells within 3 of the anchor, rally T1-2 on KG (spawn 228,
already inside), escorts follow KG (the shield source, dome radius 3).

**SHIELD MATH (generator source, verified 2026-09-07 night — this reframes
every build decision of the campaign):**
- `EffectDamage`: damage = raw × (1+STR/100) − damage × relShield% − absShield,
  floored at 0. **The target's RES does not reduce damage at all.** RES only
  multiplies the shields the RES-holder CASTS: shield value = (v1 + jet·v2) ×
  (1 + casterRES/100). Our RES-480 bruisers were bought for nothing unless
  they cast their own shields.
- **Dome does NOT cover its caster** (effect targets 26 = allies + summons,
  no TARGET_CASTER bit); fortress/wall/armor/shield/solidification (30) do;
  rampart's and carapace's second effect lands on the caster (self +4-5 %
  rel / +15 abs per cast). A lone tank's stack is fortress + wall + rampart
  self + armor/shield abs — about 125 % relative when all are up.
- Relative shields from DIFFERENT chips SUM (buff stats are added across
  active effects, no clamp anywhere) → ≥ 100% relative = zero damage.
  Recasting the same chip replaces it (non-stackable). Solidification =
  +180-200 RES RAW (unscaled) for 3 turns.
- KG (RES 460, ×5.6; ×7.6 under solidification): rampart 72%, fortress 57%,
  wall 34%, dome 84-99% on everyone within 3, carapace ~420 abs. Two casts
  on one bruiser (rampart + fortress) = 129% = immune for 3 rounds; dome
  alone near-immunizes the pack 4 of every 8 rounds. Bruisers' own dome
  (RES 480) = 64-75%.
- Deployed as `sustainStack()`: solidification self → dome (pack within 3)
  → rampart/fortress/wall on the bruiser with the lowest
  `getRelativeShield()` → carapace/armor/shield on the lowest absolute;
  used in the puzzle STACK block and phase 2. Bruisers self-dome at
  contact when their own relative shield < 60.

**BALL AT DIVE PACE — live result 0/12 (53571950-964).** The ball holds
together live (as locally) and the army takes it apart in order: the escort
glued to the leader (MH) R3-4, the leader R4-7, then KG/ED. Cohesion did not
convert into survival: KG's rotation puts 1-2 shields per round on one
bruiser while all three stand in the army's reach. **End of the sustain
program's doctrine space at these builds: 19 batches, best 4/12 graal
deaths (intercept + kite), 0 phase-2 survivals beyond 3 rounds.**

**BALL AT DIVE PACE (built + local-validated, 2026-09-07 late):**
`_turtleMode` on, `_ballHoldPerch` off (no hold/perch/retreat layers),
leader = `ballLeader()` (lowest-id named solver with the kit, computed on
every instance incl. KG), escorts within 2 taking walk-dives / ≤1-off
immediate KRs / local slides, PDIVE allowed when the landing is ≤ 2 from
the goal, KG shadows the LEADER within 2-3 with dome at contact and the
rotation on the pack. Local: 4 crystals by R8 / R9 / R12 on the 53569989 /
53571535 / 53570489 geometries, KG on the leader 100% of turns. Live batch:
see ledger.

**COHESION vs TEMPO (53571805-818):** shielding needs the bruisers within
3-7 of KG; dive-era solving scatters them 10-19 apart and the army's focus
flips between them every round. Neither the ball (cohesion, no tempo) nor
the shadow (tempo, no cohesion) converts. The reconciliation still owed: the
ball moving as one to crystal A, then B (leader dives/slides, escorts take
only solved-landing KRs and slides, KG within 3), at dive pace — i.e. the
ball doctrine with today's KR fixes but WITHOUT the blink/hold/retreat
layers and with ballObjective() re-picked per crystal. Untested as a whole.

**AGGRO FACT (53571755-767):** the army does not focus the nearest body as
a group; each unit hits whatever is in its own reach. A tank at d1-2 with a
full stack takes ~100/round while the three bruisers 5-9 cells away take
the rest. Mitigation therefore has to sit ON the bruisers (KG inside the
pack casting on them) — which is the ball, whose solve tempo collapsed
(0-2 solves in 25-50 rounds). The two halves have not been reconciled.

**THE PHASE-2 EQUATION (53571702, the cleanest sample):** three buffed
bruisers adjacent to the scribe deliver ~2,000-2,700/round; the scribe
heals ~1,600/round; the bruisers survive 2-3 rounds in melee. Killing the
scribe (6,000) needs either a one-round burst ≥ 6,000 (4 leeks: KG has STR
0), his heal suppressed (TP shackles are MAG-scaled — useless on these
builds; the poison MAG carrier is gone with MH's respec), or the bruisers
surviving 6+ rounds adjacent (the winners' near-immunity). Everything
below this line is the day's trail to that equation.

**Sustain-team verdict (2026-09-07 night, ~150 fights on the new builds):**
the puzzle converts again with the intercept doctrine (graal R9-13 in 3-4 of
12, 2-3 alive at the flip) and phase 2 now exists (`executeBossMelee`:
scribe-first, rhino 2-4, heavy sword adjacent; steroid/protein before the
sword; bruisers skip the flip retreat). The arithmetic that remains: a
heavy-sword hit is ~650 (STR 460) → ~1,300 buffed; 36k army at 3×1,300 ≈
9-10 rounds of three bruisers surviving adjacent to the army. Today they
survive 2-3 rounds of phase 2. KG's stack covers one focus target; in melee
all three are in the army. Next levers: KG dome/carapace rotation on the
whole melee pack (stand inside it), rampart from range, the scribe's
6,000 HP as the only kill that matters (its heals are what make the grind
impossible), and the chest as an Apocalypse hazard (53571619: chest
re-killed a revived crystal at R12 with every chip on cooldown).

Decision 1 (TP respec) was taken earlier: graal R5-7 in 4-5 of 12 with the dive builds.
What remains is invariant across the last 36 fights: every leek that dives
is dead 1-3 turns later (teleport spent on the dive = no escape; the army
kills ~one leek per turn from R3), so the flip is reached with 0-1 alive
and phase 2 (36k HP, 1-3k/turn of healing) is lost immediately.
Remaining decisions:
1. **Phase-2 team** (the only path to a clear): the winners' 4-leek shape = SCI-720 shield-bot + 3 STR600/RES450/WIS400/TP29 bruisers (§7), turtling under shields; the KR layer then solves at walk-dive pace (TP 21) plus slides, R8-15 instead of R5-7, with bodies intact. Needs all four loadouts rebuilt (loadouts 794-797 are a stale first attempt) and a shield-rotation doctrine that actually keeps the pack alive (KG's current rotation: dome/rage/slb/wall on the nearest pair).
2. Phase-2 doctrine after the flip (scribe first, kite, covid) is unwritten and untestable until (1).
3. Cheap puzzle-side polish left: MH dies R2-3 on her dive (HP 2450 into the pad); ED's dives land R3-5 because his crystals are far — both cosmetic next to (1).

### Next-agent prompt (paste to start)

> Read `docs/fennel_boss.md` "SESSION HANDOFF (2026-09-07, evening)" first
> — CLOSING VERDICT v3, SHIELD MATH, CASTLE CORRIDORS and SINGLE-FILE COLUMN
> are the current state — then sections 1, 7 and the runbook. Live AI =
> ball mode (`_turtleMode = true`, `_anchorShadow = true`, KG leads via
> `columnMove`); builds = shield-math respec (KG RES 760 caster, STR 640
> bruisers). First experiment recommended: intercept-tank with the new KG
> (`_anchorIntercept = true`, `_turtleMode = false`). Builds = the SUSTAIN TEAM (loadouts 812/814/817/818
> rebuilt 2026-09-07 night, see "Live builds now"); AI = intercept tank +
> kite-until-aggro + dive-era solving + `executeBossMelee` phase 2. Loadouts 812/814/817/818 must be
> applied (verify with `tools/fetch_leek_configs.py`; the user sometimes
> reverts to solo loadouts). 4-leek clear only (user ruling; no 8-leek
> lobby). The puzzle is solved: all four leeks kill+resurrect by R2-3, graal
> dies R5-7 in ~40% of fights — but with 0-1 leeks alive, and phase 2 is
> lost every time. Do not spend more loops on the puzzle. The next work is
> the phase-2-capable team (§7 winners' shape) + a shield doctrine that keeps
> 4 alive to the flip, then the phase-2 grind. Ask before any respec or git
> mutation. Validate every .lk change with `tools/local_boss_v9.py --fight
> 53569989` (bare `return` swallows the next line; say() costs 1 TP).

---

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
