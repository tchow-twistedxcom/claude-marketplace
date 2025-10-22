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
- **Python 3.8+** (for certain MCP servers)

## Installation Methods

### Method 1: Install from GitHub (Recommended)

Once you push this repository to GitHub:

```bash
# Add marketplace
/plugin marketplace add tchow-twistedxcom/claude-marketplace

# Install all your custom plugins
/plugin install superclaude-framework chrome-devtools netsuite-workflows

# Or install selectively
/plugin install superclaude-framework
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

## Verifying Installation

### Check Installed Plugins
```bash
/plugin list
```

Expected output:
```
✓ superclaude-framework (1.0.0)
✓ chrome-devtools (1.0.0)
✓ netsuite-workflows (1.0.0)
✓ personal-automation (1.0.0)
```

### Check Available Commands
```bash
# SuperClaude commands
/sc:load
/sc:save
/sc:analyze

# Chrome DevTools commands
/browser-test

# NetSuite commands
/deploy-netsuite
/netsuite-setup
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
