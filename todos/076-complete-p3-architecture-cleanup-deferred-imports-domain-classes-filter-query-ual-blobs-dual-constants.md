---
status: complete
priority: p3
issue_id: "076"
tags: [code-review, architecture, azure-ad]
dependencies: []
---

# 076 — Architecture cleanup: deferred imports, DOMAIN_CLASSES manual, filter_query length cap, _ual_fetch_blobs silent, dual auth constants, _triage_one extraction

## Problem Statement

Six architectural improvements: deferred per-call `format_output` imports in domain modules (implicit sys.path dependency), manually maintained `DOMAIN_CLASSES` list, no `filter_query` length cap, `_ual_fetch_blobs` swallows all blob download failures silently, `GRAPH_BASE`/`GRAPH_SCOPE`/`TOKEN_REFRESH_BUFFER` defined independently in both `server.py` and `auth.py`, and `_triage_one` (348 lines) embedded as an inner async function.

## Findings

### 1. Deferred `from mimecast_formatter import format_output` per method call (domains/*.py)
`directory_sync.py` lines 54, 101; `human_risk.py` lines 54, 111; `awareness_training.py` ~16 occurrences. Import deferred inside each `cmd_*` handler body because the module is one level up in `scripts/`. Works only when `scripts/` is on `sys.path` — domain modules cannot be imported in isolation (e.g., tests). The `awareness_training.py` variant repeats the import 16 times unnecessarily.

### 2. `DOMAIN_CLASSES` manually maintained list (domains/__init__.py ~line 7)
```python
DOMAIN_CLASSES = [AwarenessTrainingDomain, DirectorySyncDomain, HumanRiskDomain]
```
Adding a new domain requires editing 3 files and adding to this list. A new domain silently breaks dispatch if the developer forgets to update it. The `BaseDomain` ABC enforces interface but not registration.

### 3. `filter_query` no length cap (server.py ~lines 259, 391, 473)
`filter_query` on `list_users`, `list_groups`, `list_devices` is documented as admin-only pass-through but has no length guard. A multi-kilobyte filter can produce slow or opaque Graph API errors.

### 4. `_ual_fetch_blobs` swallows all exceptions silently (server.py ~lines 913–924)
```python
for resp in responses:
    if isinstance(resp, Exception):
        continue  # Skip untrusted URIs silently
```
HTTP errors, token expiry, SSRF rejections, and 429 throttles are all swallowed identically. The caller (`azure_ad_ual_inbox_rules`, `_triage_one`) sees a potentially empty list and reports "no findings" when data is simply missing. The comment "Skip untrusted URIs" only applies to one of the error cases.

### 5. Dual auth stack shared constants not shared (server.py ~lines 61–64, auth.py ~lines 48–50)
```python
# server.py:
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"
TOKEN_REFRESH_BUFFER = 300

# auth.py (independent definitions):
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"  # different variable name!
GRAPH_SCOPE = "https://graph.microsoft.com/.default"
TOKEN_REFRESH_BUFFER = 300
```
Three constants defined independently. Different variable names (`GRAPH_BASE` vs `GRAPH_BASE_URL`) mean a future change to one won't be caught by grep. No shared import between the two stacks.

### 6. `_triage_one` inner async function is 348 lines (server.py ~lines 1862–2210)
Closes over 6+ outer-scope variables (`ual_events`, `trusted_ip_set`, `hours`, `since`, `domain`, `PHISHING_SUBJECTS`). Too large to test in isolation. `PHISHING_SUBJECTS` is defined as a local set inside the outer function body rather than a module-level constant. Should be extracted to a module-level async helper.

## Proposed Solutions

### 1. Deferred imports
Option A: Hoist import to class body: `from ..mimecast_formatter import format_output` (requires `__init__.py` package structure).
Option B: Move `format_output` to `domains/__init__.py` and import from there.
Option C (minimal): Move import to top of each domain file (outside method bodies) — still relies on sys.path but eliminates per-call overhead and the 16× repetition in `awareness_training.py`.

### 2. DOMAIN_CLASSES
Implement `@register_domain` decorator that appends to a global registry list on class definition. Or use `importlib` auto-discovery scanning `domains/` for `BaseDomain` subclasses. Minimal change: decorator pattern.

### 3. filter_query length cap
Add `if filter_query and len(filter_query) > 2000: raise ValueError(...)` in `list_users`, `list_groups`, `list_devices` before calling `_get_all_pages`.

### 4. _ual_fetch_blobs error surfacing
Count and log blob failures:
```python
errors = [str(r) for r in responses if isinstance(r, Exception)]
if errors:
    print(f"WARNING: {len(errors)}/{len(tasks)} UAL blobs failed", file=sys.stderr)
```
For triage, add `"ualDataIncomplete": bool(errors)` to `ualFindings` return.

### 5. Shared constants
Create a shared constants reference at the top of `server.py` with a comment noting the values must match `auth.py`. Short of a shared module, add a `# MUST MATCH auth.py TOKEN_REFRESH_BUFFER` comment at both definitions. Full fix: extract to a `shared_constants.py` importable by both.

### 6. _triage_one extraction
Extract `_triage_one(upn, ual_events, trusted_ip_set, hours, since, domain)` to a module-level async function. Move `PHISHING_SUBJECTS` to module scope.

- Effort: Small (3, 4, 5); Medium (1, 2, 6). Risk: Low.

## Acceptance Criteria

- [ ] `from mimecast_formatter import format_output` hoisted to file-level (not per-call) in all domain modules
- [ ] `@register_domain` decorator auto-registers domains without manual `DOMAIN_CLASSES` edit
- [ ] `filter_query` rejects values over 2000 characters in list_users/groups/devices
- [ ] `_ual_fetch_blobs` logs blob failure count to stderr; triage result includes `ualDataIncomplete` flag
- [ ] `GRAPH_BASE`/`GRAPH_SCOPE`/`TOKEN_REFRESH_BUFFER` divergence documented (or shared) between server.py and auth.py
- [ ] `_triage_one` extracted to module-level function; `PHISHING_SUBJECTS` moved to module scope

## Work Log

- 2026-04-08: Identified by architecture-strategist (FINDING-8/9/10/11) and kieran-python-reviewer (FINDING-11) in 5th review pass
- 2026-04-08: Resolved. format_output imports hoisted to file level in all 3 domain modules (16 per-call duplicates removed from awareness_training.py). @register_domain decorator added to domains/__init__.py; _DOMAIN_REGISTRY auto-populates via decorators on all domain classes. filter_query length cap (>2000 chars) added to list_users/list_groups/list_devices. _ual_fetch_blobs now returns (events, incomplete) tuple; logs error counts to stderr; ualDataIncomplete added to triage ualFindings. GRAPH_BASE/GRAPH_SCOPE/TOKEN_REFRESH_BUFFER annotated with must-match-auth.py comment. _triage_one extracted to module-level async function; PHISHING_SUBJECTS moved to module scope as frozenset. Commit: a8c2a30.
