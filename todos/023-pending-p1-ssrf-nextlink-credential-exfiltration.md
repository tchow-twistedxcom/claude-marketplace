---
status: pending
priority: p1
issue_id: "023"
tags: [code-review, security, ssrf, azure-ad]
dependencies: []
---

# 023 — SSRF via unvalidated @odata.nextLink — Bearer token exfiltration vector

## Problem Statement

In `azure_ad_api.py`, `_get_all_pages()` follows `@odata.nextLink` URLs from API response bodies by passing them directly to `requests.get()` — including the Bearer token in `get_auth_headers()`. If an `@odata.nextLink` URL in a Graph response is tampered with (compromised network, DNS hijack, misconfigured proxy, or a compromised middleware), the token would be sent to an arbitrary host.

## Findings

- **File**: `plugins/m365-skills/skills/azure-ad/scripts/azure_ad_api.py`, lines 144-163
- **Agent**: security-sentinel (HIGH)

```python
while endpoint and page_count < max_pages:
    if endpoint.startswith('http'):
        # Handle @odata.nextLink URLs
        response = requests.get(
            endpoint,                              # UNVALIDATED URL from response body
            headers=self.auth.get_auth_headers(),  # Bearer token sent to arbitrary host
            timeout=self.config.get('defaults', {}).get('timeout', 30)
        )
```

Additionally, the error handling in this branch does not go through `_request()`'s `GraphAPIError` wrapping — HTTP errors on next-page links raise raw `requests.exceptions.HTTPError`.

## Proposed Solutions

### Option A: Validate nextLink prefix (Recommended)
```python
GRAPH_BASE = "https://graph.microsoft.com/"
if endpoint.startswith('http'):
    if not endpoint.startswith(GRAPH_BASE):
        raise ValueError(f"Unexpected nextLink host (possible SSRF): {endpoint[:100]}")
    response = requests.get(endpoint, headers=self.auth.get_auth_headers(), ...)
```

### Option B: Route nextLink through _request()
Extract the path from the full URL and call `self._request()` instead of `requests.get` directly. This also fixes the error handling gap.

### Option C: Accept risk (admin tool)
This tool runs as a local CLI with controlled credentials. In practice the risk requires active MitM. Document as accepted risk.

## Recommended Action

Option A — one-line prefix check. Takes 2 minutes, eliminates the SSRF vector entirely.

## Acceptance Criteria

- [ ] `_get_all_pages` validates nextLink URLs start with `https://graph.microsoft.com/` before following
- [ ] HTTP errors on next-page links are caught and raised as `GraphAPIError` (or at least not silently dropped)

## Work Log

- 2026-04-07: Identified by security-sentinel as H2 (HIGH)
