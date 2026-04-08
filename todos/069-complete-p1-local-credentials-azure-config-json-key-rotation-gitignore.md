---
status: complete
priority: p1
issue_id: "069"
tags: [code-review, security, azure-ad]
dependencies: []
---

# 069 — Local credentials: client secret in azure_config.json must be rotated; add directory-level gitignore

## Problem Statement

The file `plugins/m365-skills/skills/azure-ad/config/azure_config.json` contains a live Azure AD client secret for an app registration that holds extremely broad tenant-wide permissions including `Policy.ReadWrite.ConditionalAccess`, `User.RevokeSessions.All`, `IdentityRiskEvent.ReadWrite.All`, `Mail.Read` (all mailboxes), and `ThreatHunting.Read.All`. The file is covered by the root `.gitignore` and has never been committed to git, but:

1. The plaintext secret is on disk readable by any process running as the same OS user.
2. A cached access token (expired) is also present in `.azure_tokens.json` in the same directory.
3. Only a single `.gitignore` layer at the repo root protects both files — no directory-level guard.

## Findings

### `config/azure_config.json` (security-sentinel FINDING-01)
```json
"client_secret": "azO8Q~KaP2~Y3..."  # production secret, line 7
"client_id": "b068503f-6a62-..."
"tenant_id": "ede4fe1e-8fc0-..."
```
App registration holds: `Policy.ReadWrite.ConditionalAccess`, `User.RevokeSessions.All`, `IdentityRiskEvent.ReadWrite.All`, `IdentityRiskyUser.ReadWrite.All`, `Mail.Read`, `ThreatHunting.Read.All`, `AuditLog.Read.All`. Compromise of this secret = full tenant-wide audit + revoke + policy write access.

### `.azure_tokens.json` (security-sentinel FINDING-02)
Expired access token (exp ~1775325483) stored alongside config. Client credentials flow — no refresh token — but the file path is predictable.

### Single-layer `.gitignore` protection
Root `.gitignore` lines 80 and 88 cover `**/azure_config.json` and `**/.azure_tokens.json`. No `config/.gitignore` exists as a second layer.

## Proposed Solutions

**Option A (Recommended):**
1. **Immediately rotate** the client secret in the Azure AD app registration portal. Generate a new secret and update `azure_config.json` locally.
2. Add `plugins/m365-skills/skills/azure-ad/config/.gitignore` containing:
   ```
   azure_config.json
   .azure_tokens.json
   *.json
   ```
3. Consider adding a pre-commit check (e.g., `git-secrets` pattern or simple `grep` hook) to reject any file matching `client_secret` from being staged.
- Effort: Small. Risk: Medium (rotation causes brief service interruption until local config updated).

## Acceptance Criteria

- [ ] Client secret rotated in Azure portal; new secret stored in `azure_config.json`
- [ ] `config/.gitignore` created with `azure_config.json`, `.azure_tokens.json` exclusions
- [ ] Root `.gitignore` patterns remain as second layer (no removal)

## Work Log

- 2026-04-08: Identified by security-sentinel (FINDING-01, FINDING-02) in 5th review pass. Token expired; git history clean (file never committed).
- 2026-04-08: Created config/.gitignore as second-layer gitignore protection. Secret rotation in Azure portal requires manual user action.
- 2026-04-08: Created config/.gitignore with azure_config.json and .azure_tokens.json exclusions. Secret rotation requires manual user action in Azure AD portal.
