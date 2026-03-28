# Airbyte DB Operations

Direct PostgreSQL access via `airbyte-db-0` pod. Use when the API is unavailable, for ground-truth status, or for bulk operations.

## DB Command Wrapper

```bash
db_query() {
  docker exec airbyte-abctl-control-plane kubectl exec -n airbyte-abctl airbyte-db-0 -- \
    psql -U airbyte -d db-airbyte -t -c "$1"
}

# Or via SSH:
ssh 100.117.161.21 "docker exec airbyte-abctl-control-plane kubectl exec -n airbyte-abctl airbyte-db-0 -- \
  psql -U airbyte -d db-airbyte -t -c \"$SQL\""
```

## Key Tables

| Table | Purpose |
|-------|---------|
| `jobs` | Top-level sync/reset job records |
| `attempts` | Attempt records (1 job can have multiple attempts) |
| `workload` | Fine-grained workload tracking; most accurate status |
| `actor` | Sources and destinations |
| `actor_definition` | Connector types |
| `actor_definition_version` | Connector images (docker_image_tag) |
| `connection` | Connection configs |
| `stream_reset` | Tracks which streams need full reset |

## Common Queries

### Get latest job for a connection
```sql
SELECT id, status, created_at, updated_at
FROM jobs
WHERE scope='<conn_id>'
ORDER BY id DESC LIMIT 5;
```

### Check workload status (ground truth)
```sql
-- workload ID format: {conn_id}_{job_id}_{attempt_number}_sync
SELECT id, status, updated_at
FROM workload
WHERE id='<conn_id>_<job_id>_0_sync';
```

### Get attempt output (stream counts, errors)
```sql
SELECT status, output::text, created_at, ended_at
FROM attempts
WHERE job_id=<job_id>
ORDER BY attempt_number;
```

### Check stream count from last attempt
```sql
SELECT output::json->'standardSyncSummary'->'totalStats'->'streamCount' as stream_count
FROM attempts
WHERE job_id=<job_id>
ORDER BY attempt_number DESC LIMIT 1;
```

### Check what image tag is in use
```sql
SELECT id, docker_image_tag, docker_repository
FROM actor_definition_version
WHERE id IN (
  'cde0f46c-a3ab-4662-ae1f-7938c69059cb',  -- VC
  '0f0aa1a3-ccf4-4927-8fde-2c87ec572b2d'   -- SC
);
```

### Update connector image tag
```sql
UPDATE actor_definition_version
SET docker_image_tag='5.6.0-vc-fix5'
WHERE id IN ('cde0f46c-a3ab-4662-ae1f-7938c69059cb','0f0aa1a3-ccf4-4927-8fde-2c87ec572b2d');
```

### Cancel running job (emergency — prefer API)
```sql
UPDATE jobs SET status='cancelled', updated_at=NOW()
WHERE id=<job_id> AND status='running';

UPDATE attempts SET status='failed', updated_at=NOW(), ended_at=NOW()
WHERE job_id=<job_id> AND status='running';

UPDATE workload SET status='cancelled', updated_at=NOW()
WHERE id='<conn_id>_<job_id>_0_sync' AND status IN ('running','launched');
```

### Check resource requirements on actor definitions
```sql
SELECT id, name, resource_requirements
FROM actor_definition
WHERE name ILIKE '%amazon%';
-- NULL means: uses ConfigMap JOB_MAIN_CONTAINER_MEMORY_LIMIT (not per-source config)
```

### Check connection config
```sql
SELECT id, name, status, source_id, destination_id, catalog
FROM connection
WHERE id='<conn_id>';
```

## DB Status vs API Status

**IMPORTANT**: `jobs.status` is NOT always reliable. When a pod is killed mid-sync:
- `jobs.status` may show `succeeded` (set first by server)
- `workload.status` will show `failure` (set later by workload monitor)
- `attempts.output` will have `streamCount: 0` and `workload-monitor-heartbeat` error

**Ground truth order**: `workload.status` > `attempts.output` > `jobs.status`

Detect false successes:
```sql
SELECT j.id, j.status as job_status, w.status as workload_status,
       a.output::json->'standardSyncSummary'->'totalStats'->'streamCount' as streams
FROM jobs j
LEFT JOIN workload w ON w.id = j.scope || '_' || j.id || '_0_sync'
LEFT JOIN attempts a ON a.job_id = j.id
WHERE j.scope = '<conn_id>'
ORDER BY j.id DESC LIMIT 3;
```
