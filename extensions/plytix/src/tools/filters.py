"""Filter discovery tools — list available filter fields for search endpoints."""
from mcp.server.fastmcp import FastMCP
from plytix_client import PlytixClient, fmt, handle_error


def register_filter_tools(mcp: FastMCP, client: PlytixClient, read_only: bool = False) -> None:
    """Register filter discovery tools. Always read-only."""

    @mcp.tool(
        name="plytix_get_product_filters",
        annotations={"title": "Get Product Filter Fields", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_get_product_filters() -> str:
        """Get available filter fields for product search.

        Returns the list of fields that can be used in plytix_search_products filters.

        Note:
            Custom attributes cannot be used as product search filters — only system
            fields returned by this endpoint are valid filter fields.
            Use plytix_find_products_by_attribute for custom attribute filtering.

        Returns:
            JSON array of filter field definitions with field name, operators, and type.
        """
        try:
            result = await client.get("/filters/product")
            return fmt(result)
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_get_asset_filters",
        annotations={"title": "Get Asset Filter Fields", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_get_asset_filters() -> str:
        """Get available filter fields for asset search.

        Returns the list of fields that can be used in plytix_search_assets filters.

        Returns:
            JSON array of filter field definitions with field name, operators, and type.
        """
        try:
            result = await client.get("/filters/asset")
            return fmt(result)
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_get_relationship_filters",
        annotations={"title": "Get Relationship Filter Fields", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_get_relationship_filters() -> str:
        """Get available filter fields for relationship type search.

        Returns the list of fields that can be used in plytix_search_relationships filters.

        Returns:
            JSON array of filter field definitions with field name, operators, and type.
        """
        try:
            result = await client.get("/filters/relationships")
            return fmt(result)
        except Exception as e:
            return handle_error(e)
