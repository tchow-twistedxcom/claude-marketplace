"""
Checkpoint Manager
==================

Manages sync state persistence for resume capability.
Saves/loads checkpoint data to enable resuming interrupted syncs.
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..models import SyncPhase, SyncResult, SyncItemResult, SyncStatus

logger = logging.getLogger(__name__)

# Data file names for phase output persistence
MATCHES_FILE = "matches.json"
ASIN_MAPPING_FILE = "asin_mapping.json"
CANONICAL_FAILURES_FILE = "canonical_failures.json"


class CheckpointManager:
    """
    Manages checkpoint files for sync resume capability.

    Checkpoint structure:
    {
        "run_id": "20250101_120000",
        "phase": "load_products",
        "last_checkpoint": "2025-01-01T12:30:00",
        "processed_asins": ["B07X...", "B08Y..."],
        "pending_asins": ["B09Z..."],
        "failed_asins": {"B10A...": "Error message"},
        "parent_asins": ["B077..."],
        "canonical_index_built": true,
        "results": { ... }
    }
    """

    def __init__(self, data_dir: str, run_id: Optional[str] = None):
        """
        Initialize checkpoint manager.

        Args:
            data_dir: Base directory for sync data
            run_id: Specific run ID (for resume) or None for new run
        """
        self.data_dir = Path(data_dir)
        self.run_id = run_id or self._generate_run_id()
        self.run_dir = self.data_dir / self.run_id
        self.checkpoint_file = self.run_dir / "checkpoint.json"
        self.backup_file = self.run_dir / "checkpoint.json.bak"

        # In-memory state
        self._processed_asins: Set[str] = set()
        self._pending_asins: List[str] = []
        self._failed_asins: Dict[str, str] = {}
        self._parent_asins: Set[str] = set()
        self._current_phase: SyncPhase = SyncPhase.INIT
        self._results: Dict[str, Any] = {}
        self._canonical_index_built: bool = False

        # Rate-limited queues (persist to avoid losing work on crash)
        # Format: [(product_id, family_id, retry_after), ...]
        self._rate_limited_products: List[List] = []
        # Format: [(url, asin, index, product_id), ...]
        self._rate_limited_images: List[List] = []

        # Ensure directories exist
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def _generate_run_id(self) -> str:
        """Generate unique run ID based on timestamp."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @property
    def processed_asins(self) -> Set[str]:
        """Set of already processed ASINs."""
        return self._processed_asins

    @property
    def pending_asins(self) -> List[str]:
        """List of ASINs pending processing."""
        return self._pending_asins

    @property
    def failed_asins(self) -> Dict[str, str]:
        """Map of failed ASINs to error messages."""
        return self._failed_asins

    @property
    def parent_asins(self) -> Set[str]:
        """Set of discovered parent ASINs."""
        return self._parent_asins

    @property
    def current_phase(self) -> SyncPhase:
        """Current sync phase."""
        return self._current_phase

    @property
    def rate_limited_products(self) -> List[List]:
        """List of rate-limited product family assignments."""
        return self._rate_limited_products

    @property
    def rate_limited_images(self) -> List[List]:
        """List of rate-limited image uploads."""
        return self._rate_limited_images

    def has_checkpoint(self) -> bool:
        """Check if a checkpoint exists for this run."""
        return self.checkpoint_file.exists()

    def load(self) -> bool:
        """
        Load checkpoint from disk.

        Returns:
            True if checkpoint was loaded, False if no checkpoint exists
        """
        if not self.checkpoint_file.exists():
            logger.info(f"No checkpoint found for run {self.run_id}")
            return False

        try:
            with open(self.checkpoint_file, 'r') as f:
                data = json.load(f)

            self._processed_asins = set(data.get('processed_asins', []))
            self._pending_asins = data.get('pending_asins', [])
            self._failed_asins = data.get('failed_asins', {})
            self._parent_asins = set(data.get('parent_asins', []))
            self._current_phase = SyncPhase.from_string(data.get('phase', 'init'))
            self._results = data.get('results', {})
            self._canonical_index_built = data.get('canonical_index_built', False)

            # Restore rate-limited queues
            self._rate_limited_products = data.get('rate_limited_products', [])
            self._rate_limited_images = data.get('rate_limited_images', [])

            rate_limited_msg = ""
            if self._rate_limited_products or self._rate_limited_images:
                rate_limited_msg = f", rate_limited_products={len(self._rate_limited_products)}, rate_limited_images={len(self._rate_limited_images)}"

            logger.info(
                f"Loaded checkpoint: phase={self._current_phase.value}, "
                f"processed={len(self._processed_asins)}, "
                f"pending={len(self._pending_asins)}, "
                f"failed={len(self._failed_asins)}{rate_limited_msg}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            # Try backup
            if self.backup_file.exists():
                logger.info("Attempting to load backup checkpoint...")
                shutil.copy(self.backup_file, self.checkpoint_file)
                return self.load()
            return False

    def save(self) -> None:
        """Save current state to checkpoint file."""
        # Backup existing checkpoint
        if self.checkpoint_file.exists():
            shutil.copy(self.checkpoint_file, self.backup_file)

        data = {
            "run_id": self.run_id,
            "phase": self._current_phase.name.lower(),
            "last_checkpoint": datetime.now().isoformat(),
            "processed_asins": list(self._processed_asins),
            "pending_asins": self._pending_asins,
            "failed_asins": self._failed_asins,
            "parent_asins": list(self._parent_asins),
            "canonical_index_built": self._canonical_index_built,
            "results": self._results,
            # Persist rate-limited queues so they can be retried after crash/restart
            "rate_limited_products": self._rate_limited_products,
            "rate_limited_images": self._rate_limited_images,
            "stats": {
                "processed_count": len(self._processed_asins),
                "pending_count": len(self._pending_asins),
                "failed_count": len(self._failed_asins),
                "parent_count": len(self._parent_asins),
                "rate_limited_products_count": len(self._rate_limited_products),
                "rate_limited_images_count": len(self._rate_limited_images),
            }
        }

        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Checkpoint saved: {len(self._processed_asins)} processed")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise

    def set_phase(self, phase: SyncPhase) -> None:
        """Update current phase and save checkpoint."""
        self._current_phase = phase
        self.save()
        logger.info(f"Phase: {phase.value}")

    def set_pending_asins(self, asins: List[str]) -> None:
        """Set the list of ASINs to process."""
        self._pending_asins = asins
        self.save()

    def mark_processed(self, asin: str) -> None:
        """Mark an ASIN as successfully processed."""
        self._processed_asins.add(asin)
        if asin in self._pending_asins:
            self._pending_asins.remove(asin)
        if asin in self._failed_asins:
            del self._failed_asins[asin]

    def mark_failed(self, asin: str, error: str) -> None:
        """Mark an ASIN as failed with error message."""
        self._failed_asins[asin] = error
        if asin in self._pending_asins:
            self._pending_asins.remove(asin)

    def add_parent_asin(self, asin: str) -> None:
        """Add a discovered parent ASIN."""
        self._parent_asins.add(asin)

    def add_parent_asins(self, asins: List[str]) -> None:
        """Add multiple parent ASINs."""
        self._parent_asins.update(asins)

    def mark_canonical_index_built(self) -> None:
        """Mark that the canonical product index has been built."""
        self._canonical_index_built = True
        self.save()

    def set_rate_limited_products(self, items: List) -> None:
        """
        Update rate-limited products queue.

        Args:
            items: List of tuples (product_id, family_id, retry_after)
        """
        self._rate_limited_products = [list(item) for item in items]
        # Note: Don't auto-save here to avoid excessive I/O; call save() explicitly when needed

    def set_rate_limited_images(self, items: List) -> None:
        """
        Update rate-limited images queue.

        Args:
            items: List of tuples (url, asin, index, product_id)
        """
        self._rate_limited_images = [list(item) for item in items]
        # Note: Don't auto-save here to avoid excessive I/O; call save() explicitly when needed

    def has_rate_limited_items(self) -> bool:
        """Check if there are any rate-limited items to retry."""
        return bool(self._rate_limited_products) or bool(self._rate_limited_images)

    def is_canonical_index_built(self) -> bool:
        """Check if canonical index was already built."""
        return self._canonical_index_built

    def is_processed(self, asin: str) -> bool:
        """Check if an ASIN has been processed."""
        return asin in self._processed_asins

    def set_result(self, key: str, value: Any) -> None:
        """Store a result value."""
        self._results[key] = value

    def get_result(self, key: str, default: Any = None) -> Any:
        """Retrieve a stored result."""
        return self._results.get(key, default)

    def should_checkpoint(self, count: int, interval: int) -> bool:
        """Check if we should save a checkpoint based on count."""
        return count > 0 and count % interval == 0

    def get_data_file_path(self, filename: str) -> Path:
        """Get path to a data file in the run directory."""
        return self.run_dir / filename

    def save_data_file(self, filename: str, data: Any) -> Path:
        """Save data to a JSON file in the run directory."""
        path = self.get_data_file_path(filename)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        logger.debug(f"Saved data file: {filename}")
        return path

    def load_data_file(self, filename: str) -> Optional[Any]:
        """Load data from a JSON file in the run directory."""
        path = self.get_data_file_path(filename)
        if not path.exists():
            return None
        with open(path, 'r') as f:
            return json.load(f)

    # =========================================================================
    # Match Data Persistence (for CANONICAL phase resume)
    # =========================================================================

    def save_matches(self, matches: List) -> Path:
        """
        Save match phase results for resume capability.

        Args:
            matches: List of CanonicalMatch objects from MATCH phase

        Returns:
            Path to saved file
        """
        data = [m.to_dict() for m in matches]
        path = self.save_data_file(MATCHES_FILE, data)
        logger.info(f"Saved {len(data)} matches to {MATCHES_FILE}")
        return path

    def load_matches(self, amazon_products_by_asin: Dict[str, Any]) -> Optional[List]:
        """
        Load match phase results for resume.

        Args:
            amazon_products_by_asin: Mapping to reconnect ASIN references

        Returns:
            List of CanonicalMatch or None if file doesn't exist
        """
        from ..models import CanonicalMatch  # Avoid circular import

        data = self.load_data_file(MATCHES_FILE)
        if data is None:
            logger.warning(f"{MATCHES_FILE} not found - MATCH phase must be rerun")
            return None

        matches = []
        missing_count = 0
        for item in data:
            match = CanonicalMatch.from_dict(item, amazon_products_by_asin)
            if match:
                matches.append(match)
            else:
                missing_count += 1

        if missing_count > 0:
            logger.warning(f"Skipped {missing_count} matches with missing ASIN references")

        logger.info(f"Loaded {len(matches)} matches from {MATCHES_FILE}")
        return matches

    def has_matches_file(self) -> bool:
        """Check if matches file exists."""
        return self.get_data_file_path(MATCHES_FILE).exists()

    # =========================================================================
    # ASIN Mapping Persistence (for CANONICAL/HIERARCHY phase resume)
    # =========================================================================

    def save_asin_mapping(self, asin_to_product_id: Dict[str, str]) -> Path:
        """
        Save ASIN → Plytix product ID mapping.

        Args:
            asin_to_product_id: Mapping from ASIN to Plytix product ID

        Returns:
            Path to saved file
        """
        path = self.save_data_file(ASIN_MAPPING_FILE, asin_to_product_id)
        logger.info(f"Saved {len(asin_to_product_id)} ASIN mappings to {ASIN_MAPPING_FILE}")
        return path

    def load_asin_mapping(self) -> Optional[Dict[str, str]]:
        """
        Load ASIN → product ID mapping for resume.

        Returns:
            Dictionary mapping or None if file doesn't exist
        """
        data = self.load_data_file(ASIN_MAPPING_FILE)
        if data is None:
            logger.warning(f"{ASIN_MAPPING_FILE} not found")
            return None

        logger.info(f"Loaded {len(data)} ASIN mappings from {ASIN_MAPPING_FILE}")
        return data

    def has_asin_mapping_file(self) -> bool:
        """Check if ASIN mapping file exists."""
        return self.get_data_file_path(ASIN_MAPPING_FILE).exists()

    # =========================================================================
    # Canonical Failures Persistence (for targeted retry)
    # =========================================================================

    def save_canonical_failures(self, failures: List[Dict[str, Any]]) -> Path:
        """
        Save detailed canonical linking failures for retry capability.

        Args:
            failures: List of failure dicts with canonical_id, amazon_product_ids, error

        Returns:
            Path to saved file
        """
        path = self.save_data_file(CANONICAL_FAILURES_FILE, failures)
        logger.info(f"Saved {len(failures)} canonical failures to {CANONICAL_FAILURES_FILE}")
        return path

    def load_canonical_failures(self) -> Optional[List[Dict[str, Any]]]:
        """
        Load canonical failures for retry.

        Returns:
            List of failure dicts or None if file doesn't exist
        """
        data = self.load_data_file(CANONICAL_FAILURES_FILE)
        if data is None:
            return None

        logger.info(f"Loaded {len(data)} canonical failures from {CANONICAL_FAILURES_FILE}")
        return data

    def get_resume_info(self) -> Dict[str, Any]:
        """Get information about resumable state."""
        return {
            "run_id": self.run_id,
            "phase": self._current_phase.value,
            "can_resume": self.has_checkpoint(),
            "processed_count": len(self._processed_asins),
            "pending_count": len(self._pending_asins),
            "failed_count": len(self._failed_asins),
            "checkpoint_file": str(self.checkpoint_file),
            # Phase data availability for smart resume
            "has_matches": self.has_matches_file(),
            "has_asin_mapping": self.has_asin_mapping_file(),
            "has_canonical_failures": self.get_data_file_path(CANONICAL_FAILURES_FILE).exists(),
        }

    def cleanup(self, keep_results: bool = True) -> None:
        """
        Clean up checkpoint files after successful completion.

        Args:
            keep_results: If True, keep result files but remove checkpoint
        """
        if self.backup_file.exists():
            self.backup_file.unlink()

        if not keep_results:
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
            logger.info("Checkpoint files cleaned up")

    @classmethod
    def list_runs(cls, data_dir: str) -> List[Dict[str, Any]]:
        """List all sync runs with their status."""
        data_path = Path(data_dir)
        if not data_path.exists():
            return []

        runs = []
        for run_dir in sorted(data_path.iterdir(), reverse=True):
            if run_dir.is_dir():
                checkpoint_file = run_dir / "checkpoint.json"
                if checkpoint_file.exists():
                    try:
                        with open(checkpoint_file, 'r') as f:
                            data = json.load(f)
                        runs.append({
                            "run_id": run_dir.name,
                            "phase": data.get('phase', 'unknown'),
                            "last_checkpoint": data.get('last_checkpoint'),
                            "stats": data.get('stats', {}),
                        })
                    except Exception:
                        runs.append({
                            "run_id": run_dir.name,
                            "phase": "corrupted",
                            "last_checkpoint": None,
                            "stats": {},
                        })

        return runs
