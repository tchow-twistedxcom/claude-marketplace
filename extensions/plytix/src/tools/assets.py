"""Asset domain MCP tools — CRUD, search, upload, download URL."""
from typing import Optional
from mcp.server.fastmcp import FastMCP
from plytix_client import PlytixClient, fmt, handle_error
from urllib.parse import quote
import httpx


def register_asset_tools(mcp: FastMCP, client: PlytixClient, read_only: bool = False) -> None:
    """Register all asset tools. Pass read_only=True to skip write tools."""

    @mcp.tool(
        name="plytix_get_asset",
        annotations={"title": "Get Plytix Asset", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_get_asset(asset_id: str) -> str:
        """Get full asset details by ID.

        Args:
            asset_id: The Plytix asset ID.

        Returns:
            JSON asset object with id, filename, file_type, file_size, url, public_url,
            categories, created, modified.
        """
        try:
            result = await client.get(f"/assets/{quote(asset_id)}")
            return fmt(result)
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_search_assets",
        annotations={"title": "Search Plytix Assets", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_search_assets(
        filters: Optional[list] = None,
        limit: int = 100,
        page: int = 1,
    ) -> str:
        """Search assets with filters.

        Args:
            filters: List of filter dicts [{field, operator, value}].
                     Operators: eq, !eq, like, !like, in, !in, gt, gte, lt, lte, last_days.
                     Use 'like' for partial text match (NOT 'contains').
                     Common fields: filename, extension, created, modified.
            limit: Results per page (max 100). Default 100.
            page: Page number. Default 1.

        Returns:
            JSON with data array and pagination.

        Note:
            'public_url' is NOT directly searchable. Search by filename instead
            (last segment of the URL path).
        """
        try:
            wrapped = [filters] if filters and isinstance(filters[0], dict) else (filters or [])
            data = {
                "filters": wrapped,
                "pagination": {"page": page, "page_size": limit},
            }
            result = await client.post("/assets/search", data)
            return fmt(result, "assets")
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_get_asset_download_url",
        annotations={"title": "Get Asset Download URL", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_get_asset_download_url(asset_id: str) -> str:
        """Get the download URL for an asset.

        Args:
            asset_id: The Plytix asset ID.

        Returns:
            JSON with download URL information.
        """
        try:
            result = await client.get(f"/assets/{quote(asset_id)}/download")
            return fmt(result)
        except Exception as e:
            return handle_error(e)

    if not read_only:
        @mcp.tool(
            name="plytix_upload_asset_url",
            annotations={"title": "Upload Asset from URL", "readOnlyHint": False, "openWorldHint": True}
        )
        async def plytix_upload_asset_url(
            url: str,
            filename: Optional[str] = None,
            return_existing: bool = True,
        ) -> str:
            """Upload an asset to Plytix from a public URL.

            Args:
                url: Public URL of the image/file to import. Must be publicly accessible.
                filename: Optional custom filename (otherwise derived from URL).
                return_existing: If True and asset already exists (409 Conflict), return the
                                 existing asset info instead of raising an error. Default True.

            Returns:
                JSON asset object with id, filename, url.
                If asset already existed and return_existing=True: {'id': existing_id, 'status': 'existing', 'url': url}.

            Note:
                Returns 409 Conflict if the URL is already uploaded. With return_existing=True
                (default), the existing asset ID is extracted from the error and returned.
            """
            try:
                data: dict = {"url": url}
                if filename:
                    data["filename"] = filename
                result = await client.post("/assets", data)
                # Unwrap: {"data": [asset_dict]}
                if isinstance(result, dict) and "data" in result:
                    items = result["data"]
                    if isinstance(items, list) and items:
                        return fmt(items[0])
                return fmt(result)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 409 and return_existing:
                    try:
                        body = e.response.json()
                        error_info = body.get("error", body)
                        errors = error_info.get("errors", [])
                        for err in errors:
                            if err.get("field") == "asset.id":
                                existing_id = err.get("msg")
                                if existing_id:
                                    return fmt({"id": existing_id, "status": "existing", "url": url})
                    except Exception:
                        pass
                return handle_error(e)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_update_asset",
            annotations={"title": "Update Plytix Asset", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": False}
        )
        async def plytix_update_asset(
            asset_id: str,
            filename: Optional[str] = None,
            categories: Optional[list] = None,
        ) -> str:
            """Update asset metadata.

            Args:
                asset_id: The Plytix asset ID.
                filename: New filename for the asset (optional).
                categories: List of file category IDs to assign to the asset (optional).
                            Each category ID should be a string.

            Returns:
                JSON with updated asset data.
            """
            try:
                data: dict = {}
                if filename is not None:
                    data["filename"] = filename
                if categories is not None:
                    data["categories"] = [{"id": c} for c in categories]
                if not data:
                    return '{"error": "No fields provided to update."}'
                result = await client.patch(f"/assets/{quote(asset_id)}", data)
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_delete_asset",
            annotations={"title": "Delete Plytix Asset", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": True}
        )
        async def plytix_delete_asset(asset_id: str) -> str:
            """Delete an asset from Plytix. This action is irreversible.

            Args:
                asset_id: The Plytix asset ID to delete.

            Returns:
                JSON confirmation of deletion.
            """
            try:
                result = await client.delete(f"/assets/{quote(asset_id)}")
                return fmt(result)
            except Exception as e:
                return handle_error(e)
