# Flows API Reference

Flows are data processing pipelines containing exports (sources) and imports (destinations).

## Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List all | GET | `/flows` |
| Get one | GET | `/flows/{id}` |
| Create | POST | `/flows` |
| Update | PUT | `/flows/{id}` |
| Delete | DELETE | `/flows/{id}` |
| Run flow | POST | `/flows/{id}/run` |
| Get latest jobs | GET | `/flows/{id}/jobs/latest` |
| Get audit log | GET | `/flows/{id}/audit` |
| Get dependencies | GET | `/flows/{id}/dependencies` |
| Get descendants | GET | `/flows/{id}/descendants` |
| Download template | GET | `/flows/{id}/template` |
| Get last export time | GET | `/flows/{id}/lastExportDateTime` |

## Flow Object

```json
{
  "_id": "flow123",
  "name": "Customer Sync",
  "description": "Sync customers from Salesforce to NetSuite",
  "_integrationId": "int123",
  "disabled": false,
  "schedule": "0 */6 * * *",
  "timezone": "America/Los_Angeles",
  "pageGenerators": [
    {
      "_exportId": "exp123",
      "skipRetries": false
    }
  ],
  "pageProcessors": [
    {
      "type": "import",
      "_importId": "imp123"
    }
  ],
  "createdAt": "2024-01-01T00:00:00.000Z",
  "lastModified": "2024-01-15T12:00:00.000Z"
}
```

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `_id` | string | Unique identifier |
| `name` | string | Display name (required) |
| `description` | string | Optional description |
| `_integrationId` | string | Parent integration ID |
| `disabled` | boolean | Flow enabled/disabled |
| `schedule` | string | Cron expression for scheduling |
| `timezone` | string | Timezone for schedule |
| `pageGenerators` | array | Export configurations (sources) |
| `pageProcessors` | array | Import/lookup configurations (destinations) |
| `_runNextFlowIds` | array | Flows to trigger after completion |

## Flow Structure

```
Flow
├── pageGenerators (exports/sources)
│   └── Export → Extracts data from source
└── pageProcessors (imports/destinations)
    ├── Import → Loads data to destination
    └── Lookup → Enriches data from reference
```

## Operations

### List All Flows

```bash
curl -X GET "https://api.integrator.io/v1/flows" \
  -H "Authorization: Bearer $API_KEY"
```

**Query Parameters:**
```
?_integrationId=abc123    # Filter by integration
?disabled=false           # Only enabled flows
```

### Get Single Flow

```bash
curl -X GET "https://api.integrator.io/v1/flows/{flow_id}" \
  -H "Authorization: Bearer $API_KEY"
```

### Create Flow

```bash
curl -X POST "https://api.integrator.io/v1/flows" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Data Flow",
    "description": "Sync data between systems",
    "_integrationId": "integration_id",
    "disabled": true,
    "pageGenerators": [
      {"_exportId": "export_id"}
    ],
    "pageProcessors": [
      {"type": "import", "_importId": "import_id"}
    ]
  }'
```

### Update Flow

```bash
curl -X PUT "https://api.integrator.io/v1/flows/{flow_id}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Flow Name",
    "disabled": false,
    "schedule": "0 0 * * *"
  }'
```

### Delete Flow

```bash
curl -X DELETE "https://api.integrator.io/v1/flows/{flow_id}" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:** 204 No Content

### Run Flow (Trigger Execution)

```bash
curl -X POST "https://api.integrator.io/v1/flows/{flow_id}/run" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json"
```

**With Specific Exports:**
```bash
curl -X POST "https://api.integrator.io/v1/flows/{flow_id}/run" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "_exportIds": ["export1", "export2"]
  }'
```

**With Date Range (Delta Flows):**
```bash
curl -X POST "https://api.integrator.io/v1/flows/{flow_id}/run" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "startDate": "2024-01-01T00:00:00.000Z",
    "endDate": "2024-01-31T23:59:59.999Z"
  }'
```

**Response:**
```json
{
  "_jobId": "job123",
  "_exportId": "exp123",
  "flowExecutionGroupId": "group123"
}
```

### Get Latest Jobs

```bash
curl -X GET "https://api.integrator.io/v1/flows/{flow_id}/jobs/latest" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:**
```json
[
  {
    "_id": "job123",
    "type": "flow",
    "status": "completed",
    "numSuccess": 100,
    "numError": 2,
    "startedAt": "2024-01-15T10:00:00.000Z",
    "endedAt": "2024-01-15T10:05:00.000Z"
  }
]
```

### Get Last Export DateTime

```bash
curl -X GET "https://api.integrator.io/v1/flows/{flow_id}/lastExportDateTime" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:**
```json
{
  "lastExportDateTime": "2024-01-15T10:00:00.000Z"
}
```

### Get Audit Log

```bash
curl -X GET "https://api.integrator.io/v1/flows/{flow_id}/audit" \
  -H "Authorization: Bearer $API_KEY"
```

### Get Flow Descendants

Returns full export and import configurations:

```bash
curl -X GET "https://api.integrator.io/v1/flows/{flow_id}/descendants" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:**
```json
{
  "exports": [
    {"_id": "exp123", "name": "Customer Export", ...}
  ],
  "imports": [
    {"_id": "imp123", "name": "Customer Import", ...}
  ]
}
```

## Schedule Configuration

### Cron Expression Format
```
┌───────────── minute (0-59)
│ ┌───────────── hour (0-23)
│ │ ┌───────────── day of month (1-31)
│ │ │ ┌───────────── month (1-12)
│ │ │ │ ┌───────────── day of week (0-6, Sunday=0)
│ │ │ │ │
* * * * *
```

### Examples
```
"0 0 * * *"      # Daily at midnight
"0 */6 * * *"    # Every 6 hours
"0 9 * * 1-5"    # Weekdays at 9am
"*/15 * * * *"   # Every 15 minutes
"0 0 1 * *"      # Monthly on 1st
```

## Flow States

| Status | Description |
|--------|-------------|
| `enabled` | Flow runs on schedule |
| `disabled` | Flow won't run (manual only) |
| `running` | Currently executing |

## Common Use Cases

### Enable/Disable Flow

```bash
# Disable
curl -X PUT "https://api.integrator.io/v1/flows/{flow_id}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"disabled": true}'

# Enable
curl -X PUT "https://api.integrator.io/v1/flows/{flow_id}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"disabled": false}'
```

### Update Schedule

```bash
curl -X PUT "https://api.integrator.io/v1/flows/{flow_id}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "schedule": "0 */2 * * *",
    "timezone": "UTC"
  }'
```

### Chain Flows

```bash
curl -X PUT "https://api.integrator.io/v1/flows/{flow_id}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "_runNextFlowIds": ["next_flow_id_1", "next_flow_id_2"]
  }'
```

## Error Handling

### Flow Running
```json
{
  "errors": [{
    "code": "conflict",
    "message": "Flow is currently running"
  }]
}
```

### Invalid Schedule
```json
{
  "errors": [{
    "code": "validation_error",
    "message": "Invalid cron expression",
    "field": "schedule"
  }]
}
```

### Missing Export/Import
```json
{
  "errors": [{
    "code": "not_found",
    "message": "Export not found: exp123"
  }]
}
```
