#!/usr/bin/env python3
"""
Source Fetchers for Claude Code Skill Auto-Update

HTTP clients for each documentation source with:
- Conditional GET support (ETag/Last-Modified)
- Retry logic with exponential backoff
- Rate limit handling
- GitHub raw content fetching

Sources:
- GitHub Mirror: ericbuess/claude-code-docs (updated every 3 hours)
- Official Changelog: anthropics/claude-code/CHANGELOG.md

Pattern inspired by: celigo-integration/scripts/celigo_api.py
"""

import hashlib
import time
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# Default settings (can be overridden by sources.json)
DEFAULT_TIMEOUT = 15
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2

# User agent for requests
USER_AGENT = 'ClaudeCodeSkillUpdater/1.0'


@dataclass
class FetchResult:
    """Result of a fetch operation."""
    success: bool
    status_code: int = 0
    content: Optional[str] = None
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    content_hash: Optional[str] = None
    error: Optional[str] = None
    not_modified: bool = False  # 304 response

    def compute_hash(self) -> str:
        """Compute SHA256 hash of content."""
        if self.content:
            self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()
        return self.content_hash or ''


class SourceFetcher:
    """Base fetcher with retry logic and conditional GET support."""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout

    def _make_request(
        self,
        url: str,
        method: str = 'GET',
        headers: Dict[str, str] = None,
        if_none_match: str = None,
        if_modified_since: str = None
    ) -> FetchResult:
        """
        Make HTTP request with retry logic.

        Supports conditional GET via If-None-Match and If-Modified-Since headers.
        """
        req_headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/plain, text/markdown, application/json'
        }

        if headers:
            req_headers.update(headers)

        if if_none_match:
            req_headers['If-None-Match'] = if_none_match

        if if_modified_since:
            req_headers['If-Modified-Since'] = if_modified_since

        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                req = Request(url, headers=req_headers, method=method)

                with urlopen(req, timeout=self.timeout) as response:
                    content = response.read().decode('utf-8') if method == 'GET' else None
                    etag = response.headers.get('ETag')
                    last_modified = response.headers.get('Last-Modified')

                    result = FetchResult(
                        success=True,
                        status_code=response.status,
                        content=content,
                        etag=etag,
                        last_modified=last_modified
                    )

                    if content:
                        result.compute_hash()

                    return result

            except HTTPError as e:
                if e.code == 304:
                    # Not Modified - content unchanged
                    return FetchResult(
                        success=True,
                        status_code=304,
                        not_modified=True
                    )

                if e.code == 429:
                    # Rate limited - respect Retry-After
                    retry_after = e.headers.get('Retry-After', str(RETRY_BACKOFF_BASE ** attempt * 60))
                    try:
                        wait = int(retry_after)
                    except ValueError:
                        wait = RETRY_BACKOFF_BASE ** attempt * 60

                    if attempt < MAX_RETRIES - 1:
                        time.sleep(min(wait, 120))  # Cap at 2 minutes
                        continue

                last_error = f"HTTP {e.code}: {e.reason}"

            except URLError as e:
                last_error = f"URL Error: {e.reason}"

            except TimeoutError:
                last_error = "Request timeout"

            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"

            # Exponential backoff before retry
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_BASE ** attempt)

        return FetchResult(
            success=False,
            error=last_error
        )

    def fetch(self, url: str, cached_etag: str = None, cached_last_modified: str = None) -> FetchResult:
        """Fetch URL with conditional GET support."""
        return self._make_request(
            url,
            method='GET',
            if_none_match=cached_etag,
            if_modified_since=cached_last_modified
        )

    def head(self, url: str) -> FetchResult:
        """HEAD request to check for changes without downloading."""
        return self._make_request(url, method='HEAD')


class GitHubDocsMirrorFetcher(SourceFetcher):
    """
    Fetches documentation from the ericbuess/claude-code-docs GitHub mirror.

    This mirror is updated every 3 hours and contains 61+ markdown files
    with the full Claude Code documentation in raw markdown format.
    """

    REPO = "ericbuess/claude-code-docs"
    BRANCH = "main"
    BASE_RAW_URL = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"
    API_URL = f"https://api.github.com/repos/{REPO}/contents/docs"

    # Core documentation files to fetch
    CORE_DOCS = [
        "overview.md",
        "cli-reference.md",
        "sub-agents.md",
        "mcp.md",
        "hooks.md",
        "hooks-guide.md",
        "common-workflows.md",
        "settings.md",
        "skills.md",
        "plugins.md",
        "plugins-reference.md",
        "memory.md",
        "third-party-integrations.md",
        "security.md",
        "troubleshooting.md",
    ]

    def get_doc_url(self, filename: str) -> str:
        """Get raw URL for a documentation file."""
        return f"{self.BASE_RAW_URL}/docs/{filename}"

    def fetch_doc(self, filename: str, cached_etag: str = None) -> FetchResult:
        """Fetch a specific documentation file."""
        url = self.get_doc_url(filename)
        return self.fetch(url, cached_etag=cached_etag)

    def check_doc(self, filename: str) -> FetchResult:
        """Check if a specific doc has changed (HEAD request)."""
        url = self.get_doc_url(filename)
        return self.head(url)

    def list_docs(self) -> FetchResult:
        """Get list of all documentation files via GitHub API."""
        result = self.fetch(self.API_URL)
        if result.success and result.content:
            try:
                import json
                files = json.loads(result.content)
                doc_files = [f['name'] for f in files if f['name'].endswith('.md')]
                result.content = json.dumps(doc_files)
            except Exception as e:
                result.error = f"Failed to parse file list: {e}"
        return result

    def fetch_core_docs(self, cached_states: Dict[str, str] = None) -> Dict[str, FetchResult]:
        """Fetch all core documentation files."""
        cached_states = cached_states or {}
        results = {}
        for doc in self.CORE_DOCS:
            cached_etag = cached_states.get(doc)
            results[doc] = self.fetch_doc(doc, cached_etag=cached_etag)
        return results

    def check_for_updates(self, cached_etag: str = None) -> FetchResult:
        """Check if docs have changed by checking the overview file."""
        return self.check_doc("overview.md")


class ChangelogFetcher(SourceFetcher):
    """
    Fetches CHANGELOG.md from the official anthropics/claude-code repo.

    This is the authoritative source for version numbers and release notes.
    """

    CHANGELOG_URL = "https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md"

    def fetch_changelog(self, cached_etag: str = None) -> FetchResult:
        """Fetch the changelog file."""
        return self.fetch(self.CHANGELOG_URL, cached_etag=cached_etag)

    def check_changelog(self) -> FetchResult:
        """Check if changelog has changed (HEAD request)."""
        return self.head(self.CHANGELOG_URL)

    def extract_latest_version(self, content: str) -> Optional[str]:
        """
        Extract the latest version from changelog content.

        Looks for patterns like:
        - ## 2.0.74
        - ## [2.0.74]
        - ## Version 2.0.74
        """
        patterns = [
            r'^##\s*\[?v?(\d+\.\d+\.\d+)\]?',  # ## 2.0.74 or ## [2.0.74]
            r'^##\s*Version\s+v?(\d+\.\d+\.\d+)',  # ## Version 2.0.74
            r'^\*\*Version\s+v?(\d+\.\d+\.\d+)\*\*',  # **Version 2.0.74**
        ]

        for line in content.split('\n')[:100]:  # Check first 100 lines
            for pattern in patterns:
                match = re.match(pattern, line.strip(), re.IGNORECASE)
                if match:
                    return match.group(1)

        return None

    def extract_versions(self, content: str, limit: int = 10) -> List[str]:
        """Extract multiple versions from changelog (for comparison)."""
        versions = []
        pattern = r'^##\s*\[?v?(\d+\.\d+\.\d+)\]?'

        for line in content.split('\n'):
            match = re.match(pattern, line.strip())
            if match:
                versions.append(match.group(1))
                if len(versions) >= limit:
                    break

        return versions


class VersionDetector:
    """
    Detects version changes across multiple sources.

    Uses:
    - GitHub docs mirror for documentation changes
    - Official changelog for version detection
    - ETag/Last-Modified for efficient change detection
    - Content hash for verification
    """

    def __init__(self):
        self.docs_fetcher = GitHubDocsMirrorFetcher()
        self.changelog_fetcher = ChangelogFetcher()

    def detect_changes(
        self,
        cached_sources: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check all sources for changes.

        Args:
            cached_sources: Dict of source name -> cached state (etag, hash, etc.)

        Returns:
            Dict with:
                - has_changes: bool
                - changed_sources: list of source names that changed
                - source_states: new states for each source
                - latest_version: detected version from changelog
        """
        changed_sources = []
        source_states = {}
        latest_version = None

        # Check changelog for version changes
        changelog_cached = cached_sources.get('changelog', {})
        changelog_result = self.changelog_fetcher.check_changelog()

        if changelog_result.success:
            if changelog_result.etag != changelog_cached.get('etag'):
                changed_sources.append('changelog')

            source_states['changelog'] = {
                'etag': changelog_result.etag,
                'last_modified': changelog_result.last_modified
            }

        # Check GitHub docs mirror
        docs_cached = cached_sources.get('github_docs', {})
        docs_result = self.docs_fetcher.check_for_updates()

        if docs_result.success:
            if docs_result.etag != docs_cached.get('etag'):
                changed_sources.append('github_docs')

            source_states['github_docs'] = {
                'etag': docs_result.etag,
                'last_modified': docs_result.last_modified
            }

        return {
            'has_changes': len(changed_sources) > 0,
            'changed_sources': changed_sources,
            'source_states': source_states,
            'latest_version': latest_version
        }

    def fetch_all_content(self) -> Dict[str, Any]:
        """
        Fetch all content for full regeneration.

        Returns dict of source name -> content.
        """
        content = {}

        # Fetch changelog
        changelog_result = self.changelog_fetcher.fetch_changelog()
        if changelog_result.success:
            latest_version = self.changelog_fetcher.extract_latest_version(
                changelog_result.content
            )
            content['changelog'] = {
                'content': changelog_result.content,
                'etag': changelog_result.etag,
                'hash': changelog_result.content_hash,
                'version': latest_version
            }

        # Fetch all core documentation files
        docs_results = self.docs_fetcher.fetch_core_docs()
        content['github_docs'] = {}

        for doc, result in docs_results.items():
            if result.success:
                content['github_docs'][doc] = {
                    'content': result.content,
                    'etag': result.etag,
                    'hash': result.content_hash
                }

        return content

    def get_latest_version(self) -> Optional[str]:
        """Get the latest version from the changelog."""
        result = self.changelog_fetcher.fetch_changelog()
        if result.success and result.content:
            return self.changelog_fetcher.extract_latest_version(result.content)
        return None


if __name__ == '__main__':
    # Quick test
    print("Testing source fetchers...")
    print("-" * 50)

    # Test changelog fetcher
    print("\n1. Testing Changelog Fetcher:")
    changelog = ChangelogFetcher()
    result = changelog.check_changelog()
    print(f"   HEAD request: success={result.success}, etag={result.etag[:30] if result.etag else None}...")

    result = changelog.fetch_changelog()
    if result.success:
        version = changelog.extract_latest_version(result.content)
        print(f"   Latest version: {version}")
        versions = changelog.extract_versions(result.content, limit=5)
        print(f"   Recent versions: {versions}")
    else:
        print(f"   Error: {result.error}")

    # Test GitHub docs mirror
    print("\n2. Testing GitHub Docs Mirror Fetcher:")
    docs = GitHubDocsMirrorFetcher()
    result = docs.check_for_updates()
    print(f"   HEAD request: success={result.success}, etag={result.etag[:30] if result.etag else None}...")

    result = docs.fetch_doc("overview.md")
    if result.success:
        print(f"   overview.md: {len(result.content)} bytes, hash={result.content_hash[:16]}...")
    else:
        print(f"   Error: {result.error}")

    # Test version detector
    print("\n3. Testing Version Detector:")
    detector = VersionDetector()
    version = detector.get_latest_version()
    print(f"   Detected version: {version}")

    changes = detector.detect_changes({})
    print(f"   Changes detected: {changes['has_changes']}")
    print(f"   Changed sources: {changes['changed_sources']}")

    print("\n" + "-" * 50)
    print("Tests complete!")
