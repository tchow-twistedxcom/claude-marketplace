---
status: pending
priority: p3
issue_id: "031"
tags: [code-review, quality, mimecast, pattern-bypass]
dependencies: []
---

# 031 — directory_sync.py and human_risk.py bypass format_output() — inconsistent output, no CSV

## Problem Statement

The two new domain modules added in this PR both bypass the established `format_output()` pattern used by every other domain module. Instead, they do their own table rendering, per-function `import json`, and manual column-width calculation. This produces visually inconsistent output compared to the rest of the Mimecast CLI, and neither module has CSV support.

## Findings

- **File**: `plugins/mimecast-skills/scripts/domains/directory_sync.py` — 17 direct `print()` calls, manual column widths, `import json as _json` at function scope (lines 53, 94), `import re` at function scope (line 127)
- **File**: `plugins/mimecast-skills/scripts/domains/human_risk.py` — same pattern, 12 per-function `import json` calls
- **Agents**: pattern-recognition-specialist (HIGH), code-simplicity-reviewer

```python
# directory_sync.py pattern (should use format_output):
if getattr(args, "output", "table") == "json":
    import json as _json
    print(_json.dumps(connections, indent=2))
    return
```

Compare to established pattern in `awareness_training.py`:
```python
from mimecast_formatter import format_output
format_output(result, args.output, 'awareness-campaigns')
```

## Proposed Solutions

### Option A: Refactor to use format_output() (Recommended)
Convert `cmd_status()`, `cmd_history()`, `cmd_summary()`, `cmd_users()` to build result dicts and call `format_output(result, args.output, 'resource_type')`. Move all `import json` / `import re` to module top.

### Option B: Add CSV support manually to both modules
Keep the current pattern but add CSV output mode to match other domains. Less ideal — duplicates formatter logic.

### Option C: Accept inconsistency
These are new domains with specialized display logic. The inconsistency is acceptable for personal tools.

## Recommended Action

Option A for a follow-up cleanup PR. Not a blocker for the current PR, but creates a noticeable UX inconsistency.

## Acceptance Criteria

- [ ] `directory_sync.py` domain commands use `format_output()` for json/csv/table routing
- [ ] `human_risk.py` domain commands use `format_output()` for json/csv/table routing
- [ ] All `import json` / `import re` calls moved to module top level

## Work Log

- 2026-04-07: Identified by pattern-recognition-specialist (HIGH) and code-simplicity-reviewer
