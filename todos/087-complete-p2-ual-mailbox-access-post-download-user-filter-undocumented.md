---
status: complete
priority: p2
issue_id: "087"
tags: [code-review, performance, azure-ad, ual]
dependencies: []
---

# 087 — `azure_ad_ual_mailbox_access` user filter is post-download — O(N×E) not documented

## Problem Statement

`azure_ad_ual_mailbox_access` accepts a `users` parameter that filters events by user. However, the Office 365 Management Activity API does not support server-side user filtering — all events for the time window must be downloaded first, then filtered in Python. For tenants with high mailbox activity, passing a small `users` set still requires downloading the full audit stream. This O(N×E) behavior (N blob pages × E events per page) is not documented, and callers may assume the filter reduces API traffic.

## Findings

- **server.py line 1104**: `if users and e.get("UserId", "").lower() not in {u.lower() for u in users}` — client-side filter applied after full download
- The O365 Management Activity API (`/subscriptions/content`) returns all content blobs for a content type; there is no user-level filter parameter
- For a busy tenant with 10,000 mailbox events/day, fetching 7 days = ~70,000 events downloaded to filter to 5 users' events
- No warning in tool docstring or response that `users` is a post-download filter
- Flagged by: performance-oracle (medium severity)

## Proposed Solutions

### Option A: Document the limitation clearly in docstring (Recommended)
Add to the `users` parameter description:
> "**Note**: The O365 Management API does not support server-side user filtering. All events are downloaded then filtered client-side. Passing a `users` set reduces the returned events but does NOT reduce API calls or download volume."

Optionally add a runtime warning when `len(users) < 10` and event volume is high.
- **Effort**: Trivial | **Risk**: None

### Option B: Add a warning in the response when filtered
When `users` is non-empty and < 20% of events match, include:
`"filterNote": "User filter applied post-download; X of Y total events matched"`
- **Effort**: Small | **Risk**: None

## Acceptance Criteria
- [ ] Docstring documents that `users` filter is applied post-download
- [ ] No false impression that `users` reduces API traffic
- [ ] Optionally: response includes filter efficiency stats when `users` param is used

## Work Log
- 2026-04-08: Identified in 6th code review pass (performance-oracle)
- 2026-04-08: Fixed — added Note to users parameter docstring clarifying that user filtering is client-side post-download and the O365 Management API has no server-side user filter. Commit: fix(azure-ad): resolve 6th review todos 077-098a in server.py
