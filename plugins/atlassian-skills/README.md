# Atlassian Skills

Skills for working with Atlassian Confluence and Jira via REST API.

## Skills Included

### atlassian-api

Execute Confluence and Jira operations via direct REST API calls with automatic OAuth token refresh.

**Confluence Operations:**
- Search pages by title (CQL fuzzy matching)
- Get, create, update, archive pages
- Upload and list attachments
- Navigate page hierarchies (children, spaces)
- Markdown-to-Confluence conversion with Mermaid diagram support

**Jira Operations:**
- Search issues with JQL
- Get, create, update issues
- Add comments
- Transition issues between statuses
- List projects and issue types

## Why Use This Over MCP?

- **More reliable** - Direct REST API calls, no hanging connections
- **Efficient** - ~50 tokens vs ~2000 for MCP responses
- **Markdown support** - Convert markdown files directly to Confluence format
- **Mermaid diagrams** - Full support for weweave Mermaid Charts plugin

## Quick Start

```bash
# Search Confluence
python3 scripts/atlassian_api.py --confluence search --query "PRI Container" --limit 10

# Create page from markdown
python3 scripts/atlassian_api.py --confluence create-page --space TWXGBDL --title "New Page" --body-file doc.md --input-format md

# Search Jira
python3 scripts/atlassian_api.py --jira search --jql "project = TWXDEV AND status = Open"
```

See the skill's SKILL.md for complete documentation.
