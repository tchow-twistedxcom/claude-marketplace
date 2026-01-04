#!/usr/bin/env python3
"""
Fix Amazon Variation Relationships

Generates and submits JSON_LISTINGS_FEED to fix parent-child relationships
for Amazon listings based on Plytix product structure.

Usage:
    # Generate feed file only (for review)
    python fix_amazon_relationships.py --mapping mca0032_mapping.json --parent-asin B0F5BDG84W --generate

    # Submit feed to Amazon
    python fix_amazon_relationships.py --mapping mca0032_mapping.json --parent-asin B0F5BDG84W --submit

    # Update Plytix with desired parent
    python fix_amazon_relationships.py --mapping mca0032_mapping.json --parent-asin B0F5BDG84W --update-plytix
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient
from spapi_feeds import FeedsAPI, build_relationship_message

# Add plytix scripts to path
PLYTIX_SCRIPTS = Path(__file__).parent.parent.parent / 'plytix-skills' / 'skills' / 'plytix-api' / 'scripts'
sys.path.insert(0, str(PLYTIX_SCRIPTS))

from plytix_api import PlytixAPI, PlytixAPIError


class RelationshipFixer:
    """Fix Amazon variation relationships."""

    def __init__(self, spapi_profile: str = 'production', plytix_account: str = None):
        self.auth = SPAPIAuth(profile=spapi_profile)
        self.client = SPAPIClient(self.auth)
        self.feeds = FeedsAPI(self.client)
        self.seller_id = self.auth.get_selling_partner_id(spapi_profile)
        self.plytix = PlytixAPI(account=plytix_account) if plytix_account else PlytixAPI()

    def load_mapping(self, mapping_path: str) -> Dict:
        """Load the mapping file."""
        with open(mapping_path) as f:
            return json.load(f)

    def analyze_relationships(self, mapping: Dict, target_parent_asin: str) -> Dict:
        """
        Analyze relationship issues in the mapping.

        Args:
            mapping: Mapping data with matched products
            target_parent_asin: Desired parent ASIN

        Returns:
            Analysis results
        """
        matched = mapping.get('matched', [])

        analysis = {
            'target_parent': target_parent_asin,
            'total': len(matched),
            'orphaned': [],        # No current parent
            'wrong_parent': [],    # Has parent but wrong one
            'correct': [],         # Already on target parent
            'no_amazon_sku': []    # Missing amazon_sku
        }

        for entry in matched:
            asin = entry.get('amazon_asin')
            current_parent = entry.get('amazon_parent_asin')
            amazon_sku = entry.get('amazon_sku')
            sku = entry.get('plytix_product_sku')

            item = {
                'sku': sku,
                'amazon_sku': amazon_sku,
                'asin': asin,
                'current_parent': current_parent,
                'plytix_id': entry.get('plytix_product_id')
            }

            if not amazon_sku:
                analysis['no_amazon_sku'].append(item)
            elif current_parent == target_parent_asin:
                analysis['correct'].append(item)
            elif not current_parent:
                analysis['orphaned'].append(item)
            else:
                analysis['wrong_parent'].append(item)

        return analysis

    def generate_feed(
        self,
        analysis: Dict,
        parent_sku: str = None,
        parent_asin: str = None
    ) -> Dict:
        """
        Generate JSON_LISTINGS_FEED for relationship fix.

        Args:
            analysis: Analysis from analyze_relationships
            parent_sku: Parent SKU (preferred if available)
            parent_asin: Parent ASIN (fallback for Vendor Central parents)

        Returns:
            Feed content dict
        """
        messages = []
        message_id = 1

        # Fix orphaned variants
        for item in analysis['orphaned']:
            if item.get('amazon_sku'):
                msg = build_relationship_message(
                    message_id=message_id,
                    sku=item['amazon_sku'],
                    parent_sku=parent_sku,
                    parent_asin=parent_asin if not parent_sku else None
                )
                messages.append(msg)
                message_id += 1

        # Fix wrong parent variants
        for item in analysis['wrong_parent']:
            if item.get('amazon_sku'):
                msg = build_relationship_message(
                    message_id=message_id,
                    sku=item['amazon_sku'],
                    parent_sku=parent_sku,
                    parent_asin=parent_asin if not parent_sku else None
                )
                messages.append(msg)
                message_id += 1

        return {
            "header": {
                "sellerId": self.seller_id,
                "version": "2.0"
            },
            "messages": messages
        }

    def save_feed(self, feed: Dict, output_path: str):
        """Save feed to file for review."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, 'w') as f:
            json.dump(feed, f, indent=2)
        print(f"Feed saved to {output_path}")

    def submit_feed(self, feed: Dict, wait: bool = False) -> Dict:
        """
        Submit feed to Amazon.

        Args:
            feed: Feed content from generate_feed
            wait: Whether to wait for completion

        Returns:
            Submission result
        """
        messages = feed.get('messages', [])
        if not messages:
            return {'error': 'No messages to submit'}

        return self.feeds.submit_json_listings_feed(
            messages=messages,
            seller_id=self.seller_id,
            wait_for_completion=wait
        )

    def update_plytix_desired_parent(
        self,
        mapping: Dict,
        target_parent_asin: str,
        dry_run: bool = False
    ) -> Dict:
        """
        Update Plytix amazon_desired_parent field for all matched products.

        Args:
            mapping: Mapping data
            target_parent_asin: Desired parent ASIN to set
            dry_run: Preview without saving

        Returns:
            Update results
        """
        matched = mapping.get('matched', [])
        results = {
            'updated': [],
            'skipped': [],
            'errors': []
        }

        for entry in matched:
            product_id = entry.get('plytix_product_id')
            sku = entry.get('plytix_product_sku')

            if not product_id:
                results['skipped'].append({'sku': sku, 'reason': 'no product_id'})
                continue

            print(f"  Updating {sku}...", end=' ')

            if dry_run:
                print("DRY RUN")
                results['updated'].append({
                    'product_id': product_id,
                    'sku': sku,
                    'amazon_desired_parent': target_parent_asin,
                    'dry_run': True
                })
                continue

            try:
                self.plytix.update_product(product_id, {
                    'attributes': {
                        'amazon_desired_parent': target_parent_asin
                    }
                })
                print("OK")
                results['updated'].append({
                    'product_id': product_id,
                    'sku': sku,
                    'amazon_desired_parent': target_parent_asin
                })
            except PlytixAPIError as e:
                print(f"ERROR: {e}")
                results['errors'].append({
                    'product_id': product_id,
                    'sku': sku,
                    'error': str(e)
                })

        return results


def print_analysis(analysis: Dict):
    """Print analysis results."""
    print("\n" + "=" * 60)
    print("RELATIONSHIP ANALYSIS")
    print("=" * 60)
    print(f"Target Parent ASIN: {analysis['target_parent']}")
    print(f"Total Products:     {analysis['total']}")
    print(f"Orphaned (no parent): {len(analysis['orphaned'])}")
    print(f"Wrong Parent:         {len(analysis['wrong_parent'])}")
    print(f"Already Correct:      {len(analysis['correct'])}")
    print(f"Missing Amazon SKU:   {len(analysis['no_amazon_sku'])}")
    print("=" * 60)

    if analysis['orphaned']:
        print("\nOrphaned ASINs (need to add to parent):")
        for item in analysis['orphaned'][:10]:
            print(f"  {item['sku']} ({item['asin']})")
        if len(analysis['orphaned']) > 10:
            print(f"  ... and {len(analysis['orphaned']) - 10} more")

    if analysis['wrong_parent']:
        print("\nWrong Parent ASINs (need to re-parent):")
        for item in analysis['wrong_parent'][:10]:
            print(f"  {item['sku']} ({item['asin']}) - current: {item['current_parent']}")
        if len(analysis['wrong_parent']) > 10:
            print(f"  ... and {len(analysis['wrong_parent']) - 10} more")

    if analysis['no_amazon_sku']:
        print("\nMissing Amazon SKU (cannot fix via feed):")
        for item in analysis['no_amazon_sku']:
            print(f"  {item['sku']} ({item['asin']})")


def main():
    parser = argparse.ArgumentParser(
        description="Fix Amazon variation relationships"
    )
    parser.add_argument(
        "--mapping", "-m",
        required=True,
        help="Path to mapping JSON file"
    )
    parser.add_argument(
        "--parent-asin",
        required=True,
        help="Target parent ASIN to link variants to"
    )
    parser.add_argument(
        "--parent-sku",
        help="Parent SKU (if seller has one - preferred over ASIN)"
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze and print relationship issues"
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate feed file (does not submit)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output path for generated feed (default: data/<style>_relationship_fix.json)"
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Submit feed to Amazon"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for feed to complete processing (with --submit)"
    )
    parser.add_argument(
        "--update-plytix",
        action="store_true",
        help="Update Plytix amazon_desired_parent field"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without saving (for --update-plytix)"
    )
    parser.add_argument(
        "--spapi-profile",
        default="production",
        help="SP-API config profile"
    )
    parser.add_argument(
        "--plytix-account",
        help="Plytix account alias"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    # Validate arguments
    if not any([args.analyze, args.generate, args.submit, args.update_plytix]):
        print("Error: Must specify at least one action: --analyze, --generate, --submit, or --update-plytix")
        sys.exit(1)

    try:
        fixer = RelationshipFixer(
            spapi_profile=args.spapi_profile,
            plytix_account=args.plytix_account
        )

        # Load mapping
        print(f"Loading mapping from {args.mapping}")
        mapping = fixer.load_mapping(args.mapping)

        # Analyze relationships
        analysis = fixer.analyze_relationships(mapping, args.parent_asin)

        if args.analyze:
            print_analysis(analysis)
            if args.json:
                print("\n" + json.dumps(analysis, indent=2))

        if args.generate or args.submit:
            # Generate feed
            feed = fixer.generate_feed(
                analysis,
                parent_sku=args.parent_sku,
                parent_asin=args.parent_asin
            )

            print(f"\nGenerated feed with {len(feed['messages'])} messages")

            if args.generate:
                # Save to file
                output_path = args.output
                if not output_path:
                    # Derive from mapping filename
                    mapping_name = Path(args.mapping).stem
                    output_path = f"data/{mapping_name}_relationship_fix.json"
                fixer.save_feed(feed, output_path)

            if args.submit:
                print("\nSubmitting feed to Amazon...")
                result = fixer.submit_feed(feed, wait=args.wait)
                print(f"Feed ID: {result.get('feedId')}")
                if result.get('processingStatus'):
                    print(f"Status: {result['processingStatus']}")
                if args.json:
                    print(json.dumps(result, indent=2))

        if args.update_plytix:
            print("\nUpdating Plytix amazon_desired_parent...")
            results = fixer.update_plytix_desired_parent(
                mapping,
                args.parent_asin,
                dry_run=args.dry_run
            )
            mode = "[DRY RUN] " if args.dry_run else ""
            print(f"\n{mode}Updated: {len(results['updated'])}")
            print(f"{mode}Skipped: {len(results['skipped'])}")
            print(f"{mode}Errors:  {len(results['errors'])}")
            if args.json:
                print(json.dumps(results, indent=2))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
