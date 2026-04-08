---
status: pending
priority: p1
issue_id: "040"
tags: [code-review, security, architecture, azure-ad]
dependencies: []
---

# 040 — DXT binary is stale — 114 lines of security hardening missing from distributed archive

## Problem Statement

`extensions/azure-ad.dxt` is a ZIP archive containing the packaged Claude Desktop extension. It was built from an older version of `extensions/azure-ad/src/server.py`. The current `server.py` includes approximately 114 lines of security hardening added in todos 014–034 (OData validation, destructive operation guards, httpx singleton, `_validate_safe_name`, `confirm=False` defaults, `dry_run=True` defaults, etc.). The distributed DXT does NOT include these fixes.

Any user who installs the extension via the `.dxt` file (Claude Desktop users) gets the vulnerable version without the security improvements. The DXT must be rebuilt from the current source.

## Findings

- `extensions/azure-ad.dxt` is committed as a binary ZIP artifact alongside the source in `extensions/azure-ad/`.
- The DXT was last rebuilt before todos 014–034 were completed.
- Security fixes from todos 014, 015, 023, 025, 026, 027, 028, 029, 030, 034 are present in `server.py` but absent from the DXT.
- Claude Desktop users who install via the `.dxt` file get the pre-hardening version — the MCP server they run lacks OData injection protection, SSRF guards, and destructive operation confirmations.
- There is no automated check or build script to detect or prevent this staleness from recurring.

## Proposed Solutions

**Option A (Recommended):**
- Rebuild the DXT: `cd extensions/azure-ad && zip -r ../azure-ad.dxt . -x "*.pyc" -x "__pycache__/*" -x ".git/*"`
- Verify the rebuilt DXT contains the current server.py: `unzip -p ../azure-ad.dxt src/server.py | wc -l` should match `wc -l server.py`
- Add a Makefile or script `make dxt` that rebuilds the archive, to prevent future staleness
- Effort: Small, Risk: Low

**Option B:**
- Add a CI check (pre-commit hook or GitHub Action) that fails if `azure-ad.dxt` is older than `server.py`
- Effort: Small, Risk: Low

## Acceptance Criteria

- [ ] `azure-ad.dxt` contains the current `server.py` (same line count and SHA)
- [ ] A `make dxt` or `./build-dxt.sh` command exists for future rebuilds
- [ ] DXT is committed alongside the server.py changes

## Work Log

- 2026-04-08: Identified in 3rd review pass
