---
status: pending
priority: p3
issue_id: "107"
tags: [code-review, quality, azure-ad]
dependencies: []
---

# 107 — `SKILL.md` line 201: `dry_run=True` should be `confirm=False` (stale parameter name)

## Problem Statement

`SKILL.md` line 201 documents a parameter as `dry_run=True default` but the actual parameter in `server.py` was renamed to `confirm` (with `confirm=False` as the safe default). The documentation is stale after the rename, which will confuse users and agents reading the skill description to understand how to invoke the tool safely.

## Findings

- **`plugins/m365-skills/skills/azure-ad/SKILL.md` line 201**: refers to `dry_run=True` as the safe default
- **`server.py`**: parameter is `confirm: bool = False` (not `dry_run`)
- `confirm=False` means "don't execute" (preview mode); the SKILL.md phrasing inverts the semantics
- Flagged by: pattern-recognition-specialist (7th review pass)

## Proposed Solutions

### Option A: Update SKILL.md to say `confirm=False` (recommended)

Replace the stale `dry_run=True default` reference with `confirm=False (default — preview mode)`.

- **Effort**: Trivial | **Risk**: None

## Acceptance Criteria

- [ ] SKILL.md line 201 uses `confirm=False` and correctly describes preview vs execute semantics

## Work Log

- 2026-04-08: Identified in 7th code review pass (pattern-recognition-specialist) — stale after dry_run→confirm rename
