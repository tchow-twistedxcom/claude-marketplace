# Celigo Notifications

Per-resource, per-event email subscription management.

## CLI surface

```bash
python3 celigo_api.py notifications list
python3 celigo_api.py notifications get <id>
python3 celigo_api.py notifications create --data '<json>'
python3 celigo_api.py notifications update <id> --data '<partial-json>'
python3 celigo_api.py notifications delete <id>
```

## Create payload

```json
{
  "_resourceId": "<flow-id-or-integration-id>",
  "_resourceType": "flow",
  "event": "error",
  "recipients": ["user@example.com"]
}
```

Required fields: `_resourceId`, `_resourceType`, `event`.

## Key notes

- `_resourceType` values include `flow`, `integration`, `connection`.
- `event` values include `error`, `completed`, `warning`.
- `update` uses fetch-merge-PUT discipline.
