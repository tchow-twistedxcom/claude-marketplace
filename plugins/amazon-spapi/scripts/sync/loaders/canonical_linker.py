"""
Canonical Linker
================

Links Amazon products to their canonical Plytix products.
"""

import logging
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
plytix_path = Path(__file__).parent.parent.parent.parent.parent / "plytix-skills" / "skills" / "plytix-api" / "scripts"
sys.path.insert(0, str(plytix_path))

from plytix_api import PlytixAPI

from ..models import CanonicalMatch, SyncConfig
from ..extractors.batch_processor import RateLimiter

logger = logging.getLogger(__name__)

# Rate limit handling constants
MAX_RETRY_WAIT = 60  # Maximum seconds to wait for rate limit
MAX_RETRIES = 3  # Maximum retry attempts per operation
INITIAL_BACKOFF = 2  # Initial backoff seconds
BACKOFF_MULTIPLIER = 2  # Exponential backoff multiplier


class RateLimitExceeded(Exception):
    """Raised when rate limit is too long to wait."""
    def __init__(self, retry_after: int, message: str = None):
        self.retry_after = retry_after
        super().__init__(message or f"Rate limit exceeded: {retry_after}s wait required")


class CanonicalLinker:
    """
    Links canonical Plytix products to their Amazon product representations.

    Relationship structure:
    - Canonical product → Amazon products
    - Uses "amazon_listings" relationship type
    - One canonical can have multiple Amazon listings (different marketplaces)
    """

    def __init__(self, config: SyncConfig):
        """
        Initialize canonical linker.

        Args:
            config: Sync configuration
        """
        self.config = config
        self.api = PlytixAPI()

        # Rate limiter
        self.rate_limiter = RateLimiter(
            rate=config.plytix_rate_limit,
            burst=2
        )

        # Track linked canonicals
        self._linked_canonicals: Set[str] = set()

        # Group: canonical_id -> list of amazon_product_ids
        self._canonical_to_amazon: Dict[str, List[str]] = {}

        # Cache relationship ID (avoid repeated API lookups)
        # None = not looked up yet, False = confirmed not found, str = found ID
        self._cached_relationship_id: Optional[str] = None
        self._relationship_lookup_failed: bool = False  # Track API failures vs not-found

        # Track Amazon products with reverse relationships (avoid duplicate links)
        self._linked_amazon_products: Set[str] = set()

    def _extract_retry_after(self, error: Exception) -> Optional[int]:
        """Extract retry-after seconds from rate limit error message."""
        error_str = str(error)
        match = re.search(r'(?:Retry after|retry_after[\'\":\s]+)(\d+)', error_str)
        if match:
            return int(match.group(1))
        return None

    def _with_retry(self, operation: callable, operation_name: str, *args, **kwargs):
        """
        Execute an operation with exponential backoff retry for rate limits.

        Raises:
            RateLimitExceeded: If rate limit wait exceeds MAX_RETRY_WAIT
            Exception: Other errors after MAX_RETRIES attempts
        """
        backoff = INITIAL_BACKOFF

        for attempt in range(MAX_RETRIES):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                retry_after = self._extract_retry_after(e)

                if retry_after is not None:
                    if retry_after > MAX_RETRY_WAIT:
                        logger.warning(
                            f"{operation_name}: Rate limit {retry_after}s exceeds max wait {MAX_RETRY_WAIT}s, skipping"
                        )
                        raise RateLimitExceeded(retry_after)

                    wait_time = min(retry_after, MAX_RETRY_WAIT)
                    logger.info(f"{operation_name}: Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(wait_time)
                    continue

                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"{operation_name}: Error on attempt {attempt + 1}, retrying in {backoff}s: {e}")
                    time.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER
                else:
                    raise

        raise Exception(f"{operation_name}: Max retries exceeded")

    def prepare_links(
        self,
        matches: List[CanonicalMatch],
        asin_to_product_id: Dict[str, str],
    ) -> None:
        """
        Prepare link data from matches.

        Args:
            matches: List of canonical matches
            asin_to_product_id: Mapping of ASIN -> Plytix product ID
        """
        self._canonical_to_amazon.clear()

        for match in matches:
            if not match.matched or not match.canonical_product_id:
                continue

            # Get the Amazon product's Plytix ID
            amazon_product_id = asin_to_product_id.get(match.amazon_product.asin)
            if not amazon_product_id:
                continue

            canonical_id = match.canonical_product_id

            if canonical_id not in self._canonical_to_amazon:
                self._canonical_to_amazon[canonical_id] = []

            self._canonical_to_amazon[canonical_id].append(amazon_product_id)

        logger.info(
            f"Prepared {len(self._canonical_to_amazon)} canonical products "
            f"for linking to Amazon products"
        )

    def load_links(self) -> Dict[str, any]:
        """
        Create canonical → Amazon relationships.

        Returns:
            Summary of results
        """
        results = {
            "linked": 0,
            "skipped": 0,
            "errors": [],
        }

        for canonical_id, amazon_ids in self._canonical_to_amazon.items():
            success, error = self._link_canonical_to_amazon(
                canonical_id, amazon_ids
            )

            if success:
                results["linked"] += 1
            elif error:
                results["errors"].append({
                    "canonical_id": canonical_id,
                    "error": error,
                })
            else:
                results["skipped"] += 1

        logger.info(
            f"Canonical linking complete: {results['linked']} linked, "
            f"{results['skipped']} skipped, {len(results['errors'])} errors"
        )

        return results

    def _link_canonical_to_amazon(
        self,
        canonical_id: str,
        amazon_ids: List[str],
    ) -> Tuple[bool, Optional[str]]:
        """
        Create bidirectional relationships between canonical and Amazon products.

        Creates:
        1. Canonical → Amazon (forward)
        2. Amazon → Canonical (reverse, for visibility on Amazon product)

        Args:
            canonical_id: Canonical Plytix product ID
            amazon_ids: List of Amazon Plytix product IDs

        Returns:
            Tuple of (success, error_message)
        """
        # Skip if already linked
        if canonical_id in self._linked_canonicals:
            return False, None

        if not amazon_ids:
            return False, None

        # Get the actual relationship ID (not the label)
        relationship_id = self.get_relationship_id()
        if not relationship_id:
            return False, f"Relationship '{self.config.amazon_listings_relationship}' not found in Plytix"

        try:
            # Forward: Canonical → Amazon (1 API call)
            def _add_forward_link():
                self.rate_limiter.acquire()
                self.api.add_product_relationships(
                    product_id=canonical_id,
                    relationship_id=relationship_id,
                    related_product_ids=amazon_ids,
                )

            self._with_retry(_add_forward_link, f"link_canonical_{canonical_id}")

            # Reverse: Amazon → Canonical (skip already-linked products)
            # Filter to only unlinked Amazon products
            unlinked_amazon_ids = [
                aid for aid in amazon_ids
                if aid not in self._linked_amazon_products
            ]

            if unlinked_amazon_ids:
                for amazon_id in unlinked_amazon_ids:
                    def _add_reverse_link(aid=amazon_id):
                        self.rate_limiter.acquire()
                        self.api.add_product_relationships(
                            product_id=aid,
                            relationship_id=relationship_id,
                            related_product_ids=[canonical_id],
                        )

                    try:
                        self._with_retry(_add_reverse_link, f"reverse_link_{amazon_id}")
                        self._linked_amazon_products.add(amazon_id)
                    except RateLimitExceeded:
                        logger.warning(f"Rate limit exceeded for reverse link {amazon_id}, skipping")
                        continue

            self._linked_canonicals.add(canonical_id)
            logger.debug(
                f"Linked canonical {canonical_id} ↔ {len(amazon_ids)} Amazon products "
                f"({len(unlinked_amazon_ids)} new reverse links)"
            )
            return True, None

        except RateLimitExceeded as e:
            return False, f"Rate limit exceeded: {e.retry_after}s wait required"

        except Exception as e:
            return False, str(e)

    def get_relationship_id(self) -> Optional[str]:
        """
        Get or verify the amazon_listings relationship exists.

        Uses cached value to avoid repeated API calls.
        Distinguishes between "not found" and "API failure" to avoid
        repeated failing API calls.

        Returns:
            Relationship ID or None if not found/failed
        """
        # Return cached value if available (could be ID string or False for confirmed not-found)
        if self._cached_relationship_id is not None:
            return self._cached_relationship_id if self._cached_relationship_id else None

        # Skip if previous lookup failed due to API error (avoid hammering rate-limited API)
        if self._relationship_lookup_failed:
            return None

        def _do_lookup():
            self.rate_limiter.acquire()
            return self.api.list_relationships()

        try:
            relationships = self._with_retry(_do_lookup, "list_relationships")
            rel_data = relationships.get("data", [])

            for rel in rel_data:
                if rel.get("label") == self.config.amazon_listings_relationship:
                    # Cache the actual relationship ID
                    self._cached_relationship_id = rel.get("id")
                    logger.info(f"Found relationship '{self.config.amazon_listings_relationship}' with ID: {self._cached_relationship_id}")
                    return self._cached_relationship_id

            # Successfully queried but relationship not found - cache as False
            self._cached_relationship_id = False
            logger.warning(
                f"Relationship '{self.config.amazon_listings_relationship}' not found. "
                f"Create it in Plytix first."
            )
            return None

        except RateLimitExceeded as e:
            # Rate limit too long - mark as failed to avoid repeated attempts
            self._relationship_lookup_failed = True
            logger.warning(f"Relationship lookup rate limited ({e.retry_after}s), skipping canonical linking")
            return None

        except Exception as e:
            # API error - mark as failed to avoid repeated attempts
            self._relationship_lookup_failed = True
            logger.error(f"Failed to check relationship: {e}")
            return None

    def verify_setup(self) -> bool:
        """
        Verify amazon_listings relationship exists in Plytix.

        Returns:
            True if setup is valid
        """
        rel_id = self.get_relationship_id()
        return rel_id is not None

    def get_link_summary(self) -> Dict[str, int]:
        """Get summary of prepared links."""
        total_amazon = sum(len(ids) for ids in self._canonical_to_amazon.values())
        return {
            "canonical_products": len(self._canonical_to_amazon),
            "amazon_products": total_amazon,
            "already_linked": len(self._linked_canonicals),
        }
