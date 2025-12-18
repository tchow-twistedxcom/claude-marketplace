# Jobs API Reference

Jobs represent execution instances of flows. Each flow run creates job records for tracking status and metrics.

## Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List all | GET | `/jobs` |
| Get one | GET | `/jobs/{id}` |
| Cancel | DELETE | `/jobs/{id}` |

## Job Object

```json
{
  "_id": "job123",
  "type": "flow",
  "status": "completed",
  "_integrationId": "int123",
  "_flowId": "flow123",
  "_exportId": "exp123",
  "numSuccess": 100,
  "numError": 2,
  "numIgnore": 5,
  "numExport": 107,
  "numPagesGenerated": 2,
  "numPagesProcessed": 2,
  "doneExporting": true,
  "flowExecutionGroupId": "group123",
  "createdAt": "2024-01-15T10:00:00.000Z",
  "startedAt": "2024-01-15T10:00:01.000Z",
  "endedAt": "2024-01-15T10:05:00.000Z",
  "lastModified": "2024-01-15T10:05:00.000Z",
  "purgeAt": "2024-02-14T10:05:00.000Z"
}
```

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `_id` | string | Unique identifier |
| `type` | string | Job type: flow, export, import |
| `status` | string | Current status |
| `_integrationId` | string | Parent integration |
| `_flowId` | string | Associated flow |
| `_exportId` | string | Associated export |
| `numSuccess` | number | Successful records |
| `numError` | number | Failed records |
| `numIgnore` | number | Filtered/ignored records |
| `numExport` | number | Total exported records |
| `numPagesGenerated` | number | Pages extracted |
| `numPagesProcessed` | number | Pages loaded |
| `doneExporting` | boolean | Export phase complete |
| `flowExecutionGroupId` | string | Groups related jobs |
| `createdAt` | string | Job creation time |
| `startedAt` | string | Execution start time |
| `endedAt` | string | Execution end time |
| `purgeAt` | string | When job data expires |

## Job Types

| Type | Description |
|------|-------------|
| `flow` | Top-level flow execution |
| `export` | Export/extraction job |
| `import` | Import/load job |

## Job Statuses

| Status | Description |
|--------|-------------|
| `queued` | Waiting to execute |
| `running` | Currently executing |
| `completed` | Finished successfully |
| `failed` | Finished with errors |
| `canceled` | Manually stopped |

## Operations

### List Jobs

```bash
curl -X GET "https://api.integrator.io/v1/jobs" \
  -H "Authorization: Bearer $API_KEY"
```

**Query Parameters:**

```
# Filter by resource
?integration_id=abc123       # Jobs for integration
?flow_id=flow123             # Jobs for flow
?export_id=exp123            # Jobs for export
?flow_job_id=job123          # Child jobs of flow

# Filter by status
?status=running              # Only running jobs
?status=completed            # Only completed jobs
?status=failed               # Only failed jobs

# Filter by type
?type=flow                   # Only flow jobs
?type=export                 # Only export jobs
?type=import                 # Only import jobs

# Filter by date
?createdAt_gte=2024-01-01T00:00:00.000Z    # Created after
?createdAt_lte=2024-01-31T23:59:59.999Z    # Created before

# Filter by record counts
?numSuccess_gte=100          # At least 100 successes
?numSuccess_lte=10           # At most 10 successes
?numIgnore_gte=1             # Has ignored records

# Multiple flows
?flow_id_in=flow1,flow2,flow3
```

**Pagination:**
- Returns max 1001 jobs per request
- Results ordered by `createdAt` descending
- Use `createdAt_lte` with last job's timestamp for next page

### Pagination Example

```python
def get_all_jobs(flow_id, since_date):
    all_jobs = []
    created_at_lte = None

    while True:
        params = f"flow_id={flow_id}&createdAt_gte={since_date}"
        if created_at_lte:
            params += f"&createdAt_lte={created_at_lte}"

        response = api_get(f"/jobs?{params}")
        jobs = response.json()

        if not jobs:
            break

        all_jobs.extend(jobs)

        # Get timestamp for next page (subtract 1ms)
        last_created = jobs[-1]['createdAt']
        created_at_lte = subtract_ms(last_created)

        if len(jobs) < 1001:
            break

    return all_jobs
```

### Get Single Job

```bash
curl -X GET "https://api.integrator.io/v1/jobs/{job_id}" \
  -H "Authorization: Bearer $API_KEY"
```

### Cancel Job

**Note:** Only flow jobs can be canceled. Export/import jobs cannot be canceled directly.

```bash
curl -X DELETE "https://api.integrator.io/v1/jobs/{job_id}" \
  -H "Authorization: Bearer $API_KEY"
```

**Response (canceled job):**
```json
{
  "_id": "job123",
  "type": "flow",
  "status": "canceled",
  "canceledBy": "user@example.com",
  "endedAt": "2024-01-15T10:10:00.000Z"
}
```

## Common Queries

### Get Running Jobs

```bash
curl -X GET "https://api.integrator.io/v1/jobs?status=running" \
  -H "Authorization: Bearer $API_KEY"
```

### Get Failed Jobs (Last 24 Hours)

```bash
curl -X GET "https://api.integrator.io/v1/jobs?status=failed&createdAt_gte=2024-01-14T00:00:00.000Z" \
  -H "Authorization: Bearer $API_KEY"
```

### Get Jobs with Errors

```bash
curl -X GET "https://api.integrator.io/v1/jobs?type=flow&numError_gte=1" \
  -H "Authorization: Bearer $API_KEY"
```

### Get Child Jobs of Flow Execution

```bash
curl -X GET "https://api.integrator.io/v1/jobs?flow_job_id={flow_job_id}" \
  -H "Authorization: Bearer $API_KEY"
```

### Get Jobs for Date Range

```bash
curl -X GET "https://api.integrator.io/v1/jobs?createdAt_gte=2024-01-01T00:00:00.000Z&createdAt_lte=2024-01-31T23:59:59.999Z" \
  -H "Authorization: Bearer $API_KEY"
```

## Job Metrics

### Calculate Success Rate

```python
def calculate_success_rate(job):
    total = job['numSuccess'] + job['numError'] + job['numIgnore']
    if total == 0:
        return 100.0
    return (job['numSuccess'] / total) * 100
```

### Calculate Duration

```python
from datetime import datetime

def calculate_duration_seconds(job):
    if not job.get('startedAt') or not job.get('endedAt'):
        return None
    start = datetime.fromisoformat(job['startedAt'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(job['endedAt'].replace('Z', '+00:00'))
    return (end - start).total_seconds()
```

## Job Relationships

```
Flow Job
├── Export Jobs (one per pageGenerator)
│   └── Export error records
└── Import Jobs (one per pageProcessor)
    └── Import error records
```

### Get Complete Job Tree

```python
def get_job_tree(flow_job_id):
    # Get flow job
    flow_job = api_get(f"/jobs/{flow_job_id}").json()

    # Get child jobs
    children = api_get(f"/jobs?flow_job_id={flow_job_id}").json()

    export_jobs = [j for j in children if j['type'] == 'export']
    import_jobs = [j for j in children if j['type'] == 'import']

    return {
        "flow": flow_job,
        "exports": export_jobs,
        "imports": import_jobs
    }
```

## Error Handling

### Job Not Found
```json
{
  "errors": [{
    "code": "not_found",
    "message": "Job not found"
  }]
}
```

### Cannot Cancel
```json
{
  "errors": [{
    "code": "invalid_operation",
    "message": "Only flow jobs can be canceled"
  }]
}
```

### Job Already Complete
```json
{
  "errors": [{
    "code": "conflict",
    "message": "Cannot cancel completed job"
  }]
}
```

## Data Retention

- Job data is retained for 30 days by default
- `purgeAt` field indicates when data will be deleted
- Error records follow same retention policy
- Historical metrics may be available via reporting API
