# Mimecast Policy Management Reference

## Policy Overview

Mimecast policies control email flow, security actions, and sender reputation.

### Policy Types

| Type | Description |
|------|-------------|
| Blocked Senders | Block emails from specific senders |
| Permitted Senders | Allow emails from specific senders |
| Anti-Spoofing | Prevent domain spoofing attacks |
| Content Examination | Scan email content |
| Attachment Management | Control attachment handling |

---

## List Policies

List all configured policies.

```bash
# List all policies
python3 scripts/mimecast_api.py policies list

# Filter by type
python3 scripts/mimecast_api.py policies list --type blockedsenders

# JSON output
python3 scripts/mimecast_api.py policies list --output json
```

**API Endpoint:** `POST /api/policy/get-policies`

**Response Fields:**
| Field | Description |
|-------|-------------|
| `id` | Policy ID |
| `description` | Policy description |
| `policyType` | Type of policy |
| `enabled` | Enabled status |
| `from` | Source criteria |
| `to` | Destination criteria |

---

## Blocked Sender Policy

Block emails from specific senders.

### Create Blocked Sender

```bash
# Block by email address
python3 scripts/mimecast_api.py policies block-sender --email spam@malicious.com

# With custom description
python3 scripts/mimecast_api.py policies block-sender \
    --email spam@malicious.com \
    --description "Known spam source"
```

**API Endpoint:** `POST /api/policy/blockedsenders/create-policy`

**Request Structure:**
```json
{
  "option": "block_sender",
  "policy": {
    "description": "Block spam@malicious.com",
    "fromPart": "envelope_from",
    "fromType": "individual_email_address",
    "fromValue": "spam@malicious.com"
  }
}
```

### Block Options

| From Type | Description | Example |
|-----------|-------------|---------|
| `individual_email_address` | Single email | `spam@bad.com` |
| `email_domain` | Entire domain | `bad.com` |
| `address_attribute_value` | Pattern match | `*@bad.com` |

---

## Permitted Sender Policy

Allow emails from trusted senders (bypass spam filtering).

### Create Permitted Sender

```bash
# Permit by email address
python3 scripts/mimecast_api.py policies permit-sender --email trusted@partner.com

# With custom description
python3 scripts/mimecast_api.py policies permit-sender \
    --email trusted@partner.com \
    --description "Trusted business partner"
```

**API Endpoint:** `POST /api/policy/permitsenders/create-policy`

**Request Structure:**
```json
{
  "option": "permit_sender",
  "policy": {
    "description": "Permit trusted@partner.com",
    "fromPart": "envelope_from",
    "fromType": "individual_email_address",
    "fromValue": "trusted@partner.com"
  }
}
```

---

## Policy Definitions

List available policy definition options.

```bash
python3 scripts/mimecast_api.py policies definitions
python3 scripts/mimecast_api.py policies definitions --output json
```

**API Endpoint:** `POST /api/policy/get-definitions`

---

## Anti-Spoofing Policy

Get anti-spoofing bypass policy configuration.

```python
# Via Python API
api = MimecastAPI()
result = api.get_anti_spoofing_policy()
```

**API Endpoint:** `POST /api/policy/antispoofing-bypass/get-policy`

---

## Common Workflows

### Block Phishing Domain

```bash
# Block entire domain
python3 scripts/mimecast_api.py policies block-sender \
    --email "@phishing-domain.com" \
    --description "Known phishing domain"

# Verify policy created
python3 scripts/mimecast_api.py policies list --type blockedsenders
```

### Whitelist Business Partner

```bash
# Permit partner domain
python3 scripts/mimecast_api.py policies permit-sender \
    --email "@partner-company.com" \
    --description "Business partner - bypass spam filtering"

# Verify
python3 scripts/mimecast_api.py policies list --type permitsenders
```

### Review All Policies

```bash
# Export all policies to JSON for review
python3 scripts/mimecast_api.py policies list --output json > policies_backup.json

# Check for specific policy types
python3 scripts/mimecast_api.py policies list --type blockedsenders
python3 scripts/mimecast_api.py policies list --type permitsenders
```

### Incident Response - Block Threat Actor

```bash
# 1. Block the malicious sender
python3 scripts/mimecast_api.py policies block-sender \
    --email attacker@malicious.com \
    --description "Phishing attack - blocked $(date +%Y-%m-%d)"

# 2. Check for any messages from this sender
python3 scripts/mimecast_api.py messages search --from attacker@malicious.com

# 3. Check TTP logs for any clicks
python3 scripts/mimecast_api.py ttp urls --start $(date -d "7 days ago" +%Y-%m-%d)
```

---

## Best Practices

1. **Document policies** - Use descriptive descriptions with dates
2. **Regular review** - Audit policies quarterly
3. **Test before production** - Use sandbox environment
4. **Backup policies** - Export to JSON before major changes
5. **Least privilege** - Only permit what's necessary
