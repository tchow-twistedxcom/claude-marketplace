---
module: n8n MCP
date: 2026-03-08
problem_type: integration_issue
component: tooling
symptoms:
  - "tools/list returns 0 tools on per-workflow MCP SSE endpoint"
  - "ZodError on tool call: path: [''], expected: string, received: undefined"
  - "toolHttpRequest header using headerParameters.parameters creates spurious empty-string toolParameter"
root_cause: wrong_api
resolution_type: code_fix
severity: high
tags: [n8n, mcp, toolhttprequest, mcp-server-trigger, architecture, zod-error]
---

# Troubleshooting: n8n MCP Server Trigger — Zero Tools Exposed + ZodError on Call

## Problem

Building n8n workflows to expose Celigo API calls as MCP tools. The per-workflow SSE endpoint connected, `tools/list` returned 0 tools (or returned tools with spurious empty-string parameters causing ZodErrors), and tool calls failed completely.

## Environment

- Module: n8n MCP Server (Portainer-hosted n8n on twistedx-dockerprod)
- Affected Component: `@n8n/n8n-nodes-langchain.mcpTrigger` + `@n8n/n8n-nodes-langchain.toolHttpRequest`
- Date: 2026-03-08

## Symptoms

- `tools/list` via per-workflow SSE (`GET /mcp/{path}/sse`) returns `{"tools": []}`
- After fixing architecture: `tools/list` returns tool with an empty-string parameter `""`
- Tool call fails with ZodError: `path: [""], expected: string, received: undefined`
- `execute_workflow` via global n8n MCP returns: "Only workflows with Schedule Trigger, Webhook Trigger, Form Trigger, Chat Trigger can be executed"

## What Didn't Work

**Attempted Solution 1:** Webhook-style workflow structure (Trigger → HTTP Request → Code → Respond to Webhook)
- **Why it failed:** MCP Server Trigger node has `inputs: [AiTool]` and `outputs: []`. It is NOT a passthrough trigger. It does NOT pass execution to downstream nodes. The correct data flow is REVERSED — tool nodes connect INTO the trigger, which collects and exposes them.

**Attempted Solution 2:** Calling `execute_workflow` via global n8n MCP server to test MCP Server Trigger workflows
- **Why it failed:** The global n8n MCP server's `execute_workflow` only supports Schedule/Webhook/Form/Chat trigger types. MCP Server Trigger workflows must be accessed via their own per-workflow SSE endpoint (`/mcp/{path}/sse`).

**Attempted Solution 3:** Correct tool-based architecture but using `headerParameters.parameters` for Authorization header in toolHttpRequest
- **Why it failed:** `headerParameters.parameters` is the field format for the regular `HTTP Request` node, not `toolHttpRequest`. The `toolHttpRequest` node uses `parametersHeaders.values` (keypair) or `jsonHeaders` (json string). When using `sendHeaders: true` without `specifyHeaders`, the default `parametersHeaders = {values: [{name: ""}]}` creates a toolParameter with an empty string name. This makes `configureToolFunction` skip the `toolParameters.length === 0` shortcut and fail when the tool is called with an object argument instead of the expected string.

## Solution

### Fix 1: Correct MCP Server Trigger Architecture

**WRONG** (webhook-style — zero tools exposed):
```
MCP Server Trigger → HTTP Request → Code → Respond to Webhook
```

**CORRECT** (tool-based — each connected tool node becomes one MCP tool):
```
toolHttpRequest → [ai_tool output] → MCP Server Trigger [ai_tool input]
```

The connection must use `ai_tool` type, NOT `main`:

```python
# Correct connections JSON
"connections": {
    "My Tool Name": {
        "ai_tool": [[{"node": "MCP Server Trigger", "type": "ai_tool", "index": 0}]]
    }
}
```

### Fix 2: Correct toolHttpRequest Header Configuration

**WRONG** (uses `headerParameters.parameters` — creates empty spurious toolParameter):
```json
{
    "sendHeaders": true,
    "headerParameters": {"parameters": [{"name": "Authorization", "value": "Bearer KEY"}]}
}
```

**CORRECT** (use `specifyHeaders: "json"` with `jsonHeaders`):
```json
{
    "sendHeaders": true,
    "specifyHeaders": "json",
    "jsonHeaders": "{\"Authorization\": \"Bearer YOUR_API_KEY\"}"
}
```

### Complete Working Workflow Structure

```python
import uuid, json

tool_id = str(uuid.uuid4())
trigger_id = str(uuid.uuid4())

workflow = {
    "name": "My MCP Tool Workflow",
    "settings": {"executionOrder": "v1", "availableInMCP": True},
    "nodes": [
        {
            "id": tool_id,
            "name": "My Tool",
            "type": "@n8n/n8n-nodes-langchain.toolHttpRequest",
            "typeVersion": 1.1,
            "position": [-200, 0],
            "parameters": {
                "toolDescription": "Description of what this tool does.",
                "method": "GET",
                "url": "https://api.example.com/endpoint",
                "sendHeaders": True,
                "specifyHeaders": "json",
                "jsonHeaders": json.dumps({"Authorization": "Bearer API_KEY"})
            }
        },
        {
            "id": trigger_id,
            "name": "MCP Server Trigger",
            "type": "@n8n/n8n-nodes-langchain.mcpTrigger",
            "typeVersion": 1,
            "position": [0, 0],
            "webhookId": str(uuid.uuid4()),
            "parameters": {"authentication": "none", "path": "my-tool-path"}
        }
    ],
    "connections": {
        "My Tool": {
            "ai_tool": [[{"node": "MCP Server Trigger", "type": "ai_tool", "index": 0}]]
        }
    }
}
```

### Per-Workflow SSE Access (typeVersion 1)

```bash
# 1. Open SSE connection (get sessionId from event: endpoint)
curl -N -H "Authorization: Bearer JWT_TOKEN" \
  "https://n8n.example.com/mcp/my-tool-path/sse"
# Response includes: event: endpoint, data: /mcp/my-tool-path/messages?sessionId=...

# 2. Send MCP initialize
curl -X POST \
  -H "Authorization: Bearer JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  "https://n8n.example.com/mcp/my-tool-path/messages?sessionId=SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# 3. List tools
curl -X POST \
  -H "Accept: application/json, text/event-stream" \
  "https://n8n.example.com/mcp/my-tool-path/messages?sessionId=SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

**Important**: The `Accept: application/json, text/event-stream` header is required for POST to `/messages`. Without it, n8n returns "Not Acceptable".

## Why This Works

1. **MCP Server Trigger architecture**: The node source (`McpTrigger.node.js`) declares `inputs: [AiTool]` and `outputs: []`. It calls `getConnectedTools(ctx, true, true)` to collect all AI Tool nodes connected to its input and exposes them via `setRequestHandler(ListToolsRequestSchema, ...)`. It is a collector, not a passthrough.

2. **toolHttpRequest header fields**: `headerParameters.parameters` is the field schema for the regular `HTTP Request` node (`n8n-nodes-base.httpRequest`). The `toolHttpRequest` node (`@n8n/n8n-nodes-langchain.toolHttpRequest`) uses a different field structure: `parametersHeaders.values` for keypair mode or `jsonHeaders` for JSON mode. The default value for `parametersHeaders` is `{values: [{name: ""}]}` — this one entry with `name: ""` causes `configureToolFunction` to add an empty-string key to `toolParameters`, which defeats the zero-parameter shortcut and causes ZodErrors when calling the tool.

3. **`availableInMCP: true` in settings**: Required for the workflow to appear in the n8n MCP server's workflow list. Without it, the per-workflow endpoint still works but the workflow won't show up in global tool listings.

## Prevention

- When creating n8n MCP workflows, **always** use `toolHttpRequest` or `toolCode` nodes connected to the trigger's `ai_tool` INPUT — never structure it as a passthrough webhook.
- For `toolHttpRequest` headers: **always** use `specifyHeaders: "json"` + `jsonHeaders` (JSON string). Never use `headerParameters.parameters` — that's for the regular HTTP Request node.
- The `Accept: application/json, text/event-stream` header is required for POSTing to the `/messages` endpoint; omitting it causes 406 "Not Acceptable".
- Do NOT include `active` in the workflow POST body — it's read-only. Activate separately via `POST /api/v1/workflows/{id}/activate`.

## Related Issues

- [mcp-tool-calling-convention-n8n-MCP-20260308.md](./mcp-tool-calling-convention-n8n-MCP-20260308.md) — after fixing architecture: all tools expose `{input: string}` schema, `fetch` not available in toolCode, correct calling convention is `arguments: {"input": "<json-string>"}`
