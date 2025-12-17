# Jira REST API Reference

Quick reference for Jira operations via this skill.

## Issue Operations

### Search Issues (JQL)
```bash
# Basic search
python3 scripts/atlassian_api.py --jira search --jql "project = TWXDEV"

# With filters
python3 scripts/atlassian_api.py --jira search --jql "project = TWXDEV AND status = Open" --limit 50

# Complex JQL
python3 scripts/atlassian_api.py --jira search \
  --jql "project = TWXDEV AND assignee = currentUser() AND updated >= -7d ORDER BY priority DESC"
```

**Note:** Jira v3 API requires bounded queries. Always include a filter (project, assignee, etc.) - unbounded queries like `ORDER BY updated` alone will fail.

### Get Issue Details
```bash
# Default format (markdown-style)
python3 scripts/atlassian_api.py --jira get-issue --issue-key TWXDEV-123

# JSON format (full details)
python3 scripts/atlassian_api.py --jira get-issue --issue-key TWXDEV-123 --format json
```

### Create Issue
```bash
# Basic task
python3 scripts/atlassian_api.py --jira create-issue \
  --project TWXDEV \
  --type Task \
  --summary "Implement new feature"

# With description
python3 scripts/atlassian_api.py --jira create-issue \
  --project TWXDEV \
  --type Bug \
  --summary "Login button not working" \
  --description "Users report clicking login does nothing on Safari"
```

### Update Issue
```bash
# Update summary
python3 scripts/atlassian_api.py --jira update-issue --issue-key TWXDEV-123 \
  --fields '{"summary": "Updated title"}'

# Update multiple fields
python3 scripts/atlassian_api.py --jira update-issue --issue-key TWXDEV-123 \
  --fields '{"summary": "New title", "priority": {"name": "High"}}'

# Add labels
python3 scripts/atlassian_api.py --jira update-issue --issue-key TWXDEV-123 \
  --fields '{"labels": ["urgent", "customer-reported"]}'
```

### Add Comment
```bash
python3 scripts/atlassian_api.py --jira add-comment --issue-key TWXDEV-123 \
  --body "Investigated this issue. Root cause is XYZ."
```

### Transition Issue
```bash
# First, see available transitions
python3 scripts/atlassian_api.py --jira transitions --issue-key TWXDEV-123

# Then transition by name
python3 scripts/atlassian_api.py --jira transition --issue-key TWXDEV-123 --to "In Progress"
python3 scripts/atlassian_api.py --jira transition --issue-key TWXDEV-123 --to "Done"

# Or by ID
python3 scripts/atlassian_api.py --jira transition --issue-key TWXDEV-123 --to "31"
```

## JQL Reference

### Basic Syntax
```sql
field OPERATOR value [AND|OR field OPERATOR value]
```

### Common Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Equals | `status = Open` |
| `!=` | Not equals | `status != Done` |
| `~` | Contains (text) | `summary ~ "login"` |
| `!~` | Not contains | `summary !~ "test"` |
| `>`, `<` | Greater/less | `created > -7d` |
| `>=`, `<=` | Greater/less or equal | `priority >= High` |
| `IN` | In list | `status IN (Open, "In Progress")` |
| `NOT IN` | Not in list | `status NOT IN (Done, Closed)` |
| `IS` | Is empty/null | `assignee IS EMPTY` |
| `IS NOT` | Is not empty | `assignee IS NOT EMPTY` |
| `WAS` | Was at some point | `status WAS "In Progress"` |
| `CHANGED` | Field changed | `status CHANGED` |

### Common Fields

| Field | Description | Example |
|-------|-------------|---------|
| `project` | Project key | `project = TWXDEV` |
| `status` | Issue status | `status = Open` |
| `assignee` | Assigned user | `assignee = currentUser()` |
| `reporter` | Reporter | `reporter = "john@example.com"` |
| `priority` | Priority level | `priority = High` |
| `issuetype` | Issue type | `issuetype = Bug` |
| `created` | Creation date | `created >= -30d` |
| `updated` | Last update | `updated >= startOfWeek()` |
| `resolved` | Resolution date | `resolved IS NOT EMPTY` |
| `labels` | Issue labels | `labels = urgent` |
| `component` | Components | `component = "Backend"` |
| `fixVersion` | Fix version | `fixVersion = "1.0"` |
| `sprint` | Sprint | `sprint IN openSprints()` |
| `text` | Full text search | `text ~ "error message"` |

### Date Functions

| Function | Description |
|----------|-------------|
| `now()` | Current time |
| `startOfDay()` | Start of today |
| `startOfWeek()` | Start of current week |
| `startOfMonth()` | Start of current month |
| `startOfYear()` | Start of current year |
| `endOfDay()` | End of today |
| `endOfWeek()` | End of current week |
| `-Nd` | N days ago |
| `-Nw` | N weeks ago |

### Common JQL Patterns

```sql
-- My open issues
project = TWXDEV AND assignee = currentUser() AND status != Done

-- Recently updated bugs
project = TWXDEV AND issuetype = Bug AND updated >= -7d ORDER BY updated DESC

-- Unassigned issues
project = TWXDEV AND assignee IS EMPTY AND status = Open

-- High priority items
project = TWXDEV AND priority IN (Highest, High) AND status != Done

-- Issues in current sprint
project = TWXDEV AND sprint IN openSprints()

-- Overdue issues
project = TWXDEV AND duedate < now() AND status != Done

-- Issues created this month
project = TWXDEV AND created >= startOfMonth()

-- Full text search
project = TWXDEV AND text ~ "authentication error"
```

## Issue Types

Common issue types (project-specific):

| Type | Description |
|------|-------------|
| `Bug` | Software defect |
| `Task` | Work item |
| `Story` | User story |
| `Epic` | Large feature |
| `Sub-task` | Child of another issue |
| `Improvement` | Enhancement |

## Transitions

Transitions are workflow-specific. Common patterns:

| From | To | Transition Name |
|------|-----|-----------------|
| Open | In Progress | "Start Progress" |
| In Progress | Done | "Done" |
| In Progress | Open | "Stop Progress" |
| Any | Closed | "Close Issue" |

Use `--jira transitions --issue-key XXX` to see available transitions.

## API Endpoints Used

| Operation | Endpoint | Method |
|-----------|----------|--------|
| Search | `/rest/api/3/search` | POST |
| Get issue | `/rest/api/3/issue/{key}` | GET |
| Create issue | `/rest/api/3/issue` | POST |
| Update issue | `/rest/api/3/issue/{key}` | PUT |
| Add comment | `/rest/api/3/issue/{key}/comment` | POST |
| Get transitions | `/rest/api/3/issue/{key}/transitions` | GET |
| Transition | `/rest/api/3/issue/{key}/transitions` | POST |

## Field Formats for Updates

```json
// String fields
{"summary": "New title"}

// Select fields (by name)
{"priority": {"name": "High"}}
{"issuetype": {"name": "Bug"}}

// User fields
{"assignee": {"accountId": "5ebc331106a3eb0b7e500075"}}

// Array fields
{"labels": ["label1", "label2"]}

// Components
{"components": [{"name": "Backend"}]}
```

## Rate Limits

Jira Cloud rate limits:
- **Standard**: 100 requests/minute per user
- **Search**: Limited by result size
- **Bulk operations**: Use batching

## Tips

1. **JQL escaping**: Quote strings with spaces: `status = "In Progress"`
2. **Current user**: Use `currentUser()` function instead of email
3. **Date math**: Use relative dates like `-7d` for "7 days ago"
4. **Transitions**: Always check available transitions first
5. **Assignee by ID**: Use `accountId`, not email (for GDPR compliance)
6. **Bulk updates**: Consider scripting for many issues
