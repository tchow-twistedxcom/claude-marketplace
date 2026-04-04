#!/usr/bin/env python3
"""
Mimecast MCP Server

FastMCP server for Mimecast email security API operations.
Supports OAuth 2.0 (primary) and Legacy HMAC authentication.
Credentials are read from environment variables set by Claude Desktop.
"""

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from email.utils import formatdate
from pathlib import Path
from typing import Optional
import httpx
from mcp.server.fastmcp import FastMCP

# =============================================================================
# Configuration
# =============================================================================

CHARACTER_LIMIT = 25000

mcp = FastMCP("mimecast_mcp")

# Token cache (in-memory, per server process lifetime)
_token_cache: dict = {}


def _get_region_urls(region: str) -> tuple[str, str]:
    """Return (legacy_url, oauth_url) for region."""
    legacy = {
        "us": "https://us-api.mimecast.com", "eu": "https://eu-api.mimecast.com",
        "de": "https://de-api.mimecast.com", "au": "https://au-api.mimecast.com",
        "za": "https://za-api.mimecast.com", "ca": "https://ca-api.mimecast.com",
        "uk": "https://uk-api.mimecast.com", "sandbox": "https://sandbox-api.mimecast.com",
    }
    oauth = {
        "us": "https://us-api.services.mimecast.com", "eu": "https://eu-api.services.mimecast.com",
        "de": "https://de-api.services.mimecast.com", "au": "https://au-api.services.mimecast.com",
        "za": "https://za-api.services.mimecast.com", "ca": "https://ca-api.services.mimecast.com",
        "uk": "https://uk-api.services.mimecast.com", "sandbox": "https://sandbox-api.services.mimecast.com",
        "global": "https://api.services.mimecast.com",
    }
    region = region.lower()
    return legacy.get(region, legacy["us"]), oauth.get(region, oauth["global"])


def _get_auth_config() -> dict:
    """Get auth configuration from env vars or config file."""
    region = os.environ.get("MIMECAST_REGION", "us")
    client_id = os.environ.get("MIMECAST_CLIENT_ID", "")
    client_secret = os.environ.get("MIMECAST_CLIENT_SECRET", "")
    app_id = os.environ.get("MIMECAST_APP_ID", "")
    app_key = os.environ.get("MIMECAST_APP_KEY", "")
    access_key = os.environ.get("MIMECAST_ACCESS_KEY", "")
    secret_key = os.environ.get("MIMECAST_SECRET_KEY", "")

    # Config file fallback
    if not (client_id or app_id):
        config_paths = [
            Path(__file__).parent.parent.parent.parent / "plugins" / "mimecast-skills" / "config" / "mimecast_config.json",
        ]
        for path in config_paths:
            if path.exists():
                with open(path) as f:
                    cfg = json.load(f)
                profile_name = cfg.get("default_profile", "production")
                p = cfg.get("profiles", {}).get(profile_name, {})
                region = p.get("region", region)
                client_id = p.get("client_id", client_id)
                client_secret = p.get("client_secret", client_secret)
                app_id = p.get("app_id", app_id)
                app_key = p.get("app_key", app_key)
                access_key = p.get("access_key", access_key)
                secret_key = p.get("secret_key", secret_key)
                break

    legacy_url, oauth_url = _get_region_urls(region)

    if client_id and client_secret and not client_id.startswith("YOUR_"):
        return {"auth_type": "oauth2", "client_id": client_id, "client_secret": client_secret,
                "base_url": legacy_url, "oauth_url": oauth_url}
    elif app_id and access_key and secret_key and not app_id.startswith("YOUR_"):
        return {"auth_type": "hmac", "app_id": app_id, "app_key": app_key,
                "access_key": access_key, "secret_key": secret_key, "base_url": legacy_url}
    else:
        raise ValueError(
            "Mimecast credentials not configured. "
            "Set MIMECAST_CLIENT_ID + MIMECAST_CLIENT_SECRET (OAuth 2.0) "
            "or MIMECAST_APP_ID + MIMECAST_APP_KEY + MIMECAST_ACCESS_KEY + MIMECAST_SECRET_KEY (Legacy HMAC)."
        )


async def _get_oauth_token() -> str:
    """Get OAuth 2.0 access token with caching."""
    cfg = _get_auth_config()
    cache_key = f"oauth_{cfg['client_id'][:8]}"

    if cache_key in _token_cache:
        token_data = _token_cache[cache_key]
        if time.time() < token_data["expires_at"] - 300:
            return token_data["access_token"]

    oauth_url = cfg["oauth_url"]
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{oauth_url}/oauth/token",
            data={"grant_type": "client_credentials", "client_id": cfg["client_id"],
                  "client_secret": cfg["client_secret"]},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        token_resp = resp.json()

    token_data = {
        "access_token": token_resp["access_token"],
        "expires_at": time.time() + token_resp.get("expires_in", 3600),
    }
    _token_cache[cache_key] = token_data
    return token_data["access_token"]


def _hmac_headers(cfg: dict, uri: str) -> dict:
    """Generate HMAC-SHA1 headers for a request URI."""
    date_str = formatdate(localtime=True)
    req_id = str(uuid.uuid4())
    data_to_sign = f"{date_str}\n{req_id}\n{uri}\n{cfg['app_key']}"
    secret = base64.b64decode(cfg["secret_key"])
    sig = base64.b64encode(hmac.new(secret, data_to_sign.encode(), hashlib.sha1).digest()).decode()
    return {
        "Authorization": f"MC {cfg['access_key']}:{sig}",
        "x-mc-date": date_str,
        "x-mc-req-id": req_id,
        "x-mc-app-id": cfg["app_id"],
        "Content-Type": "application/json",
    }


async def _mimecast_request(uri: str, body: dict = None, v2_path: str = None) -> dict:
    """Make authenticated Mimecast API request.

    Args:
        uri: API 1.0 URI (e.g., '/api/account/get-account') for HMAC
        body: Request body
        v2_path: API 2.0 path (overrides uri, uses OAuth)
    """
    cfg = _get_auth_config()

    if v2_path or cfg["auth_type"] == "oauth2":
        token = await _get_oauth_token()
        url = f"{cfg['oauth_url']}{v2_path or uri}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    else:
        headers = _hmac_headers(cfg, uri)
        url = f"{cfg['base_url']}{uri}"

    payload = {"data": [body]} if body is not None and not v2_path else body

    async with httpx.AsyncClient(timeout=30.0) as client:
        if v2_path:
            resp = await client.get(url, headers=headers)
        else:
            resp = await client.post(url, headers=headers, json=payload or {"data": []})
        resp.raise_for_status()
        return resp.json()


def _extract_data(response: dict) -> list:
    """Extract data from Mimecast response envelope."""
    return response.get("data", response) if isinstance(response, dict) else response


def _handle_error(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        if code == 401:
            return "Error: Authentication failed. Check your Mimecast credentials."
        if code == 403:
            return "Error: Permission denied. Ensure the API application has required product assignments."
        if code == 429:
            return "Error: Rate limit exceeded. Wait before making more requests."
        try:
            body = e.response.json()
            fail = body.get("fail", [{}])
            msg = fail[0].get("message", "") if fail else ""
            return f"Error {code}: {msg or e.response.text[:200]}"
        except Exception:
            return f"Error {code}: {e.response.text[:200]}"
    if isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. Try again."
    if isinstance(e, ValueError):
        return f"Configuration error: {e}"
    return f"Error: {type(e).__name__}: {e}"


def _truncate(result: str) -> str:
    """Safely truncate large responses while preserving valid JSON."""
    if len(result) <= CHARACTER_LIMIT:
        return result
    try:
        data = json.loads(result)
        if isinstance(data, list):
            # Trim list to fit within limit
            half = max(1, len(data) // 2)
            trimmed = data[:half]
            truncated = json.dumps(
                {"items": trimmed, "truncated": True,
                 "total_returned": half, "total_available": len(data),
                 "hint": "Use date filters or --limit to narrow results."},
                indent=2
            )
            # Recurse once in case half is still too large
            if len(truncated) > CHARACTER_LIMIT:
                quarter = max(1, half // 2)
                trimmed = data[:quarter]
                truncated = json.dumps(
                    {"items": trimmed, "truncated": True,
                     "total_returned": quarter, "total_available": len(data),
                     "hint": "Use date filters or --limit to narrow results."},
                    indent=2
                )
            return truncated
        elif isinstance(data, dict):
            # For dicts, return a note instead of breaking the structure
            return json.dumps(
                {"truncated": True,
                 "message": f"Response too large ({len(result)} chars). Use more specific filters.",
                 "keys": list(data.keys())[:20]},
                indent=2
            )
    except Exception:
        pass
    # Fallback: return a valid JSON error rather than broken truncated string
    return json.dumps(
        {"truncated": True,
         "message": f"Response too large to display ({len(result)} chars). Use more specific filters."},
        indent=2
    )


# =============================================================================
# Account
# =============================================================================

@mcp.tool(
    name="mimecast_get_account",
    annotations={"title": "Get Mimecast Account Info", "readOnlyHint": True, "openWorldHint": True}
)
async def mimecast_get_account() -> str:
    """Get Mimecast account information including domain, region, and account details.

    Returns:
        JSON with account code, name, domain, region, and package information.
    """
    try:
        resp = await _mimecast_request("/api/account/get-account")
        return json.dumps(_extract_data(resp), indent=2)
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# Messages
# =============================================================================

@mcp.tool(
    name="mimecast_list_held_messages",
    annotations={"title": "List Held Messages", "readOnlyHint": True, "openWorldHint": True}
)
async def mimecast_list_held_messages(admin: bool = False) -> str:
    """List messages currently held in the Mimecast queue awaiting review.

    Args:
        admin: True for admin hold queue, False for user hold queue (default: False)

    Returns:
        JSON array of held message objects with id, fromEnv, to, subject, reason.
    """
    try:
        body = {"admin": admin}
        resp = await _mimecast_request("/api/gateway/get-hold-message-list", body)
        return _truncate(json.dumps(_extract_data(resp), indent=2))
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="mimecast_track_message",
    annotations={"title": "Track Message", "readOnlyHint": True, "openWorldHint": True}
)
async def mimecast_track_message(
    sender: Optional[str] = None,
    recipient: Optional[str] = None,
    subject: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> str:
    """Track messages through the Mimecast gateway.

    Args:
        sender: Filter by sender email address (optional)
        recipient: Filter by recipient email address (optional)
        subject: Filter by subject (optional)
        from_date: Start date ISO format e.g. '2024-01-01T00:00:00+0000' (optional, default: 24h ago)
        to_date: End date ISO format (optional, default: now)

    Returns:
        JSON array of message tracking records with status, delivery info, and route.
    """
    try:
        now = datetime.now(timezone.utc)
        body = {
            "from": from_date or (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "to": to_date or now.strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "pageSize": 50,
        }
        if sender:
            body["senderOrRecipient"] = sender
        if recipient:
            body["senderOrRecipient"] = recipient
        if subject:
            body["subject"] = subject

        resp = await _mimecast_request("/api/message-finder/search", body)
        return _truncate(json.dumps(_extract_data(resp), indent=2))
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# TTP (Targeted Threat Protection)
# =============================================================================

@mcp.tool(
    name="mimecast_list_ttp_url_logs",
    annotations={"title": "List TTP URL Logs", "readOnlyHint": True, "openWorldHint": True}
)
async def mimecast_list_ttp_url_logs(
    scan_result: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> str:
    """Get TTP URL protection scan logs showing clicked URLs and threat results.

    Args:
        scan_result: Filter by result: 'clean', 'malicious', 'warn', 'error', 'neutral' (optional)
        from_date: Start date ISO format e.g. '2024-01-01T00:00:00+0000' (optional, default: 24h ago)
        to_date: End date ISO format (optional, default: now)

    Returns:
        JSON array of TTP URL log entries with url, userEmailAddress, scanResult, date.
    """
    try:
        now = datetime.now(timezone.utc)
        body = {
            "from": from_date or (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "to": to_date or now.strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "pageSize": 100,
        }
        if scan_result:
            body["scanResult"] = scan_result

        resp = await _mimecast_request("/api/ttp/url/get-logs", body)
        return _truncate(json.dumps(_extract_data(resp), indent=2))
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="mimecast_list_ttp_attachment_logs",
    annotations={"title": "List TTP Attachment Logs", "readOnlyHint": True, "openWorldHint": True}
)
async def mimecast_list_ttp_attachment_logs(
    result: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> str:
    """Get TTP attachment protection scan logs for sandboxed email attachments.

    Args:
        result: Filter by result: 'clean', 'malicious', 'unknown', 'timeout' (optional)
        from_date: Start date ISO format (optional, default: 24h ago)
        to_date: End date ISO format (optional, default: now)

    Returns:
        JSON array of attachment scan records with filename, result, threatName, date.
    """
    try:
        now = datetime.now(timezone.utc)
        body = {
            "from": from_date or (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "to": to_date or now.strftime("%Y-%m-%dT%H:%M:%S+0000"),
        }
        if result:
            body["result"] = result

        resp = await _mimecast_request("/api/ttp/attachment/get-logs", body)
        return _truncate(json.dumps(_extract_data(resp), indent=2))
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# Users & Groups
# =============================================================================

@mcp.tool(
    name="mimecast_list_users",
    annotations={"title": "List Mimecast Users", "readOnlyHint": True, "openWorldHint": True}
)
async def mimecast_list_users(query: Optional[str] = None) -> str:
    """List Mimecast users, optionally filtered by name or email.

    Args:
        query: Search query string to filter users by name or email (optional)

    Returns:
        JSON array of user objects with emailAddress, name, alias, domain.
    """
    try:
        body = {}
        if query:
            body["query"] = query
        resp = await _mimecast_request("/api/user/get-internal-user", body)
        return _truncate(json.dumps(_extract_data(resp), indent=2))
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="mimecast_list_groups",
    annotations={"title": "List Mimecast Groups", "readOnlyHint": True, "openWorldHint": True}
)
async def mimecast_list_groups(query: Optional[str] = None) -> str:
    """List Mimecast directory groups.

    Args:
        query: Search query to filter groups by name (optional)

    Returns:
        JSON array of group objects with id, description, parentSummary, userCount.
    """
    try:
        body = {}
        if query:
            body["query"] = query
        resp = await _mimecast_request("/api/directory/get-group", body)
        return _truncate(json.dumps(_extract_data(resp), indent=2))
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# Senders Policy
# =============================================================================

@mcp.tool(
    name="mimecast_list_managed_senders",
    annotations={"title": "List Managed Senders", "readOnlyHint": True, "openWorldHint": True}
)
async def mimecast_list_managed_senders(sender_type: str = "blocked") -> str:
    """List managed senders (blocked or permitted) in Mimecast.

    Args:
        sender_type: 'blocked' or 'permit' (default: 'blocked')

    Returns:
        JSON array of sender entries with id, sender, to, type, date.
    """
    try:
        body = {"type": sender_type}
        resp = await _mimecast_request("/api/managedsender/get-policy-for-sender", body)
        return _truncate(json.dumps(_extract_data(resp), indent=2))
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# Audit
# =============================================================================

@mcp.tool(
    name="mimecast_get_audit_events",
    annotations={"title": "Get Audit Events", "readOnlyHint": True, "openWorldHint": True}
)
async def mimecast_get_audit_events(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    category: Optional[str] = None,
) -> str:
    """Get Mimecast audit events for admin activity tracking.

    Args:
        from_date: Start date ISO format e.g. '2024-01-01T00:00:00+0000' (optional, default: 24h ago)
        to_date: End date ISO format (optional, default: now)
        category: Filter by event category (optional)

    Returns:
        JSON array of audit events with user, eventInfo, category, datetime.
    """
    try:
        now = datetime.now(timezone.utc)
        body = {
            "from": from_date or (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "to": to_date or now.strftime("%Y-%m-%dT%H:%M:%S+0000"),
        }
        if category:
            body["category"] = category

        resp = await _mimecast_request("/api/audit/get-audit-events", body)
        return _truncate(json.dumps(_extract_data(resp), indent=2))
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# Policies
# =============================================================================

@mcp.tool(
    name="mimecast_list_policies",
    annotations={"title": "List Mimecast Policies", "readOnlyHint": True, "openWorldHint": True}
)
async def mimecast_list_policies(policy_type: str = "blocked-senders") -> str:
    """List Mimecast policies of a given type.

    Args:
        policy_type: Policy type to list. Options: 'blocked-senders', 'permitted-senders',
                     'anti-spoofing', 'content-examination' (default: 'blocked-senders')

    Returns:
        JSON array of policy objects.
    """
    try:
        endpoint_map = {
            "blocked-senders": "/api/policy/blockedsenders/get-policy",
            "permitted-senders": "/api/policy/permittedsenders/get-policy",
            "anti-spoofing": "/api/policy/antispoofing-bypass/get-policy",
        }
        uri = endpoint_map.get(policy_type, f"/api/policy/{policy_type}/get-policy")
        resp = await _mimecast_request(uri, {})
        return _truncate(json.dumps(_extract_data(resp), indent=2))
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# Quarantine & Message Actions
# =============================================================================

@mcp.tool(
    name="mimecast_release_held_message",
    annotations={"title": "Release Held Message", "readOnlyHint": False,
                 "destructiveHint": False, "openWorldHint": True}
)
async def mimecast_release_held_message(message_id: str, reason: str = "") -> str:
    """Release a held message from the Mimecast hold queue so it can be delivered.

    Args:
        message_id: ID of the held message to release (required)
        reason: Optional reason for releasing the message

    Returns:
        JSON confirmation of the release action.
    """
    try:
        body = {"id": message_id, "reason": reason}
        resp = await _mimecast_request("/api/gateway/accept-hold-message", body)
        return json.dumps(_extract_data(resp), indent=2)
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# Sender Management
# =============================================================================

@mcp.tool(
    name="mimecast_block_sender",
    annotations={"title": "Block Sender", "readOnlyHint": False,
                 "destructiveHint": False, "openWorldHint": True}
)
async def mimecast_block_sender(
    sender: str,
    to: str = "",
    comment: str = "",
) -> str:
    """Add an email sender to the Mimecast blocked senders list.

    Args:
        sender: Email address to block (required)
        to: Recipient address to scope the block to (optional, empty = all recipients)
        comment: Optional comment describing why sender is blocked

    Returns:
        JSON confirmation with the created managed sender entry.
    """
    try:
        body = {
            "sender": sender,
            "to": to,
            "type": "block",
        }
        if comment:
            body["comment"] = comment
        resp = await _mimecast_request("/api/managedsender/permit-or-block-sender", body)
        return json.dumps(_extract_data(resp), indent=2)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="mimecast_permit_sender",
    annotations={"title": "Permit Sender", "readOnlyHint": False,
                 "destructiveHint": False, "openWorldHint": True}
)
async def mimecast_permit_sender(
    sender: str,
    to: str = "",
    comment: str = "",
) -> str:
    """Add an email sender to the Mimecast permitted senders list.

    Args:
        sender: Email address to permit (required)
        to: Recipient address to scope the permit to (optional, empty = all recipients)
        comment: Optional comment describing why sender is permitted

    Returns:
        JSON confirmation with the created managed sender entry.
    """
    try:
        body = {
            "sender": sender,
            "to": to,
            "type": "permit",
        }
        if comment:
            body["comment"] = comment
        resp = await _mimecast_request("/api/managedsender/permit-or-block-sender", body)
        return json.dumps(_extract_data(resp), indent=2)
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# TTP URL Management
# =============================================================================

@mcp.tool(
    name="mimecast_block_url",
    annotations={"title": "Block URL in TTP", "readOnlyHint": False,
                 "destructiveHint": False, "openWorldHint": True}
)
async def mimecast_block_url(url: str, comment: str = "") -> str:
    """Add a URL to the Mimecast TTP URL block list to prevent users from accessing it.

    Args:
        url: URL to block (required)
        comment: Optional comment describing why URL is blocked

    Returns:
        JSON confirmation with the created managed URL entry.
    """
    try:
        body = {"url": url, "action": "block"}
        if comment:
            body["comment"] = comment
        resp = await _mimecast_request("/api/ttp/url/create-managed-url", body)
        return json.dumps(_extract_data(resp), indent=2)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="mimecast_permit_url",
    annotations={"title": "Permit URL in TTP", "readOnlyHint": False,
                 "destructiveHint": False, "openWorldHint": True}
)
async def mimecast_permit_url(url: str, comment: str = "") -> str:
    """Add a URL to the Mimecast TTP URL permit list to allow users to access it.

    Args:
        url: URL to permit (required)
        comment: Optional comment describing why URL is permitted

    Returns:
        JSON confirmation with the created managed URL entry.
    """
    try:
        body = {"url": url, "action": "permit"}
        if comment:
            body["comment"] = comment
        resp = await _mimecast_request("/api/ttp/url/create-managed-url", body)
        return json.dumps(_extract_data(resp), indent=2)
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# TTP Impersonation Logs
# =============================================================================

@mcp.tool(
    name="mimecast_get_ttp_impersonation_logs",
    annotations={"title": "Get TTP Impersonation Logs", "readOnlyHint": True,
                 "openWorldHint": True}
)
async def mimecast_get_ttp_impersonation_logs(
    days: int = 1,
    action: Optional[str] = None,
    limit: int = 100,
) -> str:
    """Get TTP impersonation protection logs showing emails blocked or warned as impersonation attempts.

    Args:
        days: Number of days to look back (default: 1, max: 7)
        action: Filter by action taken: 'block', 'warn', 'none' (optional)
        limit: Maximum number of results to return (default: 100, max: 500)

    Returns:
        JSON array of impersonation log entries with sender, subject, action, reason, date.
    """
    try:
        now = datetime.now(timezone.utc)
        body = {
            "from": (now - timedelta(days=min(days, 7))).strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "to": now.strftime("%Y-%m-%dT%H:%M:%S+0000"),
            "pageSize": min(limit, 500),
        }
        if action:
            body["action"] = action
        resp = await _mimecast_request("/api/ttp/impersonation/get-logs", body)
        return _truncate(json.dumps(_extract_data(resp), indent=2))
    except Exception as e:
        return _handle_error(e)


if __name__ == "__main__":
    mcp.run()
