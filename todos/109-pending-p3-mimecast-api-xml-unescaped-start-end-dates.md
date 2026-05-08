---
status: pending
priority: p3
issue_id: "109"
tags: [code-review, security, mimecast-skills]
dependencies: []
---

# 109 — `mimecast_api.py` lines 452-455: `start`/`end` dates not escaped with `html.escape()` in XML

## Problem Statement

`mimecast_api.py` builds XML request bodies for message tracking queries. `sender`, `recipient`, and `subject` fields are passed through `html.escape()` before insertion. However, `start` and `end` date parameters (lines 452-455) are inserted directly without escaping. While ISO8601 date strings are unlikely to contain XML-significant characters, consistency with the other fields is a correctness requirement — and if date values are ever sourced from less-controlled inputs, unescaped `<`, `>`, or `&` characters could corrupt the XML payload.

## Findings

- **`plugins/mimecast-skills/scripts/mimecast_api.py` lines 452-455**: `start` and `end` inserted raw in XML template
- **Lines ~430-450**: `sender`, `recipient`, `subject` all correctly use `html.escape()`
- No escaping on date fields despite being part of same XML string interpolation
- Flagged by: security-sentinel (7th review pass)

## Proposed Solutions

### Option A: Apply `html.escape()` to `start` and `end` (recommended)

```python
f"<start>{html.escape(start)}</start><end>{html.escape(end)}</end>"
```

- **Effort**: Trivial | **Risk**: None (no behavior change for valid ISO8601 dates)

## Acceptance Criteria

- [ ] `start` and `end` date values wrapped in `html.escape()` in XML body construction
- [ ] Consistent escaping across all user-supplied fields in XML payloads

## Work Log

- 2026-04-08: Identified in 7th code review pass (security-sentinel) — inconsistent escaping with other fields
