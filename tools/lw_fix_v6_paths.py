#!/usr/bin/env python3
"""
Fix include paths in V6_main.ls and update in LeekWars
"""

import sys
import re
import requests
from pathlib import Path

def fix_include_paths(content: str) -> str:
    """Fix include paths to use full LeekWars paths"""
    print("🔧 Fixing include paths...")
    
    # Pattern to match include statements
    pattern = r'include\("([^"]+)"\)'
    
    def replace_path(match):
        old_path = match.group(1)
        # Add the 6.0/V6/ prefix to all paths
        new_path = f"6.0/V6/{old_path}"
        print(f"   {old_path} → {new_path}")
        return f'include("{new_path}")'
    
    # Replace all include paths
    fixed_content = re.sub(pattern, replace_path, content)
    
    return fixed_content

def update_v6_main_in_leekwars(content: str):
    """Update V6_main.ls in LeekWars"""
    print("\n📤 Updating V6_main in LeekWars...")
    
    session = requests.Session()
    base_url = "https://leekwars.com/api"
    
    # Login
    print("🔐 Logging in...")
    response = session.post(
        f"{base_url}/farmer/login-token",
        data={"login": "tanguy.pedrazzoli@gmail.com", "password": "tanguy0211"}
    )
    
    if response.status_code != 200:
        print("❌ Login failed")
        return False
    
    data = response.json()
    token = data.get("token")
    print(f"✅ Logged in as: {data['farmer']['login']}")
    
    # Update V6_main.ls (ID: 445295)
    v6_main_id = 445295
    print(f"📝 Updating V6_main.ls (ID: {v6_main_id})...")
    
    response = session.post(
        f"{base_url}/ai/save",
        data={
            "ai_id": str(v6_main_id),
            "code": content
        }
    )
    
    if response.status_code == 200:
        print("✅ V6_main.ls updated successfully!")
        result = True
    else:
        print(f"❌ Failed to update (Status: {response.status_code})")
        result = False
    
    # Disconnect
    session.post(f"{base_url}/farmer/disconnect/{token}")
    print("👋 Disconnected")
    
    return result

def main():
    print("="*60)
    print("V6 INCLUDE PATH FIXER")
    print("="*60)
    
    # Read V6_main.ls
    v6_main_path = Path("/home/ubuntu/V6_modules/V6_main.ls")
    
    if not v6_main_path.exists():
        print("❌ V6_main.ls not found")
        return 1
    
    print(f"📖 Reading {v6_main_path}...")
    with open(v6_main_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix include paths
    fixed_content = fix_include_paths(content)
    
    # Save fixed version locally
    fixed_path = Path("/home/ubuntu/V6_modules/V6_main_fixed.ls")
    print(f"\n💾 Saving fixed version to {fixed_path}...")
    with open(fixed_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    # Update in LeekWars
    if update_v6_main_in_leekwars(fixed_content):
        print("\n✅ All done! V6_main.ls has been fixed and updated in LeekWars")
        print("   Include paths now use full LeekWars paths (6.0/V6/...)")
        return 0
    else:
        print("\n⚠️  Local file fixed but LeekWars update failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())