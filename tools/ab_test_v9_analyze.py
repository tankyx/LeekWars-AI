#!/usr/bin/env python3
"""Analyze data/ab_test_v9.jsonl: win rates + talent deltas, V8 vs V9."""
import json
from collections import defaultdict
from pathlib import Path

LOG = Path(__file__).parent.parent / "data" / "ab_test_v9.jsonl"
V8, V9 = "8.0/V8/main.lk", "9.0/V9/main.lk"

stats = defaultdict(lambda: [0, 0, 0])  # (leek, ai) -> [W, L, D]
for line in LOG.read_text().splitlines():
    if not line.strip():
        continue
    r = json.loads(line)
    if "ai" not in r:
        continue
    key = (r["leek_name"], "V9" if r["ai"] == V9 else "V8")
    res = r["result"]
    if res == "W":
        stats[key][0] += 1
    elif res == "L":
        stats[key][1] += 1
    elif res == "D":
        stats[key][2] += 1

tot = defaultdict(lambda: [0, 0, 0])
print(f"{'leek':18s}{'AI':4s}{'W':>5s}{'L':>5s}{'D':>4s}{'win%':>8s}")
for (name, ai) in sorted(stats):
    w, l, dd = stats[(name, ai)]
    n = max(1, w + l)
    print(f"{name:18s}{ai:4s}{w:5d}{l:5d}{dd:4d}{100*w/n:7.1f}%")
    tot[ai][0] += w
    tot[ai][1] += l
    tot[ai][2] += dd
print("-" * 40)
for ai in ("V8", "V9"):
    w, l, dd = tot[ai]
    n = max(1, w + l)
    print(f"{'TOTAL':18s}{ai:4s}{w:5d}{l:5d}{dd:4d}{100*w/n:7.1f}%")
w8 = tot["V8"][0] / max(1, tot["V8"][0] + tot["V8"][1])
w9 = tot["V9"][0] / max(1, tot["V9"][0] + tot["V9"][1])
print(f"\nV9 edge over V8: {100*(w9-w8):+.1f} points (n={tot['V8'][0]+tot['V8'][1]} vs {tot['V9'][0]+tot['V9'][1]})")
