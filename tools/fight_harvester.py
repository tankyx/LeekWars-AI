#!/usr/bin/env python3
"""W1 fight harvester: bulk-download every fight in the leek history DBs to
data/fight_cache/<fight_id>.json for the learned-value-model dataset.

Resumable (skips cached), paced at 0.35s/call. ~15k fights ≈ 90 min.

Usage: python3 tools/fight_harvester.py [--limit N] [--leeks main|cure|both]
"""
import argparse
import json
import sqlite3
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
CACHE = ROOT / "data" / "fight_cache"
CACHE.mkdir(parents=True, exist_ok=True)

MAIN_LEEKS = [20443, 129295, 129296, 129288]
CURE_LEEKS = [19703, 21175, 129801, 130236]
PACE = 0.36


def fight_ids(leek_id):
    db = ROOT / "tools" / f"fight_history_{leek_id}.db"
    if not db.exists():
        return []
    con = sqlite3.connect(db)
    rows = con.execute("SELECT fight_id FROM fight_history").fetchall()
    con.close()
    return [r[0] for r in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--leeks", default="both", choices=["main", "cure", "both"])
    args = ap.parse_args()

    leeks = (MAIN_LEEKS + CURE_LEEKS) if args.leeks == "both" else \
            (MAIN_LEEKS if args.leeks == "main" else CURE_LEEKS)
    todo = []
    for lid in leeks:
        todo.extend(fight_ids(lid))
    todo = sorted(set(todo), reverse=True)  # newest first
    have = {int(p.stem) for p in CACHE.glob("*.json") if p.stem.isdigit()}
    todo = [f for f in todo if f not in have]
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(todo)} fights to download ({len(have)} already cached)")

    t0 = time.time()
    ok = err = 0
    for i, fid in enumerate(todo):
        try:
            with urllib.request.urlopen(f"https://leekwars.com/api/fight/get/{fid}") as r:
                d = json.loads(r.read())
            (CACHE / f"{fid}.json").write_text(json.dumps(d))
            ok += 1
        except Exception as e:
            err += 1
            if err <= 5 or err % 50 == 0:
                print(f"  {fid}: ERR {e}", flush=True)
        time.sleep(PACE)
        if (i + 1) % 100 == 0:
            rate = (i + 1) / (time.time() - t0)
            eta = (len(todo) - i - 1) / rate / 60 if rate else 0
            print(f"  [{i+1}/{len(todo)}] ok={ok} err={err} {rate:.2f}/s ETA {eta:.0f}min", flush=True)
    print(f"done: {ok} ok, {err} err in {(time.time()-t0)/60:.0f} min; cache={len(have)+ok}")


if __name__ == "__main__":
    main()
