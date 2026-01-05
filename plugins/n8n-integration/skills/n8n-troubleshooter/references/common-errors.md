# n8n Common Errors Catalog

Comprehensive catalog of n8n errors with causes and resolutions.

## HTTP/Network Errors

### ECONNREFUSED
```yaml
error: "connect ECONNREFUSED 127.0.0.1:3000"
category: Connection
severity: High

causes:
  - Target service not running
  - Wrong port number
  - Firewall blocking connection
  - Service crashed

diagnosis:
  - Verify service is running
  - Check port configuration
  - Test connectivity from n8n host
  - Review firewall rules

resolution:
  - Start/restart target service
  - Correct port number in node
  - Update firewall rules
  - Check service logs for crashes
```

### ETIMEDOUT
```yaml
error: "ETIMEDOUT: Connection timed out"
category: Connection
severity: Medium

causes:
  - Service responding slowly
  - Network latency issues
  - Timeout configured too low
  - Large payload processing

diagnosis:
  - Check service response times
  - Test with curl/Postman
  - Review timeout settings
  - Check payload sizes

resolution:
  - Increase timeout value
  - Optimize service performance
  - Reduce payload size
  - Add retry logic
```

### ENOTFOUND
```yaml
error: "getaddrinfo ENOTFOUND api.example.com"
category: DNS
severity: High

causes:
  - Domain doesn't exist
  - DNS resolution failure
  - Typo in hostname
  - DNS server issues

diagnosis:
  - Verify domain spelling
  - Test DNS resolution
  - Check DNS server configuration

resolution:
  - Correct hostname spelling
  - Use IP address if DNS unreliable
  - Configure alternative DNS
```

### SELF_SIGNED_CERT_IN_CHAIN
```yaml
error: "self signed certificate in certificate chain"
category: SSL/TLS
severity: Medium

causes:
  - Self-signed certificate
  - Custom CA not trusted
  - Certificate chain incomplete

diagnosis:
  - Check certificate configuration
  - Verify CA certificates

resolution:
  - Add CA to trusted store
  - Use proper SSL certificate
  - Disable SSL verification (not recommended)
```

## HTTP Status Errors

### 400 Bad Request
```yaml
error: "400 Bad Request"
category: Client Error
severity: Medium

causes:
  - Invalid request body
  - Missing required fields
  - Wrong data format
  - Invalid parameters

diagnosis:
  - Review request body structure
  - Check API documentation
  - Validate JSON format
  - Verify required fields

resolution:
  - Fix request body format
  - Add missing required fields
  - Correct data types
  - Match API specification
```

### 401 Unauthorized
```yaml
error: "401 Unauthorized"
category: Authentication
severity: High

causes:
  - Invalid credentials
  - Expired token
  - Missing authentication
  - Wrong auth method

diagnosis:
  - Check credential configuration
  - Verify token validity
  - Review auth headers
  - Check OAuth status

resolution:
  - Update credentials in n8n
  - Refresh OAuth tokens
  - Re-authenticate
  - Verify API key validity
```

### 403 Forbidden
```yaml
error: "403 Forbidden"
category: Authorization
severity: High

causes:
  - Insufficient permissions
  - IP not whitelisted
  - Account restricted
  - Resource access denied

diagnosis:
  - Check API permissions
  - Review IP restrictions
  - Verify account status
  - Check resource access

resolution:
  - Request additional permissions
  - Whitelist n8n IP address
  - Contact account admin
  - Use correct resource identifiers
```

### 404 Not Found
```yaml
error: "404 Not Found"
category: Resource
severity: Medium

causes:
  - Wrong URL/endpoint
  - Resource doesn't exist
  - API version mismatch
  - Typo in path

diagnosis:
  - Verify endpoint URL
  - Check resource exists
  - Review API documentation
  - Validate path parameters

resolution:
  - Correct endpoint URL
  - Verify resource ID
  - Update API version
  - Fix path parameters
```

### 429 Too Many Requests
```yaml
error: "429 Too Many Requests"
category: Rate Limiting
severity: Medium

causes:
  - API rate limit exceeded
  - Too many concurrent requests
  - Quota exhausted

diagnosis:
  - Check rate limit headers
  - Review request frequency
  - Check quota usage

resolution:
  - Implement rate limiting
  - Add delays between requests
  - Use batch operations
  - Upgrade API plan
```

### 500 Internal Server Error
```yaml
error: "500 Internal Server Error"
category: Server Error
severity: High

causes:
  - Server-side bug
  - Database issues
  - Service overload
  - Infrastructure problems

diagnosis:
  - Check if issue is consistent
  - Review error response body
  - Check service status page
  - Test with simpler request

resolution:
  - Wait and retry
  - Simplify request
  - Contact service support
  - Implement error handling
```

### 502 Bad Gateway
```yaml
error: "502 Bad Gateway"
category: Server Error
severity: High

causes:
  - Upstream server failure
  - Proxy configuration issues
  - Service temporarily unavailable

diagnosis:
  - Check upstream service status
  - Review proxy configuration
  - Test direct connection

resolution:
  - Wait for service recovery
  - Implement retry logic
  - Check service status
```

### 503 Service Unavailable
```yaml
error: "503 Service Unavailable"
category: Server Error
severity: High

causes:
  - Service maintenance
  - Server overloaded
  - Deployment in progress

diagnosis:
  - Check service status page
  - Review maintenance schedule
  - Monitor service availability

resolution:
  - Wait for service recovery
  - Schedule workflows around maintenance
  - Implement retry with backoff
```

## n8n-Specific Errors

### NodeOperationError
```yaml
error: "NodeOperationError: The operation failed"
category: Node Execution
severity: Variable

causes:
  - Invalid node configuration
  - Unsupported operation
  - Missing required input
  - Data format mismatch

diagnosis:
  - Check node parameters
  - Review input data
  - Verify operation selection
  - Check node documentation

resolution:
  - Fix node configuration
  - Transform input data
  - Select correct operation
  - Follow node requirements
```

### ExpressionError
```yaml
error: "ExpressionError: Invalid expression"
category: Expression
severity: Medium

causes:
  - Syntax error in expression
  - Undefined variable
  - Invalid function call
  - Missing brackets

diagnosis:
  - Check expression syntax
  - Verify variable references
  - Validate function usage

resolution:
  - Fix bracket balance {{ }}
  - Correct variable paths
  - Use valid n8n functions
  - Check data availability
```

### WorkflowActivationError
```yaml
error: "WorkflowActivationError: Workflow could not be activated"
category: Activation
severity: High

causes:
  - Invalid trigger configuration
  - Missing credentials
  - Webhook path conflict
  - Node configuration error

diagnosis:
  - Check trigger node setup
  - Verify credentials assigned
  - Check webhook uniqueness
  - Validate all nodes

resolution:
  - Configure trigger properly
  - Set up credentials
  - Use unique webhook path
  - Fix validation errors
```

### CredentialNotFoundError
```yaml
error: "CredentialNotFoundError: Credential not found"
category: Credentials
severity: High

causes:
  - Credential deleted
  - Credential renamed
  - Wrong credential selected
  - Access permissions

diagnosis:
  - Check credential exists
  - Verify credential name
  - Review access permissions

resolution:
  - Create new credential
  - Update credential reference
  - Request credential access
```

## Data Processing Errors

### TypeError
```yaml
error: "TypeError: Cannot read property 'x' of undefined"
category: Data
severity: Medium

causes:
  - Null/undefined value
  - Wrong JSON path
  - Missing data field
  - Empty response

diagnosis:
  - Check input data structure
  - Verify data paths
  - Review null handling
  - Check upstream node output

resolution:
  - Add null checks
  - Fix JSON paths
  - Handle empty data
  - Add default values
```

### JSON Parse Error
```yaml
error: "SyntaxError: Unexpected token"
category: Data
severity: Medium

causes:
  - Invalid JSON format
  - Malformed response
  - Encoding issues
  - Truncated data

diagnosis:
  - Validate JSON syntax
  - Check response format
  - Review encoding settings
  - Check for truncation

resolution:
  - Fix JSON structure
  - Handle non-JSON responses
  - Correct encoding
  - Increase size limits
```

### MaxItemsExceeded
```yaml
error: "MaxItemsExceeded: Too many items"
category: Limits
severity: Medium

causes:
  - Too much data to process
  - Batch too large
  - No pagination

diagnosis:
  - Check item count
  - Review batch settings
  - Assess data volume

resolution:
  - Implement pagination
  - Process in smaller batches
  - Filter unnecessary items
```

## Webhook Errors

### Webhook Not Found
```yaml
error: "Webhook not found (404)"
category: Webhook
severity: High

causes:
  - Workflow not active
  - Wrong webhook path
  - Webhook deleted
  - Path changed

diagnosis:
  - Verify workflow is active
  - Check webhook URL
  - Confirm path matches

resolution:
  - Activate workflow (manual)
  - Correct webhook path
  - Update webhook URL
```

### Webhook Method Not Allowed
```yaml
error: "Method Not Allowed (405)"
category: Webhook
severity: Medium

causes:
  - Wrong HTTP method
  - Webhook expects different method

diagnosis:
  - Check expected HTTP method
  - Review webhook configuration

resolution:
  - Use correct HTTP method
  - Update webhook settings
```

## Node Version Errors

### compareOperationFunctions Error
```yaml
error: "compareOperationFunctions[compareData.operation] is not a function"
category: Node Version
severity: High

causes:
  - If node typeVersion=1 but conditions use v2 format
  - Missing combineOperation field in v1 If node
  - Version mismatch between node structure and typeVersion

diagnosis:
  - Check If node typeVersion field
  - Compare conditions structure against expected format
  - Look for combineOperation (v1) vs combinator (v2)

resolution:
  - Upgrade typeVersion to 2 and use v2 format
  - Or add missing combineOperation for v1
  - See node-patterns.md for v1 vs v2 format examples

v1_format:
  conditions:
    string:
      - value1: "={{ $json.field }}"
        operation: "equals"
        value2: "value"
  combineOperation: "all"

v2_format:
  conditions:
    conditions:
      - leftValue: "={{ $json.field }}"
        rightValue: "value"
        operator:
          type: "string"
          operation: "equals"
    combinator: "and"
```

### Data Table ID Format Error
```yaml
error: "The workflow has issues and cannot be executed"
category: Configuration
severity: High

causes:
  - tableId.value contains table name instead of ID
  - Resource locator mode=list expects internal ID
  - Table ID is empty or malformed

diagnosis:
  - Check Data Table node tableId.value
  - IDs are alphanumeric (e.g., "0vQXXKgjO8WncMK2")
  - Names contain spaces/punctuation

resolution:
  - Find table ID from n8n UI URL or API
  - Update tableId.value to use internal ID
  - Keep mode: "list" unchanged

finding_table_id:
  - UI: Open n8n → Data Tables → URL contains ID
  - API: GET /api/v1/data-tables
  - CLI: python3 n8n_api.py data-tables list
```

### Environment Variable Access Denied
```yaml
error: "access to env vars denied" or silent empty value
category: Security
severity: Medium

causes:
  - N8N_BLOCK_ENV_ACCESS_IN_NODE=true (default in n8n v2.0+)
  - Security policy blocking $env access
  - Code node cannot access process.env

diagnosis:
  - Check n8n environment configuration
  - Look for $env usage in expressions
  - Test if $env returns empty/null (fails silently!)

resolution:
  - Use n8n credentials store instead (recommended)
  - Or set N8N_BLOCK_ENV_ACCESS_IN_NODE=false (not recommended)
  - Create credentials via API and reference by ID

recommended_approach:
  1. Create credential via API:
     python3 n8n_api.py credentials create \
       --name "My Token" --type httpHeaderAuth \
       --data '{"name":"X-Token","value":"secret"}'
  2. Reference credential in node:
     credentials:
       httpHeaderAuth:
         id: "credential-id"
         name: "My Token"
```

## Quick Reference Table

| Error Code | Category | First Action |
|------------|----------|--------------|
| ECONNREFUSED | Network | Check target service |
| ETIMEDOUT | Network | Increase timeout |
| 401 | Auth | Check credentials |
| 403 | Auth | Check permissions |
| 404 | Resource | Verify URL/path |
| 429 | Rate Limit | Add delays |
| 500/502/503 | Server | Wait and retry |
| Expression | Config | Check syntax |
| Credential | Config | Update in UI |
| compareOperationFunctions | Node Version | Check If node typeVersion vs format |
| workflow has issues | Data Table | Use internal table ID, not name |
| env vars denied | Security | Use credentials store instead of $env |
