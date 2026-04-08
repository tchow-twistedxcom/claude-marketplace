---
status: pending
priority: p1
issue_id: "079"
tags: [code-review, performance, azure-ad, throttling]
dependencies: []
---

# 079 — Unbounded `asyncio.gather` in `azure_ad_incident_triage`: N users × 9 Graph calls → throttling

## Problem Statement

`azure_ad_incident_triage` calls `asyncio.gather(*[_triage_one(u) for u in users])` with no concurrency cap. Each `_triage_one` call makes 9 Graph API calls (sign-ins, risk history, inbox rules, mailbox delegates, mail forwards, MFA methods, named locations, audit events, CA policies). For a tenant with 50 suspicious users this fires 450 simultaneous Graph requests — well above Microsoft's throttling thresholds (typically 12,000 req/min per tenant, but burst limits much lower). Throttled requests fail with 429 errors, causing silent data gaps in triage output.

## Findings

- **server.py lines 2371-2374**: `results = await asyncio.gather(*[_triage_one(u, ...) for u in users], return_exceptions=True)` — no semaphore
- `_triage_one` makes 9 concurrent Graph calls internally via another `asyncio.gather`
- Total concurrent calls = N users × 9 = N*9 with no cap
- Microsoft Graph throttles at tenant level; 429 errors cause `return_exceptions=True` to silently return exception objects → missing triage data
- Flagged by: performance-oracle (critical severity)

## Proposed Solutions

### Option A: Add semaphore to `_triage_one` (Recommended)
Add a module-level or parameter-passed semaphore limiting concurrent user triages:
```python
_TRIAGE_SEMAPHORE = asyncio.Semaphore(10)  # max 10 users concurrently = 90 Graph calls max

async def _triage_one(user, ..., sem: asyncio.Semaphore = _TRIAGE_SEMAPHORE):
    async with sem:
        # existing logic
```
- **Effort**: Small | **Risk**: Low (slightly slower for large batches, but correct)

### Option B: Batch users with semaphore at call site
```python
sem = asyncio.Semaphore(10)
async def _bounded_triage(u):
    async with sem:
        return await _triage_one(u, ...)
results = await asyncio.gather(*[_bounded_triage(u) for u in users], return_exceptions=True)
```
- Same effect, keeps semaphore at call site
- **Effort**: Small | **Risk**: Low

### Option C: Sequential processing for large batches
- If `len(users) > 20`, process sequentially
- Simple but slow for large batches
- **Effort**: Small | **Risk**: None (but performance regression)

## Acceptance Criteria
- [ ] `azure_ad_incident_triage` respects a concurrency cap (≤ 10 simultaneous user triages)
- [ ] No increase in 429 errors under normal tenant load
- [ ] Semaphore constant is documented with the reasoning (Graph throttle avoidance)
- [ ] Module-level Semaphore creation is handled safely (see todo 082 re: Lock instantiation)

## Work Log
- 2026-04-08: Identified in 6th code review pass (performance-oracle, critical severity)
