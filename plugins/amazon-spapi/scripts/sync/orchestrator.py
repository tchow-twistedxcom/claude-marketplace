"""
Sync Orchestrator
=================

Main coordinator for Amazon → Plytix sync pipeline.
"""

import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .models import (
    AmazonProduct,
    CanonicalMatch,
    PlytixProduct,
    SyncConfig,
    SyncPhase,
    SyncResult,
    SyncStatus,
)
from .state import CheckpointManager, ProgressTracker
from .extractors import CatalogExtractor
from .transformers import DataTransformer, CanonicalMatcher
from .loaders import ProductLoader, ImageLoader, HierarchyLoader, CanonicalLinker

logger = logging.getLogger(__name__)


class SyncOrchestrator:
    """
    Orchestrates the full Amazon → Plytix sync pipeline.

    Pipeline phases:
    1. EXTRACT - Fetch products from SP-API
    2. TRANSFORM - Map fields, generate SKUs
    3. MATCH - Find canonical product matches
    4. LOAD_PRODUCTS - Create/update Plytix products
    5. LOAD_IMAGES - Upload and link images
    6. LOAD_HIERARCHY - Create parent-child relationships
    7. LINK_CANONICAL - Link to canonical products

    Features:
    - Checkpoint/resume capability
    - Progress tracking with ETA
    - Graceful shutdown handling
    - Dry-run mode
    """

    def __init__(
        self,
        config: SyncConfig,
        run_id: Optional[str] = None,
        dry_run: bool = False,
        spapi_profile: str = "production",
        rerun_phases: Optional[List[str]] = None,
        skip_extract: bool = False,
    ):
        """
        Initialize orchestrator.

        Args:
            config: Sync configuration
            run_id: Run ID for resume (None for new run)
            dry_run: If True, don't make changes to Plytix
            spapi_profile: SP-API profile name
            rerun_phases: List of phase names to force rerun (images, hierarchy, canonical, attributes)
            skip_extract: If True, skip extract phase and use cached data
        """
        self.config = config
        self.dry_run = dry_run
        self.rerun_phases = set(rerun_phases) if rerun_phases else set()
        self.skip_extract = skip_extract

        # State management
        self.checkpoint = CheckpointManager(config.data_dir, run_id)
        self.progress = ProgressTracker(show_progress_bar=True)

        # Pipeline components
        self.extractor = CatalogExtractor(config, profile=spapi_profile)
        self.transformer = DataTransformer(config)
        self.matcher = CanonicalMatcher(config)
        self.product_loader = ProductLoader(config)
        self.image_loader = ImageLoader(config)
        self.hierarchy_loader = HierarchyLoader(config)
        self.canonical_linker = CanonicalLinker(config)

        # Runtime state
        self._amazon_products: List[AmazonProduct] = []
        self._plytix_products: List[PlytixProduct] = []
        self._matches: List[CanonicalMatch] = []
        self._asin_to_product_id: Dict[str, str] = {}

        # Failure tracking for final result
        self._transform_failures: List[str] = []

        # Shutdown handling
        self._shutdown_requested = False
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown."""
        logger.warning("Shutdown requested - saving checkpoint...")
        self._shutdown_requested = True
        # Persist rate-limited queues so they can be retried on resume
        self._save_rate_limited_queues()
        self.checkpoint.save()

    def run(
        self,
        asins: Optional[List[str]] = None,
        brand: Optional[str] = None,
        asin_file: Optional[str] = None,
    ) -> SyncResult:
        """
        Run the full sync pipeline.

        Args:
            asins: List of ASINs to sync
            brand: Brand name to search (alternative to asins)
            asin_file: Path to file with ASINs (alternative to asins)

        Returns:
            SyncResult with outcomes
        """
        result = SyncResult(run_id=self.checkpoint.run_id)

        try:
            # Check for resume
            if self.checkpoint.has_checkpoint():
                logger.info(f"Resuming run {self.checkpoint.run_id}")
                self.checkpoint.load()
                # Restore rate-limited queues from checkpoint
                self._restore_rate_limited_queues()
            else:
                logger.info(f"Starting new run {self.checkpoint.run_id}")

            # Fail fast if relationships are missing (when configured)
            if not self.dry_run and self.config.fail_on_missing_relationships:
                self.verify_setup(fail_fast=True)

            # Determine ASINs to process
            if asins is None:
                if asin_file:
                    asins = self.extractor.load_asins_from_file(asin_file)
                elif brand:
                    # Will search by brand in extract phase
                    asins = []
                else:
                    asins = self.checkpoint.pending_asins

            result.total_items = len(asins)
            self.progress.start_run(len(asins))

            # Set pending ASINs
            if asins and not self.checkpoint.pending_asins:
                self.checkpoint.set_pending_asins(asins)

            # Run phases
            self._run_extract_phase(asins, brand)
            if self._shutdown_requested:
                return self._finalize_result(result)

            self._run_transform_phase()
            if self._shutdown_requested:
                return self._finalize_result(result)

            self._run_match_phase()
            if self._shutdown_requested:
                return self._finalize_result(result)

            if not self.dry_run:
                self._run_load_products_phase()
                if self._shutdown_requested:
                    return self._finalize_result(result)

                self._run_load_images_phase()
                if self._shutdown_requested:
                    return self._finalize_result(result)

                self._run_load_hierarchy_phase()
                if self._shutdown_requested:
                    return self._finalize_result(result)

                self._run_link_canonical_phase()
            else:
                logger.info("DRY RUN - Skipping load phases")

            # Mark complete
            self.checkpoint.set_phase(SyncPhase.COMPLETE)
            result.is_complete = True

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            result.is_failed = True
            result.errors.append(str(e))
            self.checkpoint.set_phase(SyncPhase.FAILED)

        return self._finalize_result(result)

    def _save_rate_limited_queues(self) -> None:
        """Persist rate-limited queues to checkpoint for recovery."""
        rate_limited_products = self.product_loader.get_rate_limited_products()
        rate_limited_images = self.image_loader.get_rate_limited_images()

        self.checkpoint.set_rate_limited_products(rate_limited_products)
        self.checkpoint.set_rate_limited_images(rate_limited_images)

        if rate_limited_products or rate_limited_images:
            logger.info(
                f"Persisting rate-limited queues: "
                f"{len(rate_limited_products)} products, {len(rate_limited_images)} images"
            )

    def _restore_rate_limited_queues(self) -> None:
        """Restore rate-limited queues from checkpoint after resume."""
        if self.checkpoint.rate_limited_products:
            self.product_loader.set_rate_limited_products(
                self.checkpoint.rate_limited_products
            )
        if self.checkpoint.rate_limited_images:
            self.image_loader.set_rate_limited_images(
                self.checkpoint.rate_limited_images
            )

        if self.checkpoint.has_rate_limited_items():
            logger.info(
                f"Restored rate-limited queues from checkpoint - "
                f"will retry after phase completion"
            )

    def _build_amazon_products_by_asin(self) -> Dict[str, AmazonProduct]:
        """Build ASIN → AmazonProduct lookup from loaded products."""
        return {p.asin: p for p in self._amazon_products}

    def _restore_matches_from_checkpoint(self) -> bool:
        """
        Restore match data from checkpoint for resume.

        Returns:
            True if matches were restored, False if not available
        """
        amazon_by_asin = self._build_amazon_products_by_asin()
        matches = self.checkpoint.load_matches(amazon_by_asin)

        if matches is None:
            logger.error(
                "Cannot resume CANONICAL phase: matches.json not found. "
                "Rerun with --rerun-phases match to regenerate."
            )
            return False

        self._matches = matches
        logger.info(f"Restored {len(self._matches)} matches from checkpoint")
        return True

    def _restore_asin_mapping_from_checkpoint(self) -> bool:
        """
        Restore ASIN mapping from checkpoint or rebuild from Plytix.

        Returns:
            True if mapping was restored/rebuilt successfully
        """
        # Try to load from checkpoint first (fast path)
        mapping = self.checkpoint.load_asin_mapping()

        if mapping:
            self._asin_to_product_id = mapping
            # Also populate PlytixProduct.id for downstream phases
            for amazon, plytix in zip(self._amazon_products, self._plytix_products):
                product_id = mapping.get(amazon.asin)
                if product_id:
                    plytix.id = product_id
            logger.info(f"Restored {len(mapping)} ASIN mappings from checkpoint")
            return True

        # Fallback: Rebuild from Plytix (slower but works)
        logger.info("ASIN mapping not found, rebuilding from Plytix...")
        self._rebuild_product_ids_from_plytix()

        # Save for future resumes
        if self._asin_to_product_id:
            self.checkpoint.save_asin_mapping(self._asin_to_product_id)

        return bool(self._asin_to_product_id)

    def _should_skip_phase(self, phase: SyncPhase, phase_name: str) -> bool:
        """
        Check if a phase should be skipped.

        Args:
            phase: The SyncPhase enum value
            phase_name: The phase name for rerun check (e.g., 'images', 'hierarchy')

        Returns:
            True if phase should be skipped
        """
        # Force rerun if requested
        if phase_name in self.rerun_phases:
            logger.info(f"Force rerunning phase: {phase_name}")
            return False

        # Skip if already complete
        return self.checkpoint.current_phase > phase

    def _run_extract_phase(
        self,
        asins: List[str],
        brand: Optional[str],
    ) -> None:
        """Extract phase - fetch from SP-API."""
        if self.skip_extract or self._should_skip_phase(SyncPhase.EXTRACT, 'extract'):
            logger.info("Skipping extract phase (already complete or --skip-extract)")
            # Load cached data
            cached = self.checkpoint.load_data_file("raw_catalog.json")
            if cached:
                self._amazon_products = [
                    AmazonProduct(**p) for p in cached
                ]
            return

        self.checkpoint.set_phase(SyncPhase.EXTRACT)

        if brand and not asins:
            # Search by brand
            self._amazon_products = self.extractor.extract_by_brand(brand)
        else:
            # Extract by ASIN list
            self._amazon_products = self.extractor.extract_by_asins(
                asins,
                skip_asins=self.checkpoint.processed_asins,
            )

        # Discover and fetch parent ASINs
        parent_asins = self.extractor.discover_parent_asins(self._amazon_products)
        if parent_asins:
            new_parent_asins = parent_asins - self.checkpoint.parent_asins
            if new_parent_asins:
                self.checkpoint.add_parent_asins(list(new_parent_asins))
                parent_products = self.extractor.extract_by_asins(
                    list(new_parent_asins)
                )
                self._amazon_products.extend(parent_products)

        # Save raw data
        raw_data = self.extractor.to_raw_data(self._amazon_products)
        self.checkpoint.save_data_file("raw_catalog.json", raw_data)

        logger.info(f"Extracted {len(self._amazon_products)} products")

    def _run_transform_phase(self) -> None:
        """Transform phase - map to Plytix format."""
        if self._should_skip_phase(SyncPhase.TRANSFORM, 'transform'):
            logger.info("Skipping transform phase (already complete)")
            return

        self.checkpoint.set_phase(SyncPhase.TRANSFORM)
        self.progress.start_phase(SyncPhase.TRANSFORM, len(self._amazon_products))

        # Build existing product index
        self.product_loader.build_sku_index(sku_pattern="AMZN-")

        # Get existing products for update detection
        existing_map = {}
        for amazon in self._amazon_products:
            sku = self.config.generate_sku(amazon.asin)
            product_id = self.product_loader.get_product_id_by_sku(sku)
            if product_id:
                # Create minimal existing product
                existing_map[sku] = PlytixProduct(
                    id=product_id,
                    sku=sku,
                    attributes={},
                )

        # Transform (returns tuple of products and failed ASINs)
        self._plytix_products, transform_failures = self.transformer.transform_batch(
            self._amazon_products,
            existing_map,
        )

        # Track transform failures in result
        if transform_failures:
            self._transform_failures = transform_failures

        self.progress.complete_phase(SyncPhase.TRANSFORM)
        logger.info(f"Transformed {len(self._plytix_products)} products")

    def _run_match_phase(self) -> None:
        """Match phase - find canonical products."""
        if self._should_skip_phase(SyncPhase.MATCH, 'match'):
            logger.info("Skipping match phase (already complete)")
            # CRITICAL: Restore matches for downstream phases (CANONICAL)
            self._restore_matches_from_checkpoint()
            return

        self.checkpoint.set_phase(SyncPhase.MATCH)

        # Build canonical index if not already done
        if not self.checkpoint.is_canonical_index_built():
            canonical_products = self.product_loader.get_all_canonical_products()
            self.matcher.build_index(canonical_products)
            self.checkpoint.mark_canonical_index_built()

        # Match products
        self._matches = self.matcher.match_batch(self._amazon_products)

        # Save matches for resume capability
        self.checkpoint.save_matches(self._matches)

        # Log match stats
        matched = sum(1 for m in self._matches if m.matched)
        logger.info(f"Matched {matched}/{len(self._matches)} products to canonicals")

    def _run_load_products_phase(self) -> None:
        """Load products phase - create/update in Plytix."""
        # Allow 'attributes' to trigger product update for attribute sync
        if self._should_skip_phase(SyncPhase.LOAD_PRODUCTS, 'products') and 'attributes' not in self.rerun_phases:
            logger.info("Skipping load products phase (already complete)")
            # Restore ASIN mapping from checkpoint (fast) or rebuild from Plytix (slow)
            self._restore_asin_mapping_from_checkpoint()
            return

        self.checkpoint.set_phase(SyncPhase.LOAD_PRODUCTS)
        self.progress.start_phase(SyncPhase.LOAD_PRODUCTS, len(self._plytix_products))

        def on_progress(completed: int, total: int, status: SyncStatus):
            self.progress.increment(SyncPhase.LOAD_PRODUCTS, status)

            # Checkpoint periodically
            if self.checkpoint.should_checkpoint(
                completed, self.config.checkpoint_interval
            ):
                self.checkpoint.save()

        results = self.product_loader.load_batch(
            self._plytix_products,
            on_progress=on_progress,
        )

        # Retry rate-limited family assignments after cooldown
        rate_limited = self.product_loader.get_rate_limited_products()
        if rate_limited:
            logger.info(f"Waiting 30s before retrying {len(rate_limited)} rate-limited family assignments...")
            time.sleep(30)  # Brief cooldown before retrying
            retry_results = self.product_loader.retry_rate_limited_families()
            logger.info(
                f"Rate-limit retry: {retry_results['success']} succeeded, "
                f"{retry_results['failed']} still pending"
            )

        # Persist any remaining rate-limited items to checkpoint
        self._save_rate_limited_queues()
        self.checkpoint.save()

        # Update ASIN -> product ID mapping
        for amazon, plytix in zip(self._amazon_products, self._plytix_products):
            if plytix.id:
                self._asin_to_product_id[amazon.asin] = plytix.id

        # Save ASIN mapping for resume capability
        self.checkpoint.save_asin_mapping(self._asin_to_product_id)

        self.progress.finish_progress_bar()
        self.progress.complete_phase(SyncPhase.LOAD_PRODUCTS)

    def _rebuild_product_ids_from_plytix(self) -> None:
        """
        Rebuild product IDs from Plytix when skipping load phase.
        This ensures image/hierarchy/canonical phases have product IDs to work with.
        """
        logger.info("Rebuilding product IDs from Plytix...")
        self.product_loader.build_sku_index(sku_pattern="AMZN-")

        # Populate PlytixProduct.id and ASIN mapping
        for amazon, plytix in zip(self._amazon_products, self._plytix_products):
            product_id = self.product_loader.get_product_id_by_sku(plytix.sku)
            if product_id:
                plytix.id = product_id
                self._asin_to_product_id[amazon.asin] = product_id
            else:
                logger.warning(f"Product not found in Plytix: {plytix.sku}")

        logger.info(f"Rebuilt {len(self._asin_to_product_id)} product IDs")

    def _run_load_images_phase(self) -> None:
        """Load images phase - upload and link."""
        if self._should_skip_phase(SyncPhase.LOAD_IMAGES, 'images'):
            logger.info("Skipping load images phase (already complete)")
            return

        self.checkpoint.set_phase(SyncPhase.LOAD_IMAGES)

        # Pre-build asset filename index (batch fetch vs per-image API calls)
        self.image_loader.build_asset_index()

        # Pair Amazon and Plytix products
        product_pairs = list(zip(self._amazon_products, self._plytix_products))
        self.progress.start_phase(SyncPhase.LOAD_IMAGES, len(product_pairs))

        def on_progress(completed: int, total: int, status: SyncStatus = SyncStatus.SUCCESS):
            self.progress.increment(SyncPhase.LOAD_IMAGES, status)

        results = self.image_loader.load_images_batch(
            product_pairs,
            on_progress=on_progress,
        )

        # Retry rate-limited images after cooldown
        rate_limited = self.image_loader.get_rate_limited_images()
        if rate_limited:
            logger.info(f"Waiting 60s before retrying {len(rate_limited)} rate-limited images...")
            time.sleep(60)
            retry_results = self.image_loader.retry_rate_limited_images()
            logger.info(
                f"Image rate-limit retry: {retry_results['success']} succeeded, "
                f"{retry_results['failed']} failed, {retry_results['still_limited']} still pending"
            )

        # Persist any remaining rate-limited items to checkpoint
        self._save_rate_limited_queues()
        self.checkpoint.save()

        self.progress.finish_progress_bar()
        self.progress.complete_phase(SyncPhase.LOAD_IMAGES)

    def _run_load_hierarchy_phase(self) -> None:
        """Load hierarchy phase - parent-child relationships."""
        if self._should_skip_phase(SyncPhase.LOAD_HIERARCHY, 'hierarchy'):
            logger.info("Skipping load hierarchy phase (already complete)")
            return

        self.checkpoint.set_phase(SyncPhase.LOAD_HIERARCHY)

        # Build ASIN index for hierarchy
        self.hierarchy_loader.build_asin_index(self._plytix_products)

        results = self.hierarchy_loader.load_hierarchy(self._amazon_products)

    def _run_link_canonical_phase(self) -> None:
        """Link canonical phase - connect to master products."""
        if self._should_skip_phase(SyncPhase.LINK_CANONICAL, 'canonical'):
            logger.info("Skipping link canonical phase (already complete)")
            return

        self.checkpoint.set_phase(SyncPhase.LINK_CANONICAL)

        # CRITICAL: Ensure we have matches data for this phase
        if not self._matches:
            logger.warning("No matches data available, attempting to restore from checkpoint...")
            if not self._restore_matches_from_checkpoint():
                logger.error("Cannot run CANONICAL phase without matches data")
                return

        # Prepare links from matches
        self.canonical_linker.prepare_links(
            self._matches,
            self._asin_to_product_id,
        )

        results = self.canonical_linker.load_links()

        # Store canonical linking stats
        self._canonical_link_results = results

        # Save detailed failures for targeted retry capability
        if results.get("errors"):
            detailed_failures = []
            for err in results["errors"]:
                canonical_id = err.get("canonical_id")
                # Get the Amazon products that were supposed to link
                amazon_ids = self.canonical_linker._canonical_to_amazon.get(canonical_id, [])
                detailed_failures.append({
                    "canonical_id": canonical_id,
                    "amazon_product_ids": amazon_ids,
                    "error": err.get("error"),
                })
            self.checkpoint.save_canonical_failures(detailed_failures)

            # Log first 5 errors for debugging
            for err in results["errors"][:5]:
                logger.warning(
                    f"Canonical link error for {err.get('canonical_id')}: {err.get('error')}"
                )

    def _finalize_result(self, result: SyncResult) -> SyncResult:
        """Finalize and save results."""
        result.completed_at = datetime.now()
        result.processed_items = len(self._plytix_products)
        result.products_created = sum(1 for p in self._plytix_products if p.is_new)
        result.products_updated = sum(1 for p in self._plytix_products if not p.is_new)

        # Track transform failures
        if self._transform_failures:
            result.transform_failures = self._transform_failures

        # Track family assignment failures
        family_failures = self.product_loader.get_family_assignment_failures()
        if family_failures:
            result.family_assignment_failures = [pid for pid, _ in family_failures]

        # Track image failures
        # image_failures is List[Tuple[url, asin, index, product_id]]
        image_failures = self.image_loader.get_rate_limited_images()
        if image_failures:
            result.images_failed = len(image_failures)
            result.image_upload_failures = [
                {"sku": asin, "error": "Rate limit exceeded"}
                for url, asin, index, product_id in image_failures[:100]  # Limit stored errors
            ]

        # Add canonical linking stats if available
        if hasattr(self, '_canonical_link_results'):
            result.canonicals_linked = self._canonical_link_results.get("linked", 0)
            if self._canonical_link_results.get("errors"):
                result.canonical_failures = [
                    err.get('canonical_id') for err in self._canonical_link_results["errors"]
                ]
                for err in self._canonical_link_results["errors"]:
                    result.errors.append(f"Canonical link: {err.get('error')}")

        # Save final checkpoint
        self.checkpoint.save()

        # Save results
        self.checkpoint.save_data_file("sync_results.json", result.to_dict())

        # Log summary
        self.progress.log_summary()

        return result

    def verify_setup(self, fail_fast: bool = None) -> bool:
        """
        Verify all required Plytix relationships exist.

        Args:
            fail_fast: If True, raise exception on missing relationships.
                      Defaults to config.fail_on_missing_relationships.

        Returns:
            True if setup is valid

        Raises:
            RuntimeError: If fail_fast and relationships are missing
        """
        if fail_fast is None:
            fail_fast = self.config.fail_on_missing_relationships

        hierarchy_ok = self.hierarchy_loader.verify_setup()
        canonical_ok = self.canonical_linker.verify_setup()

        missing = []

        if not hierarchy_ok:
            missing.append(f"'{self.config.amazon_hierarchy_relationship}'")
            logger.warning(
                f"Create relationship '{self.config.amazon_hierarchy_relationship}' "
                f"in Plytix before running hierarchy sync"
            )

        if not canonical_ok:
            missing.append(f"'{self.config.amazon_listings_relationship}'")
            logger.warning(
                f"Create relationship '{self.config.amazon_listings_relationship}' "
                f"in Plytix before running canonical linking"
            )

        if missing and fail_fast:
            raise RuntimeError(
                f"Missing required Plytix relationships: {', '.join(missing)}. "
                f"Create them in Plytix or set fail_on_missing_relationships: false in config."
            )

        return hierarchy_ok and canonical_ok
