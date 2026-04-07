---
status: complete
priority: p2
issue_id: "027"
tags: [code-review, performance, azure-ad, server]
dependencies: []
---

# 027 — httpx.AsyncClient created per Graph request — no connection pooling (highest-impact perf issue)

## Problem Statement

In `server.py`, `_graph()` (line 134) and `_ual_request()` (line 832) each create a new `httpx.AsyncClient` for every single API call. `httpx.AsyncClient` is designed to be long-lived for connection pooling and TLS session reuse. Creating a new client per call means:

- A new TLS handshake (~150–300ms to `graph.microsoft.com`) per request
- No HTTP/2 multiplexing across calls
- `azure_ad_incident_triage` fires 9 `asyncio.gather` calls — each establishes its own TLS connection
- 50-page `_get_all_pages` call creates 50 sequential TLS connections

## Findings

- **File**: `extensions/azure-ad/src/server.py`, lines 134, 832
- **Agent**: performance-oracle (CRITICAL — highest ROI change in the PR)

```python
# line 134 — new client per Graph call
async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
    response = await client.request(...)
```

At 50 pages × 200ms TLS overhead = 7.5s extra latency vs <0.5s with a persistent client.

## Proposed Solutions

### Option A: Module-level AsyncClient singleton (Recommended)
```python
_http_client: Optional[httpx.AsyncClient] = None

def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=60,
            follow_redirects=True,
            http2=True,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _http_client
```
Replace `async with httpx.AsyncClient(...) as client:` in both `_graph` and `_ual_request` with `client = _get_http_client()`.

### Option B: Context-var per request lifecycle
Create the client once at the start of each tool call and pass it through. More complex, avoids global state.

## Recommended Action

Option A — module-level singleton. Standard httpx pattern for long-lived servers. FastMCP servers are persistent processes — a module-level client is correct.

## Acceptance Criteria

- [ ] `_graph()` uses a shared `httpx.AsyncClient` instead of creating one per call
- [ ] `_ual_request()` uses the same shared client
- [ ] `azure_ad_incident_triage` with 9 parallel calls uses connection pooling

## Work Log

- 2026-04-07: Identified by performance-oracle as CRITICAL (highest ROI change)
- 2026-04-07: Fixed in server.py (commit 25d965c). Added _http_client module-level singleton (Optional[httpx.AsyncClient]) and _get_http_client() factory that creates/recreates the client when None or closed. Set limits=httpx.Limits(max_connections=20, max_keepalive_connections=10). Replaced async with httpx.AsyncClient in _graph() (line 134), _ual_request() (line 832), and _ual_fetch_blobs() blob download loop. All Graph API calls now reuse TLS connections. azure_ad_incident_triage parallel gather calls benefit from connection pooling.
