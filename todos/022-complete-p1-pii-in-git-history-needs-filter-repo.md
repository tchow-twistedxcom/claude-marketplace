---
status: complete
priority: p1
issue_id: "022"
tags: [code-review, security, pii, git-history]
dependencies: []
---

# 022 — PII audit snapshot still exists in git history (merge blocker for shared repos)

## Problem Statement

`audit-2026-04-04.md` (791 real user records, employee names, emails, internal GUIDs) was committed in `fc44a5b` and removed via `git rm` in `a3e1561`. The `.gitignore` prevents future commits. However, the file still exists in the branch's git object store — `git show fc44a5b:plugins/mimecast-skills/audit-2026-04-04.md` returns the full PII content. Anyone with read access to the remote repo (team members, CI runners, future public release) can retrieve the data.

## Findings

- **Commit**: `fc44a5b feat(mimecast-m365-audit): add Azure AD security sweep, extension, and audit docs`
- **File path in history**: `plugins/mimecast-skills/audit-2026-04-04.md`
- **Agent**: architecture-strategist (HIGH — merge blocker for shared repos)
- **Todo 011** addressed the gitignore and git rm steps but did NOT purge history

```bash
# Verify PII still in history:
git cat-file -e fc44a5b:plugins/mimecast-skills/audit-2026-04-04.md
echo $?  # returns 0 if object exists
```

## Proposed Solutions

### Option A: git filter-repo (Recommended)
```bash
pip install git-filter-repo
git filter-repo --path plugins/mimecast-skills/audit-2026-04-04.md --invert-paths --force
git push --force origin feat/mimecast-m365-audit
```
Requires force-push coordination for all clones.

### Option B: BFG Repo Cleaner (simpler UI)
```bash
bfg --delete-files audit-2026-04-04.md
git reflog expire --expire=now --all && git gc --prune=now --aggressive
git push --force
```

### Option C: Accept risk for personal private repo
If this repo is strictly local (no remote sharing, no CI, no team members), the risk is contained. Document decision and skip purge.

## Recommended Action

Option C for now (this appears to be a personal private repo). If the repo is ever shared or made public, run Option A immediately. Document the known PII history entry in CLAUDE.md or a security note.

## Acceptance Criteria

- [ ] Either: git history purged of the PII file (Options A/B)
- [ ] Or: Decision documented that repo is private-only and risk is accepted (Option C)

## Work Log

- 2026-04-07: Initial git rm done in a3e1561 (todo 011)
- 2026-04-07: Architecture-strategist confirmed PII still in history, flags as merge blocker for shared repos
- 2026-04-07: **DECISION — Option C accepted.** This is a personal private repo with no remote sharing, CI runners, or team members. Risk is documented and contained. If repo is ever shared or made public, run `git filter-repo --path plugins/mimecast-skills/audit-2026-04-04.md --invert-paths --force` before sharing.
