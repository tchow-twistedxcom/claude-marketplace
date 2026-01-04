"""
Data Models for Amazon → Plytix Sync
====================================

Dataclasses representing products, matches, and sync state.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum, Enum
from typing import Dict, List, Optional, Any
from pathlib import Path
import yaml


class SyncPhase(IntEnum):
    """Phases of the sync pipeline with proper ordering."""
    INIT = 0
    EXTRACT = 1
    TRANSFORM = 2
    MATCH = 3
    LOAD_PRODUCTS = 4
    LOAD_IMAGES = 5
    LOAD_HIERARCHY = 6
    LINK_CANONICAL = 7
    COMPLETE = 8
    FAILED = 99

    @classmethod
    def from_string(cls, s: str) -> "SyncPhase":
        """Convert string name to SyncPhase."""
        mapping = {
            "init": cls.INIT,
            "extract": cls.EXTRACT,
            "transform": cls.TRANSFORM,
            "match": cls.MATCH,
            "load_products": cls.LOAD_PRODUCTS,
            "load_images": cls.LOAD_IMAGES,
            "load_hierarchy": cls.LOAD_HIERARCHY,
            "link_canonical": cls.LINK_CANONICAL,
            "complete": cls.COMPLETE,
            "failed": cls.FAILED,
        }
        return mapping.get(s, cls.INIT)


class SyncStatus(Enum):
    """Status of individual item sync."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class SyncConfig:
    """Configuration loaded from sync_config.yaml."""

    # Marketplace
    marketplace: str = "US"
    sku_prefix: str = "AMZN"
    sku_format: str = "{prefix}-{marketplace}-{asin}"

    # Batch processing
    batch_size: int = 50
    checkpoint_interval: int = 100
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    delay_between_batches: float = 0.5

    # Rate limits
    spapi_rate_limit: float = 5.0
    plytix_rate_limit: float = 3.0

    # Plytix settings
    product_family_id: str = "694a3a2d665d9e1363da7922"
    amazon_hierarchy_relationship: str = "amazon_hierarchy"
    amazon_listings_relationship: str = "amazon_listings"
    amazon_images_attribute: str = "amazon_images"
    default_status: str = "draft"

    # Attribute mapping
    attribute_mapping: Dict[str, str] = field(default_factory=dict)
    always_write: List[str] = field(default_factory=list)
    fill_empty: List[str] = field(default_factory=list)

    # Canonical matching
    matching_priority: List[str] = field(default_factory=lambda: ["gtin", "upc", "ean", "model_number", "model_to_sku", "model_size", "sku"])
    normalize_identifiers: bool = True
    orphan_handling: str = "create"
    exclude_sku_prefixes: List[str] = field(default_factory=lambda: ["TC"])  # SKU prefixes to exclude from matching
    canonical_cache_ttl_hours: int = 24  # TTL for canonical product cache

    # Image settings
    images_sync_enabled: bool = True
    max_images_per_product: int = 10
    skip_existing_images: bool = True
    set_first_as_thumbnail: bool = True
    main_image_attribute: Optional[str] = None  # Attribute to store main image
    asset_index_max_pages: int = 1000  # Max pages for asset filename index

    # Hierarchy
    hierarchy_sync_enabled: bool = True
    fail_on_missing_relationships: bool = True  # Fail fast if required relationships don't exist

    # Index limits
    sku_index_max_pages: int = 1000  # Max pages for SKU index (100 products/page)

    # State directory
    data_dir: str = "data/sync_runs"

    @classmethod
    def from_yaml(cls, path: str) -> "SyncConfig":
        """Load configuration from YAML file."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        config = cls()

        # Sync settings
        sync = data.get('sync', {})
        config.marketplace = sync.get('marketplace', config.marketplace)
        config.sku_prefix = sync.get('sku_prefix', config.sku_prefix)
        config.sku_format = sync.get('sku_format', config.sku_format)
        config.batch_size = sync.get('batch_size', config.batch_size)
        config.checkpoint_interval = sync.get('checkpoint_interval', config.checkpoint_interval)
        config.max_retries = sync.get('max_retries', config.max_retries)
        config.retry_delay_seconds = sync.get('retry_delay_seconds', config.retry_delay_seconds)
        config.delay_between_batches = sync.get('delay_between_batches', config.delay_between_batches)
        config.spapi_rate_limit = sync.get('spapi_rate_limit', config.spapi_rate_limit)
        config.plytix_rate_limit = sync.get('plytix_rate_limit', config.plytix_rate_limit)

        # Plytix settings
        plytix = data.get('plytix', {})
        config.product_family_id = plytix.get('product_family_id', config.product_family_id)
        config.amazon_hierarchy_relationship = plytix.get('amazon_hierarchy_relationship', config.amazon_hierarchy_relationship)
        config.amazon_listings_relationship = plytix.get('amazon_listings_relationship', config.amazon_listings_relationship)
        config.amazon_images_attribute = plytix.get('amazon_images_attribute', config.amazon_images_attribute)
        config.default_status = plytix.get('default_status', config.default_status)

        # Attribute mapping
        config.attribute_mapping = data.get('attribute_mapping', {})

        # Write rules
        write_rules = data.get('write_rules', {})
        config.always_write = write_rules.get('always_write', [])
        config.fill_empty = write_rules.get('fill_empty', [])

        # Canonical matching
        matching = data.get('canonical_matching', {})
        config.matching_priority = matching.get('priority', config.matching_priority)
        config.normalize_identifiers = matching.get('normalize_identifiers', config.normalize_identifiers)
        config.orphan_handling = matching.get('orphan_handling', config.orphan_handling)
        config.exclude_sku_prefixes = matching.get('exclude_sku_prefixes', config.exclude_sku_prefixes)
        config.canonical_cache_ttl_hours = matching.get('cache_ttl_hours', config.canonical_cache_ttl_hours)

        # Images
        images = data.get('images', {})
        config.images_sync_enabled = images.get('sync_enabled', config.images_sync_enabled)
        config.max_images_per_product = images.get('max_images_per_product', config.max_images_per_product)
        config.skip_existing_images = images.get('skip_existing', config.skip_existing_images)
        config.set_first_as_thumbnail = images.get('set_first_as_thumbnail', config.set_first_as_thumbnail)
        config.main_image_attribute = images.get('main_image_attribute', config.main_image_attribute)
        config.asset_index_max_pages = images.get('asset_index_max_pages', config.asset_index_max_pages)

        # Hierarchy
        hierarchy = data.get('hierarchy', {})
        config.hierarchy_sync_enabled = hierarchy.get('sync_enabled', config.hierarchy_sync_enabled)
        config.fail_on_missing_relationships = hierarchy.get('fail_on_missing_relationships', config.fail_on_missing_relationships)

        # Index limits
        indexes = data.get('indexes', {})
        config.sku_index_max_pages = indexes.get('sku_max_pages', config.sku_index_max_pages)

        # State
        state = data.get('state', {})
        config.data_dir = state.get('data_dir', config.data_dir)

        return config

    def generate_sku(self, asin: str) -> str:
        """Generate Plytix SKU from ASIN."""
        return self.sku_format.format(
            prefix=self.sku_prefix,
            marketplace=self.marketplace,
            asin=asin
        )


@dataclass
class AmazonProduct:
    """Amazon product data extracted from SP-API."""

    asin: str
    parent_asin: Optional[str] = None
    item_name: Optional[str] = None
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    product_type: Optional[str] = None

    # Identifiers
    upc: Optional[str] = None
    ean: Optional[str] = None
    gtin: Optional[str] = None

    # Variation
    variation_theme: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    is_parent: bool = False
    child_asins: List[str] = field(default_factory=list)

    # Content
    bullet_points: List[str] = field(default_factory=list)
    product_description: Optional[str] = None

    # Physical
    item_dimensions: Optional[Dict[str, Any]] = None
    item_weight: Optional[Dict[str, Any]] = None

    # Images
    image_urls: List[str] = field(default_factory=list)

    # Raw data for reference
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def primary_identifier(self) -> Optional[str]:
        """Return first available identifier for matching."""
        return self.gtin or self.upc or self.ean or self.model_number


@dataclass
class PlytixProduct:
    """Plytix product representation for sync."""

    id: Optional[str] = None  # Plytix product ID (None if new)
    sku: str = ""
    label: str = ""
    status: str = "draft"
    product_family_id: Optional[str] = None

    # Attributes to set
    attributes: Dict[str, Any] = field(default_factory=dict)

    # Assets
    thumbnail_asset_id: Optional[str] = None
    asset_ids: List[str] = field(default_factory=list)

    # Categories
    category_ids: List[str] = field(default_factory=list)

    # Relationships
    parent_product_id: Optional[str] = None
    child_product_ids: List[str] = field(default_factory=list)
    canonical_product_id: Optional[str] = None

    # Source reference
    source_asin: Optional[str] = None

    # Sync metadata
    is_new: bool = True
    needs_update: bool = False


@dataclass
class CanonicalMatch:
    """Result of canonical product matching."""

    amazon_product: AmazonProduct
    plytix_product: Optional[PlytixProduct] = None
    matched: bool = False
    match_type: Optional[str] = None  # gtin, upc, ean, model_number, sku
    match_confidence: float = 0.0
    canonical_product_id: Optional[str] = None

    @property
    def is_orphan(self) -> bool:
        """True if no canonical match found."""
        return not self.matched

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary for checkpoint persistence.

        Only stores essential fields needed for resume - NOT the full AmazonProduct.
        The ASIN reference is sufficient since we have raw_catalog.json.
        """
        return {
            "asin": self.amazon_product.asin,
            "matched": self.matched,
            "match_type": self.match_type,
            "match_confidence": self.match_confidence,
            "canonical_product_id": self.canonical_product_id,
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        amazon_products_by_asin: Dict[str, AmazonProduct],
    ) -> Optional["CanonicalMatch"]:
        """
        Deserialize from dictionary.

        Requires amazon_products_by_asin lookup to reconnect the reference.
        Returns None if the ASIN is not found (data inconsistency).
        """
        asin = data.get("asin")
        amazon_product = amazon_products_by_asin.get(asin)

        if not amazon_product:
            return None

        return cls(
            amazon_product=amazon_product,
            matched=data.get("matched", False),
            match_type=data.get("match_type"),
            match_confidence=data.get("match_confidence", 0.0),
            canonical_product_id=data.get("canonical_product_id"),
        )


@dataclass
class SyncItemResult:
    """Result of syncing a single item."""

    asin: str
    sku: str
    status: SyncStatus = SyncStatus.PENDING
    plytix_product_id: Optional[str] = None
    canonical_product_id: Optional[str] = None

    # What was done
    product_created: bool = False
    product_updated: bool = False
    family_assigned: bool = False
    images_uploaded: int = 0
    hierarchy_linked: bool = False
    canonical_linked: bool = False

    # Errors
    error_message: Optional[str] = None
    error_phase: Optional[SyncPhase] = None

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class SyncResult:
    """Overall sync run result."""

    run_id: str
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # Counts
    total_items: int = 0
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0

    # Details
    products_created: int = 0
    products_updated: int = 0
    images_uploaded: int = 0
    images_failed: int = 0
    hierarchies_linked: int = 0
    canonicals_linked: int = 0

    # State
    current_phase: SyncPhase = SyncPhase.INIT
    is_complete: bool = False
    is_failed: bool = False

    # Item results
    item_results: Dict[str, SyncItemResult] = field(default_factory=dict)

    # Errors - detailed tracking for debugging
    errors: List[str] = field(default_factory=list)
    transform_failures: List[str] = field(default_factory=list)  # ASINs that failed transform
    family_assignment_failures: List[str] = field(default_factory=list)  # Product IDs that failed family assignment
    image_upload_failures: List[Dict[str, str]] = field(default_factory=list)  # {sku, error} for image failures
    hierarchy_failures: List[str] = field(default_factory=list)  # ASINs that failed hierarchy linking
    canonical_failures: List[str] = field(default_factory=list)  # Canonical IDs that failed linking

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        if self.processed_items == 0:
            return 0.0
        return self.successful_items / self.processed_items

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "successful_items": self.successful_items,
            "failed_items": self.failed_items,
            "skipped_items": self.skipped_items,
            "products_created": self.products_created,
            "products_updated": self.products_updated,
            "images_uploaded": self.images_uploaded,
            "images_failed": self.images_failed,
            "hierarchies_linked": self.hierarchies_linked,
            "canonicals_linked": self.canonicals_linked,
            "current_phase": self.current_phase.value,
            "is_complete": self.is_complete,
            "is_failed": self.is_failed,
            "duration_seconds": self.duration_seconds,
            "success_rate": self.success_rate,
            "errors": self.errors,
            "transform_failures": self.transform_failures,
            "family_assignment_failures": self.family_assignment_failures,
            "image_upload_failures": self.image_upload_failures,
            "hierarchy_failures": self.hierarchy_failures,
            "canonical_failures": self.canonical_failures,
        }
