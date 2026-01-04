#!/usr/bin/env python3
"""
n8n Authentication Helper

Test API connectivity and display account information.

Usage:
    python3 n8n_auth.py --test [--account <id>]
    python3 n8n_auth.py --info
"""

import argparse
import json
import sys
from pathlib import Path

# Import from same directory
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from n8n_config import get_api_credentials, list_accounts, get_default_account_id
from n8n_api import check_health, N8nClient


def test_connection(account_id: str = None) -> dict:
    """Test API connection and return status."""
    try:
        url, api_key = get_api_credentials(account_id)

        # Mask API key for display
        masked_key = api_key[:20] + "..." if len(api_key) > 20 else api_key[:5] + "..."

        result = check_health(account_id)

        return {
            "account": account_id or get_default_account_id(),
            "url": url,
            "api_key_preview": masked_key,
            "connected": result.get("healthy", False),
            "workflows": result.get("workflows", {}),
            "error": result.get("error") if not result.get("healthy") else None
        }
    except SystemExit:
        return {
            "account": account_id or "default",
            "connected": False,
            "error": "Configuration error - check account settings"
        }
    except Exception as e:
        return {
            "account": account_id or "default",
            "connected": False,
            "error": str(e)
        }


def cmd_test(args) -> None:
    """Test connection to n8n."""
    result = test_connection(args.account)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\nn8n Connection Test")
        print("=" * 50)
        print(f"Account: {result.get('account')}")
        print(f"URL: {result.get('url', 'N/A')}")
        print(f"API Key: {result.get('api_key_preview', 'N/A')}")
        print(f"Connected: {'Yes' if result.get('connected') else 'No'}")

        if result.get("connected"):
            wf = result.get("workflows", {})
            print(f"\nWorkflows:")
            print(f"  Total: {wf.get('total', 0)}")
            print(f"  Active: {wf.get('active', 0)}")
            print(f"  Inactive: {wf.get('inactive', 0)}")
            print(f"\nConnection successful!")
        else:
            print(f"\nError: {result.get('error')}")
            print("\nTroubleshooting:")
            print("1. Verify n8n is running")
            print("2. Check API key in n8n Settings > API")
            print("3. Verify URL includes /api/v1")
            sys.exit(1)


def cmd_info(args) -> None:
    """Show configuration info."""
    accounts = list_accounts()
    default = get_default_account_id()

    if args.json:
        print(json.dumps({
            "default_account": default,
            "accounts": accounts
        }, indent=2))
    else:
        print(f"\nn8n Configuration Info")
        print("=" * 50)
        print(f"Default Account: {default}")
        print(f"Total Accounts: {len(accounts)}")

        for acct in accounts:
            status = "Configured" if acct.get("configured") else "Needs API key"
            default_marker = " (default)" if acct.get("is_default") else ""

            print(f"\n{acct.get('id')}{default_marker}")
            print(f"  Name: {acct.get('name')}")
            print(f"  URL: {acct.get('url')}")
            print(f"  Status: {status}")


def cmd_test_all(args) -> None:
    """Test all configured accounts."""
    accounts = list_accounts()

    print(f"\nTesting {len(accounts)} account(s)...")
    print("=" * 50)

    results = []
    for acct in accounts:
        result = test_connection(acct.get("id"))
        results.append(result)

        status = "OK" if result.get("connected") else "FAILED"
        print(f"{acct.get('id')}: {status}")

    if args.json:
        print(json.dumps(results, indent=2))

    # Summary
    connected = sum(1 for r in results if r.get("connected"))
    print(f"\nSummary: {connected}/{len(results)} accounts connected")


def main():
    parser = argparse.ArgumentParser(
        description="n8n Authentication Helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --test                 Test default account connection
  %(prog)s --test --account prod  Test specific account
  %(prog)s --info                 Show configuration info
  %(prog)s --test-all             Test all accounts
"""
    )

    parser.add_argument("--test", action="store_true", help="Test connection")
    parser.add_argument("--test-all", action="store_true", help="Test all accounts")
    parser.add_argument("--info", action="store_true", help="Show config info")
    parser.add_argument("--account", "-a", help="Account ID")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.test_all:
        cmd_test_all(args)
    elif args.test:
        cmd_test(args)
    elif args.info:
        cmd_info(args)
    else:
        # Default: test connection
        cmd_test(args)


if __name__ == "__main__":
    main()
