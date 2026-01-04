---
name: claude-code
description: "Comprehensive guide for expert Claude Code usage including tool selection, agent orchestration, MCP integration, hooks, CLI mastery, and advanced workflows. This skill should be used when choosing between native tools (Read vs Bash, Edit vs MultiEdit), selecting specialized agents for tasks, configuring MCP servers, writing hooks, optimizing Claude Code performance, or debugging Claude Code issues."
version: 2.0.0
license: MIT
---

# Claude Code Mastery

Expert guidance for maximizing Claude Code effectiveness through intelligent tool selection, agent orchestration, and advanced feature utilization.

## When to Use This Skill

This skill activates when:
- Choosing between native tools (Read vs Bash, Edit vs MultiEdit, Grep vs Task)
- Selecting specialized agents for tasks (which of 30+ subagent types)
- Configuring MCP servers and integrations
- Writing hooks for automation
- Optimizing performance or debugging issues
- Understanding CLI flags and advanced features

## Quick Decision Frameworks

### Which Native Tool?

| Task | Best Tool | Avoid |
|------|-----------|-------|
| Read file content | `Read` | `Bash cat` |
| Search file content | `Grep` | `Bash grep/rg` |
| Find files by pattern | `Glob` | `Bash find` |
| Edit 1-2 files | `Edit` | `MultiEdit` |
| Edit 3+ files | `MultiEdit` | Sequential `Edit` |
| Complex codebase search | `Task` (Explore agent) | Direct `Grep` |
| System/git commands | `Bash` | - |
| Fetch web content | `WebFetch` | `Bash curl` |
| Search the web | `WebSearch` | - |
| Clarify with user | `AskUserQuestion` | Assumptions |
| Track progress | `TodoWrite` | - |
| Plan complex work | `EnterPlanMode` | Jumping to code |

**Key Principle**: Use specialized tools over Bash equivalents for better integration and output handling.

### Which Agent? (Quick Reference)

**For Exploration**:
- `Explore` - Codebase discovery, file patterns, understanding structure
- `general-purpose` - Complex multi-step research
- `claude-code-guide` - Questions about Claude Code itself

**For Implementation**:
- `Plan` - Design implementation strategy before coding
- `feature-dev:code-architect` - Feature blueprints and design
- `tc-implementation-agent` - Production-ready feature development

**For Quality**:
- `feature-dev:code-reviewer` - Code review and quality check
- `security-engineer` - Vulnerability assessment
- `performance-engineer` - Optimization analysis

**For Debugging**:
- `root-cause-analyst` - Complex bug investigation
- `refactoring-expert` - Code improvement and cleanup

See [references/agent-catalog.md](references/agent-catalog.md) for all 30+ agents organized by use case.

### Which MCP Server?

| Need | MCP Server | Transport |
|------|------------|-----------|
| Library documentation | Context7 | stdio |
| Complex multi-step reasoning | Sequential | stdio |
| UI component generation | Magic | stdio |
| Browser automation/testing | Playwright | stdio |
| Live browser inspection | Chrome DevTools | stdio |
| Semantic code operations | Serena | stdio |
| Bulk pattern-based edits | Morphllm | stdio |
| Cloud services/OAuth | HTTP servers | http |

See [references/mcp-guide.md](references/mcp-guide.md) for configuration examples.

## Core Concepts

### Architecture

Claude Code operates as an **agentic coding tool** with:
- **Terminal-first execution** - Direct file edits, command execution, commits
- **Subagents** - Specialized AI agents for specific task types
- **Plugins** - Custom commands, skills, hooks, MCP servers
- **MCP Integration** - Connect external tools via Model Context Protocol

### Tool Hierarchy

Prefer tools in this order:
1. **Specialized tools** (Read, Edit, Grep, Glob) - Best integration
2. **Task agents** - Complex multi-step operations
3. **MCP tools** - External service integration
4. **Bash** - System commands, git operations

### Agent Invocation

To use a specialized agent:
```
Task tool with subagent_type parameter
```

Agents run autonomously and return results. Launch multiple agents in parallel for independent operations.

## CLI Essentials

### Core Commands

```bash
claude                          # Interactive REPL
claude "query"                  # Start with prompt
claude -p "query"               # Print mode (non-interactive)
claude -c                       # Continue last conversation
claude -r "session" "query"     # Resume specific session
```

### Essential Flags

| Flag | Purpose |
|------|---------|
| `-p, --print` | Non-interactive output |
| `-c, --continue` | Resume last conversation |
| `--model <name>` | Select model (sonnet/opus/haiku) |
| `--agent <name>` | Use specific agent |
| `--tools "..."` | Restrict available tools |
| `--max-turns <n>` | Limit agentic turns |
| `--verbose` | Detailed output |
| `--debug` | Debug logging |

See [references/cli-reference.md](references/cli-reference.md) for all 30+ flags.

## Hooks System

Hooks automate responses to Claude Code events.

### Event Types

| Event | Purpose | Has Matcher |
|-------|---------|-------------|
| `PreToolUse` | Before tool execution | Yes |
| `PostToolUse` | After tool completes | Yes |
| `PermissionRequest` | Permission dialog shown | Yes |
| `UserPromptSubmit` | User submits prompt | No |
| `Stop` | Main agent finishes | No |
| `SubagentStop` | Subagent finishes | No |
| `SessionStart` | Session begins | Yes |
| `SessionEnd` | Session ends | No |

### Hook Types

- **Command hooks** (`type: "command"`) - Execute bash scripts
- **Prompt hooks** (`type: "prompt"`) - LLM-based decisions (Haiku)

### Basic Example

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "npx prettier --write \"$TOOL_INPUT_FILE_PATH\"",
        "timeout": 30
      }]
    }]
  }
}
```

See [references/hooks-reference.md](references/hooks-reference.md) for complete documentation.

## Common Workflows

### Debugging Pattern

1. **Understand** - Use `Explore` agent or `Read` to understand context
2. **Investigate** - Use `root-cause-analyst` agent for complex bugs
3. **Fix** - Use `Edit` for targeted changes
4. **Verify** - Use `Bash` to run tests

### Implementation Pattern

1. **Plan** - Use `EnterPlanMode` for non-trivial features
2. **Design** - Use `Plan` agent for architecture
3. **Implement** - Use `Edit`/`MultiEdit` for code
4. **Review** - Use `feature-dev:code-reviewer` agent
5. **Test** - Use `Bash` for test execution

### Research Pattern

1. **Explore** - Use `Explore` agent with specific focus
2. **Read** - Use `Read` for identified files
3. **Synthesize** - Combine findings
4. **Report** - Present to user

See [examples/](examples/) for detailed workflow walkthroughs.

## Advanced Features

### Extended Thinking

Enable for complex problems requiring deep reasoning:
- **10k tokens** - Moderate complexity
- **20k tokens** - High complexity
- **32k tokens** - Critical/architectural decisions

### Plan Mode

Use `EnterPlanMode` for:
- Multi-file implementations
- Architectural decisions
- Unclear requirements
- Multiple valid approaches

### Parallel Execution

Launch multiple independent operations simultaneously:
- Multiple `Read` calls for different files
- Multiple `Task` agents for independent research
- Multiple `Grep` searches

### Session Management

```bash
claude -c                    # Continue last session
claude -r "name" "query"     # Resume named session
claude --fork-session        # Branch from existing
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Tool not working | Check `--tools` flag, verify permissions |
| MCP connection failed | Run `/mcp`, check config, verify server running |
| Agent not triggering | Verify subagent_type spelling, check description match |
| Hook not executing | Run `/hooks`, check JSON syntax, verify matcher |
| Performance slow | Use appropriate model (haiku for simple), enable caching |

### Debug Mode

```bash
claude --debug              # Enable debug logging
claude --debug "api,mcp"    # Specific categories
claude --verbose            # Detailed turn output
```

## Auto-Update

This skill automatically syncs with official Claude Code documentation via GitHub mirrors.

### How It Works

1. **On Activation**: Background check runs with < 50ms latency
2. **Version Detection**: Parses official CHANGELOG.md for version numbers
3. **Content Sync**: Fetches documentation from GitHub mirror (updated every 3 hours)
4. **Notification**: Shows update prompt when new content is available

### Sources

| Source | URL | Purpose |
|--------|-----|---------|
| Changelog | `anthropics/claude-code/CHANGELOG.md` | Version detection |
| Docs Mirror | `ericbuess/claude-code-docs` | Documentation content |

### Commands

```bash
# Check current status
python3 scripts/skill_autoupdate.py --status

# Force update now
python3 scripts/skill_autoupdate.py --update

# Quick check (runs automatically on activation)
python3 scripts/skill_autoupdate.py --check
```

### What Gets Updated

| File | Description |
|------|-------------|
| `references/*.md` | Regenerated from GitHub docs mirror |
| `skill.json` | Version synced to match Claude Code release |

### Cache Behavior

- **Fresh** (< 6 hours): No network check
- **Stale** (6h - 7 days): Background refresh, serve cached
- **Expired** (> 7 days): Force refresh attempt

## Reference Index

| Document | Content |
|----------|---------|
| [references/tool-selection.md](references/tool-selection.md) | Complete tool decision matrix |
| [references/agent-catalog.md](references/agent-catalog.md) | All 30+ agents by use case |
| [references/mcp-guide.md](references/mcp-guide.md) | MCP configuration and selection |
| [references/workflows.md](references/workflows.md) | Detailed workflow patterns |
| [references/enterprise.md](references/enterprise.md) | Enterprise deployment guide |

## Example Walkthroughs

| Example | Description |
|---------|-------------|
| [examples/debugging-workflow.md](examples/debugging-workflow.md) | Complete debugging session |
| [examples/feature-implementation.md](examples/feature-implementation.md) | End-to-end feature build |
| [examples/research-exploration.md](examples/research-exploration.md) | Codebase exploration |

---

*Last updated: 2025-12-20*
