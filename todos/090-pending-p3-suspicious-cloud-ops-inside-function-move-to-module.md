---
status: pending
priority: p3
issue_id: "090"
tags: [code-review, quality, azure-ad]
dependencies: []
---

# 090 — `SUSPICIOUS_CLOUD_OPS` set defined inside `_triage_one` function body

## Problem Statement

`SUSPICIOUS_CLOUD_OPS` is a constant set of suspicious cloud operation names used in `_triage_one`. It is defined inside the function body, which means it is re-created on every call. Constants should be at module scope to avoid unnecessary allocation and to be accessible for testing.

## Findings

- **server.py lines 2235-2236** (approximately): `SUSPICIOUS_CLOUD_OPS = {...)` defined inside `_triage_one`
- Set is re-created on every invocation of `_triage_one`
- Module-level placement would allow direct testing of the set's contents
- Flagged by: code-simplicity-reviewer, architecture-strategist

## Proposed Solutions

### Option A: Move to module scope (Recommended)
Hoist `SUSPICIOUS_CLOUD_OPS` to module level, near other module-level constants like `PHISHING_SUBJECTS` and `VALID_MAIL_FOLDERS`.
- **Effort**: Trivial | **Risk**: None

## Acceptance Criteria
- [ ] `SUSPICIOUS_CLOUD_OPS` is defined at module level, not inside `_triage_one`
- [ ] No functional change to how it is used

## Work Log
- 2026-04-08: Identified in 6th code review pass (code-simplicity-reviewer, architecture-strategist)
