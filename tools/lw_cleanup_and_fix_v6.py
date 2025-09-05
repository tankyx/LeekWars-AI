#!/usr/bin/env python3
"""
Clean up LeekWars mess and properly upload V6
Uses correct DELETE endpoints for cleanup
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional

class LeekWarsCleanupAndFix:
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
    
    def get_all_folders_and_ais(self):
        """Get all folders and AIs from farmer data"""
        print("\n📋 Getting current structure...")
        
        response = self.session.get(f"{self.base_url}/farmer/get/{self.farmer['id']}")
        
        if response.status_code == 200:
            data = response.json()
            if "farmer" in data:
                farmer_data = data["farmer"]
                folders = farmer_data.get("folders", [])
                ais = farmer_data.get("ais", [])
                
                print(f"   Found {len(folders)} folders and {len(ais)} AIs")
                return folders, ais
        
        return [], []
    
    def delete_folder_properly(self, folder_id: int, name: str) -> bool:
        """Delete a folder using DELETE method"""
        print(f"   🗑️  Deleting folder: {name} (ID: {folder_id})")
        
        # Use DELETE method as shown in frontend code
        response = self.session.request(
            "DELETE",
            f"{self.base_url}/ai-folder/delete",
            json={"folder_id": folder_id}
        )
        
        if response.status_code == 200:
            print(f"      ✅ Deleted successfully")
            return True
        
        # Fallback to POST with data (not json)
        response = self.session.post(
            f"{self.base_url}/ai-folder/delete",
            data={"folder_id": folder_id}
        )
        
        if response.status_code == 200:
            print(f"      ✅ Deleted successfully (POST method)")
            return True
        
        print(f"      ❌ Failed to delete (Status: {response.status_code})")
        return False
    
    def delete_ai_properly(self, ai_id: int, name: str) -> bool:
        """Delete an AI using DELETE method"""
        print(f"   🗑️  Deleting AI: {name} (ID: {ai_id})")
        
        # Use DELETE method
        response = self.session.request(
            "DELETE",
            f"{self.base_url}/ai/delete",
            json={"ai_id": ai_id}
        )
        
        if response.status_code == 200:
            print(f"      ✅ Moved to recycle bin")
            return True
        
        # Fallback to POST
        response = self.session.post(
            f"{self.base_url}/ai/delete",
            data={"ai_id": ai_id}
        )
        
        if response.status_code == 200:
            print(f"      ✅ Moved to recycle bin (POST method)")
            return True
        
        print(f"      ❌ Failed to delete")
        return False
    
    def cleanup_all_mess(self):
        """Clean up all the mess - duplicates, unnamed folders, misplaced items"""
        print("\n🧹 CLEANING UP ALL MESS")
        print("="*60)
        
        folders, ais = self.get_all_folders_and_ais()
        
        # Folders to keep in root
        keep_root_folders = ["2.0", "3.0", "4.0", "6.0"]
        
        # Step 1: Delete all misplaced/duplicate folders
        print("\n📁 Cleaning up folders...")
        folders_to_delete = []
        
        for folder in folders:
            folder_name = folder.get("name", "")
            folder_id = folder.get("id")
            parent_id = folder.get("parent")
            
            # Delete conditions:
            # 1. Unnamed folders
            # 2. V6_Modular anywhere (we'll recreate properly)
            # 3. Category folders (core, combat, etc) in root
            # 4. Any duplicate V6 folders
            
            should_delete = False
            
            # Unnamed or invalid folders
            if not folder_name or folder_name in ["undefined", "null", ""]:
                should_delete = True
                folder_name = f"Unnamed_{folder_id}"
            
            # V6_Modular anywhere
            elif folder_name == "V6_Modular":
                should_delete = True
            
            # Category folders in root
            elif folder_name in ["core", "combat", "movement", "strategy", "ai", "utils", "V6"]:
                # Only delete if in root
                if parent_id == 0 or parent_id is None:
                    should_delete = True
            
            if should_delete:
                folders_to_delete.append((folder_id, folder_name))
        
        # Delete folders
        for folder_id, folder_name in folders_to_delete:
            self.delete_folder_properly(folder_id, folder_name)
            time.sleep(0.3)
        
        # Step 2: Delete all misplaced AIs in root
        print("\n📄 Cleaning up root AIs...")
        
        for ai in ais:
            ai_name = ai.get("name", "")
            ai_id = ai.get("id")
            folder_id = ai.get("folder")
            
            # Delete AIs in root except specific ones
            if folder_id == 0 or folder_id is None:
                # Keep only specific scripts
                if ai_id not in [444880]:  # Keep your main script ID
                    self.delete_ai_properly(ai_id, ai_name)
                    time.sleep(0.3)
        
        print("\n✅ Cleanup complete!")
    
    def create_folder_with_name(self, name: str, parent_id: int = 0) -> Optional[int]:
        """Create a folder using the correct endpoint"""
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
    
    def create_ai_with_name(self, name: str, code: str, folder_id: int) -> bool:
        """Create an AI with name using correct endpoint"""
        print(f"   📄 Creating AI: {name}")
        
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
                print(f"      Created with ID: {ai_id}")
                
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
                        print(f"      ✅ Code saved successfully")
                        return True
                
                print(f"      ❌ Failed to save code")
            else:
                print(f"      ❌ No AI ID returned")
        else:
            print(f"      ❌ Failed to create AI")
        
        return False
    
    def create_proper_v6_structure(self, v6_dir: Path):
        """Create the proper 6.0/V6 structure"""
        print("\n📤 CREATING PROPER V6 STRUCTURE")
        print("="*60)
        
        # Step 1: Create or find 6.0 folder
        folders, _ = self.get_all_folders_and_ais()
        folder_6_0_id = None
        
        for folder in folders:
            if folder.get("name") == "6.0" and (folder.get("parent") == 0 or folder.get("parent") is None):
                folder_6_0_id = folder.get("id")
                print(f"✅ Found existing 6.0 folder (ID: {folder_6_0_id})")
                break
        
        if not folder_6_0_id:
            print("\n📁 Creating 6.0 folder...")
            folder_6_0_id = self.create_folder_with_name("6.0", 0)
            
            if not folder_6_0_id:
                print("❌ Failed to create 6.0 folder")
                return False
        
        # Step 2: Create V6 folder inside 6.0
        print("\n📁 Creating V6 folder inside 6.0...")
        folder_v6_id = self.create_folder_with_name("V6", folder_6_0_id)
        
        if not folder_v6_id:
            print("❌ Failed to create V6 folder")
            return False
        
        # Step 3: Upload main V6 script
        print("\n📤 Uploading V6 scripts...")
        
        # Upload integrated version (most important)
        integrated_file = v6_dir / "V6_integrated.ls"
        if integrated_file.exists():
            with open(integrated_file, 'r', encoding='utf-8') as f:
                code = f.read()
            
            if self.create_ai_with_name("V6_Integrated", code, folder_v6_id):
                print("   ✅ V6 Integrated uploaded successfully!")
            time.sleep(1)
        
        # Upload main file
        main_file = v6_dir / "V6_main.ls"
        if main_file.exists():
            with open(main_file, 'r', encoding='utf-8') as f:
                code = f.read()
            
            if self.create_ai_with_name("V6_Main", code, folder_v6_id):
                print("   ✅ V6 Main uploaded successfully!")
            time.sleep(1)
        
        # Step 4: Create category folders for future use
        print("\n📁 Creating category folders for modules...")
        categories = ['core', 'combat', 'movement', 'strategy', 'ai', 'utils']
        
        for category in categories:
            self.create_folder_with_name(category, folder_v6_id)
            time.sleep(0.5)
        
        print("\n" + "="*60)
        print("✅ V6 STRUCTURE CREATED SUCCESSFULLY!")
        print("="*60)
        print("\n📁 Final structure:")
        print("   Root/")
        print("   ├── 2.0/")
        print("   ├── 3.0/")
        print("   ├── 4.0/")
        print("   └── 6.0/")
        print("       └── V6/")
        print("           ├── V6_Integrated.ls (Full working version)")
        print("           ├── V6_Main.ls (Modular main)")
        print("           ├── core/ (empty - for future modules)")
        print("           ├── combat/ (empty)")
        print("           ├── movement/ (empty)")
        print("           ├── strategy/ (empty)")
        print("           ├── ai/ (empty)")
        print("           └── utils/ (empty)")
        print("\n✨ Your V6 is ready to use in LeekWars!")
        print("   Navigate to: LeekWars > Editor > 6.0 > V6 > V6_Integrated")
        
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
    
    manager = LeekWarsCleanupAndFix()
    
    # Login
    if not manager.login("tanguy.pedrazzoli@gmail.com", "tanguy0211"):
        sys.exit(1)
    
    try:
        # Step 1: Clean up all the mess
        manager.cleanup_all_mess()
        
        # Wait a bit for cleanup to process
        print("\n⏳ Waiting for cleanup to process...")
        time.sleep(2)
        
        # Step 2: Create proper V6 structure
        manager.create_proper_v6_structure(v6_dir)
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        manager.disconnect()

if __name__ == '__main__':
    main()