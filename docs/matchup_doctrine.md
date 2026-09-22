# Matchup doctrine

Per-archetype playbooks for V9, and the evidence behind each one. A doctrine
only earns a place here once it has been **measured on a stable testbed** —
reasoning that sounds right but measures neutral is recorded as such, because
the negative results are what stop the same idea being re-tried every quarter.

## How anything here gets measured

Three tools, in the order you use them:

| tool | question it answers |
|---|---|
| `tools/matchup_diag.py` | what did each side actually *do*, split by win/loss |
| `tools/matchup_stability.py` | is this matchup a usable testbed at all |
| `tools/matchup_ab.py` | did a change help, on the same seeds (McNemar) |

**Always stabilise before you measure.** `matchup_stability.py` checks two
things that are easy to assume and expensive to get wrong:

- *Determinism.* A replayed seed must reproduce exactly. It does (12/12 on
  `ladder_eleeksire`), which is what makes the paired A/B design legal and
  3-6x cheaper than comparing two independent win rates.
- *Excess variance.* Block-to-block win rate must be no wider than binomial
  noise predicts. On `ladder_eleeksire`: block sd 0.113 vs 0.095 expected —
  consistent with chance, so seed blocks are interchangeable.

Seeds vary real geometry, not just crit rolls: with no custom map the generator
randomises obstacles **and** start positions from the seeded RNG.

Sample sizes at a ~23% baseline: +10pp needs ~281 fights/arm unpaired but
~92-233 paired; +15pp needs ~125 unpaired, ~61-155 paired.

### Read fight data only through `tools/lw_decode.py`

A fight action references a chip or weapon by the generator's `template` field.
`tools/item_get-all.json` is keyed by a *different* id space and the two
overlap, so a naive lookup silently returns the wrong item — an early version
of the diagnostic reported `hat_fedora` and `potion_skin_white` as chips being
cast. There are three spaces:

| | action payload | config / loadout |
|---|---|---|
| chip | `template` (antidote 70) | `id` (antidote 110) |
| weapon | `template` (heavy_sword 36) | `item` (heavy_sword 278) |

The weapon config key is `item`, not `id` — `Generator.java` builds `Weapon`
with the `item` field as its id, and `id` is a third distinct value.
`Decoder.self_test()` pins all of it.

---

## Architectural finding: a scorer weight does not control behaviour

**Chips reach the board by three independent routes, and they do not share a
gate.** Suppressing a weight in `weight_profiles` / `strategic_depth` only
closes one of them:

1. **The scorer** — `scenario_scorer.lk` scales chip valuations by the profile
   weight (e.g. `drScale` for mirror/thorn/bramble).
2. **The greedy TP-recovery pass** — `quickRecoveryChipValue` in
   `unified_strategy.lk` spends leftover TP with *hardcoded* values
   (`isDamageReturnChip -> value += 150`) and never reads the weights at all.
3. **Dedicated scenario templates** — e.g.
   `createDamageReturnCyclingScenario` in `scenario_combos.lk`.

This was found the hard way: cutting the `damageReturn` weight from 415 to 10
flipped **exactly 0 of 120 fights**, with an HP-lead differential of +0.0. Not
noise — bit-identical behaviour, because every cast was coming from route (2).

*If you change a weight and the A/B returns a suspiciously perfect null, you
have probably only closed one of the three routes.* A real change perturbs
something.

---

## vs pure poison / sustain-caster  (e.g. `ladder_eleeksire`)

**Signature.** MAG-heavy, STR ~0, poison chips, cheap high-WIS heal.
Éleeksire: MAG 672, WIS 520, RES 200, 3,233 HP.

### Engine facts that constrain the matchup

- **Poison ignores shields entirely.** `EffectPoison.applyStartTurn` applies its
  value with no shield step and no reflect step; only `INVINCIBLE` zeroes it.
- **Poison therefore ignores damage-return too**, which makes the whole
  thorn/mirror/bramble package inert against a pure caster.
- A weapon switch costs 1 TP (`State.setWeapon` -> `useTP(1)`). On a 4-weapon
  leek that is ~1 TP/turn, and it is easy to omit from TP accounting.

### What actually happens (ED, n=120, 23.3% win rate)

Damage taken is **98% poison** — they barely attack (15 direct damage/turn).
The fight is a race that we lose by a small, consistent margin:

|  | wins | losses |
|---|---|---|
| weapon uses/turn | 1.49 | 1.16 |
| damage dealt/turn | 858 | 701 |
| heal:damage ratio | 0.77 | **0.56** |
| turns dealing zero damage | — | **32%** |

Poison intake is *identical* in wins and losses (6,471 vs 6,654) — nothing
about their offense differs. What differs is our own throughput. 57.6% of our
healing immediately follows a weapon use (lifesteal) and 25.8% is
regeneration, so sustain is proportional to damage output: fewer shots ->
less lifesteal -> dead before the kill lands.

The arithmetic: they hold 3,233 HP and heal ~600/turn with `remission` (5 TP,
CD 1, WIS 520), so net progress is 150-300/turn and a kill takes 11-20 turns.
Their poison does ~670/turn into our 2,510 pool, killing us around turn 11.

### Doctrine

- **Antidote is not the lever.** Median gap between casts is 4.0 turns against
  a cooldown of 4 — already pinned at the cooldown ceiling.
- **TP efficiency is not the lever.** TP ends at 0-3 on 14 of 16 turns. There
  is no surplus to harvest.
- **Suppressing reflect is not the lever either — measured, not assumed.**
  Gating all three routes on the enemy's direct-damage share moved 34 of 120
  fights and gained nothing: 16 won, 18 lost, McNemar p=0.86, HP-lead diff
  +0.1 (t=0.02). The waste is real (~11 damage/turn returned for ~1 TP/turn,
  against ~100 damage per TP from a weapon) but removing it does not change
  who wins, because TP was never the binding constraint.

**What the evidence points at instead:** the race is lost by a small margin, so
only three things can close it — roughly +30% damage, denial of their ~600/turn
heal, or a real cut in poison intake. `liberation` (5 TP, CD 5, strips 40% of
our negative effects) is the one identified gap with headroom: against
~670 poison/turn it is worth ~270/turn, and it is cast at 0.13/turn against a
cooldown ceiling of 0.20. Unmeasured as of this writing.

### The signal, for reuse

`profile['directDamageShare']` (0-100, `enemy_intelligence.lk`) is the fraction
of an enemy's damage potential that is direct rather than poison, published per
turn as `__primaryDirectShare` for code that cannot see the weights. It
separates the classes cleanly with no hand-tuned threshold:

| opponent | direct share |
|---|---|
| Éleeksire | 1.7% |
| Sepignouf | 3.7% |
| Ludaskia | 100% |
| EdsgerDijkstra | 100% |

It replaced an `enemyRes >= 300` gate, which was a proxy for the wrong thing —
RES has nothing to do with whether reflect works, and ladder poison builds sat
just under it (Éleeksire RES 200) and kept paying for reflect all fight.

---

## Negative result: rebalancing the damage/defence scale does nothing

**Tested 2026-09-21. Scaling the defensive terms 100x flips 13 of 120 paired
fights, p=1.00. It is one more valuation change with no effect — not a fix, and
not a disaster either.**

### The observation that motivates the idea

Instrumenting every dimension's contribution to the *winning* scenario shows the
scorer is a damage maximiser regardless of weight profile:

| build | damage | dot | heal | shield | rest |
|---|---|---|---|---|---|
| EdsgerDijkstra (**BRUISER_REFLECT**, burst 118) | 84.6% | 15.0% | 0.1% | 0.0% | 0.1% |
| KurtGodel (**STR_SCIENCE**, burst 304) | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| MargaretHamilton (MAGIC, burst 38) | 90.3% | 9.6% | 0.0% | 0.0% | 0.0% |

Measured scale: **~12,820 score points per HP of damage dealt vs ~9.5 per HP
healed**, about 1,350:1. Lifesteal is no better: `lifestealScore` is 2.0 points
per HP.

**CORRECTION (2026-09-21, same day):** an earlier version of this table labelled
Ed as AGILITY and KurtGodel as TANK_SCI, and argued the asymmetry was proven on
"the build with the highest defensive weights in the codebase
(`shieldValue` 400, `healValue` 280)". Both labels were wrong — verified by
reading `__playerBuildType` out of a live fight rather than inferring it from
the stat line. KurtGodel classifies as **STR_SCIENCE**, whose `burstDamage` of
304 is the *highest damage weight in the codebase*, so damage dominating his
score is expected rather than evidence of a defect. The defensive-rebalance A/B
below was run on that same leek, so it tested a damage profile, not a tank one.

In fact **no leek in the fleet uses TANK_SCI**: detection requires RES >= 300
AND SCI >= 300, and KurtGodel is RES 12 / SCI 524. The profile carrying the
defensive weights is unused. Half the fleet (MargaretHamilton, LeekRain,
DawnFall, DuskHope) runs MAGIC at `burstDamage` 38.

Verify a leek's profile with the `BUILD_<n>` debug line rather than reading
`detectBuildType` against a stat sheet — the priority order (TANK_SCI >
SUPPORT > BRUISER_REFLECT > STR_SCIENCE > MAGIC > HYBRID > AGILITY > STRENGTH)
makes it easy to guess wrong.

It looks exactly like a calibration bug.

### What happened when it was corrected

A `_defScale` knob multiplying the heal/shield terms (1.0 = current behaviour),
KurtGodel vs `ladder_eleeksire`, **paired, n=120**:

| | wins | |
|---|---|---|
| `_defScale` 100 | 23/120 (19.2%) | 7 gained, 6 lost |
| baseline | 22/120 (18.3%) | McNemar **p = 1.00** |

HP-lead differential −2.8 (sd 16.1, t=−1.92) — a weak negative lean, not
significant. Only 13 of 120 fights changed outcome at all.

### DO NOT trust the n=40 sweep that preceded this

The first pass swept n=40 per point and produced 13 → 6 → 5 wins at
1x / 100x / 1000x, which reads as a clean monotone collapse and was briefly
written up as "rebalancing halves the win rate". **It did not replicate.** The
same baseline scores 13/40 on seeds 7000-7039 but 22/120 over 7000-7119; the
100x arm scores 6/40 on the first block and 23/120 overall. The sweep was noise
dressed as a trend.

`matchup_stability.py` had already printed the reason: at this baseline,
detecting a 15pp change needs ~125 fights per arm unpaired. A 5-point sweep at
n=40 cannot resolve anything, and reading a trend off one is how you invent a
result. **Sweep to locate a direction, then confirm with a paired A/B at the
sample size the stability tool prescribes — never publish the sweep.**

### Choose the test subject by its KIT, not by its build label

An earlier sweep ran on EdsgerDijkstra and came back flat — which proved
nothing, because **Ed carries no shield chips at all** and only regeneration +
antidote for healing. The knob scaled `shieldsGained` (always 0 for him) and
`hpGained` (non-zero only on a rare regeneration turn). Before sweeping a
dimension, confirm the leek has chips that produce it: `tools/lw_decode.py`
`Decoder.chip_cfg` + `info()` answers it in seconds.

### What IS still broken, and was left alone deliberately

- **`healValue` is dead code in combat.** It is read only in `scorePuzzle`
  (boss fights). Every `adapted['healValue'] *= ...` in `strategic_depth.lk` —
  the vs-kiter, vs-burst and vs-reflect adaptations — therefore does nothing
  outside boss fights. It is a knob people believe they are turning that is not
  connected. Connecting it is unlikely to help given the result above, but it
  should be connected or deleted rather than left as a decoy.
- **DoT is double-counted.** `totalDamage = damageDealt + dotDmg + novaDmg`
  feeds `damageScore`, then `dotScore` and `novaScore` are added again.

### Related prior evidence (different claim, do not conflate)

`scenario_scorer.lk:833` records a finding from 4,434 mined ladder fights:
top-2000 players win by shielding early and converting to weapons, and lose with
heal-cycling. That is evidence about *heal-cycling behaviour*, not about this
scale factor, and it neither confirms nor refutes the result above.

---

## Kit experiments (2026-09-21): what a ladder audit can and cannot tell you

**Six kit arms, one positive, three significantly negative. The negative ones
were all built on a cross-player chip correlation whose sign was wrong for
defensive chips. The within-player fight data predicted every sign before the
runs finished.**

### The correlation that started it

Top 75 vs bottom 75 of the FR ladder top-300, by chips *carried*:
mobility/buff/denial/summon chips over-represented at the top (manumission
+27pp, jump +20, seven_league_boots +17, doping +16, rage +15, bulbs +13,
reflexes +12); every shield and heal under-represented (fortress -24, armor
-20, remission -19, wall -17, elevation -16, shield/serum/armoring -13..-15).
It looks like "winners don't shield". It is not.

### What the fights say (first 10 turns, within the same players)

Top-ladder solo fights split by outcome: fortress, shield, armor, wall, rage,
reflexes and soporific are all cast **more in the fights they win**; jump,
metallic_bulb, healer_bulb and remission are cast **more in the fights they
lose** (bulbs 0.004/turn in wins vs 0.06 in losses). Short fights (<=15 turns)
are won 56%, long ones 32%. This matches the codebase's own mined rule at
`scenario_scorer.lk:833` ("shield early + convert to weapons; lose with
heal-cycling"). **Who carries a chip and who wins with it are different
questions.** Build kit changes on the second one.

### The arms (paired, vs `ladder_eleeksire`, `tools/kit_ab.py`)

| leek | change | n | wins | flipped | p | HP-lead |
|---|---|---|---|---|---|---|
| Ed KIT | -armoring,elevation,thorn +manumission,7league,reflexes | 120 | 25 -> **36** | 30/19 | 0.15 | **+12.8 (t=2.09)** |
| KG KIT | -fortress,armor,elevation,3 boss chips +manumission,7league,doping,reflexes,**2 bulbs** | 60 | 12 -> 6 | 5/11 | 0.21 | -19.0 (t=-3.11) |
| Ada KIT | -fortress,wall,elevation,armoring,3 boss chips +manumission,7league,doping,**2 bulbs** | 60 | 18 -> 7 | 5/16 | **0.027** | -20.9 (t=-2.37) |
| MH KIT | -armoring,serum,elevation +manumission,7league,**metallic_bulb** | 60 | 42 -> 12 | 2/32 | **~0** | **-43.9 (t=-7.62)** |
| KG KIT2 | keep shields; -3 boss chips,elevation +manumission,7league,doping,reflexes | 60 | 12 -> 10 | 6/8 | 0.79 | -7.0 |
| Ada KIT2 | same shape | 60 | 18 -> 14 | 10/14 | 0.54 | -2.2 |

The only gain came from the one arm that removed no shield and added a buff
winners cast at 0.20/turn. Every arm that dropped shields and added bulbs lost;
keeping the shields (KIT2) removed the harm but produced no gain.

### A whole top-ladder kit transplanted onto our AI loses badly

Alpacake (rank 8, talent 3345, 721 base stat points) has a kit that is
**entirely on the main account already** — every weapon, every chip, both
components. AdaLovelace is a near-exact chassis (base STR 520 vs 515). Her
stats cannot be reduced (the only capital service is `leek/spend-capital`; no
reset exists in the API), so the test was Alpacake's full kit on Ada's stats,
one chip cut to fit her 17 slots:

| | wins | flipped | p | HP-lead |
|---|---|---|---|---|
| Ada (own kit) | 37/120 | 8 gained / 32 lost | **0.0002** | **-20.2 (t=-3.33)** |
| Ada + Alpacake kit | 13/120 | | | |

A kit that carries a player to rank 8 costs *our* AI 20 points of win rate.
Kits are tuned to the AI that drives them; the kit is not the transferable
part. This is the same conclusion the 20-0 / 16-0 finding reached from the
other side, and it is the strongest evidence this project has that **the gap
is how the kit is played, not what is carried.** Stat allocation is not it
either: across the top 300, spread vs concentration correlates with talent at
|r| < 0.14, and our fleet sits exactly on the ladder median (3 stats >= 100).

### The audit itself, with the constraints that matter

- Components: 208 / 300 top builds replicable from main's stock (44 templates,
  ~1,100 units).
- **Forgotten weapons are unlockables, one per farmer** (not market items).
  Applied: 77 of those 208 are blocked; `mysterious_electrisor` alone gates 42,
  `revoked_m_laser` 32. We hold 5 of 9. Two of our leeks can never both carry
  the same one (dark_katana clash between Maelam and LeekOfAir).
- Stat budget <= ours (1,140): **84 survive**. Seven of the top ten need no
  forgotten weapon at all (Alpacake, Alpacare, ChellJohnson, sif, artorias,
  Blasar, Alpacore).
- Chips are also one instance per equip; the bag holds one of each.

### Data gaps closed on the way

- The generator, the AI's `item_database.lk` and the market snapshot all
  lacked 3 live weapons: `plutonium_bazooka` (forgotten, never in the market
  listing), `desert_saber`, `sun_spear`. Seeded from `/weapon/get-all` into
  `data/market_data.json`; the regeneration pair now targets V9 and locates
  its block by content instead of a hardcoded line number. V9 now carries 39.
- Server fights use the same template id space as local ones; only the
  packaging differs (`fight['data']`). `/leek/get` top-level stats are BASE;
  `total_*` are what fights use — `leek_configs.json` was never stale.
- On ladder testbeds **both sides run our AI** and the log has no entity tag;
  tag probes with `getEntity()` or you average our decisions with theirs.

### To reproduce the kit variants

`fetch_leek_configs.py` regenerates `tools/leek_configs.json`, so the `*_KIT`
entries are not committed. Recipes are the drop/add lists in the table above
(chip ids via `Decoder.chip_cfg`, weapons via `Decoder.weapon_cfg`).

---

## What top players DO (5,380 solo fights, 185 accounts) vs what our AI does (500)

Single-chip cast rates barely separate their wins from their losses
(owner-normalised, first 10 turns: jump 0.05/0.05, reflexes 0.05/0.05,
wall 0.12/0.12, armoring 0.19/0.19). The one robust exception is **remission
cast more in losses** (0.163 won vs 0.208 lost) — heal-cycling as the loser
signature, third independent confirmation of `scenario_scorer.lk:833`.

The signal is in **how they play**, not what they cast — measured with three
proxies that need no map geometry (all owner-normalised, first 10 turns):

| behaviour | top players won / lost | **ours** won / lost |
|---|---|---|
| enemy fired no weapon on their next turn, **vs weapon-user opponents** | 0.33 / 0.26 | 0.31 / 0.21 |
| **moved AFTER firing** (hit-and-hide) | **0.32 / 0.27** (STR builds 0.39 / 0.30; vs STR opp 0.36 / 0.26) | **0.13 / 0.14** |
| dealt no damage this turn | 0.42 / 0.48 | 0.25 / 0.35 |

Read across: denial of the enemy's shot discriminates wins for both sides by
about the same margin once conditioned on weapon-user opponents (the
unconditioned gap was partly caster opponents who never fire). Our AI deals
damage on MORE turns than they do. The gap is the middle row: **they fire and
then move; we fire and stand.** We do it at ~40% of their rate, and for us it
does not track outcome at all — it is not a play our AI makes on purpose.
Combos say the same thing about denial: MAG winners pair a shackle with a
poison in the same turn (fracture+arsenic, fracture+venom, stacked slow_down);
losers pair remission with anything.

This is a positioning / scenario-generation lever, not a scoring one — exactly
where seven null valuation changes and the ALPA transplant already pointed.
Position is ~0.1% of scenario score, and `MOVEMENT_HNS` exists as an action
type; whether fire-then-move is rarely generated or generated-and-outscored is
the next question to answer before touching anything.

Method notes: "enemy fired no weapon next turn" is a proxy (dead/finishing
enemies also fire nothing); always condition on opponent archetype. Cover, LoS
and AoE placement proper need the map's cell geometry, not yet derived.
Scripts: `/tmp/ladder/analyze_play.py`, `analyze_wide.py` (to be moved into
tools/ once the geometry work decides their final shape).

---

## Fire-then-move: generated, chosen, and then lost between plan and execution

The doctrine's open question ("rarely generated, or generated and outscored?")
is answered, and the answer is neither.

**It is generated and it wins the turn.** Probing our own candidate pool
(entity-tagged, local, ED vs the two ladder testbeds):

| opponent | our turns | fire-then-move candidate in pool | its score / winner's | its damage / winner's | it WON the turn |
|---|---|---|---|---|---|
| Éleeksire (MAG) | 206 | 64% | median 1.00 (p25 0.88) | 1.00 | **74 / 132 (56%)** |
| Sepignouf (STR) | 74 | 46% | median 0.98 (p25 0.73) | 1.00 | **8 / 34 (24%)**, chosen post-fire **0 / 74** |

So position weight is not the block: the hide candidate scores at parity with
identical damage. Two different failures follow:

1. **vs the STR weapon-user — where denial matters most — it is never the
   post-fire pick.** Parity plus tie-break goes to stand-and-fire every time.
2. **vs the MAG caster it IS picked by the generator, then overridden before
   execution — by the learned re-rank.** Pinned with a stage probe (30 fights,
   28 generator-picked post-fire hides): 13 survived to execution and moved;
   **14 were replaced by `rolloutRerankLearned`** (it ran on 18 of the 28
   turns and overrode the hide on 14 — 78% of the turns it touched); 1 by the
   veto. `validateAndFilterActions` drops none — an earlier attribution of
   "≥21% stripped by the filter" was wrong: the filter's *input* already
   lacked the hide, because the re-rank had swapped the plan upstream.

   This is not a bug. The re-rank flips to a stand-and-fire twin at identical
   score and damage on a P(win)-delta of ≥0.005 — and the learned re-rank is
   the one change in this project that ever measured positive (+7–11pp in
   mirror A/B, p=0.001/0.038). Two valid measurements are in tension: the
   mirror harness rewards standing and firing; 5,380 top-ladder fights say
   firing then moving is what wins. The mirror harness plays V9 against V9,
   so it can only ever reward what V9 already does. **Next experiment,
   deliberately not run without a decision:** `_v9RerankLearnedEnabled` on vs
   off, paired, on the ladder testbeds, scoring BOTH win rate and the
   fire-then-move proxy — the first A/B whose success criterion is a
   behaviour the ladder rewards rather than the harness.

   **Run 2026-09-21, paired n=120, BASELINE = re-rank ON (HEAD), NEW = OFF:**

   | testbed | wins NEW / BASE | flipped | p | HP-lead | fire-then-move NEW / BASE | shot-denial |
   |---|---|---|---|---|---|---|
   | Éleeksire (MAG) | 20 / 23 | 14 / 17 | 0.72 | +1.0 (t=0.23) | **0.170 / 0.128** | +0.025 |
   | Sepignouf (STR) | 120 / 120 | 0 / 0 | 1.00 | +0.0 | **0.003 / 0.003** | −0.012 |

   Three readings. (a) The re-rank's override is real — switching it off
   raises hit-and-hide by a third — but outcome-neutral on a real-opponent
   testbed: **the +7–11pp mirror gain does not transfer.** The mirror harness
   rewarded V9 for what V9 already did. (b) Even with the re-rank off our
   rate is 0.17, half the ladder's 0.32, so the re-rank is not the main
   suppressor. (c) Versus the STR weapon-user — exactly where the ladder
   says denial matters most — we produce a post-fire hide on **0.3% of
   firing turns on both arms** — but Sepignouf is a 120/120 ceiling where
   hiding never matters, so that number is **not** evidence of a generation
   gap (an earlier draft of this line said it was; retracted). Reading the
   composition sites (`base_strategy.lk` 1118 / 1544 / 2744 / 2770): the
   templates ARE fire-then-hide — the `MOVEMENT_HNS` is pushed after the
   attack block — gated only on `findHideAndSeekCell("defensive")` returning
   a cell and that cell being reachable with leftover MP. The surviving
   evidence for under-hiding vs weapon users is the real-fight comparison
   (ours 0.14 / 0.16 vs the ladder's 0.36 / 0.26 against STR opponents).
   To test generation vs STR without a ceiling, measure the proxy on
   `ladder_ludaskia` (STR). **Measured (true null, n=40): we win 16/40 =
   40%** — the fleet matrix's 9/12 was an n=12 upward fluctuation — and our
   **post-fire hide rate there is 0.015**, against the ladder winners' 0.36
   vs STR opponents. Against a STR weapon-user we lose to, we hide after
   firing on 1.5% of firing turns. Ludaskia is the testbed for this gap.

   **Hide-cell selection is not the flaw.** `findHideAndSeekCell("defensive")`
   ranks candidates by `computeDangerForCell` and `evaluateCoverScore`, both
   computed against the enemy's *reachable* cells (`enemyAccess`), not its
   current position, and has no archetype gate. Three suspects remain for
   the real-fight gap (ours 0.14 vs ladder 0.36 vs STR opponents):
   leftover MP after approaching rarely reaches a low-danger cell (the
   `legLen <= playerMP` gate — **verified correct as accounting**:
   `createOffensiveScenario` starts `playerMP` at `_currMp`, subtracts the
   approach leg and any second offensive move, and measures `legLen` from
   the firing cell, so this is a genuine budget limit, not a bug); the
   `_ops89` early return truncates the search; and the **tie-break** — the stage probe found the fire-then-hide
   candidate present on 46% of turns vs Sepignouf at parity score and
   identical damage, yet chosen post-fire on 0/74. The selection compares
   with strict `>` (first-seen wins exact ties). Since the hide variant is generated as a later sibling of the
   no-hide plan, a first-seen tie-break hands every exact parity to
   stand-and-fire.

   **Suspects measured (30 fights each, probe of cell search / ops cut /
   pool / selection) — the tie-break proposal is RETRACTED:**

   | | Ludaskia (STR) | Éleeksire (MAG) |
   |---|---|---|
   | `findHideAndSeekCell` found a cell | 158 / 158 (100%) | 588 / 588 |
   | aborted by the `_ops89` cut | 0 | 0 |
   | post-fire-hide candidate in pool | 34% of turns | 65% |
   | its score / winner's (median) | 1.01 | 1.00 |
   | **it won selection when present** | **17 / 32 (53%)** | 114 / 208 (55%) |

   Cell search: not the block. Ops cut: not the block. Tie-break: not the
   block — the hide candidate scores *above* parity and wins selection more
   than half the time it exists (**correction:** that pool probe counted
   score *ties* as selection wins; the stage probe, which checks the scenario
   actually picked, puts the generator's post-fire-hide pick rate on Ludaskia
   at ~6% of turns, 6 in 30 fights). The executed rate is 1.5%. **The hide
   is discarded after selection, by the learned re-rank on both testbeds:**
   Éleeksire 14 of 15 (veto 1); Ludaskia 4 of 6.

   **Re-rank on vs off, Ludaskia, paired n=120 (seeds 7000–7119):**

   | | wins | flipped | p | HP-lead | fire-then-move | shot-denial |
   |---|---|---|---|---|---|---|
   | OFF (NEW) | **60 / 120** | 10 gained / 2 lost | **0.039** | +2.7 (t=1.05) | 0.023 | 0.526 |
   | ON (HEAD) | 52 / 120 | | | | 0.014 | 0.558 |

   The first significant real-opponent result of the campaign — and it says
   the only feature that ever measured positive (mirror +7–11pp on Margaret
   and Ed) is **worse against a STR opponent we lose to**. Two things to hold
   it to before adoption: it is one testbed on one seed block at p=0.039, and
   the hide rate barely moved, so **hiding is not the mechanism** — the
   re-rank is costing something else vs STR. Across testbeds: Éleeksire
   null (p=0.72), Sepignouf ceiling, Ludaskia OFF better. Confirmation queued:
   Ed on a fresh seed block, then MargaretHamilton and KurtGodel on both
   testbeds, all scored on the proxies. Not adopted without that.

   **Confirmation (paired n=120 each, re-rank OFF = NEW vs ON = HEAD):**

   | leek vs testbed | OFF | ON | flipped | p | HP-lead | fire-then-move | shot-denial |
   |---|---|---|---|---|---|---|---|
   | Ed vs Ludaskia, fresh seeds 7120+ | **62** | 55 | 7 / **0** | **0.016** | +2.6 | 0.020 / 0.009 | −0.02 |
   | **Margaret vs Éleeksire** | **88** | 51 | **48 / 11** | **≈0** | **+30.8 (t=6.97)** | 0.155 / 0.168 | **+0.136** |
   | KurtGodel vs Éleeksire | 21 | 16 | 11 / 6 | 0.33 | +2.6 | 0.357 / 0.326 | −0.02 |
   | Margaret vs Ludaskia | 120 | 120 | 0 / 0 | ceiling | +3.0 | | |
   | KurtGodel vs Ludaskia | 113 | 112 | 1 / 0 | ceiling | −3.2 (t=−2.1) | | |

   **Conclusion: the learned re-rank is worse on every non-saturated
   real-opponent testbed — two significant results, none against, and the Ed
   result replicates on a seed block it never saw.** The leek the mirror A/B
   credited with +11pp (Margaret) loses 31 points of win rate to the re-rank
   against the poison archetype that caps our rank. The mechanism is not
   hiding (rate flat) but **shot denial**: on Margaret vs Éleeksire the share
   of turns after which the enemy fired nothing rises 0.58 → 0.72 with the
   re-rank off. The re-rank was overriding plans that denied the enemy's
   next shot in favour of stand-and-fire twins at equal score.

   **Why the mirror harness got it backwards:** mirror A/B plays V9 against
   V9, so a change that makes V9 better at beating V9's own habits scores as
   a win even when it makes V9 worse against opponents who play differently.
   The mirror harness is not evidence for adoption; ladder testbeds with the
   behavioural proxies are.

   **Recommendation:** set `_v9RerankLearnedEnabled = false` fleet-wide and
   upload. Left at the committed state (ON) pending the decision. Watch-out
   on adoption: KurtGodel vs Ludaskia leans −3.2 HP (t=−2.1) on a 94% ceiling
   — worth a look on the real ladder, not a reason to hold. (The
   `createOffensiveScenario` MP-gate probe never fired: that template is not
   the one producing these hides.)

This is the same signature as the morning's category-D turns (plan predicted
damage, nothing executed). The lever is the plan->execution path, not a weight.

### Synergy: we also under-use the buff -> fire pattern

| per turn, first 10, owner-normalised | top players won / lost | ours |
|---|---|---|
| offensive buff cast BEFORE firing / firing turns | 0.28 / 0.26 | **0.09 / 0.09** |
| shots in an adrenaline turn | 0.66 / 0.57 | 0.37 / 0.22 |
| shots with / without a preceding buff | 1.84 / 2.01 | 1.47 / 1.57 |

We buff-then-fire at a third of their rate and convert adrenaline into fewer
shots. Caveat: for them it barely discriminates wins (0.28 vs 0.26) and a
buff costs a shot that turn; no (buff -> weapon) pair exceeds +0.005/turn.
A frequency gap, not a proven win lever. Tool: `tools/ladder_synergy_analysis.py`.

### Is the deployed AI the one we measured?

Our 500 real solo fights were played by the server copy uploaded 2026-09-21
11:03 UTC. `strategy/base_strategy.lk` on the server is byte-identical in
size to HEAD (126,307 chars), and the strategy/scorer files last changed in
HEAD on 2026-08-20, so the behavioural comparison is against the same
decision logic. The server reports `main.lk` as ~1.5 MB / 35,787 lines: that
is the include-resolved size it computes after compiling, not a separate
bundle (`upload_v9.py` does not bundle) — verified below.

---

## The lever above the re-rank: parity ties, and a threat model blind to denial

The tie-break retraction above was wrong — it rested on the pool probe that
counted ties as wins. A corrected probe compares **final** scores (post-2-ply
where present) of the winner and the best post-fire-hide sibling:

| | Ed vs Ludaskia (32 turns) | Margaret vs TheLeaker (199) |
|---|---|---|
| hide final / winner final, median (p25–p75) | **1.000** (1.000–1.000) | 0.852 (0.471–1.000) |
| **exact ties (within 0.1%)** | **75%** | **44%** |
| hide strictly higher | **0%** | **0%** |
| hide gives up damage | 12% of turns | 8% |
| **hide cell safer by adversarial threat** | **0% of turns** | **17%** |

So: on parity the strict `>` at every selection site hands the turn to the
first-seen stand-and-fire plan, and the learned re-rank then overrode most of
the remainder. That is the whole selection story, and it is why re-rank OFF
helps everywhere.

The deeper fact is *why* it is parity — and the first explanation written
here ("the threat cache is blind to denial") was **wrong**. Measured on the
same cells at the moment the hide is picked:

| | Ed vs Ludaskia (113 picks) | Margaret vs TheLeaker (255) |
|---|---|---|
| picker: hide cell lower danger than current | 75% | 75% |
| **scorer: adversarial threat lower at hide cell** | **40%** (median 0 vs 191) | **69%** (475 vs 1306) |
| adversarial threat **zero at both cells** | **42%** | **23%** |

The cache does see the hide as safer most of the time. Parity has two other
causes: the threat/position term carries ~0.1% of score weight (the scale
asymmetry), and on a quarter to two-fifths of turns the cache predicts the
enemy can reach *neither* cell — i.e. it believes standing cannot be
punished, while 5,380 ladder fights say it is. That is a **calibration gap
in predicted next-turn enemy reach**, not line-of-sight blindness.

**Tie-break experiment, first attempt — broken, not null.** A hide-preferring
break on `score == bestScore` ran 960 paired fights across the panel and
Ludaskia and produced **zero flips and zero proxy change** — bit-identical,
the "perfect null means a half-closed gate" signature this document already
warns about. The ties measured above were *within 0.1%*, not equal floats;
float `==` never fired. **Second attempt, 0.1% relative band with a fire-count
guard: the branch fired 0 times in 6 fights** (the chain then failed to
abort and was killed by hand — every chain now uses an explicit
`|| {{ revert; exit 1; }}` plus `trap revert EXIT` instead of `set -e`).

**Why neither can fire — the parity claim was an artefact.** A gap probe at
the three selection sites, logging every hide candidate against the
incumbent *at the moment of comparison* (10 fights, 33 evaluations):

| site | evals | cand above incumbent | within 0.1% below | >0.1% below | median rel. gap |
|---|---|---|---|---|---|
| 1 base score | 11 | **0** | 3 | 8 | **−34%** |
| 2 two-ply | 8 | **0** | 1 | 7 | −23% |
| 3 finalScore | 14 | **0** | 2 | 12 | −24% |

The "75% / 44% exact ties" above counted the eventual winner as its own
hide twin (ratio 1.000 trivially). Against a non-hide incumbent the hide
plan sits **a quarter to a third lower**. There are no ties to break; the
tie-break is dead. The question is now **which dimension prices a post-fire
hide at −25–35%**: a second shot forgone, the position term, or 2-ply
projecting less next-turn damage from the hide cell. **Measured — none of
them.** Pairing the best non-hide and best hide-shaped scenario scored on
each turn (43 turns, MH vs TheLeaker + Ed vs Ludaskia), median per
dimension:

| dim | non-hide | hide | |
|---|---|---|---|
| total | 1,116,821 | 1,103,121 | **~1% apart** |
| damage | 326,089 | 321,380 | −1.5% |
| DoT | 249,955 | 249,955 | equal |
| TP-efficiency | 278,131 | **348,165** | hide +25% (23 TP for the same damage) |
| position / threat / heal / shield | equal | equal | threat ≈ 0.06% of total |
| 2-ply bonus | 0 | **+154** | favours the hide |

So the hide *shape* is not what scores 25–35% lower. What trails by 25–35%
at the selection sites is the **unmutated hide sibling in the pool**, and
the incumbent it loses to is the **mutation planner's winner** — scored
first at quick-score 9999, refined, buffed. Hide-shaped plans that score
within 1% of it exist only *inside* `HybridMutationPlanner.planWithMutations`,
which returns exactly one scenario; its runners-up never reach the pool,
so 2-ply (which favours the hide) and final scoring never get to compare
them. Hypothesis to test next: the planner's internal top-3 contains a
hide-shaped plan within 1–2% of its winner on most turns. If so, the lever
is a **candidate-set** change — return the best hide-shaped runner-up
alongside the winner — exactly the "proposal ceiling" the SWOT named, and
not a weight.

**Measured — the planner is not the wall.** Inside `planWithMutations`
(10 fights, 64 calls): the winner it returns is **hide-shaped on 41%** of
calls; 2,174 hide-shaped mutants were compared against the running best,
69 beat it, 412 sat within 2%; on **77% of turns** with a hide candidate the
best one was within 2% of the planner's final winner. Yet the eventual pick
(measured at `s0gen`, before the re-rank) is hide-shaped on ~6%. So the
hide-shaped planner winner is **beaten in the pool selection** by an
unmutated non-hide seed — by the ~1% the composition probe showed: 1.5%
more damage (one extra TP on attack) against a denial benefit the scorer
prices at ~0.06%. This is the damage-dominance asymmetry biting at the
margin where the ladder's winners take the opposite trade.

It also explains the failed tie-break: the real gap is **1–2%**, not 0.1%.
The 0.1% band could not see a single one of the 412 mutants within 2%.
Next experiment: the same hide-preferring band at **2%**, fire-count
guarded, local A/B on the panel + Ludaskia with the proxies.

**Run: the 2% band fired 0 times in 6 fights.** The explicit guard aborted
the chain and the trap reverted the tree within minutes (the pattern that
replaced `set -e` paid for itself on its first outing). So the band is
wrong-*sided*, not wrong-width. Reading the two probes together, selection
has two regimes: when the incumbent is the planner's **hide** winner (41%
of planner calls), nearby hide candidates have nothing to prefer over it;
when the incumbent is non-hide, hide candidates trail by 23–34%. The
41% → ~6% collapse must therefore be **non-hide candidates overtaking a
hide incumbent** — the ~1% edge the composition probe showed — a
comparison the gap probe never logged because it only recorded hide
*challengers*. Measured next: every non-hide overtake of a hide incumbent,
with margin and site. If those margins are ~1–2%, the right experiment is
the **inverse** band — a non-hide challenger must beat a hide incumbent by
more than the band to displace it.

**Measured: 2 overtakes in 10 fights.** Non-hide candidates almost never
displace a hide incumbent. The inverse band is dead — the fourth
selection-layer margin hypothesis in a row (tie-break, threat-blind cache,
planner runner-up, inverse band) killed by measurement. What fits every
probe at once: the planner's hide winner never *becomes* the incumbent,
because it fails the **feasibility gate** (`feasible` at the pool stage —
the NET-TP check, Fix #1B). That would produce zero hide challengers near
a non-hide incumbent (the hide was filtered before comparison), zero
overtakes (it was never incumbent), the 41% → ~6% collapse, and the
morning's "plan predicted damage, nothing executed" turns. Measured next:
every site-1 candidate's hide flag and feasibility, and whether the
planner's index-0 winner is hide-shaped and infeasible.

**Measured — this is the mechanism** (10 fights, 458 site-1 evaluations):

| | candidates | **infeasible** | median dropped actions | median TP / MP spent |
|---|---|---|---|---|
| non-hide | 328 | 76 (23%) | 1 | 20 / 5 |
| **hide-shaped** | 130 | **115 (88%)** | 1 | 25 / 4 |
| planner's winner (index 0), hide-shaped | 26 | **24 (92%)** | | |

On **8 of 14 turns every hide candidate was infeasible** — eliminated by
the gate before any comparison. `feasible` is
`netTP <= tpBudget && simResult.droppedActions == 0`, and `droppedActions`
counts actions the **simulator** dropped because `canExecuteAction` said no
— a trailing hide move it will not simulate. One dropped move voids the
whole plan. This reconciles every probe: no hide challengers near a
non-hide incumbent (filtered first), no overtakes (never incumbent),
planner 41% → pick 6%, and the morning's "plan predicted damage, nothing
executed" turns. Not a weight, not a tie-break: **a plan the planner builds
and the simulator refuses.** Next: instrument the drop — required MP vs
simulated MP remaining, TP remaining — to tell a true MP shortfall (fix the
planner's MP accounting) from a planner/simulator mismatch (fix the
simulator).

**Measured: 2,324 refused hide moves — 98% genuine MP shortfalls**
(median 4 MP left after the attack, hide leg needing median 10), **0**
planner/simulator mismatches. The simulator is right. The defect is where
the hide cell comes from: `getHideAndSeekAction(mpBudget)` uses its budget
only as `if (mpBudget <= 0) return null`, then returns a per-turn cached
cell that `findHideAndSeekCell("defensive")` picked from
`getAccessibleCells(player)` — **cells reachable with full MP from the
pre-move position** — and that cell is appended to plans *after* an
approach and attack have spent most of that MP. The globally safest cell is
~10 steps away; the plan has 4. The ladder's winners hide with the MP they
have left. **Fix: bound the hide cell by residual MP from the plan's
post-attack position at insertion** (fall back to the best reachable cover
cell rather than the best cell). Not a weight, not a tie-break; a
reachability bug in candidate construction — the "proposal ceiling" made
concrete. To be A/B'd locally on the panel + Ludaskia with the proxies, with
a guard that the number of feasible hide plans actually rises.

**Measured: the MP-bounded hide fix (`docs/patches/hide_mp_bounded_v2.patch`,
three files, ~70 lines).** `findHideAndSeekCell` takes an `origin` and
`mpBound`, and filters the existing full-MP candidate list by cached path
length from the plan position (bounded by the list, not the board -- a
board-scan variant was also written but never measured: both variants first
failed to compile because a stale `return null` was left after the new
return, `CANT_ADD_INSTRUCTION_AFTER_BREAK`, AI dead, smoke 0W/3D -- which
was first misread as "fix ineffective"). All 12 `getHideAndSeekAction`
call sites in the combos pass `simPos`; results are memoised per
(position, budget).

*Guard passed:* post-fire hide plans feasible at site 1 went from **12% to
77%** (63 of 82, 0 errors, 8 fights). The proposal ceiling is lifted.

*Paired A/B, fix vs HEAD, n=60 each, `-j 2` (`-j 4` was OOM-killed):*

| opponent | NEW | HEAD | gained / lost | p | HP-lead | fire-then-move | shot-denial |
|---|---|---|---|---|---|---|---|
| Ed vs Ludaskia | 23 | 23 | 2 / 2 | 1.0 | +2.1 | +0.040 | -0.001 |
| Margaret vs TheLeaker | 24 | 22 | 7 / 5 | 0.77 | +4.9 | +0.004 | +0.005 |
| Margaret vs ReauBotcode | 4 | 4 | 3 / 3 | 1.0 | +11.2 (t=2.7) | +0.013 | +0.051 |
| Margaret vs BretzelLeekide | 46 | 40 | 8 / 2 | 0.11 | +8.7 (t=2.2) | +0.032 | +0.017 |
| Margaret vs Hydrogène | 23 | 20 | 4 / 1 | 0.38 | +7.9 (t=2.8) | -0.025 | +0.028 |
| **Margaret pooled (n=240)** | **97 (40.4%)** | 86 (35.8%) | **22 / 11** | **0.080** | **+8.2 (se 1.8, t=4.5)** | +0.006 | +0.025 |

Reading: every arm is >= HEAD on wins and positive on HP-lead; the pooled
win-rate gain (+4.6pp) misses 0.05 while the HP-lead gain is unambiguous
(t=4.5). Ed is unchanged (his hide budget after a Ludaskia approach is
rarely non-zero). The fire-then-move rate barely moves (+0.006) even though
feasible hide plans went 12% -> 77%: the plans now survive the gate but are
still out-scored -- so the *second* half of the ceiling is the scorer, not
the proposal. The fix is a correctness repair (a plan the planner builds and
the simulator refuses is a bug regardless of the A/B) with a small,
consistent, real-opponent gain and no measured harm. Recommended to adopt;
independent of the held re-rank flag. A larger sample (n=120 on the two
best arms) would settle the win-rate p if wanted before a server deploy.

**Adopted 2026-09-21** (commit `1016fe2b`, uploaded to `9.0/V9/`).

### After the gate: why the surviving hide plans still lose (the scorer, measured)

Term-by-term probe (ten cumulative snapshots inside `score()`, logged for
every feasible candidate at site 1, 8 fights on the panel + Ludaskia; pick
vs the best feasible post-fire hide plan on the same turn):

| | Margaret (23 turns) | Ed (5 turns) |
|---|---|---|
| hide plan picked | 4 | 3 |
| median score gap pick − hide | 986,826 | 40,024 |
| gap from damage term | 249k (63% of turns >0) | 25k |
| gap from eff/buff/denial/synergy | 231k (100%) | 15k |
| gap from position | −301 (hide slightly better) | −753 |
| gap from death/threat | **0** | **0** |
| adversarial threat at final cell, pick vs hide (median) | 1928 vs 1928 | 199 vs 199 |

The hide plans that survive are **weaker attack sequences with a hide
appended** (the templates give the move 50–70% of MP and the attack a
reduced budget), so they lose on damage by an order of magnitude more than
any positional term can pay. And their hide cell is no safer than the
pick's: same threat. When a hide plan carried the *same* damage it was
picked (7 of 7 such turns). So the scorer is not the ceiling either; the
candidate set is — there is no "the pick, plus a hide" candidate.

### Is hiding actually worth anything against these opponents? (measured)

End-of-turn probe, 113 turn pairs, 20 fights (Margaret vs TheLeaker,
BretzelLeekide, Hydrogène; Ed vs Ludaskia): our cell, enemy cell, LoS,
cache-predicted threat, HP now vs HP at our next turn start.

| end of our turn | n | damage taken on the enemy's turn (median / mean) | took 0 |
|---|---|---|---|
| enemy has LoS to us | 64 | 846 / 883 | 8% |
| enemy has **no LoS** (hidden) | 49 | **0 / 310** | **63%** |
| hidden and dist ≥ 8 | 40 | 0 / ~330 | 64–71% |

Ending hidden is worth ~570 HP per turn on average against the STR
opponents that set Margaret's ladder. The adversarial threat cache is
**calibrated, not blind**: cells it rates 0–300 took a mean 316 (23 when
hidden); cells rated 1500–2500 took 1093 (it over-predicts by ~2x there,
being a max over enemy positions, but the ordering is right). So a hidden
cell already scores lower on threat, death and cover — the scorer would
prefer it if it were offered.

### The unused hide (measured — this is the lever)

Same probe, 100 turns, at the end of each turn with leftover MP:

| | Margaret (85 turns) | Ed (15) |
|---|---|---|
| ended hidden | 29% | 33% |
| ended exposed with a no-LoS cell within leftover MP **by path length** | **77%** | **70%** |
| turns with a firing cell | 68% | 53% |
| …of which a fire-AND-hide cell existed (fire cell + no-LoS cell within remaining MP) | 98% | 100% |
| MP left at end of turn (median) | 4 | 2 |

Three of four exposed turns could have ended hidden with the MP we had
left, with the plan otherwise unchanged. The ladder's fire-then-move is
not a different plan; it is the same plan plus the move we throw away.

**Fix under test: hide-append pass** (`_v9HideAppendEnabled`, unified
strategy, after the base scoring loop): for the top-5 feasible plans that
leave MP and do not already end in a hide/flee, clone the plan, append an
MP-exact `MOVEMENT_HNS` to the lowest-threat no-LoS cell reachable from
the plan's final position (`findLosBreakCell`; never a cell the cache
rates worse than staying), simulate, score, and let it compete for the
pick and for 2-ply. Smoke stage must show it winning selection at least
once before the A/B runs (a change that cannot be shown to fire is not an
experiment).

*Smoke:* 24 turns, 40 hide variants added, 4 won selection (fires; ~10%).

*Panel 1 (paired n=60 each, seeds 7000+, `-j 2`, baseline = HEAD which
already carries the MP-bounded fix), patch `docs/patches/hide_append_v1.patch`:*

| opponent | NEW | HEAD | gained / lost | p | HP-lead | fire-then-move | shot-denial |
|---|---|---|---|---|---|---|---|
| Ed vs Ludaskia | 23 | 22 | 1 / 0 | 1.0 | +0.7 | +0.011 | +0.006 |
| Margaret vs TheLeaker | 24 | 21 | 7 / 4 | 0.55 | −1.0 | **+0.127** | +0.013 |
| Margaret vs ReauBotcode | **13** | 4 | **10 / 1** | **0.012** | +1.0 | **+0.117** | +0.061 |
| Margaret vs BretzelLeekide | 45 | 46 | 3 / 4 | 1.0 | +4.3 | **+0.169** | +0.030 |
| Margaret vs Hydrogène | 18 | 20 | 3 / 5 | 0.73 | −2.6 | +0.084 | +0.017 |
| **Margaret pooled (n=240)** | **100 (41.7%)** | 91 (37.9%) | 23 / 14 | 0.19 | +0.2 | **+0.124** | +0.030 |

Reading: the behaviour moved to where the ladder is (fire-then-move
0.21–0.29 → 0.33–0.41, the top-player band), and the one opponent she was
losing 4/60 to went to 13/60 (p=0.012). But the pooled win-rate gain
(+3.8pp) is within noise and, unlike the MP-bounded fix, the **HP-lead did
not move (+0.2)** although the probe said a hidden end costs the enemy
~570 HP/turn. Either the appended hides are the shallow ones (in current
LoS shadow but inside the enemy's reach — the cache-rated 1500–2500
bucket that still took 1093), or the hide costs us next-turn damage by
moving us off our firing cell. A paired end-of-turn probe (same seeds as
the HEAD probe: damage taken AND dealt per turn) and a second fresh-seed
panel (seeds 7100+, pooled to n=480) are running to separate the two
before any adoption call.

*Paired end-of-turn probe (same 20 seeds as the HEAD probe):* Margaret
ends hidden 42% → 48% of turns, **damage taken per turn 714 → 602**,
damage dealt per turn unchanged (25 → 56, noisy: poison vs. their heals),
fights 7.5 → 8.3 turns. So the hides are real and do not cost damage; the
flat HP-lead in panel 1 was the small effect at n=240.

*Panel 2 (fresh seeds 7100+):* pooled **103 (42.9%) vs 88 (36.7%)**,
gained 27 / lost 12, **p=0.024**; BretzelLeekide 46 vs 38 with **8 gained
/ 0 lost** (p=0.008); TheLeaker the one flat arm (25 vs 26).

*Both panels pooled (n=480):* **203 (42.3%) vs 179 (37.3%), gained 50 /
lost 26, McNemar p=0.0079**; fire-then-move +0.116; shot-denial +0.034.
Ed vs Ludaskia: 27 vs 26 and 23 vs 22, no harm.

**Adopted 2026-09-21** and uploaded to `9.0/V9/`. Together with the
MP-bounded fix, Margaret's STR panel went from 35.8% (morning HEAD) to
~42% on the same opponents. The learned re-rank flag is untouched (held).

What this settles about "the scorer": it was never the ceiling. The
23-dimension scorer is calibrated on threat and already prefers a hidden
end; the ceiling was that no candidate ever offered *the chosen attack
sequence plus the move we had MP for*. The two fixes are both candidate
construction. The next ceiling of the same kind is the firing cell: 98% of
turns had a fire-AND-hide cell, and the tactical cell chooser
(`findBestTacticalCell`: damage − threat×w − path) does not know whether a
hide exists within the MP it leaves — a retreat-aware firing cell would
let the append pass fire on the turns where the current pick leaves
nothing to hide behind.

### Retreat-aware firing cell: three variants, all negative (2026-09-22)

`findBestTacticalCell` scores `damage − threat×w − path×2`. Diagnostic
(one fight each, Margaret/TheLeaker and Ed/Ludaskia): its threat term is
`enemyThreatMap`, **flat and tiny** (342 on every cell for Margaret, 18–41
for Ed) against damage values of 2,000–6,000 — threat never decides the
firing cell. The adversarial cache rates the no-LoS cells within reach
(1303–1357) about as dangerous as the firing cell (1306–1648).

| variant | picks changed | Margaret: ended hidden | damage taken / turn | dealt / turn | wins (15 paired) |
|---|---|---|---|---|---|
| HEAD (both hide fixes) | — | 48% | 602 | 56 | 10 |
| v1: replace threat by retreat-cell threat | **0** of 77 | — | — | — | — |
| v2: +300 bonus, retreat by `getCellDistance` | 13 of 387 | 46% | 656 | 58 | 10 |
| v2: +1000 bonus | 84 of 371 | 40% | 696 | 34 | 8 |
| v3: +500, retreat by **exact path**, top-8 re-pick | 169 of 375 | 41% | 679 | 51 | 7 |
| v3: +1500 | 219 of 397 | 40% | 689 | 32 | 9 |

Ed (5 paired): v3 raised his hidden-end rate 50% → 80% / 62% and damage
dealt 438 → 589 / 660, but also damage taken 156 → 182 / 250; 2 wins vs 1,
too few to read. Margaret is the leek the lever was for, and every
variant that changed her picks made her end hidden *less* often and take
*more* damage on the same seeds.

Two traps recorded: (1) a LoS-break cell is usually across the obstacle
that blocks the path — bounding the retreat by `getCellDistance` picks
cells that are one step away and five steps to walk (v2); (2) fixing that
(v3) did not help, so the failure is not the bound. The chooser is one
movement provider among several, its `maxMP` is a template's movement
budget rather than the MP the final plan leaves, and the firing cell it
prefers for a retreat changes which attacks the plan can make — the
scorer then picks a different plan whose end is *not* hidden. A
chooser-level heuristic cannot see any of that; the two fixes that worked
both added candidates and let the full simulation + scorer decide.

**Not adopted.** If the firing cell is to be revisited, the
pipeline-shaped version is: emit the top-2/3 tactical cells as separate
scenario variants (not one heuristic pick), so "fire from the cell with a
retreat, then hide" exists as a fully simulated candidate and the scorer
judges the whole turn. Cost is scenario count; to be measured with the
same probe before any A/B.

### Multi-cell scenario variants: null (2026-09-22)

Built as a mutation (`MoveCell`, `docs/patches/multicell_move_mutation_v1_NULL.patch`):
for each planner seed, retarget its first offensive/approach move to the
two runner-up tactical cells (`findTopTacticalCells`, same base score as
the chooser) and let the full simulation + scorer + hide-append judge. It
fires: 9 MoveCell mutations became the planner's best in the 4-fight
smoke. Paired 20-seed probe: Margaret hidden 48% → 49%, taken 602 → 608,
dealt 56 → 39 — nothing. Ed hidden 50% → 62%, dealt 438 → 571, taken 156
→ 148 on 5 fights.

| pooled, two panels | NEW | HEAD | gained / lost | p | HP-lead | fire-then-move |
|---|---|---|---|---|---|---|
| Margaret STR panel n=480 | 206 (42.9%) | 209 (43.5%) | 16 / 19 | 0.74 | −1.1 (t −1.5) | −0.002 |
| Ed vs Ludaskia n=60 | 22 | 22 | **0 / 0** | 1.0 | +0.0 | +0.000 |

Bit-identical for Ed, 35 flips in 480 for Margaret with no direction.
The runner-up firing cells, judged by the full pipeline, are simply not
better: once the plan can already append its own hide, *which* firing
cell it fires from carries no further value against these opponents.
**Not adopted; tree reverted.** The firing-cell lever is closed both
ways (heuristic: harmful; candidate: null).

Where Margaret's remaining 57% of losses on this panel live is now the
open question, and it is not positioning. Next measurement should be the
loss autopsy on the current build (turn of death, HP trajectory, whether
the poison landed, what the STR opponent did on the killing turns) --
the same panel, the losses only.

### Loss autopsy, Margaret vs the STR panel (2026-09-22, 120 fights, current build)

`tools/loss_autopsy.py` on 30 fights per opponent (seeds 7200+), wins vs
losses side by side. Record: TheLeaker 10/30, Hydrogène 16/30,
ReauBotcode 4/30, BretzelLeekide 19/30.

Shape of every fight: both sides fire on turn 1; fights last 6–10 turns;
the HP-lead is negative from turn 1 in wins AND losses (−5 to −30 by
turn 3) because the STR opponent's direct damage lands first and our
poison ticks later. Wins are races the poison catches up in around turn
6–7; in losses we die at turn 7–9 with the enemy at **48–68% HP**. So a
loss is not a close race lost; it is a race we were never in.

| per turn, wins vs losses | Bretzel | Hydrogène | ReauBotcode | TheLeaker |
|---|---|---|---|---|
| damage taken, turn 4+ | 710 / 1011 | 770 / 964 | 693 / 945 | 624 / 802 |
| poison dealt per turn | 819 / 661 | 951 / 698 | 926 / 778 | 1066 / 888 |
| enemy healed per fight | 2717 / 3757 | 4115 / 4400 | 4789 / 4856 | 5464 / 6764 |
| enemy antidotes per fight | 1.4 / 2.2 | 1.3 / 1.7 | 1.8 / 1.9 | 1.4 / 2.2 |

**The antidote is the mechanism.** Enemy antidote cadence is exactly
every 4 turns (84 of 93 gaps; chip cooldown 4) and they cast it the
first turn it is ready while poisoned. Queued poison wiped per fight vs
poison that actually landed:

| | wins | losses |
|---|---|---|
| Bretzel | 1656 wiped / 5431 landed (30%) | 5238 / 5169 (**101%**) |
| Hydrogène | 4804 / 7129 (67%) | 5000 / 5334 (**94%**) |
| ReauBotcode | 6531 / 8334 (78%) | 7407 / 6347 (**117%**) |
| TheLeaker | 4042 / 9380 (43%) | 7928 / 8476 (**94%**) |

In losses the antidote wipes as much poison as lands — roughly twice the
enemy's max HP per fight. And our casting is not synchronised with the
cadence: queued poison cast in the 2 turns before an antidote equals
that cast in the 2 turns after (602k vs 593k value·turns); 56% of our
queued poison is cast with ≤2 ticks available; covid/plague (7-turn)
are cast at 0–1 ticks left 24–32 times each.

*Cooldown semantics, probed live:* with the enemy's antidote cooldown
reading `c` on our turn (`getCooldown(CHIP_ANTIDOTE, enemy)` is exact for
enemies), a poison cast now ticks **max(1, c)** times, then is wiped.
The scorer's `calculateAntidoteMultiplier` already reads that cooldown,
but multiplies the *full* queued value (0.4–0.7× at c=0), so a 7-turn
covid at c=0 is still valued at ~3.9 ticks against a true 1 — a 4×
overvaluation that lets it outscore a shot.

**Fix under test: antidote-aware poison cap** in the simulator
(`_v9DotCapEnabled`): each poison source's queued damage and duration are
capped at max(1, c) ticks when the target carries antidote. Downstream
scoring (dot weight, multiplier, lifetime bonus, continuation) is
unchanged; the scorer just sees the poison that can land. Gate: the 120
seeds above re-run paired against these HEAD fights (wins, wiped/landed),
then a fresh-seed panel.

*Result:* the cap fires thousands of times per fight and changes almost
nothing she casts — every damage source Margaret owns is poison, so the
cap lowers every plan by the same factor and the pick stays. Paired: 120
autopsy seeds 53 vs 49 (8/4, p=0.39); fresh panel n=240 108 vs 102
(14/8, p=0.29, HP-lead +2.3 t=2.3); Éleeksire 49 vs 46 (4/1). All 420
paired: gained 26 / lost 13. Consistent, small, not adoption-grade alone;
**held uncommitted** (`_v9DotCapEnabled` in the working tree). The lever
the autopsy found is a turn shape (deny + hide at antidote cooldown 0–1,
dump at 3–4), not a price.

## Fleet loss autopsy on REAL solo fights (2026-09-22)

`data/ladder/our_solo.json`: 125 real ladder fights per main leek
(AdaLovelace, EdsgerDijkstra, KurtGodel, MargaretHamilton), same action
format as local fights, plus the map. Run through `tools/loss_autopsy.py`
and an exact geometry port of the generator (`tools/lw_geometry.py`:
cell→(x,y), getCellDistance, `verifyLoS` with the same Bresenham walk and
entity rules).

**Who beats us (all four leeks):** ranged-STR users (rhino, lightninger,
m_laser, enhanced lightninger) — 85 W / 118 L = 42%; melee opponents 38
W / 19 L; poison ~55%. Losses across the fleet are longer, we take ~30%
more per turn and deal less, and the share of our turns with no shot
rises (Ada 24%→36%, Ed 31%→39%, KG 20%→36%).

**No-shot turns in losses, by exact geometry** (a "firing cell" = walkable,
unoccupied, in range of a weapon we used that fight, with LoS; MP bound
by distance, so this bucket is an upper bound):

| leek | no-shot turns in losses | shot from start cell | firing cell within MP | none possible |
|---|---|---|---|---|
| AdaLovelace | 289 | 43 (15%) | 129 (45%) | 117 (40%) |
| EdsgerDijkstra | 97 | 30 (31%) | 24 (25%) | 43 (44%) |
| KurtGodel | 207 | 20 (10%) | 101 (49%) | 86 (42%) |
| MargaretHamilton | 126 | 13 (10%) | 20 (16%) | 93 (74%) |

Of the turns where a shot existed, TP was still affordable after the
chips cast (median 20 TP left): Ada 150/172, KG 98/121, Margaret 24/33;
Ed 17/54 (Ed spends his TP on buffs first). The exact, unarguable subset
— shot from the start cell, LoS, TP affordable, none fired:

| leek | per loss | per win | what was done instead |
|---|---|---|---|
| **AdaLovelace** | **0.57** (losses last 15.5 turns) | 0.12 | move, knowledge, armoring, steroid+vaccine+wall, regeneration+wall |
| KurtGodel | 0.22 | 0.03 | nothing (3), regeneration, rage, fortress+knowledge |
| Margaret | 0.10 | 0.08 | regeneration+serum |
| Ed | 0.07 | 0.12 | — |

Ada is the fleet's clearest case: long losses to ranged STR in which she
turtles (wall 4.7, fortress 3.8, knowledge 3.7, steroid 3.3, vaccine 3.0
per loss vs 3.3/2.4/2.6/2.3/2.1 per win) with 20 TP unused on turns a
heavy-sword/lightninger shot was on the board, 63 of those 150 turns at
HP ≥ 70%. KurtGodel's losses end with the enemy at 25% (his are the
closest races) and include turns with literally no action. No AI error
(1002) in any of the 500 fights. Local reproduction (Ada/KG vs the
ranged-STR ladder configs, per-turn probe of TP left, damage-map cells,
state and the chosen plan) is running to see the decision from the
AI's side.

**Local reproduction (Ada, KurtGodel vs Hydrogène/TheLeaker/Ludaskia, 48
fights, per-turn probe of TP left, damage-map cells, state and the chosen
plan's action types):** a new metric, *plan had an attack, nothing
fired*: Ada 22 of 426 turns, KG 18 of 248. On those turns the executor
logged `FLT ... c162 ... Out of range/LOS` and `EXEC ... STALE_TARGET_SKIP`:
chip 162 is the **grapple**. The three grapple-combo templates
(heavy sword, axe, ranged) aimed the grapple at the cell *next to the
player*, checked only "same line", never the chip's 2–8 range or LoS to
the enemy; the simulator validated range against the adjacent aim cell,
so the plan simulated as two free sword hits (quick-scorer +2000 for the
grapple and a combo bonus: COMBO family topped the pool 75 times in 24
Ada fights), and the executor — which validates push/pull chips against
the enemy — rejected it every time. **0 grapple casts in Ada's 125 real
fights**, with 20+ TP left on those turns. Ada and KG both carry grapple.

*Fix (adopted 2026-09-22, `docs/patches/grapple_templates_fix.patch`):*
require 2 ≤ dist ≤ 8, same line via the validator's own helper, and LoS
to the enemy; aim the grapple at the enemy's cell (as the covid combo
already did). Local: Ada 22 → 12 wasted-attack turns on the same seeds;
KG unchanged (his 18 are a different cause). Paired A/B vs HEAD, n=60
each: Ada vs TheLeaker 50/47 (5/2), Ludaskia 54/53 (3/2), Hydrogène 1/1
(0/0 — a matchup she cannot win locally); KG bit-identical on both.
Pooled 8 gained / 4 lost, p=0.39 — no harm, small gain, mechanism
proven; adopted as a correctness repair.

Open: KurtGodel's 18 turns where the plan had an attack and nothing
fired (`plan=APPROACH.DIRECT did=move`, `plan=DIRECT did=adrenaline`
with 33 TP left at distance 9) are not the grapple. Entity-tagged
executor reasons on those turns are the next probe.

**Measured (entity-tagged executor lines, 48 fights):** KG 18 of 18 and
Ada 8 of 12 wasted-attack turns are `EXEC ... STALE_TARGET_SKIP`, with
the plan's aim cell 2 ids from the live enemy for 4 consecutive turns
while the enemy never moved. Not a stale target: a **splash aim**. When
the enemy's own cell has no LoS from the firing cell,
`findBestAvailableAttack` aims an AoE weapon at a cell beside the enemy
(`findAoEWeaponSplashCell`, `isSplash = true`); the executor compares the
aim cell to the live enemy cell, assumes the enemy moved, tries to
retarget onto the LoS-less enemy cell, fails LoS, skips the shot, and the
turn ends with 20–33 TP. Executor fix (`docs/patches`, `keepSplashAim`):
keep the aim when it is still in range, LoS and launch-valid from the
current cell AND its area covers the live enemy. Local on the same seeds:
KG 18 → 12 wasted-attack turns, `SPLASH_KEEP` fired 8×, but 13 STALE
skips remained — and a second diagnostic explains them exactly: all 13
were range OK, LoS OK, launch OK, **area coverage false, aim cell 4
cells from the enemy on an X-shaped area of radius 2** (quantum rifle).

**Third member, the root of the family:** `getAoEAffectedCells` builds
area cells by adding hard-coded id offsets (x 18 / y 17) to the centre —
not how the diamond map is laid out (this was also the root cause of the
old self-poison bug). For X shapes its "diagonals" are ±1 / ±35 in id
space, i.e. cells that are 4 game-cells away. The splash finder believed
those cells covered the enemy; the game would have hit nothing. Rewrite
(`getAoEAffectedCells`, `wouldAoEHitCell`) on the generator's own
shapes (MaskAreaCell: circle |dx|+|dy| ≤ r, plus = axes, X = diagonals,
square = Chebyshev box) in `getCellX/getCellY` coordinates via
`getCellFromXY`, obstacle/off-map cells dropped, memoised per turn. Under
test together with the executor fix.

Step 2 of the plan (the wasted-attack metric for Ed and Margaret) from
their REAL fights: the exact, unarguable subset (shot from the start
cell, LoS, TP affordable, none fired) is 4 turns in Ed's 58 losses and 6
in Margaret's 58 — it is not their problem. Local probes for them follow
the geometry A/B.

---

## Real-ladder baselines and the STR-nemesis panel (2026-09-21)

All four main leeks sit at Elo equilibrium on the real ladder (last 125 solo
fights each): Ada 48%, Ed 51%, KurtGodel 51%, Margaret 53%. Margaret's split
by opponent archetype: **STR 47/97 (48%)**, MAG 11/15 (73%), SCI 8/13 (62%).
She meets STR opponents 78% of the time and is at parity against them; the
+31pp re-rank-off gain was measured vs a MAG opponent she meets 12% of the
time. **The real-ladder value of any change to Margaret is decided by her
STR matchups**, and neither Sepignouf nor Ludaskia is a testbed for that —
she ceilings both (120/120).

So the panel is built from her own losses: the four STR opponents she went
0/2 against in those 125 fights, fetched via `/leek/get` with `total_*` stats
and full kits, added as `ladder_theleaker`, `ladder_bretzelleekide`,
`ladder_hydrogene`, `ladder_reaubotcode` (`science: -1` on ReauBotcode — an
alteration debuff — clamped to 0 for the generator). 0/2 is thin per opponent;
the panel is meant to be read together. First use: a true-null baseline to
find which of the four she does not ceiling, then the re-rank on/off A/B on
those, scored on the proxies. Held findings are not adopted on this.

**Baseline (true null, n=30 each):** TheLeaker **13/30 (43%)**, BretzelLeekide
22/30 (73%), Hydrogène **8/30 (27%)**, ReauBotcode **6/30 (20%)**. None is a
ceiling; three are losing matchups. The panel reproduces her real-ladder
48%-vs-STR picture and is the testbed the re-rank decision was missing.

**Re-rank OFF vs ON on the panel (paired n=60 each, pooled by
`tools/pool_ab.py`):**

| opponent | OFF | ON | gained / lost | p | HP-lead | shot-denial |
|---|---|---|---|---|---|---|
| TheLeaker | **38** | 24 | 23 / 9 | **0.020** | +19.9 | +0.047 |
| Hydrogène | 18 | 15 | 11 / 8 | 0.65 | +9.7 | +0.039 |
| ReauBotcode | **14** | 3 | 11 / **0** | **0.001** | +24.5 | +0.073 |
| BretzelLeekide | **54** | 42 | 15 / 3 | **0.0075** | +30.3 | +0.059 |
| **pooled (n=240)** | **124 (51.7%)** | **84 (35.0%)** | **60 / 20** | **≈0** | **+22.2 (t=7.63)** | **+0.054** |

Fire-then-move −0.018: the gain is not hiding, it is **shot denial** — the
same mechanism as vs Éleeksire. With this, there is no real-opponent testbed
on which the learned re-rank wins: Ed vs Ludaskia ×2 (p=0.039, 0.016),
Margaret vs Éleeksire (p≈0), Margaret vs her STR panel (p≈0), KurtGodel
same direction, two ceilings. The mirror A/B that shipped it was V9
rewarding V9's own habits.

**Adoption case, restated after the hold:** +16.7pp on the archetype that
sets Margaret's real-ladder talent, replicated across four opponents built
from her own losses. Lowest-risk path: side-by-side deploy (`9.0/V9-NR/`,
flag off) with only Margaret assigned, 50 real solo fights against her 53%
baseline, fully reversible by reassigning her AI. `upload_v9.py --root`
exists for exactly this.

---

## Other archetypes

Not yet written. Each needs a stabilised testbed first (`matchup_stability.py`),
because a doctrine measured on an unstable matchup is indistinguishable from
noise. `ladder_sepignouf` (poison, weaker) and `ladder_ludaskia` (direct) exist
as opponents but have not been through the stability check.
