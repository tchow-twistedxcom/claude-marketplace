#!/usr/bin/env python3
"""
Response Formatting Module for Atlassian API

Provides efficient output formatting to minimize context usage:
- Table format: ASCII tables with truncation (default)
- JSON format: Simplified JSON with selected fields
- CSV format: Comma-separated for data export
- Markdown format: For page content

Key efficiency features:
- Field selection (only essential fields)
- Row limiting (default 20)
- Value truncation (40 chars max for table)
- Metadata headers (minimal context overhead)
"""

import json
import html
import re
from datetime import datetime


# Default limits
DEFAULT_LIMIT = 20
MAX_COLUMN_WIDTH = 40
MAX_CONTENT_PREVIEW = 200


def truncate(text, max_length=MAX_COLUMN_WIDTH):
    """Truncate text with ellipsis if too long."""
    if text is None:
        return ''
    text = str(text)
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + '...'


def format_date(date_str):
    """Format ISO date string to YYYY-MM-DD."""
    if not date_str:
        return ''
    try:
        # Handle various ISO formats
        if 'T' in date_str:
            date_str = date_str.split('T')[0]
        return date_str[:10]
    except:
        return str(date_str)[:10]


def html_to_text(html_content):
    """Convert HTML to plain text."""
    if not html_content:
        return ''
    # Remove tags
    text = re.sub(r'<[^>]+>', ' ', html_content)
    # Decode entities
    text = html.unescape(text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def html_to_markdown(html_content):
    """
    Convert Confluence storage format HTML to markdown.

    Simple conversion for common elements.
    """
    if not html_content:
        return ''

    text = html_content

    # Headers
    for i in range(6, 0, -1):
        text = re.sub(rf'<h{i}[^>]*>(.*?)</h{i}>', r'\n' + '#' * i + r' \1\n', text, flags=re.DOTALL)

    # Bold and italic
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text, flags=re.DOTALL)
    text = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', text, flags=re.DOTALL)

    # Links
    text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL)

    # Lists
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', text, flags=re.DOTALL)
    text = re.sub(r'<[ou]l[^>]*>', '\n', text)
    text = re.sub(r'</[ou]l>', '\n', text)

    # Paragraphs and breaks
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', text, flags=re.DOTALL)
    text = re.sub(r'<br\s*/?>', '\n', text)

    # Code blocks - extract language parameter if present
    def replace_code_block(match):
        """Replace code macro with markdown code block, preserving language."""
        full_match = match.group(0)
        code_content = match.group(1)
        # Try to extract language parameter
        lang_match = re.search(r'<ac:parameter[^>]*ac:name="language"[^>]*>([^<]+)</ac:parameter>', full_match)
        lang = lang_match.group(1) if lang_match else ''
        return f'\n```{lang}\n{code_content}\n```\n'

    text = re.sub(r'<ac:structured-macro[^>]*ac:name="code"[^>]*>.*?<ac:plain-text-body><!\[CDATA\[(.*?)\]\]></ac:plain-text-body>.*?</ac:structured-macro>',
                  replace_code_block, text, flags=re.DOTALL)

    # Remove remaining tags
    text = re.sub(r'<[^>]+>', '', text)

    # Decode entities
    text = html.unescape(text)

    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


def format_table(rows, columns, header=None):
    """
    Format rows as ASCII table.

    Args:
        rows: List of dicts with row data
        columns: List of (key, header, width) tuples
        header: Optional header line

    Returns:
        Formatted table string
    """
    if not rows:
        return header + '\nNo results found.' if header else 'No results found.'

    # Build header row
    col_widths = [min(w, MAX_COLUMN_WIDTH) for _, _, w in columns]
    headers = [h for _, h, _ in columns]

    lines = []
    if header:
        lines.append(header)

    # Header line
    header_line = ' | '.join(h.ljust(w)[:w] for h, w in zip(headers, col_widths))
    lines.append(header_line)

    # Separator
    sep_line = '-+-'.join('-' * w for w in col_widths)
    lines.append(sep_line)

    # Data rows
    for row in rows:
        values = []
        for key, _, width in columns:
            val = row.get(key, '')
            val = truncate(str(val), width)
            values.append(val.ljust(width)[:width])
        lines.append(' | '.join(values))

    return '\n'.join(lines)


# =============================================================================
# Confluence Formatters
# =============================================================================

def format_confluence_pages(pages, format='table', limit=DEFAULT_LIMIT, domain=''):
    """
    Format Confluence page list.

    Args:
        pages: List of page objects from API
        format: Output format (table, json, csv)
        limit: Max results
        domain: Site domain for URLs

    Returns:
        Formatted string
    """
    if not pages:
        return 'No pages found.'

    pages = pages[:limit]

    # Extract essential fields (handle both v1 and v2 API formats)
    simplified = []
    for p in pages:
        # v1 API has space.key, v2 has spaceId (need to look up key) or _links
        space_key = p.get('space', {}).get('key', '') or p.get('spaceKey', '')
        # v2 API: try to get space key from _links.webui (format: /spaces/KEY/pages/...)
        if not space_key and '_links' in p:
            webui = p.get('_links', {}).get('webui', '')
            if '/spaces/' in webui:
                parts = webui.split('/spaces/')
                if len(parts) > 1:
                    space_key = parts[1].split('/')[0]

        # v1 API has version.when, v2 API has version.createdAt or page-level createdAt
        version_info = p.get('version', {})
        updated = version_info.get('when', '') or version_info.get('createdAt', '') or p.get('createdAt', '') or p.get('lastModified', '')

        simplified.append({
            'id': p.get('id', ''),
            'title': p.get('title', ''),
            'space': space_key,
            'updated': format_date(updated),
            'url': f"https://{domain}/wiki/spaces/{space_key}/pages/{p.get('id', '')}" if domain and space_key else ''
        })

    if format == 'json':
        return json.dumps(simplified, indent=2)

    elif format == 'csv':
        lines = ['id,title,space,updated,url']
        for row in simplified:
            values = [
                str(row['id']),
                f'"{row["title"]}"',
                row['space'],
                row['updated'],
                row['url']
            ]
            lines.append(','.join(values))
        return '\n'.join(lines)

    else:  # table
        header = f"[{domain}] Confluence - {len(simplified)} page(s)"
        columns = [
            ('id', 'ID', 12),
            ('title', 'Title', 40),
            ('space', 'Space', 10),
            ('updated', 'Updated', 12)
        ]
        return format_table(simplified, columns, header)


def format_confluence_page_content(page, format='markdown', domain=''):
    """
    Format single Confluence page with content.

    Args:
        page: Page object from API with body
        format: Output format (markdown, json, html)
        domain: Site domain for header

    Returns:
        Formatted string
    """
    if not page:
        return 'Page not found.'

    # Extract metadata (handle both v1 and v2 API formats)
    page_id = page.get('id', '')
    title = page.get('title', 'Untitled')

    # v1 API has space.key, v2 has spaceId or _links
    space = page.get('space', {}).get('key', '') or page.get('spaceKey', '')
    # v2 API: try to get space key from _links.webui
    if not space and '_links' in page:
        webui = page.get('_links', {}).get('webui', '')
        if '/spaces/' in webui:
            parts = webui.split('/spaces/')
            if len(parts) > 1:
                space = parts[1].split('/')[0]

    # v1 API has version.number and version.when
    # v2 API has version.number and version.createdAt (or page-level createdAt)
    version_info = page.get('version', {})
    version = version_info.get('number', '?')
    updated = format_date(version_info.get('when', '') or version_info.get('createdAt', '') or page.get('createdAt', ''))

    # v1 API has version.by.displayName, v2 has version.authorId (not displayName)
    author = version_info.get('by', {}).get('displayName', '') or version_info.get('authorId', '')

    # Get body content
    # v1 API: body.storage.value
    # v2 API: body.storage.value (same structure when body-format=storage requested)
    body = page.get('body', {})
    storage = body.get('storage', {}).get('value', '')
    view = body.get('view', {}).get('value', '')

    content = storage or view or ''

    if format == 'json':
        return json.dumps({
            'id': page_id,
            'title': title,
            'space': space,
            'version': version,
            'updated': updated,
            'author': author,
            'body_storage': content,  # Raw Confluence storage format (XHTML)
            'body_markdown': html_to_markdown(content)  # Converted to markdown
        }, indent=2)

    elif format in ('html', 'storage'):
        # Return raw Confluence storage format (XHTML)
        header = f"<!-- Page: {title} (ID: {page_id}) | Space: {space} | v{version} -->\n"
        return header + content

    else:  # markdown (default)
        md_content = html_to_markdown(content)
        header = f"# {title}\n\n"
        header += f"**Page ID**: {page_id} | **Space**: {space} | **Version**: {version}\n"
        header += f"**Updated**: {updated} by {author}\n\n"
        header += "---\n\n"
        return header + md_content


def format_confluence_spaces(spaces, format='table', limit=DEFAULT_LIMIT, domain=''):
    """Format Confluence space list."""
    if not spaces:
        return 'No spaces found.'

    spaces = spaces[:limit]

    simplified = []
    for s in spaces:
        simplified.append({
            'key': s.get('key', ''),
            'name': s.get('name', ''),
            'type': s.get('type', ''),
            'status': s.get('status', 'current')
        })

    if format == 'json':
        return json.dumps(simplified, indent=2)

    elif format == 'csv':
        lines = ['key,name,type,status']
        for row in simplified:
            lines.append(f"{row['key']},\"{row['name']}\",{row['type']},{row['status']}")
        return '\n'.join(lines)

    else:  # table
        header = f"[{domain}] Confluence Spaces - {len(simplified)} space(s)"
        columns = [
            ('key', 'Key', 15),
            ('name', 'Name', 40),
            ('type', 'Type', 12),
            ('status', 'Status', 10)
        ]
        return format_table(simplified, columns, header)


# =============================================================================
# Jira Formatters
# =============================================================================

def format_jira_issues(issues, format='table', limit=DEFAULT_LIMIT, domain=''):
    """
    Format Jira issue list.

    Args:
        issues: List of issue objects from API
        format: Output format (table, json, csv)
        limit: Max results
        domain: Site domain for URLs

    Returns:
        Formatted string
    """
    if not issues:
        return 'No issues found.'

    issues = issues[:limit]

    simplified = []
    for issue in issues:
        fields = issue.get('fields', {})
        simplified.append({
            'key': issue.get('key', ''),
            'summary': fields.get('summary', ''),
            'status': fields.get('status', {}).get('name', ''),
            'type': fields.get('issuetype', {}).get('name', ''),
            'assignee': (fields.get('assignee') or {}).get('displayName', 'Unassigned'),
            'priority': (fields.get('priority') or {}).get('name', ''),
            'updated': format_date(fields.get('updated', ''))
        })

    if format == 'json':
        return json.dumps(simplified, indent=2)

    elif format == 'csv':
        lines = ['key,summary,status,type,assignee,priority,updated']
        for row in simplified:
            values = [
                row['key'],
                f'"{row["summary"]}"',
                row['status'],
                row['type'],
                f'"{row["assignee"]}"',
                row['priority'],
                row['updated']
            ]
            lines.append(','.join(values))
        return '\n'.join(lines)

    else:  # table
        header = f"[{domain}] Jira - {len(simplified)} issue(s)"
        columns = [
            ('key', 'Key', 12),
            ('summary', 'Summary', 35),
            ('status', 'Status', 12),
            ('type', 'Type', 10),
            ('assignee', 'Assignee', 15)
        ]
        return format_table(simplified, columns, header)


def format_jira_issue_detail(issue, format='table', domain=''):
    """
    Format single Jira issue with full details.

    Args:
        issue: Issue object from API
        format: Output format (table, json, markdown)
        domain: Site domain

    Returns:
        Formatted string
    """
    if not issue:
        return 'Issue not found.'

    fields = issue.get('fields', {})

    detail = {
        'key': issue.get('key', ''),
        'summary': fields.get('summary', ''),
        'description': fields.get('description', '') or '',
        'status': fields.get('status', {}).get('name', ''),
        'type': fields.get('issuetype', {}).get('name', ''),
        'priority': (fields.get('priority') or {}).get('name', ''),
        'assignee': (fields.get('assignee') or {}).get('displayName', 'Unassigned'),
        'reporter': (fields.get('reporter') or {}).get('displayName', ''),
        'project': fields.get('project', {}).get('key', ''),
        'created': format_date(fields.get('created', '')),
        'updated': format_date(fields.get('updated', '')),
        'labels': fields.get('labels', []),
        'components': [c.get('name', '') for c in fields.get('components', [])]
    }

    if format == 'json':
        return json.dumps(detail, indent=2)

    else:  # markdown/table
        lines = [
            f"# [{detail['key']}] {detail['summary']}",
            "",
            f"**Status**: {detail['status']} | **Type**: {detail['type']} | **Priority**: {detail['priority']}",
            f"**Project**: {detail['project']} | **Assignee**: {detail['assignee']} | **Reporter**: {detail['reporter']}",
            f"**Created**: {detail['created']} | **Updated**: {detail['updated']}",
        ]

        if detail['labels']:
            lines.append(f"**Labels**: {', '.join(detail['labels'])}")
        if detail['components']:
            lines.append(f"**Components**: {', '.join(detail['components'])}")

        lines.append("")
        lines.append("## Description")
        lines.append("")
        lines.append(detail['description'] or '*No description*')

        return '\n'.join(lines)


def format_jira_transitions(transitions, format='table'):
    """Format available issue transitions."""
    if not transitions:
        return 'No transitions available.'

    simplified = []
    for t in transitions:
        simplified.append({
            'id': t.get('id', ''),
            'name': t.get('name', ''),
            'to_status': t.get('to', {}).get('name', '')
        })

    if format == 'json':
        return json.dumps(simplified, indent=2)

    else:  # table
        columns = [
            ('id', 'ID', 8),
            ('name', 'Transition', 25),
            ('to_status', 'To Status', 20)
        ]
        return format_table(simplified, columns, "Available Transitions")


# =============================================================================
# Generic Formatters
# =============================================================================

def format_success(message, data=None):
    """Format success message."""
    result = f"SUCCESS: {message}"
    if data:
        result += f"\n{json.dumps(data, indent=2)}"
    return result


def format_error(message, details=None):
    """Format error message."""
    result = f"ERROR: {message}"
    if details:
        result += f"\nDetails: {details}"
    return result


if __name__ == '__main__':
    # Test formatters
    print("Testing formatters...")

    # Test page list
    test_pages = [
        {'id': '123', 'title': 'Test Page', 'spaceKey': 'TEST', 'version': {'when': '2025-01-15T10:00:00Z'}},
        {'id': '456', 'title': 'Another Very Long Page Title That Should Be Truncated', 'spaceKey': 'TEST', 'version': {'when': '2025-01-14T10:00:00Z'}}
    ]
    print("\n--- Table Format ---")
    print(format_confluence_pages(test_pages, 'table', domain='test.atlassian.net'))

    print("\n--- JSON Format ---")
    print(format_confluence_pages(test_pages, 'json', limit=1))

    print("\nFormatters OK!")
