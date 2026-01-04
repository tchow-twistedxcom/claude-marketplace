"""
Hierarchy Loader
================

Creates parent-child relationships between Amazon products in Plytix.
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

from ..models import AmazonProduct, PlytixProduct, SyncConfig
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


class HierarchyLoader:
    """
    Creates Amazon product hierarchy (parent-child) relationships in Plytix.

    Relationship structure:
    - VARIATION_PARENT → VARIATION_CHILD
    - Uses "amazon_hierarchy" relationship type
    - Links FROM parent TO children
    """

    def __init__(self, config: SyncConfig):
        """
        Initialize hierarchy loader.

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

        # ASIN -> Plytix product ID mapping
        self._asin_to_product: Dict[str, str] = {}

        # Track created relationships
        self._linked_parents: Set[str] = set()

        # Cache relationship ID (avoid repeated API lookups)
        # None = not looked up yet, False = confirmed not found, str = found ID
        self._cached_relationship_id: Optional[str] = None
        self._relationship_lookup_failed: bool = False  # Track API failures vs not-found

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

    def build_asin_index(self, products: List[PlytixProduct]) -> None:
        """
        Build index of ASIN -> Plytix product ID.

        Args:
            products: List of synced PlytixProduct objects
        """
        self._asin_to_product.clear()
        missing_source_asin = 0
        missing_id = 0

        for product in products:
            if not product.source_asin:
                missing_source_asin += 1
                continue
            if not product.id:
                missing_id += 1
                continue
            self._asin_to_product[product.source_asin] = product.id

        if missing_source_asin > 0:
            logger.warning(f"Hierarchy index: {missing_source_asin} products missing source_asin - hierarchy linking will fail for these")
        if missing_id > 0:
            logger.warning(f"Hierarchy index: {missing_id} products missing Plytix ID - were they created?")

        logger.info(f"Built ASIN index: {len(self._asin_to_product)} products")

    def add_to_asin_index(self, asin: str, product_id: str) -> None:
        """
        Add a single ASIN to the index.

        Args:
            asin: Amazon ASIN
            product_id: Plytix product ID
        """
        self._asin_to_product[asin] = product_id

    def load_hierarchy(
        self,
        amazon_products: List[AmazonProduct],
    ) -> Dict[str, any]:
        """
        Create hierarchy relationships for all parent products.

        Args:
            amazon_products: List of Amazon products

        Returns:
            Summary of results
        """
        if not self.config.hierarchy_sync_enabled:
            logger.info("Hierarchy sync disabled")
            return {"linked": 0, "skipped": 0, "errors": []}

        results = {
            "linked": 0,
            "skipped": 0,
            "errors": [],
        }

        # Find parent products
        parents = [p for p in amazon_products if p.is_parent and p.child_asins]

        logger.info(f"Processing {len(parents)} parent products for hierarchy")

        for parent in parents:
            success, error = self._link_parent_to_children(parent)

            if success:
                results["linked"] += 1
            elif error:
                results["errors"].append({
                    "asin": parent.asin,
                    "error": error,
                })
            else:
                results["skipped"] += 1

        logger.info(
            f"Hierarchy loading complete: {results['linked']} linked, "
            f"{results['skipped']} skipped, {len(results['errors'])} errors"
        )

        return results

    def _link_parent_to_children(
        self,
        parent: AmazonProduct,
    ) -> Tuple[bool, Optional[str]]:
        """
        Create relationship from parent to child products.

        Args:
            parent: Parent Amazon product

        Returns:
            Tuple of (success, error_message)
        """
        # Get parent product ID
        parent_id = self._asin_to_product.get(parent.asin)
        if not parent_id:
            return False, f"Parent ASIN {parent.asin} not found in Plytix"

        # Skip if already linked
        if parent_id in self._linked_parents:
            return False, None

        # Get child product IDs
        child_ids = []
        for child_asin in parent.child_asins:
            child_id = self._asin_to_product.get(child_asin)
            if child_id:
                child_ids.append(child_id)

        if not child_ids:
            return False, f"No child products found for parent {parent.asin}"

        # Get the actual relationship ID (not the label)
        relationship_id = self.get_relationship_id()
        if not relationship_id:
            return False, f"Relationship '{self.config.amazon_hierarchy_relationship}' not found in Plytix"

        # Create relationship with retry
        def _do_link():
            self.rate_limiter.acquire()
            self.api.add_product_relationships(
                product_id=parent_id,
                relationship_id=relationship_id,
                related_product_ids=child_ids,
            )

        try:
            self._with_retry(_do_link, f"link_hierarchy_{parent.asin}")

            self._linked_parents.add(parent_id)
            logger.debug(
                f"Linked parent {parent.asin} to {len(child_ids)} children"
            )
            return True, None

        except RateLimitExceeded as e:
            return False, f"Rate limit exceeded: {e.retry_after}s wait required"

        except Exception as e:
            return False, str(e)

    def get_relationship_id(self) -> Optional[str]:
        """
        Get or verify the hierarchy relationship exists.

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
                if rel.get("label") == self.config.amazon_hierarchy_relationship:
                    # Cache the actual relationship ID
                    self._cached_relationship_id = rel.get("id")
                    logger.info(f"Found relationship '{self.config.amazon_hierarchy_relationship}' with ID: {self._cached_relationship_id}")
                    return self._cached_relationship_id

            # Successfully queried but relationship not found - cache as False
            self._cached_relationship_id = False
            logger.warning(
                f"Relationship '{self.config.amazon_hierarchy_relationship}' not found. "
                f"Create it in Plytix first."
            )
            return None

        except RateLimitExceeded as e:
            # Rate limit too long - mark as failed to avoid repeated attempts
            self._relationship_lookup_failed = True
            logger.warning(f"Relationship lookup rate limited ({e.retry_after}s), skipping hierarchy linking")
            return None

        except Exception as e:
            # API error - mark as failed to avoid repeated attempts
            self._relationship_lookup_failed = True
            logger.error(f"Failed to check relationship: {e}")
            return None

    def verify_setup(self) -> bool:
        """
        Verify hierarchy relationship exists in Plytix.

        Returns:
            True if setup is valid
        """
        rel_id = self.get_relationship_id()
        return rel_id is not None
