---
status: pending
priority: p2
issue_id: "071"
tags: [code-review, architecture, quality, azure-ad]
dependencies: []
---

# 071 — Audit accuracy: connections[0] only, createdDateTime false-positives, global AZURE_SVC_PREFIXES, subprocess silent errors

## Problem Statement

Four architectural issues in `audit_m365_sync.py` that affect data accuracy and correctness:

1. `analyze_sync_health` inspects only `connections[0]` — silent data loss for multi-forest or multi-AD tenants with multiple directory sync connections.
2. `cross_reference` uses `createdDateTime` as proxy for disable date — long-tenured employees disabled last week have old `createdDateTime`, producing false-positive HIGH severity findings (classified as `stale_grace` instead of `grace_period`).
3. `global AZURE_SVC_PREFIXES` mutation via CLI argument is a Python antipattern that makes `filter_azure_users` non-deterministic if imported.
4. `run_cli()` collapses auth errors, empty results, and JSON parse failures into the same `None`/`[]` return — callers cannot distinguish "zero users" from "auth failed".

## Findings

### 1. `analyze_sync_health` only checks connections[0] (audit_m365_sync.py ~line 671)
```python
conn = connections[0]
```
Mimecast can return multiple directory sync connection objects (one per LDAP/AD source). If a multi-forest tenant has one healthy and one error-state connection, only the first is analyzed — the second error is silently missed. `DirectorySyncDomain.cmd_status` in `directory_sync.py` correctly iterates all connections.

### 2. `createdDateTime` proxy for disable date (audit_m365_sync.py ~lines 440–452)
```python
# NOTE: Using createdDateTime as a proxy for "recently disabled" date.
# Long-tenured employees disabled last week will have old createdDateTime
# and will NOT appear in the grace bucket.
```
A user hired 3 years ago and disabled yesterday has `createdDateTime` from 3 years ago → classified `stale_grace` (HIGH severity) when they should be `grace_period` (INFO). This is the dominant case for routine offboarding. The fix is to use `signInActivity.lastSignInDateTime` (already a required permission: `AuditLog.Read.All`).

### 3. `global AZURE_SVC_PREFIXES` mutation (audit_m365_sync.py ~lines 1001–1003)
```python
if args.svc_prefixes.strip():
    global AZURE_SVC_PREFIXES
    AZURE_SVC_PREFIXES = tuple(...)
```
Using `global` to override a module constant via CLI args is an antipattern. Any code importing `filter_azure_users` in the same process will see the mutated constant. The correct pattern: `filter_azure_users(users, svc_prefixes=...)` with a default parameter.

### 4. Subprocess bridge silent errors (audit_m365_sync.py ~lines 76–96)
`run_cli()` returns `None` on non-zero exit, `None` on JSON parse error, and `None` on timeout — all three collapse to `fetch_results[key] = []` at the call site. Auth misconfiguration looks identical to "zero users in tenant". `fetch_errors` tracking (added in todo 061) catches exceptions from the ThreadPoolExecutor futures but not the silent `None` returns from `run_cli` itself.

## Proposed Solutions

### 1. connections[0] fix
Iterate over all connections and emit findings per connection, prefixing `check` field with connection name/index. Match the `for conn in connections:` pattern already used in `DirectorySyncDomain.cmd_status`.

### 2. createdDateTime → lastSignInDateTime
Add `signInActivity` to the `--select` list in `fetch_azure_users`. In `cross_reference`, use `user.get("signInActivity", {}).get("lastSignInDateTime")` as the grace period boundary, falling back to `createdDateTime` only when absent.

### 3. global removal
Change `filter_azure_users` signature to `filter_azure_users(users, svc_prefixes=AZURE_SVC_PREFIXES)`. In `main()`, pass `args.svc_prefixes` as a parameter instead of reassigning the global. Remove `global` statement.

### 4. run_cli error differentiation
Have `run_cli()` raise a typed `CLIError` (or return a `Result` tuple `(data, error)`) instead of returning `None`. Update all callers to capture errors into `fetch_errors`.

- Effort: Medium (items 2 and 4 require more care). Risk: Low.

## Acceptance Criteria

- [ ] `analyze_sync_health` iterates all connections (not just index 0)
- [ ] `cross_reference` uses `signInActivity.lastSignInDateTime` for grace period boundary (falls back to `createdDateTime`)
- [ ] `global AZURE_SVC_PREFIXES` removed; `filter_azure_users` accepts `svc_prefixes` parameter
- [ ] `run_cli()` distinguishes non-zero exit from empty result; auth failures surface in `fetch_errors`

## Work Log

- 2026-04-08: Identified by architecture-strategist (FINDING-4/5/6/7) and kieran-python-reviewer (FINDING-1) in 5th review pass
