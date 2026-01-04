#!/usr/bin/env python3
"""
Amazon SP-API Authentication Module

Handles OAuth 2.0 via Login with Amazon (LWA):
- Access token acquisition and caching
- Automatic token refresh (1-hour expiry)
- Restricted Data Token (RDT) for PII access
- Multi-region endpoint selection
- AWS Signature V4 signing support
"""

import json
import time
import hashlib
import hmac
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

# LWA Token endpoint
LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"

# Regional SP-API endpoints
ENDPOINTS = {
    "NA": "https://sellingpartnerapi-na.amazon.com",
    "EU": "https://sellingpartnerapi-eu.amazon.com",
    "FE": "https://sellingpartnerapi-fe.amazon.com"
}

# AWS regions for signing
AWS_REGIONS = {
    "NA": "us-east-1",
    "EU": "eu-west-1",
    "FE": "us-west-2"
}

# Marketplace IDs by region
MARKETPLACES = {
    "NA": {
        "US": "ATVPDKIKX0DER",
        "CA": "A2EUQ1WTGCTBG2",
        "MX": "A1AM78C64UM0Y8",
        "BR": "A2Q3Y263D00KWC"
    },
    "EU": {
        "UK": "A1F83G8C2ARO7P",
        "GB": "A1F83G8C2ARO7P",  # Alias
        "DE": "A1PA6795UKMFR9",
        "FR": "A13V1IB3VIYZZH",
        "IT": "APJ6JRA9NG5V4",
        "ES": "A1RKKUPIHCS9HS",
        "NL": "A1805IZSGTT6HS",
        "SE": "A2NODRKZP88ZB9",
        "PL": "A1C3SOZRARQ6R3",
        "TR": "A33AVAJ2PDY3EV",
        "AE": "A2VIGQ35RCS4UG",
        "SA": "A17E79C6D8DWNP",
        "EG": "ARBP9OOSHTCHU",
        "IN": "A21TJRUUN4KGV",
        "BE": "AMEN7PMS3EDWL"
    },
    "FE": {
        "JP": "A1VC38T7YXB528",
        "AU": "A39IBJ37TRP1C6",
        "SG": "A19VAU5U5O7RUS"
    }
}

# Token cache file
TOKEN_CACHE_FILE = ".spapi_token_cache.json"


class SPAPIAuth:
    """Manages LWA OAuth tokens for SP-API access."""

    def __init__(self, config_path: Path = None, profile: str = None):
        """
        Initialize authentication manager.

        Args:
            config_path: Path to config file. Defaults to ../config/spapi_config.json
            profile: Profile name to use (defaults to config's default_profile)
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "spapi_config.json"
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._token_cache = self._load_token_cache()
        self._default_profile = profile  # Store profile for default usage

    def _load_config(self) -> dict:
        """Load configuration from file."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Config not found: {self.config_path}\n"
                f"Copy spapi_config.template.json to spapi_config.json and fill in credentials."
            )
        with open(self.config_path) as f:
            return json.load(f)

    def _get_token_cache_path(self) -> Path:
        """Get path to token cache file."""
        return self.config_path.parent / TOKEN_CACHE_FILE

    def _load_token_cache(self) -> dict:
        """Load token cache from file."""
        cache_path = self._get_token_cache_path()
        if cache_path.exists():
            try:
                with open(cache_path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_token_cache(self):
        """Save token cache to file."""
        cache_path = self._get_token_cache_path()
        with open(cache_path, "w") as f:
            json.dump(self._token_cache, f, indent=2)

    def get_profile(self, profile: str = None) -> str:
        """Get profile name, defaulting to configured default."""
        return profile or self._default_profile or self.config.get("default_profile", "production")

    def get_profile_config(self, profile: str = None) -> dict:
        """Get configuration for a specific profile."""
        profile = self.get_profile(profile)
        if profile not in self.config.get("profiles", {}):
            raise ValueError(f"Profile not found: {profile}")
        return self.config["profiles"][profile]

    def get_access_token(self, profile: str = None) -> str:
        """
        Get LWA access token, refreshing if needed.

        Args:
            profile: Profile name to use

        Returns:
            Valid access token string
        """
        profile = self.get_profile(profile)

        # Check cache (with 60-second buffer for expiry)
        cached = self._token_cache.get(profile)
        if cached and cached.get("expires_at", 0) > time.time() + 60:
            return cached["access_token"]

        # Refresh token
        creds = self.get_profile_config(profile)
        token_data = self._request_token(
            creds["lwa_client_id"],
            creds["lwa_client_secret"],
            creds["refresh_token"]
        )

        # Cache token
        self._token_cache[profile] = {
            "access_token": token_data["access_token"],
            "expires_at": time.time() + token_data.get("expires_in", 3600),
            "token_type": token_data.get("token_type", "bearer")
        }
        self._save_token_cache()

        return token_data["access_token"]

    def _request_token(self, client_id: str, client_secret: str,
                       refresh_token: str) -> dict:
        """
        Request new access token from LWA.

        Args:
            client_id: LWA client ID
            client_secret: LWA client secret
            refresh_token: LWA refresh token

        Returns:
            Token response dict with access_token, expires_in, token_type
        """
        data = urlencode({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret
        }).encode()

        req = Request(LWA_TOKEN_URL, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            raise RuntimeError(
                f"LWA token request failed: {e.code} {e.reason}\n{error_body}"
            )
        except URLError as e:
            raise RuntimeError(f"LWA token request failed: {e.reason}")

    def get_restricted_data_token(self, profile: str, path: str,
                                   data_elements: list,
                                   method: str = "GET") -> str:
        """
        Get Restricted Data Token for PII access.

        Required for accessing buyer info, shipping addresses, and other PII.

        Args:
            profile: Profile name to use
            path: API path requiring RDT (e.g., /orders/v0/orders/{orderId}/address)
            data_elements: List of data elements to access (e.g., ["shippingAddress", "buyerInfo"])
            method: HTTP method (GET, POST, etc.)

        Returns:
            Restricted Data Token string
        """
        access_token = self.get_access_token(profile)
        endpoint = self.get_endpoint(profile)

        url = f"{endpoint}/tokens/2021-03-01/restrictedDataToken"
        data = json.dumps({
            "restrictedResources": [{
                "method": method,
                "path": path,
                "dataElements": data_elements
            }]
        }).encode()

        req = Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Bearer {access_token}")
        req.add_header("Content-Type", "application/json")
        req.add_header("x-amz-access-token", access_token)

        try:
            with urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                return result["restrictedDataToken"]
        except HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            raise RuntimeError(
                f"RDT request failed: {e.code} {e.reason}\n{error_body}"
            )

    def get_endpoint(self, profile: str = None) -> str:
        """
        Get regional endpoint for profile.

        Args:
            profile: Profile name to use

        Returns:
            Regional SP-API endpoint URL
        """
        prof_config = self.get_profile_config(profile)
        region = prof_config.get("region", "NA")
        return ENDPOINTS.get(region, ENDPOINTS["NA"])

    def get_aws_region(self, profile: str = None) -> str:
        """
        Get AWS region for profile (used in request signing).

        Args:
            profile: Profile name to use

        Returns:
            AWS region string (e.g., us-east-1)
        """
        prof_config = self.get_profile_config(profile)
        region = prof_config.get("region", "NA")
        return AWS_REGIONS.get(region, AWS_REGIONS["NA"])

    def get_marketplace_id(self, profile: str = None,
                           marketplace: str = None) -> str:
        """
        Get marketplace ID for profile.

        Args:
            profile: Profile name to use
            marketplace: Override marketplace code (e.g., US, UK, DE)

        Returns:
            Amazon marketplace ID string
        """
        prof_config = self.get_profile_config(profile)
        region = prof_config.get("region", "NA")
        marketplace = marketplace or prof_config.get("marketplace", "US")

        region_marketplaces = MARKETPLACES.get(region, MARKETPLACES["NA"])
        marketplace_id = region_marketplaces.get(marketplace.upper())

        if not marketplace_id:
            raise ValueError(
                f"Unknown marketplace: {marketplace} in region {region}\n"
                f"Available: {list(region_marketplaces.keys())}"
            )

        return marketplace_id

    def get_selling_partner_id(self, profile: str = None) -> Optional[str]:
        """
        Get selling partner ID from profile config.

        Args:
            profile: Profile name to use

        Returns:
            Selling partner ID or None if not configured
        """
        prof_config = self.get_profile_config(profile)
        return prof_config.get("selling_partner_id")

    def list_profiles(self) -> list:
        """List available profiles."""
        return list(self.config.get("profiles", {}).keys())

    def get_token_info(self, profile: str = None) -> dict:
        """
        Get information about cached token for profile.

        Args:
            profile: Profile name to use

        Returns:
            Dict with token info (masked token, expiry, etc.)
        """
        profile = self.get_profile(profile)
        cached = self._token_cache.get(profile)

        if not cached:
            return {"status": "no_token", "profile": profile}

        expires_at = cached.get("expires_at", 0)
        expires_in = max(0, int(expires_at - time.time()))
        token = cached.get("access_token", "")

        return {
            "status": "valid" if expires_in > 0 else "expired",
            "profile": profile,
            "token_preview": f"{token[:10]}...{token[-10:]}" if len(token) > 20 else "***",
            "expires_in_seconds": expires_in,
            "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()
        }

    def clear_token_cache(self, profile: str = None):
        """
        Clear cached token(s).

        Args:
            profile: Profile to clear, or None to clear all
        """
        if profile:
            self._token_cache.pop(profile, None)
        else:
            self._token_cache = {}
        self._save_token_cache()


def _sign_request_v4(request: Request, access_key: str, secret_key: str,
                     region: str, service: str = "execute-api") -> Request:
    """
    Sign a request using AWS Signature Version 4.

    Note: Most SP-API calls use LWA tokens, but some operations
    (like certain upload operations) may require AWS SigV4.

    Args:
        request: urllib Request object to sign
        access_key: AWS access key ID
        secret_key: AWS secret access key
        region: AWS region
        service: AWS service name (default: execute-api)

    Returns:
        Request object with authorization headers added
    """
    # Get current time
    t = datetime.now(timezone.utc)
    amz_date = t.strftime('%Y%m%dT%H%M%SZ')
    date_stamp = t.strftime('%Y%m%d')

    # Parse request URL
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(request.full_url)
    host = parsed.netloc
    canonical_uri = parsed.path or '/'
    canonical_querystring = parsed.query or ''

    # Create canonical headers
    headers_to_sign = {
        'host': host,
        'x-amz-date': amz_date
    }
    signed_headers = ';'.join(sorted(headers_to_sign.keys()))
    canonical_headers = ''.join(
        f"{k}:{v}\n" for k, v in sorted(headers_to_sign.items())
    )

    # Create payload hash
    payload = request.data or b''
    payload_hash = hashlib.sha256(payload).hexdigest()

    # Create canonical request
    canonical_request = '\n'.join([
        request.method,
        canonical_uri,
        canonical_querystring,
        canonical_headers,
        signed_headers,
        payload_hash
    ])

    # Create string to sign
    algorithm = 'AWS4-HMAC-SHA256'
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = '\n'.join([
        algorithm,
        amz_date,
        credential_scope,
        hashlib.sha256(canonical_request.encode()).hexdigest()
    ])

    # Create signing key
    def sign(key, msg):
        return hmac.new(key, msg.encode(), hashlib.sha256).digest()

    k_date = sign(f"AWS4{secret_key}".encode(), date_stamp)
    k_region = sign(k_date, region)
    k_service = sign(k_region, service)
    k_signing = sign(k_service, "aws4_request")

    # Create signature
    signature = hmac.new(
        k_signing, string_to_sign.encode(), hashlib.sha256
    ).hexdigest()

    # Create authorization header
    authorization = (
        f"{algorithm} Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    # Add headers to request
    request.add_header('x-amz-date', amz_date)
    request.add_header('Authorization', authorization)

    return request


# CLI interface for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SP-API Authentication Manager")
    parser.add_argument("--profile", "-p", help="Profile to use")
    parser.add_argument("--config", "-c", help="Path to config file")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List profiles
    subparsers.add_parser("profiles", help="List available profiles")

    # Get token info
    subparsers.add_parser("info", help="Get token info for profile")

    # Test auth
    subparsers.add_parser("test", help="Test authentication")

    # Clear cache
    clear_parser = subparsers.add_parser("clear", help="Clear token cache")
    clear_parser.add_argument("--all", action="store_true", help="Clear all profiles")

    # Get marketplace ID
    mp_parser = subparsers.add_parser("marketplace", help="Get marketplace ID")
    mp_parser.add_argument("code", nargs="?", help="Marketplace code (e.g., US, UK)")

    args = parser.parse_args()

    try:
        config_path = Path(args.config) if args.config else None
        auth = SPAPIAuth(config_path)

        if args.command == "profiles":
            print("Available profiles:")
            for p in auth.list_profiles():
                default = " (default)" if p == auth.get_profile() else ""
                print(f"  - {p}{default}")

        elif args.command == "info":
            info = auth.get_token_info(args.profile)
            print(json.dumps(info, indent=2))

        elif args.command == "test":
            print(f"Testing authentication for profile: {auth.get_profile(args.profile)}")
            token = auth.get_access_token(args.profile)
            print(f"Success! Token: {token[:10]}...{token[-10:]}")
            print(f"Endpoint: {auth.get_endpoint(args.profile)}")
            print(f"Marketplace ID: {auth.get_marketplace_id(args.profile)}")

        elif args.command == "clear":
            if args.all:
                auth.clear_token_cache()
                print("Cleared all token caches")
            else:
                auth.clear_token_cache(args.profile)
                print(f"Cleared token cache for: {auth.get_profile(args.profile)}")

        elif args.command == "marketplace":
            mp_id = auth.get_marketplace_id(args.profile, args.code)
            print(f"Marketplace ID: {mp_id}")

        else:
            parser.print_help()

    except Exception as e:
        print(f"Error: {e}", file=__import__("sys").stderr)
        __import__("sys").exit(1)
