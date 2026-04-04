---
status: complete
priority: p3
issue_id: "009"
tags: [code-review, performance, mimecast, mcp-server, caching]
dependencies: []
---

# 009 — `_get_auth_config()` re-reads config file on every MCP tool call

## Problem Statement

In `extensions/mimecast/src/server.py`, `_get_auth_config()` reads and parses the config YAML/TOML file from disk on every invocation. Since it's called by every MCP tool, a burst of 10 tool calls causes 10 disk reads of the same file.

On fast local storage this is minor, but in containerized or NFS environments it adds unnecessary latency.

## Findings

- **Agent**: performance-oracle (P3)
- **File**: `extensions/mimecast/src/server.py`

## Proposed Solutions

### Option A: Module-level cache with `functools.lru_cache`

```python
from functools import lru_cache

@lru_cache(maxsize=1)
def _get_auth_config(profile: str = "default") -> dict:
    ...
```

- **Pros**: Zero-effort caching; file read once per profile
- **Cons**: Config changes during process lifetime won't be picked up
- **Effort**: Tiny
- **Risk**: Very low

### Option B: `functools.cache` (Python 3.9+)

Same as above but uses `@cache` (unbounded). Appropriate since there are typically 1-2 profiles.

### Recommended
**Option A** — `@lru_cache(maxsize=4)` (supports a few profiles). Standard pattern.

## Technical Details

- **Affected files**: `extensions/mimecast/src/server.py`

## Acceptance Criteria

- [ ] Config file is read at most once per unique profile per process lifetime
- [ ] No behavioral change for callers

## Work Log

- 2026-04-04: Created by code review (performance-oracle finding)
