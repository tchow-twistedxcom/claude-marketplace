---
status: pending
priority: p3
issue_id: "111"
tags: [code-review, quality, azure-ad]
dependencies: []
---

# 111 — `server.py` lines 61-64: three `NOTE: must match auth.py` comments point to non-existent file

## Problem Statement

`server.py` lines 61-64 have three comments reading `# NOTE: This value must match the corresponding constant in auth.py`. However, `auth.py` does not exist anywhere in `extensions/azure-ad/src/`. The dual-constants issue (GRAPH_BASE, GRAPH_SCOPE, TOKEN_REFRESH_BUFFER) was documented in todo 077 and the comments were added as a minimal fix — but they reference a file (`auth.py`) that was never created in that location. These comments are now misleading maintenance noise pointing to a ghost file.

## Findings

- **`extensions/azure-ad/src/server.py` lines 61-64**: three `# NOTE: ... auth.py` comments
- `extensions/azure-ad/src/auth.py` does not exist (the `auth.py` with atomic write is in `plugins/m365-skills/skills/azure-ad/scripts/`, a different module)
- These comments were added by todo 077 fix but reference the wrong path/file
- Flagged by: code-simplicity-reviewer (7th review pass)

## Proposed Solutions

### Option A: Remove or correct the comments

Either remove the comments entirely (since the constants are self-explanatory) or update to reference the correct file:
```python
# NOTE: Keep in sync with TOKEN_REFRESH_BUFFER in scripts/auth.py (auth cache module)
```

But since the constants are not actually shared between the two files, the cleanest fix is to remove the comments and leave the constants as-is.

- **Effort**: Trivial | **Risk**: None

## Acceptance Criteria

- [ ] Comments on lines 61-64 of `server.py` no longer reference a non-existent `auth.py` in `extensions/azure-ad/src/`

## Work Log

- 2026-04-08: Identified in 7th code review pass (code-simplicity-reviewer) — stale comments from 077 fix
