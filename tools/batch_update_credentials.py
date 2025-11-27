#!/usr/bin/env python3
"""
Batch update all scripts to use config_loader instead of hardcoded credentials
"""

import re
import os
from pathlib import Path

# List of files to update (excluding already updated ones)
FILES_TO_UPDATE = [
    "check_leek_simple.py",
    "check_leeks.py",
    "debug_websocket.py",
    "delete_specific_folders.py",
    "delete_unwanted_files.py",
    "lw_boss_fights.py",
    "lw_charateristics.py",
    "lw_check_structure.py",
    "lw_cleanup_root.py",
    "lw_cookie_uploader.py",
    "lw_debug.py",
    "lw_farmer_fights.py",
    "lw_get_fight_auth.py",
    "lw_leeks_info.py",
    "lw_retrieve_script.py",
    "lw_save_test.py",
    "lw_solo_fights_db.py",
    "lw_solo_fights_leek_1.py",
    "lw_solo_fights_leek_2.py",
    "lw_solo_fights_smart.py",
    "lw_team_fights_all.py",
    "lw_team_fights_all_cure.py",
    "lw_test_runner.py",
    "lw_update_script.py",
    "test_my_leeks.py",
    "test_specific_leek.py",
    "test_weapon_loadouts.py",
    "validate_local_file.py",
    "validate_script.py",
    "websocket_validator.py"
]

def add_import_if_needed(content):
    """Add config_loader import if not present"""
    if "from config_loader import load_credentials" in content:
        return content

    # Find the last import statement
    import_pattern = r'^(import .+|from .+ import .+)$'
    lines = content.split('\n')
    last_import_idx = -1

    for i, line in enumerate(lines):
        if re.match(import_pattern, line.strip()):
            last_import_idx = i

    if last_import_idx != -1:
        # Add import after last import
        lines.insert(last_import_idx + 1, "from config_loader import load_credentials")
        return '\n'.join(lines)
    else:
        # Add at beginning after docstring
        in_docstring = False
        insert_idx = 0
        for i, line in enumerate(lines):
            if '"""' in line or "'''" in line:
                in_docstring = not in_docstring
                if not in_docstring:
                    insert_idx = i + 1
                    break

        lines.insert(insert_idx, "from config_loader import load_credentials")
        return '\n'.join(lines)

def update_credentials(content, is_cure=False):
    """Replace hardcoded credentials with config_loader calls"""

    # Pattern 1: email = "tanguy.pedrazzoli@gmail.com" followed by password = "tanguy0211"
    pattern1 = r'(\s*)email\s*=\s*["\']tanguy\.pedrazzoli@gmail\.com["\']\s*\n\s*password\s*=\s*["\']tanguy0211["\']'
    replacement1 = r'\1email, password = load_credentials()'
    content = re.sub(pattern1, replacement1, content)

    # Pattern 2: Cure account
    pattern2 = r'(\s*)email\s*=\s*["\']Cure["\']\s*\n\s*password\s*=\s*["\']tanguy0211["\']'
    replacement2 = r'\1email, password = load_credentials(account="cure")'
    content = re.sub(pattern2, replacement2, content)

    # Pattern 3: email = input(...) or "tanguy.pedrazzoli@gmail.com"
    pattern3 = r'email\s*=\s*input\([^)]*\)\s*or\s*["\']tanguy\.pedrazzoli@gmail\.com["\']'
    replacement3 = 'email, password = load_credentials()  # Changed from input prompt'
    content = re.sub(pattern3, replacement3, content)

    # Pattern 4: Direct login calls with hardcoded credentials
    pattern4 = r'\.login\(\s*["\']tanguy\.pedrazzoli@gmail\.com["\']\s*,\s*["\']tanguy0211["\']\s*\)'
    replacement4 = '.login(*load_credentials())'
    content = re.sub(pattern4, replacement4, content)

    # Pattern 5: Cure account login
    pattern5 = r'\.login\(\s*["\']Cure["\']\s*,\s*["\']tanguy0211["\']\s*\)'
    replacement5 = '.login(*load_credentials(account="cure"))'
    content = re.sub(pattern5, replacement5, content)

    # Pattern 6: Direct data dict with login/password
    pattern6 = r'(["\']login["\']\s*:\s*)["\']tanguy\.pedrazzoli@gmail\.com["\'](\s*,\s*["\']password["\']\s*:\s*)["\']tanguy0211["\']'
    # This one is tricky - need to keep dict structure
    # For now, skip complex cases

    # Pattern 7: JSON-style data
    pattern7 = r'data\s*=\s*\{\s*["\']login["\']\s*:\s*["\']tanguy\.pedrazzoli@gmail\.com["\']\s*,\s*["\']password["\']\s*:\s*["\']tanguy0211["\']\s*\}'
    replacement7 = 'email, password = load_credentials()\n        data = {"login": email, "password": password}'
    content = re.sub(pattern7, replacement7, content)

    # Pattern 8: Cure JSON-style
    pattern8 = r'data\s*=\s*\{\s*["\']login["\']\s*:\s*["\']Cure["\']\s*,\s*["\']password["\']\s*:\s*["\']tanguy0211["\']\s*\}'
    replacement8 = 'email, password = load_credentials(account="cure")\n        data = {"login": email, "password": password}'
    content = re.sub(pattern8, replacement8, content)

    return content

def update_file(filepath, is_cure=False):
    """Update a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

        # Add import
        content = add_import_if_needed(content)

        # Update credentials
        content = update_credentials(content, is_cure)

        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"   ❌ Error updating {filepath}: {e}")
        return False

def main():
    tools_dir = Path(__file__).parent

    print("="*60)
    print("BATCH UPDATE CREDENTIALS TO USE CONFIG LOADER")
    print("="*60)
    print(f"Processing {len(FILES_TO_UPDATE)} files...\n")

    updated_count = 0
    skipped_count = 0

    for filename in FILES_TO_UPDATE:
        filepath = tools_dir / filename

        if not filepath.exists():
            print(f"⚠️  File not found: {filename}")
            skipped_count += 1
            continue

        is_cure = "cure" in filename.lower()

        if update_file(filepath, is_cure):
            print(f"✅ Updated: {filename}")
            updated_count += 1
        else:
            print(f"⏭️  Skipped (no changes): {filename}")
            skipped_count += 1

    print("\n" + "="*60)
    print("BATCH UPDATE COMPLETE")
    print("="*60)
    print(f"✅ Updated: {updated_count} files")
    print(f"⏭️  Skipped: {skipped_count} files")
    print(f"📁 Total: {len(FILES_TO_UPDATE)} files processed")

if __name__ == "__main__":
    main()
