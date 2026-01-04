---
name: mimecast-api
description: |
  Execute Mimecast operations via Python CLI. Use when managing email security,
  user provisioning, policy management, or security reporting programmatically.
  Covers TTP URL/attachment protection, held messages, user/group management,
  blocked/permitted senders, audit logs, and SIEM integration.
---

# Mimecast API Skill

Execute Mimecast email security operations via Python CLI.

## When to Use

- Managing email security (held messages, TTP logs)
- User and group provisioning
- Policy management (block/permit senders)
- Security reporting and SIEM integration
- Threat intelligence retrieval

## CLI Location

```bash
cd plugins/mimecast-skills
python3 scripts/mimecast_api.py <resource> <action> [options]
```

## Quick Reference

### Account & Info
```bash
python3 scripts/mimecast_api.py account info
```

### Email Security
```bash
# Search messages
python3 scripts/mimecast_api.py messages search --from sender@example.com
python3 scripts/mimecast_api.py messages search --subject "invoice"

# Held messages
python3 scripts/mimecast_api.py messages held
python3 scripts/mimecast_api.py messages release --id MSG123

# TTP Protection Logs
python3 scripts/mimecast_api.py ttp urls --start 2024-01-01
python3 scripts/mimecast_api.py ttp attachments --start 2024-01-01
python3 scripts/mimecast_api.py ttp impersonation --start 2024-01-01
```

### User Management
```bash
python3 scripts/mimecast_api.py users list
python3 scripts/mimecast_api.py users create --email user@example.com --name "John Doe"
python3 scripts/mimecast_api.py users update --email user@example.com --alias alias@example.com
python3 scripts/mimecast_api.py users delete --email user@example.com
```

### Group Management
```bash
python3 scripts/mimecast_api.py groups list
python3 scripts/mimecast_api.py groups create --description "Sales Team"
python3 scripts/mimecast_api.py groups add-member --group GROUP_ID --email user@example.com
python3 scripts/mimecast_api.py groups remove-member --group GROUP_ID --email user@example.com
```

### Policy Management
```bash
python3 scripts/mimecast_api.py policies list
python3 scripts/mimecast_api.py policies block-sender --email spam@malicious.com
python3 scripts/mimecast_api.py policies permit-sender --email trusted@partner.com
python3 scripts/mimecast_api.py policies definitions
```

### Reporting
```bash
python3 scripts/mimecast_api.py reports audit --start 2024-01-01 --end 2024-01-31
python3 scripts/mimecast_api.py reports siem --type receipt --format json
python3 scripts/mimecast_api.py reports stats
python3 scripts/mimecast_api.py reports threat-intel
```

## Output Formats

```bash
# Table format (default)
python3 scripts/mimecast_api.py users list

# JSON format
python3 scripts/mimecast_api.py users list --output json
```

## Profile Selection

```bash
# Use default profile
python3 scripts/mimecast_api.py users list

# Use specific profile
python3 scripts/mimecast_api.py users list --profile sandbox
```

## Reference Documentation

- [Authentication](references/mimecast-authentication.md) - HMAC-SHA1 signature setup
- [Email Security](references/mimecast-email-security.md) - Message tracking, TTP, held messages
- [User Management](references/mimecast-user-management.md) - User and group operations
- [Policy Management](references/mimecast-policy-management.md) - Block/permit sender policies
- [Reporting](references/mimecast-reporting.md) - Audit, SIEM, threat intelligence
