---
status: pending
priority: p3
issue_id: "112"
tags: [code-review, quality, azure-ad]
dependencies: []
---

# 112 — `audit_m365_sync.py` simplicity batch: dead logic, single-element set, redundant guard, dead len-check

## Problem Statement

Four expression-level dead-logic issues in `audit_m365_sync.py` identified in the simplicity review:

1. **Line 246** — `local_prefix = email.split("@")[0] + "@"` — appends `"@"` to a local-part variable, but `MIMECAST_INTERNAL_PREFIXES = ("api-", "ingest_")` never starts with `@`. The `+ "@"` is dead noise.
2. **Line 1026** — `f["severity"] in {"HIGH"}` — single-element set membership is identical to `==`. Should be `f["severity"] == "HIGH"`.
3. **Lines 1070-1074** — `svc_prefixes` guard uses `args.svc_prefixes and args.svc_prefixes.strip()` — the second `.strip()` call is redundant since the comprehension's own `if p.strip()` already handles whitespace-only entries.
4. **Lines 102, 113** — `if len(cmd) > 1 else "unknown"` guards in `run_cli` error paths — `cmd` is always called with 2+ elements; these dead branches add noise to error paths.

## Findings

- All four from code-simplicity-reviewer (7th review pass)
- Expression-level — no structural changes needed

## Proposed Solutions

### Option A: Fix all four in a single pass

```python
# 1. Line 246:
local = email.split("@")[0]
# remove + "@"

# 2. Line 1026:
f["severity"] == "HIGH"

# 3. Lines 1070-1072:
if args.svc_prefixes  # remove .strip() from condition

# 4. Lines 102, 113:
# remove if len(cmd) > 1 else "unknown" dead branches
```

- **Effort**: Trivial | **Risk**: None

## Acceptance Criteria

- [ ] `local_prefix` does not append `"@"` to local-part string
- [ ] `in {"HIGH"}` replaced with `== "HIGH"`
- [ ] `svc_prefixes` guard simplified to single truthiness check
- [ ] Dead `else "unknown"` branches removed from `run_cli`

## Work Log

- 2026-04-08: Identified in 7th code review pass (code-simplicity-reviewer)
