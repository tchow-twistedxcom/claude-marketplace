"""Account domain MCP tools — members and API credentials (read-only)."""
from typing import Optional
from mcp.server.fastmcp import FastMCP
from plytix_client import PlytixClient, fmt, handle_error


def register_account_tools(mcp: FastMCP, client: PlytixClient, read_only: bool = False) -> None:
    """Register all account tools. Always read-only (no write tools for accounts)."""

    @mcp.tool(
        name="plytix_list_members",
        annotations={"title": "List Account Members", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_list_members(
        filters: Optional[list] = None,
        limit: int = 100,
        page: int = 1,
    ) -> str:
        """List account members (users) in your Plytix organization.

        Args:
            filters: Optional list of filter dicts [{field, operator, value}].
            limit: Results per page (max 100). Default 100.
            page: Page number. Default 1.

        Returns:
            JSON with data array of member objects. Each has id, email, name, role.
        """
        try:
            wrapped = [filters] if filters and isinstance(filters[0], dict) else (filters or [])
            data = {
                "filters": wrapped,
                "pagination": {"page": page, "page_size": limit},
            }
            result = await client.post("/accounts/memberships/search", data)
            return fmt(result, "members")
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_list_api_credentials",
        annotations={"title": "List API Credentials", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_list_api_credentials(
        filters: Optional[list] = None,
        limit: int = 100,
        page: int = 1,
    ) -> str:
        """List API credentials (API keys and tokens) in your Plytix organization.

        Useful for auditing which API keys exist and their associated users.

        Args:
            filters: Optional list of filter dicts [{field, operator, value}].
            limit: Results per page (max 100). Default 100.
            page: Page number. Default 1.

        Returns:
            JSON with data array of credential objects.
        """
        try:
            wrapped = [filters] if filters and isinstance(filters[0], dict) else (filters or [])
            data = {
                "filters": wrapped,
                "pagination": {"page": page, "page_size": limit},
            }
            result = await client.post("/accounts/api-credentials/search", data)
            return fmt(result, "credentials")
        except Exception as e:
            return handle_error(e)
