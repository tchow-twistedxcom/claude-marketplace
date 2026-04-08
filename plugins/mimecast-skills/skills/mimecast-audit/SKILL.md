---
name: mimecast-audit
description: |
  Audit Mimecast configuration against Microsoft 365 / Azure AD. Use when asked to:
  audit mimecast, check mimecast config, m365 sync, employee lifecycle, user sync,
  orphaned accounts, departed employees, terminated users, license audit,
  mimecast m365, mimecast azure, mimecast health check, mimecast compliance.
---

# Mimecast ↔ M365 Configuration Audit Skill

Run a comprehensive audit of Mimecast configuration against Azure AD (Entra ID) to identify
user sync drift, orphaned accounts, employee lifecycle issues, and security misconfigurations.

## When to Use

- Auditing Mimecast user accounts against Active Directory / M365
- Identifying departed employees who still have Mimecast accounts
- Finding active employees who are missing Mimecast protection
- Reviewing security config (DKIM, TTP, policies, delivery routes)
- Checking awareness training coverage and high-risk users

## Quick Start

```bash
cd plugins/mimecast-skills
python3 scripts/audit_m365_sync.py
```

This runs the full audit with default settings:
- Mimecast profile: `production`
- Azure AD tenant: `default`
- Grace period: 90 days
- Output: markdown report to stdout

## Options

```bash
# Full audit with all options
python3 scripts/audit_m365_sync.py \
  --mimecast-profile production \
  --azure-tenant default \
  --grace-days 90 \
  --exclude-domains "service.local,shared.company.com" \
  --output audit-report.md \
  --verbose

# JSON output for programmatic use
python3 scripts/audit_m365_sync.py --json

# Custom grace period (60 days)
python3 scripts/audit_m365_sync.py --grace-days 60
```

## What It Checks

### User Sync (Azure AD ↔ Mimecast)

| Category | Description | Action |
|---|---|---|
| ✅ Active | In both Azure AD (enabled) and Mimecast | None |
| 🔴 Orphaned | In Mimecast, no Azure AD account | Remove from Mimecast |
| 🟡 Missing | Azure AD active, not in Mimecast | Provision in Mimecast |
| 🔴 Disabled but active | Azure AD disabled, Mimecast active | Remove from Mimecast |
| ℹ️ Grace period | Disabled within N days (transition) | Monitor |
| 🔴 Stale grace | Disabled > N days ago, still in Mimecast | Remove |

**Grace Period Limitation**: The grace/stale buckets use `createdDateTime` (account creation date) as a proxy
for "recently disabled". This is imprecise — long-tenured employees disabled last week will have an old
`createdDateTime` and will appear as stale or orphaned rather than in the grace bucket. For accurate
classification, `signInActivity.lastSignInDateTime` would be a better signal but requires `AuditLog.Read.All`
permission. Always manually verify the grace bucket against HR offboarding records. (See TODO 044.)

### Security Configuration

- **DKIM** — signing enabled for all configured domains
- **Domain alignment** — domains match between Azure AD and Mimecast
- **TTP protection** — URL, attachment, and impersonation scanning active
- **Anti-spoofing policies** — policies configured for your domains
- **Delivery routes** — M365 routing correctly configured
- **Awareness training** — training coverage and SAFE score summary
- **High-risk watchlist** — users on the Mimecast SAFE watchlist

## Interpreting Results

### User Remediation Commands

The report includes copy-paste CLI commands for each finding:

```bash
# Remove orphaned/departed user from Mimecast
python3 scripts/mimecast_api.py users delete --email former.employee@company.com

# Provision missing user in Mimecast
python3 scripts/mimecast_api.py users create --email new.hire@company.com --name "New Hire"
```

### Config Deep-Dives

```bash
# Check DKIM for specific domain
python3 scripts/mimecast_api.py dkim status --output json

# Review all active policies
python3 scripts/mimecast_api.py policies list --output json

# TTP summary (URL + attachment + impersonation)
python3 scripts/mimecast_api.py ttp summary

# Review delivery routes
python3 scripts/mimecast_api.py delivery routes --output json

# High-risk user watchlist
python3 scripts/mimecast_api.py awareness watchlist

# SAFE score summary
python3 scripts/mimecast_api.py awareness safe-score-summary
```

## Prerequisites (verify before running)

1. **Mimecast credentials**: Test with:
   ```bash
   python3 plugins/mimecast-skills/scripts/mimecast_api.py users list --output json
   ```
   If this fails, run `/mimecast-setup` first.

2. **Azure AD credentials**: Test with:
   ```bash
   python3 plugins/m365-skills/skills/azure-ad/scripts/azure_ad_api.py users list --format json
   ```
   If this fails, configure `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` environment variables.

Both must succeed before running the audit. The audit will silently return empty results if either side is unconfigured.

## Workflow

1. Run `python3 scripts/audit_m365_sync.py --verbose`
2. Review the **User Sync** section — address 🔴 HIGH findings first
3. Review the **Security Configuration** section — fix HIGH severity items
4. Execute remediation commands from the report
5. Re-run the audit to verify fixes

## Related Skills

- `mimecast-api` — Full Mimecast CLI reference for running individual operations
- `azure-ad` — Azure AD CLI reference for user, group, and directory operations
