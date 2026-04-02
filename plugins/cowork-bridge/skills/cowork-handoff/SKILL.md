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
  - Bash(test *)
  - Bash(echo *)
  - Bash(pbcopy *)
  - Bash(xclip *)
---

## Overview

This skill packages Claude Code session artifacts (analysis files, data exports, reports) and
prepares them for handoff to Claude Cowork. It creates a structured artifact folder in
`~/cowork-bridge/inbox/`, updates the shared manifest, and generates an outcome-oriented
prompt for Cowork to pick up and produce a polished client deliverable.

Requires `~/cowork-bridge/` to be initialized. Run `/cowork-setup` if not yet done.

## When to Use

Trigger phrases that activate this skill:
- "hand off to cowork" / "handoff to cowork"
- "package for cowork" / "package this for cowork"
- "send to cowork"
- "prepare a client deliverable"
- "cowork bridge"
- "create a report from this analysis"
- "turn this into a proposal"
- "make a deck from this data"
- "handoff" (in context of Cowork or deliverables)

## Prerequisites

Before running this skill:
1. `~/cowork-bridge/` must exist with `inbox/`, `outbox/`, `templates/` subdirectories
2. `~/cowork-bridge/manifest.json` must exist and be valid JSON
3. `~/cowork-bridge/templates/` must contain at least one template file

If any of these are missing, stop and tell the user: **"Run `/cowork-setup` first to initialize
the workspace."**

## Deliverable Types

| Type | Code Generates | Cowork Produces | Template |
|------|---------------|-----------------|----------|
| `audit` | Findings .md, JSON evidence, severity ratings | Client-facing PDF/DOCX report with exec summary | `audit-to-report.md` |
| `integration` | API analysis, flow diagrams, capability matrix | Implementation proposal with timeline + investment | `analysis-to-proposal.md` |
| `data` | Structured JSON/CSV, metrics, trend analysis | Slide deck outline or visual summary | `data-to-deck.md` |

## First-Run Check

Before proceeding with any handoff, verify the workspace exists:

```bash
test -d ~/cowork-bridge/inbox || echo "MISSING"
test -f ~/cowork-bridge/manifest.json || echo "MISSING"
test -d ~/cowork-bridge/templates || echo "MISSING"
```

If any check fails:
- Tell the user: "Your `~/cowork-bridge/` workspace is not initialized. Run `/cowork-setup` to set it up."
- Stop here — do not proceed.

Also check for a stale lock file:
```bash
test -f ~/cowork-bridge/manifest.json.lock && echo "LOCKED"
```

If locked: "Another handoff appears to be in progress (or a previous one was interrupted).
If no other handoff is running, delete `~/cowork-bridge/manifest.json.lock` and retry."

## Handoff Workflow

### Step 1: Confirm Deliverable Type

Detect the deliverable type from conversation context:
- Mentions of "security", "vulnerabilities", "audit", "findings" → likely `audit`
- Mentions of "integration", "API", "proposal", "implementation" → likely `integration`
- Mentions of "data", "metrics", "report", "deck", "trends" → likely `data`

Always confirm with the user:
> "I'll package this as an **[detected type]** handoff, which will produce a **[output]** in Cowork.
> Does that sound right? (Or choose: audit / integration / data)"

**Do not write any files until the user confirms.**

### Step 2: Collect Artifacts

Ask the user to identify the files to package:
> "Which files from this session should I include? List the paths, or say 'all files we created'."

**Security warning — always show before packaging:**
> "Before I package these files, please confirm they don't contain API keys, passwords,
> or credentials. I'll proceed once you confirm."

Collect:
- `analysis.md` or equivalent — the primary findings/analysis file
- `data.json` or equivalent — structured data/evidence
- Any additional supporting files the user specifies

Also collect metadata from the user:
- Project name (will be sanitized to alphanumeric/hyphens, max 40 chars)
- Client name
- Brief summary (1 sentence describing what was analyzed)

### Step 3: Package Artifacts

Generate a unique artifact ID:
```bash
ARTIFACT_ID="$(date +%Y%m%d-%H%M%S)-$(uuidgen 2>/dev/null | head -c 8 || cat /proc/sys/kernel/random/uuid 2>/dev/null | head -c 8 || echo "$(date +%N | head -c 8)")"
```

Sanitize the project name:
```bash
PROJECT_CLEAN=$(echo "$PROJECT_NAME" | sed 's/[^a-zA-Z0-9_-]/-/g' | cut -c1-40)
```

Create the artifact folder:
```bash
mkdir -p ~/cowork-bridge/inbox/$ARTIFACT_ID
```

Copy files into the artifact folder:
```bash
cp "$FILE1" ~/cowork-bridge/inbox/$ARTIFACT_ID/analysis.md
cp "$FILE2" ~/cowork-bridge/inbox/$ARTIFACT_ID/data.json
```

Write `metadata.json` into the artifact folder:
```json
{
  "id": "{ARTIFACT_ID}",
  "type": "{TYPE}",
  "created": "{ISO_TIMESTAMP}",
  "project": "{PROJECT_CLEAN}",
  "client": "{CLIENT_NAME}",
  "deliverable_type": "{DELIVERABLE_TYPE}",
  "template": "{TEMPLATE_FILENAME}",
  "summary": "{USER_SUMMARY}"
}
```

### Step 4: Update manifest.json

Safely update the manifest:

1. Check for and create lock file:
   ```bash
   touch ~/cowork-bridge/manifest.json.lock
   ```

2. Backup current manifest:
   ```bash
   cp ~/cowork-bridge/manifest.json ~/cowork-bridge/manifest.json.bak
   ```

3. Read current manifest, append new artifact entry, write updated manifest using the Write tool.

   New artifact entry to append to `artifacts` array:
   ```json
   {
     "id": "{ARTIFACT_ID}",
     "type": "{TYPE}",
     "status": "ready",
     "created": "{ISO_TIMESTAMP}",
     "project": "{PROJECT_CLEAN}",
     "client": "{CLIENT_NAME}",
     "deliverable_type": "{DELIVERABLE_TYPE}",
     "template": "{TEMPLATE_FILENAME}",
     "path": "inbox/{ARTIFACT_ID}/",
     "summary": "{USER_SUMMARY}",
     "files": ["{FILE_LIST}"]
   }
   ```

4. Remove lock file:
   ```bash
   rm ~/cowork-bridge/manifest.json.lock
   ```

### Step 5: Generate and Display Cowork Prompt

Generate an outcome-oriented prompt (do NOT write it to a file — display inline):

```markdown
# Task: Create [Client] [DeliverableType]

You have access to ~/cowork-bridge/ in your workspace.

## Ready for you: inbox/{ARTIFACT_ID}/
Files: {file_list}
Template: templates/{TEMPLATE_FILENAME}

## Your goal
Produce a polished client-facing [deliverable type]. Read the template first — it tells
you exactly what to create and where to save it.

When complete, write a brief summary to: outbox/{ARTIFACT_ID}-done.md

## Context
- Client: {CLIENT_NAME}
- Project: {PROJECT_CLEAN}
- Summary: {USER_SUMMARY}
```

Display this prompt to the user, then:
1. Offer to copy to clipboard:
   ```bash
   echo "$PROMPT" | pbcopy 2>/dev/null || echo "$PROMPT" | xclip -selection clipboard 2>/dev/null
   ```
2. Inform the user:
   > "Artifact packaged at `inbox/{ARTIFACT_ID}/`. SharePoint sync takes ~10–45 seconds.
   > Paste the above prompt into Cowork after a brief pause."
3. Mention checking for completion: "When Cowork finishes, check `~/cowork-bridge/outbox/` for your deliverable."

## Receiving Deliverables

To check if Cowork has completed a handoff:
```bash
ls ~/cowork-bridge/outbox/
```

Look for:
- `{ARTIFACT_ID}-done.md` — Cowork's completion marker
- `{date}-{project}-{type}.docx` or `.pptx` — the deliverable file

To list all pending artifacts from the manifest:
```bash
cat ~/cowork-bridge/manifest.json
```
Look for entries with `"status": "ready"` or `"in-progress"`.

To mark an artifact as delivered (manual update to manifest):
Open `~/cowork-bridge/manifest.json` and change `"status": "ready"` → `"status": "delivered"` for the completed artifact.

## Known Pitfalls

| Issue | Cause | Solution |
|-------|-------|----------|
| `manifest.json.lock` exists at start | Previous handoff interrupted | Delete lock file if no handoff is running: `rm ~/cowork-bridge/manifest.json.lock` |
| Files not appearing in SharePoint | abraunegg not running | Start: `systemctl --user start onedrive` or `onedrive --monitor &` |
| Cowork can't find files | SharePoint connector not configured | Ensure Cowork SharePoint connector points to the correct library |
| Template not found | Setup not run or templates cleared | Run `/cowork-setup` to restore templates |
| `uuidgen` not available | Not installed | Install: `sudo apt install uuid-runtime` |
| Manifest malformed | Partial write from previous error | Restore from backup: `cp ~/cowork-bridge/manifest.json.bak ~/cowork-bridge/manifest.json` |

## SharePoint Sync Setup

One-time setup using `abraunegg/onedrive`:

**1. Install:**
```bash
sudo apt install onedrive        # Ubuntu/Debian
# Or: sudo snap install onedrive
```

**2. Authenticate (Device Flow — works on headless/SSH servers):**
```bash
onedrive --auth-files authUrl:authResponse
```
Follow the URL printed to screen, complete auth in your browser, paste the response URL back.

**3. Configure** `~/.config/onedrive/config`:
```ini
sync_dir = ~/cowork-bridge
drive_id = <your SharePoint library drive_id>
monitor_interval = 45
skip_dotfiles = true
skip_symlinks = true
```
Get `drive_id` from SharePoint URL or abraunegg's `--list-shared-libraries` flag.

**4. Start daemon:**
```bash
systemctl --user enable --now onedrive
# Or for one-time: onedrive --monitor &
```

**5. Verify:**
```bash
touch ~/cowork-bridge/test-sync.txt
# Wait ~45 seconds, check SharePoint
rm ~/cowork-bridge/test-sync.txt
```

**Security note:** Protect OAuth token: `chmod 600 ~/.config/onedrive/refresh_token`

**Plugin works without SharePoint sync** — files are packaged locally and Cowork can access
them directly if running on the same machine or mapped network share.
