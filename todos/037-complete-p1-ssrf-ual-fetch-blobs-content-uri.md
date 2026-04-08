---
status: pending
priority: p1
issue_id: "037"
tags: [code-review, security, azure-ad]
dependencies: []
---

# 037 — SSRF via unvalidated contentUri in `_ual_fetch_blobs`

## Problem Statement

`extensions/azure-ad/src/server.py` `_ual_fetch_blobs()` (around lines 897–900) fetches blob URLs from `contentUri` fields returned by the UAL search API. These `contentUri` values are fetched without validating they point to a Microsoft-owned host. A compromised Office 365 API or MITM could return `contentUri` values pointing to internal SSRF targets (e.g., metadata endpoints, internal services). The fix added to `_get_all_pages` does not cover `_ual_fetch_blobs`.

## Findings

- `_ual_fetch_blobs()` retrieves blob container URLs from the UAL content API and then fetches each blob's content directly.
- No hostname or scheme validation is performed on `contentUri` values before the outbound HTTP request is made.
- The UAL API is an Office 365 service — a MITM or compromised tenant could return attacker-controlled `contentUri` values.
- Cloud metadata endpoints (`http://169.254.169.254/`, `http://metadata.google.internal/`) are reachable from most cloud-hosted MCP deployments.
- This is a distinct SSRF vector from the `_get_all_pages` nextLink issue (todo 036) — different code path, different data source, separate fix required.

## Proposed Solutions

**Option A (Recommended):**
- Validate each `contentUri` with: `if not content_uri.startswith("https://") or urlparse(content_uri).netloc not in ALLOWED_BLOB_HOSTS: raise ValueError(...)`
- Define `ALLOWED_BLOB_HOSTS = {"*.blob.core.windows.net", "*.office.com"}` and check with regex or `endswith`
- Effort: Small, Risk: Low

**Option B:**
- Add a general URL allowlist validator function used by both `_get_all_pages` and `_ual_fetch_blobs`
- Effort: Small, Risk: Low

## Acceptance Criteria

- [ ] `_ual_fetch_blobs` validates contentUri host before fetching
- [ ] Non-allowlisted URIs raise ValueError and are not fetched
- [ ] Unit test: mock blob API returning `http://169.254.169.254/` raises exception

## Work Log

- 2026-04-08: Identified in 3rd review pass
