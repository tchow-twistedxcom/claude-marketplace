#!/usr/bin/env python3
"""
Plytix Output Formatters

Token-efficient output formatting for Plytix API responses.
Supports multiple output formats: table, json, compact, summary.
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


class OutputFormat:
    """Output format constants."""
    TABLE = 'table'
    JSON = 'json'
    COMPACT = 'compact'
    SUMMARY = 'summary'


def truncate(text: str, max_length: int = 50, suffix: str = '...') -> str:
    """Truncate text to max length with suffix."""
    if not text:
        return ''
    text = str(text)
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_timestamp(ts: Optional[str]) -> str:
    """Format ISO timestamp to readable format."""
    if not ts:
        return '-'
    try:
        # Handle various ISO formats
        if 'T' in ts:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        return ts[:10]  # Just date portion
    except (ValueError, TypeError):
        return str(ts)[:16]


def format_size(size_bytes: Optional[int]) -> str:
    """Format byte size to human readable."""
    if size_bytes is None:
        return '-'
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


def safe_get(obj: Dict, *keys, default: Any = '-') -> Any:
    """Safely get nested dictionary value."""
    for key in keys:
        if isinstance(obj, dict):
            obj = obj.get(key, default)
        else:
            return default
    return obj if obj is not None else default


# =============================================================================
# TABLE FORMATTING
# =============================================================================

def print_table(headers: List[str], rows: List[List[str]], max_widths: Optional[List[int]] = None):
    """Print formatted ASCII table."""
    if not rows:
        print("No results found.")
        return

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    # Apply max widths if specified
    if max_widths:
        widths = [min(w, m) if m else w for w, m in zip(widths, max_widths + [None] * len(widths))]

    # Print header
    header_line = ' | '.join(h.ljust(widths[i]) for i, h in enumerate(headers))
    separator = '-+-'.join('-' * w for w in widths)

    print(header_line)
    print(separator)

    # Print rows
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            cell_str = str(cell) if cell is not None else '-'
            if i < len(widths):
                cell_str = truncate(cell_str, widths[i])
                cells.append(cell_str.ljust(widths[i]))
            else:
                cells.append(cell_str)
        print(' | '.join(cells))


def print_key_value(data: Dict[str, Any], indent: int = 0):
    """Print key-value pairs with formatting."""
    prefix = '  ' * indent
    for key, value in data.items():
        if isinstance(value, dict):
            print(f"{prefix}{key}:")
            print_key_value(value, indent + 1)
        elif isinstance(value, list):
            print(f"{prefix}{key}: [{len(value)} items]")
            if value and len(value) <= 5:
                for item in value:
                    if isinstance(item, dict):
                        print(f"{prefix}  - {safe_get(item, 'id', default=str(item)[:50])}")
                    else:
                        print(f"{prefix}  - {truncate(str(item), 60)}")
        else:
            print(f"{prefix}{key}: {value}")


# =============================================================================
# PRODUCT FORMATTERS
# =============================================================================

def format_product_row(product: Dict) -> List[str]:
    """Format single product for table row."""
    return [
        safe_get(product, 'id'),
        truncate(safe_get(product, 'sku'), 20),
        truncate(safe_get(product, 'label'), 40),
        safe_get(product, 'status', default='active'),
        format_timestamp(safe_get(product, 'modified')),
    ]


def format_products_table(products: List[Dict]):
    """Format products list as table."""
    headers = ['ID', 'SKU', 'Label', 'Status', 'Modified']
    rows = [format_product_row(p) for p in products]
    print_table(headers, rows, max_widths=[36, 20, 40, 10, 16])


def format_product_detail(product: Dict):
    """Format single product with full details."""
    print(f"\n{'='*60}")
    print(f"Product: {safe_get(product, 'label')}")
    print(f"{'='*60}")

    # Core fields
    core = {
        'ID': safe_get(product, 'id'),
        'SKU': safe_get(product, 'sku'),
        'Label': safe_get(product, 'label'),
        'Status': safe_get(product, 'status'),
        'Created': format_timestamp(safe_get(product, 'created')),
        'Modified': format_timestamp(safe_get(product, 'modified')),
    }
    print_key_value(core)

    # Attributes
    attributes = product.get('attributes', {})
    if attributes:
        print(f"\nAttributes ({len(attributes)}):")
        for key, value in list(attributes.items())[:10]:
            print(f"  {key}: {truncate(str(value), 50)}")
        if len(attributes) > 10:
            print(f"  ... and {len(attributes) - 10} more")

    # Categories
    categories = product.get('categories', [])
    if categories:
        print(f"\nCategories ({len(categories)}):")
        for cat in categories[:5]:
            print(f"  - {safe_get(cat, 'label', default=cat)}")

    # Assets
    assets = product.get('assets', [])
    if assets:
        print(f"\nAssets ({len(assets)}):")
        for asset in assets[:5]:
            print(f"  - {safe_get(asset, 'filename', default=safe_get(asset, 'id'))}")


def format_products_summary(products: List[Dict], total: Optional[int] = None):
    """Format products summary."""
    count = len(products)
    total = total or count

    statuses = {}
    for p in products:
        status = safe_get(p, 'status', default='unknown')
        statuses[status] = statuses.get(status, 0) + 1

    print(f"\nProducts Summary: {count} of {total}")
    print("-" * 30)
    for status, cnt in sorted(statuses.items()):
        print(f"  {status}: {cnt}")


# =============================================================================
# ASSET FORMATTERS
# =============================================================================

def format_asset_row(asset: Dict) -> List[str]:
    """Format single asset for table row."""
    return [
        safe_get(asset, 'id'),
        truncate(safe_get(asset, 'filename'), 30),
        safe_get(asset, 'file_type', default='-'),
        format_size(safe_get(asset, 'file_size', default=None)),
        format_timestamp(safe_get(asset, 'modified')),
    ]


def format_assets_table(assets: List[Dict]):
    """Format assets list as table."""
    headers = ['ID', 'Filename', 'Type', 'Size', 'Modified']
    rows = [format_asset_row(a) for a in assets]
    print_table(headers, rows, max_widths=[36, 30, 10, 10, 16])


def format_asset_detail(asset: Dict):
    """Format single asset with full details."""
    print(f"\n{'='*60}")
    print(f"Asset: {safe_get(asset, 'filename')}")
    print(f"{'='*60}")

    core = {
        'ID': safe_get(asset, 'id'),
        'Filename': safe_get(asset, 'filename'),
        'File Type': safe_get(asset, 'file_type'),
        'File Size': format_size(safe_get(asset, 'file_size', default=None)),
        'URL': truncate(safe_get(asset, 'url'), 60),
        'Created': format_timestamp(safe_get(asset, 'created')),
        'Modified': format_timestamp(safe_get(asset, 'modified')),
    }
    print_key_value(core)

    # Metadata
    metadata = asset.get('metadata', {})
    if metadata:
        print(f"\nMetadata:")
        print_key_value(metadata, indent=1)


# =============================================================================
# CATEGORY FORMATTERS
# =============================================================================

def format_category_row(category: Dict) -> List[str]:
    """Format single category for table row."""
    # Plytix uses 'name' for categories, with 'path' showing hierarchy
    name = safe_get(category, 'name') or safe_get(category, 'label')
    return [
        safe_get(category, 'id'),
        truncate(name, 40),
        str(safe_get(category, 'n_children', default=0)),
        safe_get(category, 'path', default='-'),
        format_timestamp(safe_get(category, 'modified')),
    ]


def format_categories_table(categories: List[Dict]):
    """Format categories list as table."""
    headers = ['ID', 'Name', 'Children', 'Path', 'Modified']
    rows = [format_category_row(c) for c in categories]
    print_table(headers, rows, max_widths=[36, 40, 8, 30, 16])


def format_category_tree(categories: List[Dict], indent: int = 0, is_last: bool = False):
    """Format categories as tree structure built from flat list with parents_ids."""
    for i, cat in enumerate(categories):
        is_last_item = (i == len(categories) - 1)
        prefix = '│   ' * indent
        connector = '└── ' if is_last_item else '├── '

        name = safe_get(cat, 'name') or safe_get(cat, 'label')
        children = cat.get('children', [])
        child_count = len(children) if children else safe_get(cat, 'n_children', default=0)

        print(f"{prefix}{connector}{name} ({child_count} children)")

        if children:
            format_category_tree(children, indent + 1, is_last_item)


def format_category_detail(category: Dict):
    """Format single category with full details."""
    name = safe_get(category, 'name') or safe_get(category, 'label')
    print(f"\n{'='*60}")
    print(f"Category: {name}")
    print(f"{'='*60}")

    core = {
        'ID': safe_get(category, 'id'),
        'Name': name,
        'Slug': safe_get(category, 'slug'),
        'Path': safe_get(category, 'path'),
        'Parents': safe_get(category, 'parents_ids'),
        'Children': safe_get(category, 'n_children'),
        'Order': safe_get(category, 'order'),
        'Modified': format_timestamp(safe_get(category, 'modified')),
    }
    print_key_value(core)


# =============================================================================
# VARIANT FORMATTERS
# =============================================================================

def format_variant_row(variant: Dict) -> List[str]:
    """Format single variant for table row."""
    return [
        safe_get(variant, 'id'),
        truncate(safe_get(variant, 'sku'), 20),
        truncate(safe_get(variant, 'label'), 35),
        safe_get(variant, 'product_id', default='-')[:12] + '...',
        format_timestamp(safe_get(variant, 'modified')),
    ]


def format_variants_table(variants: List[Dict]):
    """Format variants list as table."""
    headers = ['ID', 'SKU', 'Label', 'Product', 'Modified']
    rows = [format_variant_row(v) for v in variants]
    print_table(headers, rows, max_widths=[36, 20, 35, 15, 16])


def format_variant_detail(variant: Dict):
    """Format single variant with full details."""
    print(f"\n{'='*60}")
    print(f"Variant: {safe_get(variant, 'label')}")
    print(f"{'='*60}")

    core = {
        'ID': safe_get(variant, 'id'),
        'SKU': safe_get(variant, 'sku'),
        'Label': safe_get(variant, 'label'),
        'Product ID': safe_get(variant, 'product_id'),
        'Created': format_timestamp(safe_get(variant, 'created')),
        'Modified': format_timestamp(safe_get(variant, 'modified')),
    }
    print_key_value(core)

    # Attributes
    attributes = variant.get('attributes', {})
    if attributes:
        print(f"\nAttributes ({len(attributes)}):")
        for key, value in list(attributes.items())[:10]:
            print(f"  {key}: {truncate(str(value), 50)}")


# =============================================================================
# ATTRIBUTE FORMATTERS
# =============================================================================

def format_attribute_row(attr: Dict) -> List[str]:
    """Format single attribute for table row."""
    # Search endpoint returns only id and filter_type, get endpoint returns full details
    label = safe_get(attr, 'label', default=None) or safe_get(attr, 'name', default=None) or '-'
    attr_type = safe_get(attr, 'type_class', default=None) or safe_get(attr, 'filter_type', default=None) or '-'
    # Clean up filter_type format (e.g., "TextAttribute" -> "Text")
    if isinstance(attr_type, str) and attr_type.endswith('Attribute'):
        attr_type = attr_type[:-9]
    return [
        safe_get(attr, 'id'),
        truncate(label, 30),
        attr_type,
        'Yes' if safe_get(attr, 'mandatory') else 'No',
        safe_get(attr, 'group', default='-'),
    ]


def format_attributes_table(attributes: List[Dict]):
    """Format attributes list as table."""
    headers = ['ID', 'Label', 'Type', 'Required', 'Group']
    rows = [format_attribute_row(a) for a in attributes]
    print_table(headers, rows, max_widths=[36, 30, 15, 8, 20])


def format_attribute_detail(attr: Dict):
    """Format single attribute with full details."""
    print(f"\n{'='*60}")
    print(f"Attribute: {safe_get(attr, 'label')}")
    print(f"{'='*60}")

    core = {
        'ID': safe_get(attr, 'id'),
        'Label': safe_get(attr, 'label'),
        'Type': safe_get(attr, 'type_class'),
        'Mandatory': safe_get(attr, 'mandatory'),
        'Group': safe_get(attr, 'group'),
        'Description': safe_get(attr, 'description'),
    }
    print_key_value(core)

    # Options for select types
    options = attr.get('options', [])
    if options:
        print(f"\nOptions ({len(options)}):")
        for opt in options[:10]:
            print(f"  - {opt}")
        if len(options) > 10:
            print(f"  ... and {len(options) - 10} more")


def format_attribute_groups_table(groups: List[Dict]):
    """Format attribute groups list as table."""
    headers = ['ID', 'Label', 'Attributes']
    rows = [
        [
            safe_get(g, 'id'),
            truncate(safe_get(g, 'label'), 40),
            str(safe_get(g, 'attributes_count', default=0)),
        ]
        for g in groups
    ]
    print_table(headers, rows, max_widths=[36, 40, 12])


# =============================================================================
# GENERIC FORMATTERS
# =============================================================================

def format_json(data: Any, indent: int = 2):
    """Format data as JSON."""
    print(json.dumps(data, indent=indent, default=str))


def format_compact(data: Union[Dict, List]):
    """Format data in compact single-line format."""
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                # Show key fields only
                parts = []
                for key in ['id', 'sku', 'label', 'filename', 'name']:
                    if key in item:
                        parts.append(f"{key}={item[key]}")
                print(' | '.join(parts) if parts else str(item)[:80])
            else:
                print(str(item)[:80])
    elif isinstance(data, dict):
        parts = [f"{k}={v}" for k, v in list(data.items())[:5]]
        print(' | '.join(parts))


def format_error(error: str, details: Optional[Dict] = None):
    """Format error message."""
    print(f"\n❌ Error: {error}", file=sys.stderr)
    if details:
        for key, value in details.items():
            print(f"   {key}: {value}", file=sys.stderr)


def format_success(message: str, details: Optional[Dict] = None):
    """Format success message."""
    print(f"\n✅ {message}")
    if details:
        for key, value in details.items():
            print(f"   {key}: {value}")


def format_warning(message: str):
    """Format warning message."""
    print(f"\n⚠️  {message}", file=sys.stderr)


# =============================================================================
# DISPATCHER
# =============================================================================

def format_output(
    data: Any,
    entity_type: str,
    output_format: str = OutputFormat.TABLE,
    detail: bool = False,
    total: Optional[int] = None
):
    """
    Main output formatter dispatcher.

    Args:
        data: Data to format (dict or list)
        entity_type: Type of entity (products, assets, categories, variants, attributes)
        output_format: Output format (table, json, compact, summary)
        detail: Show detailed view for single items
        total: Total count for pagination info
    """
    if output_format == OutputFormat.JSON:
        format_json(data)
        return

    if output_format == OutputFormat.COMPACT:
        format_compact(data)
        return

    if isinstance(data, list):
        if output_format == OutputFormat.SUMMARY:
            # Summary view
            if entity_type == 'products':
                format_products_summary(data, total)
            else:
                print(f"\n{entity_type.title()}: {len(data)} items")
            return

        # Table view
        formatters = {
            'products': format_products_table,
            'assets': format_assets_table,
            'categories': format_categories_table,
            'variants': format_variants_table,
            'attributes': format_attributes_table,
            'attribute_groups': format_attribute_groups_table,
        }
        formatter = formatters.get(entity_type)
        if formatter:
            formatter(data)
            if total and total > len(data):
                print(f"\nShowing {len(data)} of {total} total")
        else:
            format_json(data)

    elif isinstance(data, dict):
        if detail:
            # Detail view
            detail_formatters = {
                'products': format_product_detail,
                'assets': format_asset_detail,
                'categories': format_category_detail,
                'variants': format_variant_detail,
                'attributes': format_attribute_detail,
            }
            formatter = detail_formatters.get(entity_type)
            if formatter:
                formatter(data)
            else:
                print_key_value(data)
        else:
            print_key_value(data)

    else:
        print(data)


if __name__ == '__main__':
    # Test formatters
    test_products = [
        {'id': 'prod-001', 'sku': 'SKU-001', 'label': 'Test Product', 'status': 'active', 'modified': '2024-01-15T10:30:00Z'},
        {'id': 'prod-002', 'sku': 'SKU-002', 'label': 'Another Product with Long Name', 'status': 'draft', 'modified': '2024-01-14T08:00:00Z'},
    ]

    print("Table format:")
    format_output(test_products, 'products', OutputFormat.TABLE)

    print("\n\nCompact format:")
    format_output(test_products, 'products', OutputFormat.COMPACT)

    print("\n\nJSON format:")
    format_output(test_products, 'products', OutputFormat.JSON)
