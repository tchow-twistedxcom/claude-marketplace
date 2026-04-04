---
status: complete
priority: p2
issue_id: "004"
tags: [code-review, performance, mimecast, pagination]
dependencies: []
---

# 004 — `paginate_v2()` max_results check fires after full page fetch

## Problem Statement

In `plugins/mimecast-skills/scripts/mimecast_client.py`, the `paginate_v2()` method checks `max_results` AFTER extending the results list with a full page:

```python
results.extend(page)
if max_results and len(results) >= max_results:
    return results[:max_results]
```

When `max_results=5` and the page size is 50, it fetches all 50 items, extends the list, then truncates to 5. For large datasets with many pages, this over-fetches by up to `(page_size - 1) * num_pages` items — wasting network, memory, and potentially Mimecast rate-limit budget.

## Findings

- **File**: `plugins/mimecast-skills/scripts/mimecast_client.py`, `paginate_v2()` method
- **Agent**: performance-oracle (P1 in their ranking)

## Proposed Solutions

### Option A: Break before extending when we already have enough

```python
results.extend(page)
if max_results and len(results) >= max_results:
    return results[:max_results]
```

Becomes:

```python
if max_results:
    remaining = max_results - len(results)
    results.extend(page[:remaining])
    if len(results) >= max_results:
        return results
else:
    results.extend(page)
```

- **Pros**: Never over-fetches items within a page; correct semantics
- **Cons**: Slightly more verbose
- **Effort**: Small
- **Risk**: Very low

### Option B: Pass `top` / `$top` parameter to API
Mimecast API 2.0 may support `$top` OData parameter to limit server-side results.

- **Pros**: Reduces network traffic at source
- **Cons**: Not all endpoints support `$top`; requires per-endpoint knowledge
- **Effort**: Medium
- **Risk**: Medium (endpoint-specific)

### Recommended
**Option A** — client-side early exit. Simple, universal, correct.

## Technical Details

- **Affected files**: `plugins/mimecast-skills/scripts/mimecast_client.py`

## Acceptance Criteria

- [ ] `paginate_v2(max_results=5)` with 50-item pages returns exactly 5 items
- [ ] `paginate_v2(max_results=5)` only calls the API once (one page)
- [ ] `paginate_v2(max_results=None)` still fetches all pages correctly

## Work Log

- 2026-04-04: Created by code review (performance-oracle finding)
