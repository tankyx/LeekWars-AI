#!/usr/bin/env python3
"""
V8 upload script - Creates structure and uploads V8 modules
Adapted from V7 uploader for the modular V8 architecture

Usage:
    python3 upload_v8.py              # Upload to main account
    python3 upload_v8.py --account cure  # Upload to cure account
"""

import os
import sys
import json
import time
import requests
import argparse
from pathlib import Path
from typing import Dict, Optional
from config_loader import load_credentials

class V8Uploader:
    def __init__(self):
        self.base_url = "https://leekwars.com/api"
        self.session = requests.Session()
        self.token = None
        self.farmer = None
        self.folder_ids = {}

    def login(self, email: str, password: str) -> bool:
        """Login to LeekWars"""
        print("🔐 Logging in...")

        login_url = f"{self.base_url}/farmer/login-token"
        response = self.session.post(login_url, data={
            "login": email,
            "password": password
        })

        if response.status_code == 200:
            data = response.json()
            if "farmer" in data and "token" in data:
                self.farmer = data["farmer"]
                self.token = data["token"]
                print(f"✅ Logged in as: {self.farmer.get('login')} (ID: {self.farmer.get('id')})")
                return True

        print("❌ Login failed")
        return False

    def get_existing_folders(self) -> Dict:
        """Get all existing folders"""
        response = self.session.get(f"{self.base_url}/ai/get-farmer-ais")
        if response.status_code == 200:
            return response.json()
        return {"folders": [], "ais": []}

    def find_folder(self, name: str, parent_id: int, folders: list) -> Optional[int]:
        """Find a folder by name in parent"""
        for folder in folders:
            if folder["name"] == name and folder["folder"] == parent_id:
                return folder["id"]
        return None

    def find_ai(self, name: str, folder_id: int, ais: list) -> Optional[int]:
        """Find an AI by name in folder"""
        for ai in ais:
            if ai["name"] == name and ai["folder"] == folder_id:
                return ai["id"]
        return None

    def create_or_get_folder(self, name: str, parent_id: int = 0, existing_folders: list = None) -> Optional[int]:
        """Create a folder or return existing one"""
        # Check if folder already exists
        if existing_folders:
            folder_id = self.find_folder(name, parent_id, existing_folders)
            if folder_id:
                print(f"   📁 Using existing folder: {name} (ID: {folder_id})")
                return folder_id

        # Create new folder
        print(f"   📁 Creating folder: {name}")
        response = self.session.post(
            f"{self.base_url}/ai-folder/new-name",
            data={"folder_id": parent_id, "name": name}
        )

        if response.status_code == 200:
            data = response.json()
            folder_id = data.get("id")
            if folder_id:
                print(f"      ✅ Created with ID: {folder_id}")
                return folder_id

        print(f"      ❌ Failed to create")
        return None

    def create_or_update_ai_script(self, name: str, code: str, folder_id: int, existing_ais: list = None) -> Optional[int]:
        """Create an AI script and save its code with retry logic"""
        # Check if AI already exists
        if existing_ais:
            ai_id = self.find_ai(name, folder_id, existing_ais)
            if ai_id:
                print(f"   📄 Updating existing: {name}.lk (ID: {ai_id})")
                # Update existing AI
                save_response = self.session.post(
                    f"{self.base_url}/ai/save",
                    data={
                        "ai_id": str(ai_id),
                        "code": code
                    }
                )
                if save_response.status_code == 200:
                    print(f"      ✅ Updated")
                    return ai_id
                else:
                    print(f"      ❌ Failed to update")
                    return None

        print(f"   📄 Creating: {name}.lk")

        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            # Create AI with name
            response = self.session.post(
                f"{self.base_url}/ai/new-name",
                data={
                    "folder_id": folder_id,
                    "version": 4,
                    "name": name
                }
            )

            if response.status_code == 429:  # Rate limited
                if attempt < max_retries - 1:
                    print(f"      ⏳ Rate limited, waiting {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    print(f"      ❌ API error: 429 (rate limited after {max_retries} attempts)")
                    return None

            if response.status_code == 200:
                data = response.json()
                ai_data = data.get("ai", {})
                ai_id = ai_data.get("id")

                if ai_id:
                    # Save the code
                    save_response = self.session.post(
                        f"{self.base_url}/ai/save",
                        data={
                            "ai_id": str(ai_id),
                            "code": code
                        }
                    )

                    if save_response.status_code == 200:
                        print(f"      ✅ Uploaded (ID: {ai_id})")
                        return ai_id
                    else:
                        print(f"      ⚠️  Created but failed to save code")
                else:
                    print(f"      ❌ Failed to create")
            else:
                print(f"      ❌ API error: {response.status_code}")

            break  # Only retry on 429, not other errors

        return None

    def create_v8_structure(self, v8_dir: Path):
        """Create complete V8 structure with all modules"""
        print("\n📤 CREATING/UPDATING V8 MODULAR STRUCTURE")
        print("="*60)

        # Get existing structure first
        print("\n0️⃣ Checking existing structure...")
        existing_data = self.get_existing_folders()
        existing_folders = existing_data.get("folders", [])
        existing_ais = existing_data.get("ais", [])

        # Step 1: Create or get 8.0 folder
        print("\n1️⃣ Setting up root 8.0 folder...")
        folder_8_0 = self.create_or_get_folder("8.0", 0, existing_folders)
        if not folder_8_0:
            print("❌ Failed to setup 8.0 folder")
            return False
        self.folder_ids["8.0"] = folder_8_0

        # Step 2: Create or get V8 folder inside 8.0
        print("\n2️⃣ Setting up V8 folder...")
        folder_v8 = self.create_or_get_folder("V8", folder_8_0, existing_folders)
        if not folder_v8:
            print("❌ Failed to setup V8 folder")
            return False
        self.folder_ids["V8"] = folder_v8

        stats = {"total": 0, "success": 0, "failed": 0}

        # Step 3: Upload root-level V8 modules
        print("\n3️⃣ Uploading root-level modules...")
        root_modules = [
            "main",
            "game_entity",
            "item",
            "field_map",
            "field_map_core",
            "field_map_patterns",
            "field_map_tactical"
        ]

        for module_name in root_modules:
            module_file = v8_dir / f"{module_name}.lk"
            if module_file.exists():
                stats["total"] += 1
                with open(module_file, 'r', encoding='utf-8') as f:
                    code = f.read()
                # Include .lk extension in the uploaded name
                ai_id = self.create_or_update_ai_script(f"{module_name}.lk", code, folder_v8, existing_ais)
                if ai_id:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
                time.sleep(1.0)
            else:
                print(f"   ⚠️  Missing: {module_name}.lk")

        # Step 4: Create strategy folder and upload strategy modules
        print("\n4️⃣ Uploading strategy modules...")
        strategy_folder = self.create_or_get_folder("strategy", folder_v8, existing_folders)
        if not strategy_folder:
            print("   ⚠️  Failed to create strategy folder")
        else:
            self.folder_ids["strategy"] = strategy_folder

            # Upload strategy modules (excluding OLD_BACKUP files)
            strategy_path = v8_dir / "strategy"
            if strategy_path.exists():
                strategy_files = sorted(strategy_path.glob("*.lk"))
                # Filter out backup files
                strategy_files = [f for f in strategy_files if "OLD_BACKUP" not in f.name and "BACKUP" not in f.name]

                print(f"   Found {len(strategy_files)} strategy modules to upload")

                for module_file in strategy_files:
                    # Keep full filename including .lk extension
                    module_name = module_file.name
                    stats["total"] += 1

                    with open(module_file, 'r', encoding='utf-8') as f:
                        code = f.read()

                    ai_id = self.create_or_update_ai_script(module_name, code, strategy_folder, existing_ais)

                    if ai_id:
                        stats["success"] += 1
                    else:
                        stats["failed"] += 1

                    time.sleep(1.0)
            else:
                print("   ⚠️  No strategy directory found")

        # Step 5: Create math folder and upload math modules
        print("\n5️⃣ Uploading math modules...")
        math_folder = self.create_or_get_folder("math", folder_v8, existing_folders)
        if not math_folder:
            print("   ⚠️  Failed to create math folder")
        else:
            self.folder_ids["math"] = math_folder

            # Upload math modules (excluding README/markdown files)
            math_path = v8_dir / "math"
            if math_path.exists():
                math_files = sorted(math_path.glob("*.lk"))

                print(f"   Found {len(math_files)} math modules to upload")

                for module_file in math_files:
                    # Keep full filename including .lk extension
                    module_name = module_file.name
                    stats["total"] += 1

                    with open(module_file, 'r', encoding='utf-8') as f:
                        code = f.read()

                    ai_id = self.create_or_update_ai_script(module_name, code, math_folder, existing_ais)

                    if ai_id:
                        stats["success"] += 1
                    else:
                        stats["failed"] += 1

                    time.sleep(1.0)
            else:
                print("   ⚠️  No math directory found")

        # Summary
        print("\n" + "="*60)
        print("📊 UPLOAD COMPLETE")
        print("="*60)
        print(f"✅ Successfully uploaded: {stats['success']}/{stats['total']} modules")
        if stats['failed'] > 0:
            print(f"❌ Failed: {stats['failed']} modules")

        print("\n📁 V8 structure in LeekWars:")
        print("   8.0/")
        print("   └── V8/")
        print("       ├── main.lk")
        print("       ├── game_entity.lk")
        print("       ├── item.lk")
        print("       ├── field_map.lk")
        print("       ├── field_map_core.lk")
        print("       ├── field_map_patterns.lk")
        print("       ├── field_map_tactical.lk")
        print("       ├── strategy/")

        strategy_path = v8_dir / "strategy"
        if strategy_path.exists():
            modules = [f for f in sorted(strategy_path.glob("*.lk")) if "OLD_BACKUP" not in f.name]
            if modules:
                print(f"       │   ({len(modules)} modules)")
                for m in modules:
                    print(f"       │   ├── {m.name}")

        print("       └── math/")
        math_path = v8_dir / "math"
        if math_path.exists():
            math_modules = sorted(math_path.glob("*.lk"))
            if math_modules:
                print(f"           ({len(math_modules)} modules)")
                for m in math_modules:
                    print(f"           ├── {m.name}")

        print("\n✨ V8 MODULAR AI SYSTEM IS COMPLETE!")
        print("\n🚀 V8 KEY FEATURES:")
        print("   🎯 Action queue pattern (planning + execution phases)")
        print("   ⚔️  Build-specific strategies (Strength, Agility, Magic, Boss)")
        print("   🧠 Shared combat logic in base_strategy.lk")
        print("   💊 Magic antidote baiting + GRAPPLE-COVID combo")
        print("   🛡️  AoE self-damage prevention")
        print("   🏃 Fighting retreat (attack while fleeing)")
        print("   📍 Smart positioning (HNS, reachable cells)")
        print("   📊 Probability-based OTKO with kill probability calculation")

        print("\n📖 Usage:")
        print("   main.lk - Entry point with build detection")
        print("   include() statements: include('game_entity'), include('strategy/base_strategy')")

        return stats['success'] > 0

    def disconnect(self):
        """Disconnect from LeekWars"""
        if self.token:
            self.session.post(f"{self.base_url}/farmer/disconnect/{self.token}")
            print("\n👋 Disconnected")

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Upload V8 modules to LeekWars')
    parser.add_argument('--account', default='main', choices=['main', 'cure'],
                        help='Account to use (main or cure, default: main)')
    args = parser.parse_args()

    # Get V8_modules path relative to script location
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    v8_dir = script_dir.parent / "V8_modules"

    if not v8_dir.exists():
        print("❌ V8_modules directory not found")
        sys.exit(1)

    # Count total modules
    total_modules = 0
    root_modules = ["main", "game_entity", "item", "field_map", "field_map_core",
                    "field_map_patterns", "field_map_tactical"]
    for module in root_modules:
        if (v8_dir / f"{module}.lk").exists():
            total_modules += 1

    strategy_path = v8_dir / "strategy"
    if strategy_path.exists():
        strategy_files = [f for f in strategy_path.glob("*.lk") if "OLD_BACKUP" not in f.name]
        total_modules += len(strategy_files)

    print("="*60)
    print("V8 MODULAR AI UPLOADER")
    print("="*60)
    print(f"📁 Source: {v8_dir}")
    print(f"📦 Total modules to upload: {total_modules}")
    print(f"🏗️  Architecture: Action queue pattern + build-specific strategies")
    print(f"👤 Account: {args.account}")

    uploader = V8Uploader()

    # Login with credentials from config
    email, password = load_credentials(account=args.account)
    if not uploader.login(email, password):
        sys.exit(1)

    try:
        # Create structure and upload all modules
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

if __name__ == '__main__':
    main()
