"""Variant domain MCP tools — CRUD, bulk create, resync."""
from typing import Optional
from mcp.server.fastmcp import FastMCP
from plytix_client import PlytixClient, fmt, handle_error
from urllib.parse import quote


def register_variant_tools(mcp: FastMCP, client: PlytixClient, read_only: bool = False) -> None:
    """Register all variant tools. Pass read_only=True to skip write tools."""

    @mcp.tool(
        name="plytix_list_variants",
        annotations={"title": "List Product Variants", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_list_variants(
        product_id: str,
        limit: int = 100,
        page: int = 1,
    ) -> str:
        """List variants for a parent product.

        Args:
            product_id: The parent product ID.
            limit: Results per page (max 100). Default 100.
            page: Page number. Default 1.

        Returns:
            JSON with data array of variant objects (id, sku, label, modified).
        """
        try:
            params = {"pagination[limit]": limit, "pagination[page]": page}
            result = await client.get(f"/products/{quote(product_id)}/variants", params)
            return fmt(result, "variants")
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_get_variant",
        annotations={"title": "Get Plytix Variant", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_get_variant(variant_id: str) -> str:
        """Get full variant details by ID.

        Args:
            variant_id: The Plytix variant ID.

        Returns:
            JSON variant object with id, sku, label, attributes, product_id (parent), modified.
        """
        try:
            result = await client.get(f"/variants/{quote(variant_id)}")
            return fmt(result)
        except Exception as e:
            return handle_error(e)

    if not read_only:
        @mcp.tool(
            name="plytix_create_variant",
            annotations={"title": "Create Product Variant", "readOnlyHint": False, "openWorldHint": True}
        )
        async def plytix_create_variant(
            product_id: str,
            sku: str,
            label: Optional[str] = None,
            attributes: Optional[dict] = None,
        ) -> str:
            """Create a new variant under a parent product.

            Args:
                product_id: The parent product ID.
                sku: SKU for the variant (must be unique).
                label: Display name for the variant (optional).
                attributes: Dict of {attribute_label: value} for variant-specific attributes.

            Returns:
                JSON with created variant data including the new ID.
            """
            try:
                data: dict = {"sku": sku}
                if label is not None:
                    data["label"] = label
                if attributes:
                    data["attributes"] = attributes
                result = await client.post(f"/products/{quote(product_id)}/variants", data)
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_update_variant",
            annotations={"title": "Update Product Variant", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": False}
        )
        async def plytix_update_variant(
            variant_id: str,
            sku: Optional[str] = None,
            label: Optional[str] = None,
            attributes: Optional[dict] = None,
        ) -> str:
            """Update a variant's fields (partial update).

            Args:
                variant_id: The Plytix variant ID.
                sku: New SKU (optional).
                label: New display name (optional).
                attributes: Dict of {attribute_label: value} to update. Set to null to clear.

            Returns:
                JSON with updated variant data.
            """
            try:
                data: dict = {}
                if sku is not None:
                    data["sku"] = sku
                if label is not None:
                    data["label"] = label
                if attributes is not None:
                    data["attributes"] = attributes
                if not data:
                    return '{"error": "No fields provided to update."}'
                result = await client.patch(f"/variants/{quote(variant_id)}", data)
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_delete_variant",
            annotations={"title": "Delete Product Variant", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": True}
        )
        async def plytix_delete_variant(variant_id: str) -> str:
            """Delete a variant. This action is irreversible.

            Args:
                variant_id: The Plytix variant ID to delete.

            Returns:
                JSON confirmation of deletion.
            """
            try:
                result = await client.delete(f"/variants/{quote(variant_id)}")
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_bulk_create_variants",
            annotations={"title": "Bulk Create Variants", "readOnlyHint": False, "openWorldHint": True}
        )
        async def plytix_bulk_create_variants(product_id: str, variants: list) -> str:
            """Create multiple variants for a product in a single request.

            Args:
                product_id: The parent product ID.
                variants: List of variant objects, each with 'sku' (required) and optionally
                          'label' and 'attributes' fields.
                          Example: [{"sku": "VAR-001", "label": "Red", "attributes": {"color": "red"}}]

            Returns:
                JSON API response for the bulk creation.
            """
            try:
                result = await client.post(
                    f"/products/{quote(product_id)}/variants/bulk",
                    {"variants": variants},
                )
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_resync_variant_attributes",
            annotations={"title": "Resync Variant Attributes", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": False}
        )
        async def plytix_resync_variant_attributes(product_id: str) -> str:
            """Resync variant attributes with the parent product's attribute configuration.

            Useful after changing the parent product's attributes to ensure variants
            inherit the updated attribute definitions.

            Args:
                product_id: The parent product ID (not a variant ID).

            Returns:
                JSON API response.
            """
            try:
                result = await client.post(f"/products/{quote(product_id)}/variants/resync", {})
                return fmt(result)
            except Exception as e:
                return handle_error(e)
