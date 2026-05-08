# Celigo Trading Partner Connectors

B2B onboarding templates that bundle connection, export, import, and EDI profile
configurations for a specific trading partner relationship.

## CLI surface

```bash
python3 celigo_api.py trading-partners list
python3 celigo_api.py trading-partners get <id>
python3 celigo_api.py trading-partners create --data '<json>'
python3 celigo_api.py trading-partners update <id> --data '<partial-json>'  # fetch-merge-PUT
```

Note: Trading Partner Connectors do not support delete via the API.

## Create payload example

```json
{
  "name": "ACME B2B Connector",
  "supportedBy": [
    {"type": "ediProfile", "_id": "<edi-profile-id>"},
    {"type": "connection",  "_id": "<connection-id>"},
    {"type": "export",      "_id": "<export-id>"},
    {"type": "import",      "_id": "<import-id>"}
  ]
}
```

## Key notes

- `supportedBy` links the connector to existing Celigo resources.
- Pass `_id` values (not names) for `supportedBy` entries.
- `update` uses fetch-merge-PUT discipline.
