#!/usr/bin/env python3
"""
Shopify OAuth Token Manager

Handles OAuth 2.0 client credentials flow for Shopify Admin API.
Tokens expire after 24 hours (86399 seconds).

Usage:
    # Get new access token
    python3 shopify_auth.py --get-token

    # Get token for specific store
    python3 shopify_auth.py --get-token --store my-store

    # Test current token
    python3 shopify_auth.py --test

    # Show token info (without exposing full token)
    python3 shopify_auth.py --info
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

# Config paths
SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
CONFIG_FILE = CONFIG_DIR / "shopify_config.json"
TOKEN_CACHE_FILE = CONFIG_DIR / ".shopify_tokens.json"


def load_config():
    """Load configuration from shopify_config.json"""
    if not CONFIG_FILE.exists():
        template = CONFIG_DIR / "shopify_config.template.json"
        print(f"Error: Config file not found at {CONFIG_FILE}")
        print(f"Copy the template and fill in your credentials:")
        print(f"  cp {template} {CONFIG_FILE}")
        sys.exit(1)

    with open(CONFIG_FILE) as f:
        return json.load(f)


def load_token_cache():
    """Load cached tokens"""
    if TOKEN_CACHE_FILE.exists():
        with open(TOKEN_CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_token_cache(cache):
    """Save tokens to cache file"""
    with open(TOKEN_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)
    # Secure the file
    os.chmod(TOKEN_CACHE_FILE, 0o600)


def get_access_token(config, store_key=None):
    """
    Exchange client credentials for access token.

    Args:
        config: Configuration dict
        store_key: Store identifier (uses default if not specified)

    Returns:
        dict with access_token, scope, expires_in, expires_at
    """
    store_key = store_key or config["defaults"]["store"]
    store = config["stores"].get(store_key)

    if not store:
        print(f"Error: Store '{store_key}' not found in config")
        print(f"Available stores: {list(config['stores'].keys())}")
        sys.exit(1)

    shop_domain = store["shop_domain"]
    client_id = config["oauth"]["client_id"]
    client_secret = config["oauth"]["client_secret"]

    # Prepare request
    url = f"https://{shop_domain}/admin/oauth/access_token"
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    print(f"Requesting token for {shop_domain}...")

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

            # Add expiration timestamp
            expires_at = datetime.now() + timedelta(seconds=result["expires_in"])
            result["expires_at"] = expires_at.isoformat()
            result["store"] = store_key

            # Cache the token
            cache = load_token_cache()
            cache[store_key] = result
            save_token_cache(cache)

            print(f"Token obtained successfully!")
            print(f"  Scopes: {result['scope']}")
            print(f"  Expires: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")

            return result

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"Error: HTTP {e.code}")
        try:
            error_json = json.loads(error_body)
            print(f"  {error_json.get('error', 'Unknown error')}")
            print(f"  {error_json.get('error_description', '')}")
        except:
            print(f"  {error_body}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Network error - {e.reason}")
        sys.exit(1)


def get_cached_token(store_key=None):
    """
    Get cached token if still valid (with 1 hour buffer).

    Returns:
        Token dict if valid, None if expired or not found
    """
    config = load_config()
    store_key = store_key or config["defaults"]["store"]
    cache = load_token_cache()

    if store_key not in cache:
        return None

    token_data = cache[store_key]
    expires_at = datetime.fromisoformat(token_data["expires_at"])

    # Check if token expires within 1 hour
    if datetime.now() + timedelta(hours=1) > expires_at:
        return None

    return token_data


def test_token(store_key=None):
    """Test if current token is valid by making a simple API call"""
    config = load_config()
    store_key = store_key or config["defaults"]["store"]
    store = config["stores"].get(store_key)

    token_data = get_cached_token(store_key)
    if not token_data:
        print("No valid cached token. Run --get-token first.")
        sys.exit(1)

    shop_domain = store["shop_domain"]
    api_version = store.get("api_version", "2024-10")

    # Simple shop query
    url = f"https://{shop_domain}/admin/api/{api_version}/graphql.json"
    query = '{"query": "{ shop { name } }"}'

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": token_data["access_token"]
    }

    try:
        req = urllib.request.Request(url, data=query.encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

            if "errors" in result:
                print(f"Token invalid: {result['errors']}")
                sys.exit(1)

            shop_name = result.get("data", {}).get("shop", {}).get("name", "Unknown")
            print(f"Token valid! Connected to: {shop_name}")
            return True

    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("Token expired or invalid. Run --get-token to refresh.")
        else:
            print(f"Error: HTTP {e.code}")
        sys.exit(1)


def show_token_info(store_key=None):
    """Show token information without exposing the full token"""
    config = load_config()
    store_key = store_key or config["defaults"]["store"]
    token_data = get_cached_token(store_key)

    if not token_data:
        cache = load_token_cache()
        if store_key in cache:
            token_data = cache[store_key]
            expired = True
        else:
            print(f"No token found for store '{store_key}'")
            sys.exit(1)
    else:
        expired = False

    token = token_data["access_token"]
    masked_token = f"{token[:10]}...{token[-4:]}"
    expires_at = datetime.fromisoformat(token_data["expires_at"])

    print(f"Store: {store_key}")
    print(f"Token: {masked_token}")
    print(f"Scopes: {token_data['scope']}")
    print(f"Expires: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Status: {'EXPIRED' if expired else 'Valid'}")


def main():
    parser = argparse.ArgumentParser(
        description="Shopify OAuth Token Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --get-token              Get new access token for default store
  %(prog)s --get-token --store xyz  Get token for specific store
  %(prog)s --test                   Test if current token is valid
  %(prog)s --info                   Show token info (masked)
        """
    )

    parser.add_argument("--get-token", action="store_true", help="Get new access token")
    parser.add_argument("--test", action="store_true", help="Test current token validity")
    parser.add_argument("--info", action="store_true", help="Show token info")
    parser.add_argument("--store", type=str, help="Store identifier")
    parser.add_argument("--token", action="store_true", help="Output just the token (for scripts)")

    args = parser.parse_args()

    if args.get_token:
        config = load_config()
        get_access_token(config, args.store)
    elif args.test:
        test_token(args.store)
    elif args.info:
        show_token_info(args.store)
    elif args.token:
        # Just output the token for piping to other commands
        token_data = get_cached_token(args.store)
        if token_data:
            print(token_data["access_token"])
        else:
            config = load_config()
            result = get_access_token(config, args.store)
            print(result["access_token"])
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
