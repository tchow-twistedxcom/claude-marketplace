# Plytix PIM MCP Server

Full-coverage MCP server for the [Plytix PIM API v1](https://pim.plytix.com/api/v1). ~77 tools across all resource domains.

## Domains Covered

| Domain | Tools | Read | Write |
|--------|-------|------|-------|
| Products | 17 | list, get, search, find_by_attribute, get_assets, get_categories, get_relationships | create, update, delete, bulk_update, add/remove assets, add/remove categories, add/remove relationships, assign_family |
| Assets | 7 | list, get, search, get_download_url | upload_url, update, delete |
| Categories (Product) | 8 | list, get, get_tree, list_products | create, update, delete, add_subcategory |
| Categories (File) | 6 | list, search | create, add_subcategory, update, delete |
| Variants | 7 | list, get | create, update, delete, bulk_create, resync |
| Attributes | 10 | list, get, list_groups, get_group | create, update, delete, create_group, update_group, delete_group |
| Relationships | 11 | list, get, search, get_by_name | create, update, delete |
| Families | 10 | list, get, search, get_attributes, get_all_attributes | create, update, delete, link_attributes, unlink_attributes |
| Accounts | 2 | list_members, list_api_credentials | — |
| Filters | 3 | get_product/asset/relationship_filters | — |

## Setup

### Claude Desktop / Cursor / Other MCP clients

Add to your `.mcp.json` (or client MCP config):

```json
{
  "mcpServers": {
    "plytix": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/<your-org>/<your-repo>@main#subdirectory=extensions/plytix",
        "plytix-mcp"
      ],
      "env": {
        "PLYTIX_API_KEY": "your-api-key",
        "PLYTIX_API_PASSWORD": "your-api-password"
      }
    }
  }
}
```

### Read-Only Mode

To restrict to read-only operations (~40 tools — no create/update/delete):

```json
{
  "env": {
    "PLYTIX_API_KEY": "your-api-key",
    "PLYTIX_API_PASSWORD": "your-api-password",
    "PLYTIX_READ_ONLY": "true"
  }
}
```

### Claude Code (local dev)

Run directly from this directory:

```bash
cd extensions/plytix
uv run --with mcp>=1.0.0 --with httpx>=0.27.0 src/server.py
```

Or add to `.mcp.json` at repo root:

```json
{
  "mcpServers": {
    "plytix": {
      "command": "uv",
      "args": [
        "run",
        "--with", "mcp>=1.0.0",
        "--with", "httpx>=0.27.0",
        "/path/to/extensions/plytix/src/server.py"
      ],
      "env": {
        "PLYTIX_API_KEY": "your-api-key",
        "PLYTIX_API_PASSWORD": "your-api-password"
      }
    }
  }
}
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PLYTIX_API_KEY` | Yes | — | Plytix API key |
| `PLYTIX_API_PASSWORD` | Yes | — | Plytix API password |
| `PLYTIX_API_URL` | No | `https://pim.plytix.com/api/v1` | Override API base URL |
| `PLYTIX_AUTH_URL` | No | `https://auth.plytix.com/auth/api/get-token` | Override auth URL |
| `PLYTIX_READ_ONLY` | No | `false` | Set to `true` for read-only mode |

## API Notes

- **Authentication**: API Key + Password → 15-minute bearer token, auto-refreshed
- **Rate limits**: 429 responses are retried automatically with `Retry-After` header
- **Response size**: Results are truncated to 900KB to stay within MCP limits
- **Attribute groups**: The Plytix `/attributes/product/groups` API has a known upstream 500 error bug
- **Product search**: Returns basic fields only; use `plytix_get_product` for full details
- **Custom attribute filters**: Cannot be used in `plytix_search_products`; use `plytix_find_products_by_attribute` instead
