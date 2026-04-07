---
status: pending
priority: p1
issue_id: "021"
tags: [code-review, agent-native, m365-skills, registration]
dependencies: []
---

# 021 — DXT extension not registered in plugin.json — 48 tools orphaned

## Problem Statement

`extensions/azure-ad/src/server.py` contains 48 MCP tools (incident triage, email forensics, Defender hunting, OAuth persistence detection, CA policy management, etc.). The `extensions/azure-ad/manifest.json` and `.dxt` bundle exist. However, `plugins/m365-skills/plugin.json` has `"mcpServers": []` — the extension is never registered with the plugin system. Any agent or user installing `m365-skills` from the marketplace does not get the DXT extension tools. All 48 tools are completely invisible.

## Findings

- **File**: `plugins/m365-skills/plugin.json`, line 29 — `"mcpServers": []`
- **File**: `extensions/azure-ad/manifest.json` — exists with full manifest, 48 tools defined
- **File**: `extensions/azure-ad.dxt` — binary bundle exists
- **Agent**: agent-native-reviewer (CRITICAL)

The highest-value tools in the entire PR — `azure_ad_incident_triage`, email forensics tools, Defender KQL hunting — are unreachable without this registration.

**Agent-native score impact**: 0/48 DXT tools are accessible through the plugin marketplace.

## Proposed Solutions

### Option A: Add DXT extension path to plugin.json (Recommended)
```json
{
  "mcpServers": ["../../extensions/azure-ad.dxt"]
}
```
Or using relative path from plugin root — depends on how the marketplace resolver handles DXT paths. Check how other DXT extensions (if any) are registered.

### Option B: Add manifest.json reference
```json
{
  "mcpServers": [{"path": "../../extensions/azure-ad/manifest.json"}]
}
```

### Option C: Document as separate manual install
Add instructions to SKILL.md / README for manual DXT registration with Claude Code, and note that the CLI path (`azure_ad_api.py`) is the primary agent interface.

## Recommended Action

Option A — determine the correct DXT registration path by looking at marketplace.json plugin entries that reference DXT extensions, or check Claude Code DXT installation documentation.

## Acceptance Criteria

- [ ] `plugins/m365-skills/plugin.json` `mcpServers` array references the DXT extension
- [ ] An agent installing `m365-skills` has access to `azure_ad_incident_triage` tool
- [ ] Or: SKILL.md explicitly documents that DXT tools require separate installation with instructions

## Work Log

- 2026-04-07: Identified by agent-native-reviewer as CRITICAL (0/48 DXT tools accessible)
