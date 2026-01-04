#!/usr/bin/env python3
"""
n8n MCP Wrapper

Bridges accounts.yaml configuration to the n8n-mcp server.
Reads credentials from config, sets environment variables, and executes n8n-mcp.

Usage:
    python3 n8n_mcp_wrapper.py
    N8N_ACCOUNT=production python3 n8n_mcp_wrapper.py

Environment Variables:
    N8N_ACCOUNT - Account ID to use (overrides default_account from config)
"""

import os
import sys
from pathlib import Path

# Import from same directory
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from n8n_config import get_api_credentials, get_default_account_id

# Common locations for n8n-mcp binary
N8N_MCP_PATHS = [
    Path.home() / ".local" / "bin" / "n8n-mcp",
    Path.home() / ".local" / "lib" / "node_modules" / ".bin" / "n8n-mcp",
    Path.home() / ".local" / "lib" / "node_modules" / "n8n-mcp" / "dist" / "mcp" / "index.js",
    Path("/usr/local/bin/n8n-mcp"),
    Path("/usr/bin/n8n-mcp"),
]


def find_n8n_mcp() -> Path:
    """Find the n8n-mcp binary."""
    # Check N8N_MCP_PATH environment variable first
    env_path = os.environ.get("N8N_MCP_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    # Check common locations
    for path in N8N_MCP_PATHS:
        if path.exists():
            return path

    # Try to find via 'which'
    import subprocess
    try:
        result = subprocess.run(["which", "n8n-mcp"], capture_output=True, text=True)
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except:
        pass

    return None


def main():
    # Get account from environment or config
    account_id = os.environ.get("N8N_ACCOUNT")

    try:
        # Get credentials from config
        url, api_key = get_api_credentials(account_id)
    except SystemExit as e:
        # Config error - already printed
        sys.exit(1)

    # Set environment variables for n8n-mcp
    os.environ["N8N_API_URL"] = url
    os.environ["N8N_API_KEY"] = api_key

    # Find n8n-mcp binary
    n8n_mcp_path = find_n8n_mcp()

    if not n8n_mcp_path:
        print("Error: n8n-mcp not found.", file=sys.stderr)
        print("Install with: npm install -g n8n-mcp", file=sys.stderr)
        print("Or set N8N_MCP_PATH environment variable.", file=sys.stderr)
        sys.exit(1)

    # Determine how to execute
    if n8n_mcp_path.suffix == ".js":
        # Node.js script
        exec_args = ["node", str(n8n_mcp_path)] + sys.argv[1:]
        os.execvp("node", exec_args)
    else:
        # Binary/symlink
        exec_args = [str(n8n_mcp_path)] + sys.argv[1:]
        os.execv(str(n8n_mcp_path), exec_args)


if __name__ == "__main__":
    main()
