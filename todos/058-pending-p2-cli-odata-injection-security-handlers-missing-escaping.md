---
status: pending
priority: p2
issue_id: "058"
tags: [code-review, security, azure-ad]
dependencies: []
---

# 058 — CLI OData injection — security command handlers missing quote-escaping

## Problem Statement
`azure_ad_api.py` security command handlers (`handle_security`) interpolate CLI args `--user`, `--ip`, `--app`, `--country`, `--category` directly into OData filter strings without quote-escaping. The `--since` parameter is also interpolated without ISO 8601 validation. This is inconsistent with `users_search`, `groups_search`, and `devices_search` in the same file which correctly apply `.replace("'", "''")`. IPs extracted from external Graph API risk-event responses in `sweep.py` are also used unvalidated in OData filters.

## Findings
- `azure_ad_api.py` line 852: `filter_parts.append(f"userPrincipalName eq '{args.user}'")`  — no `.replace("'", "''")`
- `azure_ad_api.py` line 854: `filter_parts.append(f"ipAddress eq '{args.ip}'")`  — no validation
- `azure_ad_api.py` line 856: `filter_parts.append(f"appDisplayName eq '{args.app}'")`  — no `.replace`
- `azure_ad_api.py` line 860: `filter_parts.append(f"location/countryOrRegion eq '{args.country}'")`  — no escaping
- `azure_ad_api.py` line 54: `return f"{field} ge {since}"` — raw ISO string, no format validation
- `sweep.py` line 61: `f = f"ipAddress eq '{ip}'"` — IP from Graph API response, no validation
- Contrast with `azure_ad_api.py` lines 226, 418: `query.replace("'", "''")` is applied correctly in users_search, devices_search

## Proposed Solutions
Option A (Recommended):
1. Apply `.replace("'", "''")` to `args.user`, `args.app`, `args.country`, `args.category` before interpolation
2. For `args.ip`: validate against IP regex pattern `re.match(r'^[\d.:/\[\]a-fA-F]+$', ip)` before use
3. For `--since`: validate with `re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', since)` before interpolation
4. For `sweep.py` IPs from API responses: validate with same IP pattern before filter construction
- Effort: Small. Risk: Low.

## Acceptance Criteria
- [ ] `--user`, `--app`, `--country`, `--category` values quote-escaped before OData interpolation in `handle_security`
- [ ] `--ip` values validated against IP format pattern
- [ ] `--since` value validated as ISO 8601 datetime pattern
- [ ] `sweep.py` IPs from Graph API risk events validated before OData filter construction

## Work Log
- 2026-04-08: Found by security-sentinel in 4th review pass
