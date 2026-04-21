#!/usr/bin/env python3
"""
V8 upload script - Creates structure and uploads V8 modules

Uses the path-based /ai/write API. The legacy /ai/get-farmer-ais,
/ai/save, /ai/new-name, and /ai-folder/new-name endpoints were removed
by LeekWars; inventory now lives under farmer.ai_tree and writes go
through /ai/write keyed by server-relative path.

Usage:
    python3 upload_v8.py              # Upload to main account
    python3 upload_v8.py --account cure  # Upload to cure account
"""

import os
import sys
import time
import requests
import argparse
from pathlib import Path
from typing import Set
from config_loader import load_credentials


SERVER_ROOT = "8.0/V8"  # paths under ai_tree for the V8 build


class V8Uploader:
    def __init__(self):
        self.base_url = "https://leekwars.com/api"
        self.session = requests.Session()
        self.token = None
        self.farmer = None
        self.existing_paths: Set[str] = set()

    def login(self, email: str, password: str) -> bool:
        """Login to LeekWars."""
        print("🔐 Logging in...")

        response = self.session.post(
            f"{self.base_url}/farmer/login-token",
            data={"login": email, "password": password},
        )

        if response.status_code == 200:
            data = response.json()
            if "farmer" in data and "token" in data:
                self.farmer = data["farmer"]
                self.token = data["token"]
                print(f"✅ Logged in as: {self.farmer.get('login')} (ID: {self.farmer.get('id')})")
                return True

        print("❌ Login failed")
        return False

    def load_ai_tree(self) -> bool:
        """Populate existing_paths from farmer.ai_tree (new path-based API)."""
        response = self.session.get(f"{self.base_url}/farmer/get-from-token")
        if response.status_code != 200:
            print(f"❌ Failed to fetch ai_tree: HTTP {response.status_code}")
            return False
        data = response.json()
        tree = (data.get("farmer") or {}).get("ai_tree") or {}
        self.existing_paths = {f.get("path") for f in tree.get("files", []) if f.get("path")}
        return True

    def upload_file(self, relative_path: str, code: str) -> bool:
        """Upload a single file under SERVER_ROOT/relative_path using /ai/write.

        /ai/write creates or updates in place; folders implied by the path must
        already exist (SERVER_ROOT is pre-created on both accounts).
        """
        server_path = f"{SERVER_ROOT}/{relative_path}"
        action = "Updating" if server_path in self.existing_paths else "Creating"
        print(f"   📄 {action}: {server_path}")

        max_retries = 3
        retry_delay = 2
        for attempt in range(max_retries):
            response = self.session.post(
                f"{self.base_url}/ai/write",
                data={"path": server_path, "code": code},
            )
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    print(f"      ⏳ Rate limited, waiting {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                print(f"      ❌ Rate limited after {max_retries} attempts")
                return False

            if response.status_code == 200:
                data = response.json()
                if data.get("modified"):
                    self.existing_paths.add(server_path)
                    print(f"      ✅ {action.rstrip('ing')}ed (modified: {data.get('modified')})")
                    return True
                print(f"      ❌ Write refused: {data}")
                return False

            print(f"      ❌ API error: {response.status_code}")
            return False

        return False

    def create_v8_structure(self, v8_dir: Path) -> bool:
        """Upload complete V8 module tree."""
        print("\n📤 CREATING/UPDATING V8 MODULAR STRUCTURE")
        print("=" * 60)

        print("\n0️⃣ Loading existing ai_tree...")
        if not self.load_ai_tree():
            return False
        print(f"   Found {len(self.existing_paths)} existing files under tracked roots")

        stats = {"total": 0, "success": 0, "failed": 0}

        root_modules = [
            "main", "game_entity", "item", "item_database", "item_roles",
            "field_map", "field_map_core", "field_map_patterns", "field_map_tactical",
            "kill_planning", "cooldown_tracker", "enemy_predictor", "enemy_intelligence",
            "performance_infra", "cache_manager", "tactical_awareness",
            "strategic_depth", "reachable_graph", "scenario_simulator", "scenario_scorer",
            "scenario_helpers", "scenario_combos", "scenario_generator",
            "scenario_quick_scorer", "scenario_mutation", "weight_profiles",
            "game_context", "bulb_ai", "boss_context", "beam_search",
        ]

        # Root-level modules
        print("\n1️⃣ Uploading root-level modules...")
        for module_name in root_modules:
            module_file = v8_dir / f"{module_name}.lk"
            if not module_file.exists():
                print(f"   ⚠️  Missing: {module_name}.lk")
                continue
            stats["total"] += 1
            with open(module_file, "r", encoding="utf-8") as f:
                code = f.read()
            ok = self.upload_file(f"{module_name}.lk", code)
            stats["success" if ok else "failed"] += 1
            time.sleep(0.5)

        # strategy/ subfolder
        print("\n2️⃣ Uploading strategy modules...")
        strategy_path = v8_dir / "strategy"
        if strategy_path.exists():
            strategy_files = sorted(strategy_path.glob("*.lk"))
            strategy_files = [
                f for f in strategy_files
                if "OLD_BACKUP" not in f.name and "BACKUP" not in f.name
            ]
            print(f"   Found {len(strategy_files)} strategy modules")
            for module_file in strategy_files:
                stats["total"] += 1
                with open(module_file, "r", encoding="utf-8") as f:
                    code = f.read()
                ok = self.upload_file(f"strategy/{module_file.name}", code)
                stats["success" if ok else "failed"] += 1
                time.sleep(0.5)
        else:
            print("   ⚠️  No strategy directory found")

        # math/ subfolder
        print("\n3️⃣ Uploading math modules...")
        math_path = v8_dir / "math"
        if math_path.exists():
            math_files = sorted(math_path.glob("*.lk"))
            print(f"   Found {len(math_files)} math modules")
            for module_file in math_files:
                stats["total"] += 1
                with open(module_file, "r", encoding="utf-8") as f:
                    code = f.read()
                ok = self.upload_file(f"math/{module_file.name}", code)
                stats["success" if ok else "failed"] += 1
                time.sleep(0.5)
        else:
            print("   ⚠️  No math directory found")

        # Re-save main.lk with build timestamp to force recompile
        # (generator caches compiled .lk and only checks the root file's mtime,
        #  so appending a comment guarantees the code differs)
        print("\n4️⃣ Re-saving main.lk to recompile with updated includes...")
        main_file = v8_dir / "main.lk"
        if main_file.exists():
            with open(main_file, "r", encoding="utf-8") as f:
                main_code = f.read()
            import datetime
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            stamped = main_code.rstrip() + f"\n// build: {ts}\n"
            if self.upload_file("main.lk", stamped):
                print(f"   ✅ main.lk recompiled (build: {ts})")
            else:
                print("   ❌ Failed to recompile main.lk")
            time.sleep(0.5)

        # Summary
        print("\n" + "=" * 60)
        print("📊 UPLOAD COMPLETE")
        print("=" * 60)
        print(f"✅ Successfully uploaded: {stats['success']}/{stats['total']} modules")
        if stats["failed"] > 0:
            print(f"❌ Failed: {stats['failed']} modules")

        return stats["success"] > 0

    def disconnect(self):
        """Disconnect from LeekWars."""
        if self.token:
            self.session.post(f"{self.base_url}/farmer/disconnect/{self.token}")
            print("\n👋 Disconnected")


def main():
    parser = argparse.ArgumentParser(description="Upload V8 modules to LeekWars")
    parser.add_argument(
        "--account", default="main", choices=["main", "cure"],
        help="Account to use (main or cure, default: main)",
    )
    args = parser.parse_args()

    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    v8_dir = script_dir.parent / "V8_modules"

    if not v8_dir.exists():
        print("❌ V8_modules directory not found")
        sys.exit(1)

    print("=" * 60)
    print("V8 MODULAR AI UPLOADER")
    print("=" * 60)
    print(f"📁 Source: {v8_dir}")
    print(f"👤 Account: {args.account}")

    uploader = V8Uploader()

    email, password = load_credentials(account=args.account)
    if not uploader.login(email, password):
        sys.exit(1)

    try:
        success = uploader.create_v8_structure(v8_dir)
        if not success:
            print("\n⚠️  Some issues occurred during upload")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        uploader.disconnect()


if __name__ == "__main__":
    main()
