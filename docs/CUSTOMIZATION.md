# Customization Guide

Learn how to extend and customize the tchow-essentials marketplace plugins.

## Table of Contents
- [Plugin Structure](#plugin-structure)
- [Adding Commands](#adding-commands)
- [Creating Skills](#creating-skills)
- [Adding MCP Servers](#adding-mcp-servers)
- [Global Instructions](#global-instructions)
- [Creating New Plugins](#creating-new-plugins)
- [Marketplace Configuration](#marketplace-configuration)

---

## Plugin Structure

Standard plugin structure:

```
my-plugin/
├── plugin.json              # Plugin configuration (required)
├── commands/                # Slash commands
│   └── my-command.md
├── agents/                  # Agent definitions
│   └── my-agent.md
├── skills/                  # Skills
│   └── my-skill/
│       └── SKILL.md
├── mcp-configs/             # MCP server configs
│   └── my-mcp.json
└── README.md               # Documentation
```

### plugin.json Schema

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Plugin description",
  "author": {
    "name": "Your Name",
    "url": "https://github.com/yourusername"
  },
  "license": "MIT",
  "keywords": ["keyword1", "keyword2"],
  "category": "development",
  "strict": false,
  "commands": ["./commands/my-command.md"],
  "agents": ["./agents/my-agent.md"],
  "skills": ["./skills/my-skill"],
  "mcpServers": ["./mcp-configs/my-mcp.json"],
  "globalInstructions": ["./instructions.md"]
}
```

---

## Adding Commands

### Command File Format

Create `commands/my-command.md`:

```markdown
---
name: my-command
description: Brief description of what this command does
---

# Command Implementation

Detailed instructions for Claude on how to execute this command.

## Usage

When the user requests [trigger phrase]:

1. Step 1
2. Step 2
3. Step 3

## Examples

**User:** "Do something"
**Action:** Execute command logic

## Error Handling

If X happens, do Y.
```

### Registering Commands

Update `plugin.json`:

```json
{
  "commands": [
    "./commands/my-command.md",
    "./commands/another-command.md"
  ]
}
```

### Testing Commands

```bash
# Reload plugin
/plugin reload my-plugin

# Test command
/my-command
```

### Command Best Practices

1. **Clear Triggers**: Define when command should activate
2. **Step-by-Step**: Break down logic into numbered steps
3. **Examples**: Show typical use cases
4. **Error Handling**: Anticipate common failures
5. **Output Format**: Specify what user should see

---

## Creating Skills

### Skill File Format

Create `skills/my-skill/SKILL.md`:

```markdown
---
name: my-skill
description: "When Claude needs to do X, this skill provides Y patterns. Use when Z conditions exist."
license: MIT
---

# My Skill Title

## When to Use

This skill activates when:
- Condition 1
- Condition 2
- Condition 3

## Patterns Provided

### Pattern 1: Name
Description and code examples

### Pattern 2: Name
Description and code examples

## Best Practices

1. Practice 1
2. Practice 2

## Examples

Example usage scenarios
```

### Skill Frontmatter

```yaml
---
name: skill-name          # Required: Unique identifier
description: "..."        # Required: When/why to use this skill
license: MIT              # Optional: License type
author: Your Name         # Optional: Author info
version: 1.0.0           # Optional: Version
---
```

### Registering Skills

Update `plugin.json`:

```json
{
  "skills": [
    "./skills/my-skill",
    "./skills/another-skill"
  ]
}
```

### Skill Activation

Skills activate automatically when conditions in description match. Example:

```markdown
description: "Use when implementing REST APIs with Express.js"
```

Activates when Claude detects:
- REST API work
- Express.js framework
- API implementation tasks

### Skill Best Practices

1. **Specific Triggers**: Clear activation conditions
2. **Actionable Patterns**: Provide copy-paste templates
3. **Context-Aware**: Include when to use each pattern
4. **Examples**: Real-world use cases
5. **Cross-References**: Link to related skills

---

## Adding MCP Servers

### MCP Configuration Format

Create `mcp-configs/my-mcp.json`:

```json
{
  "my-mcp": {
    "command": "npx",
    "args": [
      "my-mcp-package@latest",
      "--option=value"
    ],
    "env": {
      "MY_API_KEY": "",
      "OTHER_VAR": "value"
    }
  }
}
```

### MCP Types

#### NPX Package
```json
{
  "my-mcp": {
    "command": "npx",
    "args": ["-y", "package@latest"]
  }
}
```

#### Local Script
```json
{
  "my-mcp": {
    "command": "node",
    "args": ["/path/to/script.js"]
  }
}
```

#### HTTP MCP
```json
{
  "my-mcp": {
    "type": "http",
    "url": "https://api.example.com/mcp"
  }
}
```

### Registering MCP Servers

Update `plugin.json`:

```json
{
  "mcpServers": [
    "./mcp-configs/my-mcp.json"
  ]
}
```

### MCP Best Practices

1. **Environment Variables**: Store API keys securely
2. **Version Pinning**: Use `@latest` or specific version
3. **Error Handling**: Provide clear error messages
4. **Documentation**: Document required environment variables

---

## Global Instructions

### Format

Create global instruction files (markdown):

```markdown
# My Global Instructions

These instructions apply to all Claude Code interactions when this plugin is active.

## Principle 1

Detailed explanation and examples

## Principle 2

Detailed explanation and examples
```

### Registering Global Instructions

Update `plugin.json`:

```json
{
  "globalInstructions": [
    "./instructions/coding-standards.md",
    "./instructions/project-conventions.md"
  ]
}
```

### Use Cases

- Coding standards
- Project conventions
- Team workflows
- Security requirements
- Quality guidelines

---

## Creating New Plugins

### Step 1: Create Structure

```bash
cd /home/tchow/claude-marketplace/plugins
mkdir -p my-new-plugin/{commands,agents,skills,mcp-configs}
```

### Step 2: Create plugin.json

```bash
cat > my-new-plugin/plugin.json <<EOF
{
  "name": "my-new-plugin",
  "version": "1.0.0",
  "description": "Description",
  "author": {
    "name": "tchow",
    "url": "https://github.com/tchow-twistedxcom"
  },
  "license": "MIT",
  "strict": false,
  "commands": [],
  "skills": []
}
EOF
```

### Step 3: Add to Marketplace

Update `.claude-plugin/marketplace.json`:

```json
{
  "plugins": [
    {
      "name": "my-new-plugin",
      "source": "./plugins/my-new-plugin",
      "description": "Plugin description",
      "version": "1.0.0"
    }
  ]
}
```

### Step 4: Test Plugin

```bash
/plugin marketplace refresh
/plugin install my-new-plugin
```

---

## Marketplace Configuration

### Adding External Plugins

Reference GitHub repos in marketplace.json:

```json
{
  "plugins": [
    {
      "name": "external-plugin",
      "source": {
        "source": "github",
        "repo": "username/repo"
      },
      "description": "⭐ Curated: External plugin"
    }
  ]
}
```

### Plugin Categories

Use these categories for organization:

- `framework` - Core frameworks
- `development` - Development tools
- `testing` - Testing tools
- `deployment` - Deployment automation
- `security` - Security tools
- `automation` - Workflow automation
- `skills` - Skill collections

### Marketplace Metadata

Update marketplace metadata:

```json
{
  "name": "marketplace-name",
  "owner": {
    "name": "Your Name",
    "email": "email@example.com",
    "url": "https://github.com/username"
  },
  "metadata": {
    "description": "Marketplace description",
    "version": "1.0.0",
    "homepage": "https://github.com/username/repo",
    "repository": "https://github.com/username/repo",
    "license": "MIT"
  }
}
```

---

## Example: Complete Custom Plugin

### Directory Structure
```
plugins/deployment-automation/
├── plugin.json
├── commands/
│   ├── deploy-staging.md
│   └── deploy-production.md
├── skills/
│   └── deployment-patterns/
│       └── SKILL.md
└── README.md
```

### plugin.json
```json
{
  "name": "deployment-automation",
  "version": "1.0.0",
  "description": "Automated deployment workflows for staging and production",
  "author": {
    "name": "tchow",
    "url": "https://github.com/tchow-twistedxcom"
  },
  "license": "MIT",
  "keywords": ["deployment", "ci-cd", "automation"],
  "category": "deployment",
  "strict": false,
  "commands": [
    "./commands/deploy-staging.md",
    "./commands/deploy-production.md"
  ],
  "skills": [
    "./skills/deployment-patterns"
  ]
}
```

### commands/deploy-staging.md
```markdown
---
name: deploy-staging
description: Deploy application to staging environment
---

# Deploy to Staging

Execute deployment workflow for staging environment.

## Steps

1. Run tests
2. Build application
3. Deploy to staging
4. Verify deployment
5. Report status

## Usage

**User:** "Deploy to staging"
**Action:** Execute full staging deployment workflow
```

### skills/deployment-patterns/SKILL.md
```markdown
---
name: deployment-patterns
description: "Use when implementing deployment workflows, CI/CD pipelines, or automated releases."
---

# Deployment Patterns

## Zero-Downtime Deployment

Blue-green deployment pattern...

## Rollback Strategy

How to safely rollback...
```

---

## Testing & Debugging

### Test Plugin Locally

```bash
# Reload after changes
/plugin reload my-plugin

# Check plugin status
/plugin list

# Test commands
/my-command

# Verify skills activate
# (Skills activate automatically based on triggers)
```

### Debug Issues

1. **Command not found**
   - Check plugin.json `commands` array
   - Verify file path is correct
   - Reload plugin

2. **Skill not activating**
   - Check skill description triggers
   - Verify path in plugin.json
   - Test with explicit trigger phrases

3. **MCP server errors**
   - Check MCP config syntax
   - Verify command/package exists
   - Test MCP independently: `npx package@latest`

---

## Best Practices Summary

1. **Modular Design**: Small, focused plugins
2. **Clear Documentation**: README for each plugin
3. **Semantic Versioning**: Version plugins properly
4. **Test Thoroughly**: Test before committing
5. **Git Workflow**: Commit, tag versions, push
6. **User-Friendly**: Clear command names and descriptions

---

## Next Steps

- [Usage Guide](./USAGE.md) - Learn how to use plugins
- [Installation Guide](./INSTALLATION.md) - Setup instructions
- [Main README](../README.md) - Overview

## Resources

- **Claude Code Plugin Docs**: https://docs.claude.com/en/docs/claude-code/plugins
- **Example Plugins**: Check `plugins/` directory in this repo
- **Community Examples**:
  - Anthropic Skills: https://github.com/anthropics/skills
  - Seth Hobson's Workflows: https://github.com/wshobson/agents
