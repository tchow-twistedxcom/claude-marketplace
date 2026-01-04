# Usage Guide

Learn how to use each plugin in the tchow-essentials marketplace.

## SuperClaude Framework

### Commands Overview

| Command | Description | Example |
|---------|-------------|---------|
| `/sc:load` | Load project context | Session start |
| `/sc:save` | Save session state | Session end |
| `/sc:analyze` | Code analysis | Before refactoring |
| `/sc:implement` | Feature implementation | New feature development |
| `/sc:test` | Run tests | Quality assurance |
| `/sc:git` | Git operations | Commits, PRs |
| `/sc:document` | Generate documentation | API docs |
| `/sc:troubleshoot` | Debug issues | Error investigation |
| `/sc:design` | System design | Architecture planning |
| `/sc:build` | Build project | Compilation |
| `/sc:deploy` | Deployment workflows | Production release |

**[See full command list](../plugins/superclaude-framework/README.md)**

### Behavioral Modes

Modes activate automatically based on task context, or manually with flags:

#### Brainstorming Mode (`--brainstorm`)
**When:** Vague requirements, exploration needs

**Usage:**
```
--brainstorm I want to build something that helps with...
```

**What happens:**
- Socratic dialogue for requirements
- Collaborative discovery
- Structured brief generation

#### Introspection Mode (`--introspect`)
**When:** Complex problems, error recovery

**Usage:**
```
--introspect Analyze why this approach failed
```

**What happens:**
- Meta-cognitive analysis
- Pattern detection
- Learning insights

#### Orchestration Mode (`--orchestrate`)
**When:** Multi-tool operations, performance needs

**Usage:**
```
--orchestrate Optimize this workflow across 50 files
```

**What happens:**
- Smart tool selection
- Parallel execution
- Resource optimization

#### Task Management Mode (`--task-manage`)
**When:** >3 steps, complex scope

**Usage:**
```
--task-manage Implement authentication system
```

**What happens:**
- Hierarchical task breakdown
- Memory-driven context
- Progressive enhancement

#### Token Efficiency Mode (`--uc` / `--ultracompressed`)
**When:** Context pressure, large operations

**Usage:**
```
--uc Analyze entire codebase
```

**What happens:**
- Symbol-enhanced communication
- 30-50% token reduction
- Compressed clarity

### MCP Servers

SuperClaude includes 6 MCPs - automatically activated when relevant:

| MCP | Triggers | Use For |
|-----|----------|---------|
| **Context7** | Import statements, framework questions | Official library docs |
| **Sequential** | Complex analysis, `--think` flags | Multi-step reasoning |
| **Magic** | UI component requests, `/ui` command | Modern UI generation |
| **Playwright** | Browser testing, E2E scenarios | Real browser automation |
| **Serena** | Symbol operations, large codebases | Semantic understanding |
| **Morphllm** | Bulk edits, pattern updates | Pattern-based transformations |

### Workflow Examples

#### Example 1: New Feature Development
```bash
# 1. Load project context
/sc:load

# 2. Brainstorm requirements
--brainstorm Need user authentication

# 3. Design system
/sc:design JWT authentication

# 4. Implement with task management
--task-manage /sc:implement authentication

# 5. Test implementation
/sc:test authentication

# 6. Generate docs
/sc:document authentication

# 7. Save session
/sc:save
```

#### Example 2: Code Analysis & Refactoring
```bash
# 1. Load context
/sc:load

# 2. Analyze codebase
--think-hard /sc:analyze architecture

# 3. Improve code quality
--loop /sc:improve --focus=quality

# 4. Run comprehensive tests
/sc:test --coverage

# 5. Save improvements
/sc:save
```

#### Example 3: Troubleshooting
```bash
# 1. Load context
/sc:load

# 2. Analyze issue
--introspect /sc:troubleshoot "API timeout errors"

# 3. Implement fix
/sc:implement timeout handling

# 4. Verify fix
/sc:test integration

# 5. Document resolution
/sc:document troubleshooting
```

---

## Chrome DevTools

### Commands

#### `/browser-test`
Run browser automation and E2E testing.

**Basic Usage:**
```
/browser-test
Test the login form at http://localhost:3000/login
```

**What happens:**
1. Connects to Chrome at http://localhost:37443
2. Navigates to URL
3. Takes snapshot (accessible tree)
4. Performs interactions (fill, click)
5. Validates expected behavior
6. Reports results with screenshots

**Advanced Usage:**
```
/browser-test
Run visual regression test:
1. Navigate to homepage
2. Take baseline screenshot
3. Make styling changes
4. Take comparison screenshot
5. Report differences
```

### Skills

#### E2E Testing Patterns
Automatically activates when:
- Creating browser tests
- Implementing E2E scenarios
- Validating user journeys

**Provides:**
- Page Object patterns
- Snapshot-first approach
- Visual validation workflows
- Performance testing patterns
- Accessibility testing

### Common Workflows

#### User Journey Testing
```
Test user registration flow:
1. Navigate to /register
2. Fill form (email, password, confirm)
3. Submit form
4. Verify success message
5. Check console for errors
6. Take screenshot of dashboard
```

#### Visual Validation
```
Check homepage rendering:
1. Navigate to homepage
2. Take snapshot for structure
3. Take screenshot for visuals
4. List console messages
5. Report any errors or warnings
```

#### Performance Testing
```
Analyze page performance:
1. Start performance trace
2. Navigate to target page
3. Stop trace
4. Report Core Web Vitals
5. Identify bottlenecks
```

---

## NetSuite Workflows

### Commands

#### `/deploy-netsuite`
Deploy SDF bundles to NetSuite environments.

**Basic Usage:**
```
/deploy-netsuite
Deploy Record Display to SB2
```

**Interactive Prompts:**
1. Bundle name (default: "Record Display")
2. Target environment (sb2, production, dev)
3. Confirmation

**What happens:**
1. Validates bundle structure
2. Executes deployment script
3. Monitors output
4. Reports status and errors

**Advanced Usage:**
```
/deploy-netsuite
Validate bundle before deploying to production
```

#### `/netsuite-setup`
Configure NetSuite SDF projects.

**Usage:**
```
/netsuite-setup
Set up new SDF project for customizations
```

**Guides through:**
1. Project initialization
2. Account authentication
3. Project structure
4. Environment configuration

### Skills

#### SDF Bundle Creation
Automatically activates when:
- Creating NetSuite objects
- Writing SuiteScripts
- Configuring bundles

**Provides:**
- Bundle structure patterns
- Naming conventions
- Script templates
- Deployment best practices

#### NetSuite Customization
Automatically activates when:
- Implementing workflows
- Creating saved searches
- Designing integrations

**Provides:**
- Workflow patterns
- Search formulas
- Form customization
- RESTlet templates
- Performance optimization

### Common Workflows

#### Deploy to Sandbox
```
/deploy-netsuite
Deploy "Record Display" to SB2
```

#### Create New Bundle
```
/netsuite-setup
Create new bundle for Order Management
```

#### Production Deployment
```
/deploy-netsuite
Validate bundle first
Deploy to production (with confirmation)
```

---

## Personal Automation

This is a template plugin - add your own content!

### Adding Custom Commands

1. Create command file:
```bash
# /plugins/personal-automation/commands/my-workflow.md
---
name: my-workflow
description: Custom infrastructure automation
---

Instructions for Claude to execute this workflow...
```

2. Update plugin.json:
```json
{
  "commands": ["./commands/my-workflow.md"]
}
```

3. Reload plugin:
```bash
/plugin reload personal-automation
```

4. Use command:
```bash
/my-workflow
```

### Adding Custom Skills

1. Create skill directory:
```bash
mkdir -p plugins/personal-automation/skills/my-skill
```

2. Create SKILL.md:
```markdown
---
name: my-skill
description: "When to use this skill"
---

# My Skill

Skill content...
```

3. Update plugin.json:
```json
{
  "skills": ["./skills/my-skill"]
}
```

4. Skill activates automatically when conditions match

---

## Celigo Integration

Enterprise iPaaS integration with 63 MCP tools for managing integrations, flows, connections, jobs, and errors.

### Commands

#### `/celigo-setup`
Configure Celigo CLI and API authentication.

**Usage:**
```
/celigo-setup
Configure API keys for production environment
```

#### `/celigo-manage`
Manage integrations, flows, and connections via CLI.

**Usage:**
```
/celigo-manage
List all active integrations and their status
```

### Skills

#### Integration Patterns
Automatically activates when:
- Designing data integrations
- Building ETL workflows
- Connecting business applications

**Provides:**
- Best practices for Celigo integrations
- Error handling patterns
- Rate limiting strategies
- Data transformation templates

### MCP Tools Available
| Category | Tools |
|----------|-------|
| Integrations | List, get, create, update, clone, delete |
| Flows | List, get, enable, disable, run, schedule |
| Connections | List, get, create, test, update |
| Jobs | List, get, rerun, retry errors |
| Errors | List, get, acknowledge, reprocess |
| Lookup Caches | List, manage, refresh |
| Tags | List, apply, remove |

---

## Shopify Workflows

Shopify Admin API workflow automation with 5 specialized skills.

### Skills

#### Content Creator
For blog articles, pages, and theme assets.

**Activates when:**
- Creating blog posts
- Managing pages
- Publishing content

**Example:**
```
Create a blog post about our new product launch
[content-creator skill activates]
```

#### Merchant Operations
For inventory, orders, and product management.

**Activates when:**
- Managing products
- Processing orders
- Updating inventory

#### Marketing Campaigns
For discounts, promotions, and customer engagement.

**Activates when:**
- Creating discount codes
- Setting up promotions
- Building marketing campaigns

#### Developer Integrations
For webhooks, metafields, and custom apps.

**Activates when:**
- Building Shopify integrations
- Setting up webhooks
- Developing custom functionality

#### Analytics
For sales reports and performance metrics.

**Activates when:**
- Generating reports
- Analyzing trends
- Querying performance metrics

---

## Atlassian Skills

Confluence and Jira operations via REST API with OAuth authentication.

### Skills

#### Atlassian API
Full coverage for Confluence and Jira operations.

**Confluence Operations:**
- Page creation, update, archive
- Space management
- Search functionality
- Attachment handling
- Markdown-to-Confluence conversion with Mermaid diagram support

**Jira Operations:**
- Issue management (create, update, transition)
- JQL queries
- Comment handling
- Workflow transitions

**Activates when:**
```
Create a Confluence page documenting the API
[atlassian-api skill activates]

Search Jira for all open bugs assigned to me
[atlassian-api skill activates]
```

---

## Plytix PIM Skills

Product Information Management operations via REST API with multi-account support.

### Skills

#### Plytix PIM
Full coverage for PIM operations.

**Capabilities:**
- Product management (CRUD, bulk operations)
- Digital asset handling (upload, organize, link)
- Category organization (hierarchies, assignments)
- Variant creation and management
- Attribute schema management

**Activates when:**
```
Upload product images to Plytix
[plytix-pim skill activates]

Create product variants for size options
[plytix-pim skill activates]
```

**Supports:**
- Multi-account (production/staging)
- Bulk operations
- Asset workflows

---

## NinjaOne RMM Skills

Remote Monitoring and Management API integration with 70+ endpoints.

### Skills

#### NinjaOne API
Full coverage across 9 domains.

| Domain | Capabilities |
|--------|-------------|
| Devices | List, get, manage, monitor |
| Alerts | Create, acknowledge, resolve |
| Ticketing | Create, update, assign tickets |
| Patching | Scan, approve, deploy patches |
| Reports | Generate, schedule, export |
| Groups | Create, manage, assign devices |
| Policies | Create, apply, manage |
| Users | List, manage, permissions |
| Automation | Scripts, scheduled tasks |

**Activates when:**
```
Get status of all Windows devices
[ninjaone-api skill activates]

Create a patch approval for Microsoft updates
[ninjaone-api skill activates]
```

---

## M365 / Azure AD Skills

Microsoft 365 and Azure integrations via Microsoft Graph API.

### Skills

#### Azure AD / Entra ID
Directory operations for users, groups, and devices.

**Capabilities:**
- User management (create, update, disable, license)
- Group management (create, membership, dynamic groups)
- Device management (list, compliance, policies)
- Directory queries and reports

**Authentication:**
- MSAL OAuth 2.0
- Delegated and application permissions
- Token caching

**Activates when:**
```
List all users in the Engineering group
[m365-azuread skill activates]

Disable account and revoke sessions for terminated employee
[m365-azuread skill activates]
```

---

## Amazon SP-API Skills

Amazon Selling Partner API integration via Python CLI.

### Skills

9 specialized skills covering Vendor (1P) and Seller operations.

| Skill | Coverage |
|-------|----------|
| Vendor Orders | Purchase orders, acknowledgments |
| Vendor Shipments | ASN creation, shipment tracking |
| Vendor Invoices | Invoice submission, reconciliation |
| Seller Orders | Order management, fulfillment |
| Catalog | Product listing, content management |
| Inventory | FBA inventory, replenishment |
| Reports | Sales reports, inventory reports |
| Feeds | Bulk operations, feed submission |
| Pricing | Competitive pricing, repricing |

**Features:**
- LWA OAuth authentication
- Rate limiting with exponential backoff
- Multi-region support (NA, EU, FE)

**Activates when:**
```
Submit ASN for PO-12345 to Amazon
[amazon-spapi skill activates]

Check FBA inventory levels for ASIN B08XYZ123
[amazon-spapi skill activates]
```

---

## Mimecast Skills

Email security integration with 28 operations.

### Skills

#### Mimecast Security
Full coverage for email security operations.

| Category | Operations |
|----------|------------|
| TTP URL Protection | Decode, analyze, report |
| TTP Attachment Protection | Scan, quarantine, release |
| Held Messages | List, release, reject |
| User Management | Create, update, groups |
| Blocked Senders | Add, remove, list |
| Permitted Senders | Add, remove, list |
| Audit Logs | Query, export |
| SIEM Integration | Log streaming, events |

**Authentication:**
- HMAC-SHA1 signing
- Multi-region support

**Activates when:**
```
Release held message for user@company.com
[mimecast-security skill activates]

Add sender to blocked list
[mimecast-security skill activates]
```

---

## ClaudeKit Skills

Curated collection of 35+ specialized skills for development workflows.

### Claude Code Mastery

Expert guidance for Claude Code usage (auto-updates to match official releases).

**Covers:**
- Tool selection (Read vs Bash, Edit vs MultiEdit)
- Agent orchestration (30+ subagent types)
- MCP integration and configuration
- Hooks system
- CLI mastery

**Activates when:**
```
Which tool should I use to edit multiple files?
[claude-code skill activates]

How do I configure an MCP server?
[claude-code skill activates]
```

### Framework Skills

| Skill | Usage |
|-------|-------|
| `nextjs` | Next.js App Router, server components, data fetching |
| `tailwindcss` | Utility-first styling, responsive design, dark mode |
| `shadcn-ui` | UI components with Radix + Tailwind |
| `better-auth` | Authentication framework for TypeScript |
| `turborepo` | Monorepo build system |

### Tool Skills

| Skill | Usage |
|-------|-------|
| `ffmpeg` | Video/audio encoding, conversion, streaming |
| `imagemagick` | Image processing, format conversion, batch ops |
| `repomix` | Repository packaging for AI analysis |
| `mcp-builder` | Creating MCP servers (Python/TypeScript) |

### Debugging Methodologies

4 systematic approaches to debugging:

| Skill | When to Use |
|-------|-------------|
| `systematic-debugging` | Structured investigation process |
| `root-cause-tracing` | Finding underlying causes |
| `defense-in-depth` | Layered error prevention |
| `verification-before-completion` | Ensuring fixes are complete |

**Activates when:**
```
Help me debug this authentication failure
[debugging skill activates]
```

### Problem-Solving Techniques

6 techniques for complex problems:

| Technique | Description |
|-----------|-------------|
| `when-stuck` | Strategies for breaking through blocks |
| `inversion-exercise` | Solving by considering opposites |
| `collision-zone-thinking` | Finding points of conflict |
| `minimum-viable-change` | Smallest effective solution |
| `evidence-based-diagnosis` | Data-driven problem solving |
| `problem-loop-detection` | Identifying circular issues |

**Activates when:**
```
I'm stuck on how to approach this refactoring
[problem-solving skill activates]
```

### Document Processing

| Skill | Formats | Operations |
|-------|---------|------------|
| `docx` | Word documents | Create, edit, track changes, comments |
| `xlsx` | Excel spreadsheets | Formulas, formatting, data analysis |
| `pptx` | PowerPoint | Create, edit, layouts, notes |
| `pdf` | PDF documents | Extract, create, merge, forms |

**Activates when:**
```
Create an Excel report with pivot tables
[xlsx skill activates]

Fill out this PDF form
[pdf skill activates]
```

### Additional Skills

| Skill | Purpose |
|-------|---------|
| `google-adk` | Google Agent Development Kit for AI agents |
| `remix-icon` | Icon library integration (3100+ icons) |
| `shopify` | Shopify app/extension development |
| `skill-creator` | Creating new Claude Code skills |
| `docs-seeker` | Finding documentation via llms.txt |
| `canvas-design` | Creating visual art and designs |
| `frontend-design` | Production-grade UI development |

---

## Tips & Best Practices

### General
1. **Start sessions with `/sc:load`** - Loads project context
2. **End sessions with `/sc:save`** - Persists state
3. **Use flags for mode control** - `--brainstorm`, `--think`, `--uc`
4. **Let skills activate automatically** - Trust the framework

### SuperClaude
1. **Combine modes** - `--think --task-manage` for complex work
2. **Use /sc: commands** - Structured workflows
3. **Leverage MCP servers** - They activate when needed
4. **Track with todos** - Framework manages task lists

### Chrome DevTools
1. **Take snapshots first** - More reliable than screenshots
2. **Wait for dynamic content** - Use `wait_for()` with text
3. **Check console always** - Include in every test
4. **Capture screenshots** - Visual evidence for validation

### NetSuite
1. **Validate before deploy** - Catch errors early
2. **Test in sandbox** - Never deploy untested to production
3. **Use skills for patterns** - SDF and customization skills guide
4. **Document customizations** - Maintain clear records

### Enterprise Integrations (Celigo, Shopify, Atlassian, etc.)
1. **Set up authentication first** - Run `/celigo-setup` or equivalent before operations
2. **Use read-only operations initially** - List and get before create/update
3. **Test in staging/sandbox** - Most integrations support multi-environment
4. **Handle rate limits** - Skills include built-in throttling strategies
5. **Check audit logs** - Most integrations log operations for troubleshooting

### Amazon SP-API
1. **Use correct endpoint region** - NA, EU, or FE depending on marketplace
2. **Handle throttling gracefully** - Built-in exponential backoff
3. **Validate ASNs before submission** - Check carton/pallet counts
4. **Monitor report generation** - Reports are async, check status

### ClaudeKit Skills
1. **Let skills auto-activate** - Don't force activation unnecessarily
2. **Use debugging skills early** - Systematic approach saves time
3. **Combine problem-solving techniques** - When stuck, try multiple approaches
4. **Keep claude-code skill updated** - Auto-sync with official releases

## Next Steps

- [Installation Guide](./INSTALLATION.md) - Setup details
- [Customization Guide](./CUSTOMIZATION.md) - Extend plugins
- [Main README](../README.md) - Overview

## Getting Help

- **Issues**: https://github.com/tchow-twistedxcom/claude-marketplace/issues
- **Claude Code Docs**: https://docs.claude.com/en/docs/claude-code
