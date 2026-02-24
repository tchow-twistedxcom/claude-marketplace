---
name: slack-ops
description: "Read, search, and write Slack messages, canvases, and user profiles via the official Slack MCP server. Use when user mentions: Slack, channels, messages, notifications, threads, search, canvases, drafts, #channel-name, DMs, or wants to verify Slack-posted content like Health Digest messages."
---

# Slack Operations Skill

Interact with Slack via the official MCP server at `mcp.slack.com/mcp`.

## When to Use This Skill

- Searching for messages, files, channels, or people in Slack
- Reading messages from channels or threads
- Posting messages or creating drafts in Slack
- Creating or reading Slack canvases
- Verifying bot-posted content (e.g., Health Digest messages from Celigo)
- Looking up user profiles, statuses, and custom fields

## Available MCP Tools

### Search

| Tool | Purpose |
|------|---------|
| `slack_search_public` | Search public channels (no consent required) |
| `slack_search_public_and_private` | Search all channels including private, DMs, group DMs (requires user consent) |
| `slack_search_channels` | Find channels by name or description |
| `slack_search_users` | Find users by name, email, or role |

### Read

| Tool | Purpose |
|------|---------|
| `slack_read_channel` | Read recent messages from a channel (supports `oldest`/`latest` timestamps) |
| `slack_read_thread` | Read all replies in a message thread |
| `slack_read_user_profile` | Get user profile info including custom fields and status |

### Write

| Tool | Purpose |
|------|---------|
| `slack_send_message` | Send a message to any conversation |
| `slack_send_message_draft` | Create a draft message for review in Slack client |
| `slack_create_canvas` | Create and share a rich canvas document |

## Setup

### Authentication

The official Slack MCP server uses **OAuth 2.0** with user tokens. No bot token or manual API key setup required.

1. The MCP server is hosted remotely at `https://mcp.slack.com/mcp`
2. On first use, Claude Code triggers an OAuth flow in your browser
3. You authorize the app in your Slack workspace
4. Authentication is cached — no need to re-auth each session

### Configuration

The `.mcp.json` is pre-configured:

```json
{
  "mcpServers": {
    "slack": {
      "type": "http",
      "url": "https://mcp.slack.com/mcp",
      "oauth": {
        "clientId": "1601185624273.8899143856786",
        "callbackPort": 3118
      }
    }
  }
}
```

Run `/mcp` in Claude Code to verify the connection and trigger OAuth if needed.

### OAuth Scopes (granted during authorization)

- `search:read.public`, `search:read.private`, `search:read.mpim`, `search:read.im` (search)
- `search:read.files` (file search)
- `search:read.users` (user search)
- `chat:write` (send messages)
- `channels:history`, `groups:history`, `mpim:history`, `im:history` (read messages)
- `canvases:read`, `canvases:write` (canvas operations)
- `users:read`, `users:read.email` (user profiles)

## Common Workflows

### Search for Messages

1. `slack_search_public` with a natural language query or keywords
2. Add modifiers: `in:channel-name`, `from:@user`, `after:2025-01-01`
3. Use `slack_read_thread` to get full thread context on results

### Verify Health Digest Message

1. `slack_search_channels` → find `thomas-test-notifications` channel
2. `slack_read_channel` → read latest messages
3. Check the Block Kit message content for dynamic error data and buttons

### Post a Notification

1. `slack_search_channels` → find target channel by name
2. `slack_send_message` with channel ID and mrkdwn-formatted text

### Draft an Announcement

1. `slack_search_channels` → find target channel
2. `slack_send_message_draft` → create draft for user to review and send from Slack

### Create a Document

1. `slack_create_canvas` → create a rich formatted canvas
2. Share it in a channel via `slack_send_message` with a link

### Read a Thread

1. `slack_read_channel` → find the message timestamp
2. `slack_read_thread` with channel ID and thread timestamp

### Find a Person

1. `slack_search_users` with name, email, or role
2. `slack_read_user_profile` for full profile details

## Slash Commands

| Command | Description |
|---------|-------------|
| `/slack:summarize-channel <channel>` | Summarize recent activity in a channel |
| `/slack:find-discussions <topic>` | Find discussions about a topic across channels |
| `/slack:draft-announcement <topic>` | Draft a formatted announcement |
| `/slack:standup` | Generate standup from your recent activity |
| `/slack:channel-digest <ch1,ch2,...>` | Digest of multiple channels |
