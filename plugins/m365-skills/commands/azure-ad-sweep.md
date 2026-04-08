---
name: azure-ad-sweep
description: Run a compromise sweep across Azure AD / Entra ID. Detects attacker IPs, MFA fatigue, Identity Protection risk events, audit anomalies, and auth method changes.
---

# Azure AD Compromise Sweep

Run a multi-vector security sweep across Azure AD / Entra ID to detect indicators of compromise.

## Detection Vectors

1. **IP sweep** — sign-ins from known attacker IPs
2. **MFA fatigue** — error 50199 failures followed by success within N minutes
3. **Risk detections** — Identity Protection risk events (requires Entra ID P1+)
4. **Risk IP cross-ref** — IPs from risk detections used for additional sign-in sweep
5. **Audit anomalies** — password resets, MFA changes, consent grants per victim
6. **Auth methods** — current MFA enrollment per affected account

## Usage

```bash
# Sweep last 48 hours
PYTHONPATH="${HOME}/.claude/plugins/marketplaces/tchow-essentials/plugins/m365-skills/skills/azure-ad/scripts" \
  python3 "${HOME}/.claude/plugins/marketplaces/tchow-essentials/plugins/m365-skills/skills/azure-ad/scripts/sweep.py" --hours 48

# Sweep with known attacker IPs
PYTHONPATH="${HOME}/.claude/plugins/marketplaces/tchow-essentials/plugins/m365-skills/skills/azure-ad/scripts" \
  python3 "${HOME}/.claude/plugins/marketplaces/tchow-essentials/plugins/m365-skills/skills/azure-ad/scripts/sweep.py" --ips 203.0.113.50,198.51.100.20 --hours 48

# Sweep from specific start time
PYTHONPATH="${HOME}/.claude/plugins/marketplaces/tchow-essentials/plugins/m365-skills/skills/azure-ad/scripts" \
  python3 "${HOME}/.claude/plugins/marketplaces/tchow-essentials/plugins/m365-skills/skills/azure-ad/scripts/sweep.py" --since 2026-03-30T00:00:00Z

# JSON output for further analysis
PYTHONPATH="${HOME}/.claude/plugins/marketplaces/tchow-essentials/plugins/m365-skills/skills/azure-ad/scripts" \
  python3 "${HOME}/.claude/plugins/marketplaces/tchow-essentials/plugins/m365-skills/skills/azure-ad/scripts/sweep.py" --hours 72 --mfa-window 15 --json > sweep_report.json
```

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--hours N` | Look back N hours from now | 48 |
| `--since ISO8601` | Look back from specific timestamp | — |
| `--ips IP1,IP2` | Known attacker IPs to sweep | — |
| `--mfa-window N` | Minutes after MFA failure to check for success | 10 |
| `--tenant ALIAS` | Azure tenant alias from config | default |
| `--json` | Output JSON instead of table | false |

## Prerequisites

- Azure AD config at `skills/azure-ad/config/azure_config.json`
- Permissions: `AuditLog.Read.All`, `IdentityRiskyUser.Read.All`, `IdentityRiskEvent.Read.All`, `UserAuthenticationMethod.Read.All`
- Entra ID P1 or P2 license for Identity Protection features

## Output

Produces a unified report per affected account showing:
- Confidence level (HIGH / MEDIUM / LOW)
- Which detection vectors triggered
- Sign-in details (IP, location, timestamp)
- MFA fatigue evidence
- Post-compromise audit events
- Current auth method enrollment

## Reference

See `skills/azure-ad/references/security_api.md` for full API details and incident response playbook.
