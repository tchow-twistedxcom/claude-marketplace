# tchow-essentials

**Personal curated collection for Claude Code**: SuperClaude framework + Chrome DevTools + NetSuite skills + Celigo integration + ClaudeKit skills + Shopify workflows + Atlassian skills + Plytix PIM + NinjaOne RMM + Microsoft 365/Azure AD

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Quick Start

```bash
# Add marketplace
/plugin marketplace add tchow-twistedxcom/claude-marketplace

# Install everything
/plugin install superclaude-framework chrome-devtools netsuite-skills celigo-integration claudekit-skills shopify-workflows atlassian-skills plytix-skills ninjaone-skills m365-skills

# Or install selectively
/plugin install superclaude-framework
/plugin install celigo-integration
/plugin install claudekit-skills
/plugin install atlassian-skills
```

## What's Included

### Core Framework & Tools

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

---

### Enterprise Integrations

#### NetSuite Skills
NetSuite expertise for debugging, diagnosing, and deploying complex implementations.

**Includes:**
- **PRI Container Tracking**: Prolecto freight management with 23+ Application Settings
- **SDF Deployment**: Automatic credential detection, CI/CD, certificate-based auth
- **SuiteQL**: Query execution via NetSuite API Gateway
- Multi-environment deployment workflows

#### Celigo Integration
Celigo iPaaS automation with 63 MCP tools.

**Includes:**
- `/celigo-setup` command
- `/celigo-manage` command
- Celigo integration patterns skill
- 63 MCP tools (integrations, flows, connections, jobs, errors, etc.)
- Python-based FastMCP server

#### Atlassian Skills
Confluence and Jira operations via REST API.

**Includes:**
- Page creation/update/archive and search
- Attachments and markdown-to-Confluence conversion
- Mermaid diagram support
- Jira issue management, JQL queries, and transitions
- OAuth authentication

#### Shopify Workflows
Shopify Admin API automation with 5 specialized workflow skills.

**Includes:**
- 5 workflow-specific skills: content-creator, merchant-daily, marketing-ops, developer, analytics
- Shopify Dev MCP integration (GraphQL schema introspection, validation)
- Production-ready GraphQL mutations and queries
- Zero overlap between skills (clear boundaries)
- Token-efficient (60-75% reduction vs monolithic)

#### Plytix Skills
Plytix PIM operations via REST API.

**Includes:**
- Product management and digital asset handling
- Category organization and variant creation
- Attribute schema management
- Multi-account support (production/staging)

#### NinjaOne Skills
NinjaOne RMM API integration for MSP operations.

**Includes:**
- Device monitoring and management
- Ticketing and reporting
- 70+ endpoints across 9 domains
- OAuth 2.0 authentication

#### Microsoft 365 Skills
Microsoft 365 and Azure integrations via Microsoft Graph API.

**Includes:**
- Azure AD/Entra ID operations
- User, group, and device management
- Directory operations
- MSAL OAuth 2.0 authentication

---

### Community Skills

#### ClaudeKit Skills
Curated collection of 20+ specialized skills from the ClaudeKit community.

**Includes:**
- `/git/cp`, `/git/cm`, `/git/pr` commands (git commit patterns, pull requests)
- `/skill/create` command (create custom skills)
- **20 Skills**: Next.js, Tailwind CSS, shadcn-ui, Turborepo, better-auth, FFmpeg, ImageMagick, Google ADK, MCP builder, document processing, problem-solving, debugging, canvas design, Remix Icon, and more
- Community-maintained patterns and workflows

---

### Curated Community Plugins

#### From Anthropic
- **document-skills**: Excel, Word, PowerPoint, PDF processing
- **example-skills**: MCP builder, canvas design, algorithmic art, etc.

#### From Seth Hobson (claude-code-workflows)
- **backend-development**: API design, architecture patterns, microservices
- **frontend-mobile-development**: React, Flutter, mobile workflows
- **security-scanning**: Security auditing and SAST configuration
- **kubernetes-operations**: K8s with GitOps, Helm, manifest generation

## Documentation

- [Installation Guide](./docs/INSTALLATION.md) - Detailed setup instructions
- [Usage Guide](./docs/USAGE.md) - How to use each plugin
- [Customization Guide](./docs/CUSTOMIZATION.md) - Extending plugins

## Plugin Details

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

### NetSuite Skills

**Skills:**
- **PRI Container Tracking** - Prolecto freight with 23+ Application Settings
- **SDF Deployment** - Automated deployment with credential management
- **SuiteQL** - Query execution via API Gateway

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

### Atlassian Skills

**Skills:**
- **Atlassian API** - Confluence and Jira operations

**Capabilities:**
- Confluence: Pages, spaces, attachments, search, markdown conversion
- Jira: Issues, JQL queries, transitions, comments
- Mermaid diagram rendering
- OAuth authentication

### Shopify Workflows

**Skills (5):**
- **Content Creator** - Blog articles, pages, theme assets
- **Merchant Daily** - Orders, inventory, customers
- **Marketing Ops** - Discounts, campaigns, promotions
- **Developer** - Webhooks, metafields, custom apps
- **Analytics** - Sales reports, performance metrics

### Plytix Skills

**Skills:**
- **Plytix API** - PIM operations

**Capabilities:**
- Product CRUD operations
- Digital asset management
- Category and variant handling
- Attribute schema management

### NinjaOne Skills

**Skills:**
- **NinjaOne API** - RMM operations

**Capabilities:**
- Device monitoring and management
- Patch management and alerts
- Ticketing system
- Reporting and analytics
- 70+ API endpoints

### Microsoft 365 Skills

**Skills:**
- **Azure AD** - Entra ID operations

**Capabilities:**
- User management (create, update, delete, license)
- Group management (security, M365, dynamic)
- Device management
- Directory queries and reporting

### ClaudeKit Skills

**Commands:**
- `/git/cp` - Git commit with conventional patterns
- `/git/cm` - Git commit message helper
- `/git/pr` - Pull request creation
- `/skill/create` - Create custom Claude Code skills

**Skills (20):**
- **Development**: nextjs, tailwindcss, shadcn-ui, turborepo, better-auth
- **Media**: ffmpeg, imagemagick
- **AI/Agents**: google-adk-python, mcp-builder, claude-code
- **Documents**: document-skills (PDF, Excel, PowerPoint, Word)
- **Problem-Solving**: problem-solving frameworks, debugging
- **Design**: canvas-design, remix-icon (3,100+ icons)
- **Utilities**: docs-seeker, repomix, shopify, skill-creator

**Source:**
- Original repository: https://github.com/mrgoonie/claudekit-skills
- 20+ curated skills from the ClaudeKit community

## Full Marketplace Access

When you install this marketplace, you also get access to:
- **anthropic-agent-skills** marketplace (14 skills)
- **claude-code-workflows** marketplace (64 plugins)

Browse all plugins:
```bash
/plugin browse
```

## Requirements

- Claude Code v2.0.13 or later
- Node.js 18+ (for MCP servers)
- Chrome browser (for Chrome DevTools MCP)
- NetSuite SDF CLI (for NetSuite plugins)
- Python 3.10+ (for Celigo, Atlassian, Plytix, NinjaOne, M365 skills)

## Usage Examples

### Example 1: Full Setup
```bash
# Install everything
/plugin install superclaude-framework chrome-devtools netsuite-skills celigo-integration

# Load project context
/sc:load

# Start coding with full framework
```

### Example 2: Enterprise Integrations
```bash
# Install integration tools
/plugin install superclaude-framework celigo-integration atlassian-skills

# Set up Celigo
/celigo-setup

# Use Atlassian skill for documentation
```

### Example 3: E-commerce Stack
```bash
# Install Shopify + Plytix
/plugin install shopify-workflows plytix-skills

# Manage products and sync to Shopify
```

### Example 4: IT Operations
```bash
# Install RMM and M365 tools
/plugin install ninjaone-skills m365-skills

# Monitor devices and manage Azure AD
```

## Contributing

This is a personal marketplace, but suggestions are welcome!

To suggest improvements:
1. Open an issue
2. Describe the enhancement
3. Explain the use case

## License

MIT License - see [LICENSE](./LICENSE) for details

## Links

- **Repository**: https://github.com/tchow-twistedxcom/claude-marketplace
- **Issues**: https://github.com/tchow-twistedxcom/claude-marketplace/issues
- **Claude Code**: https://claude.ai/code
- **Anthropic Skills**: https://github.com/anthropics/skills
- **Seth Hobson's Workflows**: https://github.com/wshobson/agents
- **ClaudeKit Skills**: https://github.com/mrgoonie/claudekit-skills

## Acknowledgments

- **Anthropic** - For Claude Code and official skills
- **Seth Hobson** - For comprehensive claude-code-workflows
- **mrgoonie** - For ClaudeKit skills collection
- **SuperClaude Framework** - For behavioral modes and orchestration patterns

---

**Made with care by tchow** | v1.5.0
