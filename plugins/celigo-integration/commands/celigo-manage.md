---
name: celigo-manage
description: Manage Celigo integrations, flows, and connections
---

# Celigo Integration Management

Execute Celigo integration platform operations using MCP tools.

## Usage

When the user requests Celigo operations:

### Integration Management

**List Integrations**
```
User: "List all my Celigo integrations"
Action: Use list_integrations tool, display name, status, version
```

**Get Integration Details**
```
User: "Show details for integration XYZ"
Action: Use get_integration tool, display full configuration
```

**Create Integration**
```
User: "Create a new Salesforce to NetSuite integration"
Action:
1. Gather requirements (source, destination, mapping)
2. Use create_integration tool
3. Confirm creation and provide integration ID
```

**Clone Integration**
```
User: "Clone the order sync integration"
Action: Use clone_integration tool with new name
```

### Flow Management

**List Flows**
```
User: "Show all flows in the customer sync integration"
Action: Use list_flows tool with integration filter
```

**Trigger Flow**
```
User: "Run the customer export flow"
Action:
1. Find flow by name
2. Use trigger_flow_run tool
3. Monitor job status
4. Report results
```

**Update Flow**
```
User: "Update the mapping in the product flow"
Action:
1. Get current flow configuration
2. Apply mapping updates
3. Use update_flow tool
4. Verify changes
```

### Connection Management

**List Connections**
```
User: "What connections are configured?"
Action: Use list_connections tool, display type and status
```

**Test Connection**
```
User: "Test the Salesforce connection"
Action: Use test_connection tool, report health status
```

**Create Connection**
```
User: "Add a new NetSuite connection"
Action:
1. Ask for connection details (auth, credentials)
2. Use create_connection tool
3. Test connection
4. Confirm setup
```

### Job & Error Management

**Monitor Jobs**
```
User: "Show recent integration jobs"
Action: Use list_jobs tool with time filter, show status
```

**Retry Failed Jobs**
```
User: "Retry all failed jobs from yesterday"
Action:
1. List failed jobs with date filter
2. Use retry_job for each
3. Report retry results
```

**View Errors**
```
User: "Show errors for the order sync integration"
Action: Use list_errors tool, display error details and counts
```

**Clear Errors**
```
User: "Clear resolved errors from last week"
Action: Use clear_errors tool with date filter
```

### Export & Import Management

**List Exports**
```
User: "Show all data exports"
Action: Use list_exports tool, display name, status, schedule
```

**Trigger Export**
```
User: "Run the customer export now"
Action: Use trigger_export tool, monitor completion
```

### Tag Management

**List Tags**
```
User: "What tags are available?"
Action: Use list_tags tool
```

**Tag Integration**
```
User: "Add 'production' tag to customer sync"
Action: Use add_tag_to_integration tool
```

## Best Practices

### Before Making Changes
1. **Backup Configuration**: Export integration before updates
2. **Test in Sandbox**: Use test environment first
3. **Verify Connections**: Test connections before running flows
4. **Check Dependencies**: Review integration dependencies

### Monitoring
1. **Regular Job Review**: Check job success rates
2. **Error Tracking**: Monitor and resolve errors promptly
3. **Performance**: Track integration execution times
4. **Data Quality**: Validate data transformations

### Troubleshooting
1. **Check Logs**: Review job logs for detailed errors
2. **Test Connections**: Verify API connectivity
3. **Validate Mappings**: Ensure field mappings are correct
4. **Review Permissions**: Check API token permissions

## Common Workflows

### Daily Health Check
```
1. List recent jobs (last 24h)
2. Check for failed jobs
3. Review error counts
4. Test critical connections
5. Report status summary
```

### Create New Integration
```
1. Create source connection
2. Create destination connection
3. Test both connections
4. Create integration
5. Create flows (import/export)
6. Configure mappings
7. Test with sample data
8. Enable and monitor
```

### Troubleshoot Failed Jobs
```
1. Get job details
2. List job errors
3. Analyze error patterns
4. Fix root cause (mapping, connection, data)
5. Retry failed jobs
6. Verify success
7. Clear resolved errors
```

## Error Codes Reference

Common Celigo error patterns:

- **401**: Authentication failed - check API token
- **403**: Permission denied - verify token scope
- **404**: Resource not found - check integration/flow ID
- **429**: Rate limit exceeded - reduce API calls
- **500**: Server error - retry after delay

## Security Notes

- Always use environment variables for tokens
- Never log sensitive data
- Rotate API tokens regularly
- Use role-based access in Celigo
- Monitor API usage for anomalies
