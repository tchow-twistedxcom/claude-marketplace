"""Meraki Dashboard API MCP server using FastMCP."""

import os
import json
from typing import Optional, Any
import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP("meraki")

CHARACTER_LIMIT = 25000
API_BASE = os.environ.get("MERAKI_API_URL", "https://api.meraki.com/api/v1")
API_KEY = os.environ.get("MERAKI_API_KEY", "")


def _get_api_key() -> str:
    """Get API key from env or fallback config file."""
    key = API_KEY
    if not key:
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "plugins",
            "meraki-skills", "config", "meraki_config.json"
        )
        if os.path.exists(config_path):
            with open(config_path) as f:
                cfg = json.load(f)
                key = cfg.get("api_key", "")
    return key


async def _meraki_request(
    method: str,
    endpoint: str,
    params: Optional[dict] = None,
    data: Optional[dict] = None,
) -> Any:
    """Make an authenticated request to the Meraki Dashboard API."""
    api_key = _get_api_key()
    if not api_key:
        raise ValueError(
            "MERAKI_API_KEY not set. Provide your Meraki Dashboard API key."
        )

    url = f"{API_BASE.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        response = await client.request(
            method=method.upper(),
            url=url,
            headers=headers,
            params=params,
            json=data,
        )
        if response.status_code == 429:
            raise RuntimeError("Rate limited by Meraki API. Wait and retry.")
        if response.status_code == 404:
            raise ValueError(f"Resource not found: {endpoint}")
        if response.status_code == 401:
            raise ValueError(
                "Unauthorized. Check your MERAKI_API_KEY is valid and has sufficient permissions."
            )
        response.raise_for_status()
        if response.content:
            return response.json()
        return {}


def _truncate(text: str) -> str:
    if len(text) > CHARACTER_LIMIT:
        return text[:CHARACTER_LIMIT] + f"\n\n[Truncated — {len(text)} chars total]"
    return text


def _fmt(data: Any) -> str:
    return _truncate(json.dumps(data, indent=2))


# ─── Organizations ────────────────────────────────────────────────────────────

@mcp.tool()
async def meraki_list_organizations() -> str:
    """List all organizations accessible with the current API key.

    Returns organization IDs, names, URLs, and licensing model.
    Use organization IDs in other tools (meraki_list_networks, meraki_list_devices, etc.).
    """
    result = await _meraki_request("GET", "/organizations")
    return _fmt(result)


@mcp.tool()
async def meraki_get_organization(organization_id: str) -> str:
    """Get details for a specific organization.

    Args:
        organization_id: The Meraki organization ID (get from meraki_list_organizations).

    Returns organization name, URL, API settings, licensing model, and cloud region.
    """
    result = await _meraki_request("GET", f"/organizations/{organization_id}")
    return _fmt(result)


@mcp.tool()
async def meraki_get_organization_inventory(
    organization_id: str,
    used_state: Optional[str] = None,
    search: Optional[str] = None,
) -> str:
    """Get device inventory for an organization.

    Args:
        organization_id: The Meraki organization ID.
        used_state: Filter by 'used' or 'unused'. Leave blank for all.
        search: Search by serial, MAC, or model (e.g. 'MX', 'MS-225').

    Returns list of devices with serial, model, MAC, network assignment, and order info.
    """
    params: dict = {}
    if used_state:
        params["usedState"] = used_state
    if search:
        params["search"] = search
    result = await _meraki_request("GET", f"/organizations/{organization_id}/inventory/devices", params=params)
    return _fmt(result)


@mcp.tool()
async def meraki_get_organization_uplinks_status(organization_id: str) -> str:
    """Get uplink status for all MX appliances in an organization.

    Args:
        organization_id: The Meraki organization ID.

    Returns WAN uplink status, IP addresses, gateway, DNS, and interface details
    for all MX security appliances. Use to check WAN connectivity health across sites.
    """
    result = await _meraki_request("GET", f"/organizations/{organization_id}/uplinks/statuses")
    return _fmt(result)


# ─── Networks ─────────────────────────────────────────────────────────────────

@mcp.tool()
async def meraki_list_networks(
    organization_id: str,
    config_template_id: Optional[str] = None,
    tags: Optional[str] = None,
) -> str:
    """List all networks in an organization.

    Args:
        organization_id: The Meraki organization ID.
        config_template_id: Filter networks bound to a specific config template ID.
        tags: Comma-separated tags to filter networks (e.g. 'branch,retail').

    Returns network IDs, names, types (appliance/switch/wireless/etc.), timezone, and tags.
    """
    params: dict = {}
    if config_template_id:
        params["configTemplateId"] = config_template_id
    if tags:
        params["tags"] = tags.split(",")
    result = await _meraki_request("GET", f"/organizations/{organization_id}/networks", params=params)
    return _fmt(result)


@mcp.tool()
async def meraki_get_network(network_id: str) -> str:
    """Get details for a specific network.

    Args:
        network_id: The Meraki network ID (get from meraki_list_networks).

    Returns network name, type, timezone, tags, notes, and product types.
    """
    result = await _meraki_request("GET", f"/networks/{network_id}")
    return _fmt(result)


@mcp.tool()
async def meraki_get_network_devices(network_id: str) -> str:
    """List all devices in a network.

    Args:
        network_id: The Meraki network ID.

    Returns devices with serial, model, name, MAC, IP, firmware, and location tags.
    """
    result = await _meraki_request("GET", f"/networks/{network_id}/devices")
    return _fmt(result)


@mcp.tool()
async def meraki_get_network_clients(
    network_id: str,
    timespan: int = 86400,
) -> str:
    """List clients that have connected to a network recently.

    Args:
        network_id: The Meraki network ID.
        timespan: Seconds to look back (default 86400 = 24h, max 2592000 = 30 days).

    Returns client MAC, IP, hostname, VLAN, SSID, usage (bytes sent/received), and status.
    """
    result = await _meraki_request(
        "GET", f"/networks/{network_id}/clients",
        params={"timespan": timespan, "perPage": 200}
    )
    return _fmt(result)


@mcp.tool()
async def meraki_get_network_alerts(network_id: str) -> str:
    """Get alert settings and alert history for a network.

    Args:
        network_id: The Meraki network ID.

    Returns configured alert types and their notification recipients.
    """
    result = await _meraki_request("GET", f"/networks/{network_id}/alerts/settings")
    return _fmt(result)


@mcp.tool()
async def meraki_get_network_events(
    network_id: str,
    product_type: Optional[str] = None,
    event_types: Optional[str] = None,
    timespan: int = 7200,
) -> str:
    """Get event log entries for a network.

    Args:
        network_id: The Meraki network ID.
        product_type: Filter by product: 'appliance', 'switch', 'wireless', 'camera'.
        event_types: Comma-separated event type filter (e.g. 'vpn_connectivity_change,dhcp_no_offers').
        timespan: Seconds to look back (default 7200 = 2h, max 604800 = 7 days).

    Returns timestamped events with type, description, device serial, and client details.
    """
    params: dict = {"perPage": 100, "timespan": timespan}
    if product_type:
        params["productType"] = product_type
    if event_types:
        params["includedEventTypes[]"] = event_types.split(",")
    result = await _meraki_request("GET", f"/networks/{network_id}/events", params=params)
    return _fmt(result)


# ─── Devices ──────────────────────────────────────────────────────────────────

@mcp.tool()
async def meraki_get_device(serial: str) -> str:
    """Get details for a specific device by serial number.

    Args:
        serial: Device serial number (e.g. 'Q2AB-1234-5678').

    Returns name, model, MAC, LAN IP, firmware, tags, address, and network assignment.
    """
    result = await _meraki_request("GET", f"/devices/{serial}")
    return _fmt(result)


@mcp.tool()
async def meraki_get_device_uplink(serial: str) -> str:
    """Get uplink information for a device (MX appliances).

    Args:
        serial: Device serial number.

    Returns interface name, status, IP, subnet, gateway, DNS, and public IP for each uplink.
    """
    result = await _meraki_request("GET", f"/devices/{serial}/appliance/uplinks/settings")
    return _fmt(result)


# ─── Wireless ─────────────────────────────────────────────────────────────────

@mcp.tool()
async def meraki_list_ssids(network_id: str) -> str:
    """List all SSIDs configured on a wireless network.

    Args:
        network_id: The Meraki network ID (must include wireless product type).

    Returns SSID name, number, enabled status, auth mode, encryption, VLAN, and band.
    """
    result = await _meraki_request("GET", f"/networks/{network_id}/wireless/ssids")
    return _fmt(result)


@mcp.tool()
async def meraki_get_wireless_status(network_id: str) -> str:
    """Get wireless connection stats and channel utilization for a network.

    Args:
        network_id: The Meraki network ID.

    Returns AP-level connection stats (assoc/auth/DHCP/DNS/success rates) and channel utilization.
    """
    result = await _meraki_request("GET", f"/networks/{network_id}/wireless/channelUtilizationHistory",
                                   params={"timespan": 3600, "resolution": 3600})
    return _fmt(result)


# ─── Switch ───────────────────────────────────────────────────────────────────

@mcp.tool()
async def meraki_list_switch_ports(serial: str) -> str:
    """List all ports on a Meraki switch.

    Args:
        serial: Switch serial number.

    Returns port ID, name, enabled state, VLAN, PoE, link speed, STP, and type (access/trunk).
    """
    result = await _meraki_request("GET", f"/devices/{serial}/switch/ports")
    return _fmt(result)


@mcp.tool()
async def meraki_get_switch_port_statuses(serial: str) -> str:
    """Get live status of all ports on a Meraki switch.

    Args:
        serial: Switch serial number.

    Returns per-port status: link speed, duplex, PoE draw, traffic, and CDP/LLDP neighbor info.
    """
    result = await _meraki_request("GET", f"/devices/{serial}/switch/ports/statuses")
    return _fmt(result)


if __name__ == "__main__":
    mcp.run()
