---
status: pending
priority: p1
issue_id: "011"
tags: [code-review, security, pii, data-exposure]
dependencies: []
---

# 011 — PII committed to repository: audit-2026-04-04.md must be removed from git history

## Problem Statement

`plugins/mimecast-skills/audit-2026-04-04.md` is a 931-line live tenant audit snapshot containing real PII and sensitive internal data that was committed to the repository. The `.gitignore` does not exclude it. Anyone with read access to this repository (or its history) can enumerate employee names, email addresses, security tooling, and internal API identifiers.

This file must be removed from git history before the PR is merged.

## Findings

- **File**: `plugins/mimecast-skills/audit-2026-04-04.md`
- **Agents**: security-sentinel (CRIT-1), architecture-strategist
- **Contains**:
  - Full names + email addresses of hundreds of current and former employees across 7 domains (`@twistedxboots.com`, `@twistedx.com`, `@twxlb.com`, `@blackstarboots.com`, `@tamarindofootwear.com`, `@cellsole.com`, `@wranglerfootwear.com`)
  - Internal API integration GUIDs (Arctic Wolf IH, MCP integration, Claude Integration)
  - 791 "orphaned" Mimecast accounts with ready-to-paste delete CLI commands
  - 48 disabled-but-active accounts (former employees still in Mimecast)
  - Security tooling enumeration (Arctic Wolf, FreshDesk, Certify)
  - Mimecast ingestion GUIDs for cloud-sync service accounts

## Proposed Solutions

### Option A: git filter-repo (Recommended)
Remove the file from all git history and add `.gitignore` rule.

```bash
# Remove from history
pip install git-filter-repo
git filter-repo --path plugins/mimecast-skills/audit-2026-04-04.md --invert-paths

# Add gitignore rule
echo "plugins/mimecast-skills/audit-*.md" >> .gitignore
git add .gitignore
git commit -m "chore: exclude audit snapshots from version control"

# Force push (coordinate with team first)
git push origin feat/mimecast-m365-audit --force
```

- **Pros**: Completely purges from history
- **Cons**: Requires force push; all clones need to re-sync
- **Effort**: Small
- **Risk**: Medium (force push coordination)

### Option B: Remove file + gitignore (no history purge)
If the repo is private and history exposure is acceptable:

```bash
git rm plugins/mimecast-skills/audit-2026-04-04.md
echo "plugins/mimecast-skills/audit-*.md" >> .gitignore
git add .gitignore
git commit -m "chore: remove audit snapshot and add gitignore rule"
```

- **Pros**: Simpler, no force push needed
- **Cons**: File remains in git history — still accessible via `git show <commit>`
- **Effort**: Tiny
- **Risk**: Low for merge, medium for data exposure if repo ever made public

## Recommended Action

Option A if any risk of repo becoming public. Option B minimum for merge.

## Technical Details

- **Affected files**: `plugins/mimecast-skills/audit-2026-04-04.md`
- **Related**: `.gitignore` needs `plugins/mimecast-skills/audit-*.md` pattern

## Acceptance Criteria

- [ ] `audit-2026-04-04.md` is no longer tracked in the repository
- [ ] `.gitignore` excludes `plugins/mimecast-skills/audit-*.md`
- [ ] README or SKILL.md notes that audit output should not be committed

## Work Log

- 2026-04-07: Identified by security-sentinel and architecture-strategist in code review
