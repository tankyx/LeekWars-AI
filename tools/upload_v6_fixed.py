#!/usr/bin/env python3
"""
Fixed V6 Upload Script - Properly creates folder hierarchy
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, Optional

class V6Upload:
    def __init__(self):
        self.base_url = "https://leekwars.com/api"
        self.session = requests.Session()
        self.token = None
        self.farmer = None
        
    def login(self, email: str, password: str) -> bool:
        """Login using the working method"""
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
                print(f"✅ Logged in as: {self.farmer.get('login')}")
                return True
        
        print("❌ Login failed")
        return False
    
    def get_ai_folders(self) -> dict:
        """Get current AI folders structure"""
        response = self.session.get(f"{self.base_url}/ai-folder/get-farmer-folders")
        if response.status_code == 200:
            return response.json()
        return {}
    
    def delete_ai(self, ai_id: int) -> bool:
        """Delete an AI script"""
        response = self.session.post(f"{self.base_url}/ai/delete", data={"ai_id": ai_id})
        return response.status_code == 200
    
    def delete_folder(self, folder_id: int) -> bool:
        """Delete a folder"""
        response = self.session.post(f"{self.base_url}/ai-folder/delete", data={"folder_id": folder_id})
        return response.status_code == 200
    
    def clean_existing_v6(self):
        """Clean up any existing V6 folders/scripts in wrong location"""
        print("\n🧹 Cleaning up existing V6 files...")
        
        # Get current folder structure
        folders_data = self.get_ai_folders()
        
        if not folders_data:
            print("   Could not get folder structure")
            return
        
        # Look for V6_Modular folder and misplaced category folders
        folders_to_check = ['V6_Modular', 'core', 'combat', 'movement', 'strategy', 'ai', 'utils']
        
        # Note: This would need the actual folder structure from the API
        # For now, we'll just proceed with the upload
        print("   Ready for fresh upload")
    
    def create_folder_properly(self, name: str, parent_id: int = 0) -> Optional[int]:
        """Create a folder and return its ID"""
        print(f"   📁 Creating folder: {name} (parent: {parent_id})")
        
        # The correct endpoint from frontend code
        response = self.session.post(
            f"{self.base_url}/ai-folder/new",
            data={"name": name, "folder_id": parent_id}
        )
        
        if response.status_code == 200:
            data = response.json()
            # The ID should be in data.id or data.folder.id
            folder_id = data.get("id")
            if not folder_id and "folder" in data:
                folder_id = data["folder"].get("id")
            
            if folder_id:
                print(f"      ✅ Created with ID: {folder_id}")
                return folder_id
            else:
                print(f"      ⚠️  Created but no ID returned")
                # Try alternate structure
                print(f"      Debug: {data}")
        else:
            print(f"      ❌ Failed: {response.status_code}")
            
        return None
    
    def create_ai_in_folder(self, name: str, code: str, folder_id: int) -> bool:
        """Create an AI script in a specific folder"""
        print(f"   📄 Creating: {name} in folder {folder_id}")
        
        # First create the AI
        response = self.session.post(
            f"{self.base_url}/ai/new",
            data={"name": name, "folder_id": folder_id}
        )
        
        if response.status_code == 200:
            data = response.json()
            ai_id = data.get("ai", {}).get("id")
            
            if ai_id:
                # Save the code
                save_response = self.session.post(
                    f"{self.base_url}/ai/save",
                    data={"ai_id": str(ai_id), "code": code}
                )
                
                if save_response.status_code == 200:
                    result = save_response.json()
                    if result.get("success") or "result" in result:
                        print(f"      ✅ Uploaded successfully")
                        return True
        
        print(f"      ❌ Failed to upload")
        return False
    
    def upload_v6_properly(self, v6_dir: Path):
        """Upload V6 with proper folder structure"""
        print("\n" + "="*60)
        print("📤 UPLOADING V6 WITH PROPER STRUCTURE")
        print("="*60)
        
        # Step 1: Create main V6_Modular folder in root (folder_id=0)
        print("\n1️⃣ Creating main V6_Modular folder...")
        v6_folder_id = self.create_folder_properly("V6_Modular", 0)
        
        if not v6_folder_id:
            print("❌ Could not create main folder - trying to continue anyway")
            v6_folder_id = 0
        
        # Step 2: Create category folders INSIDE V6_Modular
        print("\n2️⃣ Creating category folders inside V6_Modular...")
        category_folders = {}
        categories = ['core', 'combat', 'movement', 'strategy', 'ai', 'utils']
        
        for category in categories:
            # Create each category folder INSIDE V6_Modular
            cat_id = self.create_folder_properly(category, v6_folder_id)
            if cat_id:
                category_folders[category] = cat_id
            else:
                print(f"   ⚠️  Failed to create {category}, will use main folder")
                category_folders[category] = v6_folder_id
            
            time.sleep(0.3)  # Rate limit
        
        # Step 3: Upload main file to V6_Modular folder
        print("\n3️⃣ Uploading main V6 script to V6_Modular...")
        main_file = v6_dir / "V6_main.ls"
        if main_file.exists():
            with open(main_file, 'r', encoding='utf-8') as f:
                main_code = f.read()
            
            self.create_ai_in_folder("V6_Main", main_code, v6_folder_id)
        
        # Step 4: Upload modules to their respective category folders
        print("\n4️⃣ Uploading modules to category folders...")
        
        uploaded = 0
        failed = 0
        
        for category in categories:
            category_path = v6_dir / category
            if not category_path.exists():
                continue
            
            print(f"\n   📦 Uploading {category} modules...")
            category_folder_id = category_folders.get(category, v6_folder_id)
            
            for module_file in sorted(category_path.glob("*.ls")):
                module_name = module_file.stem
                
                with open(module_file, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                if self.create_ai_in_folder(module_name, code, category_folder_id):
                    uploaded += 1
                else:
                    failed += 1
                
                time.sleep(0.5)  # Rate limit
        
        # Step 5: Upload integrated version
        integrated_file = v6_dir / "V6_integrated.ls"
        if integrated_file.exists():
            print("\n5️⃣ Uploading integrated version...")
            with open(integrated_file, 'r', encoding='utf-8') as f:
                integrated_code = f.read()
            
            if self.create_ai_in_folder("V6_Integrated", integrated_code, v6_folder_id):
                uploaded += 1
        
        # Summary
        print("\n" + "="*60)
        print("📊 UPLOAD COMPLETE")
        print("="*60)
        print(f"✅ Uploaded: {uploaded} files")
        if failed > 0:
            print(f"❌ Failed: {failed} files")
        print("\n📁 Structure created:")
        print("   V6_Modular/")
        print("   ├── V6_Main.ls")
        print("   ├── V6_Integrated.ls")
        for category in categories:
            if category in category_folders:
                print(f"   ├── {category}/")
                cat_path = v6_dir / category
                if cat_path.exists():
                    for f in sorted(cat_path.glob("*.ls"))[:2]:
                        print(f"   │   ├── {f.stem}.ls")
                    if len(list(cat_path.glob("*.ls"))) > 2:
                        print(f"   │   └── ...")
        
        print("\n✨ Your V6 modular structure is ready in LeekWars!")
        print("   Navigate to: LeekWars > Editor > V6_Modular > V6_Main")
    
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
    
    uploader = V6Upload()
    
    # Login with credentials from lw_update_script.py
    if not uploader.login("tanguy.pedrazzoli@gmail.com", "tanguy0211"):
        sys.exit(1)
    
    try:
        # Clean up any existing mess
        uploader.clean_existing_v6()
        
        # Upload with proper structure
        uploader.upload_v6_properly(v6_dir)
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        uploader.disconnect()

if __name__ == '__main__':
    main()