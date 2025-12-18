#!/usr/bin/env python3
"""
NinjaOne OAuth 2.0 Authentication Module

Handles OAuth2 client credentials flow for NinjaOne RMM API.
Supports token caching with automatic refresh before expiry.
"""

import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

# Default config location
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / 'config' / 'ninjaone_config.json'

# Persistent token cache location (survives restarts)
TOKEN_CACHE_PATH = Path(__file__).parent.parent / 'config' / '.ninjaone_tokens.json'

# Token refresh buffer (refresh 5 minutes before expiry)
TOKEN_REFRESH_BUFFER = 300

# Default token expiry if not provided (1 hour)
DEFAULT_TOKEN_EXPIRY = 3600

# Retry settings for token acquisition
TOKEN_RETRIES = 3
TOKEN_BACKOFF = 1.0  # Base backoff in seconds


class NinjaOneAuthError(Exception):
    """Authentication error with NinjaOne APIs."""
    pass


class NinjaOneAuth:
    """
    Manages OAuth 2.0 Client Credentials authentication for NinjaOne API.

    Authentication Flow:
    1. Load client_id and client_secret from config
    2. POST to OAuth token endpoint with client credentials
    3. Cache access token with expiry time
    4. Auto-refresh before expiry

    Features:
    - Automatic token refresh before expiry
    - Persistent token caching
    - Retry logic with exponential backoff
    """

    def __init__(self, config_path=None):
        """
        Initialize authentication handler.

        Args:
            config_path: Path to config file. Defaults to config/ninjaone_config.json
        """
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.config = self._load_config()
        self._validate_config()
        self._token_cache = self._load_token_cache()

    def _load_config(self):
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            raise NinjaOneAuthError(
                f"Config file not found: {self.config_path}\n"
                f"Please copy config/ninjaone_config.template.json to config/ninjaone_config.json "
                f"and fill in your OAuth credentials."
            )

        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise NinjaOneAuthError(f"Invalid JSON in config file: {e}")

    def _validate_config(self):
        """
        Validate config has required fields.

        Raises:
            NinjaOneAuthError: If required fields are missing
        """
        errors = []

        # Check instance section
        if 'instance' not in self.config:
            errors.append("Missing section: instance")
        else:
            instance = self.config['instance']
            for field in ['api_url', 'client_id', 'client_secret']:
                if field not in instance or not instance[field]:
                    errors.append(f"Missing or empty: instance.{field}")

        if errors:
            raise NinjaOneAuthError(
                "Invalid config file:\n" + "\n".join(f"  - {e}" for e in errors) +
                "\n\nSee README.md for configuration instructions."
            )

    def _load_token_cache(self):
        """Load persistent token cache from disk."""
        if TOKEN_CACHE_PATH.exists():
            try:
                with open(TOKEN_CACHE_PATH, 'r') as f:
                    cache = json.load(f)
                    # Validate cache structure
                    if isinstance(cache, dict) and 'token' in cache and 'expiry' in cache:
                        # Check if not expired (with buffer)
                        if cache['expiry'] > time.time() + TOKEN_REFRESH_BUFFER:
                            return cache
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

    def get_token(self):
        """
        Get valid access token, refreshing if needed.

        Returns:
            Valid access token string
        """
        # Check cache
        if self._token_cache and time.time() < self._token_cache.get('expiry', 0) - TOKEN_REFRESH_BUFFER:
            return self._token_cache['token']

        # Need to get new token - use retry mechanism
        token = self._get_token_with_retry()

        # Save cache to disk for persistence
        self._save_token_cache()

        return token

    def _get_token_with_retry(self, retries=None, backoff=None):
        """
        Get access token with retry logic for transient failures.

        Args:
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
                return self._do_get_token()
            except NinjaOneAuthError as e:
                error_str = str(e).lower()
                # Permanent failures - don't retry
                if 'invalid_client' in error_str or 'invalid_grant' in error_str:
                    raise NinjaOneAuthError(
                        f"Authentication failed: {e}\n\n"
                        f"Your client credentials are invalid.\n"
                        f"Check your config file: {self.config_path}\n"
                        f"Verify client_id and client_secret in NinjaOne admin portal."
                    )
                if '401' in error_str or 'unauthorized' in error_str:
                    raise NinjaOneAuthError(
                        f"Authentication failed: {e}\n\n"
                        f"Your credentials are incorrect or expired.\n"
                        f"Create new API application in NinjaOne: Administration → Apps → API"
                    )
                # Transient failures - retry with backoff
                last_error = e
                if attempt < retries - 1:
                    sleep_time = backoff * (2 ** attempt)
                    time.sleep(sleep_time)

        raise last_error

    def _do_get_token(self):
        """
        Perform the actual token acquisition request.

        Returns:
            New access token
        """
        instance = self.config.get('instance', {})
        api_url = instance.get('api_url', 'https://app.ninjarmm.com')
        scopes = instance.get('scopes', ['monitoring', 'management', 'control'])

        # OAuth2 client credentials grant
        data = urlencode({
            'grant_type': 'client_credentials',
            'client_id': instance['client_id'],
            'client_secret': instance['client_secret'],
            'scope': ' '.join(scopes)
        }).encode('utf-8')

        token_url = f"{api_url.rstrip('/')}/oauth/token"

        req = Request(
            token_url,
            data=data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
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
                error_msg = error_json.get('error_description', error_json.get('error', str(e)))
            except (json.JSONDecodeError, KeyError, TypeError):
                error_msg = error_body[:500] if error_body else str(e)
            raise NinjaOneAuthError(f"Token acquisition failed ({e.code}): {error_msg}")
        except URLError as e:
            raise NinjaOneAuthError(f"Network error during authentication: {e}")

        # Extract token and expiry
        access_token = result.get('access_token')
        expires_in = result.get('expires_in', DEFAULT_TOKEN_EXPIRY)

        if not access_token:
            raise NinjaOneAuthError(f"No access_token in response: {result}")

        # Update cache
        self._token_cache = {
            'token': access_token,
            'expiry': time.time() + expires_in,
            'obtained_at': time.time(),
            'token_type': result.get('token_type', 'Bearer'),
            'scope': result.get('scope', '')
        }

        return access_token

    def get_headers(self):
        """
        Get authentication headers for API requests.

        Returns:
            Dict of headers including Authorization
        """
        token = self.get_token()
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def get_api_url(self):
        """
        Get API base URL.

        Returns:
            API base URL string
        """
        return self.config.get('instance', {}).get('api_url', 'https://app.ninjarmm.com')

    def get_instance_name(self):
        """Get the instance name from config."""
        return self.config.get('instance', {}).get('name', 'NinjaOne')

    def get_defaults(self):
        """Get default settings from config."""
        return self.config.get('defaults', {
            'timeout': 30,
            'max_retries': 3,
            'page_size': 100
        })

    def clear_cache(self):
        """Clear cached token."""
        self._token_cache = {}
        self._save_token_cache()

    def test_connection(self):
        """
        Test connection by attempting to get a token.

        Returns:
            True if successful

        Raises:
            NinjaOneAuthError: If connection fails
        """
        self.clear_cache()
        token = self.get_token()
        return bool(token)

    def get_token_info(self):
        """
        Get information about the current cached token.

        Returns:
            Dict with token info or None if no valid token
        """
        if not self._token_cache:
            return None

        expiry = self._token_cache.get('expiry', 0)
        remaining = int(expiry - time.time())

        return {
            'valid': remaining > 0,
            'expires_in': max(0, remaining),
            'token_type': self._token_cache.get('token_type', 'Bearer'),
            'scope': self._token_cache.get('scope', ''),
            'obtained_at': self._token_cache.get('obtained_at')
        }


def create_config_template():
    """Create a template config file."""
    template = {
        "instance": {
            "name": "NinjaOne",
            "api_url": "https://app.ninjarmm.com",
            "client_id": "YOUR_CLIENT_ID",
            "client_secret": "YOUR_CLIENT_SECRET",
            "scopes": ["monitoring", "management", "control"]
        },
        "defaults": {
            "timeout": 30,
            "max_retries": 3,
            "page_size": 100
        }
    }
    return json.dumps(template, indent=2)


if __name__ == '__main__':
    # Test authentication
    import argparse

    parser = argparse.ArgumentParser(description='NinjaOne Authentication Helper')
    parser.add_argument('--test', action='store_true', help='Test authentication')
    parser.add_argument('--clear-cache', action='store_true', help='Clear token cache')
    parser.add_argument('--token', action='store_true', help='Print current token')
    parser.add_argument('--info', action='store_true', help='Show token info')
    args = parser.parse_args()

    try:
        auth = NinjaOneAuth()

        if args.clear_cache:
            auth.clear_cache()
            print("Token cache cleared.")
            sys.exit(0)

        if args.test:
            print(f"Testing authentication for: {auth.get_instance_name()}")
            print(f"API URL: {auth.get_api_url()}")
            if auth.test_connection():
                print("Authentication successful!")
                token_info = auth.get_token_info()
                if token_info:
                    print(f"Token expires in: {token_info['expires_in']}s")
                    print(f"Scopes: {token_info['scope']}")
            sys.exit(0)

        if args.token:
            token = auth.get_token()
            print(token)
            sys.exit(0)

        if args.info:
            token_info = auth.get_token_info()
            if token_info:
                print(f"Valid: {token_info['valid']}")
                print(f"Expires in: {token_info['expires_in']}s")
                print(f"Token type: {token_info['token_type']}")
                print(f"Scopes: {token_info['scope']}")
            else:
                print("No cached token. Run --test to obtain one.")
            sys.exit(0)

        # Default: show status
        print("NinjaOne Authentication Status")
        print("=" * 40)
        print(f"Config file: {auth.config_path}")
        print(f"Instance: {auth.get_instance_name()}")
        print(f"API URL: {auth.get_api_url()}")

        token_info = auth.get_token_info()
        if token_info and token_info['valid']:
            print(f"\nToken: cached ({token_info['expires_in']}s remaining)")
            print(f"Scopes: {token_info['scope']}")
        else:
            print("\nToken: not cached or expired")
            print("Run with --test to test authentication")

    except NinjaOneAuthError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
