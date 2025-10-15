#!/usr/bin/env python3
"""
Delete unwanted refactored files from LeekWars
"""

import os
import sys
import json
import requests
from pathlib import Path
from config_loader import load_credentials

class FileDeleter:
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
    
    def get_existing_ais(self):
        """Get all existing AIs"""
        response = self.session.get(f"{self.base_url}/ai/get-farmer-ais")
        if response.status_code == 200:
            return response.json()
        return {"folders": [], "ais": []}
    
    def find_ai_by_name(self, name: str, ais: list):
        """Find AI by name"""
        for ai in ais:
            if ai["name"] == name:
                return ai["id"]
        return None
    
    def delete_ai(self, ai_id: int, name: str) -> bool:
        """Delete an AI script"""
        print(f"🗑️  Deleting: {name} (ID: {ai_id})")
        
        # Try different possible endpoints
        endpoints = [
            f"{self.base_url}/ai/delete",
            f"{self.base_url}/ai/delete/{ai_id}",
            f"{self.base_url}/ai/delete-ai"
        ]
        
        for endpoint in endpoints:
            response = self.session.post(endpoint, data={"ai_id": ai_id})
            if response.status_code == 200:
                return True
            print(f"   Tried {endpoint}: {response.status_code}")
        
        # If all endpoints failed, return the last response for debugging
        response = self.session.post(f"{self.base_url}/ai/delete", data={"ai_id": ai_id})
        
        if response.status_code == 200:
            print(f"   ✅ Deleted successfully")
            return True
        else:
            print(f"   ❌ Failed to delete: {response.status_code}")
            return False
    
    def delete_unwanted_files(self):
        """Delete the unwanted refactored files"""
        print("============================================================")
        print("DELETING UNWANTED REFACTORED FILES")
        print("============================================================")
        
        # Get all existing AIs
        data = self.get_existing_ais()
        ais = data.get("ais", [])
        
        # List of files to delete
        files_to_delete = [
            "V6_main_refactored",
            "V6_BLaser_main", 
            "test_refactored",
            "REFACTORED_MODULE_INDEX_md"
        ]
        
        deleted_count = 0
        
        for filename in files_to_delete:
            ai_id = self.find_ai_by_name(filename, ais)
            if ai_id:
                if self.delete_ai(ai_id, filename):
                    deleted_count += 1
            else:
                print(f"🔍 File not found: {filename}")
        
        print(f"\n✨ Deletion complete: {deleted_count}/{len(files_to_delete)} files deleted")

def main():
    deleter = FileDeleter()
    
    # Use same credentials as upload script
    if deleter.login(*load_credentials()):
        deleter.delete_unwanted_files()
        print("\n👋 Disconnected")
    else:
        print("Failed to login")
        sys.exit(1)

if __name__ == "__main__":
    main()