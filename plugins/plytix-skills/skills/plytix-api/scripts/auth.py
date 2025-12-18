#!/usr/bin/env python3
"""
Plytix Authentication Module

Handles API Key + Password → Access Token authentication for Plytix PIM API.
Supports multi-account configuration with automatic token caching.
"""

import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Default config location
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / 'config' / 'plytix_config.json'

# Persistent token cache location (survives restarts)
TOKEN_CACHE_PATH = Path(__file__).parent.parent / 'config' / '.plytix_tokens.json'

# Token refresh buffer (refresh 5 minutes before expiry)
TOKEN_REFRESH_BUFFER = 300

# Default token expiry if not provided (1 hour)
DEFAULT_TOKEN_EXPIRY = 3600

# Retry settings for token acquisition
TOKEN_RETRIES = 3
TOKEN_BACKOFF = 1.0  # Base backoff in seconds


class PlytixAuthError(Exception):
    """Authentication error with Plytix APIs."""
    pass


class PlytixAuth:
    """
    Manages API Key + Password authentication for Plytix PIM API.

    Authentication Flow:
    1. Load API key and password from config
    2. POST to auth endpoint to get access token
    3. Cache token with expiry time
    4. Auto-refresh before expiry

    Features:
    - Automatic token refresh before expiry
    - Multi-account support with aliases
    - Persistent token caching
    """

    def __init__(self, config_path=None):
        """
        Initialize authentication handler.

        Args:
            config_path: Path to config file. Defaults to config/plytix_config.json
        """
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.config = self._load_config()
        self._validate_config()
        self._token_cache = self._load_token_cache()

    def _load_config(self):
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            raise PlytixAuthError(
                f"Config file not found: {self.config_path}\n"
                f"Please copy config/plytix_config.template.json to config/plytix_config.json "
                f"and fill in your API credentials."
            )

        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise PlytixAuthError(f"Invalid JSON in config file: {e}")

    def _validate_config(self):
        """
        Validate config has required fields.

        Raises:
            PlytixAuthError: If required fields are missing
        """
        errors = []

        # Check accounts section
        if 'accounts' not in self.config:
            errors.append("Missing section: accounts")
        elif not self.config['accounts']:
            errors.append("No accounts configured in 'accounts' section")
        else:
            # Validate each account
            for name, account in self.config['accounts'].items():
                for field in ['api_url', 'auth_url', 'api_key', 'api_password']:
                    if field not in account or not account[field]:
                        errors.append(f"Missing or empty: accounts.{name}.{field}")

        # Check defaults section
        if 'defaults' not in self.config:
            errors.append("Missing section: defaults")
        elif 'account' not in self.config.get('defaults', {}):
            errors.append("Missing: defaults.account")

        if errors:
            raise PlytixAuthError(
                "Invalid config file:\n" + "\n".join(f"  - {e}" for e in errors) +
                "\n\nSee README.md for configuration instructions."
            )

    def _load_token_cache(self):
        """Load persistent token cache from disk."""
        if TOKEN_CACHE_PATH.exists():
            try:
                with open(TOKEN_CACHE_PATH, 'r') as f:
                    cache = json.load(f)
                    # Validate cache structure and remove expired entries
                    valid_cache = {}
                    current_time = time.time()
                    for account, data in cache.items():
                        if isinstance(data, dict) and 'token' in data and 'expiry' in data:
                            # Keep if not expired (with buffer)
                            if data['expiry'] > current_time + TOKEN_REFRESH_BUFFER:
                                valid_cache[account] = data
                    return valid_cache
            except (json.JSONDecodeError, IOError):
                # Cache is corrupted, start fresh
                pass
        return {}

    def _save_token_cache(self):
        """Save token cache to disk for persistence."""
        try:
            # Ensure directory exists
            TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            # Write atomically
            temp_path = TOKEN_CACHE_PATH.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(self._token_cache, f, indent=2)
            temp_path.replace(TOKEN_CACHE_PATH)
        except IOError as e:
            # Non-fatal - just log warning
            print(f"Warning: Could not save token cache: {e}", file=sys.stderr)

    def resolve_account(self, alias):
        """
        Resolve account alias to canonical name.

        Args:
            alias: Account alias (e.g., 'prod', 'stg')

        Returns:
            Canonical account name
        """
        if alias is None:
            alias = self.config.get('defaults', {}).get('account', 'production')

        aliases = self.config.get('aliases', {})
        return aliases.get(alias.lower(), alias.lower())

    def get_account_config(self, account_alias=None):
        """
        Get configuration for a specific account.

        Args:
            account_alias: Account alias or None for default

        Returns:
            Dict with account config (api_url, auth_url, api_key, api_password)
        """
        account = self.resolve_account(account_alias)
        accounts = self.config.get('accounts', {})

        if account not in accounts:
            available = ', '.join(accounts.keys())
            raise PlytixAuthError(
                f"Unknown account: {account}. Available accounts: {available}"
            )

        return accounts[account]

    def get_token(self, account_alias=None):
        """
        Get valid access token, refreshing if needed.

        Args:
            account_alias: Account alias or None for default

        Returns:
            Valid access token string
        """
        account = self.resolve_account(account_alias)

        # Check cache (both in-memory and persistent)
        cached = self._token_cache.get(account)
        if cached and time.time() < cached['expiry'] - TOKEN_REFRESH_BUFFER:
            return cached['token']

        # Need to get new token - use retry mechanism
        token = self._get_token_with_retry(account)

        # Save cache to disk for persistence
        self._save_token_cache()

        return token

    def _get_token_with_retry(self, account, retries=None, backoff=None):
        """
        Get access token with retry logic for transient failures.

        Args:
            account: Canonical account name
            retries: Number of retries (default: TOKEN_RETRIES)
            backoff: Base backoff time in seconds (default: TOKEN_BACKOFF)

        Returns:
            New access token
        """
        retries = retries if retries is not None else TOKEN_RETRIES
        backoff = backoff if backoff is not None else TOKEN_BACKOFF

        last_error = None
        for attempt in range(retries):
            try:
                return self._do_get_token(account)
            except PlytixAuthError as e:
                error_str = str(e).lower()
                # Permanent failures - don't retry
                if 'invalid' in error_str and ('key' in error_str or 'credential' in error_str):
                    raise PlytixAuthError(
                        f"Authentication failed: {e}\n\n"
                        f"Your API credentials are invalid.\n"
                        f"Check your config file: {self.config_path}\n"
                        f"Get new credentials from: accounts.plytix.com"
                    )
                if '401' in error_str or 'unauthorized' in error_str:
                    raise PlytixAuthError(
                        f"Authentication failed: {e}\n\n"
                        f"Your API key or password is incorrect.\n"
                        f"Check your credentials at: accounts.plytix.com"
                    )
                # Transient failures - retry with backoff
                last_error = e
                if attempt < retries - 1:
                    sleep_time = backoff * (2 ** attempt)
                    time.sleep(sleep_time)

        raise last_error

    def _do_get_token(self, account):
        """
        Perform the actual token acquisition request.

        Args:
            account: Canonical account name

        Returns:
            New access token
        """
        account_config = self.get_account_config(account)

        data = json.dumps({
            'api_key': account_config['api_key'],
            'api_password': account_config['api_password']
        }).encode('utf-8')

        req = Request(
            account_config['auth_url'],
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )

        try:
            with urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
        except HTTPError as e:
            error_body = e.read().decode('utf-8')
            try:
                error_json = json.loads(error_body)
                error_msg = error_json.get('message', error_json.get('error', str(e)))
            except (json.JSONDecodeError, KeyError, TypeError):
                error_msg = error_body[:500] if error_body else str(e)
            raise PlytixAuthError(f"Token acquisition failed ({e.code}): {error_msg}")
        except URLError as e:
            raise PlytixAuthError(f"Network error during authentication: {e}")

        # Extract token and expiry
        # Plytix returns: {"data": [{"access_token": "...", ...}]}
        data_section = result.get('data', result)
        # Handle both list and dict response formats
        if isinstance(data_section, list) and len(data_section) > 0:
            data_section = data_section[0]
        access_token = data_section.get('access_token') if isinstance(data_section, dict) else None

        if not access_token:
            raise PlytixAuthError(f"No access_token in response: {result}")

        # Use expires_in if provided, otherwise default
        expires_in = data_section.get('expires_in', DEFAULT_TOKEN_EXPIRY)

        # Update cache
        self._token_cache[account] = {
            'token': access_token,
            'expiry': time.time() + expires_in,
            'obtained_at': time.time()
        }

        return access_token

    def get_headers(self, account_alias=None):
        """
        Get authentication headers for API requests.

        Args:
            account_alias: Account alias or None for default

        Returns:
            Dict of headers including Authorization
        """
        token = self.get_token(account_alias)
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def get_api_url(self, account_alias=None):
        """
        Get API base URL for an account.

        Args:
            account_alias: Account alias or None for default

        Returns:
            API base URL string
        """
        account_config = self.get_account_config(account_alias)
        return account_config['api_url']

    def list_accounts(self):
        """
        List available accounts.

        Returns:
            List of (alias, name, api_url) tuples
        """
        accounts = self.config.get('accounts', {})
        return [
            (alias, config.get('name', alias), config.get('api_url', 'unknown'))
            for alias, config in accounts.items()
        ]

    def get_default_account(self):
        """Get the default account name."""
        return self.config.get('defaults', {}).get('account', 'production')

    def clear_cache(self, account_alias=None):
        """
        Clear cached token(s).

        Args:
            account_alias: Specific account to clear, or None for all
        """
        if account_alias:
            account = self.resolve_account(account_alias)
            self._token_cache.pop(account, None)
        else:
            self._token_cache.clear()
        self._save_token_cache()

    def test_connection(self, account_alias=None):
        """
        Test connection by attempting to get a token.

        Args:
            account_alias: Account to test or None for default

        Returns:
            True if successful

        Raises:
            PlytixAuthError: If connection fails
        """
        self.clear_cache(account_alias)
        token = self.get_token(account_alias)
        return bool(token)


def create_config_template():
    """Create a template config file."""
    template = {
        "accounts": {
            "production": {
                "name": "Production",
                "api_url": "https://pim.plytix.com/api/v1",
                "auth_url": "https://auth.plytix.com/api/v1/auth/api_key",
                "api_key": "YOUR_API_KEY",
                "api_password": "YOUR_API_PASSWORD"
            }
        },
        "defaults": {
            "account": "production",
            "timeout": 30,
            "max_retries": 3
        },
        "aliases": {
            "prod": "production"
        }
    }
    return json.dumps(template, indent=2)


if __name__ == '__main__':
    # Test authentication
    import argparse

    parser = argparse.ArgumentParser(description='Plytix Authentication Helper')
    parser.add_argument('--account', '-a', help='Account alias to use')
    parser.add_argument('--test', action='store_true', help='Test authentication')
    parser.add_argument('--list', action='store_true', help='List accounts')
    parser.add_argument('--clear-cache', action='store_true', help='Clear token cache')
    parser.add_argument('--token', action='store_true', help='Print current token')
    args = parser.parse_args()

    try:
        auth = PlytixAuth()

        if args.list:
            print("Available accounts:")
            for alias, name, url in auth.list_accounts():
                default = " (default)" if alias == auth.get_default_account() else ""
                print(f"  {alias}: {name}{default}")
                print(f"    API: {url}")
            sys.exit(0)

        if args.clear_cache:
            auth.clear_cache(args.account)
            print("Token cache cleared.")
            sys.exit(0)

        if args.test:
            print(f"Testing authentication for account: {args.account or auth.get_default_account()}")
            if auth.test_connection(args.account):
                print("Authentication successful!")
            sys.exit(0)

        if args.token:
            token = auth.get_token(args.account)
            print(token)
            sys.exit(0)

        # Default: show status
        print("Plytix Authentication Status")
        print("=" * 40)
        print(f"Config file: {auth.config_path}")
        print(f"Default account: {auth.get_default_account()}")
        print("\nAvailable accounts:")
        for alias, name, url in auth.list_accounts():
            cached = auth._token_cache.get(alias)
            if cached:
                remaining = int(cached['expiry'] - time.time())
                status = f"cached ({remaining}s remaining)" if remaining > 0 else "expired"
            else:
                status = "not cached"
            print(f"  {alias}: {name} [{status}]")

    except PlytixAuthError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
