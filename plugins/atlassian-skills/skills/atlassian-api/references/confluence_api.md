# Confluence REST API Reference

Quick reference for Confluence operations via this skill.

## Page Operations

### Search Pages
```bash
# Basic search (fuzzy title match)
python3 scripts/atlassian_api.py --confluence search --query "Container" --limit 10

# Search within a specific space
python3 scripts/atlassian_api.py --confluence search --query "PRI" --space TWXGBDL --limit 10

# Output as JSON
python3 scripts/atlassian_api.py --confluence search --query "API" --format json
```

### Get Page by ID
```bash
# Get as markdown (default for content)
python3 scripts/atlassian_api.py --confluence get-page --page-id 3174662145 --format markdown

# Get as JSON (metadata + content)
python3 scripts/atlassian_api.py --confluence get-page --page-id 3174662145 --format json

# Get raw HTML
python3 scripts/atlassian_api.py --confluence get-page --page-id 3174662145 --format html
```

### Create Page
```bash
# From file
python3 scripts/atlassian_api.py --confluence create-page \
  --space TWXGBDL \
  --title "New Documentation Page" \
  --body-file content.md \
  --parent 1821736961

# From stdin
echo "# Page Content\n\nThis is the body." | \
  python3 scripts/atlassian_api.py --confluence create-page \
    --space TWXGBDL \
    --title "Quick Page"
```

**Body format:** Confluence storage format (XHTML-based). Markdown is NOT automatically converted.

### Update Page
```bash
# Update content from file
python3 scripts/atlassian_api.py --confluence update-page --page-id 3174662145 \
  --body-file updated_content.md \
  --message "Updated diagrams section"

# Update title too
python3 scripts/atlassian_api.py --confluence update-page --page-id 3174662145 \
  --body-file content.md \
  --title "New Title" \
  --message "Renamed page"
```

## Space Operations

### List Spaces
```bash
python3 scripts/atlassian_api.py --confluence list-spaces --limit 50
python3 scripts/atlassian_api.py --confluence list-spaces --format json
```

### List Pages in Space
```bash
python3 scripts/atlassian_api.py --confluence list-pages --space TWXGBDL --limit 100
```

## CQL Reference (Confluence Query Language)

The skill uses CQL internally for search. Understanding CQL helps construct effective searches.

### Basic Syntax
```sql
field OPERATOR value [AND|OR field OPERATOR value]
```

### Common Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Exact match | `space = "TWXGBDL"` |
| `!=` | Not equals | `type != attachment` |
| `~` | Contains (fuzzy) | `title ~ "Container"` |
| `!~` | Not contains | `title !~ "draft"` |
| `>`, `<` | Greater/less than | `created > "2024-01-01"` |
| `>=`, `<=` | Greater/less or equal | `lastModified >= "-7d"` |
| `IN` | In list | `space IN ("TWXGBDL", "IT")` |
| `NOT IN` | Not in list | `type NOT IN (comment, attachment)` |

### Common Fields

| Field | Description | Example |
|-------|-------------|---------|
| `type` | Content type | `type = page` |
| `space` | Space key | `space = "TWXGBDL"` |
| `title` | Page title | `title ~ "API"` |
| `text` | Full content search | `text ~ "authentication"` |
| `creator` | Created by | `creator = "john@example.com"` |
| `contributor` | Edited by | `contributor = currentUser()` |
| `created` | Creation date | `created >= "2024-01-01"` |
| `lastModified` | Last update | `lastModified >= "-30d"` |
| `label` | Page labels | `label = "documentation"` |
| `parent` | Parent page ID | `parent = 123456789` |
| `ancestor` | Any ancestor | `ancestor = 123456789` |
| `id` | Content ID | `id = 3174662145` |

### Date Formats

| Format | Description | Example |
|--------|-------------|---------|
| `"YYYY-MM-DD"` | Absolute date | `created > "2024-06-01"` |
| `"-Nd"` | N days ago | `lastModified >= "-7d"` |
| `"-Nw"` | N weeks ago | `created >= "-2w"` |
| `"-Nm"` | N months ago | `lastModified >= "-1m"` |
| `"now"` | Current time | `created < "now"` |

### Common CQL Patterns

```sql
-- Search pages by title (fuzzy match)
type = page AND title ~ "Container"

-- Search in specific space
type = page AND space = "TWXGBDL" AND title ~ "API"

-- Recently modified pages
type = page AND lastModified >= "-7d" ORDER BY lastModified DESC

-- Pages with specific label
type = page AND label = "documentation"

-- Full text search (searches page content)
type = page AND text ~ "authentication error"

-- Pages created by user
type = page AND creator = "user@example.com"

-- Pages under a parent
type = page AND ancestor = 1821736961

-- Multiple conditions
type = page AND space = "TWXGBDL" AND title ~ "PRI" AND lastModified >= "-30d"

-- Exclude certain content
type = page AND space = "TWXGBDL" AND title !~ "Draft" AND title !~ "Archive"
```

### Content Types

| Type | Description |
|------|-------------|
| `page` | Standard pages |
| `blogpost` | Blog posts |
| `comment` | Page comments |
| `attachment` | File attachments |
| `space` | Space metadata |

## Common Space Keys

| Key | Name | Description |
|-----|------|-------------|
| TWXGBDL | TWXGB Documentation Library | Main documentation |
| TWXDEV | Development | Dev team space |
| IT | IT Department | IT documentation |

## Confluence Storage Format

Confluence uses XHTML-based storage format. Common elements:

```html
<!-- Headings -->
<h1>Heading 1</h1>
<h2>Heading 2</h2>

<!-- Paragraphs -->
<p>Paragraph text with <strong>bold</strong> and <em>italic</em>.</p>

<!-- Lists -->
<ul>
  <li>Bullet item</li>
</ul>
<ol>
  <li>Numbered item</li>
</ol>

<!-- Links -->
<a href="https://example.com">External link</a>
<ac:link><ri:page ri:content-title="Page Title" /></ac:link>

<!-- Code blocks -->
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">python</ac:parameter>
  <ac:plain-text-body><![CDATA[print("Hello")]]></ac:plain-text-body>
</ac:structured-macro>

<!-- Tables -->
<table>
  <tr><th>Header</th></tr>
  <tr><td>Cell</td></tr>
</table>

<!-- Mermaid diagrams (via code macro) -->
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">mermaid</ac:parameter>
  <ac:plain-text-body><![CDATA[
flowchart TD
    A --> B
  ]]></ac:plain-text-body>
</ac:structured-macro>
```

## API Endpoints Used

| Operation | Endpoint | Method |
|-----------|----------|--------|
| Search (CQL) | `/wiki/rest/api/content/search?cql=...` | GET |
| Get page | `/wiki/api/v2/pages/{id}` | GET |
| Create page | `/wiki/api/v2/pages` | POST |
| Update page | `/wiki/api/v2/pages/{id}` | PUT |
| List spaces | `/wiki/api/v2/spaces` | GET |
| List pages | `/wiki/api/v2/spaces/{id}/pages` | GET |

## Rate Limits

Confluence Cloud rate limits:
- **Standard**: 100 requests/minute per user
- **Burst**: Up to 200 requests in short bursts
- **Response header**: `X-RateLimit-Remaining`

The skill handles rate limiting with exponential backoff.

## Error Handling

| HTTP Code | Meaning | Solution |
|-----------|---------|----------|
| 401 | Unauthorized | Token expired, will auto-refresh |
| 403 | Forbidden | Missing scope, check OAuth permissions |
| 404 | Not found | Page/space doesn't exist |
| 429 | Rate limited | Wait and retry (handled automatically) |

## Tips

1. **Page IDs**: Get from URL (`/pages/123456789/`) or from search results
2. **Space IDs vs Keys**: Use keys (TWXGBDL) in commands, skill converts to IDs
3. **Content format**: Body must be Confluence storage format, not markdown
4. **Version messages**: Always include `--message` for update audit trail
5. **Parent pages**: Use `--parent` to create page hierarchy
6. **CQL escaping**: Quote values with spaces: `title ~ "User Guide"`
7. **Fuzzy vs exact**: Use `~` for contains/fuzzy, `=` for exact match
