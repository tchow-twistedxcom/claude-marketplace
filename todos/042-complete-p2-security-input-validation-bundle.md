---
status: pending
priority: p2
issue_id: "042"
tags: [code-review, security, azure-ad, mimecast]
dependencies: []
---

# 042 — Security P2 bundle — folder/CIDR/content_type/UPN OData/MSAL error validation missing

## Problem Statement

Multiple medium-severity input validation gaps identified across `server.py` and `sweep.py`. None are individually critical but together they represent a meaningful attack surface for misconfigured or adversarially-supplied inputs.

## Findings

### 1. `azure_ad_search_mail` folder parameter (`server.py`)

The `folder` parameter is passed directly to the Microsoft Graph URL (`/mailFolders/{folder}/messages`) without validation. A malicious value like `../../users` could traverse into unintended Graph API paths.

### 2. `create_named_location` CIDR validation (`server.py`)

IP ranges passed to `create_named_location` are not validated as valid CIDR notation before sending to Graph API. Invalid CIDRs cause unhelpful 400 errors with no guidance to the caller.

### 3. UAL `content_type` unsanitized (`server.py`)

The `content_type` parameter in UAL search functions is interpolated into OData filters without an allowlist. Should be restricted to known values (e.g., `MicrosoftTeams`, `Exchange`, `SharePoint`, `AzureActiveDirectory`).

### 4. `sweep.py` UPN from API response in OData filter (`sweep.py`)

When building OData filters using UPNs from Azure AD API responses, `sweep.py` does not escape single quotes in the UPN values. A UPN containing `'` (valid in some tenants) breaks the filter syntax.

### 5. MSAL `error_description` leaked to caller (`server.py`)

MSAL authentication failures return the full `error_description` which may include internal tenant information (e.g., tenant ID, policy names). Should be sanitized before surfacing to the MCP caller.

## Proposed Solutions

### Option A — Fix each independently (Recommended)

- `folder`: Add allowlist of known folder names (`inbox`, `sentitems`, `drafts`, `deleteditems`) + GUID regex fallback. Reject others.
- CIDR: Add `ipaddress.ip_network(cidr, strict=False)` validation with `ValueError` catch before sending to Graph API.
- `content_type`: Add `VALID_CONTENT_TYPES = {"Exchange", "AzureActiveDirectory", "MicrosoftTeams", "SharePoint", "OneDrive"}` allowlist.
- sweep.py UPN: Apply `.replace("'", "''")` to UPN values before OData interpolation.
- MSAL error: Replace `error_description` with `error_code` only in exception messages.
- Effort: Small per item, Risk: Low

## Acceptance Criteria

- [ ] `folder` validated against allowlist before URL construction
- [ ] CIDR validated with `ipaddress` module
- [ ] `content_type` restricted to known allowlist values
- [ ] sweep.py UPN values escaped before OData interpolation
- [ ] MSAL exceptions expose error_code but not full error_description

## Work Log

- 2026-04-08: Identified in 3rd review pass
- 2026-04-08: sweep.py UPN OData escaping complete — applied safe_upn = upn.replace("'", "''") before filter interpolation in collect_mfa_fatigue_victims and collect_suspicious_audit_events. Remaining items (folder, CIDR, content_type, MSAL error) are in server.py.
