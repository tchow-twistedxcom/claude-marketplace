---
status: pending
priority: p2
issue_id: "106"
tags: [code-review, performance, azure-ad]
dependencies: []
---

# 106 — `_TRIAGE_SEMAPHORE(10)` limits users but 90 concurrent Graph calls possible (semaphore at wrong level)

## Problem Statement

`_TRIAGE_SEMAPHORE = asyncio.Semaphore(10)` gates user-level concurrency so at most 10 users are triaged simultaneously. However, each user's triage makes approximately 9 Graph API calls. With 10 users concurrent, this allows up to 90 simultaneous Graph requests — well above the typical Graph API throttle budget per tenant (typically 10–20 concurrent calls per app). This can trigger 429 rate-limit responses that are either silently swallowed or cause partial triage results.

## Findings

- **`server.py`** `_TRIAGE_SEMAPHORE = asyncio.Semaphore(10)` (~line 79)
- Per-user triage makes ~9 Graph calls (mailbox, cloud events, sign-in logs, UAL, rule listing, etc.)
- 10 users × 9 calls = 90 simultaneous in-flight Graph requests at peak
- Graph API throttles at the app level — all 90 calls share the same throttle budget
- `_TRIAGE_SEMAPHORE` was added to prevent Python-level overload but doesn't address API throttling
- Flagged by: performance-oracle (7th review pass)

## Proposed Solutions

### Option A: Add a Graph API call-level semaphore (recommended)

Add a separate `_GRAPH_SEMAPHORE = asyncio.Semaphore(20)` for all Graph HTTP calls, independent of user-level semaphore:
```python
_GRAPH_SEMAPHORE = asyncio.Semaphore(20)  # max concurrent Graph API calls

async def _graph_get(url, headers):
    async with _GRAPH_SEMAPHORE:
        return await _http_get(url, headers)
```

- **Effort**: Medium | **Risk**: Low (limits burst, may slightly increase latency for large batches)

### Option B: Reduce `_TRIAGE_SEMAPHORE` to 2–3 users

With 9 calls per user, semaphore(2) → 18 concurrent calls, semaphore(3) → 27 calls. Simpler than adding a second semaphore, but limits throughput.

- **Effort**: Trivial | **Risk**: Low

### Option C: Document the burst potential without changing behavior

Add a comment noting the 9× multiplier and the Graph throttle risk. Defer to operational tuning.

- **Effort**: Trivial | **Risk**: None (documentation only)

## Acceptance Criteria

- [ ] Graph API concurrent call count bounded to a safe level (≤ 20–30 simultaneously)
- [ ] OR documented with explicit rationale for current approach and known throttle risk

## Work Log

- 2026-04-08: Identified in 7th code review pass (performance-oracle) — semaphore controls users not Graph calls
