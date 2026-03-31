"""Product domain MCP tools — CRUD, search, bulk, assets/categories/relationships."""
import asyncio
import csv
import io
import json
import time
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
            # Preserve any attribute/relationship fields the caller explicitly requested
            extra: set = set()
            if attributes:
                for a in attributes:
                    if a.startswith("attributes."):
                        extra.add("attributes")
                    elif a.startswith("relationships."):
                        extra.add("relationships")
                    else:
                        extra.add(a)
            return fmt(result, "products", extra_keep=extra or None)
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

            # Return full product data — no slim, just byte-cap
            return fmt(matching)
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_export_products",
        annotations={"title": "Export Products to File", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_export_products(
        filters: Optional[list] = None,
        attributes: Optional[list] = None,
        format: str = "csv",
        max_products: int = 1000,
    ) -> str:
        """Export products to a CSV or JSON file with auto-pagination.

        Handles the N+1 API limitation automatically: uses the fast search path
        when ≤20 custom attributes are needed, or concurrent get_product calls otherwise.

        Args:
            filters: List of filter dicts [{field, operator, value}]. Same syntax as
                     plytix_search_products. Use 'like' for text matching.
            attributes: List of attribute labels to export, e.g. ['attributes.brand',
                        'attributes.color']. Max 20 for fast path (search API).
                        Pass None or >20 to use the full path (all attributes via get_product).
            format: Output format — 'csv' (default) or 'json'.
            max_products: Maximum products to export. Default 1000, max 10000.

        Returns:
            JSON metadata: {file_path, format, product_count, columns (CSV only),
                            strategy, elapsed_seconds, truncated}.

        Notes:
            Fast path (≤20 custom attrs): ~10 products/second via search API.
            Full path (>20 attrs or None): ~5 products/second via get_product calls.
            The exported file is written to /tmp/ and can be read with standard file tools.
        """
        try:
            import httpx as _httpx

            t_start = time.time()
            fmt_lower = format.lower()
            if fmt_lower not in ("csv", "json"):
                return json.dumps({"error": "format must be 'csv' or 'json'"})
            max_products = min(max_products, 10_000)

            # Determine strategy
            custom_attr_count = sum(
                1 for a in (attributes or []) if a.startswith("attributes.")
            ) if attributes else 0
            use_fast_path = attributes is not None and custom_attr_count <= 20

            # ----------------------------------------------------------------
            # Helpers
            # ----------------------------------------------------------------
            async def _safe_post(endpoint: str, payload: dict, retries: int = 3) -> dict:
                for attempt in range(retries):
                    try:
                        return await client.post(endpoint, payload)
                    except _httpx.HTTPStatusError as e:
                        if e.response.status_code == 429 and attempt < retries - 1:
                            wait = int(e.response.headers.get("Retry-After", "10"))
                            await asyncio.sleep(wait)
                            continue
                        raise
                raise RuntimeError("Rate limit retries exhausted")

            async def _safe_get(endpoint: str, retries: int = 3) -> dict:
                for attempt in range(retries):
                    try:
                        return await client.get(endpoint)
                    except _httpx.HTTPStatusError as e:
                        if e.response.status_code == 429 and attempt < retries - 1:
                            wait = int(e.response.headers.get("Retry-After", "10"))
                            await asyncio.sleep(wait)
                            continue
                        raise
                raise RuntimeError("Rate limit retries exhausted")

            # ----------------------------------------------------------------
            # Fast path: search with attributes param
            # ----------------------------------------------------------------
            products = []
            strategy = "fast_path" if use_fast_path else "full_path"
            truncated = False

            if use_fast_path:
                page = 1
                while len(products) < max_products:
                    payload: dict = {
                        "pagination": {"page": page, "page_size": 100},
                        "attributes": attributes,
                    }
                    if filters:
                        payload["filters"] = [filters] if isinstance(filters[0], dict) else filters
                    result = await _safe_post("/products/search", payload)
                    batch = result.get("data", [])
                    if not batch:
                        break
                    products.extend(batch)
                    # Check if we've hit max
                    if len(products) >= max_products:
                        products = products[:max_products]
                        # Check if there were more
                        pagination = result.get("pagination", {})
                        total = pagination.get("total_count", pagination.get("total", 0))
                        truncated = total > max_products
                        break
                    if len(batch) < 100:
                        break
                    page += 1
                    await asyncio.sleep(0.2)

            # ----------------------------------------------------------------
            # Full path: search IDs → concurrent get_product
            # ----------------------------------------------------------------
            else:
                # Phase 1: collect IDs
                product_ids = []
                page = 1
                while len(product_ids) < max_products:
                    payload = {
                        "pagination": {"page": page, "page_size": 100},
                        "attributes": ["sku"],
                    }
                    if filters:
                        payload["filters"] = [filters] if isinstance(filters[0], dict) else filters
                    result = await _safe_post("/products/search", payload)
                    batch = result.get("data", [])
                    if not batch:
                        break
                    product_ids.extend(p["id"] for p in batch if "id" in p)
                    if len(product_ids) >= max_products:
                        product_ids = product_ids[:max_products]
                        pagination = result.get("pagination", {})
                        total = pagination.get("total_count", pagination.get("total", 0))
                        truncated = total > max_products
                        break
                    if len(batch) < 100:
                        break
                    page += 1
                    await asyncio.sleep(0.1)

                # Phase 2: concurrent get_product with semaphore
                sem = asyncio.Semaphore(5)

                async def fetch_one(pid: str):
                    async with sem:
                        r = await _safe_get(f"/products/{quote(pid)}")
                        if r and "data" in r and r["data"]:
                            return r["data"][0]
                        return None

                tasks = [fetch_one(pid) for pid in product_ids]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                products = [r for r in results if isinstance(r, dict)]

            # ----------------------------------------------------------------
            # Build inline output (no file — returned directly in response)
            # ----------------------------------------------------------------
            elapsed = round(time.time() - t_start, 1)

            if fmt_lower == "json":
                header = json.dumps({
                    "product_count": len(products),
                    "strategy": strategy,
                    "elapsed_seconds": elapsed,
                    "truncated": truncated,
                }, indent=2)
                return header + "\n\n" + json.dumps(products, indent=2, default=str)
            else:
                # Build column list: built-in fields first, then attributes.*
                builtin_cols = ["id", "sku", "label", "status", "gtin",
                                "thumbnail", "product_family_id", "created", "modified"]
                attr_col_set: set = set()
                for p in products:
                    for key in p.get("attributes", {}):
                        attr_col_set.add(f"attributes.{key}")
                columns = builtin_cols + sorted(attr_col_set)

                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
                writer.writeheader()
                for p in products:
                    row: dict = {k: p.get(k, "") for k in builtin_cols}
                    for key, val in p.get("attributes", {}).items():
                        cell = json.dumps(val, default=str) if isinstance(val, (list, dict)) else val
                        row[f"attributes.{key}"] = "" if cell is None else cell
                    writer.writerow(row)

                meta_comment = (
                    f"# product_count={len(products)} strategy={strategy} "
                    f"elapsed={elapsed}s truncated={truncated}\n"
                )
                return meta_comment + buf.getvalue()
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
