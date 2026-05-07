# Celigo Builder-mode APIs

REST endpoint definitions built with Celigo's API builder. Deployed versions are callable
by external consumers including MCP Servers.

## CLI surface

```bash
python3 celigo_api.py builder-apis list
python3 celigo_api.py builder-apis get <id>
python3 celigo_api.py builder-apis create --data '<json>'
python3 celigo_api.py builder-apis update <id> --data '<partial-json>'   # fetch-merge-PUT
python3 celigo_api.py builder-apis delete <id>
python3 celigo_api.py builder-apis deploy <id>
python3 celigo_api.py builder-apis versions <id>
```

## Key notes

- `deploy` publishes the current draft as a live version.
- `versions` returns version history — use for rollback planning.
- `update` uses fetch-merge-PUT discipline.
