#!/usr/bin/env python3
"""
LeekWars Script Updater
Updates a script on LeekWars with content from a local file
Usage: python3 lw_update_script.py <file_path> <script_id>
"""

import requests
import json
import sys
import os
import argparse
from datetime import datetime

BASE_URL = "https://leekwars.com/api"

class LeekWarsScriptUpdater:
    def __init__(self):
        """Initialize session and variables"""
        self.session = requests.Session()
        self.farmer = None
        self.token = None
        
    def login(self, email, password):
        """Login using email and password, maintain session cookies"""
        print("🔐 Logging in...")
        
        login_url = f"{BASE_URL}/farmer/login-token"
        login_data = {
            "login": email,
            "password": password
        }
        
        try:
            response = self.session.post(login_url, data=login_data)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    if "farmer" in data and "token" in data:
                        self.farmer = data["farmer"]
                        self.token = data["token"]
                        
                        farmer_name = self.farmer.get("login", "Unknown")
                        farmer_id = self.farmer.get("id", "Unknown")
                        
                        print(f"\n✅ Connected successfully!")
                        print(f"   👤 Farmer: {farmer_name} (ID: {farmer_id})")
                        
                        return True
                    
                    elif "success" in data and not data["success"]:
                        error_msg = data.get("error", "Unknown error")
                        print(f"   ❌ Login failed: {error_msg}")
                        return False
                    
                    else:
                        print(f"   ❌ Unexpected response structure")
                        return False
                        
                except json.JSONDecodeError as e:
                    print(f"   ❌ Failed to parse JSON response: {e}")
                    return False
                    
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {e}")
            return False
    
    def get_script_info(self, script_id):
        """Get information about the script before updating"""
        print(f"\n📄 Getting current script info (ID: {script_id})...")
        
        url = f"{BASE_URL}/ai/get/{script_id}"
        response = self.session.get(url)
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                if "ai" in data:
                    script_data = data["ai"]
                    
                    if isinstance(script_data, dict):
                        script_name = script_data.get("name", "Unknown")
                        current_size = len(script_data.get("code", ""))
                        script_valid = script_data.get("valid", None)
                        
                        print(f"   📝 Name: {script_name}")
                        print(f"   📏 Current size: {current_size} characters")
                        if script_valid is not None:
                            if script_valid:
                                print(f"   ✓ Currently valid: {script_valid}")
                            else:
                                print(f"   ❌ Currently invalid: {script_valid}")
                                # Check for compilation errors
                                if "error" in script_data:
                                    print(f"   ❌ Error: {script_data['error']}")
                                if "errors" in script_data:
                                    print(f"   ❌ Errors:")
                                    for err in script_data["errors"]:
                                        print(f"      - {err}")
                        
                        return script_data
                
                if "success" in data and not data["success"]:
                    error = data.get("error", "Unknown error")
                    print(f"   ❌ API error: {error}")
                else:
                    print(f"   ⚠️ Script not found or no access")
                    
            except json.JSONDecodeError:
                print(f"   ❌ Invalid JSON response")
        
        elif response.status_code == 404:
            print(f"   ❌ Script not found")
        elif response.status_code == 401:
            print(f"   ❌ Unauthorized - login may have expired")
        elif response.status_code == 403:
            print(f"   ❌ Forbidden - you don't have access to this script")
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
        
        return None
    
    def update_script(self, script_id, code_content):
        """Update a script with new code content"""
        print(f"\n📤 Updating script {script_id}...")
        
        # Try different possible API endpoints for updating
        endpoints = [
            f"{BASE_URL}/ai/save",
            f"{BASE_URL}/ai-script/save",
            f"{BASE_URL}/script/save"
        ]
        
        for url in endpoints:
            print(f"   Trying: {url}")
            
            # Prepare the data - the API expects ai_id and code
            data = {
                "ai_id": str(script_id),
                "code": code_content
            }
            
            response = self.session.post(url, data=data)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    
                    # Check for success response
                    if result.get("success") == True:
                        print(f"\n✅ Script updated successfully!")
                        
                        # Show validation results if available
                        if "result" in result:
                            validation = result["result"]
                            if isinstance(validation, dict):
                                if validation.get("valid"):
                                    print(f"   ✓ Code is valid")
                                else:
                                    print(f"   ⚠️ Code has validation errors:")
                                    if "errors" in validation:
                                        for error in validation["errors"]:
                                            print(f"      - {error}")
                        
                        return True
                    
                    # Check for alternate success format (with result and modified fields)
                    elif "result" in result and "modified" in result:
                        # This appears to be a successful update with compilation info
                        print(f"\n✅ Script updated successfully!")
                        
                        # Parse compilation results if available
                        if isinstance(result["result"], dict):
                            for script_id, compile_info in result["result"].items():
                                if compile_info is None:
                                    print(f"   ❌ Compilation failed! Script has errors.")
                                elif compile_info == False:
                                    print(f"   ❌ Compilation failed! Script is invalid.")
                                elif isinstance(compile_info, list):
                                    if len(compile_info) > 0:
                                        print(f"   ✓ Script compiled with {len(compile_info)} include(s)")
                                    else:
                                        print(f"   ✓ Script compiled successfully")
                                elif isinstance(compile_info, dict):
                                    # Check for error information in the dict
                                    if "error" in compile_info:
                                        print(f"   ❌ Compilation error: {compile_info['error']}")
                                    elif "errors" in compile_info:
                                        print(f"   ❌ Compilation errors:")
                                        for error in compile_info["errors"]:
                                            print(f"      - {error}")
                                    elif "warnings" in compile_info:
                                        print(f"   ⚠️ Compilation warnings:")
                                        for warning in compile_info["warnings"]:
                                            print(f"      - {warning}")
                                    else:
                                        print(f"   ℹ️ Compilation info: {compile_info}")
                                else:
                                    print(f"   ℹ️ Compilation result: {compile_info}")
                        
                        # Also check for errors/warnings at the top level
                        if "errors" in result:
                            print(f"\n   ❌ Errors found:")
                            for error in result["errors"]:
                                if isinstance(error, dict):
                                    line = error.get("line", "?")
                                    char = error.get("char", "?")
                                    msg = error.get("message", error)
                                    print(f"      Line {line}, char {char}: {msg}")
                                else:
                                    print(f"      - {error}")
                        
                        if "warnings" in result:
                            print(f"\n   ⚠️ Warnings found:")
                            for warning in result["warnings"]:
                                if isinstance(warning, dict):
                                    line = warning.get("line", "?")
                                    char = warning.get("char", "?")
                                    msg = warning.get("message", warning)
                                    print(f"      Line {line}, char {char}: {msg}")
                                else:
                                    print(f"      - {warning}")
                        
                        return True
                    
                    elif result.get("success") == False:
                        error = result.get("error", "Unknown error")
                        print(f"   ❌ Failed to update: {error}")
                        
                        # Try to get more details
                        if "result" in result:
                            print(f"   Details: {result['result']}")
                    
                    else:
                        print(f"   ⚠️ Unexpected response: {result}")
                        
                except json.JSONDecodeError:
                    print(f"   ❌ Invalid JSON response")
                    
            elif response.status_code == 404:
                print(f"   ⚠️ Endpoint not found, trying next...")
                continue
            elif response.status_code == 401:
                print(f"   ❌ Unauthorized - login may have expired")
                return False
            elif response.status_code == 403:
                print(f"   ❌ Forbidden - you don't have permission to update this script")
                return False
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                if response.text:
                    print(f"   Response: {response.text[:200]}")
        
        print("\n❌ Could not update script using any endpoint")
        return False
    
    def create_backup(self, script_data, backup_dir="backups"):
        """Create a backup of the current script before updating"""
        if not script_data:
            return None
            
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        script_name = script_data.get("name", "unknown").replace(" ", "_")
        script_id = script_data.get("id", "unknown")
        
        backup_file = f"{backup_dir}/backup_{script_id}_{script_name}_{timestamp}.lks"
        
        with open(backup_file, "w", encoding="utf-8") as f:
            f.write(script_data.get("code", ""))
        
        print(f"   💾 Backup saved: {backup_file}")
        return backup_file
    
    def disconnect(self):
        """Disconnect from LeekWars"""
        if self.token:
            url = f"{BASE_URL}/farmer/disconnect/{self.token}"
            response = self.session.post(url)
            if response.status_code == 401:
                url = f"{BASE_URL}/farmer/disconnect"
                self.session.post(url)
            print("\n👋 Disconnected from LeekWars")

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='LeekWars Script Updater - Update scripts from local files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 lw_update_script.py my_script.lks 444880
  python3 lw_update_script.py /path/to/script.txt 123456 --no-backup
  python3 lw_update_script.py script.lks 789 --backup-dir ./my_backups
        """
    )
    
    parser.add_argument('file_path', help='Path to the file containing the new script code')
    parser.add_argument('script_id', type=int, help='ID of the script to update on LeekWars')
    parser.add_argument('--no-backup', action='store_true', help='Skip creating a backup of the current script')
    parser.add_argument('--backup-dir', default='backups', help='Directory to store backups (default: backups)')
    
    args = parser.parse_args()
    
    # Validate file exists
    if not os.path.exists(args.file_path):
        print(f"❌ Error: File not found: {args.file_path}")
        return 1
    
    if not os.path.isfile(args.file_path):
        print(f"❌ Error: Path is not a file: {args.file_path}")
        return 1
    
    print("="*60)
    print("LEEKWARS SCRIPT UPDATER")
    print("="*60)
    print(f"📁 Source file: {args.file_path}")
    print(f"🎯 Target script ID: {args.script_id}")
    print(f"💾 Backup: {'Disabled' if args.no_backup else f'Enabled (dir: {args.backup_dir})'}")
    
    # Read the file content
    try:
        with open(args.file_path, "r", encoding="utf-8") as f:
            new_code = f.read()
        
        file_size = len(new_code)
        file_lines = new_code.count('\n') + 1
        
        print(f"\n📊 File info:")
        print(f"   Size: {file_size} characters")
        print(f"   Lines: {file_lines}")
        
    except Exception as e:
        print(f"\n❌ Error reading file: {e}")
        return 1
    
    # Create updater instance
    updater = LeekWarsScriptUpdater()
    
    # Get credentials
    email, password = load_credentials()
    
    # Login
    if not updater.login(email, password):
        print("\n❌ Failed to login. Please check your credentials.")
        return 1
    
    try:
        # Get current script info
        current_script = updater.get_script_info(args.script_id)
        
        if not current_script:
            print("\n❌ Cannot access script. Make sure:")
            print("   - The script ID is correct")
            print("   - You have permission to edit this script")
            print("   - The script exists")
            return 1
        
        # Create backup unless disabled
        if not args.no_backup:
            print(f"\n💾 Creating backup...")
            backup_path = updater.create_backup(current_script, args.backup_dir)
        
        # Update the script
        print(f"\n📝 Uploading new code ({file_size} characters)...")
        success = updater.update_script(args.script_id, new_code)
        
        if success:
            print(f"\n✨ Script {args.script_id} has been updated successfully!")
            
            # Verify the update
            print(f"\n🔍 Verifying update...")
            updated_script = updater.get_script_info(args.script_id)
            if updated_script:
                new_size = len(updated_script.get("code", ""))
                if new_size == file_size:
                    print(f"   ✓ Size matches: {new_size} characters")
                else:
                    print(f"   ⚠️ Size mismatch: expected {file_size}, got {new_size}")
        else:
            print(f"\n❌ Failed to update script")
            if not args.no_backup and backup_path:
                print(f"   Your backup is available at: {backup_path}")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        return 1
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
from config_loader import load_credentials
        traceback.print_exc()
        return 1
        
    finally:
        # Always disconnect properly
        updater.disconnect()
    
    return 0

if __name__ == "__main__":
    exit(main())