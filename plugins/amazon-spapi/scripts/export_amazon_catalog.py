#!/usr/bin/env python3
"""
Export Amazon Catalog Data for Plytix Integration

Exports Amazon catalog data to JSON for mapping to Plytix variants.
Supports searching by style number, brand, or ASIN list.

Usage:
    python export_amazon_catalog.py --style MCA0032 --output mca0032_amazon.json
    python export_amazon_catalog.py --asins B07X8Z63ZL,B07X8ZABCD --output asins.json
    python export_amazon_catalog.py --brand "Twisted X" --keywords "wedge boot" --output all.json
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient
from spapi_catalog import CatalogItemsAPI


# Data sections to retrieve for each ASIN
INCLUDED_DATA = ['summaries', 'identifiers', 'relationships', 'attributes', 'images']


class AmazonCatalogExporter:
    """Export Amazon catalog data for Plytix integration."""

    def __init__(self, profile: str = 'production'):
        self.auth = SPAPIAuth(profile=profile)
        self.client = SPAPIClient(self.auth)
        self.catalog = CatalogItemsAPI(self.client)
        self.marketplace_id = self.auth.get_marketplace_id()

    def search_by_style(self, style: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Search for products by style number.

        Args:
            style: Product style number (e.g., MCA0032)
            max_results: Maximum results to return

        Returns:
            List of catalog items
        """
        all_items = []
        page_token = None

        while len(all_items) < max_results:
            result = self.catalog.search_catalog_items(
                keywords=[style],
                included_data=['summaries', 'productTypes'],
                page_size=20,
                page_token=page_token
            )

            items = result.get('items', [])
            all_items.extend(items)

            # Check for next page
            pagination = result.get('pagination', {})
            page_token = pagination.get('nextToken')
            if not page_token or not items:
                break

            time.sleep(0.5)  # Rate limiting

        return all_items[:max_results]

    def get_item_details(self, asin: str) -> Optional[Dict[str, Any]]:
        """
        Get full details for a single ASIN.

        Args:
            asin: Amazon ASIN

        Returns:
            Item details or None if not found
        """
        # Get each data section separately (API limitation)
        result = {'asin': asin}

        for data_type in INCLUDED_DATA:
            try:
                response = self.catalog.get_catalog_item(
                    asin=asin,
                    included_data=[data_type]
                )
                if data_type in response:
                    result[data_type] = response[data_type]
                time.sleep(0.2)  # Rate limiting
            except Exception as e:
                print(f"  Warning: Could not get {data_type} for {asin}: {e}", file=sys.stderr)

        return result if len(result) > 1 else None

    def extract_variant_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured variant data from raw API response.

        Args:
            item: Raw catalog item data

        Returns:
            Structured variant data for Plytix mapping
        """
        asin = item.get('asin')

        # Extract from summaries
        summary = {}
        summaries = item.get('summaries', [])
        if summaries:
            for s in summaries:
                if s.get('marketplaceId') == self.marketplace_id:
                    summary = s
                    break

        # Extract identifiers (UPC, EAN)
        upc = None
        ean = None
        identifiers = item.get('identifiers', [])
        for id_set in identifiers:
            if id_set.get('marketplaceId') == self.marketplace_id:
                for ident in id_set.get('identifiers', []):
                    if ident.get('identifierType') == 'UPC':
                        upc = ident.get('identifier')
                    elif ident.get('identifierType') == 'EAN':
                        ean = ident.get('identifier')

        # Extract relationships (parent ASIN, variation theme)
        parent_asin = None
        variation_theme = None
        relationships = item.get('relationships', [])
        for rel_set in relationships:
            if rel_set.get('marketplaceId') == self.marketplace_id:
                for rel in rel_set.get('relationships', []):
                    if rel.get('type') == 'VARIATION':
                        parents = rel.get('parentAsins', [])
                        if parents:
                            parent_asin = parents[0]
                        theme = rel.get('variationTheme', {})
                        variation_theme = theme.get('theme')

        # Extract images
        images = {}
        image_data = item.get('images', [])
        for img_set in image_data:
            if img_set.get('marketplaceId') == self.marketplace_id:
                for img in img_set.get('images', []):
                    variant = img.get('variant', 'MAIN')
                    link = img.get('link')
                    height = img.get('height', 0)
                    # Store highest resolution for each variant
                    current = images.get(variant, {})
                    if not current or height > current.get('height', 0):
                        images[variant] = {'link': link, 'height': height}

        # Derive listing status from item_classification
        # Valid Plytix values: active, inactive, suppressed, unknown
        listing_status = None
        classification = summary.get('itemClassification')
        if classification in ('BASE_PRODUCT', 'VARIATION_PARENT'):
            listing_status = None  # Not applicable to parents (skip in Plytix)
        elif summary:
            # If item exists in catalog, consider active
            listing_status = 'active'
        else:
            listing_status = 'inactive'

        # Extract from attributes
        attributes = item.get('attributes', {})

        def get_attr_value(attr_name: str, field: str = 'value') -> Optional[str]:
            """Helper to extract attribute value."""
            attr_list = attributes.get(attr_name, [])
            for attr in attr_list:
                if attr.get('marketplace_id') == self.marketplace_id:
                    return attr.get(field)
            return None

        def get_attr_text(attr_name: str) -> Optional[str]:
            """Helper to extract text attribute value."""
            attr_list = attributes.get(attr_name, [])
            for attr in attr_list:
                if attr.get('marketplace_id') == self.marketplace_id:
                    # Check for language_tag value (text fields)
                    if 'value' in attr:
                        return attr.get('value')
                    elif 'language_tag' in attr:
                        return attr.get('value')
            return None

        # Build structured output
        return {
            # Amazon identifiers
            'amazon_asin': asin,
            'amazon_parent_asin': parent_asin,
            'amazon_sku': get_attr_value('part_number'),

            # Product identifiers
            'upc': upc,
            'ean': ean,

            # Product info
            'title': summary.get('itemName') or get_attr_text('item_name'),
            'brand': summary.get('brand') or get_attr_text('brand'),
            'model_number': summary.get('modelNumber') or get_attr_value('model_number'),
            'part_number': summary.get('partNumber') or get_attr_value('part_number'),

            # Variation data
            'size': summary.get('size') or get_attr_value('size'),
            'color': summary.get('color') or get_attr_text('color'),
            'variation_theme': variation_theme,

            # Classification
            'item_classification': summary.get('itemClassification'),
            'product_type': None,  # Will be set from productTypes if available

            # Listing status (derived from item_classification)
            'amazon_listing_status': listing_status,

            # Images (highest resolution for each variant)
            'amazon_image_main': images.get('MAIN', {}).get('link'),
            'amazon_image_variant_1': images.get('PT01', {}).get('link'),
            'amazon_image_variant_2': images.get('PT02', {}).get('link'),
            'amazon_image_variant_3': images.get('PT03', {}).get('link'),
            'amazon_image_variant_4': images.get('PT04', {}).get('link'),
            'amazon_image_variant_5': images.get('PT05', {}).get('link'),
            'amazon_image_variant_6': images.get('PT06', {}).get('link'),
            'amazon_image_variant_7': images.get('PT07', {}).get('link'),
            'amazon_image_variant_8': images.get('PT08', {}).get('link'),
            'amazon_image_swatch': images.get('SWATCH', {}).get('link'),

            # Raw data for reference
            '_raw_summary': summary,
            '_raw_attributes': attributes,
            '_raw_images': images
        }

    def fetch_missing_parents(
        self,
        variants: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Fetch catalog data for parent ASINs not already in the variants list.

        Amazon VARIATION_PARENTs are often not returned by brand/keyword searches.
        This method ensures parent ASINs referenced by children are included.

        Args:
            variants: List of already-extracted variant data

        Returns:
            List of parent variant data to add to export
        """
        # Collect ASINs already in export
        existing_asins = {v.get('amazon_asin') for v in variants}

        # Collect unique parent ASINs from variants
        parent_asins = set()
        for v in variants:
            parent = v.get('amazon_parent_asin')
            if parent and parent not in existing_asins:
                parent_asins.add(parent)

        if not parent_asins:
            return []

        print(f"\nFetching {len(parent_asins)} missing parent ASINs...")
        parent_variants = []
        for i, asin in enumerate(sorted(parent_asins)):
            print(f"  [{i+1}/{len(parent_asins)}] Getting details for parent {asin}...")

            details = self.get_item_details(asin)
            if details:
                variant_data = self.extract_variant_data(details)
                parent_variants.append(variant_data)

        print(f"  Added {len(parent_variants)} parent ASINs to export")
        return parent_variants

    def export_style(
        self,
        style: str,
        output_path: str,
        max_results: int = 100,
        include_parents: bool = True
    ) -> Dict[str, Any]:
        """
        Export all variants for a style to JSON.

        Args:
            style: Style number (e.g., MCA0032)
            output_path: Output JSON file path
            max_results: Maximum results
            include_parents: Fetch and include parent ASINs not in initial results

        Returns:
            Export summary
        """
        print(f"Searching for style: {style}")

        # Search for items
        items = self.search_by_style(style, max_results)
        print(f"Found {len(items)} items in search")

        # Get full details for each
        variants = []
        for i, item in enumerate(items):
            asin = item.get('asin')
            print(f"  [{i+1}/{len(items)}] Getting details for {asin}...")

            details = self.get_item_details(asin)
            if details:
                variant_data = self.extract_variant_data(details)
                variants.append(variant_data)

        # Fetch missing parent ASINs
        parent_count = 0
        if include_parents:
            parent_variants = self.fetch_missing_parents(variants)
            variants.extend(parent_variants)
            parent_count = len(parent_variants)

        # Build export
        export_data = {
            'metadata': {
                'style': style,
                'marketplace_id': self.marketplace_id,
                'export_date': datetime.utcnow().isoformat() + 'Z',
                'item_count': len(variants),
                'parent_asins_added': parent_count
            },
            'variants': variants
        }

        # Write to file
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        print(f"\nExported {len(variants)} variants to {output_path}")
        if parent_count:
            print(f"  (includes {parent_count} parent ASINs)")
        return export_data['metadata']

    def export_asins(
        self,
        asins: List[str],
        output_path: str,
        include_parents: bool = True
    ) -> Dict[str, Any]:
        """
        Export specific ASINs to JSON.

        Args:
            asins: List of ASINs
            output_path: Output JSON file path
            include_parents: Fetch and include parent ASINs not in list

        Returns:
            Export summary
        """
        print(f"Exporting {len(asins)} ASINs")

        variants = []
        for i, asin in enumerate(asins):
            print(f"  [{i+1}/{len(asins)}] Getting details for {asin}...")

            details = self.get_item_details(asin)
            if details:
                variant_data = self.extract_variant_data(details)
                variants.append(variant_data)

        # Fetch missing parent ASINs
        parent_count = 0
        if include_parents:
            parent_variants = self.fetch_missing_parents(variants)
            variants.extend(parent_variants)
            parent_count = len(parent_variants)

        # Build export
        export_data = {
            'metadata': {
                'source': 'asin_list',
                'marketplace_id': self.marketplace_id,
                'export_date': datetime.utcnow().isoformat() + 'Z',
                'item_count': len(variants),
                'parent_asins_added': parent_count
            },
            'variants': variants
        }

        # Write to file
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        print(f"\nExported {len(variants)} variants to {output_path}")
        if parent_count:
            print(f"  (includes {parent_count} parent ASINs)")
        return export_data['metadata']


def main():
    parser = argparse.ArgumentParser(
        description="Export Amazon catalog data for Plytix integration"
    )
    parser.add_argument(
        "--style",
        help="Style number to search (e.g., MCA0032)"
    )
    parser.add_argument(
        "--asins",
        help="Comma-separated list of ASINs"
    )
    parser.add_argument(
        "--brand",
        help="Brand name to filter"
    )
    parser.add_argument(
        "--keywords",
        help="Additional search keywords"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output JSON file path"
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=100,
        help="Maximum results (default: 100)"
    )
    parser.add_argument(
        "--profile",
        default="production",
        help="SP-API config profile"
    )
    parser.add_argument(
        "--include-parents",
        action="store_true",
        default=True,
        help="Fetch parent ASINs not in initial results (default: enabled)"
    )
    parser.add_argument(
        "--no-parents",
        action="store_true",
        help="Skip fetching parent ASINs"
    )

    args = parser.parse_args()

    # Resolve include_parents flag
    include_parents = args.include_parents and not args.no_parents

    # Validate arguments
    if not args.style and not args.asins:
        print("Error: Must specify --style or --asins", file=sys.stderr)
        sys.exit(1)

    try:
        exporter = AmazonCatalogExporter(profile=args.profile)

        if args.asins:
            asins = [a.strip() for a in args.asins.split(',')]
            exporter.export_asins(asins, args.output, include_parents=include_parents)
        else:
            exporter.export_style(args.style, args.output, args.max_results, include_parents=include_parents)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
