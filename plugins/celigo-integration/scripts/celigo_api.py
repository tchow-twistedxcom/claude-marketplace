#!/usr/bin/env python3
"""
Celigo API CLI - Full REST API Client

A comprehensive command-line interface for all Celigo integrator.io REST API operations.
Replaces MCP-based integration with direct Python script execution.

Usage:
    python3 celigo_api.py <resource> <action> [options]

Examples:
    python3 celigo_api.py integrations list
    python3 celigo_api.py flows run <flow_id>
    python3 celigo_api.py jobs list --status running
    python3 celigo_api.py errors list --flow <id> --import <id>
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
CONFIG_FILE = CONFIG_DIR / "celigo_config.json"

DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2


# =============================================================================
# Configuration & Authentication
# =============================================================================

def load_config() -> dict:
    """Load configuration from config file."""
    if not CONFIG_FILE.exists():
        print(f"Error: Configuration file not found at {CONFIG_FILE}", file=sys.stderr)
        print("Run: cp config/celigo_config.template.json config/celigo_config.json", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)


def get_environment(config: dict, env_name: str = None) -> dict:
    """Get environment configuration."""
    env_name = env_name or config.get("defaults", {}).get("environment", "production")
    if env_name not in config.get("environments", {}):
        print(f"Error: Environment '{env_name}' not found.", file=sys.stderr)
        print(f"Available: {list(config.get('environments', {}).keys())}", file=sys.stderr)
        sys.exit(1)
    return config["environments"][env_name]


def get_api_credentials(env_name: str = None) -> tuple:
    """Get API URL and key for specified environment."""
    config = load_config()
    env = get_environment(config, env_name)
    api_url = env.get("api_url", "https://api.integrator.io/v1")
    api_key = env.get("api_key", "")
    if not api_key or api_key.startswith("YOUR_"):
        print(f"Error: API key not configured for '{env.get('name', env_name)}'", file=sys.stderr)
        sys.exit(1)
    return api_url, api_key


# =============================================================================
# HTTP Client
# =============================================================================

class CeligoClient:
    """HTTP client for Celigo API with retry logic and error handling."""

    def __init__(self, env_name: str = None):
        self.api_url, self.api_key = get_api_credentials(env_name)
        self.timeout = DEFAULT_TIMEOUT

    def _make_request(self, method: str, endpoint: str, data: dict = None,
                      params: dict = None) -> dict:
        """Make HTTP request with retry logic."""
        url = f"{self.api_url}{endpoint}"
        if params:
            # Filter out None values
            params = {k: v for k, v in params.items() if v is not None}
            if params:
                url += "?" + urlencode(params)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        body = json.dumps(data).encode() if data else None

        for attempt in range(MAX_RETRIES):
            try:
                req = Request(url, data=body, headers=headers, method=method)
                with urlopen(req, timeout=self.timeout) as response:
                    content = response.read().decode()
                    if not content:
                        return {}
                    return json.loads(content)
            except HTTPError as e:
                if e.code == 429:  # Rate limited
                    wait = RETRY_BACKOFF_BASE ** attempt * 60
                    print(f"Rate limited. Waiting {wait}s...", file=sys.stderr)
                    time.sleep(wait)
                    continue
                elif e.code == 204:  # No content (successful delete)
                    return {"success": True, "status": 204}
                error_body = e.read().decode() if e.fp else ""
                return {
                    "error": True,
                    "status": e.code,
                    "message": e.reason,
                    "details": error_body
                }
            except URLError as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_BACKOFF_BASE ** attempt)
                    continue
                return {"error": True, "message": str(e.reason)}
            except Exception as e:
                return {"error": True, "message": str(e)}

        return {"error": True, "message": "Max retries exceeded"}

    def get(self, endpoint: str, params: dict = None) -> dict:
        return self._make_request("GET", endpoint, params=params)

    def post(self, endpoint: str, data: dict = None) -> dict:
        return self._make_request("POST", endpoint, data=data)

    def put(self, endpoint: str, data: dict = None) -> dict:
        return self._make_request("PUT", endpoint, data=data)

    def delete(self, endpoint: str) -> dict:
        return self._make_request("DELETE", endpoint)


# =============================================================================
# Output Formatting
# =============================================================================

def format_table(data: List[dict], columns: List[str] = None, headers: List[str] = None) -> str:
    """Format data as ASCII table."""
    if not data:
        return "No data found."

    if isinstance(data, dict):
        if data.get("error"):
            return f"Error: {data.get('message', 'Unknown error')}\n{data.get('details', '')}"
        data = [data]

    # Auto-detect columns if not specified
    if not columns:
        columns = list(data[0].keys()) if data else []

    # Use headers or column names
    if not headers:
        headers = columns

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in data:
        for i, col in enumerate(columns):
            val = str(row.get(col, ""))[:50]  # Truncate long values
            widths[i] = max(widths[i], len(val))

    # Build table
    lines = []
    # Header
    header_line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    lines.append(header_line)
    lines.append("-+-".join("-" * w for w in widths))

    # Rows
    for row in data:
        values = [str(row.get(col, ""))[:50].ljust(widths[i]) for i, col in enumerate(columns)]
        lines.append(" | ".join(values))

    return "\n".join(lines)


def format_output(data: Any, fmt: str = "table", columns: List[str] = None,
                  headers: List[str] = None) -> str:
    """Format output based on requested format."""
    if fmt == "json":
        return json.dumps(data, indent=2, default=str)
    elif fmt == "table":
        if isinstance(data, list):
            return format_table(data, columns, headers)
        elif isinstance(data, dict):
            if data.get("error"):
                return f"Error: {data.get('message', 'Unknown error')}\n{data.get('details', '')}"
            # Single object - format as key-value pairs
            lines = []
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    v = json.dumps(v, default=str)
                lines.append(f"{k}: {v}")
            return "\n".join(lines)
    return str(data)


def print_result(data: Any, fmt: str = "table", columns: List[str] = None,
                 headers: List[str] = None):
    """Print formatted result."""
    print(format_output(data, fmt, columns, headers))


# =============================================================================
# Resource: Integrations
# =============================================================================

class IntegrationsAPI:
    """Integrations resource operations."""

    def __init__(self, client: CeligoClient):
        self.client = client

    def list(self, sandbox: bool = None) -> list:
        """List all integrations."""
        params = {}
        if sandbox is not None:
            params["sandbox"] = str(sandbox).lower()
        return self.client.get("/integrations", params)

    def get(self, integration_id: str) -> dict:
        """Get single integration."""
        return self.client.get(f"/integrations/{integration_id}")

    def flows(self, integration_id: str) -> list:
        """Get flows for integration."""
        return self.client.get(f"/integrations/{integration_id}/flows")

    def connections(self, integration_id: str) -> list:
        """Get connections for integration."""
        return self.client.get(f"/integrations/{integration_id}/connections")

    def exports(self, integration_id: str) -> list:
        """Get exports for integration."""
        return self.client.get(f"/integrations/{integration_id}/exports")

    def imports(self, integration_id: str) -> list:
        """Get imports for integration."""
        return self.client.get(f"/integrations/{integration_id}/imports")

    def users(self, integration_id: str) -> list:
        """Get users/shares for integration."""
        return self.client.get(f"/integrations/{integration_id}/ashares")

    def template(self, integration_id: str) -> dict:
        """Get integration template download URL."""
        return self.client.get(f"/integrations/{integration_id}/template")

    def dependencies(self, integration_id: str) -> dict:
        """Get integration dependencies."""
        return self.client.get(f"/integrations/{integration_id}/dependencies")

    def audit(self, integration_id: str, page: int = 1, page_size: int = 100) -> list:
        """Get integration audit log."""
        params = {"page": page, "pageSize": page_size}
        return self.client.get(f"/integrations/{integration_id}/audit", params)

    def errors(self, integration_id: str, occurred_gte: str = None,
               occurred_lte: str = None, source: str = None) -> list:
        """Get integration error summary."""
        params = {}
        if occurred_gte:
            params["occurredAt_gte"] = occurred_gte
        if occurred_lte:
            params["occurredAt_lte"] = occurred_lte
        if source:
            params["source"] = source
        return self.client.get(f"/integrations/{integration_id}/errors", params)


# =============================================================================
# Resource: Flows
# =============================================================================

class FlowsAPI:
    """Flows resource operations."""

    def __init__(self, client: CeligoClient):
        self.client = client

    def list(self, integration_id: str = None, disabled: bool = None,
             page: int = 1, page_size: int = 100) -> list:
        """List all flows."""
        params = {"page": page, "pageSize": page_size}
        if integration_id:
            params["_integrationId"] = integration_id
        if disabled is not None:
            params["disabled"] = str(disabled).lower()
        return self.client.get("/flows", params)

    def get(self, flow_id: str) -> dict:
        """Get single flow."""
        return self.client.get(f"/flows/{flow_id}")

    def run(self, flow_id: str, export_ids: list = None,
            start_date: str = None, end_date: str = None) -> dict:
        """Run/trigger a flow."""
        data = {}
        if export_ids:
            data["_exportIds"] = export_ids
        if start_date:
            data["startDate"] = start_date
        if end_date:
            data["endDate"] = end_date
        return self.client.post(f"/flows/{flow_id}/run", data if data else None)

    def template(self, flow_id: str) -> dict:
        """Get flow template download URL."""
        return self.client.get(f"/flows/{flow_id}/template")

    def dependencies(self, flow_id: str) -> dict:
        """Get flow dependencies."""
        return self.client.get(f"/flows/{flow_id}/dependencies")

    def descendants(self, flow_id: str) -> dict:
        """Get flow descendants (exports and imports)."""
        return self.client.get(f"/flows/{flow_id}/descendants")

    def jobs_latest(self, flow_id: str) -> list:
        """Get latest jobs for flow."""
        return self.client.get(f"/flows/{flow_id}/jobs/latest")

    def last_export_datetime(self, flow_id: str) -> dict:
        """Get last export datetime for flow."""
        return self.client.get(f"/flows/{flow_id}/lastExportDateTime")

    def audit(self, flow_id: str) -> list:
        """Get flow audit log."""
        return self.client.get(f"/flows/{flow_id}/audit")


# =============================================================================
# Resource: Connections
# =============================================================================

class ConnectionsAPI:
    """Connections resource operations."""

    def __init__(self, client: CeligoClient):
        self.client = client

    def list(self, integration_id: str = None, conn_type: str = None) -> list:
        """List all connections."""
        params = {}
        if integration_id:
            params["_integrationId"] = integration_id
        if conn_type:
            params["type"] = conn_type
        return self.client.get("/connections", params)

    def get(self, connection_id: str) -> dict:
        """Get single connection."""
        return self.client.get(f"/connections/{connection_id}")

    def test(self, connection_id: str) -> dict:
        """Test/ping connection."""
        return self.client.post(f"/connections/{connection_id}/ping")

    def debug_log(self, connection_id: str) -> dict:
        """Get connection debug log."""
        return self.client.get(f"/connections/{connection_id}/debuglog")

    def logs(self, connection_id: str) -> list:
        """Get connection usage logs."""
        return self.client.get(f"/connections/{connection_id}/logs")

    def dependencies(self, connection_id: str) -> dict:
        """Get connection dependencies."""
        return self.client.get(f"/connections/{connection_id}/dependencies")


# =============================================================================
# Resource: Exports
# =============================================================================

class ExportsAPI:
    """Exports resource operations."""

    def __init__(self, client: CeligoClient):
        self.client = client

    def list(self, page: int = 1, page_size: int = 100) -> list:
        """List all exports."""
        params = {"page": page, "pageSize": page_size}
        return self.client.get("/exports", params)

    def get(self, export_id: str) -> dict:
        """Get single export."""
        return self.client.get(f"/exports/{export_id}")

    def audit(self, export_id: str) -> list:
        """Get export audit log."""
        return self.client.get(f"/exports/{export_id}/audit")

    def dependencies(self, export_id: str) -> dict:
        """Get export dependencies."""
        return self.client.get(f"/exports/{export_id}/dependencies")


# =============================================================================
# Resource: Imports
# =============================================================================

class ImportsAPI:
    """Imports resource operations."""

    def __init__(self, client: CeligoClient):
        self.client = client

    def list(self, page: int = 1, page_size: int = 100) -> list:
        """List all imports."""
        params = {"page": page, "pageSize": page_size}
        return self.client.get("/imports", params)

    def get(self, import_id: str) -> dict:
        """Get single import."""
        return self.client.get(f"/imports/{import_id}")

    def audit(self, import_id: str) -> list:
        """Get import audit log."""
        return self.client.get(f"/imports/{import_id}/audit")

    def dependencies(self, import_id: str) -> dict:
        """Get import dependencies."""
        return self.client.get(f"/imports/{import_id}/dependencies")


# =============================================================================
# Resource: Jobs
# =============================================================================

class JobsAPI:
    """Jobs resource operations."""

    def __init__(self, client: CeligoClient):
        self.client = client

    def list(self, integration_id: str = None, flow_id: str = None,
             export_id: str = None, flow_job_id: str = None,
             status: str = None, job_type: str = None,
             created_gte: str = None, created_lte: str = None,
             flow_id_in: str = None) -> list:
        """List jobs with filtering."""
        params = {}
        if integration_id:
            params["integration_id"] = integration_id
        if flow_id:
            params["flow_id"] = flow_id
        if export_id:
            params["export_id"] = export_id
        if flow_job_id:
            params["flow_job_id"] = flow_job_id
        if status:
            params["status"] = status
        if job_type:
            params["type"] = job_type
        if created_gte:
            params["createdAt_gte"] = created_gte
        if created_lte:
            params["createdAt_lte"] = created_lte
        if flow_id_in:
            params["flow_id_in"] = flow_id_in
        return self.client.get("/jobs", params)

    def get(self, job_id: str) -> dict:
        """Get single job."""
        return self.client.get(f"/jobs/{job_id}")

    def cancel(self, job_id: str) -> dict:
        """Cancel a running flow job."""
        # First verify it's a flow job
        job = self.get(job_id)
        if job.get("error"):
            return job
        if job.get("type") != "flow":
            return {"error": True, "message": "Only flow jobs can be canceled"}
        return self.client.delete(f"/jobs/{job_id}")


# =============================================================================
# Resource: Errors
# =============================================================================

class ErrorsAPI:
    """Errors resource operations."""

    def __init__(self, client: CeligoClient):
        self.client = client

    # Export Errors
    def list_export(self, flow_id: str, export_id: str,
                    occurred_gte: str = None, occurred_lte: str = None,
                    source: str = None) -> dict:
        """List export errors."""
        params = {}
        if occurred_gte:
            params["occurredAt_gte"] = occurred_gte
        if occurred_lte:
            params["occurredAt_lte"] = occurred_lte
        if source:
            params["source"] = source
        return self.client.get(f"/flows/{flow_id}/exports/{export_id}/errors", params)

    def resolved_export(self, flow_id: str, export_id: str,
                        occurred_gte: str = None, occurred_lte: str = None,
                        source: str = None) -> dict:
        """List resolved export errors."""
        params = {}
        if occurred_gte:
            params["occurredAt_gte"] = occurred_gte
        if occurred_lte:
            params["occurredAt_lte"] = occurred_lte
        if source:
            params["source"] = source
        return self.client.get(f"/flows/{flow_id}/exports/{export_id}/resolved", params)

    def retry_data_export(self, flow_id: str, export_id: str, retry_key: str) -> dict:
        """Get export error retry data."""
        return self.client.get(f"/flows/{flow_id}/exports/{export_id}/errors/{retry_key}")

    def resolve_export(self, flow_id: str, export_id: str, error_ids: list) -> dict:
        """Resolve export errors."""
        return self.client.post(f"/flows/{flow_id}/exports/{export_id}/errors/resolve",
                                {"errorIds": error_ids})

    def retry_export(self, flow_id: str, export_id: str, retry_keys: list) -> dict:
        """Retry export errors."""
        return self.client.post(f"/flows/{flow_id}/exports/{export_id}/errors/retry",
                                {"retryDataKeys": retry_keys})

    def assign_export(self, flow_id: str, export_id: str, error_ids: list,
                      email: str) -> dict:
        """Assign export errors to user."""
        return self.client.post(f"/flows/{flow_id}/exports/{export_id}/errors/assign",
                                {"errorIds": error_ids, "email": email})

    def tags_export(self, flow_id: str, export_id: str, errors: list,
                    tag_ids: list) -> dict:
        """Tag export errors."""
        return self.client.post(f"/flows/{flow_id}/exports/{export_id}/errors/tags",
                                {"errors": errors, "tagIds": tag_ids})

    # Import Errors
    def list_import(self, flow_id: str, import_id: str,
                    occurred_gte: str = None, occurred_lte: str = None,
                    source: str = None) -> dict:
        """List import errors."""
        params = {}
        if occurred_gte:
            params["occurredAt_gte"] = occurred_gte
        if occurred_lte:
            params["occurredAt_lte"] = occurred_lte
        if source:
            params["source"] = source
        return self.client.get(f"/flows/{flow_id}/imports/{import_id}/errors", params)

    def resolved_import(self, flow_id: str, import_id: str,
                        occurred_gte: str = None, occurred_lte: str = None,
                        source: str = None) -> dict:
        """List resolved import errors."""
        params = {}
        if occurred_gte:
            params["occurredAt_gte"] = occurred_gte
        if occurred_lte:
            params["occurredAt_lte"] = occurred_lte
        if source:
            params["source"] = source
        return self.client.get(f"/flows/{flow_id}/imports/{import_id}/resolved", params)

    def retry_data_import(self, flow_id: str, import_id: str, retry_key: str) -> dict:
        """Get import error retry data."""
        return self.client.get(f"/flows/{flow_id}/imports/{import_id}/errors/{retry_key}")

    def resolve_import(self, flow_id: str, import_id: str, error_ids: list) -> dict:
        """Resolve import errors."""
        return self.client.post(f"/flows/{flow_id}/imports/{import_id}/errors/resolve",
                                {"errorIds": error_ids})

    def retry_import(self, flow_id: str, import_id: str, retry_keys: list) -> dict:
        """Retry import errors."""
        return self.client.post(f"/flows/{flow_id}/imports/{import_id}/errors/retry",
                                {"retryDataKeys": retry_keys})

    def assign_import(self, flow_id: str, import_id: str, error_ids: list,
                      email: str) -> dict:
        """Assign import errors to user."""
        return self.client.post(f"/flows/{flow_id}/imports/{import_id}/errors/assign",
                                {"errorIds": error_ids, "email": email})

    def tags_import(self, flow_id: str, import_id: str, errors: list,
                    tag_ids: list) -> dict:
        """Tag import errors."""
        return self.client.post(f"/flows/{flow_id}/imports/{import_id}/errors/tags",
                                {"errors": errors, "tagIds": tag_ids})

    # Integration Errors
    def integration_summary(self, integration_id: str, occurred_gte: str = None,
                            occurred_lte: str = None, source: str = None) -> list:
        """Get integration error summary."""
        params = {}
        if occurred_gte:
            params["occurredAt_gte"] = occurred_gte
        if occurred_lte:
            params["occurredAt_lte"] = occurred_lte
        if source:
            params["source"] = source
        return self.client.get(f"/integrations/{integration_id}/errors", params)

    def assign_integration(self, integration_id: str, error_ids: list,
                           email: str) -> dict:
        """Assign integration errors to user."""
        return self.client.post(f"/integrations/{integration_id}/errors/assign",
                                {"errorIds": error_ids, "email": email})


# =============================================================================
# Resource: Lookup Caches
# =============================================================================

class LookupCachesAPI:
    """Lookup caches resource operations."""

    def __init__(self, client: CeligoClient):
        self.client = client

    def list(self) -> list:
        """List all lookup caches."""
        return self.client.get("/lookupcaches")

    def get(self, cache_id: str) -> dict:
        """Get lookup cache metadata."""
        return self.client.get(f"/lookupcaches/{cache_id}")

    def data(self, cache_id: str, keys: list = None, starts_with: str = None,
             page_size: int = None, start_after_key: str = None) -> dict:
        """Get lookup cache data."""
        params = {}
        if keys:
            params["keys"] = ",".join(keys)
        if starts_with:
            params["starts_with"] = starts_with
        if page_size:
            params["pageSize"] = page_size
        if start_after_key:
            params["start_after_key"] = start_after_key
        return self.client.get(f"/lookupcaches/{cache_id}/data", params)


# =============================================================================
# Resource: Tags
# =============================================================================

class TagsAPI:
    """Tags resource operations."""

    def __init__(self, client: CeligoClient):
        self.client = client

    def list(self) -> list:
        """List all tags."""
        return self.client.get("/tags")

    def get(self, tag_id: str) -> dict:
        """Get single tag."""
        return self.client.get(f"/tags/{tag_id}")

    def create(self, tag_name: str) -> dict:
        """Create a new tag."""
        return self.client.post("/tags", {"tag": tag_name})

    def update(self, tag_id: str, tag_name: str, tag_tag_id: str) -> dict:
        """Update a tag."""
        return self.client.put(f"/tags/{tag_id}",
                               {"_id": tag_id, "tag": tag_name, "tagId": tag_tag_id})

    def delete(self, tag_id: str) -> dict:
        """Delete a tag."""
        return self.client.delete(f"/tags/{tag_id}")


# =============================================================================
# Resource: Users
# =============================================================================

class UsersAPI:
    """Users/shares resource operations."""

    def __init__(self, client: CeligoClient):
        self.client = client

    def list(self) -> list:
        """List all users/shares."""
        return self.client.get("/ashares")

    def get(self, user_id: str) -> dict:
        """Get single user/share."""
        return self.client.get(f"/ashares/{user_id}")


# =============================================================================
# CLI Command Handlers
# =============================================================================

def cmd_integrations(args):
    """Handle integrations subcommands."""
    client = CeligoClient(args.env)
    api = IntegrationsAPI(client)

    if args.action == "list":
        data = api.list(sandbox=args.sandbox if hasattr(args, 'sandbox') else None)
        columns = ["_id", "name", "sandbox", "lastModified"]
        print_result(data, args.format, columns)

    elif args.action == "get":
        print_result(api.get(args.id), args.format)

    elif args.action == "flows":
        data = api.flows(args.id)
        columns = ["_id", "name", "disabled", "lastModified"]
        print_result(data, args.format, columns)

    elif args.action == "connections":
        data = api.connections(args.id)
        columns = ["_id", "name", "type", "offline"]
        print_result(data, args.format, columns)

    elif args.action == "exports":
        data = api.exports(args.id)
        columns = ["_id", "name", "adaptorType", "lastModified"]
        print_result(data, args.format, columns)

    elif args.action == "imports":
        data = api.imports(args.id)
        columns = ["_id", "name", "adaptorType", "lastModified"]
        print_result(data, args.format, columns)

    elif args.action == "users":
        data = api.users(args.id)
        print_result(data, args.format)

    elif args.action == "template":
        print_result(api.template(args.id), args.format)

    elif args.action == "dependencies":
        print_result(api.dependencies(args.id), args.format)

    elif args.action == "audit":
        data = api.audit(args.id, page=args.page, page_size=args.page_size)
        print_result(data, args.format)

    elif args.action == "errors":
        data = api.errors(args.id, occurred_gte=args.since, occurred_lte=args.until,
                          source=args.source)
        columns = ["_flowId", "numError"]
        print_result(data, args.format, columns)


def cmd_flows(args):
    """Handle flows subcommands."""
    client = CeligoClient(args.env)
    api = FlowsAPI(client)

    if args.action == "list":
        data = api.list(integration_id=args.integration, disabled=args.disabled,
                        page=args.page, page_size=args.page_size)
        columns = ["_id", "name", "disabled", "_integrationId"]
        print_result(data, args.format, columns)

    elif args.action == "get":
        print_result(api.get(args.id), args.format)

    elif args.action == "run":
        export_ids = args.export_ids.split(",") if args.export_ids else None
        data = api.run(args.id, export_ids=export_ids,
                       start_date=args.start_date, end_date=args.end_date)
        print_result(data, args.format)

    elif args.action == "template":
        print_result(api.template(args.id), args.format)

    elif args.action == "dependencies":
        print_result(api.dependencies(args.id), args.format)

    elif args.action == "descendants":
        print_result(api.descendants(args.id), args.format)

    elif args.action == "jobs-latest":
        data = api.jobs_latest(args.id)
        columns = ["_id", "type", "status", "numSuccess", "numError", "endedAt"]
        print_result(data, args.format, columns)

    elif args.action == "last-export-datetime":
        print_result(api.last_export_datetime(args.id), args.format)

    elif args.action == "audit":
        print_result(api.audit(args.id), args.format)


def cmd_connections(args):
    """Handle connections subcommands."""
    client = CeligoClient(args.env)
    api = ConnectionsAPI(client)

    if args.action == "list":
        data = api.list(integration_id=args.integration, conn_type=args.type)
        columns = ["_id", "name", "type", "offline"]
        print_result(data, args.format, columns)

    elif args.action == "get":
        print_result(api.get(args.id), args.format)

    elif args.action == "test":
        print_result(api.test(args.id), args.format)

    elif args.action == "debug-log":
        print_result(api.debug_log(args.id), args.format)

    elif args.action == "logs":
        print_result(api.logs(args.id), args.format)

    elif args.action == "dependencies":
        print_result(api.dependencies(args.id), args.format)


def cmd_exports(args):
    """Handle exports subcommands."""
    client = CeligoClient(args.env)
    api = ExportsAPI(client)

    if args.action == "list":
        data = api.list(page=args.page, page_size=args.page_size)
        columns = ["_id", "name", "adaptorType", "_connectionId"]
        print_result(data, args.format, columns)

    elif args.action == "get":
        print_result(api.get(args.id), args.format)

    elif args.action == "audit":
        print_result(api.audit(args.id), args.format)

    elif args.action == "dependencies":
        print_result(api.dependencies(args.id), args.format)


def cmd_imports(args):
    """Handle imports subcommands."""
    client = CeligoClient(args.env)
    api = ImportsAPI(client)

    if args.action == "list":
        data = api.list(page=args.page, page_size=args.page_size)
        columns = ["_id", "name", "adaptorType", "_connectionId"]
        print_result(data, args.format, columns)

    elif args.action == "get":
        print_result(api.get(args.id), args.format)

    elif args.action == "audit":
        print_result(api.audit(args.id), args.format)

    elif args.action == "dependencies":
        print_result(api.dependencies(args.id), args.format)


def cmd_jobs(args):
    """Handle jobs subcommands."""
    client = CeligoClient(args.env)
    api = JobsAPI(client)

    if args.action == "list":
        data = api.list(
            integration_id=args.integration,
            flow_id=args.flow,
            export_id=args.export,
            flow_job_id=args.flow_job,
            status=args.status,
            job_type=args.type,
            created_gte=args.since,
            created_lte=args.until,
            flow_id_in=args.flow_ids
        )
        columns = ["_id", "type", "status", "numSuccess", "numError", "createdAt"]
        print_result(data, args.format, columns)

    elif args.action == "get":
        print_result(api.get(args.id), args.format)

    elif args.action == "cancel":
        print_result(api.cancel(args.id), args.format)


def cmd_errors(args):
    """Handle errors subcommands."""
    client = CeligoClient(args.env)
    api = ErrorsAPI(client)

    # Determine if export or import based on provided args
    is_export = hasattr(args, 'export') and args.export
    is_import = hasattr(args, 'import_id') and args.import_id

    if args.action == "list":
        if is_export:
            data = api.list_export(args.flow, args.export,
                                   occurred_gte=args.since, occurred_lte=args.until,
                                   source=args.source)
        elif is_import:
            data = api.list_import(args.flow, args.import_id,
                                   occurred_gte=args.since, occurred_lte=args.until,
                                   source=args.source)
        else:
            print("Error: Specify --export or --import", file=sys.stderr)
            sys.exit(1)
        print_result(data, args.format)

    elif args.action == "resolved":
        if is_export:
            data = api.resolved_export(args.flow, args.export,
                                       occurred_gte=args.since, occurred_lte=args.until,
                                       source=args.source)
        elif is_import:
            data = api.resolved_import(args.flow, args.import_id,
                                       occurred_gte=args.since, occurred_lte=args.until,
                                       source=args.source)
        else:
            print("Error: Specify --export or --import", file=sys.stderr)
            sys.exit(1)
        print_result(data, args.format)

    elif args.action == "retry-data":
        if is_export:
            data = api.retry_data_export(args.flow, args.export, args.key)
        elif is_import:
            data = api.retry_data_import(args.flow, args.import_id, args.key)
        else:
            print("Error: Specify --export or --import", file=sys.stderr)
            sys.exit(1)
        print_result(data, args.format)

    elif args.action == "resolve":
        error_ids = args.ids.split(",")
        if is_export:
            data = api.resolve_export(args.flow, args.export, error_ids)
        elif is_import:
            data = api.resolve_import(args.flow, args.import_id, error_ids)
        else:
            print("Error: Specify --export or --import", file=sys.stderr)
            sys.exit(1)
        print_result(data, args.format)

    elif args.action == "retry":
        retry_keys = args.keys.split(",")
        if is_export:
            data = api.retry_export(args.flow, args.export, retry_keys)
        elif is_import:
            data = api.retry_import(args.flow, args.import_id, retry_keys)
        else:
            print("Error: Specify --export or --import", file=sys.stderr)
            sys.exit(1)
        print_result(data, args.format)

    elif args.action == "assign":
        error_ids = args.ids.split(",")
        if is_export:
            data = api.assign_export(args.flow, args.export, error_ids, args.email)
        elif is_import:
            data = api.assign_import(args.flow, args.import_id, error_ids, args.email)
        else:
            print("Error: Specify --export or --import", file=sys.stderr)
            sys.exit(1)
        print_result(data, args.format)

    elif args.action == "tags":
        # Parse errors as JSON list: [{"id": "...", "rdk": "..."}]
        errors = json.loads(args.errors)
        tag_ids = args.tag_ids.split(",")
        if is_export:
            data = api.tags_export(args.flow, args.export, errors, tag_ids)
        elif is_import:
            data = api.tags_import(args.flow, args.import_id, errors, tag_ids)
        else:
            print("Error: Specify --export or --import", file=sys.stderr)
            sys.exit(1)
        print_result(data, args.format)

    elif args.action == "integration-summary":
        data = api.integration_summary(args.integration,
                                       occurred_gte=args.since, occurred_lte=args.until,
                                       source=args.source)
        columns = ["_flowId", "numError"]
        print_result(data, args.format, columns)

    elif args.action == "integration-assign":
        error_ids = args.ids.split(",")
        data = api.assign_integration(args.integration, error_ids, args.email)
        print_result(data, args.format)


def cmd_caches(args):
    """Handle lookup caches subcommands."""
    client = CeligoClient(args.env)
    api = LookupCachesAPI(client)

    if args.action == "list":
        data = api.list()
        columns = ["_id", "name", "description"]
        print_result(data, args.format, columns)

    elif args.action == "get":
        print_result(api.get(args.id), args.format)

    elif args.action == "data":
        keys = args.keys.split(",") if args.keys else None
        data = api.data(args.id, keys=keys, starts_with=args.starts_with,
                        page_size=args.page_size, start_after_key=args.start_after)
        print_result(data, args.format)


def cmd_tags(args):
    """Handle tags subcommands."""
    client = CeligoClient(args.env)
    api = TagsAPI(client)

    if args.action == "list":
        data = api.list()
        columns = ["_id", "tag", "tagId"]
        print_result(data, args.format, columns)

    elif args.action == "get":
        print_result(api.get(args.id), args.format)

    elif args.action == "create":
        print_result(api.create(args.name), args.format)

    elif args.action == "update":
        print_result(api.update(args.id, args.name, args.tag_id), args.format)

    elif args.action == "delete":
        print_result(api.delete(args.id), args.format)


def cmd_users(args):
    """Handle users subcommands."""
    client = CeligoClient(args.env)
    api = UsersAPI(client)

    if args.action == "list":
        data = api.list()
        print_result(data, args.format)

    elif args.action == "get":
        print_result(api.get(args.id), args.format)


# =============================================================================
# CLI Parser Setup
# =============================================================================

def create_parser():
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Celigo API CLI - Full REST API Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s integrations list
  %(prog)s integrations get <id>
  %(prog)s flows list --integration <id>
  %(prog)s flows run <id>
  %(prog)s jobs list --status running
  %(prog)s errors list --flow <id> --import <id>
  %(prog)s errors retry --flow <id> --import <id> --keys key1,key2
        """
    )

    # Global options
    parser.add_argument("--env", "-e", default=None,
                        help="Environment (production/sandbox)")
    parser.add_argument("--format", "-f", choices=["table", "json"], default="table",
                        help="Output format (default: table)")

    subparsers = parser.add_subparsers(dest="resource", help="Resource type")

    # --- Integrations ---
    int_parser = subparsers.add_parser("integrations", help="Integration operations")
    int_sub = int_parser.add_subparsers(dest="action")

    int_list = int_sub.add_parser("list", help="List integrations")
    int_list.add_argument("--sandbox", type=lambda x: x.lower() == 'true',
                          help="Filter by sandbox status")

    int_get = int_sub.add_parser("get", help="Get integration")
    int_get.add_argument("id", help="Integration ID")

    int_flows = int_sub.add_parser("flows", help="Get integration flows")
    int_flows.add_argument("id", help="Integration ID")

    int_conns = int_sub.add_parser("connections", help="Get integration connections")
    int_conns.add_argument("id", help="Integration ID")

    int_exports = int_sub.add_parser("exports", help="Get integration exports")
    int_exports.add_argument("id", help="Integration ID")

    int_imports = int_sub.add_parser("imports", help="Get integration imports")
    int_imports.add_argument("id", help="Integration ID")

    int_users = int_sub.add_parser("users", help="Get integration users")
    int_users.add_argument("id", help="Integration ID")

    int_template = int_sub.add_parser("template", help="Get integration template URL")
    int_template.add_argument("id", help="Integration ID")

    int_deps = int_sub.add_parser("dependencies", help="Get integration dependencies")
    int_deps.add_argument("id", help="Integration ID")

    int_audit = int_sub.add_parser("audit", help="Get integration audit log")
    int_audit.add_argument("id", help="Integration ID")
    int_audit.add_argument("--page", type=int, default=1)
    int_audit.add_argument("--page-size", type=int, default=100)

    int_errors = int_sub.add_parser("errors", help="Get integration error summary")
    int_errors.add_argument("id", help="Integration ID")
    int_errors.add_argument("--since", help="Occurred after (ISO 8601)")
    int_errors.add_argument("--until", help="Occurred before (ISO 8601)")
    int_errors.add_argument("--source", help="Error source filter")

    # --- Flows ---
    flow_parser = subparsers.add_parser("flows", help="Flow operations")
    flow_sub = flow_parser.add_subparsers(dest="action")

    flow_list = flow_sub.add_parser("list", help="List flows")
    flow_list.add_argument("--integration", help="Filter by integration ID")
    flow_list.add_argument("--disabled", type=lambda x: x.lower() == 'true',
                           help="Filter by disabled status")
    flow_list.add_argument("--page", type=int, default=1)
    flow_list.add_argument("--page-size", type=int, default=100)

    flow_get = flow_sub.add_parser("get", help="Get flow")
    flow_get.add_argument("id", help="Flow ID")

    flow_run = flow_sub.add_parser("run", help="Run/trigger flow")
    flow_run.add_argument("id", help="Flow ID")
    flow_run.add_argument("--export-ids", help="Comma-separated export IDs")
    flow_run.add_argument("--start-date", help="Start date for delta flows (ISO 8601)")
    flow_run.add_argument("--end-date", help="End date for delta flows (ISO 8601)")

    flow_template = flow_sub.add_parser("template", help="Get flow template URL")
    flow_template.add_argument("id", help="Flow ID")

    flow_deps = flow_sub.add_parser("dependencies", help="Get flow dependencies")
    flow_deps.add_argument("id", help="Flow ID")

    flow_desc = flow_sub.add_parser("descendants", help="Get flow descendants")
    flow_desc.add_argument("id", help="Flow ID")

    flow_jobs = flow_sub.add_parser("jobs-latest", help="Get latest flow jobs")
    flow_jobs.add_argument("id", help="Flow ID")

    flow_last = flow_sub.add_parser("last-export-datetime", help="Get last export time")
    flow_last.add_argument("id", help="Flow ID")

    flow_audit = flow_sub.add_parser("audit", help="Get flow audit log")
    flow_audit.add_argument("id", help="Flow ID")

    # --- Connections ---
    conn_parser = subparsers.add_parser("connections", help="Connection operations")
    conn_sub = conn_parser.add_subparsers(dest="action")

    conn_list = conn_sub.add_parser("list", help="List connections")
    conn_list.add_argument("--integration", help="Filter by integration ID")
    conn_list.add_argument("--type", help="Filter by connection type")

    conn_get = conn_sub.add_parser("get", help="Get connection")
    conn_get.add_argument("id", help="Connection ID")

    conn_test = conn_sub.add_parser("test", help="Test/ping connection")
    conn_test.add_argument("id", help="Connection ID")

    conn_debug = conn_sub.add_parser("debug-log", help="Get debug log")
    conn_debug.add_argument("id", help="Connection ID")

    conn_logs = conn_sub.add_parser("logs", help="Get usage logs")
    conn_logs.add_argument("id", help="Connection ID")

    conn_deps = conn_sub.add_parser("dependencies", help="Get dependencies")
    conn_deps.add_argument("id", help="Connection ID")

    # --- Exports ---
    exp_parser = subparsers.add_parser("exports", help="Export operations")
    exp_sub = exp_parser.add_subparsers(dest="action")

    exp_list = exp_sub.add_parser("list", help="List exports")
    exp_list.add_argument("--page", type=int, default=1)
    exp_list.add_argument("--page-size", type=int, default=100)

    exp_get = exp_sub.add_parser("get", help="Get export")
    exp_get.add_argument("id", help="Export ID")

    exp_audit = exp_sub.add_parser("audit", help="Get audit log")
    exp_audit.add_argument("id", help="Export ID")

    exp_deps = exp_sub.add_parser("dependencies", help="Get dependencies")
    exp_deps.add_argument("id", help="Export ID")

    # --- Imports ---
    imp_parser = subparsers.add_parser("imports", help="Import operations")
    imp_sub = imp_parser.add_subparsers(dest="action")

    imp_list = imp_sub.add_parser("list", help="List imports")
    imp_list.add_argument("--page", type=int, default=1)
    imp_list.add_argument("--page-size", type=int, default=100)

    imp_get = imp_sub.add_parser("get", help="Get import")
    imp_get.add_argument("id", help="Import ID")

    imp_audit = imp_sub.add_parser("audit", help="Get audit log")
    imp_audit.add_argument("id", help="Import ID")

    imp_deps = imp_sub.add_parser("dependencies", help="Get dependencies")
    imp_deps.add_argument("id", help="Import ID")

    # --- Jobs ---
    job_parser = subparsers.add_parser("jobs", help="Job operations")
    job_sub = job_parser.add_subparsers(dest="action")

    job_list = job_sub.add_parser("list", help="List jobs")
    job_list.add_argument("--integration", help="Filter by integration ID")
    job_list.add_argument("--flow", help="Filter by flow ID")
    job_list.add_argument("--export", help="Filter by export ID")
    job_list.add_argument("--flow-job", help="Filter by parent flow job ID")
    job_list.add_argument("--status", choices=["queued", "running", "completed", "failed", "canceled"])
    job_list.add_argument("--type", choices=["flow", "export", "import"])
    job_list.add_argument("--since", help="Created after (ISO 8601)")
    job_list.add_argument("--until", help="Created before (ISO 8601)")
    job_list.add_argument("--flow-ids", help="Comma-separated flow IDs")

    job_get = job_sub.add_parser("get", help="Get job")
    job_get.add_argument("id", help="Job ID")

    job_cancel = job_sub.add_parser("cancel", help="Cancel running job")
    job_cancel.add_argument("id", help="Job ID (must be flow type)")

    # --- Errors ---
    err_parser = subparsers.add_parser("errors", help="Error operations")
    err_sub = err_parser.add_subparsers(dest="action")

    # Common error args
    def add_error_args(p, with_keys=False, with_ids=False, with_email=False):
        p.add_argument("--flow", required=True, help="Flow ID")
        p.add_argument("--export", help="Export ID")
        p.add_argument("--import", dest="import_id", help="Import ID")
        p.add_argument("--since", help="Occurred after (ISO 8601)")
        p.add_argument("--until", help="Occurred before (ISO 8601)")
        p.add_argument("--source", help="Error source filter")
        if with_keys:
            p.add_argument("--keys", required=True, help="Comma-separated retry data keys")
        if with_ids:
            p.add_argument("--ids", required=True, help="Comma-separated error IDs")
        if with_email:
            p.add_argument("--email", required=True, help="User email")

    err_list = err_sub.add_parser("list", help="List errors")
    add_error_args(err_list)

    err_resolved = err_sub.add_parser("resolved", help="List resolved errors")
    add_error_args(err_resolved)

    err_retry_data = err_sub.add_parser("retry-data", help="Get retry data")
    err_retry_data.add_argument("--flow", required=True, help="Flow ID")
    err_retry_data.add_argument("--export", help="Export ID")
    err_retry_data.add_argument("--import", dest="import_id", help="Import ID")
    err_retry_data.add_argument("--key", required=True, help="Retry data key")

    err_resolve = err_sub.add_parser("resolve", help="Resolve errors")
    err_resolve.add_argument("--flow", required=True, help="Flow ID")
    err_resolve.add_argument("--export", help="Export ID")
    err_resolve.add_argument("--import", dest="import_id", help="Import ID")
    err_resolve.add_argument("--ids", required=True, help="Comma-separated error IDs")

    err_retry = err_sub.add_parser("retry", help="Retry errors")
    err_retry.add_argument("--flow", required=True, help="Flow ID")
    err_retry.add_argument("--export", help="Export ID")
    err_retry.add_argument("--import", dest="import_id", help="Import ID")
    err_retry.add_argument("--keys", required=True, help="Comma-separated retry data keys")

    err_assign = err_sub.add_parser("assign", help="Assign errors to user")
    err_assign.add_argument("--flow", required=True, help="Flow ID")
    err_assign.add_argument("--export", help="Export ID")
    err_assign.add_argument("--import", dest="import_id", help="Import ID")
    err_assign.add_argument("--ids", required=True, help="Comma-separated error IDs")
    err_assign.add_argument("--email", required=True, help="User email")

    err_tags = err_sub.add_parser("tags", help="Tag errors")
    err_tags.add_argument("--flow", required=True, help="Flow ID")
    err_tags.add_argument("--export", help="Export ID")
    err_tags.add_argument("--import", dest="import_id", help="Import ID")
    err_tags.add_argument("--errors", required=True, help='JSON array: [{"id":"...","rdk":"..."}]')
    err_tags.add_argument("--tag-ids", required=True, help="Comma-separated tag IDs")

    err_int_summary = err_sub.add_parser("integration-summary", help="Get integration error summary")
    err_int_summary.add_argument("--integration", required=True, help="Integration ID")
    err_int_summary.add_argument("--since", help="Occurred after (ISO 8601)")
    err_int_summary.add_argument("--until", help="Occurred before (ISO 8601)")
    err_int_summary.add_argument("--source", help="Error source filter")

    err_int_assign = err_sub.add_parser("integration-assign", help="Assign integration errors")
    err_int_assign.add_argument("--integration", required=True, help="Integration ID")
    err_int_assign.add_argument("--ids", required=True, help="Comma-separated error IDs")
    err_int_assign.add_argument("--email", required=True, help="User email")

    # --- Lookup Caches ---
    cache_parser = subparsers.add_parser("caches", help="Lookup cache operations")
    cache_sub = cache_parser.add_subparsers(dest="action")

    cache_list = cache_sub.add_parser("list", help="List caches")

    cache_get = cache_sub.add_parser("get", help="Get cache metadata")
    cache_get.add_argument("id", help="Cache ID")

    cache_data = cache_sub.add_parser("data", help="Get cache data")
    cache_data.add_argument("id", help="Cache ID")
    cache_data.add_argument("--keys", help="Comma-separated keys to retrieve")
    cache_data.add_argument("--starts-with", help="Key prefix filter")
    cache_data.add_argument("--page-size", type=int, help="Items per page")
    cache_data.add_argument("--start-after", help="Pagination cursor (key)")

    # --- Tags ---
    tag_parser = subparsers.add_parser("tags", help="Tag operations")
    tag_sub = tag_parser.add_subparsers(dest="action")

    tag_list = tag_sub.add_parser("list", help="List tags")

    tag_get = tag_sub.add_parser("get", help="Get tag")
    tag_get.add_argument("id", help="Tag ID")

    tag_create = tag_sub.add_parser("create", help="Create tag")
    tag_create.add_argument("name", help="Tag name")

    tag_update = tag_sub.add_parser("update", help="Update tag")
    tag_update.add_argument("id", help="Tag database ID (_id)")
    tag_update.add_argument("name", help="New tag name")
    tag_update.add_argument("tag_id", help="Tag public ID (tagId)")

    tag_delete = tag_sub.add_parser("delete", help="Delete tag")
    tag_delete.add_argument("id", help="Tag ID")

    # --- Users ---
    user_parser = subparsers.add_parser("users", help="User operations")
    user_sub = user_parser.add_subparsers(dest="action")

    user_list = user_sub.add_parser("list", help="List users")

    user_get = user_sub.add_parser("get", help="Get user")
    user_get.add_argument("id", help="User share ID")

    return parser


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = create_parser()
    args = parser.parse_args()

    if not args.resource:
        parser.print_help()
        sys.exit(1)

    # Route to appropriate handler
    handlers = {
        "integrations": cmd_integrations,
        "flows": cmd_flows,
        "connections": cmd_connections,
        "exports": cmd_exports,
        "imports": cmd_imports,
        "jobs": cmd_jobs,
        "errors": cmd_errors,
        "caches": cmd_caches,
        "tags": cmd_tags,
        "users": cmd_users,
    }

    handler = handlers.get(args.resource)
    if handler:
        if not args.action:
            print(f"Error: Specify an action for '{args.resource}'", file=sys.stderr)
            parser.parse_args([args.resource, "-h"])
        handler(args)
    else:
        print(f"Unknown resource: {args.resource}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
