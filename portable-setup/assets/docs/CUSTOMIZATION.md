# Customization Guide

Complete guide for customizing your Claude Code portable setup.

## Table of Contents
- [Statusline Customization](#statusline-customization)
- [Agent Customization](#agent-customization)
- [Hook Customization](#hook-customization)
- [Behavioral Mode Customization](#behavioral-mode-customization)
- [Notification Customization](#notification-customization)
- [MCP Server Integration](#mcp-server-integration)

---

## Statusline Customization

The statusline shows at the bottom of your Claude Code interface providing context about your current session.

### Using Presets (Easiest)

```bash
# Launch interactive UI
claudeup

# Browse 54 presets organized in 9 categories:
# • Color Themes: Catppuccin, Dracula, Nord, Gruvbox, Tokyo Night, etc.
# • Shell Prompts: Starship, Powerline, Pure, etc.
# • Developer: Hacker, DevOps, Metrics, Performance, etc.
# • Minimal: Zen, Clean, Arrow, Simple, etc.
# • Fun: Retro, Brackets, Pipes, Wave, etc.
# • Compact: Micro, Chevron, Slim, etc.
# • Time: Timer, Session-focused, Clock, etc.
# • Git-focused: Branch, Status, Commit info, etc.
# • Context-rich: Full details, Multi-line, etc.
```

### Using Custom Scripts

Edit `~/.claude/settings.json`:
```json
{
  "statusLine": {
    "type": "command",
    "command": "/path/to/your/custom-statusline.sh"
  }
}
```

### Template Variables

Available variables in custom statusline scripts:

| Variable | Description | Example |
|----------|-------------|---------|
| `{model}` | Current Claude model | `claude-sonnet-4` |
| `{git_branch}` | Active git branch | `main` |
| `{cwd}` | Current working directory | `/home/user/project` |
| `{input_tokens}` | Input tokens used | `1500` |
| `{output_tokens}` | Output tokens used | `800` |
| `{cost}` | Session cost | `$0.023` |
| `{session_duration}` | Time in session | `15:32` |

### Statusline Examples

#### Basic
Shows model and directory:
```bash
#!/bin/bash
echo "Claude $(basename $PWD)"
```

#### With Git Branch
```bash
#!/bin/bash
BRANCH=$(git branch --show-current 2>/dev/null)
echo "Claude $(basename $PWD) ${BRANCH:+($BRANCH)}"
```

#### With Colors
```bash
#!/bin/bash
MODEL="\033[36mClaude\033[0m"  # Cyan
DIR="\033[33m$(basename $PWD)\033[0m"  # Yellow
BRANCH=$(git branch --show-current 2>/dev/null)
echo -e "$MODEL $DIR ${BRANCH:+\033[32m($BRANCH)\033[0m}"
```

#### With Token Usage
```bash
#!/bin/bash
MODEL="Claude"
DIR=$(basename $PWD)
TOKENS="${CLAUDE_INPUT_TOKENS:-0}/${CLAUDE_OUTPUT_TOKENS:-0}"
echo "$MODEL $DIR [$TOKENS tokens]"
```

#### Powerline Style
Uses the default powerline package:
```json
{
  "statusLine": {
    "type": "command",
    "command": "npx -y @owloops/claude-powerline@latest --style=powerline"
  }
}
```

### Statusline Color Codes

ANSI color codes for terminal customization:

| Color | Code | Example |
|-------|------|---------|
| Black | `\033[30m` | `\033[30mText\033[0m` |
| Red | `\033[31m` | `\033[31mText\033[0m` |
| Green | `\033[32m` | `\033[32mText\033[0m` |
| Yellow | `\033[33m` | `\033[33mText\033[0m` |
| Blue | `\033[34m` | `\033[34mText\033[0m` |
| Magenta | `\033[35m` | `\033[35mText\033[0m` |
| Cyan | `\033[36m` | `\033[36mText\033[0m` |
| White | `\033[37m` | `\033[37mText\033[0m` |
| Reset | `\033[0m` | Returns to default |

Bold: Add `;1` after the color code (e.g., `\033[32;1m` for bold green)

---

## Agent Customization

Agents are specialized behaviors that activate based on context or explicit requests.

### Adding New Agents

Create `~/.claude/agents/your-agent-name.md`:

```markdown
# Agent Name

**Purpose**: Brief description of what this agent does

## Activation Triggers
- Explicit keyword: "use agent-name"
- Context patterns: when user mentions X
- File types: when working with .ext files
- Project types: when in React/Vue/etc. projects

## Behavioral Changes
- Specific behavior modification 1
- Specific behavior modification 2
- Tool preference changes
- Communication style changes

## Tool Preferences
- Prefer Tool A over Tool B for task X
- Use Tool C for specific operations
- Avoid Tool D in this context

## Examples

### Example 1: Basic Usage
```
User: <example user request>
Agent: <example agent response>
```

### Example 2: Advanced Usage
```
User: <example complex request>
Agent: <example detailed response>
```

## Success Criteria
- Deliverable 1 meets standard X
- Deliverable 2 validated by Y
- User feedback indicates Z
```

### Modifying Existing Agents

Edit any agent file in `~/.claude/agents/`:

```bash
nano ~/.claude/agents/existing-agent.md
```

**Common modifications**:
- Add new activation triggers
- Refine behavioral changes
- Update tool preferences
- Add examples from your usage
- Adjust success criteria

### Agent Activation

Agents activate through:

1. **Explicit requests**: "Use the [agent-name] agent"
2. **Keyword triggers**: Specified in activation triggers section
3. **Context detection**: File types, project structure, etc.
4. **Manual flags**: `--agent=[agent-name]`

### Agent Categories

Organize agents by purpose:

```
~/.claude/agents/
├── development/          # Code-focused agents
│   ├── react-dev.md
│   ├── python-expert.md
│   └── api-architect.md
├── operations/           # DevOps and deployment
│   ├── docker-ops.md
│   └── ci-cd-expert.md
├── data/                 # Data and analytics
│   ├── sql-expert.md
│   └── data-analyst.md
└── proprietary/          # Company-specific
    ├── twx-agent-1.md
    └── twx-agent-2.md
```

---

## Hook Customization

Hooks execute at specific points in the Claude Code workflow.

### Available Hooks

Located in `~/.config/claude-code/hooks/`:

| Hook | When It Runs | Use Cases |
|------|-------------|-----------|
| `on-wait.sh` | When Claude waits for user input | Send notifications, log sessions |
| `on-complete.sh` | When task completes | Validation, deployment triggers |
| `on-error.sh` | When errors occur | Error logging, alerting |
| `on-start.sh` | When session starts | Environment setup, context loading |

### on-wait Hook

**Current default**: Sends ntfy notification when Claude waits

Customize `~/.config/claude-code/hooks/on-wait.sh`:

```bash
#!/bin/bash
# Custom on-wait hook

# Send Slack notification
curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
  -H 'Content-Type: application/json' \
  -d '{"text": "Claude is waiting for input"}'

# Send email (using sendmail)
echo "Claude needs your attention" | mail -s "Claude Code Alert" you@example.com

# Desktop notification (Linux)
notify-send "Claude Code" "Waiting for input"

# Or keep ntfy
TOPIC="${NTFY_TOPIC_DEFAULT:-your-topic}"
curl -d "Claude is waiting" "https://ntfy.sh/$TOPIC"
```

### on-complete Hook

**Current default**: Runs validation and sends success notification

Customize `~/.config/claude-code/hooks/on-complete.sh`:

```bash
#!/bin/bash
# Custom on-complete hook

TASK="$1"  # Task description
STATUS="$2"  # success or failure

if [ "$STATUS" = "success" ]; then
    # Run tests
    npm test || exit 1

    # Build project
    npm run build || exit 1

    # Deploy to staging (optional)
    # npm run deploy:staging

    # Send success notification
    curl -d "✅ Task completed: $TASK" "https://ntfy.sh/your-topic"

    # Log to file
    echo "$(date): Task completed - $TASK" >> ~/.claude/task-log.txt
else
    # Send failure notification
    curl -d "❌ Task failed: $TASK" "https://ntfy.sh/your-errors-topic"
fi
```

### Hook Environment Variables

Available in all hooks:

```bash
$CLAUDE_SESSION_ID      # Unique session identifier
$CLAUDE_MODEL           # Current model (e.g., claude-sonnet-4)
$CLAUDE_CWD             # Current working directory
$CLAUDE_TASK            # Current task description
$NTFY_TOPIC_DEFAULT     # Default notification topic
$NTFY_TOPIC_ERRORS      # Error notification topic
```

---

## Behavioral Mode Customization

Modes change how Claude approaches tasks.

### Available Modes

Edit mode files in `~/.claude/`:

| Mode | File | Purpose |
|------|------|---------|
| Brainstorming | `MODE_Brainstorming.md` | Collaborative discovery |
| Introspection | `MODE_Introspection.md` | Meta-cognitive analysis |
| Orchestration | `MODE_Orchestration.md` | Tool optimization |
| Task Management | `MODE_Task_Management.md` | Complex multi-step work |
| Token Efficiency | `MODE_Token_Efficiency.md` | Symbol-enhanced communication |

### Customizing Modes

Edit any mode file to adjust:

1. **Activation Triggers**: When the mode should activate
2. **Behavioral Changes**: How Claude should behave differently
3. **Tool Preferences**: Which tools to prefer/avoid
4. **Communication Style**: Verbosity, tone, formatting
5. **Examples**: Reference examples for the mode

Example modification to `MODE_Task_Management.md`:

```markdown
## Activation Triggers
- Operations with >3 steps requiring coordination
- Multiple file/directory scope (>2 directories OR >3 files)
- Complex dependencies requiring phases
- Manual flags: `--task-manage`, `--delegate`
- **CUSTOM**: When working on feature-X projects  # Added custom trigger
```

### Creating New Modes

Create `~/.claude/MODE_YourMode.md`:

```markdown
# Your Mode Name

**Purpose**: What this mode accomplishes

## Activation Triggers
- When to activate this mode
- Keywords or patterns
- Manual flags

## Behavioral Changes
- How behavior differs from standard
- Communication style changes
- Process modifications

## Tool Selection
- Preferred tools in this mode
- Tools to avoid
- Special tool configurations

## Outcomes
- Expected results
- Success criteria
- Quality standards

## Examples
[Provide usage examples]
```

---

## Notification Customization

### ntfy Configuration

Edit `~/.config/claude-code/.env`:

```bash
# Topics
NTFY_TOPIC_DEFAULT=your-main-topic
NTFY_TOPIC_ERRORS=your-errors-topic
NTFY_TOPIC_BUILDS=your-builds-topic      # Custom topic
NTFY_TOPIC_DEPLOYMENTS=your-deploy-topic # Custom topic

# Features
NTFY_ENABLE_SOUND=true
NTFY_ENABLE_DESKTOP=true
NTFY_DAILY_SUMMARY=true

# Priority levels
NTFY_PRIORITY_INFO=3        # Info messages (1-5)
NTFY_PRIORITY_WARNING=4     # Warnings
NTFY_PRIORITY_ERROR=5       # Errors (max priority)

# Rate limiting
NTFY_MAX_PER_HOUR=30        # Max notifications per hour
NTFY_QUIET_HOURS=22-07      # No notifications between 10PM-7AM
```

### Advanced ntfy Configuration

Edit `~/.config/claude-code/config.json`:

```json
{
  "ntfy": {
    "docker": {
      "enabled": true,
      "url": "http://localhost:8093"
    },
    "features": {
      "enableActions": true,
      "attachments": true,
      "clickActions": true,
      "icons": true
    },
    "customization": {
      "successIcon": "✅",
      "errorIcon": "❌",
      "warningIcon": "⚠️",
      "defaultTags": ["claude-code", "automation"]
    }
  }
}
```

### Notification Actions

Add clickable actions to notifications:

```bash
# In hook script
curl -H "Actions: view, Open PR, https://github.com/user/repo/pulls/123" \
     -d "Pull request ready for review" \
     "https://ntfy.sh/your-topic"
```

### Multiple Notification Channels

Combine ntfy with other services:

```bash
#!/bin/bash
# Multi-channel notification script

MESSAGE="$1"
SEVERITY="${2:-info}"

# ntfy
curl -d "$MESSAGE" "https://ntfy.sh/your-topic"

# Slack (if high severity)
if [ "$SEVERITY" = "error" ]; then
    curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK \
         -H 'Content-Type: application/json' \
         -d "{\"text\": \"$MESSAGE\"}"
fi

# Email (if critical)
if [ "$SEVERITY" = "critical" ]; then
    echo "$MESSAGE" | mail -s "Claude Code Alert" you@example.com
fi
```

---

## MCP Server Integration

MCP servers extend Claude's capabilities with specialized tools.

### Available MCP Guides

Reference guides in `~/.claude/MCP_*.md`:

| Server | Guide | Purpose |
|--------|-------|---------|
| Context7 | `MCP_Context7.md` | Official docs lookup |
| Magic | `MCP_Magic.md` | UI component generation |
| Morphllm | `MCP_Morphllm.md` | Pattern-based edits |
| Playwright | `MCP_Playwright.md` | Browser automation |
| Sequential | `MCP_Sequential.md` | Multi-step reasoning |
| Serena | `MCP_Serena.md` | Semantic code understanding |

### Customizing MCP Guides

Edit any MCP guide to add:

- Project-specific triggers
- Custom usage patterns
- Integration with your agents
- Performance tips

Example addition to `MCP_Sequential.md`:

```markdown
## Project-Specific Triggers

### For React Projects
- Component architecture analysis
- State management flow debugging
- Performance bottleneck identification

### For API Projects
- Endpoint dependency mapping
- Request/response flow analysis
- Error propagation tracking
```

### Combining MCP Servers

Create agent that uses multiple MCP servers:

```markdown
# Full-Stack Feature Agent

**Purpose**: Implement complete full-stack features

## Tool Strategy
1. **Sequential MCP**: Plan implementation architecture
2. **Context7 MCP**: Get official framework patterns
3. **Magic MCP**: Generate UI components
4. **Playwright MCP**: Create E2E tests
5. **Serena MCP**: Track changes across codebase

## Workflow
1. Analyze requirements → Sequential
2. Look up best practices → Context7
3. Generate UI → Magic
4. Create tests → Playwright
5. Track implementation → Serena
```

---

## Advanced Customization

### Custom Commands

Create custom commands in `~/.claude/commands/`:

```bash
#!/bin/bash
# ~/.claude/commands/deploy

# Usage: /deploy [environment]

ENV="${1:-staging}"

echo "Deploying to $ENV..."

# Build
npm run build

# Test
npm test

# Deploy
if [ "$ENV" = "production" ]; then
    npm run deploy:prod
else
    npm run deploy:staging
fi

echo "✅ Deployed to $ENV"
```

Make executable:
```bash
chmod +x ~/.claude/commands/deploy
```

Use in Claude:
```
/deploy production
```

### Environment-Specific Configuration

Create multiple configuration profiles:

```bash
# ~/.claude/profiles/
├── work/
│   ├── agents/
│   ├── .env
│   └── settings.json
└── personal/
    ├── agents/
    ├── .env
    └── settings.json
```

Switch profiles:
```bash
# In .bashrc
alias claude-work='CLAUDE_PROFILE=~/.claude/profiles/work claude'
alias claude-personal='CLAUDE_PROFILE=~/.claude/profiles/personal claude'
```

### Logging and Analytics

Add logging to track Claude usage:

```bash
# ~/.config/claude-code/hooks/on-complete.sh

LOG_FILE=~/.claude/analytics.log

echo "$(date),$CLAUDE_MODEL,$CLAUDE_TASK,$STATUS,$DURATION" >> "$LOG_FILE"
```

Analyze logs:
```bash
# Task completion rate
grep "success" ~/.claude/analytics.log | wc -l

# Average session duration
awk -F, '{sum+=$5} END {print sum/NR}' ~/.claude/analytics.log
```

---

## Tips and Best Practices

### Statusline
- Keep it concise (< 80 characters)
- Use colors sparingly for readability
- Include only actionable information
- Test in different terminal sizes

### Agents
- Start simple, add complexity as needed
- Use clear, specific activation triggers
- Provide realistic examples
- Update based on actual usage patterns

### Hooks
- Make hooks idempotent (safe to run multiple times)
- Add error handling for external services
- Log hook execution for debugging
- Keep execution time under 5 seconds

### Modes
- Modes should feel distinctly different
- Avoid overlapping triggers
- Document when to use each mode
- Combine modes when needed

### Notifications
- Use appropriate priority levels
- Respect quiet hours
- Batch related notifications
- Test before deploying to production

### MCP Servers
- Understand each server's strengths
- Combine servers for complex tasks
- Monitor performance impact
- Update guides with learned patterns
