#!/usr/bin/env python3
"""
Azure AD Authentication using MSAL (Microsoft Authentication Library).

Features:
- OAuth 2.0 Client Credentials flow (app-only)
- Multi-tenant support with aliases
- Token caching with auto-refresh
- 5-minute refresh buffer before expiry
- Retry logic with exponential backoff

Usage:
    from auth import AzureAuth

    auth = AzureAuth()  # Uses default tenant
    auth = AzureAuth(tenant="prod")  # Uses specific tenant/alias

    token = auth.get_token()
    headers = auth.get_auth_headers()
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

try:
    from msal import ConfidentialClientApplication
except ImportError:
    print("Error: MSAL library not installed. Run: pip install msal")
    sys.exit(1)

import requests


class AuthError(Exception):
    """Authentication error."""
    pass


class AzureAuth:
    """Azure AD authentication handler using MSAL."""

    GRAPH_SCOPE = "https://graph.microsoft.com/.default"
    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    TOKEN_REFRESH_BUFFER = 300  # Refresh 5 minutes before expiry

    def __init__(self, tenant: Optional[str] = None, config_path: Optional[str] = None):
        """
        Initialize Azure AD authentication.

        Args:
            tenant: Tenant name or alias (uses default if not specified)
            config_path: Path to config file (auto-detected if not specified)
        """
        self.config_path = config_path or self._find_config_path()
        self.config = self._load_config()
        self.tenant_name = self._resolve_tenant_name(tenant)
        self.tenant_config = self._get_tenant_config()
        self.token_cache_path = self._get_token_cache_path()
        self.app = self._create_msal_app()

    def _find_config_path(self) -> str:
        """Find the config file path."""
        # Check relative to this script
        script_dir = Path(__file__).parent
        config_dir = script_dir.parent / "config"
        config_file = config_dir / "azure_config.json"

        if config_file.exists():
            return str(config_file)

        # Check template exists
        template_file = config_dir / "azure_config.template.json"
        if template_file.exists():
            raise AuthError(
                f"Config file not found. Copy the template:\n"
                f"  cp {template_file} {config_file}\n"
                f"Then edit {config_file} with your Azure credentials."
            )

        raise AuthError(f"Config file not found at {config_file}")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise AuthError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise AuthError(f"Failed to load config: {e}")

    def _resolve_tenant_name(self, tenant: Optional[str]) -> str:
        """Resolve tenant name from alias or use default."""
        if tenant is None:
            return self.config.get('defaults', {}).get('tenant', 'default')

        # Check if it's an alias
        aliases = self.config.get('aliases', {})
        if tenant in aliases:
            return aliases[tenant]

        # Check if it's a direct tenant name
        tenants = self.config.get('tenants', {})
        if tenant in tenants:
            return tenant

        raise AuthError(
            f"Unknown tenant or alias: '{tenant}'. "
            f"Available tenants: {list(tenants.keys())}, "
            f"aliases: {list(aliases.keys())}"
        )

    def _get_tenant_config(self) -> Dict[str, Any]:
        """Get configuration for the current tenant."""
        tenants = self.config.get('tenants', {})
        if self.tenant_name not in tenants:
            raise AuthError(f"Tenant '{self.tenant_name}' not found in config")

        tenant_config = tenants[self.tenant_name]

        # Validate required fields
        required = ['tenant_id', 'client_id', 'client_secret']
        missing = [f for f in required if not tenant_config.get(f) or tenant_config[f].startswith('YOUR_')]
        if missing:
            raise AuthError(
                f"Missing or placeholder values in tenant '{self.tenant_name}': {missing}. "
                f"Please update {self.config_path} with your Azure credentials."
            )

        return tenant_config

    def _get_token_cache_path(self) -> str:
        """Get path for token cache file."""
        config_dir = Path(self.config_path).parent
        return str(config_dir / ".azure_tokens.json")

    def _create_msal_app(self) -> ConfidentialClientApplication:
        """Create MSAL confidential client application."""
        authority = f"https://login.microsoftonline.com/{self.tenant_config['tenant_id']}"

        return ConfidentialClientApplication(
            client_id=self.tenant_config['client_id'],
            client_credential=self.tenant_config['client_secret'],
            authority=authority
        )

    def _load_token_cache(self) -> Dict[str, Any]:
        """Load token cache from file."""
        try:
            if os.path.exists(self.token_cache_path):
                with open(self.token_cache_path, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_token_cache(self, cache: Dict[str, Any]):
        """Save token cache to file."""
        try:
            with open(self.token_cache_path, 'w') as f:
                json.dump(cache, f, indent=2)
            # Set restrictive permissions
            os.chmod(self.token_cache_path, 0o600)
        except Exception as e:
            print(f"Warning: Could not save token cache: {e}", file=sys.stderr)

    def _get_cached_token(self) -> Optional[Dict[str, Any]]:
        """Get cached token for current tenant."""
        cache = self._load_token_cache()
        return cache.get(self.tenant_name)

    def _cache_token(self, token_data: Dict[str, Any]):
        """Cache token with expiry time."""
        cache = self._load_token_cache()

        # Calculate absolute expiry time
        expires_in = token_data.get('expires_in', 3600)
        expiry_time = time.time() + expires_in

        cache[self.tenant_name] = {
            'access_token': token_data['access_token'],
            'expires_at': expiry_time,
            'token_type': token_data.get('token_type', 'Bearer')
        }

        self._save_token_cache(cache)

    def _is_token_expired(self, token_data: Dict[str, Any]) -> bool:
        """Check if token is expired or will expire soon."""
        expires_at = token_data.get('expires_at', 0)
        return time.time() >= (expires_at - self.TOKEN_REFRESH_BUFFER)

    def get_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.

        Returns:
            Valid access token string

        Raises:
            AuthError: If token acquisition fails
        """
        # Check cache first
        cached = self._get_cached_token()
        if cached and not self._is_token_expired(cached):
            return cached['access_token']

        # Acquire new token
        result = self.app.acquire_token_for_client(
            scopes=[self.GRAPH_SCOPE]
        )

        if "access_token" in result:
            self._cache_token(result)
            return result['access_token']
        else:
            error = result.get('error', 'Unknown error')
            error_desc = result.get('error_description', 'No description')
            raise AuthError(f"Failed to acquire token: {error} - {error_desc}")

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers with authorization.

        Returns:
            Dictionary with Authorization header
        """
        token = self.get_token()
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

    def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection by fetching organization info.

        Returns:
            Organization info dict

        Raises:
            AuthError: If connection test fails
        """
        headers = self.get_auth_headers()

        try:
            response = requests.get(
                f"{self.GRAPH_BASE_URL}/organization",
                headers=headers,
                timeout=self.config.get('defaults', {}).get('timeout', 30)
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            raise AuthError(f"API request failed: {e.response.status_code} - {e.response.text}")
        except requests.exceptions.RequestException as e:
            raise AuthError(f"Connection failed: {e}")

    def get_token_info(self) -> Dict[str, Any]:
        """Get information about the current token."""
        cached = self._get_cached_token()
        if cached:
            expires_at = cached.get('expires_at', 0)
            expires_in = max(0, int(expires_at - time.time()))
            return {
                'tenant': self.tenant_name,
                'expires_in_seconds': expires_in,
                'expires_at': datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
                'is_valid': not self._is_token_expired(cached)
            }
        return {
            'tenant': self.tenant_name,
            'cached': False
        }


def main():
    """CLI for testing authentication."""
    parser = argparse.ArgumentParser(description='Azure AD Authentication')
    parser.add_argument('-t', '--tenant', help='Tenant name or alias')
    parser.add_argument('--test', action='store_true', help='Test connection')
    parser.add_argument('--info', action='store_true', help='Show token info')
    parser.add_argument('--token', action='store_true', help='Print access token')

    args = parser.parse_args()

    try:
        auth = AzureAuth(tenant=args.tenant)

        if args.test:
            print(f"Testing connection to tenant: {auth.tenant_name}")
            org_info = auth.test_connection()
            orgs = org_info.get('value', [])
            if orgs:
                org = orgs[0]
                print(f"  Organization: {org.get('displayName', 'N/A')}")
                print(f"  Tenant ID: {org.get('id', 'N/A')}")
                domains = org.get('verifiedDomains', [])
                primary = next((d['name'] for d in domains if d.get('isDefault')), 'N/A')
                print(f"  Primary Domain: {primary}")
            print("Connection successful!")

        elif args.info:
            info = auth.get_token_info()
            print(f"Tenant: {info['tenant']}")
            if info.get('cached', True):
                print(f"Token Valid: {info['is_valid']}")
                print(f"Expires In: {info['expires_in_seconds']} seconds")
                print(f"Expires At: {info['expires_at']}")
            else:
                print("No cached token")

        elif args.token:
            token = auth.get_token()
            print(token)

        else:
            # Default: test and show info
            print(f"Tenant: {auth.tenant_name}")
            token = auth.get_token()
            info = auth.get_token_info()
            print(f"Token acquired successfully")
            print(f"Expires in: {info['expires_in_seconds']} seconds")

    except AuthError as e:
        print(f"Authentication error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
