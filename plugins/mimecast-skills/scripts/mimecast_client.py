#!/usr/bin/env python3
"""
Mimecast HTTP Client

Provides rate-limited HTTP client for Mimecast API with retry logic,
exponential backoff, and proper error handling.
"""

import json
import random
import sys
import time
from typing import Optional, Dict, Any, List
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from mimecast_auth import MimecastAuth


class TokenBucket:
    """Token bucket rate limiter for API request throttling."""

    def __init__(self, rate: float, capacity: float):
        """
        Initialize token bucket.

        Args:
            rate: Tokens per second to add
            capacity: Maximum tokens in bucket
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()

    def _add_tokens(self):
        """Add tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

    def consume(self, tokens: float = 1.0) -> bool:
        """
        Try to consume tokens.

        Returns:
            True if tokens consumed, False if not enough tokens
        """
        self._add_tokens()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def wait(self, tokens: float = 1.0):
        """Wait until tokens are available, then consume."""
        while not self.consume(tokens):
            # Wait for at least one token to be added
            wait_time = (tokens - self.tokens) / self.rate
            time.sleep(max(0.01, wait_time))


class MimecastError(Exception):
    """Base exception for Mimecast API errors."""

    def __init__(self, message: str, status_code: int = None, error_key: str = None,
                 details: str = None, request_id: str = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_key = error_key
        self.details = details
        self.request_id = request_id

    def __str__(self):
        parts = [self.message]
        if self.status_code:
            parts.insert(0, f"[{self.status_code}]")
        if self.error_key:
            parts.append(f"(Key: {self.error_key})")
        return " ".join(parts)


class MimecastClient:
    """
    HTTP client for Mimecast API with rate limiting and retry logic.

    Features:
    - Token bucket rate limiting (120 requests/minute default)
    - Exponential backoff with jitter for retries
    - Automatic retry on transient errors (429, 5xx)
    - Proper error parsing and reporting
    """

    # Rate limiting: 120 requests per minute = 2 per second
    DEFAULT_RATE_LIMIT = 2.0  # requests per second
    DEFAULT_BURST = 10  # burst capacity

    # Retry configuration
    MAX_RETRIES = 5
    BASE_BACKOFF = 1.0  # seconds
    MAX_BACKOFF = 120.0  # seconds

    # Timeout
    DEFAULT_TIMEOUT = 60  # seconds

    def __init__(self, auth: MimecastAuth, rate_limit: float = None, timeout: int = None):
        """
        Initialize Mimecast HTTP client.

        Args:
            auth: MimecastAuth instance for generating signatures
            rate_limit: Requests per second (default: 2.0)
            timeout: Request timeout in seconds (default: 60)
        """
        self.auth = auth
        self.base_url = auth.base_url
        self.timeout = timeout or self.DEFAULT_TIMEOUT

        rate = rate_limit or self.DEFAULT_RATE_LIMIT
        self.rate_limiter = TokenBucket(rate, self.DEFAULT_BURST)

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter."""
        backoff = min(self.MAX_BACKOFF, self.BASE_BACKOFF * (2 ** attempt))
        jitter = random.uniform(0, backoff * 0.1)
        return backoff + jitter

    def _parse_error_response(self, response_body: str) -> Dict[str, Any]:
        """Parse Mimecast error response format."""
        try:
            data = json.loads(response_body)
            fail_list = data.get("fail", [])
            if fail_list:
                first_error = fail_list[0]
                return {
                    "key": first_error.get("key", "unknown_error"),
                    "message": first_error.get("message", "Unknown error"),
                    "retryable": first_error.get("retryable", False)
                }
            return {"key": "unknown_error", "message": response_body, "retryable": False}
        except json.JSONDecodeError:
            return {"key": "parse_error", "message": response_body, "retryable": False}

    def _is_retryable(self, status_code: int, error_info: Dict) -> bool:
        """Determine if error is retryable."""
        # Rate limit exceeded
        if status_code == 429:
            return True
        # Server errors
        if 500 <= status_code < 600:
            return True
        # Check error response
        return error_info.get("retryable", False)

    def request_v2(
        self,
        method: str,
        uri: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated API 2.0 request (no data wrapper).

        API 2.0 uses different request/response format than API 1.0:
        - GET requests with query params instead of POST with data wrapper
        - Response not wrapped in {"data": [...]}

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            uri: API endpoint URI (e.g., /domain/cloud-gateway/v1/external-domains)
            data: Request body for POST/PATCH (sent as-is, not wrapped)
            params: Query parameters for GET requests

        Returns:
            API response as dict

        Raises:
            MimecastError: On API errors
        """
        self.rate_limiter.wait()

        # Build URL with query params
        url = f"{self.base_url}{uri}"
        if params:
            from urllib.parse import urlencode
            url = f"{url}?{urlencode(params)}"

        # Prepare body (not wrapped for API 2.0)
        body_bytes = None
        if data is not None:
            body_bytes = json.dumps(data).encode('utf-8')

        headers = self.auth.get_headers(uri)

        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                req = Request(url, data=body_bytes, headers=headers, method=method)
                with urlopen(req, timeout=self.timeout) as response:
                    return json.loads(response.read().decode())

            except HTTPError as e:
                error_body = e.read().decode() if e.fp else ""
                error_info = self._parse_error_response(error_body)

                if self._is_retryable(e.code, error_info) and attempt < self.MAX_RETRIES - 1:
                    backoff = self._calculate_backoff(attempt)
                    print(f"Request failed ({e.code}), retrying in {backoff:.1f}s...",
                          file=sys.stderr)
                    time.sleep(backoff)
                    continue

                last_error = MimecastError(
                    message=error_info.get("message", e.reason),
                    status_code=e.code,
                    error_key=error_info.get("key"),
                    details=error_body[:500] if error_body else None
                )
                break

            except URLError as e:
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self._calculate_backoff(attempt)
                    time.sleep(backoff)
                    continue
                last_error = MimecastError(message=f"Network error: {e.reason}")
                break

            except Exception as e:
                last_error = MimecastError(message=f"Unexpected error: {str(e)}")
                break

        if last_error:
            raise last_error

        raise MimecastError("Request failed for unknown reason")

    def get_v2(self, uri: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API 2.0 GET request."""
        return self.request_v2("GET", uri, params=params)

    def post_v2(self, uri: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API 2.0 POST request."""
        return self.request_v2("POST", uri, data=data)

    def request(
        self,
        method: str,
        uri: str,
        data: Optional[Dict] = None,
        paginate: bool = False
    ) -> Dict[str, Any]:
        """
        Make authenticated API request with rate limiting and retry.

        Args:
            method: HTTP method (typically POST for Mimecast)
            uri: API endpoint URI (e.g., /api/account/get-account)
            data: Request data (will be wrapped in {"data": [data]})
            paginate: If True, handle pagination automatically

        Returns:
            API response as dict

        Raises:
            MimecastError: On API errors after retries exhausted
        """
        # Wait for rate limit
        self.rate_limiter.wait()

        # Build request URL
        url = f"{self.base_url}{uri}"

        # Prepare request body - Mimecast expects {"data": []}
        if data is None:
            body = {"data": []}
        elif isinstance(data, list):
            body = {"data": data}
        else:
            body = {"data": [data]}

        body_bytes = json.dumps(body).encode('utf-8')

        last_error = None
        last_request_id = None

        for attempt in range(self.MAX_RETRIES):
            # Generate fresh signature for each attempt (time-sensitive)
            headers = self.auth.get_headers(uri)
            last_request_id = headers.get('x-mc-req-id')

            try:
                req = Request(url, data=body_bytes, headers=headers, method=method)
                with urlopen(req, timeout=self.timeout) as response:
                    result = json.loads(response.read().decode())

                    # Handle pagination if requested
                    if paginate and result.get("meta", {}).get("pagination"):
                        return self._paginate(method, uri, data, result)

                    return result

            except HTTPError as e:
                error_body = e.read().decode() if e.fp else ""
                error_info = self._parse_error_response(error_body)

                # Check if retryable
                if self._is_retryable(e.code, error_info) and attempt < self.MAX_RETRIES - 1:
                    backoff = self._calculate_backoff(attempt)
                    print(f"Request failed ({e.code}), retrying in {backoff:.1f}s...",
                          file=sys.stderr)
                    time.sleep(backoff)
                    continue

                # Not retryable or retries exhausted
                last_error = MimecastError(
                    message=error_info.get("message", e.reason),
                    status_code=e.code,
                    error_key=error_info.get("key"),
                    details=error_body[:500] if error_body else None,
                    request_id=last_request_id
                )
                break

            except URLError as e:
                # Network error - may be retryable
                if attempt < self.MAX_RETRIES - 1:
                    backoff = self._calculate_backoff(attempt)
                    print(f"Network error: {e.reason}, retrying in {backoff:.1f}s...",
                          file=sys.stderr)
                    time.sleep(backoff)
                    continue

                last_error = MimecastError(
                    message=f"Network error: {e.reason}",
                    request_id=last_request_id
                )
                break

            except Exception as e:
                last_error = MimecastError(
                    message=f"Unexpected error: {str(e)}",
                    request_id=last_request_id
                )
                break

        if last_error:
            raise last_error

        # Should not reach here
        raise MimecastError("Request failed for unknown reason")

    def _paginate(
        self,
        method: str,
        uri: str,
        data: Optional[Dict],
        first_response: Dict
    ) -> Dict[str, Any]:
        """Handle pagination by fetching all pages."""
        all_data = first_response.get("data", [])
        meta = first_response.get("meta", {})
        pagination = meta.get("pagination", {})

        while pagination.get("next"):
            # Prepare next page request
            next_token = pagination.get("next")
            page_data = data.copy() if data else {}
            page_data["meta"] = {"pagination": {"pageToken": next_token}}

            # Wait for rate limit
            self.rate_limiter.wait()

            # Make request
            body = {"data": [page_data]}
            body_bytes = json.dumps(body).encode('utf-8')
            url = f"{self.base_url}{uri}"
            headers = self.auth.get_headers(uri)

            try:
                req = Request(url, data=body_bytes, headers=headers, method=method)
                with urlopen(req, timeout=self.timeout) as response:
                    result = json.loads(response.read().decode())
                    all_data.extend(result.get("data", []))
                    pagination = result.get("meta", {}).get("pagination", {})

            except Exception as e:
                # Return what we have so far on error
                print(f"Pagination error: {e}, returning partial results", file=sys.stderr)
                break

        # Return combined response
        first_response["data"] = all_data
        if "meta" in first_response and "pagination" in first_response["meta"]:
            del first_response["meta"]["pagination"]

        return first_response

    def get(self, uri: str, data: Optional[Dict] = None, paginate: bool = False) -> Dict:
        """Convenience method for GET-like requests (Mimecast uses POST)."""
        return self.request("POST", uri, data, paginate)

    def post(self, uri: str, data: Optional[Dict] = None) -> Dict:
        """Convenience method for POST requests."""
        return self.request("POST", uri, data)


def create_client(profile: str = None, config_path: str = None) -> MimecastClient:
    """
    Factory function to create a configured Mimecast client.

    Args:
        profile: Profile name from config (default: from config)
        config_path: Path to config file (default: config/mimecast_config.json)

    Returns:
        Configured MimecastClient instance
    """
    auth = MimecastAuth(config_path=config_path, profile=profile)
    return MimecastClient(auth)
