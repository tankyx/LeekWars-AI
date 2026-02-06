#!/usr/bin/env python3
"""
Generate LeekScript item database from market_data.json

This script reads the market_data.json file and generates a LeekScript module
(item_database.lk) containing all weapon and chip information as static data structures.
"""

import json
import os
import sys

def escape_string(s):
    """Escape string for LeekScript"""
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')

def generate_effect_map(effects):
    """Generate LeekScript map representation of effects array"""
    if not effects:
        return '[:]'

    # Group effects by effect ID, summing values
    effect_groups = {}
    for effect in effects:
        effect_id = effect['type']  # The 'type' field is the effect constant (EFFECT_DAMAGE, EFFECT_POISON, etc.)

        if effect_id not in effect_groups:
            effect_groups[effect_id] = {
                'min': 0,
                'max': 0,
                'turns': effect.get('turns', 0)
            }

        effect_groups[effect_id]['min'] += effect.get('value1', 0)
        effect_groups[effect_id]['max'] += effect.get('value2', 0)
        # Use max turns if multiple effects of same type
        effect_groups[effect_id]['turns'] = max(effect_groups[effect_id]['turns'], effect.get('turns', 0))

    # Build LeekScript map
    entries = []
    for effect_id, values in effect_groups.items():
        # Format: effect_id: [min, max, turns]
        entries.append(f"{effect_id}: [{values['min']}, {values['max']}, {values['turns']}]")

    return '[' + ', '.join(entries) + ']'

def generate_weapon_entry(weapon_id, weapon_data):
    """Generate LeekScript map entry for a weapon"""
    name = weapon_data.get('name', f'weapon_{weapon_id}')
    min_range = weapon_data.get('min_range', 0)
    max_range = weapon_data.get('max_range', 0)
    tp_cost = weapon_data.get('tp_cost', 0)
    launch_type = weapon_data.get('launch_type', 7)
    area = weapon_data.get('area', 1)
    effects = generate_effect_map(weapon_data.get('effects', []))

    return f"""    {weapon_id}: [
        "{escape_string(name)}",  // name
        {min_range},  // min_range
        {max_range},  // max_range
        {effects},  // effects
        {tp_cost},  // tp_cost
        {launch_type},  // launch_type
        {area}  // area
    ]"""

def generate_chip_entry(chip_id, chip_data):
    """Generate LeekScript map entry for a chip"""
    name = chip_data.get('name', f'chip_{chip_id}')
    min_range = chip_data.get('min_range', 0)
    max_range = chip_data.get('max_range', 0)
    tp_cost = chip_data.get('tp_cost', 0)
    launch_type = chip_data.get('launch_type', 7)
    area = chip_data.get('area', 1)
    cooldown = chip_data.get('cooldown', 0)
    effects = generate_effect_map(chip_data.get('effects', []))

    return f"""    {chip_id}: [
        "{escape_string(name)}",  // name
        {min_range},  // min_range
        {max_range},  // max_range
        {effects},  // effects
        {tp_cost},  // tp_cost
        {launch_type},  // launch_type
        {area},  // area
        {cooldown}  // cooldown
    ]"""

def generate_leekscript_database(json_path, output_path):
    """Generate the complete LeekScript database file"""

    with open(json_path, 'r') as f:
        data = json.load(f)

    weapons = data.get('weapons', {})
    chips = data.get('chips', {})

    print(f"Found {len(weapons)} weapons and {len(chips)} chips")

    # Generate weapon entries
    weapon_entries = []
    for weapon_id, weapon_data in weapons.items():
        weapon_entries.append(generate_weapon_entry(weapon_id, weapon_data))

    # Generate chip entries
    chip_entries = []
    for chip_id, chip_data in chips.items():
        chip_entries.append(generate_chip_entry(chip_id, chip_data))

    # Build the complete LeekScript file
    leekscript_code = f"""// AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
// Generated from market_data.json by tools/generate_item_database.py
//
// This module provides static weapon and chip data for the V8 AI system.
// Data format:
//   Weapons: [name, min_range, max_range, effects, tp_cost, launch_type, area]
//   Chips: [name, min_range, max_range, effects, tp_cost, launch_type, area, cooldown]
//   Effects: [effect_type: [min_value, max_value, turns], ...]

global WEAPON_DATABASE = [
{',\n'.join(weapon_entries)}
]

global CHIP_DATABASE = [
{',\n'.join(chip_entries)}
]

// Lookup functions
function getWeaponData(weaponId) {{
    if (mapContainsKey(WEAPON_DATABASE, weaponId)) {{
        return WEAPON_DATABASE[weaponId]
    }}
    return null
}}

function getChipData(chipId) {{
    if (mapContainsKey(CHIP_DATABASE, chipId)) {{
        return CHIP_DATABASE[chipId]
    }}
    return null
}}

function hasWeaponData(weaponId) {{
    return mapContainsKey(WEAPON_DATABASE, weaponId)
}}

function hasChipData(chipId) {{
    return mapContainsKey(CHIP_DATABASE, chipId)
}}
"""

    # Write to output file
    with open(output_path, 'w') as f:
        f.write(leekscript_code)

    print(f"Generated {output_path}")
    print(f"  - {len(weapon_entries)} weapons")
    print(f"  - {len(chip_entries)} chips")

    # Report file size
    file_size = os.path.getsize(output_path)
    print(f"  - File size: {file_size:,} bytes ({file_size / 1024:.1f} KB)")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    json_path = os.path.join(project_root, 'data', 'market_data.json')
    output_path = os.path.join(project_root, 'V8_modules', 'item_database.lk')

    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found", file=sys.stderr)
        sys.exit(1)

    generate_leekscript_database(json_path, output_path)
    print("\\nDone! Don't forget to upload the V8 modules with the new database.")

if __name__ == '__main__':
    main()
