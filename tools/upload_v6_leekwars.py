#!/usr/bin/env python3
"""
Upload V6 Modular Structure to LeekWars
Uses the correct LeekWars API endpoints to create folders and upload scripts
Based on the working authentication from lw_update_script.py
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, Optional
import getpass

class V6LeekWarsUploader:
    def __init__(self):
        self.base_url = "https://leekwars.com/api"
        self.session = requests.Session()
        self.token = None
        self.farmer = None
        self.folders_map = {}  # Map folder paths to IDs
        self.scripts_map = {}  # Map script paths to IDs
        
    def login(self, email: str = None, password: str = None) -> bool:
        """Login to LeekWars using the working method from lw_update_script.py"""
        print("🔐 Logging in to LeekWars...")
        
        if not email:
            email = input("LeekWars email: ")
        if not password:
            password = getpass.getpass("LeekWars password: ")
        
        login_url = f"{self.base_url}/farmer/login-token"
        login_data = {
            "login": email,
            "password": password
        }
        
        try:
            response = self.session.post(login_url, data=login_data)
            
            if response.status_code == 200:
                data = response.json()
                
                if "farmer" in data and "token" in data:
                    self.farmer = data["farmer"]
                    self.token = data["token"]
                    
                    farmer_name = self.farmer.get("login", "Unknown")
                    farmer_id = self.farmer.get("id", "Unknown")
                    
                    print(f"✅ Connected successfully!")
                    print(f"   👤 Farmer: {farmer_name} (ID: {farmer_id})")
                    
                    return True
                
                elif "success" in data and not data["success"]:
                    error_msg = data.get("error", "Unknown error")
                    print(f"❌ Login failed: {error_msg}")
                    return False
                    
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return False
    
    def get_root_folder_id(self) -> Optional[int]:
        """Get the root AI folder ID for the current farmer"""
        # The root folder ID is typically 0 or we can get it from farmer data
        # For now, we'll use 0 as the root
        return 0
    
    def create_folder(self, name: str, parent_folder_id: int = 0) -> Optional[int]:
        """Create a folder using the correct endpoint"""
        print(f"   📁 Creating folder: {name}")
        
        # Use the endpoint found in the frontend: ai-folder/new-name
        url = f"{self.base_url}/ai-folder/new-name"
        
        payload = {
            "folder_id": parent_folder_id,
            "name": name
        }
        
        try:
            response = self.session.post(url, data=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                if "success" in data and data["success"]:
                    folder_id = data.get("id", None)
                    if folder_id:
                        print(f"      ✅ Created with ID: {folder_id}")
                        return folder_id
                    else:
                        # Sometimes the ID is in a different field
                        if "folder" in data:
                            folder_id = data["folder"].get("id")
                            print(f"      ✅ Created with ID: {folder_id}")
                            return folder_id
                else:
                    error = data.get("error", "Unknown error")
                    print(f"      ❌ Failed: {error}")
                    print(f"      Debug - Full response: {data}")
            else:
                print(f"      ❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
        
        return None
    
    def create_ai_script(self, name: str, code: str, folder_id: int = 0) -> Optional[int]:
        """Create an AI script using the correct endpoint"""
        print(f"   📄 Creating script: {name}")
        
        # First create the AI using ai/new-name endpoint
        url = f"{self.base_url}/ai/new-name"
        
        payload = {
            "folder_id": folder_id,
            "version": 4,  # LeekScript version 4
            "name": name
        }
        
        try:
            response = self.session.post(url, data=payload)
            
            if response.status_code == 200:
                data = response.json()
                
                if "success" in data and data["success"]:
                    ai_id = data.get("id", None)
                    if not ai_id and "ai" in data:
                        ai_id = data["ai"].get("id")
                    
                    if ai_id:
                        print(f"      ✅ Created AI with ID: {ai_id}")
                        
                        # Now save the code
                        return self.save_ai_code(ai_id, code, name)
                    else:
                        print(f"      ❌ No AI ID returned")
                else:
                    error = data.get("error", "Unknown error")
                    print(f"      ❌ Failed to create AI: {error}")
            else:
                print(f"      ❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"      ❌ Error creating AI: {e}")
        
        return None
    
    def save_ai_code(self, ai_id: int, code: str, name: str) -> Optional[int]:
        """Save code to an AI script"""
        # Use the save endpoint like in lw_update_script.py
        url = f"{self.base_url}/ai/save"
        
        data = {
            "ai_id": str(ai_id),
            "code": code
        }
        
        try:
            response = self.session.post(url, data=data)
            
            if response.status_code == 200:
                result = response.json()
                
                # Check for success (same logic as lw_update_script.py)
                if result.get("success") == True:
                    print(f"      ✅ Code saved successfully")
                    return ai_id
                
                elif "result" in result and "modified" in result:
                    print(f"      ✅ Code saved and compiled")
                    
                    # Check compilation results
                    if isinstance(result["result"], dict):
                        for script_id, compile_info in result["result"].items():
                            if compile_info is None:
                                print(f"      ⚠️  Compilation failed - script has errors")
                            elif isinstance(compile_info, list):
                                if len(compile_info) > 0:
                                    print(f"      ✓ Compiled with {len(compile_info)} include(s)")
                    
                    return ai_id
                else:
                    print(f"      ❌ Save failed: {result}")
            else:
                print(f"      ❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"      ❌ Error saving code: {e}")
        
        return None
    
    def upload_v6_structure(self, v6_dir: Path):
        """Upload the complete V6 structure to LeekWars"""
        
        print("\n" + "="*60)
        print("📤 UPLOADING V6 STRUCTURE TO LEEKWARS")
        print("="*60)
        
        # Step 1: Create main V6 folder
        print("\n📁 Creating main V6 folder...")
        root_folder_id = self.get_root_folder_id()
        v6_folder_id = self.create_folder("V6_Modular", root_folder_id)
        
        if not v6_folder_id:
            print("❌ Failed to create main V6 folder")
            # Try to continue anyway with root folder
            v6_folder_id = root_folder_id
        
        self.folders_map["V6_Modular"] = v6_folder_id
        
        # Step 2: Create category subfolders
        print("\n📁 Creating category folders...")
        categories = ['core', 'combat', 'movement', 'strategy', 'ai', 'utils']
        
        for category in categories:
            category_path = v6_dir / category
            if category_path.exists():
                folder_id = self.create_folder(category, v6_folder_id)
                if folder_id:
                    self.folders_map[category] = folder_id
                else:
                    print(f"   ⚠️  Could not create {category} folder, using main folder")
                    self.folders_map[category] = v6_folder_id
                
                # Small delay to avoid rate limiting
                time.sleep(0.3)
        
        # Step 3: Upload module files
        print("\n📤 Uploading module scripts...")
        
        module_files = []
        for category in categories:
            category_path = v6_dir / category
            if category_path.exists():
                module_files.extend(category_path.glob("*.ls"))
        
        uploaded_count = 0
        failed_count = 0
        
        for module_file in sorted(module_files):
            # Get parent folder ID
            parent_name = module_file.parent.name
            parent_folder_id = self.folders_map.get(parent_name, v6_folder_id)
            
            # Read module code
            with open(module_file, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Create script name (without .ls extension)
            script_name = module_file.stem
            
            # Create and upload the script
            ai_id = self.create_ai_script(script_name, code, parent_folder_id)
            
            if ai_id:
                uploaded_count += 1
                self.scripts_map[str(module_file.relative_to(v6_dir))] = ai_id
            else:
                failed_count += 1
            
            # Rate limiting
            time.sleep(0.5)
        
        # Step 4: Upload main file
        print("\n📤 Uploading main V6 script...")
        main_file = v6_dir / "V6_main.ls"
        
        if main_file.exists():
            with open(main_file, 'r', encoding='utf-8') as f:
                main_code = f.read()
            
            main_id = self.create_ai_script("V6_Main", main_code, v6_folder_id)
            
            if main_id:
                uploaded_count += 1
                self.scripts_map["V6_main.ls"] = main_id
            else:
                failed_count += 1
        
        # Step 5: Optionally upload integrated version
        integrated_file = v6_dir / "V6_integrated.ls"
        if integrated_file.exists():
            print("\n📤 Uploading integrated version...")
            with open(integrated_file, 'r', encoding='utf-8') as f:
                integrated_code = f.read()
            
            integrated_id = self.create_ai_script("V6_Integrated_Full", integrated_code, v6_folder_id)
            
            if integrated_id:
                uploaded_count += 1
                print("   ✅ Integrated version uploaded")
        
        # Summary
        print("\n" + "="*60)
        print("📊 UPLOAD SUMMARY")
        print("="*60)
        print(f"✅ Successfully uploaded: {uploaded_count} scripts")
        if failed_count > 0:
            print(f"❌ Failed uploads: {failed_count}")
        print(f"📁 Folders created: {len(self.folders_map)}")
        
        # Save manifest
        manifest = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "folders": self.folders_map,
            "scripts": self.scripts_map,
            "stats": {
                "uploaded": uploaded_count,
                "failed": failed_count
            }
        }
        
        manifest_file = v6_dir / "upload_manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"\n📝 Upload manifest saved to: {manifest_file}")
        
        if failed_count == 0:
            print("\n✅ V6 UPLOAD COMPLETE!")
            print("   Your modular V6 structure is now available in LeekWars!")
            print("   Main script: V6_Main")
            print("\n   To use in battle:")
            print("   1. Go to your AI scripts in LeekWars")
            print("   2. Navigate to V6_Modular folder")
            print("   3. Select V6_Main as your leek's AI")
            return True
        else:
            print("\n⚠️  Upload completed with some failures")
            print("   Check the manifest file for details")
            return False
    
    def disconnect(self):
        """Disconnect from LeekWars"""
        if self.token:
            url = f"{self.base_url}/farmer/disconnect/{self.token}"
            self.session.post(url)
            print("\n👋 Disconnected from LeekWars")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload V6 modules to LeekWars')
    parser.add_argument('--dir', default='/home/ubuntu/V6_modules',
                      help='V6 modules directory')
    parser.add_argument('--email', help='LeekWars email')
    parser.add_argument('--password', help='LeekWars password')
    
    args = parser.parse_args()
    
    v6_dir = Path(args.dir)
    if not v6_dir.exists():
        print(f"❌ Error: {v6_dir} does not exist")
        print("Run the modularization script first:")
        print("  python3 /home/ubuntu/scripts/tools/lw_create_v6_structure.py")
        sys.exit(1)
    
    # Check that we have the integrated file
    if not (v6_dir / "V6_main.ls").exists():
        print(f"❌ Error: V6_main.ls not found in {v6_dir}")
        sys.exit(1)
    
    print("="*60)
    print("V6 LEEKWARS UPLOADER")
    print("="*60)
    print(f"📁 Source: {v6_dir}")
    print(f"📦 Modules: {len(list(v6_dir.rglob('*.ls')))} files")
    
    # Create uploader
    uploader = V6LeekWarsUploader()
    
    # Get credentials
    email = args.email
    password = args.password
    
    if not email:
        email = "tanguy.pedrazzoli@gmail.com"  # Default from lw_update_script.py
    if not password:
        password = "tanguy0211"  # Default from lw_update_script.py
    
    # Login
    if not uploader.login(email, password):
        print("\n❌ Failed to login. Please check your credentials.")
        sys.exit(1)
    
    try:
        # Upload V6 structure
        success = uploader.upload_v6_structure(v6_dir)
        
        if not success:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        # Always disconnect properly
        uploader.disconnect()
    
    sys.exit(0)

if __name__ == '__main__':
    main()