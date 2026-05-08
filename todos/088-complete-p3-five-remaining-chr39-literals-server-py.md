---
status: complete
priority: p3
issue_id: "088"
tags: [code-review, quality, azure-ad]
dependencies: []
---

# 088 — 5 remaining `chr(39)` literals in server.py missed by previous pass

## Problem Statement

A previous review pass replaced many `chr(39)` (apostrophe workarounds) with direct `'` quotes. However 5 occurrences were missed: lines 619, 625, 680, 763, 765. These are minor readability issues.

## Findings

- **server.py lines 619, 625, 680, 763, 765**: `chr(39)` still used instead of literal `'`
- Previous pass (todo 074) caught other instances but missed these 5
- Flagged by: code-simplicity-reviewer

## Proposed Solutions

### Option A: Replace all remaining chr(39) occurrences
Simple search-and-replace: `chr(39)` → `"'"` or restructure the f-string to use `'` quotes
- **Effort**: Trivial | **Risk**: None

## Acceptance Criteria
- [ ] Zero `chr(39)` occurrences remain in server.py
- [ ] Grep confirms: `grep -n "chr(39)" server.py` returns no results

## Work Log
- 2026-04-08: Identified in 6th code review pass (code-simplicity-reviewer)
- 2026-04-08: Fixed — replaced all 5 chr(39) occurrences in sign_ins, risk_detections, and audit_logs filters with string concatenation using literal apostrophes. grep confirms clean. Commit: fix(azure-ad): resolve 6th review todos 077-098a in server.py
