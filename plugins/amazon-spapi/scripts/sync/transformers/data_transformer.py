"""
Data Transformer
================

Transforms Amazon product data to Plytix format.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models import AmazonProduct, PlytixProduct, SyncConfig

logger = logging.getLogger(__name__)


class DataTransformer:
    """
    Transforms Amazon SP-API data to Plytix PIM format.

    Features:
    - SKU generation (AMZN-{marketplace}-{ASIN})
    - Field mapping per configuration
    - Write rule application (always_write vs fill_empty)
    - Date formatting (YYYY-MM-DD)
    """

    def __init__(self, config: SyncConfig):
        """
        Initialize transformer with configuration.

        Args:
            config: Sync configuration with attribute mapping
        """
        self.config = config

    def transform(
        self,
        amazon_product: AmazonProduct,
        existing_plytix: Optional[PlytixProduct] = None,
    ) -> PlytixProduct:
        """
        Transform Amazon product to Plytix format.

        Args:
            amazon_product: Source Amazon product
            existing_plytix: Existing Plytix product (for updates)

        Returns:
            Transformed PlytixProduct ready for sync
        """
        # Generate SKU
        sku = self.config.generate_sku(amazon_product.asin)

        # Create or update product
        if existing_plytix:
            product = existing_plytix
            product.is_new = False
            product.needs_update = True
            # ALWAYS update label from Amazon data
            product.label = amazon_product.item_name or sku
        else:
            product = PlytixProduct(
                sku=sku,
                label=amazon_product.item_name or sku,
                status=self.config.default_status,
                product_family_id=self.config.product_family_id,
                is_new=True,
            )

        product.source_asin = amazon_product.asin

        # Map attributes
        product.attributes = self._map_attributes(
            amazon_product,
            existing_plytix.attributes if existing_plytix else {},
        )

        # Set asset tracking
        product.asset_ids = []  # Will be populated by image loader

        return product

    def transform_batch(
        self,
        amazon_products: List[AmazonProduct],
        existing_map: Optional[Dict[str, PlytixProduct]] = None,
    ) -> tuple[List[PlytixProduct], List[str]]:
        """
        Transform multiple Amazon products.

        Args:
            amazon_products: List of Amazon products
            existing_map: Map of SKU -> existing PlytixProduct

        Returns:
            Tuple of (List of transformed PlytixProduct objects, List of failed ASINs)
        """
        existing_map = existing_map or {}
        transformed = []
        failed_asins = []

        for amazon_product in amazon_products:
            sku = self.config.generate_sku(amazon_product.asin)
            existing = existing_map.get(sku)

            try:
                plytix_product = self.transform(amazon_product, existing)
                transformed.append(plytix_product)
            except Exception as e:
                failed_asins.append(amazon_product.asin)
                logger.error(f"Failed to transform ASIN {amazon_product.asin}: {e}")

        if failed_asins:
            logger.warning(f"Transform failures: {len(failed_asins)} products dropped: {failed_asins[:10]}{'...' if len(failed_asins) > 10 else ''}")

        logger.info(
            f"Transformed {len(transformed)} products "
            f"({sum(1 for p in transformed if p.is_new)} new, "
            f"{sum(1 for p in transformed if not p.is_new)} updates)"
        )

        return transformed, failed_asins

    def _map_attributes(
        self,
        amazon: AmazonProduct,
        existing_attrs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Map Amazon fields to Plytix attributes.

        Args:
            amazon: Source Amazon product
            existing_attrs: Existing Plytix attributes

        Returns:
            Mapped attribute dictionary
        """
        attrs = existing_attrs.copy()
        mapping = self.config.attribute_mapping

        # Helper to set attribute only if mapped in config
        def set_if_mapped(amazon_field: str, value, normalize: bool = False):
            if amazon_field in mapping:
                if normalize and value:
                    value = self._normalize_identifier(value)
                self._set_attribute(attrs, mapping[amazon_field], value, existing_attrs)

        # Core identification (always write)
        attrs[mapping.get("asin", "amazon_asin")] = amazon.asin

        if amazon.parent_asin and "parent_asin" in mapping:
            attrs[mapping["parent_asin"]] = amazon.parent_asin

        # Product info - only set if mapped
        set_if_mapped("item_name", amazon.item_name)
        set_if_mapped("brand", amazon.brand)
        set_if_mapped("manufacturer", amazon.manufacturer)
        set_if_mapped("model_number", amazon.model_number)
        set_if_mapped("product_type", amazon.product_type)

        # Identifiers - only set if mapped, with normalization
        set_if_mapped("upc", amazon.upc, normalize=True)
        set_if_mapped("ean", amazon.ean, normalize=True)
        set_if_mapped("gtin", amazon.gtin, normalize=True)

        # Variation info - only set if mapped
        if amazon.variation_theme:
            set_if_mapped("variation_theme", amazon.variation_theme)
        if amazon.color:
            set_if_mapped("color", amazon.color)
        if amazon.size:
            set_if_mapped("size", amazon.size)

        # Content - only set if mapped
        if amazon.bullet_points and "bullet_points" in mapping:
            bullet_text = "\n".join(f"• {bp}" for bp in amazon.bullet_points)
            self._set_attribute(attrs, mapping["bullet_points"], bullet_text, existing_attrs)

        if amazon.product_description:
            set_if_mapped("product_description", amazon.product_description)

        # Dimensions - only set if mapped
        if amazon.item_dimensions and "item_dimensions" in mapping:
            dims = amazon.item_dimensions
            dim_str = self._format_dimensions(dims)
            if dim_str:
                self._set_attribute(attrs, mapping["item_dimensions"], dim_str, existing_attrs)

            # Weight as separate attribute if available and mapped
            if "item_weight" in mapping:
                weight = dims.get("weight")
                if weight:
                    weight_str = self._format_weight(weight)
                    if weight_str:
                        self._set_attribute(attrs, mapping["item_weight"], weight_str, existing_attrs)

        # Sync metadata (always write)
        attrs[mapping.get("last_synced", "amazon_last_synced")] = (
            datetime.now().strftime("%Y-%m-%d")  # Plytix date format
        )

        return attrs

    def _set_attribute(
        self,
        attrs: Dict[str, Any],
        attr_name: str,
        value: Any,
        existing: Dict[str, Any],
    ) -> None:
        """
        Set attribute value based on write rules.

        Args:
            attrs: Target attribute dictionary
            attr_name: Attribute name
            value: Value to set
            existing: Existing attributes for fill_empty check
        """
        if value is None:
            return

        # Check if always_write
        if attr_name in self.config.always_write:
            attrs[attr_name] = value
            return

        # Check if fill_empty
        if attr_name in self.config.fill_empty:
            existing_value = existing.get(attr_name)
            if not existing_value:
                attrs[attr_name] = value
            return

        # Default: always write
        attrs[attr_name] = value

    def _normalize_identifier(self, value: Optional[str]) -> Optional[str]:
        """
        Normalize identifier (strip leading zeros, standardize format).

        Args:
            value: Raw identifier value

        Returns:
            Normalized identifier or None
        """
        if not value:
            return None

        if not self.config.normalize_identifiers:
            return value

        original = value

        # Remove non-numeric characters except for check digit 'X'
        cleaned = re.sub(r'[^0-9X]', '', value.upper())

        # Strip leading zeros for UPC/EAN
        if cleaned and cleaned[0] == '0' and len(cleaned) > 10:
            cleaned = cleaned.lstrip('0')
            # Ensure minimum length
            if len(cleaned) < 10:
                cleaned = value  # Restore original if too short
                logger.debug(f"Identifier normalization: '{original}' -> restored (too short after strip)")

        # Log significant changes for debugging
        if cleaned and original != cleaned:
            logger.debug(f"Identifier normalized: '{original}' -> '{cleaned}'")

        return cleaned if cleaned else None

    def _format_dimensions(self, dims: Dict[str, Any]) -> Optional[str]:
        """
        Format dimensions for storage.

        Args:
            dims: Dimension dictionary from Amazon

        Returns:
            Formatted dimension string or None
        """
        parts = []

        for key in ["length", "width", "height"]:
            dim = dims.get(key)
            if dim and isinstance(dim, dict):
                value = dim.get("value")
                unit = dim.get("unit", "")
                if value:
                    parts.append(f"{value} {unit}")

        if parts:
            return " x ".join(parts)
        return None

    def _format_weight(self, weight: Dict[str, Any]) -> Optional[str]:
        """
        Format weight for storage.

        Args:
            weight: Weight dictionary from Amazon

        Returns:
            Formatted weight string or None
        """
        if not isinstance(weight, dict):
            return None

        value = weight.get("value")
        unit = weight.get("unit", "")

        if value:
            return f"{value} {unit}"
        return None
