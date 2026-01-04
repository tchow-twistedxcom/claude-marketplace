#!/usr/bin/env python3
"""
Sync Amazon Product Images to Plytix

Uploads Amazon product images to Plytix as assets and links them to products.
Deduplicates by URL - each unique image is uploaded once and linked to all
products that use it.

Usage:
    python sync_amazon_images.py --mapping mca0032_mapping.json --dry-run
    python sync_amazon_images.py --mapping mca0032_mapping.json --execute
    python sync_amazon_images.py --mapping mca0032_mapping.json --execute --skip-existing
"""

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from urllib.parse import urlparse

# Add plytix scripts to path
PLYTIX_SCRIPTS = Path(__file__).parent.parent.parent / 'plytix-skills' / 'skills' / 'plytix-api' / 'scripts'
sys.path.insert(0, str(PLYTIX_SCRIPTS))

from plytix_api import PlytixAPI, PlytixAPIError


# Image variant mapping: Amazon variant name -> Plytix attribute/naming convention
IMAGE_VARIANTS = {
    'amazon_image_main': {'slot': 'MAIN', 'priority': 1},
    'amazon_image_variant_1': {'slot': 'PT01', 'priority': 2},
    'amazon_image_variant_2': {'slot': 'PT02', 'priority': 3},
    'amazon_image_variant_3': {'slot': 'PT03', 'priority': 4},
    'amazon_image_variant_4': {'slot': 'PT04', 'priority': 5},
    'amazon_image_variant_5': {'slot': 'PT05', 'priority': 6},
    'amazon_image_variant_6': {'slot': 'PT06', 'priority': 7},
    'amazon_image_variant_7': {'slot': 'PT07', 'priority': 8},
    'amazon_image_variant_8': {'slot': 'PT08', 'priority': 9},
    'amazon_image_swatch': {'slot': 'SWATCH', 'priority': 10},
}


class AmazonImageSyncer:
    """Sync Amazon product images to Plytix as assets with deduplication."""

    def __init__(self, plytix_account: str = None):
        self.api = PlytixAPI(account=plytix_account)
        self._asset_cache = {}  # filename -> asset_id
        self._url_to_asset = {}  # url -> asset_id (for deduplication)
        self._parent_cache = {}  # parent_sku -> product_id

    def extract_parent_sku(self, variant_sku: str) -> Optional[str]:
        """
        Extract parent SKU from variant SKU.

        Pattern: MCA0032-M-13 -> MCA0032, MCA0032-W-07.5 -> MCA0032

        Args:
            variant_sku: Variant product SKU

        Returns:
            Parent SKU or None if pattern doesn't match
        """
        if not variant_sku:
            return None
        # Match pattern: STYLE-SIZE_MODIFIER-SIZE (e.g., MCA0032-M-13, MCA0032-W-07.5)
        match = re.match(r'^([A-Z0-9]+)-[MW]-[\d.]+$', variant_sku)
        if match:
            return match.group(1)
        return None

    def find_product_by_sku(self, sku: str) -> Optional[str]:
        """
        Find product ID in Plytix by SKU.

        Args:
            sku: Product SKU

        Returns:
            Product ID if found, None otherwise
        """
        if sku in self._parent_cache:
            return self._parent_cache[sku]

        try:
            result = self.api.search_products(
                filters=[{'field': 'sku', 'operator': 'eq', 'value': sku}],
                limit=1
            )
            # Handle response format: {'data': [...], 'pagination': {...}}
            data = result.get('data', []) if isinstance(result, dict) else result
            if data and len(data) > 0:
                product_id = data[0].get('id')
                self._parent_cache[sku] = product_id
                return product_id
        except PlytixAPIError as e:
            print(f"  Warning: Could not find product {sku}: {e}")

        self._parent_cache[sku] = None
        return None

    def find_parent_product(self, parent_sku: str) -> Optional[str]:
        """Find parent product ID in Plytix by SKU."""
        return self.find_product_by_sku(parent_sku)

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

    def generate_asset_filename(self, url: str, priority: int = 0, slot: str = '') -> str:
        """
        Generate a consistent filename for the asset based on Amazon image ID.

        Args:
            url: Amazon image URL
            priority: Image position priority (1=MAIN, 2=PT01, etc.)
            slot: Slot name (MAIN, PT01, PT02, etc.)

        Returns:
            Standardized filename with position first for sorting (e.g., amazon_01_MAIN_61wixnPXtlL.jpg)
        """
        image_id = self.extract_amazon_image_id(url)
        ext = Path(urlparse(url).path).suffix or '.jpg'

        if priority and slot:
            # Position first for alphabetical sorting: amazon_01_MAIN_61wixnPXtlL.jpg
            return f"amazon_{priority:02d}_{slot}_{image_id}{ext}"
        else:
            return f"amazon_{image_id}{ext}"

    def find_existing_asset(self, filename: str) -> Optional[str]:
        """
        Check if an asset with this filename already exists.

        Args:
            filename: Asset filename to search for

        Returns:
            Asset ID if found, None otherwise
        """
        if filename in self._asset_cache:
            return self._asset_cache[filename]

        try:
            result = self.api.search_assets(
                filters=[{'field': 'filename', 'operator': 'eq', 'value': filename}],
                limit=1
            )
            assets = result.get('data', [])
            if assets:
                asset_id = assets[0].get('id')
                self._asset_cache[filename] = asset_id
                return asset_id
        except PlytixAPIError as e:
            print(f"  Warning: Could not search for asset {filename}: {e}")

        return None

    def upload_image(self, url: str, filename: str, slot: str = '') -> Optional[str]:
        """
        Upload an image to Plytix from Amazon URL.

        Args:
            url: Amazon image URL
            filename: Target filename
            slot: Image slot type (MAIN, PT01, etc.)

        Returns:
            Asset ID if successful, None otherwise
        """
        image_id = self.extract_amazon_image_id(url)
        slot_desc = f" | Slot: {slot}" if slot else ""
        metadata = {
            'alt_text': f"Amazon product image {image_id}",
            'public': True,
            'description': f"Source: Amazon | Image ID: {image_id}{slot_desc}"
        }

        try:
            result = self.api.upload_asset_url(url, filename, metadata)
            # Handle various response formats from Plytix API
            asset_id = None
            if isinstance(result, list) and result:
                # Direct list response
                asset_id = result[0].get('id')
            elif isinstance(result, dict):
                data = result.get('data', result)
                if isinstance(data, list) and data:
                    # {'data': [...]} format
                    asset_id = data[0].get('id')
                elif isinstance(data, dict):
                    # {'data': {...}} or direct dict format
                    asset_id = data.get('id')

            if asset_id:
                self._asset_cache[filename] = asset_id
                self._url_to_asset[url] = asset_id
                return asset_id
        except PlytixAPIError as e:
            print(f"  Error uploading {filename}: {e}")

        return None

    def link_asset_to_product(
        self,
        product_id: str,
        asset_id: str,
        attribute_label: str = 'amazon_images'
    ) -> bool:
        """
        Link an asset to a product via a media gallery attribute.

        Args:
            product_id: Plytix product ID
            asset_id: Plytix asset ID
            attribute_label: Media gallery attribute to link to

        Returns:
            True if successful, False otherwise
        """
        try:
            # Plytix API format: POST /products/{id}/assets with {id, attribute_label}
            data = {'id': asset_id, 'attribute_label': attribute_label}
            self.api.post(f'/products/{product_id}/assets', data)
            return True
        except PlytixAPIError as e:
            # Asset may already be linked
            if 'already' in str(e).lower():
                return True
            print(f"  Error linking asset {asset_id} to product {product_id}: {e}")
            return False

    def collect_unique_images(
        self,
        mappings: List[Dict]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Collect all unique image URLs and their associated products.

        Tracks which slot(s) each URL is used for and uses the highest priority
        slot for the filename (lowest priority number = most important).

        Option B format: Uses 'suggested_sku' (AMZN-{marketplace}-{ASIN}) to identify products.
        Legacy format: Uses 'plytix_product_id' directly.

        Args:
            mappings: List of product mappings with image URLs

        Returns:
            Dict mapping URL -> {filename, product_skus: set, priority, slot}
        """
        url_map = {}

        for mapping in mappings:
            # Option B: Use suggested_sku as product identifier
            # Legacy: Use plytix_product_id
            product_ref = mapping.get('suggested_sku') or mapping.get('plytix_product_id')
            if not product_ref:
                continue

            for attr_name, variant_info in IMAGE_VARIANTS.items():
                url = mapping.get(attr_name)
                if not url:
                    continue

                priority = variant_info['priority']
                slot = variant_info['slot']

                if url not in url_map:
                    # First time seeing this URL - store with current slot info
                    url_map[url] = {
                        'priority': priority,
                        'slot': slot,
                        'product_skus': set()
                    }
                else:
                    # URL already seen - keep highest priority (lowest number)
                    if priority < url_map[url]['priority']:
                        url_map[url]['priority'] = priority
                        url_map[url]['slot'] = slot

                url_map[url]['product_skus'].add(product_ref)

        # Generate filenames with priority/slot info
        for url, info in url_map.items():
            info['filename'] = self.generate_asset_filename(
                url,
                priority=info['priority'],
                slot=info['slot']
            )

        return url_map

    def sync_all_images(
        self,
        mappings: List[Dict],
        skip_existing: bool = True,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Sync images for all products with deduplication.

        Phase 1: Upload unique images
        Phase 2: Link assets to products

        Args:
            mappings: List of product mappings with image URLs
            skip_existing: Skip upload if asset already exists
            dry_run: Preview without uploading

        Returns:
            Summary of sync operation
        """
        # Collect unique images
        url_map = self.collect_unique_images(mappings)

        summary = {
            'total_products': len(mappings),
            'products_with_images': sum(1 for m in mappings if any(m.get(attr) for attr in IMAGE_VARIANTS.keys())),
            'total_image_refs': sum(1 for m in mappings for attr in IMAGE_VARIANTS.keys() if m.get(attr)),
            'unique_images': len(url_map),
            'images_uploaded': 0,
            'images_skipped': 0,
            'links_created': 0,
            'errors': []
        }

        print(f"\nPhase 1: Processing {len(url_map)} unique images")
        print("=" * 60)

        # Phase 1: Upload unique images (sorted by priority for consistent ordering)
        sorted_items = sorted(url_map.items(), key=lambda x: x[1]['priority'])

        for i, (url, info) in enumerate(sorted_items):
            filename = info['filename']
            slot = info['slot']
            product_count = len(info['product_skus'])

            if dry_run:
                existing = self.find_existing_asset(filename)
                if existing:
                    print(f"  [{i+1}/{len(url_map)}] SKIP: {filename} (exists, links to {product_count} products)")
                    summary['images_skipped'] += 1
                    self._url_to_asset[url] = existing
                else:
                    print(f"  [{i+1}/{len(url_map)}] UPLOAD: {filename} (links to {product_count} products)")
                    summary['images_uploaded'] += 1
                    self._url_to_asset[url] = 'dry-run-placeholder'  # Track for link counting
                continue

            # Check for existing asset
            existing_id = self.find_existing_asset(filename)
            if existing_id and skip_existing:
                summary['images_skipped'] += 1
                self._url_to_asset[url] = existing_id
                print(f"  [{i+1}/{len(url_map)}] SKIP: {filename} (exists)")
                continue

            # Upload new image
            print(f"  [{i+1}/{len(url_map)}] UPLOAD: {filename}...", end=" ")
            asset_id = self.upload_image(url, filename, slot)
            if asset_id:
                summary['images_uploaded'] += 1
                print("OK")
            else:
                summary['errors'].append(f"Failed to upload {filename}")
                print("FAILED")

            time.sleep(0.3)  # Rate limiting

        # Phase 2: Link assets to Amazon products (Option B)
        # Images go to AMZN-{marketplace}-{ASIN} products, not canonical products
        if not dry_run:
            print(f"\nPhase 2: Linking assets to Amazon products")
            print("=" * 60)

            summary['main_image_links'] = 0
            for mapping in mappings:
                # Option B: Use suggested_sku to find the Amazon product
                amazon_sku = mapping.get('suggested_sku')
                if not amazon_sku:
                    # Fallback for old mapping format
                    amazon_sku = mapping.get('plytix_product_sku', 'unknown')

                # Find the Amazon product by SKU
                product_id = self.find_product_by_sku(amazon_sku)
                if not product_id:
                    print(f"  {amazon_sku}: product not found, skipping")
                    continue

                asset_ids = set()
                main_image_asset_id = None
                for attr_name in IMAGE_VARIANTS.keys():
                    url = mapping.get(attr_name)
                    if url and url in self._url_to_asset:
                        asset_id = self._url_to_asset[url]
                        asset_ids.add(asset_id)
                        # Track main image for separate attribute
                        if attr_name == 'amazon_image_main':
                            main_image_asset_id = asset_id

                if asset_ids:
                    print(f"  {amazon_sku}: linking {len(asset_ids)} assets...", end=" ")
                    linked = 0
                    for asset_id in asset_ids:
                        if self.link_asset_to_product(product_id, asset_id):
                            linked += 1
                        time.sleep(0.1)
                    summary['links_created'] += linked

                    # Also link main image to amazon_main_image attribute
                    if main_image_asset_id:
                        if self.link_asset_to_product(product_id, main_image_asset_id, 'amazon_main_image_test'):
                            summary['main_image_links'] += 1
                        time.sleep(0.1)

                    print(f"{linked} OK")

            # Note: For Option B, images go only to Amazon products
            # Parent/canonical products don't get Amazon images directly
            summary['parent_links_created'] = 0
            summary['parent_main_image_links'] = 0

        else:
            # Dry run - estimate links
            for mapping in mappings:
                amazon_sku = mapping.get('suggested_sku') or mapping.get('plytix_product_sku')
                if not amazon_sku:
                    continue
                for attr_name in IMAGE_VARIANTS.keys():
                    url = mapping.get(attr_name)
                    if url and url in self._url_to_asset:
                        summary['links_created'] += 1

        return summary


def sync_amazon_images(
    mapping_path: str,
    output_path: str = None,
    plytix_account: str = None,
    skip_existing: bool = True,
    dry_run: bool = False
) -> Dict:
    """
    Sync Amazon images to Plytix with deduplication.

    Args:
        mapping_path: Path to mapping JSON file
        output_path: Output path for sync report
        plytix_account: Plytix account alias
        skip_existing: Skip upload if asset already exists
        dry_run: Preview without uploading

    Returns:
        Sync summary
    """
    # Load mapping data
    print(f"Loading mapping data from {mapping_path}")
    with open(mapping_path) as f:
        mapping_data = json.load(f)

    mappings = mapping_data.get('matched', [])
    print(f"Found {len(mappings)} matched products")

    # Initialize syncer
    syncer = AmazonImageSyncer(plytix_account=plytix_account)

    # Collect stats before sync
    url_map = syncer.collect_unique_images(mappings)
    total_refs = sum(1 for m in mappings for attr in IMAGE_VARIANTS.keys() if m.get(attr))

    print(f"\nImage Statistics:")
    print(f"  Total image references: {total_refs}")
    print(f"  Unique images: {len(url_map)}")
    print(f"  Duplicates avoided: {total_refs - len(url_map)}")

    if not url_map:
        print("\nNo products have image URLs. Re-export with images included.")
        return {'error': 'No image URLs found in mapping'}

    # Run sync
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Starting image sync...")

    summary = syncer.sync_all_images(mappings, skip_existing, dry_run)

    # Print summary
    print("\n" + "=" * 60)
    print("IMAGE SYNC SUMMARY")
    print("=" * 60)
    print(f"Total products:         {summary['total_products']}")
    print(f"Products with images:   {summary['products_with_images']}")
    print(f"Total image references: {summary['total_image_refs']}")
    print(f"Unique images:          {summary['unique_images']}")
    print(f"Images uploaded:        {summary['images_uploaded']}")
    print(f"Images skipped:         {summary['images_skipped']}")
    print(f"Variant-asset links:    {summary['links_created']}")
    if summary.get('main_image_links'):
        print(f"Variant main images:    {summary['main_image_links']}")
    if summary.get('parent_links_created'):
        print(f"Parent-asset links:     {summary['parent_links_created']}")
    if summary.get('parent_main_image_links'):
        print(f"Parent main images:     {summary['parent_main_image_links']}")
    if summary['errors']:
        print(f"Errors:                 {len(summary['errors'])}")
    print("=" * 60)

    # Add metadata
    summary['metadata'] = {
        'source_file': mapping_path,
        'sync_date': datetime.now(timezone.utc).isoformat(),
        'dry_run': dry_run,
        'skip_existing': skip_existing
    }

    # Save report
    if output_path and not dry_run:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"\nSync report saved to {output_path}")
    elif dry_run:
        print("\n[DRY RUN - No changes made]")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Sync Amazon product images to Plytix as assets (with deduplication)"
    )
    parser.add_argument(
        "--mapping", "-m",
        required=True,
        help="Path to mapping JSON file (from generate_asin_mapping.py)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output path for sync report JSON"
    )
    parser.add_argument(
        "--plytix-account",
        help="Plytix account alias"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip upload if asset with same filename exists (default: True)"
    )
    parser.add_argument(
        "--force-reupload",
        action="store_true",
        help="Re-upload even if asset exists (overrides --skip-existing)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without uploading"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the sync (required to make changes)"
    )

    args = parser.parse_args()

    # Require explicit --execute or --dry-run
    if not args.dry_run and not args.execute:
        print("Error: Must specify --dry-run or --execute", file=sys.stderr)
        print("  --dry-run   Preview changes without uploading")
        print("  --execute   Execute the sync operation")
        sys.exit(1)

    # Set default output path if not specified
    output_path = args.output
    if not output_path and args.execute:
        input_path = Path(args.mapping)
        output_path = str(input_path.parent / f"{input_path.stem}_image_sync.json")

    skip_existing = args.skip_existing and not args.force_reupload

    try:
        summary = sync_amazon_images(
            mapping_path=args.mapping,
            output_path=output_path,
            plytix_account=args.plytix_account,
            skip_existing=skip_existing,
            dry_run=args.dry_run
        )

        if summary.get('error'):
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
