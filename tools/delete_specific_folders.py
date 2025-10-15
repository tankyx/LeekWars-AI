#!/usr/bin/env python3
"""
Delete specific version folders (6.0 and 7.0)
"""

import requests
import sys
import time
from config_loader import load_credentials

class SpecificFolderDeleter:
    def __init__(self):
        self.base_url = "https://leekwars.com/api"
        self.session = requests.Session()
        self.token = None
        
    def login(self):
        """Login to LeekWars"""
        print("🔐 Logging in...")

        email, password = load_credentials()
        data = {"login": email, "password": password}

        response = self.session.post(
            f"{self.base_url}/farmer/login-token",
            data=data
        )
        
        if response.status_code == 200:
            data = response.json()
            if "farmer" in data and "token" in data:
                self.token = data["token"]
                farmer = data["farmer"]
                print(f"✅ Logged in as: {farmer.get('login')}")
                return True
        
        print("❌ Login failed")
        return False
    
    def get_folders(self):
        """Get all folders"""
        response = self.session.get(f"{self.base_url}/ai/get-farmer-ais")
        if response.status_code == 200:
            data = response.json()
            return data.get("folders", [])
        return []
    
    def delete_folder_and_contents(self, folder_id, folder_name):
        """Delete a folder and all its contents"""
        print(f"🗑️  Deleting folder: {folder_name} (ID: {folder_id})")
        
        # Get current structure to find contents
        folders = self.get_folders()
        response = self.session.get(f"{self.base_url}/ai/get-farmer-ais")
        if response.status_code == 200:
            data = response.json()
            ais = data.get("ais", [])
            
            # Find subfolders
            subfolders = [f for f in folders if f.get("parent") == folder_id]
            # Find AIs in this folder
            folder_ais = [a for a in ais if a.get("folder") == folder_id]
            
            # Delete AIs first
            for ai in folder_ais:
                ai_id = ai.get("id")
                ai_name = ai.get("name", "Unnamed")
                print(f"   🗑️  Deleting AI: {ai_name} (ID: {ai_id})")
                
                delete_response = self.session.post(f"{self.base_url}/ai/delete", data={"ai_id": ai_id})
                if delete_response.status_code == 200:
                    print(f"      ✅ AI deleted")
                else:
                    print(f"      ❌ Failed to delete AI")
                time.sleep(0.2)
            
            # Delete subfolders recursively
            for subfolder in subfolders:
                subfolder_id = subfolder.get("id")
                subfolder_name = subfolder.get("name", "Unnamed")
                self.delete_folder_and_contents(subfolder_id, subfolder_name)
                time.sleep(0.2)
        
        # Delete the folder itself
        response = self.session.post(f"{self.base_url}/ai-folder/delete", data={"folder_id": folder_id})
        
        if response.status_code == 200:
            print(f"   ✅ Folder {folder_name} deleted successfully")
            return True
        else:
            print(f"   ❌ Failed to delete folder {folder_name} (Status: {response.status_code})")
            return False
    
    def delete_target_folders(self):
        """Delete 6.0 and 7.0 folders"""
        print("\n🗑️ DELETING 6.0 AND 7.0 FOLDERS")
        print("="*40)
        
        folders = self.get_folders()
        
        # Find target folders
        target_folders = []
        for folder in folders:
            name = folder.get("name", "")
            parent = folder.get("parent")
            
            # Only root folders with names 6.0 or 7.0
            if name in ["6.0", "7.0"] and parent in [0, None]:
                target_folders.append(folder)
        
        print(f"Found {len(target_folders)} target folders:")
        for f in target_folders:
            print(f"  - {f.get('name')} (ID: {f.get('id')})")
        
        if len(target_folders) == 0:
            print("✅ No target folders found!")
            return 0
        
        deleted_count = 0
        for folder in target_folders:
            folder_id = folder.get("id")
            folder_name = folder.get("name", "Unnamed")
            
            if self.delete_folder_and_contents(folder_id, folder_name):
                deleted_count += 1
            
            time.sleep(0.5)
        
        return deleted_count
    
    def verify_deletion(self):
        """Verify the folders are gone"""
        print("\n🔍 Verifying deletion...")
        
        folders = self.get_folders()
        remaining_targets = [f for f in folders if f.get("name") in ["6.0", "7.0"] and f.get("parent") in [0, None]]
        
        if len(remaining_targets) == 0:
            print("✅ Perfect! 6.0 and 7.0 folders successfully removed")
            
            # Show remaining root folders
            root_folders = [f for f in folders if f.get("parent") in [0, None]]
            print(f"\nRemaining root folders ({len(root_folders)}):")
            for f in sorted(root_folders, key=lambda x: x.get("name", "")):
                print(f"  - {f.get('name', 'Unnamed')}")
                
            return True
        else:
            print(f"⚠️  {len(remaining_targets)} target folders still remain:")
            for f in remaining_targets:
                print(f"   - {f.get('name')} (ID: {f.get('id')})")
            return False
    
    def disconnect(self):
        """Disconnect from LeekWars"""
        if self.token:
            self.session.post(f"{self.base_url}/farmer/disconnect/{self.token}")
            print("\n👋 Disconnected")

def main():
    print("="*50)
    print("DELETE 6.0 AND 7.0 FOLDERS")
    print("="*50)
    print("This will delete 6.0 and 7.0 folders and all their contents!")
    print()
    
    deleter = SpecificFolderDeleter()
    
    if not deleter.login():
        sys.exit(1)
    
    try:
        deleted_count = deleter.delete_target_folders()
        
        print(f"\n⏳ Waiting for changes to propagate...")
        time.sleep(2)
        
        deleter.verify_deletion()
        
        print(f"\n✅ Deletion complete! Removed {deleted_count} folders")
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    finally:
        deleter.disconnect()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())