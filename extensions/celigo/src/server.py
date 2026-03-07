#!/usr/bin/env python3
"""
Celigo MCP Server

FastMCP server for Celigo integrator.io REST API operations.
Credentials are read from environment variables set by Claude Desktop.
Falls back to config file for Claude Code compatibility.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Optional
import httpx
from mcp.server.fastmcp import FastMCP

# =============================================================================
# Configuration
# =============================================================================

CHARACTER_LIMIT = 80_000   # ~80KB text — well under Claude Desktop's 1MB MCP limit
BYTE_HARD_LIMIT = 900_000  # 900KB hard cap on raw bytes returned

mcp = FastMCP("celigo_mcp")

# Credentials from env vars (set by Claude Desktop via user_config)
# Falls back to config file for Claude Code / CLI compatibility
def _get_credentials() -> tuple[str, str]:
    """Return (api_url, api_key). Raises ValueError if not configured."""
    api_key = os.environ.get("CELIGO_API_KEY", "")
    api_url = os.environ.get("CELIGO_API_URL", "https://api.integrator.io/v1")

    if not api_key:
        # Try config file fallback (Claude Code compatibility)
        config_paths = [
            Path(__file__).parent.parent.parent / "plugins" / "celigo-integration" / "config" / "celigo_config.json",
            Path.home() / ".claude" / "plugins" / "marketplaces" / "tchow-essentials" / "plugins" / "celigo-integration" / "config" / "celigo_config.json",
        ]
        for config_path in config_paths:
            if config_path.exists():
                with open(config_path) as f:
                    cfg = json.load(f)
                env_name = cfg.get("defaults", {}).get("environment", "production")
                env = cfg.get("environments", {}).get(env_name, {})
                api_key = env.get("api_key", "")
                api_url = env.get("api_url", api_url)
                if api_key and not api_key.startswith("YOUR_"):
                    return api_url, api_key

        raise ValueError(
            "Celigo API key not configured. "
            "Set CELIGO_API_KEY environment variable or configure via Claude Desktop."
        )

    return api_url.rstrip("/"), api_key


async def _celigo_request(method: str, endpoint: str, data: dict = None, params: dict = None) -> dict:
    """Make authenticated Celigo API request."""
    api_url, api_key = _get_credentials()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    url = f"{api_url}{endpoint}"
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
            return "Error: Authentication failed. Check your Celigo API key."
        if code == 403:
            return "Error: Permission denied. You don't have access to this resource."
        if code == 404:
            return "Error: Resource not found. Check the ID is correct."
        if code == 429:
            return "Error: Rate limit exceeded. Wait before making more requests."
        try:
            body = e.response.json()
            msg = body.get("message") or body.get("errors", [{}])[0].get("message", "")
            return f"Error {code}: {msg or e.response.text[:200]}"
        except Exception:
            return f"Error {code}: {e.response.text[:200]}"
    if isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. Try again."
    if isinstance(e, ValueError):
        return f"Configuration error: {e}"
    return f"Error: {type(e).__name__}: {e}"


# Whitelist of fields to keep per resource type for list views.
# Integration/flow objects are 10KB+ each — whitelist drops them to ~200 bytes.
_LIST_KEEP: dict[str, set] = {
    "integrations": {"_id", "name", "lastModified", "createdAt", "sandbox"},
    "flows":        {"_id", "name", "_integrationId", "disabled", "lastModified",
                     "lastExecutedAt", "autoResolveMatchingTraceKeys", "free"},
    "connections":  {"_id", "name", "type", "offline", "lastModified", "_integrationId"},
    "scripts":      {"_id", "name", "lastModified"},   # never include content in list
    "jobs":         {"_id", "type", "status", "startedAt", "endedAt",
                     "numSuccess", "numError", "numIgnore", "_flowId", "_integrationId"},
}


def _slim(item: dict, resource: str) -> dict:
    keep = _LIST_KEEP.get(resource)
    if keep:
        return {k: v for k, v in item.items() if k in keep}
    # Fallback: strip known heavy fields
    heavy = {"content", "mappings", "responseMapping", "filter", "transform",
             "inputFilter", "hooks", "pageGenerators", "pageProcessors",
             "install", "installSteps", "uninstallSteps", "changeEditionSteps",
             "flowGroupings", "_registeredConnectionIds"}
    return {k: v for k, v in item.items() if k not in heavy}


def _fmt_list(data: list, resource: str = "") -> str:
    """Slim list items by resource type, then hard-cap."""
    items = [_slim(i, resource) if isinstance(i, dict) else i for i in data]
    result = json.dumps(items, indent=2)
    size = len(result.encode("utf-8"))
    if size <= BYTE_HARD_LIMIT:
        return result
    # Still too large (shouldn't happen with whitelists, but guard anyway)
    kept = max(1, len(items) * BYTE_HARD_LIMIT // size)
    return json.dumps({
        "items": items[:kept],
        "truncated": True,
        "shown": kept,
        "total": len(data),
        "hint": "Response truncated. Add filters to narrow results.",
    }, indent=2)


def _fmt(data, resource: str = "") -> str:
    """Format any response with hard byte cap."""
    if isinstance(data, list):
        return _fmt_list(data, resource)
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


# =============================================================================
# Integrations
# =============================================================================

@mcp.tool(
    name="celigo_list_integrations",
    annotations={"title": "List Celigo Integrations", "readOnlyHint": True, "openWorldHint": True}
)
async def celigo_list_integrations(sandbox: Optional[bool] = None) -> str:
    """List all Celigo integrations with their IDs, names, and error counts.

    Args:
        sandbox: Filter by sandbox (True) or production (False). None returns all.

    Returns:
        JSON array of integration objects with _id, name, lastModified, numError fields.
    """
    try:
        params = {}
        if sandbox is not None:
            params["sandbox"] = str(sandbox).lower()
        data = await _celigo_request("GET", "/integrations", params=params)
        return _fmt(data, "integrations")
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="celigo_get_integration",
    annotations={"title": "Get Celigo Integration", "readOnlyHint": True, "openWorldHint": True}
)
async def celigo_get_integration(integration_id: str) -> str:
    """Get details for a specific Celigo integration.

    Args:
        integration_id: The integration _id (e.g., '5f8a1234abcd1234abcd1234')

    Returns:
        JSON object with integration details including flows, connections, and settings.
    """
    try:
        data = await _celigo_request("GET", f"/integrations/{integration_id}")
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="celigo_get_integration_errors",
    annotations={"title": "Get Integration Error Summary", "readOnlyHint": True, "openWorldHint": True}
)
async def celigo_get_integration_errors(integration_id: str) -> str:
    """Get error summary for all flows in a Celigo integration.

    Args:
        integration_id: The integration _id

    Returns:
        JSON array of {_flowId, numError, lastErrorAt} per flow with errors.
    """
    try:
        data = await _celigo_request("GET", f"/integrations/{integration_id}/errors")
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# Flows
# =============================================================================

@mcp.tool(
    name="celigo_list_flows",
    annotations={"title": "List Celigo Flows", "readOnlyHint": True, "openWorldHint": True}
)
async def celigo_list_flows(integration_id: Optional[str] = None, disabled: Optional[bool] = None) -> str:
    """List Celigo flows, optionally filtered by integration.

    Args:
        integration_id: Filter flows by integration ID (optional)
        disabled: Filter by disabled status (optional)

    Returns:
        JSON array of flow objects with _id, name, _integrationId, disabled, lastModified.
    """
    try:
        params = {}
        if integration_id:
            params["_integrationId"] = integration_id
        if disabled is not None:
            params["disabled"] = str(disabled).lower()
        data = await _celigo_request("GET", "/flows", params=params)
        return _fmt(data, "flows")
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="celigo_get_flow",
    annotations={"title": "Get Celigo Flow", "readOnlyHint": True, "openWorldHint": True}
)
async def celigo_get_flow(flow_id: str) -> str:
    """Get details for a specific Celigo flow including page generators and processors.

    Args:
        flow_id: The flow _id

    Returns:
        JSON object with full flow definition including pageGenerators, pageProcessors, hooks.
    """
    try:
        data = await _celigo_request("GET", f"/flows/{flow_id}")
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="celigo_run_flow",
    annotations={"title": "Run Celigo Flow", "readOnlyHint": False, "destructiveHint": False, "openWorldHint": True}
)
async def celigo_run_flow(flow_id: str) -> str:
    """Trigger a Celigo flow to run immediately.

    Args:
        flow_id: The flow _id to run

    Returns:
        JSON with job ID and status for the triggered run.
    """
    try:
        data = await _celigo_request("POST", f"/flows/{flow_id}/run")
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="celigo_get_flow_errors",
    annotations={"title": "Get Flow Error Summary", "readOnlyHint": True, "openWorldHint": True}
)
async def celigo_get_flow_errors(flow_id: str) -> str:
    """Get error counts per step for a specific Celigo flow.

    Args:
        flow_id: The flow _id

    Returns:
        JSON with {flowErrors: [{_expOrImpId, numError, lastErrorAt}]} per step.
    """
    try:
        data = await _celigo_request("GET", f"/flows/{flow_id}/errors")
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# Jobs
# =============================================================================

@mcp.tool(
    name="celigo_list_jobs",
    annotations={"title": "List Celigo Jobs", "readOnlyHint": True, "openWorldHint": True}
)
async def celigo_list_jobs(
    flow_id: Optional[str] = None,
    integration_id: Optional[str] = None,
    status: Optional[str] = None,
) -> str:
    """List Celigo flow jobs with optional filters.

    Args:
        flow_id: Filter by flow ID (optional)
        integration_id: Filter by integration ID (optional)
        status: Filter by status: 'running', 'completed', 'failed', 'canceled' (optional)

    Returns:
        JSON array of job objects with _id, type, status, startedAt, endedAt, numSuccess, numError.
    """
    try:
        params = {}
        if flow_id:
            params["_flowId"] = flow_id
        if integration_id:
            params["_integrationId"] = integration_id
        if status:
            params["status"] = status
        data = await _celigo_request("GET", "/jobs", params=params)
        return _fmt(data, "jobs")
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="celigo_get_job",
    annotations={"title": "Get Celigo Job", "readOnlyHint": True, "openWorldHint": True}
)
async def celigo_get_job(job_id: str) -> str:
    """Get details for a specific Celigo job.

    Args:
        job_id: The job _id

    Returns:
        JSON object with job details including status, timing, error counts, and child jobs.
    """
    try:
        data = await _celigo_request("GET", f"/jobs/{job_id}")
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# Errors
# =============================================================================

@mcp.tool(
    name="celigo_list_step_errors",
    annotations={"title": "List Step Errors", "readOnlyHint": True, "openWorldHint": True}
)
async def celigo_list_step_errors(
    flow_id: str,
    step_id: str,
    step_type: str = "imports",
) -> str:
    """List errors for a specific export or import step in a flow.

    Args:
        flow_id: The flow _id
        step_id: The export or import _id
        step_type: 'exports' or 'imports' (default: 'imports')

    Returns:
        JSON with error records including retryDataKey, message, occurredAt, source.
    """
    try:
        data = await _celigo_request("GET", f"/flows/{flow_id}/{step_type}/{step_id}/errors")
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="celigo_resolve_step_errors",
    annotations={"title": "Resolve Step Errors", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True}
)
async def celigo_resolve_step_errors(flow_id: str, step_id: str, error_ids: list[str]) -> str:
    """Resolve (dismiss) errors for a flow step.

    Args:
        flow_id: The flow _id
        step_id: The export or import _id
        error_ids: List of error IDs to resolve

    Returns:
        Success confirmation or error message.
    """
    try:
        data = await _celigo_request(
            "PUT", f"/flows/{flow_id}/{step_id}/resolved",
            data={"errorIds": error_ids}
        )
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# Connections
# =============================================================================

@mcp.tool(
    name="celigo_list_connections",
    annotations={"title": "List Celigo Connections", "readOnlyHint": True, "openWorldHint": True}
)
async def celigo_list_connections(integration_id: Optional[str] = None) -> str:
    """List Celigo connections, optionally filtered by integration.

    Args:
        integration_id: Filter by integration ID (optional)

    Returns:
        JSON array of connection objects with _id, name, type, offline status.
    """
    try:
        params = {}
        if integration_id:
            params["_integrationId"] = integration_id
        data = await _celigo_request("GET", "/connections", params=params)
        return _fmt(data, "connections")
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# Scripts
# =============================================================================

@mcp.tool(
    name="celigo_list_scripts",
    annotations={"title": "List Celigo Scripts", "readOnlyHint": True, "openWorldHint": True}
)
async def celigo_list_scripts() -> str:
    """List all Celigo scripts.

    Returns:
        JSON array of script objects with _id, name, lastModified.
    """
    try:
        data = await _celigo_request("GET", "/scripts")
        return _fmt(data, "scripts")  # 'content' stripped by whitelist
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="celigo_get_script",
    annotations={"title": "Get Celigo Script", "readOnlyHint": True, "openWorldHint": True}
)
async def celigo_get_script(script_id: str) -> str:
    """Get a Celigo script including its content.

    Args:
        script_id: The script _id

    Returns:
        JSON object with script name, content (JavaScript code), and metadata.
    """
    try:
        data = await _celigo_request("GET", f"/scripts/{script_id}")
        # Truncate content field if over 50KB to stay well under 1MB limit
        content = data.get("content", "")
        if len(content) > 50_000:
            data["content"] = content[:50_000] + "\n// ... [content truncated at 50KB]"
        return _fmt(data)
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# EDI Reporting
# =============================================================================

_EDI_KEYWORDS = {"EDI", "856", "850", "810", "820", "846", "855", "860", "997", "X12", "EDIFACT"}
_EDI_DOC_TYPES = {
    "850": "Purchase Order (IB)", "855": "PO Acknowledgement (OB)",
    "856": "Advance Ship Notice (OB)", "810": "Invoice (OB)",
    "820": "Payment Order (IB)", "846": "Inventory Advice (OB)",
    "860": "PO Change (IB)", "864": "Text Message (IB)",
    "997": "Functional Acknowledgement", "753": "Routing Request (OB)",
    "754": "Routing Instructions (IB)", "824": "App Advice (IB)",
    "940": "Warehouse Shipping Order", "945": "Warehouse Shipping Advice",
}


def _parse_edi_integration(name: str) -> dict:
    """Extract trading partner metadata from an EDI integration name."""
    import re
    staging_match = re.search(r'\((\d{1,2}/\d{1,2}/\d{4})\)\s*$', name)
    is_staging = staging_match is not None
    clean = re.sub(r'\s*\(\d{1,2}/\d{1,2}/\d{4}\)\s*$', '', name).strip()

    network = "direct"
    partner = clean
    if clean.startswith("EDI - VAN - "):
        network = "VAN"
        partner = clean[len("EDI - VAN - "):]
    elif clean.startswith("EDI - SPS - "):
        network = "SPS"
        partner = clean[len("EDI - SPS - "):]
    elif clean.startswith("EDI - "):
        partner = clean[len("EDI - "):]

    return {"partner": partner, "network": network, "staging": is_staging,
            "staging_date": staging_match.group(1) if staging_match else None}


def _extract_doc_type(flow_name: str) -> str:
    """Extract EDI document type code from a flow name."""
    import re
    match = re.search(r'\b(8[0-9]{2}|9[0-9]{2}|7[0-9]{2})\b', flow_name)
    return match.group(1) if match else "other"


def _is_edi_integration(name: str) -> bool:
    return any(kw in name.upper() for kw in _EDI_KEYWORDS) and name.startswith("EDI")


@mcp.tool(
    name="celigo_list_edi_integrations",
    annotations={"title": "List EDI Integrations", "readOnlyHint": True, "openWorldHint": True}
)
async def celigo_list_edi_integrations(
    include_staging: bool = False,
    network: Optional[str] = None,
) -> str:
    """List all EDI trading partner integrations with metadata.

    Args:
        include_staging: Include staging/dated copies (e.g. 'EDI - Academy (10/14/2025)'). Default False.
        network: Filter by network type: 'VAN', 'SPS', or 'direct'. Default returns all.

    Returns:
        JSON array of EDI integrations with partner name, network type, integration ID,
        and staging status. Use _id values with other EDI tools.
    """
    try:
        data = await _celigo_request("GET", "/integrations")
        edi = []
        for i in data:
            name = i.get("name", "")
            if not _is_edi_integration(name):
                continue
            meta = _parse_edi_integration(name)
            if not include_staging and meta["staging"]:
                continue
            if network and meta["network"].upper() != network.upper():
                continue
            edi.append({
                "_id": i["_id"],
                "name": name,
                "partner": meta["partner"],
                "network": meta["network"],
                "staging": meta["staging"],
                "lastModified": i.get("lastModified"),
            })
        edi.sort(key=lambda x: x["partner"].lower())
        return _fmt(edi, "integrations")
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="celigo_get_edi_error_summary",
    annotations={"title": "EDI Error Summary", "readOnlyHint": True, "openWorldHint": True}
)
async def celigo_get_edi_error_summary(include_staging: bool = False) -> str:
    """Get aggregated error summary across all active EDI trading partner integrations.

    Calls the errors endpoint for each active EDI integration and returns a
    ranked summary of which trading partners have the most outstanding errors.

    Args:
        include_staging: Include staging/dated integration copies. Default False.

    Returns:
        JSON object with:
        - total_errors: sum across all EDI integrations
        - partners_with_errors: count of partners with at least 1 error
        - by_partner: list sorted by error count (partner, network, _integrationId, total_errors, flow_errors)
    """
    try:
        integrations = await _celigo_request("GET", "/integrations")
        edi_integrations = []
        for i in integrations:
            name = i.get("name", "")
            if not _is_edi_integration(name):
                continue
            meta = _parse_edi_integration(name)
            if not include_staging and meta["staging"]:
                continue
            edi_integrations.append({**i, **meta})

        # Fetch errors for each EDI integration concurrently
        import asyncio
        async def get_errors(integ):
            try:
                errors = await _celigo_request("GET", f"/integrations/{integ['_id']}/errors")
                total = sum(e.get("numError", 0) for e in (errors or []))
                flows_with_errors = [e for e in (errors or []) if e.get("numError", 0) > 0]
                return {
                    "partner": integ["partner"],
                    "network": integ["network"],
                    "_integrationId": integ["_id"],
                    "total_errors": total,
                    "flows_with_errors": len(flows_with_errors),
                    "flow_details": flows_with_errors[:10],
                }
            except Exception:
                return {"partner": integ["partner"], "network": integ["network"],
                        "_integrationId": integ["_id"], "total_errors": -1, "error": "fetch_failed"}

        results = await asyncio.gather(*[get_errors(i) for i in edi_integrations])
        results = sorted(results, key=lambda x: x.get("total_errors", 0), reverse=True)

        total_errors = sum(r.get("total_errors", 0) for r in results if r.get("total_errors", 0) >= 0)
        partners_with_errors = sum(1 for r in results if r.get("total_errors", 0) > 0)

        report = {
            "total_errors": total_errors,
            "partners_with_errors": partners_with_errors,
            "total_edi_integrations": len(edi_integrations),
            "by_partner": results,
        }
        return _fmt(report)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="celigo_get_edi_flow_summary",
    annotations={"title": "EDI Flow Summary by Partner", "readOnlyHint": True, "openWorldHint": True}
)
async def celigo_get_edi_flow_summary(integration_id: str) -> str:
    """Get detailed flow status for a specific EDI trading partner integration.

    Args:
        integration_id: The integration _id (get from celigo_list_edi_integrations).

    Returns:
        JSON with integration name, partner info, and flows grouped by document type
        (850 PO, 856 ASN, 810 Invoice, etc.) showing enabled/disabled status
        and last execution time.
    """
    try:
        import asyncio
        integ, flows_all, errors = await asyncio.gather(
            _celigo_request("GET", f"/integrations/{integration_id}"),
            _celigo_request("GET", "/flows"),
            _celigo_request("GET", f"/integrations/{integration_id}/errors"),
        )

        # Filter flows belonging to this integration
        flows = [f for f in flows_all if f.get("_integrationId") == integration_id]
        error_map = {e["_flowId"]: e.get("numError", 0) for e in (errors or [])}

        by_doc_type: dict = {}
        for f in flows:
            doc = _extract_doc_type(f["name"])
            label = _EDI_DOC_TYPES.get(doc, f"Doc {doc}")
            if doc not in by_doc_type:
                by_doc_type[doc] = {"doc_type": doc, "description": label, "flows": []}
            by_doc_type[doc]["flows"].append({
                "_id": f["_id"],
                "name": f["name"],
                "enabled": not f.get("disabled", False),
                "lastExecutedAt": f.get("lastExecutedAt"),
                "numError": error_map.get(f["_id"], 0),
            })

        name = integ.get("name", "")
        meta = _parse_edi_integration(name)
        return _fmt({
            "_integrationId": integration_id,
            "name": name,
            "partner": meta["partner"],
            "network": meta["network"],
            "total_flows": len(flows),
            "active_flows": sum(1 for f in flows if not f.get("disabled")),
            "total_errors": sum(error_map.values()),
            "by_doc_type": sorted(by_doc_type.values(), key=lambda x: x["doc_type"]),
        })
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="celigo_get_edi_health_dashboard",
    annotations={"title": "EDI Health Dashboard", "readOnlyHint": True, "openWorldHint": True}
)
async def celigo_get_edi_health_dashboard() -> str:
    """Get a high-level health dashboard across all active EDI trading partners.

    Returns a compact summary suitable for a quick status overview:
    - Count of active vs disabled flows per partner
    - Outstanding error counts
    - Network type (VAN/SPS/direct)
    - Partners sorted by error count (most problematic first)

    No arguments needed. Filters out staging/dated integration copies.
    """
    try:
        import asyncio
        integrations, flows_all = await asyncio.gather(
            _celigo_request("GET", "/integrations"),
            _celigo_request("GET", "/flows"),
        )

        edi_integrations = []
        for i in integrations:
            name = i.get("name", "")
            if not _is_edi_integration(name):
                continue
            meta = _parse_edi_integration(name)
            if meta["staging"]:
                continue
            edi_integrations.append({**i, **meta})

        # Build flow counts per integration
        flow_map: dict = {}
        for f in flows_all:
            iid = f.get("_integrationId", "")
            if iid not in flow_map:
                flow_map[iid] = {"active": 0, "disabled": 0, "doc_types": set()}
            if f.get("disabled"):
                flow_map[iid]["disabled"] += 1
            else:
                flow_map[iid]["active"] += 1
            doc = _extract_doc_type(f["name"])
            if doc != "other":
                flow_map[iid]["doc_types"].add(doc)

        # Fetch errors concurrently
        async def get_error_count(integ):
            try:
                errors = await _celigo_request("GET", f"/integrations/{integ['_id']}/errors")
                return integ["_id"], sum(e.get("numError", 0) for e in (errors or []))
            except Exception:
                return integ["_id"], -1

        error_results = await asyncio.gather(*[get_error_count(i) for i in edi_integrations])
        error_map = dict(error_results)

        # Build dashboard rows
        rows = []
        for integ in edi_integrations:
            iid = integ["_id"]
            fmap = flow_map.get(iid, {"active": 0, "disabled": 0, "doc_types": set()})
            rows.append({
                "partner": integ["partner"],
                "network": integ["network"],
                "_integrationId": iid,
                "active_flows": fmap["active"],
                "disabled_flows": fmap["disabled"],
                "doc_types": sorted(fmap["doc_types"]),
                "errors": error_map.get(iid, 0),
            })

        rows.sort(key=lambda x: (-x["errors"], x["partner"].lower()))

        total_errors = sum(r["errors"] for r in rows if r["errors"] >= 0)
        return _fmt({
            "summary": {
                "active_partners": len(rows),
                "total_errors": total_errors,
                "partners_with_errors": sum(1 for r in rows if r["errors"] > 0),
                "total_active_flows": sum(r["active_flows"] for r in rows),
            },
            "partners": rows,
        })
    except Exception as e:
        return _handle_error(e)


if __name__ == "__main__":
    mcp.run()
