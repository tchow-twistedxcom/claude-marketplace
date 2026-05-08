# Celigo OPA (On-Premise Agents)

Manage On-Premise Agents that bridge Celigo cloud to private/on-premise data sources.

## CLI surface

```bash
python3 celigo_api.py opa list
python3 celigo_api.py opa get <id>
python3 celigo_api.py opa create --data '<json>'
python3 celigo_api.py opa update <id> --data '<partial-json>'   # fetch-merge-PUT
python3 celigo_api.py opa delete <id>
python3 celigo_api.py opa status <id>
python3 celigo_api.py opa restart <id>
```

## Key notes

- `status` returns the current connection state (`connected`, `disconnected`, `unknown`).
- `restart` triggers a reconnect attempt — useful when an OPA has gone offline.
- An OPA must be installed and running on your private network before `status` shows `connected`.
