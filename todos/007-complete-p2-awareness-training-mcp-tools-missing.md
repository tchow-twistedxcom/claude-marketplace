---
status: complete
priority: p2
issue_id: "007"
tags: [code-review, agent-native, mimecast, mcp-tools]
dependencies: []
---

# 007 — 8 of 12 awareness training CLI operations have no MCP tool

## Problem Statement

PR #3 adds 12 awareness training CLI operations, but only 4 have corresponding MCP tools:

| CLI Command | MCP Tool | Has MCP? |
|---|---|---|
| `awareness campaigns` | `mimecast_list_campaigns` | ✅ |
| `awareness safe-score` | `mimecast_get_safe_scores` | ✅ |
| `awareness phishing` | `mimecast_get_phishing_results` | ✅ |
| `awareness watchlist` | `mimecast_get_watchlist` | ✅ |
| `awareness campaign-users` | — | ❌ |
| `awareness performance` | — | ❌ |
| `awareness performance-summary` | — | ❌ |
| `awareness phishing-users` | — | ❌ |
| `awareness safe-score-summary` | — | ❌ |
| `awareness queue` | — | ❌ |
| `awareness training-details` | — | ❌ |
| `awareness watchlist-summary` | — | ❌ |

Agents using the MCP server cannot access 8 of the 12 new endpoints without falling back to CLI subprocess calls. This breaks agent parity.

## Findings

- **Agent**: agent-native-reviewer (Critical in their ranking, P2 overall)
- **Files**: `extensions/mimecast/src/server.py`

## Proposed Solutions

### Option A: Add all 8 missing MCP tools to server.py

Add `@mcp.tool()` functions for each missing awareness operation, following the pattern of the 4 existing ones.

- **Pros**: Full agent parity; consistent with plan Phase 1 goal
- **Cons**: 8 more functions to maintain
- **Effort**: Medium
- **Risk**: Very low

### Option B: Add a generic awareness training tool
Single tool with `action` parameter:

```python
@mcp.tool(name="mimecast_awareness")
async def mimecast_awareness(action: str, **kwargs) -> str: ...
```

- **Pros**: One function, flexible
- **Cons**: Poor discoverability; agents need to know valid `action` values; defeats MCP's semantic tool design
- **Effort**: Small
- **Risk**: Low

### Recommended
**Option A** — add all 8 individual tools. MCP tools should be semantically distinct for best agent usability.

## Technical Details

- **Affected files**: `extensions/mimecast/src/server.py`, `extensions/mimecast/manifest.json` (also fixes todo #001)

Missing tools to implement:
1. `mimecast_get_campaign_users(campaign_id?)` → `awareness campaign-users`
2. `mimecast_get_performance()` → `awareness performance`
3. `mimecast_get_performance_summary()` → `awareness performance-summary`
4. `mimecast_get_phishing_user_data(campaign_id?)` → `awareness phishing-users`
5. `mimecast_get_safe_score_summary()` → `awareness safe-score-summary`
6. `mimecast_get_training_queue()` → `awareness queue`
7. `mimecast_get_training_details(email?)` → `awareness training-details`
8. `mimecast_get_watchlist_summary()` → `awareness watchlist-summary`

## Acceptance Criteria

- [ ] All 12 awareness training operations accessible via MCP tools
- [ ] New tools listed in `manifest.json` (resolves overlap with todo #001)
- [ ] `readOnlyHint: True` set on all new tools (all are read-only)
- [ ] Each tool has a helpful docstring describing what it returns

## Work Log

- 2026-04-04: Created by code review (agent-native-reviewer finding)
