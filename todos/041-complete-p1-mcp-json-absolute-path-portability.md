---
status: pending
priority: p1
issue_id: "041"
tags: [code-review, architecture, azure-ad]
dependencies: []
---

# 041 — `.mcp.json` hardcoded absolute path `/home/tchow/` — breaks portability for all other users

## Problem Statement

`plugins/m365-skills/.mcp.json` (created in todo 021) contains the hardcoded path `/home/tchow/.claude/plugins/marketplaces/tchow-essentials/extensions/azure-ad/src/server.py`. This path only works on one specific machine. Any other user who installs this plugin will get a broken MCP server configuration because the path does not exist on their system.

This also exposes the username `tchow` unnecessarily in a committed file.

## Findings

- `plugins/m365-skills/.mcp.json` was committed with an absolute path referencing `/home/tchow/`.
- The file is part of the marketplace plugin that can be installed by other users via `/plugin install m365-skills`.
- On a different machine or user account, the MCP server will fail to start with a "file not found" error.
- The username `tchow` is exposed in the repository, leaking account information unnecessarily.
- Other plugins in this marketplace may use a different path resolution pattern — should be checked for consistency.

## Proposed Solutions

**Option A (Recommended):**
- Use a relative path from the `.mcp.json` location, or use the `${__dirname}` equivalent Claude Code MCP resolution supports
- Check if Claude Code MCP configs support `${PLUGIN_ROOT}` or relative paths — if so, use `./../../extensions/azure-ad/src/server.py`
- Effort: Small, Risk: Low

**Option B:**
- Generate `.mcp.json` at install time using the actual install path
- Add a setup script that runs `sed "s|PLACEHOLDER|$(pwd)|g" .mcp.json.template > .mcp.json` and gitignores `.mcp.json`
- Keep `.mcp.json.template` with a `PLACEHOLDER` token
- Effort: Small, Risk: Low

**Option C (Simplest):**
- Check what pattern other plugins in this marketplace use for MCP server paths
- Match that pattern exactly
- Effort: Small, Risk: Low

## Acceptance Criteria

- [ ] `.mcp.json` does not contain `/home/tchow/` or any other hardcoded absolute path
- [ ] The MCP server starts correctly after a fresh install by a different user on a different machine
- [ ] If `.mcp.json` must be generated, `.mcp.json.template` is committed and `.mcp.json` is gitignored

## Work Log

- 2026-04-08: Identified in 3rd review pass
