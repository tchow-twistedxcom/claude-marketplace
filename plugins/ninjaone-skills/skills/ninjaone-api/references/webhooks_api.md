# Webhooks API Reference

Event notification configuration and management.

## Endpoints

### Configure Webhook
```bash
python ninjaone_api.py webhooks configure --url URL --events EVENTS [--secret SECRET]
```

**Parameters:**
- `--url`: Webhook endpoint URL (required)
- `--events`: Comma-separated event types (required)
- `--secret`: Shared secret for signature verification

**Example:**
```bash
python ninjaone_api.py webhooks configure \
  --url "https://example.com/webhook" \
  --events "ALERT_TRIGGERED,DEVICE_OFFLINE,TICKET_CREATED" \
  --secret "my_webhook_secret"
```

### Disable Webhook
```bash
python ninjaone_api.py webhooks disable
```

Disable webhook notifications.

### Get Webhook Status
```bash
python ninjaone_api.py webhooks status
```

Get current webhook configuration.

## Event Types

### Alert Events
| Event | Description |
|-------|-------------|
| `ALERT_TRIGGERED` | New alert created |
| `ALERT_RESET` | Alert acknowledged |
| `ALERT_CLEARED` | Alert auto-cleared |

### Device Events
| Event | Description |
|-------|-------------|
| `DEVICE_ADDED` | New device registered |
| `DEVICE_OFFLINE` | Device went offline |
| `DEVICE_ONLINE` | Device came online |
| `DEVICE_DELETED` | Device removed |
| `DEVICE_APPROVED` | Device approved |
| `DEVICE_REJECTED` | Device rejected |

### Ticket Events
| Event | Description |
|-------|-------------|
| `TICKET_CREATED` | New ticket created |
| `TICKET_UPDATED` | Ticket modified |
| `TICKET_CLOSED` | Ticket closed |
| `TICKET_COMMENT_ADDED` | Comment added |

### Job Events
| Event | Description |
|-------|-------------|
| `JOB_STARTED` | Remote job started |
| `JOB_COMPLETED` | Job completed |
| `JOB_FAILED` | Job failed |

### Patch Events
| Event | Description |
|-------|-------------|
| `PATCH_INSTALLED` | Patch installed |
| `PATCH_FAILED` | Patch installation failed |

## Webhook Payload

### Common Fields
| Field | Type | Description |
|-------|------|-------------|
| `eventType` | string | Event type |
| `timestamp` | string | ISO 8601 timestamp |
| `data` | object | Event-specific data |

### Example Payloads

**Alert Triggered:**
```json
{
  "eventType": "ALERT_TRIGGERED",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "uid": "abc123",
    "deviceId": 12345,
    "severity": "CRITICAL",
    "message": "CPU usage above 95%",
    "sourceType": "CONDITION"
  }
}
```

**Device Offline:**
```json
{
  "eventType": "DEVICE_OFFLINE",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "deviceId": 12345,
    "systemName": "WORKSTATION-01",
    "organizationId": 123,
    "lastContact": "2024-01-15T10:25:00Z"
  }
}
```

**Ticket Created:**
```json
{
  "eventType": "TICKET_CREATED",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "ticketId": 456,
    "subject": "Network Issue",
    "priority": "High",
    "organizationId": 123,
    "createdBy": "user@example.com"
  }
}
```

## Security

### Signature Verification

When a secret is configured, NinjaOne signs webhook payloads:

```
X-Ninja-Signature: sha256=<signature>
```

Verify in your webhook handler:

```python
import hmac
import hashlib

def verify_signature(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

### Best Practices

1. **Always use HTTPS** for webhook URLs
2. **Verify signatures** using the shared secret
3. **Respond quickly** (< 5 seconds) to webhook calls
4. **Use async processing** for heavy operations
5. **Implement retry logic** for your processing
6. **Log webhook events** for debugging

## Common Workflows

### Setup Monitoring Webhook
```bash
# Configure webhook for alerts and device events
python ninjaone_api.py webhooks configure \
  --url "https://monitoring.example.com/ninjaone" \
  --events "ALERT_TRIGGERED,ALERT_CLEARED,DEVICE_OFFLINE,DEVICE_ONLINE" \
  --secret "monitoring_secret_123"

# Verify configuration
python ninjaone_api.py webhooks status
```

### Ticketing Integration
```bash
# Configure webhook for ticket sync
python ninjaone_api.py webhooks configure \
  --url "https://helpdesk.example.com/api/ninjaone" \
  --events "TICKET_CREATED,TICKET_UPDATED,TICKET_CLOSED,TICKET_COMMENT_ADDED" \
  --secret "ticketing_secret_456"
```

### Patch Compliance Tracking
```bash
# Configure webhook for patch events
python ninjaone_api.py webhooks configure \
  --url "https://compliance.example.com/patches" \
  --events "PATCH_INSTALLED,PATCH_FAILED" \
  --secret "compliance_secret_789"
```

## Webhook Handler Example

```python
from flask import Flask, request, abort
import hmac
import hashlib

app = Flask(__name__)
WEBHOOK_SECRET = "your_secret_here"

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    # Verify signature
    signature = request.headers.get('X-Ninja-Signature', '')
    payload = request.data.decode()

    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(f"sha256={expected}", signature):
        abort(401)

    # Process event
    event = request.json
    event_type = event['eventType']
    data = event['data']

    if event_type == 'ALERT_TRIGGERED':
        handle_alert(data)
    elif event_type == 'DEVICE_OFFLINE':
        handle_device_offline(data)
    # ... handle other events

    return 'OK', 200
```

## API Notes

- Only one webhook endpoint can be configured at a time
- Webhook delivery is best-effort (no guaranteed ordering)
- Failed deliveries may be retried by NinjaOne
- Webhook configuration requires admin permissions
- Test webhooks using tools like webhook.site before production
