# Atlas API Skill

MongoDB Atlas Admin API v2 operations for monitoring alerts, clusters, and performance metrics.

## Quick Start

```bash
# Set environment variables
export ATLAS_PUBLIC_KEY="your_public_key"
export ATLAS_PRIVATE_KEY="your_private_key"
export ATLAS_PROJECT_ID="your_project_id"

# List alerts
python3 scripts/atlas_api.py alerts list

# Check cluster status
python3 scripts/atlas_api.py clusters status MyCluster
```

## Prerequisites

1. **Atlas API Key** - Create in Atlas Organization Settings > Access Manager > API Keys
2. **IP Whitelist** - Add your IP to the API key access list
3. **Project ID** - Found in Atlas Project Settings

## Commands

### Alerts
```bash
python3 scripts/atlas_api.py alerts list [--status open|closed]
python3 scripts/atlas_api.py alerts get ALERT_ID
python3 scripts/atlas_api.py alerts ack ALERT_ID [--comment "message"]
```

### Clusters
```bash
python3 scripts/atlas_api.py clusters list
python3 scripts/atlas_api.py clusters status CLUSTER_NAME
```

### Metrics
```bash
python3 scripts/atlas_api.py metrics --cluster CLUSTER_NAME [--period PT24H]
```

### Projects
```bash
python3 scripts/atlas_api.py projects list
```

## Output Formats

- `--format table` (default) - Human-readable table format
- `--format json` - JSON output for scripting

## Troubleshooting

| Error | Solution |
|-------|----------|
| 401 Unauthorized | Check API key credentials |
| 403 Forbidden | Add your IP to Atlas API access list |
| 404 Not Found | Verify project ID and resource names |

## Documentation

- [SKILL.md](SKILL.md) - Full skill documentation
- [references/api_endpoints.md](references/api_endpoints.md) - API endpoint reference
