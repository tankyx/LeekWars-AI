#!/usr/bin/env python3
"""
Enhanced V6 upload script - Uploads original AND refactored modules
Supports both the original V6 system and the new refactored V6.1 modules
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, Optional

class V6RefactoredUploader:
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
        """Find folder by name and parent"""
        for folder in folders:
            if folder["name"] == name and folder["folder"] == parent_id:
                return folder["id"]
        return None
    
    def create_folder(self, name: str, parent_id: int) -> Optional[int]:
        """Create new folder"""
        print(f"   📁 Creating folder: {name}")
        response = self.session.post(f"{self.base_url}/ai/new-folder", data={
            "folder": parent_id,
            "name": name
        })
        
        if response.status_code == 200:
            folder_id = response.json().get("folder")
            print(f"      ✅ Created folder (ID: {folder_id})")
            return folder_id
        
        print(f"      ❌ Failed to create folder")
        return None
    
    def create_or_get_folder(self, name: str, parent_id: int, existing_folders: list) -> Optional[int]:
        """Create folder if it doesn't exist, otherwise return existing ID"""
        folder_id = self.find_folder(name, parent_id, existing_folders)
        if folder_id:
            print(f"   📁 Using existing folder: {name} (ID: {folder_id})")
            return folder_id
        
        return self.create_folder(name, parent_id)
    
    def find_ai_script(self, name: str, folder_id: int, existing_ais: list) -> Optional[int]:
        """Find AI script by name and folder"""
        for ai in existing_ais:
            if ai["name"] == name and ai["folder"] == folder_id:
                return ai["id"]
        return None
    
    def create_or_update_ai_script(self, name: str, code: str, folder_id: int, existing_ais: list) -> Optional[int]:
        """Create or update AI script"""
        ai_id = self.find_ai_script(name, folder_id, existing_ais)
        
        if ai_id:
            print(f"   📄 Updating existing: {name} (ID: {ai_id})")
            # Update existing script
            response = self.session.post(
                f"{self.base_url}/ai/save", 
                data={
                    "ai": ai_id,
                    "code": code
                }
            )
            
            if response.status_code == 200:
                print(f"      ✅ Updated")
                return ai_id
            else:
                print(f"      ❌ Failed to update")
                return None
        
        # Create new script
        print(f"   📄 Creating new: {name}")
        for retry in range(3):  # Retry logic for rate limits
            if retry > 0:
                time.sleep(2 ** retry)  # Exponential backoff
            
            response = self.session.post(
                f"{self.base_url}/ai/new", 
                data={
                    "folder": folder_id,
                    "v2": "true"
                }
            )
            
            if response.status_code == 429:  # Rate limited
                print(f"      ⏳ Rate limited, retrying in {2 ** (retry + 1)} seconds...")
                continue
            elif response.status_code == 200:
                ai_id = response.json().get("ai")
                if ai_id:
                    # Set name and save code
                    save_response = self.session.post(
                        f"{self.base_url}/ai/save", 
                        data={
                            "ai": ai_id,
                            "name": name,
                            "code": code
                        }
                    )
                    
                    if save_response.status_code == 200:
                        print(f"      ✅ Created (ID: {ai_id})")
                        return ai_id
                    else:
                        print(f"      ⚠️  Created but failed to save code")
                else:
                    print(f"      ❌ Failed to create")
            else:
                print(f"      ❌ API error: {response.status_code}")
            
            break  # Only retry on 429, not other errors
        
        return None
    
    def upload_refactored_structure(self, v6_dir: Path, include_refactored: bool = True, include_original: bool = True):
        """Upload complete V6 structure including refactored modules"""
        print("\n📤 UPLOADING V6 STRUCTURE WITH REFACTORED MODULES")
        print("="*60)
        print(f"🔧 Include original modules: {'✅' if include_original else '❌'}")
        print(f"🆕 Include refactored modules: {'✅' if include_refactored else '❌'}")
        
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
        
        # Step 3: Upload main files
        main_files_uploaded = self.upload_main_files(v6_dir, folder_v6, existing_ais, include_refactored)
        
        # Step 4: Upload original modules if requested
        original_stats = {"total": 0, "success": 0, "failed": 0}
        if include_original:
            original_stats = self.upload_original_modules(v6_dir, folder_v6, existing_folders, existing_ais)
        
        # Step 5: Upload refactored modules if requested
        refactored_stats = {"total": 0, "success": 0, "failed": 0}
        if include_refactored:
            refactored_stats = self.upload_refactored_modules(v6_dir, folder_v6, existing_folders, existing_ais)
        
        # Summary
        self.print_upload_summary(original_stats, refactored_stats, v6_dir, include_original, include_refactored)
        
        return True
    
    def upload_main_files(self, v6_dir: Path, folder_v6: int, existing_ais: list, include_refactored: bool) -> bool:
        """Upload main V6 files"""
        print("\n3️⃣ Uploading main V6 files...")
        
        # Upload original V6_main.ls
        main_file = v6_dir / "V6_main.ls"
        if main_file.exists():
            with open(main_file, 'r', encoding='utf-8') as f:
                code = f.read()
            self.create_or_update_ai_script("V6_main", code, folder_v6, existing_ais)
        
        # Upload refactored V6_main_refactored.ls
        if include_refactored:
            refactored_main = v6_dir / "V6_main_refactored.ls"
            if refactored_main.exists():
                with open(refactored_main, 'r', encoding='utf-8') as f:
                    code = f.read()
                self.create_or_update_ai_script("V6_main_refactored", code, folder_v6, existing_ais)
                print("   🆕 Refactored main file uploaded!")
        
        # Upload B-Laser main file
        blaser_main_file = v6_dir / "V6_BLaser_main.ls"
        if blaser_main_file.exists():
            with open(blaser_main_file, 'r', encoding='utf-8') as f:
                code = f.read()
            self.create_or_update_ai_script("V6_BLaser_main", code, folder_v6, existing_ais)
        
        # Upload test file if it exists
        test_file = v6_dir / "test_refactored.ls"
        if test_file.exists() and include_refactored:
            with open(test_file, 'r', encoding='utf-8') as f:
                code = f.read()
            self.create_or_update_ai_script("test_refactored", code, folder_v6, existing_ais)
            print("   🧪 Test file uploaded!")
        
        return True
    
    def upload_original_modules(self, v6_dir: Path, folder_v6: int, existing_folders: list, existing_ais: list) -> Dict:
        """Upload original V6 modules"""
        print("\n4️⃣ Uploading original V6 modules...")
        
        categories = ['core', 'combat', 'movement', 'strategy', 'ai', 'utils', 'blaser']
        stats = {"total": 0, "success": 0, "failed": 0}
        
        for category in categories:
            print(f"\n📦 Processing original {category}/...")
            
            # Create or get category folder
            cat_folder = self.create_or_get_folder(category, folder_v6, existing_folders)
            if not cat_folder:
                print(f"   ⚠️  Failed to create {category} folder")
                continue
            
            self.folder_ids[category] = cat_folder
            
            # Upload all modules in this category (excluding refactored ones)
            category_path = v6_dir / category
            if not category_path.exists():
                print(f"   ⚠️  No local files for {category}")
                continue
            
            # Filter out refactored modules
            module_files = [f for f in sorted(category_path.glob("*.ls")) 
                          if not f.stem.endswith("_refactored")]
            
            print(f"   Found {len(module_files)} original modules to upload")
            
            for module_file in module_files:
                module_name = module_file.stem
                stats["total"] += 1
                
                with open(module_file, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                ai_id = self.create_or_update_ai_script(module_name, code, cat_folder, existing_ais)
                
                if ai_id:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
                
                time.sleep(0.8)  # Rate limiting
        
        return stats
    
    def upload_refactored_modules(self, v6_dir: Path, folder_v6: int, existing_folders: list, existing_ais: list) -> Dict:
        """Upload new refactored V6 modules"""
        print("\n5️⃣ Uploading refactored V6.1 modules...")
        
        stats = {"total": 0, "success": 0, "failed": 0}
        
        # Define refactored module structure
        refactored_modules = {
            "ai": [
                "emergency_decisions.ls",
                "tactical_decisions_ai.ls", 
                "combat_decisions.ls",
                "decision_making_refactored.ls"
            ],
            "combat": [
                "weapon_selection.ls",
                "positioning_logic.ls",
                "attack_execution.ls",
                "execute_combat_refactored.ls"
            ]
        }
        
        for category, module_list in refactored_modules.items():
            print(f"\n🆕 Processing refactored {category}/...")
            
            # Use existing category folder or create it
            if category not in self.folder_ids:
                cat_folder = self.create_or_get_folder(category, folder_v6, existing_folders)
                if not cat_folder:
                    print(f"   ⚠️  Failed to create {category} folder")
                    continue
                self.folder_ids[category] = cat_folder
            else:
                cat_folder = self.folder_ids[category]
            
            print(f"   Found {len(module_list)} refactored modules to upload")
            
            for module_filename in module_list:
                module_path = v6_dir / category / module_filename
                if not module_path.exists():
                    print(f"   ⚠️  Module not found: {module_filename}")
                    continue
                
                module_name = module_path.stem
                stats["total"] += 1
                
                with open(module_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                ai_id = self.create_or_update_ai_script(module_name, code, cat_folder, existing_ais)
                
                if ai_id:
                    stats["success"] += 1
                    print(f"   🆕 {module_name} uploaded successfully!")
                else:
                    stats["failed"] += 1
                
                time.sleep(0.8)  # Rate limiting
        
        # Upload standalone refactored files in root V6 directory
        root_refactored_files = [
            "REFACTORED_MODULE_INDEX.md"
        ]
        
        for filename in root_refactored_files:
            file_path = v6_dir / filename
            if file_path.exists():
                print(f"\n📚 Uploading {filename}...")
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # Convert .md to .ls for LeekWars compatibility
                name = filename.replace('.md', '_md')
                stats["total"] += 1
                
                ai_id = self.create_or_update_ai_script(name, code, folder_v6, existing_ais)
                if ai_id:
                    stats["success"] += 1
                    print(f"   📚 {name} uploaded as documentation!")
                else:
                    stats["failed"] += 1
                
                time.sleep(0.8)
        
        return stats
    
    def print_upload_summary(self, original_stats: Dict, refactored_stats: Dict, v6_dir: Path, 
                           include_original: bool, include_refactored: bool):
        """Print comprehensive upload summary"""
        print("\n" + "="*60)
        print("📊 UPLOAD COMPLETE - V6.1 REFACTORED SYSTEM")
        print("="*60)
        
        if include_original:
            print(f"✅ Original modules: {original_stats['success']}/{original_stats['total']}")
            if original_stats['failed'] > 0:
                print(f"❌ Original failed: {original_stats['failed']}")
        
        if include_refactored:
            print(f"🆕 Refactored modules: {refactored_stats['success']}/{refactored_stats['total']}")
            if refactored_stats['failed'] > 0:
                print(f"❌ Refactored failed: {refactored_stats['failed']}")
        
        total_success = original_stats['success'] + refactored_stats['success']
        total_modules = original_stats['total'] + refactored_stats['total']
        
        print(f"\n🎯 Total uploaded: {total_success}/{total_modules} modules")
        
        print("\n📁 V6.1 structure in LeekWars:")
        print("   6.0/")
        print("   └── V6/")
        print("       ├── V6_main.ls (original)")
        if include_refactored:
            print("       ├── V6_main_refactored.ls (V6.1)")
            print("       ├── test_refactored.ls")
        print("       ├── V6_BLaser_main.ls")
        
        categories = ['core', 'combat', 'movement', 'strategy', 'ai', 'utils', 'blaser']
        for category in categories:
            if category in self.folder_ids:
                category_path = v6_dir / category
                if category_path.exists():
                    modules = list(category_path.glob("*.ls"))
                    original_count = len([m for m in modules if not m.stem.endswith("_refactored")])
                    refactored_count = len([m for m in modules if m.stem.endswith("_refactored") or 
                                          m.stem in ["emergency_decisions", "tactical_decisions_ai", 
                                                   "combat_decisions", "weapon_selection", 
                                                   "positioning_logic", "attack_execution"]])
                    
                    if original_count > 0 or refactored_count > 0:
                        status_text = []
                        if original_count > 0:
                            status_text.append(f"{original_count} original")
                        if refactored_count > 0:
                            status_text.append(f"{refactored_count} refactored")
                        
                        print(f"       ├── {category}/ ({', '.join(status_text)})")
        
        if include_refactored:
            print("\n🆕 NEW REFACTORED MODULES AVAILABLE:")
            print("   🧠 AI Modules:")
            print("      • emergency_decisions.ls - Panic mode & emergency handling")
            print("      • tactical_decisions_ai.ls - Strategic positioning & teleportation")
            print("      • combat_decisions.ls - Combat execution & kill strategies")
            print("      • decision_making_refactored.ls - Clean orchestrator")
            print("   ⚔️  Combat Modules:")
            print("      • weapon_selection.ls - Weapon prioritization logic")
            print("      • positioning_logic.ls - Movement & positioning optimization")
            print("      • attack_execution.ls - Core attack orchestration")
            print("      • execute_combat_refactored.ls - Clean combat interface")
        
        print("\n✨ V6.1 REFACTORED SYSTEM IS READY!")
        print("🎯 Use V6_main_refactored.ls to test the new modular architecture")

def main():
    # Check if we're in the right directory
    v6_dir = Path("V6_modules")
    if not v6_dir.exists():
        print("❌ V6_modules directory not found. Please run from the LeekWars-AI root directory.")
        return
    
    uploader = V6RefactoredUploader()
    
    # Get credentials
    email = input("📧 Enter your LeekWars email: ")
    password = input("🔒 Enter your password: ")
    
    if not uploader.login(email, password):
        return
    
    # Ask what to upload
    print("\n🔧 What would you like to upload?")
    print("1. Both original and refactored modules (recommended)")
    print("2. Only refactored modules")
    print("3. Only original modules")
    
    choice = input("Enter choice (1-3): ").strip()
    
    include_original = choice in ["1", "3"]
    include_refactored = choice in ["1", "2"]
    
    if choice not in ["1", "2", "3"]:
        print("Using default: uploading both original and refactored modules")
        include_original = True
        include_refactored = True
    
    success = uploader.upload_refactored_structure(
        v6_dir, 
        include_refactored=include_refactored, 
        include_original=include_original
    )
    
    if success:
        print("\n🎉 Upload completed successfully!")
        if include_refactored:
            print("\n🚀 Next steps:")
            print("1. Test V6_main_refactored.ls in LeekWars")
            print("2. Compare performance with original V6_main.ls")
            print("3. Run battles to validate functionality")
    else:
        print("\n❌ Upload failed!")

if __name__ == "__main__":
    main()