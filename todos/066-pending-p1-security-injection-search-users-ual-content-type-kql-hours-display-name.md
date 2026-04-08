---
status: pending
priority: p1
issue_id: "066"
tags: [code-review, security, azure-ad]
dependencies: []
---

# 066 — Security injection bundle: search_users $search, UAL content_type, KQL hours, display_name, folder GUID

## Problem Statement

Four new injection vectors in `server.py` that were not caught by previous passes:

1. `azure_ad_search_users` interpolates `query` directly into a Graph API `$search` value without sanitization — embedded `"` can alter the predicate structure.
2. `azure_ad_ual_search` and `_ual_fetch_blobs` inject `content_type` into a URL path segment and request params without an allowlist — only 3 valid values exist.
3. `azure_ad_email_events`, `azure_ad_email_attachments`, and the `_triage_one` inner function inject `hours` as an integer directly into KQL `ago({hours}h)` with no lower/upper bound — negative or astronomical values produce silent API errors.
4. `azure_ad_create_named_location`, `azure_ad_create_ca_policy`, `azure_ad_update_ca_policy` pass `display_name` to Graph API JSON payload with no length or character validation.
5. `azure_ad_search_mail` folder GUID bypass regex `r'^[0-9a-f\-]{8,}$'` doesn't match real Graph folder IDs (which are base64url, not hex), giving false security and allowing loose values like `a-a-a-a-a-a-a-a`.

## Findings

### 1. `$search` injection — `azure_ad_search_users` (server.py ~line 299)
```python
params = {"$search": f'"displayName:{query}" OR "mail:{query}" OR "userPrincipalName:{query}"'}
```
`query = 'x" OR userPrincipalName:admin@'` yields a syntactically altered predicate. No sanitization applied despite `_validate_kql_value` existing for exactly this purpose.

### 2. UAL `content_type` injection — `_ual_fetch_blobs` / `azure_ad_ual_search` (server.py ~line 886)
```python
await _ual_request("POST", f"/subscriptions/start?contentType={content_type}", ...)
```
Valid values: `{"Audit.Exchange", "Audit.AzureActiveDirectory", "Audit.General"}`. No `VALID_UAL_CONTENT_TYPES` allowlist defined. MCP tool `azure_ad_ual_search` exposes this parameter directly to agents.

### 3. KQL `hours` no bounds — multiple KQL tools (server.py ~lines 1476, 1726, 1873, 1879)
```python
filters = [f"Timestamp >= ago({hours}h)"]
```
`hours=-1` → `ago(-1h)` (future timestamp, silent empty result). `hours=720000` → 82-year lookback, expensive server-side query. No cap analogous to `azure_ad_sent_emails` which correctly caps at 168h.

### 4. `display_name` unvalidated — CA/named location tools (server.py ~lines 1246, 1283, 1364)
No length check, no character filtering. `_validate_safe_name` already exists.

### 5. Folder GUID bypass regex — `azure_ad_search_mail` (server.py ~lines 1153–1156)
```python
if folder_safe not in VALID_MAIL_FOLDERS and not re.match(r'^[0-9a-f\-]{8,}$', folder):
```
Real Graph folder IDs are base64url (e.g. `AAMkAGI...`), not hex GUIDs. The documented GUID bypass path doesn't work as claimed and accepts loose values that Graph API will reject with confusing errors.

## Proposed Solutions

**Option A (Recommended):**
1. `azure_ad_search_users`: apply `_validate_safe_name(query)` or strip/reject `"` from query before interpolation.
2. UAL `content_type`: add `VALID_UAL_CONTENT_TYPES = {"Audit.Exchange", "Audit.AzureActiveDirectory", "Audit.General"}` and call `_validate_enum(content_type, VALID_UAL_CONTENT_TYPES, "content_type")`.
3. KQL `hours`: add `hours = max(1, min(hours, 720))` before KQL construction in `azure_ad_email_events`, `azure_ad_email_attachments`, and `_triage_one`.
4. `display_name`: add length cap `if len(display_name) > 256: raise ValueError(...)` in all three CA/named-location creation/update tools.
5. Folder GUID: replace bypass regex with RFC 4122 UUID pattern `r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'` or accept base64url IDs from Graph.
- Effort: Small. Risk: Low.

## Acceptance Criteria

- [ ] `azure_ad_search_users` rejects or sanitizes `query` values containing `"` characters
- [ ] `VALID_UAL_CONTENT_TYPES` allowlist added; `content_type` validated before use in URL/params
- [ ] `hours` capped to `[1, 720]` in `azure_ad_email_events`, `azure_ad_email_attachments`, and `_triage_one` KQL paths
- [ ] `display_name` length-capped (≤256 chars) in CA policy and named location create/update tools
- [ ] Folder GUID bypass regex tightened to RFC 4122 full UUID pattern

## Work Log

- 2026-04-08: Identified by security-sentinel in 5th review pass
