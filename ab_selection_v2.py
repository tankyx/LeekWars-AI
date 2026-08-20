#!/usr/bin/env python3
"""Interleaved production A/B: selection v2 (talent-EV) vs v1 (win-prob only).
Alternates 5-fight blocks (model, modelv1, ...) so both policies face the same
bracket window. 5 blocks each = 25+25 fights per leek."""
import subprocess
import sys

LEEKS = [("Ada", 20443), ("KG", 129295), ("MH", 129296), ("ED", 129288)]
BLOCKS = 5
PER_BLOCK = 5

for name, lid in LEEKS:
    tally = {"model": {"WIN": 0, "LOSS": 0, "DRAW": 0}, "modelv1": {"WIN": 0, "LOSS": 0, "DRAW": 0}}
    for b in range(BLOCKS):
        for strat in ("model", "modelv1"):
            out = subprocess.run(
                [sys.executable, "tools/fast_solo.py", str(lid), str(PER_BLOCK),
                 "--strategy", strat],
                capture_output=True, text=True, cwd="/home/ubuntu/LeekWars-AI")
            for line in out.stdout.splitlines():
                for r in ("WIN", "LOSS", "DRAW"):
                    if line.strip().startswith("[") and f" {r} vs " in line:
                        tally[strat][r] += 1
    m, s = tally["model"], tally["modelv1"]
    print(f"{name}: v2 {m['WIN']}W/{m['LOSS']}L/{m['DRAW']}D  vs  v1 {s['WIN']}W/{s['LOSS']}L/{s['DRAW']}D", flush=True)

print("done")
