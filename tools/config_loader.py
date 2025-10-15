#!/usr/bin/env python3
"""
Config Loader - Helper module for loading LeekWars credentials from config.json

Usage:
    from config_loader import load_credentials

    # Load main account (default)
    email, password = load_credentials()

    # Load specific account
    email, password = load_credentials(account="cure")
"""

import json
import os
import sys
from pathlib import Path


def get_config_path():
    """Get the path to config.json"""
    # Get the tools directory (where this script is located)
    tools_dir = Path(__file__).parent
    config_path = tools_dir / "config.json"
    return config_path


def load_config():
    """Load the config.json file"""
    config_path = get_config_path()

    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        print(f"   Please copy config.template.json to config.json and fill in your credentials")
        sys.exit(1)

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing config.json: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading config.json: {e}")
        sys.exit(1)


def load_credentials(account="main"):
    """Load LeekWars credentials from config.json

    Args:
        account (str): Account name to load ("main" or "cure"). Default is "main".

    Returns:
        tuple: (email, password)
    """
    config = load_config()

    if "accounts" not in config:
        print("❌ Missing 'accounts' section in config.json")
        sys.exit(1)

    accounts = config["accounts"]

    if account not in accounts:
        print(f"❌ Account '{account}' not found in config.json")
        print(f"   Available accounts: {', '.join(accounts.keys())}")
        sys.exit(1)

    account_data = accounts[account]

    email = account_data.get("email")
    password = account_data.get("password")

    if not email or not password:
        print(f"❌ Missing email or password for account '{account}' in config.json")
        sys.exit(1)

    # Check if credentials are still default template values
    if email in ["your.email@example.com", "your_alternate_account"] or password == "your_password_here":
        print(f"❌ Please update config.json with your actual credentials for account '{account}'")
        print(f"   Edit: {get_config_path()}")
        sys.exit(1)

    return email, password


if __name__ == "__main__":
    # Test the config loader
    print("Testing config loader...")
    print("\n=== Main Account ===")
    email, password = load_credentials()
    print(f"✅ Loaded credentials for: {email}")
    print(f"   Password: {'*' * len(password)}")

    print("\n=== Cure Account ===")
    email, password = load_credentials(account="cure")
    print(f"✅ Loaded credentials for: {email}")
    print(f"   Password: {'*' * len(password)}")
