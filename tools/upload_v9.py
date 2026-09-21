#!/usr/bin/env python3
"""Upload V9 (V9_modules/) to LeekWars as 9.0/V9/* — SIDE BY SIDE with V8.

Never touches 8.0/V8/* and never changes any leek's AI assignment. V9 starts
with zero leeks; trials are per-leek opt-in via leekwars_set_leek_ai.

Usage: python3 tools/upload_v9.py [--account main|cure]
"""
import argparse
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config_loader import load_credentials  # noqa: E402

BASE = "https://leekwars.com/api"
V9_DIR = Path(__file__).parent.parent / "V9_modules"
ROOT_PATH = "9.0/V9"


def resolve_includes(root: Path, entry: str) -> list:
    """Every module reachable from `entry` via include(), as posix relpaths.

    include() paths are relative to the including file, so strategy/*.lk
    reference the root modules as '../foo.lk' — normalise before recursing or
    the closure silently drops them.
    """
    import re

    seen, order, stack = set(), [], [entry]
    while stack:
        rel = stack.pop()
        rel = os.path.normpath(rel).replace(os.sep, "/")
        if rel in seen:
            continue
        path = root / rel
        if not path.is_file():
            print(f"  warning: include target not found, skipping: {rel}")
            continue
        seen.add(rel)
        order.append(rel)
        base = os.path.dirname(rel)
        for m in re.findall(r"include\(\s*['\"]([^'\"]+)['\"]\s*\)", path.read_text()):
            # A bare include() from inside strategy/ is ambiguous: it resolves
            # relative to the including file locally, but we do not know that
            # the server resolves it the same way -- and the tree carries a
            # byte-identical V9_modules/action.lk alongside
            # V9_modules/strategy/action.lk, which is what that duplicate is
            # for. Ship every candidate that exists rather than guess; an extra
            # identical file is harmless, a missing one breaks the server build.
            cands = [os.path.join(base, m)] if base else [m]
            if base and (root / m).is_file():
                cands.append(m)
            for c in cands:
                stack.append(c)
    return sorted(order)


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

    # Upload exactly the transitive include closure of main.lk. The old filter
    # was a single "BACKUP" name check over glob("*.lk"), which shipped every
    # stray dev copy in the tree to the server AI folder — main_iso.lk,
    # enemy_model_data_iso.lk and enemy_model_data.lk.test.lk (that last one
    # ends in .lk, so the glob caught it) — plus the two modules nothing
    # includes any more, rollout.lk and generators.lk. Resolving the closure
    # instead is self-maintaining: a new module ships the moment something
    # includes it, and a file that stops being included stops being uploaded.
    # Server path mirrors the local relative path: strategy/foo.lk ->
    # 9.0/V9/strategy/foo.lk.
    files = [V9_DIR / rel for rel in resolve_includes(V9_DIR, "main.lk")]
    skipped = sorted(
        {p.relative_to(V9_DIR).as_posix()
         for p in list(V9_DIR.glob("*.lk")) + list((V9_DIR / "strategy").glob("*.lk"))}
        - {p.relative_to(V9_DIR).as_posix() for p in files}
    )
    if skipped:
        print(f"not included by main.lk, not uploading ({len(skipped)}): {', '.join(skipped)}")
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
