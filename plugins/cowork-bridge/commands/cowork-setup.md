---
description: Initialize the ~/cowork-bridge/ workspace and configure SharePoint sync for Claude Code ↔ Cowork collaboration
---

# Cowork Bridge Setup

This command initializes the `~/cowork-bridge/` shared workspace used to exchange artifacts
between Claude Code and Claude Cowork.

## What This Does

1. Creates the `~/cowork-bridge/` folder structure
2. Copies deliverable templates from the plugin
3. Initializes `manifest.json` to track artifact handoffs
4. Prints SharePoint sync setup instructions

This command is **idempotent** — safe to run multiple times. Existing directories and a valid
`manifest.json` will not be overwritten.

---

## Step 1: Check Existing State

```bash
test -d ~/cowork-bridge && echo "EXISTS" || echo "NEW"
```

If `~/cowork-bridge/` already exists:
- Tell the user: "Found existing workspace at `~/cowork-bridge/`. Running in refresh mode — will add missing dirs and templates without overwriting existing data."

If it doesn't exist:
- Tell the user: "Creating new workspace at `~/cowork-bridge/`."

---

## Step 2: Create Directory Structure

```bash
mkdir -p ~/cowork-bridge/inbox
mkdir -p ~/cowork-bridge/outbox
mkdir -p ~/cowork-bridge/templates
```

Confirm each directory was created (or already existed).

---

## Step 3: Locate Plugin and Copy Templates

Find the plugin directory:
```bash
PLUGIN_DIR=$(find ~/.claude/plugins -name "cowork-bridge" -type d 2>/dev/null | head -1)
```

If `PLUGIN_DIR` is empty:
- Tell the user: "Could not locate the cowork-bridge plugin. Ensure it is installed via your marketplace."
- Stop here.

Copy templates (only if they don't already exist in `~/cowork-bridge/templates/`):
```bash
for tmpl in audit-to-report.md analysis-to-proposal.md data-to-deck.md; do
  if [ ! -f ~/cowork-bridge/templates/$tmpl ]; then
    cp "$PLUGIN_DIR/templates/$tmpl" ~/cowork-bridge/templates/
    echo "Copied: $tmpl"
  else
    echo "Skipped (exists): $tmpl"
  fi
done
```

---

## Step 4: Initialize manifest.json

If `~/cowork-bridge/manifest.json` does **not** exist:
```bash
test -f ~/cowork-bridge/manifest.json || echo "MISSING"
```

If missing, create it with the current timestamp:
```json
{
  "version": "1.0",
  "initialized_at": "<current ISO 8601 timestamp>",
  "artifacts": []
}
```

Use `date -u +"%Y-%m-%dT%H:%M:%SZ"` to get the current UTC timestamp.

If `manifest.json` already exists, leave it untouched and report: "manifest.json already exists — preserved."

---

## Step 5: Print SharePoint Sync Instructions

Display the following setup guide for `abraunegg/onedrive`:

---

**Optional: SharePoint Sync Setup**

To sync `~/cowork-bridge/` to SharePoint so Cowork can access your artifacts remotely:

**Install abraunegg/onedrive:**
```bash
sudo apt install onedrive
```

**Authenticate (Device Flow — works on SSH/headless servers):**
```bash
onedrive --auth-files authUrl:authResponse
# Open the URL in your browser, authenticate, paste the response URL back
```

**Configure** `~/.config/onedrive/config`:
```ini
sync_dir = ~/cowork-bridge
drive_id = <your SharePoint Document Library drive_id>
monitor_interval = 45
skip_dotfiles = true
skip_symlinks = true
```

To find your `drive_id`: run `onedrive --list-shared-libraries` after authentication.

**Start daemon:**
```bash
systemctl --user enable --now onedrive
```

**Test sync:**
```bash
touch ~/cowork-bridge/test-sync.txt
# Wait ~45 seconds and verify the file appears in your SharePoint library
rm ~/cowork-bridge/test-sync.txt
```

**Security:** `chmod 600 ~/.config/onedrive/refresh_token`

> Note: SharePoint sync is optional. The plugin works locally without it — Cowork can
> access `~/cowork-bridge/` directly if running on the same machine.

---

## Step 6: Confirm Completion

After all steps complete, summarize:

```
✓ Workspace ready at ~/cowork-bridge/
  ├── inbox/          (Claude Code → Cowork artifacts)
  ├── outbox/         (Cowork → Claude Code deliverables)
  └── templates/      (3 deliverable templates)
      ├── audit-to-report.md
      ├── analysis-to-proposal.md
      └── data-to-deck.md
✓ manifest.json initialized (or preserved)

Next: Run /cowork-handoff after completing an analysis session to package artifacts for Cowork.
```
