---
status: complete
priority: p3
issue_id: "010"
tags: [code-review, agent-native, mimecast, documentation]
dependencies: []
---

# 010 — SKILL.md missing awareness training CLI examples

## Problem Statement

`plugins/mimecast-skills/skills/mimecast-api/SKILL.md` was updated with awareness training activation keywords, but does not include example CLI invocations for the 12 new `awareness` subcommands. Agents activating this skill won't know how to use the new operations without the reference doc.

## Findings

- **Agent**: agent-native-reviewer (P3)
- **File**: `plugins/mimecast-skills/skills/mimecast-api/SKILL.md`

## Proposed Solutions

### Option A: Add an Awareness Training section to SKILL.md

Add a `### Awareness Training` section with representative CLI examples:

```bash
# Training campaigns
python3 scripts/mimecast_api.py awareness campaigns
python3 scripts/mimecast_api.py awareness safe-score --email user@example.com
python3 scripts/mimecast_api.py awareness phishing --campaign-id CAMP123
python3 scripts/mimecast_api.py awareness watchlist
```

- **Pros**: Agents immediately have usage patterns; reference doc already exists for full detail
- **Effort**: Tiny
- **Risk**: Very low

### Recommended
**Option A** — add section with representative examples.

## Technical Details

- **Affected files**: `plugins/mimecast-skills/skills/mimecast-api/SKILL.md`

## Acceptance Criteria

- [ ] SKILL.md has `### Awareness Training` section
- [ ] Section shows at least 4 representative examples
- [ ] Examples match actual CLI syntax (resource + action pattern)

## Work Log

- 2026-04-04: Created by code review (agent-native-reviewer finding)
