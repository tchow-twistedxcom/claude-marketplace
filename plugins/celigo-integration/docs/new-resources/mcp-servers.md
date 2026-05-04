# Celigo MCP Servers

Expose Celigo Tools and builder-mode APIs to AI agents via the Model Context Protocol.

## CLI surface

```bash
python3 celigo_api.py mcp-servers list
python3 celigo_api.py mcp-servers get <id>
python3 celigo_api.py mcp-servers create --data '<json>'
python3 celigo_api.py mcp-servers update <id> --data '<partial-json>'   # fetch-merge-PUT
python3 celigo_api.py mcp-servers delete <id>
python3 celigo_api.py mcp-servers start <id>
python3 celigo_api.py mcp-servers stop <id>
python3 celigo_api.py mcp-servers status <id>
```

## Key notes

- A running MCP Server exposes an SSE endpoint that Claude Code and other MCP clients
  can connect to for tool invocations.
- `start` and `stop` are asynchronous — poll `status` to confirm the state transition.
- Stopping a server does not delete it; its configuration is preserved.
