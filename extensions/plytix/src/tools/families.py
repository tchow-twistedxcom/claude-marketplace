"""Product family domain MCP tools — CRUD, attribute linking, product assignment."""
from typing import Optional
from mcp.server.fastmcp import FastMCP
from plytix_client import PlytixClient, fmt, handle_error
from urllib.parse import quote


def register_family_tools(mcp: FastMCP, client: PlytixClient, read_only: bool = False) -> None:
    """Register all product family tools. Pass read_only=True to skip write tools."""

    @mcp.tool(
        name="plytix_get_product_family",
        annotations={"title": "Get Product Family", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_get_product_family(family_id: str) -> str:
        """Get product family details by ID.

        Args:
            family_id: The Plytix product family ID.

        Returns:
            JSON family object with id, name, label, description, attributes.
        """
        try:
            result = await client.get(f"/product_families/{quote(family_id)}")
            return fmt(result)
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_search_product_families",
        annotations={"title": "Search Product Families", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_search_product_families(
        filters: Optional[list] = None,
        limit: int = 100,
        page: int = 1,
    ) -> str:
        """Search product families with filters.

        Args:
            filters: List of filter dicts [{field, operator, value}].
                     Example: [{"field": "name", "operator": "like", "value": "Amazon"}]
            limit: Results per page (max 100). Default 100.
            page: Page number. Default 1.

        Returns:
            JSON with data array of matching product families.
        """
        try:
            wrapped = [filters] if filters and isinstance(filters[0], dict) else (filters or [])
            data = {
                "filters": wrapped,
                "pagination": {"page": page, "page_size": limit},
            }
            result = await client.post("/product_families/search", data)
            return fmt(result, "families")
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_get_family_attributes",
        annotations={"title": "Get Family Attributes", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_get_family_attributes(family_id: str) -> str:
        """Get all attributes available to a product family.

        Includes attributes directly assigned to this family, inherited from parent
        families, and system-wide default attributes.

        Args:
            family_id: The product family ID.

        Returns:
            JSON with data array of all attribute objects available to this family.
        """
        try:
            result = await client.get(f"/product_families/{quote(family_id)}/all_attributes")
            return fmt(result, "attributes")
        except Exception as e:
            return handle_error(e)

    if not read_only:
        @mcp.tool(
            name="plytix_create_product_family",
            annotations={"title": "Create Product Family", "readOnlyHint": False, "openWorldHint": True}
        )
        async def plytix_create_product_family(
            name: str,
            label: Optional[str] = None,
            description: Optional[str] = None,
        ) -> str:
            """Create a new product family definition.

            Args:
                name: Display name (e.g., 'Amazon Products', '8 - Amazon').
                label: Internal identifier (slug). Auto-generated from name if not provided.
                description: Optional description.

            Returns:
                JSON with created product family data including the new ID.
            """
            try:
                data: dict = {"name": name}
                if label is not None:
                    data["label"] = label
                if description is not None:
                    data["description"] = description
                result = await client.post("/product_families", data)
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_update_product_family",
            annotations={"title": "Update Product Family", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": False}
        )
        async def plytix_update_product_family(
            family_id: str,
            name: Optional[str] = None,
            description: Optional[str] = None,
        ) -> str:
            """Update an existing product family definition.

            Args:
                family_id: The Plytix product family ID.
                name: New display name (optional).
                description: New description (optional).

            Returns:
                JSON with updated product family data.
            """
            try:
                data: dict = {}
                if name is not None:
                    data["name"] = name
                if description is not None:
                    data["description"] = description
                if not data:
                    return '{"error": "No fields provided to update."}'
                result = await client.patch(f"/product_families/{quote(family_id)}", data)
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_delete_product_family",
            annotations={"title": "Delete Product Family", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": True}
        )
        async def plytix_delete_product_family(family_id: str) -> str:
            """Delete a product family. This action is irreversible.

            Args:
                family_id: The Plytix product family ID to delete.

            Returns:
                JSON confirmation of deletion.
            """
            try:
                result = await client.delete(f"/product_families/{quote(family_id)}")
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_link_family_attributes",
            annotations={"title": "Link Attributes to Family", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": False}
        )
        async def plytix_link_family_attributes(family_id: str, attribute_ids: list) -> str:
            """Link attributes to a product family.

            Linked attributes become available on all products in this family.

            Args:
                family_id: The product family ID.
                attribute_ids: List of attribute IDs to link to this family.

            Returns:
                JSON API response confirming the link.
            """
            try:
                result = await client.post(
                    f"/product_families/{quote(family_id)}/attributes/link",
                    {"attributes": attribute_ids},
                )
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_unlink_family_attributes",
            annotations={"title": "Unlink Attributes from Family", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": True}
        )
        async def plytix_unlink_family_attributes(family_id: str, attribute_ids: list) -> str:
            """Unlink attributes from a product family.

            Removes the attributes from the family schema. Existing attribute values
            on products will be lost.

            Args:
                family_id: The product family ID.
                attribute_ids: List of attribute IDs to unlink from this family.

            Returns:
                JSON API response confirming the unlink.
            """
            try:
                result = await client.post(
                    f"/product_families/{quote(family_id)}/attributes/unlink",
                    {"attributes": attribute_ids},
                )
                return fmt(result)
            except Exception as e:
                return handle_error(e)
