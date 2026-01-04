"""
Image Loader
============

Uploads and links Amazon product images to Plytix.

Filename convention matches MCA0032 test sync:
- amazon_01_MAIN_61wixnPXtlL.jpg (position first for sorting)
- amazon_02_PT01_ABC123DEF.jpg
"""

import logging
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
plytix_path = Path(__file__).parent.parent.parent.parent.parent / "plytix-skills" / "skills" / "plytix-api" / "scripts"
sys.path.insert(0, str(plytix_path))

from plytix_api import PlytixAPI

from ..models import AmazonProduct, PlytixProduct, SyncConfig, SyncStatus
from ..extractors.batch_processor import RateLimiter

logger = logging.getLogger(__name__)


# Image slot mapping: index -> (slot_name, priority)
# Matches MCA0032 convention for consistent filenames
IMAGE_SLOTS = {
    0: ('MAIN', 1),
    1: ('PT01', 2),
    2: ('PT02', 3),
    3: ('PT03', 4),
    4: ('PT04', 5),
    5: ('PT05', 6),
    6: ('PT06', 7),
    7: ('PT07', 8),
    8: ('PT08', 9),
    9: ('SWATCH', 10),
}

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


class GlobalRateLimitPause:
    """Thread-safe global pause for rate limit cooldowns."""

    def __init__(self):
        self._lock = threading.Lock()
        self._pause_until = 0.0
        self._pause_reason = ""

    def trigger_pause(self, retry_after: int, reason: str = "") -> None:
        """Trigger a global pause for all workers."""
        with self._lock:
            pause_until = time.time() + retry_after
            # Only extend if this pause is longer than current
            if pause_until > self._pause_until:
                self._pause_until = pause_until
                self._pause_reason = reason
                logger.warning(
                    f"🛑 Global rate limit pause triggered: {retry_after}s cooldown. "
                    f"All image uploads paused until {time.strftime('%H:%M:%S', time.localtime(pause_until))}"
                )

    def wait_if_paused(self) -> float:
        """Wait if globally paused. Returns seconds waited."""
        with self._lock:
            remaining = self._pause_until - time.time()

        if remaining > 0:
            logger.info(f"⏳ Waiting {remaining:.0f}s for global rate limit cooldown...")
            time.sleep(remaining)
            return remaining
        return 0.0

    def is_paused(self) -> bool:
        """Check if currently paused."""
        with self._lock:
            return time.time() < self._pause_until

    def get_remaining(self) -> float:
        """Get remaining pause time in seconds."""
        with self._lock:
            return max(0, self._pause_until - time.time())


class ImageLoader:
    """
    Loads product images into Plytix.

    Features:
    - Upload images from URL with standardized filenames
    - Deduplicate by filename (amazon_{priority}_{slot}_{image_id}.ext)
    - Link to product media gallery
    - Set first image as thumbnail and main image attribute
    """

    def __init__(self, config: SyncConfig):
        """
        Initialize image loader.

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

        # Global rate limit pause - shared across all workers
        self._global_pause = GlobalRateLimitPause()

        # Cache of filename -> asset ID (for deduplication)
        self._filename_to_asset: Dict[str, str] = {}

        # Cache of URL -> asset ID (for within-session deduplication)
        self._url_to_asset: Dict[str, str] = {}

        # Set of product IDs that have images
        self._products_with_images: Set[str] = set()

        # Track rate-limited images for retry
        # List of (url, asin, index, product_id) tuples
        self._rate_limited_images: List[Tuple[str, str, int, str]] = []

    def _extract_retry_after(self, error: Exception) -> Optional[int]:
        """Extract retry-after seconds from rate limit error message."""
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

        Uses global pause to coordinate all workers during rate limit cooldowns.
        Actually waits the full retry_after period instead of retrying immediately.

        Raises:
            RateLimitExceeded: If rate limit wait exceeds MAX_RETRY_WAIT
            Exception: Other errors after MAX_RETRIES attempts
        """
        backoff = INITIAL_BACKOFF

        for attempt in range(MAX_RETRIES):
            # Check global pause before attempting (another worker may have triggered it)
            self._global_pause.wait_if_paused()

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

                    # Trigger global pause - all workers will wait
                    self._global_pause.trigger_pause(retry_after, operation_name)

                    # Wait the full period (this handles the actual sleep)
                    self._global_pause.wait_if_paused()
                    continue

                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"{operation_name}: Error on attempt {attempt + 1}, retrying in {backoff}s: {e}")
                    time.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER
                else:
                    raise

        raise Exception(f"{operation_name}: Max retries exceeded")

    def extract_amazon_image_id(self, url: str) -> str:
        """
        Extract the unique image ID from an Amazon image URL.

        Args:
            url: Amazon image URL (e.g., https://m.media-amazon.com/images/I/61wixnPXtlL.jpg)

        Returns:
            Image ID (e.g., 61wixnPXtlL)
        """
        parsed = urlparse(url)
        filename = Path(parsed.path).stem  # Get filename without extension
        return filename

    def generate_asset_filename(self, url: str, index: int) -> str:
        """
        Generate a consistent filename for the asset based on Amazon image ID.

        Matches MCA0032 convention: amazon_{priority:02d}_{slot}_{image_id}.ext
        Position first for alphabetical sorting.

        Args:
            url: Amazon image URL
            index: Image index (0-based)

        Returns:
            Standardized filename (e.g., amazon_01_MAIN_61wixnPXtlL.jpg)
        """
        image_id = self.extract_amazon_image_id(url)
        ext = Path(urlparse(url).path).suffix or '.jpg'

        # Get slot info from mapping
        slot_name, priority = IMAGE_SLOTS.get(index, (f'IMG{index:02d}', index + 11))

        # Position first for alphabetical sorting: amazon_01_MAIN_61wixnPXtlL.jpg
        return f"amazon_{priority:02d}_{slot_name}_{image_id}{ext}"

    def build_asset_index(self) -> None:
        """
        Pre-fetch all Amazon asset filenames to avoid per-image API calls.

        Searches for all assets with "amazon_" prefix and caches them.
        This replaces N individual API calls with a single paginated fetch.
        """
        if self._filename_to_asset:
            logger.debug("Asset index already populated, skipping build")
            return

        logger.info("Building asset filename index...")

        page = 1
        total_found = 0

        while True:
            # Wait for global pause before starting
            self._global_pause.wait_if_paused()
            self.rate_limiter.acquire()

            try:
                result = self.api.search_assets(
                    filters=[{'field': 'filename', 'operator': 'like', 'value': 'amazon_'}],
                    limit=100,
                    page=page,
                )

                assets = result.get('data', [])
                if not assets:
                    break

                for asset in assets:
                    filename = asset.get('filename')
                    asset_id = asset.get('id')
                    if filename and asset_id:
                        self._filename_to_asset[filename] = asset_id
                        total_found += 1

                page += 1

                # Configurable safety limit (default 1000 pages = 100K assets)
                max_pages = self.config.asset_index_max_pages
                if page > max_pages:
                    logger.warning(f"Reached page limit ({max_pages}) for asset index, stopping")
                    break

            except Exception as e:
                # Check if it's a rate limit error
                retry_after = self._extract_retry_after(e)
                if retry_after is not None:
                    if retry_after > MAX_RETRY_WAIT:
                        logger.warning(
                            f"Rate limit {retry_after}s exceeds max wait {MAX_RETRY_WAIT}s on asset index page {page}, "
                            f"stopping with {total_found} assets indexed"
                        )
                        break
                    logger.warning(f"Rate limit hit on asset index page {page}, pausing for {retry_after}s")
                    self._global_pause.trigger_pause(retry_after, "asset_index_build")
                    # Continue after pause instead of breaking
                    continue
                else:
                    logger.warning(f"Error building asset index at page {page}: {e}")
                    break

        logger.info(f"Asset index built: {total_found} amazon assets cached")

    def build_products_with_assets_index(self) -> None:
        """
        Pre-fetch all products that have assets linked.

        Uses search filter with exists operator instead of per-product API calls.
        This replaces N individual get_product_assets() calls with paginated search.

        Note: The 'assets' field is an ObjectIdAttribute (relation), not an array,
        so we use 'exists' operator instead of 'len_gte'.
        """
        if self._products_with_images:
            logger.debug("Products-with-assets index already populated, skipping build")
            return

        logger.info("Building products-with-assets index...")

        page = 1
        total_found = 0

        while True:
            # Wait for global pause before starting
            self._global_pause.wait_if_paused()
            self.rate_limiter.acquire()

            try:
                # Find products with assets linked (exists operator for ObjectId relation)
                result = self.api.search_products(
                    filters=[{'field': 'assets', 'operator': 'exists'}],
                    limit=100,
                    page=page,
                )

                products = result.get('data', [])
                if not products:
                    break

                for product in products:
                    product_id = product.get('id')
                    if product_id:
                        self._products_with_images.add(product_id)
                        total_found += 1

                # Check if there are more pages
                pagination = result.get('pagination', {})
                if not pagination.get('has_next', False):
                    break

                page += 1

                # Safety limit (same as asset index)
                max_pages = self.config.asset_index_max_pages
                if page > max_pages:
                    logger.warning(f"Reached page limit ({max_pages}) for products-with-assets index, stopping")
                    break

            except Exception as e:
                # Check if it's a rate limit error
                retry_after = self._extract_retry_after(e)
                if retry_after is not None:
                    if retry_after > MAX_RETRY_WAIT:
                        logger.warning(
                            f"Rate limit {retry_after}s exceeds max wait {MAX_RETRY_WAIT}s on products-with-assets index page {page}, "
                            f"stopping with {total_found} products indexed"
                        )
                        break
                    logger.warning(f"Rate limit hit on products-with-assets index page {page}, pausing for {retry_after}s")
                    self._global_pause.trigger_pause(retry_after, "products_with_assets_index_build")
                    # Continue after pause instead of breaking
                    continue
                else:
                    logger.warning(f"Error building products-with-assets index at page {page}: {e}")
                    break

        logger.info(f"Products-with-assets index built: {total_found} products with images cached")

    def find_existing_asset(self, filename: str) -> Optional[str]:
        """
        Check if an asset with this filename already exists.

        Uses pre-built index only - no live API calls.

        Args:
            filename: Asset filename to search for

        Returns:
            Asset ID if found, None otherwise
        """
        # Only use cached index - no live API calls
        return self._filename_to_asset.get(filename)

    def load_images(
        self,
        amazon_product: AmazonProduct,
        plytix_product: PlytixProduct,
    ) -> Tuple[int, List[str]]:
        """
        Upload and link images for a product.

        Args:
            amazon_product: Source Amazon product with image URLs
            plytix_product: Target Plytix product

        Returns:
            Tuple of (images_uploaded, asset_ids)
        """
        if not self.config.images_sync_enabled:
            return 0, []

        if not amazon_product.image_urls:
            return 0, []

        if not plytix_product.id:
            logger.warning(f"Cannot load images - no product ID for {plytix_product.sku}")
            return 0, []

        # Skip if already has images and configured to skip
        # Uses pre-built index only - no per-product API calls
        if self.config.skip_existing_images:
            if plytix_product.id in self._products_with_images:
                logger.debug(f"Skipping images for {plytix_product.sku} - already has images")
                return 0, []

        asset_ids = []
        uploaded_count = 0

        # Limit to max images
        image_urls = amazon_product.image_urls[:self.config.max_images_per_product]

        for i, url in enumerate(image_urls):
            asset_id = self._upload_image(url, amazon_product.asin, i, plytix_product.id)
            if asset_id:
                asset_ids.append(asset_id)
                uploaded_count += 1

        if asset_ids:
            # Link assets to product
            self._link_assets_to_product(plytix_product.id, asset_ids)

            # Set first as thumbnail if configured
            if self.config.set_first_as_thumbnail:
                self._set_thumbnail(plytix_product.id, asset_ids[0])

            # Also set main image attribute if configured
            if self.config.main_image_attribute:
                self._set_main_image_attribute(
                    plytix_product.id,
                    asset_ids[0],
                    self.config.main_image_attribute
                )

            self._products_with_images.add(plytix_product.id)

        return uploaded_count, asset_ids

    def _upload_image(
        self,
        url: str,
        asin: str,
        index: int,
        product_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Upload a single image from URL with standardized filename.

        Args:
            url: Image URL
            asin: ASIN for logging
            index: Image index for naming
            product_id: Plytix product ID (for retry queue)

        Returns:
            Asset ID or None if failed
        """
        # Wait for any global rate limit pause first
        self._global_pause.wait_if_paused()

        # Check URL cache first (same image may be used by multiple products)
        if url in self._url_to_asset:
            logger.debug(f"Using cached asset for URL: {url[:50]}...")
            return self._url_to_asset[url]

        # Generate standardized filename
        filename = self.generate_asset_filename(url, index)
        slot_name, _ = IMAGE_SLOTS.get(index, (f'IMG{index:02d}', index + 11))

        # Check if asset with this filename already exists
        if self.config.skip_existing_images:
            existing_id = self.find_existing_asset(filename)
            if existing_id:
                logger.debug(f"Asset already exists: {filename}")
                self._url_to_asset[url] = existing_id
                return existing_id

        # Build metadata
        image_id = self.extract_amazon_image_id(url)
        metadata = {
            'alt_text': f"Amazon product image {image_id}",
            'public': True,
            'description': f"Source: Amazon | Image ID: {image_id} | Slot: {slot_name}"
        }

        def _do_upload():
            self.rate_limiter.acquire()
            return self.api.upload_asset_url(url, filename, metadata)

        try:
            result = self._with_retry(_do_upload, f"upload_image_{asin}_{index}")

            # Handle various response formats
            asset_id = None
            if isinstance(result, list) and result:
                asset_id = result[0].get('id')
            elif isinstance(result, dict):
                data = result.get('data', result)
                if isinstance(data, list) and data:
                    asset_id = data[0].get('id')
                elif isinstance(data, dict):
                    asset_id = data.get('id')

            if asset_id:
                self._filename_to_asset[filename] = asset_id
                self._url_to_asset[url] = asset_id
                logger.debug(f"Uploaded image {index} for {asin}: {filename} -> {asset_id}")
                return asset_id
            else:
                logger.warning(f"No asset ID returned for {filename}")
                return None

        except RateLimitExceeded:
            # Queue for retry instead of permanently skipping
            if product_id:
                self._rate_limited_images.append((url, asin, index, product_id))
                logger.info(f"Queued rate-limited image for retry: {asin}_{index}")
            else:
                logger.warning(f"Rate limit exceeded for image upload {asin}_{index}, skipping (no product_id)")
            return None

        except Exception as e:
            logger.warning(f"Failed to upload image for {asin}: {e}")
            return None

    def _link_assets_to_product(
        self,
        product_id: str,
        asset_ids: List[str],
    ) -> None:
        """
        Link assets to product's media gallery.

        Args:
            product_id: Plytix product ID
            asset_ids: List of asset IDs to link
        """
        if not asset_ids:
            return

        def _do_link():
            self.rate_limiter.acquire()
            self.api.add_product_assets(
                product_id=product_id,
                asset_ids=asset_ids,
                attribute_label=self.config.amazon_images_attribute,
            )

        try:
            self._with_retry(_do_link, f"link_assets_{product_id}")
            logger.debug(f"Linked {len(asset_ids)} assets to product {product_id}")

        except RateLimitExceeded:
            logger.warning(f"Rate limit exceeded for linking assets to {product_id}, skipping")

        except Exception as e:
            logger.warning(f"Failed to link assets to product {product_id}: {e}")

    def _set_thumbnail(self, product_id: str, asset_id: str) -> None:
        """
        Set product thumbnail.

        Args:
            product_id: Plytix product ID
            asset_id: Asset ID to use as thumbnail
        """
        def _do_set_thumbnail():
            self.rate_limiter.acquire()
            # The API wrapper auto-wraps string to {'id': asset_id}
            self.api.update_product(product_id, {"thumbnail": asset_id})

        try:
            self._with_retry(_do_set_thumbnail, f"set_thumbnail_{product_id}")
            logger.debug(f"Set thumbnail for product {product_id}")

        except RateLimitExceeded:
            logger.warning(f"Rate limit exceeded for setting thumbnail on {product_id}, skipping")

        except Exception as e:
            logger.warning(f"Failed to set thumbnail for {product_id}: {e}")

    def _set_main_image_attribute(
        self,
        product_id: str,
        asset_id: str,
        attribute_label: str
    ) -> None:
        """
        Set main image attribute (MediaGalleryAttribute).

        Args:
            product_id: Plytix product ID
            asset_id: Asset ID to use as main image
            attribute_label: Attribute label (e.g., 'amazon_main_image_test')
        """
        def _do_set_main_image():
            self.rate_limiter.acquire()
            # For MediaGalleryAttribute, link the asset to the product attribute
            self.api.add_product_assets(
                product_id=product_id,
                asset_ids=[asset_id],
                attribute_label=attribute_label,
            )

        try:
            self._with_retry(_do_set_main_image, f"set_main_image_{product_id}")
            logger.debug(f"Set {attribute_label} for product {product_id}")

        except RateLimitExceeded:
            logger.warning(f"Rate limit exceeded for setting {attribute_label} on {product_id}, skipping")

        except Exception as e:
            logger.warning(f"Failed to set {attribute_label} for {product_id}: {e}")

    def load_images_batch(
        self,
        products: List[Tuple[AmazonProduct, PlytixProduct]],
        on_progress: Optional[callable] = None,
    ) -> Dict[str, any]:
        """
        Load images for multiple products in parallel.

        Args:
            products: List of (AmazonProduct, PlytixProduct) tuples
            on_progress: Optional callback(completed, total, status) - status is SyncStatus enum

        Returns:
            Summary of results
        """
        # Build indexes upfront to avoid per-product API calls
        self.build_asset_index()
        self.build_products_with_assets_index()

        results = {
            "total_products": len(products),
            "products_with_images": 0,
            "images_uploaded": 0,
            "images_skipped": 0,
            "errors": [],
        }

        # Thread-safe progress tracking
        progress_lock = threading.Lock()
        completed_count = 0
        results_lock = threading.Lock()

        def process_product_images(product_pair: Tuple[AmazonProduct, PlytixProduct]) -> Tuple[str, int, Optional[str]]:
            """Process images for a single product with rate limiting and delay."""
            nonlocal completed_count

            amazon, plytix = product_pair
            error = None

            try:
                # Rate limiting handled by load_images
                count, asset_ids = self.load_images(amazon, plytix)

                # Determine status based on result
                if count > 0:
                    status = SyncStatus.SUCCESS
                elif not amazon.image_urls:
                    status = SyncStatus.SKIPPED  # No images to upload
                else:
                    status = SyncStatus.SKIPPED  # Product already has images

                # Update progress (thread-safe)
                with progress_lock:
                    completed_count += 1
                    current_count = completed_count

                    if on_progress:
                        on_progress(current_count, len(products), status)

                # Small delay between products (rate limiter handles concurrency)
                time.sleep(0.05)

                return plytix.sku, count, None

            except Exception as e:
                error = str(e)
                logger.warning(f"Error loading images for {plytix.sku}: {e}")

                # Report failure status
                with progress_lock:
                    completed_count += 1
                    current_count = completed_count

                    if on_progress:
                        on_progress(current_count, len(products), SyncStatus.FAILED)

                return plytix.sku, 0, error

        # Process products in parallel (2 workers based on burst=2)
        logger.debug(f"Processing images for {len(products)} products with 2 parallel workers")

        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit all tasks
            futures = [executor.submit(process_product_images, product_pair) for product_pair in products]

            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    sku, count, error = future.result()

                    # Update results (thread-safe)
                    with results_lock:
                        if error:
                            results["errors"].append({
                                "sku": sku,
                                "error": error,
                            })
                        elif count > 0:
                            results["products_with_images"] += 1
                            results["images_uploaded"] += count

                except Exception as e:
                    # Handle unexpected errors in worker
                    with results_lock:
                        results["errors"].append({
                            "sku": "unknown",
                            "error": f"Worker exception: {str(e)}",
                        })
                    logger.error(f"Worker exception: {e}")

        logger.info(
            f"Image loading complete: {results['images_uploaded']} images "
            f"for {results['products_with_images']} products"
        )

        return results

    def check_existing_images(self, product_ids: List[str]) -> None:
        """
        Check which products already have images.

        DEPRECATED: Use build_products_with_assets_index() instead.
        This method now delegates to the bulk index builder.

        Args:
            product_ids: List of product IDs to check (ignored, index is built globally)
        """
        logger.info("check_existing_images() is deprecated, using build_products_with_assets_index()")
        self.build_products_with_assets_index()
        logger.info(f"Found {len(self._products_with_images)} products with existing images")

    def get_rate_limited_images(self) -> List[Tuple[str, str, int, str]]:
        """
        Get list of images that were rate-limited during upload.

        Returns:
            List of (url, asin, index, product_id) tuples
        """
        return self._rate_limited_images.copy()

    def set_rate_limited_images(self, items: List[Tuple[str, str, int, str]]) -> None:
        """
        Restore rate-limited images queue from checkpoint.

        Args:
            items: List of (url, asin, index, product_id) tuples
        """
        self._rate_limited_images = [(str(item[0]), str(item[1]), int(item[2]), str(item[3])) for item in items]
        if self._rate_limited_images:
            logger.info(f"Restored {len(self._rate_limited_images)} rate-limited images from checkpoint")

    def retry_rate_limited_images(self) -> Dict[str, int]:
        """
        Retry uploading rate-limited images with slower pacing.

        Should be called after a cooldown period (e.g., 60 seconds).

        Returns:
            Dict with 'success', 'failed', 'still_limited' counts
        """
        if not self._rate_limited_images:
            return {"success": 0, "failed": 0, "still_limited": 0}

        results = {"success": 0, "failed": 0, "still_limited": 0}

        # Take a snapshot of items to retry and clear the queue
        # (new rate-limited items will be re-added during retry)
        items_to_retry = self._rate_limited_images.copy()
        self._rate_limited_images.clear()

        logger.info(f"Retrying {len(items_to_retry)} rate-limited images...")

        for url, asin, index, product_id in items_to_retry:
            # Slower pacing for retries
            time.sleep(0.5)

            try:
                asset_id = self._upload_image(url, asin, index, product_id)

                if asset_id:
                    # Successfully uploaded - link to product
                    self._link_assets_to_product(product_id, [asset_id])
                    results["success"] += 1
                    logger.debug(f"Retry succeeded for {asin}_{index}")
                else:
                    # _upload_image returns None for rate limit (re-queued) or other failure
                    # Check if it was re-queued
                    if any(item[1] == asin and item[2] == index for item in self._rate_limited_images):
                        results["still_limited"] += 1
                    else:
                        results["failed"] += 1

            except Exception as e:
                logger.warning(f"Retry failed for {asin}_{index}: {e}")
                results["failed"] += 1

        logger.info(
            f"Image retry complete: {results['success']} succeeded, "
            f"{results['failed']} failed, {results['still_limited']} still rate-limited"
        )

        return results
