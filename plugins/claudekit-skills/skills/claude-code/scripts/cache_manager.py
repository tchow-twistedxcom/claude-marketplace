#!/usr/bin/env python3
"""
Cache Manager for Claude Code Skill Auto-Update

Implements stale-while-revalidate caching pattern.
Pattern inspired by: atlassian-skills/scripts/auth.py

Key guarantees:
- Reads complete in <10ms (no network)
- Stale content served immediately if available
- Background refresh doesn't block activation
"""

import json
import os
import time
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone


# Cache file location (relative to skill directory)
CACHE_PATH = Path(__file__).parent.parent / 'config' / '.update_cache.json'

# Cache TTL settings
CACHE_TTL_HOURS = 6       # Check every 6 hours
STALE_TTL_DAYS = 7        # Max stale before forcing refresh
LOCK_TIMEOUT_SECONDS = 300  # 5 minute lock timeout


@dataclass
class SourceState:
    """State for a single documentation source."""
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    content_hash: Optional[str] = None
    checked_utc: Optional[str] = None


@dataclass
class CacheEntry:
    """Complete cache state."""
    schema_version: int = 1
    skill_version: str = "2.0.0"
    last_checked_utc: Optional[str] = None
    sources: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    update_available: bool = False
    pending_version: Optional[str] = None
    pending_changelog: Optional[str] = None
    notified_version: Optional[str] = None
    update_in_progress: bool = False
    lock_acquired_utc: Optional[str] = None
    last_error: Optional[str] = None
    error_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """Create from dictionary."""
        return cls(
            schema_version=data.get('schema_version', 1),
            skill_version=data.get('skill_version', '2.0.0'),
            last_checked_utc=data.get('last_checked_utc'),
            sources=data.get('sources', {}),
            update_available=data.get('update_available', False),
            pending_version=data.get('pending_version'),
            pending_changelog=data.get('pending_changelog'),
            notified_version=data.get('notified_version'),
            update_in_progress=data.get('update_in_progress', False),
            lock_acquired_utc=data.get('lock_acquired_utc'),
            last_error=data.get('last_error'),
            error_count=data.get('error_count', 0)
        )


class CacheManager:
    """
    Stale-while-revalidate cache implementation.

    Usage:
        cache = CacheManager()

        # Fast path check
        if cache.is_fresh():
            return  # Nothing to do

        # Stale but usable - trigger background refresh
        if cache.is_stale_but_usable():
            spawn_background_refresh()
            return
    """

    def __init__(self, cache_path: Path = None):
        """Initialize cache manager."""
        self.cache_path = cache_path or CACHE_PATH
        self._entry: Optional[CacheEntry] = None

    @property
    def entry(self) -> CacheEntry:
        """Get current cache entry, loading from disk if needed."""
        if self._entry is None:
            self._entry = self._load_cache()
        return self._entry

    def _load_cache(self) -> CacheEntry:
        """Load cache from disk."""
        if not self.cache_path.exists():
            return CacheEntry()

        try:
            with open(self.cache_path, 'r') as f:
                data = json.load(f)
                return CacheEntry.from_dict(data)
        except (json.JSONDecodeError, IOError) as e:
            # Corrupted cache - start fresh
            return CacheEntry()

    def _save_cache(self, entry: CacheEntry) -> bool:
        """
        Atomically save cache to disk.

        Uses temp file + rename pattern for atomic writes.
        """
        try:
            # Ensure directory exists
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to temp file first
            fd, temp_path = tempfile.mkstemp(
                suffix='.json',
                prefix='.update_cache_',
                dir=self.cache_path.parent
            )

            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(entry.to_dict(), f, indent=2)

                # Atomic rename
                os.replace(temp_path, self.cache_path)
                self._entry = entry
                return True
            except Exception:
                # Clean up temp file on failure
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise

        except Exception as e:
            return False

    def is_fresh(self) -> bool:
        """
        Check if cache is within TTL (no refresh needed).

        Returns True if last check was within CACHE_TTL_HOURS.
        """
        if not self.entry.last_checked_utc:
            return False

        try:
            last_check = datetime.fromisoformat(self.entry.last_checked_utc.replace('Z', '+00:00'))
            age_hours = (datetime.now(timezone.utc) - last_check).total_seconds() / 3600
            return age_hours < CACHE_TTL_HOURS
        except (ValueError, TypeError):
            return False

    def is_stale_but_usable(self) -> bool:
        """
        Check if cache is expired but within stale window.

        Returns True if older than TTL but within STALE_TTL_DAYS.
        """
        if not self.entry.last_checked_utc:
            return False

        try:
            last_check = datetime.fromisoformat(self.entry.last_checked_utc.replace('Z', '+00:00'))
            age_days = (datetime.now(timezone.utc) - last_check).total_seconds() / 86400
            age_hours = age_days * 24

            # Stale if past TTL but within stale window
            return age_hours >= CACHE_TTL_HOURS and age_days < STALE_TTL_DAYS
        except (ValueError, TypeError):
            return False

    def needs_refresh(self) -> bool:
        """Check if cache needs any kind of refresh."""
        return not self.is_fresh()

    def acquire_update_lock(self) -> bool:
        """
        Acquire update lock to prevent parallel updates.

        Returns True if lock acquired, False if already locked.
        """
        entry = self.entry

        # Check for stale lock
        if entry.update_in_progress and entry.lock_acquired_utc:
            try:
                lock_time = datetime.fromisoformat(entry.lock_acquired_utc.replace('Z', '+00:00'))
                lock_age = (datetime.now(timezone.utc) - lock_time).total_seconds()
                if lock_age > LOCK_TIMEOUT_SECONDS:
                    # Stale lock - can acquire
                    pass
                else:
                    # Active lock
                    return False
            except (ValueError, TypeError):
                pass
        elif entry.update_in_progress:
            return False

        # Acquire lock
        entry.update_in_progress = True
        entry.lock_acquired_utc = datetime.now(timezone.utc).isoformat()
        return self._save_cache(entry)

    def release_update_lock(self):
        """Release update lock."""
        entry = self.entry
        entry.update_in_progress = False
        entry.lock_acquired_utc = None
        self._save_cache(entry)

    def update_last_checked(self):
        """Update last checked timestamp."""
        entry = self.entry
        entry.last_checked_utc = datetime.now(timezone.utc).isoformat()
        self._save_cache(entry)

    def update_source_state(self, source_name: str, state: Dict[str, Any]):
        """Update state for a specific source."""
        entry = self.entry
        entry.sources[source_name] = {
            **state,
            'checked_utc': datetime.now(timezone.utc).isoformat()
        }
        self._save_cache(entry)

    def set_update_available(self, version: str, changelog: str = None):
        """Mark that an update is available."""
        entry = self.entry
        entry.update_available = True
        entry.pending_version = version
        entry.pending_changelog = changelog
        self._save_cache(entry)

    def clear_update_available(self):
        """Clear update available flag (after update applied)."""
        entry = self.entry
        entry.update_available = False
        entry.pending_version = None
        entry.pending_changelog = None
        entry.notified_version = None
        self._save_cache(entry)

    def mark_notified(self, version: str):
        """Mark that user has been notified about this version."""
        entry = self.entry
        entry.notified_version = version
        self._save_cache(entry)

    def should_notify_user(self) -> bool:
        """Check if user should be notified about available update."""
        entry = self.entry
        return (
            entry.update_available and
            entry.pending_version and
            entry.pending_version != entry.notified_version
        )

    def get_pending_update_info(self) -> Optional[Dict[str, str]]:
        """Get info about pending update for user notification."""
        if not self.should_notify_user():
            return None

        entry = self.entry
        return {
            'version': entry.pending_version,
            'changelog': entry.pending_changelog
        }

    def record_error(self, error: str):
        """Record an error and increment error count."""
        entry = self.entry
        entry.last_error = error
        entry.error_count += 1
        self._save_cache(entry)

    def clear_errors(self):
        """Clear error state after successful operation."""
        entry = self.entry
        entry.last_error = None
        entry.error_count = 0
        self._save_cache(entry)

    def get_source_etag(self, source_name: str) -> Optional[str]:
        """Get cached ETag for a source (for conditional GET)."""
        source = self.entry.sources.get(source_name, {})
        return source.get('etag')

    def get_source_last_modified(self, source_name: str) -> Optional[str]:
        """Get cached Last-Modified for a source."""
        source = self.entry.sources.get(source_name, {})
        return source.get('last_modified')


if __name__ == '__main__':
    # Quick test
    cache = CacheManager()
    print(f"Fresh: {cache.is_fresh()}")
    print(f"Stale but usable: {cache.is_stale_but_usable()}")
    print(f"Cache entry: {cache.entry.to_dict()}")
