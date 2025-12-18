# NinjaOne Skills Plugin

NinjaOne RMM (Remote Monitoring & Management) API integration for Claude Code.

## Features

- **Device Management**: List, search, and manage endpoints
- **Organization Management**: Multi-tenant organization operations
- **Queries/Reports**: Pre-built reports for AV, patches, software, health
- **Management Actions**: Reboot, scripts, patches, services
- **Ticketing**: PSA ticketing integration
- **Alerts**: Alert management and reset
- **Policies**: Policy configuration
- **Webhooks**: Event notification setup

## Installation

```bash
# From tchow-essentials marketplace
/plugin install ninjaone-skills
```

## Setup

See [skills/ninjaone-api/README.md](skills/ninjaone-api/README.md) for OAuth2 setup instructions.

## Skills

| Skill | Description |
|-------|-------------|
| `ninjaone-api` | Full NinjaOne API client (~70 operations) |

## Quick Start

```bash
# List all devices
python scripts/ninjaone_api.py devices list

# Get device details
python scripts/ninjaone_api.py devices get 12345

# Run AV status report
python scripts/ninjaone_api.py queries antivirus-status

# List tickets
python scripts/ninjaone_api.py tickets list
```

## Requirements

- Python 3.8+
- NinjaOne account with API access
- OAuth2 client credentials (client_id, client_secret)
