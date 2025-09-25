# Tools Guide (V7)

## Upload & Deployment
- Upload V7: `python3 tools/upload_v7.py`
- Update a single script: `python3 tools/lw_update_script.py V7_modules/V7_main.ls <script_id>`
  - Example: `python3 tools/lw_update_script.py V7_modules/V7_main.ls 446029`
- Retrieve a script: `python3 tools/lw_retrieve_script.py <script_id>`

## Testing & Combat
- Bot tests (by script ID):
  - `python3 tools/lw_test_script.py <script_id> <num_tests> <opponent>`
  - Example: `python3 tools/lw_test_script.py 446029 20 rex`
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
