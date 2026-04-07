---
status: pending
priority: p2
issue_id: "028"
tags: [code-review, bug, audit, mimecast]
dependencies: []
---

# 028 — SEVERITY_ICON dict lowercase "error" key — error-severity findings show "•" in report

## Problem Statement

`audit_m365_sync.py` defines `SEVERITY_ICON` with a lowercase `"error"` key, but `analyze_config()` assigns `severity: "error"` to findings when config operations fail. The markdown report looks up `SEVERITY_ICON.get(f["severity"], "•")` — since `"error"` is lowercase and the dict has only uppercase keys (`"HIGH"`, `"MEDIUM"`, etc.), the `.get()` falls through to the default `"•"` bullet. Error-severity config findings are displayed without the `"❌"` icon, visually indistinguishable from regular findings.

## Findings

- **File**: `plugins/mimecast-skills/scripts/audit_m365_sync.py`, lines 766-773 — `SEVERITY_ICON` dict
- **File**: `audit_m365_sync.py`, line 481 — `analyze_config()` assigns `"severity": "error"`
- **Agent**: pattern-recognition-specialist (HIGH bug)

```python
SEVERITY_ICON = {
    "HIGH": "🔴",
    "MEDIUM": "🟡",
    "LOW": "🔵",
    "OK": "✅",
    "INFO": "ℹ️",
    "error": "❌",    # lowercase — never matched by .get(f["severity"], "•")
}
```

## Proposed Solutions

### Option A: Uppercase the "error" key (Recommended)
Change `"error": "❌"` to `"ERROR": "❌"` and update `analyze_config()` to use `"ERROR"` instead of `"error"`.

### Option B: Normalize severity to uppercase at lookup time
`SEVERITY_ICON.get(f["severity"].upper(), "•")`

## Recommended Action

Option A — fix at the source. Two-line change.

## Acceptance Criteria

- [ ] `SEVERITY_ICON` has no lowercase keys; all keys match the uppercase severity values used throughout
- [ ] Error-severity config findings display `"❌"` in the generated markdown report

## Work Log

- 2026-04-07: Identified by pattern-recognition-specialist and code-simplicity-reviewer
