#!/usr/bin/env python3
"""
Plytix PIM Async HTTP Client

Handles authentication (API Key + Password → bearer token with auto-refresh),
rate limiting, and response formatting for the FastMCP server.

Credentials are read from environment variables set by Claude Desktop.
Falls back to config file for Claude Code compatibility.
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Optional
import httpx

# =============================================================================
# Configuration
# =============================================================================

BYTE_HARD_LIMIT = 80_000  # 80KB hard cap on raw bytes returned

DEFAULT_API_URL = "https://pim.plytix.com/api/v1"
DEFAULT_AUTH_URL = "https://auth.plytix.com/auth/api/get-token"


def _get_credentials() -> tuple[str, str, str, str]:
    """Return (api_url, auth_url, api_key, api_password). Raises ValueError if not configured."""
    api_key = os.environ.get("PLYTIX_API_KEY", "")
    api_password = os.environ.get("PLYTIX_API_PASSWORD", "")
    api_url = os.environ.get("PLYTIX_API_URL", DEFAULT_API_URL)
    auth_url = os.environ.get("PLYTIX_AUTH_URL", DEFAULT_AUTH_URL)

    if not api_key or not api_password:
        # Try config file fallback (Claude Code compatibility)
        config_paths = [
            Path(__file__).parent.parent.parent / "plugins" / "plytix-skills" / "skills" / "plytix-api" / "config" / "plytix_config.json",
            Path.home() / ".claude" / "plugins" / "marketplaces" / "tchow-essentials" / "plugins" / "plytix-skills" / "skills" / "plytix-api" / "config" / "plytix_config.json",
        ]
        for config_path in config_paths:
            if config_path.exists():
                with open(config_path) as f:
                    cfg = json.load(f)
                env_name = cfg.get("defaults", {}).get("environment", "production")
                env = cfg.get("environments", {}).get(env_name, {})
                api_key = env.get("api_key", "")
                api_password = env.get("api_password", "")
                api_url = env.get("api_url", api_url)
                auth_url = env.get("auth_url", auth_url)
                if api_key and api_password and not api_key.startswith("YOUR_"):
                    break

    if not api_key or not api_password:
        raise ValueError(
            "Plytix credentials not configured. "
            "Set PLYTIX_API_KEY and PLYTIX_API_PASSWORD environment variables "
            "or configure via Claude Desktop."
        )

    return api_url.rstrip("/"), auth_url, api_key, api_password


def is_read_only() -> bool:
    """Return True if PLYTIX_READ_ONLY env var is set to 'true' (case-insensitive)."""
    return os.environ.get("PLYTIX_READ_ONLY", "false").strip().lower() == "true"


# =============================================================================
# Plytix Client
# =============================================================================

class PlytixClient:
    """Async Plytix PIM API client with automatic token refresh."""

    def __init__(self):
        self._api_url, self._auth_url, self._api_key, self._api_password = _get_credentials()
        self._token: Optional[str] = None
        self._token_expiry: float = 0
        self._token_lock = asyncio.Lock()

    async def _ensure_token(self) -> str:
        """Get a valid bearer token, refreshing if within 60s of expiry."""
        async with self._token_lock:
            now = time.time()
            if self._token and now < self._token_expiry - 60:
                return self._token

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self._auth_url,
                    json={"api_key": self._api_key, "api_password": self._api_password},
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                )
                resp.raise_for_status()
                result = resp.json()

            # Plytix returns: {"data": [{"access_token": "...", "expires_in": 900}]}
            data_section = result.get("data", result)
            if isinstance(data_section, list) and data_section:
                data_section = data_section[0]
            access_token = data_section.get("access_token") if isinstance(data_section, dict) else None

            if not access_token:
                raise ValueError(f"No access_token in auth response: {result}")

            expires_in = data_section.get("expires_in", 900)
            self._token = access_token
            self._token_expiry = time.time() + expires_in
            return self._token

    async def request(
        self,
        method: str,
        endpoint: str,
        data: dict = None,
        params: dict = None,
        _retry: bool = True,
    ) -> dict:
        """Make an authenticated Plytix API request with auto-retry on 401."""
        token = await self._ensure_token()
        url = f"{self._api_url}{endpoint}"
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method, url, headers=headers, params=clean_params, json=data
            )

            # Token expired — clear and retry once
            if resp.status_code == 401 and _retry:
                self._token = None
                self._token_expiry = 0
                return await self.request(method, endpoint, data, params, _retry=False)

            # Rate limited — respect Retry-After header
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "60"))
                raise httpx.HTTPStatusError(
                    f"Rate limited. Retry after {retry_after}s",
                    request=resp.request,
                    response=resp,
                )

            if resp.status_code == 204:
                return {"success": True}

            resp.raise_for_status()
            return resp.json()

    async def get(self, endpoint: str, params: dict = None) -> dict:
        return await self.request("GET", endpoint, params=params)

    async def post(self, endpoint: str, data: dict = None) -> dict:
        return await self.request("POST", endpoint, data=data)

    async def patch(self, endpoint: str, data: dict = None) -> dict:
        return await self.request("PATCH", endpoint, data=data)

    async def delete(self, endpoint: str, data: dict = None) -> dict:
        return await self.request("DELETE", endpoint, data=data)


# =============================================================================
# Response Formatting
# =============================================================================

_LIST_KEEP: dict[str, set] = {
    "products":      {"id", "sku", "label", "status", "modified", "thumbnail",
                      "product_family_id", "gtin"},
    "assets":        {"id", "filename", "file_type", "file_size", "modified", "public_url"},
    "categories":    {"id", "name", "label", "n_children", "parents_ids", "modified"},
    "file_categories": {"id", "name", "label", "n_children", "parents_ids", "modified"},
    "variants":      {"id", "sku", "label", "product_id", "modified"},
    "attributes":    {"id", "label", "name", "type_class", "mandatory", "modified"},
    "attr_groups":   {"id", "label", "name", "attributes"},
    "relationships": {"id", "name", "label", "bidirectional"},
    "families":      {"id", "name", "label", "modified"},
    "members":       {"id", "email", "name", "role", "status"},
    "credentials":   {"id", "name", "api_key", "created", "modified"},
}


def _slim(item: dict, resource: str, extra_keep: Optional[set] = None) -> dict:
    keep = _LIST_KEEP.get(resource)
    if keep:
        effective = keep | extra_keep if extra_keep else keep
        return {k: v for k, v in item.items() if k in effective}
    # Fallback: strip known heavy fields (but honour extra_keep)
    heavy = {"attributes", "assets", "categories", "relationships", "variants",
             "options", "mappings", "hooks", "install", "installSteps"}
    if extra_keep:
        heavy = heavy - extra_keep
    return {k: v for k, v in item.items() if k not in heavy}


def _fmt_list(data: list, resource: str = "", extra_keep: Optional[set] = None) -> str:
    """Slim list items by resource type, then hard-cap bytes."""
    items = [_slim(i, resource, extra_keep) if isinstance(i, dict) else i for i in data]
    result = json.dumps(items, indent=2)
    size = len(result.encode("utf-8"))
    if size <= BYTE_HARD_LIMIT:
        return result
    # Still too large — truncate to fit
    kept = max(1, len(items) * BYTE_HARD_LIMIT // size)
    return json.dumps({
        "items": items[:kept],
        "truncated": True,
        "shown": kept,
        "total": len(data),
        "hint": "Response truncated. Add filters or reduce page size.",
    }, indent=2)


def fmt(data, resource: str = "", extra_keep: Optional[set] = None) -> str:
    """Format any response with hard byte cap."""
    if isinstance(data, list):
        return _fmt_list(data, resource, extra_keep)
    # Unwrap Plytix envelope: {'data': [...]} → format the list
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
        list_result = _fmt_list(data["data"], resource, extra_keep)
        # If there's pagination info, include it
        pagination = data.get("pagination") or data.get("meta")
        if pagination:
            try:
                parsed = json.loads(list_result)
                if isinstance(parsed, list):
                    return json.dumps({"data": parsed, "pagination": pagination}, indent=2)
            except (json.JSONDecodeError, TypeError):
                pass
        return list_result
    text = json.dumps(data, indent=2)
    encoded = text.encode("utf-8")
    if len(encoded) <= BYTE_HARD_LIMIT:
        return text
    # Hard-truncate single objects at a safe boundary
    trimmed = encoded[:BYTE_HARD_LIMIT].decode("utf-8", errors="ignore")
    cut = trimmed.rfind("\n")
    if cut > BYTE_HARD_LIMIT // 2:
        trimmed = trimmed[:cut]
    return trimmed + "\n// [TRUNCATED — use a more specific query to get full details]"


def handle_error(e: Exception) -> str:
    """Format exceptions as user-friendly error strings."""
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        if code == 401:
            return "Error: Authentication failed. Check your PLYTIX_API_KEY and PLYTIX_API_PASSWORD."
        if code == 403:
            return "Error: Permission denied. You don't have access to this resource."
        if code == 404:
            return "Error: Resource not found. Check the ID is correct."
        if code == 409:
            return "Error: Conflict — resource already exists."
        if code == 422:
            try:
                body = e.response.json()
                msg = body.get("message") or body.get("msg") or str(body)[:300]
                return f"Error 422 (Validation): {msg}"
            except Exception:
                return f"Error 422 (Validation): {e.response.text[:300]}"
        if code == 428:
            return "Error 428: Result set too large for ordering. Remove sort_by or add more restrictive filters."
        if code == 429:
            return "Error: Rate limit exceeded. Wait before making more requests."
        if code == 500:
            return "Error 500: Internal Server Error from Plytix API. This may be a known upstream bug (e.g., attribute groups endpoint)."
        try:
            body = e.response.json()
            msg = body.get("message") or body.get("msg") or body.get("error", "")
            return f"Error {code}: {msg or e.response.text[:200]}"
        except Exception:
            return f"Error {code}: {e.response.text[:200]}"
    if isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. Try again."
    if isinstance(e, ValueError):
        return f"Configuration error: {e}"
    return f"Error: {type(e).__name__}: {e}"
