#!/usr/bin/env python3
"""
Atlassian OAuth 2.0 Authentication Module

Handles token management with automatic refresh for Atlassian Cloud APIs.
Supports multiple sites with alias resolution.
"""

import json
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

# Default config location
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / 'config' / 'atlassian_config.json'

# Token refresh buffer (refresh 5 minutes before expiry)
TOKEN_REFRESH_BUFFER = 300

# Site aliases for convenience
SITE_ALIASES = {
    'twx': 'twistedx',
    'twistedx': 'twistedx',
    'dm': 'dutyman',
    'dutyman': 'dutyman'
}


class AtlassianAuthError(Exception):
    """Authentication error with Atlassian APIs."""
    pass


class AtlassianAuth:
    """
    Manages OAuth 2.0 authentication for Atlassian Cloud APIs.

    Features:
    - Automatic token refresh before expiry
    - Multi-site support with aliases
    - Token caching to avoid unnecessary refreshes
    """

    def __init__(self, config_path=None):
        """
        Initialize authentication handler.

        Args:
            config_path: Path to config file. Defaults to config/atlassian_config.json
        """
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.config = self._load_config()
        self._token_cache = {}  # site -> {token, expiry}

    def _load_config(self):
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            raise AtlassianAuthError(
                f"Config file not found: {self.config_path}\n"
                f"Please copy config/atlassian_config.template.json to config/atlassian_config.json "
                f"and fill in your OAuth credentials."
            )

        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise AtlassianAuthError(f"Invalid JSON in config file: {e}")

    def resolve_site(self, alias):
        """
        Resolve site alias to canonical name.

        Args:
            alias: Site alias (e.g., 'twx', 'dm')

        Returns:
            Canonical site name
        """
        if alias is None:
            alias = self.config.get('defaults', {}).get('site', 'twistedx')
        return SITE_ALIASES.get(alias.lower(), alias.lower())

    def get_site_config(self, site_alias=None):
        """
        Get configuration for a specific site.

        Args:
            site_alias: Site alias or None for default

        Returns:
            Dict with site config (cloud_id, domain, name)
        """
        site = self.resolve_site(site_alias)
        sites = self.config.get('sites', {})

        if site not in sites:
            available = ', '.join(sites.keys())
            raise AtlassianAuthError(
                f"Unknown site: {site}. Available sites: {available}"
            )

        return sites[site]

    def get_token(self, site_alias=None):
        """
        Get valid access token, refreshing if needed.

        Args:
            site_alias: Site alias or None for default

        Returns:
            Valid access token string
        """
        site = self.resolve_site(site_alias)

        # Check cache
        cached = self._token_cache.get(site)
        if cached and time.time() < cached['expiry'] - TOKEN_REFRESH_BUFFER:
            return cached['token']

        # Need to refresh
        return self._refresh_token(site)

    def _refresh_token(self, site):
        """
        Refresh access token using refresh token.

        Args:
            site: Canonical site name

        Returns:
            New access token
        """
        oauth = self.config.get('oauth', {})

        if not all(k in oauth for k in ['client_id', 'client_secret', 'refresh_token']):
            raise AtlassianAuthError(
                "Missing OAuth credentials in config. Required: client_id, client_secret, refresh_token"
            )

        data = urlencode({
            'grant_type': 'refresh_token',
            'client_id': oauth['client_id'],
            'client_secret': oauth['client_secret'],
            'refresh_token': oauth['refresh_token']
        }).encode('utf-8')

        req = Request(
            'https://auth.atlassian.com/oauth/token',
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
            except:
                error_msg = error_body or str(e)
            raise AtlassianAuthError(f"Token refresh failed: {error_msg}")
        except URLError as e:
            raise AtlassianAuthError(f"Network error during token refresh: {e}")

        # Extract token and expiry
        access_token = result.get('access_token')
        expires_in = result.get('expires_in', 3600)

        if not access_token:
            raise AtlassianAuthError("No access_token in refresh response")

        # Update cache
        self._token_cache[site] = {
            'token': access_token,
            'expiry': time.time() + expires_in
        }

        # If we got a new refresh token, update config
        if 'refresh_token' in result and result['refresh_token'] != oauth['refresh_token']:
            self._update_refresh_token(result['refresh_token'])

        return access_token

    def _update_refresh_token(self, new_token):
        """Update refresh token in config file (Atlassian rotates tokens)."""
        self.config['oauth']['refresh_token'] = new_token
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            # Non-fatal - just log warning
            print(f"Warning: Could not save new refresh token: {e}")

    def get_headers(self, site_alias=None):
        """
        Get authentication headers for API requests.

        Args:
            site_alias: Site alias or None for default

        Returns:
            Dict of headers including Authorization
        """
        token = self.get_token(site_alias)
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def get_cloud_id(self, site_alias=None):
        """
        Get cloud ID for a site.

        Args:
            site_alias: Site alias or None for default

        Returns:
            Cloud ID string
        """
        site_config = self.get_site_config(site_alias)
        return site_config['cloud_id']

    def get_domain(self, site_alias=None):
        """
        Get domain for a site.

        Args:
            site_alias: Site alias or None for default

        Returns:
            Domain string (e.g., 'twistedx.atlassian.net')
        """
        site_config = self.get_site_config(site_alias)
        return site_config['domain']

    def list_sites(self):
        """
        List available sites.

        Returns:
            List of (alias, name, domain) tuples
        """
        sites = self.config.get('sites', {})
        return [
            (alias, config.get('name', alias), config.get('domain', 'unknown'))
            for alias, config in sites.items()
        ]


def create_config_template():
    """Create a template config file."""
    template = {
        "sites": {
            "twistedx": {
                "name": "Twisted X",
                "cloud_id": "YOUR_CLOUD_ID",
                "domain": "twistedx.atlassian.net"
            }
        },
        "oauth": {
            "client_id": "YOUR_CLIENT_ID",
            "client_secret": "YOUR_CLIENT_SECRET",
            "refresh_token": "YOUR_REFRESH_TOKEN"
        },
        "defaults": {
            "site": "twistedx"
        }
    }
    return json.dumps(template, indent=2)


if __name__ == '__main__':
    # Test authentication
    import sys

    try:
        auth = AtlassianAuth()
        print("Available sites:")
        for alias, name, domain in auth.list_sites():
            print(f"  {alias}: {name} ({domain})")

        print("\nTesting token refresh...")
        token = auth.get_token()
        print(f"Token obtained: {token[:20]}...")
        print("Authentication successful!")

    except AtlassianAuthError as e:
        print(f"Authentication error: {e}", file=sys.stderr)
        sys.exit(1)
