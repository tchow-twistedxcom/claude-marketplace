---
title: "feat: Add cowork-bridge plugin for Claude Code ↔ Cowork collaboration"
type: feat
status: completed
date: 2026-04-02
brainstorm: docs/brainstorms/2026-04-02-cowork-bridge-brainstorm.md
---

# feat: Add cowork-bridge Plugin for Claude Code ↔ Cowork Collaboration

## Enhancement Summary

**Deepened on:** 2026-04-02
**Sections enhanced:** 8
**Research agents used:** Architecture, Security, YAGNI/Simplicity, SKILL.md Best Practices, Agent-Native Architecture, DevOps/SharePoint, Pattern Recognition, create-agent-skills

### Key Improvements
1. **Naming scheme simplified**: `{YYYYMMDD}-{HHmmss}-{uuid8}` replaces fragile seq-based collision avoidance
2. **Manifest safety**: Lock file pattern for concurrent write protection; skip prompts/ folder (generate inline)
3. **Skill activation hardened**: Directive description language + `disable-model-invocation: true` for filesystem safety
4. **plugin.json enriched**: Add `homepage`, `repository`, `author.url` fields per marketplace pattern
5. **Setup simplified**: Cut `archive/` and `prompts/` from initial dir structure (YAGNI); generate prompt inline
6. **abraunegg config precise**: `monitor_interval=45`, `skip_dotfiles=true`, Device Flow OAuth for headless servers

### New Considerations Discovered
- **Security**: Sanitize artifacts before packaging (credential leakage risk); validate project name for path traversal
- **Agent-native**: Cowork completion signal via `outbox/{id}-done.md` marker file (explicit, no polling)
- **SharePoint headless auth**: Device Flow (`onedrive --auth-files`) is the correct OAuth flow for Linux servers
- **SKILL.md `disable-model-invocation: true`**: Required to prevent unconfirmed filesystem side effects

---

## Overview

Add a `cowork-bridge` plugin to the tchow-essentials marketplace that enables structured collaboration between Claude Code and Claude Cowork. Claude Code generates technical artifacts; the plugin packages them and hands off to Cowork via a shared SharePoint-backed folder. Cowork consumes the artifacts and produces polished client deliverables.

## Problem Statement

Claude Code generates valuable technical artifacts — security audits, integration analyses, data extractions, architecture diagrams — but there's no structured way to hand them off to Claude Cowork for transformation into client-ready deliverables (reports, proposals, presentation decks). Currently, this requires manual copy-paste and loses context.

## Proposed Solution

**Architecture:**
```
Linux Server                    SharePoint Online                  Cowork
~/cowork-bridge/ ──sync──► SP Document Library ◄──connector── Claude Cowork
 (Claude Code writes)      (abraunegg/onedrive)               (reads & produces)
```

**Components:**
1. `~/cowork-bridge/` — shared local folder synced to SharePoint via `abraunegg/onedrive`
2. `/cowork-setup` command — first-run initialization + SharePoint sync guidance
3. `/cowork-handoff` skill — packages artifacts, updates manifest, generates Cowork-ready prompt
4. Manifest system (`manifest.json`) — tracks artifact lifecycle
5. Deliverable templates — pure markdown instructions for Cowork

### Research Insights: Architecture

**Naming Convention (updated):**
Replace seq-based `{YYYYMMDD}-{project}-{type}-{seq:02d}` with `{YYYYMMDD}-{HHmmss}-{uuid8}` (e.g., `20260402-143022-a1b2c3d4`). Rationale:
- Seq requires directory scan + parse to find next value — race-prone in concurrent sessions
- HHmmss eliminates same-second collisions in practice; uuid8 suffix is bulletproof fallback
- Simpler implementation: one `date +%Y%m%d-%H%M%S` + `uuidgen | head -c 8`

**Manifest Write Safety:**
Use a lock file (`manifest.json.lock`) to prevent concurrent corruption:
```bash
# Before write:
if [ -f ~/cowork-bridge/manifest.json.lock ]; then
  echo "Another handoff is in progress. Wait a moment and retry."
  exit 1
fi
touch ~/cowork-bridge/manifest.json.lock
# ... read-backup-merge-write ...
rm ~/cowork-bridge/manifest.json.lock
```

**Sync Latency Note (add to SKILL.md):**
After packaging to `inbox/`, files sync to SharePoint within ~5–30 seconds depending on abraunegg monitor interval. Inform user: "Files are ready. SharePoint sync takes ~10–30 seconds — paste the prompt into Cowork after a brief pause."

**Cowork Completion Signal:**
Cowork writes `outbox/{id}-done.md` when finished. Claude Code can check: `ls ~/cowork-bridge/outbox/ | grep {id}` to detect completion without polling.

## Technical Approach

### Architecture

**SharePoint as Shared Layer:**
- `abraunegg/onedrive` (12k GitHub stars) syncs `~/cowork-bridge/` to a SharePoint Document Library
- Real-time via `--monitor` flag (inotify-based); bidirectional by default
- Cowork accesses the same SharePoint library via its built-in connector
- No custom infrastructure required — just filesystem conventions + sync daemon

**Manifest System:**
- `manifest.json` at `~/cowork-bridge/manifest.json` tracks all artifacts
- Schema-versioned for forward compatibility
- Read-modify-write with lock file protection + atomic backup before updates
- Status lifecycle: `pending` → `ready` → `in-progress` → `delivered`

**Deliverable Type System:**
- 3 core pipelines: `audit` (→ report), `integration` (→ proposal), `data` (→ deck)
- Each type has a dedicated template in `~/cowork-bridge/templates/`
- Templates are pure markdown — Cowork instruction documents, not code

### Research Insights: Security

**Critical: Credential Sanitization**
Before packaging any artifact into `inbox/`:
- Warn user: "I'll package these files. Please ensure they don't contain API keys, passwords, or credentials before proceeding."
- Do NOT silently scan for secrets (false positives cause frustration); user confirmation is the gate.

**Path Traversal Protection**
Project names from user input must be sanitized before use in filesystem paths:
```bash
# Safe project name: allow only alphanumeric, hyphens, underscores
project_name=$(echo "$raw_input" | sed 's/[^a-zA-Z0-9_-]/-/g' | head -c 40)
```

**OAuth Token Protection**
abraunegg stores OAuth tokens at `~/.config/onedrive/`. Ensure:
- Not included in any git commits or exports
- File permissions: `chmod 600 ~/.config/onedrive/refresh_token`

**Prompt Injection Mitigation**
Cowork prompts generated by the skill should not include raw user-provided text in instruction positions. Summary/description fields are safe; only path references go into the "read these files" section.

### Implementation Phases

#### Phase 1: Plugin Skeleton & Foundation
Create the base plugin structure and register in marketplace.

Files:
- `plugins/cowork-bridge/plugin.json`
- `.claude-plugin/marketplace.json` (modify — add entry)

#### Phase 2: Templates (Dependency-free)
Create deliverable templates and manifest template. These must exist before SKILL.md can reference them.

Files:
- `plugins/cowork-bridge/templates/manifest-template.json`
- `plugins/cowork-bridge/templates/audit-to-report.md`
- `plugins/cowork-bridge/templates/analysis-to-proposal.md`
- `plugins/cowork-bridge/templates/data-to-deck.md`

#### Phase 3: Core Skill (Main Logic)
Create the primary skill with full handoff workflow. References are inlined into the SKILL.md body rather than separate files (YAGNI).

Files:
- `plugins/cowork-bridge/skills/cowork-handoff/SKILL.md`

#### Phase 4: Commands (User Entry Points)
Create slash commands.

Files:
- `plugins/cowork-bridge/commands/cowork-handoff.md`
- `plugins/cowork-bridge/commands/cowork-setup.md`

### File Specifications

#### `plugins/cowork-bridge/plugin.json`
```json
{
  "name": "cowork-bridge",
  "version": "1.0.0",
  "description": "Shared workspace bridge between Claude Code and Claude Cowork. Packages artifacts, generates Cowork-ready prompts with deliverable templates, and tracks handoffs via manifest. Syncs via SharePoint/OneDrive.",
  "author": {
    "name": "tchow",
    "url": "https://github.com/tchow-twistedxcom"
  },
  "homepage": "https://github.com/tchow-twistedxcom/claude-marketplace",
  "repository": "https://github.com/tchow-twistedxcom/claude-marketplace",
  "license": "MIT",
  "keywords": ["cowork", "sharepoint", "handoff", "deliverables", "collaboration", "onedrive"],
  "commands": [
    "./commands/cowork-handoff.md",
    "./commands/cowork-setup.md"
  ],
  "skills": [
    "./skills/cowork-handoff"
  ]
}
```

**Pattern Research Insights:** Added `homepage`, `repository`, `author.url` fields to match marketplace convention (other plugins in tchow-essentials use these). COMPLIANT with plugin structure standards.

#### `plugins/cowork-bridge/skills/cowork-handoff/SKILL.md` (CRITICAL FILE)

**YAML Frontmatter:**
```yaml
---
name: cowork-handoff
disable-model-invocation: true
description: "Package Claude Code artifacts and hand off to Claude Cowork for client
  deliverable creation. Invoke when the user says: 'hand off to cowork', 'package
  for cowork', 'send to cowork', 'prepare a client deliverable', 'cowork bridge',
  'create a report from this analysis', 'turn this into a proposal', 'make a deck
  from this data', or 'handoff'."
allowed-tools:
  - Read
  - Write
  - Bash(ls *)
  - Bash(mkdir *)
  - Bash(cp *)
  - Bash(cat *)
  - Bash(date *)
  - Bash(uuidgen)
  - Bash(touch *)
  - Bash(rm *)
---
```

**Research Insights: SKILL.md Design**

`disable-model-invocation: true` is **mandatory** — this skill writes files to the filesystem. Without it, a mention of "cowork" in conversation could trigger unconfirmed file writes. User must explicitly invoke via `/cowork-handoff` or the listed trigger phrases.

`allowed-tools` scoping prevents the skill from making network calls, running Python scripts, or doing destructive operations without user awareness.

**Directive description pattern** (best practice): Start with an action verb ("Package"), list specific trigger phrases in a quoted list. This achieves ~100% activation accuracy vs ~77% for passive descriptions like "Skill for packaging...". Current wording is already directive — preserve it.

**Body Sections (target 250-300 lines following marketplace patterns):**
1. `## Overview` — 2-3 sentence description
2. `## When to Use` — trigger phrase list
3. `## Prerequisites` — `~/cowork-bridge/` must exist (prompt to run `/cowork-setup`)
4. `## Deliverable Types` — table: type | input | output | template
5. `## First-Run Check` — if `~/cowork-bridge/` missing, guide to `/cowork-setup`
6. `## Handoff Workflow` — 5 numbered steps (see below)
7. `## Receiving Deliverables` — check `outbox/` for Cowork output
8. `## Known Pitfalls` — table with common issues and solutions
9. `## SharePoint Sync Setup` — inline abraunegg/onedrive setup (replaces separate reference file)

**Handoff Workflow — 5 Steps (updated):**
- Step 1: Confirm prerequisites (~/cowork-bridge/ exists, manifest.json readable)
- Step 2: Auto-detect + confirm deliverable type (audit/integration/data) — **explicit user confirmation required before any filesystem writes**
- Step 3: Collect artifacts (list current session outputs, let user select/confirm); warn about credential sanitization
- Step 4: Package to `~/cowork-bridge/inbox/{YYYYMMDD}-{HHmmss}-{uuid8}/` + update `manifest.json` (lock → backup → merge → unlock)
- Step 5: Generate Cowork prompt inline (display to user + offer clipboard copy via `pbcopy`/`xclip`)

**Agent-Native Research Insights: Outcome-Oriented Prompt**

Generated Cowork prompt should be outcome-oriented, not procedural:
```markdown
# Task: Create [Client] [DeliverableType]

You have access to ~/cowork-bridge/ in your workspace.

## Ready for you: inbox/{artifact-id}/
Files: analysis.md, data.json, metadata.json
Template: templates/audit-to-report.md

## Your goal
Produce a polished client-facing report. Read the template first — it tells you
exactly what to create and where to save it.

When complete, write a brief summary to: outbox/{artifact-id}-done.md
```

This approach (outcome + pointer to template) lets Cowork adapt execution rather than following rigid steps that may not match its current context.

**Critical design decisions:**
- Auto-detect from conversation context, always confirm with user before ANY filesystem writes
- Naming: `{YYYYMMDD}-{HHmmss}-{uuid8}` (timestamp + 8-char uuid for guaranteed uniqueness)
- If manifest lock file exists, warn user and abort gracefully
- If manifest is missing/malformed, prompt user to run `/cowork-setup` before continuing
- Templates copied from plugin to user's `~/cowork-bridge/templates/` on first setup — skill reads user's copy (allows customization)
- Plugin self-location: `find ~/.claude/plugins -name "cowork-bridge" -type d | head -1`
- NO `prompts/` folder — generate prompt inline (display + clipboard); simpler, less filesystem surface

#### `manifest-template.json`
```json
{
  "version": "1.0",
  "initialized_at": "{ISO_8601_TIMESTAMP}",
  "artifacts": []
}
```

Each artifact entry:
```json
{
  "id": "20260402-143022-a1b2c3d4",
  "type": "audit",
  "status": "ready",
  "created": "2026-04-02T14:30:22Z",
  "project": "celigo-health-digest",
  "client": "TwistedX",
  "deliverable_type": "report",
  "template": "audit-to-report.md",
  "path": "inbox/20260402-143022-a1b2c3d4/",
  "summary": "Security audit of Celigo health digest flow",
  "files": ["analysis.md", "data.json", "metadata.json"]
}
```

Note: ID format changed from `{project}-{seq:02d}` to `{YYYYMMDD}-{HHmmss}-{uuid8}` for uniqueness.

#### Template Files (Pure Markdown Cowork Instructions)

**`audit-to-report.md`** — instructs Cowork to:
- Read `metadata.json` first for client/scope/severity context
- Read `analysis.md` for detailed findings
- Read `data.json` for structured evidence
- Produce DOCX/PDF: cover page → executive summary → scope → findings table → detailed findings (per severity) → remediation roadmap → appendix
- Professional tone, non-technical executive audience for summary, technical detail in findings
- Save to `~/cowork-bridge/outbox/{date}-{project}-audit-report.docx`
- Write completion marker: `~/cowork-bridge/outbox/{artifact-id}-done.md`

**`analysis-to-proposal.md`** — instructs Cowork to:
- Read system analysis artifacts (API docs, flow diagrams, gap analysis)
- Produce implementation proposal: problem statement → proposed architecture → phases → timeline → investment → risk mitigation
- Persuasive business tone with data backing
- Save to `~/cowork-bridge/outbox/{date}-{project}-integration-proposal.docx`
- Write completion marker: `~/cowork-bridge/outbox/{artifact-id}-done.md`

**`data-to-deck.md`** — instructs Cowork to:
- Read data artifacts (JSON/CSV exports, metrics, trend analysis)
- Produce slide-by-slide outline: title → agenda → key findings → data deep-dives → trends → recommendations → next steps
- For each slide: title, key message, data points, visualization type, speaker notes
- Save to `~/cowork-bridge/outbox/{date}-{project}-deck.pptx`
- Write completion marker: `~/cowork-bridge/outbox/{artifact-id}-done.md`

#### SharePoint Sync Setup (inline in SKILL.md `## SharePoint Sync Setup`)

One-time setup of `abraunegg/onedrive`:

1. **Install** (Ubuntu/Debian): `sudo apt install onedrive`
2. **Authenticate** (Device Flow — works on headless servers):
   ```bash
   onedrive --auth-files authUrl:authResponse
   # Follow URL printed, paste response back
   ```
3. **Configure** `~/.config/onedrive/config`:
   ```ini
   sync_dir = ~/cowork-bridge
   drive_id = <SharePoint library drive_id>
   monitor_interval = 45
   skip_dotfiles = true
   skip_symlinks = true
   ```
4. **Start daemon**: `systemctl --user enable --now onedrive`
5. **Verify**: `touch ~/cowork-bridge/test-sync.txt` → confirm in SharePoint → `rm ~/cowork-bridge/test-sync.txt`

**DevOps Research Insights:**
- `monitor_interval = 45` (not default 300) gives ~45s sync latency — acceptable for handoff workflows
- `skip_dotfiles = true` prevents `.DS_Store` and other hidden files from syncing
- Device Flow (`--auth-files`) is the correct OAuth method for headless/SSH servers — no browser needed on server
- Protect token: `chmod 600 ~/.config/onedrive/refresh_token`
- abraunegg handles SharePoint's silent file modification (avoids false conflict detections)

#### `commands/cowork-setup.md`
```yaml
---
description: Initialize the ~/cowork-bridge/ workspace and configure SharePoint sync
---
```
Body — Step-by-step initialization:
1. Check if `~/cowork-bridge/` exists; if so, confirm idempotent reinit
2. Create folder structure: `inbox/`, `outbox/`, `templates/`
3. Locate plugin: `find ~/.claude/plugins -name "cowork-bridge" -type d | head -1`
4. Copy templates from plugin to `~/cowork-bridge/templates/`
5. Initialize `manifest.json` from `manifest-template.json`
6. Print SharePoint sync setup instructions (abraunegg Device Flow steps)
7. Confirm completion with what was created

**YAGNI simplification:** Removed `prompts/` and `archive/` from init dirs. Prompts are generated inline; archiving is manual user action (move files), no dedicated folder needed.

#### `commands/cowork-handoff.md`
```yaml
---
description: Package current session artifacts and hand off to Claude Cowork
---
```
Body: Activates the `cowork-handoff` skill and guides through the 5-step workflow.

#### Marketplace Registration (`.claude-plugin/marketplace.json`)
Add to `plugins` array:
```json
{
  "name": "cowork-bridge",
  "source": "./plugins/cowork-bridge",
  "description": "Shared workspace bridge between Claude Code and Claude Cowork. Packages artifacts, generates Cowork-ready prompts with deliverable templates, and tracks handoffs via manifest. Syncs via SharePoint/OneDrive.",
  "version": "1.0.0",
  "keywords": ["cowork", "sharepoint", "handoff", "deliverables", "collaboration"]
}
```

## Acceptance Criteria

### Functional Requirements

- [x] **AC 1.1** `/cowork-setup` creates `~/cowork-bridge/` with `inbox/`, `outbox/`, `templates/`
- [x] **AC 1.2** `/cowork-setup` copies templates from plugin to `~/cowork-bridge/templates/`
- [x] **AC 1.3** `/cowork-setup` initializes valid `manifest.json` with schema version `"1.0"`
- [x] **AC 1.4** `/cowork-setup` is idempotent — safe to rerun without destroying existing state
- [x] **AC 1.5** `/cowork-setup` provides SharePoint sync guidance output (Device Flow auth steps)
- [x] **AC 2.1** `/cowork-handoff` detects deliverable type from conversation context and confirms with user
- [x] **AC 2.2** `/cowork-handoff` creates correctly named artifact folder: `{YYYYMMDD}-{HHmmss}-{uuid8}/`
- [x] **AC 2.3** `/cowork-handoff` sanitizes project name (alphanumeric/hyphens only, max 40 chars)
- [x] **AC 2.4** `/cowork-handoff` updates `manifest.json` safely (lock → backup → merge → write → unlock)
- [x] **AC 2.5** `/cowork-handoff` generates Cowork-ready prompt and displays inline (+ clipboard offer)
- [x] **AC 2.6** Cowork prompt is outcome-oriented: goal + artifact path + template reference + done marker path
- [x] **AC 3.1** Plugin appears in marketplace after `marketplace.json` registration
- [x] **AC 3.2** `/cowork-handoff` and `/cowork-setup` activate correctly from slash command
- [x] **AC 3.3** SKILL.md has `disable-model-invocation: true` and scoped `allowed-tools`

### Non-Functional Requirements

- [x] SKILL.md is 200-300 lines (matching marketplace patterns)
- [x] All templates include completion marker instructions (`outbox/{id}-done.md`)
- [x] Folder naming is consistent with `{YYYYMMDD}-{HHmmss}-{uuid8}` convention
- [x] `plugin.json` version matches `marketplace.json` version (`1.0.0`)
- [x] No hardcoded absolute paths — use dynamic discovery pattern
- [x] OAuth token file has `600` permissions in setup guide

### Quality Gates

- [x] `plugin.json` is valid JSON (check with `python3 -m json.tool`)
- [x] `manifest-template.json` is valid JSON
- [x] All referenced template files exist before SKILL.md is created
- [x] All command files have valid YAML frontmatter

## Edge Cases Addressed

| Edge Case | Handling |
|---|---|
| `/cowork-setup` rerun | Idempotent — skips existing dirs, preserves manifest |
| Manifest malformed/missing | Prompt to run `/cowork-setup` before continuing |
| Manifest lock file exists | Abort with message: "Another handoff in progress, retry in a moment" |
| No artifacts available | Offer conversation-export type; show empty state guidance |
| Naming collision | Impossible — HHmmss + uuid8 guarantees uniqueness |
| Deliverable type ambiguous | Interactive prompt with 3 options (audit/integration/data) |
| Templates missing from user dir | Prompt to rerun `/cowork-setup` to restore |
| Plugin updated with new templates | Rerun `/cowork-setup` to refresh user templates |
| Project name with special chars | Sanitize: alphanumeric/hyphens only, max 40 chars |
| Credential leakage | User confirmation gate before packaging — explicit warning shown |
| abraunegg not installed | Detect in setup, show install instructions, continue without sync |

## Dependencies & Prerequisites

- `abraunegg/onedrive` installed and configured for SharePoint sync (user one-time setup, instructions in `/cowork-setup` output)
- Cowork has SharePoint Document Library configured via its connector (user one-time setup)
- `~/cowork-bridge/` initialized via `/cowork-setup` before first `/cowork-handoff`

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| User never sets up SharePoint sync | HIGH | LOW | Plugin works locally without sync; sync is optional enhancement |
| manifest.json corruption | LOW | MEDIUM | Lock file + atomic backup before each write |
| Template not found | LOW | LOW | Fallback: use inline minimal template in SKILL.md |
| Credential leakage in artifacts | MEDIUM | HIGH | Explicit user warning before packaging; user confirmation required |
| Path traversal via project name | LOW | MEDIUM | Sanitize project names before filesystem use |
| abraunegg auth failure on headless | MEDIUM | LOW | Document Device Flow OAuth in setup; offer local-only mode |

## Future Considerations

- `/cowork-doctor` diagnostic command (check manifest health, directory permissions, template integrity)
- `/cowork-receive` command to explicitly check outbox for Cowork deliverables (look for `-done.md` markers)
- `/cowork-status` to list all pending artifacts from manifest
- MCP bridge server for tighter real-time integration (currently out of scope)
- Custom deliverable types beyond the 3 core pipelines

## References

### Internal References
- Brainstorm: `docs/brainstorms/2026-04-02-cowork-bridge-brainstorm.md`
- Plugin conventions: `docs/CUSTOMIZATION.md`
- Similar plugin (first-run pattern): `plugins/portable-setup/commands/install.md`
- Marketplace format: `.claude-plugin/marketplace.json`
- SKILL.md patterns: `plugins/claudekit-skills/skills/*/SKILL.md`

### External References
- [abraunegg/onedrive GitHub](https://github.com/abraunegg/onedrive) — 12k stars, Linux SharePoint sync
- [abraunegg SharePoint guide](https://abraunegg.github.io/) — configuration for Document Libraries
- [abraunegg Device Flow auth](https://github.com/abraunegg/onedrive/blob/master/docs/usage.md#authorization-when-operating-headless-or-without-a-gui) — headless OAuth
- [Claude Cowork SharePoint connector](https://support.claude.com/en/articles/11176164-use-connectors-to-extend-claude-s-capabilities)

## Verification Checklist

### Plugin
- [ ] `plugin.json` validates as JSON
- [ ] Plugin listed after `marketplace.json` update: `/plugin list`
- [ ] Commands register: try `/cowork-setup` and `/cowork-handoff`
- [ ] Skill activates on keyword: mention "hand off to cowork" in conversation
- [ ] SKILL.md has `disable-model-invocation: true`

### First Run
- [ ] `/cowork-setup` → `~/cowork-bridge/` created with `inbox/`, `outbox/`, `templates/`
- [ ] Templates exist in `~/cowork-bridge/templates/` (3 .md files)
- [ ] `manifest.json` valid JSON with `"version": "1.0"`
- [ ] Rerun `/cowork-setup` → no error, existing dirs preserved

### Handoff Flow
- [ ] `/cowork-handoff` → prompts for deliverable type with confirmation
- [ ] Creates artifact folder with `{YYYYMMDD}-{HHmmss}-{uuid8}` naming
- [ ] `manifest.json` updated with new entry (lock file created/removed)
- [ ] Prompt generated inline (displayed + clipboard offered)
- [ ] Prompt is outcome-oriented with done marker path

### Security
- [ ] Credential warning displayed before packaging
- [ ] Project name with `../` is sanitized to `--` (path traversal blocked)
- [ ] abraunegg token file has `600` permissions (documented in setup)

### End-to-End (Manual)
- [ ] Create sample analysis files → run `/cowork-handoff` → verify in `~/cowork-bridge/inbox/`
- [ ] (If SharePoint configured) Verify files appear in SharePoint library within ~45 seconds
- [ ] Paste generated prompt into Cowork → verify it finds the files and produces deliverable
- [ ] Cowork writes `outbox/{id}-done.md` → verify Claude Code can detect completion
