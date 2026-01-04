#!/usr/bin/env python3
"""
Claude Code Skill Auto-Updater

Main orchestrator implementing stale-while-revalidate pattern for
minimal latency skill activation with background updates.

Usage:
    # Fast path - called on skill activation (< 50ms)
    python3 skill_autoupdate.py --check

    # Force immediate update (blocking)
    python3 skill_autoupdate.py --update

    # Background refresh (internal, spawned by --check)
    python3 skill_autoupdate.py --background-refresh

    # Show current status
    python3 skill_autoupdate.py --status
"""

import argparse
import json
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Add scripts directory to path for imports
SCRIPTS_DIR = Path(__file__).parent
SKILL_DIR = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))

from cache_manager import CacheManager
from source_fetchers import VersionDetector, GitHubDocsMirrorFetcher, ChangelogFetcher


def get_skill_version() -> str:
    """Read current skill version from skill.json."""
    skill_json = SKILL_DIR / 'skill.json'
    try:
        with open(skill_json, 'r') as f:
            data = json.load(f)
            return data.get('version', '0.0.0')
    except (IOError, json.JSONDecodeError):
        return '0.0.0'


def update_skill_version(new_version: str) -> bool:
    """Update version in skill.json."""
    skill_json = SKILL_DIR / 'skill.json'
    try:
        with open(skill_json, 'r') as f:
            data = json.load(f)

        data['version'] = new_version

        with open(skill_json, 'w') as f:
            json.dump(data, f, indent=2)
            f.write('\n')

        return True
    except (IOError, json.JSONDecodeError):
        return False


def handle_activation_check() -> int:
    """
    Fast path for skill activation.

    Time budget: <50ms

    Steps:
    1. Load cache (10ms)
    2. Check freshness (1ms)
    3. If stale, spawn background process (10ms)
    4. Check for pending update notification
    5. Return immediately
    """
    cache = CacheManager()

    # Check for pending update to notify user
    update_info = cache.get_pending_update_info()
    if update_info:
        print(f"\n✨ Update available: v{update_info['version']}")
        print("   Run: python3 skill_autoupdate.py --update")
        cache.mark_notified(update_info['version'])

    if cache.is_fresh():
        # Cache valid, nothing to do
        return 0

    if cache.is_stale_but_usable() or not cache.entry.last_checked_utc:
        # Spawn background refresh, don't block
        spawn_background_refresh()

    return 0


def spawn_background_refresh():
    """Spawn detached background process for update check."""
    script = Path(__file__).resolve()

    # Use nohup-style detached process
    try:
        subprocess.Popen(
            [sys.executable, str(script), '--background-refresh'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            cwd=str(SKILL_DIR)
        )
    except Exception as e:
        # Silently fail - don't block activation
        pass


def handle_background_refresh() -> int:
    """
    Background update process.

    Steps:
    1. Acquire lock (prevent parallel updates)
    2. Check sources for changes
    3. If changes detected, set update_available flag
    4. Update cache
    5. Release lock
    """
    cache = CacheManager()

    # Try to acquire lock
    if not cache.acquire_update_lock():
        # Another update in progress
        return 0

    try:
        detector = VersionDetector()

        # Check for changes (HEAD requests only - fast)
        result = detector.detect_changes(cache.entry.sources)

        if result['has_changes']:
            # Determine new version
            current_version = get_skill_version()
            major, minor, patch = map(int, current_version.split('.'))

            # Bump patch version for detected changes
            new_version = f"{major}.{minor}.{patch + 1}"

            cache.set_update_available(
                version=new_version,
                changelog=f"Updated from: {', '.join(result['changed_sources'])}"
            )

        # Update source states in cache
        for source, state in result['source_states'].items():
            cache.update_source_state(source, state)

        # Update last checked timestamp
        cache.update_last_checked()
        cache.clear_errors()

    except Exception as e:
        cache.record_error(str(e))

    finally:
        cache.release_update_lock()

    return 0


def handle_force_update() -> int:
    """
    Force immediate update with full content sync.

    Blocks until complete.
    """
    print("Checking for updates...")

    cache = CacheManager()
    detector = VersionDetector()

    # Check for changes first
    print("  Checking sources...")
    result = detector.detect_changes(cache.entry.sources)

    if not result['has_changes'] and not cache.entry.update_available:
        print("  No updates available. Skill is up to date.")
        cache.update_last_checked()
        return 0

    print(f"  Changes detected in: {', '.join(result['changed_sources'])}")
    print("  Fetching content...")

    # Fetch all content
    content = detector.fetch_all_content()

    # Import and run reference generator
    try:
        from reference_generator import ReferenceGenerator

        generator = ReferenceGenerator(SKILL_DIR)

        print("  Regenerating references...")
        generator.regenerate_all(content)

        # Determine new version - prefer detected from changelog
        current_version = get_skill_version()
        new_version = None

        if 'changelog' in content and content['changelog'].get('version'):
            detected_version = content['changelog']['version']
            print(f"  Detected Claude Code version: {detected_version}")
            new_version = detected_version
        else:
            # Fallback: bump patch version
            major, minor, patch = map(int, current_version.split('.'))
            new_version = f"{major}.{minor}.{patch + 1}"

        print(f"  Updating version: {current_version} → {new_version}")
        update_skill_version(new_version)

        # Update SKILL.md timestamp
        generator.update_skill_md_timestamp()

        # Clear update flag and update cache
        cache.clear_update_available()
        for source, state in result['source_states'].items():
            cache.update_source_state(source, state)
        cache.update_last_checked()
        cache.clear_errors()

        print(f"\n✅ Successfully updated to v{new_version}")

    except ImportError:
        print("  Warning: reference_generator not available. Skipping content sync.")
        cache.update_last_checked()

    except Exception as e:
        print(f"\n❌ Update failed: {e}")
        cache.record_error(str(e))
        return 1

    return 0


def handle_status() -> int:
    """Show current cache and update status."""
    cache = CacheManager()
    entry = cache.entry

    print("Claude Code Skill Auto-Update Status")
    print("=" * 40)
    print(f"Skill Version: {get_skill_version()}")
    print(f"Cache Fresh: {cache.is_fresh()}")
    print(f"Cache Stale but Usable: {cache.is_stale_but_usable()}")
    print(f"Last Checked: {entry.last_checked_utc or 'Never'}")
    print(f"Update Available: {entry.update_available}")

    if entry.update_available:
        print(f"  Pending Version: {entry.pending_version}")
        print(f"  Changelog: {entry.pending_changelog}")

    print(f"Update in Progress: {entry.update_in_progress}")
    print(f"Error Count: {entry.error_count}")

    if entry.last_error:
        print(f"Last Error: {entry.last_error}")

    print("\nSource States:")
    for source, state in entry.sources.items():
        print(f"  {source}:")
        for key, value in state.items():
            print(f"    {key}: {value}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Claude Code Skill Auto-Updater',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --check              Quick check on skill activation
  %(prog)s --update             Force immediate update
  %(prog)s --status             Show current status
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true',
                       help='Quick cache check (for hook activation)')
    group.add_argument('--update', action='store_true',
                       help='Force full update now')
    group.add_argument('--background-refresh', action='store_true',
                       help='Run background refresh (internal)')
    group.add_argument('--status', action='store_true',
                       help='Show current status')

    args = parser.parse_args()

    if args.check:
        return handle_activation_check()
    elif args.update:
        return handle_force_update()
    elif args.background_refresh:
        return handle_background_refresh()
    elif args.status:
        return handle_status()


if __name__ == '__main__':
    sys.exit(main())
