"""Relationship domain MCP tools — relationship type CRUD + product-level link/unlink."""
from typing import Optional
from mcp.server.fastmcp import FastMCP
from plytix_client import PlytixClient, fmt, handle_error
from urllib.parse import quote


def register_relationship_tools(mcp: FastMCP, client: PlytixClient, read_only: bool = False) -> None:
    """Register all relationship tools. Pass read_only=True to skip write tools."""

    @mcp.tool(
        name="plytix_list_relationships",
        annotations={"title": "List Relationship Types", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_list_relationships(limit: int = 100, page: int = 1) -> str:
        """List relationship type definitions with pagination.

        Relationship types define how products can be connected (e.g., 'Amazon Hierarchy',
        'Related Products', 'Accessories').

        Args:
            limit: Results per page (max 100). Default 100.
            page: Page number. Default 1.

        Returns:
            JSON with data array of relationship types. Each has id, name, label, bidirectional.
        """
        try:
            data = {
                "filters": [],
                "pagination": {"page": page, "page_size": limit},
            }
            result = await client.post("/relationships/search", data)
            return fmt(result, "relationships")
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_get_relationship",
        annotations={"title": "Get Relationship Type", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_get_relationship(relationship_id: str) -> str:
        """Get relationship type definition by ID.

        Args:
            relationship_id: The Plytix relationship type ID.

        Returns:
            JSON object with id, name, label, bidirectional, description.
        """
        try:
            result = await client.get(f"/relationships/{quote(relationship_id)}")
            return fmt(result)
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_search_relationships",
        annotations={"title": "Search Relationship Types", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_search_relationships(
        filters: Optional[list] = None,
        limit: int = 100,
        page: int = 1,
    ) -> str:
        """Search relationship type definitions with filters.

        Args:
            filters: List of filter dicts [{field, operator, value}].
                     Example: [{"field": "name", "operator": "like", "value": "Amazon"}]
            limit: Results per page (max 100). Default 100.
            page: Page number. Default 1.

        Returns:
            JSON with data array of matching relationship types.
        """
        try:
            wrapped = [filters] if filters and isinstance(filters[0], dict) else (filters or [])
            data = {
                "filters": wrapped,
                "pagination": {"page": page, "page_size": limit},
            }
            result = await client.post("/relationships/search", data)
            return fmt(result, "relationships")
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="plytix_get_relationship_by_name",
        annotations={"title": "Get Relationship by Name", "readOnlyHint": True, "openWorldHint": True}
    )
    async def plytix_get_relationship_by_name(name: str) -> str:
        """Find a relationship type definition by name (case-insensitive).

        Args:
            name: The relationship name to search for (partial match using 'like' operator).
                  Returns the first exact match, or first partial match if no exact match.

        Returns:
            JSON relationship type object, or null if not found.
        """
        try:
            data = {
                "filters": [[{"field": "name", "operator": "like", "value": name}]],
                "pagination": {"page": 1, "page_size": 100},
            }
            result = await client.post("/relationships/search", data)
            relationships = result.get("data", [])
            # Prefer exact case-insensitive match
            for rel in relationships:
                if rel.get("name", "").lower() == name.lower():
                    return fmt(rel)
            # Fall back to first result
            if relationships:
                return fmt(relationships[0])
            return fmt(None)
        except Exception as e:
            return handle_error(e)

    if not read_only:
        @mcp.tool(
            name="plytix_create_relationship",
            annotations={"title": "Create Relationship Type", "readOnlyHint": False, "openWorldHint": True}
        )
        async def plytix_create_relationship(
            name: str,
            label: Optional[str] = None,
            bidirectional: bool = False,
            description: Optional[str] = None,
        ) -> str:
            """Create a new relationship type definition.

            Args:
                name: Display name (e.g., 'Amazon Hierarchy', 'Accessories').
                label: Internal identifier (slug). Auto-generated from name if not provided.
                bidirectional: If True, the relationship is visible from both sides. Default False.
                description: Optional description.

            Returns:
                JSON with created relationship type data including the new ID.
            """
            try:
                data: dict = {"name": name, "bidirectional": bidirectional}
                if label is not None:
                    data["label"] = label
                if description is not None:
                    data["description"] = description
                result = await client.post("/relationships", data)
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_update_relationship",
            annotations={"title": "Update Relationship Type", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": False}
        )
        async def plytix_update_relationship(
            relationship_id: str,
            name: Optional[str] = None,
            bidirectional: Optional[bool] = None,
            description: Optional[str] = None,
        ) -> str:
            """Update a relationship type definition.

            Args:
                relationship_id: The Plytix relationship type ID.
                name: New display name (optional).
                bidirectional: New bidirectionality setting (optional).
                description: New description (optional).

            Returns:
                JSON with updated relationship type data.
            """
            try:
                data: dict = {}
                if name is not None:
                    data["name"] = name
                if bidirectional is not None:
                    data["bidirectional"] = bidirectional
                if description is not None:
                    data["description"] = description
                if not data:
                    return '{"error": "No fields provided to update."}'
                result = await client.patch(f"/relationships/{quote(relationship_id)}", data)
                return fmt(result)
            except Exception as e:
                return handle_error(e)

        @mcp.tool(
            name="plytix_delete_relationship",
            annotations={"title": "Delete Relationship Type", "readOnlyHint": False, "openWorldHint": True, "destructiveHint": True}
        )
        async def plytix_delete_relationship(relationship_id: str) -> str:
            """Delete a relationship type definition. This action is irreversible.

            Args:
                relationship_id: The Plytix relationship type ID to delete.

            Returns:
                JSON confirmation of deletion.
            """
            try:
                result = await client.delete(f"/relationships/{quote(relationship_id)}")
                return fmt(result)
            except Exception as e:
                return handle_error(e)
