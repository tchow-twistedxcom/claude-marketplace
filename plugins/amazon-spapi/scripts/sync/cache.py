"""
Cache Manager
=============

Disk-based caching for expensive data to avoid repeated API calls.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default cache directory (relative to sync module)
DEFAULT_CACHE_DIR = Path(__file__).parent / "cache"

# Cache TTL defaults (in seconds)
CANONICAL_INDEX_TTL = 24 * 60 * 60  # 24 hours
ASSET_INDEX_TTL = 1 * 60 * 60  # 1 hour
SKU_INDEX_TTL = 0  # Session-only (no TTL)


class CacheManager:
    """
    Manages disk-based caching for expensive data.

    Cache files:
    - canonical_index.json: Product identifier → ID mappings
    - asset_filenames.json: Filename → Asset ID mappings
    - sku_index.json: SKU → Product ID mappings
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize cache manager.

        Args:
            cache_dir: Optional custom cache directory
        """
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, name: str) -> Path:
        """Get path to cache file."""
        return self.cache_dir / f"{name}.json"

    def _get_meta_path(self, name: str) -> Path:
        """Get path to cache metadata file."""
        return self.cache_dir / f"{name}.meta.json"

    def is_valid(self, name: str, ttl: int = 0) -> bool:
        """
        Check if cache is valid (exists and not expired).

        Args:
            name: Cache name
            ttl: Time-to-live in seconds (0 = no expiry)

        Returns:
            True if cache is valid
        """
        cache_path = self._get_cache_path(name)
        meta_path = self._get_meta_path(name)

        if not cache_path.exists():
            return False

        # No TTL means always valid if exists
        if ttl == 0:
            return True

        # Check metadata for creation time
        if meta_path.exists():
            try:
                with open(meta_path, 'r') as f:
                    meta = json.load(f)
                    created = meta.get('created', 0)
                    return (time.time() - created) < ttl
            except Exception:
                pass

        # Fall back to file modification time
        try:
            mtime = cache_path.stat().st_mtime
            return (time.time() - mtime) < ttl
        except Exception:
            return False

    def load(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Load cache from disk.

        Args:
            name: Cache name

        Returns:
            Cached data or None
        """
        cache_path = self._get_cache_path(name)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
                logger.debug(f"Loaded cache '{name}': {len(data)} entries")
                return data
        except Exception as e:
            logger.warning(f"Failed to load cache '{name}': {e}")
            return None

    def save(self, name: str, data: Dict[str, Any]) -> bool:
        """
        Save data to cache.

        Args:
            name: Cache name
            data: Data to cache

        Returns:
            True if saved successfully
        """
        cache_path = self._get_cache_path(name)
        meta_path = self._get_meta_path(name)

        try:
            # Save data
            with open(cache_path, 'w') as f:
                json.dump(data, f)

            # Save metadata
            meta = {
                'created': time.time(),
                'created_at': datetime.now().isoformat(),
                'entries': len(data),
            }
            with open(meta_path, 'w') as f:
                json.dump(meta, f)

            logger.debug(f"Saved cache '{name}': {len(data)} entries")
            return True

        except Exception as e:
            logger.warning(f"Failed to save cache '{name}': {e}")
            return False

    def invalidate(self, name: str) -> bool:
        """
        Invalidate (delete) a cache.

        Args:
            name: Cache name

        Returns:
            True if invalidated
        """
        cache_path = self._get_cache_path(name)
        meta_path = self._get_meta_path(name)

        try:
            if cache_path.exists():
                cache_path.unlink()
            if meta_path.exists():
                meta_path.unlink()
            logger.debug(f"Invalidated cache '{name}'")
            return True
        except Exception as e:
            logger.warning(f"Failed to invalidate cache '{name}': {e}")
            return False

    def invalidate_all(self) -> None:
        """Invalidate all caches."""
        for path in self.cache_dir.glob("*.json"):
            try:
                path.unlink()
            except Exception:
                pass

    def get_cache_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a cache.

        Args:
            name: Cache name

        Returns:
            Cache info dict or None
        """
        meta_path = self._get_meta_path(name)
        cache_path = self._get_cache_path(name)

        if not cache_path.exists():
            return None

        info = {
            'name': name,
            'path': str(cache_path),
            'size_bytes': cache_path.stat().st_size,
        }

        if meta_path.exists():
            try:
                with open(meta_path, 'r') as f:
                    meta = json.load(f)
                    info.update(meta)
            except Exception:
                pass

        return info

    def list_caches(self) -> List[Dict[str, Any]]:
        """
        List all caches with info.

        Returns:
            List of cache info dicts
        """
        caches = []
        for path in self.cache_dir.glob("*.json"):
            if not path.name.endswith(".meta.json"):
                name = path.stem
                info = self.get_cache_info(name)
                if info:
                    caches.append(info)
        return caches


# Global cache instance
_cache: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Get global cache manager instance."""
    global _cache
    if _cache is None:
        _cache = CacheManager()
    return _cache
