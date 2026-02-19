---
module: Celigo Integration
date: 2026-02-19
problem_type: integration_issue
component: tooling
symptoms:
  - "Flow name cleared to empty string after PUT update with partial payload"
  - "pageGenerators and pageProcessors removed from flow after partial PUT"
  - "PUT /flows/{id} with only {description: 'new'} wiped all other fields"
root_cause: wrong_api
resolution_type: code_fix
severity: critical
tags: [celigo, put-api, full-replace, data-loss, integrator-io]
---

# Troubleshooting: Celigo PUT API Destroys Data with Partial Payloads

## Problem
Celigo's REST API `PUT` endpoints perform a **full object replacement**, not a partial/merge update. Sending a partial payload (e.g., just `{"description": "new"}`) silently clears all omitted fields, destroying flow configuration including name, exports, and imports.

## Environment
- Module: Celigo Integration CLI (`celigo_api.py`)
- API: Celigo integrator.io REST API v1
- Affected Endpoints: `PUT /flows/{id}`, `PUT /exports/{id}`, `PUT /imports/{id}`
- Date: 2026-02-19

## Symptoms
- Flow name set to empty string `""` after updating only the description field
- `pageGenerators` array removed from flow (exports disconnected)
- `pageProcessors` array removed from flow (imports disconnected)
- Flow appeared to "break" — no visible exports or imports in Celigo UI

## What Didn't Work

**Attempted Solution 1:** Direct partial PUT (like a PATCH)
- Sent `PUT /flows/{id}` with `{"description": "new text"}` only
- **Why it failed:** Celigo PUT replaces the entire object. Omitted fields are reset to defaults/empty, not preserved. This is standard REST semantics but unexpected when other APIs (like some SaaS platforms) treat PUT as merge.

## Solution

Implemented a **fetch-merge-PUT** pattern: always GET the current object, merge changes on top, then PUT the full object back.

**Code changes:**

```python
# Before (broken - partial PUT destroys data):
def update(args):
    data = resolve_input(args)
    result = api.update(args.id, data)  # Only sends changed fields

# After (fixed - fetch-merge-PUT preserves all fields):
def update(args):
    updates = resolve_input(args)
    # Fetch current state first
    current = api.get(args.id)
    if current.get("error"):
        print_result(current, args.format)
        return
    # Remove read-only fields before merge
    for key in ("_id", "lastModified", "createdAt", "lastExecutedAt"):
        current.pop(key, None)
    # Merge updates on top of current state
    current.update(updates)
    result = api.update(args.id, current)
```

**File:** `plugins/celigo-integration/scripts/celigo_api.py` (lines 877-892)

## Why This Works

1. **Root cause:** Celigo's REST API follows strict PUT semantics where the request body represents the complete desired state of the resource. Any field not included in the payload is treated as "should be empty/default."
2. **The fix** ensures all existing fields are preserved by fetching the current state, then overlaying only the changed fields before sending the full object back.
3. Read-only fields (`_id`, `lastModified`, `createdAt`, `lastExecutedAt`) must be stripped before PUT or the API may reject them.

## Prevention

- **Always use fetch-merge-PUT** when updating any Celigo resource (flows, exports, imports, connections)
- **Never send partial payloads** to Celigo PUT endpoints
- **Test updates on non-production objects first** — a partial PUT can silently destroy configuration
- **Same pattern applies to exports and imports** — discovered this applies to `PUT /exports/{id}` and `PUT /imports/{id}` as well
- When building CLI tools for APIs, always verify whether PUT is full-replace or merge before implementing update commands

## Related Issues

- See also: [ai-agent-response-mapping-CeligoIntegration-20260219.md](./ai-agent-response-mapping-CeligoIntegration-20260219.md) - Discovered during the same debugging session
