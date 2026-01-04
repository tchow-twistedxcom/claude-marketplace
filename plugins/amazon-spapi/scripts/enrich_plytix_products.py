#!/usr/bin/env python3
"""
Enrich Plytix Products with Amazon Data

Updates existing Plytix products with Amazon catalog data as attribute overlay.
Uses "Amazon Hierarchy" relationship to track parent/variant relationships.

Usage:
    python enrich_plytix_products.py --mapping mca0032_mapping.json --dry-run
    python enrich_plytix_products.py --mapping mca0032_mapping.json --execute
"""

import argparse
import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add plytix scripts to path
PLYTIX_SCRIPTS = Path(__file__).parent.parent.parent / 'plytix-skills' / 'skills' / 'plytix-api' / 'scripts'
sys.path.insert(0, str(PLYTIX_SCRIPTS))

from plytix_api import PlytixAPI, PlytixAPIError


# =============================================================================
# ATTRIBUTE WRITE RULES
# =============================================================================

# ALWAYS WRITE - Amazon is authoritative for these
ALWAYS_WRITE = [
    'amazon_asin',
    'amazon_asin_secondary',  # Additional ASINs for same product (comma-separated)
    'amazon_parent_asin',
    'amazon_upc_imported',
    'amazon_ean_imported',
    'amazon_title_imported',
    'amazon_sync_status',
    'amazon_last_synced',
    'amazon_listing_status',
    'amazon_size',
    'amazon_color',
    'amazon_variation_theme',
    # NOTE: Image URLs are NOT stored as attributes - they are synced
    # as Plytix assets via sync_amazon_images.py
    # A+ Content (synced via sync_aplus_content.py)
    'amazon_aplus_content_key',
    'amazon_aplus_status',
    'amazon_aplus_content_type',
    'amazon_aplus_headline',
    'amazon_aplus_last_synced',
    'amazon_aplus_content',
]

# FILL EMPTY - Only write if Plytix field is empty
FILL_EMPTY = [
    'upc',
    'ean',
    'amazon_sku',
    'amazon_desired_parent',
]

# NEVER WRITE - Plytix owns content
NEVER_WRITE = [
    'amazon_long_description',
    'amazon_feature_1',
    'amazon_feature_2',
    'amazon_feature_3',
    'amazon_feature_4',
    'amazon_feature_5',
    'amazon_search_terms',
]


class PlytixEnricher:
    """Enriches Plytix products with Amazon data."""

    def __init__(self, account: str = None):
        self.api = PlytixAPI(account=account)
        self._amazon_hierarchy_id = None

    def get_amazon_hierarchy_id(self) -> Optional[str]:
        """Get the Amazon Hierarchy relationship ID."""
        if self._amazon_hierarchy_id:
            return self._amazon_hierarchy_id

        try:
            rel = self.api.get_relationship_by_name("Amazon Hierarchy")
            if rel:
                self._amazon_hierarchy_id = rel.get('id')
                return self._amazon_hierarchy_id
            print("Warning: Amazon Hierarchy relationship not found")
            return None
        except PlytixAPIError as e:
            print(f"Warning: Could not lookup Amazon Hierarchy relationship: {e}")
            return None

    def find_parent_product(self, variant_sku: str) -> Optional[Dict]:
        """
        Find the parent product for a variant SKU.

        Assumes SKU format: BASE-SIZE (e.g., MCA0032-W-12 -> MCA0032)
        """
        # Extract base SKU (remove size suffix)
        parts = variant_sku.split('-')
        if len(parts) >= 2:
            # Try progressively shorter prefixes
            for i in range(len(parts) - 1, 0, -1):
                base_sku = '-'.join(parts[:i])
                try:
                    result = self.api.search_products(
                        filters=[{'field': 'sku', 'operator': 'eq', 'value': base_sku}],
                        limit=1
                    )
                    products = result.get('data', [])
                    if products:
                        return products[0]
                except PlytixAPIError:
                    continue
        return None

    def create_relationships(
        self,
        parent_id: str,
        variant_ids: List[str],
        relationship_id: str,
        dry_run: bool = False
    ) -> Dict:
        """
        Create bidirectional Amazon Hierarchy relationships.

        Args:
            parent_id: Plytix parent product ID
            variant_ids: List of variant product IDs
            relationship_id: Amazon Hierarchy relationship ID
            dry_run: Preview without creating

        Returns:
            Results dict with created/errors
        """
        results = {'parent_to_variants': None, 'variants_to_parent': [], 'errors': []}

        if dry_run:
            results['parent_to_variants'] = {'dry_run': True, 'count': len(variant_ids)}
            results['variants_to_parent'] = [{'dry_run': True, 'variant_id': vid} for vid in variant_ids]
            return results

        # Link parent to all variants
        try:
            self.api.add_product_relationships(parent_id, relationship_id, variant_ids)
            results['parent_to_variants'] = {'success': True, 'count': len(variant_ids)}
        except PlytixAPIError as e:
            results['errors'].append(f"Parent->variants: {e}")

        # Link each variant back to parent
        for vid in variant_ids:
            try:
                self.api.add_product_relationships(vid, relationship_id, [parent_id])
                results['variants_to_parent'].append({'success': True, 'variant_id': vid})
            except PlytixAPIError as e:
                results['errors'].append(f"Variant {vid}->parent: {e}")

        return results

    def get_product(self, product_id: str) -> Optional[Dict]:
        """Get product by ID with attributes."""
        try:
            return self.api.get_product(product_id)
        except PlytixAPIError as e:
            print(f"Warning: Could not get product {product_id}: {e}")
            return None

    def build_attribute_update(
        self,
        mapping: Dict,
        existing_attrs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build attribute update payload based on write rules.

        Args:
            mapping: Matched mapping entry with Amazon data
            existing_attrs: Current Plytix product attributes

        Returns:
            Dict of attributes to update
        """
        updates = {}
        conflicts = []
        # Format timestamp as ISO 8601 for Plytix DateAttribute
        # Store both ISO (for DateAttribute) and human-readable (for notes)
        now = datetime.now(ZoneInfo('America/Chicago'))
        timestamp_iso = now.strftime('%Y-%m-%d')  # DateAttribute format
        timestamp_display = now.strftime('%Y-%m-%d %-I:%M %p CST')  # For notes

        # ALWAYS WRITE attributes
        if mapping.get('amazon_asin'):
            updates['amazon_asin'] = mapping['amazon_asin']

        # Secondary ASINs (other ASINs that map to this same Plytix product)
        if mapping.get('amazon_asin_secondary'):
            updates['amazon_asin_secondary'] = mapping['amazon_asin_secondary']

        if mapping.get('amazon_parent_asin'):
            updates['amazon_parent_asin'] = mapping['amazon_parent_asin']

        # Store Amazon's UPC/EAN in imported fields for comparison
        if mapping.get('amazon_upc'):
            updates['amazon_upc_imported'] = mapping['amazon_upc']
            # Check for conflict with existing Plytix UPC
            plytix_upc = existing_attrs.get('upc')
            if plytix_upc and plytix_upc != mapping['amazon_upc']:
                conflicts.append(f"UPC mismatch: Plytix={plytix_upc}, Amazon={mapping['amazon_upc']}")

        if mapping.get('amazon_ean'):
            updates['amazon_ean_imported'] = mapping['amazon_ean']
            plytix_ean = existing_attrs.get('ean')
            if plytix_ean and plytix_ean != mapping['amazon_ean']:
                conflicts.append(f"EAN mismatch: Plytix={plytix_ean}, Amazon={mapping['amazon_ean']}")

        if mapping.get('amazon_title'):
            updates['amazon_title_imported'] = mapping['amazon_title']

        # Amazon variation data
        if mapping.get('amazon_size'):
            updates['amazon_size'] = mapping['amazon_size']

        if mapping.get('amazon_color'):
            updates['amazon_color'] = mapping['amazon_color']

        if mapping.get('amazon_variation_theme'):
            updates['amazon_variation_theme'] = mapping['amazon_variation_theme']

        # Listing status
        if mapping.get('amazon_listing_status'):
            updates['amazon_listing_status'] = mapping['amazon_listing_status']

        # NOTE: Image URLs are synced as Plytix assets via sync_amazon_images.py
        # Not stored as text attributes

        # Sync tracking (DateAttribute uses ISO format)
        updates['amazon_last_synced'] = timestamp_iso

        # FILL EMPTY attributes (only Amazon-specific ones that we created)
        # Note: upc/ean are standard Plytix fields that may not exist
        # If they don't exist, they must be created in Plytix UI first
        if mapping.get('amazon_sku') and not existing_attrs.get('amazon_sku'):
            updates['amazon_sku'] = mapping['amazon_sku']

        # Set sync status based on conflicts
        if conflicts:
            updates['amazon_sync_status'] = 'conflict'
            updates['amazon_sync_conflict'] = True
            updates['amazon_sync_notes'] = f"[{timestamp_display}] Conflicts detected:\n" + "\n".join(f"  - {c}" for c in conflicts)
        else:
            updates['amazon_sync_status'] = 'synced'
            updates['amazon_sync_conflict'] = False

        return updates, conflicts

    def update_product(
        self,
        product_id: str,
        attributes: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict:
        """
        Update product with Amazon attributes.

        Args:
            product_id: Plytix product ID
            attributes: Attributes to update
            dry_run: Preview without saving

        Returns:
            Update result
        """
        if dry_run:
            return {'dry_run': True, 'product_id': product_id, 'attributes': attributes}

        return self.api.update_product(product_id, {'attributes': attributes})

    def enrich_from_mapping(
        self,
        mapping_path: str,
        dry_run: bool = False,
        create_relationships: bool = False
    ) -> Dict:
        """
        Enrich products from mapping file.

        Args:
            mapping_path: Path to mapping JSON
            dry_run: Preview without saving
            create_relationships: Create Amazon Hierarchy relationships

        Returns:
            Enrichment results
        """
        # Load mapping
        print(f"Loading mapping from {mapping_path}")
        with open(mapping_path) as f:
            mapping_data = json.load(f)

        matched = mapping_data.get('matched', [])
        print(f"Processing {len(matched)} matched products")

        results = {
            'updated': [],
            'conflicts': [],
            'errors': [],
            'skipped': [],
            'relationships': {'created': [], 'errors': []}
        }

        # Get Amazon Hierarchy relationship ID
        hierarchy_id = self.get_amazon_hierarchy_id() if create_relationships else None
        if create_relationships and not hierarchy_id:
            print("Warning: Cannot create relationships - Amazon Hierarchy not found")

        # Track variants by parent for relationship creation
        parent_variants = {}  # parent_id -> [variant_ids]

        for i, entry in enumerate(matched):
            product_id = entry.get('plytix_product_id')
            product_sku = entry.get('plytix_product_sku')
            asin = entry.get('amazon_asin')

            print(f"  [{i+1}/{len(matched)}] {product_sku} <- {asin}...", end=' ')

            if not product_id:
                print("SKIP (no product_id)")
                results['skipped'].append({
                    'sku': product_sku,
                    'reason': 'No product_id in mapping'
                })
                continue

            # Get current product attributes
            product = self.get_product(product_id)
            if not product:
                print("ERROR (product not found)")
                results['errors'].append({
                    'product_id': product_id,
                    'sku': product_sku,
                    'error': 'Product not found in Plytix'
                })
                continue

            existing_attrs = product.get('attributes', {})

            # Build attribute update
            updates, conflicts = self.build_attribute_update(entry, existing_attrs)

            try:
                result = self.update_product(product_id, updates, dry_run)

                if conflicts:
                    print(f"CONFLICT ({len(conflicts)} issues)")
                    results['conflicts'].append({
                        'product_id': product_id,
                        'sku': product_sku,
                        'asin': asin,
                        'conflicts': conflicts,
                        'dry_run': dry_run
                    })
                else:
                    print("OK")

                results['updated'].append({
                    'product_id': product_id,
                    'sku': product_sku,
                    'asin': asin,
                    'attributes_updated': list(updates.keys()),
                    'dry_run': dry_run
                })

                # Track variant for relationship creation
                if create_relationships and hierarchy_id:
                    parent = self.find_parent_product(product_sku)
                    if parent and parent.get('id') != product_id:
                        parent_id = parent['id']
                        if parent_id not in parent_variants:
                            parent_variants[parent_id] = {'sku': parent.get('sku'), 'variants': []}
                        parent_variants[parent_id]['variants'].append({
                            'id': product_id,
                            'sku': product_sku
                        })

            except PlytixAPIError as e:
                print(f"ERROR ({e})")
                results['errors'].append({
                    'product_id': product_id,
                    'sku': product_sku,
                    'asin': asin,
                    'error': str(e)
                })

        # Create relationships after all products are enriched
        if create_relationships and hierarchy_id and parent_variants:
            print(f"\nCreating Amazon Hierarchy relationships...")
            for parent_id, data in parent_variants.items():
                parent_sku = data['sku']
                variant_ids = [v['id'] for v in data['variants']]
                print(f"  {parent_sku} <-> {len(variant_ids)} variants...", end=' ')

                rel_result = self.create_relationships(
                    parent_id, variant_ids, hierarchy_id, dry_run
                )

                if rel_result['errors']:
                    print(f"PARTIAL ({len(rel_result['errors'])} errors)")
                    results['relationships']['errors'].extend(rel_result['errors'])
                else:
                    print("OK")

                results['relationships']['created'].append({
                    'parent_id': parent_id,
                    'parent_sku': parent_sku,
                    'variant_count': len(variant_ids),
                    'dry_run': dry_run
                })

        return results


def print_results(results: Dict, dry_run: bool = False):
    """Print enrichment results."""
    mode = "[DRY RUN] " if dry_run else ""

    print("\n" + "=" * 60)
    print(f"{mode}ENRICHMENT RESULTS")
    print("=" * 60)
    print(f"Updated:   {len(results['updated'])}")
    print(f"Conflicts: {len(results['conflicts'])}")
    print(f"Errors:    {len(results['errors'])}")
    print(f"Skipped:   {len(results['skipped'])}")

    # Relationship results
    rel_results = results.get('relationships', {})
    if rel_results.get('created') or rel_results.get('errors'):
        print(f"Relationships: {len(rel_results.get('created', []))} parent-variant groups")
        if rel_results.get('errors'):
            print(f"  Relationship errors: {len(rel_results['errors'])}")

    print("=" * 60)

    if results['conflicts']:
        print("\nConflicts requiring review:")
        for c in results['conflicts'][:5]:
            print(f"  {c['sku']} ({c['asin']}):")
            for conflict in c['conflicts']:
                print(f"    - {conflict}")

    if results['errors']:
        print("\nErrors:")
        for e in results['errors'][:5]:
            print(f"  {e.get('sku', e.get('product_id'))}: {e['error']}")

    if rel_results.get('errors'):
        print("\nRelationship errors:")
        for e in rel_results['errors'][:5]:
            print(f"  {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Enrich Plytix products with Amazon data"
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
        help="Preview changes without saving"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute the enrichment"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output results JSON path"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output full results as JSON"
    )
    parser.add_argument(
        "--create-relationships",
        action="store_true",
        help="Create Amazon Hierarchy relationships between parent and variants"
    )

    args = parser.parse_args()

    # Require explicit flag
    if not args.dry_run and not args.execute:
        print("Error: Must specify --dry-run or --execute", file=sys.stderr)
        print("\nUse --dry-run to preview changes without saving")
        print("Use --execute to actually update Plytix products")
        sys.exit(1)

    try:
        enricher = PlytixEnricher(account=args.plytix_account)

        results = enricher.enrich_from_mapping(
            mapping_path=args.mapping,
            dry_run=args.dry_run,
            create_relationships=args.create_relationships
        )

        if args.json:
            print("\n" + json.dumps(results, indent=2, default=str))
        else:
            print_results(results, dry_run=args.dry_run)

        # Save results if output specified
        if args.output:
            output_file = Path(args.output)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\nResults saved to {args.output}")

        if results['errors']:
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
