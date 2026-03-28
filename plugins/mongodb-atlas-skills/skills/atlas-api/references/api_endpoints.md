# MongoDB Atlas Admin API v2 - Endpoint Reference

## Base URL
```
https://cloud.mongodb.com/api/atlas/v2
```

## Authentication
HTTP Digest Authentication using Atlas API key pair (public key as username, private key as password).

Required header:
```
Accept: application/vnd.atlas.2024-08-05+json
```

## Alerts

### List Alerts
```
GET /groups/{groupId}/alerts
```
Query parameters:
- `status` - OPEN, CLOSED
- `itemsPerPage` - Number of items per page (default: 100, max: 500)
- `pageNum` - Page number (default: 1)

### Get Alert
```
GET /groups/{groupId}/alerts/{alertId}
```

### Acknowledge Alert
```
PATCH /groups/{groupId}/alerts/{alertId}
```
Body:
```json
{
  "acknowledgedUntil": "2099-12-31T23:59:59Z",
  "acknowledgementComment": "Optional comment"
}
```

### Unacknowledge Alert
```
PATCH /groups/{groupId}/alerts/{alertId}
```
Body:
```json
{
  "acknowledgedUntil": null
}
```

## Clusters

### List Clusters
```
GET /groups/{groupId}/clusters
```

### Get Cluster
```
GET /groups/{groupId}/clusters/{clusterName}
```

### Get Advanced Configuration
```
GET /groups/{groupId}/clusters/{clusterName}/processArgs
```

## Processes & Metrics

### List Processes
```
GET /groups/{groupId}/processes
```

### Get Process Measurements
```
GET /groups/{groupId}/processes/{processId}/measurements
```
Query parameters:
- `granularity` - PT1M, PT5M, PT1H, P1D
- `period` - PT1H, PT24H, P7D, P30D
- `m` - Metric name (can specify multiple)

### Common Metrics
- `SYSTEM_CPU_USER` - CPU usage (%)
- `SYSTEM_MEMORY_USED` - Memory used (bytes)
- `CONNECTIONS` - Active connections
- `OPCOUNTER_CMD` - Commands/sec
- `OPCOUNTER_QUERY` - Queries/sec
- `OPCOUNTER_INSERT` - Inserts/sec
- `OPCOUNTER_UPDATE` - Updates/sec
- `OPCOUNTER_DELETE` - Deletes/sec
- `DISK_PARTITION_IOPS_READ` - Disk reads/sec
- `DISK_PARTITION_IOPS_WRITE` - Disk writes/sec

## Projects

### List Projects
```
GET /groups
```

### Get Project
```
GET /groups/{groupId}
```

## Alert Types Reference

| Event Type | Description |
|------------|-------------|
| HOST_DOWN | Host is down |
| HOST_RECOVERING | Host is recovering |
| HOST_MONGOS_IS_MISSING | Mongos is missing |
| REPLICATION_OPLOG_WINDOW_RUNNING_OUT | Oplog window is running out |
| CLUSTER_MONGOS_IS_MISSING | Cluster mongos is missing |
| HOST_HAS_INDEX_SUGGESTIONS | Index suggestions available |
| JOINED_GROUP | User joined project |
| OUTSIDE_METRIC_THRESHOLD | Metric outside threshold |
| PRIMARY_ELECTED | New primary elected |
| USER_ROLES_CHANGED_AUDIT | User roles changed |
| BACKUP_SNAPSHOT_DOWNLOAD_REQUEST_FAILED | Snapshot download failed |

## Error Codes

| Code | Description |
|------|-------------|
| 401 | Unauthorized - Invalid credentials |
| 403 | Forbidden - IP not in access list |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limited |
| 500 | Internal Server Error |

## Rate Limits

- 100 requests per minute per organization
- 500 requests per minute per IP address

## Resources

- [Full API Reference](https://www.mongodb.com/docs/atlas/reference/api-resources/)
- [API Authentication](https://www.mongodb.com/docs/atlas/api/api-authentication/)
- [Alert Types](https://www.mongodb.com/docs/atlas/reference/alert-types/)
