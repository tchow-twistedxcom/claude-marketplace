# tchow-essentials

**Personal curated collection for Claude Code**: SuperClaude framework + Chrome DevTools + NetSuite workflows + best community plugins

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Quick Start

```bash
# Add marketplace
/plugin marketplace add tchow-twistedxcom/claude-marketplace

# Install everything
/plugin install superclaude-framework chrome-devtools netsuite-workflows celigo-integration

# Or install selectively
/plugin install superclaude-framework
/plugin install celigo-integration
/plugin install backend-development
```

## 📦 What's Included

### 🏗️ Your Custom Plugins

#### SuperClaude Framework
Complete framework with FLAGS, PRINCIPLES, RULES, 5 behavioral modes, and 6 bundled MCPs.

**Includes:**
- **20+ /sc: commands**: `/sc:load`, `/sc:save`, `/sc:analyze`, `/sc:implement`, etc.
- **5 Behavioral Modes**: Brainstorming, Introspection, Orchestration, Task Management, Token Efficiency
- **6 MCP Servers**: Context7, Sequential, Magic, Playwright, Serena, Morphllm
- **Framework Documentation**: FLAGS.md, PRINCIPLES.md, RULES.md, MODE_*.md, MCP_*.md

#### Chrome DevTools
Browser automation and E2E testing with Chrome DevTools MCP.

**Includes:**
- `/browser-test` command
- E2E testing patterns skill
- Chrome DevTools MCP configuration

#### NetSuite Workflows
NetSuite SDF deployment automation for Record Display app.

**Includes:**
- `/deploy-netsuite` command
- `/netsuite-setup` command
- SDF bundle creation skill
- NetSuite customization patterns skill

#### Celigo Integration
Celigo integration platform automation with 63 MCP tools.

**Includes:**
- `/celigo-setup` command
- `/celigo-manage` command
- Celigo integration patterns skill
- 63 MCP tools (integrations, flows, connections, jobs, errors, etc.)
- Python-based FastMCP server

#### Personal Automation
Template for your custom workflows (empty, ready for your additions).

---

### ⭐ Curated Community Plugins

#### From Anthropic
- **document-skills**: Excel, Word, PowerPoint, PDF processing
- **example-skills**: MCP builder, canvas design, algorithmic art, etc.

#### From Seth Hobson (claude-code-workflows)
- **backend-development**: API design, architecture patterns, microservices
- **frontend-mobile-development**: React, Flutter, mobile workflows
- **security-scanning**: Security auditing and SAST configuration
- **kubernetes-operations**: K8s with GitOps, Helm, manifest generation

## 📚 Documentation

- [Installation Guide](./docs/INSTALLATION.md) - Detailed setup instructions
- [Usage Guide](./docs/USAGE.md) - How to use each plugin
- [Customization Guide](./docs/CUSTOMIZATION.md) - Extending plugins

## 🔧 Plugin Details

### SuperClaude Framework

**Commands (20+):**
- `/sc:load` - Load project context
- `/sc:save` - Save session state
- `/sc:analyze` - Code analysis
- `/sc:implement` - Feature implementation
- `/sc:test` - Run tests
- `/sc:git` - Git operations
- `/sc:deploy` - Deployment workflows
- [See all commands](./plugins/superclaude-framework/README.md)

**Modes:**
- `--brainstorm` - Collaborative discovery
- `--introspect` - Meta-cognitive analysis
- `--orchestrate` - Tool optimization
- `--task-manage` - Multi-step organization
- `--token-efficient` - Compressed communication

**MCPs:**
- Context7 - Library documentation
- Sequential - Multi-step reasoning
- Magic - UI component generation
- Playwright - Browser automation
- Serena - Semantic code analysis
- Morphllm - Pattern-based edits

### Chrome DevTools

**Commands:**
- `/browser-test` - Browser automation testing

**Skills:**
- E2E testing patterns
- Visual validation workflows
- Performance testing

**MCP:**
- Chrome DevTools MCP @ http://localhost:37443

### NetSuite Workflows

**Commands:**
- `/deploy-netsuite` - Deploy SDF bundles
- `/netsuite-setup` - Configure SDF projects

**Skills:**
- SDF bundle creation patterns
- Advanced customization patterns

**Deployment Script:**
- Location: `/home/tchow/NetSuiteBundlet/SDF/twx-sdf-deploy.sh`

### Celigo Integration

**Commands:**
- `/celigo-setup` - Configure Celigo MCP server
- `/celigo-manage` - Manage integrations, flows, connections

**Skills:**
- Celigo integration patterns (bi-directional sync, hub-and-spoke, pipelines)
- ETL workflows and data transformation
- Error handling and monitoring

**MCP Tools (63):**
- Integrations (13 tools)
- Connections (6 tools)
- Flows (9 tools)
- Exports & Imports (8 tools)
- Jobs & Errors (17 tools)
- Lookup Caches (3 tools)
- Tags (7 tools)

## 🌐 Full Marketplace Access

When you install this marketplace, you also get access to:
- **anthropic-agent-skills** marketplace (14 skills)
- **claude-code-workflows** marketplace (64 plugins)

Browse all plugins:
```bash
/plugin browse
```

## 🛠️ Requirements

- Claude Code v2.0.13 or later
- Node.js 18+ (for MCP servers)
- Chrome browser (for Chrome DevTools MCP)
- NetSuite SDF CLI (for NetSuite plugins)

## 📖 Usage Examples

### Example 1: Full Setup
```bash
# Install everything
/plugin install superclaude-framework chrome-devtools netsuite-workflows

# Load project context
/sc:load

# Start coding with full framework
```

### Example 2: Backend Development
```bash
# Install framework + backend tools
/plugin install superclaude-framework backend-development

# Use backend architecture patterns
# Framework modes automatically activate
```

### Example 3: Testing Focus
```bash
# Install testing tools
/plugin install chrome-devtools superclaude-framework

# Run browser tests
/browser-test

# Use E2E patterns skill (automatically available)
```

## 🤝 Contributing

This is a personal marketplace, but suggestions are welcome!

To suggest improvements:
1. Open an issue
2. Describe the enhancement
3. Explain the use case

## 📝 License

MIT License - see [LICENSE](./LICENSE) for details

## 🔗 Links

- **Repository**: https://github.com/tchow-twistedxcom/claude-marketplace
- **Issues**: https://github.com/tchow-twistedxcom/claude-marketplace/issues
- **Claude Code**: https://claude.ai/code
- **Anthropic Skills**: https://github.com/anthropics/skills
- **Seth Hobson's Workflows**: https://github.com/wshobson/agents

## 🙏 Acknowledgments

- **Anthropic** - For Claude Code and official skills
- **Seth Hobson** - For comprehensive claude-code-workflows
- **SuperClaude Framework** - For behavioral modes and orchestration patterns

---

**Made with ❤️ by tchow**
