#!/usr/bin/env python3
"""
Sync A+ Content from Amazon to Plytix

Fetches A+ Content data from Amazon and stores it in Plytix product attributes.

Usage:
    python sync_aplus_content.py --mapping mca0032_mapping.json --dry-run
    python sync_aplus_content.py --mapping mca0032_mapping.json --execute
    python sync_aplus_content.py --asin B07X8Z63ZL --dry-run
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
from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient, SPAPIError
from spapi_aplus import AplusContentAPI


# Plytix attributes for A+ Content
APLUS_ATTRIBUTES = [
    'amazon_aplus_content_key',
    'amazon_aplus_status',
    'amazon_aplus_content_type',
    'amazon_aplus_last_synced',
    'amazon_aplus_headline',
    'amazon_aplus_content',  # Serialized JSON for full content
]


class AplusContentSyncer:
    """Sync A+ Content from Amazon to Plytix."""

    def __init__(
        self,
        spapi_profile: str = 'production',
        plytix_account: str = None
    ):
        """
        Initialize A+ Content syncer.

        Args:
            spapi_profile: SP-API configuration profile
            plytix_account: Plytix account alias
        """
        # Initialize Amazon SP-API
        self.auth = SPAPIAuth(profile=spapi_profile)
        self.client = SPAPIClient(self.auth)
        self.aplus_api = AplusContentAPI(self.client)
        self.marketplace_id = self.auth.get_marketplace_id()

        # Initialize Plytix API
        self.plytix = PlytixAPI(account=plytix_account)

        # Cache for content lookups
        self._content_cache = {}

    def get_aplus_content_for_asin(self, asin: str) -> Optional[Dict[str, Any]]:
        """
        Get A+ Content for a specific ASIN.

        Args:
            asin: Amazon ASIN

        Returns:
            A+ Content data or None if not found
        """
        if asin in self._content_cache:
            return self._content_cache[asin]

        try:
            content = self.aplus_api.get_content_for_asin(
                asin=asin,
                marketplace_id=self.marketplace_id
            )
            self._content_cache[asin] = content
            return content
        except SPAPIError as e:
            print(f"  Warning: Could not get A+ Content for {asin}: {e}")
            self._content_cache[asin] = None
            return None

    def extract_content_summary(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract key information from A+ Content response.

        Args:
            content: Full A+ Content response

        Returns:
            Summarized content data for Plytix storage
        """
        if not content:
            return {}

        # Extract content document
        doc = content.get("contentDocument", {})

        # Extract headline from first module if available
        headline = None
        modules = doc.get("contentModuleList", [])
        for module in modules:
            # Try to find a headline in various module types
            for key in module:
                if "Module" in key and key != "contentModuleType":
                    module_data = module[key]
                    if isinstance(module_data, dict):
                        if "headline" in module_data:
                            headline_obj = module_data["headline"]
                            if isinstance(headline_obj, dict):
                                headline = headline_obj.get("value")
                            else:
                                headline = headline_obj
                            break
            if headline:
                break

        # Extract content type and status
        content_type = doc.get("contentType")
        content_key = doc.get("contentReferenceKey")

        # Get status from metadata
        metadata = content.get("contentMetadata", {})
        status = metadata.get("status")

        return {
            "content_reference_key": content_key,
            "content_type": content_type,
            "status": status,
            "headline": headline,
            "locale": doc.get("locale"),
            "module_count": len(modules),
            "full_content": doc  # Store full document for reference
        }

    def update_plytix_product(
        self,
        product_id: str,
        aplus_data: Dict[str, Any],
        dry_run: bool = False
    ) -> bool:
        """
        Update Plytix product with A+ Content data.

        Args:
            product_id: Plytix product ID
            aplus_data: Extracted A+ Content data
            dry_run: Preview without updating

        Returns:
            True if successful, False otherwise
        """
        if not aplus_data:
            return False

        # Build attribute updates
        attributes = {
            "amazon_aplus_content_key": aplus_data.get("content_reference_key"),
            "amazon_aplus_status": aplus_data.get("status"),
            "amazon_aplus_content_type": aplus_data.get("content_type"),
            "amazon_aplus_headline": aplus_data.get("headline"),
            "amazon_aplus_last_synced": datetime.now(timezone.utc).isoformat(),
        }

        # Store full content as serialized JSON
        if aplus_data.get("full_content"):
            attributes["amazon_aplus_content"] = json.dumps(
                aplus_data["full_content"],
                indent=None,
                default=str
            )

        # Filter out None values
        attributes = {k: v for k, v in attributes.items() if v is not None}

        if dry_run:
            print(f"    [PREVIEW] Would update {len(attributes)} A+ attributes")
            return True

        try:
            self.plytix.update_product(product_id, {"attributes": attributes})
            return True
        except PlytixAPIError as e:
            print(f"    Error updating Plytix product {product_id}: {e}")
            return False

    def sync_product(
        self,
        mapping: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Sync A+ Content for a single product.

        Args:
            mapping: Product mapping entry with ASIN and Plytix product ID
            dry_run: Preview without updating

        Returns:
            Sync result for this product
        """
        asin = mapping.get("amazon_asin")
        product_id = mapping.get("plytix_product_id")
        product_sku = mapping.get("plytix_product_sku", asin)

        result = {
            "asin": asin,
            "product_sku": product_sku,
            "has_aplus": False,
            "synced": False,
            "error": None
        }

        # Get A+ Content for this ASIN
        content = self.get_aplus_content_for_asin(asin)
        time.sleep(0.2)  # Rate limiting

        if not content:
            return result

        result["has_aplus"] = True

        # Extract content summary
        aplus_data = self.extract_content_summary(content)

        if dry_run:
            print(f"    Content Key: {aplus_data.get('content_reference_key')}")
            print(f"    Type: {aplus_data.get('content_type')}")
            print(f"    Status: {aplus_data.get('status')}")
            print(f"    Modules: {aplus_data.get('module_count')}")
            if aplus_data.get("headline"):
                print(f"    Headline: {aplus_data['headline'][:50]}...")
            result["synced"] = True
            return result

        # Update Plytix product
        if self.update_plytix_product(product_id, aplus_data, dry_run):
            result["synced"] = True
        else:
            result["error"] = "Failed to update Plytix"

        return result

    def sync_all(
        self,
        mappings: List[Dict[str, Any]],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Sync A+ Content for all products in mapping.

        Args:
            mappings: List of product mappings
            dry_run: Preview without updating

        Returns:
            Summary of sync operation
        """
        summary = {
            "total_products": len(mappings),
            "products_checked": 0,
            "with_aplus": 0,
            "synced": 0,
            "errors": 0,
            "product_results": []
        }

        for i, mapping in enumerate(mappings):
            asin = mapping.get("amazon_asin")
            sku = mapping.get("plytix_product_sku", asin)

            print(f"\n[{i+1}/{len(mappings)}] {sku} ({asin})")
            summary["products_checked"] += 1

            result = self.sync_product(mapping, dry_run)
            summary["product_results"].append(result)

            if result["has_aplus"]:
                summary["with_aplus"] += 1
            if result["synced"]:
                summary["synced"] += 1
            if result["error"]:
                summary["errors"] += 1

        return summary


def sync_aplus_content(
    mapping_path: str = None,
    asins: List[str] = None,
    output_path: str = None,
    spapi_profile: str = 'production',
    plytix_account: str = None,
    dry_run: bool = False
) -> Dict:
    """
    Sync A+ Content from Amazon to Plytix.

    Args:
        mapping_path: Path to mapping JSON file
        asins: List of specific ASINs to sync
        output_path: Output path for sync report
        spapi_profile: SP-API configuration profile
        plytix_account: Plytix account alias
        dry_run: Preview without updating

    Returns:
        Sync summary
    """
    mappings = []

    if mapping_path:
        print(f"Loading mapping data from {mapping_path}")
        with open(mapping_path) as f:
            mapping_data = json.load(f)
        mappings = mapping_data.get("matched", [])
        print(f"Found {len(mappings)} matched products")

    if asins:
        # Create minimal mappings for specific ASINs
        for asin in asins:
            # Check if already in mappings
            existing = next((m for m in mappings if m.get("amazon_asin") == asin), None)
            if not existing:
                mappings.append({
                    "amazon_asin": asin,
                    "plytix_product_id": None,  # Will skip Plytix update
                    "plytix_product_sku": asin
                })

    if not mappings:
        print("No products to sync. Provide --mapping or --asins.")
        return {"error": "No products to sync"}

    # Initialize syncer
    syncer = AplusContentSyncer(
        spapi_profile=spapi_profile,
        plytix_account=plytix_account
    )

    # Run sync
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Starting A+ Content sync...")
    print("=" * 60)

    summary = syncer.sync_all(mappings, dry_run)

    # Print summary
    print("\n" + "=" * 60)
    print("A+ CONTENT SYNC SUMMARY")
    print("=" * 60)
    print(f"Total products:      {summary['total_products']}")
    print(f"Products checked:    {summary['products_checked']}")
    print(f"With A+ Content:     {summary['with_aplus']}")
    print(f"Successfully synced: {summary['synced']}")
    print(f"Errors:              {summary['errors']}")
    print("=" * 60)

    # Add metadata
    summary["metadata"] = {
        "source_file": mapping_path,
        "sync_date": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run
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
        description="Sync A+ Content from Amazon to Plytix"
    )
    parser.add_argument(
        "--mapping", "-m",
        help="Path to mapping JSON file (from generate_asin_mapping.py)"
    )
    parser.add_argument(
        "--asins", "-a",
        help="Comma-separated list of specific ASINs to sync"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output path for sync report JSON"
    )
    parser.add_argument(
        "--spapi-profile",
        default="production",
        help="SP-API configuration profile"
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
        print("  --dry-run   Preview changes without updating")
        print("  --execute   Execute the sync operation")
        sys.exit(1)

    # Require at least one input source
    if not args.mapping and not args.asins:
        print("Error: Must provide --mapping or --asins", file=sys.stderr)
        sys.exit(1)

    # Parse ASINs if provided
    asins = None
    if args.asins:
        asins = [a.strip() for a in args.asins.split(",")]

    # Set default output path if not specified
    output_path = args.output
    if not output_path and args.execute and args.mapping:
        input_path = Path(args.mapping)
        output_path = str(input_path.parent / f"{input_path.stem}_aplus_sync.json")

    try:
        summary = sync_aplus_content(
            mapping_path=args.mapping,
            asins=asins,
            output_path=output_path,
            spapi_profile=args.spapi_profile,
            plytix_account=args.plytix_account,
            dry_run=args.dry_run
        )

        if summary.get("error"):
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
