# Mimecast Authentication Reference

## HMAC-SHA1 Signature Authentication

Mimecast uses HMAC-SHA1 signature-based authentication (not OAuth).

### Required Credentials

| Credential | Description | Where to Find |
|------------|-------------|---------------|
| `app_id` | Application ID | Admin Console → API Integrations |
| `app_key` | Application Key | Generated with application |
| `access_key` | Access Key | User-level credential |
| `secret_key` | Secret Key (base64) | Generated with access key |

### Signature Generation

```
Authorization: MC {accessKey}:{base64(HMAC-SHA1(secretKey, dataToSign))}
```

**Data to Sign Format:**
```
{dateHeader}\n{requestId}\n{uri}\n{appKey}
```

### Required Request Headers

| Header | Description | Example |
|--------|-------------|---------|
| `Authorization` | HMAC signature | `MC abc123:xyz789==` |
| `x-mc-date` | RFC 2822 date | `Thu, 19 Dec 2024 10:30:00 +0000` |
| `x-mc-req-id` | Unique UUID | `550e8400-e29b-41d4-a716-446655440000` |
| `x-mc-app-id` | Application ID | `your-app-id` |
| `Content-Type` | Always JSON | `application/json` |

### Regional Endpoints

| Region | Base URL |
|--------|----------|
| US | `https://us-api.mimecast.com` |
| EU | `https://eu-api.mimecast.com` |
| DE | `https://de-api.mimecast.com` |
| AU | `https://au-api.mimecast.com` |
| ZA | `https://za-api.mimecast.com` |
| CA | `https://ca-api.mimecast.com` |
| UK | `https://uk-api.mimecast.com` |
| Sandbox | `https://sandbox-api.mimecast.com` |

### Python Implementation

```python
import base64
import hashlib
import hmac
import uuid
from email.utils import formatdate

def generate_signature(secret_key, access_key, app_key, uri):
    date_header = formatdate(localtime=True)
    request_id = str(uuid.uuid4())

    data_to_sign = f"{date_header}\n{request_id}\n{uri}\n{app_key}"

    hmac_sha1 = hmac.new(
        base64.b64decode(secret_key),
        data_to_sign.encode('utf-8'),
        digestmod=hashlib.sha1
    )
    signature = base64.b64encode(hmac_sha1.digest()).decode('utf-8')

    return {
        'Authorization': f"MC {access_key}:{signature}",
        'x-mc-date': date_header,
        'x-mc-req-id': request_id
    }
```

### Testing Authentication

```bash
# Test credentials
python3 scripts/mimecast_auth.py --test

# Show configuration
python3 scripts/mimecast_auth.py --info

# Generate curl command
python3 scripts/mimecast_auth.py --curl /api/account/get-account
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Signature mismatch` | Incorrect credentials | Verify all 4 credentials |
| `Clock skew` | System time incorrect | Sync system clock with NTP |
| `Access denied` | Missing permissions | Check API role permissions |
| `Invalid application` | Wrong app_id | Verify application ID |

### Security Best Practices

1. **Never commit credentials** - Use config/.gitignore
2. **Rotate keys regularly** - Regenerate access/secret keys
3. **Limit permissions** - Use role-based API access
4. **Monitor usage** - Track API calls in Admin Console
5. **Use HTTPS** - All endpoints require TLS
