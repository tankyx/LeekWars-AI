#!/usr/bin/env python3
"""
Check the actual structure in LeekWars with detailed logging
"""

import sys
import json
import requests
from typing import List, Dict

class LeekWarsStructureChecker:
    def __init__(self):
        self.base_url = "https://leekwars.com/api"
        self.session = requests.Session()
        self.token = None
        self.farmer = None
        
    def login(self, email: str, password: str) -> bool:
        """Login to LeekWars"""
        print("🔐 Logging in...")
        
        response = self.session.post(
            f"{self.base_url}/farmer/login-token",
            data={"login": email, "password": password}
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
    
    def check_structure(self):
        """Check all folders and AIs with detailed logging"""
        print("\n📋 Getting farmer data...")
        
        # Try different endpoints
        print("\n1️⃣ Trying farmer/get endpoint...")
        response = self.session.get(f"{self.base_url}/farmer/get/{self.farmer['id']}")
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response keys: {list(data.keys())}")
            
            if "farmer" in data:
                farmer_data = data["farmer"]
                print(f"   Farmer data keys: {list(farmer_data.keys())}")
                
                # Check folders
                folders = farmer_data.get("folders", [])
                print(f"\n📁 FOLDERS ({len(folders)} total):")
                
                if folders:
                    # Group by parent
                    root_folders = []
                    child_folders = {}
                    
                    for folder in folders:
                        parent = folder.get("parent")
                        if parent == 0 or parent is None:
                            root_folders.append(folder)
                        else:
                            if parent not in child_folders:
                                child_folders[parent] = []
                            child_folders[parent].append(folder)
                    
                    print(f"\n   Root folders ({len(root_folders)}):")
                    for folder in root_folders:
                        folder_id = folder.get("id")
                        folder_name = folder.get("name", f"UNNAMED_{folder_id}")
                        print(f"   └── {folder_name} (ID: {folder_id})")
                        
                        # Show children
                        if folder_id in child_folders:
                            for child in child_folders[folder_id]:
                                child_name = child.get("name", f"UNNAMED_{child.get('id')}")
                                child_id = child.get("id")
                                print(f"       └── {child_name} (ID: {child_id})")
                                
                                # Show grandchildren
                                if child_id in child_folders:
                                    for grandchild in child_folders[child_id]:
                                        gc_name = grandchild.get("name", f"UNNAMED_{grandchild.get('id')}")
                                        gc_id = grandchild.get("id")
                                        print(f"           └── {gc_name} (ID: {gc_id})")
                else:
                    print("   No folders found")
                
                # Check AIs
                ais = farmer_data.get("ais", [])
                print(f"\n📄 SCRIPTS ({len(ais)} total):")
                
                if ais:
                    # Group by folder
                    root_ais = []
                    folder_ais = {}
                    
                    for ai in ais:
                        folder = ai.get("folder")
                        if folder == 0 or folder is None:
                            root_ais.append(ai)
                        else:
                            if folder not in folder_ais:
                                folder_ais[folder] = []
                            folder_ais[folder].append(ai)
                    
                    if root_ais:
                        print(f"\n   Root scripts ({len(root_ais)}):")
                        for ai in root_ais:
                            ai_name = ai.get("name", f"UNNAMED_{ai.get('id')}")
                            ai_id = ai.get("id")
                            print(f"   - {ai_name} (ID: {ai_id})")
                    
                    # Show scripts per folder
                    for folder_id, scripts in folder_ais.items():
                        folder_name = "Unknown"
                        for f in folders:
                            if f.get("id") == folder_id:
                                folder_name = f.get("name", f"UNNAMED_{folder_id}")
                                break
                        
                        print(f"\n   Scripts in {folder_name} (ID: {folder_id}):")
                        for ai in scripts[:5]:  # Show first 5
                            ai_name = ai.get("name", f"UNNAMED_{ai.get('id')}")
                            print(f"   - {ai_name}")
                        if len(scripts) > 5:
                            print(f"   ... and {len(scripts) - 5} more")
                else:
                    print("   No scripts found")
                
                # Raw data dump for debugging
                print("\n📊 RAW FOLDER DATA (first 3):")
                for folder in folders[:3]:
                    print(f"   Folder: {json.dumps(folder, indent=2)}")
                
                return folders, ais
        
        # Try alternate endpoints
        print("\n2️⃣ Trying ai-folder/get-farmer-folders endpoint...")
        response = self.session.get(f"{self.base_url}/ai-folder/get-farmer-folders/{self.farmer['id']}")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)[:500]}")
        
        return [], []
    
    def disconnect(self):
        """Disconnect from LeekWars"""
        if self.token:
            self.session.post(f"{self.base_url}/farmer/disconnect/{self.token}")
            print("\n👋 Disconnected")

def main():
    print("="*60)
    print("LEEKWARS STRUCTURE CHECKER")
    print("="*60)
    
    checker = LeekWarsStructureChecker()
    
    # Login
    if not checker.login(*load_credentials()):
        sys.exit(1)
    
    try:
        # Check structure
        folders, ais = checker.check_structure()
        
        # Summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        
        if folders or ais:
            root_folders = [f for f in folders if f.get("parent") in [0, None]]
            root_ais = [a for a in ais if a.get("folder") in [0, None]]
            
            print(f"📁 Total folders: {len(folders)} ({len(root_folders)} in root)")
            print(f"📄 Total scripts: {len(ais)} ({len(root_ais)} in root)")
            
            # Check for items to clean
            import re
            version_pattern = r'^\d+\.0$'
            
            folders_to_delete = []
            for f in root_folders:
                name = f.get("name", "")
                if not re.match(version_pattern, name):
                    folders_to_delete.append(f)
            
            if folders_to_delete:
                print(f"\n🗑️  Folders that should be deleted from root:")
                for f in folders_to_delete:
                    print(f"   - {f.get('name', 'UNNAMED')} (ID: {f.get('id')})")
            
            if root_ais:
                print(f"\n🗑️  Scripts that should be deleted from root:")
                for a in root_ais:
                    print(f"   - {a.get('name', 'UNNAMED')} (ID: {a.get('id')})")
        else:
            print("⚠️  No data retrieved - might be an API issue")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
from config_loader import load_credentials
        traceback.print_exc()
        return 1
    finally:
        checker.disconnect()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())