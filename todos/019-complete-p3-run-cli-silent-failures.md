---
status: complete
priority: p3
issue_id: "019"
tags: [code-review, quality, audit, mimecast]
dependencies: []
---

# 019 — run_cli() silently swallows failures, producing misleading clean audit reports

## Problem Statement

`run_cli()` in `audit_m365_sync.py` catches all exceptions and returns `None`, which callers treat as empty data. If an API call fails (credential error, network issue, timeout), the audit report says "0 orphaned accounts" instead of surfacing the fetch failure. This makes a broken audit indistinguishable from a clean one.

## Findings

- **File**: `plugins/mimecast-skills/scripts/audit_m365_sync.py`, lines 65-88
- **Agents**: kieran-python-reviewer (MEDIUM), security-sentinel (MED-1)

```python
except Exception as e:
    print(f"  ⚠ CLI error: {e}", file=sys.stderr)
    return None  # caller treats this as [] — audit continues silently
```

Also: `returncode != 0` truncates stderr to 200 chars and continues. Timeout error doesn't name which command timed out.

## Proposed Solutions

### Option A: Add --tolerant flag; fail-hard by default
Add `strict: bool = True` to `run_cli()`. In strict mode, raise on non-zero exit or timeout. Add `--tolerant` CLI flag to opt into best-effort mode.

### Option B: Propagate failure as a special sentinel
Return a `FetchError` sentinel object instead of `None`. Callers can distinguish "API returned empty" from "API call failed" and the report can flag incomplete data sections.

### Option C: Minimal improvement — better error message
At minimum, include the command name in timeout and error messages:
```python
print(f"  ⚠ CLI timed out: {cmd[1]} {cmd[2] if len(cmd)>2 else ''}", file=sys.stderr)
```

## Recommended Action

Option C immediately (tiny fix). Option A as a follow-up if audit reliability matters.

## Acceptance Criteria

- [ ] Timeout error messages include the script name and command verb
- [ ] Either: audit fails loudly on fetch error, OR: report clearly marks sections with incomplete data

## Work Log

- 2026-04-07: Identified by kieran-python-reviewer and security-sentinel
