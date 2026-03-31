"""Attribute domain MCP tools — product attributes + attribute groups."""
from typing import Optional
from mcp.server.fastmcp import FastMCP
from plytix_client import PlytixClient, fmt, handle_error
from urllib.parse import quote


def register_attribute_tools(mcp: FastMCP, client: PlytixClient, read_only: bool = False) -> None:
    """Register all attribute tools. Pass read_only=True to skip write tools."""

    @mcp.tool(
        name="plytix_list_attributes",
        annotations={"title": "List Product Attributes", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_list_attributes(limit: int = 100, page: int = 1) -> str:
        """List product attributes with pagination.

        Args:
            limit: Results per page (max 100). Default 100.
            page: Page number. Default 1.

        Returns:
            JSON with data array of attributes. Each attribute has id, label, name,
            type_class, mandatory, modified.

        Note:
            Returns attribute metadata, not product values. The 'label' is the snake_case
            identifier used in product attributes dicts. The 'name' is the human-readable label.
        """
        try:
            data = {
                "filters": [],
                "pagination": {"page": page, "page_size": limit},
            }
            result = await client.post("/attributes/product/search", data)
            return fmt(result, "attributes")
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_get_attribute",
        annotations={"title": "Get Product Attribute", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_get_attribute(attribute_id: str) -> str:
        """Get full attribute metadata by ID.

        Args:
            attribute_id: The Plytix attribute ID.

        Returns:
            JSON attribute object with id, label, name, type_class, mandatory,
            options (for dropdown/multiselect), description, modified.
        """
        try:
            result = await client.get(f"/attributes/product/{quote(attribute_id)}")
            return fmt(result)
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_list_attribute_groups",
        annotations={"title": "List Attribute Groups", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_list_attribute_groups(limit: int = 100, page: int = 1) -> str:
        """List attribute groups with pagination.

        IMPORTANT: The Plytix attribute groups API (/attributes/product/groups) is known
        to return 500 Internal Server Error. This is a confirmed upstream bug in the
        Plytix API — not a client issue. Individual attribute operations work fine.

        Args:
            limit: Results per page (max 100). Default 100.
            page: Page number. Default 1.

        Returns:
            JSON with attribute group data, or 500 error if Plytix's API is broken.
        """
        try:
            data = {
                "filters": [],
                "pagination": {"page": page, "page_size": limit},
            }
            result = await client.post("/attributes/product/groups/search", data)
            return fmt(result, "attr_groups")
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_get_attribute_group",
        annotations={"title": "Get Attribute Group", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_get_attribute_group(group_id: str) -> str:
        """Get attribute group details by ID.

        IMPORTANT: The Plytix attribute groups API may return 500 Internal Server Error
        (known upstream bug). Individual attribute endpoints work normally.

        Args:
            group_id: The attribute group ID.

        Returns:
            JSON attribute group object, or 500 error from Plytix's API.
        """
        try:
            result = await client.get(f"/attributes/product/groups/{quote(group_id)}")
            return fmt(result)
        except Exception as e:
            return handle_error(e)

    if not read_only:
        @mcp.tool(
            name="plytix_create_attribute",
            annotations={"title": "Create Product Attribute", "readOnlyHint": False, "openWorldHint": True}
        )
        async def plytix_create_attribute(
            name: str,
            type_class: str,
            label: Optional[str] = None,
            description: Optional[str] = None,
            options: Optional[list] = None,
            groups: Optional[list] = None,
        ) -> str:
            """Create a new product attribute.

            Args:
                name: Human-readable display name (e.g., 'Head Material').
                type_class: Attribute type. Valid values:
                            TextAttribute, HtmlAttribute, BooleanAttribute,
                            NumberAttribute, DateAttribute, DropdownAttribute,
                            MultiSelectAttribute, MediaGalleryAttribute.
                label: Internal snake_case identifier (auto-generated from name if not provided).
                       This is what you use in product attributes dicts.
                description: Optional description.
                options: Required for DropdownAttribute / MultiSelectAttribute.
                         Must be simple strings: ['US', 'CA', 'MX'] — NOT objects.
                groups: Optional list of attribute group IDs to assign this attribute to.

            Returns:
                JSON with created attribute data including the new ID and label.

            Notes:
                - DateAttribute values must be 'YYYY-MM-DD' format (not ISO timestamps).
                - DropdownAttribute options must be simple strings, not {value, label} objects.
                - MediaGalleryAttribute is used for product image galleries.
            """
            try:
                data: dict = {"name": name, "type_class": type_class}
                if label is not None:
                    data["label"] = label
                if description is not None:
                    data["description"] = description
                if options is not None:
                    data["options"] = options
                if groups is not None:
                    data["groups"] = groups
                result = await client.post("/attributes/product", data)
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_update_attribute",
            annotations={"title": "Update Product Attribute", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": False}
        )
        async def plytix_update_attribute(
            attribute_id: str,
            name: Optional[str] = None,
            description: Optional[str] = None,
            options: Optional[list] = None,
        ) -> str:
            """Update an existing product attribute.

            Args:
                attribute_id: The Plytix attribute ID.
                name: New human-readable display name (optional).
                description: New description (optional).
                options: New options list for DropdownAttribute / MultiSelectAttribute.
                         Must be simple strings.

            Returns:
                JSON with updated attribute data.
            """
            try:
                data: dict = {}
                if name is not None:
                    data["name"] = name
                if description is not None:
                    data["description"] = description
                if options is not None:
                    data["options"] = options
                if not data:
                    return '{"error": "No fields provided to update."}'
                result = await client.patch(f"/attributes/product/{quote(attribute_id)}", data)
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_delete_attribute",
            annotations={"title": "Delete Product Attribute", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": True}
        )
        async def plytix_delete_attribute(attribute_id: str) -> str:
            """Delete a product attribute. This action is irreversible and removes
            this attribute from all products.

            Args:
                attribute_id: The Plytix attribute ID to delete.

            Returns:
                JSON confirmation of deletion.
            """
            try:
                result = await client.delete(f"/attributes/product/{quote(attribute_id)}")
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_create_attribute_group",
            annotations={"title": "Create Attribute Group", "readOnlyHint": False, "openWorldHint": True}
        )
        async def plytix_create_attribute_group(
            name: str,
            label: Optional[str] = None,
            attributes: Optional[list] = None,
        ) -> str:
            """Create a new attribute group.

            IMPORTANT: The Plytix attribute groups API may return 500 Internal Server Error
            (known upstream bug). This tool is implemented but may not work until Plytix fixes it.

            Args:
                name: Display name for the group.
                label: Internal identifier (auto-generated if not provided).
                attributes: Optional list of attribute IDs to include in this group.

            Returns:
                JSON with created group data, or 500 error from Plytix's API.
            """
            try:
                data: dict = {"name": name}
                if label is not None:
                    data["label"] = label
                if attributes is not None:
                    data["attributes"] = attributes
                result = await client.post("/attributes/product/groups", data)
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_update_attribute_group",
            annotations={"title": "Update Attribute Group", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": False}
        )
        async def plytix_update_attribute_group(
            group_id: str,
            name: Optional[str] = None,
            attributes: Optional[list] = None,
        ) -> str:
            """Update an existing attribute group.

            IMPORTANT: The Plytix attribute groups API may return 500 Internal Server Error
            (known upstream bug).

            Args:
                group_id: The attribute group ID.
                name: New display name (optional).
                attributes: New list of attribute IDs (optional).

            Returns:
                JSON with updated group data, or 500 error from Plytix's API.
            """
            try:
                data: dict = {}
                if name is not None:
                    data["name"] = name
                if attributes is not None:
                    data["attributes"] = attributes
                if not data:
                    return '{"error": "No fields provided to update."}'
                result = await client.patch(f"/attributes/product/groups/{quote(group_id)}", data)
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_delete_attribute_group",
            annotations={"title": "Delete Attribute Group", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": True}
        )
        async def plytix_delete_attribute_group(group_id: str) -> str:
            """Delete an attribute group.

            IMPORTANT: The Plytix attribute groups API may return 500 Internal Server Error
            (known upstream bug).

            Args:
                group_id: The attribute group ID to delete.

            Returns:
                JSON confirmation of deletion, or 500 error from Plytix's API.
            """
            try:
                result = await client.delete(f"/attributes/product/groups/{quote(group_id)}")
                return fmt(result)
            except Exception as e:
                return handle_error(e)
