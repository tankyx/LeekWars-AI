#!/usr/bin/env python3
"""Remove comments from LeekScript files while preserving strings"""

import re
import sys
from pathlib import Path

def remove_comments(content):
    """Remove // and /* */ comments while preserving strings"""
    result = []
    i = 0
    while i < len(content):
        # Check for string literals (single or double quoted)
        if content[i] in ('"', "'"):
            quote = content[i]
            result.append(content[i])
            i += 1
            # Copy entire string including escaped quotes
            while i < len(content):
                if content[i] == '\\' and i + 1 < len(content):
                    result.append(content[i:i+2])
                    i += 2
                elif content[i] == quote:
                    result.append(content[i])
                    i += 1
                    break
                else:
                    result.append(content[i])
                    i += 1
        # Check for multi-line comment
        elif i + 1 < len(content) and content[i:i+2] == '/*':
            # Skip until we find */
            i += 2
            while i + 1 < len(content):
                if content[i:i+2] == '*/':
                    i += 2
                    break
                i += 1
        # Check for single-line comment
        elif i + 1 < len(content) and content[i:i+2] == '//':
            # Skip until end of line
            while i < len(content) and content[i] != '\n':
                i += 1
            # Keep the newline
            if i < len(content):
                result.append(content[i])
                i += 1
        else:
            result.append(content[i])
            i += 1

    return ''.join(result)

def clean_empty_lines(content):
    """Remove excessive empty lines (more than 1 consecutive)"""
    lines = content.split('\n')
    result = []
    prev_empty = False

    for line in lines:
        is_empty = line.strip() == ''
        if is_empty and prev_empty:
            continue  # Skip multiple consecutive empty lines
        result.append(line)
        prev_empty = is_empty

    return '\n'.join(result)

def process_file(filepath):
    """Process a single file"""
    print(f"Processing {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove comments
    content = remove_comments(content)

    # Clean up excessive empty lines
    content = clean_empty_lines(content)

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  ✓ Cleaned {filepath}")

def main():
    v8_dir = Path('/home/ubuntu/LeekWars-AI/V8_modules')

    # Find all .lk files
    lk_files = list(v8_dir.rglob('*.lk'))

    print(f"Found {len(lk_files)} LeekScript files")
    print("=" * 60)

    for lk_file in sorted(lk_files):
        process_file(lk_file)

    print("=" * 60)
    print(f"✅ Processed {len(lk_files)} files")

if __name__ == '__main__':
    main()
