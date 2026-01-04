---
name: mimecast-manage
description: Manage Mimecast integrations, flows, and connections via CLI
---

# Mimecast CLI Operations

Execute Mimecast API operations via Python CLI.

## Quick Reference

### Account Information
```bash
python3 scripts/mimecast_api.py account info
```

### Email Security Operations

#### Message Search & Tracking
```bash
# Search by sender
python3 scripts/mimecast_api.py messages search --from sender@example.com

# Search by recipient
python3 scripts/mimecast_api.py messages search --to recipient@example.com

# Search by subject with date range
python3 scripts/mimecast_api.py messages search --subject "invoice" --start 2024-01-01 --end 2024-01-31
```

#### Held Messages
```bash
# List held messages
python3 scripts/mimecast_api.py messages held

# Admin held queue
python3 scripts/mimecast_api.py messages held --admin

# Release held message
python3 scripts/mimecast_api.py messages release --id MESSAGE_ID
```

#### TTP Protection Logs
```bash
# URL protection logs
python3 scripts/mimecast_api.py ttp urls --start 2024-01-01

# Attachment protection logs
python3 scripts/mimecast_api.py ttp attachments --start 2024-01-01

# Impersonation protection logs
python3 scripts/mimecast_api.py ttp impersonation --start 2024-01-01
```

#### Email Archive
```bash
python3 scripts/mimecast_api.py archive search --query "project report"
```

### User Management

```bash
# List users
python3 scripts/mimecast_api.py users list
python3 scripts/mimecast_api.py users list --domain example.com

# Create user
python3 scripts/mimecast_api.py users create --email user@example.com --name "John Doe"

# Update user
python3 scripts/mimecast_api.py users update --email user@example.com --name "Jane Doe"

# Delete user
python3 scripts/mimecast_api.py users delete --email user@example.com
```

### Group Management

```bash
# List groups
python3 scripts/mimecast_api.py groups list

# Create group
python3 scripts/mimecast_api.py groups create --description "Sales Team"

# Add member
python3 scripts/mimecast_api.py groups add-member --group GROUP_ID --email user@example.com

# Remove member
python3 scripts/mimecast_api.py groups remove-member --group GROUP_ID --email user@example.com
```

### Policy Management

```bash
# List policies
python3 scripts/mimecast_api.py policies list

# Block sender
python3 scripts/mimecast_api.py policies block-sender --email spam@malicious.com

# Permit sender
python3 scripts/mimecast_api.py policies permit-sender --email trusted@partner.com

# List policy definitions
python3 scripts/mimecast_api.py policies definitions
```

### Reporting & SIEM

```bash
# Audit events
python3 scripts/mimecast_api.py reports audit --start 2024-01-01 --end 2024-01-31

# SIEM logs
python3 scripts/mimecast_api.py reports siem --type receipt --format json

# Account stats
python3 scripts/mimecast_api.py reports stats

# Threat intelligence
python3 scripts/mimecast_api.py reports threat-intel
```

## Output Formats

```bash
# Table format (default)
python3 scripts/mimecast_api.py users list

# JSON format
python3 scripts/mimecast_api.py users list --output json

# Pipe to jq
python3 scripts/mimecast_api.py users list --output json | jq '.[].emailAddress'
```

## Profile Selection

```bash
# Default profile
python3 scripts/mimecast_api.py users list

# Specific profile
python3 scripts/mimecast_api.py users list --profile sandbox
```

## Common Workflows

### Block Phishing Attack
```bash
# 1. Block the sender
python3 scripts/mimecast_api.py policies block-sender --email attacker@phishing.com

# 2. Check for any messages from this sender
python3 scripts/mimecast_api.py messages search --from attacker@phishing.com

# 3. Review TTP logs
python3 scripts/mimecast_api.py ttp urls --start $(date -d "7 days ago" +%Y-%m-%d)
```

### Daily Security Review
```bash
# Check held messages
python3 scripts/mimecast_api.py messages held

# Review TTP URL events
python3 scripts/mimecast_api.py ttp urls --start $(date +%Y-%m-%d)

# Check impersonation attempts
python3 scripts/mimecast_api.py ttp impersonation --start $(date +%Y-%m-%d)
```

### User Onboarding
```bash
# Create user
python3 scripts/mimecast_api.py users create --email newuser@company.com --name "New Employee"

# Add to groups
python3 scripts/mimecast_api.py groups add-member --group DEPT_ID --email newuser@company.com
```

## Usage Examples

**User:** "Check Mimecast for phishing attempts"
**Action:** Execute `python3 scripts/mimecast_api.py ttp impersonation --start 2024-01-01`

**User:** "Block spam sender"
**Action:** Execute `python3 scripts/mimecast_api.py policies block-sender --email spam@sender.com`

**User:** "List all Mimecast users"
**Action:** Execute `python3 scripts/mimecast_api.py users list`
