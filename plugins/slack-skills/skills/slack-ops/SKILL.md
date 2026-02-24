---
name: slack-ops
description: "Read and write Slack messages, manage channels, threads, reactions, and user profiles via MCP. Use when user mentions: Slack, channels, messages, notifications, threads, reactions, #channel-name, DMs, or wants to verify Slack-posted content like Health Digest messages."
---

# Slack Operations Skill

Read and write Slack messages via the official `@modelcontextprotocol/server-slack` MCP server.

## When to Use This Skill

- Reading messages from Slack channels (public or private)
- Posting messages to Slack channels
- Verifying bot-posted content (e.g., Health Digest messages from Celigo)
- Replying to message threads
- Adding emoji reactions to messages
- Listing channels or searching for a specific channel
- Looking up user profiles

## Available MCP Tools

| Tool | Purpose |
|------|---------|
| `slack_list_channels` | List public/private channels (use `limit` param) |
| `slack_get_channel_history` | Read recent messages from a channel |
| `slack_post_message` | Send a message to a channel |
| `slack_reply_to_thread` | Reply to a specific message thread |
| `slack_get_thread_replies` | Read all replies in a thread |
| `slack_add_reaction` | Add an emoji reaction to a message |
| `slack_get_users` | List workspace users |
| `slack_get_user_profile` | Get a specific user's profile |

## Setup

### Prerequisites

1. A Slack Bot with the following OAuth scopes:
   - `channels:history` + `channels:read` (public channels)
   - `groups:history` + `groups:read` (private channels)
   - `chat:write` (send messages)
   - `reactions:write` (add reactions)
   - `users:read` (list users)

2. Bot must be invited to any private channels it needs to access.

### Configuration

Edit `plugins/slack-skills/.mcp.json` and replace the placeholder values:

```json
{
  "slack": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-slack"],
    "env": {
      "SLACK_BOT_TOKEN": "xoxb-your-actual-bot-token",
      "SLACK_TEAM_ID": "T-your-team-id"
    }
  }
}
```

See `config/slack_config.template.json` for where to find these values.

## Common Workflows

### Verify Health Digest Message
1. `slack_list_channels` → find `#thomas-test-notifications` channel ID
2. `slack_get_channel_history` with the channel ID → read latest messages
3. Check the Block Kit message content for dynamic error data

### Post a Notification
1. `slack_list_channels` → find target channel ID
2. `slack_post_message` with channel ID and message text

### Read a Thread
1. `slack_get_channel_history` → find the message `ts` (timestamp)
2. `slack_get_thread_replies` with channel ID and thread `ts`
