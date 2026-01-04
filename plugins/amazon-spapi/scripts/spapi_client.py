#!/usr/bin/env python3
"""
Amazon SP-API HTTP Client

Features:
- Rate limiting with per-resource quotas
- Exponential backoff with jitter
- Request retry logic
- Response handling and error classification
- Support for both LWA tokens and RDT tokens
"""

import json
import time
import random
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timezone

# Rate limits by API resource (requests per second)
# These are conservative defaults - actual limits vary by operation
RATE_LIMITS = {
    # Vendor APIs (generally higher limits)
    "vendorOrders": 10,
    "vendorShipments": 10,
    "vendorInvoices": 10,
    "vendorTransactionStatus": 10,

    # Orders API (very restrictive for getOrders)
    "orders": 0.0167,  # 1 per minute for getOrders
    "orders.getOrder": 0.5,
    "orders.getOrderItems": 0.5,

    # Catalog APIs
    "catalogItems": 5,
    "listingsItems": 5,
    "productTypeDefinitions": 5,

    # Reports & Feeds
    "reports": 0.0167,  # 1 per minute for createReport
    "reports.getReport": 2,
    "reports.getReports": 0.0222,  # ~80 per hour
    "feeds": 0.0167,
    "feeds.getFeed": 2,

    # Other APIs
    "notifications": 1,
    "pricing": 0.5,
    "finances": 0.5,
    "fbaInventory": 2,
    "tokens": 1,
    "aplusContent": 10,

    # Default fallback
    "default": 1.0
}

# Retry configuration
MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0  # seconds
MAX_BACKOFF = 120.0  # seconds
JITTER_FACTOR = 0.5  # Add up to 50% random jitter


class RateLimiter:
    """
    Token bucket rate limiter for API throttling.

    Tracks request rates per API resource and enforces delays
    when necessary to stay within rate limits.
    """

    def __init__(self):
        self._buckets: Dict[str, dict] = {}
        self._last_request_times: Dict[str, float] = {}

    def wait(self, api: str, rate: float = None):
        """
        Wait if necessary to respect rate limit.

        Args:
            api: API resource identifier
            rate: Requests per second (overrides default for api)
        """
        if rate is None:
            rate = RATE_LIMITS.get(api, RATE_LIMITS["default"])

        if rate <= 0:
            return

        now = time.time()
        min_interval = 1.0 / rate

        # Get last request time for this API
        last_time = self._last_request_times.get(api, 0)
        elapsed = now - last_time

        # Wait if we're requesting too fast
        if elapsed < min_interval:
            wait_time = min_interval - elapsed
            time.sleep(wait_time)

        self._last_request_times[api] = time.time()

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            "tracked_apis": list(self._last_request_times.keys()),
            "bucket_count": len(self._buckets)
        }


class SPAPIError(Exception):
    """Exception for SP-API errors."""

    def __init__(self, status_code: int, message: str, error_code: str = None,
                 details: str = None, response: dict = None):
        self.status_code = status_code
        self.message = message
        self.error_code = error_code
        self.details = details
        self.response = response or {}
        super().__init__(f"[{status_code}] {error_code or 'Error'}: {message}")

    def is_retryable(self) -> bool:
        """Check if this error is retryable."""
        return self.status_code in (429, 500, 502, 503, 504)

    def is_rate_limited(self) -> bool:
        """Check if this is a rate limit error."""
        return self.status_code == 429


class SPAPIClient:
    """
    HTTP client for Amazon Selling Partner API.

    Provides methods for making API requests with automatic:
    - Rate limiting
    - Retry with exponential backoff
    - Error handling
    - Token management
    """

    def __init__(self, auth, profile: str = None, timeout: int = 30):
        """
        Initialize SP-API client.

        Args:
            auth: SPAPIAuth instance for token management
            profile: Profile name to use (defaults to auth default)
            timeout: Request timeout in seconds
        """
        self.auth = auth
        self.profile = profile
        self.timeout = timeout
        self.rate_limiter = RateLimiter()

        # Request statistics
        self._stats = {
            "requests": 0,
            "retries": 0,
            "rate_limits_hit": 0,
            "errors": 0
        }

    def request(self, method: str, path: str,
                api_name: str = "default",
                params: Dict = None,
                data: Dict = None,
                use_rdt: bool = False,
                rdt_path: str = None,
                rdt_elements: List[str] = None,
                rate_limit: float = None,
                extra_headers: Dict = None) -> Tuple[int, Any]:
        """
        Make API request with rate limiting and retry.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            path: API path (e.g., /vendor/orders/v1/purchaseOrders)
            api_name: API resource name for rate limiting
            params: Query parameters dict
            data: Request body dict (will be JSON encoded)
            use_rdt: Whether to use Restricted Data Token
            rdt_path: Path for RDT request (defaults to request path)
            rdt_elements: Data elements for RDT (e.g., ["shippingAddress"])
            rate_limit: Override rate limit for this request
            extra_headers: Additional headers to include

        Returns:
            Tuple of (status_code, response_data)

        Raises:
            SPAPIError: On non-retryable errors after all retries exhausted
        """
        self._stats["requests"] += 1

        # Build URL
        endpoint = self.auth.get_endpoint(self.profile)
        url = f"{endpoint}{path}"

        # Add query parameters
        if params:
            # Filter out None values
            params = {k: v for k, v in params.items() if v is not None}
            if params:
                # Handle list parameters (some APIs use comma-separated)
                encoded_params = []
                for k, v in params.items():
                    if isinstance(v, (list, tuple)):
                        v = ",".join(str(x) for x in v)
                    encoded_params.append(f"{quote(str(k))}={quote(str(v))}")
                url += "?" + "&".join(encoded_params)

        # Get appropriate token
        if use_rdt and rdt_elements:
            token = self.auth.get_restricted_data_token(
                self.profile,
                rdt_path or path,
                rdt_elements,
                method
            )
        else:
            token = self.auth.get_access_token(self.profile)

        # Build headers
        headers = {
            "Authorization": f"Bearer {token}",
            "x-amz-access-token": token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "SPAPI-Python-Client/1.0"
        }

        if extra_headers:
            headers.update(extra_headers)

        # Encode body
        body = json.dumps(data).encode() if data else None

        # Retry loop with exponential backoff
        last_error = None
        for attempt in range(MAX_RETRIES):
            # Apply rate limiting
            self.rate_limiter.wait(api_name, rate_limit)

            try:
                req = Request(url, data=body, headers=headers, method=method)

                with urlopen(req, timeout=self.timeout) as resp:
                    content = resp.read().decode()
                    response_data = json.loads(content) if content else {}

                    # Check for API-level errors in successful response
                    if "errors" in response_data and response_data["errors"]:
                        error = response_data["errors"][0]
                        raise SPAPIError(
                            status_code=resp.status,
                            message=error.get("message", "Unknown error"),
                            error_code=error.get("code"),
                            details=error.get("details"),
                            response=response_data
                        )

                    return resp.status, response_data

            except HTTPError as e:
                status = e.code
                error_body = ""
                try:
                    error_body = e.read().decode() if e.fp else ""
                except:
                    pass

                # Parse error response
                try:
                    error_response = json.loads(error_body) if error_body else {}
                except json.JSONDecodeError:
                    error_response = {"raw": error_body}

                # Extract error details
                errors = error_response.get("errors", [])
                error_info = errors[0] if errors else {}
                error_code = error_info.get("code", "UnknownError")
                error_message = error_info.get("message", e.reason)

                last_error = SPAPIError(
                    status_code=status,
                    message=error_message,
                    error_code=error_code,
                    details=error_info.get("details"),
                    response=error_response
                )

                # Rate limited - backoff and retry
                if status == 429:
                    self._stats["rate_limits_hit"] += 1
                    self._stats["retries"] += 1
                    backoff = self._calculate_backoff(attempt)
                    time.sleep(backoff)
                    continue

                # Server errors - retry with backoff
                if status >= 500:
                    self._stats["retries"] += 1
                    if attempt < MAX_RETRIES - 1:
                        backoff = self._calculate_backoff(attempt)
                        time.sleep(backoff)
                        continue

                # Client errors (4xx except 429) - don't retry
                self._stats["errors"] += 1
                raise last_error

            except URLError as e:
                self._stats["retries"] += 1
                last_error = SPAPIError(
                    status_code=0,
                    message=str(e.reason),
                    error_code="NetworkError"
                )
                if attempt < MAX_RETRIES - 1:
                    backoff = self._calculate_backoff(attempt)
                    time.sleep(backoff)
                    continue
                self._stats["errors"] += 1
                raise last_error

            except json.JSONDecodeError as e:
                self._stats["errors"] += 1
                raise SPAPIError(
                    status_code=0,
                    message=f"Invalid JSON response: {e}",
                    error_code="ParseError"
                )

        # Should not reach here, but handle edge case
        self._stats["errors"] += 1
        if last_error:
            raise last_error
        raise SPAPIError(
            status_code=0,
            message="Max retries exceeded",
            error_code="RetryExhausted"
        )

    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calculate backoff time with exponential increase and jitter.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Backoff time in seconds
        """
        # Exponential backoff
        backoff = INITIAL_BACKOFF * (2 ** attempt)

        # Add jitter
        jitter = backoff * JITTER_FACTOR * random.random()
        backoff += jitter

        # Cap at max
        return min(backoff, MAX_BACKOFF)

    # Convenience methods
    def get(self, path: str, api_name: str = "default", **kwargs) -> Tuple[int, Any]:
        """Make GET request."""
        return self.request("GET", path, api_name, **kwargs)

    def post(self, path: str, api_name: str = "default", **kwargs) -> Tuple[int, Any]:
        """Make POST request."""
        return self.request("POST", path, api_name, **kwargs)

    def put(self, path: str, api_name: str = "default", **kwargs) -> Tuple[int, Any]:
        """Make PUT request."""
        return self.request("PUT", path, api_name, **kwargs)

    def patch(self, path: str, api_name: str = "default", **kwargs) -> Tuple[int, Any]:
        """Make PATCH request."""
        return self.request("PATCH", path, api_name, **kwargs)

    def delete(self, path: str, api_name: str = "default", **kwargs) -> Tuple[int, Any]:
        """Make DELETE request."""
        return self.request("DELETE", path, api_name, **kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            **self._stats,
            "rate_limiter": self.rate_limiter.get_stats()
        }

    def reset_stats(self):
        """Reset client statistics."""
        self._stats = {
            "requests": 0,
            "retries": 0,
            "rate_limits_hit": 0,
            "errors": 0
        }


def paginate(client: SPAPIClient, path: str, api_name: str,
             params: Dict = None, next_token_key: str = "NextToken",
             response_key: str = None, max_pages: int = 100,
             **kwargs) -> List[Any]:
    """
    Paginate through API results.

    Many SP-API endpoints use pagination with NextToken. This helper
    automatically fetches all pages.

    Args:
        client: SPAPIClient instance
        path: API path
        api_name: API name for rate limiting
        params: Initial query parameters
        next_token_key: Key for next token in response (default: NextToken)
        response_key: Key containing results in response (auto-detected if None)
        max_pages: Maximum pages to fetch (safety limit)
        **kwargs: Additional arguments passed to client.get()

    Returns:
        List of all results across pages
    """
    params = dict(params) if params else {}
    all_results = []
    page = 0

    while page < max_pages:
        status, response = client.get(path, api_name, params=params, **kwargs)

        # Find results in response
        if response_key:
            results = response.get(response_key, [])
        else:
            # Auto-detect: look for first list value
            results = []
            for key, value in response.items():
                if isinstance(value, list):
                    results = value
                    break

        all_results.extend(results)

        # Check for next page
        next_token = response.get(next_token_key)
        if not next_token:
            # Also check payload wrapper
            payload = response.get("payload", {})
            next_token = payload.get(next_token_key)

        if not next_token:
            break

        params["nextToken"] = next_token
        page += 1

    return all_results


# CLI interface for testing
if __name__ == "__main__":
    print("SP-API Client Module")
    print("This module provides the HTTP client for SP-API requests.")
    print("\nUsage:")
    print("  from spapi_client import SPAPIClient")
    print("  from spapi_auth import SPAPIAuth")
    print("")
    print("  auth = SPAPIAuth()")
    print("  client = SPAPIClient(auth)")
    print("  status, data = client.get('/vendor/orders/v1/purchaseOrders', 'vendorOrders')")
