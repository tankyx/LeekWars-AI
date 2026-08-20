#!/usr/bin/env python3
"""Fast solo fight runner — 0.35s between API calls (the rate the API
comfortably allows), vs the 2s/step of lw_solo_fights_smart.py.

Replicates the MCP 'smart' opponent policy (beatable > unknown > risky[:2])
so A/B cells stay comparable with earlier batches. Records results into
tools/fight_history_<leek_id>.db (same schema as the other runners).

Usage:
    python3 tools/fast_solo.py <leek_id> <n_fights> [--account main] [--strategy smart|model]
"""
import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_credentials
import opponent_model

BASE = "https://leekwars.com/api"
PACE = 0.35


class FastRunner:
    def __init__(self, account, leek_id, strategy="smart"):
        login, password = load_credentials(account)
        self.s = requests.Session()
        r = self.s.post(f"{BASE}/farmer/login-token", data={"login": login, "password": password})
        self.token = r.json()["token"]
        self.leek_id = leek_id
        self.strategy = strategy
        self.model_entry = None
        if strategy in ("model", "modelv1"):
            self.model_entry = opponent_model.get_leek_entry(leek_id)
            if not self.model_entry:
                print("  model: no cache entry for this leek, falling back to smart")
                self.strategy = "smart"
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    f"fight_history_{leek_id}.db")
        self._last_call = 0.0

    def _pace(self):
        dt = time.time() - self._last_call
        if dt < PACE:
            time.sleep(PACE - dt)
        self._last_call = time.time()

    def call_get(self, path, retries=3):
        for a in range(retries):
            self._pace()
            r = self.s.get(f"{BASE}{path}")
            if r.status_code == 429:
                time.sleep(1.0)
                continue
            return r.json()
        return {}

    def call_post(self, path, data, retries=3):
        for a in range(retries):
            self._pace()
            r = self.s.post(f"{BASE}{path}", data=data)
            if r.status_code == 429:
                time.sleep(1.0)
                continue
            return r.json()
        return {}

    # ---- opponent DB (same policy as the smart script) ----
    def opp_stats(self):
        con = sqlite3.connect(self.db_path)
        con.execute("""CREATE TABLE IF NOT EXISTS fight_history(
            fight_id INTEGER PRIMARY KEY, opponent_id INTEGER, opponent_name TEXT,
            opponent_level INTEGER, result TEXT, duration INTEGER, actions_count INTEGER,
            fight_url TEXT, timestamp TEXT)""")
        rows = con.execute("SELECT opponent_id, result, COUNT(*) FROM fight_history "
                           "GROUP BY opponent_id, result").fetchall()
        con.close()
        agg = {}
        for oid, res, n in rows:
            a = agg.setdefault(oid, {"W": 0, "L": 0, "D": 0})
            a[res[0]] = a.get(res[0], 0) + n
        return agg

    def pick(self, opponents, agg):
        beatable, unknown, risky = [], [], []
        for o in opponents:
            a = agg.get(o["id"])
            if not a:
                unknown.append(o)
                continue
            tot = a["W"] + a["L"] + a["D"]
            wr = a["W"] / tot if tot else 0.5
            if a["W"] >= 2 and wr >= 0.7:
                beatable.append((o, wr))
            elif a["L"] >= 2 and wr <= 0.3:
                risky.append((o, wr))
            else:
                unknown.append((o, 0.5))
        beatable.sort(key=lambda x: -x[1])
        pool = [x[0] for x in beatable] + [x[0] if isinstance(x, tuple) else x for x in unknown] \
               + [x[0] for x in risky[:2]]
        return pool[0] if pool else (opponents[0] if opponents else None)

    def pick_model(self, opponents):
        # v2: highest expected talent delta (see tools/opponent_model.py);
        # ties broken on talent inside pick_best.
        return opponent_model.pick_best(self.model_entry, opponents)

    def pick_modelv1(self, opponents):
        # v1: highest blended win probability only (no talent-EV transform).
        best, best_key = None, None
        for o in opponents:
            s = opponent_model.score_opponent(self.model_entry, o.get("id"), o.get("level"))
            key = (round(s, 9), o.get("talent") or 0, o.get("level") or 0)
            if best_key is None or key > best_key:
                best, best_key = o, key
        return best

    def record(self, fight, opp, result):
        con = sqlite3.connect(self.db_path)
        con.execute("""CREATE TABLE IF NOT EXISTS fight_history(
            fight_id INTEGER PRIMARY KEY, opponent_id INTEGER, opponent_name TEXT,
            opponent_level INTEGER, result TEXT, duration INTEGER, actions_count INTEGER,
            fight_url TEXT, timestamp TEXT)""")
        ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        # Schema drift: MCP-created DBs have 7 cols (no duration/actions_count),
        # runner-created ones have 9. Match whatever exists.
        cols = [r[1] for r in con.execute("PRAGMA table_info(fight_history)")]
        if "duration" in cols:
            con.execute("INSERT OR REPLACE INTO fight_history VALUES (?,?,?,?,?,?,?,?,?)",
                        (fight, opp.get("id"), opp.get("name"), opp.get("level"),
                         result, None, None, f"https://leekwars.com/fight/{fight}", ts))
        else:
            con.execute("INSERT OR REPLACE INTO fight_history VALUES (?,?,?,?,?,?,?)",
                        (fight, opp.get("id"), opp.get("name"), opp.get("level"),
                         result, f"https://leekwars.com/fight/{fight}", ts))
        con.commit()
        con.close()

    def run(self, n):
        agg = self.opp_stats()
        res_count = {"WIN": 0, "LOSS": 0, "DRAW": 0}
        t0 = time.time()
        for i in range(n):
            opps = self.call_get(f"/garden/get-leek-opponents/{self.leek_id}").get("opponents", [])
            if not opps:
                print("  no opponents, waiting 5s")
                time.sleep(5)
                continue
            if self.strategy == "model":
                opp = self.pick_model(opps)
            elif self.strategy == "modelv1":
                opp = self.pick_modelv1(opps)
            else:
                opp = self.pick(opps, agg)
            r = self.call_post("/garden/start-solo-fight",
                               {"leek_id": str(self.leek_id), "target_id": str(opp["id"])})
            fid = r.get("fight")
            if not fid:
                print(f"  fight {i+1}: start failed: {str(r)[:120]}")
                time.sleep(1.0)
                continue
            # result: poll until the server finishes the fight (winner -1
            # while processing; resolves in ~1-1.5s)
            result = None
            for _ in range(8):
                f = self.call_get(f"/fight/get/{fid}")
                winner = f.get("winner")
                if winner is not None and winner != -1:
                    result = "WIN" if winner == 1 else ("LOSS" if winner == 2 else "DRAW")
                    break
            if result is None:
                print(f"  fight {i+1}: {fid} never resolved, skipping")
                continue
            self.record(fid, opp, result)
            res_count[result] += 1
            a = agg.setdefault(opp["id"], {"W": 0, "L": 0, "D": 0})
            a[result[0]] += 1
            print(f"  [{i+1}/{n}] {result} vs {opp.get('name')} (fight {fid}) "
                  f"{time.time()-t0:.1f}s")
        print(f"done: {res_count} in {time.time()-t0:.0f}s ({(time.time()-t0)/max(1,n):.2f}s/fight)")
        return res_count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("leek_id", type=int)
    ap.add_argument("n", type=int)
    ap.add_argument("--account", default="main")
    ap.add_argument("--strategy", default="smart", choices=["smart", "model", "modelv1"],
                    help="opponent selection: 'smart' (current W/L policy) or "
                         "'model' (blended win-probability model, tools/opponent_model.py)")
    args = ap.parse_args()
    FastRunner(args.account, args.leek_id, strategy=args.strategy).run(args.n)


if __name__ == "__main__":
    main()
