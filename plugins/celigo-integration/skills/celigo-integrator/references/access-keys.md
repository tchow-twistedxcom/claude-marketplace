# Access Tokens

Account-level API tokens for programmatic access. Managed via `/v1/accesstokens`.

## CLI Commands

```bash
# List all access tokens
python3 scripts/celigo_api.py accesstokens list

# Get a specific token
python3 scripts/celigo_api.py accesstokens get <token_id>

# Create a new token
python3 scripts/celigo_api.py accesstokens create \
  --data '{"name": "CI Deploy Token", "scope": "integrations:write"}'

# Update a token (fetch-merge-PUT)
python3 scripts/celigo_api.py accesstokens update <token_id> \
  --data '{"name": "New Name"}'

# Delete a token
python3 scripts/celigo_api.py accesstokens delete <token_id>
```

## Key Fields

| Field | Type | Description |
|---|---|---|
| `_id` | string | Token ObjectId |
| `name` | string | Human-readable label |
| `scope` | string | Permission scope |
| `token` | string | The actual bearer token value (read-only after creation) |
| `createdAt` | ISO 8601 | Creation timestamp |
| `lastModified` | ISO 8601 | Last modification |

Note: The `token` field value is only visible at creation time. It cannot be retrieved later
(read-only field, stripped on PUT). Store it securely when created.

## API Endpoints (Reference)

```
GET    /v1/accesstokens         - List tokens
GET    /v1/accesstokens/:id     - Get token
POST   /v1/accesstokens         - Create token
PUT    /v1/accesstokens/:id     - Update token (full-replace)
DELETE /v1/accesstokens/:id     - Delete token
```
