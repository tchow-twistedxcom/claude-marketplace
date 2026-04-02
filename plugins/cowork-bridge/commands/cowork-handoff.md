---
description: Package current session artifacts and hand off to Claude Cowork for client deliverable creation
---

# Cowork Handoff

This command packages artifacts from the current Claude Code session and prepares them
for Claude Cowork to transform into a polished client deliverable (report, proposal, or deck).

## Prerequisites

`~/cowork-bridge/` must be initialized. If you haven't run setup yet:

```
/cowork-setup
```

---

## Activating the Skill

This command activates the `cowork-handoff` skill, which will guide you through the
following 5-step workflow:

1. **Confirm deliverable type** — audit → report, integration → proposal, or data → deck
2. **Collect artifacts** — identify which files from this session to package
3. **Package** — creates a uniquely-named folder in `~/cowork-bridge/inbox/`
4. **Update manifest** — records the handoff in `manifest.json`
5. **Generate Cowork prompt** — an outcome-oriented prompt ready to paste into Cowork

---

## Quick Reference

**What gets created:**
- `~/cowork-bridge/inbox/{YYYYMMDD}-{HHmmss}-{uuid8}/` — artifact folder
- `~/cowork-bridge/manifest.json` — updated with new entry

**What you get:**
- A ready-to-paste Cowork prompt with the artifact location and instructions
- Clipboard copy offered automatically

**After handoff:**
- Check `~/cowork-bridge/outbox/` for Cowork's completed deliverable
- Look for `{artifact-id}-done.md` as the completion marker

---

Activate the `cowork-handoff` skill now and begin the 5-step workflow.
