---
name: celigo-setup
description: Set up Celigo CLI configuration and API authentication
---

# Celigo CLI Setup

Configure the Celigo Python CLI for integration platform access.

## Prerequisites

- **Python 3.8+** installed
- **requests** library (`pip install requests`)
- **tabulate** library (`pip install tabulate`) - for table output
- **Celigo account** with API access
- **Celigo API token** (from Celigo dashboard)

## Quick Setup

### 1. Get Your Celigo API Token

1. Log in to your Celigo dashboard at https://integrator.io
2. Navigate to **Settings → API Tokens**
3. Click **Generate New Token**
4. Copy the token (you won't see it again)
5. Store it securely

### 2. Create Configuration File

Create the config file at `plugins/celigo-integration/config/celigo_config.json`:

```bash
# Navigate to config directory
cd plugins/celigo-integration/config

# Copy template
cp celigo_config.template.json celigo_config.json

# Edit with your API key
```

Configuration file format:

```json
{
  "environments": {
    "production": {
      "api_key": "YOUR_PRODUCTION_API_KEY",
      "base_url": "https://api.integrator.io/v1"
    },
    "sandbox": {
      "api_key": "YOUR_SANDBOX_API_KEY",
      "base_url": "https://api.integrator.io/v1"
    }
  },
  "default_environment": "production"
}
```

### 3. Install Dependencies

```bash
pip install requests tabulate
```

### 4. Verify Installation

```bash
# Test the CLI
cd plugins/celigo-integration
python3 scripts/celigo_api.py integrations list

# Should display your integrations in table format
```

## CLI Usage

### Basic Commands

```bash
# List all integrations
python3 scripts/celigo_api.py integrations list

# Get specific integration
python3 scripts/celigo_api.py integrations get <integration_id>

# Check for failed jobs
python3 scripts/celigo_api.py jobs list --status failed

# Run a flow
python3 scripts/celigo_api.py flows run <flow_id>
```

### Output Formats

```bash
# Human-readable table (default)
python3 scripts/celigo_api.py integrations list

# JSON for scripting
python3 scripts/celigo_api.py integrations list --format json

# Pipe to jq for processing
python3 scripts/celigo_api.py flows get <id> --format json | jq '.name'
```

### Environment Selection

```bash
# Use production (default)
python3 scripts/celigo_api.py integrations list

# Use sandbox
python3 scripts/celigo_api.py integrations list --env sandbox
```

## Available Operations (63 Total)

| Resource | Operations |
|----------|------------|
| integrations | list, get, flows, connections, exports, imports, users, template, dependencies, audit, errors |
| flows | list, get, run, template, dependencies, descendants, jobs-latest, last-export-datetime, audit |
| connections | list, get, test, debug-log, logs, dependencies |
| exports | list, get, audit, dependencies |
| imports | list, get, audit, dependencies |
| jobs | list, get, cancel |
| errors | list, resolved, retry-data, resolve, retry, assign, tags, integration-summary, integration-assign |
| caches | list, get, data |
| tags | list, get, create, update, delete |
| users | list, get |

## Security Best Practices

1. **Never Commit Config**: Add `config/celigo_config.json` to `.gitignore`
2. **Use Template**: Keep `celigo_config.template.json` without real keys
3. **Rotate Tokens Regularly**: Generate new tokens periodically
4. **Limit Token Scope**: Use role-based permissions in Celigo
5. **Monitor API Usage**: Track token usage in Celigo dashboard

## Troubleshooting

### Authentication Failed
```
Error: 401 Unauthorized
```

**Solution:**
- Verify API key in `config/celigo_config.json`
- Check token hasn't expired
- Regenerate token in Celigo dashboard

### Config File Not Found
```
Error: Config file not found
```

**Solution:**
```bash
# Create config from template
cp config/celigo_config.template.json config/celigo_config.json

# Edit with your API key
```

### Missing Dependencies
```
ModuleNotFoundError: No module named 'requests'
```

**Solution:**
```bash
pip install requests tabulate
```

### Connection Timeout
```
Error: Request timeout
```

**Solution:**
- Check network connectivity
- Verify Celigo API status at https://status.celigo.com
- Try again in a few moments

## Usage Examples

**User:** "Set up Celigo integration"
**Action:** Guide through config file creation and API key setup

**User:** "List my Celigo integrations"
**Action:** Execute `python3 scripts/celigo_api.py integrations list`

**User:** "Check for failed jobs"
**Action:** Execute `python3 scripts/celigo_api.py jobs list --status failed`
