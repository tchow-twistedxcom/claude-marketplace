#!/usr/bin/env python3
"""
n8n REST API CLI - Full API Client

A comprehensive command-line interface for n8n REST API operations.
Supports workflows, executions, credentials (read-only), and webhooks.

Usage:
    python3 n8n_api.py <resource> <action> [options]

Examples:
    python3 n8n_api.py workflows list
    python3 n8n_api.py workflows get <id>
    python3 n8n_api.py executions list --status error
    python3 n8n_api.py health
    python3 n8n_api.py webhook <url> --data '{"key": "value"}'
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

# Import config module from same directory
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from n8n_config import get_api_credentials, get_default_account_id

# =============================================================================
# Configuration
# =============================================================================

DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2


# =============================================================================
# HTTP Client
# =============================================================================

class N8nClient:
    """HTTP client for n8n API with retry logic and error handling."""

    def __init__(self, account_id: Optional[str] = None):
        self.api_url, self.api_key = get_api_credentials(account_id)
        self.timeout = DEFAULT_TIMEOUT
        # Remove trailing /api/v1 for base URL if present
        self.base_url = self.api_url.rstrip('/')
        if self.base_url.endswith('/api/v1'):
            self.base_url = self.base_url[:-7]

    def _make_request(self, method: str, endpoint: str, data: dict = None,
                      params: dict = None, timeout: int = None) -> dict:
        """Make HTTP request with retry logic."""
        # Build URL
        url = f"{self.api_url.rstrip('/')}{endpoint}"
        if params:
            params = {k: v for k, v in params.items() if v is not None}
            if params:
                url += "?" + urlencode(params)

        headers = {
            "X-N8N-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        body = json.dumps(data).encode() if data else None
        req_timeout = timeout or self.timeout

        for attempt in range(MAX_RETRIES):
            try:
                req = Request(url, data=body, headers=headers, method=method)
                with urlopen(req, timeout=req_timeout) as response:
                    content = response.read().decode()
                    if not content:
                        return {"success": True}
                    return json.loads(content)
            except HTTPError as e:
                if e.code == 429:  # Rate limited
                    wait = RETRY_BACKOFF_BASE ** attempt * 5
                    print(f"Rate limited. Waiting {wait}s...", file=sys.stderr)
                    time.sleep(wait)
                    continue
                elif e.code == 204:  # No content (successful delete)
                    return {"success": True, "status": 204}
                error_body = ""
                try:
                    error_body = e.read().decode() if e.fp else ""
                except:
                    pass
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

    def post(self, endpoint: str, data: dict = None, timeout: int = None) -> dict:
        return self._make_request("POST", endpoint, data=data, timeout=timeout)

    def put(self, endpoint: str, data: dict = None) -> dict:
        return self._make_request("PUT", endpoint, data=data)

    def patch(self, endpoint: str, data: dict = None) -> dict:
        return self._make_request("PATCH", endpoint, data=data)

    def delete(self, endpoint: str) -> dict:
        return self._make_request("DELETE", endpoint)


# =============================================================================
# Workflows API
# =============================================================================

class WorkflowsAPI:
    """Workflows resource operations."""

    def __init__(self, client: N8nClient):
        self.client = client

    def list(self, active: Optional[bool] = None, tags: Optional[str] = None,
             limit: int = 100, cursor: Optional[str] = None) -> dict:
        """List all workflows."""
        params = {"limit": limit}
        if active is not None:
            params["active"] = str(active).lower()
        if tags:
            params["tags"] = tags
        if cursor:
            params["cursor"] = cursor
        return self.client.get("/workflows", params=params)

    def get(self, workflow_id: str) -> dict:
        """Get workflow by ID."""
        return self.client.get(f"/workflows/{workflow_id}")

    def create(self, workflow_data: dict) -> dict:
        """Create a new workflow."""
        return self.client.post("/workflows", data=workflow_data)

    def update(self, workflow_id: str, workflow_data: dict) -> dict:
        """Update an existing workflow."""
        return self.client.put(f"/workflows/{workflow_id}", data=workflow_data)

    def delete(self, workflow_id: str) -> dict:
        """Delete a workflow."""
        return self.client.delete(f"/workflows/{workflow_id}")

    def activate(self, workflow_id: str) -> dict:
        """Activate a workflow."""
        return self.client.post(f"/workflows/{workflow_id}/activate")

    def deactivate(self, workflow_id: str) -> dict:
        """Deactivate a workflow."""
        return self.client.post(f"/workflows/{workflow_id}/deactivate")

    def add_node(self, workflow_id: str, node_data: dict,
                 connect_to: Optional[str] = None,
                 node_name: Optional[str] = None,
                 node_type: Optional[str] = None,
                 type_version: int = 1,
                 position: Optional[tuple] = None) -> dict:
        """Add a node to an existing workflow.

        Args:
            workflow_id: Target workflow ID
            node_data: Full node JSON (or empty dict if using other params)
            connect_to: Name of node to connect this node's output to
            node_name: Display name for the node
            node_type: n8n node type (e.g., 'n8n-nodes-base.manualTrigger')
            type_version: Node type version (default: 1)
            position: Tuple of (x, y) coordinates
        """
        import uuid

        # Get current workflow
        workflow = self.get(workflow_id)
        if workflow.get("error"):
            return workflow

        nodes = workflow.get("nodes", [])
        connections = workflow.get("connections", {})

        # Build node from params if node_data is minimal
        if node_type and not node_data.get("type"):
            node_data["type"] = node_type
        if node_name and not node_data.get("name"):
            node_data["name"] = node_name
        if not node_data.get("typeVersion"):
            node_data["typeVersion"] = type_version
        if not node_data.get("parameters"):
            node_data["parameters"] = {}

        # Auto-generate ID if missing
        if not node_data.get("id"):
            node_data["id"] = str(uuid.uuid4())

        # Auto-calculate position if missing
        if position:
            node_data["position"] = list(position)
        elif not node_data.get("position"):
            # Find min Y position and place above it
            if nodes:
                min_y = min(n.get("position", [0, 300])[1] for n in nodes)
                avg_x = sum(n.get("position", [240, 0])[0] for n in nodes) // len(nodes)
                node_data["position"] = [avg_x, min_y - 160]
            else:
                node_data["position"] = [240, 300]

        # Add the node
        nodes.append(node_data)
        workflow["nodes"] = nodes

        # Create connection if connect_to specified
        if connect_to:
            source_name = node_data.get("name", f"Node_{len(nodes)}")
            connections[source_name] = {
                "main": [[{"node": connect_to, "type": "main", "index": 0}]]
            }
            workflow["connections"] = connections

        # Update workflow
        return self.update(workflow_id, workflow)


# =============================================================================
# Executions API
# =============================================================================

class ExecutionsAPI:
    """Executions resource operations."""

    def __init__(self, client: N8nClient):
        self.client = client

    def list(self, workflow_id: Optional[str] = None, status: Optional[str] = None,
             limit: int = 20, cursor: Optional[str] = None) -> dict:
        """List executions."""
        params = {"limit": limit}
        if workflow_id:
            params["workflowId"] = workflow_id
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor
        return self.client.get("/executions", params=params)

    def get(self, execution_id: str) -> dict:
        """Get execution by ID."""
        return self.client.get(f"/executions/{execution_id}")

    def delete(self, execution_id: str) -> dict:
        """Delete an execution."""
        return self.client.delete(f"/executions/{execution_id}")


# =============================================================================
# Credentials API
# =============================================================================

class CredentialsAPI:
    """Credentials resource operations."""

    def __init__(self, client: N8nClient):
        self.client = client

    def list(self) -> dict:
        """List all credentials (without sensitive data)."""
        return self.client.get("/credentials")

    def create(self, name: str, cred_type: str, data: dict) -> dict:
        """Create a new credential.

        Args:
            name: Display name for the credential
            cred_type: Credential type (e.g., 'httpHeaderAuth', 'oAuth2Api')
            data: Credential data (varies by type)

        Example:
            api.create(
                name="Webhook Auth Token",
                cred_type="httpHeaderAuth",
                data={"name": "X-Webhook-Token", "value": "secret123"}
            )

        Returns:
            Created credential with id, name, type fields
        """
        payload = {"name": name, "type": cred_type, "data": data}
        return self.client.post("/credentials", data=payload)

    def delete(self, credential_id: str) -> dict:
        """Delete a credential by ID."""
        return self.client.delete(f"/credentials/{credential_id}")

    def get_schema(self, credential_type: str) -> dict:
        """Get the schema for a credential type.

        Args:
            credential_type: Type name (e.g., 'httpHeaderAuth')

        Returns:
            JSON schema describing required fields for this credential type
        """
        return self.client.get(f"/credentials/schema/{credential_type}")


# =============================================================================
# Webhooks
# =============================================================================

def trigger_webhook(url: str, method: str = "POST", data: dict = None,
                    headers: dict = None, timeout: int = 120) -> dict:
    """Trigger a webhook URL."""
    req_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if headers:
        req_headers.update(headers)

    body = json.dumps(data).encode() if data else None

    try:
        req = Request(url, data=body, headers=req_headers, method=method)
        with urlopen(req, timeout=timeout) as response:
            content = response.read().decode()
            status = response.status
            if not content:
                return {"success": True, "status": status}
            try:
                return {"success": True, "status": status, "data": json.loads(content)}
            except json.JSONDecodeError:
                return {"success": True, "status": status, "data": content}
    except HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode() if e.fp else ""
        except:
            pass
        return {
            "error": True,
            "status": e.code,
            "message": e.reason,
            "details": error_body
        }
    except URLError as e:
        return {"error": True, "message": str(e.reason)}
    except Exception as e:
        return {"error": True, "message": str(e)}


# =============================================================================
# Health Check
# =============================================================================

def check_health(account_id: Optional[str] = None) -> dict:
    """Check n8n API health and get version info."""
    try:
        client = N8nClient(account_id)

        # Try to list workflows as a health check
        result = client.get("/workflows", params={"limit": 1})

        if result.get("error"):
            return {
                "healthy": False,
                "error": result.get("message", "Unknown error"),
                "status": result.get("status")
            }

        # Get workflow count
        workflows = client.get("/workflows", params={"limit": 100})
        workflow_list = workflows.get("data", [])
        active_count = sum(1 for w in workflow_list if w.get("active"))

        return {
            "healthy": True,
            "url": client.api_url,
            "workflows": {
                "total": len(workflow_list),
                "active": active_count,
                "inactive": len(workflow_list) - active_count
            }
        }
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e)
        }


# =============================================================================
# Validation Helpers
# =============================================================================

def validate_data_table_node(node: dict) -> List[Dict[str, Any]]:
    """Validate Data Table node configuration.

    Checks for common issues like using table names instead of IDs.

    Args:
        node: Node configuration dict

    Returns:
        List of issue dicts with 'type', 'message', 'fix' keys
    """
    issues = []
    params = node.get("parameters", {})
    table_id = params.get("tableId", {})

    # Check resource locator format when mode is "list"
    if table_id.get("mode") == "list":
        value = table_id.get("value", "")
        # IDs are short alphanumeric strings, names often contain spaces
        if not value:
            issues.append({
                "type": "data_table_id_empty",
                "message": "tableId.value is empty",
                "fix": "Set tableId.value to the internal table ID (e.g., '0vQXXKgjO8WncMK2')"
            })
        elif " " in value or len(value) > 20:
            issues.append({
                "type": "data_table_id_format",
                "message": f"tableId.value '{value}' appears to be a name, not an ID",
                "fix": "Use the internal table ID (find it in the n8n UI URL or via API)"
            })

    return issues


def validate_if_node(node: dict) -> List[Dict[str, Any]]:
    """Validate If node configuration for version compatibility.

    Checks for mismatches between typeVersion and conditions structure.

    Args:
        node: Node configuration dict

    Returns:
        List of issue dicts with 'type', 'message', 'fix' keys
    """
    issues = []
    type_version = node.get("typeVersion", 1)
    params = node.get("parameters", {})
    conditions = params.get("conditions", {})

    if type_version == 1:
        # v1 requires combineOperation at params level
        if "combineOperation" not in params:
            issues.append({
                "type": "if_v1_missing_combine",
                "message": "If node v1 missing 'combineOperation' field",
                "fix": "Add 'combineOperation': 'all' or 'any' to parameters"
            })
        # v1 uses conditions.string format, not conditions.conditions
        if "string" not in conditions and "conditions" in conditions:
            issues.append({
                "type": "if_v1_v2_mismatch",
                "message": "If node typeVersion=1 but conditions use v2 format",
                "fix": "Upgrade typeVersion to 2, or convert to v1 format (conditions.string)"
            })

    elif type_version >= 2:
        # v2 requires combinator inside conditions object
        if "combinator" not in conditions:
            issues.append({
                "type": "if_v2_missing_combinator",
                "message": "If node v2 missing 'combinator' in conditions",
                "fix": "Add 'combinator': 'and' or 'or' to conditions object"
            })
        # v2 uses conditions.conditions, not conditions.string
        if "string" in conditions and "conditions" not in conditions:
            issues.append({
                "type": "if_v2_v1_mismatch",
                "message": "If node typeVersion=2 but conditions use v1 format",
                "fix": "Convert to v2 format with conditions.conditions array"
            })

    return issues


def validate_env_usage(workflow: dict) -> List[Dict[str, Any]]:
    """Check for $env usage that may fail with N8N_BLOCK_ENV_ACCESS_IN_NODE.

    Args:
        workflow: Full workflow dict

    Returns:
        List of warning dicts if $env is used
    """
    issues = []
    workflow_json = json.dumps(workflow)

    if "$env" in workflow_json:
        issues.append({
            "type": "env_var_usage",
            "severity": "warning",
            "message": "Workflow uses $env variables which may be blocked by N8N_BLOCK_ENV_ACCESS_IN_NODE",
            "recommendation": "Consider using n8n credentials store instead for sensitive values"
        })

    return issues


def validate_workflow(workflow: dict) -> Dict[str, Any]:
    """Validate entire workflow for common issues.

    Args:
        workflow: Full workflow dict

    Returns:
        Dict with 'valid' bool and 'issues' list
    """
    all_issues = []

    # Check for $env usage
    all_issues.extend(validate_env_usage(workflow))

    # Check each node
    for node in workflow.get("nodes", []):
        node_type = node.get("type", "")
        node_name = node.get("name", "Unknown")

        # Data Table validation
        if "dataTable" in node_type.lower():
            node_issues = validate_data_table_node(node)
            for issue in node_issues:
                issue["node"] = node_name
            all_issues.extend(node_issues)

        # If node validation
        if node_type == "n8n-nodes-base.if":
            node_issues = validate_if_node(node)
            for issue in node_issues:
                issue["node"] = node_name
            all_issues.extend(node_issues)

    return {
        "valid": len([i for i in all_issues if i.get("severity") != "warning"]) == 0,
        "issues": all_issues
    }


# =============================================================================
# CLI Commands
# =============================================================================

def output_json(data: dict, pretty: bool = True) -> None:
    """Output data as JSON."""
    if pretty:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(json.dumps(data, default=str))


def cmd_workflows(args) -> None:
    """Handle workflows commands."""
    client = N8nClient(args.account)
    api = WorkflowsAPI(client)

    if args.action == "list":
        result = api.list(
            active=args.active,
            tags=args.tags,
            limit=args.limit
        )

        if result.get("error"):
            print(f"Error: {result.get('message')}", file=sys.stderr)
            if result.get("details"):
                print(f"Details: {result.get('details')}", file=sys.stderr)
            sys.exit(1)

        workflows = result.get("data", [])

        if args.json:
            output_json(result)
        else:
            print(f"\nn8n Workflows ({len(workflows)} found)")
            print("=" * 70)
            for wf in workflows:
                status = "Active" if wf.get("active") else "Inactive"
                tags = ", ".join(wf.get("tags", [])) or "none"
                print(f"\n{wf.get('id')} - {wf.get('name')}")
                print(f"  Status: {status}")
                print(f"  Tags: {tags}")
                print(f"  Nodes: {len(wf.get('nodes', []))}")

    elif args.action == "get":
        if not args.id:
            print("Error: workflow ID required", file=sys.stderr)
            sys.exit(1)

        result = api.get(args.id)
        if result.get("error"):
            print(f"Error: {result.get('message')}", file=sys.stderr)
            sys.exit(1)

        output_json(result)

    elif args.action == "create":
        if not args.file:
            print("Error: --file required for create", file=sys.stderr)
            sys.exit(1)

        with open(args.file) as f:
            workflow_data = json.load(f)

        result = api.create(workflow_data)
        if result.get("error"):
            print(f"Error: {result.get('message')}", file=sys.stderr)
            sys.exit(1)

        print(f"Workflow created: {result.get('id')}")
        if args.json:
            output_json(result)

    elif args.action == "update":
        if not args.id:
            print("Error: workflow ID required", file=sys.stderr)
            sys.exit(1)

        if args.file:
            with open(args.file) as f:
                workflow_data = json.load(f)
        elif args.add_node or args.node_type:
            # Parse node data from JSON or build from args
            node_data = json.loads(args.add_node) if args.add_node else {}

            # Parse position if provided
            position = None
            if args.position:
                try:
                    x, y = map(int, args.position.split(","))
                    position = (x, y)
                except ValueError:
                    print("Error: --position must be 'x,y' format", file=sys.stderr)
                    sys.exit(1)

            result = api.add_node(
                args.id,
                node_data,
                connect_to=args.connect_to,
                node_name=args.node_name,
                node_type=args.node_type,
                type_version=args.type_version,
                position=position
            )
            if result.get("error"):
                print(f"Error: {result.get('message')}", file=sys.stderr)
                sys.exit(1)
            print(f"Node added to workflow {args.id}")
            return
        else:
            print("Error: --file, --add-node, or --node-type required for update", file=sys.stderr)
            sys.exit(1)

        result = api.update(args.id, workflow_data)
        if result.get("error"):
            print(f"Error: {result.get('message')}", file=sys.stderr)
            sys.exit(1)

        print(f"Workflow updated: {args.id}")

    elif args.action == "delete":
        if not args.id:
            print("Error: workflow ID required", file=sys.stderr)
            sys.exit(1)

        result = api.delete(args.id)
        if result.get("error"):
            print(f"Error: {result.get('message')}", file=sys.stderr)
            sys.exit(1)

        print(f"Workflow deleted: {args.id}")

    elif args.action == "activate":
        if not args.id:
            print("Error: workflow ID required", file=sys.stderr)
            sys.exit(1)

        result = api.activate(args.id)
        if result.get("error"):
            print(f"Error: {result.get('message')}", file=sys.stderr)
            print("Note: Activation via API may not be supported. Try the n8n UI.", file=sys.stderr)
            sys.exit(1)

        print(f"Workflow activated: {args.id}")

    elif args.action == "deactivate":
        if not args.id:
            print("Error: workflow ID required", file=sys.stderr)
            sys.exit(1)

        result = api.deactivate(args.id)
        if result.get("error"):
            print(f"Error: {result.get('message')}", file=sys.stderr)
            sys.exit(1)

        print(f"Workflow deactivated: {args.id}")


def cmd_executions(args) -> None:
    """Handle executions commands."""
    client = N8nClient(args.account)
    api = ExecutionsAPI(client)

    if args.action == "list":
        result = api.list(
            workflow_id=args.workflow,
            status=args.status,
            limit=args.limit
        )

        if result.get("error"):
            print(f"Error: {result.get('message')}", file=sys.stderr)
            sys.exit(1)

        executions = result.get("data", [])

        if args.json:
            output_json(result)
        else:
            print(f"\nn8n Executions ({len(executions)} found)")
            print("=" * 70)
            for ex in executions:
                status = ex.get("status", "unknown")
                started = ex.get("startedAt", "")[:19] if ex.get("startedAt") else "N/A"
                workflow_name = ex.get("workflowData", {}).get("name", ex.get("workflowId", "Unknown"))

                print(f"\n{ex.get('id')} - {workflow_name}")
                print(f"  Status: {status}")
                print(f"  Started: {started}")
                if ex.get("stoppedAt"):
                    print(f"  Stopped: {ex.get('stoppedAt', '')[:19]}")

    elif args.action == "get":
        if not args.id:
            print("Error: execution ID required", file=sys.stderr)
            sys.exit(1)

        result = api.get(args.id)
        if result.get("error"):
            print(f"Error: {result.get('message')}", file=sys.stderr)
            sys.exit(1)

        output_json(result)

    elif args.action == "delete":
        if not args.id:
            print("Error: execution ID required", file=sys.stderr)
            sys.exit(1)

        result = api.delete(args.id)
        if result.get("error"):
            print(f"Error: {result.get('message')}", file=sys.stderr)
            sys.exit(1)

        print(f"Execution deleted: {args.id}")


def cmd_credentials(args) -> None:
    """Handle credentials commands."""
    client = N8nClient(args.account)
    api = CredentialsAPI(client)

    if args.action == "list":
        result = api.list()

        if result.get("error"):
            print(f"Error: {result.get('message')}", file=sys.stderr)
            sys.exit(1)

        creds = result.get("data", [])

        if args.json:
            output_json(result)
        else:
            print(f"\nn8n Credentials ({len(creds)} found)")
            print("=" * 70)
            for cred in creds:
                print(f"\n{cred.get('id')} - {cred.get('name')}")
                print(f"  Type: {cred.get('type')}")

    elif args.action == "create":
        if not args.name or not args.type:
            print("Error: --name and --type required for create", file=sys.stderr)
            print("Example: credentials create --name 'My Token' --type httpHeaderAuth --data '{\"name\":\"X-Token\",\"value\":\"secret\"}'", file=sys.stderr)
            sys.exit(1)

        data = {}
        if args.data:
            try:
                data = json.loads(args.data)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in --data: {e}", file=sys.stderr)
                sys.exit(1)

        result = api.create(args.name, args.type, data)

        if result.get("error"):
            print(f"Error: {result.get('message')}", file=sys.stderr)
            if result.get("details"):
                print(f"Details: {result.get('details')}", file=sys.stderr)
            sys.exit(1)

        if args.json:
            output_json(result)
        else:
            print(f"Credential created successfully")
            print(f"  ID: {result.get('id')}")
            print(f"  Name: {result.get('name')}")
            print(f"  Type: {result.get('type')}")

    elif args.action == "delete":
        if not args.id:
            print("Error: credential ID required for delete", file=sys.stderr)
            sys.exit(1)

        result = api.delete(args.id)

        if result.get("error"):
            print(f"Error: {result.get('message')}", file=sys.stderr)
            sys.exit(1)

        print(f"Credential deleted: {args.id}")

    elif args.action == "schema":
        if not args.type:
            print("Error: --type required for schema", file=sys.stderr)
            sys.exit(1)

        result = api.get_schema(args.type)

        if result.get("error"):
            print(f"Error: {result.get('message')}", file=sys.stderr)
            sys.exit(1)

        output_json(result)


def cmd_health(args) -> None:
    """Check n8n health."""
    result = check_health(args.account)

    if args.json:
        output_json(result)
    else:
        if result.get("healthy"):
            print("\nn8n Health Check: HEALTHY")
            print("=" * 40)
            print(f"URL: {result.get('url')}")
            wf = result.get("workflows", {})
            print(f"Workflows: {wf.get('total', 0)} total")
            print(f"  Active: {wf.get('active', 0)}")
            print(f"  Inactive: {wf.get('inactive', 0)}")
        else:
            print("\nn8n Health Check: UNHEALTHY")
            print("=" * 40)
            print(f"Error: {result.get('error')}")
            if result.get("status"):
                print(f"Status: {result.get('status')}")
            sys.exit(1)


def cmd_webhook(args) -> None:
    """Trigger a webhook."""
    if not args.url:
        print("Error: webhook URL required", file=sys.stderr)
        sys.exit(1)

    data = None
    if args.data:
        data = json.loads(args.data)
    elif args.file:
        with open(args.file) as f:
            data = json.load(f)

    headers = None
    if args.headers:
        headers = json.loads(args.headers)

    result = trigger_webhook(
        url=args.url,
        method=args.method,
        data=data,
        headers=headers,
        timeout=args.timeout
    )

    if args.json:
        output_json(result)
    else:
        if result.get("success"):
            print(f"\nWebhook triggered successfully")
            print(f"Status: {result.get('status')}")
            if result.get("data"):
                print("\nResponse:")
                if isinstance(result["data"], dict):
                    output_json(result["data"])
                else:
                    print(result["data"])
        else:
            print(f"\nWebhook failed")
            print(f"Error: {result.get('message')}")
            if result.get("status"):
                print(f"Status: {result.get('status')}")
            if result.get("details"):
                print(f"Details: {result.get('details')}")
            sys.exit(1)


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="n8n REST API CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s workflows list                    List all workflows
  %(prog)s workflows list --active           List active workflows only
  %(prog)s workflows get <id>                Get workflow details
  %(prog)s workflows activate <id>           Activate a workflow
  %(prog)s executions list --status error    List failed executions
  %(prog)s credentials list                  List all credentials
  %(prog)s credentials create --name "My Token" --type httpHeaderAuth --data '{"name":"X-Token","value":"secret"}'
  %(prog)s credentials delete <id>           Delete a credential
  %(prog)s credentials schema --type httpHeaderAuth  Get credential schema
  %(prog)s health                            Check n8n health
  %(prog)s webhook <url> --data '{}'         Trigger webhook
"""
    )

    # Global options
    parser.add_argument("--account", "-a", help="Account ID to use")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    subparsers = parser.add_subparsers(dest="resource", help="Resource to operate on")

    # Workflows
    workflows_parser = subparsers.add_parser("workflows", help="Workflow operations")
    workflows_parser.add_argument("action", choices=["list", "get", "create", "update", "delete", "activate", "deactivate"])
    workflows_parser.add_argument("id", nargs="?", help="Workflow ID")
    workflows_parser.add_argument("--active", type=lambda x: x.lower() == "true", help="Filter by active status")
    workflows_parser.add_argument("--tags", help="Filter by tags (comma-separated)")
    workflows_parser.add_argument("--limit", type=int, default=100, help="Max results")
    workflows_parser.add_argument("--file", "-f", help="JSON file for create/update")
    workflows_parser.add_argument("--add-node", help="JSON node data to add (or use --node-type)")
    workflows_parser.add_argument("--node-type", help="Node type (e.g., n8n-nodes-base.manualTrigger)")
    workflows_parser.add_argument("--node-name", help="Display name for the node")
    workflows_parser.add_argument("--connect-to", help="Name of node to connect output to")
    workflows_parser.add_argument("--type-version", type=int, default=1, help="Node type version")
    workflows_parser.add_argument("--position", help="Node position as 'x,y' (e.g., '240,140')")

    # Executions
    executions_parser = subparsers.add_parser("executions", help="Execution operations")
    executions_parser.add_argument("action", choices=["list", "get", "delete"])
    executions_parser.add_argument("id", nargs="?", help="Execution ID")
    executions_parser.add_argument("--workflow", "-w", help="Filter by workflow ID")
    executions_parser.add_argument("--status", "-s", choices=["success", "error", "waiting", "running"])
    executions_parser.add_argument("--limit", type=int, default=20, help="Max results")

    # Credentials
    credentials_parser = subparsers.add_parser("credentials", help="Credentials operations")
    credentials_parser.add_argument("action", choices=["list", "create", "delete", "schema"], default="list", nargs="?")
    credentials_parser.add_argument("id", nargs="?", help="Credential ID (for delete)")
    credentials_parser.add_argument("--name", "-n", help="Credential name (for create)")
    credentials_parser.add_argument("--type", "-t", help="Credential type (e.g., httpHeaderAuth, oAuth2Api)")
    credentials_parser.add_argument("--data", "-d", help="Credential data as JSON (for create)")

    # Health
    health_parser = subparsers.add_parser("health", help="Health check")

    # Webhook
    webhook_parser = subparsers.add_parser("webhook", help="Trigger webhook")
    webhook_parser.add_argument("url", help="Webhook URL")
    webhook_parser.add_argument("--method", "-m", default="POST", choices=["GET", "POST", "PUT", "DELETE"])
    webhook_parser.add_argument("--data", "-d", help="JSON data to send")
    webhook_parser.add_argument("--file", "-f", help="JSON file with data")
    webhook_parser.add_argument("--headers", help="Additional headers as JSON")
    webhook_parser.add_argument("--timeout", "-t", type=int, default=120, help="Timeout in seconds")

    args = parser.parse_args()

    if not args.resource:
        parser.print_help()
        sys.exit(1)

    # Route to appropriate handler
    if args.resource == "workflows":
        cmd_workflows(args)
    elif args.resource == "executions":
        cmd_executions(args)
    elif args.resource == "credentials":
        cmd_credentials(args)
    elif args.resource == "health":
        cmd_health(args)
    elif args.resource == "webhook":
        cmd_webhook(args)


if __name__ == "__main__":
    main()
