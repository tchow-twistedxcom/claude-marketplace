# MongoDB Atlas Skills

MongoDB Atlas API integration for Claude Code - monitor alerts, clusters, and performance metrics.

## Skills Included

### atlas-api
Query MongoDB Atlas Admin API v2 for:
- **Alerts** - List, view, and acknowledge alerts
- **Clusters** - Check cluster status and configuration
- **Metrics** - Monitor CPU, memory, disk, and performance
- **Projects** - List accessible projects

## Setup

### 1. Environment Variables
```bash
export ATLAS_PUBLIC_KEY="your_public_key"
export ATLAS_PRIVATE_KEY="your_private_key"
export ATLAS_PROJECT_ID="your_project_id"
```

### 2. IP Whitelist
Ensure your IP is added to the Atlas API access list.

## Quick Start

```bash
# List all alerts
python3 scripts/atlas_api.py alerts list

# Check cluster status
python3 scripts/atlas_api.py clusters list

# Get performance metrics
python3 scripts/atlas_api.py metrics --cluster MyCluster
```

## Authentication

Uses HTTP Digest Authentication with Atlas API keys.

## Documentation

- [Atlas Admin API v2](https://www.mongodb.com/docs/atlas/api/atlas-admin-api-ref/)
- [API Authentication](https://www.mongodb.com/docs/atlas/api/api-authentication/)
