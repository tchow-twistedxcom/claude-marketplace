---
name: atlassian-api
description: "Execute Atlassian Confluence and Jira operations via REST API. Use when creating/updating Confluence pages, searching Jira issues, or managing documentation. More reliable than MCP with efficient response formatting that reduces context usage by 97%."
---

# Atlassian API Skill

Execute Confluence and Jira operations via direct REST API calls with automatic OAuth token refresh.

## When to Use This Skill

- Creating, updating, or reading Confluence pages
- Converting Markdown to Confluence storage format (with Mermaid diagram support)
- Uploading attachments to Confluence pages
- Searching Confluence content and navigating page hierarchies
- Creating, updating, or transitioning Jira issues
- Searching Jira with JQL queries
- When the Atlassian MCP is unreliable or hanging
- When response efficiency is critical (this skill uses ~50 tokens vs ~2000 for MCP)

## OAuth Scopes

This skill uses **v2 granular OAuth scopes**. Your Atlassian app must have these scopes configured:

**Confluence (Required):**
- `read:content:confluence`, `write:content:confluence`
- `read:content-details:confluence`, `read:page:confluence`, `write:page:confluence`
- `read:space:confluence`

**Jira (Optional):**
- `read:jira-work`, `write:jira-work`, `read:jira-user`

**Required for refresh tokens:**
- `offline_access` - MUST be included

See [README.md](README.md) for complete OAuth setup instructions.

## Quick Start

```bash
# Set up config first (see README.md for OAuth setup)
cd ~/.claude/skills/atlassian-api

# Confluence operations
python3 scripts/atlassian_api.py --confluence search --query "PRI Container" --limit 10
python3 scripts/atlassian_api.py --confluence get-page --page-id 3174662145 --format markdown
python3 scripts/atlassian_api.py --confluence list-spaces

# Jira operations
python3 scripts/atlassian_api.py --jira search --jql "project = TWXDEV AND status = Open"
python3 scripts/atlassian_api.py --jira get-issue --issue-key TWXDEV-123
python3 scripts/atlassian_api.py --jira transition --issue-key TWXDEV-123 --to "Done"
```

## Confluence Operations

### Search Pages
```bash
# Search by title (partial match supported)
python3 scripts/atlassian_api.py --confluence search --query "Container" --limit 10

# Search within a specific space
python3 scripts/atlassian_api.py --confluence search --query "Container" --space TWXGBDL --limit 10
```

### Get Page Content
```bash
python3 scripts/atlassian_api.py --confluence get-page --page-id 3174662145 --format markdown
python3 scripts/atlassian_api.py --confluence get-page --page-id 3174662145 --format json
python3 scripts/atlassian_api.py --confluence get-page --page-id 3174662145 --format storage  # Raw XHTML
```

### Create Page
```bash
# From HTML file
python3 scripts/atlassian_api.py --confluence create-page --space TWXGBDL --title "New Page" --body-file content.html

# From Markdown file (auto-converted with TOC sidebar)
python3 scripts/atlassian_api.py --confluence create-page --space TWXGBDL --title "New Page" --body-file content.md --input-format md
```

### Update Page
```bash
# Standard update (HTML)
python3 scripts/atlassian_api.py --confluence update-page --page-id 3174662145 --body-file updated.html --message "Update note"

# Update from Markdown (auto-converted)
python3 scripts/atlassian_api.py --confluence update-page --page-id 3174662145 --body-file document.md --input-format md --message "Updated from markdown"

# Dry-run (preview without saving)
python3 scripts/atlassian_api.py --confluence update-page --page-id 3174662145 --body-file updated.md --input-format md --dry-run
```

### Archive Page
```bash
# Archive a page (safer than delete - reversible via Confluence UI)
python3 scripts/atlassian_api.py --confluence archive-page --page-id 3174662145
```

### List Spaces
```bash
python3 scripts/atlassian_api.py --confluence list-spaces --limit 20
```

### List Pages in Space
```bash
python3 scripts/atlassian_api.py --confluence list-pages --space TWXGBDL --limit 20
```

### Get Child Pages
```bash
python3 scripts/atlassian_api.py --confluence get-children --page-id 3174662145 --limit 20
```

### Upload Attachment
```bash
python3 scripts/atlassian_api.py --confluence upload-attachment --page-id 3174662145 --file /path/to/image.png --comment "Screenshot"
```

### List Attachments
```bash
python3 scripts/atlassian_api.py --confluence list-attachments --page-id 3174662145
```

## Markdown to Confluence Converter

Convert Markdown files to Confluence storage format with full support for Mermaid diagrams.

### Basic Usage
```bash
# Convert markdown file to Confluence format
python3 scripts/md_to_confluence.py input.md output.html

# Then upload to Confluence
python3 scripts/atlassian_api.py --confluence update-page --page-id 123456 --body-file output.html
```

### Supported Markdown Features
- Headings (H1-H6) with automatic anchor generation
- Bold, italic, inline code
- Links and images
- Ordered and unordered lists
- Tables
- Code blocks with syntax highlighting
- Mermaid diagrams (rendered via weweave plugin)
- Horizontal rules
- Confluence Table of Contents macro (auto-generated in sidebar)

### Mermaid Diagram Support

The converter automatically converts Mermaid code blocks to the weweave "Mermaid Charts & Diagrams for Confluence" macro format.

**Example Markdown:**
````markdown
```mermaid
flowchart TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action]
    B -->|No| D[End]
```
````

**Features enabled by default:**
- Theme: `neutral` (best for light/dark mode)
- Pan & zoom: enabled
- Fullscreen: enabled
- Alignment: center

### Mermaid Best Practices

**IMPORTANT: Follow these rules to avoid rendering errors:**

| Issue | Wrong | Correct |
|-------|-------|---------|
| Line breaks | `<br/>` | `<br>` |
| Nested brackets | `[Task: [value]]` | `[Task: value]` |
| Special chars in nodes | `Node[Text with "quotes"]` | `Node[Text with quotes]` |

**Common Errors:**

1. **"Parse error... Expecting 'SQE'"** - Usually caused by nested `[]` brackets in node definitions
   ```mermaid
   # WRONG - nested brackets break parser
   A[Task: [New value]]

   # CORRECT - remove inner brackets
   A[Task: New value]
   ```

2. **Diagram not rendering** - Check for `<br/>` tags (should be `<br>`)

3. **Broken in dark mode** - Use `neutral` theme instead of `default`

### Two-Column Layout with TOC

The converter automatically creates a two-column layout:
- **Left column**: Main content
- **Right sidebar**: Table of Contents (sticky navigation)

This matches the Confluence best practice for long documents.

## Jira Operations

### Search Issues (JQL)
```bash
python3 scripts/atlassian_api.py --jira search --jql "project = TWXDEV AND status = Open" --limit 20
python3 scripts/atlassian_api.py --jira search --jql "assignee = currentUser() ORDER BY updated DESC"
```

**Note:** Jira v3 API requires bounded queries. Always include a filter (project, assignee, etc.) - unbounded queries like `ORDER BY updated` alone will fail.

### Get Issue Details
```bash
python3 scripts/atlassian_api.py --jira get-issue --issue-key TWXDEV-123
python3 scripts/atlassian_api.py --jira get-issue --issue-key TWXDEV-123 --format json
```

### Create Issue
```bash
python3 scripts/atlassian_api.py --jira create-issue --project TWXDEV --type Task --summary "New task" --description "Details"
```

### Update Issue
```bash
python3 scripts/atlassian_api.py --jira update-issue --issue-key TWXDEV-123 --fields '{"summary": "Updated title"}'
```

### Add Comment
```bash
python3 scripts/atlassian_api.py --jira add-comment --issue-key TWXDEV-123 --body "This is a comment"
```

### Transition Issue
```bash
# First, list available transitions
python3 scripts/atlassian_api.py --jira transitions --issue-key TWXDEV-123

# Then transition
python3 scripts/atlassian_api.py --jira transition --issue-key TWXDEV-123 --to "Done"
```

### List Projects
```bash
python3 scripts/atlassian_api.py --jira list-projects --limit 20
```

### List Issue Types
```bash
# All issue types
python3 scripts/atlassian_api.py --jira list-issue-types

# Issue types for specific project
python3 scripts/atlassian_api.py --jira list-issue-types --project TWXDEV
```

## Multi-Site Support

```bash
# Default site (from config)
python3 scripts/atlassian_api.py --confluence search --query "Container"

# Specific site
python3 scripts/atlassian_api.py --site twx --confluence search --query "Container"
python3 scripts/atlassian_api.py --site dm --jira search --jql "project = DM"

# List available sites
python3 scripts/atlassian_api.py --list-sites
```

## Output Formats

| Format | Use Case | Token Usage |
|--------|----------|-------------|
| `table` | Human-readable listing (default) | ~50 tokens |
| `json` | Programmatic processing | ~100 tokens |
| `csv` | Data export | ~30 tokens |
| `markdown` | Page content with formatting | Varies |
| `storage` | Raw Confluence XHTML | Varies |

## Common Options

```
--site, -s       Site alias (twx, dm, etc.)
--format, -f     Output format: table, json, csv, markdown, storage
--limit, -l      Max results (default: 20)
--timeout, -t    Request timeout in seconds (default: 30)
--verbose, -v    Show debug info
--dry-run        Preview changes without saving (update-page only)
--input-format   Input format for body content: html (default) or md (auto-converted)
```

## Response Efficiency

This skill produces compact output compared to the Atlassian MCP:

**MCP Response (~2000 tokens):**
```json
{"parentType":"page","parentId":"1821736961","lastOwnerId":null,...full nested JSON...}
```

**This Skill (~50 tokens):**
```
[twistedx.atlassian.net] Confluence - 3 page(s)
ID          | Title                              | Space  | Updated
3174563841  | PRI Departure Ports - Admin...     | TWXGBDL| 2025-12-16
```

## Troubleshooting

### Authentication Errors
```bash
# Test authentication
python3 scripts/auth.py

# If token expired, the skill auto-refreshes
# If refresh token invalid, re-run OAuth flow (see README.md)
```

### Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| "Config file not found" | No config | Copy template to `config/atlassian_config.json` |
| "Token refresh failed" | Invalid refresh token | Re-run OAuth authorization flow |
| "HTTP 403" | Missing permissions | Check OAuth app scopes |
| "Space not found" | Wrong space key | Use `--confluence list-spaces` to verify |
| "Unbounded JQL queries not allowed" | Missing filter in JQL | Add project, assignee, or other filter |
| "Parse error" in Mermaid | Invalid syntax | Check for nested `[]` or `<br/>` tags |

## Files

- `scripts/atlassian_api.py` - Main CLI executor
- `scripts/md_to_confluence.py` - Markdown to Confluence converter
- `scripts/auth.py` - OAuth 2.0 authentication
- `scripts/formatters.py` - Response formatting
- `config/atlassian_config.json` - Credentials (create from template)
- `references/confluence_api.md` - Confluence API patterns
- `references/jira_api.md` - Jira JQL reference

## Related Documentation

- [README.md](README.md) - Installation and OAuth setup
- [references/confluence_api.md](references/confluence_api.md) - Confluence patterns
- [references/jira_api.md](references/jira_api.md) - JQL syntax reference
