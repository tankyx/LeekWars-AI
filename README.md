# LeekWars AI - V7 Streamlined Combat System

A compact, robust AI for LeekWars with enemy‑centric damage zones, A* pathfinding, and scenario‑based combat. V7 replaces V6 with fewer modules, better reliability, and clearer tooling.

## Project Structure

```
LeekWars-AI/
├── V7_modules/            # Core LeekScript AI
│   ├── V7_main.ls         # Entry point
│   ├── core/              # Globals & game state
│   ├── config/            # Weapon/TP mappings
│   ├── decision/          # Targeting, evaluation, buffs, emergency
│   ├── combat/            # Combat execution
│   ├── movement/          # A* pathfinding
│   └── utils/             # Debug & cache
├── tools/                 # Python automation
│   ├── upload_v7.py       # Deploy V7 to LeekWars
│   └── lw_test_script.py  # Run fights and save logs
└── fight_logs/            # Saved fight data (auto‑generated)
```

## Install

1) Clone and enter:
```bash
git clone https://github.com/yourusername/LeekWars-AI.git
cd LeekWars-AI
```
2) Python deps and credentials:
```bash
pip3 install -r requirements.txt
mkdir -p ~/.config/leekwars
printf '{"username":"YOUR_EMAIL","password":"YOUR_PASSWORD"}' > ~/.config/leekwars/config.json
```

## Usage

Upload V7 to LeekWars:
```bash
python3 tools/upload_v7.py
```

Run tests vs opponents (domingo, betalpha, tisma, guj, hachess, rex):
```bash
python3 tools/lw_test_script.py 446029 20 rex
```

Quick ranked fights (example for leek 1):
```bash
python3 tools/lw_solo_fights_flexible.py 1 10 --quick
```

Logs are saved under `fight_logs/<leek_id>/`.

## Development Notes

- Keep `debugEnabled` off by default; use `utils/debug.ls` helpers.
- Validate changes with 10–20 fights per opponent for signal.
- See `AGENTS.md` for style, testing, and PR guidelines.

## License

Open source for LeekWars AI experimentation and learning.

