#!/usr/bin/env python3
"""
Revert Amazon Enrichment from Plytix Products

Clears amazon_* attributes and unlinks Amazon images from canonical Plytix products.
Used to reset products before switching to the new AMZN-{marketplace}-{ASIN} model.

Usage:
    python revert_amazon_enrichment.py --mapping mca0032_mapping.json --dry-run
    python revert_amazon_enrichment.py --mapping mca0032_mapping.json --execute
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

# Add plytix scripts to path
PLYTIX_SCRIPTS = Path(__file__).parent.parent.parent / 'plytix-skills' / 'skills' / 'plytix-api' / 'scripts'
sys.path.insert(0, str(PLYTIX_SCRIPTS))

from plytix_api import PlytixAPI, PlytixAPIError


# Attributes to clear (set to None/empty)
AMAZON_ATTRIBUTES = [
    'amazon_asin',
    'amazon_asin_secondary',
    'amazon_parent_asin',
    'amazon_sku',
    'amazon_upc_imported',
    'amazon_ean_imported',
    'amazon_title_imported',
    'amazon_size',
    'amazon_color',
    'amazon_variation_theme',
    'amazon_listing_status',
    'amazon_sync_status',
    'amazon_sync_conflict',
    'amazon_sync_notes',
    'amazon_last_synced',
    'amazon_desired_parent',
]


class PlytixReverter:
    """Reverts Amazon enrichment from Plytix products."""

    def __init__(self, account: str = None):
        self.api = PlytixAPI(account=account)

    def find_parent_product(self, style: str) -> Optional[Dict]:
        """Find parent product by style SKU."""
        try:
            result = self.api.search_products(
                filters=[{'field': 'sku', 'operator': 'eq', 'value': style}],
                limit=1
            )
            data = result.get('data', []) if isinstance(result, dict) else result
            if data:
                return data[0]
        except PlytixAPIError as e:
            print(f"  Warning: Could not find parent {style}: {e}")
        return None

    def get_product_assets(self, product_id: str) -> List[Dict]:
        """Get assets linked to a product."""
        try:
            result = self.api.get_product(product_id)
            # Assets are included in product response
            return result.get('assets', []) if isinstance(result, dict) else []
        except PlytixAPIError:
            return []

    def unlink_amazon_assets(self, product_id: str, dry_run: bool = False) -> int:
        """Unlink Amazon-sourced assets from a product."""
        assets = self.get_product_assets(product_id)
        unlinked = 0

        for asset in assets:
            asset_id = asset.get('id')
            filename = asset.get('filename', '')

            # Identify Amazon assets by filename pattern
            if filename.startswith('amazon_'):
                if dry_run:
                    print(f"    [PREVIEW] Would unlink asset: {filename}")
                    unlinked += 1
                else:
                    try:
                        # API requires list of asset IDs
                        self.api.remove_product_assets(product_id, [asset_id])
                        unlinked += 1
                    except PlytixAPIError as e:
                        print(f"    Warning: Could not unlink {filename}: {e}")

        return unlinked

    def clear_amazon_attributes(
        self,
        product_id: str,
        dry_run: bool = False
    ) -> List[str]:
        """Clear all amazon_* attributes from a product."""
        # Build update payload - set all amazon attributes to None
        updates = {attr: None for attr in AMAZON_ATTRIBUTES}

        if dry_run:
            return list(updates.keys())

        try:
            self.api.update_product(product_id, {'attributes': updates})
            return list(updates.keys())
        except PlytixAPIError as e:
            print(f"    Warning: Error clearing attributes: {e}")
            return []

    def revert_products(
        self,
        product_ids: List[str],
        product_skus: Dict[str, str],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Revert multiple products."""
        summary = {
            'products_processed': 0,
            'attributes_cleared': 0,
            'assets_unlinked': 0,
            'errors': []
        }

        for product_id in product_ids:
            sku = product_skus.get(product_id, product_id)
            print(f"  {sku}...", end=' ')

            try:
                # Clear attributes
                cleared = self.clear_amazon_attributes(product_id, dry_run)
                summary['attributes_cleared'] += len(cleared)

                # Unlink Amazon assets
                unlinked = self.unlink_amazon_assets(product_id, dry_run)
                summary['assets_unlinked'] += unlinked

                summary['products_processed'] += 1
                print(f"OK ({len(cleared)} attrs, {unlinked} assets)")

                time.sleep(0.2)  # Rate limiting

            except Exception as e:
                print(f"ERROR: {e}")
                summary['errors'].append({'product_id': product_id, 'sku': sku, 'error': str(e)})

        return summary


def revert_amazon_enrichment(
    mapping_path: str,
    plytix_account: str = None,
    dry_run: bool = False
) -> Dict:
    """
    Revert Amazon enrichment from products in mapping file.

    Args:
        mapping_path: Path to mapping JSON
        plytix_account: Plytix account alias
        dry_run: Preview without making changes

    Returns:
        Summary of revert operation
    """
    # Load mapping
    print(f"Loading mapping from {mapping_path}")
    with open(mapping_path) as f:
        mapping_data = json.load(f)

    matched = mapping_data.get('matched', [])
    print(f"Found {len(matched)} products to revert")

    # Collect product IDs and SKUs
    product_ids: Set[str] = set()
    product_skus: Dict[str, str] = {}

    for entry in matched:
        pid = entry.get('plytix_product_id')
        sku = entry.get('plytix_product_sku')
        if pid:
            product_ids.add(pid)
            product_skus[pid] = sku

    # Also find parent product
    if matched:
        first_sku = matched[0].get('plytix_product_sku', '')
        # Extract style from SKU (e.g., MCA0032-M-13 -> MCA0032)
        parts = first_sku.split('-')
        if parts:
            style = parts[0]
            print(f"\nLooking for parent product: {style}")

    # Initialize reverter
    reverter = PlytixReverter(account=plytix_account)

    # Find and add parent
    if style:
        parent = reverter.find_parent_product(style)
        if parent:
            parent_id = parent.get('id')
            product_ids.add(parent_id)
            product_skus[parent_id] = style
            print(f"  Found parent: {style} ({parent_id})")

    # Run revert
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Reverting {len(product_ids)} products...")
    print("=" * 60)

    summary = reverter.revert_products(
        list(product_ids),
        product_skus,
        dry_run
    )

    # Print summary
    print("\n" + "=" * 60)
    print(f"{'[DRY RUN] ' if dry_run else ''}REVERT SUMMARY")
    print("=" * 60)
    print(f"Products processed:  {summary['products_processed']}")
    print(f"Attributes cleared:  {summary['attributes_cleared']}")
    print(f"Assets unlinked:     {summary['assets_unlinked']}")
    if summary['errors']:
        print(f"Errors:              {len(summary['errors'])}")
        for err in summary['errors']:
            print(f"  - {err['sku']}: {err['error']}")
    print("=" * 60)

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Revert Amazon enrichment from Plytix products"
    )
    parser.add_argument(
        "--mapping", "-m",
        required=True,
        help="Path to mapping JSON file"
    )
    parser.add_argument(
        "--plytix-account",
        help="Plytix account alias"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without making changes"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute the revert"
    )

    args = parser.parse_args()

    # Require explicit flag
    if not args.dry_run and not args.execute:
        print("Error: Must specify --dry-run or --execute", file=sys.stderr)
        sys.exit(1)

    try:
        summary = revert_amazon_enrichment(
            mapping_path=args.mapping,
            plytix_account=args.plytix_account,
            dry_run=args.dry_run
        )

        if summary['errors']:
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
