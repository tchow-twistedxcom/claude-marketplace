---
status: complete
priority: p1
issue_id: "001"
tags: [code-review, agent-native, mimecast, dxt]
dependencies: []
---

# 001 — manifest.json stale: 10 new MCP tools not listed

## Problem Statement

The DXT extension manifest at `extensions/mimecast/manifest.json` has not been updated to include the 10 new MCP tools added in PR #3. The `tools` array still lists the original 10 tools from v1.0.0. Users who install the Mimecast DXT extension will see a stale tool list that omits all 4 new awareness training tools plus the 6 security tools added in Phase 0.

This is a **distribution bug**: anyone installing via the `.dxt` file gets an incomplete extension.

## Findings

- **File**: `extensions/mimecast/manifest.json` — `tools` array
- **Agent**: agent-native-reviewer (P1 — BLOCKS MERGE)
- **Evidence**: The `tools` array in the manifest documents which tools the extension exposes. All new tools added in Phase 0 (6 security tools) and Phase 1 (4 awareness training tools) are absent.

New tools that must be added to `manifest.json`:
- Phase 0 additions (from server.py): check which 6 were added
- Phase 1 additions: `mimecast_list_campaigns`, `mimecast_get_safe_scores`, `mimecast_get_phishing_results`, `mimecast_get_watchlist`

## Proposed Solutions

### Option A: Update manifest.json tools array manually
Add entries for each missing tool following the existing format in the tools array.

- **Pros**: Straightforward, targeted fix
- **Cons**: Must be maintained manually on each PR
- **Effort**: Small
- **Risk**: Low

### Option B: Auto-generate manifest tools from server.py
Write a script that introspects `@mcp.tool()` decorators in `server.py` and generates the manifest tools array.

- **Pros**: Never gets out of sync
- **Cons**: Added complexity, not standard pattern in this codebase
- **Effort**: Medium
- **Risk**: Low

### Recommended
**Option A** — update manifest manually for now.

## Technical Details

- **Affected files**: `extensions/mimecast/manifest.json`
- **Pattern**: Each tool entry needs `name`, `description`, `input_schema`

## Acceptance Criteria

- [ ] All tools in `server.py` are listed in `manifest.json`
- [ ] Tool descriptions in manifest match `@mcp.tool()` docstrings
- [ ] `ast.parse()` on server.py extracts same tool count as manifest

## Work Log

- 2026-04-04: Created by code review (agent-native-reviewer finding)
