#!/usr/bin/env python3
"""
Plytix Amazon Integration Schema Setup

Creates the Amazon-specific attributes in Plytix for storing
Amazon catalog data as an overlay on existing variants.

Usage:
    python setup_plytix_amazon_schema.py --list              # List existing attributes
    python setup_plytix_amazon_schema.py --dry-run           # Preview changes
    python setup_plytix_amazon_schema.py --create            # Create attributes
    python setup_plytix_amazon_schema.py --group-id <uuid>   # Specify attribute group
"""

import argparse
import json
import sys
from pathlib import Path

# Add plytix scripts to path
PLYTIX_SCRIPTS = Path(__file__).parent.parent.parent / 'plytix-skills' / 'skills' / 'plytix-api' / 'scripts'
sys.path.insert(0, str(PLYTIX_SCRIPTS))

from plytix_api import PlytixAPI, PlytixAPIError


# =============================================================================
# ATTRIBUTE SCHEMA DEFINITION
# =============================================================================

# Plytix API field mapping:
#   name: Display name shown in UI (human readable)
#   label: Internal identifier/slug (auto-generated if not provided)
#   type_class: TextAttribute, DropdownAttribute, BooleanAttribute, HtmlAttribute, DateAttribute

# Type class mapping from simple names
TYPE_CLASS_MAP = {
    "text": "TextAttribute",
    "dropdown": "DropdownAttribute",
    "boolean": "BooleanAttribute",
    "html": "HtmlAttribute",
    "date": "DateAttribute",
    "number": "NumberAttribute",
}

# Attributes for VARIANTS (Amazon data lives on variants, not parent products)
VARIANT_ATTRIBUTES = [
    # Amazon Identifiers (ALWAYS WRITE)
    {
        "name": "Amazon ASIN",
        "label": "amazon_asin",
        "type_class": "text",
        "description": "Amazon Standard Identification Number for this variant"
    },
    {
        "name": "Amazon Parent ASIN",
        "label": "amazon_parent_asin",
        "type_class": "text",
        "description": "Current parent ASIN on Amazon (may be incorrect)"
    },
    {
        "name": "Amazon Desired Parent",
        "label": "amazon_desired_parent",
        "type_class": "text",
        "description": "Override: What parent ASIN this should be under on Amazon"
    },
    {
        "name": "Amazon SKU",
        "label": "amazon_sku",
        "type_class": "text",
        "description": "Seller SKU for SP-API operations"
    },

    # Imported Values (preserve Amazon's data for comparison)
    {
        "name": "Amazon UPC (Imported)",
        "label": "amazon_upc_imported",
        "type_class": "text",
        "description": "UPC value from Amazon catalog (for comparison with Plytix UPC)"
    },
    {
        "name": "Amazon EAN (Imported)",
        "label": "amazon_ean_imported",
        "type_class": "text",
        "description": "EAN value from Amazon catalog (for comparison with Plytix EAN)"
    },
    {
        "name": "Amazon Title (Imported)",
        "label": "amazon_title_imported",
        "type_class": "text",
        "description": "Product title from Amazon catalog"
    },

    # Status & Conflict Tracking
    {
        "name": "Amazon Sync Status",
        "label": "amazon_sync_status",
        "type_class": "dropdown",
        "description": "Current synchronization state with Amazon",
        "options": ["synced", "pending", "needs_fix", "conflict", "error"]
    },
    {
        "name": "Amazon Sync Conflict",
        "label": "amazon_sync_conflict",
        "type_class": "boolean",
        "description": "Flag indicating data conflict requiring review"
    },
    {
        "name": "Amazon Sync Notes",
        "label": "amazon_sync_notes",
        "type_class": "html",
        "description": "Conflict details and audit log"
    },
    {
        "name": "Amazon Listing Status",
        "label": "amazon_listing_status",
        "type_class": "dropdown",
        "description": "Amazon listing status",
        "options": ["active", "inactive", "suppressed", "unknown"]
    },
    {
        "name": "Amazon Last Synced",
        "label": "amazon_last_synced",
        "type_class": "date",
        "description": "Timestamp of last sync with Amazon"
    },

    # Amazon Variation Data
    {
        "name": "Amazon Size",
        "label": "amazon_size",
        "type_class": "text",
        "description": "Size value on Amazon"
    },
    {
        "name": "Amazon Color",
        "label": "amazon_color",
        "type_class": "text",
        "description": "Color value on Amazon"
    },
    {
        "name": "Amazon Variation Theme",
        "label": "amazon_variation_theme",
        "type_class": "text",
        "description": "Variation theme (SIZE_COLOR, SIZE_NAME, etc.)"
    },
]

# Attributes for PARENT PRODUCTS (optional metadata)
PRODUCT_ATTRIBUTES = [
    {
        "name": "Amazon Product Type",
        "label": "amazon_product_type",
        "type_class": "text",
        "description": "Amazon product type (SHOES, BOOT, etc.)"
    },
    {
        "name": "Amazon Brand Registered",
        "label": "amazon_brand_registered",
        "type_class": "boolean",
        "description": "Whether product is Brand Registry enrolled"
    },
    # Note: amazon_long_description likely already exists
    # Content attributes (amazon_feature_1-5, amazon_search_terms) added separately if needed
]

# Content attributes (NEVER overwrite - Plytix owns content)
CONTENT_ATTRIBUTES = [
    {
        "name": "Amazon Feature 1",
        "label": "amazon_feature_1",
        "type_class": "text",
        "description": "Bullet point 1 for Amazon listing"
    },
    {
        "name": "Amazon Feature 2",
        "label": "amazon_feature_2",
        "type_class": "text",
        "description": "Bullet point 2 for Amazon listing"
    },
    {
        "name": "Amazon Feature 3",
        "label": "amazon_feature_3",
        "type_class": "text",
        "description": "Bullet point 3 for Amazon listing"
    },
    {
        "name": "Amazon Feature 4",
        "label": "amazon_feature_4",
        "type_class": "text",
        "description": "Bullet point 4 for Amazon listing"
    },
    {
        "name": "Amazon Feature 5",
        "label": "amazon_feature_5",
        "type_class": "text",
        "description": "Bullet point 5 for Amazon listing"
    },
    {
        "name": "Amazon Search Terms",
        "label": "amazon_search_terms",
        "type_class": "html",
        "description": "Generic keywords for Amazon search"
    },
]


# =============================================================================
# SCHEMA MANAGER
# =============================================================================

class PlytixSchemaManager:
    """Manages Plytix attribute schema for Amazon integration."""

    def __init__(self, account: str = None):
        self.api = PlytixAPI(account=account)
        self._existing_attributes = None

    def get_existing_attributes(self, force_refresh: bool = False) -> dict:
        """
        Get all existing attributes, indexed by name/label.

        Returns:
            Dict mapping attribute names to attribute objects
        """
        if self._existing_attributes is not None and not force_refresh:
            return self._existing_attributes

        attributes = {}
        page = 1
        while True:
            result = self.api.list_attributes(limit=100, page=page)
            batch = result.get('data', [])
            if not batch:
                break
            for attr in batch:
                # Index by both label and name (if available)
                label = attr.get('label', '').lower()
                name = attr.get('name', attr.get('id', '')).lower()
                if label:
                    attributes[label] = attr
                if name and name != label:
                    attributes[name] = attr
            if len(batch) < 100:
                break
            page += 1

        self._existing_attributes = attributes
        return attributes

    def attribute_exists(self, attr_def: dict) -> dict:
        """
        Check if an attribute already exists.

        Args:
            attr_def: Attribute definition with 'label' and/or 'name'

        Returns:
            Existing attribute dict if found, None otherwise
        """
        existing = self.get_existing_attributes()

        # Check by name first (more reliable)
        name = attr_def.get('name', '').lower()
        if name and name in existing:
            return existing[name]

        # Check by label
        label = attr_def.get('label', '').lower()
        if label and label in existing:
            return existing[label]

        return None

    def create_attribute(self, attr_def: dict, group_id: str = None, dry_run: bool = False) -> dict:
        """
        Create an attribute in Plytix.

        Args:
            attr_def: Attribute definition with:
                - name: Display name (human readable)
                - label: Internal identifier (slug)
                - type_class: Simple type name (text, dropdown, boolean, html)
                - description: Optional description
                - options: Required for dropdown type
            group_id: Optional attribute group UUID
            dry_run: If True, don't actually create

        Returns:
            Created attribute or dry-run preview
        """
        # Convert simple type_class to Plytix full type name
        simple_type = attr_def["type_class"]
        plytix_type = TYPE_CLASS_MAP.get(simple_type, simple_type)

        # Build creation payload (Plytix format)
        payload = {
            "name": attr_def["name"],      # Display name
            "label": attr_def["label"],    # Internal identifier
            "type_class": plytix_type,     # Full type name (TextAttribute, etc.)
        }

        # Add optional fields
        if attr_def.get("description"):
            payload["description"] = attr_def["description"]
        if attr_def.get("options"):
            payload["options"] = attr_def["options"]
        if attr_def.get("mandatory"):
            payload["mandatory"] = attr_def["mandatory"]
        if group_id:
            payload["groups"] = [group_id]

        if dry_run:
            return {"dry_run": True, "payload": payload}

        result = self.api.create_attribute(payload)

        # Invalidate cache
        self._existing_attributes = None

        return result

    def setup_schema(
        self,
        group_id: str = None,
        dry_run: bool = False,
        include_content: bool = False,
        include_product: bool = False
    ) -> dict:
        """
        Set up the complete Amazon integration schema.

        Args:
            group_id: Optional attribute group UUID for organization
            dry_run: Preview changes without creating
            include_content: Include content attributes (amazon_feature_*)
            include_product: Include product-level attributes

        Returns:
            Summary of created/skipped attributes
        """
        results = {
            "created": [],
            "skipped": [],
            "errors": []
        }

        # Collect all attributes to process
        all_attributes = list(VARIANT_ATTRIBUTES)
        if include_product:
            all_attributes.extend(PRODUCT_ATTRIBUTES)
        if include_content:
            all_attributes.extend(CONTENT_ATTRIBUTES)

        for attr_def in all_attributes:
            name = attr_def.get('name', attr_def['label'])

            # Check if exists
            existing = self.attribute_exists(attr_def)
            if existing:
                results["skipped"].append({
                    "name": name,
                    "label": attr_def["label"],
                    "reason": "already exists",
                    "existing_id": existing.get("id")
                })
                continue

            # Create attribute
            try:
                result = self.create_attribute(attr_def, group_id, dry_run)
                results["created"].append({
                    "name": name,
                    "label": attr_def["label"],
                    "type": attr_def["type_class"],
                    "dry_run": dry_run,
                    "result": result
                })
            except PlytixAPIError as e:
                results["errors"].append({
                    "name": name,
                    "label": attr_def["label"],
                    "error": str(e)
                })

        return results


# =============================================================================
# CLI
# =============================================================================

def print_results(results: dict, verbose: bool = False):
    """Print schema setup results."""
    print("\n" + "=" * 60)
    print("PLYTIX AMAZON SCHEMA SETUP RESULTS")
    print("=" * 60)

    if results["created"]:
        print(f"\n✅ CREATED ({len(results['created'])} attributes):")
        for item in results["created"]:
            dry_run_tag = " [DRY RUN]" if item.get("dry_run") else ""
            print(f"   • {item['label']} ({item['type']}){dry_run_tag}")

    if results["skipped"]:
        print(f"\n⏭️  SKIPPED ({len(results['skipped'])} attributes - already exist):")
        for item in results["skipped"]:
            print(f"   • {item['label']}")

    if results["errors"]:
        print(f"\n❌ ERRORS ({len(results['errors'])} attributes):")
        for item in results["errors"]:
            print(f"   • {item['label']}: {item['error']}")

    print("\n" + "=" * 60)
    print(f"Summary: {len(results['created'])} created, "
          f"{len(results['skipped'])} skipped, "
          f"{len(results['errors'])} errors")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Set up Plytix attributes for Amazon integration"
    )
    parser.add_argument(
        "--account", "-a",
        help="Plytix account alias"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List existing Amazon-related attributes"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without creating attributes"
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="Create the Amazon attributes"
    )
    parser.add_argument(
        "--group-id",
        help="Attribute group UUID to assign attributes to"
    )
    parser.add_argument(
        "--include-content",
        action="store_true",
        help="Include content attributes (amazon_feature_1-5, amazon_search_terms)"
    )
    parser.add_argument(
        "--include-product",
        action="store_true",
        help="Include product-level attributes (amazon_product_type, etc.)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    try:
        manager = PlytixSchemaManager(account=args.account)

        if args.list:
            # List existing Amazon-related attributes
            existing = manager.get_existing_attributes()
            amazon_attrs = {k: v for k, v in existing.items()
                          if 'amazon' in k.lower()}

            if args.json:
                print(json.dumps(list(amazon_attrs.values()), indent=2, default=str))
            else:
                print(f"\nFound {len(amazon_attrs)} Amazon-related attributes:\n")
                for name, attr in sorted(amazon_attrs.items()):
                    attr_type = attr.get('type_class', 'unknown')
                    attr_id = attr.get('id', 'no-id')
                    print(f"  • {attr.get('label', name)} ({attr_type})")
                    print(f"    ID: {attr_id}")
            return

        if args.create or args.dry_run:
            # Set up schema
            results = manager.setup_schema(
                group_id=args.group_id,
                dry_run=args.dry_run,
                include_content=args.include_content,
                include_product=args.include_product
            )

            if args.json:
                print(json.dumps(results, indent=2, default=str))
            else:
                print_results(results, verbose=args.verbose)

            if results["errors"]:
                sys.exit(1)
            return

        # Default: show help
        parser.print_help()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
