#!/usr/bin/env python3
"""
Complete V6 upload - Creates structure and uploads ALL module files
Now includes V6.1 refactored modules for improved performance and maintainability
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, Optional

class V6CompleteUploader:
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
                print(f"   📄 Updating existing: {name}.ls (ID: {ai_id})")
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
        
        print(f"   📄 Creating: {name}.ls")
        
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
    
    def create_full_structure(self, v6_dir: Path):
        """Create complete V6 structure with all modules"""
        print("\n📤 CREATING/UPDATING V6 STRUCTURE WITH MODULES")
        print("="*60)
        
        # Get existing structure first
        print("\n0️⃣ Checking existing structure...")
        existing_data = self.get_existing_folders()
        existing_folders = existing_data.get("folders", [])
        existing_ais = existing_data.get("ais", [])
        
        # Step 1: Create or get 6.0 folder
        print("\n1️⃣ Setting up root 6.0 folder...")
        folder_6_0 = self.create_or_get_folder("6.0", 0, existing_folders)
        if not folder_6_0:
            print("❌ Failed to setup 6.0 folder")
            return False
        self.folder_ids["6.0"] = folder_6_0
        
        # Step 2: Create or get V6 folder inside 6.0
        print("\n2️⃣ Setting up V6 folder...")
        folder_v6 = self.create_or_get_folder("V6", folder_6_0, existing_folders)
        if not folder_v6:
            print("❌ Failed to setup V6 folder")
            return False
        self.folder_ids["V6"] = folder_v6
        
        # Step 3: Upload main V6 file
        print("\n3️⃣ Uploading main V6 file...")
        main_file = v6_dir / "V6_main.ls"
        if main_file.exists():
            with open(main_file, 'r', encoding='utf-8') as f:
                code = f.read()
            self.create_or_update_ai_script("V6_main", code, folder_v6, existing_ais)
        
        # Step 3.5: Skip problematic files that shouldn't be uploaded
        # - test_refactored.ls (has invalid syntax)
        # - REFACTORED_MODULE_INDEX.md (markdown file, not LeekScript)
        # - V6_BLaser_main.ls (not needed)  
        # - V6_main_refactored.ls (not needed)
        print("\n   ⚠️  Skipping problematic files: test_refactored, REFACTORED_MODULE_INDEX.md, V6_BLaser_main, V6_main_refactored")
        
        # Step 4: Create category folders and upload modules
        print("\n4️⃣ Creating categories and uploading modules...")
        categories = ['core', 'combat', 'movement', 'strategy', 'ai', 'utils', 'blaser']
        
        stats = {"total": 0, "success": 0, "failed": 0}
        
        for category in categories:
            print(f"\n📦 Processing {category}/...")
            
            # Create or get category folder
            cat_folder = self.create_or_get_folder(category, folder_v6, existing_folders)
            if not cat_folder:
                print(f"   ⚠️  Failed to create {category} folder")
                continue
            
            self.folder_ids[category] = cat_folder
            
            # Upload all modules in this category
            category_path = v6_dir / category
            if not category_path.exists():
                print(f"   ⚠️  No local files for {category}")
                continue
            
            module_files = sorted(category_path.glob("*.ls"))
            print(f"   Found {len(module_files)} modules to upload")
            
            for module_file in module_files:
                module_name = module_file.stem
                
                # Skip problematic files
                if module_name in ["test_refactored", "REFACTORED_MODULE_INDEX", "V6_BLaser_main", "V6_main_refactored"]:
                    print(f"   ⏭️  Skipping: {module_name}.ls (problematic file)")
                    continue
                
                stats["total"] += 1
                
                with open(module_file, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # Upload or update the module
                ai_id = self.create_or_update_ai_script(module_name, code, cat_folder, existing_ais)
                
                if ai_id:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
                
                # Rate limiting
                time.sleep(0.8)  # Increased delay to avoid rate limits
        
        # Summary
        print("\n" + "="*60)
        print("📊 UPLOAD COMPLETE")
        print("="*60)
        print(f"✅ Successfully uploaded: {stats['success']}/{stats['total']} modules")
        if stats['failed'] > 0:
            print(f"❌ Failed: {stats['failed']} modules")
        
        print("\n📁 Final V6 structure in LeekWars:")
        print("   6.0/")
        print("   └── V6/")
        print("       ├── V6_main.ls")
        
        for category in categories:
            if category in self.folder_ids:
                category_path = v6_dir / category
                if category_path.exists():
                    modules = list(category_path.glob("*.ls"))
                    if modules:
                        # Count refactored modules
                        refactored_modules = [m for m in modules if 
                                            m.stem in ["emergency_decisions", "tactical_decisions_ai", 
                                                     "combat_decisions", "decision_making_refactored",
                                                     "weapon_selection", "positioning_logic", 
                                                     "attack_execution", "execute_combat_refactored"]]
                        original_modules = [m for m in modules if m not in refactored_modules]
                        
                        status_parts = []
                        if original_modules:
                            status_parts.append(f"{len(original_modules)} original")
                        if refactored_modules:
                            status_parts.append(f"{len(refactored_modules)} 🆕 refactored")
                        
                        status = ", ".join(status_parts) if status_parts else str(len(modules))
                        print(f"       ├── {category}/ ({status})")
                        
                        # Show refactored modules specifically
                        for m in refactored_modules:
                            print(f"       │   ├── 🆕 {m.stem}.ls")
                        
                        # Show a few original modules
                        shown = len(refactored_modules)
                        for m in sorted(original_modules)[:max(0, 2-shown)]:
                            print(f"       │   ├── {m.stem}.ls")
                        
                        remaining = len(modules) - shown - max(0, 2-shown)
                        if remaining > 0:
                            print(f"       │   └── ... and {remaining} more")
        
        print("\n✨ V6 REFACTORED SYSTEM IS COMPLETE!")
        
        # Check if refactored modules exist
        has_refactored = any([
            (v6_dir / "ai" / "emergency_decisions.ls").exists(),
            (v6_dir / "ai" / "tactical_decisions_ai.ls").exists(),
            (v6_dir / "combat" / "weapon_selection.ls").exists()
        ])
        
        if has_refactored:
            print("\n🆕 REFACTORED MODULES INCLUDED:")
            print("   🧠 AI: emergency_decisions, tactical_decisions_ai, combat_decisions, decision_making_refactored")
            print("   ⚔️  Combat: weapon_selection, positioning_logic, attack_execution, execute_combat_refactored")
            print("   🎯 V6_main.ls now uses the refactored modular architecture!")
        
        print("\n📖 Usage:")
        print("   V6_main.ls - Refactored modular architecture with better performance")
        print("   include() statements work like: include('core/globals'), include('combat/weapon_selection')")
        
        return stats['success'] > 0
    
    def disconnect(self):
        """Disconnect from LeekWars"""
        if self.token:
            self.session.post(f"{self.base_url}/farmer/disconnect/{self.token}")
            print("\n👋 Disconnected")

def main():
    # Get V6_modules path relative to script location
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    v6_dir = script_dir.parent / "V6_modules"
    
    if not v6_dir.exists():
        print("❌ V6_modules directory not found")
        sys.exit(1)
    
    # Count total modules
    total_modules = 0
    for category in ['core', 'combat', 'movement', 'strategy', 'ai', 'utils', 'blaser']:
        cat_path = v6_dir / category
        if cat_path.exists():
            total_modules += len(list(cat_path.glob("*.ls")))
    
    # Count main files
    main_files = 0
    if (v6_dir / "V6_main.ls").exists():
        main_files += 1
    if (v6_dir / "V6_BLaser_main.ls").exists():
        main_files += 1
    
    print("="*60)
    print("V6 COMPLETE MODULE UPLOADER")
    print("="*60)
    print(f"📁 Source: {v6_dir}")
    print(f"📦 Total modules to upload: {total_modules + main_files}")
    
    uploader = V6CompleteUploader()
    
    # Login
    if not uploader.login("tanguy.pedrazzoli@gmail.com", "tanguy0211"):
        sys.exit(1)
    
    try:
        # Create structure and upload all modules
        success = uploader.create_full_structure(v6_dir)
        
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