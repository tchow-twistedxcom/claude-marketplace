---
status: complete
priority: p1
issue_id: "077"
tags: [code-review, security, azure-ad, ual]
dependencies: []
---

# 077 — `azure_ad_ual_sharepoint`: "Audit.SharePoint" not in VALID_UAL_CONTENT_TYPES → silent empty results

## Problem Statement

`azure_ad_ual_sharepoint` calls `_ual_fetch_blobs("Audit.SharePoint", ...)` but `VALID_UAL_CONTENT_TYPES` at server.py line 104 only contains `{"Audit.Exchange", "Audit.AzureActiveDirectory", "Audit.General"}`. The function raises `ValueError: Invalid content_type 'Audit.SharePoint'`, which is caught by `asyncio.gather(return_exceptions=True)` at line 1855 — silently producing `sp_events = []` on every call. An analyst investigating file exfiltration receives no SharePoint audit data with no warning.

## Findings

- **server.py line 104**: `VALID_UAL_CONTENT_TYPES = {"Audit.Exchange", "Audit.AzureActiveDirectory", "Audit.General"}` — does NOT include `"Audit.SharePoint"`
- **server.py line 1856**: `_ual_fetch_blobs("Audit.SharePoint", start, end)` → always raises ValueError
- **server.py lines 1860-1861**: `sp_result = results[1]` receives the exception object; `isinstance(sp_result, tuple)` is False → `sp_events = []` always
- **`ualDataIncomplete` flag**: Not set in this code path — the gap is invisible in returned results
- Confirmed by: performance-oracle, architecture-strategist, kieran-python-reviewer, security-sentinel, agent-native-reviewer (5/5 agents flagged this)

## Proposed Solutions

### Option A: Add "Audit.SharePoint" to VALID_UAL_CONTENT_TYPES (Recommended)
- If the Office 365 Management Activity API supports "Audit.SharePoint" as a valid content type, add it to the allowlist
- Also surface a warning in the return dict when either fetch fails: `"sharepointFetchError": "..."`
- **Effort**: Small | **Risk**: Low

### Option B: Replace "Audit.SharePoint" with "Audit.General"
- SharePoint events may be accessible under "Audit.General" — use that content type instead
- Renames intent in docstring to match actual behavior
- **Effort**: Small | **Risk**: Low

### Option C: Add error surfacing without changing allowlist
- Catch the ValueError explicitly, set `ualDataIncomplete = True` and add `"sharepointFetchError"` to the return
- **Effort**: Small | **Risk**: Low (but doesn't fix the actual data gap)

## Acceptance Criteria
- [ ] `azure_ad_ual_sharepoint` returns non-empty SharePoint events when SharePoint activity exists
- [ ] If "Audit.SharePoint" fetch fails for any reason, `ualDataIncomplete: true` is set in the response
- [ ] Tool tested against a real O365 tenant or confirmed against Microsoft's UAL content type docs

## Work Log
- 2026-04-08: Identified in 6th code review pass (5 agents independently flagged)
- 2026-04-08: Fixed — added "Audit.SharePoint" to VALID_UAL_CONTENT_TYPES; updated azure_ad_ual_sharepoint to properly unpack (events, incomplete) from both fetches and OR the incomplete flags into ualDataIncomplete in return dict. Commit: fix(azure-ad): resolve 6th review todos 077-098a in server.py
