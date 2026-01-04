#!/usr/bin/env python3
"""
Generate ASIN to Plytix Variant Mapping

Matches Amazon ASINs to existing Plytix variants by UPC, SKU, or other identifiers.

Usage:
    python generate_asin_mapping.py --amazon-data mca0032_amazon.json --output mapping.json
    python generate_asin_mapping.py --amazon-data mca0032_amazon.json --dry-run
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add plytix scripts to path
PLYTIX_SCRIPTS = Path(__file__).parent.parent.parent / 'plytix-skills' / 'skills' / 'plytix-api' / 'scripts'
sys.path.insert(0, str(PLYTIX_SCRIPTS))

from plytix_api import PlytixAPI, PlytixAPIError


class PlytixProductMapper:
    """Maps Amazon ASINs to Plytix products (Plytix stores variants as products)."""

    def __init__(self, account: str = None):
        self.api = PlytixAPI(account=account)
        self._products_cache = {}

    def search_products_by_style(self, style: str) -> List[Dict]:
        """
        Search for products by style number.

        Args:
            style: Style number (e.g., MCA0032)

        Returns:
            List of product objects with attributes
        """
        all_products = []
        page = 1

        while True:
            result = self.api.search_products(
                filters=[{'field': 'sku', 'operator': 'like', 'value': style}],
                attributes=['sku', 'label', 'gtin', 'ean', 'brand'],
                limit=100,
                page=page
            )
            products = result.get('data', [])
            if not products:
                break
            all_products.extend(products)
            print(f"  Loaded {len(all_products)} products...", end='\r')
            if len(products) < 100:
                break
            page += 1

        print(f"  Loaded {len(all_products)} products total")
        return all_products

    def build_product_index(self, style: str) -> Dict[str, Dict]:
        """
        Build index of Plytix products by various identifiers.

        Args:
            style: Style number to search for

        Returns:
            Dict with keys for upc, ean, sku pointing to product data
        """
        products = self.search_products_by_style(style)
        index = {
            'by_gtin': {},
            'by_ean': {},
            'by_sku': {}
        }

        print("Building product index...")
        for product in products:
            product_id = product.get('id')
            product_sku = product.get('sku', '')
            attributes = product.get('attributes', {})

            # GTIN is a native Plytix field (not in attributes)
            gtin = product.get('gtin') or attributes.get('gtin')

            product_data = {
                'product_id': product_id,
                'product_sku': product_sku,
                'label': product.get('label'),
                'gtin': gtin,
                'ean': attributes.get('ean'),
                'brand': attributes.get('brand'),
                'attributes': attributes
            }

            # Index by GTIN/UPC (if available)
            if gtin:
                gtin_normalized = gtin.lstrip('0')
                index['by_gtin'][gtin_normalized] = product_data

            # Index by EAN (if available)
            ean = attributes.get('ean')
            if ean:
                ean_normalized = ean.lstrip('0')
                index['by_ean'][ean_normalized] = product_data

            # Index by SKU (most reliable for Plytix matching)
            if product_sku:
                index['by_sku'][product_sku.upper()] = product_data

        print(f"\nIndex built: {len(index['by_sku'])} SKUs, {len(index['by_gtin'])} GTINs")
        return index

    def match_amazon_to_plytix(
        self,
        amazon_variants: List[Dict],
        product_index: Dict,
        marketplace: str = 'US'
    ) -> Dict[str, List]:
        """
        Match Amazon variants to Plytix products.

        Option B approach: Each ASIN becomes a separate entry (no consolidation).
        Generates suggested_sku in format AMZN-{marketplace}-{ASIN}.

        Args:
            amazon_variants: List of Amazon variant data
            product_index: Plytix product index (by_upc, by_ean, by_sku)
            marketplace: Amazon marketplace code (US, CA, MX, etc.)

        Returns:
            Dict with matched, unmatched_amazon lists
        """
        results = {
            'matched': [],
            'unmatched_amazon': []
        }

        for amazon in amazon_variants:
            asin = amazon.get('amazon_asin')
            amazon_sku = amazon.get('amazon_sku', '')
            upc = amazon.get('upc', '')
            ean = amazon.get('ean', '')

            match = None
            match_method = None

            # Try matching by GTIN/UPC first (if Plytix has GTIN data)
            if upc:
                upc_normalized = upc.lstrip('0')
                if upc_normalized in product_index['by_gtin']:
                    match = product_index['by_gtin'][upc_normalized]
                    match_method = 'gtin'

            # Try EAN if no UPC match
            if not match and ean:
                ean_normalized = ean.lstrip('0')
                if ean_normalized in product_index['by_ean']:
                    match = product_index['by_ean'][ean_normalized]
                    match_method = 'ean'

            # Try SKU matching (most reliable for Plytix)
            if not match and amazon_sku:
                sku_upper = amazon_sku.upper()
                if sku_upper in product_index['by_sku']:
                    match = product_index['by_sku'][sku_upper]
                    match_method = 'sku'

            if match:
                # Each ASIN gets its own entry with suggested SKU
                results['matched'].append({
                    # Amazon product SKU (new Plytix product)
                    'suggested_sku': f'AMZN-{marketplace}-{asin}',
                    'marketplace': marketplace,
                    # Amazon identifiers
                    'amazon_asin': asin,
                    'amazon_parent_asin': amazon.get('amazon_parent_asin'),
                    'amazon_sku': amazon_sku,
                    'amazon_upc': upc,
                    'amazon_ean': ean,
                    # Amazon metadata
                    'amazon_size': amazon.get('size'),
                    'amazon_color': amazon.get('color'),
                    'amazon_title': amazon.get('title'),
                    'amazon_variation_theme': amazon.get('variation_theme'),
                    'amazon_listing_status': amazon.get('amazon_listing_status'),
                    # Image URLs (highest resolution per variant)
                    'amazon_image_main': amazon.get('amazon_image_main'),
                    'amazon_image_variant_1': amazon.get('amazon_image_variant_1'),
                    'amazon_image_variant_2': amazon.get('amazon_image_variant_2'),
                    'amazon_image_variant_3': amazon.get('amazon_image_variant_3'),
                    'amazon_image_variant_4': amazon.get('amazon_image_variant_4'),
                    'amazon_image_variant_5': amazon.get('amazon_image_variant_5'),
                    'amazon_image_variant_6': amazon.get('amazon_image_variant_6'),
                    'amazon_image_variant_7': amazon.get('amazon_image_variant_7'),
                    'amazon_image_variant_8': amazon.get('amazon_image_variant_8'),
                    'amazon_image_swatch': amazon.get('amazon_image_swatch'),
                    # Canonical Plytix product reference (for Amazon Listings relationship)
                    'canonical_plytix_sku': match['product_sku'],
                    'canonical_plytix_id': match['product_id'],
                    'canonical_plytix_label': match.get('label'),
                    'canonical_plytix_gtin': match.get('gtin'),
                    # Match metadata
                    'match_method': match_method,
                    'gtin_match': upc == match.get('gtin') if upc and match.get('gtin') else None
                })
            else:
                results['unmatched_amazon'].append({
                    'suggested_sku': f'AMZN-{marketplace}-{asin}',
                    'marketplace': marketplace,
                    'amazon_asin': asin,
                    'amazon_sku': amazon_sku,
                    'amazon_upc': upc,
                    'amazon_size': amazon.get('size'),
                    'amazon_color': amazon.get('color'),
                    'amazon_title': amazon.get('title'),
                    'reason': 'No matching Plytix variant found'
                })

        return results


def generate_mapping(
    amazon_data_path: str,
    output_path: str = None,
    plytix_account: str = None,
    style: str = None,
    marketplace: str = 'US',
    dry_run: bool = False
) -> Dict:
    """
    Generate ASIN to Plytix mapping.

    Option B approach: Each ASIN becomes a separate Amazon product in Plytix.
    Generates suggested_sku in format AMZN-{marketplace}-{ASIN}.

    Args:
        amazon_data_path: Path to Amazon export JSON
        output_path: Output path for mapping JSON
        plytix_account: Plytix account alias
        style: Style number to search for in Plytix (e.g., MCA0032)
        marketplace: Amazon marketplace code (US, CA, MX, etc.)
        dry_run: Preview without saving

    Returns:
        Mapping results
    """
    # Load Amazon data
    print(f"Loading Amazon data from {amazon_data_path}")
    with open(amazon_data_path) as f:
        amazon_export = json.load(f)

    amazon_variants = amazon_export.get('variants', [])
    print(f"Loaded {len(amazon_variants)} Amazon variants")
    print(f"Marketplace: {marketplace}")

    # Determine style from metadata if not provided
    if not style:
        style = amazon_export.get('metadata', {}).get('style')
    if not style:
        # Try to extract from first variant SKU
        if amazon_variants:
            first_sku = amazon_variants[0].get('amazon_sku', '')
            if first_sku and '-' in first_sku:
                style = first_sku.split('-')[0]

    if not style:
        raise ValueError("Could not determine style. Please provide --style argument.")

    print(f"Style: {style}")

    # Initialize mapper
    mapper = PlytixProductMapper(account=plytix_account)

    # Build Plytix index for this style
    print(f"\nBuilding Plytix product index for {style}...")
    index = mapper.build_product_index(style)

    # Match variants
    print("\nMatching Amazon variants to Plytix products...")
    results = mapper.match_amazon_to_plytix(amazon_variants, index, marketplace)

    # Build output
    output = {
        'metadata': {
            'source_file': amazon_data_path,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'marketplace': marketplace,
            'amazon_count': len(amazon_variants),
            'matched_count': len(results['matched']),
            'unmatched_count': len(results['unmatched_amazon'])
        },
        'matched': results['matched'],
        'unmatched_amazon': results['unmatched_amazon']
    }

    # Print summary
    print("\n" + "=" * 60)
    print("MAPPING RESULTS")
    print("=" * 60)
    print(f"Amazon variants:     {len(amazon_variants)}")
    print(f"Matched to Plytix:   {len(results['matched'])}")
    print(f"Unmatched Amazon:    {len(results['unmatched_amazon'])}")
    print("=" * 60)

    if results['matched']:
        print("\nAmazon products to create:")
        for m in results['matched'][:10]:
            print(f"  {m['suggested_sku']} -> canonical: {m['canonical_plytix_sku']} (via {m['match_method']})")
        if len(results['matched']) > 10:
            print(f"  ... and {len(results['matched']) - 10} more")

    if results['unmatched_amazon']:
        print("\nUnmatched Amazon variants (will create without canonical link):")
        for u in results['unmatched_amazon'][:5]:
            print(f"  {u['suggested_sku']} ({u['amazon_sku']}) - {u['amazon_title'][:50] if u.get('amazon_title') else 'N/A'}...")

    # Save output
    if not dry_run and output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        print(f"\nMapping saved to {output_path}")
    elif dry_run:
        print("\n[DRY RUN - No file saved]")

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Generate ASIN to Plytix mapping (Option B: separate Amazon products)"
    )
    parser.add_argument(
        "--amazon-data", "-a",
        required=True,
        help="Path to Amazon export JSON"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output mapping JSON path"
    )
    parser.add_argument(
        "--plytix-account",
        help="Plytix account alias"
    )
    parser.add_argument(
        "--style", "-s",
        help="Style number to search for in Plytix (e.g., MCA0032)"
    )
    parser.add_argument(
        "--marketplace", "-m",
        default="US",
        help="Amazon marketplace code (default: US). Options: US, CA, MX, UK, DE, etc."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without saving"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output full results as JSON"
    )

    args = parser.parse_args()

    # Set default output path if not specified
    output_path = args.output
    if not output_path and not args.dry_run:
        input_path = Path(args.amazon_data)
        output_path = str(input_path.parent / f"{input_path.stem}_mapping.json")

    try:
        results = generate_mapping(
            amazon_data_path=args.amazon_data,
            output_path=output_path,
            plytix_account=args.plytix_account,
            style=args.style,
            marketplace=args.marketplace,
            dry_run=args.dry_run
        )

        if args.json:
            print("\n" + json.dumps(results, indent=2, default=str))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
