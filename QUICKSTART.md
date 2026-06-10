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

For all server-side operations (upload, fights, listing AIs) prefer the
**LeekWars MCP** tools (`mcp__leekwars__*`). They stay in sync with API
changes. The Python wrappers below are fallbacks.

Upload V8 to LeekWars:
```bash
# Preferred: mcp__leekwars__leekwars_upload_v8
python3 tools/upload_v8.py   # fallback
```

Server bot tests — script `459440` is the V8 AI (do **not** use `447461`,
which is the old broken entry point). Argument order is `<num_tests>
<script_id> <opponent>`:
```bash
python3 tools/lw_test_script.py 20 459440 rex
```

Test against several opponents quickly:
```bash
for op in domingo betalpha tisma guj hachess rex; do
  python3 tools/lw_test_script.py 5 459440 $op
done
```

Ranked solo fights (example for leek 1):
```bash
python3 tools/lw_solo_fights_flexible.py 1 20 --quick
```

Local deterministic fights (uses the generator at
`/home/ubuntu/leek-wars-generator/`):
```bash
python3 tools/local_test.py 40 smart_tank --leek EdsgerDijkstra --parallel 2
```

## Common Tasks

After editing any `.lk` file, clear the generator cache **before** local
testing — it only checks the root file's timestamp:
```bash
rm -f /home/ubuntu/leek-wars-generator/ai/*.class \
      /home/ubuntu/leek-wars-generator/ai/*.java \
      /home/ubuntu/leek-wars-generator/ai/*.lines
```

Sanity check + upload:
```bash
python3 tools/local_test.py 20 smart_str --leek EdsgerDijkstra
# Preferred: mcp__leekwars__leekwars_upload_v8
python3 tools/upload_v8.py
```

Push to GitHub:
```bash
git add <files>
git commit -m "Describe your change"
git push origin main
```

## Troubleshooting

- Check credentials: `~/.config/leekwars/config.json`
- Ensure dependencies installed: `pip3 install -r requirements.txt`
- Logs saved under `fight_logs/<leek_id>/`
- After a V8 upload, wait ~2 min before mass tests — server compile is
  async and early batches can crash every turn (action `1002`).
- MCP-cookie weirdness (solo fights reporting 0 wins + silent errors)?
  `rm /tmp/leekwars-cookies.txt` and re-login via
  `mcp__leekwars__leekwars_login`.
- See `CLAUDE.md` for V8-specific development guidance, full architecture,
  testing matrix, and baseline win rates.
