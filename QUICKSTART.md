# Quick Start Guide (V8)

## Setup (First Time)

1) Clone and enter:
```bash
git clone https://github.com/yourusername/LeekWars-AI.git
cd LeekWars-AI
```

2) Install dependencies and configure credentials:
```bash
pip3 install -r requirements.txt
mkdir -p ~/.config/leekwars
printf '{"username":"YOUR_EMAIL","password":"YOUR_PASSWORD"}' > ~/.config/leekwars/config.json
```

## Daily Usage

Upload V8 to LeekWars:
```bash
python3 tools/upload_v8.py
```

Run tests (example opponents: domingo, betalpha, tisma, guj, hachess, rex):
```bash
python3 tools/lw_test_script.py 447461 20 rex
```

Test all quickly:
```bash
for op in domingo betalpha tisma guj hachess rex; do
  python3 tools/lw_test_script.py 447461 5 $op
done
```

Ranked solo fights (example for leek 1):
```bash
python3 tools/lw_solo_fights_flexible.py 1 20 --quick
```

## Common Tasks

After code changes, sanity test and upload:
```bash
python3 tools/lw_test_script.py 447461 3 rex
python3 tools/upload_v8.py
```

Push to GitHub:
```bash
git add .
git commit -m "Describe your change"
git push origin main
```

## Troubleshooting

- Check credentials: `~/.config/leekwars/config.json`
- Ensure dependencies installed: `pip3 install -r requirements.txt`
- Logs saved under `fight_logs/<leek_id>/`
- See `CLAUDE.md` for V8-specific development guidance
