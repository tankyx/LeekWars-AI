#!/usr/bin/env python3
"""
Fix V6 completely - Delete all 6.0 folders and re-upload properly
"""

import sys
import time
import requests
from pathlib import Path
from typing import Optional

class V6CompleteFixManager:
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
    
    def get_all_folders_and_ais(self):
        """Get all folders and AIs"""
        response = self.session.get(f"{self.base_url}/ai/get-farmer-ais")
        
        if response.status_code == 200:
            data = response.json()
            return data.get("folders", []), data.get("ais", [])
        
        return [], []
    
    def delete_folder(self, folder_id: int, name: str) -> bool:
        """Delete a folder and all its contents"""
        print(f"   🗑️  Deleting folder: {name} (ID: {folder_id})")
        
        # Try DELETE method first
        try:
            response = self.session.request(
                "DELETE",
                f"{self.base_url}/ai-folder/delete",
                json={"folder_id": folder_id}
            )
            
            if response.status_code == 200:
                print(f"      ✅ Deleted")
                return True
        except:
            pass
        
        # Fallback to POST
        response = self.session.post(
            f"{self.base_url}/ai-folder/delete",
            data={"folder_id": folder_id}
        )
        
        if response.status_code == 200:
            print(f"      ✅ Deleted")
            return True
        
        print(f"      ❌ Failed")
        return False
    
    def step1_delete_all_6_0_folders(self):
        """Delete all 6.0 folders and their contents"""
        print("\n🧹 STEP 1: DELETING ALL 6.0 FOLDERS")
        print("="*60)
        
        folders, ais = self.get_all_folders_and_ais()
        
        # Find all 6.0 folders (there are duplicates)
        folders_6_0 = []
        for folder in folders:
            if folder.get("name") == "6.0" and folder.get("parent") in [0, None]:
                folders_6_0.append(folder)
        
        print(f"Found {len(folders_6_0)} '6.0' folders to delete")
        
        # First, find all child folders and scripts
        for folder_6_0 in folders_6_0:
            folder_id = folder_6_0.get("id")
            print(f"\nProcessing 6.0 folder (ID: {folder_id})...")
            
            # Find all child folders (like V6)
            child_folders = []
            for f in folders:
                if f.get("parent") == folder_id:
                    child_folders.append(f)
                    # Find grandchildren
                    for gf in folders:
                        if gf.get("parent") == f.get("id"):
                            child_folders.append(gf)
            
            # Delete child folders first (in reverse order for nested folders)
            for child in reversed(child_folders):
                self.delete_folder(child.get("id"), child.get("name", "unnamed"))
                time.sleep(0.3)
            
            # Delete the 6.0 folder itself
            self.delete_folder(folder_id, "6.0")
            time.sleep(0.3)
        
        print("\n✅ All 6.0 folders deleted")
    
    def create_folder(self, name: str, parent_id: int = 0) -> Optional[int]:
        """Create a folder"""
        print(f"   📁 Creating folder: {name}")
        
        response = self.session.post(
            f"{self.base_url}/ai-folder/new-name",
            data={"folder_id": parent_id, "name": name}
        )
        
        if response.status_code == 200:
            data = response.json()
            folder_id = data.get("id")
            if folder_id:
                print(f"      ✅ Created (ID: {folder_id})")
                return folder_id
        
        print(f"      ❌ Failed")
        return None
    
    def create_ai_script(self, name: str, code: str, folder_id: int) -> Optional[int]:
        """Create an AI script"""
        print(f"   📄 Creating: {name}")
        
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
                    print(f"      ✅ Uploaded (ID: {ai_id})")
                    return ai_id
        
        print(f"      ❌ Failed")
        return None
    
    def step2_upload_complete_v6(self, v6_dir: Path):
        """Upload complete V6 structure with all modules"""
        print("\n📤 STEP 2: UPLOADING COMPLETE V6 STRUCTURE")
        print("="*60)
        
        # Create 6.0 folder
        print("\n1️⃣ Creating 6.0 folder...")
        folder_6_0 = self.create_folder("6.0", 0)
        if not folder_6_0:
            print("❌ Failed to create 6.0 folder")
            return False
        
        # Create V6 folder inside 6.0
        print("\n2️⃣ Creating V6 folder...")
        folder_v6 = self.create_folder("V6", folder_6_0)
        if not folder_v6:
            print("❌ Failed to create V6 folder")
            return False
        
        # Upload main V6 file
        print("\n3️⃣ Uploading main V6 file...")
        main_file = v6_dir / "V6_main.ls"
        if main_file.exists():
            with open(main_file, 'r', encoding='utf-8') as f:
                code = f.read()
            self.create_ai_script("V6_main", code, folder_v6)
            time.sleep(0.5)
        
        # Upload integrated version (optional but useful)
        integrated_file = v6_dir / "V6_integrated.ls"
        if integrated_file.exists():
            with open(integrated_file, 'r', encoding='utf-8') as f:
                code = f.read()
            self.create_ai_script("V6_integrated", code, folder_v6)
            time.sleep(0.5)
        
        # Create category folders and upload modules
        print("\n4️⃣ Creating categories and uploading modules...")
        categories = ['core', 'combat', 'movement', 'strategy', 'ai', 'utils']
        
        stats = {"total": 0, "success": 0, "failed": 0}
        
        for category in categories:
            print(f"\n📦 Processing {category}/...")
            
            # Create category folder
            cat_folder = self.create_folder(category, folder_v6)
            if not cat_folder:
                print(f"   ⚠️  Failed to create {category} folder")
                continue
            
            # Upload all modules in this category
            category_path = v6_dir / category
            if not category_path.exists():
                print(f"   ⚠️  No local files for {category}")
                continue
            
            module_files = sorted(category_path.glob("*.ls"))
            print(f"   Found {len(module_files)} modules")
            
            for module_file in module_files:
                module_name = module_file.stem
                stats["total"] += 1
                
                with open(module_file, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # Upload the module
                ai_id = self.create_ai_script(module_name, code, cat_folder)
                
                if ai_id:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
                
                # Rate limiting
                time.sleep(0.4)
        
        # Summary
        print("\n" + "="*60)
        print("📊 UPLOAD COMPLETE")
        print("="*60)
        print(f"✅ Successfully uploaded: {stats['success']}/{stats['total']} modules")
        if stats['failed'] > 0:
            print(f"❌ Failed: {stats['failed']} modules")
        
        print("\n📁 Final V6 structure:")
        print("   6.0/")
        print("   └── V6/")
        print("       ├── V6_main.ls")
        print("       ├── V6_integrated.ls")
        for category in categories:
            category_path = v6_dir / category
            if category_path.exists():
                modules = list(category_path.glob("*.ls"))
                if modules:
                    print(f"       ├── {category}/ ({len(modules)} modules)")
        
        print("\n✨ V6 MODULAR STRUCTURE IS COMPLETE!")
        return stats['success'] > 0
    
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
    
    print("="*60)
    print("V6 COMPLETE FIX - DELETE AND RE-UPLOAD")
    print("="*60)
    print("This will:")
    print("1. Delete ALL 6.0 folders and their contents")
    print("2. Re-upload complete V6 modular structure")
    print()
    
    manager = V6CompleteFixManager()
    
    # Login
    if not manager.login("tanguy.pedrazzoli@gmail.com", "tanguy0211"):
        sys.exit(1)
    
    try:
        # Step 1: Delete all 6.0 folders
        manager.step1_delete_all_6_0_folders()
        
        # Wait for deletion to process
        print("\n⏳ Waiting for deletions to process...")
        time.sleep(3)
        
        # Step 2: Upload complete V6
        success = manager.step2_upload_complete_v6(v6_dir)
        
        if not success:
            print("\n⚠️  Some issues occurred")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        manager.disconnect()

if __name__ == '__main__':
    main()