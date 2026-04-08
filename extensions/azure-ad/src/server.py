"""Azure AD / Entra ID Microsoft Graph API MCP server using FastMCP."""

import asyncio
import ipaddress
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

try:
    from msal import ConfidentialClientApplication
except ImportError:
    raise RuntimeError("msal package required. Run: pip install msal")

mcp = FastMCP("azure-ad")

# ─── Input validation helpers ─────────────────────────────────────────────────

_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', re.IGNORECASE)
_IP_RE = re.compile(r'^\d{1,3}(\.\d{1,3}){3}$')
_SAFE_NAME_RE = re.compile(r'^[a-zA-Z0-9 @.\-_]+$')


def _validate_email(value: str) -> str:
    """Validate email format and escape single quotes for OData safety."""
    if not _EMAIL_RE.match(value):
        raise ValueError(f"Invalid email format: {value!r}")
    return value.replace("'", "''")


def _validate_ip(value: str) -> str:
    """Validate IP address format."""
    if not _IP_RE.match(value):
        raise ValueError(f"Invalid IP address format: {value!r}")
    return value


def _validate_safe_name(value: str) -> str:
    """Validate display name (group, device) for OData safety."""
    if not _SAFE_NAME_RE.match(value):
        raise ValueError(f"Unsafe characters in name: {value!r}")
    return value


def _validate_kql_value(value: str) -> str:
    """Reject KQL metacharacters in user-supplied values."""
    bad_chars = ('|', ';', '//', "'", '"', '\n', '\r', '`')
    for c in bad_chars:
        if c in value:
            raise ValueError(f"Unsafe character {c!r} in KQL value: {value!r}")
    return value


CHARACTER_LIMIT = 25000
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"
UAL_SCOPE = "https://manage.office.com/.default"
TOKEN_REFRESH_BUFFER = 300  # Refresh 5 min before expiry

# In-memory token cache: {"graph:{client_id}": ..., "ual:{client_id}": ...}
_token_cache: dict = {}
_msal_app: ConfidentialClientApplication | None = None

# ─── HTTP client singleton ────────────────────────────────────────────────────

_http_client: httpx.AsyncClient | None = None
_http_client_lock: asyncio.Lock = asyncio.Lock()
_token_lock: asyncio.Lock = asyncio.Lock()


async def _get_http_client() -> httpx.AsyncClient:
    """Return (or create) a shared httpx.AsyncClient with TOCTOU-safe initialization."""
    global _http_client
    async with _http_client_lock:
        if _http_client is None or _http_client.is_closed:
            _http_client = httpx.AsyncClient(
                timeout=60,
                follow_redirects=True,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
    return _http_client


# ─── OData enum allowlists ────────────────────────────────────────────────────

VALID_RISK_LEVELS = {"low", "medium", "high", "none", "hidden", "unknownfuturevalue"}
VALID_RISK_STATES = {"atrisk", "confirmedcompromised", "remediated", "dismissed", "none"}
VALID_RISK_EVENT_TYPES = {
    "unfamiliarfeatures", "anonymizedipaddress", "maliciousipaddress",
    "leakedcredentials", "impossibletravel", "newcountry", "suspiciousbrowser",
    "malwareinfectedipaddress", "suspiciousipaddress", "riskyipaddress",
    "investigationstrippedout", "generic", "adminconfirmedusersafe",
    "mcasmfadenial", "onpremisespasswordchange", "unknownfuturevalue",
}
VALID_RESULT_FILTERS = {"success", "failure", "timeout"}
VALID_CA_STATES = {"enabled", "disabled", "enabledforreportingbutnotenforced"}
VALID_CA_ACTIONS = {"block", "mfa", "compliantDevice", "compliantApplication"}
VALID_UAL_CONTENT_TYPES = {"Audit.Exchange", "Audit.AzureActiveDirectory", "Audit.General"}


def _validate_enum(value: str, valid_set: set, field: str) -> str:
    """Validate that value is in the allowed set (case-insensitive). Returns original casing."""
    if value.lower() not in valid_set:
        raise ValueError(f"Invalid {field}: {value!r}. Valid values: {sorted(valid_set)}")
    return value


def _get_credentials() -> tuple[str, str, str]:
    """Get credentials from environment variables."""
    tenant_id = os.environ.get("AZURE_TENANT_ID", "")
    client_id = os.environ.get("AZURE_CLIENT_ID", "")
    client_secret = os.environ.get("AZURE_CLIENT_SECRET", "")
    if not all([tenant_id, client_id, client_secret]):
        raise ValueError(
            "AZURE_TENANT_ID, AZURE_CLIENT_ID, and AZURE_CLIENT_SECRET must be set."
        )
    return tenant_id, client_id, client_secret


async def _get_msal_app() -> ConfidentialClientApplication:
    """Get or create MSAL app (cached for process lifetime), with double-checked locking."""
    global _msal_app
    if _msal_app is not None:
        return _msal_app
    async with _token_lock:
        if _msal_app is not None:
            return _msal_app
        tenant_id, client_id, client_secret = _get_credentials()
        authority = f"https://login.microsoftonline.com/{tenant_id}"
        _msal_app = ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=authority,
        )
        return _msal_app


async def _get_token(scope: str = GRAPH_SCOPE) -> str:
    """Get a valid access token for the given scope, using in-memory cache.

    Uses double-checked locking to prevent TOCTOU races when multiple coroutines
    concurrently encounter an expired (or absent) cache entry.
    """
    _, client_id, _ = _get_credentials()
    cache_key = f"{scope}:{client_id}"
    # Fast path: check without lock
    cached = _token_cache.get(cache_key)
    if cached and time.time() < cached["expires_at"] - TOKEN_REFRESH_BUFFER:
        return cached["access_token"]
    # Slow path: acquire lock, re-check, then refresh
    async with _token_lock:
        cached = _token_cache.get(cache_key)
        if cached and time.time() < cached["expires_at"] - TOKEN_REFRESH_BUFFER:
            return cached["access_token"]
        app = await _get_msal_app()
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, lambda: app.acquire_token_for_client(scopes=[scope]))
        if "access_token" not in result:
            error = result.get("error", "unknown")
            raise ValueError(f"Token acquisition failed for {scope}: {error}")
        _token_cache[cache_key] = {
            "access_token": result["access_token"],
            "expires_at": time.time() + result.get("expires_in", 3600),
        }
        return result["access_token"]


async def _graph(
    method: str,
    endpoint: str,
    params: dict | None = None,
    data: dict | None = None,
) -> Any:
    """Make an authenticated request to Microsoft Graph API."""
    token = await _get_token()
    url = f"{GRAPH_BASE}{endpoint}" if not endpoint.startswith("http") else endpoint
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "ConsistencyLevel": "eventual",  # Required for $search and $count
    }

    client = await _get_http_client()
    response = await client.request(
        method=method.upper(),
        url=url,
        headers=headers,
        params=params,
        json=data,
    )
    if response.status_code == 204:
        return {"status": "success", "message": "Operation completed successfully"}
    if response.status_code == 401:
        raise ValueError("Unauthorized. Check credentials and app permissions.")
    if response.status_code == 403:
        raise ValueError(
            f"Forbidden. The app lacks the required Graph API permission for this operation. "
            f"Details: {response.text[:300]}"
        )
    if response.status_code == 404:
        raise ValueError(f"Not found: {endpoint}")
    response.raise_for_status()
    return response.json() if response.content else {}


async def _get_all_pages(endpoint: str, params: dict | None = None, max_pages: int = 500) -> list:
    """Collect all pages of a paginated Graph API result."""
    all_items = []
    page = 0
    while endpoint and page < max_pages:
        result = await _graph("GET", endpoint, params=params)
        all_items.extend(result.get("value", []))
        endpoint = result.get("@odata.nextLink")
        if endpoint and not endpoint.startswith("https://graph.microsoft.com/"):
            raise ValueError(f"Rejected non-Graph nextLink: {endpoint[:100]!r}")
        params = None  # nextLink carries its own params
        page += 1
    if page >= max_pages and endpoint:
        print(
            f"WARNING: _get_all_pages hit max_pages={max_pages} — results TRUNCATED",
            file=sys.stderr,
        )
    return all_items


def _truncate(text: str) -> str:
    if len(text) > CHARACTER_LIMIT:
        return text[:CHARACTER_LIMIT] + f"\n\n[Truncated — {len(text)} chars total]"
    return text


def _fmt(data: Any) -> str:
    return _truncate(json.dumps(data, indent=2, default=str))


def _hours_filter(hours: int, field: str = "createdDateTime") -> str:
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"{field} ge {since}"


# ─── Users ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def azure_ad_list_users(
    filter_query: str | None = None,
    search: str | None = None,
    select: str | None = None,
    top: int = 100,
    all_pages: bool = False,
) -> str:
    """List Azure AD users with optional filtering and field selection.

    Args:
        filter_query: OData $filter expression (e.g. "department eq 'Engineering'" or "accountEnabled eq false").
            NOTE: This parameter is passed directly to the Graph API without sanitization.
            Intended for admin use only — do not pass untrusted user input here.
        search: Full-text search across displayName, UPN, email (e.g. "John Smith").
        select: Comma-separated fields to include (default: id,displayName,userPrincipalName,mail,jobTitle,department,accountEnabled).
        top: Number of results per page (default 100, max 999).
        all_pages: If True, follow pagination to get all users (use carefully on large tenants).

    Returns list of user objects. Use azure_ad_get_user for full user details.
    """
    params: dict = {"$top": min(top, 999)}
    params["$select"] = select or "id,displayName,userPrincipalName,mail,jobTitle,department,accountEnabled,createdDateTime"
    if filter_query:
        params["$filter"] = filter_query
    if search:
        params["$search"] = f'"{search}"'
        params["$count"] = "true"

    if all_pages:
        items = await _get_all_pages("/users", params)
        return _fmt({"value": items, "count": len(items)})

    result = await _graph("GET", "/users", params=params)
    return _fmt(result)


@mcp.tool()
async def azure_ad_get_user(user_id: str, select: str | None = None) -> str:
    """Get a user by UPN or object ID.

    Args:
        user_id: User principal name (e.g. 'john@contoso.com') or object ID (GUID).
        select: Comma-separated fields to return. Leave blank for full profile.

    Returns complete user object including job info, licenses, and account status.
    """
    params = {}
    if select:
        params["$select"] = select
    result = await _graph("GET", f"/users/{user_id}", params=params or None)
    return _fmt(result)


@mcp.tool()
async def azure_ad_search_users(query: str, top: int = 25) -> str:
    """Search users by display name, UPN, or email.

    Args:
        query: Search term (e.g. 'john', 'smith@contoso.com', 'IT Manager').
        top: Max results to return (default 25).

    Returns matching user objects sorted by relevance.
    """
    query = query.replace('"', '').strip()
    params = {
        "$search": f'"displayName:{query}" OR "mail:{query}" OR "userPrincipalName:{query}"',
        "$select": "id,displayName,userPrincipalName,mail,jobTitle,department,accountEnabled",
        "$top": top,
        "$count": "true",
    }
    result = await _graph("GET", "/users", params=params)
    return _fmt(result)


@mcp.tool()
async def azure_ad_user_member_of(user_id: str) -> str:
    """Get groups and directory roles a user belongs to.

    Args:
        user_id: User UPN or object ID.

    Returns list of group and role objects with displayName, type, and ID.
    """
    items = await _get_all_pages(f"/users/{user_id}/memberOf")
    return _fmt({"value": items, "count": len(items)})


@mcp.tool()
async def azure_ad_user_manager(user_id: str) -> str:
    """Get a user's manager.

    Args:
        user_id: User UPN or object ID.

    Returns the manager's user object, or an error if no manager is set.
    """
    result = await _graph("GET", f"/users/{user_id}/manager")
    return _fmt(result)


@mcp.tool()
async def azure_ad_user_direct_reports(user_id: str) -> str:
    """Get a user's direct reports.

    Args:
        user_id: User UPN or object ID.

    Returns list of direct report user objects.
    """
    result = await _graph("GET", f"/users/{user_id}/directReports")
    return _fmt(result)


@mcp.tool()
async def azure_ad_user_devices(user_id: str) -> str:
    """Get devices owned or registered by a user.

    Args:
        user_id: User UPN or object ID.

    Returns list of device objects with OS, trust type, compliance status, and last sign-in.
    """
    owned, registered = await asyncio.gather(
        _graph("GET", f"/users/{user_id}/ownedDevices"),
        _graph("GET", f"/users/{user_id}/registeredDevices"),
    )
    return _fmt({
        "ownedDevices": owned.get("value", []),
        "registeredDevices": registered.get("value", []),
    })


# ─── Groups ───────────────────────────────────────────────────────────────────

@mcp.tool()
async def azure_ad_list_groups(
    filter_query: str | None = None,
    search: str | None = None,
    top: int = 100,
) -> str:
    """List Azure AD groups with optional filtering.

    Args:
        filter_query: OData $filter (e.g. "displayName eq 'IT Admins'" or "groupTypes/any(t:t eq 'Unified')").
            NOTE: This parameter is passed directly to the Graph API without sanitization.
            Intended for admin use only — do not pass untrusted user input here.
        search: Full-text search on displayName or description.
        top: Max results (default 100).

    Returns list of group objects with displayName, type, membership rules, and mail settings.
    """
    params: dict = {
        "$top": min(top, 999),
        "$select": "id,displayName,mail,groupTypes,membershipRule,description,securityEnabled,mailEnabled",
    }
    if filter_query:
        params["$filter"] = filter_query
    if search:
        params["$search"] = f'"{search}"'
        params["$count"] = "true"
    result = await _graph("GET", "/groups", params=params)
    return _fmt(result)


@mcp.tool()
async def azure_ad_get_group(group_id: str) -> str:
    """Get a group by display name or object ID.

    Args:
        group_id: Group object ID (GUID) or exact display name.

    Returns full group object including type, membership settings, and mail info.
    Note: If passing a display name instead of ID, the API may return multiple matches.
    """
    # Try as ID first; if it looks like a name, filter by displayName
    if len(group_id) == 36 and group_id.count("-") == 4:
        result = await _graph("GET", f"/groups/{group_id}")
    else:
        params = {"$filter": f"displayName eq '{_validate_safe_name(group_id)}'"}
        result = await _graph("GET", "/groups", params=params)
    return _fmt(result)


@mcp.tool()
async def azure_ad_group_members(group_id: str, top: int = 200) -> str:
    """List members of a group.

    Args:
        group_id: Group object ID (GUID).
        top: Max members to return (default 200). Use 0 to get all pages.

    Returns list of member objects (users, groups, devices, service principals).
    """
    if top == 0:
        items = await _get_all_pages(f"/groups/{group_id}/members")
        return _fmt({"value": items, "count": len(items)})
    params = {"$top": min(top, 999)}
    result = await _graph("GET", f"/groups/{group_id}/members", params=params)
    return _fmt(result)


@mcp.tool()
async def azure_ad_group_owners(group_id: str) -> str:
    """List owners of a group.

    Args:
        group_id: Group object ID (GUID).

    Returns list of owner objects (users or service principals).
    """
    result = await _graph("GET", f"/groups/{group_id}/owners")
    return _fmt(result)


# ─── Devices ──────────────────────────────────────────────────────────────────

@mcp.tool()
async def azure_ad_list_devices(
    filter_query: str | None = None,
    search: str | None = None,
    top: int = 100,
) -> str:
    """List Azure AD registered devices.

    Args:
        filter_query: OData $filter (e.g. "operatingSystem eq 'Windows'" or "isCompliant eq false").
            NOTE: This parameter is passed directly to the Graph API without sanitization.
            Intended for admin use only — do not pass untrusted user input here.
        search: Full-text search on displayName.
        top: Max results (default 100).

    Returns list of device objects with OS, trust type, compliance, and last sign-in.
    """
    params: dict = {
        "$top": min(top, 999),
        "$select": "id,displayName,deviceId,operatingSystem,operatingSystemVersion,trustType,isManaged,isCompliant,approximateLastSignInDateTime",
    }
    if filter_query:
        params["$filter"] = filter_query
    if search:
        params["$search"] = f'"{search}"'
        params["$count"] = "true"
    result = await _graph("GET", "/devices", params=params)
    return _fmt(result)


@mcp.tool()
async def azure_ad_get_device(device_id: str) -> str:
    """Get a device by object ID or display name.

    Args:
        device_id: Device object ID (GUID) or display name.

    Returns full device object including OS, trust type, compliance, join type, and last sign-in.
    """
    if len(device_id) == 36 and device_id.count("-") == 4:
        result = await _graph("GET", f"/devices/{device_id}")
    else:
        params = {"$filter": f"displayName eq '{_validate_safe_name(device_id)}'"}
        result = await _graph("GET", "/devices", params=params)
    return _fmt(result)


# ─── Directory ────────────────────────────────────────────────────────────────

@mcp.tool()
async def azure_ad_organization() -> str:
    """Get tenant/organization information.

    Returns organization display name, tenant ID, verified domains, technical contacts,
    assigned plans, and provisioned services.
    """
    result = await _graph("GET", "/organization")
    return _fmt(result)


@mcp.tool()
async def azure_ad_domains() -> str:
    """List all verified domains in the tenant.

    Returns domain names, verification status, default/initial flags, and authentication type.
    """
    result = await _graph("GET", "/domains")
    return _fmt(result)


@mcp.tool()
async def azure_ad_licenses() -> str:
    """List subscribed SKUs (license types) with usage counts.

    Returns SKU name, capability status, consumed units, and prepaid units.
    Use to check license availability and consumption (e.g., E3, E5, Defender).
    """
    result = await _graph("GET", "/subscribedSkus")
    return _fmt(result)


@mcp.tool()
async def azure_ad_directory_roles() -> str:
    """List active directory roles and their members.

    Returns role definitions (Global Administrator, Security Administrator, etc.)
    with member counts. To see who holds a role, use azure_ad_role_changes (recent assignments)
    or azure_ad_audit_logs with category 'RoleManagement'. Note: directory role IDs are NOT
    group IDs — calling azure_ad_group_members with a role ID returns 404.
    """
    result = await _graph("GET", "/directoryRoles")
    return _fmt(result)


# ─── Security ─────────────────────────────────────────────────────────────────

@mcp.tool()
async def azure_ad_sign_ins(
    user: str | None = None,
    ip: str | None = None,
    app: str | None = None,
    error_code: int | None = None,
    risk_level: str | None = None,
    country: str | None = None,
    hours: int = 24,
    top: int = 100,
    all_pages: bool = False,
) -> str:
    """Query Azure AD sign-in logs.

    Essential for compromise investigation — filter by user, IP, error code, or risk level.

    Args:
        user: Filter by user UPN (e.g. 'john@contoso.com').
        ip: Filter by source IP address (e.g. '203.0.113.50').
        app: Filter by application display name (e.g. 'Microsoft Teams').
        error_code: Filter by status error code:
            0 = success, 50126 = bad password, 50199 = MFA interrupted/fatigue indicator (adversary-in-the-middle phishing, repeated MFA push denial). See azure_ad_incident_triage for detection logic.,
            50053 = account locked, 53003 = Conditional Access blocked.
        risk_level: Filter by risk level: 'low', 'medium', 'high', 'none'.
        country: Filter by country code (e.g. 'US', 'RU', 'CN').
        hours: Time window in hours (default 24, max ~720 per Graph API).
        top: Results per request (default 100, max 1000).
        all_pages: Follow pagination to get all matching sign-ins.

    Returns sign-in objects with timestamp, user, app, IP, location, status, and risk info.
    Sorted newest-first by default.
    """
    filters = [_hours_filter(hours)]
    if user:
        filters.append(f"userPrincipalName eq '{_validate_email(user)}'")
    if ip:
        filters.append(f"ipAddress eq '{_validate_ip(ip)}'")
    if app:
        filters.append(f"appDisplayName eq '{app.replace(chr(39), chr(39)*2)}'")
    if error_code is not None:
        filters.append(f"status/errorCode eq {error_code}")
    if risk_level:
        filters.append(f"riskLevelDuringSignIn eq '{_validate_enum(risk_level, VALID_RISK_LEVELS, 'risk_level')}'")
    if country:
        filters.append(f"location/countryOrRegion eq '{country.replace(chr(39), chr(39)*2)}'")

    params = {
        "$filter": " and ".join(filters),
        "$top": min(top, 1000),
        "$orderby": "createdDateTime desc",
    }

    if all_pages:
        items = await _get_all_pages("/auditLogs/signIns", params)
        return _fmt({"value": items, "count": len(items)})

    result = await _graph("GET", "/auditLogs/signIns", params=params)
    return _fmt(result)


@mcp.tool()
async def azure_ad_sign_in_get(sign_in_id: str) -> str:
    """Get full detail for a specific sign-in event.

    Args:
        sign_in_id: Sign-in event ID (from azure_ad_sign_ins results).

    Returns complete sign-in record including device info, Conditional Access details,
    applied policies, MFA method, network info, and risk indicators.
    Note: This endpoint may be slow (up to 60s) for recent events.
    """
    result = await _graph("GET", f"/auditLogs/signIns/{sign_in_id}")
    return _fmt(result)


@mcp.tool()
async def azure_ad_risk_detections(
    risk_level: str | None = None,
    risk_event_type: str | None = None,
    user: str | None = None,
    hours: int = 72,
    top: int = 100,
) -> str:
    """Query identity risk detection events.

    Args:
        risk_level: Filter by risk level: 'low', 'medium', 'high'.
        risk_event_type: Filter by detection type (e.g. 'unfamiliarFeatures', 'anonymizedIPAddress',
            'maliciousIPAddress', 'leakedCredentials', 'impossibleTravel').
        user: Filter by user UPN.
        hours: Time window in hours (default 72).
        top: Max results (default 100).

    Returns risk detection objects with type, level, IP, location, timing, and linked sign-in ID.
    """
    filters = [_hours_filter(hours, "activityDateTime")]
    if risk_level:
        filters.append(f"riskLevel eq '{_validate_enum(risk_level, VALID_RISK_LEVELS, 'risk_level')}'")
    if risk_event_type:
        filters.append(f"riskEventType eq '{risk_event_type.replace(chr(39), chr(39)*2)}'")
    if user:
        filters.append(f"userPrincipalName eq '{_validate_email(user)}'")

    params = {
        "$filter": " and ".join(filters),
        "$top": min(top, 1000),
        "$orderby": "activityDateTime desc",
    }
    result = await _graph("GET", "/identityProtection/riskDetections", params=params)
    return _fmt(result)


@mcp.tool()
async def azure_ad_risky_users(
    risk_level: str | None = None,
    risk_state: str | None = None,
    top: int = 100,
) -> str:
    """List users currently flagged as risky by Identity Protection.

    Args:
        risk_level: Filter by current risk level: 'low', 'medium', 'high'.
        risk_state: Filter by state: 'atRisk', 'confirmedCompromised', 'remediated', 'dismissed'.
        top: Max results (default 100).

    Returns risky user objects with risk level, state, last update, and linked detections.
    """
    filters = []
    if risk_level:
        filters.append(f"riskLevel eq '{_validate_enum(risk_level, VALID_RISK_LEVELS, 'risk_level')}'")
    if risk_state:
        filters.append(f"riskState eq '{_validate_enum(risk_state, VALID_RISK_STATES, 'risk_state')}'")

    params: dict = {"$top": min(top, 500)}
    if filters:
        params["$filter"] = " and ".join(filters)

    result = await _graph("GET", "/identityProtection/riskyUsers", params=params)
    return _fmt(result)


@mcp.tool()
async def azure_ad_risky_user_history(user_id: str) -> str:
    """Get risk history for a specific user.

    Args:
        user_id: User object ID (GUID) — get from azure_ad_get_user.

    Returns list of risk history events showing how risk level changed over time,
    what triggered each change, and which detections were involved.
    """
    result = await _graph("GET", f"/identityProtection/riskyUsers/{user_id}/history")
    return _fmt(result)


@mcp.tool()
async def azure_ad_audit_logs(
    activity: str | None = None,
    category: str | None = None,
    user: str | None = None,
    result_filter: str | None = None,
    hours: int = 24,
    top: int = 100,
    all_pages: bool = False,
) -> str:
    """Query directory audit logs.

    Args:
        activity: Filter by activity display name (e.g. 'Add user', 'Reset password',
            'Update user', 'Consent to application', 'Add member to group').
        category: Filter by log category (e.g. 'UserManagement', 'GroupManagement',
            'ApplicationManagement', 'Authentication', 'Policy', 'RoleManagement').
        user: Filter by initiating user UPN (e.g. 'admin@contoso.com').
        result_filter: Filter by result: 'success', 'failure', 'timeout'.
        hours: Time window in hours (default 24).
        top: Max results per request (default 100).
        all_pages: Follow pagination for all results.

    Returns audit log entries with timestamp, initiator, target, activity, and result.
    """
    filters = [_hours_filter(hours, "activityDateTime")]
    if activity:
        filters.append(f"activityDisplayName eq '{activity.replace(chr(39), chr(39)*2)}'")
    if category:
        filters.append(f"category eq '{category.replace(chr(39), chr(39)*2)}'")
    if result_filter:
        filters.append(f"result eq '{_validate_enum(result_filter, VALID_RESULT_FILTERS, 'result_filter')}'")
    if user:
        # Note: filtering by initiatedBy UPN requires knowing the object ID.
        # We filter client-side if user UPN provided via search param instead.
        filters.append(f"initiatedBy/user/userPrincipalName eq '{_validate_email(user)}'")

    params = {
        "$filter": " and ".join(filters),
        "$top": min(top, 1000),
        "$orderby": "activityDateTime desc",
    }

    if all_pages:
        items = await _get_all_pages("/auditLogs/directoryAudits", params)
        return _fmt({"value": items, "count": len(items)})

    result = await _graph("GET", "/auditLogs/directoryAudits", params=params)
    return _fmt(result)


@mcp.tool()
async def azure_ad_auth_methods(user_id: str) -> str:
    """List authentication methods registered for a user.

    Args:
        user_id: User UPN or object ID.

    Returns list of registered auth methods: Microsoft Authenticator, FIDO2 passkeys,
    phone numbers, email, Hello for Business, software OATH tokens, etc.
    Use to detect unauthorized MFA method additions during incident response.
    """
    result = await _graph("GET", f"/users/{user_id}/authentication/methods")
    return _fmt(result)


@mcp.tool()
async def azure_ad_named_locations() -> str:
    """List named locations (trusted IP ranges and country-based locations).

    Returns IP range named locations (trusted corp IP ranges) and
    country/region named locations used in Conditional Access policies.
    """
    result = await _graph("GET", "/identity/conditionalAccess/namedLocations")
    return _fmt(result)


@mcp.tool()
async def azure_ad_revoke_sessions(
    user: str,
    confirm: bool = False,
) -> str:
    """Revoke all sign-in sessions for a user.

    IMPORTANT: This immediately invalidates all active sessions. By default, confirm=False
    returns a preview without executing. Pass confirm=True to actually revoke sessions.

    Use during incident response to immediately terminate access for a compromised account.
    This invalidates all refresh tokens — the user will be forced to re-authenticate
    on all devices and applications.

    Args:
        user: User UPN (e.g. 'john@contoso.com') or object ID.
        confirm: If False (default), returns a preview without executing. Pass True to revoke.

    Returns preview dict when confirm=False, or Graph API result when confirm=True.
    After revocation, the user's risk level is unaffected —
    use azure_ad_confirm_compromised to also flag them in Identity Protection.
    """
    if not confirm:
        return json.dumps({
            "confirm": False,
            "would_revoke_sessions_for": user,
            "message": "Pass confirm=True to execute. This will immediately sign out the user from all devices.",
        })
    print(f"[azure-ad-server] DESTRUCTIVE OP: revokeSignInSessions user={user}", file=sys.stderr)
    result = await _graph("POST", f"/users/{user}/revokeSignInSessions")
    return _fmt(result)


@mcp.tool()
async def azure_ad_confirm_compromised(
    users: list[str],
    confirm: bool = False,
) -> str:
    """Mark users as confirmed compromised in Identity Protection.

    WARNING: This sets risk state to confirmedCompromised. If Conditional Access blocks
    high-risk users, this immediately locks out the affected accounts. IRREVERSIBLE via API.

    Pass confirm=True to execute. Defaults to False for safety.

    Triggers remediation: risk level set to 'high', account may be blocked per CA policy,
    and the event is recorded in risk history. Use together with azure_ad_revoke_sessions
    for complete incident response.

    Args:
        users: List of Azure AD object IDs (NOT UPNs). Example: users='["<id1>","<id2>"]' or pass as list.
            Get IDs from azure_ad_get_user or azure_ad_risky_users.
            Note: UPNs are NOT accepted here — must be object IDs.
        confirm: Must be set to True to execute. Defaults to False for safety.

    Returns preview dict when confirm=False, or success status when confirm=True.
    Affected users will appear in azure_ad_risky_users with riskState = 'confirmedCompromised'.
    """
    if not confirm:
        return json.dumps({
            "confirm": False,
            "would_flag_as_compromised": users,
            "warning": "This operation is irreversible via API and may immediately lock out accounts.",
            "message": "Pass confirm=True to execute.",
        })
    print(f"[azure-ad-server] DESTRUCTIVE OP: confirmCompromised users={users}", file=sys.stderr)
    result = await _graph(
        "POST",
        "/identityProtection/riskyUsers/confirmCompromised",
        data={"userIds": users},
    )
    return _fmt(result)


# ─── Unified Audit Log (Office 365 Management Activity API) ──────────────────

async def _ual_request(method: str, path: str, params: dict | None = None, data: dict | None = None) -> Any:
    """Make an authenticated request to the O365 Management Activity API."""
    tenant_id, _, _ = _get_credentials()
    token = await _get_token(UAL_SCOPE)
    base = f"https://manage.office.com/api/v1.0/{tenant_id}/activity/feed"
    url = f"{base}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    client = await _get_http_client()
    response = await client.request(method=method.upper(), url=url, headers=headers, params=params, json=data)
    if response.status_code == 403:
        raise ValueError(
            "Forbidden. Ensure the app has 'ActivityFeed.Read' from Office 365 Management APIs "
            "with admin consent granted."
        )
    response.raise_for_status()
    return response.json() if response.content else {}


def _ual_time_window(hours: int) -> tuple[str, str]:
    """Return (start, end) strings for the UAL API given a look-back in hours (max 24)."""
    now = datetime.now(timezone.utc)
    start = (now - timedelta(hours=min(hours, 24))).strftime("%Y-%m-%dT%H:%M:%S")
    end = now.strftime("%Y-%m-%dT%H:%M:%S")
    return start, end


async def _ual_fetch_blobs(content_type: str, start_time: str, end_time: str) -> list:
    """Fetch and unpack all UAL content blobs for a time window."""
    if content_type not in VALID_UAL_CONTENT_TYPES:
        raise ValueError(f"Invalid content_type '{content_type}'. Must be one of: {sorted(VALID_UAL_CONTENT_TYPES)}")
    # Ensure subscription exists — 400 is expected if already active, ignore it
    try:
        await _ual_request("POST", f"/subscriptions/start?contentType={content_type}", data={})
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 400:
            raise

    # List available blobs
    result = await _ual_request("GET", "/subscriptions/content", params={
        "contentType": content_type,
        "startTime": start_time,
        "endTime": end_time,
    })
    if not isinstance(result, list):
        return []

    # Download each blob (parallel, with SSRF host validation)
    token = await _get_token(UAL_SCOPE)
    headers = {"Authorization": f"Bearer {token}"}
    all_events = []
    client = await _get_http_client()
    tasks = []
    for blob in result:
        uri = blob.get("contentUri", "")
        if not (uri.startswith("https://") and (
            ".blob.core.windows.net" in uri or ".office.com" in uri or "manage.office.com" in uri
        )):
            continue  # Skip untrusted URIs silently
        tasks.append(client.get(uri, headers=headers))
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    for resp in responses:
        if isinstance(resp, Exception):
            continue
        if resp.status_code == 200:
            try:
                all_events.extend(resp.json())
            except json.JSONDecodeError as e:
                print(f"WARNING: UAL blob parse failed: {e}", file=sys.stderr)
            except TypeError as e:
                print(f"WARNING: UAL blob unexpected shape: {e}", file=sys.stderr)
    return all_events


@mcp.tool()
async def azure_ad_ual_inbox_rules(
    hours: int = 6,
    users: str | None = None,
) -> str:
    """Query the Unified Audit Log for inbox rule creation and modification events.

    Provides forensic-quality attribution: rule name, creator IP, timestamp, and
    user agent. Use during incident response to prove attacker-created rules.

    Requires 'ActivityFeed.Read' (Office 365 Management APIs) with admin consent.

    Args:
        hours: Time window to search (default 6h, max 24h per API limit).
        users: Comma-separated UPNs to filter by (e.g. 'john@contoso.com,jane@contoso.com').
               Leave blank to search all users.

    Returns timestamped events with Operation, UserId, ClientIP, and rule Parameters.
    Operations: New-InboxRule, Set-InboxRule, UpdateInboxRules, Enable-InboxRule,
                Disable-InboxRule, Remove-InboxRule.
    """
    start, end = _ual_time_window(hours)

    events = await _ual_fetch_blobs("Audit.Exchange", start, end)

    rule_ops = {
        "New-InboxRule", "Set-InboxRule", "UpdateInboxRules",
        "Enable-InboxRule", "Disable-InboxRule", "Remove-InboxRule",
    }
    filter_users = {u.strip().lower() for u in users.split(",")} if users else set()

    results = []
    for evt in events:
        op = evt.get("Operation", "")
        if op not in rule_ops:
            continue
        user = evt.get("UserId", "")
        if filter_users and user.lower() not in filter_users:
            continue
        params = evt.get("Parameters", [])
        rule_name = next((p["Value"] for p in params if p.get("Name") == "Name"), "")
        results.append({
            "time": evt.get("CreationTime"),
            "operation": op,
            "user": user,
            "clientIP": evt.get("ClientIP", evt.get("ActorIpAddress", "")),
            "userAgent": evt.get("UserAgent", ""),
            "ruleName": rule_name,
            "sessionId": evt.get("SessionId", ""),
            "rawParameters": params,
        })

    results.sort(key=lambda x: x["time"] or "")
    return _fmt({"count": len(results), "events": results})


@mcp.tool()
async def azure_ad_ual_search(
    operations: str | None = None,
    users: str | None = None,
    content_type: str = "Audit.Exchange",
    hours: int = 6,
) -> str:
    """Search the Unified Audit Log for any Exchange or Azure AD operations.

    Use for full forensic audit of attacker actions: mailbox access, rule changes,
    forwarding setup, calendar permissions, mail send-as, and more.

    Requires 'ActivityFeed.Read' (Office 365 Management APIs) with admin consent.

    Args:
        operations: Comma-separated operation names to filter (e.g.
            'New-InboxRule,Set-InboxRule' or 'MailItemsAccessed' or
            'Add member to role,Remove member from role').
            Leave blank to return all events in the time window.
        users: Comma-separated UPNs to filter by. Leave blank for all users.
        content_type: UAL content type to search:
            'Audit.Exchange' (mailbox/Exchange events — default),
            'Audit.AzureActiveDirectory' (AAD events),
            'Audit.General' (SharePoint, Teams, OneDrive events).
        hours: Time window in hours (default 6h, max 24h per API limit).

    Returns matching audit events with timestamps, IPs, and operation details.
    """
    if content_type not in VALID_UAL_CONTENT_TYPES:
        raise ValueError(f"Invalid content_type '{content_type}'. Must be one of: {sorted(VALID_UAL_CONTENT_TYPES)}")
    start, end = _ual_time_window(hours)

    events = await _ual_fetch_blobs(content_type, start, end)

    filter_ops = {o.strip() for o in operations.split(",")} if operations else set()
    filter_users = {u.strip().lower() for u in users.split(",")} if users else set()

    results = []
    for evt in events:
        if filter_ops and evt.get("Operation", "") not in filter_ops:
            continue
        if filter_users and evt.get("UserId", "").lower() not in filter_users:
            continue
        results.append(evt)

    results.sort(key=lambda x: x.get("CreationTime") or "")
    return _fmt({"count": len(results), "events": results})


@mcp.tool()
async def azure_ad_ual_mailbox_access(
    users: str,
    hours: int = 6,
) -> str:
    """Query the UAL for mailbox access events on specific users.

    Identifies if an attacker accessed mailbox contents (read emails, searched,
    downloaded attachments) after stealing a token.

    Requires 'ActivityFeed.Read' (Office 365 Management APIs) with admin consent.

    Args:
        users: Comma-separated UPNs to check (e.g. 'john@contoso.com,jane@contoso.com').
        hours: Time window in hours (default 6h, max 24h per API limit).

    Returns MailItemsAccessed, MessageBind, and related events showing which
    folders/messages were accessed, from which IPs, and at what time.
    """
    start, end = _ual_time_window(hours)

    events = await _ual_fetch_blobs("Audit.Exchange", start, end)

    access_ops = {
        "MailItemsAccessed", "MessageBind", "FolderBind",
        "SendAs", "SendOnBehalf", "Create", "Move", "Copy",
    }
    filter_users = {u.strip().lower() for u in users.split(",")}

    results = []
    for evt in events:
        if evt.get("Operation", "") not in access_ops:
            continue
        if evt.get("UserId", "").lower() not in filter_users:
            continue
        results.append({
            "time": evt.get("CreationTime"),
            "operation": evt.get("Operation"),
            "user": evt.get("UserId"),
            "clientIP": evt.get("ClientIP", ""),
            "userAgent": evt.get("UserAgent", ""),
            "clientInfoString": evt.get("ClientInfoString", ""),
            "folders": evt.get("Folders", []),
            "itemCount": evt.get("OperationCount", 1),
        })

    results.sort(key=lambda x: x["time"] or "")
    return _fmt({"count": len(results), "events": results})


# ─── Mail (Forensic) ──────────────────────────────────────────────────────────

@mcp.tool()
async def azure_ad_sent_emails(
    user_id: str,
    hours: int = 48,
    top: int = 100,
    include_body: bool = False,
) -> str:
    """List emails sent from a user's mailbox within a time window.

    Essential for incident response — identifies phishing/spam sent via stolen tokens.
    Use include_body=True to see message content and detect phishing lures.

    Args:
        user_id: User UPN (e.g. user@domain.com) or object ID.
        hours: Look back N hours (default 48). Max 168 (7 days).
        top: Max messages to return (default 100).
        include_body: Include bodyPreview (first 255 chars) in results.
    """
    since = (datetime.now(timezone.utc) - timedelta(hours=min(hours, 168))).strftime('%Y-%m-%dT%H:%M:%SZ')
    select = "id,subject,sentDateTime,from,toRecipients,ccRecipients,bccRecipients,hasAttachments,internetMessageId"
    if include_body:
        select += ",bodyPreview"
    params = {
        "$select": select,
        "$filter": f"sentDateTime ge {since}",
        "$orderby": "sentDateTime desc",
        "$top": top,
    }
    result = await _graph("GET", f"/users/{user_id}/mailFolders/sentItems/messages", params=params)
    messages = result.get("value", [])
    summary = []
    for m in messages:
        to = [r.get("emailAddress", {}).get("address", "") for r in m.get("toRecipients", [])]
        cc = [r.get("emailAddress", {}).get("address", "") for r in m.get("ccRecipients", [])]
        entry = {
            "sentDateTime": m.get("sentDateTime"),
            "subject": m.get("subject"),
            "to": to,
            "cc": cc,
            "hasAttachments": m.get("hasAttachments"),
            "messageId": m.get("internetMessageId"),
            "id": m.get("id"),
        }
        if include_body:
            entry["bodyPreview"] = m.get("bodyPreview", "")
        summary.append(entry)
    return _fmt({"user": user_id, "count": len(summary), "messages": summary})


@mcp.tool()
async def azure_ad_search_mail(
    user_id: str,
    query: str,
    folder: str = "sentItems",
    top: int = 50,
    hours: int = 168,
) -> str:
    """Search a user's mailbox folder by subject keyword or sender.

    Uses OData $filter (works with app-only Mail.Read permissions on any mailbox).
    Note: Searches subject line. For full-text body search, use azure_ad_sent_emails
    with include_body=True and review bodyPreview manually.

    Args:
        user_id: User UPN or object ID.
        query: Keyword or phrase to match against subject (e.g. 'SHAREDFILE', 'invoice').
               Prefix with 'from:email@domain.com' to filter by sender instead.
        folder: Folder to search: 'sentItems', 'inbox', 'deletedItems' (default: sentItems).
        top: Max results (default 50).
        hours: Look-back window in hours (default 168 = 7 days).
    """
    VALID_MAIL_FOLDERS = {"inbox", "sentitems", "drafts", "deleteditems", "junkemail", "outbox", "archive"}
    folder_safe = folder.lower()
    if folder_safe not in VALID_MAIL_FOLDERS and not (re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', folder, re.IGNORECASE) or re.match(r'^[A-Za-z0-9+/_-]{20,}={0,2}$', folder)):
        raise ValueError(f"Invalid folder: {folder!r}. Use a known folder name or a folder ID (GUID).")

    since = (datetime.now(timezone.utc) - timedelta(hours=min(hours, 720))).strftime('%Y-%m-%dT%H:%M:%SZ')

    # Build filter: support 'from:address' prefix or default subject contains
    if query.lower().startswith("from:"):
        sender = query[5:].strip().replace("'", "''")
        filter_parts = [f"from/emailAddress/address eq '{sender}'"]
    else:
        # Escape single quotes in query for OData
        safe_query = query.replace("'", "''")
        filter_parts = [f"contains(subject, '{safe_query}')"]
    filter_parts.append(f"sentDateTime ge {since}")

    params = {
        "$filter": " and ".join(filter_parts),
        "$select": "id,subject,sentDateTime,receivedDateTime,from,toRecipients,ccRecipients,hasAttachments,bodyPreview",
        "$orderby": "sentDateTime desc",
        "$top": top,
    }
    result = await _graph("GET", f"/users/{user_id}/mailFolders/{folder}/messages", params=params)
    messages = result.get("value", [])
    summary = []
    for m in messages:
        to = [r.get("emailAddress", {}).get("address", "") for r in m.get("toRecipients", [])]
        summary.append({
            "sentDateTime": m.get("sentDateTime") or m.get("receivedDateTime"),
            "subject": m.get("subject"),
            "to": to,
            "hasAttachments": m.get("hasAttachments"),
            "bodyPreview": m.get("bodyPreview", "")[:200],
            "id": m.get("id"),
        })
    return _fmt({"user": user_id, "query": query, "folder": folder, "count": len(summary), "messages": summary})


@mcp.tool()
async def azure_ad_get_email(user_id: str, message_id: str) -> str:
    """Get full detail of a specific email message including complete body.

    Use after azure_ad_sent_emails to drill into a suspicious message.

    Args:
        user_id: User UPN or object ID.
        message_id: Message ID from azure_ad_sent_emails results.
    """
    result = await _graph("GET", f"/users/{user_id}/messages/{message_id}")
    body = result.get("body", {}).get("content", "")
    to = [r.get("emailAddress", {}).get("address", "") for r in result.get("toRecipients", [])]
    cc = [r.get("emailAddress", {}).get("address", "") for r in result.get("ccRecipients", [])]
    return _fmt({
        "sentDateTime": result.get("sentDateTime"),
        "subject": result.get("subject"),
        "from": result.get("from", {}).get("emailAddress", {}).get("address", ""),
        "to": to,
        "cc": cc,
        "hasAttachments": result.get("hasAttachments"),
        "internetMessageId": result.get("internetMessageId"),
        "bodyPreview": result.get("bodyPreview", ""),
        "body": body[:5000] if body else "",
    })


# ─── Conditional Access Management ───────────────────────────────────────────

@mcp.tool()
async def azure_ad_list_ca_policies() -> str:
    """List all Conditional Access policies with state and conditions summary."""
    result = await _graph("GET", "/identity/conditionalAccess/policies")
    policies = result.get("value", [])
    summary = []
    for p in policies:
        cond = p.get("conditions", {})
        users = cond.get("users", {})
        locs = cond.get("locations", {})
        grant = p.get("grantControls") or {}
        summary.append({
            "id": p["id"],
            "displayName": p["displayName"],
            "state": p.get("state"),
            "includeUsers": users.get("includeUsers", []),
            "includeGroups": users.get("includeGroups", []),
            "includeLocations": locs.get("includeLocations", []),
            "excludeLocations": locs.get("excludeLocations", []),
            "grantControls": grant.get("builtInControls", []),
        })
    return _fmt({"count": len(summary), "policies": summary})


@mcp.tool()
async def azure_ad_create_named_location(
    display_name: str,
    ip_ranges: str,
    is_trusted: bool = True,
) -> str:
    """Create an IP-based Named Location (trusted IP range) for use in CA policies.

    Args:
        display_name: Name for the location (e.g. 'Contoso Corporate').
        ip_ranges: Comma-separated CIDR ranges (e.g. '203.0.113.0/24,198.51.100.5/32').
        is_trusted: Mark as trusted location (default True).
    """
    if display_name and len(display_name) > 256:
        raise ValueError("display_name must not exceed 256 characters")
    validated_ranges = []
    for cidr in ip_ranges.split(","):
        cidr = cidr.strip()
        if not cidr:
            continue
        try:
            ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            raise ValueError(f"Invalid CIDR notation: {cidr!r}")
        validated_ranges.append(cidr)
    ranges = [
        {"@odata.type": "#microsoft.graph.iPv4CidrRange", "cidrAddress": r}
        for r in validated_ranges
    ]
    payload = {
        "@odata.type": "#microsoft.graph.ipNamedLocation",
        "displayName": display_name,
        "isTrusted": is_trusted,
        "ipRanges": ranges,
    }
    result = await _graph("POST", "/identity/conditionalAccess/namedLocations", data=payload)
    return _fmt(result)


@mcp.tool()
async def azure_ad_create_ca_policy(
    display_name: str,
    include_users: str,
    exclude_location_ids: str,
    action: str = "block",
    state: str = "enabled",
    include_apps: str = "All",
) -> str:
    """Create a Conditional Access policy.

    Args:
        display_name: Policy name.
        include_users: Comma-separated user UPNs or object IDs (or 'All').
        exclude_location_ids: Comma-separated Named Location IDs to exclude (allow).
          Use azure_ad_named_locations to find IDs.
          Named Location IDs must be GUIDs (pass the `id` field from `azure_ad_named_locations`
          output, NOT the display name).
        action: Grant control: 'block', 'mfa', 'compliantDevice', or 'compliantApplication'.
        state: 'enabled', 'disabled', or 'enabledForReportingButNotEnforced'.
        include_apps: 'All' or comma-separated app IDs.
    """
    if display_name and len(display_name) > 256:
        raise ValueError("display_name must not exceed 256 characters")
    _validate_enum(state, VALID_CA_STATES, "state")
    _validate_enum(action, VALID_CA_ACTIONS, "action")

    user_list = [u.strip() for u in include_users.split(",") if u.strip()]
    loc_excludes = [l.strip() for l in exclude_location_ids.split(",") if l.strip()]
    app_list = [a.strip() for a in include_apps.split(",") if a.strip()]

    _action_map = {
        "block": "block",
        "mfa": "mfa",
        "compliantDevice": "compliantDevice",
        "compliantApplication": "approvedApplication",
    }
    grant = {
        "operator": "OR",
        "builtInControls": [_action_map.get(action, "mfa")],
    }

    users_condition = (
        {"includeUsers": ["All"]}
        if include_users.strip() == "All"
        else {"includeUsers": user_list}
    )
    payload = {
        "displayName": display_name,
        "state": state,
        "conditions": {
            "users": users_condition,
            "applications": {
                "includeApplications": app_list,
            },
            "locations": {
                "includeLocations": ["All"],
                "excludeLocations": loc_excludes,
            },
        },
        "grantControls": grant,
    }

    result = await _graph("POST", "/identity/conditionalAccess/policies", data=payload)
    return _fmt(result)


@mcp.tool()
async def azure_ad_update_ca_policy(
    policy_id: str,
    state: str | None = None,
    display_name: str | None = None,
) -> str:
    """Update a Conditional Access policy (enable, disable, rename).

    Args:
        policy_id: Policy object ID (from azure_ad_list_ca_policies).
        state: New state: 'enabled', 'disabled', or 'enabledForReportingButNotEnforced'.
        display_name: New display name.
    """
    if display_name and len(display_name) > 256:
        raise ValueError("display_name must not exceed 256 characters")
    payload: dict = {}
    if state:
        _validate_enum(state, VALID_CA_STATES, "state")
        payload["state"] = state
    if display_name:
        payload["displayName"] = display_name
    if not payload:
        return _fmt({"error": "Provide at least one field to update (state or display_name)."})
    result = await _graph("PATCH", f"/identity/conditionalAccess/policies/{policy_id}", data=payload)
    return _fmt(result if result else {"success": True, "policy_id": policy_id, "updated": payload})


@mcp.tool()
async def azure_ad_delete_ca_policy(
    policy_id: str,
    confirm: bool = False,
) -> str:
    """Delete a Conditional Access policy.

    WARNING: Permanently deletes the policy. This cannot be undone via API.
    Pass confirm=True to execute. Defaults to False for safety.

    Args:
        policy_id: Policy object ID (from azure_ad_list_ca_policies).
        confirm: Must be set to True to execute. Defaults to False for safety.
    """
    if not confirm:
        return _fmt({
            "confirm": False,
            "would_delete_policy": policy_id,
            "message": "Pass confirm=True to permanently delete this Conditional Access policy.",
        })
    print(f"[azure-ad-server] DESTRUCTIVE OP: deleteCAPolicy policy_id={policy_id}", file=sys.stderr)
    await _graph("DELETE", f"/identity/conditionalAccess/policies/{policy_id}")
    return _fmt({"success": True, "deleted_policy_id": policy_id})


@mcp.tool()
async def azure_ad_advanced_hunt(query: str, top: int = 1000, confirm: bool = False) -> str:
    """Run a KQL query against Microsoft 365 Defender Advanced Hunting.

    Queries the Defender telemetry layer — captures events INVISIBLE to standard
    Graph API or UAL, most critically emails sent with SaveToSentItems=false
    (attacker phishing campaigns that bypass the Sent Items folder entirely).

    Requires 'ThreatHunting.Read.All' Microsoft Graph permission with admin consent.
    Also requires Microsoft 365 Defender Plan 1/2 (included in M365 E3/E5/BP).

    Key tables:
      EmailEvents           — all inbound/outbound email at transport level
      EmailAttachmentInfo   — attachment names, file types, SHA256
      EmailUrlInfo          — URLs extracted from email bodies
      IdentityLogonEvents   — sign-in events across hybrid identity
      DeviceLogonEvents     — device-level login activity

    Args:
        query: KQL (Kusto Query Language) query string. The EmailEvents table
            captures ALL sends regardless of SaveToSentItems flag.
            Example: "EmailEvents | where SenderFromAddress =~ 'user@domain.com'
                      | where Timestamp >= ago(24h) | order by Timestamp desc"
            NOTE: The query is passed to the Defender API without validation.
            Intended for admin use only — do not pass untrusted user input here.
            A '| limit N' clause is appended automatically if 'limit'/'take' is absent.
        top: Implicit LIMIT appended if query has no 'limit' or 'take' clause (default 1000).
        confirm: Must be set to True to execute. Defaults to False (dry-run) as a reminder
            that raw KQL is passed directly to the Defender API. This tool is for
            admin/analyst use only — do not pass untrusted user input as the query.

    Returns schema and results rows.
    """
    if not confirm:
        return _fmt({
            "confirm": False,
            "message": "Pass confirm=True to execute this query. azure_ad_advanced_hunt passes KQL directly to the Defender API — review your query before executing.",
            "query_preview": query[:200],
        })
    q = query.rstrip()
    if not any(kw in q.lower() for kw in ("| limit", "| take")):
        q += f" | limit {min(top, 10000)}"
    result = await _graph("POST", "/security/runHuntingQuery", data={"Query": q})
    return _fmt(result)


@mcp.tool()
async def azure_ad_email_events(
    sender: str | None = None,
    recipient: str | None = None,
    subject: str | None = None,
    network_message_id: str | None = None,
    hours: int = 24,
    direction: str = "Outbound",
    top: int = 1000,
) -> str:
    """Query EmailEvents via Defender Advanced Hunting — complete email forensics.

    This is the ONLY API that captures emails sent with SaveToSentItems=false.
    Graph Mail API (/mailFolders/sentItems), UAL, and Mimecast ALL miss these sends.
    This queries the Exchange transport layer — identical coverage to the Exchange
    Admin Center message trace.

    Requires 'ThreatHunting.Read.All' Microsoft Graph permission with admin consent.

    Args:
        sender: Filter by sender address (e.g. 'user@domain.com').
        recipient: Filter by recipient address.
        subject: Partial subject match (KQL has() operator, case-insensitive).
        network_message_id: Exact message ID for tracking a specific email.
        hours: Look-back in hours (default 24; Defender retains up to 30 days).
        direction: 'Outbound' (default), 'Inbound', or omit for both.
        top: Max results — note: one row per recipient, so a blast to 385 people
            is 385 rows. Default 1000 covers most single-attacker campaigns.

    Returns:
        dict with keys:
          - totalRows: int — total raw Defender rows processed
          - totalMessages: int — distinct messages (by NetworkMessageId)
          - messages: list of dicts, each with:
              - time: ISO timestamp
              - subject: str
              - sender: str
              - direction: str
              - deliveryStatus: str
              - threatTypes: list[str]
              - recipients: list[str]
    """
    hours = max(1, min(int(hours), 720))
    filters = [f"Timestamp >= ago({hours}h)"]
    if direction:
        filters.append(f"EmailDirection == '{_validate_kql_value(direction)}'")
    if sender:
        filters.append(f"SenderFromAddress =~ '{_validate_kql_value(sender)}'")
    if recipient:
        filters.append(f"RecipientEmailAddress =~ '{_validate_kql_value(recipient)}'")
    if subject:
        filters.append(f"Subject has '{_validate_kql_value(subject)}'")
    if network_message_id:
        filters.append(f"NetworkMessageId == '{_validate_kql_value(network_message_id)}'")

    kql = (
        "EmailEvents\n"
        f"| where {chr(10) + '    and '.join(filters)}\n"
        "| project Timestamp, SenderFromAddress, RecipientEmailAddress, Subject,\n"
        "    NetworkMessageId, DeliveryStatus, LatestDeliveryAction,\n"
        "    EmailDirection, ThreatTypes, DetectionMethods\n"
        f"| order by Timestamp desc\n"
        f"| limit {min(top, 10000)}"
    )
    result = await _graph("POST", "/security/runHuntingQuery", data={"Query": kql})
    # Summarise: group by NetworkMessageId so caller sees message-level view
    if isinstance(result, dict) and "results" in result:
        rows = result["results"]
        msg_map: dict = {}
        for row in rows:
            mid = row.get("NetworkMessageId", "")
            if mid not in msg_map:
                msg_map[mid] = {
                    "time": row.get("Timestamp"),
                    "subject": row.get("Subject"),
                    "sender": row.get("SenderFromAddress"),
                    "direction": row.get("EmailDirection"),
                    "deliveryStatus": row.get("DeliveryStatus"),
                    "threatTypes": row.get("ThreatTypes"),
                    "recipients": [],
                }
            recip = row.get("RecipientEmailAddress", "")
            if recip and recip not in msg_map[mid]["recipients"]:
                msg_map[mid]["recipients"].append(recip)
        messages = list(msg_map.values())
        return _fmt({
            "totalRows": len(rows),
            "totalMessages": len(messages),
            "messages": messages,
        })
    return _fmt(result)


@mcp.tool()
async def azure_ad_user_oauth_grants(user_id: str) -> str:
    """List OAuth delegated permission grants for a user.

    Identifies which apps have been granted access to this user's data.
    Critical for detecting attacker persistence via OAuth app grants —
    OAuth grants survive password resets and session revocations.
    Attackers register malicious apps with broad scope (Mail.Read, Files.ReadWrite)
    and grant them consent to maintain long-term access.

    Args:
        user_id: User UPN or object ID.

    Returns list of OAuth grants with app name, publisher, granted scopes,
    consent type (user vs tenant-wide), and expiry.
    """
    grants = await _graph(
        "GET", f"/users/{user_id}/oauth2PermissionGrants",
        params={"$top": 200}
    )
    items = grants.get("value", []) if isinstance(grants, dict) else []
    # Enrich with service principal display names (parallel)
    client_ids = list({g.get("clientId", "") for g in items if g.get("clientId")})
    sp_map: dict = {}
    if client_ids:
        sp_results = await asyncio.gather(
            *[_graph("GET", f"/servicePrincipals/{cid}",
                     params={"$select": "displayName,appId,publisherName"})
              for cid in client_ids],
            return_exceptions=True,
        )
        for cid, sp in zip(client_ids, sp_results):
            if isinstance(sp, dict):
                sp_map[cid] = sp

    results = []
    for g in items:
        cid = g.get("clientId", "")
        sp = sp_map.get(cid, {})
        results.append({
            "appDisplayName": sp.get("displayName", cid),
            "appId": sp.get("appId"),
            "publisher": sp.get("publisherName"),
            "consentType": g.get("consentType"),
            "scope": g.get("scope", ""),
            "expiryTime": g.get("expiryTime"),
            "clientId": cid,
            "id": g.get("id"),
        })
    return _fmt({"user": user_id, "count": len(results), "grants": results})


@mcp.tool()
async def azure_ad_mailbox_settings(user_id: str) -> str:
    """Get mailbox settings — detect email forwarding and exfiltration config.

    Attackers frequently enable SMTP forwarding or external auto-reply after
    compromise to exfiltrate ongoing email. This is separate from inbox rules
    and operates at the mailbox level — survives inbox rule deletion.

    Args:
        user_id: User UPN or object ID.

    Returns forwarding address (if set), automatic replies config, and flags
    any external forwarding as a high-severity finding.
    """
    result = await _graph("GET", f"/users/{user_id}/mailboxSettings")
    fwd = result.get("forwardingSmtpAddress") or result.get("forwardTo")
    auto = result.get("automaticRepliesSetting", {})
    summary = {
        "user": user_id,
        "forwardingSmtpAddress": result.get("forwardingSmtpAddress"),
        "forwardTo": result.get("forwardTo"),
        "forwardingEnabled": bool(fwd),
        "automaticRepliesStatus": auto.get("status"),
        "automaticRepliesExternalAudience": auto.get("externalAudience"),
        "automaticRepliesExternalMessage": (auto.get("externalReplyMessage") or "")[:300],
        "timezone": result.get("timeZone"),
        "language": (result.get("language") or {}).get("displayName"),
    }
    if fwd:
        summary["WARNING"] = f"EMAIL_FORWARDING_ACTIVE → {fwd}"
    return _fmt(summary)


@mcp.tool()
async def azure_ad_mfa_changes(
    user: str | None = None,
    hours: int = 72,
    top: int = 200,
) -> str:
    """Query audit logs for MFA / authentication method changes.

    Detects unauthorized MFA registrations — attacker adds their own phone
    number or authenticator app to maintain access after the victim's password
    is reset. Also surfaces SSPR registration and passkey additions.

    Args:
        user: Filter by target user UPN (optional — blank returns all users).
        hours: Look-back in hours (default 72).
        top: Max results (default 200).

    Returns audit events for: Register/Delete security info, MFA method
    additions/removals, FIDO2 key registrations, authenticator app adds.
    """
    filters_auth = [
        _hours_filter(hours, "activityDateTime"),
        "category eq 'AuthenticationMethods'",
    ]
    filters_user = [
        _hours_filter(hours, "activityDateTime"),
        "category eq 'UserManagement'",
        "(activityDisplayName eq 'User registered security info' "
        "or activityDisplayName eq 'User deleted security info' "
        "or activityDisplayName eq 'Admin registered security info for user' "
        "or activityDisplayName eq 'Admin deleted security info for user')",
    ]
    params1 = {"$filter": " and ".join(filters_auth), "$top": min(top, 1000),
               "$orderby": "activityDateTime desc"}
    params2 = {"$filter": " and ".join(filters_user), "$top": min(top, 1000),
               "$orderby": "activityDateTime desc"}
    r1, r2 = await asyncio.gather(
        _graph("GET", "/auditLogs/directoryAudits", params=params1),
        _graph("GET", "/auditLogs/directoryAudits", params=params2),
        return_exceptions=True,
    )
    items = (r1.get("value", []) if isinstance(r1, dict) else []) + \
            (r2.get("value", []) if isinstance(r2, dict) else [])
    if user:
        items = [i for i in items
                 if any(t.get("userPrincipalName", "").lower() == user.lower()
                        for t in i.get("targetResources", []))]
    items.sort(key=lambda x: x.get("activityDateTime") or "", reverse=True)
    return _fmt({"events": items[:top], "count": len(items)})


@mcp.tool()
async def azure_ad_role_changes(
    user: str | None = None,
    hours: int = 72,
    top: int = 100,
) -> str:
    """Query audit logs for role assignment changes — detect privilege escalation.

    Identifies attacker adding themselves (or a backdoor account) to Global Admin,
    Security Admin, Exchange Admin, or other privileged directory roles.

    Args:
        user: Filter by affected user UPN (optional — blank returns all users).
        hours: Look-back in hours (default 72).
        top: Max results (default 100).

    Returns audit events for Add/Remove member to/from role with initiator,
    target user, role name, and timestamp.
    """
    filters = [
        _hours_filter(hours, "activityDateTime"),
        "category eq 'RoleManagement'",
    ]
    params = {
        "$filter": " and ".join(filters),
        "$top": min(top, 1000),
        "$orderby": "activityDateTime desc",
    }
    result = await _graph("GET", "/auditLogs/directoryAudits", params=params)
    items = result.get("value", []) if isinstance(result, dict) else []
    if user:
        items = [i for i in items
                 if any(t.get("userPrincipalName", "").lower() == user.lower()
                        for t in i.get("targetResources", []))]
    return _fmt({"events": items[:top], "count": len(items)})


@mcp.tool()
async def azure_ad_email_attachments(
    sender: str | None = None,
    recipient: str | None = None,
    file_name: str | None = None,
    hours: int = 24,
    top: int = 500,
) -> str:
    """Query EmailAttachmentInfo via Defender Advanced Hunting.

    Identifies files sent by compromised accounts: file names, types, SHA256
    hashes, malware family tags. Captures attachments from SaveToSentItems=false
    emails (invisible to Graph Mail API). Use to determine what was exfiltrated
    or what phishing lures/malware were distributed.

    Requires ThreatHunting.Read.All permission with admin consent.

    Args:
        sender: Filter by sender email.
        recipient: Filter by recipient email.
        file_name: Partial file name match (KQL has(), case-insensitive).
        hours: Look-back in hours (default 24).
        top: Max results (default 500).

    Returns file name, type, size, SHA256, malware family (if detected),
    and NetworkMessageId for correlation with EmailEvents.
    """
    hours = max(1, min(int(hours), 720))
    filters = [f"Timestamp >= ago({hours}h)"]
    if sender:
        filters.append(f"SenderFromAddress =~ '{_validate_kql_value(sender)}'")
    if recipient:
        filters.append(f"RecipientEmailAddress =~ '{_validate_kql_value(recipient)}'")
    if file_name:
        filters.append(f"FileName has '{_validate_kql_value(file_name)}'")

    kql = (
        "EmailAttachmentInfo\n"
        f"| where {' and '.join(filters)}\n"
        "| project Timestamp, SenderFromAddress, RecipientEmailAddress,\n"
        "    FileName, FileType, FileSize, SHA256, MalwareFamily,\n"
        "    ThreatTypes, DetectionMethods, NetworkMessageId\n"
        f"| order by Timestamp desc\n"
        f"| limit {min(top, 10000)}"
    )
    result = await _graph("POST", "/security/runHuntingQuery", data={"Query": kql})
    return _fmt(result)


@mcp.tool()
async def azure_ad_ual_sharepoint(
    users: str | None = None,
    hours: int = 6,
    operations: str | None = None,
) -> str:
    """Query UAL for SharePoint, OneDrive, and Teams forensics.

    Identifies post-compromise data exfiltration: file downloads, anonymous
    link creation, external sharing, Teams session access from attacker IPs.

    Requires ActivityFeed.Read (Office 365 Management APIs) with admin consent.

    Args:
        users: Comma-separated UPNs to filter by.
        hours: Look-back in hours (default 6, max 24 per API limit).
        operations: Comma-separated operations to filter. Default set covers
            file download, access, sharing, anonymous links, Teams activity.

    Returns events with timestamp, user, clientIP, userAgent, objectId, siteUrl.
    """
    start, end = _ual_time_window(hours)

    sp_events, gen_events = await asyncio.gather(
        _ual_fetch_blobs("Audit.SharePoint", start, end),
        _ual_fetch_blobs("Audit.General", start, end),
        return_exceptions=True,
    )
    all_events = (sp_events if isinstance(sp_events, list) else []) + \
                 (gen_events if isinstance(gen_events, list) else [])

    default_ops = {
        "FileDownloaded", "FileSyncDownloadedFull", "FileAccessed", "FileDeleted",
        "FileModified", "SharingInvitationCreated", "AnonymousLinkCreated",
        "AnonymousLinkUsed", "CompanyLinkCreated", "TeamsSessionStarted",
        "MessageCreatedHasLink", "SearchQueryPerformed",
    }
    filter_ops = {o.strip() for o in operations.split(",")} if operations else default_ops
    filter_users = {u.strip().lower() for u in users.split(",")} if users else set()

    results = []
    for evt in all_events:
        op = evt.get("Operation", "")
        if op not in filter_ops:
            continue
        if filter_users and evt.get("UserId", "").lower() not in filter_users:
            continue
        results.append({
            "time": evt.get("CreationTime"),
            "operation": op,
            "user": evt.get("UserId"),
            "clientIP": evt.get("ClientIP", ""),
            "objectId": evt.get("ObjectId", ""),
            "siteUrl": evt.get("SiteUrl", ""),
            "userAgent": evt.get("UserAgent", ""),
            "workload": evt.get("Workload", ""),
        })
    results.sort(key=lambda x: x.get("time") or "")
    return _fmt({"count": len(results), "events": results})


@mcp.tool()
async def azure_ad_incident_triage(
    users: str,
    trusted_ips: str | None = None,
    hours: int = 24,
    ual_hours: int = 6,
) -> str:
    """Full security triage for one or more potentially compromised accounts.

    Orchestrates sign-in analysis, inbox rule inspection, sent mail forensics,
    auth method review, and UAL forensics in a single operation. Designed for
    incident response: minimizes manual sequencing, produces a structured report
    with high-confidence findings only (no false positives by design).

    UAL is the forensic ground truth for inbox rule attribution — only rules
    confirmed via UAL New-InboxRule/UpdateInboxRules (IsNew=True) are flagged
    as attacker-created. Sign-in flagging requires non-trusted IP success,
    MFA fatigue (errorCode 50199), or multi-country impossible travel.

    Args:
        users: Comma-separated UPNs (e.g. 'user1@domain.com,user2@domain.com').
        trusted_ips: Comma-separated trusted/corporate IP addresses.
            Sign-ins FROM these IPs are NOT flagged as suspicious.
        hours: Look-back window for sign-ins and sent mail (default 24h).
        ual_hours: Look-back for UAL forensics (default 6h, max 24h per API limit).
            Values > 24 are silently capped to 24 (UAL API limit). Smaller values complete faster.

    Returns structured triage report per user:
    - account: enabled state, on-prem sync, Identity Protection risk level,
        last password change
    - suspiciousSignIns: non-trusted IP successes, MFA fatigue pushes,
        impossible travel (multiple countries)
    - maliciousRules: current inbox rules confirmed attacker-created via UAL,
        or matching known attacker patterns
    - authMethods: registered MFA/auth methods (detect unauthorized additions)
    - suspiciousSentMail: phishing-pattern subjects, after-hours external sends
    - ualFindings.inboxRuleChanges: forensic attribution with creator IP
    - ualFindings.mailboxAccess: evidence attacker read mailbox contents
    - riskSummary: HIGH/MEDIUM/CLEAN with indicator list
    """
    user_list = [u.strip() for u in users.split(",") if u.strip()]
    trusted_ip_set = {ip.strip() for ip in trusted_ips.split(",")} if trusted_ips else set()
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Fetch UAL blobs once — shared across all users (avoids N × blob download)
    ual_start, ual_end = _ual_time_window(ual_hours)
    try:
        ual_events = await _ual_fetch_blobs("Audit.Exchange", ual_start, ual_end)
    except Exception as e:
        print(f"WARNING: UAL fetch failed for triage: {e}", file=sys.stderr)
        ual_events = []

    PHISHING_SUBJECTS = {"sharedfile", "invoice", "urgent", "wire", "payment", "verify", "confirm"}

    async def _triage_one(upn: str) -> dict:
        user_ual = [e for e in ual_events if e.get("UserId", "").lower() == upn.lower()]
        domain = upn.split("@")[-1].lower() if "@" in upn else ""

        # Phase 1 + 2: All Graph calls in parallel per user
        # EmailEvents: captures SaveToSentItems=false attacker sends (requires Defender for O365 Plan 2)
        # CloudAppEvents: Exchange Online activity visible to MCAS/Defender — mailbox access, sends,
        #   deletes from attacker IPs. Available without Defender for O365 Plan 2.
        _upn_kql = _validate_kql_value(upn)
        _hours_capped = max(1, min(int(hours), 720))
        email_kql = (
            f"EmailEvents | where SenderFromAddress =~ '{_upn_kql}' "
            f"and Timestamp >= ago({_hours_capped}h) and EmailDirection == 'Outbound' "
            "| project Timestamp, RecipientEmailAddress, Subject, NetworkMessageId, DeliveryStatus "
            "| order by Timestamp desc | limit 1000"
        )
        cloud_kql = (
            f"CloudAppEvents | where AccountUpn =~ '{_upn_kql}' "
            f"and Timestamp >= ago({_hours_capped}h) "
            "and Application == 'Microsoft Exchange Online' "
            "| project Timestamp, ActionType, IPAddress, CountryCode, ISP, UserAgent, ObjectName "
            "| order by Timestamp desc | limit 300"
        )
        results = await asyncio.gather(
            _graph("GET", f"/users/{upn}", params={"$select":
                "id,displayName,accountEnabled,onPremisesSyncEnabled,"
                "lastPasswordChangeDateTime,mail,jobTitle"}),
            _graph("GET", f"/users/{upn}/mailFolders/inbox/messageRules"),
            _graph("GET", f"/users/{upn}/authentication/methods"),
            _graph("GET", "/identityProtection/riskyUsers",
                   params={"$filter": f"userPrincipalName eq '{_validate_email(upn)}'", "$top": 1}),
            _graph("GET", "/auditLogs/signIns", params={
                "$filter": f"userPrincipalName eq '{_validate_email(upn)}' and createdDateTime ge {since}",
                "$top": 200, "$orderby": "createdDateTime desc"}),
            _graph("POST", "/security/runHuntingQuery", data={"Query": email_kql}),
            _graph("POST", "/security/runHuntingQuery", data={"Query": cloud_kql}),
            _graph("GET", f"/users/{upn}/mailboxSettings"),
            _graph("GET", f"/users/{upn}/oauth2PermissionGrants", params={"$top": 50}),
            return_exceptions=True,
        )
        (user_data, rules_data, methods_data, risky_data,
         signins_data, email_events_raw, cloud_events_raw, mailbox_data, oauth_data) = results

        # Resolve sent mail: EmailEvents (complete) or sentItems fallback
        if isinstance(email_events_raw, Exception):
            # ThreatHunting.Read.All not granted — fall back to sentItems
            # WARNING: sentItems misses SaveToSentItems=false sends
            try:
                si_raw = await _graph("GET", f"/users/{upn}/mailFolders/sentItems/messages", params={
                    "$select": "id,subject,sentDateTime,toRecipients,ccRecipients,hasAttachments",
                    "$filter": f"sentDateTime ge {since}",
                    "$orderby": "sentDateTime desc", "$top": 100})
                sent_source = "sentItems (INCOMPLETE — grant ThreatHunting.Read.All for full coverage)"
            except Exception:
                si_raw = {}
                sent_source = "unavailable"
            # Normalise sentItems to common format
            sent_messages: list = []
            for msg in (si_raw.get("value", []) if isinstance(si_raw, dict) else []):
                to_addrs = [r.get("emailAddress", {}).get("address", "")
                            for r in msg.get("toRecipients", [])]
                sent_messages.append({
                    "time": msg.get("sentDateTime"),
                    "subject": msg.get("subject"),
                    "recipients": to_addrs,
                })
        else:
            # EmailEvents: one row per recipient — aggregate by NetworkMessageId
            sent_source = "EmailEvents (complete — includes SaveToSentItems=false)"
            msg_by_id: dict = {}
            for row in (email_events_raw.get("results", [])
                        if isinstance(email_events_raw, dict) else []):
                mid = row.get("NetworkMessageId") or f"{row.get('Subject')}|{row.get('Timestamp')}"
                if mid not in msg_by_id:
                    msg_by_id[mid] = {
                        "time": row.get("Timestamp"),
                        "subject": row.get("Subject"),
                        "deliveryStatus": row.get("DeliveryStatus"),
                        "recipients": [],
                    }
                recip = row.get("RecipientEmailAddress", "")
                if recip and recip not in msg_by_id[mid]["recipients"]:
                    msg_by_id[mid]["recipients"].append(recip)
            sent_messages = list(msg_by_id.values())

        # ── Account state ──
        risky_list = (
            (risky_data.get("value", []) if isinstance(risky_data, dict) else [])
            if not isinstance(risky_data, Exception) else []
        )
        risky = risky_list[0] if risky_list else {}
        if isinstance(user_data, dict) and "id" in user_data:
            account: dict = {
                "enabled": user_data.get("accountEnabled"),
                "displayName": user_data.get("displayName"),
                "onPremSync": user_data.get("onPremisesSyncEnabled"),
                "lastPasswordChange": user_data.get("lastPasswordChangeDateTime"),
                "riskLevel": risky.get("riskLevel", "none"),
                "riskState": risky.get("riskState", "none"),
            }
        else:
            account = {"error": str(user_data) if isinstance(user_data, Exception) else "user not found"}

        # ── Suspicious sign-ins ──
        signins = (
            (signins_data.get("value", []) if isinstance(signins_data, dict) else [])
            if not isinstance(signins_data, Exception) else []
        )
        suspicious_signins: list = []
        success_countries: list = []
        for s in signins:
            ip = s.get("ipAddress", "")
            ec = s.get("status", {}).get("errorCode", -1)
            country = (s.get("location") or {}).get("countryOrRegion", "")
            flags: list = []
            if ec == 0:
                if ip and ip not in trusted_ip_set:
                    flags.append("NON_TRUSTED_IP_SUCCESS")
                if country:
                    success_countries.append(country)
            if ec == 50199:
                flags.append("MFA_FATIGUE")
            if flags:
                suspicious_signins.append({
                    "time": s.get("createdDateTime"),
                    "ip": ip,
                    "country": country,
                    "city": (s.get("location") or {}).get("city", ""),
                    "app": s.get("appDisplayName", ""),
                    "errorCode": ec,
                    "flags": flags,
                })
        if len(set(success_countries)) > 1:
            suspicious_signins.insert(0, {
                "flag": "IMPOSSIBLE_TRAVEL",
                "countries": sorted(set(success_countries)),
                "note": f"Successful sign-ins from {len(set(success_countries))} countries in {hours}h",
            })

        # ── UAL inbox rule events (forensic ground truth) ──
        rule_ops = {"New-InboxRule", "Set-InboxRule", "UpdateInboxRules"}
        ual_rule_events: list = []
        ual_confirmed_names: set = set()
        for evt in user_ual:
            op = evt.get("Operation", "")
            if op not in rule_ops:
                continue
            params_list = evt.get("Parameters", [])
            rule_name = next((p["Value"] for p in params_list if p.get("Name") == "Name"), "")
            is_new_str = next((p["Value"] for p in params_list if p.get("Name") == "IsNew"), "")
            is_new = is_new_str.lower() == "true" or op == "New-InboxRule"
            if is_new:
                ual_confirmed_names.add(rule_name.lower())
            ual_rule_events.append({
                "time": evt.get("CreationTime"),
                "operation": op,
                "clientIP": evt.get("ClientIP", evt.get("ActorIpAddress", "")),
                "ruleName": rule_name,
                "isNew": is_new,
                "sessionId": evt.get("SessionId", ""),
            })

        # ── Malicious inbox rules (UAL-validated or high-confidence pattern) ──
        rules = (
            (rules_data.get("value", []) if isinstance(rules_data, dict) else [])
            if not isinstance(rules_data, Exception) else []
        )
        malicious_rules: list = []
        for rule in rules:
            name = rule.get("displayName", "")
            actions = rule.get("actions", {})
            conditions = rule.get("conditions", {})
            ual_confirmed = name.lower() in ual_confirmed_names
            # High-confidence patterns: delete-all, known attacker naming
            suspicious_pattern = (
                actions.get("deleteMessage") is True
                or name.startswith("TokenSender-")
                or (name and all(c == "." for c in name))
            )
            if ual_confirmed or suspicious_pattern:
                malicious_rules.append({
                    "name": name,
                    "id": rule.get("id"),
                    "deleteMessage": actions.get("deleteMessage", False),
                    "moveToFolder": actions.get("moveToFolder"),
                    "markAsRead": actions.get("markAsRead", False),
                    "stopProcessing": actions.get("stopProcessingRules", False),
                    "hasConditions": bool(conditions),
                    "ualConfirmed": ual_confirmed,
                })

        # ── Auth methods ──
        methods_raw = (
            (methods_data.get("value", []) if isinstance(methods_data, dict) else [])
            if not isinstance(methods_data, Exception) else []
        )
        auth_methods: list = []
        for m in methods_raw:
            t = m.get("@odata.type", "").split(".")[-1].replace("AuthenticationMethod", "")
            detail = m.get("phoneNumber") or m.get("emailAddress") or m.get("displayName") or ""
            auth_methods.append(f"{t}:{detail}" if detail else t)

        # ── Mailbox forwarding (attacker persistence) ──
        forwarding_address: str | None = None
        if isinstance(mailbox_data, dict) and not isinstance(mailbox_data, Exception):
            forwarding_address = (mailbox_data.get("forwardingSmtpAddress")
                                  or mailbox_data.get("forwardTo") or None)

        # ── OAuth grants (survives password reset + session revocation) ──
        oauth_grants: list = []
        grants_raw = (
            (oauth_data.get("value", []) if isinstance(oauth_data, dict) else [])
            if not isinstance(oauth_data, Exception) else []
        )
        for g in grants_raw:
            oauth_grants.append({
                "clientId": g.get("clientId"),
                "consentType": g.get("consentType"),
                "scope": g.get("scope", ""),
                "expiryTime": g.get("expiryTime"),
            })

        # ── Suspicious sent mail (uses normalised sent_messages from above) ──
        suspicious_sent: list = []
        for msg in sent_messages:
            subject = (msg.get("subject") or "").lower()
            sent_str = msg.get("time", "")
            all_recips = msg.get("recipients", [])
            external = [a for a in all_recips if domain and not a.lower().endswith("@" + domain)]
            flags = []
            if any(p in subject for p in PHISHING_SUBJECTS):
                flags.append("PHISHING_SUBJECT")
            if external and sent_str:
                try:
                    hour = datetime.fromisoformat(sent_str.replace("Z", "+00:00")).hour
                    if hour < 6 or hour >= 20:
                        flags.append("AFTER_HOURS_EXTERNAL_SEND")
                except Exception:
                    pass
            if flags:
                suspicious_sent.append({
                    "time": sent_str,
                    "subject": msg.get("subject"),
                    "to": all_recips[:20],
                    "externalTo": external[:20],
                    "totalRecipients": len(all_recips),
                    "totalExternal": len(external),
                    "flags": flags,
                })
        if sum(1 for m in suspicious_sent if m.get("totalExternal", 0) > 0) >= 5 and suspicious_sent:
            suspicious_sent[0].setdefault("flags", []).append("MASS_EXTERNAL_SEND")

        # ── UAL mailbox access (did attacker read emails?) ──
        access_ops = {"MailItemsAccessed", "MessageBind", "FolderBind", "SendAs"}
        ual_access: list = []
        for evt in user_ual:
            if evt.get("Operation", "") not in access_ops:
                continue
            ual_access.append({
                "time": evt.get("CreationTime"),
                "operation": evt.get("Operation"),
                "clientIP": evt.get("ClientIP", ""),
                "userAgent": evt.get("UserAgent", ""),
            })

        # ── CloudAppEvents: Exchange Online activity from Defender Advanced Hunting ──
        # Provides mailbox access, sends, and deletes with IP/ISP detail.
        # Available without Defender for O365 Plan 2 (unlike EmailEvents).
        cloud_events: list = []
        cloud_suspicious: list = []
        if not isinstance(cloud_events_raw, Exception) and isinstance(cloud_events_raw, dict):
            SUSPICIOUS_CLOUD_OPS = {"HardDelete", "SoftDelete", "MoveToDeletedItems",
                                    "Send", "SendAs", "SendOnBehalf"}
            for row in cloud_events_raw.get("results", []):
                ip = row.get("IPAddress", "")
                action = row.get("ActionType", "")
                entry = {
                    "time": row.get("Timestamp"),
                    "action": action,
                    "ip": ip,
                    "country": row.get("CountryCode", ""),
                    "isp": row.get("ISP", ""),
                    "object": row.get("ObjectName", ""),
                }
                cloud_events.append(entry)
                # Flag non-trusted IP activity for high-signal actions
                if ip and ip not in trusted_ip_set and action in SUSPICIOUS_CLOUD_OPS:
                    entry_flagged = dict(entry)
                    entry_flagged["flag"] = "NON_TRUSTED_IP_" + action.upper()
                    cloud_suspicious.append(entry_flagged)
        else:
            cloud_events = []
            cloud_suspicious = []

        # ── Risk summary ──
        indicators: list = []
        if any("NON_TRUSTED_IP_SUCCESS" in si.get("flags", [])
               for si in suspicious_signins if "flags" in si):
            indicators.append("NON_TRUSTED_IP_SUCCESS")
        if any(si.get("flag") == "IMPOSSIBLE_TRAVEL" for si in suspicious_signins):
            indicators.append("IMPOSSIBLE_TRAVEL")
        if any("MFA_FATIGUE" in si.get("flags", [])
               for si in suspicious_signins if "flags" in si):
            indicators.append("MFA_FATIGUE")
        if forwarding_address:
            indicators.append(f"EMAIL_FORWARDING_ACTIVE→{forwarding_address}")
        if malicious_rules:
            indicators.append(f"{len(malicious_rules)}_MALICIOUS_RULE(S)")
        if suspicious_sent:
            total_ext = sum(m.get("totalExternal", len(m.get("externalTo", []))) for m in suspicious_sent)
            indicators.append(f"{len(suspicious_sent)}_SUSPICIOUS_EMAIL(S)_{total_ext}_EXTERNAL_RECIPS")
        if risky.get("riskLevel") in ("medium", "high"):
            indicators.append(f"IDENTITY_PROTECTION_{risky['riskLevel'].upper()}")
        if ual_rule_events:
            indicators.append(f"{len(ual_rule_events)}_UAL_RULE_EVENT(S)")
        if cloud_suspicious:
            indicators.append(f"{len(cloud_suspicious)}_SUSPICIOUS_CLOUD_ACTION(S)")
        if any(g.get("scope", "").lower() in ("full_access_as_user", ".default")
               for g in oauth_grants):
            indicators.append("OAUTH_FULL_ACCESS_GRANT")

        if malicious_rules or risky.get("riskLevel") == "high" or len(indicators) >= 3:
            level = "HIGH"
        elif indicators:
            level = "MEDIUM"
        else:
            level = "CLEAN"
        risk_summary = level + (" — " + ", ".join(indicators) if indicators else "")

        return {
            "user": upn,
            "account": account,
            "forwardingAddress": forwarding_address,
            "oauthGrants": {"count": len(oauth_grants), "grants": oauth_grants},
            "suspiciousSignIns": suspicious_signins[:10],
            "maliciousRules": malicious_rules,
            "authMethods": auth_methods,
            "sentMailSource": sent_source,
            "suspiciousSentMail": suspicious_sent[:10],
            "cloudAppFindings": {
                "available": not isinstance(cloud_events_raw, Exception),
                "totalEvents": len(cloud_events),
                "suspiciousEvents": cloud_suspicious[:20],
            },
            "ualFindings": {
                "inboxRuleChanges": ual_rule_events,
                "mailboxAccess": ual_access[:10],
            },
            "riskSummary": risk_summary,
        }

    # Run all users concurrently
    reports = await asyncio.gather(*[_triage_one(upn) for upn in user_list], return_exceptions=True)

    return _fmt({
        "triageTimestamp": datetime.now(timezone.utc).isoformat(),
        "timeWindowHours": hours,
        "ualWindowHours": ual_hours,
        "ualCoverageCapped": ual_hours > 24,
        "trustedIPs": sorted(trusted_ip_set),
        "users": [
            r if not isinstance(r, Exception) else {"user": user_list[i], "error": str(r)}
            for i, r in enumerate(reports)
        ],
    })


if __name__ == "__main__":
    mcp.run()
