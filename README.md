# LeekWars AI - V8 Modular Combat System

A sophisticated AI for LeekWars with modular architecture, build-specific strategies, and advanced combat tactics. V8 uses an action queue pattern for clean separation of planning and execution.

## Project Structure

```
LeekWars-AI/
├── V8_modules/            # Core LeekScript AI (V8)
│   ├── main.lk            # Entry point & strategy selection
│   ├── game_entity.lk     # Player & enemy state tracking
│   ├── field_map*.lk      # Damage zones & tactical positioning
│   ├── item.lk            # Weapon/chip definitions
│   └── strategy/          # Build-specific strategies
│       ├── action.lk              # Action type definitions
│       ├── base_strategy.lk       # Base combat logic
│       ├── strength_strategy.lk   # Strength builds
│       ├── magic_strategy.lk      # Magic builds
│       ├── agility_strategy.lk    # Agility builds
│       └── boss_strategy.lk       # Boss fight strategy
├── tools/                 # Python automation
│   ├── upload_v8.py       # Deploy V8 to LeekWars
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

Upload V8 to LeekWars:
```bash
python3 tools/upload_v8.py
```

Run tests vs opponents (domingo, betalpha, tisma, guj, hachess, rex):
```bash
python3 tools/lw_test_script.py 447461 20 rex
```

Quick ranked fights (example for leek 1):
```bash
python3 tools/lw_solo_fights_flexible.py 1 10 --quick
```

Logs are saved under `fight_logs/<leek_id>/`.

## Development Notes

- Keep `debugEnabled` off by default; use debug() helpers.
- Validate changes with 10–20 fights per opponent for signal.
- See `AGENTS.md` for style, testing, and PR guidelines.
- See `CLAUDE.md` for V8 architecture details and development guide.

## License

Open source for LeekWars AI experimentation and learning.
