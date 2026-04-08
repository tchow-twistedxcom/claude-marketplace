---
status: complete
priority: p3
issue_id: "089"
tags: [code-review, quality, azure-ad]
dependencies: []
---

# 089 — Dead `else` branch in `_triage_one` re-initializes already-initialized variables

## Problem Statement

Inside `_triage_one`, after `if not triage_results:` (lines 2253-2254), there is an `else:` block that re-assigns `cloud_events = []` and `cloud_suspicious = []`. These variables are already initialized to `[]` earlier in the function. The else branch is dead code that adds confusion about whether the variables hold meaningful state.

## Findings

- **server.py lines 2255-2256** (approximately): `else:` block following `if not triage_results:` that re-initializes `cloud_events = []` and `cloud_suspicious = []`
- Variables were already initialized to `[]` at the top of the function body
- Re-initialization in else branch is a no-op that implies conditional logic where there is none
- Flagged by: code-simplicity-reviewer

## Proposed Solutions

### Option A: Remove the dead else branch
Delete the `else:` and its body. The variables keep their initialized values.
- **Effort**: Trivial | **Risk**: None

## Acceptance Criteria
- [ ] Dead else branch removed from `_triage_one`
- [ ] `cloud_events` and `cloud_suspicious` are only initialized once

## Work Log
- 2026-04-08: Identified in 6th code review pass (code-simplicity-reviewer)
- 2026-04-08: Fixed — removed dead else: branch in _triage_one that re-assigned cloud_events=[] and cloud_suspicious=[] (already initialized above the if block). Commit: fix(azure-ad): resolve 6th review todos 077-098a in server.py
