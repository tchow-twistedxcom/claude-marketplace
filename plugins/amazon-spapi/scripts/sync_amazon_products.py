#!/usr/bin/env python3
"""
Sync Amazon Products to Plytix (Option B)

Creates separate Plytix products for each Amazon ASIN.
SKU format: AMZN-{marketplace}-{ASIN}
Links to canonical products via "Amazon Listings" relationship.

Usage:
    python sync_amazon_products.py --mapping mca0032_mapping.json --dry-run
    python sync_amazon_products.py --mapping mca0032_mapping.json --execute
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add plytix scripts to path
PLYTIX_SCRIPTS = Path(__file__).parent.parent.parent / 'plytix-skills' / 'skills' / 'plytix-api' / 'scripts'
sys.path.insert(0, str(PLYTIX_SCRIPTS))

from plytix_api import PlytixAPI, PlytixAPIError


# Amazon Listings relationship name
AMAZON_LISTINGS_RELATIONSHIP = "Amazon Listings"


class AmazonProductSync:
    """Syncs Amazon ASINs as separate Plytix products."""

    def __init__(self, account: str = None):
        self.api = PlytixAPI(account=account)
        self._relationship_id = None

    def get_amazon_listings_relationship_id(self) -> Optional[str]:
        """Get the Amazon Listings relationship ID."""
        if self._relationship_id:
            return self._relationship_id

        try:
            rel = self.api.get_relationship_by_name(AMAZON_LISTINGS_RELATIONSHIP)
            if rel:
                self._relationship_id = rel.get('id')
                return self._relationship_id
        except PlytixAPIError as e:
            print(f"Warning: Could not find '{AMAZON_LISTINGS_RELATIONSHIP}' relationship: {e}")
        return None

    def check_product_exists(self, sku: str) -> Optional[Dict]:
        """Check if product with SKU already exists."""
        try:
            result = self.api.search_products(
                filters=[{'field': 'sku', 'operator': 'eq', 'value': sku}],
                limit=1
            )
            data = result.get('data', [])
            return data[0] if data else None
        except PlytixAPIError:
            return None

    def create_amazon_product(
        self,
        mapping: Dict,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new Amazon product in Plytix.

        Args:
            mapping: Mapping entry with suggested_sku, amazon_* fields, canonical_* fields
            dry_run: Preview without creating

        Returns:
            Result dict with status, product_id, etc.
        """
        sku = mapping['suggested_sku']
        asin = mapping['amazon_asin']

        # Check if already exists
        existing = self.check_product_exists(sku)
        if existing:
            return {
                'status': 'exists',
                'sku': sku,
                'product_id': existing.get('id'),
                'message': 'Product already exists'
            }

        if dry_run:
            return {
                'status': 'preview',
                'sku': sku,
                'message': f"Would create product {sku}"
            }

        # Build product data
        product_data = {
            'sku': sku,
            'label': mapping.get('amazon_title') or f"Amazon {asin}",
            # Assign to "8 - Amazon" product family
            'product_family': '694a3a2d665d9e1363da7922',
            'attributes': {
                # Amazon identifiers
                'amazon_asin': asin,
                'amazon_parent_asin': mapping.get('amazon_parent_asin'),
                'amazon_sku': mapping.get('amazon_sku'),
                'amazon_upc': mapping.get('amazon_upc'),
                'amazon_ean': mapping.get('amazon_ean'),
                # Amazon metadata
                'amazon_title': mapping.get('amazon_title'),
                'amazon_size': mapping.get('amazon_size'),
                'amazon_color': mapping.get('amazon_color'),
                'amazon_variation_theme': mapping.get('amazon_variation_theme'),
                'amazon_listing_status': mapping.get('amazon_listing_status'),
                # Option B specific
                'amazon_marketplace': mapping.get('marketplace', 'US'),
                'amazon_canonical_sku': mapping.get('canonical_plytix_sku'),
                'amazon_is_primary': False,  # Default - requires manual designation
                # Sync tracking (date-only format required by Plytix DateAttribute)
                'amazon_last_synced': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            }
        }

        # Remove None values
        product_data['attributes'] = {
            k: v for k, v in product_data['attributes'].items()
            if v is not None
        }

        try:
            result = self.api.create_product(product_data)
            return {
                'status': 'created',
                'sku': sku,
                'product_id': result.get('id'),
                'message': 'Product created successfully'
            }
        except PlytixAPIError as e:
            return {
                'status': 'error',
                'sku': sku,
                'message': str(e)
            }

    def link_to_canonical(
        self,
        amazon_product_id: str,
        canonical_product_id: str,
        dry_run: bool = False
    ) -> bool:
        """
        Link Amazon product to canonical via Amazon Listings relationship.

        Args:
            amazon_product_id: The new Amazon product ID
            canonical_product_id: The canonical Plytix product ID
            dry_run: Preview without linking

        Returns:
            True if successful
        """
        relationship_id = self.get_amazon_listings_relationship_id()
        if not relationship_id:
            return False

        if dry_run:
            return True

        try:
            # Link from canonical to Amazon product
            self.api.add_product_relationships(
                product_id=canonical_product_id,
                relationship_id=relationship_id,
                related_product_ids=[amazon_product_id]
            )
            return True
        except PlytixAPIError as e:
            print(f"    Warning: Could not link products: {e}")
            return False

    def sync_products(
        self,
        mappings: List[Dict],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Sync all Amazon products from mapping.

        Args:
            mappings: List of mapping entries
            dry_run: Preview without making changes

        Returns:
            Summary of sync operation
        """
        summary = {
            'total': len(mappings),
            'created': 0,
            'exists': 0,
            'linked': 0,
            'errors': []
        }

        relationship_id = self.get_amazon_listings_relationship_id()
        if relationship_id:
            print(f"Found '{AMAZON_LISTINGS_RELATIONSHIP}' relationship: {relationship_id}")
        else:
            print(f"Warning: '{AMAZON_LISTINGS_RELATIONSHIP}' relationship not found - products will not be linked")

        for mapping in mappings:
            sku = mapping['suggested_sku']
            canonical_sku = mapping.get('canonical_plytix_sku', 'N/A')
            print(f"  {sku} (canonical: {canonical_sku})...", end=" ")

            # Create product
            result = self.create_amazon_product(mapping, dry_run)

            if result['status'] == 'created':
                summary['created'] += 1
                print("CREATED", end="")

                # Link to canonical if we have the ID
                canonical_id = mapping.get('canonical_plytix_id')
                if canonical_id and relationship_id:
                    if self.link_to_canonical(result['product_id'], canonical_id, dry_run):
                        summary['linked'] += 1
                        print(" + LINKED")
                    else:
                        print(" (link failed)")
                else:
                    print()

            elif result['status'] == 'exists':
                summary['exists'] += 1
                print("EXISTS")

            elif result['status'] == 'preview':
                summary['created'] += 1
                print("[PREVIEW]")

            else:
                summary['errors'].append({
                    'sku': sku,
                    'error': result['message']
                })
                print(f"ERROR: {result['message']}")

            time.sleep(0.2)  # Rate limiting

        return summary


def sync_amazon_products(
    mapping_path: str,
    plytix_account: str = None,
    dry_run: bool = False
) -> Dict:
    """
    Sync Amazon products from mapping file.

    Args:
        mapping_path: Path to mapping JSON
        plytix_account: Plytix account alias
        dry_run: Preview without making changes

    Returns:
        Summary of sync operation
    """
    # Load mapping
    print(f"Loading mapping from {mapping_path}")
    with open(mapping_path) as f:
        mapping_data = json.load(f)

    matched = mapping_data.get('matched', [])
    unmatched = mapping_data.get('unmatched_amazon', [])
    metadata = mapping_data.get('metadata', {})
    marketplace = metadata.get('marketplace', 'US')

    # Combine matched and unmatched for sync
    # Unmatched items (like parent ASINs) get created without canonical links
    all_mappings = matched + unmatched

    print(f"Found {len(matched)} matched + {len(unmatched)} unmatched = {len(all_mappings)} Amazon products to sync")
    print(f"Marketplace: {marketplace}")

    # Initialize syncer
    syncer = AmazonProductSync(account=plytix_account)

    # Sync products
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Syncing Amazon products...")
    print("=" * 60)

    summary = syncer.sync_products(all_mappings, dry_run)

    # Print summary
    print("\n" + "=" * 60)
    print(f"{'[DRY RUN] ' if dry_run else ''}SYNC SUMMARY")
    print("=" * 60)
    print(f"Total mappings:      {summary['total']}")
    print(f"Products created:    {summary['created']}")
    print(f"Products existing:   {summary['exists']}")
    print(f"Canonical links:     {summary['linked']}")
    if summary['errors']:
        print(f"Errors:              {len(summary['errors'])}")
        for err in summary['errors'][:5]:
            print(f"  - {err['sku']}: {err['error']}")
    print("=" * 60)

    # Save results
    if not dry_run:
        output_path = Path(mapping_path).with_suffix('.sync_products.json')
        with open(output_path, 'w') as f:
            json.dump({
                **summary,
                'metadata': {
                    'source_file': mapping_path,
                    'sync_date': datetime.now(timezone.utc).isoformat(),
                    'dry_run': dry_run
                }
            }, f, indent=2)
        print(f"\nResults saved to {output_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Sync Amazon products to Plytix (Option B: separate products)"
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
        help="Actually execute the sync"
    )

    args = parser.parse_args()

    # Require explicit flag
    if not args.dry_run and not args.execute:
        print("Error: Must specify --dry-run or --execute", file=sys.stderr)
        sys.exit(1)

    try:
        summary = sync_amazon_products(
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
