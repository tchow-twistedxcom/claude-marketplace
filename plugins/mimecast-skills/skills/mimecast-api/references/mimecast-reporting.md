# Mimecast Reporting Reference

## Account Statistics

Get account information and statistics.

```bash
python3 scripts/mimecast_api.py account info
python3 scripts/mimecast_api.py reports stats
```

**API Endpoint:** `POST /api/account/get-account`

**Response Fields:**
| Field | Description |
|-------|-------------|
| `accountCode` | Account identifier |
| `accountName` | Account name |
| `type` | Account type |
| `region` | Mimecast region |
| `mailboxes` | Number of mailboxes |
| `maxRetention` | Maximum retention days |
| `packages` | Enabled feature packages |

---

## Audit Events

Get administrative audit trail events.

```bash
# Get recent audit events
python3 scripts/mimecast_api.py reports audit

# With date range
python3 scripts/mimecast_api.py reports audit --start 2024-01-01 --end 2024-01-31

# Filter by audit type
python3 scripts/mimecast_api.py reports audit --type policy_change
```

**API Endpoint:** `POST /api/audit/get-audit-events`

**Request Parameters:**
| Parameter | Description |
|-----------|-------------|
| `startDateTime` | Start date (ISO format) |
| `endDateTime` | End date (ISO format) |
| `auditType` | Filter by event type |

**Response Fields:**
| Field | Description |
|-------|-------------|
| `id` | Audit event ID |
| `auditType` | Type of event |
| `user` | User who performed action |
| `source` | Source of action |
| `eventTime` | Event timestamp |

### Common Audit Types

| Type | Description |
|------|-------------|
| `policy_change` | Policy modifications |
| `user_logon` | Admin console logins |
| `configuration_change` | System config changes |
| `permission_change` | Permission updates |

---

## SIEM Integration

Export logs for SIEM/security monitoring systems.

```bash
# Get receipt logs (default)
python3 scripts/mimecast_api.py reports siem

# Specify log type
python3 scripts/mimecast_api.py reports siem --type receipt
python3 scripts/mimecast_api.py reports siem --type process
python3 scripts/mimecast_api.py reports siem --type delivery
python3 scripts/mimecast_api.py reports siem --type ttp

# With date range
python3 scripts/mimecast_api.py reports siem --type receipt --start 2024-01-01

# Output format
python3 scripts/mimecast_api.py reports siem --format json
python3 scripts/mimecast_api.py reports siem --format key_value
```

**API Endpoint:** `POST /api/audit/get-siem-logs`

### Log Types

| Type | Description |
|------|-------------|
| `receipt` | Email receipt logs |
| `process` | Email processing logs |
| `delivery` | Email delivery logs |
| `ttp` | TTP security event logs |
| `internal` | Internal email logs |

### Output Formats

| Format | Description |
|--------|-------------|
| `json` | JSON format (default) |
| `key_value` | Key-value pairs for parsing |

---

## Threat Intelligence

Get threat intelligence feed data.

```bash
# Get threat intelligence
python3 scripts/mimecast_api.py reports threat-intel

# Specific feed
python3 scripts/mimecast_api.py reports threat-intel --feed malware
```

**API Endpoint:** `POST /api/ttp/threat-intel/get-intel`

---

## Common Workflows

### Daily Security Report

```bash
#!/bin/bash
# daily_security_report.sh

DATE=$(date +%Y-%m-%d)
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)

echo "=== Mimecast Security Report for $DATE ==="

echo -e "\n--- TTP URL Events ---"
python3 scripts/mimecast_api.py ttp urls --start $YESTERDAY --end $DATE

echo -e "\n--- TTP Attachment Events ---"
python3 scripts/mimecast_api.py ttp attachments --start $YESTERDAY --end $DATE

echo -e "\n--- Impersonation Attempts ---"
python3 scripts/mimecast_api.py ttp impersonation --start $YESTERDAY --end $DATE

echo -e "\n--- Held Messages ---"
python3 scripts/mimecast_api.py messages held
```

### SIEM Export Script

```bash
#!/bin/bash
# siem_export.sh - Export logs to SIEM

OUTPUT_DIR="/var/log/mimecast"
DATE=$(date +%Y%m%d%H%M)

# Export receipt logs
python3 scripts/mimecast_api.py reports siem --type receipt --format json \
    > "$OUTPUT_DIR/receipt_$DATE.json"

# Export TTP logs
python3 scripts/mimecast_api.py reports siem --type ttp --format json \
    > "$OUTPUT_DIR/ttp_$DATE.json"

# Export delivery logs
python3 scripts/mimecast_api.py reports siem --type delivery --format json \
    > "$OUTPUT_DIR/delivery_$DATE.json"
```

### Compliance Audit Export

```bash
# Export audit trail for compliance
python3 scripts/mimecast_api.py reports audit \
    --start 2024-01-01 \
    --end 2024-03-31 \
    --output json > q1_audit_trail.json

# Export all policies
python3 scripts/mimecast_api.py policies list --output json > policies_backup.json

# Export user list
python3 scripts/mimecast_api.py users list --output json > users_list.json
```

### Weekly Threat Summary

```bash
#!/bin/bash
# weekly_threat_summary.sh

WEEK_AGO=$(date -d "7 days ago" +%Y-%m-%d)
TODAY=$(date +%Y-%m-%d)

echo "=== Weekly Threat Summary ($WEEK_AGO to $TODAY) ==="

echo -e "\n### Malicious URLs Blocked ###"
python3 scripts/mimecast_api.py ttp urls --start $WEEK_AGO --result malicious

echo -e "\n### Malicious Attachments ###"
python3 scripts/mimecast_api.py ttp attachments --start $WEEK_AGO --result malicious

echo -e "\n### Impersonation Attacks ###"
python3 scripts/mimecast_api.py ttp impersonation --start $WEEK_AGO

echo -e "\n### Threat Intelligence ###"
python3 scripts/mimecast_api.py reports threat-intel
```

---

## Best Practices

1. **Automate exports** - Schedule SIEM exports via cron
2. **Retain audit logs** - Store audit trails for compliance
3. **Monitor trends** - Track security events over time
4. **Alert on anomalies** - Set up alerts for unusual activity
5. **Regular reviews** - Weekly threat summaries for security team
