#!/usr/bin/env python3
"""
Upload V6 Modular Structure to LeekWars
Uses the LeekWars API to create folders and upload all scripts
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, Optional
import getpass

class LeekWarsUploader:
    def __init__(self):
        self.base_url = "https://leekwars.com/api"
        self.session = requests.Session()
        self.token = None
        self.farmer_id = None
        self.folders_created = {}
        self.scripts_created = {}
        
    def login(self, username: str = None, password: str = None) -> bool:
        """Login to LeekWars and get authentication token"""
        
        if not username:
            username = input("LeekWars username/email: ")
        if not password:
            password = getpass.getpass("LeekWars password: ")
        
        # Use the working login endpoint from lw_update_script.py
        login_url = f"{self.base_url}/farmer/login-token"
        login_data = {
            "login": username,
            "password": password
        }
        
        response = self.session.post(login_url, data=login_data)
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                if "farmer" in data and "token" in data:
                    self.farmer = data["farmer"]
                    self.token = data["token"]
                    self.farmer_id = self.farmer.get("id")
                    
                    farmer_name = self.farmer.get("login", "Unknown")
                    
                    print(f"✅ Logged in successfully!")
                    print(f"   👤 Farmer: {farmer_name} (ID: {self.farmer_id})")
                    
                    return True
                
                elif "success" in data and not data["success"]:
                    error_msg = data.get("error", "Unknown error")
                    print(f"❌ Login failed: {error_msg}")
                    return False
                
                else:
                    print(f"❌ Unexpected response structure")
                    return False
                    
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
                return False
        else:
            print(f"❌ Login request failed: {response.status_code}")
            return False
    
    def create_folder(self, name: str, parent_id: Optional[int] = None) -> Optional[int]:
        """Create a folder in LeekWars"""
        
        payload = {
            "name": name
        }
        
        if parent_id:
            payload["folder_id"] = parent_id
        
        response = self.session.post(
            f"{self.base_url}/ai-folder/new",
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                folder = data.get('folder', {})
                folder_id = folder.get('id')
                print(f"   📁 Created folder: {name} (ID: {folder_id})")
                return folder_id
            else:
                print(f"   ❌ Failed to create folder {name}: {data.get('error')}")
        else:
            print(f"   ❌ Folder creation failed: {response.status_code}")
        
        return None
    
    def create_ai_script(self, name: str, code: str, folder_id: Optional[int] = None) -> Optional[int]:
        """Create an AI script in LeekWars"""
        
        # First check if AI with this name already exists and get it
        # Otherwise create new one
        
        # For now, let's just update using the save endpoint like in lw_update_script.py
        # The API seems to auto-create if it doesn't exist when using folder_id
        
        # Use the working save endpoint from lw_update_script.py
        save_data = {
            "code": code,
            "name": name  # Try including name in save
        }
        
        if folder_id:
            save_data["folder_id"] = folder_id
        
        # Try to save directly (this might auto-create)
        response = self.session.post(
            f"{self.base_url}/ai/save",
            data=save_data  # Use data, not json
        )
        
        if response.status_code == 200:
            try:
                result = response.json()
                
                # Check for success response (like in lw_update_script.py)
                if result.get("success") == True:
                    print(f"   📄 Created script: {name}")
                    return True  # We don't get the ID back directly
                
                # Check for alternate success format
                elif "result" in result and "modified" in result:
                    print(f"   📄 Created/updated script: {name}")
                    return True
                    
                else:
                    print(f"   ❌ Failed to save {name}: {result}")
                    
            except json.JSONDecodeError:
                print(f"   ❌ Invalid JSON response for {name}")
        else:
            print(f"   ❌ Save failed for {name}: {response.status_code}")
        
        return None
    
    def upload_v6_structure(self, v6_dir: Path):
        """Upload the complete V6 structure to LeekWars"""
        
        print("\n" + "="*60)
        print("📤 UPLOADING V6 TO LEEKWARS")
        print("="*60)
        
        # Step 1: Create main V6 folder
        print("\n📁 Creating folder structure...")
        main_folder_id = self.create_folder("V6_Modular")
        
        if not main_folder_id:
            print("❌ Failed to create main folder")
            return False
        
        self.folders_created["V6_Modular"] = main_folder_id
        
        # Step 2: Create category folders
        categories = ['core', 'combat', 'movement', 'strategy', 'ai', 'utils']
        
        for category in categories:
            category_path = v6_dir / category
            if category_path.exists():
                folder_id = self.create_folder(category, main_folder_id)
                if folder_id:
                    self.folders_created[category] = folder_id
                else:
                    print(f"⚠️  Warning: Could not create folder {category}")
        
        # Step 3: Upload module files
        print("\n📤 Uploading module files...")
        
        module_files = list(v6_dir.rglob("*.ls"))
        module_files.sort()
        
        uploaded = 0
        failed = 0
        
        for module_file in module_files:
            rel_path = module_file.relative_to(v6_dir)
            
            # Skip the main file for now
            if module_file.name == "V6_main.ls":
                continue
            
            # Determine parent folder
            if rel_path.parent.name in self.folders_created:
                parent_folder = self.folders_created[rel_path.parent.name]
            else:
                parent_folder = main_folder_id
            
            # Read the module code
            with open(module_file, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Create the script
            script_name = module_file.stem  # Remove .ls extension
            script_id = self.create_ai_script(script_name, code, parent_folder)
            
            if script_id:
                uploaded += 1
                self.scripts_created[str(rel_path)] = script_id
            else:
                failed += 1
            
            # Rate limiting
            time.sleep(0.5)  # Be nice to the API
        
        # Step 4: Upload main file
        print("\n📤 Uploading main file...")
        main_file = v6_dir / "V6_main.ls"
        
        if main_file.exists():
            with open(main_file, 'r', encoding='utf-8') as f:
                main_code = f.read()
            
            main_id = self.create_ai_script("V6_Main", main_code, main_folder_id)
            
            if main_id:
                uploaded += 1
                self.scripts_created["V6_main.ls"] = main_id
                print("✅ Main file uploaded successfully")
            else:
                failed += 1
                print("❌ Failed to upload main file")
        
        # Step 5: Create integrated version (optional)
        print("\n📤 Creating integrated version...")
        integrated_file = v6_dir / "V6_integrated.ls"
        
        if integrated_file.exists():
            with open(integrated_file, 'r', encoding='utf-8') as f:
                integrated_code = f.read()
            
            integrated_id = self.create_ai_script("V6_Integrated", integrated_code, main_folder_id)
            
            if integrated_id:
                uploaded += 1
                print("✅ Integrated version uploaded")
        
        # Summary
        print("\n" + "="*60)
        print("📊 UPLOAD SUMMARY")
        print("="*60)
        print(f"✅ Successfully uploaded: {uploaded} files")
        if failed > 0:
            print(f"❌ Failed: {failed} files")
        print(f"📁 Folders created: {len(self.folders_created)}")
        print(f"📄 Scripts created: {len(self.scripts_created)}")
        
        # Save upload manifest
        manifest = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "folders": self.folders_created,
            "scripts": self.scripts_created,
            "stats": {
                "uploaded": uploaded,
                "failed": failed
            }
        }
        
        manifest_file = v6_dir / "upload_manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"\n📝 Upload manifest saved to: {manifest_file}")
        
        if failed == 0:
            print("\n✅ V6 UPLOAD COMPLETE!")
            print("   Your modular V6 structure is now available in LeekWars!")
            print(f"   Main script: V6_Main (ID: {self.scripts_created.get('V6_main.ls', 'N/A')})")
            return True
        else:
            print("\n⚠️  Upload completed with some failures")
            return False
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            response = self.session.get(f"{self.base_url}/garden/get")
            return response.status_code == 200
        except:
            return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload V6 modules to LeekWars')
    parser.add_argument('--dir', default='/home/ubuntu/V6_modules',
                      help='V6 modules directory')
    parser.add_argument('--username', help='LeekWars username/email')
    parser.add_argument('--password', help='LeekWars password')
    parser.add_argument('--test', action='store_true',
                      help='Test connection only')
    
    args = parser.parse_args()
    
    v6_dir = Path(args.dir)
    if not v6_dir.exists():
        print(f"Error: {v6_dir} does not exist")
        print("Run the modularization script first:")
        print("  python3 /home/ubuntu/scripts/tools/lw_create_v6_structure.py")
        sys.exit(1)
    
    # Create uploader
    uploader = LeekWarsUploader()
    
    # Test connection
    print("🔍 Testing connection to LeekWars API...")
    if uploader.test_connection():
        print("✅ Connection successful")
    else:
        print("❌ Cannot connect to LeekWars API")
        print("   Please check your internet connection")
        sys.exit(1)
    
    if args.test:
        print("Test mode - no upload will be performed")
        sys.exit(0)
    
    # Login
    print("\n🔐 Logging in to LeekWars...")
    if not uploader.login(args.username, args.password):
        print("❌ Login failed. Please check your credentials.")
        sys.exit(1)
    
    # Upload V6 structure
    success = uploader.upload_v6_structure(v6_dir)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()