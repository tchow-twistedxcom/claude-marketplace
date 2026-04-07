---
status: complete
priority: p3
issue_id: "020"
tags: [code-review, bug, audit, mimecast]
dependencies: []
---

# 020 — normalize_email uses .onmicrosoft.com UPN causing false "missing from Mimecast" alerts

## Problem Statement

In `normalize_email()`, when an Azure AD user has no `mail` field (common for guest/sync accounts), the function falls back to `userPrincipalName` — which may be `alice@contoso.onmicrosoft.com`. This never matches a Mimecast address that uses the primary domain, causing those users to always appear in the "Missing from Mimecast" category even when correctly provisioned.

## Findings

- **File**: `plugins/mimecast-skills/scripts/audit_m365_sync.py`, lines 311-322
- **Agent**: kieran-python-reviewer (MEDIUM)

```python
def normalize_email(user: dict, source: str) -> str | None:
    if source == "azure":
        email = user.get("mail") or user.get("userPrincipalName", "")
        # If mail is None and UPN is alice@contoso.onmicrosoft.com,
        # this returns the .onmicrosoft.com address which never matches Mimecast
        return email.lower().strip() if email else None
```

Also: `source` is an unguarded string — passing any value other than `"azure"` silently falls through to the Mimecast branch, which would misparse an Azure user record.

## Proposed Solutions

### Option A: Skip .onmicrosoft.com UPNs when mail is absent
```python
if source == "azure":
    email = user.get("mail") or user.get("userPrincipalName", "")
    if not email or "#EXT#" in email:
        return None
    if email.endswith(".onmicrosoft.com") and not user.get("mail"):
        return None  # skip — no primary email, can't compare to Mimecast
    return email.lower().strip()
```

### Option B: Use Literal["azure", "mimecast"] type annotation
```python
from typing import Literal
def normalize_email(user: dict, source: Literal["azure", "mimecast"]) -> str | None:
```
This doesn't fix the runtime behavior but catches the wrong-source bug at type-check time.

## Recommended Action

Both — Option A fixes the false positives, Option B prevents future misuse.

## Acceptance Criteria

- [ ] Users with `.onmicrosoft.com` UPNs and no `mail` field are excluded from user comparison
- [ ] `source` parameter is typed as `Literal["azure", "mimecast"]`

## Work Log

- 2026-04-07: Identified by kieran-python-reviewer as MEDIUM
