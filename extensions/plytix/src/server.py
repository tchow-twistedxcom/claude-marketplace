#!/usr/bin/env python3
"""
Plytix PIM MCP Server

FastMCP server for Plytix PIM API v1 operations.
Credentials are read from environment variables set by Claude Desktop.
Falls back to config file for Claude Code compatibility.

Environment variables:
    PLYTIX_API_KEY      — Required. Plytix API key.
    PLYTIX_API_PASSWORD — Required. Plytix API password.
    PLYTIX_API_URL      — Optional. Default: https://pim.plytix.com/api/v1
    PLYTIX_AUTH_URL     — Optional. Default: https://auth.plytix.com/auth/api/get-token
    PLYTIX_READ_ONLY    — Optional. Set to 'true' to register only read tools (~40 tools).
"""

import os
import sys
from mcp.server.fastmcp import FastMCP

from plytix_client import PlytixClient
from tools.products import register_product_tools
from tools.assets import register_asset_tools
from tools.categories import register_category_tools
from tools.variants import register_variant_tools
from tools.attributes import register_attribute_tools
from tools.relationships import register_relationship_tools
from tools.families import register_family_tools
from tools.accounts import register_account_tools
from tools.filters import register_filter_tools


def main():
    mcp = FastMCP("plytix_mcp")
    client = PlytixClient()
    read_only = os.environ.get("PLYTIX_READ_ONLY", "false").lower() in ("true", "1", "yes")

    register_product_tools(mcp, client, read_only=read_only)
    register_asset_tools(mcp, client, read_only=read_only)
    register_category_tools(mcp, client, read_only=read_only)
    register_variant_tools(mcp, client, read_only=read_only)
    register_attribute_tools(mcp, client, read_only=read_only)
    register_relationship_tools(mcp, client, read_only=read_only)
    register_family_tools(mcp, client, read_only=read_only)
    register_account_tools(mcp, client, read_only=read_only)
    register_filter_tools(mcp, client, read_only=read_only)

    mcp.run()


if __name__ == "__main__":
    main()
