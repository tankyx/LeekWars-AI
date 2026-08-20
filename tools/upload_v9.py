#!/usr/bin/env python3
"""Upload V9 (V9_modules/) to LeekWars as 9.0/V9/* — SIDE BY SIDE with V8.

Never touches 8.0/V8/* and never changes any leek's AI assignment. V9 starts
with zero leeks; trials are per-leek opt-in via leekwars_set_leek_ai.

Usage: python3 tools/upload_v9.py [--account main|cure]
"""
import argparse
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config_loader import load_credentials  # noqa: E402

BASE = "https://leekwars.com/api"
V9_DIR = Path(__file__).parent.parent / "V9_modules"
ROOT_PATH = "9.0/V9"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="main", choices=["main", "cure"])
    args = ap.parse_args()

    login, password = load_credentials(account=args.account)
    s = requests.Session()
    r = s.post(f"{BASE}/farmer/login-token", data={"login": login, "password": password})
    farmer = r.json()["farmer"]
    print(f"logged in: {farmer['login']}")

    existing = {f.get("path") for f in (farmer.get("ai_tree", {}).get("files") or [])}

    # Root modules + strategy/ subfolder (V9 needs strategy/unified_strategy.lk
    # etc. — the rollout veto hooks into it). Server path mirrors the local
    # relative path: strategy/foo.lk -> 9.0/V9/strategy/foo.lk.
    files = sorted(p for p in V9_DIR.glob("*.lk") if "BACKUP" not in p.name)
    strategy_dir = V9_DIR / "strategy"
    if strategy_dir.is_dir():
        files += sorted(p for p in strategy_dir.glob("*.lk") if "BACKUP" not in p.name)
    mains = [p for p in files if p.name == "main.lk" and p.parent == V9_DIR]
    others = [p for p in files if p not in mains]

    stats = {"created": 0, "updated": 0, "failed": 0}
    import time
    for p in others + mains:  # main.lk LAST so includes resolve first
        rel = p.relative_to(V9_DIR).as_posix()
        server_path = f"{ROOT_PATH}/{rel}"
        code = p.read_text()
        j = None
        for attempt in range(5):
            res = s.post(f"{BASE}/ai/write", json={"path": server_path, "code": code})
            try:
                j = res.json()
            except Exception:
                j = {"_http": res.status_code, "_text": res.text[:200]}
            if res.status_code == 200 and j.get("modified"):
                break
            if isinstance(j, dict) and j.get("error") == "rate_limit":
                time.sleep(float(j.get("retry_after", 1)) + 0.4)
                continue
            break
        if res.status_code == 200 and j.get("modified"):
            action = "updated" if server_path in existing else "created"
            stats[action] += 1
            print(f"  {'~' if action == 'updated' else '+'} {rel}")
        else:
            stats["failed"] += 1
            print(f"  ! {rel}: {j}")
        time.sleep(0.3)

    print(f"V9 upload complete [{args.account}] -> {ROOT_PATH}/ "
          f"created={stats['created']} updated={stats['updated']} failed={stats['failed']}")
    if stats["failed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
