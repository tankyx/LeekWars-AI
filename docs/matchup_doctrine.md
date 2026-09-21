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
| EdsgerDijkstra (AGILITY) | 84.6% | 15.0% | 0.1% | 0.0% | 0.1% |
| KurtGodel (TANK_SCI) | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| MargaretHamilton (MAGIC) | 90.3% | 9.6% | 0.0% | 0.0% | 0.0% |

Measured scale: **~12,820 score points per HP of damage dealt vs ~9.5 per HP
healed**, about 1,350:1. KurtGodel's profile sets the highest defensive weights
in the codebase (`shieldValue` 400, `healValue` 280), he gains 13,370 HP over
157 turns — he really is healing and shielding — and both dimensions still land
at 0.0% of his score. Lifesteal is no better: `lifestealScore` is 2.0 points
per HP.

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

## Other archetypes

Not yet written. Each needs a stabilised testbed first (`matchup_stability.py`),
because a doctrine measured on an unstable matchup is indistinguishable from
noise. `ladder_sepignouf` (poison, weaker) and `ladder_ludaskia` (direct) exist
as opponents but have not been through the stability check.
