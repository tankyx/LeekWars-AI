#!/usr/bin/env python3
"""
Upload all V6 module files to their respective folders in LeekWars
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional

class V6ModulesUploader:
    def __init__(self):
        self.base_url = "https://leekwars.com/api"
        self.session = requests.Session()
        self.token = None
        self.farmer = None
        
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
    
    def get_folder_structure(self):
        """Get current folder structure to find our V6 folders"""
        print("\n📋 Getting folder structure...")
        
        response = self.session.get(f"{self.base_url}/farmer/get/{self.farmer['id']}")
        
        if response.status_code == 200:
            data = response.json()
            if "farmer" in data:
                folders = data["farmer"].get("folders", [])
                
                # Build folder map
                folder_map = {}
                for folder in folders:
                    folder_name = folder.get("name")
                    folder_id = folder.get("id")
                    parent_id = folder.get("parent")
                    
                    # Store with parent info for hierarchy
                    folder_map[folder_id] = {
                        "name": folder_name,
                        "parent": parent_id,
                        "id": folder_id
                    }
                
                return folder_map
        
        return {}
    
    def find_v6_folders(self, folder_map):
        """Find the V6 folder IDs we created"""
        v6_structure = {}
        
        # Find 6.0 folder
        for folder_id, folder_info in folder_map.items():
            if folder_info["name"] == "6.0" and (folder_info["parent"] == 0 or folder_info["parent"] is None):
                v6_structure["6.0"] = folder_id
                break
        
        if "6.0" not in v6_structure:
            print("❌ 6.0 folder not found")
            return None
        
        # Find V6 folder inside 6.0
        for folder_id, folder_info in folder_map.items():
            if folder_info["name"] == "V6" and folder_info["parent"] == v6_structure["6.0"]:
                v6_structure["V6"] = folder_id
                break
        
        if "V6" not in v6_structure:
            print("❌ V6 folder not found inside 6.0")
            return None
        
        # Find category folders inside V6
        categories = ['core', 'combat', 'movement', 'strategy', 'ai', 'utils']
        for category in categories:
            for folder_id, folder_info in folder_map.items():
                if folder_info["name"] == category and folder_info["parent"] == v6_structure["V6"]:
                    v6_structure[category] = folder_id
                    break
        
        return v6_structure
    
    def create_ai_module(self, name: str, code: str, folder_id: int) -> bool:
        """Create an AI module script"""
        print(f"      📄 Uploading: {name}")
        
        # Create AI with name
        response = self.session.post(
            f"{self.base_url}/ai/new-name",
            data={
                "folder_id": folder_id,
                "version": 4,
                "name": name
            }
        )
        
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
                    result = save_response.json()
                    if result.get("success") or "result" in result:
                        print(f"         ✅ Success (ID: {ai_id})")
                        return True
                
                print(f"         ❌ Failed to save code")
            else:
                print(f"         ❌ Failed to create AI")
        else:
            print(f"         ❌ Failed (Status: {response.status_code})")
        
        return False
    
    def upload_all_modules(self, v6_dir: Path):
        """Upload all module files to their respective folders"""
        print("\n📤 UPLOADING V6 MODULES")
        print("="*60)
        
        # Get folder structure
        folder_map = self.get_folder_structure()
        v6_folders = self.find_v6_folders(folder_map)
        
        if not v6_folders:
            print("❌ Could not find V6 folder structure")
            return False
        
        print(f"\n✅ Found V6 structure:")
        print(f"   6.0 (ID: {v6_folders['6.0']})")
        print(f"   └── V6 (ID: {v6_folders['V6']})")
        for category in ['core', 'combat', 'movement', 'strategy', 'ai', 'utils']:
            if category in v6_folders:
                print(f"       ├── {category} (ID: {v6_folders[category]})")
        
        # Upload modules for each category
        categories = ['core', 'combat', 'movement', 'strategy', 'ai', 'utils']
        total_uploaded = 0
        total_failed = 0
        
        for category in categories:
            if category not in v6_folders:
                print(f"\n⚠️  Skipping {category} - folder not found")
                continue
            
            category_path = v6_dir / category
            if not category_path.exists():
                print(f"\n⚠️  Skipping {category} - no local files")
                continue
            
            print(f"\n📦 Uploading {category} modules...")
            
            # Get all .ls files in this category
            module_files = sorted(category_path.glob("*.ls"))
            
            for module_file in module_files:
                module_name = module_file.stem  # Remove .ls extension
                
                # Read the module code
                with open(module_file, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # Upload the module
                if self.create_ai_module(module_name, code, v6_folders[category]):
                    total_uploaded += 1
                else:
                    total_failed += 1
                
                # Rate limiting
                time.sleep(0.5)
        
        # Also upload the main file to V6 folder if not already there
        print(f"\n📦 Checking main files in V6 folder...")
        main_file = v6_dir / "V6_main.ls"
        if main_file.exists():
            with open(main_file, 'r', encoding='utf-8') as f:
                code = f.read()
            
            print("   Uploading V6_main.ls (if not exists)...")
            # This might fail if it already exists, that's ok
            self.create_ai_module("V6_main", code, v6_folders["V6"])
        
        # Summary
        print("\n" + "="*60)
        print("📊 UPLOAD SUMMARY")
        print("="*60)
        print(f"✅ Successfully uploaded: {total_uploaded} modules")
        if total_failed > 0:
            print(f"❌ Failed: {total_failed} modules")
        
        print("\n📁 Module structure in LeekWars:")
        print("   6.0/")
        print("   └── V6/")
        print("       ├── V6_main.ls (main script)")
        
        for category in categories:
            if category in v6_folders:
                category_path = v6_dir / category
                if category_path.exists():
                    module_files = list(category_path.glob("*.ls"))
                    if module_files:
                        print(f"       ├── {category}/")
                        for f in sorted(module_files)[:3]:
                            print(f"       │   ├── {f.stem}.ls")
                        if len(module_files) > 3:
                            print(f"       │   └── ... ({len(module_files)} total)")
        
        print("\n✨ V6 modular structure is complete!")
        print("   The V6_main.ls script can now use include() to load modules")
        print("   Example: include('core/globals');")
        
        return True
    
    def disconnect(self):
        """Disconnect from LeekWars"""
        if self.token:
            self.session.post(f"{self.base_url}/farmer/disconnect/{self.token}")
            print("\n👋 Disconnected")

def main():
    v6_dir = Path("/home/ubuntu/V6_modules")
    
    if not v6_dir.exists():
        print("❌ V6_modules directory not found")
        sys.exit(1)
    
    uploader = V6ModulesUploader()
    
    # Login
    if not uploader.login("tanguy.pedrazzoli@gmail.com", "tanguy0211"):
        sys.exit(1)
    
    try:
        # Upload all modules
        success = uploader.upload_all_modules(v6_dir)
        
        if not success:
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