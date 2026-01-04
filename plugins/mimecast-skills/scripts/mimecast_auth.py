#!/usr/bin/env python3
"""
Mimecast Authentication Helper

Supports both OAuth 2.0 and Legacy HMAC-SHA1 authentication for Mimecast API.
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from datetime import datetime
from email.utils import formatdate
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

# Configuration paths
SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
CONFIG_FILE = CONFIG_DIR / "mimecast_config.json"
TEMPLATE_FILE = CONFIG_DIR / "mimecast_config.template.json"
TOKEN_CACHE_FILE = CONFIG_DIR / ".mimecast_token_cache.json"

# Regional base URLs for Legacy API (HMAC-SHA1)
REGIONAL_URLS_LEGACY = {
    "us": "https://us-api.mimecast.com",
    "eu": "https://eu-api.mimecast.com",
    "de": "https://de-api.mimecast.com",
    "au": "https://au-api.mimecast.com",
    "za": "https://za-api.mimecast.com",
    "ca": "https://ca-api.mimecast.com",
    "uk": "https://uk-api.mimecast.com",
    "sandbox": "https://sandbox-api.mimecast.com"
}

# Regional base URLs for OAuth 2.0 API (API 2.0)
REGIONAL_URLS_OAUTH = {
    "us": "https://us-api.services.mimecast.com",
    "eu": "https://eu-api.services.mimecast.com",
    "de": "https://de-api.services.mimecast.com",
    "au": "https://au-api.services.mimecast.com",
    "za": "https://za-api.services.mimecast.com",
    "ca": "https://ca-api.services.mimecast.com",
    "uk": "https://uk-api.services.mimecast.com",
    "global": "https://api.services.mimecast.com",
    "sandbox": "https://sandbox-api.services.mimecast.com"
}

# Combined for display purposes
REGIONAL_URLS = REGIONAL_URLS_LEGACY


class MimecastAuth:
    """Mimecast authentication handler supporting OAuth 2.0 and Legacy HMAC."""

    def __init__(self, config_path: str = None, profile: str = None):
        """
        Initialize authentication with config file.

        Args:
            config_path: Path to config file (default: config/mimecast_config.json)
            profile: Profile name to use (default: from config default_profile)
        """
        self.config_path = Path(config_path) if config_path else CONFIG_FILE
        self.config = self._load_config()
        self.profile_name = profile or self.config.get("default_profile", "production")
        self.profile = self._get_profile(self.profile_name)
        self._token_cache = None

    def _load_config(self) -> dict:
        """Load configuration from config file."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found at {self.config_path}\n"
                f"Copy {TEMPLATE_FILE.name} to {CONFIG_FILE.name} and add your credentials."
            )

        with open(self.config_path) as f:
            return json.load(f)

    def _get_profile(self, profile_name: str) -> dict:
        """Get profile configuration."""
        profiles = self.config.get("profiles", {})

        if profile_name not in profiles:
            available = list(profiles.keys())
            raise ValueError(
                f"Profile '{profile_name}' not found. Available profiles: {available}"
            )

        return profiles[profile_name]

    @property
    def auth_type(self) -> str:
        """Determine authentication type based on available credentials."""
        if self.profile.get("client_id") and self.profile.get("client_secret"):
            return "oauth2"
        elif self.profile.get("access_key") and self.profile.get("secret_key"):
            return "hmac"
        else:
            raise ValueError("No valid credentials found. Need either OAuth 2.0 (client_id/client_secret) or Legacy (access_key/secret_key)")

    @property
    def base_url(self) -> str:
        """Get base URL for the configured profile based on auth type."""
        # For OAuth 2.0, use API 2.0 endpoints
        if self.auth_type == "oauth2":
            if "oauth_base_url" in self.profile:
                return self.profile["oauth_base_url"]
            region = self.profile.get("region", "us").lower()
            return REGIONAL_URLS_OAUTH.get(region, REGIONAL_URLS_OAUTH["global"])

        # For Legacy HMAC, use API 1.0 endpoints
        if "base_url" in self.profile:
            return self.profile["base_url"]
        region = self.profile.get("region", "us").lower()
        return REGIONAL_URLS_LEGACY.get(region, REGIONAL_URLS_LEGACY["us"])

    # ==================== OAuth 2.0 Authentication ====================

    def _load_token_cache(self) -> dict:
        """Load cached OAuth token."""
        if self._token_cache:
            return self._token_cache

        if TOKEN_CACHE_FILE.exists():
            try:
                with open(TOKEN_CACHE_FILE) as f:
                    self._token_cache = json.load(f)
                    return self._token_cache
            except (json.JSONDecodeError, IOError):
                pass

        return {}

    def _save_token_cache(self, token_data: dict):
        """Save OAuth token to cache."""
        self._token_cache = token_data
        try:
            with open(TOKEN_CACHE_FILE, 'w') as f:
                json.dump(token_data, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not cache token: {e}", file=sys.stderr)

    def _get_oauth_token(self, force_refresh: bool = False) -> str:
        """
        Get OAuth 2.0 access token, using cache if valid.

        Args:
            force_refresh: Force token refresh even if cached token is valid

        Returns:
            Access token string
        """
        cache_key = f"{self.profile_name}_token"
        cache = self._load_token_cache()

        # Check if cached token is still valid (with 5 min buffer)
        if not force_refresh and cache_key in cache:
            token_data = cache[cache_key]
            expires_at = token_data.get("expires_at", 0)
            if time.time() < (expires_at - 300):  # 5 min buffer
                return token_data["access_token"]

        # Request new token from OAuth 2.0 endpoint
        token_url = f"{self.base_url}/oauth/token"

        # Prepare credentials - Mimecast OAuth 2.0 sends credentials in body
        client_id = self.profile["client_id"]
        client_secret = self.profile["client_secret"]

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Send client_id, client_secret, and grant_type in request body
        body = urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials"
        }).encode()

        try:
            req = Request(token_url, data=body, headers=headers, method='POST')
            with urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode())

                # Cache the token
                token_data = {
                    "access_token": result["access_token"],
                    "token_type": result.get("token_type", "Bearer"),
                    "expires_in": result.get("expires_in", 3600),
                    "expires_at": time.time() + result.get("expires_in", 3600)
                }
                cache[cache_key] = token_data
                self._save_token_cache(cache)

                return result["access_token"]

        except HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            raise ValueError(f"OAuth token request failed ({e.code}): {error_body}")
        except URLError as e:
            raise ValueError(f"OAuth token request failed: {e.reason}")

    def get_oauth_headers(self) -> dict:
        """Get headers for OAuth 2.0 authenticated request."""
        access_token = self._get_oauth_token()
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    # ==================== Legacy HMAC-SHA1 Authentication ====================

    def generate_hmac_signature(self, uri: str) -> dict:
        """
        Generate HMAC-SHA1 signature headers for Mimecast API request.

        Args:
            uri: API endpoint URI (e.g., /api/account/get-account)

        Returns:
            dict: Headers dictionary with authorization and required Mimecast headers
        """
        # Generate timestamp and request ID
        date_header = formatdate(localtime=True)
        request_id = str(uuid.uuid4())

        # Build data to sign
        data_to_sign = f"{date_header}\n{request_id}\n{uri}\n{self.profile['app_key']}"

        # Create HMAC-SHA1 signature
        secret_key = base64.b64decode(self.profile['secret_key'])
        hmac_sha1 = hmac.new(
            secret_key,
            data_to_sign.encode('utf-8'),
            digestmod=hashlib.sha1
        )
        signature = base64.b64encode(hmac_sha1.digest()).decode('utf-8')

        # Build authorization header
        authorization = f"MC {self.profile['access_key']}:{signature}"

        return {
            'Authorization': authorization,
            'x-mc-date': date_header,
            'x-mc-req-id': request_id,
            'x-mc-app-id': self.profile['app_id'],
            'Content-Type': 'application/json'
        }

    # ==================== Unified Interface ====================

    def get_headers(self, uri: str = None) -> dict:
        """
        Get authentication headers based on auth type.

        Args:
            uri: API endpoint URI (required for HMAC auth)

        Returns:
            Headers dictionary
        """
        if self.auth_type == "oauth2":
            return self.get_oauth_headers()
        else:
            if not uri:
                raise ValueError("URI required for HMAC authentication")
            return self.generate_hmac_signature(uri)

    def refresh_token(self):
        """Force refresh OAuth token."""
        if self.auth_type == "oauth2":
            self._get_oauth_token(force_refresh=True)
            print("Token refreshed successfully.")
        else:
            print("HMAC authentication does not use tokens.")


def load_config() -> dict:
    """Load configuration from config file (standalone function)."""
    if not CONFIG_FILE.exists():
        print(f"Error: Configuration file not found at {CONFIG_FILE}", file=sys.stderr)
        print(f"Copy {TEMPLATE_FILE.name} to {CONFIG_FILE.name} and add your credentials.", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_FILE) as f:
        return json.load(f)


def test_api_credentials(auth: MimecastAuth) -> dict:
    """Test API credentials by trying multiple endpoints until one succeeds."""
    # Try multiple endpoints based on common product assignments
    test_endpoints = [
        ("/api/domain/get-internal-domain", "Domain Management"),
        ("/api/directory/get-group", "Directory Management"),
        ("/api/account/get-account", "Account"),
    ]

    last_error = None
    last_details = ""

    for test_uri, product_name in test_endpoints:
        url = f"{auth.base_url}{test_uri}"
        headers = auth.get_headers(test_uri)
        data = json.dumps({"data": []}).encode('utf-8')

        try:
            req = Request(url, data=data, headers=headers, method='POST')
            with urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode())
                response_data = result.get("data", [{}])[0] if result.get("data") else {}
                return {
                    "valid": True,
                    "status": response.status,
                    "auth_type": auth.auth_type,
                    "endpoint": test_uri,
                    "product": product_name,
                    "account_code": response_data.get("accountCode", "N/A"),
                    "account_name": response_data.get("accountName", "N/A"),
                    "domain": response_data.get("domain", "N/A"),
                    "region": response_data.get("region", "N/A")
                }
        except HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            try:
                error_json = json.loads(error_body)
                fail_msg = error_json.get("fail", [{}])[0].get("message", e.reason)
            except:
                fail_msg = e.reason

            # If it's a 403 (forbidden), try the next endpoint
            if e.code == 403 and "app_forbidden" in error_body:
                last_error = fail_msg
                last_details = error_body[:500]
                continue

            # For other errors, return immediately
            return {
                "valid": False,
                "status": e.code,
                "auth_type": auth.auth_type,
                "error": fail_msg,
                "details": error_body[:500]
            }
        except URLError as e:
            return {
                "valid": False,
                "status": None,
                "auth_type": auth.auth_type,
                "error": str(e.reason)
            }
        except Exception as e:
            return {
                "valid": False,
                "status": None,
                "auth_type": auth.auth_type,
                "error": str(e)
            }

    # If we get here, all endpoints failed with 403
    return {
        "valid": False,
        "status": 403,
        "auth_type": auth.auth_type,
        "error": last_error or "All test endpoints returned 403 Forbidden",
        "details": last_details
    }


def cmd_test(args):
    """Test API credentials validity."""
    try:
        auth = MimecastAuth(profile=args.profile)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    profile = auth.profile
    print(f"Testing credentials for: {profile.get('name', args.profile or 'default')}")
    print(f"Base URL: {auth.base_url}")
    print(f"Auth Type: {auth.auth_type.upper()}")
    print(f"Region: {profile.get('region', 'us').upper()}")

    result = test_api_credentials(auth)

    if result["valid"]:
        print(f"\nCredentials: VALID")
        print(f"Status: {result['status']}")
        print(f"Test Endpoint: {result.get('endpoint', 'N/A')}")
        print(f"Product: {result.get('product', 'N/A')}")
        if result.get('domain') and result['domain'] != 'N/A':
            print(f"Domain: {result['domain']}")
        if result.get('account_code') and result['account_code'] != 'N/A':
            print(f"Account Code: {result['account_code']}")
        if result.get('account_name') and result['account_name'] != 'N/A':
            print(f"Account Name: {result['account_name']}")
        if result.get('region') and result['region'] != 'N/A':
            print(f"Region: {result['region']}")
    else:
        print(f"\nCredentials: INVALID")
        print(f"Status: {result['status']}")
        print(f"Error: {result['error']}")
        if result.get("details"):
            print(f"Details: {result['details'][:200]}")

        # Check for app_forbidden error (OAuth app missing API products)
        if "app_forbidden" in str(result.get("details", "")):
            print("\n" + "=" * 60)
            print("OAuth Token Works, but API Access Denied")
            print("=" * 60)
            print("\nYour OAuth 2.0 credentials are valid (token acquired),")
            print("but the application needs API products assigned.")
            print("\nTo fix this:")
            print("1. Log in to Mimecast Administration Console")
            print("2. Go to: Administration → Services → API and Platform Integrations")
            print("3. Find your OAuth 2.0 application")
            print("4. Click 'Edit' and assign the required API products:")
            print("   - Account (for account info)")
            print("   - Email Security (for message tracking, TTP)")
            print("   - Directory (for user/group management)")
            print("   - Policy (for policy management)")
            print("   - Audit (for reporting)")
            print("\nAfter assigning products, run this test again.")
        sys.exit(1)


def cmd_info(args):
    """Show configuration information."""
    config = load_config()
    profiles = config.get("profiles", {})
    profile_name = args.profile or config.get("default_profile", "production")

    if profile_name not in profiles:
        print(f"Error: Profile '{profile_name}' not found.", file=sys.stderr)
        sys.exit(1)

    profile = profiles[profile_name]

    print(f"Profile: {profile.get('name', profile_name)}")
    print(f"Region: {profile.get('region', 'us').upper()}")

    # Get base URL
    if "base_url" in profile:
        base_url = profile["base_url"]
    else:
        region = profile.get("region", "us").lower()
        base_url = REGIONAL_URLS.get(region, REGIONAL_URLS["us"])
    print(f"Base URL: {base_url}")

    # Determine auth type
    if profile.get("client_id") and profile.get("client_secret"):
        print(f"Auth Type: OAuth 2.0")
        # Show masked credentials
        for key in ["client_id", "client_secret"]:
            value = profile.get(key, "")
            if value and not value.startswith("YOUR_"):
                masked = value[:8] + "..." + value[-4:] if len(value) > 16 else "****"
                print(f"  {key}: {masked}")
            else:
                print(f"  {key}: NOT CONFIGURED")
    else:
        print(f"Auth Type: Legacy HMAC")
        for key in ["app_id", "app_key", "access_key", "secret_key"]:
            value = profile.get(key, "")
            if value and not value.startswith("YOUR_"):
                masked = value[:8] + "..." + value[-4:] if len(value) > 16 else "****"
                print(f"  {key}: {masked}")
            else:
                print(f"  {key}: NOT CONFIGURED")

    print(f"\nAvailable Profiles: {list(profiles.keys())}")
    print(f"Default Profile: {config.get('default_profile', 'production')}")


def cmd_refresh(args):
    """Refresh OAuth token."""
    try:
        auth = MimecastAuth(profile=args.profile)
        auth.refresh_token()
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_token(args):
    """Get OAuth token (token acquisition test)."""
    try:
        auth = MimecastAuth(profile=args.profile)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if auth.auth_type != "oauth2":
        print("Token command only works with OAuth 2.0 authentication.")
        print("Your profile is configured for Legacy HMAC authentication.")
        sys.exit(1)

    print(f"Profile: {auth.profile.get('name', args.profile or 'default')}")
    print(f"Base URL: {auth.base_url}")
    print(f"Token URL: {auth.base_url}/oauth/token")

    try:
        token = auth._get_oauth_token(force_refresh=True)
        # Show masked token
        masked = token[:20] + "..." + token[-10:] if len(token) > 40 else token[:10] + "..."
        print(f"\nToken acquired successfully!")
        print(f"Access Token: {masked}")
        print(f"Token Length: {len(token)} characters")

        # Show cache info
        cache = auth._load_token_cache()
        cache_key = f"{auth.profile_name}_token"
        if cache_key in cache:
            token_data = cache[cache_key]
            expires_in = int(token_data.get("expires_at", 0) - time.time())
            print(f"Expires in: {expires_in} seconds ({expires_in // 60} minutes)")
    except ValueError as e:
        print(f"\nToken acquisition FAILED")
        print(f"Error: {e}")
        sys.exit(1)


def cmd_regions(args):
    """List available regional endpoints."""
    print("Available Mimecast Regional Endpoints:")
    print("-" * 50)
    for region, url in sorted(REGIONAL_URLS.items()):
        print(f"  {region.upper():10} {url}")


def main():
    parser = argparse.ArgumentParser(
        description="Mimecast API Authentication Helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --test                        # Test API credentials
  %(prog)s --info                        # Show configuration
  %(prog)s --refresh                     # Refresh OAuth token
  %(prog)s --test --profile sandbox      # Test sandbox profile
  %(prog)s --regions                     # List regional endpoints
        """
    )

    parser.add_argument("--test", "-t", action="store_true",
                        help="Test API credentials validity")
    parser.add_argument("--info", "-i", action="store_true",
                        help="Show configuration info")
    parser.add_argument("--refresh", "-r", action="store_true",
                        help="Refresh OAuth token")
    parser.add_argument("--token", action="store_true",
                        help="Test OAuth token acquisition")
    parser.add_argument("--regions", action="store_true",
                        help="List available regional endpoints")
    parser.add_argument("--profile", "-p", default=None,
                        help="Profile to use (default: from config)")

    args = parser.parse_args()

    if args.test:
        cmd_test(args)
    elif args.info:
        cmd_info(args)
    elif args.refresh:
        cmd_refresh(args)
    elif args.token:
        cmd_token(args)
    elif args.regions:
        cmd_regions(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
