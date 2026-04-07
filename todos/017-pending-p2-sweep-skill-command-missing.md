---
status: pending
priority: p2
issue_id: "017"
tags: [code-review, agent-native, azure-ad, sweep]
dependencies: [013]
---

# 017 — sweep.py has no skill entry or command — invisible to agents

## Problem Statement

`sweep.py` is the highest-value new tool in this PR (compromise detection with 6 detection vectors) but has no skill entry, no command, and is not mentioned in any SKILL.md. An agent receiving "run a compromise sweep on Azure AD" has no path to discover or invoke this tool. Once the import bug (todo #013) is fixed, this needs to be wired up for agent use.

## Findings

- **File**: `plugins/m365-skills/skills/azure-ad/SKILL.md` — no mention of sweep.py
- **File**: `plugins/m365-skills/plugin.json` — `"commands": []` (empty, no sweep command)
- **Agent**: agent-native-reviewer

## Proposed Solutions

### Option A: Add sweep section to azure-ad SKILL.md + create command (Recommended)

Add to `azure-ad/SKILL.md` under a new `## Compromise Sweep` section:

```markdown
## Compromise Sweep

Detect potential account compromises across 6 detection vectors.

```bash
cd plugins/m365-skills/skills/azure-ad
python3 scripts/sweep.py --hours 48
python3 scripts/sweep.py --ips 203.0.113.50,198.51.100.20 --hours 48
python3 scripts/sweep.py --hours 72 --mfa-window 15 --json > sweep_report.json
```

Create `/azure-ad-sweep` command in `plugins/m365-skills/commands/azure-ad-sweep.md`.

- **Effort**: Small
- **Risk**: Low (blocked by #013)

### Option B: Add to existing mimecast-audit SKILL.md as a related capability
Reference sweep.py as a complementary tool when investigating audit findings.

- **Effort**: Tiny
- **Risk**: Low

## Recommended Action

Option A — create a dedicated command and add to the azure-ad SKILL.md.

## Technical Details

- **Files to create/modify**:
  - `plugins/m365-skills/skills/azure-ad/SKILL.md` (add sweep section)
  - `plugins/m365-skills/commands/azure-ad-sweep.md` (new command)
  - `plugins/m365-skills/plugin.json` (add command to `"commands"` array, bump version to 1.1.0)
  - `.claude-plugin/marketplace.json` (update m365-skills version)

## Acceptance Criteria

- [ ] Claude activates sweep.py when asked about "compromise sweep", "account compromise", "MFA fatigue", "suspicious sign-ins"
- [ ] `/azure-ad-sweep` command exists and provides usage instructions
- [ ] `m365-skills/plugin.json` version bumped

## Work Log

- 2026-04-07: Identified by agent-native-reviewer; blocked by #013 (broken import)
