---
status: complete
priority: p2
issue_id: "030"
tags: [code-review, security, audit, mimecast]
dependencies: []
---

# 030 — Remediation commands in audit report embed unquoted email/display names (second-order injection)

## Problem Statement

`audit_m365_sync.py` generates copy-pasteable shell commands in the markdown report using raw email addresses and display names from Azure AD / Mimecast. Email addresses with shell-special characters (backticks, semicolons, `$`) and display names with quotes or semicolons would produce malicious-looking command blocks that an operator copying from the report would execute.

## Findings

- **File**: `plugins/mimecast-skills/scripts/audit_m365_sync.py`, lines 776-777
- **Agent**: security-sentinel (M3 — MEDIUM)

```python
def _remediation(email: str) -> str:
    return f"`python3 scripts/mimecast_api.py users delete --email {email}`"

# Also line 886:
provision = f"`python3 scripts/mimecast_api.py users create --email {u['email']} --name \"{u.get('azure_display', '')}\" `"
```

A display name like `Alice; rm -rf /` or an email like `` user`whoami`@domain.com `` would produce a dangerous-looking command that an operator might copy-paste into their terminal.

In practice, Azure AD/Mimecast user data is trusted, but defense in depth requires shell quoting.

## Proposed Solutions

### Option A: Apply shlex.quote() to all command-line values (Recommended)
```python
import shlex

def _remediation(email: str) -> str:
    return f"`python3 scripts/mimecast_api.py users delete --email {shlex.quote(email)}`"

provision = (
    f"`python3 scripts/mimecast_api.py users create "
    f"--email {shlex.quote(u['email'])} "
    f"--name {shlex.quote(u.get('azure_display', ''))}`"
)
```

### Option B: Backtick-escape in markdown only (minimal)
If the report is markdown and commands are in code blocks, the visual rendering is already safe for display. The risk is in copy-pasting, not rendering. Option A remains the correct fix.

## Recommended Action

Option A — add `import shlex` and wrap all email/name values in `shlex.quote()` in the command generation functions.

## Acceptance Criteria

- [ ] All email addresses in generated remediation commands are wrapped in `shlex.quote()`
- [ ] All display names in generated provision commands are wrapped in `shlex.quote()`

## Work Log

- 2026-04-07: Identified by security-sentinel as M3 (MEDIUM)
- 2026-04-07: Fixed — added `import shlex` (line 25), wrapped email in `_remediation()` with `shlex.quote()` (line 778), and rewrote the provision command (lines 887-891) to wrap both email and display name with `shlex.quote()`. Committed in `9d7c561`.
