---
status: complete
priority: p2
issue_id: "061"
tags: [code-review, quality, architecture]
dependencies: []
---

# 061 — `audit_m365_sync.py` partial data fetches silently produce false-positive orphan reports

## Problem Statement
When `fetch_azure_users`, `fetch_azure_deleted_users`, `fetch_azure_domains`, or `fetch_mimecast_users` fail (timeout, auth error, etc.), they return `[]`. This empty list flows into `cross_reference()` which then produces a report showing "0 active synced users" and many "orphaned Mimecast users" — because no Azure AD users were fetched. The report has no data-confidence indicator. The `sys.exit(1)` triggered by `total_issues > 0` fires on these false positives, causing CI pipelines to fail on transient auth errors rather than real sync problems.

## Findings
```python
# audit_m365_sync.py lines 108-110
data = run_cli([...], verbose, timeout=180)
if data is None:
    return []  # Silent: looks like 0 users, not a fetch error

# audit_m365_sync.py ThreadPoolExecutor lines 1026-1034
except Exception as e:
    print(f"WARNING: worker failed for {key}: {e}", file=sys.stderr)
    fetch_results[key] = []  # False-positive: triggers orphan report

# audit_m365_sync.py line 1066 — false CI failure
if total_issues > 0:
    sys.exit(1)
```

## Proposed Solutions
Option A (Recommended):
1. Add a `fetch_errors: dict[str, str]` field to the sync_results dict, populated when a fetch function returns `[]` due to an error (vs. genuinely empty).
2. In `generate_markdown_report`, include a "Data Quality" section at the top listing any fetch errors, so the report reader knows the data is incomplete.
3. In `main()`, check if any fetch errors occurred before `sys.exit(1)` — if the Azure AD fetch failed, exit with code 2 (data error) rather than 1 (sync issues found), allowing CI to distinguish transient failures from real findings.
- Effort: Medium. Risk: Low.

Option B: Add `--strict` flag — only exit(1) when all data sources returned successfully. Simpler but doesn't surface the incomplete data in the report.

## Acceptance Criteria
- [x] `sync_results` dict includes `fetch_errors` tracking which fetches failed
- [x] Markdown report shows a "Data Quality" warning when any fetch returned empty due to error
- [x] `sys.exit()` code distinguishes data fetch failures (exit 2) from real sync issues (exit 1)

## Work Log
- 2026-04-08: Found by architecture-strategist in 4th review pass
- 2026-04-08: Resolved. Added fetch_errors: dict[str, str] initialized in main(). Both the
  initial ThreadPoolExecutor block (azure/mimecast fetches) and the config+health parallel block
  now populate fetch_errors on exception. generate_markdown_report accepts fetch_errors kwarg and
  renders a "Data Quality Warning" table at the top of the report when any are present. sys.exit()
  now uses code 2 (fetch errors + issues found) vs 1 (clean data + issues found) vs 0 (no issues).
  fetch_errors also included in --json output.
