---
module: n8n MCP
date: 2026-03-08
problem_type: integration_issue
component: tooling
symptoms:
  - "All tools expose {input: string} schema regardless of configured parameters"
  - "Tool call with arguments:{} → ZodError 'Required' at path []"
  - "toolCode 'query is not defined' when called with wrong argument structure"
  - "fetch is not defined in toolCode JavaScript sandbox"
root_cause: wrong_api
resolution_type: code_fix
severity: high
tags: [n8n, mcp, calling-convention, dynamic-tool, toolcode, fetch, helpers-httprequest]
---

# Troubleshooting: n8n MCP Tool Calling Convention + toolCode Implementation

## Problem

After fixing n8n MCP Server Trigger architecture (see [mcp-tools-not-exposed-n8n-MCP-20260308.md](./mcp-tools-not-exposed-n8n-MCP-20260308.md)), tools appeared in `tools/list` but all calls failed with ZodErrors or "query is not defined". Additionally, `fetch()` inside toolCode nodes threw "fetch is not defined".

## Environment

- Module: n8n MCP Server (Portainer-hosted n8n v2.10.4 on twistedx-dockerprod)
- Affected: `@n8n/n8n-nodes-langchain.toolHttpRequest` typeVersion 1.1, `@n8n/n8n-nodes-langchain.toolCode`
- Date: 2026-03-08

## Symptoms

- `tools/list` returns all tools with identical schema: `{"type":"object","properties":{"input":{"type":"string"}},"additionalProperties":true}`
- Tool call with `arguments: {}` → ZodError: `code: invalid_type, expected: object, received: undefined, path: []`
- toolCode tool with `arguments: {"flow_id": "...", "step_id": "..."}` → `There was an error: "query is not defined [line 1]"`
- toolCode JavaScript using `await fetch(url, ...)` → `There was an error: "fetch is not defined [line N]"`

## Root Cause Analysis

### Root Cause 1: `getConnectedTools` converts all N8nTool → DynamicTool

`McpTrigger.node.js` calls `getConnectedTools(ctx, true)` which defaults to `convertStructuredTool = true`.

In `helpers.js`:
```javascript
if (convertStructuredTool && tool instanceof N8nTool) {
    finalTools.push(tool.asDynamicTool());  // line 161
}
```

This converts every `N8nTool` (typeVersion 1.1 toolHttpRequest, which extends `DynamicStructuredTool`) to a regular `DynamicTool` via `asDynamicTool()`. `DynamicTool` has a fixed LangChain schema of `{input: string}`.

**Result**: ALL tools—including zero-parameter toolHttpRequest and toolCode tools—show `{input: string}` schema in MCP `tools/list`.

### Root Cause 2: Calling convention mismatch

Since all tools are `DynamicTool` after conversion, they expect a string input via the `input` key. When called:
- `arguments: {}` → `input` field is missing → DynamicTool receives `undefined` → ZodError at root path `[]`
- `arguments: {"flow_id": "x"}` → `input` field is missing → toolCode receives `undefined` as query → NodeVM doesn't expose undefined properties as globals → "query is not defined"

### Root Cause 3: `fetch` not available in toolCode NodeVM sandbox

toolCode uses `JavaScriptSandbox` backed by `NodeVM` (vm2). The global `fetch` Web API is NOT available in this environment. The helpers object provides `this.helpers.httpRequest()` instead.

## What Didn't Work

**Attempt 1:** Call `list_integrations` with `arguments: {}`
- `DynamicTool.invoke({})` → input field undefined → ZodError "Required" at path []

**Attempt 2:** Call toolCode with `arguments: {"flow_id": "x", "step_id": "y"}`
- DynamicTool receives `undefined` as query string → context.query = undefined → NodeVM doesn't expose undefined as global → "query is not defined"

**Attempt 3:** Use `fetch()` in toolCode JavaScript
- NodeVM sandbox doesn't include Web APIs → "fetch is not defined"

## Solution

### Fix 1: Always use `{input: "<json-string>"}` calling convention

For ALL n8n MCP tools (toolHttpRequest and toolCode), pass arguments wrapped in an `input` string key:

```python
# WRONG - missing input wrapper
arguments = {}
arguments = {"flow_id": "abc123", "step_id": "def456"}

# CORRECT - wrap as JSON string in input key
arguments = {"input": "{}"}                                      # zero-param tool
arguments = {"input": '{"flow_id": "abc123", "step_id": "def456"}'}  # tool with params
```

In MCP JSON-RPC:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "list_integrations",
    "arguments": {"input": "{}"}
  },
  "id": 2
}
```

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "list_step_errors",
    "arguments": {"input": "{\"flow_id\": \"abc123\", \"step_id\": \"def456\"}"}
  },
  "id": 3
}
```

### Fix 2: Replace `fetch()` with `this.helpers.httpRequest()` in toolCode

```javascript
// WRONG — fetch not available in NodeVM sandbox
const resp = await fetch(url, { headers: { Authorization: 'Bearer KEY' } });
if (!resp.ok) return JSON.stringify({ error: `HTTP ${resp.status}` });
return JSON.stringify(await resp.json());

// CORRECT — use n8n helpers API
try {
  const data = await this.helpers.httpRequest({
    method: 'GET',
    url: url,
    headers: { Authorization: 'Bearer KEY' },
  });
  return JSON.stringify(data);
} catch (e) {
  return JSON.stringify({ error: e.message });
}
```

`this.helpers.httpRequest(options)` returns parsed JSON body directly. Errors throw exceptions.

### Complete Working toolCode Template

```javascript
// Access query variable (the input string passed as arguments.input)
const params = JSON.parse(query || '{}');
const myId = params.my_param;

if (!myId) {
  return JSON.stringify({ error: 'Required: {"my_param": "<value>"}' });
}

try {
  const data = await this.helpers.httpRequest({
    method: 'GET',
    url: `https://api.example.com/v1/items/${myId}`,
    headers: { Authorization: 'Bearer API_KEY' },
  });
  return JSON.stringify(data);
} catch (e) {
  return JSON.stringify({ error: e.message });
}
```

### Python Test Script Pattern (SSE + Bearer JWT)

```python
import threading, queue, urllib.request, json, time

session_id = None
responses = queue.Queue()

def sse_listener():
    global session_id
    req = urllib.request.Request(SSE_URL,
        headers={"X-N8N-API-KEY": API_KEY, "Accept": "text/event-stream"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        for chunk in resp:
            line = chunk.decode("utf-8").rstrip()
            if line.startswith("data:") and "sessionId=" in line:
                session_id = line.split("sessionId=")[-1].strip()
            else:
                try: responses.put(json.loads(line[5:].strip()))
                except: pass

t = threading.Thread(target=sse_listener, daemon=True)
t.start()
time.sleep(2)  # wait for session

def call_tool(name, args_dict, msg_id):
    """args_dict is the structured input; wrapped as {input: json-string}"""
    body = json.dumps({"jsonrpc":"2.0","method":"tools/call","params":{
        "name": name,
        "arguments": {"input": json.dumps(args_dict)}
    },"id": msg_id}).encode()
    req = urllib.request.Request(
        f"{N8N}/mcp/{PATH}/messages?sessionId={session_id}",
        data=body,
        headers={
            "Authorization": f"Bearer {MCP_JWT}",   # NOT X-N8N-API-KEY
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
    )
    urllib.request.urlopen(req, timeout=15)
    return responses.get(timeout=30)
```

**Auth note**: SSE endpoint uses `X-N8N-API-KEY`; messages endpoint uses `Authorization: Bearer <MCP_JWT>` (separate JWT for MCP server API, distinct from the public API key).

## Why This Works

1. `getConnectedTools(ctx, true)` always converts N8nTool → DynamicTool. The `asDynamicTool()` method wraps the structured tool with a string-parsing wrapper (`wrappedFunc`) that accepts a JSON string and parses it into the structured args. So passing `{input: "{}"}` works end-to-end.

2. For zero-param toolHttpRequest: after `asDynamicTool()` converts it, the inner `configureToolFunction` still has the `if (!toolParameters.length) { query = '{}'; }` shortcut — it ignores the input string and makes the HTTP call directly.

3. `this.helpers` is available in toolCode's `JavaScriptSandbox` because the sandbox is created as `new JavaScriptSandbox(context, code, ctx.helpers)` and the `Sandbox` base class exposes `helpers` via `this`. The `query` variable is injected via `context.query = query` into the NodeVM sandbox context.

## Prevention

- **Always call n8n MCP tools with `arguments: {"input": "<json-string>"}`** — never pass structured args directly.
- **In toolCode JavaScript, never use `fetch()`** — use `this.helpers.httpRequest({method, url, headers})`.
- **`query` in toolCode** is the raw input string. Parse it with `JSON.parse(query || '{}')`. If `query` is undefined (wrong calling convention), code crashes with "query is not defined".
- **Keep SSE connection alive** during tool calls — session expires if SSE closes. Use a background thread.
- **Messages endpoint needs `Authorization: Bearer <MCP_JWT>`** (not the API key) — different JWT audience (`mcp-server-api` vs `public-api`).

## Related Issues

- [mcp-tools-not-exposed-n8n-MCP-20260308.md](./mcp-tools-not-exposed-n8n-MCP-20260308.md) — prerequisite: fix architecture and header config before addressing calling convention
