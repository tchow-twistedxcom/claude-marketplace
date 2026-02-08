#!/usr/bin/env python3
"""
Atlassian API CLI

A command-line interface for Atlassian Confluence and Jira operations.
Designed for efficient context usage with Claude Code.

Usage:
    python3 atlassian_api.py --confluence search "query" [options]
    python3 atlassian_api.py --jira search "JQL" [options]

See --help for full documentation.
"""

import argparse
import json
import sys
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from auth import AtlassianAuth, AtlassianAuthError
from formatters import (
    format_confluence_pages, format_confluence_page_content, format_confluence_spaces,
    format_jira_issues, format_jira_issue_detail, format_jira_transitions,
    format_success, format_error, html_to_markdown
)
from md_to_confluence import md_to_confluence
from md_to_adf import md_to_adf

# API Base URLs
# v2 API for most operations (requires granular OAuth scopes)
CONFLUENCE_API_V2 = 'https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/api/v2'
# v1 API for CQL search (more flexible querying)
CONFLUENCE_API_V1 = 'https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/rest/api'
JIRA_API = 'https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3'

# Default timeout
DEFAULT_TIMEOUT = 30


class AtlassianClient:
    """
    HTTP client for Atlassian REST APIs.

    Handles:
    - Authentication via AtlassianAuth
    - Request/response formatting
    - Error handling with retries
    - Timeout management
    """

    def __init__(self, site=None, timeout=DEFAULT_TIMEOUT, verbose=False):
        self.auth = AtlassianAuth()
        self.site = site
        self.timeout = timeout
        self.verbose = verbose
        self.cloud_id = self.auth.get_cloud_id(site)
        self.domain = self.auth.get_domain(site)
        self._space_key_cache = {}  # Cache space key -> id mappings

    def _log(self, msg):
        """Log debug message if verbose."""
        if self.verbose:
            print(f"[DEBUG] {msg}", file=sys.stderr)

    def _format_http_error(self, status_code, error_msg):
        """
        Format HTTP error with helpful hints for common issues.

        Args:
            status_code: HTTP status code
            error_msg: Error message from response

        Returns:
            Formatted error string with hints
        """
        hints = {
            401: "\n  → Token may have expired. Run: python3 scripts/auth.py",
            403: "\n  → Missing OAuth scopes. Check app permissions at:\n"
                 "    https://developer.atlassian.com/console/myapps/",
            404: "\n  → Resource not found. Verify the page/issue ID is correct.",
            429: "\n  → Rate limited. Wait a moment and retry, or reduce request frequency.",
        }
        hint = hints.get(status_code, "")
        return f"HTTP {status_code}: {error_msg}{hint}"

    def _request(self, method, url, data=None):
        """
        Make authenticated HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            url: Full URL
            data: Optional request body (dict)

        Returns:
            Parsed JSON response
        """
        headers = self.auth.get_headers(self.site)

        body = None
        if data:
            body = json.dumps(data).encode('utf-8')

        self._log(f"{method} {url}")
        if body:
            self._log(f"Body: {body[:200]}...")

        req = Request(url, data=body, headers=headers, method=method)

        try:
            with urlopen(req, timeout=self.timeout) as response:
                response_body = response.read().decode('utf-8')
                if response_body:
                    return json.loads(response_body)
                return {}
        except HTTPError as e:
            error_body = e.read().decode('utf-8')
            try:
                error_json = json.loads(error_body)
                error_msg = error_json.get('message', error_json.get('errorMessages', [str(e)])[0] if isinstance(error_json.get('errorMessages'), list) else str(e))
            except (json.JSONDecodeError, KeyError, TypeError, IndexError):
                error_msg = error_body[:500] if error_body else str(e)
            raise Exception(self._format_http_error(e.code, error_msg))
        except URLError as e:
            raise Exception(f"Network error: {e}")

    def confluence_url(self, path):
        """Build Confluence v2 API URL."""
        return CONFLUENCE_API_V2.format(cloud_id=self.cloud_id) + path

    def confluence_url_v1(self, path):
        """Build Confluence v1 API URL (for CQL search)."""
        return CONFLUENCE_API_V1.format(cloud_id=self.cloud_id) + path

    def jira_url(self, path):
        """Build Jira API URL."""
        return JIRA_API.format(cloud_id=self.cloud_id) + path

    # =========================================================================
    # Confluence Operations (v2 API)
    # =========================================================================

    def confluence_search(self, query, limit=20, space_key=None):
        """
        Search Confluence pages by title using CQL (fuzzy/partial match).

        Uses v1 API with CQL for flexible search capabilities.
        Supports partial title matching and optional space filtering.

        Args:
            query: Search query (supports partial title match)
            limit: Maximum results to return
            space_key: Optional space key to restrict search

        Returns:
            List of page results normalized to v2 format
        """
        # Build CQL query for title search (~ operator for contains/fuzzy match)
        cql_parts = [f'title ~ "{query}"']
        if space_key:
            cql_parts.append(f'space = "{space_key}"')
        cql = ' AND '.join(cql_parts)

        params = {
            'cql': cql,
            'limit': limit,
            'expand': 'space,version'
        }
        url = self.confluence_url_v1(f'/content/search?{urlencode(params)}')
        result = self._request('GET', url)

        # Normalize v1 response to match formatter expectations
        pages = []
        for item in result.get('results', []):
            # Skip non-page content (attachments, comments, etc.)
            if item.get('type') != 'page':
                continue
            pages.append({
                'id': item.get('id'),
                'title': item.get('title'),
                'spaceKey': item.get('space', {}).get('key', ''),  # Used by formatter
                'space': item.get('space', {}),  # Keep full space object
                'version': item.get('version', {}),
                '_links': item.get('_links', {})
            })
        return pages

    def confluence_search_content(self, query, limit=20, space_id=None):
        """
        Search Confluence content using full-text search.

        Note: This requires the search:confluence scope which we may not have.
        Falls back to title search if not available.
        """
        # Try v2 content search endpoint
        params = {
            'query': query,
            'limit': limit
        }
        if space_id:
            params['spaceId'] = space_id

        try:
            url = self.confluence_url(f'/search?{urlencode(params)}')
            result = self._request('GET', url)
            return result.get('results', [])
        except Exception as e:
            if '401' in str(e) or '403' in str(e):
                # Fall back to title search
                self._log(f"Search not available, falling back to title search: {e}")
                return self.confluence_search(query, limit)
            raise

    def confluence_get_page(self, page_id, include_body=True):
        """Get Confluence page by ID using v2 API."""
        # v2 API: GET /pages/{id}
        params = {}
        if include_body:
            params['body-format'] = 'storage'

        query = f'?{urlencode(params)}' if params else ''
        url = self.confluence_url(f'/pages/{page_id}{query}')
        page = self._request('GET', url)

        # Also get version info (non-critical - continue without if it fails)
        version_url = self.confluence_url(f'/pages/{page_id}/versions?limit=1')
        try:
            versions = self._request('GET', version_url)
            if versions.get('results'):
                page['version'] = versions['results'][0]
        except Exception:
            # Version info is supplementary - don't fail the whole request
            pass

        return page

    def confluence_create_page(self, space_key, title, body, parent_id=None):
        """Create new Confluence page using v2 API."""
        # v2 API requires space ID, not key - look it up
        space_id = self._get_space_id(space_key)

        data = {
            'spaceId': space_id,
            'status': 'current',
            'title': title,
            'body': {
                'representation': 'storage',
                'value': body
            }
        }
        if parent_id:
            data['parentId'] = parent_id

        url = self.confluence_url('/pages')
        return self._request('POST', url, data)

    def confluence_update_page(self, page_id, body, title=None, version_msg=None):
        """Update existing Confluence page using v2 API."""
        # Get current page info for version
        current = self.confluence_get_page(page_id, include_body=False)
        current_version = current.get('version', {}).get('number', 1)
        current_title = current.get('title', 'Untitled')

        data = {
            'id': page_id,
            'status': 'current',
            'title': title or current_title,
            'body': {
                'representation': 'storage',
                'value': body
            },
            'version': {
                'number': current_version + 1
            }
        }

        if version_msg:
            data['version']['message'] = version_msg

        url = self.confluence_url(f'/pages/{page_id}')
        return self._request('PUT', url, data)

    def confluence_list_spaces(self, limit=50):
        """List Confluence spaces using v2 API."""
        url = self.confluence_url(f'/spaces?limit={limit}')
        result = self._request('GET', url)
        return result.get('results', [])

    def confluence_list_pages(self, space_key, limit=50):
        """List pages in a Confluence space using v2 API."""
        # v2 API requires space ID
        space_id = self._get_space_id(space_key)

        url = self.confluence_url(f'/spaces/{space_id}/pages?limit={limit}&body-format=storage')
        result = self._request('GET', url)
        return result.get('results', [])

    def confluence_get_space_by_key(self, space_key):
        """Get space info by key using v2 API."""
        # v2 API: filter spaces by key
        url = self.confluence_url(f'/spaces?keys={space_key}')
        result = self._request('GET', url)
        spaces = result.get('results', [])
        if spaces:
            return spaces[0]
        raise Exception(f"Space not found: {space_key}")

    def _get_space_id(self, space_key):
        """Get space ID from space key (with caching)."""
        if space_key in self._space_key_cache:
            return self._space_key_cache[space_key]

        space = self.confluence_get_space_by_key(space_key)
        space_id = space.get('id')
        if space_id:
            self._space_key_cache[space_key] = space_id
        return space_id

    def confluence_get_children(self, page_id, limit=50):
        """Get child pages of a Confluence page."""
        url = self.confluence_url(f'/pages/{page_id}/children?limit={limit}')
        result = self._request('GET', url)
        return result.get('results', [])

    def confluence_archive_page(self, page_id):
        """Archive a Confluence page (safer than delete - reversible)."""
        # Get current page info
        current = self.confluence_get_page(page_id, include_body=False)
        current_version = current.get('version', {}).get('number', 1)
        current_title = current.get('title', 'Untitled')

        # Update status to archived
        data = {
            'id': page_id,
            'status': 'archived',
            'title': current_title,
            'version': {
                'number': current_version + 1,
                'message': 'Archived via API'
            }
        }

        url = self.confluence_url(f'/pages/{page_id}')
        return self._request('PUT', url, data)

    def confluence_upload_attachment(self, page_id, file_path, comment=None):
        """
        Upload an attachment to a Confluence page.

        Uses v1 API as v2 attachment API requires different handling.
        """
        import mimetypes
        from urllib.request import Request, urlopen
        import uuid

        file_path = Path(file_path)
        if not file_path.exists():
            raise Exception(f"File not found: {file_path}")

        filename = file_path.name
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

        # Read file content
        with open(file_path, 'rb') as f:
            file_content = f.read()

        # Build multipart form data
        boundary = f'----WebKitFormBoundary{uuid.uuid4().hex[:16]}'

        body_parts = []

        # File part
        body_parts.append(f'--{boundary}'.encode())
        body_parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode())
        body_parts.append(f'Content-Type: {content_type}'.encode())
        body_parts.append(b'')
        body_parts.append(file_content)

        # Comment part (optional)
        if comment:
            body_parts.append(f'--{boundary}'.encode())
            body_parts.append(b'Content-Disposition: form-data; name="comment"')
            body_parts.append(b'')
            body_parts.append(comment.encode())

        body_parts.append(f'--{boundary}--'.encode())
        body_parts.append(b'')

        body = b'\r\n'.join(body_parts)

        # Use v1 API for attachments
        url = self.confluence_url_v1(f'/content/{page_id}/child/attachment')

        headers = self.auth.get_headers(self.site)
        headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
        headers['X-Atlassian-Token'] = 'nocheck'

        req = Request(url, data=body, headers=headers, method='POST')

        try:
            with urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"HTTP {e.code}: {error_body[:500]}")

    def confluence_list_attachments(self, page_id, limit=50):
        """List attachments on a Confluence page."""
        url = self.confluence_url_v1(f'/content/{page_id}/child/attachment?limit={limit}')
        result = self._request('GET', url)
        return result.get('results', [])

    # =========================================================================
    # Jira Operations
    # =========================================================================

    def jira_search(self, jql, limit=50, fields=None):
        """Search Jira issues using JQL (uses new /search/jql endpoint)."""
        if fields is None:
            fields = ['summary', 'status', 'issuetype', 'assignee', 'priority', 'updated', 'created']

        data = {
            'jql': jql,
            'maxResults': limit,
            'fields': fields
        }

        # Use new /search/jql endpoint (old /search was deprecated)
        url = self.jira_url('/search/jql')
        result = self._request('POST', url, data)
        return result.get('issues', [])

    def jira_get_issue(self, issue_key, fields=None):
        """Get Jira issue by key."""
        expand = 'transitions'
        url = self.jira_url(f'/issue/{issue_key}?expand={expand}')
        return self._request('GET', url)

    def jira_create_issue(self, project_key, issue_type, summary, description=None, fields=None):
        """Create new Jira issue."""
        data = {
            'fields': {
                'project': {'key': project_key},
                'issuetype': {'name': issue_type},
                'summary': summary
            }
        }

        if description:
            # Convert to Atlassian Document Format
            data['fields']['description'] = {
                'type': 'doc',
                'version': 1,
                'content': [{
                    'type': 'paragraph',
                    'content': [{'type': 'text', 'text': description}]
                }]
            }

        if fields:
            data['fields'].update(fields)

        url = self.jira_url('/issue')
        return self._request('POST', url, data)

    def jira_update_issue(self, issue_key, fields):
        """Update Jira issue fields."""
        data = {'fields': fields}
        url = self.jira_url(f'/issue/{issue_key}')
        return self._request('PUT', url, data)

    def jira_add_comment(self, issue_key, body, internal=False, mention_users=None, visibility_value=None, use_markdown=False):
        """
        Add comment to Jira issue.

        Args:
            issue_key: Issue key (e.g., "IT-20374")
            body: Comment text (plain text or markdown if use_markdown=True)
            internal: If True, restrict comment to internal users (default: False)
            mention_users: List of user account IDs or display names to mention (optional)
            visibility_value: Custom visibility restriction value (e.g., "Internal note", "Developers")
                             Format: "role:Administrators" or "group:Internal note"
                             If not specified, internal=True defaults to "role:Administrators"
            use_markdown: If True, parse body as markdown and convert to ADF (default: False)
        """
        # Build comment content
        if use_markdown:
            # Convert markdown to ADF
            adf_doc = md_to_adf(body)
            content = adf_doc.get('content', [])
        else:
            content = []

            # If mentions provided, add them at the start
            if mention_users:
                mention_content = []
                for user in mention_users:
                    # Try to resolve user display name to account ID
                    account_id = self._resolve_user_account_id(user, issue_key)
                    if account_id:
                        mention_content.append({'type': 'mention', 'attrs': {'id': account_id}})
                        mention_content.append({'type': 'text', 'text': ' '})
                    else:
                        # Fallback: just use display name in text
                        mention_content.append({'type': 'text', 'text': f'@{user} '})

                if mention_content:
                    content.append({
                        'type': 'paragraph',
                        'content': mention_content
                    })

            # Add main comment body
            # Split by newlines and create paragraph for each
            lines = body.split('\n')
            for line in lines:
                if line.strip():  # Skip empty lines
                    content.append({
                        'type': 'paragraph',
                        'content': [{'type': 'text', 'text': line}]
                    })
                else:
                    # Empty line = paragraph break
                    content.append({
                        'type': 'paragraph',
                        'content': []
                    })

        data = {
            'body': {
                'type': 'doc',
                'version': 1,
                'content': content
            }
        }

        # Add visibility for internal comments
        if visibility_value:
            # Parse visibility value if provided
            if ':' in visibility_value:
                vis_type, vis_value = visibility_value.split(':', 1)
            else:
                # Default to group if no prefix
                vis_type, vis_value = 'group', visibility_value

            data['visibility'] = {
                'type': vis_type,
                'value': vis_value
            }

        # Add Jira Service Desk internal/public flag
        # This controls JSD agent-only comments (shows as "Internal note" with lock icon)
        if internal:
            data['properties'] = [
                {
                    'key': 'sd.public.comment',
                    'value': {
                        'internal': True
                    }
                }
            ]

        url = self.jira_url(f'/issue/{issue_key}/comment')
        return self._request('POST', url, data)

    def _resolve_user_account_id(self, user_identifier, issue_key):
        """
        Resolve user display name or account ID to account ID.

        Args:
            user_identifier: Display name (e.g., "Daniel Yubeta") or account ID
            issue_key: Issue key for context

        Returns:
            Account ID string or None if not found
        """
        # If it looks like an account ID already (contains colons), return it
        if ':' in user_identifier:
            return user_identifier

        # Try to get issue details to find user account IDs
        try:
            issue = self.jira_get_issue(issue_key)

            # Check assignee
            assignee = issue.get('fields', {}).get('assignee')
            if assignee and assignee.get('displayName') == user_identifier:
                return assignee.get('accountId')

            # Check reporter
            reporter = issue.get('fields', {}).get('reporter')
            if reporter and reporter.get('displayName') == user_identifier:
                return reporter.get('accountId')

            # Search in watchers (if available)
            # Note: This requires additional API call and permissions

        except Exception as e:
            self._log(f"Could not resolve user '{user_identifier}': {e}")

        return None

    def jira_delete_comment(self, issue_key, comment_id):
        """Delete a comment from a Jira issue."""
        url = self.jira_url(f'/issue/{issue_key}/comment/{comment_id}')
        return self._request('DELETE', url)

    def jira_get_transitions(self, issue_key):
        """Get available transitions for issue."""
        url = self.jira_url(f'/issue/{issue_key}/transitions')
        result = self._request('GET', url)
        return result.get('transitions', [])

    def jira_transition_issue(self, issue_key, transition_name_or_id):
        """Transition issue to new status."""
        # Get available transitions
        transitions = self.jira_get_transitions(issue_key)

        # Find matching transition
        transition_id = None
        for t in transitions:
            if t['id'] == transition_name_or_id or t['name'].lower() == transition_name_or_id.lower():
                transition_id = t['id']
                break

        if not transition_id:
            available = ', '.join(f"{t['name']} ({t['id']})" for t in transitions)
            raise Exception(f"Transition not found: {transition_name_or_id}. Available: {available}")

        data = {'transition': {'id': transition_id}}
        url = self.jira_url(f'/issue/{issue_key}/transitions')
        return self._request('POST', url, data)

    def jira_list_projects(self, limit=50):
        """List Jira projects."""
        url = self.jira_url(f'/project/search?maxResults={limit}')
        result = self._request('GET', url)
        return result.get('values', [])

    def jira_list_issue_types(self, project_key=None):
        """List Jira issue types, optionally filtered by project."""
        if project_key:
            url = self.jira_url(f'/project/{project_key}')
            project = self._request('GET', url)
            return project.get('issueTypes', [])
        else:
            url = self.jira_url('/issuetype')
            return self._request('GET', url)


# =============================================================================
# CLI Commands
# =============================================================================

def cmd_confluence_search(client, args):
    """Handle: --confluence search"""
    pages = client.confluence_search(args.query, limit=args.limit, space_key=args.space)
    return format_confluence_pages(pages, args.format, args.limit, client.domain)


def cmd_confluence_get_page(client, args):
    """Handle: --confluence get-page"""
    page = client.confluence_get_page(args.page_id)
    return format_confluence_page_content(page, args.format, client.domain)


def cmd_confluence_create_page(client, args):
    """Handle: --confluence create-page"""
    # Read body from file or stdin
    if args.body_file:
        with open(args.body_file, 'r') as f:
            body = f.read()
    else:
        body = sys.stdin.read()

    # Convert markdown to Confluence format if specified
    if args.input_format == 'md':
        body = md_to_confluence(body)

    result = client.confluence_create_page(args.space, args.title, body, args.parent)
    return format_success(f"Page created: {result.get('id')}", {
        'id': result.get('id'),
        'title': result.get('title'),
        'url': f"https://{client.domain}/wiki/spaces/{args.space}/pages/{result.get('id')}"
    })


def cmd_confluence_update_page(client, args):
    """Handle: --confluence update-page"""
    # Read body from file or stdin
    if args.body_file:
        with open(args.body_file, 'r') as f:
            body = f.read()
    else:
        body = sys.stdin.read()

    # Convert markdown to Confluence format if specified
    if args.input_format == 'md':
        body = md_to_confluence(body)

    result = client.confluence_update_page(args.page_id, body, args.title, args.message)
    return format_success(f"Page updated: {result.get('id')}", {
        'id': result.get('id'),
        'version': result.get('version', {}).get('number')
    })


def cmd_confluence_list_spaces(client, args):
    """Handle: --confluence list-spaces"""
    spaces = client.confluence_list_spaces(args.limit)
    return format_confluence_spaces(spaces, args.format, args.limit, client.domain)


def cmd_confluence_list_pages(client, args):
    """Handle: --confluence list-pages"""
    pages = client.confluence_list_pages(args.space, args.limit)
    return format_confluence_pages(pages, args.format, args.limit, client.domain)


def cmd_confluence_get_children(client, args):
    """Handle: --confluence get-children"""
    children = client.confluence_get_children(args.page_id, args.limit)
    return format_confluence_pages(children, args.format, args.limit, client.domain)


def cmd_confluence_archive_page(client, args):
    """Handle: --confluence archive-page"""
    result = client.confluence_archive_page(args.page_id)
    return format_success(f"Page archived: {args.page_id}", {
        'id': args.page_id,
        'title': result.get('title'),
        'version': result.get('version', {}).get('number'),
        'status': 'archived'
    })


def cmd_confluence_upload_attachment(client, args):
    """Handle: --confluence upload-attachment"""
    result = client.confluence_upload_attachment(args.page_id, args.file, args.comment)
    attachments = result.get('results', [result]) if 'results' in result else [result]
    if attachments:
        att = attachments[0]
        return format_success(f"Attachment uploaded: {att.get('title', 'unknown')}", {
            'id': att.get('id'),
            'title': att.get('title'),
            'size': att.get('extensions', {}).get('fileSize')
        })
    return format_success("Attachment uploaded")


def cmd_confluence_list_attachments(client, args):
    """Handle: --confluence list-attachments"""
    attachments = client.confluence_list_attachments(args.page_id, args.limit)
    if args.format == 'json':
        return json.dumps(attachments, indent=2)

    lines = [f"Attachments on page {args.page_id}: {len(attachments)} item(s)"]
    lines.append(f"{'ID':<12} | {'Title':<40} | {'Size':<10} | {'Type':<20}")
    lines.append("-" * 90)
    for att in attachments:
        att_id = att.get('id', '')[:12]
        title = att.get('title', '')[:40]
        size = att.get('extensions', {}).get('fileSize', 0)
        size_str = f"{size/1024:.1f}KB" if size > 1024 else f"{size}B"
        media_type = att.get('extensions', {}).get('mediaType', '')[:20]
        lines.append(f"{att_id:<12} | {title:<40} | {size_str:<10} | {media_type:<20}")
    return '\n'.join(lines)


def cmd_jira_search(client, args):
    """Handle: --jira search"""
    issues = client.jira_search(args.jql, limit=args.limit)
    return format_jira_issues(issues, args.format, args.limit, client.domain)


def cmd_jira_get_issue(client, args):
    """Handle: --jira get-issue"""
    issue = client.jira_get_issue(args.issue_key)
    return format_jira_issue_detail(issue, args.format, client.domain)


def cmd_jira_create_issue(client, args):
    """Handle: --jira create-issue"""
    result = client.jira_create_issue(
        args.project, args.type, args.summary,
        description=args.description
    )
    return format_success(f"Issue created: {result.get('key')}", {
        'key': result.get('key'),
        'id': result.get('id'),
        'url': f"https://{client.domain}/browse/{result.get('key')}"
    })


def cmd_jira_update_issue(client, args):
    """Handle: --jira update-issue"""
    fields = json.loads(args.fields) if args.fields else {}
    client.jira_update_issue(args.issue_key, fields)
    return format_success(f"Issue updated: {args.issue_key}")


def cmd_jira_add_comment(client, args):
    """Handle: --jira add-comment"""
    # Parse mention users if provided (comma-separated)
    mention_users = None
    if args.mention:
        mention_users = [u.strip() for u in args.mention.split(',')]

    # Determine if using markdown format
    use_markdown = getattr(args, 'markdown', False)

    result = client.jira_add_comment(
        args.issue_key,
        args.body,
        internal=args.internal,
        mention_users=mention_users,
        visibility_value=args.visibility,
        use_markdown=use_markdown
    )

    # Build visibility description
    if args.visibility:
        visibility = f" (restricted: {args.visibility})"
    elif args.internal:
        visibility = " (internal)"
    else:
        visibility = ""

    mentions = f" mentioning {', '.join(mention_users)}" if mention_users else ""
    return format_success(f"Comment added to {args.issue_key}{visibility}{mentions}", {
        'id': result.get('id')
    })


def cmd_jira_delete_comment(client, args):
    """Handle: --jira delete-comment"""
    client.jira_delete_comment(args.issue_key, args.comment_id)
    return format_success(f"Comment {args.comment_id} deleted from {args.issue_key}")


def cmd_jira_transition(client, args):
    """Handle: --jira transition"""
    client.jira_transition_issue(args.issue_key, args.to)
    return format_success(f"Issue {args.issue_key} transitioned to: {args.to}")


def cmd_jira_transitions(client, args):
    """Handle: --jira transitions"""
    transitions = client.jira_get_transitions(args.issue_key)
    return format_jira_transitions(transitions, args.format)


def cmd_jira_list_projects(client, args):
    """Handle: --jira list-projects"""
    projects = client.jira_list_projects(args.limit)
    if args.format == 'json':
        return json.dumps(projects, indent=2)

    lines = [f"[{client.domain}] Jira Projects - {len(projects)} project(s)"]
    lines.append(f"{'Key':<12} | {'Name':<40} | {'Type':<15}")
    lines.append("-" * 72)
    for proj in projects:
        key = proj.get('key', '')[:12]
        name = proj.get('name', '')[:40]
        ptype = proj.get('projectTypeKey', '')[:15]
        lines.append(f"{key:<12} | {name:<40} | {ptype:<15}")
    return '\n'.join(lines)


def cmd_jira_list_issue_types(client, args):
    """Handle: --jira list-issue-types"""
    issue_types = client.jira_list_issue_types(args.project)
    if args.format == 'json':
        return json.dumps(issue_types, indent=2)

    header = f"for project {args.project}" if args.project else "(all)"
    lines = [f"[{client.domain}] Jira Issue Types {header} - {len(issue_types)} type(s)"]
    lines.append(f"{'ID':<8} | {'Name':<25} | {'Subtask':<8} | {'Description':<40}")
    lines.append("-" * 90)
    for it in issue_types:
        it_id = str(it.get('id', ''))[:8]
        name = it.get('name', '')[:25]
        subtask = 'Yes' if it.get('subtask') else 'No'
        desc = (it.get('description') or '')[:40]
        lines.append(f"{it_id:<8} | {name:<25} | {subtask:<8} | {desc:<40}")
    return '\n'.join(lines)


def cmd_list_sites(args):
    """Handle: --list-sites"""
    auth = AtlassianAuth()
    sites = auth.list_sites()
    lines = ["Available sites:"]
    for alias, name, domain in sites:
        lines.append(f"  {alias}: {name} ({domain})")
    return '\n'.join(lines)


# =============================================================================
# Main CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Atlassian Confluence and Jira CLI (v2 API)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Confluence
  %(prog)s --confluence search --query "PRI Container" --limit 10
  %(prog)s --confluence get-page --page-id 123456789 --format markdown
  %(prog)s --confluence create-page --space TWXGBDL --title "New Page" --body-file content.md
  %(prog)s --confluence list-spaces
  %(prog)s --confluence list-pages --space ID

  # Jira
  %(prog)s --jira search --jql "project = TWXDEV AND status = Open" --limit 20
  %(prog)s --jira get-issue --issue-key TWXDEV-123
  %(prog)s --jira create-issue --project TWXDEV --type Task --summary "New task"
  %(prog)s --jira add-comment --issue-key TWXDEV-123 --body "Regular comment"
  %(prog)s --jira add-comment --issue-key TWXDEV-123 --body "Internal" --internal
  %(prog)s --jira add-comment --issue-key TWXDEV-123 --body "Team only" --visibility "group:Internal note"
  %(prog)s --jira add-comment --issue-key TWXDEV-123 --body "Hi team" --mention "Daniel Yubeta,John Doe"
  %(prog)s --jira transition --issue-key TWXDEV-123 --to "Done"
"""
    )

    # Global options
    parser.add_argument('--site', '-s', help='Site alias (default: from config)')
    parser.add_argument('--format', '-f', choices=['table', 'json', 'csv', 'markdown', 'storage'],
                       default='table', help='Output format (default: table). storage=raw Confluence XHTML')
    parser.add_argument('--limit', '-l', type=int, default=20,
                       help='Max results (default: 20)')
    parser.add_argument('--timeout', '-t', type=int, default=DEFAULT_TIMEOUT,
                       help=f'Request timeout seconds (default: {DEFAULT_TIMEOUT})')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show debug info')
    parser.add_argument('--list-sites', action='store_true',
                       help='List available sites')

    # Confluence subcommands
    confluence_group = parser.add_argument_group('Confluence')
    confluence_group.add_argument('--confluence', metavar='COMMAND',
                                  choices=['search', 'get-page', 'create-page', 'update-page', 'archive-page',
                                           'list-spaces', 'list-pages', 'get-children',
                                           'upload-attachment', 'list-attachments'],
                                  help='Confluence command')

    # Confluence arguments
    parser.add_argument('--query', '-q', help='Search query (for search)')
    parser.add_argument('--page-id', help='Page ID (for get-page, update-page, archive-page, get-children, attachments)')
    parser.add_argument('--space', help='Space key (for create-page, list-pages)')
    parser.add_argument('--title', help='Page title (for create-page)')
    parser.add_argument('--body-file', help='File with page body content')
    parser.add_argument('--parent', help='Parent page ID (for create-page)')
    parser.add_argument('--message', help='Version message (for update-page)')
    parser.add_argument('--file', help='File path (for upload-attachment)')
    parser.add_argument('--comment', help='Attachment comment (for upload-attachment)')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without saving (for update-page)')
    parser.add_argument('--input-format', choices=['html', 'md'], default='html',
                       help='Input format for body content: html (default) or md (markdown, auto-converted)')

    # Jira subcommands
    jira_group = parser.add_argument_group('Jira')
    jira_group.add_argument('--jira', metavar='COMMAND',
                           choices=['search', 'get-issue', 'create-issue', 'update-issue', 'add-comment',
                                    'delete-comment', 'transition', 'transitions', 'list-projects', 'list-issue-types'],
                           help='Jira command')

    # Jira arguments
    parser.add_argument('--jql', help='JQL query (for search)')
    parser.add_argument('--issue-key', help='Issue key (for get-issue, update-issue, etc.)')
    parser.add_argument('--project', help='Project key (for create-issue)')
    parser.add_argument('--type', help='Issue type (for create-issue)')
    parser.add_argument('--summary', help='Issue summary (for create-issue)')
    parser.add_argument('--description', help='Issue description (for create-issue)')
    parser.add_argument('--fields', help='JSON fields (for update-issue)')
    parser.add_argument('--body', help='Comment body (for add-comment)')
    parser.add_argument('--internal', action='store_true', help='Make comment internal/restricted to Administrators (for add-comment)')
    parser.add_argument('--visibility', help='Custom visibility restriction: "group:Name" or "role:Name" (for add-comment)')
    parser.add_argument('--mention', help='Comma-separated user names or account IDs to mention (for add-comment)')
    parser.add_argument('--markdown', action='store_true', help='Parse comment body as markdown and convert to rich ADF format (for add-comment)')
    parser.add_argument('--comment-id', help='Comment ID (for delete-comment)')
    parser.add_argument('--to', help='Target status/transition (for transition)')

    args = parser.parse_args()

    # Handle --list-sites
    if args.list_sites:
        print(cmd_list_sites(args))
        return 0

    # Validate command
    if not args.confluence and not args.jira:
        parser.print_help()
        return 1

    try:
        client = AtlassianClient(args.site, args.timeout, args.verbose)

        # Route to appropriate command handler
        if args.confluence:
            if args.confluence == 'search':
                if not args.query:
                    raise Exception("--query required for search")
                result = cmd_confluence_search(client, args)
            elif args.confluence == 'get-page':
                if not args.page_id:
                    raise Exception("--page-id required for get-page")
                result = cmd_confluence_get_page(client, args)
            elif args.confluence == 'create-page':
                if not args.space or not args.title:
                    raise Exception("--space and --title required for create-page")
                result = cmd_confluence_create_page(client, args)
            elif args.confluence == 'update-page':
                if not args.page_id:
                    raise Exception("--page-id required for update-page")
                if args.dry_run:
                    # Dry-run: show what would be updated without saving
                    if args.body_file:
                        with open(args.body_file, 'r') as f:
                            body = f.read()
                    else:
                        body = sys.stdin.read()
                    # Apply markdown conversion if specified
                    input_fmt = args.input_format
                    if input_fmt == 'md':
                        body = md_to_confluence(body)
                    current = client.confluence_get_page(args.page_id, include_body=False)
                    result = format_success(f"[DRY-RUN] Would update page: {args.page_id}", {
                        'id': args.page_id,
                        'title': args.title or current.get('title'),
                        'current_version': current.get('version', {}).get('number'),
                        'new_version': current.get('version', {}).get('number', 0) + 1,
                        'body_length': len(body),
                        'input_format': input_fmt
                    })
                else:
                    result = cmd_confluence_update_page(client, args)
            elif args.confluence == 'archive-page':
                if not args.page_id:
                    raise Exception("--page-id required for archive-page")
                result = cmd_confluence_archive_page(client, args)
            elif args.confluence == 'list-spaces':
                result = cmd_confluence_list_spaces(client, args)
            elif args.confluence == 'list-pages':
                if not args.space:
                    raise Exception("--space required for list-pages")
                result = cmd_confluence_list_pages(client, args)
            elif args.confluence == 'get-children':
                if not args.page_id:
                    raise Exception("--page-id required for get-children")
                result = cmd_confluence_get_children(client, args)
            elif args.confluence == 'upload-attachment':
                if not args.page_id or not args.file:
                    raise Exception("--page-id and --file required for upload-attachment")
                result = cmd_confluence_upload_attachment(client, args)
            elif args.confluence == 'list-attachments':
                if not args.page_id:
                    raise Exception("--page-id required for list-attachments")
                result = cmd_confluence_list_attachments(client, args)

        elif args.jira:
            if args.jira == 'search':
                if not args.jql:
                    raise Exception("--jql required for search")
                result = cmd_jira_search(client, args)
            elif args.jira == 'get-issue':
                if not args.issue_key:
                    raise Exception("--issue-key required for get-issue")
                result = cmd_jira_get_issue(client, args)
            elif args.jira == 'create-issue':
                if not args.project or not args.type or not args.summary:
                    raise Exception("--project, --type, and --summary required for create-issue")
                result = cmd_jira_create_issue(client, args)
            elif args.jira == 'update-issue':
                if not args.issue_key:
                    raise Exception("--issue-key required for update-issue")
                result = cmd_jira_update_issue(client, args)
            elif args.jira == 'add-comment':
                if not args.issue_key or not args.body:
                    raise Exception("--issue-key and --body required for add-comment")
                result = cmd_jira_add_comment(client, args)
            elif args.jira == 'delete-comment':
                if not args.issue_key or not args.comment_id:
                    raise Exception("--issue-key and --comment-id required for delete-comment")
                result = cmd_jira_delete_comment(client, args)
            elif args.jira == 'transition':
                if not args.issue_key or not args.to:
                    raise Exception("--issue-key and --to required for transition")
                result = cmd_jira_transition(client, args)
            elif args.jira == 'transitions':
                if not args.issue_key:
                    raise Exception("--issue-key required for transitions")
                result = cmd_jira_transitions(client, args)
            elif args.jira == 'list-projects':
                result = cmd_jira_list_projects(client, args)
            elif args.jira == 'list-issue-types':
                result = cmd_jira_list_issue_types(client, args)

        print(result)
        return 0

    except AtlassianAuthError as e:
        print(format_error("Authentication failed", str(e)), file=sys.stderr)
        return 1
    except Exception as e:
        print(format_error("Operation failed", str(e)), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
