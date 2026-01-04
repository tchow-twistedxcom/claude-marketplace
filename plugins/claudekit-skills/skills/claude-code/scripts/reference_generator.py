#!/usr/bin/env python3
"""
Reference Generator for Claude Code Skill Auto-Update

Transforms fetched documentation into reference files.
Full replacement mode - regenerates entirely from GitHub docs mirror.

Source: github.com/ericbuess/claude-code-docs
"""

import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional


# Reference file to source mapping
# Keys are doc filenames from github_docs (e.g., "overview.md")
REFERENCE_SOURCES = {
    "tool-selection.md": {
        "sources": ["overview.md", "cli-reference.md"],
        "description": "Native tool decision matrices",
        "sections": ["tools", "commands", "usage"]
    },
    "agent-catalog.md": {
        "sources": ["sub-agents.md"],
        "description": "30+ specialized agents by use case",
        "sections": ["agents", "subagents", "types"]
    },
    "mcp-guide.md": {
        "sources": ["mcp.md"],
        "description": "MCP server selection and configuration",
        "sections": ["mcp", "servers", "configuration"]
    },
    "hooks-reference.md": {
        "sources": ["hooks.md", "hooks-guide.md"],
        "description": "Hooks system reference",
        "sections": ["hooks", "events", "automation"]
    },
    "workflows.md": {
        "sources": ["common-workflows.md"],
        "description": "Common workflow patterns",
        "sections": ["workflows", "patterns", "debugging"]
    },
    "cli-reference.md": {
        "sources": ["cli-reference.md"],
        "description": "CLI flags and commands",
        "sections": ["cli", "flags", "commands"]
    },
    "enterprise.md": {
        "sources": ["third-party-integrations.md", "security.md"],
        "description": "Enterprise deployment guide",
        "sections": ["enterprise", "security", "integrations"]
    }
}

# GitHub mirror base URL
GITHUB_MIRROR_BASE = "https://github.com/ericbuess/claude-code-docs/blob/main/docs"


@dataclass
class ReferenceFile:
    """Generated reference file."""
    name: str
    content: str
    source_urls: List[str]
    generation_date: str


class ReferenceGenerator:
    """
    Generates reference files from GitHub documentation mirror.

    Mode: Full replace - regenerates entirely from official docs.
    """

    def __init__(self, skill_dir: Path):
        self.skill_dir = Path(skill_dir)
        self.references_dir = self.skill_dir / 'references'
        self.skill_md_path = self.skill_dir / 'SKILL.md'

    def regenerate_all(self, content: Dict[str, Any]) -> List[ReferenceFile]:
        """
        Regenerate all reference files from fetched content.

        Args:
            content: Dict with:
                - github_docs: {filename: {content, etag, hash}}
                - changelog: {content, etag, hash, version}

        Returns:
            List of generated ReferenceFile objects
        """
        docs_content = content.get('github_docs', {})
        generated = []

        for ref_file, config in REFERENCE_SOURCES.items():
            sources = config['sources']
            description = config['description']

            # Collect content from all sources
            source_contents = []
            source_urls = []

            for source in sources:
                if source in docs_content:
                    source_contents.append(docs_content[source].get('content', ''))
                    source_urls.append(f"{GITHUB_MIRROR_BASE}/{source}")

            if source_contents:
                # Transform content
                transformed = self._transform_content(
                    source_contents,
                    ref_file,
                    description
                )

                ref = ReferenceFile(
                    name=ref_file,
                    content=transformed,
                    source_urls=source_urls,
                    generation_date=datetime.now(timezone.utc).isoformat()
                )

                # Write file
                self._atomic_write(ref_file, transformed)
                generated.append(ref)

        return generated

    def _transform_content(
        self,
        source_contents: List[str],
        ref_file: str,
        description: str
    ) -> str:
        """
        Transform source content into reference format.

        For now, combines content with header and metadata.
        Future: Could add parsing, extraction, restructuring.
        """
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        # Format title from filename
        title = ref_file.replace('.md', '').replace('-', ' ').title()

        # Build header
        header = f"""# {title}

> {description}

*Auto-generated from Claude Code documentation on {now}*
*Source: github.com/ericbuess/claude-code-docs*

---

"""

        # Combine source contents
        combined = '\n\n---\n\n'.join(
            content for content in source_contents if content
        )

        # Clean up content
        cleaned = self._clean_content(combined)

        return header + cleaned

    def _clean_content(self, content: str) -> str:
        """Clean and normalize content."""
        if not content:
            return ''

        # Remove multiple consecutive blank lines
        content = re.sub(r'\n{3,}', '\n\n', content)

        # Ensure proper line endings
        content = content.replace('\r\n', '\n')

        # Strip trailing whitespace from lines
        lines = [line.rstrip() for line in content.split('\n')]
        content = '\n'.join(lines)

        return content.strip()

    def _atomic_write(self, filename: str, content: str):
        """
        Atomically write file using temp file + rename pattern.

        Ensures file is never corrupted even on crash.
        """
        target_path = self.references_dir / filename

        # Ensure directory exists
        self.references_dir.mkdir(parents=True, exist_ok=True)

        # Write to temp file first
        fd, temp_path = tempfile.mkstemp(
            suffix='.md',
            prefix=f'.{filename}_',
            dir=self.references_dir
        )

        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)
                if not content.endswith('\n'):
                    f.write('\n')

            # Atomic rename
            os.replace(temp_path, target_path)

        except Exception:
            # Clean up temp file on failure
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    def update_skill_md_timestamp(self):
        """Update 'Last updated' line in SKILL.md."""
        if not self.skill_md_path.exists():
            return

        try:
            with open(self.skill_md_path, 'r', encoding='utf-8') as f:
                content = f.read()

            now = datetime.now(timezone.utc).strftime('%Y-%m-%d')

            # Update or add last updated line
            patterns = [
                (r'\*Last updated:.*?\*', f'*Last updated: {now}*'),
                (r'Last updated:.*', f'Last updated: {now}'),
            ]

            updated = False
            for pattern, replacement in patterns:
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                    updated = True
                    break

            if not updated:
                # Add after first heading
                match = re.search(r'^#[^#].*$', content, re.MULTILINE)
                if match:
                    insert_pos = match.end()
                    content = (
                        content[:insert_pos] +
                        f'\n\n*Last updated: {now}*\n' +
                        content[insert_pos:]
                    )

            self._atomic_write_path(self.skill_md_path, content)

        except IOError:
            pass

    def _atomic_write_path(self, path: Path, content: str):
        """Atomic write to arbitrary path."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        fd, temp_path = tempfile.mkstemp(
            suffix=path.suffix,
            prefix=f'.{path.stem}_',
            dir=path.parent
        )

        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)
                if not content.endswith('\n'):
                    f.write('\n')

            os.replace(temp_path, path)

        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise


if __name__ == '__main__':
    # Quick test
    skill_dir = Path(__file__).parent.parent
    gen = ReferenceGenerator(skill_dir)

    print(f"Skill dir: {skill_dir}")
    print(f"References dir: {gen.references_dir}")
    print(f"SKILL.md path: {gen.skill_md_path}")

    print("\nReference sources:")
    for ref, config in REFERENCE_SOURCES.items():
        print(f"  {ref}: {config['sources']}")
