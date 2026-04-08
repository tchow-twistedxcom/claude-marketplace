---
status: pending
priority: p2
issue_id: "047"
tags: [code-review, quality, azure-ad, mimecast]
dependencies: []
---

# 047 — `_mc_data()` helper missing and `_get_all_pages` error handling duplicated

## Problem Statement

Two code duplication issues identified in `audit_m365_sync.py` and `server.py`. The `_extract_graph_list()` cleanup from todo 034 was applied to the fetch functions it targeted but the same pattern still appears in other locations. The `_get_all_pages` error handling pattern is independently copy-pasted in multiple places.

## Findings

### 1. `_mc_data()` helper missing (`audit_m365_sync.py`)

Seven repeated occurrences of the `isinstance(data, dict) and "value" in data` pattern remain in `audit_m365_sync.py`. The `_extract_graph_list()` cleanup from todo 034 addressed the 3 fetch functions it targeted, but additional occurrences were introduced or left untouched elsewhere in the file. A single `_mc_data(response) -> list` helper would replace all remaining occurrences and prevent future drift.

### 2. `_get_all_pages` error handling duplicated (`server.py`)

The `_get_all_pages` function's try/except pattern for handling paginated Graph API responses is copy-pasted in 3+ locations in `server.py`. Each copy handles `@odata.nextLink` traversal and error catching independently. Should be consolidated into the existing `_get_all_pages` function (applying DRY).

## Proposed Solutions

### Option A — Add `_mc_data()` helper and consolidate `_get_all_pages` (Recommended)

- Add `def _mc_data(response: dict | list) -> list: return response.get("value", []) if isinstance(response, dict) else (response if isinstance(response, list) else [])` to `audit_m365_sync.py` and replace all 7 occurrences.
- Consolidate `_get_all_pages` error handling into the existing function so callers use it without re-implementing the try/except.
- Effort: Small, Risk: Low

## Acceptance Criteria

- [ ] `_mc_data()` helper exists in audit_m365_sync.py and replaces all 7 `isinstance(data, dict) and "value" in data` patterns
- [ ] `_get_all_pages` error handling is not duplicated across server.py

## Work Log

- 2026-04-08: Identified in 3rd review pass
