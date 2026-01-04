"""
Product Loader
==============

Creates and updates products in Plytix PIM.
"""

import logging
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
plytix_path = Path(__file__).parent.parent.parent.parent.parent / "plytix-skills" / "skills" / "plytix-api" / "scripts"
sys.path.insert(0, str(plytix_path))

from plytix_api import PlytixAPI

from ..models import PlytixProduct, SyncConfig, SyncStatus
from ..extractors.batch_processor import RateLimiter
from ..cache import get_cache, CANONICAL_INDEX_TTL

logger = logging.getLogger(__name__)

# Rate limit handling constants
MAX_RETRY_WAIT = 1800  # Maximum seconds to wait for rate limit (30 min - Plytix can require 1200s+)
MAX_RETRIES = 5  # Maximum retry attempts per operation
INITIAL_BACKOFF = 2  # Initial backoff seconds
BACKOFF_MULTIPLIER = 2  # Exponential backoff multiplier


class RateLimitExceeded(Exception):
    """Raised when rate limit is too long to wait."""
    def __init__(self, retry_after: int, message: str = None):
        self.retry_after = retry_after
        super().__init__(message or f"Rate limit exceeded: {retry_after}s wait required")


class ProductLoader:
    """
    Loads products into Plytix PIM.

    Features:
    - Create new products
    - Update existing products
    - Assign product family (using correct API endpoint)
    - Rate limiting to avoid API throttling
    """

    def __init__(self, config: SyncConfig):
        """
        Initialize product loader.

        Args:
            config: Sync configuration
        """
        self.config = config
        self.api = PlytixAPI()

        # Rate limiter
        self.rate_limiter = RateLimiter(
            rate=config.plytix_rate_limit,
            burst=3
        )

        # Cache of existing products by SKU
        self._sku_to_id: Dict[str, str] = {}

        # Track products that hit catastrophic rate limits (for batch retry later)
        self._rate_limited_products: List[Tuple[str, str, int]] = []  # (product_id, family_id, retry_after)

        # Track family assignment failures for reporting
        self._family_assignment_failures: List[Tuple[str, str]] = []  # (product_id, error_message)

    def _extract_retry_after(self, error: Exception) -> Optional[int]:
        """
        Extract retry-after seconds from rate limit error message.

        Args:
            error: Exception that may contain rate limit info

        Returns:
            Retry-after seconds or None
        """
        error_str = str(error)
        # Match patterns like "Retry after 2497s", "Retry after 1089.492s", or "retry_after': '60'"
        # Note: Space after "after" is required to match "Retry after 123s" format
        match = re.search(r'(?:Retry after |retry_after[\'":\s]+)([\d.]+)', error_str)
        if match:
            return int(float(match.group(1)))  # Convert to float first to handle decimals
        return None

    def _with_retry(self, operation: callable, operation_name: str, *args, **kwargs):
        """
        Execute an operation with exponential backoff retry for rate limits.

        Args:
            operation: Callable to execute
            operation_name: Name for logging
            *args, **kwargs: Arguments for operation

        Returns:
            Operation result

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
                    # Rate limit detected
                    if retry_after > MAX_RETRY_WAIT:
                        # Rate limit exceeds max wait - log but still raise for caller to decide
                        logger.warning(
                            f"{operation_name}: Rate limit {retry_after}s exceeds max wait {MAX_RETRY_WAIT}s"
                        )
                        raise RateLimitExceeded(retry_after)

                    # Rate limit within tolerance - wait the full period and retry
                    resume_time = time.strftime('%H:%M:%S', time.localtime(time.time() + retry_after))
                    logger.warning(
                        f"🛑 {operation_name}: Rate limited for {retry_after:.0f}s. "
                        f"Waiting until {resume_time} (attempt {attempt + 1}/{MAX_RETRIES})"
                    )
                    time.sleep(retry_after)
                    continue

                # Not a rate limit error
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"{operation_name}: Error on attempt {attempt + 1}, retrying in {backoff}s: {e}")
                    time.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER
                else:
                    raise

        # Should not reach here, but just in case
        raise Exception(f"{operation_name}: Max retries exceeded")

    def build_sku_index(self, sku_pattern: Optional[str] = None, force: bool = False) -> None:
        """
        Build index of existing products by SKU.

        Args:
            sku_pattern: Optional SKU pattern to filter (e.g., "AMZN-")
            force: If True, rebuild even if index already populated
        """
        # Skip if already built (avoids duplicate API calls across phases)
        if self._sku_to_id and not force:
            logger.debug(f"SKU index already populated ({len(self._sku_to_id)} entries), skipping rebuild")
            return

        logger.info("Building SKU index from Plytix...")

        self._sku_to_id.clear()

        # Use search with SKU filter
        # NOTE: Plytix 'like' operator does prefix/substring match (NOT SQL wildcards)
        filters = []
        if sku_pattern:
            # Remove any SQL wildcard characters - Plytix uses prefix match
            pattern_value = sku_pattern.rstrip('%')
            filters.append({
                "field": "sku",
                "operator": "like",
                "value": pattern_value
            })

        # Paginate through all products with retry logic
        page = 1
        total_found = 0

        while True:
            def _do_search():
                self.rate_limiter.acquire()
                return self.api.search_products(
                    filters=filters,
                    limit=100,
                    page=page,
                )

            try:
                result = self._with_retry(_do_search, f"build_sku_index_page_{page}")
            except RateLimitExceeded as e:
                logger.warning(f"Rate limit on SKU index page {page}, stopping at {total_found} products")
                break
            except Exception as e:
                logger.error(f"Failed to build SKU index at page {page}: {e}")
                raise

            products = result.get("data", [])
            if not products:
                break

            for product in products:
                sku = product.get("sku")
                product_id = product.get("id")
                if sku and product_id:
                    self._sku_to_id[sku] = product_id
                    total_found += 1

            page += 1

            # Safety limit - configurable via sync_config.yaml
            if page > self.config.sku_index_max_pages:
                logger.warning(f"Reached SKU index page limit ({self.config.sku_index_max_pages}), stopping. "
                               f"Increase indexes.sku_max_pages in config if needed.")
                break

        logger.info(f"SKU index built: {total_found} products")

    def get_product_id_by_sku(self, sku: str) -> Optional[str]:
        """
        Get Plytix product ID by SKU.

        Args:
            sku: Product SKU

        Returns:
            Product ID or None
        """
        return self._sku_to_id.get(sku)

    def load_product(
        self,
        product: PlytixProduct,
    ) -> Tuple[SyncStatus, Optional[str], Optional[str]]:
        """
        Load a single product to Plytix.

        Args:
            product: PlytixProduct to load

        Returns:
            Tuple of (status, product_id, error_message)
        """
        self.rate_limiter.acquire()

        try:
            # Check if product exists
            existing_id = self.get_product_id_by_sku(product.sku)

            if existing_id:
                # Update existing
                return self._update_product(existing_id, product)
            else:
                # Create new
                return self._create_product(product)

        except Exception as e:
            logger.error(f"Failed to load product {product.sku}: {e}")
            return SyncStatus.FAILED, None, str(e)

    def _create_product(
        self,
        product: PlytixProduct,
    ) -> Tuple[SyncStatus, Optional[str], Optional[str]]:
        """Create a new product with retry logic."""
        try:
            # Filter out None values from attributes (critical for Plytix validation)
            filtered_attrs = {
                k: v for k, v in product.attributes.items()
                if v is not None
            }

            # Build create payload
            # NOTE: product_family is NOT supported on POST - must use assign_product_family()
            payload = {
                "sku": product.sku,
                "label": product.label,
                "status": product.status,
                "attributes": filtered_attrs,
            }

            # Create product with retry
            result = self._with_retry(
                lambda: self.api.create_product(payload),
                f"create_product({product.sku})"
            )

            # Handle response format: {'data': [{'id': '...', ...}]}
            product_id = None
            if isinstance(result, dict):
                data = result.get("data")
                if isinstance(data, list) and data:
                    product_id = data[0].get("id")
                elif isinstance(data, dict):
                    product_id = data.get("id")
                else:
                    product_id = result.get("id")

            if not product_id:
                return SyncStatus.FAILED, None, f"No product ID in response: {result}"

            # Update SKU index
            self._sku_to_id[product.sku] = product_id
            product.id = product_id

            # Assign product family (MUST use dedicated endpoint - POST/PATCH ignore it!)
            if product.product_family_id:
                self._assign_family(product_id, product.product_family_id)

            logger.debug(f"Created product: {product.sku} -> {product_id}")
            return SyncStatus.SUCCESS, product_id, None

        except RateLimitExceeded as e:
            # Catastrophic rate limit on create - this is bad
            logger.error(f"Rate limit {e.retry_after}s on create for {product.sku}")
            return SyncStatus.FAILED, None, f"Rate limit exceeded: {e.retry_after}s"
        except Exception as e:
            return SyncStatus.FAILED, None, str(e)

    def _update_product(
        self,
        product_id: str,
        product: PlytixProduct,
    ) -> Tuple[SyncStatus, Optional[str], Optional[str]]:
        """Update an existing product with retry logic."""
        try:
            product.id = product_id

            # Filter out None values from attributes (critical for Plytix validation)
            filtered_attrs = {
                k: v for k, v in product.attributes.items()
                if v is not None
            }

            # Build update payload
            payload = {
                "label": product.label,
                "attributes": filtered_attrs,
            }

            # Update product with retry
            self.rate_limiter.acquire()
            self._with_retry(
                lambda: self.api.update_product(product_id, payload),
                f"update_product({product.sku})"
            )

            # Re-assign family if needed (must use dedicated endpoint for updates!)
            if product.product_family_id:
                self.rate_limiter.acquire()
                self._assign_family(product_id, product.product_family_id)

            logger.debug(f"Updated product: {product.sku}")
            return SyncStatus.SUCCESS, product_id, None

        except RateLimitExceeded as e:
            logger.error(f"Rate limit {e.retry_after}s on update for {product.sku}")
            return SyncStatus.FAILED, product_id, f"Rate limit exceeded: {e.retry_after}s"
        except Exception as e:
            return SyncStatus.FAILED, product_id, str(e)

    def _assign_family(self, product_id: str, family_id: str) -> bool:
        """
        Assign product family using dedicated endpoint with retry logic.

        CRITICAL: Must use assign_product_family(), NOT update_product().
        The PATCH endpoint silently ignores product_family field.

        Returns:
            True if successful, False if failed (product tracked for later retry)
        """
        try:
            self._with_retry(
                lambda: self.api.assign_product_family(product_id, family_id),
                f"assign_family({product_id})"
            )
            logger.debug(f"Assigned family {family_id} to product {product_id}")
            return True
        except RateLimitExceeded as e:
            # Track for batch retry later
            self._rate_limited_products.append((product_id, family_id, e.retry_after))
            logger.warning(
                f"Product {product_id} queued for later family assignment "
                f"(rate limit {e.retry_after}s)"
            )
            return False
        except Exception as e:
            # Track failure for reporting - product was created but family not assigned
            error_msg = str(e)
            self._family_assignment_failures.append((product_id, error_msg))
            logger.warning(f"Failed to assign family to {product_id}: {e}")
            return False

    def get_rate_limited_products(self) -> List[Tuple[str, str, int]]:
        """
        Get list of products that hit catastrophic rate limits.

        Returns:
            List of (product_id, family_id, retry_after) tuples
        """
        return self._rate_limited_products.copy()

    def set_rate_limited_products(self, items: List[Tuple[str, str, int]]) -> None:
        """
        Restore rate-limited products queue from checkpoint.

        Args:
            items: List of (product_id, family_id, retry_after) tuples
        """
        self._rate_limited_products = [(str(item[0]), str(item[1]), int(item[2])) for item in items]
        if self._rate_limited_products:
            logger.info(f"Restored {len(self._rate_limited_products)} rate-limited products from checkpoint")

    def get_family_assignment_failures(self) -> List[Tuple[str, str]]:
        """
        Get list of products where family assignment failed.

        Returns:
            List of (product_id, error_message) tuples
        """
        return self._family_assignment_failures.copy()

    def retry_rate_limited_families(self) -> Dict[str, int]:
        """
        Retry family assignments for products that previously hit rate limits.

        Should be called after a cooldown period.

        Returns:
            Summary with 'success' and 'failed' counts
        """
        if not self._rate_limited_products:
            return {"success": 0, "failed": 0}

        logger.info(f"Retrying {len(self._rate_limited_products)} rate-limited family assignments...")

        results = {"success": 0, "failed": 0}
        remaining = []

        for product_id, family_id, _ in self._rate_limited_products:
            # Add delay between retries to avoid triggering rate limits again
            time.sleep(2)
            self.rate_limiter.acquire()

            try:
                self._with_retry(
                    lambda pid=product_id, fid=family_id: self.api.assign_product_family(pid, fid),
                    f"retry_assign_family({product_id})"
                )
                results["success"] += 1
                logger.debug(f"Successfully assigned family to {product_id} on retry")
            except RateLimitExceeded as e:
                remaining.append((product_id, family_id, e.retry_after))
                results["failed"] += 1
            except Exception as e:
                results["failed"] += 1
                logger.warning(f"Retry failed for {product_id}: {e}")

        self._rate_limited_products = remaining
        logger.info(f"Retry complete: {results['success']} succeeded, {results['failed']} failed")
        return results

    def load_batch(
        self,
        products: List[PlytixProduct],
        on_progress: Optional[callable] = None,
    ) -> Dict[str, any]:
        """
        Load multiple products in parallel.

        Args:
            products: List of products to load
            on_progress: Optional callback(completed, total, status)

        Returns:
            Summary of results
        """
        results = {
            "total": len(products),
            "created": 0,
            "updated": 0,
            "failed": 0,
            "errors": [],
        }

        # Thread-safe progress tracking
        progress_lock = threading.Lock()
        completed_count = 0

        def process_product(product: PlytixProduct) -> Tuple[PlytixProduct, SyncStatus, Optional[str], Optional[str]]:
            """Process a single product with rate limiting and delay."""
            nonlocal completed_count

            # Rate limiting handled by load_product
            status, product_id, error = self.load_product(product)

            # Update progress (thread-safe)
            with progress_lock:
                completed_count += 1
                current_count = completed_count

                if on_progress:
                    on_progress(current_count, len(products), status)

            # Small delay between products (rate limiter handles concurrency)
            time.sleep(0.1)

            return product, status, product_id, error

        # Process products in parallel (3 workers based on burst=3)
        logger.debug(f"Processing {len(products)} products with 3 parallel workers")

        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all tasks
            futures = [executor.submit(process_product, product) for product in products]

            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    product, status, product_id, error = future.result()

                    # Update results (thread-safe - only accessed in main thread here)
                    if status == SyncStatus.SUCCESS:
                        if product.is_new:
                            results["created"] += 1
                        else:
                            results["updated"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append({
                            "sku": product.sku,
                            "error": error,
                        })

                except Exception as e:
                    # Handle unexpected errors in worker
                    results["failed"] += 1
                    results["errors"].append({
                        "sku": "unknown",
                        "error": f"Worker exception: {str(e)}",
                    })
                    logger.error(f"Worker exception: {e}")

        # Add rate-limited products count to results
        rate_limited_count = len(self._rate_limited_products)
        results["rate_limited"] = rate_limited_count

        log_msg = (
            f"Loaded {results['total']} products: "
            f"{results['created']} created, {results['updated']} updated, "
            f"{results['failed']} failed"
        )
        if rate_limited_count > 0:
            log_msg += f", {rate_limited_count} rate-limited (family assignment deferred)"

        logger.info(log_msg)

        return results

    def get_products_by_attribute(
        self,
        attribute_name: str,
        value: str,
        sku_pattern: Optional[str] = None,
    ) -> List[Dict]:
        """
        Find products by custom attribute value.

        Note: Plytix search doesn't support custom attribute filters,
        so this fetches products and filters locally.

        Args:
            attribute_name: Attribute to search
            value: Value to match
            sku_pattern: Optional SKU pre-filter

        Returns:
            List of matching products
        """
        try:
            products = self.api.find_products_by_attribute(
                attribute_name=attribute_name,
                value=value,
                sku_pattern=sku_pattern,
            )
            return products
        except Exception as e:
            logger.error(f"Failed to find products by attribute: {e}")
            return []

    def get_all_canonical_products(self, force_refresh: bool = False) -> List[Dict]:
        """
        Get all non-Amazon products for canonical matching.

        Uses disk cache with configurable TTL (default 24h) to avoid fetching 68k+ products every run.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            List of product dictionaries
        """
        cache = get_cache()
        cache_name = "canonical_index"

        # Use configurable TTL from config (hours -> seconds)
        cache_ttl = self.config.canonical_cache_ttl_hours * 60 * 60

        # Check cache first
        if not force_refresh and cache.is_valid(cache_name, cache_ttl):
            cached_data = cache.load(cache_name)
            if cached_data:
                logger.info(f"Loaded {len(cached_data)} canonical products from cache")
                return cached_data

        logger.info("Fetching canonical products from Plytix (cache miss or expired)...")

        all_products = []
        page = 1

        # Get products that are NOT Amazon products
        # NOTE: Plytix 'like'/'!like' operator does prefix match (NOT SQL wildcards)
        while True:
            self.rate_limiter.acquire()

            try:
                # CRITICAL: Must request matching attributes explicitly!
                # Plytix search returns empty attributes:{} unless specified
                result = self.api.search_products(
                    filters=[{
                        "field": "sku",
                        "operator": "!like",
                        "value": "AMZN-"
                    }],
                    attributes=['gtin', 'upc', 'ean', 'model_number', 'amazon_model_number'],
                    limit=100,
                    page=page,
                )

                products = result.get("data", [])
                if not products:
                    break

                all_products.extend(products)

                # Log progress every 100 pages (~10k products)
                if page % 100 == 0:
                    logger.info(f"Fetching canonical products: {len(all_products)} loaded (page {page})...")

                page += 1

                # Safety limit - support up to 100k products (1000 pages)
                if page > 1000:
                    logger.warning(f"Reached page limit at {len(all_products)} products")
                    break

            except Exception as e:
                logger.error(f"Error fetching canonical products: {e}")
                break

        # Save to cache
        if all_products:
            cache.save(cache_name, all_products)

        logger.info(f"Fetched and cached {len(all_products)} canonical products")
        return all_products
