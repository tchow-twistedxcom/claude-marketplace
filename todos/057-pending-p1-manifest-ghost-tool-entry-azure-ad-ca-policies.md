---
status: pending
priority: p1
issue_id: "057"
tags: [code-review, architecture, azure-ad]
dependencies: []
---

# 057 — `manifest.json` ghost tool entry `azure_ad_ca_policies` breaks published API contract

## Problem Statement

`extensions/azure-ad/manifest.json` declares a tool named `azure_ad_ca_policies` (line 81). The actual server.py function is named `azure_ad_list_ca_policies` (line 1220). This is a stale entry from when `azure_ad_ca_policies` was the duplicate tool that was removed in todo 034. The manifest now describes a tool the server cannot fulfill, breaking the DXT published API contract.

Any MCP client (Claude Desktop) that discovers tools via the manifest and calls `azure_ad_ca_policies` will receive a tool-not-found error. The DXT was rebuilt in todo 040 — the manifest ghost entry was packaged into the new DXT binary.

## Findings

- `manifest.json` line 81: `{ "name": "azure_ad_ca_policies", "description": "List Conditional Access policies" }`
- `server.py` line 1220: `async def azure_ad_list_ca_policies(...)` — the correct function name
- `server.py` search: no function named `azure_ad_ca_policies` exists
- The DXT already contains this stale manifest (needs rebuild after fix)

## Proposed Solutions

Option A (Recommended): Update `manifest.json` line 81 to use the correct tool name:
```json
{ "name": "azure_ad_list_ca_policies", "description": "List all Conditional Access policies with state and conditions summary" }
```
Then rebuild the DXT: `cd extensions/azure-ad && zip -r ../azure-ad.dxt manifest.json pyproject.toml uv.lock src/ -x "src/__pycache__/*"`
- Effort: Trivial. Risk: Low.

## Acceptance Criteria

- [ ] `manifest.json` has `azure_ad_list_ca_policies` (not `azure_ad_ca_policies`)
- [ ] DXT rebuilt from updated manifest
- [ ] `unzip -p extensions/azure-ad.dxt manifest.json | python3 -c "import json,sys; tools=json.load(sys.stdin)['tools']; print([t['name'] for t in tools if 'ca_policies' in t['name']])"` shows `['azure_ad_list_ca_policies']`

## Work Log

- 2026-04-08: Found by architecture-strategist in 4th review pass. Previously removed the duplicate function but forgot to update the manifest.
