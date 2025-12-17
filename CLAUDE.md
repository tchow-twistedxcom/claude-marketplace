# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **tchow-essentials**, a personal Claude Code plugin marketplace containing curated plugins for:
- SuperClaude behavioral framework
- Browser automation (Chrome DevTools)
- Enterprise integrations (NetSuite, Celigo, Shopify, Atlassian)
- ClaudeKit community skills collection

## Repository Structure

```
tchow-essentials/
├── .claude-plugin/
│   └── marketplace.json     # Marketplace registry (plugin list, versions, sources)
├── plugins/
│   ├── superclaude-framework/   # Core behavioral framework + 6 MCP servers
│   ├── chrome-devtools/         # Browser automation MCP
│   ├── celigo-integration/      # iPaaS integration (63 MCP tools)
│   ├── claudekit-skills/        # 20+ community skills
│   ├── netsuite-skills/         # SDF deployment, SuiteQL, PRI skills
│   ├── shopify-workflows/       # Shopify Admin API workflows
│   ├── atlassian-skills/        # Confluence/Jira operations
│   └── personal-automation/     # User customization template
└── docs/
    ├── INSTALLATION.md
    ├── USAGE.md
    └── CUSTOMIZATION.md
```

## Plugin Architecture

### Plugin Components

Each plugin follows this structure:
```
plugin-name/
├── plugin.json              # Required: commands, skills, mcpServers, globalInstructions
├── commands/                # Slash commands (*.md files)
├── skills/                  # Skills (subdirs with SKILL.md)
├── mcp-configs/             # MCP server configurations (*.json)
└── .claude/ or globalInstructions  # Framework docs (injected into context)
```

### Key Configuration Files

- **`plugin.json`**: Plugin manifest with arrays for `commands`, `skills`, `mcpServers`, `globalInstructions`
- **`.claude-plugin/marketplace.json`**: Top-level registry listing all plugins with `source`, `version`, `description`
- **`SKILL.md`**: Skill definition with YAML frontmatter (`name`, `description` for activation triggers)
- **Command `.md`**: Slash command definition with YAML frontmatter (`name`, `description`)

### Plugin Registration Pattern

To add a plugin to the marketplace:

1. Create plugin directory in `plugins/`
2. Add `plugin.json` with required fields
3. Register in `.claude-plugin/marketplace.json`:
```json
{
  "name": "plugin-name",
  "source": "./plugins/plugin-name",
  "description": "Plugin description",
  "version": "1.0.0"
}
```

## Development Commands

```bash
# Marketplace operations
/plugin marketplace refresh            # Reload marketplace after changes
/plugin list                           # Show installed plugins
/plugin install <plugin-name>          # Install a plugin
/plugin uninstall <plugin-name>        # Remove a plugin
/plugin reload <plugin-name>           # Reload after editing

# Testing plugin changes
# 1. Edit files in plugins/<name>/
# 2. /plugin reload <name>
# 3. Test commands/skills
```

## Key Plugins Reference

### SuperClaude Framework (`superclaude-framework`)
- **21 slash commands**: `/sc:load`, `/sc:save`, `/sc:analyze`, `/sc:implement`, etc.
- **5 behavioral modes**: Brainstorming, Introspection, Orchestration, Task Management, Token Efficiency
- **6 bundled MCPs**: Context7, Sequential, Magic, Playwright, Serena, Morphllm
- **Global instructions**: FLAGS.md, PRINCIPLES.md, RULES.md, MODE_*.md, MCP_*.md

### Celigo Integration (`celigo-integration`)
- **63 MCP tools** for integrations, flows, connections, jobs, errors, lookup caches, tags
- **Python FastMCP server** for API access
- Commands: `/celigo-setup`, `/celigo-manage`

### ClaudeKit Skills (`claudekit-skills`)
- **19 skill directories** covering: nextjs, tailwindcss, shadcn-ui, ffmpeg, imagemagick, mcp-builder, debugging, etc.
- Commands: `/git/cp`, `/git/cm`, `/git/pr`, `/skill/create`
- Source: https://github.com/mrgoonie/claudekit-skills

### NetSuite Skills (`netsuite-skills`)
- Skills: `pri-container-tracking`, `netsuite-sdf-deployment`, `netsuite-suiteql`
- SDF deployment automation with credential management
- SuiteQL query execution via API Gateway

## Version Management

Plugin versions tracked in two places:
1. Individual `plugin.json` files (e.g., `"version": "1.3.0"`)
2. `.claude-plugin/marketplace.json` registry

When updating a plugin:
1. Update functionality in plugin directory
2. Bump version in `plugin.json`
3. Update version in `marketplace.json` to match
4. Commit with conventional commit message

## Testing Plugins Locally

```bash
# For local development without GitHub push:
/plugin marketplace add file:///home/tchow/.claude/plugins/marketplaces/tchow-essentials

# After making changes:
/plugin marketplace refresh
/plugin reload <plugin-name>
```

## Common Modifications

### Adding a New Command
1. Create `plugins/<name>/commands/my-command.md`
2. Add YAML frontmatter: `name`, `description`
3. Add to `plugin.json` commands array
4. `/plugin reload <name>`

### Adding a New Skill
1. Create `plugins/<name>/skills/my-skill/SKILL.md`
2. Add YAML frontmatter with `description` (activation triggers)
3. Add skill path to `plugin.json` skills array
4. `/plugin reload <name>`

### Adding MCP Server
1. Create config in `plugins/<name>/mcp-configs/my-mcp.json`
2. Add to `plugin.json` mcpServers (can be path or `.mcp.json` reference)
3. `/plugin reload <name>`
