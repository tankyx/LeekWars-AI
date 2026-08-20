#!/usr/bin/env python3
"""A/B test: V8 (8.0/V8/main.lk) vs V9 (9.0/V9/main.lk) on the main leeks.

Alternates 12-fight blocks per leek (V8 -> V9 -> V8 -> ...) with a uniform
opponent-selection rule for BOTH AIs (same selector, so the comparison is
the AI, not the bracket). Records every fight to data/ab_test_v9.jsonl and
talent after each block to the same log. Restores V9 on all leeks at the end.

Usage: python3 tools/ab_test_v9.py [--fights-per-ai 80] [--leeks 20443,129295,129296,129288]
"""
import argparse
import json
import random
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config_loader import load_credentials  # noqa: E402

BASE = "https://leekwars.com/api"
V8 = "8.0/V8/main.lk"
V9 = "9.0/V9/main.lk"
BLOCK = 12
OUT = Path(__file__).parent.parent / "data" / "ab_test_v9.jsonl"
LEEKS = {"20443": "AdaLovelace", "129295": "KurtGodel",
         "129296": "MargaretHamilton", "129288": "EdsgerDijkstra"}


def iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Driver:
    def __init__(self, account):
        login, password = load_credentials(account=account)
        self.s = requests.Session()
        self.farmer = self.s.post(f"{BASE}/farmer/login-token",
                                  data={"login": login, "password": password}).json()["farmer"]
        self.log = open(OUT, "a")
        print(f"logged in: {self.farmer['login']}")

    def post(self, path, payload, retries=5):
        for _ in range(retries):
            r = self.s.post(f"{BASE}{path}", json=payload)
            try:
                j = r.json()
            except Exception:
                j = {"_http": r.status_code}
            if isinstance(j, dict) and j.get("error") == "rate_limit":
                time.sleep(float(j.get("retry_after", 1)) + 0.4)
                continue
            if not isinstance(j, dict):
                time.sleep(1.0)
                continue  # transient string/empty body — retry
            return j
        return {"_error": "post_failed"}

    def set_ai(self, leek_id, ai_path):
        return self.post("/leek/set-ai", {"leek_id": leek_id, "ai_path": ai_path})

    def opponents(self, leek_id):
        r = self.s.get(f"{BASE}/garden/get-leek-opponents/{leek_id}")
        try:
            return r.json()
        except Exception:
            return {}

    def record_winrate_map(self, leek_id):
        db = f"tools/fight_history_{leek_id}.db"
        if not Path(db).exists():
            return {}
        con = sqlite3.connect(db)
        rows = con.execute("SELECT opponent_id, wins, losses FROM opponent_stats").fetchall()
        con.close()
        return {oid: (w, l) for oid, w, l in rows}

    def pick_targets(self, leek_id, n):
        data = self.opponents(leek_id)
        cands = data.get("opponents", [])
        hist = self.record_winrate_map(leek_id)
        picks = []
        pool = list(cands)
        random.shuffle(pool)
        for opp in pool:
            if len(picks) >= n:
                break
            oid = opp.get("id")
            wr = hist.get(oid)
            if wr is None:
                if random.random() < 0.20:
                    picks.append(opp)  # explore new
                continue
            w, l = wr
            rate = w / max(1, w + l)
            if rate < 0.15 or rate > 0.92:
                continue
            if 0.40 <= rate <= 0.70:
                wgt = 3.0
            elif 0.25 <= rate < 0.40 or 0.70 < rate <= 0.85:
                wgt = 1.0
            else:
                wgt = 0.4
            if random.random() < wgt / 3.0:
                picks.append(opp)
        # top-up if filters were too strict
        for opp in pool:
            if len(picks) >= n:
                break
            if opp not in picks:
                picks.append(opp)
        return picks[:n]

    def fight(self, leek_id, target_id):
        r = self.post("/garden/start-solo-fight", {"leek_id": leek_id, "target_id": target_id})
        if isinstance(r, dict):
            return r.get("fight") or r.get("id")
        return None

    def result_of(self, fight_id):
        # Fights simulate server-side almost instantly — fetch fast; retry only
        # while the report is still processing (data null / winner unknown).
        for _ in range(12):
            fd = self.s.get(f"{BASE}/fight/get/{fight_id}").json()
            d = fd.get("data")
            if isinstance(d, str):
                d = json.loads(d)
            if isinstance(d, dict):
                winner = fd.get("fight", fd).get("winner", d.get("winner"))
                if winner is not None:
                    return winner
            time.sleep(0.4)
        return -1

    def block(self, leek_id, ai_path, block_no):
        self.set_ai(leek_id, ai_path)
        # The garden refreshes its 5-opponent offer after EVERY fight, so a
        # fetched list goes stale the moment one target is fought. Flow:
        # fetch 5 -> pick one by bucket -> fight -> fetch fresh. Never stale.
        started = []
        for _ in range(BLOCK):
            targets = self.pick_targets(leek_id, 1)
            if not targets:
                time.sleep(0.5)
                continue
            opp = targets[0]
            r = self.post("/garden/start-solo-fight", {"leek_id": leek_id, "target_id": opp.get("id")})
            fid = r.get("fight") or r.get("id") if isinstance(r, dict) else None
            if fid:
                started.append((fid, opp))
            time.sleep(0.35)
        # results sweep after all starts — fights are already done server-side
        results = []
        for fid, opp in started:
            w = self.result_of(fid)
            res = {1: "W", 2: "L", 0: "D"}.get(w, "?")
            results.append(res)
            self.log.write(json.dumps({
                "ts": iso(), "leek": leek_id, "leek_name": LEEKS.get(str(leek_id)),
                "ai": ai_path, "block": block_no, "fight_id": fid,
                "opponent_id": opp.get("id"), "opponent_name": opp.get("name"),
                "result": res}) + "\n")
            self.log.flush()
            time.sleep(0.35)
        return results

    def talent(self, leek_id):
        f = self.s.post(f"{BASE}/farmer/login-token",
                        data={"login": load_credentials()[0], "password": load_credentials()[1]}).json()["farmer"]
        for lk in f["leeks"].values():
            if lk["id"] == leek_id:
                return lk.get("talent"), lk.get("ranking")
        return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fights-per-ai", type=int, default=80)
    ap.add_argument("--leeks", default="20443,129295,129296,129288")
    ap.add_argument("--rounds", type=int, default=30)
    ap.add_argument("--round-sleep", type=int, default=300)
    args = ap.parse_args()

    d = Driver("main")
    leeks = [int(x) for x in args.leeks.split(",")]
    blocks_per_ai = max(1, args.fights_per_ai // BLOCK)

    # cumulative per-(leek, ai) fight counts, resumable across restarts
    done = defaultdict(int)
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if "ai" in r and r.get("result") in ("W", "L", "D"):
                done[(r["leek"], r["ai"])] += 1

    for rnd in range(args.rounds):
        progressed = 0
        for leek_id in leeks:
            name = LEEKS.get(str(leek_id), str(leek_id))
            for ai_path in (V8, V9):
                if done[(leek_id, ai_path)] >= args.fights_per_ai:
                    continue
                res = d.block(leek_id, ai_path, rnd)
                got = sum(1 for x in res if x in ("W", "L", "D"))
                done[(leek_id, ai_path)] += got
                progressed += got
                w = res.count("W")
                print(f"[r{rnd}] {name} {'V9' if ai_path == V9 else 'V8'}: {w}W/{len(res)-w}X (cum {done[(leek_id, ai_path)]})")
                d.set_ai(leek_id, V9)  # keep trial config between blocks
        if all(done[(l, a)] >= args.fights_per_ai for l in leeks for a in (V8, V9)):
            print("target reached for all leeks")
            break
        if progressed == 0:
            print(f"[r{rnd}] garden dry — sleeping {args.round_sleep}s for refresh")
            time.sleep(args.round_sleep)
    for leek_id in leeks:
        d.set_ai(leek_id, V9)
    print("\nA/B complete. Analyze with: python3 tools/ab_test_v9_analyze.py")


if __name__ == "__main__":
    main()
