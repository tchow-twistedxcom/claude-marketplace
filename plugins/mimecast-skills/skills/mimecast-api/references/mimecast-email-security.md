# Mimecast Email Security Reference

## Message Tracking

### Search Messages

Search message tracking logs for delivery status and routing information.

```bash
# Search by sender
python3 scripts/mimecast_api.py messages search --from sender@example.com

# Search by recipient
python3 scripts/mimecast_api.py messages search --to recipient@example.com

# Search by subject
python3 scripts/mimecast_api.py messages search --subject "invoice"

# Search with date range
python3 scripts/mimecast_api.py messages search --from sender@example.com --start 2024-01-01 --end 2024-01-31
```

**API Endpoint:** `POST /api/message-finder/search`

**Response Fields:**
| Field | Description |
|-------|-------------|
| `id` | Message ID |
| `from` | Sender address |
| `to` | Recipient address |
| `subject` | Email subject |
| `status` | Delivery status |
| `received` | Timestamp received |

---

## Held Messages

Messages held by Mimecast policies for review or release.

### List Held Messages

```bash
# User held queue
python3 scripts/mimecast_api.py messages held

# Admin held queue
python3 scripts/mimecast_api.py messages held --admin

# With date range
python3 scripts/mimecast_api.py messages held --start 2024-01-01 --end 2024-01-31
```

**API Endpoint:** `POST /api/gateway/get-hold-message-list`

### Release Held Message

```bash
python3 scripts/mimecast_api.py messages release --id MESSAGE_ID
python3 scripts/mimecast_api.py messages release --id MESSAGE_ID --reason REASON_ID
```

**API Endpoint:** `POST /api/gateway/hold/release`

---

## TTP (Targeted Threat Protection)

### URL Protection Logs

Get logs of URL clicks protected by Mimecast TTP.

```bash
# Get URL logs
python3 scripts/mimecast_api.py ttp urls --start 2024-01-01

# Filter by route
python3 scripts/mimecast_api.py ttp urls --start 2024-01-01 --route inbound

# Filter by result
python3 scripts/mimecast_api.py ttp urls --start 2024-01-01 --result malicious
```

**API Endpoint:** `POST /api/ttp/url/get-logs`

**Response Fields:**
| Field | Description |
|-------|-------------|
| `url` | Clicked URL |
| `action` | Action taken (allowed, blocked) |
| `scanResult` | Scan result (clean, malicious, suspicious) |
| `category` | URL category |
| `userEmailAddress` | User who clicked |
| `date` | Event timestamp |

### Attachment Protection Logs

Get logs of attachment scanning.

```bash
# Get attachment logs
python3 scripts/mimecast_api.py ttp attachments --start 2024-01-01

# Filter by result
python3 scripts/mimecast_api.py ttp attachments --start 2024-01-01 --result malicious
```

**API Endpoint:** `POST /api/ttp/attachment/get-logs`

**Response Fields:**
| Field | Description |
|-------|-------------|
| `fileName` | Attachment filename |
| `fileType` | File type/extension |
| `result` | Scan result |
| `senderAddress` | Sender email |
| `date` | Event timestamp |

### Impersonation Protection Logs

Get logs of impersonation attack detection.

```bash
# Get impersonation logs
python3 scripts/mimecast_api.py ttp impersonation --start 2024-01-01

# Filter by action
python3 scripts/mimecast_api.py ttp impersonation --start 2024-01-01 --action blocked
```

**API Endpoint:** `POST /api/ttp/impersonation/get-logs`

**Response Fields:**
| Field | Description |
|-------|-------------|
| `subject` | Email subject |
| `senderAddress` | Sender email |
| `action` | Action taken |
| `impersonationType` | Type of impersonation detected |
| `eventTime` | Event timestamp |

---

## Email Archive

### Search Archive

Search the email archive for historical messages.

```bash
# Search archive
python3 scripts/mimecast_api.py archive search --query "project report"

# With date range
python3 scripts/mimecast_api.py archive search --query "invoice" --start 2024-01-01 --end 2024-06-30
```

**API Endpoint:** `POST /api/archive/search`

---

## Common Workflows

### Investigate Suspicious Email

```bash
# 1. Search for the message
python3 scripts/mimecast_api.py messages search --from suspicious@sender.com --output json

# 2. Check TTP logs for any malicious activity
python3 scripts/mimecast_api.py ttp urls --start 2024-01-01

# 3. If held, review and potentially release
python3 scripts/mimecast_api.py messages held
python3 scripts/mimecast_api.py messages release --id MSG123
```

### Review Daily Security Events

```bash
# Get today's TTP URL events
python3 scripts/mimecast_api.py ttp urls --start $(date +%Y-%m-%d) --output json

# Get today's attachment events
python3 scripts/mimecast_api.py ttp attachments --start $(date +%Y-%m-%d)

# Get today's impersonation attempts
python3 scripts/mimecast_api.py ttp impersonation --start $(date +%Y-%m-%d)
```
