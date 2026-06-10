# Tools Guide (V8)

> **Prefer the LeekWars MCP** (`mcp__leekwars__*`) for any server-side
> operation — upload, fights, AI list/save, farmer/leek/fight fetches.
> The Python wrappers below stay around as local-only fallbacks and for
> workflows that have no MCP equivalent (`local_test.py`,
> `fight_analyzer.py`, GA tooling).
>
> The current V8 entry-point script ID is **`459440`**. Do **not** use
> `447461` — it is the old broken AI.

## Upload & Deployment
- Upload V8 (preferred): `mcp__leekwars__leekwars_upload_v8`
- Upload V8 (fallback): `python3 tools/upload_v8.py`
- Update a single script: `python3 tools/lw_update_script.py V8_modules/main.lk <script_id>`
  - Example: `python3 tools/lw_update_script.py V8_modules/main.lk 459440`
- Retrieve a script: `python3 tools/lw_retrieve_script.py <script_id>`

## Testing & Combat
- Local deterministic fights (no server, fastest iteration):
  - `python3 tools/local_test.py <num_fights> <opponent> --leek <name> [--parallel N]`
  - Example: `python3 tools/local_test.py 40 smart_tank --leek EdsgerDijkstra --parallel 2`
- Bot tests on server (by script ID; arg order is `<num_tests> <script_id> <opponent>`):
  - `python3 tools/lw_test_script.py <num_tests> <script_id> <opponent>`
  - Example: `python3 tools/lw_test_script.py 20 459440 rex`
- Ranked solo fights:
  - `python3 tools/lw_solo_fights_flexible.py <leek_id> <count> [--quick]`
- Team fights (all compositions):
  - `python3 tools/lw_team_fights_all.py [--quick]`
- Farmer fights (garden/challenge):
  - `python3 tools/lw_farmer_fights.py garden <num>`
  - `python3 tools/lw_farmer_fights.py challenge <farmer_id> <num> [--seed N] [--side L/R] [--quick]`
- Continuous testing: `python3 tools/lw_test_runner.py`

## Boss Fights (WebSocket)
- Activate websocket venv first:
  - `source websocket_env/bin/activate`
- Run boss fights:
  - `python3 tools/lw_boss_fights.py <boss_number> <num_fights> [--quick]`
  - Example: `python3 tools/lw_boss_fights.py 2 10 --quick`
- Deactivate when done: `deactivate`

## Validation & WebSocket Utilities
- Validate remote script (ws): `python3 tools/validate_script.py <script_id>`
- Validate local file (ws): `python3 tools/validate_local_file.py <file> <script_id>`
- WebSocket diagnostics (ws): `python3 tools/debug_websocket.py`, `python3 tools/websocket_validator.py`, `python3 tools/simple_websocket_test.py`
- Error analyzer (ws): `python3 tools/leekwars_error_analyzer.py`

## Fight Analysis & Info
- Fight details (with actions): `python3 tools/lw_get_fight_auth.py <fight_id>`
- Fight logs (basic): `python3 tools/lw_get_fight.py <fight_id>`
- Performance compare: `python3 tools/compare_leek_performance.py`
- Leek info: `python3 tools/lw_leeks_info.py`
- Characteristics: `python3 tools/lw_charateristics.py`

## Environment & Credentials
- Preferred: `~/.config/leekwars/config.json` with `{ "username": "...", "password": "..." }`
- Or set env vars before running tools:
  - `export LEEKWARS_EMAIL="your_email@example.com"`
  - `export LEEKWARS_PASSWORD="your_password"`
- Never commit secrets. `fight_logs/` is auto-generated and should remain untracked.

Notes: Only boss/validation/debug websocket tools require the `websocket_env` virtualenv. Team/solo tests use HTTP and run without it.
