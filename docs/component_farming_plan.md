## ⚠️ CORRECTION (2026-09-08): Nasu farming was UNNECESSARY — everything is already in stock

Live inventory audit (via `tools/config_loader` + `/api/farmer/login-token` +
`/api/scheme/get-all`) proves the obsidian_plate craft chain is fully covered by
current surplus. The earlier plan mis-stated the recipe (real recipe below) and
the katana bottleneck was a keying bug (I looked up result-id 294 instead of
scheme-id 329).

**We own EVERY scheme** (iron_plate #329, amazonite_plate #330, obsidian_plate
#331) and every raw material in bulk. Real recipes (from `/api/scheme/get-all`):

- **iron_plate** (scheme 5): 30 rock, 50 brick, 20 pebble, 40 nut  ← all surplus
- **amazonite_plate** (scheme 6): 1 iron_plate, 3 amazonite, 10 nut, 2 metal_plate, 1 aragonite
- **obsidian_plate** (scheme 7): 3 topaze, 2 raw_ruby, 1 copper, 4 iron_plate,
  1 amazonite_plate, 90 broken_katana, 3 obsidian, 1 silver_lingot

Stock vs need (2026-09-08): broken_katana 4511 (need 90/plate), obsidian 6,
topaze 253, raw_ruby 30, copper 17, metal_plate 1891, silver_lingot 6,
amazonite 202, aragonite 510, rock/brick/pebble/nut in the thousands.

**Craftable RIGHT NOW: 2× obsidian_plate** (the only limiter is raw **obsidian**
id 213: have 6, each plate needs 3 → 2 plates). For 4 plates we need **+6
obsidian** (Glacier garden fights). NO Nasu farming needed for any of it.

**Open item:** no public craft API endpoint responded (component/scheme/forge/*
all return `no_such_service`); crafting is likely web-Forge only. Craft the 2
obsidian_plates in-browser, then re-equip and re-test the boss.

# Component Farming Plan — Fennel-boss phase-2 stat gap

**Why.** Max level → capital fixed ~1,780/leek. Phase-2 army (36k, scribe heals
~90%) clears only ~40% because 8 slots + 1,780 capital can't give STR+RES+HP+TP
at winning levels together. Premium crafted components pack several high stats
per slot and break the trade-off. Recipes drop from any fight; parts drop by
FIELD type + CONTEXT (table below). Stat map (encyclopedia→real): PV=life,
Mémoire=STRENGTH, Cœurs=RESISTANCE, Ops≈TP.

## Resource → where to farm (from the official loot table)

GARDEN context, by FIELD (solo/farmer/team/BR fights land on random fields):
- **Factory**: Nut, Metal plate, Wrench, Site cone, **Copper**
- **Desert**: Rock, Skull, Sand, **Rose of sands**, **Raw ruby**
- **Forest**: **Branch**, Leaf, Flower, Mushroom, **Acorn**
- **Glacier**: Ice cube, **Pine ball**, Carrot, Snowflake, **Obsidian**
- **Beach**: Pebble, Sea water, Salt, **Coconut**, Shell

TOURNAMENT context → **Temple** field: Brick, Ivy, **Statuette**, **Aragonite**,
**Gold nugget**; **Topaze (FARMER tournament only)**, Cornaline (TEAM only),
Amazonite (SOLO only). Aquamarine = **Battle Royale**.

BOSS fights (Garden), by boss field:
- **Teien** (Nasu, boss 1, L100): Eggplant flesh, **Broken katana**, Inro
- **Castel** (Fennel King, boss 2, L200): Sliced fennel, Eternal fire, Graal frag
- **Cemetery** (Evil Pumpkin, boss 3, L300): Pumpkin seeds, **Lantern**, **Feather**
- **Silver nugget**: any boss (Teien/Castel/Cemetery)

Chests: Brown=wood, Iron=iron, Diamond=diamond chest potions.

## Targets, sourced

### PRIORITY 1 — OBSIDIAN PLATE ×2 more (own 2, want 4) — MOST FARMABLE
**+300 HP, +80 RES, +20 STR** (survival AND damage; RES scales our shields).
Recipe: 3 Topaze, 2 Raw ruby, 1 Copper, 4 Metal plate, 1 Amazonite plate,
**90 Broken katana**, 3 Obsidian, 1 Silver nugget.
Farm:
- **90 Broken katana → NASU boss (Teien, boss 1, L100)** — the EASIEST boss, we
  can beat it. This is the bulk grind (many Nasu runs).
- 3 Topaze → **farmer** fights in **tournament** context (Temple).
- 3 Obsidian → **glacier** garden fights.
- 2 Raw ruby → **desert** garden fights. 1 Copper → **factory**. Metal plate → factory.
- 1 Silver nugget → any boss. Amazonite plate → craft (we own some) or solo-tournament.

### PRIORITY 2 — CHESTNUT ×4 — biggest single-slot payoff, harder parts
**+240 HP, +80 STR, +40 RES, +1 TP** — no trade-off; the ideal striker component.
Recipe: 1 Acorn, 1 Coconut, **22 Lantern**, 1 Nephelium (craft), 1 empty wood
chest, 10 Pine ball, 8 Statuette, 5 Branch.
Farm:
- **22 Lantern → EVIL PUMPKIN boss (Cemetery, boss 3, L300)** — the BOTTLENECK
  (hardest boss; likely needs the 8-leek cross-farmer lobby or many attempts).
- 1 Acorn + 5 Branch → **forest** garden. 1 Coconut → **beach**. 10 Pine ball →
  **glacier**. 8 Statuette → **tournament** (Temple). Nephelium → craft.

### PRIORITY 3 — THOKOZANI ×N — +50 STR/+50 RES/+50 to all
Recipe: 40 Leek leaf (any), 3 Shell (beach), Mangue bleutée, 3 Acorn (forest),
2 Gold nugget (tournament), 1 Raw ruby (desert), **4 restat potions**, 5
Aquamarine (**Battle Royale**). Expensive (4 restat potions each) — low priority.

## Farming routine (recommended order)

1. **Nasu boss (boss 1) grind** — beat the L100 Nasu repeatedly for Broken katana
   (90 per obsidian) + Silver nugget. This is the main obsidian bottleneck and
   the Nasu is our most winnable boss. Automatable via the boss-fight API.
2. **Garden field sweep** — run solo/farmer garden fights; over volume they land
   on glacier (Obsidian, Pine ball), desert (Raw ruby, Rose of sands), forest
   (Acorn, Branch), beach (Coconut, Shell), factory (Copper, Metal plate).
3. **Tournament fights** (Wed/Sat auto-tournaments, or on-demand) → Temple field:
   Statuette, Gold nugget, Aragonite, and Topaze (farmer-tournament).
4. **Recipes**: any fight can drop a scheme — the volume from steps 1-3 covers it.
   Check the Usine for the obsidian/chestnut/thokozani recipes as they arrive.
5. **Craft order**: 2× OBSIDIAN first (farmable now via Nasu), then 4× CHESTNUT
   as Lanterns accumulate from Pumpkin runs.
6. **Re-equip** all 4 clones: core3 + ram2 + ram + power_supply + CHESTNUT +
   OBSIDIAN + nephelium + strawberry → ~STR 600 / RES 400 / HP 3200 / TP 26
   (winner statline, no trade-off), then re-test the boss.

## Automation I can build

A daily loop that: (a) runs Nasu-boss fights + garden/farmer fights via the API,
(b) polls the farmer object each run for new `resources`/`schemes`, (c) tracks
progress toward each target recipe's part list, (d) reports when obsidian /
chestnut becomes craftable. Say the word.
