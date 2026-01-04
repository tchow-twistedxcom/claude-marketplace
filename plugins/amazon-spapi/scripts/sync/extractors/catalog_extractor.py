"""
Catalog Extractor
=================

Extracts product data from Amazon SP-API Catalog Items endpoint.
"""

import logging
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from spapi_auth import SPAPIAuth
from spapi_catalog import CatalogItemsAPI
from spapi_client import SPAPIClient
from spapi_reports import ReportsAPI

# Pre-compiled regex patterns (avoid recompilation in loops)
IMAGE_ID_PATTERN = re.compile(r'/images/I/([A-Za-z0-9]+)')

# Safe included data for get_catalog_item (excludes 'variations' which causes errors)
SAFE_CATALOG_INCLUDED_DATA = [
    'attributes',
    'dimensions',
    'identifiers',
    'images',
    'productTypes',
    'relationships',
    'salesRanks',
    'summaries',
]

from ..models import AmazonProduct, SyncConfig
from .batch_processor import BatchProcessor, RateLimiter

logger = logging.getLogger(__name__)


class CatalogExtractor:
    """
    Extracts Amazon catalog data via SP-API.

    Features:
    - Batch ASIN fetching with rate limiting
    - Parent ASIN discovery for variations
    - Full product data extraction
    - Checkpoint integration
    """

    def __init__(
        self,
        config: SyncConfig,
        profile: str = "production",
    ):
        """
        Initialize catalog extractor.

        Args:
            config: Sync configuration
            profile: SP-API profile name
        """
        self.config = config
        self.auth = SPAPIAuth(profile=profile)
        self.client = SPAPIClient(self.auth)
        self.catalog_api = CatalogItemsAPI(self.client)

        # Rate limiter for API calls
        self.rate_limiter = RateLimiter(
            rate=config.spapi_rate_limit,
            burst=5
        )

        # Batch processor
        self.batch_processor = BatchProcessor(
            batch_size=config.batch_size,
            delay_between_batches=config.delay_between_batches,
            max_retries=config.max_retries,
            retry_delay=config.retry_delay_seconds,
        )

        # Data sections to include (use safe list without 'variations')
        self.included_data = SAFE_CATALOG_INCLUDED_DATA

    def extract_by_asins(
        self,
        asins: List[str],
        skip_asins: Optional[Set[str]] = None,
    ) -> List[AmazonProduct]:
        """
        Extract product data for a list of ASINs.

        Args:
            asins: List of ASINs to fetch
            skip_asins: ASINs to skip (already processed)

        Returns:
            List of AmazonProduct objects
        """
        # Filter out already processed
        if skip_asins:
            asins = [a for a in asins if a not in skip_asins]

        if not asins:
            logger.info("No ASINs to process")
            return []

        logger.info(f"Extracting {len(asins)} ASINs")

        products = []

        def process_batch(batch: List[str]) -> List[AmazonProduct]:
            """Process a batch of ASINs."""
            batch_products = []
            for asin in batch:
                product = self._fetch_single_asin(asin)
                if product:
                    batch_products.append(product)
            return batch_products

        def on_batch_complete(batch_num: int, total: int, results: List[AmazonProduct]):
            logger.info(
                f"Batch {batch_num}/{total}: Extracted {len(results)} products"
            )

        products = self.batch_processor.process_batches(
            items=asins,
            processor=process_batch,
            on_batch_complete=on_batch_complete,
        )

        logger.info(f"Extracted {len(products)} products total")
        return products

    def _fetch_single_asin(self, asin: str) -> Optional[AmazonProduct]:
        """
        Fetch data for a single ASIN.

        Args:
            asin: Amazon ASIN

        Returns:
            AmazonProduct or None if failed
        """
        self.rate_limiter.acquire()

        try:
            data = self.catalog_api.get_catalog_item(
                asin=asin,
                included_data=self.included_data,
            )
            return self._parse_catalog_item(asin, data)

        except Exception as e:
            logger.warning(f"Failed to fetch ASIN {asin}: {e}")
            return None

    def _parse_catalog_item(self, asin: str, data: Dict[str, Any]) -> AmazonProduct:
        """
        Parse SP-API catalog item response into AmazonProduct.

        Args:
            asin: The ASIN
            data: Raw API response

        Returns:
            Parsed AmazonProduct
        """
        product = AmazonProduct(asin=asin, raw_data=data)

        # Parse summaries (basic info)
        summaries = data.get("summaries", [])
        if summaries:
            summary = summaries[0]  # First marketplace summary
            product.item_name = summary.get("itemName")
            product.brand = summary.get("brand")
            product.manufacturer = summary.get("manufacturer")
            product.model_number = summary.get("modelNumber")

        # Parse identifiers (UPC, EAN, GTIN)
        identifiers = data.get("identifiers", [])
        for id_group in identifiers:
            for identifier in id_group.get("identifiers", []):
                id_type = identifier.get("identifierType", "").upper()
                id_value = identifier.get("identifier")
                if id_type == "UPC":
                    product.upc = id_value
                elif id_type == "EAN":
                    product.ean = id_value
                elif id_type == "GTIN":
                    product.gtin = id_value

        # Parse images
        images = data.get("images", [])
        seen_image_ids = set()  # Track unique image IDs to prevent duplicates
        seen_urls = set()  # O(1) URL deduplication (vs O(n) list check)
        main_images = []  # MAIN/LARGE images (added first)
        other_images = []  # Other variant images

        for img_group in images:
            for image in img_group.get("images", []):
                variant = image.get("variant", "")
                link = image.get("link")
                if link:
                    # Skip thumbnail/small variants (e.g., _SL75_, _SL100_)
                    if "_SL75_" in link or "_SL100_" in link:
                        continue

                    # Extract image ID for deduplication using pre-compiled regex
                    match = IMAGE_ID_PATTERN.search(link)
                    if match:
                        image_id = match.group(1)
                        if image_id in seen_image_ids:
                            continue
                        seen_image_ids.add(image_id)

                    # Use set for O(1) URL deduplication
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)

                    # Separate main/large from others for priority ordering
                    if variant in ("MAIN", "LARGE"):
                        main_images.append(link)
                    else:
                        other_images.append(link)

        # Combine: main images first, then others
        product.image_urls = main_images + other_images

        # Limit to max images
        product.image_urls = product.image_urls[:self.config.max_images_per_product]

        # Parse product types
        product_types = data.get("productTypes", [])
        if product_types:
            product.product_type = product_types[0].get("productType")

        # Parse relationships (parent/child)
        relationships = data.get("relationships", [])
        for rel_group in relationships:
            for relationship in rel_group.get("relationships", []):
                rel_type = relationship.get("type")
                child_asins = relationship.get("childAsins", [])

                if rel_type == "VARIATION_PARENT":
                    product.is_parent = True
                    product.child_asins = child_asins

        # Parse variations (for child items with parent reference)
        variations = data.get("variations", [])
        for var_group in variations:
            # Get parent ASIN
            parent_asin = None
            parent_info = var_group.get("variationParent")
            if parent_info:
                parent_asin = parent_info.get("asin")

            if parent_asin and parent_asin != asin:
                product.parent_asin = parent_asin

            # Get variation theme
            product.variation_theme = var_group.get("variationTheme", {}).get("name")

        # Parse attributes for variation details
        attributes = data.get("attributes", {})
        if attributes:
            # Color
            color_val = attributes.get("color", [])
            if color_val and isinstance(color_val, list):
                product.color = color_val[0].get("value")

            # Size
            size_val = attributes.get("size", [])
            if size_val and isinstance(size_val, list):
                product.size = size_val[0].get("value")

            # Bullet points
            bullets = attributes.get("bullet_point", [])
            if bullets and isinstance(bullets, list):
                product.bullet_points = [b.get("value") for b in bullets if b.get("value")]

            # Description
            desc = attributes.get("product_description", [])
            if desc and isinstance(desc, list):
                product.product_description = desc[0].get("value")

        # Parse dimensions
        dimensions = data.get("dimensions", [])
        if dimensions:
            dim = dimensions[0]
            product.item_dimensions = {
                "height": dim.get("height"),
                "width": dim.get("width"),
                "length": dim.get("length"),
                "weight": dim.get("weight"),
            }

        return product

    def discover_parent_asins(self, products: List[AmazonProduct]) -> Set[str]:
        """
        Find parent ASINs from extracted products.

        Args:
            products: List of extracted products

        Returns:
            Set of parent ASINs not yet in the product list
        """
        existing_asins = {p.asin for p in products}
        parent_asins = set()

        for product in products:
            if product.parent_asin and product.parent_asin not in existing_asins:
                parent_asins.add(product.parent_asin)

        logger.info(f"Discovered {len(parent_asins)} parent ASINs")
        return parent_asins

    def extract_by_brand(
        self,
        brand_name: str,
        max_results: int = 10000,
        use_categories: bool = True,
    ) -> List[AmazonProduct]:
        """
        Extract all products for a brand.

        Args:
            brand_name: Brand name to search
            max_results: Maximum products to return (default 10000, use 0 for unlimited)
            use_categories: If True, search by category to bypass 1000 pagination limit

        Returns:
            List of AmazonProduct objects
        """
        # 0 means unlimited
        if max_results == 0:
            max_results = float('inf')

        logger.info(f"Searching for brand: {brand_name} (max: {max_results}, use_categories: {use_categories})")

        # Use category-based search to bypass Amazon's 1000 result pagination limit
        if use_categories:
            asins = self._search_brand_by_categories(brand_name, max_results)
        else:
            asins = self._search_brand_simple(brand_name, max_results)

        logger.info(f"Found {len(asins)} unique ASINs for brand '{brand_name}'")

        # Now fetch full details for each
        return self.extract_by_asins(asins)

    def _get_brand_categories(self, brand_name: str) -> List[Dict[str, Any]]:
        """
        Get available categories (refinements) for a brand.

        Args:
            brand_name: Brand name to search

        Returns:
            List of category refinements with id, name, and count
        """
        self.rate_limiter.acquire()

        try:
            result = self.catalog_api.search_catalog_items(
                keywords=[brand_name],
                brand_names=[brand_name],
                included_data=["summaries"],
                page_size=1,  # Only need refinements, not items
            )

            refinements = result.get("refinements", {})
            classifications = refinements.get("classifications", [])

            categories = []
            for cat in classifications:
                categories.append({
                    "id": cat.get("classificationId"),
                    "name": cat.get("displayName"),
                    "count": cat.get("numberOfResults", 0),
                })

            # Sort by count descending
            categories.sort(key=lambda x: x["count"], reverse=True)

            logger.info(f"Found {len(categories)} categories for brand '{brand_name}':")
            for cat in categories[:10]:  # Log top 10
                logger.info(f"  - {cat['name']}: {cat['count']} products")

            return categories

        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []

    def _search_brand_by_categories(
        self,
        brand_name: str,
        max_results: float,
    ) -> List[str]:
        """
        Search brand products using hierarchical classification drilling.

        Amazon SP-API limits pagination to ~1000 results per search.
        This method drills into sub-classifications to find categories
        with <1000 products, allowing complete extraction.

        Args:
            brand_name: Brand name to search
            max_results: Maximum products to return

        Returns:
            List of unique ASINs
        """
        # Get all usable classifications recursively
        usable, problematic = self._get_all_usable_classifications(brand_name)

        if not usable and not problematic:
            logger.warning("No classifications found, falling back to simple search")
            return self._search_brand_simple(brand_name, max_results)

        all_asins: Set[str] = set()

        # First, search all usable classifications (<1000 products each)
        logger.info(f"Searching {len(usable)} usable classifications (<1000 each)...")
        for cat in usable:
            if len(all_asins) >= max_results:
                break

            category_asins = self._search_in_category(
                brand_name=brand_name,
                classification_id=cat["id"],
                max_results=1000,
            )

            before = len(all_asins)
            all_asins.update(category_asins)
            new_count = len(all_asins) - before

            if new_count > 0:
                logger.info(
                    f"  {cat['name']}: +{new_count} new (total: {len(all_asins)})"
                )

        # Then search problematic classifications (>1000 products)
        # We'll get up to 999 from each, which may include some new ASINs
        if problematic and len(all_asins) < max_results:
            logger.info(f"Searching {len(problematic)} large classifications (>1000)...")
            for cat in problematic:
                if len(all_asins) >= max_results:
                    break

                category_asins = self._search_in_category(
                    brand_name=brand_name,
                    classification_id=cat["id"],
                    max_results=1000,  # Will get up to 999
                )

                before = len(all_asins)
                all_asins.update(category_asins)
                new_count = len(all_asins) - before

                if new_count > 0:
                    logger.info(
                        f"  {cat['name']}: +{new_count} new (total: {len(all_asins)})"
                    )

        logger.info(f"Total unique ASINs found: {len(all_asins)}")
        return list(all_asins)[:int(max_results) if max_results != float('inf') else None]

    def _get_all_usable_classifications(
        self,
        brand_name: str,
        max_depth: int = 5,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Recursively find all classifications, separating usable (<1000) from problematic.

        Args:
            brand_name: Brand name to search
            max_depth: Maximum recursion depth

        Returns:
            Tuple of (usable_classifications, problematic_classifications)
        """
        usable = []
        problematic = []
        visited_ids = set()  # Avoid duplicate classification IDs

        def get_sub_classifications(class_id: str) -> List[Dict[str, Any]]:
            """Get sub-classifications for a classification ID."""
            self.rate_limiter.acquire()
            try:
                result = self.catalog_api.search_catalog_items(
                    keywords=[brand_name],
                    brand_names=[brand_name],
                    classification_ids=[class_id],
                    included_data=["summaries"],
                    page_size=1,
                )
                return result.get("refinements", {}).get("classifications", [])
            except Exception as e:
                logger.warning(f"Error getting sub-classifications: {e}")
                return []

        def drill_classification(class_id: str, name: str, count: int, depth: int):
            """Recursively drill into a classification."""
            if class_id in visited_ids:
                return
            visited_ids.add(class_id)

            if count <= 1000:
                usable.append({"id": class_id, "name": name, "count": count})
                return

            if depth >= max_depth:
                problematic.append({"id": class_id, "name": name, "count": count})
                return

            # Try to find sub-classifications
            subs = get_sub_classifications(class_id)
            if not subs:
                problematic.append({"id": class_id, "name": name, "count": count})
                return

            for sub in subs:
                sub_id = sub.get("classificationId")
                sub_name = sub.get("displayName")
                sub_count = sub.get("numberOfResults", 0)
                full_name = f"{name} > {sub_name}"
                drill_classification(sub_id, full_name, sub_count, depth + 1)

        # Start with top-level classifications
        top_classifications = self._get_brand_categories(brand_name)
        logger.info(f"Found {len(top_classifications)} top-level categories")

        for cat in top_classifications:
            drill_classification(
                cat["id"],
                cat["name"],
                cat["count"],
                depth=0,
            )

        logger.info(f"Classification analysis: {len(usable)} usable, {len(problematic)} problematic")
        return usable, problematic

    def _search_in_category(
        self,
        brand_name: str,
        classification_id: str,
        max_results: int = 1000,
    ) -> List[str]:
        """
        Search for brand products within a specific category.

        Args:
            brand_name: Brand name to search
            classification_id: Amazon browse node ID
            max_results: Maximum results (capped at 1000 by Amazon)

        Returns:
            List of ASINs in this category
        """
        asins = []
        page_token = None

        while len(asins) < max_results:
            self.rate_limiter.acquire()

            try:
                result = self.catalog_api.search_catalog_items(
                    keywords=[brand_name],
                    brand_names=[brand_name],
                    classification_ids=[classification_id],
                    included_data=["identifiers"],
                    page_size=20,
                    page_token=page_token,
                )

                items = result.get("items", [])
                if not items:
                    break

                for item in items:
                    asin = item.get("asin")
                    if asin:
                        asins.append(asin)

                # Get next page
                pagination = result.get("pagination", {})
                page_token = pagination.get("nextToken")

                if not page_token:
                    break

            except Exception as e:
                logger.warning(f"Error searching category {classification_id}: {e}")
                break

        return asins

    def _search_brand_simple(
        self,
        brand_name: str,
        max_results: float,
    ) -> List[str]:
        """
        Simple brand search without category filtering.
        Limited to ~1000 results due to Amazon pagination.

        Args:
            brand_name: Brand name to search
            max_results: Maximum products to return

        Returns:
            List of ASINs
        """
        all_items = []
        page_token = None

        while len(all_items) < max_results:
            self.rate_limiter.acquire()

            try:
                # SP-API requires keywords OR identifiers - use brand name as keywords
                result = self.catalog_api.search_catalog_items(
                    keywords=[brand_name],
                    brand_names=[brand_name],
                    included_data=["identifiers", "summaries"],
                    page_size=20,
                    page_token=page_token,
                )

                items = result.get("items", [])
                if not items:
                    break

                all_items.extend(items)
                logger.info(f"Found {len(all_items)} items so far...")

                # Get next page
                pagination = result.get("pagination", {})
                page_token = pagination.get("nextToken")

                if not page_token:
                    break

            except Exception as e:
                logger.error(f"Error searching brand: {e}")
                break

        # Extract ASINs
        asins = [item.get("asin") for item in all_items if item.get("asin")]
        if max_results != float('inf'):
            asins = asins[:int(max_results)]

        return asins

    def extract_from_seller_report(
        self,
        brand_filter: Optional[str] = None,
    ) -> List[str]:
        """
        Extract ASINs from seller's listing report.

        This is the official Amazon approach for getting ALL seller listings
        without the 1000 result pagination limit that affects searchCatalogItems.

        Uses GET_MERCHANT_LISTINGS_ALL_DATA report.

        Args:
            brand_filter: Optional brand name to filter results

        Returns:
            List of ASINs from seller's inventory
        """
        logger.info("Requesting GET_MERCHANT_LISTINGS_ALL_DATA report...")

        reports_api = ReportsAPI(self.client)

        try:
            # Create and download the report
            content = reports_api.create_and_download_report(
                report_type="GET_MERCHANT_LISTINGS_ALL_DATA",
                timeout=900,  # 15 minutes max wait
            )

            # Parse tab-delimited report
            lines = content.strip().split('\n')
            if not lines:
                logger.warning("Empty report received")
                return []

            # First line is headers
            headers = lines[0].split('\t')

            # Find column indices
            asin_idx = None
            brand_idx = None
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if 'asin' in header_lower and asin_idx is None:
                    asin_idx = i
                if 'brand' in header_lower:
                    brand_idx = i

            if asin_idx is None:
                logger.error(f"ASIN column not found. Headers: {headers}")
                return []

            logger.info(f"Report has {len(lines)-1} listings")

            # Extract ASINs
            asins = []
            for line in lines[1:]:
                fields = line.split('\t')
                if len(fields) > asin_idx:
                    asin = fields[asin_idx].strip()
                    if asin:
                        # Apply brand filter if specified
                        if brand_filter and brand_idx is not None:
                            if len(fields) > brand_idx:
                                brand = fields[brand_idx].strip()
                                if brand_filter.lower() not in brand.lower():
                                    continue

                        asins.append(asin)

            logger.info(f"Extracted {len(asins)} ASINs from seller report")
            return asins

        except Exception as e:
            logger.error(f"Failed to get seller report: {e}")
            return []

    def load_asins_from_file(self, filepath: str) -> List[str]:
        """
        Load ASINs from a text file (one per line).

        Args:
            filepath: Path to ASIN list file

        Returns:
            List of ASINs
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"ASIN file not found: {filepath}")

        asins = []
        with open(path, 'r') as f:
            for line in f:
                asin = line.strip()
                if asin and not asin.startswith('#'):
                    asins.append(asin)

        logger.info(f"Loaded {len(asins)} ASINs from {filepath}")
        return asins

    def to_raw_data(self, products: List[AmazonProduct]) -> List[Dict[str, Any]]:
        """
        Convert products to raw dictionaries for JSON serialization.

        Args:
            products: List of AmazonProduct objects

        Returns:
            List of dictionaries
        """
        return [
            {
                "asin": p.asin,
                "parent_asin": p.parent_asin,
                "item_name": p.item_name,
                "brand": p.brand,
                "manufacturer": p.manufacturer,
                "model_number": p.model_number,
                "product_type": p.product_type,
                "upc": p.upc,
                "ean": p.ean,
                "gtin": p.gtin,
                "variation_theme": p.variation_theme,
                "color": p.color,
                "size": p.size,
                "is_parent": p.is_parent,
                "child_asins": p.child_asins,
                "bullet_points": p.bullet_points,
                "product_description": p.product_description,
                "item_dimensions": p.item_dimensions,
                "image_urls": p.image_urls,
            }
            for p in products
        ]
