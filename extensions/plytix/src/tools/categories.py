"""Category domain MCP tools — product categories + file/asset categories."""
from typing import Optional
from mcp.server.fastmcp import FastMCP
from plytix_client import PlytixClient, fmt, handle_error
from urllib.parse import quote


def register_category_tools(mcp: FastMCP, client: PlytixClient, read_only: bool = False) -> None:
    """Register all category tools. Pass read_only=True to skip write tools."""

    # =========================================================================
    # Product Categories — Read
    # =========================================================================

    @mcp.tool(
        name="plytix_list_categories",
        annotations={"title": "List Product Categories", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_list_categories(limit: int = 100, page: int = 1) -> str:
        """List product categories with pagination.

        Args:
            limit: Results per page (max 100). Default 100.
            page: Page number. Default 1.

        Returns:
            JSON with data array of categories. Each category has id, name, label,
            n_children, parents_ids (list of ancestor IDs from root to immediate parent).
        """
        try:
            data = {
                "filters": [],
                "pagination": {"page": page, "page_size": limit},
            }
            result = await client.post("/categories/product/search", data)
            return fmt(result, "categories")
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_get_category",
        annotations={"title": "Get Product Category", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_get_category(category_id: str) -> str:
        """Get product category details by ID.

        Args:
            category_id: The Plytix category ID.

        Returns:
            JSON category object with id, name, label, n_children, parents_ids.
        """
        try:
            result = await client.get(f"/categories/{quote(category_id)}")
            return fmt(result)
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_get_category_tree",
        annotations={"title": "Get Category Tree", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_get_category_tree() -> str:
        """Build a hierarchical category tree from all product categories.

        Fetches all categories and arranges them as a tree using the parents_ids field.
        Plytix has no native tree endpoint, so this is constructed client-side.

        Returns:
            JSON array of root categories, each with a 'children' array containing
            nested subcategories. Each node has id, name, label, n_children, children.
        """
        try:
            categories = []
            page = 1
            while True:
                result = await client.post(
                    "/categories/product/search",
                    {"filters": [], "pagination": {"page": page, "page_size": 100}},
                )
                batch = result.get("data", [])
                if not batch:
                    break
                categories.extend(batch)
                if len(batch) < 100:
                    break
                page += 1

            # Build lookup and tree
            cat_by_id = {c["id"]: {**c, "children": []} for c in categories}
            roots = []
            for cat in categories:
                node = cat_by_id[cat["id"]]
                parents = cat.get("parents_ids", [])
                if not parents:
                    roots.append(node)
                else:
                    parent_id = parents[-1]
                    if parent_id in cat_by_id:
                        cat_by_id[parent_id]["children"].append(node)
                    else:
                        roots.append(node)

            return fmt({"data": roots})
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_list_category_products",
        annotations={"title": "List Products in Category", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_list_category_products(
        category_id: str,
        limit: int = 100,
        page: int = 1,
    ) -> str:
        """List products assigned to a specific category.

        Args:
            category_id: The Plytix category ID.
            limit: Results per page (max 100). Default 100.
            page: Page number. Default 1.

        Returns:
            JSON with data array of basic product objects in this category.
        """
        try:
            params = {"pagination[limit]": limit, "pagination[page]": page}
            result = await client.get(f"/categories/{quote(category_id)}/products", params)
            return fmt(result, "products")
        except Exception as e:
            return handle_error(e)

    if not read_only:
        @mcp.tool(
            name="plytix_create_category",
            annotations={"title": "Create Product Category", "readOnlyHint": False, "openWorldHint": True}
        )
        async def plytix_create_category(
            name: str,
            label: Optional[str] = None,
            description: Optional[str] = None,
        ) -> str:
            """Create a new top-level product category.

            Args:
                name: Display name for the category.
                label: Internal identifier (slug). Auto-generated from name if not provided.
                description: Optional category description.

            Returns:
                JSON with created category data including the new ID.

            Note:
                To create a subcategory, use plytix_add_product_subcategory instead.
            """
            try:
                data: dict = {"name": name}
                if label is not None:
                    data["label"] = label
                if description is not None:
                    data["description"] = description
                result = await client.post("/categories", data)
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_update_category",
            annotations={"title": "Update Product Category", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": False}
        )
        async def plytix_update_category(
            category_id: str,
            name: Optional[str] = None,
            description: Optional[str] = None,
        ) -> str:
            """Update an existing product category.

            Args:
                category_id: The Plytix category ID.
                name: New display name (optional).
                description: New description (optional).

            Returns:
                JSON with updated category data.
            """
            try:
                data: dict = {}
                if name is not None:
                    data["name"] = name
                if description is not None:
                    data["description"] = description
                if not data:
                    return '{"error": "No fields provided to update."}'
                result = await client.patch(f"/categories/{quote(category_id)}", data)
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_delete_category",
            annotations={"title": "Delete Product Category", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": True}
        )
        async def plytix_delete_category(category_id: str) -> str:
            """Delete a product category. This action is irreversible.

            Args:
                category_id: The Plytix category ID to delete.

            Returns:
                JSON confirmation of deletion.
            """
            try:
                result = await client.delete(f"/categories/{quote(category_id)}")
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_add_product_subcategory",
            annotations={"title": "Add Product Subcategory", "readOnlyHint": False, "openWorldHint": True}
        )
        async def plytix_add_product_subcategory(
            parent_id: str,
            name: str,
            label: Optional[str] = None,
            description: Optional[str] = None,
        ) -> str:
            """Add a subcategory under an existing product category.

            Args:
                parent_id: The parent category ID.
                name: Display name for the subcategory.
                label: Internal identifier (slug). Auto-generated from name if not provided.
                description: Optional subcategory description.

            Returns:
                JSON with created subcategory data including the new ID.
            """
            try:
                data: dict = {"name": name}
                if label is not None:
                    data["label"] = label
                if description is not None:
                    data["description"] = description
                result = await client.post(f"/categories/product/{quote(parent_id)}", data)
                return fmt(result)
            except Exception as e:
                return handle_error(e)

    # =========================================================================
    # File / Asset Categories
    # =========================================================================

    @mcp.tool(
        name="plytix_search_file_categories",
        annotations={"title": "Search File Categories", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_search_file_categories(
        filters: Optional[list] = None,
        limit: int = 100,
        page: int = 1,
    ) -> str:
        """Search file/asset categories with filters.

        Args:
            filters: List of filter dicts [{field, operator, value}].
            limit: Results per page (max 100). Default 100.
            page: Page number. Default 1.

        Returns:
            JSON with data array of matching file categories.
        """
        try:
            wrapped = [filters] if filters and isinstance(filters[0], dict) else (filters or [])
            data = {
                "filters": wrapped,
                "pagination": {"page": page, "page_size": limit},
            }
            result = await client.post("/categories/file/search", data)
            return fmt(result, "file_categories")
        except Exception as e:
            return handle_error(e)

    if not read_only:
        @mcp.tool(
            name="plytix_create_file_category",
            annotations={"title": "Create File Category", "readOnlyHint": False, "openWorldHint": True}
        )
        async def plytix_create_file_category(
            name: str,
            label: Optional[str] = None,
            description: Optional[str] = None,
        ) -> str:
            """Create a new top-level file/asset category.

            Args:
                name: Display name for the file category.
                label: Internal identifier (slug). Auto-generated if not provided.
                description: Optional description.

            Returns:
                JSON with created file category data including the new ID.
            """
            try:
                data: dict = {"name": name}
                if label is not None:
                    data["label"] = label
                if description is not None:
                    data["description"] = description
                result = await client.post("/categories/file", data)
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_add_file_subcategory",
            annotations={"title": "Add File Subcategory", "readOnlyHint": False, "openWorldHint": True}
        )
        async def plytix_add_file_subcategory(
            parent_id: str,
            name: str,
            label: Optional[str] = None,
            description: Optional[str] = None,
        ) -> str:
            """Add a subcategory under an existing file/asset category.

            Args:
                parent_id: The parent file category ID.
                name: Display name for the subcategory.
                label: Internal identifier (slug). Auto-generated if not provided.
                description: Optional description.

            Returns:
                JSON with created subcategory data.
            """
            try:
                data: dict = {"name": name}
                if label is not None:
                    data["label"] = label
                if description is not None:
                    data["description"] = description
                result = await client.post(f"/categories/file/{quote(parent_id)}", data)
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_update_file_category",
            annotations={"title": "Update File Category", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": False}
        )
        async def plytix_update_file_category(
            category_id: str,
            name: Optional[str] = None,
            description: Optional[str] = None,
        ) -> str:
            """Update an existing file/asset category.

            Args:
                category_id: The file category ID.
                name: New display name (optional).
                description: New description (optional).

            Returns:
                JSON with updated file category data.
            """
            try:
                data: dict = {}
                if name is not None:
                    data["name"] = name
                if description is not None:
                    data["description"] = description
                if not data:
                    return '{"error": "No fields provided to update."}'
                result = await client.patch(f"/categories/file/{quote(category_id)}", data)
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_delete_file_category",
            annotations={"title": "Delete File Category", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": True}
        )
        async def plytix_delete_file_category(category_id: str) -> str:
            """Delete a file/asset category. This action is irreversible.

            Args:
                category_id: The file category ID to delete.

            Returns:
                JSON confirmation of deletion.
            """
            try:
                result = await client.delete(f"/categories/file/{quote(category_id)}")
                return fmt(result)
            except Exception as e:
                return handle_error(e)
