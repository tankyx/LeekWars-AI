# Live weapon/item ID reference (LeekWars main account)

**Source of truth:** the LIVE game, pulled from `/api/market/get-item-templates` +
`/api/leek/get`. The generator's `data/weapons.json` and the frontend
`src/model/weapons.ts` are OUTDATED — do not trust their ids (they had 39=scythe;
live 39=double_gun).

## ID conventions (verified 2026-08-21)
- **Loadout `weapons` field** = live weapon TEMPLATE id (= item id in the live
  game). `loadout/apply` validates ownership by this id.
- **`leek/get` `weapon[].template`** = the same live weapon id.
- The MCP `get_leek` resolves weapon NAMES from outdated data and is WRONG —
  always check names against the live map below, not get_leek's display.

## Weapons we own (live id -> name), from farmer inventory
- 37 pistol, 38 machine_gun, 39 double_gun (range 2-7), 40 destroyer,
  41 shotgun, 42 laser, 43 grenade_launcher (range 4-7), 44 electrisor,
  45 magnum, 46 flame_thrower, 47 m_laser, 48 gazor, 60 b_laser,
  107 katana, 108 broadsword, 109 axe, 115 j_laser, 116 illicit_grenade_launcher,
  118 unbridled_gazor, 151 rifle, **153 rhino (range 2-4, 54+6, cost 5, 3 uses)**,
  180 lightninger (range 6-10), 182 neutrino, 184 bazooka (range 8-12, 110+8),
  187 dark_katana, 225 enhanced_lightninger, 226 unstable_destroyer,
  277 sword, **278 heavy_sword (range 1 melee, 156+17, cost 15, 1 use — the burst)**,
  428 quantum_rifle, 429 desert_saber.

## Burst-weapon notes
- The winning boss bruisers burst ADJACENT with melee (range 1). Our AoE weapons
  (bazooka min-range 8, lightninger min 6, grenade_launcher min 4) CANNOT fire at
  range 1-3 — a squad that closes to melee deals 0 damage (53386673).
- Use **heavy_sword (278, range 1)** for the adjacent burst and **rhino (153,
  range 2-4)** as the cheap follow-up. Keep bazooka (184) for range-8-12 poke.
- Scythe is NOT leek-usable (boss/entity weapon).

## Chips (template id = live id, verified)
spark 18, resurrection 84, teleportation 59, fortress 29, wall 23, carapace 81,
solidification 96, dome 173, remission 80, antidote 110, protein 8, steroid 25,
adrenaline 16, rocky_bulb 76, whip 88, loam 89, fertilizer 90, acceleration 91,
bark 104, ferocity 102, collar 103, tactician_bulb 166, tranquilizer 94,
slow_down 92, soporific 95, inversion 68, grapple 162, boxing_glove 163,
plasma 143, covid 152, plague 99, toxin 98, venom 97, arsenic 171, burning 105.
