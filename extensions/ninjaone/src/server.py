#!/usr/bin/env python3
"""
NinjaOne MCP Server

FastMCP server for NinjaOne RMM API operations.
Credentials are read from environment variables set by Claude Desktop.
Falls back to config file for Claude Code compatibility.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional
import httpx
from mcp.server.fastmcp import FastMCP

# =============================================================================
# Configuration
# =============================================================================

CHARACTER_LIMIT = 25000

mcp = FastMCP("ninjaone_mcp")

# In-memory token cache
_token_cache: dict = {}


def _get_config() -> dict:
    """Get NinjaOne config from env vars or config file."""
    api_url = os.environ.get("NINJAONE_API_URL", "https://app.ninjarmm.com")
    client_id = os.environ.get("NINJAONE_CLIENT_ID", "")
    client_secret = os.environ.get("NINJAONE_CLIENT_SECRET", "")

    if not (client_id and client_secret):
        config_paths = [
            Path(__file__).parent.parent.parent.parent / "plugins" / "ninjaone-skills" / "skills" / "ninjaone-api" / "config" / "ninjaone_config.json",
        ]
        for path in config_paths:
            if path.exists():
                with open(path) as f:
                    cfg = json.load(f)
                inst = cfg.get("instance", {})
                api_url = inst.get("api_url", api_url).rstrip("/")
                client_id = inst.get("client_id", client_id)
                client_secret = inst.get("client_secret", client_secret)
                if client_id and not client_id.startswith("YOUR_"):
                    return {"api_url": api_url, "client_id": client_id, "client_secret": client_secret}

        if not client_id or client_id.startswith("YOUR_"):
            raise ValueError(
                "NinjaOne credentials not configured. "
                "Set NINJAONE_CLIENT_ID and NINJAONE_CLIENT_SECRET environment variables."
            )

    return {"api_url": api_url.rstrip("/"), "client_id": client_id, "client_secret": client_secret}


async def _get_access_token() -> str:
    """Get OAuth 2.0 access token with caching."""
    cfg = _get_config()
    cache_key = f"ninjaone_{cfg['client_id'][:8]}"

    if cache_key in _token_cache:
        token_data = _token_cache[cache_key]
        if time.time() < token_data["expires_at"] - 300:
            return token_data["access_token"]

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{cfg['api_url']}/ws/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "scope": "monitoring management control",
            },
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


async def _ninjaone_request(method: str, endpoint: str, data: dict = None, params: dict = None) -> dict:
    """Make authenticated NinjaOne API request."""
    cfg = _get_config()
    token = await _get_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{cfg['api_url']}{endpoint}"
    clean_params = {k: v for k, v in (params or {}).items() if v is not None}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(method, url, headers=headers, params=clean_params, json=data)
        if resp.status_code == 204:
            return {"success": True}
        resp.raise_for_status()
        return resp.json()


def _handle_error(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        if code == 401:
            return "Error: Authentication failed. Check your NinjaOne client credentials."
        if code == 403:
            return "Error: Permission denied. Ensure your OAuth app has required scopes."
        if code == 404:
            return "Error: Resource not found. Check the ID is correct."
        if code == 429:
            return "Error: Rate limit exceeded. Wait before making more requests."
        try:
            body = e.response.json()
            msg = body.get("message", body.get("error", ""))
            return f"Error {code}: {msg or e.response.text[:200]}"
        except Exception:
            return f"Error {code}: {e.response.text[:200]}"
    if isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. Try again."
    if isinstance(e, ValueError):
        return f"Configuration error: {e}"
    return f"Error: {type(e).__name__}: {e}"


def _truncate(result: str) -> str:
    if len(result) > CHARACTER_LIMIT:
        try:
            data = json.loads(result)
            items = data if isinstance(data, list) else data.get("results", data.get("items", []))
            if isinstance(items, list):
                half = max(1, len(items) // 2)
                return json.dumps({"items": items[:half], "truncated": True,
                                   "message": f"Showing {half}/{len(items)} items. Add filters to narrow results."}, indent=2)
        except Exception:
            return result[:CHARACTER_LIMIT] + "\n... [truncated]"
    return result


# =============================================================================
# Devices
# =============================================================================

@mcp.tool(
    name="ninjaone_list_devices",
    annotations={"title": "List NinjaOne Devices", "readOnlyHint": True, "openWorldHint": True}
)
async def ninjaone_list_devices(
    org_id: Optional[int] = None,
    page_size: Optional[int] = None,
    device_filter: Optional[str] = None,
) -> str:
    """List all devices in NinjaOne, optionally filtered.

    Args:
        org_id: Filter by organization ID (optional)
        page_size: Max devices to return, 1-1000 (optional, default: 100)
        device_filter: NQL filter e.g. 'class = WINDOWS_WORKSTATION' (optional)

    Returns:
        JSON array of device objects with id, systemName, os, lastContact, organizationId.
    """
    try:
        params = {}
        if org_id:
            params["organizationId"] = org_id
        if page_size:
            params["pageSize"] = min(page_size, 1000)
        if device_filter:
            params["df"] = device_filter
        data = await _ninjaone_request("GET", "/v2/devices", params=params)
        return _truncate(json.dumps(data, indent=2))
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="ninjaone_get_device",
    annotations={"title": "Get NinjaOne Device", "readOnlyHint": True, "openWorldHint": True}
)
async def ninjaone_get_device(device_id: int) -> str:
    """Get detailed information for a specific NinjaOne device.

    Args:
        device_id: The device numeric ID

    Returns:
        JSON object with device details including hardware, OS, network, last contact.
    """
    try:
        data = await _ninjaone_request("GET", f"/v2/device/{device_id}")
        return json.dumps(data, indent=2)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="ninjaone_get_device_software",
    annotations={"title": "Get Device Software Inventory", "readOnlyHint": True, "openWorldHint": True}
)
async def ninjaone_get_device_software(device_id: int) -> str:
    """Get installed software list for a NinjaOne device.

    Args:
        device_id: The device numeric ID

    Returns:
        JSON array of installed software with name, version, publisher, installDate.
    """
    try:
        data = await _ninjaone_request("GET", f"/v2/device/{device_id}/software")
        return _truncate(json.dumps(data, indent=2))
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="ninjaone_get_device_patches",
    annotations={"title": "Get Device Patch Status", "readOnlyHint": True, "openWorldHint": True}
)
async def ninjaone_get_device_patches(device_id: int, status: Optional[str] = None) -> str:
    """Get OS patch status for a NinjaOne device.

    Args:
        device_id: The device numeric ID
        status: Filter by status: 'APPROVED', 'FAILED', 'REJECTED', 'PENDING' (optional)

    Returns:
        JSON array of patches with name, severity, status, kbNumber, installedAt.
    """
    try:
        params = {}
        if status:
            params["status"] = status
        data = await _ninjaone_request("GET", f"/v2/device/{device_id}/os-patches", params=params)
        return _truncate(json.dumps(data, indent=2))
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# Organizations
# =============================================================================

@mcp.tool(
    name="ninjaone_list_organizations",
    annotations={"title": "List NinjaOne Organizations", "readOnlyHint": True, "openWorldHint": True}
)
async def ninjaone_list_organizations(page_size: Optional[int] = None) -> str:
    """List all organizations in NinjaOne.

    Args:
        page_size: Max organizations to return (optional, default: 100)

    Returns:
        JSON array of organization objects with id, name, description, nodeCount.
    """
    try:
        params = {}
        if page_size:
            params["pageSize"] = min(page_size, 1000)
        data = await _ninjaone_request("GET", "/v2/organizations", params=params)
        return _truncate(json.dumps(data, indent=2))
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# Alerts
# =============================================================================

@mcp.tool(
    name="ninjaone_list_alerts",
    annotations={"title": "List NinjaOne Alerts", "readOnlyHint": True, "openWorldHint": True}
)
async def ninjaone_list_alerts(
    source_type: Optional[str] = None,
    device_filter: Optional[str] = None,
) -> str:
    """List active alerts in NinjaOne.

    Args:
        source_type: Filter by source: 'CONDITION', 'POLICY', 'PATCH_MANAGEMENT' (optional)
        device_filter: NQL filter to scope to specific devices (optional)

    Returns:
        JSON array of alert objects with uid, message, severity, deviceId, created.
    """
    try:
        params = {}
        if source_type:
            params["sourceType"] = source_type
        if device_filter:
            params["df"] = device_filter
        data = await _ninjaone_request("GET", "/v2/alerts", params=params)
        return _truncate(json.dumps(data, indent=2))
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# Ticketing
# =============================================================================

@mcp.tool(
    name="ninjaone_list_tickets",
    annotations={"title": "List NinjaOne Tickets", "readOnlyHint": True, "openWorldHint": True}
)
async def ninjaone_list_tickets(
    board_id: Optional[int] = None,
    page_size: Optional[int] = None,
) -> str:
    """List tickets in NinjaOne ticketing system.

    Args:
        board_id: Filter by ticket board ID (optional)
        page_size: Max tickets to return (optional, default: 50)

    Returns:
        JSON array of ticket objects with id, subject, status, priority, assignedTo, deviceId.
    """
    try:
        params = {}
        if board_id:
            params["boardId"] = board_id
        if page_size:
            params["pageSize"] = min(page_size, 200)
        data = await _ninjaone_request("GET", "/v2/ticketing/ticket", params=params)
        return _truncate(json.dumps(data, indent=2))
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="ninjaone_get_ticket",
    annotations={"title": "Get NinjaOne Ticket", "readOnlyHint": True, "openWorldHint": True}
)
async def ninjaone_get_ticket(ticket_id: int) -> str:
    """Get details for a specific NinjaOne ticket.

    Args:
        ticket_id: The ticket numeric ID

    Returns:
        JSON object with full ticket details including description, comments, attachments.
    """
    try:
        data = await _ninjaone_request("GET", f"/v2/ticketing/ticket/{ticket_id}")
        return json.dumps(data, indent=2)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="ninjaone_create_ticket",
    annotations={"title": "Create NinjaOne Ticket", "readOnlyHint": False, "destructiveHint": False, "openWorldHint": True}
)
async def ninjaone_create_ticket(
    subject: str,
    description: str,
    board_id: Optional[int] = None,
    device_id: Optional[int] = None,
    priority: Optional[str] = None,
) -> str:
    """Create a new ticket in NinjaOne.

    Args:
        subject: Ticket subject/title
        description: Detailed description of the issue
        board_id: Ticket board to create in (optional)
        device_id: Associate ticket with a specific device ID (optional)
        priority: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL' (optional)

    Returns:
        JSON object with the created ticket's ID and details.
    """
    try:
        body: dict = {"subject": subject, "description": description}
        if board_id:
            body["boardId"] = board_id
        if device_id:
            body["nodeId"] = device_id
        if priority:
            body["priority"] = priority
        data = await _ninjaone_request("POST", "/v2/ticketing/ticket", data=body)
        return json.dumps(data, indent=2)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="ninjaone_add_ticket_comment",
    annotations={"title": "Add Ticket Comment", "readOnlyHint": False, "destructiveHint": False, "openWorldHint": True}
)
async def ninjaone_add_ticket_comment(ticket_id: int, body: str, public: bool = True) -> str:
    """Add a comment to an existing NinjaOne ticket.

    Args:
        ticket_id: The ticket ID to comment on
        body: Comment text content
        public: Whether comment is visible to end users (default: True)

    Returns:
        JSON confirmation of the added comment.
    """
    try:
        data = await _ninjaone_request(
            "POST", f"/v2/ticketing/ticket/{ticket_id}/log-entry",
            data={"body": body, "type": "COMMENT", "public": public}
        )
        return json.dumps(data, indent=2)
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# Policies & Activities
# =============================================================================

@mcp.tool(
    name="ninjaone_list_policies",
    annotations={"title": "List NinjaOne Policies", "readOnlyHint": True, "openWorldHint": True}
)
async def ninjaone_list_policies() -> str:
    """List all policies configured in NinjaOne.

    Returns:
        JSON array of policy objects with id, name, description, nodeRoleId.
    """
    try:
        data = await _ninjaone_request("GET", "/v2/policies")
        return json.dumps(data, indent=2)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="ninjaone_list_activities",
    annotations={"title": "List NinjaOne Activities", "readOnlyHint": True, "openWorldHint": True}
)
async def ninjaone_list_activities(
    device_filter: Optional[str] = None,
    activity_type: Optional[str] = None,
    newer_than: Optional[int] = None,
    page_size: Optional[int] = None,
) -> str:
    """List NinjaOne activity log entries.

    Args:
        device_filter: NQL filter to scope to specific devices (optional)
        activity_type: Filter by type: 'CONDITION', 'PATCH', 'SCRIPT' etc. (optional)
        newer_than: Only return activities newer than this Unix timestamp (optional)
        page_size: Max activities to return (optional, default: 200)

    Returns:
        JSON array of activity objects with id, message, activityType, deviceId, activityTime.
    """
    try:
        params = {}
        if device_filter:
            params["df"] = device_filter
        if activity_type:
            params["activityType"] = activity_type
        if newer_than:
            params["newerThan"] = newer_than
        if page_size:
            params["pageSize"] = min(page_size, 1000)
        data = await _ninjaone_request("GET", "/v2/activities", params=params)
        return _truncate(json.dumps(data, indent=2))
    except Exception as e:
        return _handle_error(e)


if __name__ == "__main__":
    mcp.run()
