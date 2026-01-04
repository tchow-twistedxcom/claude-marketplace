"""
Canonical Matcher
=================

Matches Amazon products to canonical Plytix products for linking.
"""

import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
# Path: sync/transformers/canonical_matcher.py -> ../../.. -> scripts -> ../.. -> plugins -> plytix-skills/...
plytix_path = Path(__file__).parent.parent.parent.parent.parent / "plytix-skills" / "skills" / "plytix-api" / "scripts"
sys.path.insert(0, str(plytix_path))

from plytix_api import PlytixAPI
from ..models import AmazonProduct, CanonicalMatch, PlytixProduct, SyncConfig

logger = logging.getLogger(__name__)

# Pre-compiled regex patterns (avoid recompilation in loops)
WIDTH_PATTERN = re.compile(r'\b\d+(?:\.\d+)?\s+([MDWCN]|EE|EEE)\b', re.IGNORECASE)
# Patterns to clean size field
SIZE_WIDE_PATTERN = re.compile(r'\s*Wide\s*$', re.IGNORECASE)
# Common width codes to try when matching (order: most common first)
WIDTH_VARIATIONS = ["M", "W", "EE", "D", "C", "N", "EEE", "B"]
# Pattern to extract size AND width from end of title
# Matches: "10.5 M", "13 D", "8 W", "11 EE", "9.5 Wide", etc.
TITLE_SIZE_WIDTH_PATTERN = re.compile(
    r',\s*(\d+(?:\.\d+)?)\s*([MDWBCN]|EE|EEE|Wide|Medium|Narrow)?\s*$',
    re.IGNORECASE
)


class CanonicalMatcher:
    """
    Matches Amazon products to canonical Plytix products.

    Matching priority (configurable):
    1. GTIN - Most reliable global identifier
    2. UPC - Common in US
    3. EAN - Common in Europe
    4. Model Number - Manufacturer's model
    5. model_to_sku - Amazon model_number matches canonical SKU directly
    6. SKU - Last resort (brand + model_number combination)

    Features:
    - In-memory index for fast lookups
    - Normalized identifier matching
    - Confidence scoring
    """

    def __init__(self, config: SyncConfig, api: Optional[PlytixAPI] = None):
        """
        Initialize matcher with configuration.

        Args:
            config: Sync configuration
            api: Optional Plytix API for fallback searches
        """
        self.config = config
        self.priority = config.matching_priority
        self.api = api or PlytixAPI()

        # Indexes for matching (identifier -> product_id)
        self._gtin_index: Dict[str, str] = {}
        self._upc_index: Dict[str, str] = {}
        self._ean_index: Dict[str, str] = {}
        self._model_index: Dict[str, str] = {}
        self._sku_index: Dict[str, str] = {}
        # SKU index that preserves format (for model_size matching)
        self._sku_exact_index: Dict[str, str] = {}

        # Full product cache
        self._products: Dict[str, Dict] = {}

        self._is_built = False

    def build_index(self, plytix_products: List[Dict]) -> None:
        """
        Build in-memory index from Plytix products.

        Args:
            plytix_products: List of Plytix product dictionaries
        """
        logger.info(f"Building canonical index from {len(plytix_products)} products")

        self._clear_indexes()

        tc_excluded = 0
        for product in plytix_products:
            product_id = product.get("id")
            if not product_id:
                continue

            # Get attributes - check both top-level (from search with attributes param)
            # and nested (from direct product fetch)
            attrs = product.get("attributes", {})
            sku = product.get("sku", "")

            # Skip products with excluded SKU prefixes (configurable via exclude_sku_prefixes)
            sku_upper = sku.upper()
            excluded = False
            for prefix in self.config.exclude_sku_prefixes:
                if sku_upper.startswith(prefix.upper()):
                    tc_excluded += 1
                    excluded = True
                    break
            if excluded:
                continue

            # Cache full product
            self._products[product_id] = product

            # Index by GTIN - check top-level first (search API), then nested attributes
            gtin = self._normalize(product.get("gtin") or attrs.get("gtin"))
            if gtin:
                self._gtin_index[gtin] = product_id

            # Index by UPC - check top-level first, then nested
            upc = self._normalize(product.get("upc") or attrs.get("upc"))
            if upc:
                self._upc_index[upc] = product_id

            # Index by EAN - check top-level first, then nested
            ean = self._normalize(product.get("ean") or attrs.get("ean"))
            if ean:
                self._ean_index[ean] = product_id

            # Index by model number - check top-level first, then nested
            model = self._normalize(
                product.get("model_number") or product.get("amazon_model_number") or
                attrs.get("model_number") or attrs.get("amazon_model_number")
            )
            if model:
                self._model_index[model] = product_id

            # Index by SKU (exclude AMZN- products - those are Amazon products)
            if sku and not sku.startswith("AMZN-"):
                self._sku_index[self._normalize(sku)] = product_id
                # Also store in exact index (uppercase but preserve dashes/dots)
                self._sku_exact_index[sku.upper().strip()] = product_id

        self._is_built = True

        excluded_prefixes = ", ".join(self.config.exclude_sku_prefixes) if self.config.exclude_sku_prefixes else "none"
        logger.info(
            f"Index built: {len(self._gtin_index)} GTIN, "
            f"{len(self._upc_index)} UPC, {len(self._ean_index)} EAN, "
            f"{len(self._model_index)} model, {len(self._sku_index)} SKU "
            f"(excluded {tc_excluded} products with prefixes: {excluded_prefixes})"
        )

    def _clear_indexes(self) -> None:
        """Clear all indexes."""
        self._gtin_index.clear()
        self._upc_index.clear()
        self._ean_index.clear()
        self._model_index.clear()
        self._sku_index.clear()
        self._sku_exact_index.clear()
        self._products.clear()

    def _normalize(self, value: Optional[str]) -> Optional[str]:
        """
        Normalize identifier for matching.

        Args:
            value: Raw identifier value

        Returns:
            Normalized value or None
        """
        if not value:
            return None

        # Convert to uppercase, strip whitespace
        normalized = str(value).upper().strip()

        if self.config.normalize_identifiers:
            # Remove non-alphanumeric (except X for check digits)
            normalized = re.sub(r'[^A-Z0-9]', '', normalized)

            # Strip leading zeros for numeric identifiers
            if normalized.isdigit():
                normalized = normalized.lstrip('0') or '0'

        return normalized if normalized else None

    def _normalize_size(self, size: str) -> str:
        """
        Normalize size for SKU matching.

        Handles:
        - Leading zeros for single-digit sizes: "7" -> "07", "7.5" -> "07.5"
        - Keep double-digit sizes as-is: "10", "12.5"

        Args:
            size: Raw size value

        Returns:
            Normalized size string
        """
        if not size:
            return size

        size = size.strip()

        # Check if size is a single digit (with optional decimal)
        # Pattern: exactly one digit, optionally followed by decimal portion
        # "7" -> match, "7.5" -> match, "12" -> no match, "10.5" -> no match
        if re.match(r'^\d(\.\d+)?$', size):
            # Single digit - add leading zero
            return f"0{size}"

        return size

    def _extract_size_width_from_title(self, title: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract size and width from Amazon product title.

        Title pattern: "... {color}, {size} {width}" at end
        Examples:
            "Twisted X Men's Boot, Bomber, 10.5 M" -> ("10.5", "M")
            "Twisted X Women's Shoe, Brown, 8 W" -> ("8", "W")
            "Twisted X Boot, 13 EE" -> ("13", "EE")
            "Twisted X Moc, Red, 9.5 Wide" -> ("9.5", "W")

        Args:
            title: Amazon product title

        Returns:
            Tuple of (size, width) - either can be None if not found
        """
        if not title:
            return None, None

        match = TITLE_SIZE_WIDTH_PATTERN.search(title)
        if not match:
            return None, None

        size = match.group(1)
        width = match.group(2)

        # Normalize width
        if width:
            width = width.upper()
            if width == "WIDE":
                width = "W"
            elif width == "MEDIUM":
                width = "M"
            elif width == "NARROW":
                width = "N"

        return size, width

    def match(self, amazon_product: AmazonProduct) -> CanonicalMatch:
        """
        Find canonical match for an Amazon product.

        Args:
            amazon_product: Amazon product to match

        Returns:
            CanonicalMatch with match details
        """
        if not self._is_built:
            logger.warning("Index not built - no matches possible")
            return CanonicalMatch(amazon_product=amazon_product)

        # Try each matching strategy in priority order
        for match_type in self.priority:
            product_id, confidence = self._try_match(amazon_product, match_type)
            if product_id:
                return CanonicalMatch(
                    amazon_product=amazon_product,
                    matched=True,
                    match_type=match_type,
                    match_confidence=confidence,
                    canonical_product_id=product_id,
                )

        # No match found
        return CanonicalMatch(amazon_product=amazon_product)

    def _try_match(
        self,
        amazon: AmazonProduct,
        match_type: str,
    ) -> Tuple[Optional[str], float]:
        """
        Try to match using specific identifier type.

        Args:
            amazon: Amazon product
            match_type: Type of match to attempt

        Returns:
            Tuple of (product_id, confidence) or (None, 0)
        """
        if match_type == "gtin":
            gtin = self._normalize(amazon.gtin)
            if gtin and gtin in self._gtin_index:
                return self._gtin_index[gtin], 1.0

        elif match_type == "upc":
            upc = self._normalize(amazon.upc)
            if upc:
                # Check UPC index first
                if upc in self._upc_index:
                    return self._upc_index[upc], 0.95
                # Also check GTIN index - many products store UPC in GTIN field
                if upc in self._gtin_index:
                    logger.debug(f"Matched Amazon UPC '{amazon.upc}' to canonical GTIN (from index)")
                    return self._gtin_index[upc], 0.95
                # Note: No live API fallback - accept orphans to avoid N+1 queries

        elif match_type == "ean":
            ean = self._normalize(amazon.ean)
            if ean:
                # Check EAN index first
                if ean in self._ean_index:
                    return self._ean_index[ean], 0.95
                # Also check GTIN index - EAN can be stored as GTIN
                if ean in self._gtin_index:
                    logger.debug(f"Matched Amazon EAN '{amazon.ean}' to canonical GTIN")
                    return self._gtin_index[ean], 0.95
                # Note: No live API fallback - accept orphans to avoid N+1 queries

        elif match_type == "model_number":
            model = self._normalize(amazon.model_number)
            if model and model in self._model_index:
                return self._model_index[model], 0.8

        elif match_type == "model_to_sku":
            # Direct match: Amazon model_number → canonical SKU
            # Common pattern: Twisted X products have SKU like "MDM0101"
            # and Amazon product has model_number = "MDM0101"
            model = self._normalize(amazon.model_number)
            if model and model in self._sku_index:
                logger.debug(f"Matched model_number '{amazon.model_number}' to canonical SKU")
                return self._sku_index[model], 0.85

        elif match_type == "model_size":
            # Pattern match: {model}-{width}-{size}
            # Example: MDM0033-M-13 = model_number + width(M) + size(13)
            # Get size/width from: 1) title (most reliable), 2) size field, 3) fallback
            model = amazon.model_number
            if not model:
                return None, 0.0

            # Extract size and width from title (most reliable source)
            title_size, title_width = self._extract_size_width_from_title(amazon.item_name)

            # Get size from title first, fallback to size field
            raw_size = amazon.size
            size = None

            if title_size:
                size = title_size
            elif raw_size:
                # Clean size field: remove "Wide" suffix
                size = SIZE_WIDE_PATTERN.sub('', raw_size).strip()

            if not size:
                return None, 0.0

            # Normalize size: add leading zero for single-digit sizes
            # "7.5" -> "07.5", "9" -> "09"
            size = self._normalize_size(size)

            # Determine width candidates to try (prioritized order)
            width_candidates = []

            # 1. Title width is most reliable (directly from product listing)
            if title_width:
                width_candidates.append(title_width)

            # 2. Check if size field had "Wide" -> indicates W width
            if raw_size and 'wide' in raw_size.lower() and "W" not in width_candidates:
                width_candidates.append("W")

            # 3. Try to extract width from item_name pattern "X M" or "X W" (backup)
            if amazon.item_name and not title_width:
                width_match = WIDTH_PATTERN.search(amazon.item_name)
                if width_match:
                    extracted = width_match.group(1).upper()
                    if extracted not in width_candidates:
                        width_candidates.append(extracted)

            # 4. Add remaining width variations to try
            for w in WIDTH_VARIATIONS:
                if w not in width_candidates:
                    width_candidates.append(w)

            # Try each width candidate using exact SKU format (preserve dashes)
            for width in width_candidates:
                potential_sku = f"{model}-{width}-{size}".upper()
                if potential_sku in self._sku_exact_index:
                    logger.info(f"Matched via model_size: {potential_sku}")
                    return self._sku_exact_index[potential_sku], 0.9

            # Also try without width for simpler patterns
            potential_sku2 = f"{model}-{size}".upper()
            if potential_sku2 in self._sku_exact_index:
                logger.info(f"Matched via model_size: {potential_sku2}")
                return self._sku_exact_index[potential_sku2], 0.88

        elif match_type == "sku":
            # Try brand + model as SKU pattern
            if amazon.brand and amazon.model_number:
                potential_sku = self._normalize(f"{amazon.brand}{amazon.model_number}")
                if potential_sku and potential_sku in self._sku_index:
                    return self._sku_index[potential_sku], 0.7

        return None, 0.0

    def match_batch(
        self,
        amazon_products: List[AmazonProduct],
    ) -> List[CanonicalMatch]:
        """
        Match multiple Amazon products.

        Args:
            amazon_products: List of Amazon products

        Returns:
            List of CanonicalMatch objects
        """
        matches = []
        matched_count = 0
        orphan_count = 0

        for product in amazon_products:
            match = self.match(product)
            matches.append(match)

            if match.matched:
                matched_count += 1
            else:
                orphan_count += 1

        logger.info(
            f"Matched {matched_count}/{len(amazon_products)} products, "
            f"{orphan_count} orphans"
        )

        return matches

    def get_canonical_product(self, product_id: str) -> Optional[Dict]:
        """
        Get cached canonical product by ID.

        Args:
            product_id: Plytix product ID

        Returns:
            Product dictionary or None
        """
        return self._products.get(product_id)

    def get_match_stats(self) -> Dict[str, int]:
        """Get statistics about matching indexes."""
        return {
            "gtin_entries": len(self._gtin_index),
            "upc_entries": len(self._upc_index),
            "ean_entries": len(self._ean_index),
            "model_entries": len(self._model_index),
            "sku_entries": len(self._sku_index),
            "total_products": len(self._products),
        }

    def is_built(self) -> bool:
        """Check if index has been built."""
        return self._is_built
