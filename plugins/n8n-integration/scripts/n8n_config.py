#!/usr/bin/env python3
"""
n8n Configuration Manager

Manages multi-account configuration for n8n integration.
Reads from ~/.config/n8n-integration/accounts.yaml

Usage:
    python3 n8n_config.py --list-accounts
    python3 n8n_config.py --get-default
    python3 n8n_config.py --add <id> --url <url> --key <key> [--name <name>]
    python3 n8n_config.py --remove <id>
    python3 n8n_config.py --set-default <id>
    python3 n8n_config.py --get-env [account_id]  # For wrapper script
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Try to import yaml, provide helpful error if not available
try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# =============================================================================
# Configuration Paths
# =============================================================================

CONFIG_DIR = Path.home() / ".config" / "n8n-integration"
CONFIG_FILE = CONFIG_DIR / "accounts.yaml"

DEFAULT_CONFIG = {
    "default_account": "local",
    "accounts": {
        "local": {
            "name": "Local n8n",
            "url": "http://localhost:5678/api/v1",
            "api_key": "YOUR_API_KEY_HERE",
            "description": "Local n8n instance"
        }
    }
}


# =============================================================================
# Configuration Functions
# =============================================================================

def ensure_config_dir() -> None:
    """Ensure config directory exists with proper permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(CONFIG_DIR, 0o700)


def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if not CONFIG_FILE.exists():
        print(f"Warning: Config file not found at {CONFIG_FILE}", file=sys.stderr)
        print("Creating default configuration...", file=sys.stderr)
        ensure_config_dir()
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

    with open(CONFIG_FILE) as f:
        config = yaml.safe_load(f) or {}

    # Ensure required keys exist
    if "accounts" not in config:
        config["accounts"] = {}
    if "default_account" not in config:
        config["default_account"] = "local"

    return config


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to YAML file."""
    ensure_config_dir()

    header = """# n8n Integration - Multi-Account Configuration
#
# This file stores credentials for multiple n8n instances.
# Use /n8n:setup to manage accounts.
#
# SECURITY: This file contains sensitive API keys.
# Ensure proper file permissions: chmod 600 accounts.yaml

"""

    with open(CONFIG_FILE, 'w') as f:
        f.write(header)
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    # Secure file permissions
    os.chmod(CONFIG_FILE, 0o600)


def get_account(account_id: Optional[str] = None) -> Dict[str, Any]:
    """Get account configuration by ID or default."""
    config = load_config()

    # Use provided account or default
    if account_id is None:
        account_id = os.environ.get("N8N_ACCOUNT") or config.get("default_account", "local")

    accounts = config.get("accounts", {})

    if account_id not in accounts:
        available = list(accounts.keys())
        print(f"Error: Account '{account_id}' not found.", file=sys.stderr)
        if available:
            print(f"Available accounts: {', '.join(available)}", file=sys.stderr)
        else:
            print("No accounts configured. Run: /n8n:setup --add <id>", file=sys.stderr)
        sys.exit(1)

    return accounts[account_id]


def get_api_credentials(account_id: Optional[str] = None) -> Tuple[str, str]:
    """Get API URL and key for specified account."""
    account = get_account(account_id)

    url = account.get("url", "")
    api_key = account.get("api_key", "")

    if not url:
        print(f"Error: Account missing 'url' field", file=sys.stderr)
        sys.exit(1)

    if not api_key or api_key.startswith("YOUR_"):
        print(f"Error: API key not configured for account", file=sys.stderr)
        print("Get your API key from n8n: Settings > API > Create API Key", file=sys.stderr)
        sys.exit(1)

    return url, api_key


def list_accounts() -> List[Dict[str, Any]]:
    """List all configured accounts."""
    config = load_config()
    default = config.get("default_account", "")
    accounts = []

    for account_id, account in config.get("accounts", {}).items():
        accounts.append({
            "id": account_id,
            "name": account.get("name", account_id),
            "url": account.get("url", ""),
            "description": account.get("description", ""),
            "is_default": account_id == default,
            "configured": bool(account.get("api_key")) and not account.get("api_key", "").startswith("YOUR_")
        })

    return accounts


def add_account(account_id: str, url: str, api_key: str,
                name: Optional[str] = None, description: Optional[str] = None) -> None:
    """Add or update an account."""
    config = load_config()

    # Normalize URL (ensure it ends with /api/v1 or similar)
    if not url.endswith("/"):
        url = url.rstrip("/")
    if not url.endswith("/api/v1"):
        if "/api/" not in url:
            url = f"{url}/api/v1"

    config["accounts"][account_id] = {
        "name": name or account_id,
        "url": url,
        "api_key": api_key,
        "description": description or f"n8n instance: {account_id}"
    }

    # If this is the first account, make it default
    if len(config["accounts"]) == 1:
        config["default_account"] = account_id

    save_config(config)
    print(f"Account '{account_id}' saved successfully.")


def remove_account(account_id: str) -> None:
    """Remove an account."""
    config = load_config()

    if account_id not in config.get("accounts", {}):
        print(f"Error: Account '{account_id}' not found.", file=sys.stderr)
        sys.exit(1)

    del config["accounts"][account_id]

    # If we removed the default, set a new default
    if config.get("default_account") == account_id:
        remaining = list(config["accounts"].keys())
        config["default_account"] = remaining[0] if remaining else ""

    save_config(config)
    print(f"Account '{account_id}' removed.")


def set_default(account_id: str) -> None:
    """Set the default account."""
    config = load_config()

    if account_id not in config.get("accounts", {}):
        print(f"Error: Account '{account_id}' not found.", file=sys.stderr)
        sys.exit(1)

    config["default_account"] = account_id
    save_config(config)
    print(f"Default account set to '{account_id}'.")


def get_default_account_id() -> str:
    """Get the default account ID."""
    config = load_config()
    return os.environ.get("N8N_ACCOUNT") or config.get("default_account", "local")


def get_env_export(account_id: Optional[str] = None) -> str:
    """Get environment variable export commands for shell scripts."""
    url, api_key = get_api_credentials(account_id)
    return f'export N8N_API_URL="{url}"\nexport N8N_API_KEY="{api_key}"'


# =============================================================================
# CLI Commands
# =============================================================================

def cmd_list_accounts(args) -> None:
    """List all configured accounts."""
    accounts = list_accounts()

    if not accounts:
        print("No accounts configured.")
        print("Add one with: /n8n:setup --add <id> --url <url> --key <key>")
        return

    print(f"\nn8n Accounts ({len(accounts)} configured)")
    print("=" * 60)

    for acct in accounts:
        default_marker = " (default)" if acct["is_default"] else ""
        status = "Configured" if acct["configured"] else "API key needed"

        print(f"\n{acct['id']}{default_marker}")
        print(f"  Name: {acct['name']}")
        print(f"  URL:  {acct['url']}")
        print(f"  Status: {status}")
        if acct["description"]:
            print(f"  Description: {acct['description']}")


def cmd_add_account(args) -> None:
    """Add a new account."""
    if not args.account_id:
        print("Error: --add requires account ID", file=sys.stderr)
        sys.exit(1)
    if not args.url:
        print("Error: --url is required", file=sys.stderr)
        sys.exit(1)
    if not args.key:
        print("Error: --key is required", file=sys.stderr)
        sys.exit(1)

    add_account(args.account_id, args.url, args.key, args.name, args.description)


def cmd_remove_account(args) -> None:
    """Remove an account."""
    if not args.account_id:
        print("Error: --remove requires account ID", file=sys.stderr)
        sys.exit(1)

    remove_account(args.account_id)


def cmd_set_default(args) -> None:
    """Set default account."""
    if not args.account_id:
        print("Error: --set-default requires account ID", file=sys.stderr)
        sys.exit(1)

    set_default(args.account_id)


def cmd_get_default(args) -> None:
    """Print default account ID."""
    print(get_default_account_id())


def cmd_get_env(args) -> None:
    """Print environment variable exports."""
    try:
        print(get_env_export(args.account_id))
    except SystemExit:
        sys.exit(1)


def cmd_get_credentials(args) -> None:
    """Print credentials as JSON (for programmatic use)."""
    import json
    try:
        url, api_key = get_api_credentials(args.account_id)
        print(json.dumps({"url": url, "api_key": api_key}))
    except SystemExit:
        sys.exit(1)


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="n8n Configuration Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list-accounts              List all accounts
  %(prog)s --add local --url http://localhost:5679/api/v1 --key YOUR_KEY
  %(prog)s --set-default production     Set default account
  %(prog)s --get-env                    Get env vars for default account
  %(prog)s --get-env production         Get env vars for specific account
"""
    )

    # Action flags
    parser.add_argument("--list-accounts", action="store_true",
                        help="List all configured accounts")
    parser.add_argument("--add", dest="account_id", metavar="ID",
                        help="Add or update account with given ID")
    parser.add_argument("--remove", dest="remove_id", metavar="ID",
                        help="Remove account by ID")
    parser.add_argument("--set-default", dest="default_id", metavar="ID",
                        help="Set default account")
    parser.add_argument("--get-default", action="store_true",
                        help="Print default account ID")
    parser.add_argument("--get-env", nargs="?", const="", metavar="ACCOUNT",
                        help="Print env var exports for account")
    parser.add_argument("--get-credentials", nargs="?", const="", metavar="ACCOUNT",
                        help="Print credentials as JSON")

    # Account details (for --add)
    parser.add_argument("--url", help="n8n API URL")
    parser.add_argument("--key", help="n8n API key")
    parser.add_argument("--name", help="Display name for account")
    parser.add_argument("--description", help="Account description")

    args = parser.parse_args()

    # Route to appropriate command
    if args.list_accounts:
        cmd_list_accounts(args)
    elif args.account_id:
        cmd_add_account(args)
    elif args.remove_id:
        args.account_id = args.remove_id
        cmd_remove_account(args)
    elif args.default_id:
        args.account_id = args.default_id
        cmd_set_default(args)
    elif args.get_default:
        cmd_get_default(args)
    elif args.get_env is not None:
        args.account_id = args.get_env or None
        cmd_get_env(args)
    elif args.get_credentials is not None:
        args.account_id = args.get_credentials or None
        cmd_get_credentials(args)
    else:
        # Default: show accounts
        cmd_list_accounts(args)


if __name__ == "__main__":
    main()
