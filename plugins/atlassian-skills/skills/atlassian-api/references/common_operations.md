# Common Operations Reference

Pre-built command patterns for frequent tasks.

## Confluence Operations

### Documentation Workflows

**Find and read a page:**
```bash
# Search for page
python3 scripts/atlassian_api.py --confluence search "PRI Container" --limit 5

# Read content
python3 scripts/atlassian_api.py --confluence get-page 1881669695 --format markdown
```

**Create documentation page:**
```bash
# Create under parent page
python3 scripts/atlassian_api.py --confluence create-page \
  --space TWXGBDL \
  --title "Feature Documentation" \
  --body-file docs/feature.html \
  --parent 1821736961
```

**Update existing page:**
```bash
# Update with version message
python3 scripts/atlassian_api.py --confluence update-page 3174662145 \
  --body-file updated_content.html \
  --message "Added troubleshooting section"
```

### Space Exploration

**List all spaces:**
```bash
python3 scripts/atlassian_api.py --confluence list-spaces --format table
```

**List pages in space:**
```bash
python3 scripts/atlassian_api.py --confluence list-pages --space TWXGBDL --limit 100
```

## Jira Operations

### Issue Management

**Find my open issues:**
```bash
python3 scripts/atlassian_api.py --jira search \
  "assignee = currentUser() AND status != Done ORDER BY updated DESC" \
  --limit 20
```

**Create and track a task:**
```bash
# Create
python3 scripts/atlassian_api.py --jira create-issue \
  --project TWXDEV \
  --type Task \
  --summary "Implement feature X" \
  --description "Detailed requirements here"

# Start work
python3 scripts/atlassian_api.py --jira transition TWXDEV-999 --to "In Progress"

# Add comment
python3 scripts/atlassian_api.py --jira add-comment TWXDEV-999 \
  --body "Started implementation. ETA: 2 days"

# Complete
python3 scripts/atlassian_api.py --jira transition TWXDEV-999 --to "Done"
```

**Bug triage:**
```bash
# Find unassigned bugs
python3 scripts/atlassian_api.py --jira search \
  "project = TWXDEV AND issuetype = Bug AND assignee IS EMPTY" \
  --limit 20

# Get bug details
python3 scripts/atlassian_api.py --jira get-issue TWXDEV-123 --format json

# Assign to self (need account ID)
python3 scripts/atlassian_api.py --jira update-issue TWXDEV-123 \
  --fields '{"assignee": {"accountId": "5ebc331106a3eb0b7e500075"}}'
```

### Sprint Management

**Current sprint issues:**
```bash
python3 scripts/atlassian_api.py --jira search \
  "project = TWXDEV AND sprint IN openSprints()" \
  --limit 50
```

**Blocked issues:**
```bash
python3 scripts/atlassian_api.py --jira search \
  "project = TWXDEV AND status = Blocked" \
  --format json
```

## Multi-Site Operations

**Switch between sites:**
```bash
# Twisted X (default)
python3 scripts/atlassian_api.py --confluence search "docs"

# Explicit site
python3 scripts/atlassian_api.py --site twx --confluence search "docs"
python3 scripts/atlassian_api.py --site dm --jira search "project = DM"
```

## Output Format Examples

**Table (default) - compact, human-readable:**
```bash
python3 scripts/atlassian_api.py --confluence search "PRI" --format table
```
Output:
```
[twistedx.atlassian.net] Confluence - 3 page(s)
ID          | Title                              | Space  | Updated
3174563841  | PRI Departure Ports - Admin...     | TWXGBDL| 2025-12-16
3174662145  | PRI Transit Time Mapping - C...    | TWXGBDL| 2025-12-16
3174694913  | PRI Container Ports & Transi...    | TWXGBDL| 2025-12-16
```

**JSON - for programmatic use:**
```bash
python3 scripts/atlassian_api.py --jira get-issue TWXDEV-123 --format json
```

**CSV - for data export:**
```bash
python3 scripts/atlassian_api.py --jira search "project = TWXDEV" --format csv > issues.csv
```

**Markdown - for documentation:**
```bash
python3 scripts/atlassian_api.py --confluence get-page 123456 --format markdown
```

## Scripting Patterns

### Bash: Process multiple pages
```bash
#!/bin/bash
# Export all pages from a space
for page_id in $(python3 scripts/atlassian_api.py --confluence list-pages --space TWXGBDL --format json | jq -r '.[].id'); do
  python3 scripts/atlassian_api.py --confluence get-page $page_id --format markdown > "page_$page_id.md"
done
```

### Bash: Bulk issue updates
```bash
#!/bin/bash
# Close all resolved issues
issues=$(python3 scripts/atlassian_api.py --jira search "status = Resolved" --format json | jq -r '.[].key')
for issue in $issues; do
  python3 scripts/atlassian_api.py --jira transition $issue --to "Closed"
  echo "Closed: $issue"
done
```

### Python: Integration example
```python
import subprocess
import json

def search_confluence(query, limit=10):
    result = subprocess.run([
        'python3', 'scripts/atlassian_api.py',
        '--confluence', 'search',
        '--query', query,
        '--limit', str(limit),
        '--format', 'json'
    ], capture_output=True, text=True)
    return json.loads(result.stdout)

pages = search_confluence("PRI Container")
for page in pages:
    print(f"{page['id']}: {page['title']}")
```

## Quick Reference

| Task | Command |
|------|---------|
| Search Confluence | `--confluence search "query"` |
| Get page content | `--confluence get-page ID` |
| Create page | `--confluence create-page --space X --title Y` |
| Update page | `--confluence update-page ID --body-file F` |
| List spaces | `--confluence list-spaces` |
| Search Jira | `--jira search "JQL"` |
| Get issue | `--jira get-issue KEY` |
| Create issue | `--jira create-issue --project X --type Y --summary Z` |
| Transition issue | `--jira transition KEY --to STATUS` |
| Add comment | `--jira add-comment KEY --body "text"` |
| List sites | `--list-sites` |
