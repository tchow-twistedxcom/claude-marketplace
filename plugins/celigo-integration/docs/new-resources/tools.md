# Celigo Tools

Reusable processing units that can be invoked standalone or exposed via MCP Servers.

## CLI surface

```bash
python3 celigo_api.py tools list
python3 celigo_api.py tools get <id>
python3 celigo_api.py tools create --data '<json>'
python3 celigo_api.py tools update <id> --data '<partial-json>'   # fetch-merge-PUT
python3 celigo_api.py tools delete <id>
python3 celigo_api.py tools invoke <id> --data '<payload>'
python3 celigo_api.py tools dependencies <id>
```

## Key notes

- `update` always uses fetch-merge-PUT — never send a partial payload directly.
- `invoke` triggers the tool and returns the output synchronously.
- `dependencies` returns flows and MCP Servers that reference this tool.
