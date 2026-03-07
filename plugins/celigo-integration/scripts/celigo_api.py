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
MAX_JSON_SIZE = 1024 * 1024  # 1MB limit for --data payloads
MAX_JSON_DEPTH = 20


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
        if not self.api_url.startswith("https://"):
            raise ValueError(f"API URL must use HTTPS, got: {self.api_url}")
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

    def patch(self, endpoint: str, data: dict = None) -> dict:
        return self._make_request("PATCH", endpoint, data=data)

    def delete(self, endpoint: str, data: dict = None, params: dict = None) -> dict:
        return self._make_request("DELETE", endpoint, data=data, params=params)


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

    def create(self, data: dict) -> dict:
        """Create a new integration."""
        return self.client.post("/integrations", data)

    def update(self, integration_id: str, data: dict) -> dict:
        """Update an existing integration (full-replace PUT)."""
        return self.client.put(f"/integrations/{integration_id}", data)

    def delete(self, integration_id: str) -> dict:
        """Delete an integration."""
        return self.client.delete(f"/integrations/{integration_id}")

    def register_connections(self, integration_id: str, data: dict) -> dict:
        """Register connections to an integration."""
        return self.client.put(f"/integrations/{integration_id}/connections/register", data)

    def download_template(self, integration_id: str) -> dict:
        """Download integration as installable template."""
        return self.client.post(f"/integrations/{integration_id}/template")


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

    def create(self, data: dict) -> dict:
        """Create a new flow."""
        return self.client.post("/flows", data)

    def update(self, flow_id: str, data: dict) -> dict:
        """Update an existing flow."""
        return self.client.put(f"/flows/{flow_id}", data)

    def delete(self, flow_id: str) -> dict:
        """Delete a flow."""
        return self.client.delete(f"/flows/{flow_id}")

    def clone(self, flow_id: str) -> dict:
        """Clone a flow."""
        return self.client.post(f"/flows/{flow_id}/clone")

    def patch(self, flow_id: str, data: list) -> dict:
        """Partial update flow (JSON Patch RFC 6902)."""
        return self.client.patch(f"/flows/{flow_id}", data)

    def replace_connection(self, flow_id: str, data: dict) -> dict:
        """Replace connection in a flow."""
        return self.client.put(f"/flows/{flow_id}/replaceConnection", data)


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

    def create(self, data: dict) -> dict:
        """Create a new connection."""
        return self.client.post("/connections", data)

    def update(self, connection_id: str, data: dict) -> dict:
        """Update an existing connection (full-replace PUT)."""
        return self.client.put(f"/connections/{connection_id}", data)

    def patch(self, connection_id: str, data: list) -> dict:
        """Partial update connection (JSON Patch RFC 6902)."""
        return self.client.patch(f"/connections/{connection_id}", data)

    def delete(self, connection_id: str) -> dict:
        """Delete a connection."""
        return self.client.delete(f"/connections/{connection_id}")

    def audit(self, connection_id: str) -> list:
        """Get connection audit log."""
        return self.client.get(f"/connections/{connection_id}/audit")

    def oauth2(self, connection_id: str) -> dict:
        """Get OAuth2 token info for connection."""
        return self.client.get(f"/connections/{connection_id}/oauth2")

    def ping_virtual(self, data: dict) -> dict:
        """Test a virtual (unsaved) connection."""
        return self.client.post("/connections/ping", data)

    def virtual_export(self, connection_id: str, data: dict) -> dict:
        """Run a virtual export against a connection."""
        return self.client.post(f"/connections/{connection_id}/export", data)

    def virtual_export_pages(self, connection_id: str, data: dict) -> dict:
        """Run a paged virtual export against a connection."""
        return self.client.post(f"/connections/{connection_id}/export/pages", data)

    def virtual_import(self, connection_id: str, data: dict) -> dict:
        """Run a virtual import against a connection."""
        return self.client.post(f"/connections/{connection_id}/import", data)

    def virtual_import_map(self, connection_id: str, data: dict) -> dict:
        """Get virtual import mapping for a connection."""
        return self.client.post(f"/connections/{connection_id}/import/map", data)


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

    def create(self, data: dict) -> dict:
        """Create a new export."""
        return self.client.post("/exports", data)

    def update(self, export_id: str, data: dict) -> dict:
        """Update an existing export."""
        return self.client.put(f"/exports/{export_id}", data)

    def delete(self, export_id: str) -> dict:
        """Delete an export."""
        return self.client.delete(f"/exports/{export_id}")

    def clone(self, export_id: str) -> dict:
        """Clone an export."""
        return self.client.post(f"/exports/{export_id}/clone")

    def invoke(self, export_id: str, data: dict = None) -> dict:
        """Invoke an export (run standalone)."""
        return self.client.post(f"/exports/{export_id}/invoke", data)

    def patch(self, export_id: str, data: list) -> dict:
        """Partial update export (JSON Patch RFC 6902)."""
        return self.client.patch(f"/exports/{export_id}", data)

    def replace_connection(self, export_id: str, data: dict) -> dict:
        """Replace connection in an export."""
        return self.client.put(f"/exports/{export_id}/replaceConnection", data)


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

    def create(self, data: dict) -> dict:
        """Create a new import."""
        return self.client.post("/imports", data)

    def update(self, import_id: str, data: dict) -> dict:
        """Update an existing import."""
        return self.client.put(f"/imports/{import_id}", data)

    def delete(self, import_id: str) -> dict:
        """Delete an import."""
        return self.client.delete(f"/imports/{import_id}")

    def clone(self, import_id: str) -> dict:
        """Clone an import."""
        return self.client.post(f"/imports/{import_id}/clone")

    def invoke(self, import_id: str, data: dict = None) -> dict:
        """Invoke an import (run standalone)."""
        return self.client.post(f"/imports/{import_id}/invoke", data)

    def patch(self, import_id: str, data: list) -> dict:
        """Partial update import (JSON Patch RFC 6902)."""
        return self.client.patch(f"/imports/{import_id}", data)

    def replace_connection(self, import_id: str, data: dict) -> dict:
        """Replace connection in an import."""
        return self.client.put(f"/imports/{import_id}/replaceConnection", data)


# =============================================================================
# Resource: Scripts
# =============================================================================

class ScriptsAPI:
    """Scripts resource operations."""

    def __init__(self, client: CeligoClient):
        self.client = client

    def list(self) -> list:
        """List all scripts."""
        return self.client.get("/scripts")

    def get(self, script_id: str) -> dict:
        """Get single script."""
        return self.client.get(f"/scripts/{script_id}")

    def create(self, data: dict) -> dict:
        """Create a new script."""
        return self.client.post("/scripts", data)

    def update(self, script_id: str, data: dict) -> dict:
        """Update an existing script."""
        return self.client.put(f"/scripts/{script_id}", data)

    def delete(self, script_id: str) -> dict:
        """Delete a script."""
        return self.client.delete(f"/scripts/{script_id}")

    def logs(self, script_id: str) -> list:
        """Get script execution logs."""
        return self.client.get(f"/scripts/{script_id}/logs")


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
        """Resolve export errors (PUT /resolved, not POST)."""
        return self.client.put(f"/flows/{flow_id}/{export_id}/resolved",
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
        """Resolve import errors (PUT /resolved, not POST)."""
        return self.client.put(f"/flows/{flow_id}/{import_id}/resolved",
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

    def delete_resolved_export(self, flow_id: str, export_id: str) -> dict:
        """Delete resolved export errors."""
        return self.client.delete(f"/flows/{flow_id}/{export_id}/resolved")

    def delete_resolved_import(self, flow_id: str, import_id: str) -> dict:
        """Delete resolved import errors."""
        return self.client.delete(f"/flows/{flow_id}/{import_id}/resolved")

    def update_retry_data(self, flow_id: str, exp_or_imp_id: str,
                          retry_key: str, data: dict) -> dict:
        """Update retry data for an error before retrying."""
        return self.client.put(f"/flows/{flow_id}/{exp_or_imp_id}/{retry_key}/data", data)

    def view_request(self, flow_id: str, page_processor_id: str,
                     request_key: str) -> dict:
        """View request/response details for an error."""
        return self.client.get(f"/flows/{flow_id}/{page_processor_id}/requests/{request_key}")


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

    def delete(self, cache_id: str) -> dict:
        """Delete a lookup cache."""
        return self.client.delete(f"/lookupcaches/{cache_id}")

    def data(self, cache_id: str, keys: list = None, starts_with: str = None,
             page_size: int = None, start_after_key: str = None) -> dict:
        """Get lookup cache data (POST /getData — NOT GET)."""
        body = {}
        if keys:
            body["keys"] = keys
        if starts_with:
            body["starts_with"] = starts_with
        if page_size:
            body["pageSize"] = page_size
        if start_after_key:
            body["start_after_key"] = start_after_key
        return self.client.post(f"/lookupcaches/{cache_id}/getData", body if body else None)

    def data_update(self, cache_id: str, data: dict) -> dict:
        """Upsert lookup cache data (POST /data)."""
        return self.client.post(f"/lookupcaches/{cache_id}/data", data)

    def data_delete(self, cache_id: str, keys: list) -> dict:
        """Delete specific keys from lookup cache data."""
        return self.client.delete(f"/lookupcaches/{cache_id}/data", data={"keys": keys})

    def data_purge(self, cache_id: str) -> dict:
        """Delete all data from lookup cache."""
        return self.client.delete(f"/lookupcaches/{cache_id}/data/purge")


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

    def update(self, user_id: str, data: dict) -> dict:
        """Update user permissions (full-replace PUT)."""
        return self.client.put(f"/ashares/{user_id}", data)

    def delete(self, user_id: str) -> dict:
        """Remove a user."""
        return self.client.delete(f"/ashares/{user_id}")

    def disable(self, user_id: str) -> dict:
        """Disable a user."""
        return self.client.put(f"/ashares/{user_id}/disable")

    def invite(self, data: dict) -> dict:
        """Invite a user (POST /invite, not POST /ashares)."""
        return self.client.post("/invite", data)

    def invite_multiple(self, data: dict) -> dict:
        """Invite multiple users at once."""
        return self.client.post("/invite/multiple", data)

    def reinvite(self, data: dict) -> dict:
        """Reinvite a user."""
        return self.client.post("/reinvite", data)

    def sso_update(self, client_id: str, data: dict) -> dict:
        """Update SSO client settings."""
        return self.client.patch(f"/ssoclients/{client_id}", data)


# =============================================================================
# Resource: State API
# =============================================================================

class StateAPI:
    """State API for persistent key-value storage."""

    def __init__(self, client: CeligoClient):
        self.client = client

    def list(self) -> list:
        """List all state keys."""
        return self.client.get("/state")

    def get(self, key: str) -> dict:
        """Get state value by key."""
        return self.client.get(f"/state/{quote(key, safe='')}")

    def set(self, key: str, data: dict) -> dict:
        """Set state value for key."""
        return self.client.put(f"/state/{quote(key, safe='')}", data)

    def delete(self, key: str) -> dict:
        """Delete a state key."""
        return self.client.delete(f"/state/{quote(key, safe='')}")

    def list_scoped(self, import_id: str) -> list:
        """List import-scoped state keys."""
        return self.client.get(f"/imports/{import_id}/state")

    def get_scoped(self, import_id: str, key: str) -> dict:
        """Get import-scoped state value."""
        return self.client.get(f"/imports/{import_id}/state/{quote(key, safe='')}")

    def set_scoped(self, import_id: str, key: str, data: dict) -> dict:
        """Set import-scoped state value."""
        return self.client.put(f"/imports/{import_id}/state/{quote(key, safe='')}", data)


# =============================================================================
# Resource: File Definitions
# =============================================================================

class FileDefinitionsAPI:
    """File definitions resource operations (standard CRUD)."""

    def __init__(self, client: CeligoClient):
        self.client = client

    def list(self) -> list:
        """List all file definitions."""
        return self.client.get("/filedefinitions")

    def get(self, fd_id: str) -> dict:
        """Get a file definition."""
        return self.client.get(f"/filedefinitions/{fd_id}")

    def create(self, data: dict) -> dict:
        """Create a file definition."""
        return self.client.post("/filedefinitions", data)

    def update(self, fd_id: str, data: dict) -> dict:
        """Update a file definition (full-replace PUT)."""
        return self.client.put(f"/filedefinitions/{fd_id}", data)

    def delete(self, fd_id: str) -> dict:
        """Delete a file definition."""
        return self.client.delete(f"/filedefinitions/{fd_id}")


# =============================================================================
# Resource: Recycle Bin
# =============================================================================

class RecycleBinAPI:
    """Recycle bin operations (recycleBinTTL endpoints)."""

    def __init__(self, client: CeligoClient):
        self.client = client

    def list(self, resource_type: str = None) -> list:
        """List recycled resources, optionally filtered by type."""
        if resource_type:
            return self.client.get(f"/recycleBinTTL/{resource_type}")
        return self.client.get("/recycleBinTTL")

    def get(self, resource_type: str, resource_id: str) -> dict:
        """Get a specific recycled resource."""
        return self.client.get(f"/recycleBinTTL/{resource_type}/{resource_id}")

    def restore(self, resource_type: str, resource_id: str) -> dict:
        """Restore a recycled resource."""
        return self.client.post(f"/recycleBinTTL/{resource_type}/{resource_id}")

    def delete(self, resource_type: str, resource_id: str) -> dict:
        """Permanently delete a recycled resource."""
        return self.client.delete(f"/recycleBinTTL/{resource_type}/{resource_id}")


# =============================================================================
# Resource: Audit
# =============================================================================

class AuditAPI:
    """Account-wide audit log."""

    def __init__(self, client: CeligoClient):
        self.client = client

    def list(self, resource_type: str = None, user: str = None,
             since: str = None, until: str = None) -> list:
        """List account-wide audit entries."""
        params = {}
        if resource_type:
            params["resourceType"] = resource_type
        if user:
            params["byUser"] = user
        if since:
            params["startDate"] = since
        if until:
            params["endDate"] = until
        return self.client.get("/audit", params)


# =============================================================================
# Resource: iClients
# =============================================================================

class IClientsAPI:
    """iClients (OAuth2 app) resource operations."""

    def __init__(self, client: CeligoClient):
        self.client = client

    def list(self) -> list:
        """List all iClients."""
        return self.client.get("/iclients")

    def get(self, iclient_id: str) -> dict:
        """Get an iClient."""
        return self.client.get(f"/iclients/{iclient_id}")

    def create(self, data: dict) -> dict:
        """Create an iClient."""
        return self.client.post("/iclients", data)

    def update(self, iclient_id: str, data: dict) -> dict:
        """Update an iClient (full-replace PUT)."""
        return self.client.put(f"/iclients/{iclient_id}", data)

    def patch(self, iclient_id: str, data: list) -> dict:
        """Partial update iClient (JSON Patch RFC 6902)."""
        return self.client.patch(f"/iclients/{iclient_id}", data)

    def delete(self, iclient_id: str) -> dict:
        """Delete an iClient."""
        return self.client.delete(f"/iclients/{iclient_id}")

    def dependencies(self, iclient_id: str) -> dict:
        """Get iClient dependencies."""
        return self.client.get(f"/iclients/{iclient_id}/dependencies")


# =============================================================================
# Resource: Connectors & Licenses
# =============================================================================

class ConnectorsAPI:
    """Connectors and licenses resource operations."""

    def __init__(self, client: CeligoClient):
        self.client = client

    def list(self) -> list:
        """List all connectors."""
        return self.client.get("/connectors")

    def get(self, connector_id: str) -> dict:
        """Get a connector."""
        return self.client.get(f"/connectors/{connector_id}")

    def create(self, data: dict) -> dict:
        """Create a connector."""
        return self.client.post("/connectors", data)

    def update(self, connector_id: str, data: dict) -> dict:
        """Update a connector (full-replace PUT)."""
        return self.client.put(f"/connectors/{connector_id}", data)

    def delete(self, connector_id: str) -> dict:
        """Delete a connector."""
        return self.client.delete(f"/connectors/{connector_id}")

    def install_base(self, connector_id: str) -> list:
        """Get connector install base."""
        return self.client.get(f"/connectors/{connector_id}/installBase")

    def publish_update(self, connector_id: str, data: dict) -> dict:
        """Publish a connector update."""
        return self.client.put(f"/connectors/{connector_id}/update", data)

    def list_licenses(self, connector_id: str) -> list:
        """List licenses for a connector."""
        return self.client.get(f"/connectors/{connector_id}/licenses")

    def create_license(self, connector_id: str, data: dict) -> dict:
        """Create a license for a connector."""
        return self.client.post(f"/connectors/{connector_id}/licenses", data)

    def get_license(self, connector_id: str, license_id: str) -> dict:
        """Get a specific license."""
        return self.client.get(f"/connectors/{connector_id}/licenses/{license_id}")

    def update_license(self, connector_id: str, license_id: str, data: dict) -> dict:
        """Update a license."""
        return self.client.put(f"/connectors/{connector_id}/licenses/{license_id}", data)

    def delete_license(self, connector_id: str, license_id: str) -> dict:
        """Delete a license."""
        return self.client.delete(f"/connectors/{connector_id}/licenses/{license_id}")


# =============================================================================
# Resource: Processors (Parser & Generator)
# =============================================================================

class ProcessorsAPI:
    """Data processors for parsing and generating structured files."""

    def __init__(self, client: CeligoClient):
        self.client = client

    def parse_xml(self, data: dict) -> dict:
        """Parse XML data."""
        return self.client.post("/processors/xmlParser", data)

    def parse_csv(self, data: dict) -> dict:
        """Parse CSV data."""
        return self.client.post("/processors/csvParser", data)

    def generate_csv(self, data: dict) -> dict:
        """Generate CSV data."""
        return self.client.post("/processors/csvDataGenerator", data)

    def generate_structured(self, data: dict) -> dict:
        """Generate structured file data."""
        return self.client.post("/processors/structuredFileGenerator", data)

    def parse_structured(self, data: dict) -> dict:
        """Parse structured file data."""
        return self.client.post("/processors/structuredFileParser", data)


# =============================================================================
# Resource: Templates
# =============================================================================

class TemplatesAPI:
    """Template resource operations."""

    def __init__(self, client: CeligoClient):
        self.client = client

    def list(self) -> list:
        """List all templates."""
        return self.client.get("/template")

    def update(self, template_id: str, data: dict) -> dict:
        """Update a template."""
        return self.client.put(f"/template/{template_id}", data)


# =============================================================================
# Resource: EDI/B2B
# =============================================================================

class EDIAPI:
    """EDI/B2B profile and transaction operations."""

    def __init__(self, client: CeligoClient):
        self.client = client

    def list(self) -> list:
        """List all EDI profiles."""
        return self.client.get("/ediprofiles")

    def get(self, profile_id: str) -> dict:
        """Get an EDI profile."""
        return self.client.get(f"/ediprofiles/{profile_id}")

    def create(self, data: dict) -> dict:
        """Create an EDI profile."""
        return self.client.post("/ediprofiles", data)

    def update(self, profile_id: str, data: dict) -> dict:
        """Update an EDI profile (full-replace PUT)."""
        return self.client.put(f"/ediprofiles/{profile_id}", data)

    def patch(self, profile_id: str, data: list) -> dict:
        """Partial update EDI profile (JSON Patch RFC 6902)."""
        return self.client.patch(f"/ediprofiles/{profile_id}", data)

    def delete(self, profile_id: str) -> dict:
        """Delete an EDI profile."""
        return self.client.delete(f"/ediprofiles/{profile_id}")

    def update_transactions(self, data: dict) -> dict:
        """Update EDI transactions."""
        return self.client.patch("/ediTransactions", data)

    def query_transactions(self, data: dict) -> dict:
        """Query EDI transactions."""
        return self.client.post("/ediTransactions/query", data)

    def get_fa_details(self, transaction_id: str) -> dict:
        """Get functional acknowledgment details for a transaction."""
        return self.client.get(f"/ediTransactions/{transaction_id}/faDetails")


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

    elif args.action == "create":
        data = _resolve_json_input(args)
        if not data.get("name"):
            print("Error: Integration name is required.", file=sys.stderr)
            sys.exit(1)
        print_result(api.create(data), args.format)

    elif args.action == "update":
        updates = _resolve_json_input(args)
        if not updates:
            print("Error: No update data provided.", file=sys.stderr)
            sys.exit(1)
        current = api.get(args.id)
        if current.get("error"):
            print_result(current, args.format)
            return
        merged = _merge_updates_for_put(current, updates, INTEGRATION_READONLY_FIELDS)
        print_result(api.update(args.id, merged), args.format)

    elif args.action == "delete":
        print_result(api.delete(args.id), args.format)

    elif args.action == "register-connections":
        data = _resolve_json_input(args)
        print_result(api.register_connections(args.id, data), args.format)

    elif args.action == "download-template":
        print_result(api.download_template(args.id), args.format)


# Read-only fields to strip before PUT requests (Celigo PUT is full-replace)
FLOW_READONLY_FIELDS = frozenset(["_id", "lastModified", "createdAt", "lastExecutedAt"])
EXPORT_READONLY_FIELDS = frozenset(["_id", "lastModified", "createdAt"])
IMPORT_READONLY_FIELDS = frozenset(["_id", "lastModified", "createdAt"])
SCRIPT_READONLY_FIELDS = frozenset(["_id", "lastModified", "createdAt"])
CONNECTION_READONLY_FIELDS = frozenset(["_id", "lastModified", "createdAt"])
INTEGRATION_READONLY_FIELDS = frozenset(["_id", "lastModified", "createdAt"])
LOOKUPCACHE_READONLY_FIELDS = frozenset(["_id", "lastModified", "createdAt"])
USER_READONLY_FIELDS = frozenset(["_id", "lastModified", "createdAt"])
FILEDEFINITION_READONLY_FIELDS = frozenset(["_id", "lastModified", "createdAt"])
ICLIENT_READONLY_FIELDS = frozenset(["_id", "lastModified", "createdAt"])
CONNECTOR_READONLY_FIELDS = frozenset(["_id", "lastModified", "createdAt"])
EDIPROFILE_READONLY_FIELDS = frozenset(["_id", "lastModified", "createdAt"])


def _merge_updates_for_put(current: dict, updates: dict, readonly_fields: frozenset) -> dict:
    """Merge updates into current state for Celigo PUT (full-replace) request."""
    merged = current.copy()
    for field in readonly_fields:
        merged.pop(field, None)
    merged.update(updates)
    return merged


def _safe_json_parse(json_string: str) -> dict:
    """Parse JSON with size and depth limits."""
    if len(json_string) > MAX_JSON_SIZE:
        raise ValueError(f"JSON payload too large: {len(json_string)} bytes (max {MAX_JSON_SIZE})")

    def _check_depth(obj: Any, depth: int = 0) -> None:
        if depth > MAX_JSON_DEPTH:
            raise ValueError(f"JSON nesting too deep (max {MAX_JSON_DEPTH})")
        if isinstance(obj, dict):
            for v in obj.values():
                _check_depth(v, depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                _check_depth(item, depth + 1)

    data = json.loads(json_string)
    _check_depth(data)
    return data


def _validate_code_file(file_path: str) -> Path:
    """Validate code file path: must exist, must be .js or .json."""
    path = Path(file_path).resolve()
    if not path.is_file():
        raise ValueError(f"Not a file: {file_path}")
    if path.suffix not in ('.js', '.json'):
        raise ValueError(f"Invalid file type '{path.suffix}' — only .js and .json allowed")
    return path


def _resolve_json_input(args) -> dict:
    """Resolve JSON data from --data, --file, or individual convenience flags."""
    data = {}

    if hasattr(args, 'file') and args.file:
        try:
            with open(args.file) as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in file: {e}", file=sys.stderr)
            sys.exit(1)

    if hasattr(args, 'data') and args.data:
        try:
            data.update(_safe_json_parse(args.data))
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error: Invalid JSON in --data: {e}", file=sys.stderr)
            sys.exit(1)

    if hasattr(args, 'name') and args.name is not None:
        data["name"] = args.name
    if hasattr(args, 'description') and args.description is not None:
        data["description"] = args.description
    if hasattr(args, 'integration') and args.integration is not None:
        data["_integrationId"] = args.integration
    if hasattr(args, 'disabled') and args.disabled is not None:
        data["disabled"] = args.disabled
    if hasattr(args, 'schedule') and args.schedule is not None:
        data["schedule"] = args.schedule
    if hasattr(args, 'timezone') and args.timezone is not None:
        data["timezone"] = args.timezone
    if hasattr(args, 'email') and args.email is not None:
        data["email"] = args.email
    if hasattr(args, 'role') and args.role is not None:
        data["accessLevel"] = args.role
    if hasattr(args, 'key') and args.key is not None:
        data["key"] = args.key

    return data


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

    elif args.action == "create":
        data = _resolve_json_input(args)
        if not data.get("name"):
            print("Error: Flow name is required. Use --name or include 'name' in --data/--file",
                  file=sys.stderr)
            sys.exit(1)
        result = api.create(data)
        print_result(result, args.format)

    elif args.action == "update":
        updates = _resolve_json_input(args)
        if not updates:
            print("Error: No update data provided. Use --name, --disabled, --data, or --file",
                  file=sys.stderr)
            sys.exit(1)
        current = api.get(args.id)
        if current.get("error"):
            print_result(current, args.format)
            return
        merged = _merge_updates_for_put(current, updates, FLOW_READONLY_FIELDS)
        result = api.update(args.id, merged)
        print_result(result, args.format)

    elif args.action == "delete":
        result = api.delete(args.id)
        print_result(result, args.format)

    elif args.action == "clone":
        print_result(api.clone(args.id), args.format)

    elif args.action == "patch":
        data = _resolve_json_input(args)
        if not data:
            print("Error: No patch data provided. Use --data with JSON Patch array.", file=sys.stderr)
            sys.exit(1)
        patch_ops = data if isinstance(data, list) else [data]
        print_result(api.patch(args.id, patch_ops), args.format)

    elif args.action == "replace-connection":
        data = _resolve_json_input(args)
        print_result(api.replace_connection(args.id, data), args.format)


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

    elif args.action == "create":
        data = _resolve_json_input(args)
        result = api.create(data)
        print_result(result, args.format)

    elif args.action == "update":
        updates = _resolve_json_input(args)
        if not updates:
            print("Error: No update data provided.", file=sys.stderr)
            sys.exit(1)
        current = api.get(args.id)
        if current.get("error"):
            print_result(current, args.format)
            return
        merged = _merge_updates_for_put(current, updates, CONNECTION_READONLY_FIELDS)
        print_result(api.update(args.id, merged), args.format)

    elif args.action == "delete":
        print_result(api.delete(args.id), args.format)

    elif args.action == "patch":
        data = _resolve_json_input(args)
        if not data:
            print("Error: No patch data provided.", file=sys.stderr)
            sys.exit(1)
        patch_ops = data if isinstance(data, list) else [data]
        print_result(api.patch(args.id, patch_ops), args.format)

    elif args.action == "audit":
        print_result(api.audit(args.id), args.format)

    elif args.action == "oauth2":
        print_result(api.oauth2(args.id), args.format)

    elif args.action == "ping-virtual":
        data = _resolve_json_input(args)
        print_result(api.ping_virtual(data), args.format)

    elif args.action == "virtual-export":
        data = _resolve_json_input(args)
        print_result(api.virtual_export(args.id, data), args.format)

    elif args.action == "virtual-import":
        data = _resolve_json_input(args)
        print_result(api.virtual_import(args.id, data), args.format)


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

    elif args.action == "create":
        data = _resolve_json_input(args)
        result = api.create(data)
        print_result(result, args.format)

    elif args.action == "update":
        updates = _resolve_json_input(args)
        if not updates:
            print("Error: No update data provided. Use --data or --file",
                  file=sys.stderr)
            sys.exit(1)
        current = api.get(args.id)
        if current.get("error"):
            print_result(current, args.format)
            return
        merged = _merge_updates_for_put(current, updates, EXPORT_READONLY_FIELDS)
        result = api.update(args.id, merged)
        print_result(result, args.format)

    elif args.action == "delete":
        result = api.delete(args.id)
        print_result(result, args.format)

    elif args.action == "clone":
        print_result(api.clone(args.id), args.format)

    elif args.action == "invoke":
        data = _resolve_json_input(args) if hasattr(args, 'data') else None
        print_result(api.invoke(args.id, data), args.format)

    elif args.action == "patch":
        data = _resolve_json_input(args)
        if not data:
            print("Error: No patch data provided.", file=sys.stderr)
            sys.exit(1)
        patch_ops = data if isinstance(data, list) else [data]
        print_result(api.patch(args.id, patch_ops), args.format)

    elif args.action == "replace-connection":
        data = _resolve_json_input(args)
        print_result(api.replace_connection(args.id, data), args.format)


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

    elif args.action == "create":
        data = _resolve_json_input(args)
        result = api.create(data)
        print_result(result, args.format)

    elif args.action == "update":
        updates = _resolve_json_input(args)
        if not updates:
            print("Error: No update data provided. Use --data or --file",
                  file=sys.stderr)
            sys.exit(1)
        current = api.get(args.id)
        if current.get("error"):
            print_result(current, args.format)
            return
        merged = _merge_updates_for_put(current, updates, IMPORT_READONLY_FIELDS)
        result = api.update(args.id, merged)
        print_result(result, args.format)

    elif args.action == "delete":
        result = api.delete(args.id)
        print_result(result, args.format)

    elif args.action == "clone":
        print_result(api.clone(args.id), args.format)

    elif args.action == "invoke":
        data = _resolve_json_input(args) if hasattr(args, 'data') else None
        print_result(api.invoke(args.id, data), args.format)

    elif args.action == "patch":
        data = _resolve_json_input(args)
        if not data:
            print("Error: No patch data provided.", file=sys.stderr)
            sys.exit(1)
        patch_ops = data if isinstance(data, list) else [data]
        print_result(api.patch(args.id, patch_ops), args.format)

    elif args.action == "replace-connection":
        data = _resolve_json_input(args)
        print_result(api.replace_connection(args.id, data), args.format)


def cmd_scripts(args):
    """Handle scripts subcommands."""
    client = CeligoClient(args.env)
    api = ScriptsAPI(client)

    if args.action == "list":
        data = api.list()
        columns = ["_id", "name", "function"]
        print_result(data, args.format, columns)

    elif args.action == "get":
        print_result(api.get(args.id), args.format)

    elif args.action == "create":
        data = _resolve_json_input(args)
        # Support convenience flags for common fields
        if not data:
            data = {}
        if getattr(args, "name", None):
            data["name"] = args.name
        if getattr(args, "function_type", None):
            data["function"] = args.function_type
        if getattr(args, "code_file", None):
            try:
                safe_path = _validate_code_file(args.code_file)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
            with open(safe_path, "r") as f:
                data["content"] = f.read()
        result = api.create(data)
        print_result(result, args.format)

    elif args.action == "update":
        updates = _resolve_json_input(args)
        if not updates:
            updates = {}
        # Support convenience flags
        if getattr(args, "name", None):
            updates["name"] = args.name
        if getattr(args, "code_file", None):
            try:
                safe_path = _validate_code_file(args.code_file)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
            with open(safe_path, "r") as f:
                updates["content"] = f.read()
        if not updates:
            print("Error: No update data provided. Use --data, --file, --name, or --code-file",
                  file=sys.stderr)
            sys.exit(1)
        current = api.get(args.id)
        if current.get("error"):
            print_result(current, args.format)
            return
        merged = _merge_updates_for_put(current, updates, SCRIPT_READONLY_FIELDS)
        result = api.update(args.id, merged)
        print_result(result, args.format)

    elif args.action == "delete":
        result = api.delete(args.id)
        print_result(result, args.format)

    elif args.action == "logs":
        print_result(api.logs(args.id), args.format)


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

    elif args.action == "delete-resolved":
        if is_export:
            data = api.delete_resolved_export(args.flow, args.export)
        elif is_import:
            data = api.delete_resolved_import(args.flow, args.import_id)
        else:
            print("Error: Specify --export or --import", file=sys.stderr)
            sys.exit(1)
        print_result(data, args.format)

    elif args.action == "update-retry-data":
        exp_or_imp = args.export or args.import_id
        if not exp_or_imp:
            print("Error: Specify --export or --import", file=sys.stderr)
            sys.exit(1)
        update_data = _resolve_json_input(args)
        data = api.update_retry_data(args.flow, exp_or_imp, args.key, update_data)
        print_result(data, args.format)

    elif args.action == "view-request":
        pp_id = args.export or args.import_id
        if not pp_id:
            print("Error: Specify --export or --import (page processor ID)", file=sys.stderr)
            sys.exit(1)
        data = api.view_request(args.flow, pp_id, args.key)
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

    elif args.action == "delete":
        print_result(api.delete(args.id), args.format)

    elif args.action == "data-update":
        data = _resolve_json_input(args)
        if not data:
            print("Error: No data provided. Use --data or --file with {\"data\": [{\"key\": ..., \"value\": ...}]}",
                  file=sys.stderr)
            sys.exit(1)
        print_result(api.data_update(args.id, data), args.format)

    elif args.action == "data-delete":
        keys = args.keys.split(",")
        print_result(api.data_delete(args.id, keys), args.format)

    elif args.action == "data-purge":
        print_result(api.data_purge(args.id), args.format)


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

    elif args.action == "update":
        updates = _resolve_json_input(args)
        if not updates:
            print("Error: No update data provided.", file=sys.stderr)
            sys.exit(1)
        current = api.get(args.id)
        if current.get("error"):
            print_result(current, args.format)
            return
        merged = _merge_updates_for_put(current, updates, USER_READONLY_FIELDS)
        print_result(api.update(args.id, merged), args.format)

    elif args.action == "delete":
        print_result(api.delete(args.id), args.format)

    elif args.action == "disable":
        print_result(api.disable(args.id), args.format)

    elif args.action == "invite":
        data = _resolve_json_input(args)
        if not data.get("email"):
            print("Error: --email is required for invite.", file=sys.stderr)
            sys.exit(1)
        print_result(api.invite(data), args.format)

    elif args.action == "invite-multiple":
        data = _resolve_json_input(args)
        print_result(api.invite_multiple(data), args.format)

    elif args.action == "reinvite":
        data = _resolve_json_input(args)
        if not data.get("email"):
            print("Error: --email is required for reinvite.", file=sys.stderr)
            sys.exit(1)
        print_result(api.reinvite(data), args.format)

    elif args.action == "sso-update":
        data = _resolve_json_input(args)
        print_result(api.sso_update(args.id, data), args.format)


def cmd_state(args):
    """Handle state API subcommands."""
    client = CeligoClient(args.env)
    api = StateAPI(client)

    if args.action == "list":
        print_result(api.list(), args.format)

    elif args.action == "get":
        print_result(api.get(args.key), args.format)

    elif args.action == "set":
        data = _resolve_json_input(args)
        if not data:
            print("Error: No data provided. Use --data or --file", file=sys.stderr)
            sys.exit(1)
        print_result(api.set(args.key, data), args.format)

    elif args.action == "delete":
        print_result(api.delete(args.key), args.format)

    elif args.action == "list-scoped":
        print_result(api.list_scoped(args.import_id), args.format)

    elif args.action == "get-scoped":
        print_result(api.get_scoped(args.import_id, args.key), args.format)

    elif args.action == "set-scoped":
        data = _resolve_json_input(args)
        if not data:
            print("Error: No data provided. Use --data or --file", file=sys.stderr)
            sys.exit(1)
        print_result(api.set_scoped(args.import_id, args.key, data), args.format)


def cmd_filedefinitions(args):
    """Handle file definitions subcommands."""
    client = CeligoClient(args.env)
    api = FileDefinitionsAPI(client)

    if args.action == "list":
        data = api.list()
        columns = ["_id", "name", "lastModified"]
        print_result(data, args.format, columns)

    elif args.action == "get":
        print_result(api.get(args.id), args.format)

    elif args.action == "create":
        data = _resolve_json_input(args)
        print_result(api.create(data), args.format)

    elif args.action == "update":
        updates = _resolve_json_input(args)
        if not updates:
            print("Error: No update data provided.", file=sys.stderr)
            sys.exit(1)
        current = api.get(args.id)
        if current.get("error"):
            print_result(current, args.format)
            return
        merged = _merge_updates_for_put(current, updates, FILEDEFINITION_READONLY_FIELDS)
        print_result(api.update(args.id, merged), args.format)

    elif args.action == "delete":
        print_result(api.delete(args.id), args.format)


def cmd_recyclebin(args):
    """Handle recycle bin subcommands."""
    client = CeligoClient(args.env)
    api = RecycleBinAPI(client)

    if args.action == "list":
        resource_type = getattr(args, 'resource_type', None)
        data = api.list(resource_type)
        columns = ["_id", "name", "type", "deletedAt"]
        print_result(data, args.format, columns)

    elif args.action == "get":
        print_result(api.get(args.resource_type, args.id), args.format)

    elif args.action == "restore":
        print_result(api.restore(args.resource_type, args.id), args.format)

    elif args.action == "delete":
        print_result(api.delete(args.resource_type, args.id), args.format)


def cmd_audit(args):
    """Handle account audit log subcommands."""
    client = CeligoClient(args.env)
    api = AuditAPI(client)

    if args.action == "list":
        data = api.list(
            resource_type=getattr(args, 'resource_type', None),
            user=getattr(args, 'user', None),
            since=getattr(args, 'since', None),
            until=getattr(args, 'until', None)
        )
        print_result(data, args.format)


def cmd_iclients(args):
    """Handle iClients subcommands."""
    client = CeligoClient(args.env)
    api = IClientsAPI(client)

    if args.action == "list":
        data = api.list()
        columns = ["_id", "name", "lastModified"]
        print_result(data, args.format, columns)

    elif args.action == "get":
        print_result(api.get(args.id), args.format)

    elif args.action == "create":
        data = _resolve_json_input(args)
        print_result(api.create(data), args.format)

    elif args.action == "update":
        updates = _resolve_json_input(args)
        if not updates:
            print("Error: No update data provided.", file=sys.stderr)
            sys.exit(1)
        current = api.get(args.id)
        if current.get("error"):
            print_result(current, args.format)
            return
        merged = _merge_updates_for_put(current, updates, ICLIENT_READONLY_FIELDS)
        print_result(api.update(args.id, merged), args.format)

    elif args.action == "patch":
        data = _resolve_json_input(args)
        if not data:
            print("Error: No patch data provided.", file=sys.stderr)
            sys.exit(1)
        patch_ops = data if isinstance(data, list) else [data]
        print_result(api.patch(args.id, patch_ops), args.format)

    elif args.action == "delete":
        print_result(api.delete(args.id), args.format)

    elif args.action == "dependencies":
        print_result(api.dependencies(args.id), args.format)


def cmd_connectors(args):
    """Handle connectors and licenses subcommands."""
    client = CeligoClient(args.env)
    api = ConnectorsAPI(client)

    if args.action == "list":
        data = api.list()
        columns = ["_id", "name", "lastModified"]
        print_result(data, args.format, columns)

    elif args.action == "get":
        print_result(api.get(args.id), args.format)

    elif args.action == "create":
        data = _resolve_json_input(args)
        print_result(api.create(data), args.format)

    elif args.action == "update":
        updates = _resolve_json_input(args)
        if not updates:
            print("Error: No update data provided.", file=sys.stderr)
            sys.exit(1)
        current = api.get(args.id)
        if current.get("error"):
            print_result(current, args.format)
            return
        merged = _merge_updates_for_put(current, updates, CONNECTOR_READONLY_FIELDS)
        print_result(api.update(args.id, merged), args.format)

    elif args.action == "delete":
        print_result(api.delete(args.id), args.format)

    elif args.action == "install-base":
        print_result(api.install_base(args.id), args.format)

    elif args.action == "publish-update":
        data = _resolve_json_input(args)
        print_result(api.publish_update(args.id, data), args.format)

    elif args.action == "list-licenses":
        data = api.list_licenses(args.id)
        columns = ["_id", "name", "lastModified"]
        print_result(data, args.format, columns)

    elif args.action == "create-license":
        data = _resolve_json_input(args)
        print_result(api.create_license(args.id, data), args.format)

    elif args.action == "get-license":
        print_result(api.get_license(args.id, args.license_id), args.format)

    elif args.action == "update-license":
        data = _resolve_json_input(args)
        print_result(api.update_license(args.id, args.license_id, data), args.format)

    elif args.action == "delete-license":
        print_result(api.delete_license(args.id, args.license_id), args.format)


def cmd_processors(args):
    """Handle processor subcommands."""
    client = CeligoClient(args.env)
    api = ProcessorsAPI(client)

    data = _resolve_json_input(args)
    if not data:
        print("Error: No data provided. Use --data or --file", file=sys.stderr)
        sys.exit(1)

    if args.action == "parse-xml":
        print_result(api.parse_xml(data), args.format)
    elif args.action == "parse-csv":
        print_result(api.parse_csv(data), args.format)
    elif args.action == "generate-csv":
        print_result(api.generate_csv(data), args.format)
    elif args.action == "generate-structured":
        print_result(api.generate_structured(data), args.format)
    elif args.action == "parse-structured":
        print_result(api.parse_structured(data), args.format)


def cmd_templates(args):
    """Handle template subcommands."""
    client = CeligoClient(args.env)
    api = TemplatesAPI(client)

    if args.action == "list":
        data = api.list()
        columns = ["_id", "name", "lastModified"]
        print_result(data, args.format, columns)

    elif args.action == "update":
        data = _resolve_json_input(args)
        if not data:
            print("Error: No update data provided.", file=sys.stderr)
            sys.exit(1)
        print_result(api.update(args.id, data), args.format)


def cmd_edi(args):
    """Handle EDI/B2B subcommands."""
    client = CeligoClient(args.env)
    api = EDIAPI(client)

    if args.action == "list":
        data = api.list()
        columns = ["_id", "name", "lastModified"]
        print_result(data, args.format, columns)

    elif args.action == "get":
        print_result(api.get(args.id), args.format)

    elif args.action == "create":
        data = _resolve_json_input(args)
        print_result(api.create(data), args.format)

    elif args.action == "update":
        updates = _resolve_json_input(args)
        if not updates:
            print("Error: No update data provided.", file=sys.stderr)
            sys.exit(1)
        current = api.get(args.id)
        if current.get("error"):
            print_result(current, args.format)
            return
        merged = _merge_updates_for_put(current, updates, EDIPROFILE_READONLY_FIELDS)
        print_result(api.update(args.id, merged), args.format)

    elif args.action == "patch":
        data = _resolve_json_input(args)
        if not data:
            print("Error: No patch data provided.", file=sys.stderr)
            sys.exit(1)
        patch_ops = data if isinstance(data, list) else [data]
        print_result(api.patch(args.id, patch_ops), args.format)

    elif args.action == "delete":
        print_result(api.delete(args.id), args.format)

    elif args.action == "update-transactions":
        data = _resolve_json_input(args)
        print_result(api.update_transactions(data), args.format)

    elif args.action == "query-transactions":
        data = _resolve_json_input(args)
        print_result(api.query_transactions(data), args.format)

    elif args.action == "fa-details":
        print_result(api.get_fa_details(args.id), args.format)


def cmd_edi_reports(args):
    """EDI-specific reporting and health commands."""
    import re

    client = CeligoClient(args.env)

    _EDI_DOC_TYPES = {
        "850": "Purchase Order (IB)", "855": "PO Acknowledgement (OB)",
        "856": "Advance Ship Notice (OB)", "810": "Invoice (OB)",
        "820": "Payment Order (IB)", "846": "Inventory Advice (OB)",
        "860": "PO Change (IB)", "864": "Text Message (IB)",
        "997": "Functional Acknowledgement", "753": "Routing Request (OB)",
        "754": "Routing Instructions (IB)", "824": "App Advice (IB)",
        "940": "Warehouse Shipping Order", "945": "Warehouse Shipping Advice",
    }

    def parse_edi_name(name):
        staging_match = re.search(r'\((\d{1,2}/\d{1,2}/\d{4})\)\s*$', name)
        is_staging = staging_match is not None
        clean = re.sub(r'\s*\(\d{1,2}/\d{1,2}/\d{4}\)\s*$', '', name).strip()
        network = "direct"
        partner = clean
        if clean.startswith("EDI - VAN - "):
            network, partner = "VAN", clean[len("EDI - VAN - "):]
        elif clean.startswith("EDI - SPS - "):
            network, partner = "SPS", clean[len("EDI - SPS - "):]
        elif clean.startswith("EDI - "):
            partner = clean[len("EDI - "):]
        return partner, network, is_staging, (staging_match.group(1) if staging_match else None)

    def extract_doc_type(flow_name):
        m = re.search(r'\b(8[0-9]{2}|9[0-9]{2}|7[0-9]{2})\b', flow_name)
        return m.group(1) if m else "other"

    def get_edi_integrations(include_staging=False, network_filter=None):
        all_ints = client.get( "/integrations")
        result = []
        for i in all_ints:
            name = i.get("name", "")
            if not (name.startswith("EDI") and any(k in name.upper() for k in ["EDI", "856", "850", "810"])):
                continue
            partner, network, staging, sdate = parse_edi_name(name)
            if not include_staging and staging:
                continue
            if network_filter and network.upper() != network_filter.upper():
                continue
            result.append({**i, "partner": partner, "network": network,
                           "staging": staging, "staging_date": sdate})
        return sorted(result, key=lambda x: x["partner"].lower())

    if args.action == "list":
        include_staging = getattr(args, "include_staging", False)
        network_filter = getattr(args, "network", None)
        edi_ints = get_edi_integrations(include_staging, network_filter)
        rows = [{
            "_id": i["_id"], "partner": i["partner"],
            "network": i["network"], "staging": i["staging"],
            "lastModified": i.get("lastModified", ""),
        } for i in edi_ints]
        print_result(rows, args.format, ["_id", "partner", "network", "staging"])

    elif args.action == "errors":
        include_staging = getattr(args, "include_staging", False)
        edi_ints = get_edi_integrations(include_staging)
        print(f"Fetching errors for {len(edi_ints)} EDI integrations...", file=sys.stderr)
        results = []
        for integ in edi_ints:
            try:
                errors = client.get( f"/integrations/{integ['_id']}/errors") or []
                total = sum(e.get("numError", 0) for e in errors)
                results.append({
                    "partner": integ["partner"],
                    "network": integ["network"],
                    "_integrationId": integ["_id"],
                    "total_errors": total,
                    "flows_with_errors": sum(1 for e in errors if e.get("numError", 0) > 0),
                })
            except Exception as ex:
                results.append({"partner": integ["partner"], "network": integ["network"],
                                "_integrationId": integ["_id"], "total_errors": -1, "error": str(ex)})
        results.sort(key=lambda x: -x.get("total_errors", 0))
        total_errors = sum(r["total_errors"] for r in results if r["total_errors"] >= 0)
        print(f"\nTotal EDI errors: {total_errors} across {sum(1 for r in results if r['total_errors'] > 0)} partners\n")
        print_result(results, args.format, ["partner", "network", "total_errors", "flows_with_errors", "_integrationId"])

    elif args.action == "partner":
        if not getattr(args, "integration_id", None):
            print("Error: --integration-id required", file=sys.stderr)
            sys.exit(1)
        iid = args.integration_id
        integ = client.get( f"/integrations/{iid}")
        all_flows = client.get( "/flows")
        errors = client.get( f"/integrations/{iid}/errors") or []
        error_map = {e["_flowId"]: e.get("numError", 0) for e in errors}

        flows = [f for f in all_flows if f.get("_integrationId") == iid]
        by_doc: dict = {}
        for f in flows:
            doc = extract_doc_type(f["name"])
            label = _EDI_DOC_TYPES.get(doc, f"Doc {doc}")
            if doc not in by_doc:
                by_doc[doc] = {"doc_type": doc, "description": label, "flows": []}
            by_doc[doc]["flows"].append({
                "_id": f["_id"],
                "name": f["name"],
                "enabled": not f.get("disabled", False),
                "lastExecutedAt": f.get("lastExecutedAt", ""),
                "numError": error_map.get(f["_id"], 0),
            })

        name = integ.get("name", "")
        partner, network, staging, _ = parse_edi_name(name)
        report = {
            "_integrationId": iid, "partner": partner, "network": network,
            "total_flows": len(flows),
            "active_flows": sum(1 for f in flows if not f.get("disabled")),
            "total_errors": sum(error_map.values()),
            "by_doc_type": sorted(by_doc.values(), key=lambda x: x["doc_type"]),
        }
        print_result(report, args.format)

    elif args.action == "dashboard":
        edi_ints = get_edi_integrations(include_staging=False)
        all_flows = client.get( "/flows")
        print(f"Fetching errors for {len(edi_ints)} active EDI partners...", file=sys.stderr)

        flow_map: dict = {}
        for f in all_flows:
            iid = f.get("_integrationId", "")
            if iid not in flow_map:
                flow_map[iid] = {"active": 0, "disabled": 0, "doc_types": set()}
            if f.get("disabled"):
                flow_map[iid]["disabled"] += 1
            else:
                flow_map[iid]["active"] += 1
            doc = extract_doc_type(f["name"])
            if doc != "other":
                flow_map[iid]["doc_types"].add(doc)

        rows = []
        for integ in edi_ints:
            iid = integ["_id"]
            try:
                errors = client.get( f"/integrations/{iid}/errors") or []
                total_errors = sum(e.get("numError", 0) for e in errors)
            except Exception:
                total_errors = -1
            fmap = flow_map.get(iid, {"active": 0, "disabled": 0, "doc_types": set()})
            rows.append({
                "partner": integ["partner"],
                "network": integ["network"],
                "active_flows": fmap["active"],
                "errors": total_errors,
                "doc_types": ",".join(sorted(fmap["doc_types"])),
                "_integrationId": iid,
            })

        rows.sort(key=lambda x: (-x["errors"], x["partner"].lower()))
        total_errors = sum(r["errors"] for r in rows if r["errors"] >= 0)
        partners_with_errors = sum(1 for r in rows if r["errors"] > 0)
        print(f"\nEDI Dashboard: {len(rows)} active partners | {total_errors} total errors | {partners_with_errors} partners with errors\n")
        print_result(rows, args.format, ["partner", "network", "active_flows", "errors", "doc_types", "_integrationId"])


def cmd_health_digest(args):
    """Generate a comprehensive health digest from all recent jobs."""
    from datetime import timezone

    client = CeligoClient(args.env)
    now = datetime.now(timezone.utc)
    days = args.days if hasattr(args, 'days') and args.days else 7

    # Fetch all jobs (bypasses Celigo's delta tracking)
    print(f"Fetching all jobs from the last {days} days...", file=sys.stderr)
    all_jobs = client.get("/jobs?pageSize=1000")
    if not isinstance(all_jobs, list):
        print("Error: unexpected response from /v1/jobs", file=sys.stderr)
        sys.exit(1)

    # Filter to time window
    cutoff = (now - timedelta(days=days)).isoformat()
    jobs = [j for j in all_jobs if (j.get('endedAt') or j.get('createdAt', '')) >= cutoff]

    # Accumulate stats (mirrors health_digest_hook.js v4 logic — flow-type jobs only)
    stats = {
        'totalFlowRuns': 0,
        'totalErrors': 0,
        'totalSuccesses': 0,
        'totalOpenErrors': 0,
        'totalResolved': 0,
        'errorsByFlow': {},
        'openErrorsByFlow': {},
        'agingBuckets': {'under24h': 0, 'days1to3': 0, 'days3to7': 0, 'days7to14': 0, 'over14d': 0},
        'earliest': None,
        'latest': None,
    }

    for job in jobs:
        # v4: skip export/import child jobs to avoid double-counting errors
        if job.get('type') != 'flow':
            continue
        stats['totalFlowRuns'] += 1
        stats['totalErrors'] += (job.get('numError') or 0)
        stats['totalSuccesses'] += (job.get('numSuccess') or 0)
        stats['totalOpenErrors'] += (job.get('numOpenError') or 0)
        stats['totalResolved'] += (job.get('numResolved') or 0)

        fid = job.get('_flowId') or 'unknown'

        # Errors by flow
        if fid not in stats['errorsByFlow']:
            stats['errorsByFlow'][fid] = {'errors': 0, 'successes': 0}
        stats['errorsByFlow'][fid]['errors'] += (job.get('numError') or 0)
        stats['errorsByFlow'][fid]['successes'] += (job.get('numSuccess') or 0)

        # Open errors by flow with aging
        open_count = job.get('numOpenError') or 0
        if open_count > 0:
            if fid not in stats['openErrorsByFlow']:
                stats['openErrorsByFlow'][fid] = {'open': 0, 'oldest': None, 'newest': None}
            stats['openErrorsByFlow'][fid]['open'] += open_count

            job_time = job.get('endedAt') or job.get('startedAt')
            if job_time:
                if not stats['openErrorsByFlow'][fid]['oldest'] or job_time < stats['openErrorsByFlow'][fid]['oldest']:
                    stats['openErrorsByFlow'][fid]['oldest'] = job_time
                if not stats['openErrorsByFlow'][fid]['newest'] or job_time > stats['openErrorsByFlow'][fid]['newest']:
                    stats['openErrorsByFlow'][fid]['newest'] = job_time

                # Age bucket
                try:
                    job_dt = datetime.fromisoformat(job_time.replace('Z', '+00:00'))
                    age_hours = (now - job_dt).total_seconds() / 3600
                    if age_hours < 24:
                        stats['agingBuckets']['under24h'] += open_count
                    elif age_hours < 72:
                        stats['agingBuckets']['days1to3'] += open_count
                    elif age_hours < 168:
                        stats['agingBuckets']['days3to7'] += open_count
                    elif age_hours < 336:
                        stats['agingBuckets']['days7to14'] += open_count
                    else:
                        stats['agingBuckets']['over14d'] += open_count
                except (ValueError, TypeError):
                    pass

        # Time range
        ended = job.get('endedAt')
        if ended:
            if not stats['earliest'] or ended < stats['earliest']:
                stats['earliest'] = ended
            if not stats['latest'] or ended > stats['latest']:
                stats['latest'] = ended

    # Compute rates
    total = stats['totalErrors'] + stats['totalSuccesses']
    error_rate = f"{(stats['totalErrors'] / total * 100):.1f}%" if total > 0 else "0.0%"
    resolution_rate = f"{(stats['totalResolved'] / stats['totalErrors'] * 100):.1f}%" if stats['totalErrors'] > 0 else "100.0%"

    summary = {
        'totalFlowRuns': stats['totalFlowRuns'],
        'totalErrors': stats['totalErrors'],
        'totalSuccesses': stats['totalSuccesses'],
        'totalOpenErrors': stats['totalOpenErrors'],
        'totalResolved': stats['totalResolved'],
        'errorRate': error_rate,
        'resolutionRate': resolution_rate,
        'errorsByFlow': stats['errorsByFlow'],
        'openErrorsByFlow': stats['openErrorsByFlow'],
        'agingBuckets': stats['agingBuckets'],
        'timeRange': f"{stats['earliest'] or 'N/A'} to {stats['latest'] or 'N/A'}",
        'daysCovered': days,
        'generatedAt': now.isoformat(),
    }

    if args.format == "json":
        print(json.dumps(summary, indent=2))
    else:
        # Human-readable table output
        print(f"Health Digest ({days}-day window)")
        print(f"{'='*50}")
        print(f"Time Range:       {summary['timeRange']}")
        print(f"Total Flow Runs:  {summary['totalFlowRuns']}")
        print(f"Total Errors:     {summary['totalErrors']}")
        print(f"Total Successes:  {summary['totalSuccesses']}")
        print(f"Error Rate:       {summary['errorRate']}")
        print(f"Open Errors:      {summary['totalOpenErrors']}")
        print(f"Resolved:         {summary['totalResolved']}")
        print(f"Resolution Rate:  {summary['resolutionRate']}")
        print()
        print("Aging Buckets:")
        for bucket, count in summary['agingBuckets'].items():
            label = bucket.replace('under', '<').replace('days', '').replace('to', '-').replace('over', '>')
            print(f"  {label:>10}: {count}")
        print()
        if summary['openErrorsByFlow']:
            print("Open Errors by Flow:")
            for fid, info in summary['openErrorsByFlow'].items():
                print(f"  {fid}: {info['open']} open (oldest: {info.get('oldest', 'N/A')})")
        else:
            print("No open errors.")

    # Trigger the Celigo flow (export now fetches full data, no delta tracking)
    if hasattr(args, 'run') and args.run:
        flow_id = getattr(args, 'flow_id', None) or "698b4a31ae386aee54914746"
        flows_api = FlowsAPI(client)
        print("Triggering Celigo flow...", file=sys.stderr)
        run_result = flows_api.run(flow_id)
        if isinstance(run_result, list) and run_result:
            job_id = run_result[0].get("_jobId")
        elif isinstance(run_result, dict):
            job_id = run_result.get("_jobId")
        else:
            job_id = None
        print(f"Flow triggered. Job: {job_id}", file=sys.stderr)


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

    int_create = int_sub.add_parser("create", help="Create an integration")
    int_create.add_argument("--name", help="Integration name")
    int_create.add_argument("--description", help="Description")
    int_create.add_argument("--data", help="Full JSON (inline)")
    int_create.add_argument("--file", help="Path to JSON file")

    int_update = int_sub.add_parser("update", help="Update an integration")
    int_update.add_argument("id", help="Integration ID")
    int_update.add_argument("--name", help="New name")
    int_update.add_argument("--description", help="New description")
    int_update.add_argument("--data", help="Partial JSON (inline)")
    int_update.add_argument("--file", help="Path to JSON file")

    int_delete = int_sub.add_parser("delete", help="Delete an integration")
    int_delete.add_argument("id", help="Integration ID")

    int_regconn = int_sub.add_parser("register-connections", help="Register connections")
    int_regconn.add_argument("id", help="Integration ID")
    int_regconn.add_argument("--data", help="Connection registration JSON")
    int_regconn.add_argument("--file", help="Path to JSON file")

    int_dltpl = int_sub.add_parser("download-template", help="Download as installable template")
    int_dltpl.add_argument("id", help="Integration ID")

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

    flow_create = flow_sub.add_parser("create", help="Create a new flow")
    flow_create.add_argument("--name", help="Flow name (required unless in --data/--file)")
    flow_create.add_argument("--description", help="Flow description")
    flow_create.add_argument("--integration", help="Integration ID (_integrationId)")
    flow_create.add_argument("--disabled", type=lambda x: x.lower() == 'true',
                             help="Set disabled status (true/false)")
    flow_create.add_argument("--schedule", help="Cron schedule expression")
    flow_create.add_argument("--timezone", help="Timezone for schedule")
    flow_create.add_argument("--data", help="Full flow JSON (inline string)")
    flow_create.add_argument("--file", help="Path to JSON file with flow definition")

    flow_update = flow_sub.add_parser("update", help="Update a flow")
    flow_update.add_argument("id", help="Flow ID")
    flow_update.add_argument("--name", help="New flow name")
    flow_update.add_argument("--description", help="New description")
    flow_update.add_argument("--disabled", type=lambda x: x.lower() == 'true',
                             help="Set disabled status (true/false)")
    flow_update.add_argument("--schedule", help="New cron schedule expression")
    flow_update.add_argument("--timezone", help="Timezone for schedule")
    flow_update.add_argument("--data", help="Partial flow JSON (inline string)")
    flow_update.add_argument("--file", help="Path to JSON file with updates")

    flow_delete = flow_sub.add_parser("delete", help="Delete a flow")
    flow_delete.add_argument("id", help="Flow ID")

    flow_clone = flow_sub.add_parser("clone", help="Clone a flow")
    flow_clone.add_argument("id", help="Flow ID")

    flow_patch = flow_sub.add_parser("patch", help="Partial update (JSON Patch)")
    flow_patch.add_argument("id", help="Flow ID")
    flow_patch.add_argument("--data", help='JSON Patch array: [{"op":"replace","path":"/name","value":"new"}]')
    flow_patch.add_argument("--file", help="Path to JSON Patch file")

    flow_replconn = flow_sub.add_parser("replace-connection", help="Replace connection in flow")
    flow_replconn.add_argument("id", help="Flow ID")
    flow_replconn.add_argument("--data", help="Connection replacement JSON")
    flow_replconn.add_argument("--file", help="Path to JSON file")

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

    conn_create = conn_sub.add_parser("create", help="Create a new connection")
    conn_create.add_argument("--data", help="Full connection JSON (inline string)")
    conn_create.add_argument("--file", help="Path to JSON file with connection definition")

    conn_update = conn_sub.add_parser("update", help="Update connection (fetch-merge-PUT)")
    conn_update.add_argument("id", help="Connection ID")
    conn_update.add_argument("--data", help="Partial JSON (inline)")
    conn_update.add_argument("--file", help="Path to JSON file")

    conn_delete = conn_sub.add_parser("delete", help="Delete a connection")
    conn_delete.add_argument("id", help="Connection ID")

    conn_patch = conn_sub.add_parser("patch", help="Partial update (JSON Patch)")
    conn_patch.add_argument("id", help="Connection ID")
    conn_patch.add_argument("--data", help="JSON Patch array")
    conn_patch.add_argument("--file", help="Path to JSON Patch file")

    conn_audit = conn_sub.add_parser("audit", help="Get audit log")
    conn_audit.add_argument("id", help="Connection ID")

    conn_oauth2 = conn_sub.add_parser("oauth2", help="Get OAuth2 token info")
    conn_oauth2.add_argument("id", help="Connection ID")

    conn_pingv = conn_sub.add_parser("ping-virtual", help="Test virtual (unsaved) connection")
    conn_pingv.add_argument("--data", help="Connection definition JSON")
    conn_pingv.add_argument("--file", help="Path to JSON file")

    conn_vexp = conn_sub.add_parser("virtual-export", help="Run virtual export")
    conn_vexp.add_argument("id", help="Connection ID")
    conn_vexp.add_argument("--data", help="Export definition JSON")
    conn_vexp.add_argument("--file", help="Path to JSON file")

    conn_vimp = conn_sub.add_parser("virtual-import", help="Run virtual import")
    conn_vimp.add_argument("id", help="Connection ID")
    conn_vimp.add_argument("--data", help="Import definition JSON")
    conn_vimp.add_argument("--file", help="Path to JSON file")

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

    exp_create = exp_sub.add_parser("create", help="Create a new export")
    exp_create.add_argument("--data", help="Full export JSON (inline string)")
    exp_create.add_argument("--file", help="Path to JSON file with export definition")

    exp_update = exp_sub.add_parser("update", help="Update an export (fetch-merge-PUT)")
    exp_update.add_argument("id", help="Export ID")
    exp_update.add_argument("--data", help="Partial export JSON (inline string)")
    exp_update.add_argument("--file", help="Path to JSON file with updates")

    exp_delete = exp_sub.add_parser("delete", help="Delete an export")
    exp_delete.add_argument("id", help="Export ID")

    exp_clone = exp_sub.add_parser("clone", help="Clone an export")
    exp_clone.add_argument("id", help="Export ID")

    exp_invoke = exp_sub.add_parser("invoke", help="Invoke export (run standalone)")
    exp_invoke.add_argument("id", help="Export ID")
    exp_invoke.add_argument("--data", help="Invoke parameters JSON")
    exp_invoke.add_argument("--file", help="Path to JSON file")

    exp_patch = exp_sub.add_parser("patch", help="Partial update (JSON Patch)")
    exp_patch.add_argument("id", help="Export ID")
    exp_patch.add_argument("--data", help="JSON Patch array")
    exp_patch.add_argument("--file", help="Path to JSON Patch file")

    exp_replconn = exp_sub.add_parser("replace-connection", help="Replace connection")
    exp_replconn.add_argument("id", help="Export ID")
    exp_replconn.add_argument("--data", help="Connection replacement JSON")
    exp_replconn.add_argument("--file", help="Path to JSON file")

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

    imp_create = imp_sub.add_parser("create", help="Create a new import")
    imp_create.add_argument("--data", help="Full import JSON (inline string)")
    imp_create.add_argument("--file", help="Path to JSON file with import definition")

    imp_update = imp_sub.add_parser("update", help="Update an import (fetch-merge-PUT)")
    imp_update.add_argument("id", help="Import ID")
    imp_update.add_argument("--data", help="Partial import JSON (inline string)")
    imp_update.add_argument("--file", help="Path to JSON file with updates")

    imp_delete = imp_sub.add_parser("delete", help="Delete an import")
    imp_delete.add_argument("id", help="Import ID")

    imp_clone = imp_sub.add_parser("clone", help="Clone an import")
    imp_clone.add_argument("id", help="Import ID")

    imp_invoke = imp_sub.add_parser("invoke", help="Invoke import (run standalone)")
    imp_invoke.add_argument("id", help="Import ID")
    imp_invoke.add_argument("--data", help="Invoke parameters JSON")
    imp_invoke.add_argument("--file", help="Path to JSON file")

    imp_patch = imp_sub.add_parser("patch", help="Partial update (JSON Patch)")
    imp_patch.add_argument("id", help="Import ID")
    imp_patch.add_argument("--data", help="JSON Patch array")
    imp_patch.add_argument("--file", help="Path to JSON Patch file")

    imp_replconn = imp_sub.add_parser("replace-connection", help="Replace connection")
    imp_replconn.add_argument("id", help="Import ID")
    imp_replconn.add_argument("--data", help="Connection replacement JSON")
    imp_replconn.add_argument("--file", help="Path to JSON file")

    # --- Scripts ---
    scr_parser = subparsers.add_parser("scripts", help="Script operations")
    scr_sub = scr_parser.add_subparsers(dest="action")

    scr_list = scr_sub.add_parser("list", help="List scripts")

    scr_get = scr_sub.add_parser("get", help="Get script")
    scr_get.add_argument("id", help="Script ID")

    scr_create = scr_sub.add_parser("create", help="Create a new script")
    scr_create.add_argument("--name", help="Script name")
    scr_create.add_argument("--function", dest="function_type",
                            choices=["preSavePage", "preMap", "postMap",
                                     "postSubmit", "postResponseMap", "postAggregate"],
                            help="Hook function type")
    scr_create.add_argument("--code-file", help="Path to JavaScript file with hook code")
    scr_create.add_argument("--data", help="Full script JSON (inline string)")
    scr_create.add_argument("--file", help="Path to JSON file with script definition")

    scr_update = scr_sub.add_parser("update", help="Update a script (fetch-merge-PUT)")
    scr_update.add_argument("id", help="Script ID")
    scr_update.add_argument("--name", help="New script name")
    scr_update.add_argument("--code-file", help="Path to JavaScript file with updated hook code")
    scr_update.add_argument("--data", help="Partial script JSON (inline string)")
    scr_update.add_argument("--file", help="Path to JSON file with updates")

    scr_delete = scr_sub.add_parser("delete", help="Delete a script")
    scr_delete.add_argument("id", help="Script ID")

    scr_logs = scr_sub.add_parser("logs", help="Get script execution logs")
    scr_logs.add_argument("id", help="Script ID")

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

    err_del_resolved = err_sub.add_parser("delete-resolved", help="Delete resolved errors")
    err_del_resolved.add_argument("--flow", required=True, help="Flow ID")
    err_del_resolved.add_argument("--export", help="Export ID")
    err_del_resolved.add_argument("--import", dest="import_id", help="Import ID")

    err_upd_retry = err_sub.add_parser("update-retry-data", help="Update retry data before retrying")
    err_upd_retry.add_argument("--flow", required=True, help="Flow ID")
    err_upd_retry.add_argument("--export", help="Export ID")
    err_upd_retry.add_argument("--import", dest="import_id", help="Import ID")
    err_upd_retry.add_argument("--key", required=True, help="Retry data key")
    err_upd_retry.add_argument("--data", help="Updated record JSON")
    err_upd_retry.add_argument("--file", help="Path to JSON file")

    err_view_req = err_sub.add_parser("view-request", help="View request/response for error")
    err_view_req.add_argument("--flow", required=True, help="Flow ID")
    err_view_req.add_argument("--export", help="Export/page-processor ID")
    err_view_req.add_argument("--import", dest="import_id", help="Import/page-processor ID")
    err_view_req.add_argument("--key", required=True, help="Request key")

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

    cache_delete = cache_sub.add_parser("delete", help="Delete a cache")
    cache_delete.add_argument("id", help="Cache ID")

    cache_data_upd = cache_sub.add_parser("data-update", help="Upsert cache data")
    cache_data_upd.add_argument("id", help="Cache ID")
    cache_data_upd.add_argument("--data", help='JSON: {"data": [{"key": "...", "value": {...}}]}')
    cache_data_upd.add_argument("--file", help="Path to JSON file")

    cache_data_del = cache_sub.add_parser("data-delete", help="Delete specific cache keys")
    cache_data_del.add_argument("id", help="Cache ID")
    cache_data_del.add_argument("--keys", required=True, help="Comma-separated keys to delete")

    cache_data_purge = cache_sub.add_parser("data-purge", help="Delete all cache data")
    cache_data_purge.add_argument("id", help="Cache ID")

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

    user_update = user_sub.add_parser("update", help="Update user permissions")
    user_update.add_argument("id", help="User share ID")
    user_update.add_argument("--role", help="Access level (monitor/manage/administrator)")
    user_update.add_argument("--data", help="Full update JSON")
    user_update.add_argument("--file", help="Path to JSON file")

    user_delete = user_sub.add_parser("delete", help="Remove user")
    user_delete.add_argument("id", help="User share ID")

    user_disable = user_sub.add_parser("disable", help="Disable user access")
    user_disable.add_argument("id", help="User share ID")

    user_invite = user_sub.add_parser("invite", help="Invite a user (POST /invite)")
    user_invite.add_argument("--email", required=True, help="User email")
    user_invite.add_argument("--role", help="Access level (monitor/manage/administrator)")
    user_invite.add_argument("--data", help="Full invite JSON")
    user_invite.add_argument("--file", help="Path to JSON file")

    user_invite_multi = user_sub.add_parser("invite-multiple", help="Invite multiple users")
    user_invite_multi.add_argument("--data", help="Bulk invite JSON")
    user_invite_multi.add_argument("--file", help="Path to JSON file")

    user_reinvite = user_sub.add_parser("reinvite", help="Reinvite a user")
    user_reinvite.add_argument("--email", required=True, help="User email")
    user_reinvite.add_argument("--data", help="Reinvite JSON")
    user_reinvite.add_argument("--file", help="Path to JSON file")

    user_sso = user_sub.add_parser("sso-update", help="Update SSO client (PATCH)")
    user_sso.add_argument("id", help="SSO client ID")
    user_sso.add_argument("--data", help="SSO update JSON")
    user_sso.add_argument("--file", help="Path to JSON file")

    # --- Health Digest ---
    hd_parser = subparsers.add_parser("health-digest", help="Generate health digest")
    hd_sub = hd_parser.add_subparsers(dest="action")

    hd_gen = hd_sub.add_parser("generate", help="Generate full health digest (bypasses delta tracking)")
    hd_gen.add_argument("--days", type=int, default=7, help="Number of days to analyze (default: 7)")
    hd_gen.add_argument("--run", action="store_true",
                         help="Trigger the Celigo AI Agent flow after generating summary")
    hd_gen.add_argument("--flow-id", help="Flow ID (default: AI Test flow)")

    # --- State ---
    state_parser = subparsers.add_parser("state", help="State API operations")
    state_sub = state_parser.add_subparsers(dest="action")

    state_sub.add_parser("list", help="List all state keys")

    state_get = state_sub.add_parser("get", help="Get state value")
    state_get.add_argument("key", help="State key")

    state_set = state_sub.add_parser("set", help="Set state value")
    state_set.add_argument("key", help="State key")
    state_set.add_argument("--data", help="Value JSON (inline)")
    state_set.add_argument("--file", help="Path to JSON file")

    state_del = state_sub.add_parser("delete", help="Delete state key")
    state_del.add_argument("key", help="State key")

    state_list_scoped = state_sub.add_parser("list-scoped", help="List import-scoped state keys")
    state_list_scoped.add_argument("--import", dest="import_id", required=True, help="Import ID")

    state_get_scoped = state_sub.add_parser("get-scoped", help="Get import-scoped state")
    state_get_scoped.add_argument("--import", dest="import_id", required=True, help="Import ID")
    state_get_scoped.add_argument("key", help="State key")

    state_set_scoped = state_sub.add_parser("set-scoped", help="Set import-scoped state")
    state_set_scoped.add_argument("--import", dest="import_id", required=True, help="Import ID")
    state_set_scoped.add_argument("key", help="State key")
    state_set_scoped.add_argument("--data", help="Value JSON (inline)")
    state_set_scoped.add_argument("--file", help="Path to JSON file")

    # --- File Definitions ---
    fd_parser = subparsers.add_parser("filedefinitions", help="File definition operations")
    fd_sub = fd_parser.add_subparsers(dest="action")

    fd_sub.add_parser("list", help="List file definitions")

    fd_get = fd_sub.add_parser("get", help="Get file definition")
    fd_get.add_argument("id", help="File definition ID")

    fd_create = fd_sub.add_parser("create", help="Create file definition")
    fd_create.add_argument("--data", help="Full JSON (inline)")
    fd_create.add_argument("--file", help="Path to JSON file")

    fd_update = fd_sub.add_parser("update", help="Update file definition")
    fd_update.add_argument("id", help="File definition ID")
    fd_update.add_argument("--data", help="Partial JSON (inline)")
    fd_update.add_argument("--file", help="Path to JSON file")

    fd_delete = fd_sub.add_parser("delete", help="Delete file definition")
    fd_delete.add_argument("id", help="File definition ID")

    # --- Recycle Bin ---
    rb_parser = subparsers.add_parser("recyclebin", help="Recycle bin operations")
    rb_sub = rb_parser.add_subparsers(dest="action")

    rb_list = rb_sub.add_parser("list", help="List recycled resources")
    rb_list.add_argument("--resource-type", help="Filter by type (flows/exports/imports/connections/scripts)")

    rb_get = rb_sub.add_parser("get", help="Get recycled resource")
    rb_get.add_argument("resource_type", help="Resource type")
    rb_get.add_argument("id", help="Resource ID")

    rb_restore = rb_sub.add_parser("restore", help="Restore recycled resource")
    rb_restore.add_argument("resource_type", help="Resource type")
    rb_restore.add_argument("id", help="Resource ID")

    rb_delete = rb_sub.add_parser("delete", help="Permanently delete recycled resource")
    rb_delete.add_argument("resource_type", help="Resource type")
    rb_delete.add_argument("id", help="Resource ID")

    # --- Audit ---
    audit_parser = subparsers.add_parser("audit", help="Account audit log")
    audit_sub = audit_parser.add_subparsers(dest="action")

    audit_list = audit_sub.add_parser("list", help="List audit entries")
    audit_list.add_argument("--resource-type", help="Filter by resource type")
    audit_list.add_argument("--user", help="Filter by user")
    audit_list.add_argument("--since", help="Start date (ISO 8601)")
    audit_list.add_argument("--until", help="End date (ISO 8601)")

    # --- iClients ---
    ic_parser = subparsers.add_parser("iclients", help="iClient (OAuth2 app) operations")
    ic_sub = ic_parser.add_subparsers(dest="action")

    ic_sub.add_parser("list", help="List iClients")

    ic_get = ic_sub.add_parser("get", help="Get iClient")
    ic_get.add_argument("id", help="iClient ID")

    ic_create = ic_sub.add_parser("create", help="Create iClient")
    ic_create.add_argument("--data", help="Full JSON (inline)")
    ic_create.add_argument("--file", help="Path to JSON file")

    ic_update = ic_sub.add_parser("update", help="Update iClient")
    ic_update.add_argument("id", help="iClient ID")
    ic_update.add_argument("--data", help="Partial JSON (inline)")
    ic_update.add_argument("--file", help="Path to JSON file")

    ic_patch = ic_sub.add_parser("patch", help="Partial update (JSON Patch)")
    ic_patch.add_argument("id", help="iClient ID")
    ic_patch.add_argument("--data", help="JSON Patch array")
    ic_patch.add_argument("--file", help="Path to JSON Patch file")

    ic_delete = ic_sub.add_parser("delete", help="Delete iClient")
    ic_delete.add_argument("id", help="iClient ID")

    ic_deps = ic_sub.add_parser("dependencies", help="Get iClient dependencies")
    ic_deps.add_argument("id", help="iClient ID")

    # --- Connectors & Licenses ---
    cnr_parser = subparsers.add_parser("connectors", help="Connector and license operations")
    cnr_sub = cnr_parser.add_subparsers(dest="action")

    cnr_sub.add_parser("list", help="List connectors")

    cnr_get = cnr_sub.add_parser("get", help="Get connector")
    cnr_get.add_argument("id", help="Connector ID")

    cnr_create = cnr_sub.add_parser("create", help="Create connector")
    cnr_create.add_argument("--data", help="Full JSON (inline)")
    cnr_create.add_argument("--file", help="Path to JSON file")

    cnr_update = cnr_sub.add_parser("update", help="Update connector")
    cnr_update.add_argument("id", help="Connector ID")
    cnr_update.add_argument("--data", help="Partial JSON (inline)")
    cnr_update.add_argument("--file", help="Path to JSON file")

    cnr_delete = cnr_sub.add_parser("delete", help="Delete connector")
    cnr_delete.add_argument("id", help="Connector ID")

    cnr_ib = cnr_sub.add_parser("install-base", help="Get install base")
    cnr_ib.add_argument("id", help="Connector ID")

    cnr_pub = cnr_sub.add_parser("publish-update", help="Publish connector update")
    cnr_pub.add_argument("id", help="Connector ID")
    cnr_pub.add_argument("--data", help="Update JSON")
    cnr_pub.add_argument("--file", help="Path to JSON file")

    cnr_ll = cnr_sub.add_parser("list-licenses", help="List licenses")
    cnr_ll.add_argument("id", help="Connector ID")

    cnr_cl = cnr_sub.add_parser("create-license", help="Create license")
    cnr_cl.add_argument("id", help="Connector ID")
    cnr_cl.add_argument("--data", help="License JSON")
    cnr_cl.add_argument("--file", help="Path to JSON file")

    cnr_gl = cnr_sub.add_parser("get-license", help="Get license")
    cnr_gl.add_argument("id", help="Connector ID")
    cnr_gl.add_argument("license_id", help="License ID")

    cnr_ul = cnr_sub.add_parser("update-license", help="Update license")
    cnr_ul.add_argument("id", help="Connector ID")
    cnr_ul.add_argument("license_id", help="License ID")
    cnr_ul.add_argument("--data", help="License update JSON")
    cnr_ul.add_argument("--file", help="Path to JSON file")

    cnr_dl = cnr_sub.add_parser("delete-license", help="Delete license")
    cnr_dl.add_argument("id", help="Connector ID")
    cnr_dl.add_argument("license_id", help="License ID")

    # --- Processors ---
    proc_parser = subparsers.add_parser("processors", help="Data processor operations")
    proc_sub = proc_parser.add_subparsers(dest="action")

    proc_px = proc_sub.add_parser("parse-xml", help="Parse XML data")
    proc_px.add_argument("--data", help="XML parser config JSON")
    proc_px.add_argument("--file", help="Path to JSON file")

    proc_pc = proc_sub.add_parser("parse-csv", help="Parse CSV data")
    proc_pc.add_argument("--data", help="CSV parser config JSON")
    proc_pc.add_argument("--file", help="Path to JSON file")

    proc_gc = proc_sub.add_parser("generate-csv", help="Generate CSV data")
    proc_gc.add_argument("--data", help="CSV generator config JSON")
    proc_gc.add_argument("--file", help="Path to JSON file")

    proc_gs = proc_sub.add_parser("generate-structured", help="Generate structured file")
    proc_gs.add_argument("--data", help="Structured file config JSON")
    proc_gs.add_argument("--file", help="Path to JSON file")

    proc_ps = proc_sub.add_parser("parse-structured", help="Parse structured file")
    proc_ps.add_argument("--data", help="Structured file config JSON")
    proc_ps.add_argument("--file", help="Path to JSON file")

    # --- Templates ---
    tpl_parser = subparsers.add_parser("templates", help="Template operations")
    tpl_sub = tpl_parser.add_subparsers(dest="action")

    tpl_sub.add_parser("list", help="List all templates")

    tpl_update = tpl_sub.add_parser("update", help="Update a template")
    tpl_update.add_argument("id", help="Template ID")
    tpl_update.add_argument("--data", help="Template update JSON")
    tpl_update.add_argument("--file", help="Path to JSON file")

    # --- EDI/B2B ---
    # EDI Reports
    edir_parser = subparsers.add_parser("edi-reports", help="EDI trading partner reporting and health")
    edir_sub = edir_parser.add_subparsers(dest="action")

    edir_list = edir_sub.add_parser("list", help="List all EDI trading partner integrations")
    edir_list.add_argument("--include-staging", action="store_true", help="Include dated staging copies")
    edir_list.add_argument("--network", choices=["VAN", "SPS", "direct"], help="Filter by network type")

    edir_err = edir_sub.add_parser("errors", help="Aggregated error counts across all EDI partners")
    edir_err.add_argument("--include-staging", action="store_true", help="Include dated staging copies")

    edir_partner = edir_sub.add_parser("partner", help="Detailed flow view for one trading partner")
    edir_partner.add_argument("--integration-id", required=True, help="Integration _id")

    edir_sub.add_parser("dashboard", help="High-level health dashboard across all active EDI partners")

    edi_parser = subparsers.add_parser("edi", help="EDI/B2B operations")
    edi_sub = edi_parser.add_subparsers(dest="action")

    edi_sub.add_parser("list", help="List EDI profiles")

    edi_get = edi_sub.add_parser("get", help="Get EDI profile")
    edi_get.add_argument("id", help="EDI profile ID")

    edi_create = edi_sub.add_parser("create", help="Create EDI profile")
    edi_create.add_argument("--data", help="Full JSON (inline)")
    edi_create.add_argument("--file", help="Path to JSON file")

    edi_update = edi_sub.add_parser("update", help="Update EDI profile")
    edi_update.add_argument("id", help="EDI profile ID")
    edi_update.add_argument("--data", help="Partial JSON (inline)")
    edi_update.add_argument("--file", help="Path to JSON file")

    edi_patch = edi_sub.add_parser("patch", help="Partial update (JSON Patch)")
    edi_patch.add_argument("id", help="EDI profile ID")
    edi_patch.add_argument("--data", help="JSON Patch array")
    edi_patch.add_argument("--file", help="Path to JSON Patch file")

    edi_delete = edi_sub.add_parser("delete", help="Delete EDI profile")
    edi_delete.add_argument("id", help="EDI profile ID")

    edi_utxn = edi_sub.add_parser("update-transactions", help="Update EDI transactions")
    edi_utxn.add_argument("--data", help="Transaction update JSON")
    edi_utxn.add_argument("--file", help="Path to JSON file")

    edi_qtxn = edi_sub.add_parser("query-transactions", help="Query EDI transactions")
    edi_qtxn.add_argument("--data", help="Query JSON")
    edi_qtxn.add_argument("--file", help="Path to JSON file")

    edi_fa = edi_sub.add_parser("fa-details", help="Get FA details for transaction")
    edi_fa.add_argument("id", help="Transaction ID")

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
        "scripts": cmd_scripts,
        "jobs": cmd_jobs,
        "errors": cmd_errors,
        "caches": cmd_caches,
        "tags": cmd_tags,
        "users": cmd_users,
        "state": cmd_state,
        "filedefinitions": cmd_filedefinitions,
        "recyclebin": cmd_recyclebin,
        "audit": cmd_audit,
        "iclients": cmd_iclients,
        "connectors": cmd_connectors,
        "processors": cmd_processors,
        "templates": cmd_templates,
        "edi": cmd_edi,
        "edi-reports": cmd_edi_reports,
        "health-digest": cmd_health_digest,
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
