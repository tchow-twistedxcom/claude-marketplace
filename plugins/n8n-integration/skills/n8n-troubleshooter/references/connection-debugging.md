# n8n Connection Debugging Guide

Diagnosing and resolving network and connection issues in n8n workflows.

## Connection Issue Categories

### DNS Resolution
```yaml
errors:
  - ENOTFOUND
  - getaddrinfo ENOTFOUND

symptoms:
  - Cannot resolve hostname
  - Domain not found

diagnosis:
  1. Verify hostname spelling
  2. Test DNS from n8n host:
     - nslookup hostname
     - dig hostname
  3. Check DNS configuration

resolution:
  - Fix hostname typos
  - Configure DNS server
  - Use IP address as fallback
  - Check /etc/hosts file
```

### TCP Connection
```yaml
errors:
  - ECONNREFUSED
  - ECONNRESET
  - ETIMEDOUT
  - EHOSTUNREACH

symptoms:
  - Cannot establish connection
  - Connection dropped
  - Connection too slow

diagnosis:
  1. Verify target is reachable
  2. Check port is correct
  3. Test with telnet/nc:
     - telnet host port
     - nc -zv host port
  4. Check firewall rules

resolution:
  - Start target service
  - Open firewall ports
  - Correct port number
  - Check network path
```

### SSL/TLS
```yaml
errors:
  - SELF_SIGNED_CERT_IN_CHAIN
  - UNABLE_TO_VERIFY_LEAF_SIGNATURE
  - CERT_HAS_EXPIRED
  - ERR_TLS_CERT_ALTNAME_INVALID

symptoms:
  - SSL handshake failure
  - Certificate validation error

diagnosis:
  1. Check certificate validity
  2. Verify certificate chain
  3. Check hostname match
  4. Review SSL configuration

resolution:
  - Use valid certificate
  - Add CA to trust store
  - Fix hostname mismatch
  - Disable SSL verify (last resort)
```

## HTTP Request Node Issues

### Authentication Problems
```yaml
credential_types:
  basic_auth:
    issues:
      - Wrong username/password
      - Encoding issues
    check:
      - Credential values
      - Base64 encoding

  bearer_token:
    issues:
      - Token expired
      - Wrong token format
    check:
      - Token validity
      - Expiration time

  oauth2:
    issues:
      - Refresh token expired
      - Scope insufficient
      - Redirect URI mismatch
    check:
      - OAuth configuration
      - Token refresh
      - App permissions

  api_key:
    issues:
      - Key invalid
      - Wrong header name
    check:
      - Key value
      - Header configuration
```

### Request Configuration
```yaml
common_issues:
  wrong_method:
    symptom: 405 Method Not Allowed
    fix: Use correct HTTP method

  missing_headers:
    symptom: 400 Bad Request
    fix: Add required headers (Content-Type, Accept)

  wrong_content_type:
    symptom: 415 Unsupported Media Type
    fix: Set correct Content-Type header

  body_format:
    symptom: Invalid JSON / Parse error
    fix: Validate JSON body structure
```

### URL Configuration
```yaml
issues:
  wrong_url:
    cause: Typo or incorrect path
    check: Compare with API documentation

  missing_path_params:
    cause: Template variables not replaced
    check: Verify expression evaluation

  query_params:
    cause: Wrong format or encoding
    check: URL encoding, parameter names

  base_url:
    cause: Environment mismatch
    check: Dev vs prod URL
```

## Webhook Issues

### Webhook Not Responding
```yaml
problem: Webhook returns 404
causes:
  - Workflow not active
  - Wrong webhook path
  - Production vs test URL

diagnosis:
  1. Check workflow active status
  2. Verify webhook URL
  3. Test webhook path
  4. Check n8n logs

resolution:
  - Activate workflow (manual)
  - Copy correct webhook URL
  - Use production URL for active workflow
```

### Webhook Timeout
```yaml
problem: Webhook request times out
causes:
  - Workflow takes too long
  - Response mode misconfigured
  - Large data processing

resolution:
  - Use "Respond Immediately" mode
  - Optimize workflow execution
  - Increase client timeout
```

### Webhook Authentication
```yaml
problem: Webhook requests rejected
causes:
  - Missing authentication
  - Wrong credentials
  - IP not allowed

resolution:
  - Configure webhook authentication
  - Update caller with credentials
  - Whitelist source IP
```

## External API Issues

### Rate Limiting
```yaml
error: 429 Too Many Requests
causes:
  - Exceeded API rate limit
  - Too many concurrent requests

diagnosis:
  - Check rate limit headers
  - Review request frequency

resolution:
  - Add delays between requests
  - Implement exponential backoff
  - Use batch operations
  - Cache responses
```

### API Versioning
```yaml
problem: API returns unexpected results
causes:
  - API version changed
  - Deprecated endpoints
  - New required fields

resolution:
  - Check API changelog
  - Update endpoint URLs
  - Add new required fields
  - Use versioned endpoints
```

### Pagination
```yaml
problem: Missing data from API
causes:
  - Only first page returned
  - Pagination not handled

resolution:
  - Implement pagination loop
  - Use HTTP Request node with pagination
  - Process pages in batches
```

## Database Connection Issues

### Connection Errors
```yaml
common_errors:
  ECONNREFUSED:
    cause: Database not running or wrong port
    fix: Start database, check port

  ENOTFOUND:
    cause: Wrong hostname
    fix: Verify database host

  ETIMEDOUT:
    cause: Network issue or firewall
    fix: Check network path, firewall

  authentication_failed:
    cause: Wrong credentials
    fix: Update credentials in n8n
```

### Query Issues
```yaml
problems:
  syntax_error:
    cause: Invalid SQL/query
    fix: Validate query syntax

  timeout:
    cause: Query too complex
    fix: Optimize query, add indexes

  permission_denied:
    cause: Insufficient privileges
    fix: Grant required permissions
```

## Debugging Techniques

### Request Logging
```yaml
technique: Log full request
steps:
  1. Add Set node before HTTP request
  2. Log request configuration
  3. Check actual values sent

benefits:
  - See actual URL with variables resolved
  - Verify headers and body
  - Debug expression results
```

### Response Inspection
```yaml
technique: Capture and log response
steps:
  1. Set HTTP node to return full response
  2. Add Set node to extract parts
  3. Log status, headers, body

benefits:
  - See complete response
  - Understand error details
  - Debug content type issues
```

### Network Testing
```yaml
technique: Test from n8n host
steps:
  1. Access n8n server shell
  2. Use curl to test endpoint:
     curl -v https://api.example.com/endpoint
  3. Compare with n8n behavior

benefits:
  - Isolate n8n vs network issues
  - Test authentication
  - Verify SSL/TLS
```

### Proxy Configuration
```yaml
technique: Use proxy for debugging
steps:
  1. Configure n8n to use proxy
  2. Capture requests in proxy
  3. Analyze request/response

tools:
  - mitmproxy
  - Charles Proxy
  - Fiddler
```

## Resolution Patterns

### Retry Logic
```yaml
pattern: Implement retries
when: Transient failures
implementation:
  - Enable "Retry On Fail" on node
  - Configure retry count
  - Set wait between retries
  - Consider exponential backoff
```

### Timeout Configuration
```yaml
pattern: Adjust timeouts
when: Slow responses
implementation:
  - Set node-level timeout
  - Configure workflow timeout
  - Match client expectations
```

### Fallback Strategy
```yaml
pattern: Handle failures gracefully
when: Non-critical integrations
implementation:
  - Add IF node for error check
  - Route to alternative path
  - Log failures for review
  - Continue workflow execution
```

### Circuit Breaker
```yaml
pattern: Prevent cascade failures
when: Repeated failures to same service
implementation:
  - Track failure count
  - Stop requests after threshold
  - Retry after cooldown
  - Alert on circuit open
```

## Quick Reference

| Symptom | First Check | Common Fix |
|---------|-------------|------------|
| 404 on webhook | Workflow active? | Activate workflow |
| Connection refused | Service running? | Start service |
| Timeout | Service responsive? | Increase timeout |
| 401/403 | Credentials valid? | Update credentials |
| SSL error | Certificate valid? | Fix certificate |
| DNS failure | Hostname correct? | Fix spelling |
