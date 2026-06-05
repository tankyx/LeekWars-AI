# LeekWars AI — V8 Modular Combat System

A scenario-driven AI for LeekWars (LeekScript) with a unified strategy and per-build weight profiles. V8 generates candidate action sequences, prunes them with a quick scorer, mutates the survivors, simulates the results, and picks the best of ~20 scored scenarios per turn.

For architecture details (pipeline stages, build types, scoring dimensions, ops budget, file map) see [`CLAUDE.md`](CLAUDE.md).

## Project Structure

```
LeekWars-AI/
├── V8_modules/                  # LeekScript AI (deployed to LeekWars server)
│   ├── main.lk                  # Entry point, include order, per-turn loop
│   ├── scenario_*.lk            # Scenario pipeline (generate / quick-score / mutate / simulate / score)
│   ├── field_map_*.lk           # Reachable graph, threat map, AoE patterns, tactical positioning
│   ├── strategic_depth.lk       # Counter-strategy & weight adaptation
│   ├── tactical_awareness.lk    # Adversarial threat cache, fire-turn estimator
│   ├── enemy_*.lk               # Enemy profiling & response lookahead
│   ├── weight_profiles.lk       # 7 build profiles × 23 weights
│   ├── item*.lk                 # Weapon / chip database, roles
│   ├── boss_context.lk          # Fennel King boss fight
│   └── strategy/
│       ├── action.lk
│       ├── base_strategy.lk     # Execution, AoE safety, poison baiting
│       └── unified_strategy.lk  # Single strategy class — behavior diff via weights
├── tools/                       # Python automation (local-only, not deployed)
│   ├── upload_v8.py             # Server upload (prefer the MCP tool — see below)
│   ├── local_test.py            # Fast deterministic local fights via generator.jar
│   ├── lw_test_script.py        # Server-side test fights
│   └── fight_analyzer.py        # Replay a saved fight for debugging
└── fight_logs/                  # Saved fight data (auto-generated)
```

## Install

```bash
git clone https://github.com/yourusername/LeekWars-AI.git
cd LeekWars-AI
pip3 install -r requirements.txt

mkdir -p ~/.config/leekwars
printf '{"username":"YOUR_EMAIL","password":"YOUR_PASSWORD"}' > ~/.config/leekwars/config.json
```

The repo expects a local copy of the LeekWars generator at `/home/ubuntu/leek-wars-generator/` for `local_test.py`. See `CLAUDE.md` § Generator Setup.

## Usage

### Upload V8 to the server

Preferred path is the LeekWars MCP server (`mcp__leekwars__leekwars_upload_v8`). Python fallback:
```bash
python3 tools/upload_v8.py
```

### Local fights (fast, deterministic)

```bash
python3 tools/local_test.py 40 smart_tank --leek EdsgerDijkstra --parallel 2
```

Opponents: `smart_str`, `smart_mag`, `smart_tank`, `smart_agi`, `dummy_*`, `mirror`.
Leeks: `EdsgerDijkstra`, `KurtGodel`, `MargaretHamilton`, `AdaLovelace`, `AlanTuring`.

**Important:** after editing any `.lk` file, clear the generator's compile cache before testing — it only checks the root file's timestamp:
```bash
rm -f /home/ubuntu/leek-wars-generator/ai/*.class /home/ubuntu/leek-wars-generator/ai/*.java /home/ubuntu/leek-wars-generator/ai/*.lines
```

### Server fights (real matchmaking)

Script ID `459440` is the V8 entry point. Do not use `447461` (old, broken).
```bash
python3 tools/lw_test_script.py 10 459440 domingo --leek EdsgerDijkstra
```

### Debug a specific fight

```bash
python3 tools/fight_analyzer.py smart_tank --leek EdsgerDijkstra --seed 1
```
Writes `debug_fight_<id>.json`.

## Local Baseline Win Rates

| Matchup | Win Rate |
|---|---|
| EdsgerDijkstra vs smart_str | ~100% |
| EdsgerDijkstra vs smart_agi | ~100% |
| EdsgerDijkstra vs smart_tank | ~95–100% |
| AdaLovelace vs smart_str | ~100% |
| KurtGodel vs smart_tank | ~60–97% |
| MargaretHamilton vs smart_mag | ~90–95% |

## Development Notes

- All builds run through `UnifiedStrategy` — differentiate behavior via weight profiles, never build-specific `if` chains in the scorer or simulator.
- New behavior goes into the scenario pipeline (generate → score → execute), not into ad-hoc execution code.
- Ops budget is 14M per turn (hard fallback at 13M). API calls (`getCellDistance`, `lineOfSight`, pathfinding) are the main cost.
- LeekScript gotcha: maps use bracket notation (`map['key']`), and bare `return` throws `VALUE_EXPECTED` — use `return null`.
- Validate any change against the full regression matrix in `CLAUDE.md` § Testing before shipping.
- See `AGENTS.md` for style / PR guidelines and `CLAUDE.md` for the full architecture guide.

## License

Open source for LeekWars AI experimentation and learning.
