# Repository Guidelines

## Project Structure & Module Organization
- `V8_modules/` — LeekScript AI source (V8).
  - `main.lk` (entry point), `game_entity.lk`, `field_map*.lk`, `item.lk`, `strategy/`.
- `tools/` — Python utilities for upload, testing, and analysis.
- `fight_logs/` — Saved fight data (auto‑generated; do not commit).

## Build, Test, and Development Commands
- Install deps: `pip3 install -r requirements.txt`
- Upload V8 to LeekWars: `python3 tools/upload_v8.py`
- Run tests: `python3 tools/lw_test_script.py <script_id> <fights> <opponent>`
  - Example: `python3 tools/lw_test_script.py 447461 20 rex`
  - Logs saved under `fight_logs/<leek_id>/`.
- Quick fights (ranked): `python3 tools/lw_solo_fights_flexible.py 1 10 --quick`

## Coding Style & Naming Conventions
- LeekScript: 4‑space indentation, no tabs; functions/vars `lowerCamelCase`; constants `UPPER_SNAKE_CASE` (use LeekScript built‑ins like `CHIP_TELEPORTATION`).
- File names: lower_snake_case (e.g., `strategy/action.lk`).
- Includes: `include("folder/name");` (omit `.lk`). Keep include paths stable.
- Keep debug output minimal; prefer `debug()` function.

## Testing Guidelines
- No unit test framework; use fight simulations.
- Run 10–20 fights per opponent for signal; verify no runtime errors and reasonable win rate.
- Inspect saved logs in `fight_logs/<leek_id>/` and adjust tactics accordingly.
- Before upload, sanity‑test locally with a small sample (e.g., 3–5 fights).

## Commit & Pull Request Guidelines
- Commits: short, imperative subject (e.g., "Improve targeting priority"), optional scope.
- PRs: clear description, rationale, steps to reproduce/test (commands), and notable logs/screenshots. Link related issues.
- Touch only relevant modules; update docs if behavior or commands change.

## Security & Configuration Tips
- Credentials: store in `~/.config/leekwars/config.json` or env vars `LEEKWARS_EMAIL`/`LEEKWARS_PASSWORD`. Never commit secrets.
- `.gitignore` already excludes logs and common artifacts; keep fight data untracked.
- See `tools/CONFIG_README.md` for centralized configuration details.
