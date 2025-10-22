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

## Curated Community Plugins

### Anthropic Skills

#### document-skills
Excel, Word, PowerPoint, PDF processing

**Usage:**
Skills activate automatically when working with documents.

**Example:**
```
Create an Excel financial model with formulas
[xlsx skill activates automatically]
```

#### example-skills
Templates for creating skills, MCPs, canvas designs

**Usage:**
```
Help me create a new skill
[skill-creator activates automatically]
```

### Seth Hobson's Workflows

#### backend-development
API design, architecture, microservices

**Usage:**
Skills activate for backend work.

**Example:**
```
Design a REST API for user management
[API design principles skill activates]
```

#### security-scanning
Security auditing, SAST configuration

**Usage:**
```
Audit this codebase for security vulnerabilities
[Security scanning agent activates]
```

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

## Next Steps

- [Installation Guide](./INSTALLATION.md) - Setup details
- [Customization Guide](./CUSTOMIZATION.md) - Extend plugins
- [Main README](../README.md) - Overview

## Getting Help

- **Issues**: https://github.com/tchow-twistedxcom/claude-marketplace/issues
- **Claude Code Docs**: https://docs.claude.com/en/docs/claude-code
