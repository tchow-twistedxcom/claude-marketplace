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
    PLYTIX_READ_ONLY    — Optional. Set to 'true' to register only read tools (~30 tools).
"""

import os
from pathlib import Path
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


SYSTEM_PROMPT = """\
You have access to Plytix PIM tools for managing products, assets, categories, variants,
attributes, relationships, and product families.

## Workflow: Reading Product Data
1. Search products → plytix_search_products (basic fields + requested custom attributes, max 20)
2. Full product details → plytix_get_product (ALL attributes, assets, categories, relationships, product_family_id)
3. Search by custom attribute → plytix_find_products_by_attribute (search cannot filter on custom attributes)
4. Category hierarchy → plytix_get_category_tree (builds tree client-side from flat list)

## Workflow: Exporting Data
1. Bulk product export → plytix_export_products (auto-paginates, returns data inline)
   - Fast path (≤20 custom attrs): uses search API — ~10 products/second
   - Full path (>20 attrs or None for all): uses get_product calls — ~5 products/second
2. CSV output: returned as CSV text (first line = metadata comment, then headers + rows)
3. JSON output: returns metadata JSON + product array
4. For inline selective data: plytix_search_products with specific attributes param

## Workflow: Creating Products
1. Create product → plytix_create_product (do NOT pass family — silently ignored)
2. Assign family → plytix_assign_product_family (REQUIRED separate call)
3. Link assets → plytix_add_product_assets (specify attribute_label for media gallery)
4. Add categories → plytix_add_product_categories

## Critical API Rules
- Text search: use `like` operator (NOT `contains` — does not exist)
- Custom attributes: CANNOT be used as search filters — use plytix_find_products_by_attribute
- Search: max 50 columns, max 20 custom attributes per result
- Date attributes: YYYY-MM-DD format only (not ISO timestamps)
- Dropdown options: simple strings ['US','CA'] only (not {value, label} objects)
- Thumbnail: pass asset_id string — auto-wrapped to {id: asset_id} by the server
- Relationships: directional — link from both sides for bidirectional visibility
- plytix_search_products does NOT return product_family_id — use plytix_get_product
- Ordering with >10,000 results returns 428 — remove ordering or narrow filters
- Attribute groups API: unavailable (upstream Plytix bug, always returns 500)

## Reference Resources
- plytix://references/api-gotchas — Common pitfalls, workarounds, and rate limit info
- plytix://references/api-coverage — Full endpoint coverage map
"""

_DATA_DIR = Path(__file__).parent.parent / "data" / "references"


def main():
    mcp = FastMCP("plytix_mcp", instructions=SYSTEM_PROMPT)
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

    @mcp.resource("plytix://references/api-gotchas")
    def get_api_gotchas() -> str:
        """Common Plytix API pitfalls, workarounds, and rate limit info."""
        path = _DATA_DIR / "api_gotchas.md"
        return path.read_text() if path.exists() else "Reference file not found."

    @mcp.resource("plytix://references/api-coverage")
    def get_api_coverage() -> str:
        """Full Plytix API endpoint coverage map with all supported MCP tools."""
        path = _DATA_DIR / "api_coverage.md"
        return path.read_text() if path.exists() else "Reference file not found."

    mcp.run()


if __name__ == "__main__":
    main()
