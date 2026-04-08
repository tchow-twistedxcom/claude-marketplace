---
status: pending
priority: p3
issue_id: "093"
tags: [code-review, documentation, azure-ad]
dependencies: []
---

# 093 — SKILL.md line 244 says "47 operations" — stale, should be 49

## Problem Statement

`plugins/m365-skills/skills/azure-ad/SKILL.md` line 244 says "Cover all 47 operations" but there are 49 MCP tools (line 202 of the same file correctly says "49 Agent-Native Tools"). The inconsistency creates confusion about whether MCP and CLI have the same coverage.

## Findings

- **SKILL.md line 244**: "Cover all 47 operations" — stale from before new tools were added
- **SKILL.md line 202**: "49 Agent-Native Tools" — correct
- 2 new tools added in this PR: `azure_ad_delete_inbox_rule`, `azure_ad_dismiss_risky_users`
- Flagged by: pattern-recognition-specialist, agent-native-reviewer

## Proposed Solutions

### Option A: Update the count
Change line 244 from "47" to "49"
- **Effort**: Trivial | **Risk**: None

## Acceptance Criteria
- [ ] All references to operation/tool count in SKILL.md are consistent (49)
- [ ] No other stale counts in SKILL.md

## Work Log
- 2026-04-08: Identified in 6th code review pass (pattern-recognition-specialist, agent-native-reviewer)
