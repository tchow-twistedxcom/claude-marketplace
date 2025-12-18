# Troubleshooting Guide

Common issues and solutions when working with the Celigo Integrator.io REST API.

## Authentication Issues

### 401 Unauthorized

**Symptoms:**
```json
{
  "errors": [{
    "code": "unauthorized",
    "message": "Invalid or expired API key"
  }]
}
```

**Causes & Solutions:**

1. **Invalid API Key**
   - Verify API key is correct (no extra spaces)
   - Check key hasn't been regenerated
   - Confirm key has correct permissions

2. **Wrong Environment**
   - Production keys don't work on sandbox
   - Verify using correct environment URL

3. **Key Disabled**
   - Check if API key was disabled in account settings
   - Generate new key if needed

**Validation:**
```bash
# Test API key
curl -X GET "https://api.integrator.io/v1/integrations" \
  -H "Authorization: Bearer $API_KEY"
```

### 403 Forbidden

**Symptoms:**
```json
{
  "errors": [{
    "code": "forbidden",
    "message": "Insufficient permissions"
  }]
}
```

**Solutions:**
- Verify user has required access level (manage vs monitor)
- Check integration-specific permissions
- Confirm API key has full access scope

## Connection Issues

### Connection Timeout

**Symptoms:**
```json
{
  "errors": [{
    "code": "connection_timeout",
    "message": "Request timed out after 30 seconds"
  }]
}
```

**Solutions:**

1. **Network Issues**
   - Check internet connectivity
   - Verify firewall allows outbound HTTPS
   - Test DNS resolution for api.integrator.io

2. **Rate Limiting**
   - Reduce request frequency
   - Implement exponential backoff
   - Check rate limit headers

3. **Large Payloads**
   - Reduce batch sizes
   - Use pagination for large datasets

### SSL Certificate Errors

**Solutions:**
- Update CA certificates
- Don't disable SSL verification in production
- Check system clock is accurate

## Flow Execution Issues

### Flow Won't Start

**Possible Causes:**
1. Flow is disabled
2. Connection credentials expired
3. Schedule not configured
4. Missing required settings

**Diagnostic Steps:**
```bash
# Check flow status
curl -X GET "https://api.integrator.io/v1/flows/{flow_id}" \
  -H "Authorization: Bearer $API_KEY"

# Test connection
curl -X POST "https://api.integrator.io/v1/connections/{connection_id}/ping" \
  -H "Authorization: Bearer $API_KEY"
```

### Flow Runs But No Data

**Diagnostic Steps:**

1. **Check Export Query**
   ```bash
   # Get export details
   curl -X GET "https://api.integrator.io/v1/exports/{export_id}" \
     -H "Authorization: Bearer $API_KEY"
   ```

2. **Verify Delta Configuration**
   - Check `lastExportDateTime` value
   - Ensure delta field exists in source data
   - Test with full export first

3. **Review Filters**
   - Check output filters aren't excluding all records
   - Verify filter expressions are correct

### High Error Rates

**Investigation:**

1. **Get Error Details**
   ```bash
   curl -X GET "https://api.integrator.io/v1/flows/{flow_id}/imports/{import_id}/errors" \
     -H "Authorization: Bearer $API_KEY"
   ```

2. **Common Error Types:**
   - `FIELD_VALIDATION_ERROR` - Mapping issues
   - `DUPLICATE_RECORD` - Upsert key problems
   - `CONNECTION_ERROR` - Destination unavailable
   - `LOOKUP_NOT_FOUND` - Missing reference data

3. **Get Retry Data**
   ```bash
   curl -X GET "https://api.integrator.io/v1/flows/{flow_id}/imports/{import_id}/errors/{retry_data_key}" \
     -H "Authorization: Bearer $API_KEY"
   ```

## API Response Issues

### Empty Response

**Possible Causes:**
1. No matching data
2. Pagination at end
3. Filter too restrictive

**Solutions:**
- Remove filters and test
- Check pagination parameters
- Verify query syntax

### Truncated Response

**Causes:**
- Response exceeds size limit
- Timeout during transfer

**Solutions:**
- Use pagination with smaller page sizes
- Filter to reduce result set
- Use specific field selection if available

### Unexpected Data Format

**Diagnostic:**
```python
# Log full response for debugging
response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")
print(f"Headers: {response.headers}")
print(f"Body: {response.text[:1000]}")
```

## Rate Limiting

### 429 Too Many Requests

**Symptoms:**
```json
{
  "errors": [{
    "code": "rate_limit_exceeded",
    "message": "Too many requests"
  }]
}
```

**Solutions:**

1. **Implement Backoff**
   ```python
   import time

   def api_call_with_retry(url, max_retries=3):
       for attempt in range(max_retries):
           response = requests.get(url, headers=headers)

           if response.status_code == 429:
               wait_time = int(response.headers.get('Retry-After', 60))
               time.sleep(wait_time)
               continue

           return response

       raise Exception("Max retries exceeded")
   ```

2. **Batch Operations**
   - Combine multiple operations where possible
   - Use bulk endpoints for data updates

3. **Cache Results**
   - Cache frequently accessed data
   - Use state API for persistent storage

## Common Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| 400 | Bad Request | Check request syntax |
| 401 | Unauthorized | Verify API key |
| 403 | Forbidden | Check permissions |
| 404 | Not Found | Verify resource ID |
| 409 | Conflict | Resource in use |
| 422 | Validation Error | Fix payload data |
| 429 | Rate Limited | Reduce frequency |
| 500 | Server Error | Retry later |
| 502 | Bad Gateway | Retry later |
| 503 | Unavailable | Retry later |

## Debugging Techniques

### Enable Debug Logging

```python
import logging
import requests

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('urllib3').setLevel(logging.DEBUG)

# Make request with logging
response = requests.get(url, headers=headers)
```

### Capture Request/Response

```python
def debug_request(method, url, **kwargs):
    import json

    print(f"=== REQUEST ===")
    print(f"{method} {url}")
    print(f"Headers: {kwargs.get('headers', {})}")
    if 'json' in kwargs:
        print(f"Body: {json.dumps(kwargs['json'], indent=2)}")

    response = requests.request(method, url, **kwargs)

    print(f"\n=== RESPONSE ===")
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    try:
        print(f"Body: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Body: {response.text[:500]}")

    return response
```

### Use Connection Debug Logs

```bash
# Get connection debug logs
curl -X GET "https://api.integrator.io/v1/connections/{connection_id}/debuglog" \
  -H "Authorization: Bearer $API_KEY"
```

## Performance Issues

### Slow API Responses

**Causes:**
1. Large result sets
2. Complex queries
3. Network latency

**Solutions:**
1. Use pagination with smaller page sizes
2. Add filters to reduce data
3. Cache frequently accessed data
4. Use regional endpoints if available

### Memory Issues with Large Data

```python
# Stream large responses
def stream_large_response(url, headers):
    with requests.get(url, headers=headers, stream=True) as response:
        for chunk in response.iter_content(chunk_size=8192):
            process_chunk(chunk)
```

### Batch Processing Optimization

```python
def process_in_batches(items, batch_size=100):
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        yield batch
        time.sleep(0.5)  # Rate limit protection
```

## Getting Help

### Information to Collect

When reporting issues, gather:

1. **Request Details**
   - Full URL (without API key)
   - HTTP method
   - Request headers
   - Request body (sanitized)

2. **Response Details**
   - HTTP status code
   - Response headers
   - Error message/body

3. **Context**
   - Flow/integration IDs
   - Approximate time of error
   - Steps to reproduce

### Support Resources

- **Documentation**: https://docs.celigo.com
- **API Reference**: https://api.integrator.io/docs
- **Community**: https://community.celigo.com
- **Support Portal**: https://support.celigo.com

### Health Check Script

```python
def health_check(api_key):
    """Run comprehensive API health check."""
    base_url = "https://api.integrator.io/v1"
    headers = {"Authorization": f"Bearer {api_key}"}

    checks = {
        "auth": "/integrations",
        "connections": "/connections",
        "flows": "/flows",
        "jobs": "/jobs?limit=1"
    }

    results = {}
    for name, endpoint in checks.items():
        try:
            response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
            results[name] = {
                "status": response.status_code,
                "ok": response.status_code == 200
            }
        except Exception as e:
            results[name] = {"status": "error", "message": str(e), "ok": False}

    return results

# Run check
results = health_check(os.environ['CELIGO_API_KEY'])
for check, result in results.items():
    status = "✅" if result['ok'] else "❌"
    print(f"{status} {check}: {result['status']}")
```
