# Personal Automation Plugin

This plugin is a template for your custom workflows, agents, and automation patterns.

## Structure

```
personal-automation/
├── plugin.json          # Plugin configuration
├── commands/            # Custom slash commands
├── agents/              # Custom agent definitions
├── skills/              # Custom skills
└── README.md           # This file
```

## Adding Custom Content

### Commands

Create markdown files in `commands/` directory:

```markdown
---
name: my-command
description: Description of what this command does
---

Command implementation instructions for Claude...
```

Then add to `plugin.json`:
```json
{
  "commands": [
    "./commands/my-command.md"
  ]
}
```

### Agents

Create markdown files in `agents/` directory with agent definitions.

Then add to `plugin.json`:
```json
{
  "agents": [
    "./agents/my-agent.md"
  ]
}
```

### Skills

Create skill directories in `skills/` with `SKILL.md` files:

```markdown
---
name: my-skill
description: "Skill description with trigger conditions"
license: MIT
---

# My Skill

Skill content here...
```

Then add to `plugin.json`:
```json
{
  "skills": [
    "./skills/my-skill"
  ]
}
```

## Examples

See other plugins in this marketplace for examples:
- **superclaude-framework**: Commands and global instructions
- **chrome-devtools**: Commands and skills
- **netsuite-workflows**: Commands, scripts, and skills

## Installation

This plugin is automatically included when you install the `tchow-essentials` marketplace.

```bash
/plugin marketplace add tchow-twistedxcom/claude-marketplace
/plugin install personal-automation
```
