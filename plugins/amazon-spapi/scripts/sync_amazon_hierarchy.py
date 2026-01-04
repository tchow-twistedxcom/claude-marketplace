#!/usr/bin/env python3
"""
Sync Amazon Product Hierarchy to Plytix

Creates parent-child relationships in Plytix based on Amazon's variation structure.
- Sets amazon_asin on parent products (from variants' amazon_parent_asin)
- Links variants to parents using the "Amazon Hierarchy" relationship

Usage:
    python sync_amazon_hierarchy.py --mapping mca0032_mapping.json --dry-run
    python sync_amazon_hierarchy.py --mapping mca0032_mapping.json --execute
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add plytix scripts to path
PLYTIX_SCRIPTS = Path(__file__).parent.parent.parent / 'plytix-skills' / 'skills' / 'plytix-api' / 'scripts'
sys.path.insert(0, str(PLYTIX_SCRIPTS))

from plytix_api import PlytixAPI, PlytixAPIError


# Relationship ID for Amazon Hierarchy
AMAZON_HIERARCHY_RELATIONSHIP_ID = '6949a93a5080ffdd690599ac'


class AmazonHierarchySyncer:
    """Sync Amazon product hierarchy to Plytix relationships."""

    def __init__(self, plytix_account: str = None):
        self.api = PlytixAPI(account=plytix_account)
        self._product_cache = {}  # sku -> product_id

    def find_product_by_sku(self, sku: str) -> Optional[Dict]:
        """
        Find product in Plytix by SKU.

        Args:
            sku: Product SKU

        Returns:
            Product data or None
        """
        if sku in self._product_cache:
            return self._product_cache[sku]

        try:
            result = self.api.search_products(
                filters=[{'field': 'sku', 'operator': 'eq', 'value': sku}],
                limit=1
            )
            data = result.get('data', []) if isinstance(result, dict) else result
            if data and len(data) > 0:
                self._product_cache[sku] = data[0]
                return data[0]
        except PlytixAPIError as e:
            print(f"  Warning: Could not find product {sku}: {e}")

        self._product_cache[sku] = None
        return None

    def extract_parent_sku(self, variant_sku: str) -> Optional[str]:
        """
        Extract parent SKU from variant SKU.

        Pattern: MCA0032-M-13 -> MCA0032
        """
        import re
        if not variant_sku:
            return None
        match = re.match(r'^([A-Z0-9]+)-[MW]-[\d.]+$', variant_sku)
        if match:
            return match.group(1)
        return None

    def get_existing_relationships(self, product_id: str) -> List[str]:
        """
        Get existing related product IDs for a product.

        Args:
            product_id: Plytix product ID

        Returns:
            List of related product IDs
        """
        try:
            result = self.api.get_product_relationships(product_id)
            relationships = result.get('data', [])
            related_ids = []
            for rel in relationships:
                if rel.get('id') == AMAZON_HIERARCHY_RELATIONSHIP_ID:
                    for prod in rel.get('products', []):
                        related_ids.append(prod.get('id'))
            return related_ids
        except PlytixAPIError:
            return []

    def set_parent_amazon_asin(
        self,
        parent_id: str,
        amazon_asin: str,
        dry_run: bool = False
    ) -> bool:
        """
        Set the amazon_asin attribute on a parent product.

        Args:
            parent_id: Plytix parent product ID
            amazon_asin: Amazon parent ASIN
            dry_run: Preview without updating

        Returns:
            True if successful
        """
        if dry_run:
            print(f"    [PREVIEW] Would set amazon_asin = {amazon_asin}")
            return True

        try:
            self.api.update_product(parent_id, {
                'attributes': {'amazon_asin': amazon_asin}
            })
            return True
        except PlytixAPIError as e:
            print(f"    Error setting amazon_asin: {e}")
            return False

    def link_variants_to_parent(
        self,
        parent_id: str,
        variant_ids: List[str],
        dry_run: bool = False
    ) -> int:
        """
        Create parent-child relationships in Plytix.

        Args:
            parent_id: Plytix parent product ID
            variant_ids: List of variant product IDs
            dry_run: Preview without updating

        Returns:
            Number of relationships created
        """
        if dry_run:
            print(f"    [PREVIEW] Would link {len(variant_ids)} variants")
            return len(variant_ids)

        # Get existing relationships to avoid duplicates
        existing = set(self.get_existing_relationships(parent_id))
        new_variants = [vid for vid in variant_ids if vid not in existing]

        if not new_variants:
            print(f"    All {len(variant_ids)} variants already linked")
            return 0

        try:
            self.api.add_product_relationships(
                product_id=parent_id,
                relationship_id=AMAZON_HIERARCHY_RELATIONSHIP_ID,
                related_product_ids=new_variants
            )
            return len(new_variants)
        except PlytixAPIError as e:
            print(f"    Error linking variants: {e}")
            return 0

    def sync_hierarchy(
        self,
        mappings: List[Dict],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Sync Amazon hierarchy to Plytix.

        Args:
            mappings: List of product mappings with Amazon data
            dry_run: Preview without updating

        Returns:
            Summary of sync operation
        """
        summary = {
            'parents_found': 0,
            'parents_updated': 0,
            'variants_linked': 0,
            'errors': []
        }

        # Group variants by parent ASIN
        parent_groups = defaultdict(list)
        for mapping in mappings:
            amazon_parent_asin = mapping.get('amazon_parent_asin')
            if amazon_parent_asin:
                parent_groups[amazon_parent_asin].append(mapping)

        print(f"\nFound {len(parent_groups)} parent ASIN(s)")
        print("=" * 60)

        for amazon_parent_asin, variants in parent_groups.items():
            # Get parent SKU from first variant
            first_variant_sku = variants[0].get('plytix_product_sku')
            parent_sku = self.extract_parent_sku(first_variant_sku)

            if not parent_sku:
                print(f"\n  Could not extract parent SKU from {first_variant_sku}")
                continue

            print(f"\n  Parent: {parent_sku} (Amazon ASIN: {amazon_parent_asin})")
            print(f"  Variants: {len(variants)}")

            # Find parent product in Plytix
            parent_product = self.find_product_by_sku(parent_sku)
            if not parent_product:
                summary['errors'].append(f"Parent not found: {parent_sku}")
                print(f"    ERROR: Parent product not found in Plytix")
                continue

            parent_id = parent_product.get('id')
            summary['parents_found'] += 1

            # Set amazon_asin on parent
            print(f"    Setting amazon_asin on parent...", end=" ")
            if self.set_parent_amazon_asin(parent_id, amazon_parent_asin, dry_run):
                summary['parents_updated'] += 1
                print("OK" if not dry_run else "")

            # Collect variant product IDs
            variant_ids = []
            for v in variants:
                variant_id = v.get('plytix_product_id')
                if variant_id:
                    variant_ids.append(variant_id)

            # Link variants to parent
            print(f"    Linking {len(variant_ids)} variants...", end=" ")
            linked = self.link_variants_to_parent(parent_id, variant_ids, dry_run)
            summary['variants_linked'] += linked
            if not dry_run:
                print(f"{linked} OK")

            time.sleep(0.2)  # Rate limiting

        return summary


def sync_amazon_hierarchy(
    mapping_path: str,
    output_path: str = None,
    plytix_account: str = None,
    dry_run: bool = False
) -> Dict:
    """
    Sync Amazon hierarchy to Plytix.

    Args:
        mapping_path: Path to mapping JSON file
        output_path: Output path for sync report
        plytix_account: Plytix account alias
        dry_run: Preview without updating

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
    syncer = AmazonHierarchySyncer(plytix_account=plytix_account)

    # Run sync
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Starting hierarchy sync...")

    summary = syncer.sync_hierarchy(mappings, dry_run)

    # Print summary
    print("\n" + "=" * 60)
    print("HIERARCHY SYNC SUMMARY")
    print("=" * 60)
    print(f"Parents found:          {summary['parents_found']}")
    print(f"Parents updated:        {summary['parents_updated']}")
    print(f"Variants linked:        {summary['variants_linked']}")
    if summary['errors']:
        print(f"Errors:                 {len(summary['errors'])}")
        for err in summary['errors']:
            print(f"  - {err}")
    print("=" * 60)

    # Add metadata
    summary['metadata'] = {
        'source_file': mapping_path,
        'sync_date': datetime.now(timezone.utc).isoformat(),
        'dry_run': dry_run
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
        description="Sync Amazon product hierarchy to Plytix"
    )
    parser.add_argument(
        "--mapping", "-m",
        required=True,
        help="Path to mapping JSON file"
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
        "--dry-run",
        action="store_true",
        help="Preview without updating Plytix"
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
        sys.exit(1)

    # Set default output path
    output_path = args.output
    if not output_path and args.execute:
        input_path = Path(args.mapping)
        output_path = str(input_path.parent / f"{input_path.stem}_hierarchy_sync.json")

    try:
        summary = sync_amazon_hierarchy(
            mapping_path=args.mapping,
            output_path=output_path,
            plytix_account=args.plytix_account,
            dry_run=args.dry_run
        )

        if summary.get('errors'):
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
