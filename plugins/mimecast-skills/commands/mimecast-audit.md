---
name: mimecast-audit
description: Run a Mimecast ↔ M365 configuration audit comparing Azure AD users against Mimecast and checking security configuration
---

# /mimecast-audit

Run a comprehensive audit of Mimecast configuration against Microsoft 365 / Azure AD.

## What This Does

1. Pulls Azure AD users (enabled + disabled) and Mimecast users
2. Cross-references to find orphaned/missing/stale accounts
3. Checks security configuration (DKIM, TTP, anti-spoofing, delivery routes)
4. Generates a markdown report with actionable remediation commands

## Instructions

Load the `mimecast-audit` skill and run the following:

```bash
cd plugins/mimecast-skills
python3 scripts/audit_m365_sync.py --verbose
```

If the user wants to save the report:

```bash
python3 scripts/audit_m365_sync.py --output audit-$(date +%Y-%m-%d).md --verbose
```

For a quick check (just user sync issues, no config):

```bash
python3 scripts/audit_m365_sync.py --json | python3 -c "
import json, sys
data = json.load(sys.stdin)
r = data['sync_results']
print(f'Orphaned: {len(r[\"orphaned\"])}')
print(f'Disabled active: {len(r[\"disabled_active\"])}')
print(f'Missing from Mimecast: {len(r[\"missing\"])}')
"
```

After the audit runs, present the findings and ask the user which issues they'd like to remediate first. The report includes copy-paste CLI commands for each finding.
