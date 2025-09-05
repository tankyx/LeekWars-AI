#!/usr/bin/env python3
"""
LeekWars Root Cleanup Script
Removes everything from root folder except X.0 version folders
"""

import sys
import time
import requests
from typing import List, Dict

class LeekWarsRootCleaner:
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
    
    def get_all_folders_and_ais(self) -> tuple:
        """Get all folders and AIs from farmer data"""
        print("\n📋 Getting current root structure...")
        
        # Use the correct endpoint that returns both folders and AIs
        response = self.session.get(f"{self.base_url}/ai/get-farmer-ais")
        
        if response.status_code == 200:
            data = response.json()
            folders = data.get("folders", [])
            ais = data.get("ais", [])
            
            # Debug logging
            print(f"   Total folders: {len(folders)}, Total AIs: {len(ais)}")
            
            # Count root items
            root_folders = [f for f in folders if f.get("parent") in [0, None]]
            root_ais = [a for a in ais if a.get("folder") in [0, None]]
            
            print(f"   Found {len(root_folders)} root folders and {len(root_ais)} root scripts")
            
            # Show what's in root
            if root_folders:
                print("   Root folders found:")
                for f in root_folders:
                    print(f"     - {f.get('name', 'UNNAMED')} (ID: {f.get('id')})")
            
            if root_ais:
                print("   Root scripts found:")
                for a in root_ais[:5]:  # Show first 5
                    print(f"     - {a.get('name', 'UNNAMED')} (ID: {a.get('id')})")
                if len(root_ais) > 5:
                    print(f"     ... and {len(root_ais) - 5} more")
            
            return folders, ais
        
        print(f"   ❌ Failed to get data (Status: {response.status_code})")
        return [], []
    
    def delete_folder(self, folder_id: int, name: str) -> bool:
        """Delete a folder using DELETE method"""
        print(f"   🗑️  Deleting folder: {name} (ID: {folder_id})")
        
        # Try DELETE method first (correct way)
        try:
            response = self.session.request(
                "DELETE",
                f"{self.base_url}/ai-folder/delete",
                json={"folder_id": folder_id}
            )
            
            if response.status_code == 200:
                print(f"      ✅ Deleted successfully")
                return True
        except:
            pass
        
        # Fallback to POST
        response = self.session.post(
            f"{self.base_url}/ai-folder/delete",
            data={"folder_id": folder_id}
        )
        
        if response.status_code == 200:
            print(f"      ✅ Deleted successfully")
            return True
        
        print(f"      ❌ Failed (Status: {response.status_code})")
        return False
    
    def delete_ai(self, ai_id: int, name: str) -> bool:
        """Delete an AI using DELETE method"""
        print(f"   🗑️  Deleting script: {name} (ID: {ai_id})")
        
        # Try DELETE method first (correct way)
        try:
            response = self.session.request(
                "DELETE",
                f"{self.base_url}/ai/delete",
                json={"ai_id": ai_id}
            )
            
            if response.status_code == 200:
                print(f"      ✅ Moved to recycle bin")
                return True
        except:
            pass
        
        # Fallback to POST
        response = self.session.post(
            f"{self.base_url}/ai/delete",
            data={"ai_id": ai_id}
        )
        
        if response.status_code == 200:
            print(f"      ✅ Moved to recycle bin")
            return True
        
        print(f"      ❌ Failed")
        return False
    
    def is_version_folder(self, name: str) -> bool:
        """Check if folder name matches X.0 pattern"""
        import re
        # Match patterns like 2.0, 3.0, 4.0, 5.0, 6.0, etc.
        pattern = r'^\d+\.0$'
        return bool(re.match(pattern, name))
    
    def cleanup_root(self) -> Dict:
        """Clean up root folder - keep only X.0 version folders"""
        print("\n🧹 CLEANING ROOT FOLDER")
        print("="*60)
        print("📌 Will keep: X.0 folders (2.0, 3.0, 4.0, 5.0, 6.0, etc.)")
        print("🗑️  Will delete: Everything else in root")
        print("="*60)
        
        stats = {
            "folders_deleted": 0,
            "folders_kept": 0,
            "ais_deleted": 0,
            "errors": 0
        }
        
        folders, ais = self.get_all_folders_and_ais()
        
        # Process root folders
        print("\n📁 Processing root folders...")
        for folder in folders:
            folder_name = folder.get("name", "")
            folder_id = folder.get("id")
            parent_id = folder.get("parent")
            
            # Only process root folders
            if parent_id == 0 or parent_id is None:
                if self.is_version_folder(folder_name):
                    print(f"   ✅ Keeping: {folder_name} (version folder)")
                    stats["folders_kept"] += 1
                else:
                    # Delete non-version folders
                    if self.delete_folder(folder_id, folder_name or f"Unnamed_{folder_id}"):
                        stats["folders_deleted"] += 1
                    else:
                        stats["errors"] += 1
                    time.sleep(0.3)  # Rate limiting
        
        # Process root AIs
        print("\n📄 Processing root scripts...")
        for ai in ais:
            ai_name = ai.get("name", "")
            ai_id = ai.get("id")
            folder_id = ai.get("folder")
            
            # Only process root AIs
            if folder_id == 0 or folder_id is None:
                # Delete ALL scripts in root
                if self.delete_ai(ai_id, ai_name or f"Unnamed_{ai_id}"):
                    stats["ais_deleted"] += 1
                else:
                    stats["errors"] += 1
                time.sleep(0.3)  # Rate limiting
        
        # Print summary
        print("\n" + "="*60)
        print("📊 CLEANUP SUMMARY")
        print("="*60)
        print(f"📁 Folders kept: {stats['folders_kept']} (X.0 version folders)")
        print(f"🗑️  Folders deleted: {stats['folders_deleted']}")
        print(f"🗑️  Scripts deleted: {stats['ais_deleted']}")
        if stats["errors"] > 0:
            print(f"⚠️  Errors: {stats['errors']}")
        
        print("\n✅ Root cleanup complete!")
        print("   Your root folder now contains only X.0 version folders")
        
        return stats
    
    def verify_cleanup(self):
        """Verify the cleanup worked"""
        print("\n🔍 Verifying cleanup...")
        
        folders, ais = self.get_all_folders_and_ais()
        
        # Check root folders
        root_folders = [f for f in folders if f.get("parent") in [0, None]]
        root_ais = [a for a in ais if a.get("folder") in [0, None]]
        
        print("\n📁 Current root structure:")
        if root_folders:
            for folder in sorted(root_folders, key=lambda x: x.get("name", "")):
                name = folder.get("name", f"Unnamed_{folder.get('id')}")
                print(f"   └── {name}/")
        else:
            print("   (No folders in root)")
        
        if root_ais:
            print("\n⚠️  Scripts still in root:")
            for ai in root_ais:
                name = ai.get("name", f"Unnamed_{ai.get('id')}")
                print(f"   - {name}")
        
        # Check if only version folders remain
        non_version_folders = [
            f for f in root_folders 
            if not self.is_version_folder(f.get("name", ""))
        ]
        
        if non_version_folders:
            print(f"\n⚠️  Non-version folders still in root: {len(non_version_folders)}")
            for f in non_version_folders:
                print(f"   - {f.get('name', 'Unnamed')}")
        else:
            print("\n✨ Perfect! Only X.0 version folders remain in root")
    
    def disconnect(self):
        """Disconnect from LeekWars"""
        if self.token:
            self.session.post(f"{self.base_url}/farmer/disconnect/{self.token}")
            print("\n👋 Disconnected")

def main():
    print("="*60)
    print("LEEKWARS ROOT CLEANUP")
    print("="*60)
    print("This will remove everything from root except X.0 folders")
    print("(2.0, 3.0, 4.0, 5.0, 6.0, etc.)")
    print()
    
    cleaner = LeekWarsRootCleaner()
    
    # Login
    if not cleaner.login("tanguy.pedrazzoli@gmail.com", "tanguy0211"):
        sys.exit(1)
    
    try:
        # Perform cleanup
        stats = cleaner.cleanup_root()
        
        # Wait for changes to propagate
        if stats["folders_deleted"] > 0 or stats["ais_deleted"] > 0:
            print("\n⏳ Waiting for changes to propagate...")
            time.sleep(2)
        
        # Verify cleanup
        cleaner.verify_cleanup()
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        cleaner.disconnect()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())