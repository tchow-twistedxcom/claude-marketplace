# Installation Guide

Complete installation instructions for the tchow-essentials marketplace.

## Prerequisites

### Required
- **Claude Code** v2.0.13 or later
- **Node.js** 18+ (for MCP servers)
- **Git** (for cloning repositories)

### Optional (depending on plugins)
- **Chrome Browser** (for Chrome DevTools MCP)
- **NetSuite SDF CLI** (for NetSuite workflows)
- **Python 3.10+** (for Celigo, Atlassian, Plytix, NinjaOne, M365, Amazon SP-API, Mimecast integrations)

## Installation Methods

### Method 1: Install from GitHub (Recommended)

Once you push this repository to GitHub:

```bash
# Add marketplace
/plugin marketplace add tchow-twistedxcom/claude-marketplace

# Install all plugins
/plugin install superclaude-framework chrome-devtools netsuite-skills celigo-integration claudekit-skills shopify-workflows atlassian-skills plytix-skills ninjaone-skills m365-skills amazon-spapi mimecast-skills

# Or install selectively
/plugin install superclaude-framework
/plugin install celigo-integration
/plugin install claudekit-skills
```

### Method 2: Install from Local Directory

During development or testing:

```bash
# Add local marketplace
/plugin marketplace add file:///home/tchow/claude-marketplace

# Install plugins
/plugin install superclaude-framework
```

## Plugin-Specific Setup

### SuperClaude Framework

**No additional setup required** - Framework files and MCPs are automatically configured.

**Verify Installation:**
```bash
# Check if commands are available
/sc:load

# Verify MCPs are loaded (should see 6 MCP servers)
# Check Claude Code settings or run diagnostic
```

**API Keys Required:**
Some MCP servers need API keys:

1. **Magic MCP**: Requires `TWENTYFIRST_API_KEY`
   ```bash
   # Add to environment
   export TWENTYFIRST_API_KEY=your_key_here
   ```

2. **Morphllm MCP**: Requires `MORPH_API_KEY`
   ```bash
   export MORPH_API_KEY=your_key_here
   ```

### Chrome DevTools

**Setup:**

1. **Start Chrome in DevTools mode:**
   ```bash
   google-chrome --remote-debugging-port=37443
   ```

   Or on macOS:
   ```bash
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=37443
   ```

2. **Verify connection:**
   - Navigate to `http://localhost:37443`
   - Should see DevTools interface

3. **Install MCP server:**
   ```bash
   # MCP server is auto-installed via npx
   # No manual installation needed
   ```

**Verify Installation:**
```bash
/browser-test
# Should connect to Chrome DevTools
```

### NetSuite Workflows

**Setup:**

1. **Install NetSuite SDF CLI:**
   ```bash
   npm install -g @oracle/suitecloud-cli
   ```

2. **Configure NetSuite account:**
   ```bash
   suitecloud account:setup
   ```
   - Enter Account ID
   - Provide Authentication Token
   - Configure Role

3. **Verify deployment script:**
   ```bash
   # Check script exists
   ls -la /home/tchow/NetSuiteBundlet/SDF/twx-sdf-deploy.sh

   # Make executable if needed
   chmod +x /home/tchow/NetSuiteBundlet/SDF/twx-sdf-deploy.sh
   ```

**Verify Installation:**
```bash
/netsuite-setup
# Should guide through configuration
```

### Personal Automation

**No setup required** - Template is ready for your custom content.

To add custom content:
1. Create files in `plugins/personal-automation/commands/`, `agents/`, or `skills/`
2. Update `plugin.json` to reference new files
3. Reload plugin: `/plugin reload personal-automation`

### Celigo Integration

**Setup:**

1. **Get API credentials from Celigo:**
   - Log in to Celigo integrator.io
   - Go to Settings > API Tokens
   - Create a new token with appropriate permissions

2. **Configure via command:**
   ```bash
   /celigo-setup
   ```
   - Enter API key and region

**Verify Installation:**
```bash
/celigo-manage
List all integrations
```

### Enterprise Integrations (Atlassian, Shopify, Plytix, NinjaOne, M365)

**Common Setup Pattern:**

Each integration requires API credentials stored in its config directory:

1. **Atlassian Skills:**
   - OAuth app credentials from Atlassian Developer Console
   - Config: `plugins/atlassian-skills/skills/atlassian-api/config/`

2. **Shopify Workflows:**
   - Shopify Admin API credentials
   - Config: Use environment variables or skill config

3. **Plytix Skills:**
   - API key from Plytix account settings
   - Supports production/staging environments

4. **NinjaOne Skills:**
   - OAuth 2.0 credentials from NinjaOne
   - Config: `plugins/ninjaone-skills/skills/ninjaone-api/config/`

5. **M365 Skills:**
   - Azure AD app registration with Graph API permissions
   - MSAL authentication

### Amazon SP-API

**Setup:**

1. **Register as Amazon Developer:**
   - Create seller/vendor account
   - Register application in Seller Central

2. **Get LWA credentials:**
   - Client ID
   - Client Secret
   - Refresh Token

3. **Configure:**
   - Set environment variables or config file
   - Specify marketplace region (NA, EU, FE)

### Mimecast Skills

**Setup:**

1. **Get Mimecast API credentials:**
   - Access Key
   - Secret Key
   - Application ID/Key

2. **Configure:**
   - Set region (us, eu, de, au, za)
   - Store credentials securely

## Verifying Installation

### Check Installed Plugins
```bash
/plugin list
```

Expected output (all plugins):
```
✓ superclaude-framework (1.0.0)
✓ chrome-devtools (1.0.0)
✓ netsuite-skills (1.3.0)
✓ celigo-integration (2.0.0)
✓ claudekit-skills (1.2.0)
✓ shopify-workflows (1.0.0)
✓ atlassian-skills (1.1.0)
✓ plytix-skills (1.0.0)
✓ ninjaone-skills (1.0.0)
✓ m365-skills (1.0.0)
✓ amazon-spapi (1.0.0)
✓ mimecast-skills (1.0.0)
```

### Check Available Commands
```bash
# SuperClaude commands
/sc:load
/sc:save
/sc:analyze
/sc:implement
/sc:test

# Chrome DevTools commands
/browser-test

# NetSuite commands
/deploy-netsuite
/netsuite-setup

# Celigo commands
/celigo-setup
/celigo-manage

# ClaudeKit Git commands
/git/cp
/git/cm
/git/pr
/skill/create
```

### Check MCP Servers

In Claude Code settings, verify these MCPs are loaded:
- ✓ context7
- ✓ sequential
- ✓ magic
- ✓ playwright
- ✓ serena
- ✓ morphllm
- ✓ chrome-devtools

## Troubleshooting

### Plugin Not Found
```
Error: Plugin 'superclaude-framework' not found
```

**Solution:**
- Verify marketplace was added correctly
- Check plugin name spelling
- Try refreshing: `/plugin marketplace refresh`

### MCP Server Failed to Start
```
Error: MCP server 'context7' failed to start
```

**Solution:**
- Check Node.js version: `node --version` (should be 18+)
- Check npm global packages: `npm list -g`
- Manually test MCP: `npx @upstash/context7-mcp@latest`
- Check logs in Claude Code settings

### Chrome DevTools Connection Failed
```
Error: Could not connect to Chrome DevTools at localhost:37443
```

**Solution:**
- Start Chrome with remote debugging:
  ```bash
  google-chrome --remote-debugging-port=37443
  ```
- Verify port is accessible: `curl http://localhost:37443`
- Check firewall settings

### NetSuite Deployment Failed
```
Error: Authentication failed
```

**Solution:**
- Run `suitecloud account:setup` again
- Verify Account ID and Token
- Check Role permissions in NetSuite
- Test connection: `suitecloud account:ci`

### API Key Errors
```
Error: TWENTYFIRST_API_KEY not found
```

**Solution:**
- Set environment variable:
  ```bash
  export TWENTYFIRST_API_KEY=your_key_here
  ```
- Add to shell profile (~/.bashrc or ~/.zshrc) for persistence
- Restart Claude Code

## Updating

### Update All Plugins
```bash
/plugin update
```

### Update Specific Plugin
```bash
/plugin update superclaude-framework
```

### Update Marketplace
```bash
/plugin marketplace refresh tchow-essentials
```

## Uninstalling

### Remove Plugin
```bash
/plugin uninstall superclaude-framework
```

### Remove Marketplace
```bash
/plugin marketplace remove tchow-essentials
```

## Next Steps

Once installed, see:
- [Usage Guide](./USAGE.md) - How to use each plugin
- [Customization Guide](./CUSTOMIZATION.md) - Extending plugins
- [Main README](../README.md) - Overview and examples

## Getting Help

- **Issues**: https://github.com/tchow-twistedxcom/claude-marketplace/issues
- **Claude Code Docs**: https://docs.claude.com/en/docs/claude-code
- **Community**: Claude Code Discord/Forum
