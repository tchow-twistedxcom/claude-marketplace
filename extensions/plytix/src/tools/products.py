"""Product domain MCP tools — CRUD, search, bulk, assets/categories/relationships."""
from typing import Optional
from mcp.server.fastmcp import FastMCP
from plytix_client import PlytixClient, fmt, handle_error
from urllib.parse import quote


def register_product_tools(mcp: FastMCP, client: PlytixClient, read_only: bool = False) -> None:
    """Register all product tools. Pass read_only=True to skip write tools."""

    @mcp.tool(
        name="plytix_get_product",
        annotations={"title": "Get Plytix Product", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_get_product(product_id: str) -> str:
        """Get full product details by ID including all attributes, assets, and categories.

        Args:
            product_id: The Plytix product ID (24-character hex string).

        Returns:
            JSON product object with id, sku, label, status, attributes (dict of all custom
            attributes), assets (list), categories (list), relationships (list),
            product_family_id, gtin, created, modified.

        Note:
            product_family_id is ONLY returned by this endpoint — search results always show it as null.
            To check which family a product belongs to, always use plytix_get_product.
            Assets, categories, and relationships are all included in this response —
            no need to call separate sub-tools.
        """
        try:
            result = await client.get(f"/products/{quote(product_id)}")
            # Unwrap: {"data": [product]} → product dict
            if result and "data" in result and result["data"]:
                return fmt(result["data"][0])
            return fmt(result)
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_search_products",
        annotations={"title": "Search Plytix Products", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_search_products(
        filters: Optional[list] = None,
        attributes: Optional[list] = None,
        limit: int = 100,
        page: int = 1,
    ) -> str:
        """Search products with filters and optional attribute selection.

        Args:
            filters: List of filter dicts [{field, operator, value}].
                     Operators: like, !like, eq, !eq, in, !in, gt, gte, lt, lte, exists, !exists.
                     Use 'like' for text search (NOT 'contains' — that operator doesn't exist).
                     Custom attributes CANNOT be used as filter fields (use plytix_find_products_by_attribute).
                     Prefix custom attributes with 'attributes.' when requesting in the attributes list.
            attributes: List of attribute labels to include in results (max 20 custom attrs).
                        Example: ['sku', 'attributes.brand', 'attributes.amazon_asin'].
                        Without this, attribute values will be empty in results.
            limit: Results per page (max 100). Default 100.
            page: Page number. Default 1.

        Returns:
            JSON with data array and pagination. Results contain basic fields + requested attributes.

        Notes:
            - search results never include product_family_id — use plytix_get_product for that.
            - Ordering with >10,000 matching products returns a 428 error.
            - Max 50 columns (attributes + fields) per request.
        """
        try:
            data: dict = {"pagination": {"page": page, "page_size": limit}}
            if filters:
                if isinstance(filters[0], dict):
                    data["filters"] = [filters]
                else:
                    data["filters"] = filters
            if attributes:
                data["attributes"] = attributes
            result = await client.post("/products/search", data)
            return fmt(result, "products")
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_find_products_by_attribute",
        annotations={"title": "Find Products by Custom Attribute", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_find_products_by_attribute(
        attribute_name: str,
        value: str,
        operator: str = "eq",
        sku_pattern: Optional[str] = None,
        limit: int = 50,
    ) -> str:
        """Find products by custom attribute value (client-side filtering workaround).

        Plytix search API cannot filter by custom attributes. This tool works around
        that limitation by fetching products and filtering locally.

        Args:
            attribute_name: The attribute label to match (e.g., 'amazon_parent_asin').
            value: The value to match.
            operator: Match type — 'eq' (exact), 'like' (contains), 'startswith', 'endswith'.
            sku_pattern: Optional SKU pattern to pre-filter with API (speeds up search, use 'like').
            limit: Maximum matching products to return (default 50; higher = slower).

        Returns:
            JSON array of matching products with full attribute data.

        Warning:
            This tool makes N+1 API calls (one per product to get full attributes).
            It is slower than native API filtering. Use sku_pattern to limit the result set.
        """
        try:
            matching = []
            page = 1
            api_filters = []
            if sku_pattern:
                api_filters.append({"field": "sku", "operator": "like", "value": sku_pattern})

            while len(matching) < limit:
                data: dict = {
                    "pagination": {"page": page, "page_size": 100},
                    "attributes": [attribute_name],
                }
                if api_filters:
                    data["filters"] = [api_filters]
                result = await client.post("/products/search", data)
                products = result.get("data", [])
                if not products:
                    break

                for p in products:
                    if len(matching) >= limit:
                        break
                    full_result = await client.get(f"/products/{quote(p['id'])}")
                    if full_result and "data" in full_result and full_result["data"]:
                        full = full_result["data"][0]
                    else:
                        full = p
                    attr_val = full.get("attributes", {}).get(attribute_name)
                    match = False
                    if operator == "eq":
                        match = str(attr_val or "") == str(value)
                    elif operator == "like":
                        match = str(value).lower() in str(attr_val or "").lower()
                    elif operator == "startswith":
                        match = str(attr_val or "").startswith(value)
                    elif operator == "endswith":
                        match = str(attr_val or "").endswith(value)
                    if match:
                        matching.append(full)

                pagination = result.get("pagination", {})
                total = pagination.get("total_count", pagination.get("total", 0))
                if page * 100 >= total:
                    break
                page += 1

            return fmt(matching, "products")
        except Exception as e:
            return handle_error(e)

    if not read_only:
        @mcp.tool(
            name="plytix_create_product",
            annotations={"title": "Create Plytix Product", "readOnlyHint": False, "openWorldHint": True}
        )
        async def plytix_create_product(
            sku: str,
            label: Optional[str] = None,
            status: Optional[str] = None,
            gtin: Optional[str] = None,
            attributes: Optional[dict] = None,
        ) -> str:
            """Create a new product in Plytix PIM.

            Args:
                sku: Product SKU (required, must be unique).
                label: Product display name.
                status: Product status (e.g., 'draft', 'completed').
                gtin: GTIN/UPC/EAN barcode.
                attributes: Dict of {attribute_label: value} for custom attributes.
                            DateAttribute values must be 'YYYY-MM-DD' format.
                            DropdownAttribute values must be simple strings.

            Returns:
                JSON with created product data including the new product ID.

            Notes:
                - product_family CANNOT be set here — use plytix_assign_product_family after creation.
                - Assets and categories must be linked separately after creation.
            """
            try:
                data: dict = {"sku": sku}
                if label is not None:
                    data["label"] = label
                if status is not None:
                    data["status"] = status
                if gtin is not None:
                    data["gtin"] = gtin
                if attributes:
                    data["attributes"] = attributes
                result = await client.post("/products", data)
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_update_product",
            annotations={"title": "Update Plytix Product", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": False}
        )
        async def plytix_update_product(
            product_id: str,
            sku: Optional[str] = None,
            label: Optional[str] = None,
            status: Optional[str] = None,
            gtin: Optional[str] = None,
            thumbnail: Optional[str] = None,
            attributes: Optional[dict] = None,
        ) -> str:
            """Update an existing product's fields and/or attributes (partial update).

            Args:
                product_id: The Plytix product ID.
                sku: New SKU (optional).
                label: New display name (optional).
                status: New status (optional).
                gtin: New GTIN (optional).
                thumbnail: Asset ID to set as thumbnail (string ID is auto-wrapped to {id: ...}).
                attributes: Dict of {attribute_label: value} to update. Set value to null to clear.
                            DateAttribute: use 'YYYY-MM-DD' format.
                            DropdownAttribute: use simple strings.

            Returns:
                JSON with updated product data.

            Notes:
                - product_family CANNOT be changed here — use plytix_assign_product_family.
                - Only specified fields are updated (PATCH semantics).
                - Thumbnail is auto-wrapped: 'asset123' → {'id': 'asset123'}.
            """
            try:
                data: dict = {}
                if sku is not None:
                    data["sku"] = sku
                if label is not None:
                    data["label"] = label
                if status is not None:
                    data["status"] = status
                if gtin is not None:
                    data["gtin"] = gtin
                if thumbnail is not None:
                    data["thumbnail"] = {"id": thumbnail} if isinstance(thumbnail, str) else thumbnail
                if attributes is not None:
                    data["attributes"] = attributes
                if not data:
                    return '{"error": "No fields provided to update."}'
                result = await client.patch(f"/products/{quote(product_id)}", data)
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_delete_product",
            annotations={"title": "Delete Plytix Product", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": True}
        )
        async def plytix_delete_product(product_id: str) -> str:
            """Delete a product from Plytix PIM. This action is irreversible.

            Args:
                product_id: The Plytix product ID to delete.

            Returns:
                JSON confirmation of deletion.
            """
            try:
                result = await client.delete(f"/products/{quote(product_id)}")
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_bulk_update_products",
            annotations={"title": "Bulk Update Plytix Products", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": False}
        )
        async def plytix_bulk_update_products(updates: list) -> str:
            """Bulk update multiple products in a single API request.

            Args:
                updates: List of product update objects, each with 'id' plus fields to update.
                         Example: [{"id": "abc123", "attributes": {"brand": "ACME"}}, ...]

            Returns:
                JSON API response for the bulk operation.
            """
            try:
                result = await client.post("/products/bulk", {"products": updates})
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_add_product_assets",
            annotations={"title": "Add Assets to Product", "readOnlyHint": False, "openWorldHint": True}
        )
        async def plytix_add_product_assets(
            product_id: str,
            asset_ids: list,
            attribute_label: str = "assets",
        ) -> str:
            """Link assets to a product via a media gallery attribute.

            Args:
                product_id: The Plytix product ID.
                asset_ids: List of asset IDs to link.
                attribute_label: Media gallery attribute name to link to (default: 'assets').
                                 Use the attribute's label (e.g., 'amazon_images', 'product_photos').
                                 The attribute must be of type MediaGalleryAttribute.

            Returns:
                JSON array with per-asset results including status (linked/already_linked/error).
            """
            try:
                results = []
                for asset_id in asset_ids:
                    try:
                        data = {"id": asset_id, "attribute_label": attribute_label}
                        result = await client.post(f"/products/{quote(product_id)}/assets", data)
                        results.append({"asset_id": asset_id, "status": "linked", "response": result})
                    except Exception as err:
                        if "already" in str(err).lower():
                            results.append({"asset_id": asset_id, "status": "already_linked"})
                        else:
                            results.append({"asset_id": asset_id, "status": "error", "error": str(err)})
                return fmt(results)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_remove_product_assets",
            annotations={"title": "Remove Assets from Product", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": False}
        )
        async def plytix_remove_product_assets(product_id: str, asset_ids: list) -> str:
            """Unlink assets from a product. The assets are NOT deleted from the account.

            Args:
                product_id: The Plytix product ID.
                asset_ids: List of asset IDs to unlink.

            Returns:
                JSON API response.

            Note:
                This endpoint may return 405 (Method Not Allowed) in some Plytix configurations.
            """
            try:
                result = await client.delete(
                    f"/products/{quote(product_id)}/assets",
                    data={"assets": asset_ids},
                )
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_add_product_categories",
            annotations={"title": "Add Product to Categories", "readOnlyHint": False, "openWorldHint": True}
        )
        async def plytix_add_product_categories(product_id: str, category_ids: list) -> str:
            """Add a product to one or more categories.

            Args:
                product_id: The Plytix product ID.
                category_ids: List of category IDs to assign the product to.

            Returns:
                JSON API response.
            """
            try:
                result = await client.post(
                    f"/products/{quote(product_id)}/categories",
                    {"categories": category_ids},
                )
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_remove_product_categories",
            annotations={"title": "Remove Product from Categories", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": False}
        )
        async def plytix_remove_product_categories(product_id: str, category_ids: list) -> str:
            """Remove a product from one or more categories.

            Args:
                product_id: The Plytix product ID.
                category_ids: List of category IDs to remove the product from.

            Returns:
                JSON API response.
            """
            try:
                result = await client.delete(
                    f"/products/{quote(product_id)}/categories",
                    data={"categories": category_ids},
                )
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_add_product_relationships",
            annotations={"title": "Add Product Relationships", "readOnlyHint": False, "openWorldHint": True}
        )
        async def plytix_add_product_relationships(
            product_id: str,
            relationship_id: str,
            related_product_ids: list,
            quantity: int = 1,
        ) -> str:
            """Link related products to a product via a relationship type.

            Relationships are directional: this links FROM product_id TO related_product_ids.

            Args:
                product_id: The source product ID.
                relationship_id: The relationship type ID (use plytix_list_relationships to find IDs).
                related_product_ids: List of product IDs to link as related.
                quantity: Quantity for each relationship (default: 1).

            Returns:
                JSON API response.

            Note:
                For bidirectional visibility, link from both sides.
                Use plytix_get_relationship_by_name to find relationship IDs by name.
            """
            try:
                product_relationships = [
                    {"product_id": pid, "quantity": quantity}
                    for pid in related_product_ids
                ]
                result = await client.post(
                    f"/products/{quote(product_id)}/relationships/{quote(relationship_id)}",
                    {"product_relationships": product_relationships},
                )
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_remove_product_relationships",
            annotations={"title": "Remove Product Relationships", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": False}
        )
        async def plytix_remove_product_relationships(
            product_id: str,
            relationship_id: str,
            related_product_ids: list,
        ) -> str:
            """Unlink related products from a relationship.

            Args:
                product_id: The source product ID.
                relationship_id: The relationship type ID.
                related_product_ids: List of product IDs to unlink.

            Returns:
                JSON API response.
            """
            try:
                result = await client.delete(
                    f"/products/{quote(product_id)}/relationships/{quote(relationship_id)}",
                    data={"products": related_product_ids},
                )
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_assign_product_family",
            annotations={"title": "Assign Product Family", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": False}
        )
        async def plytix_assign_product_family(product_id: str, family_id: str) -> str:
            """Assign a product family to a product.

            This is the ONLY way to assign a family — update_product silently ignores
            the product_family field (a known Plytix API limitation).

            Args:
                product_id: The Plytix product ID.
                family_id: The product family ID to assign. Use plytix_list_product_families
                           to find available family IDs.

            Returns:
                JSON API response with updated product data.

            Warning:
                Changing a product's family may cause data loss for attributes specific
                to the previous family. Cannot assign family to variant products.
            """
            try:
                result = await client.post(
                    f"/products/{quote(product_id)}/family",
                    {"product_family_id": family_id},
                )
                return fmt(result)
            except Exception as e:
                return handle_error(e)
