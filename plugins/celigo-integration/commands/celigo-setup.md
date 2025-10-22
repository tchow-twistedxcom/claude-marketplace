---
name: celigo-setup
description: Set up Celigo MCP server configuration and API authentication
---

# Celigo MCP Setup

Configure the Celigo MCP server for integration platform access.

## Prerequisites

- **Python 3.10+** installed
- **UV package manager** (will be installed via uvx if needed)
- **Celigo account** with API access
- **Celigo API token** (from Celigo dashboard)

## Configuration Steps

### 1. Get Your Celigo API Token

1. Log in to your Celigo dashboard
2. Navigate to **Settings → API Tokens**
3. Click **Generate New Token**
4. Copy the token (you won't see it again)
5. Store it securely

### 2. Configure Environment

Set the required environment variable:

```bash
# Add to your shell profile (~/.bashrc or ~/.zshrc)
export CELIGO_API_TOKEN=your_token_here

# Or for temporary use
CELIGO_API_TOKEN=your_token_here
```

### 3. Optional Configuration

Additional environment variables:

```bash
# Custom API base URL (default: https://api.integrator.io/v1)
export CELIGO_API_BASE_URL=https://api.integrator.io/v1

# Request timeout in seconds (default: 30)
export CELIGO_TIMEOUT=60

# Logging level (default: INFO)
export LOG_LEVEL=DEBUG
```

### 4. Verify Installation

Test the MCP server:

```bash
# The MCP server will be auto-installed via uvx when first used
# No manual installation needed
```

## Available Tools (63 Total)

### Integrations (13 tools)
- List, get, create, update, delete integrations
- Clone integrations
- Manage integration versions
- Import/export integrations

### Connections (6 tools)
- List, get, create, update, delete connections
- Test connection health

### Flows (9 tools)
- List, get, create, update, delete flows
- Clone flows
- Manage flow versions
- Trigger flow runs

### Exports & Imports (8 tools)
- Manage data exports and imports
- Monitor export/import jobs
- Configure schedules

### Jobs & Errors (17 tools)
- List and monitor jobs
- Retry failed jobs
- Error tracking and debugging
- Clear error logs

### Lookup Caches (3 tools)
- Manage lookup caches
- Clear cache data

### Tags (7 tools)
- Tag management
- Organize integrations with tags

### Users (2 tools)
- List and manage users

## Security Best Practices

1. **Never Commit Tokens**: Add `.env` to `.gitignore`
2. **Use Environment Variables**: Don't hardcode tokens in code
3. **Rotate Tokens Regularly**: Generate new tokens periodically
4. **Limit Token Scope**: Use role-based permissions in Celigo
5. **Monitor API Usage**: Track token usage in Celigo dashboard

## Troubleshooting

### Authentication Failed
```
Error: 401 Unauthorized
```

**Solution:**
- Verify `CELIGO_API_TOKEN` is set correctly
- Check token hasn't expired
- Regenerate token in Celigo dashboard

### UV/Python Not Found
```
Error: uvx: command not found
```

**Solution:**
```bash
# Install UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or use pip
pip install uv
```

### Connection Timeout
```
Error: Request timeout after 30s
```

**Solution:**
- Increase timeout: `export CELIGO_TIMEOUT=60`
- Check network connectivity
- Verify Celigo API status

## Usage Examples

**User:** "Set up Celigo integration"
**Action:** Guide through token generation and environment configuration

**User:** "List my Celigo integrations"
**Action:** Use MCP tools to fetch and display integrations

**User:** "Create a new connection to Salesforce"
**Action:** Use connection creation tool with guided parameters
