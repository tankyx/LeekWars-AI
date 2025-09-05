#!/usr/bin/env python3
"""
LeekWars Script Retriever
Connects to LeekWars and retrieves a script from the editor
"""

import requests
import json
import sys
from getpass import getpass

BASE_URL = "https://leekwars.com/api"

class LeekWarsScriptRetriever:
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
    
    def get_script(self, script_id):
        """Retrieve a script from the editor using the script ID"""
        print(f"\n📄 Retrieving script {script_id}...")
        
        # Try different possible API endpoints
        endpoints = [
            f"{BASE_URL}/ai/get/{script_id}",
            f"{BASE_URL}/script/get/{script_id}",
            f"{BASE_URL}/ai-script/get/{script_id}"
        ]
        
        for url in endpoints:
            print(f"   Trying: {url}")
            response = self.session.get(url)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Check if we got script data
                    if "ai" in data or "script" in data:
                        script_data = data.get("ai") or data.get("script")
                        
                        if isinstance(script_data, dict):
                            script_name = script_data.get("name", "Unknown")
                            script_code = script_data.get("code", "")
                            script_valid = script_data.get("valid", None)
                            
                            print(f"\n✅ Script retrieved successfully!")
                            print(f"   📝 Name: {script_name}")
                            if script_valid is not None:
                                print(f"   ✓ Valid: {script_valid}")
                            
                            # Save to file
                            filename = f"script_{script_id}_{script_name.replace(' ', '_')}.lks"
                            with open(filename, "w", encoding="utf-8") as f:
                                f.write(script_code)
                            
                            print(f"   💾 Saved to: {filename}")
                            print(f"   📏 Size: {len(script_code)} characters")
                            
                            return True
                    
                    # Check for error response
                    if "success" in data and not data["success"]:
                        error = data.get("error", "Unknown error")
                        print(f"   ❌ API error: {error}")
                    else:
                        print(f"   ⚠️ Unexpected response structure")
                        print(f"   Keys: {list(data.keys())}")
                        
                except json.JSONDecodeError:
                    print(f"   ❌ Invalid JSON response")
            
            elif response.status_code == 404:
                print(f"   ⚠️ Not found at this endpoint")
            elif response.status_code == 401:
                print(f"   ❌ Unauthorized - login may have expired")
                return False
            elif response.status_code == 403:
                print(f"   ❌ Forbidden - you may not have access to this script")
                return False
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
        
        print("\n❌ Could not retrieve script from any endpoint")
        return False
    
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
    print("="*60)
    print("LEEKWARS SCRIPT RETRIEVER")
    print("="*60)
    
    # Create retriever instance
    retriever = LeekWarsScriptRetriever()
    
    # Script ID to retrieve
    script_id = 444880
    print(f"\nTarget script ID: {script_id}")
    
    # Get credentials (using the same as in the example)
    email = "tanguy.pedrazzoli@gmail.com"
    password = "tanguy0211"
    
    # Login
    if not retriever.login(email, password):
        print("\n❌ Failed to login. Please check your credentials.")
        return 1
    
    try:
        # Retrieve the script
        success = retriever.get_script(script_id)
        
        if not success:
            print("\n❌ Failed to retrieve script")
            print("\nPossible reasons:")
            print("  - The script ID may be incorrect")
            print("  - You may not have access to this script")
            print("  - The script may not exist")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        # Always disconnect properly
        retriever.disconnect()
    
    return 0

if __name__ == "__main__":
    exit(main())