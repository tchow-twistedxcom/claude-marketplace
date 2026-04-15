---
status: complete
priority: p2
issue_id: "083"
tags: [code-review, security, azure-ad, credentials]
dependencies: []
---

# 083 — `--password` CLI flag still accepted in `azure_ad_api.py` despite `getpass` fix

## Problem Statement

A previous fix added `getpass.getpass()` as a fallback when `--password` is omitted, but the `--password` CLI argument was not removed from the parser. When `--password secretValue` is passed directly, the plaintext password appears in `/proc/<pid>/cmdline`, `ps aux` output, shell history (`~/.bash_history`), and any audit logs that capture command lines. The `AZURE_INITIAL_PASSWORD` env var fallback has similar risks if set in `.env` files committed to version control or in shell `export` commands in `~/.zshrc`.

## Findings

- **azure_ad_api.py line 612**: `users_create.add_argument('--password', help='...')` — argument still registered
- **azure_ad_api.py line 949**: `'password': args.password or os.environ.get('AZURE_INITIAL_PASSWORD') or getpass.getpass('Initial password: ')`
- The `--password` flag is demoted to optional but not removed — fix is incomplete
- Flagged by: security-sentinel (low severity); considered a regression from the `getpass` fix intent

## Proposed Solutions

### Option A: Remove `--password` argument entirely (Recommended)
Delete the `add_argument('--password', ...)` line. Force all callers to use `getpass` (interactive) or `AZURE_INITIAL_PASSWORD` env var (non-interactive scripting). Update help text to document env var usage.
- **Effort**: Small | **Risk**: Low (only affects callers passing `--password` directly)

### Option B: Mark `--password` as deprecated with warning
Add `action=DeprecationWarning` or emit a `warnings.warn()` when `--password` is used
- **Effort**: Small | **Risk**: None

## Acceptance Criteria
- [ ] `--password` argument is removed from argparse (or deprecated with clear warning)
- [ ] Help text for `users create` documents `AZURE_INITIAL_PASSWORD` env var as the non-interactive path
- [ ] `getpass.getpass()` is the only interactive path

## Work Log
- 2026-04-08: Identified in 6th code review pass (security-sentinel)
- 2026-04-08: Resolved — removed `add_argument('--password', ...)` from users create subparser; updated password expression to use only env var and getpass. Commit: 37954cf
