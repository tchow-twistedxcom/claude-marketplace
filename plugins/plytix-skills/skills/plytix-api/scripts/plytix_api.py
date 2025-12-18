#!/usr/bin/env python3
"""
Plytix PIM API CLI

Comprehensive CLI for Plytix Product Information Management system.
Supports Products, Assets, Categories, Variants, and Attributes.

Usage:
    python plytix_api.py <domain> <command> [options]

Examples:
    python plytix_api.py products list --limit 50
    python plytix_api.py products get <product_id>
    python plytix_api.py assets upload /path/to/image.jpg
    python plytix_api.py categories tree
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
import time

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from auth import PlytixAuth, PlytixAuthError
from formatters import (
    format_output, format_error, format_success, format_warning,
    OutputFormat
)


# =============================================================================
# API CLIENT
# =============================================================================

class PlytixAPIError(Exception):
    """API error with status code and details."""
    def __init__(self, message: str, status_code: int = None, details: Dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class PlytixAPI:
    """
    Plytix PIM API client.

    Provides methods for all API operations across domains:
    - Products
    - Assets
    - Categories
    - Variants
    - Attributes
    """

    def __init__(self, account: str = None):
        """
        Initialize API client.

        Args:
            account: Account alias (prod, staging, etc.) or None for default
        """
        self.auth = PlytixAuth()
        self.account = account
        self._base_url = self.auth.get_api_url(account)

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Dict = None,
        params: Dict = None,
        timeout: int = 30
    ) -> Dict:
        """
        Make authenticated API request.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint (e.g., /products)
            data: Request body data
            params: Query parameters
            timeout: Request timeout in seconds

        Returns:
            Response data as dict

        Raises:
            PlytixAPIError: On API errors
        """
        url = f"{self._base_url}{endpoint}"

        if params:
            # Filter out None values
            params = {k: v for k, v in params.items() if v is not None}
            if params:
                url = f"{url}?{urlencode(params)}"

        headers = self.auth.get_headers(self.account)

        body = None
        if data is not None:
            body = json.dumps(data).encode('utf-8')

        req = Request(url, data=body, headers=headers, method=method)

        try:
            with urlopen(req, timeout=timeout) as response:
                content = response.read().decode('utf-8')
                if content:
                    return json.loads(content)
                return {}
        except HTTPError as e:
            error_body = e.read().decode('utf-8')
            try:
                error_json = json.loads(error_body)
                error_msg = error_json.get('message', error_json.get('error', str(e)))
                details = error_json
            except (json.JSONDecodeError, KeyError, TypeError):
                error_msg = error_body[:500] if error_body else str(e)
                details = {'raw': error_body}

            # Handle rate limiting
            if e.code == 429:
                retry_after = e.headers.get('Retry-After', '60')
                raise PlytixAPIError(
                    f"Rate limited. Retry after {retry_after}s",
                    status_code=429,
                    details={'retry_after': retry_after}
                )

            raise PlytixAPIError(error_msg, status_code=e.code, details=details)
        except URLError as e:
            raise PlytixAPIError(f"Network error: {e}")

    def get(self, endpoint: str, params: Dict = None) -> Dict:
        """GET request."""
        return self._request('GET', endpoint, params=params)

    def post(self, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """POST request."""
        return self._request('POST', endpoint, data=data, params=params)

    def patch(self, endpoint: str, data: Dict = None) -> Dict:
        """PATCH request."""
        return self._request('PATCH', endpoint, data=data)

    def delete(self, endpoint: str) -> Dict:
        """DELETE request."""
        return self._request('DELETE', endpoint)

    # =========================================================================
    # PRODUCTS
    # =========================================================================

    def list_products(
        self,
        limit: int = 100,
        page: int = 1,
        sort_by: str = None,
        sort_order: str = 'asc'
    ) -> Dict:
        """List products with pagination using search endpoint."""
        # Plytix API uses POST /products/search for listing products
        data = {
            'pagination': {
                'page': page,
                'page_size': limit,
            }
        }
        if sort_by:
            data['pagination']['sort_by_attribute'] = sort_by
            data['pagination']['sort_order'] = sort_order
        return self.post('/products/search', data)

    def get_product(self, product_id: str) -> Dict:
        """Get product by ID."""
        return self.get(f'/products/{quote(product_id)}')

    def create_product(self, data: Dict) -> Dict:
        """Create new product."""
        return self.post('/products', data)

    def update_product(self, product_id: str, data: Dict) -> Dict:
        """Update existing product."""
        return self.patch(f'/products/{quote(product_id)}', data)

    def delete_product(self, product_id: str) -> Dict:
        """Delete product."""
        return self.delete(f'/products/{quote(product_id)}')

    def search_products(
        self,
        filters: List[Dict] = None,
        attributes: List[str] = None,
        limit: int = 100,
        page: int = 1
    ) -> Dict:
        """
        Search products with filters.

        Args:
            filters: List of filter objects [{field, operator, value}]
                     Operators: like, !like, eq, !eq, in, !in, gt, gte, lt, lte
                     For text search use 'like', NOT 'contains'
            attributes: List of attribute names to return
            limit: Results per page
            page: Page number

        Filter Structure:
            Plytix uses nested arrays: [[AND conditions], [AND conditions], ...]
            Outer array = OR conditions, inner array = AND conditions
            Example: [[{field, op, val}]] for single filter
        """
        data = {
            'pagination': {'page': page, 'page_size': limit}
        }
        if filters:
            # Wrap filters in nested array if not already
            # [[filter1, filter2]] = filter1 AND filter2
            # [[filter1], [filter2]] = filter1 OR filter2
            if filters and isinstance(filters, list):
                if not filters:
                    pass
                elif isinstance(filters[0], dict):
                    # Simple list of filters - wrap as AND condition
                    filters = [filters]
            data['filters'] = filters
        if attributes:
            data['attributes'] = attributes
        return self.post('/products/search', data)

    def bulk_update_products(self, updates: List[Dict]) -> Dict:
        """
        Bulk update multiple products.

        Args:
            updates: List of {id, ...fields} objects
        """
        return self.post('/products/bulk', {'products': updates})

    def add_product_assets(self, product_id: str, asset_ids: List[str]) -> Dict:
        """Add assets to product."""
        return self.post(f'/products/{quote(product_id)}/assets', {'assets': asset_ids})

    def add_product_categories(self, product_id: str, category_ids: List[str]) -> Dict:
        """Add product to categories."""
        return self.post(f'/products/{quote(product_id)}/categories', {'categories': category_ids})

    def remove_product_assets(self, product_id: str, asset_ids: List[str]) -> Dict:
        """Remove assets from product."""
        return self._request(
            'DELETE',
            f'/products/{quote(product_id)}/assets',
            data={'assets': asset_ids}
        )

    def remove_product_categories(self, product_id: str, category_ids: List[str]) -> Dict:
        """Remove product from categories."""
        return self._request(
            'DELETE',
            f'/products/{quote(product_id)}/categories',
            data={'categories': category_ids}
        )

    # =========================================================================
    # ASSETS
    # =========================================================================

    def list_assets(
        self,
        limit: int = 100,
        page: int = 1,
        file_type: str = None
    ) -> Dict:
        """List assets with pagination using search endpoint."""
        # Plytix API requires 'filters' key to be present (even if empty)
        data = {
            'filters': [],
            'pagination': {
                'page': page,
                'page_size': limit,
            }
        }
        if file_type:
            data['filters'] = [
                {'field': 'file_type', 'operator': 'eq', 'value': file_type}
            ]
        return self.post('/assets/search', data)

    def get_asset(self, asset_id: str) -> Dict:
        """Get asset by ID."""
        return self.get(f'/assets/{quote(asset_id)}')

    def upload_asset(self, file_path: str, metadata: Dict = None) -> Dict:
        """
        Upload new asset from file.

        Note: This uses multipart upload which requires special handling.
        For now, provides URL-based upload as alternative.
        """
        # Check if file exists
        path = Path(file_path)
        if not path.exists():
            raise PlytixAPIError(f"File not found: {file_path}")

        # Get file info
        filename = path.name
        file_size = path.stat().st_size

        # Create asset with URL upload (simplified approach)
        # Full multipart would require additional handling
        data = {
            'filename': filename,
            'file_size': file_size,
        }
        if metadata:
            data.update(metadata)

        return self.post('/assets', data)

    def upload_asset_url(self, url: str, filename: str = None, metadata: Dict = None) -> Dict:
        """Upload asset from URL."""
        data = {'url': url}
        if filename:
            data['filename'] = filename
        if metadata:
            data.update(metadata)
        return self.post('/assets', data)

    def update_asset(self, asset_id: str, data: Dict) -> Dict:
        """Update asset metadata."""
        return self.patch(f'/assets/{quote(asset_id)}', data)

    def delete_asset(self, asset_id: str) -> Dict:
        """Delete asset."""
        return self.delete(f'/assets/{quote(asset_id)}')

    def search_assets(
        self,
        filters: List[Dict] = None,
        limit: int = 100,
        page: int = 1
    ) -> Dict:
        """
        Search assets with filters.

        Args:
            filters: List of filter objects [{field, operator, value}]
                     Text operators: like, !like, eq, !eq
                     Multi-select: in, !in
                     Date: eq, gt, gte, lt, lte, last_days
            limit: Results per page
            page: Page number

        Filter Structure:
            Plytix uses nested arrays: [[AND conditions], [AND conditions], ...]
        """
        wrapped_filters = []
        if filters:
            if isinstance(filters, list) and filters:
                if isinstance(filters[0], dict):
                    # Simple list - wrap as AND condition
                    wrapped_filters = [filters]
                else:
                    wrapped_filters = filters
        data = {
            'filters': wrapped_filters,
            'pagination': {'page': page, 'page_size': limit}
        }
        return self.post('/assets/search', data)

    def get_asset_download_url(self, asset_id: str) -> Dict:
        """Get download URL for asset."""
        return self.get(f'/assets/{quote(asset_id)}/download')

    # =========================================================================
    # CATEGORIES
    # =========================================================================

    def list_categories(self, limit: int = 100, page: int = 1) -> Dict:
        """List product categories with pagination using search endpoint."""
        # Plytix API uses POST /categories/product/search for product categories
        data = {
            'filters': [],
            'pagination': {
                'page': page,
                'page_size': limit,
            }
        }
        return self.post('/categories/product/search', data)

    def get_category(self, category_id: str) -> Dict:
        """Get category by ID."""
        return self.get(f'/categories/{quote(category_id)}')

    def create_category(self, data: Dict) -> Dict:
        """Create new category."""
        return self.post('/categories', data)

    def update_category(self, category_id: str, data: Dict) -> Dict:
        """Update existing category."""
        return self.patch(f'/categories/{quote(category_id)}', data)

    def delete_category(self, category_id: str) -> Dict:
        """Delete category."""
        return self.delete(f'/categories/{quote(category_id)}')

    def get_category_tree(self) -> Dict:
        """
        Build category hierarchy tree from flat list.

        Plytix doesn't have a dedicated tree endpoint, so we fetch all
        categories and build the tree using parents_ids field.
        """
        # Fetch all categories with pagination (max page_size is 100)
        categories = []
        page = 1
        while True:
            result = self.list_categories(limit=100, page=page)
            batch = result.get('data', [])
            if not batch:
                break
            categories.extend(batch)
            if len(batch) < 100:
                break
            page += 1

        # Build lookup dict
        cat_by_id = {cat['id']: {**cat, 'children': []} for cat in categories}

        # Build tree structure
        roots = []
        for cat in categories:
            cat_with_children = cat_by_id[cat['id']]
            parents = cat.get('parents_ids', [])

            if not parents:
                # Root category
                roots.append(cat_with_children)
            else:
                # Find immediate parent (last in parents_ids list)
                parent_id = parents[-1] if parents else None
                if parent_id and parent_id in cat_by_id:
                    cat_by_id[parent_id]['children'].append(cat_with_children)
                else:
                    # Parent not found, treat as root
                    roots.append(cat_with_children)

        return {'data': roots}

    def list_category_products(
        self,
        category_id: str,
        limit: int = 100,
        page: int = 1
    ) -> Dict:
        """List products in a category."""
        params = {
            'pagination[limit]': limit,
            'pagination[page]': page,
        }
        return self.get(f'/categories/{quote(category_id)}/products', params)

    # =========================================================================
    # VARIANTS
    # =========================================================================

    def list_variants(
        self,
        product_id: str,
        limit: int = 100,
        page: int = 1
    ) -> Dict:
        """List variants for a specific product."""
        # Variants are accessed per-product in Plytix API
        params = {
            'pagination[limit]': limit,
            'pagination[page]': page,
        }
        return self.get(f'/products/{quote(product_id)}/variants', params)

    def get_variant(self, variant_id: str) -> Dict:
        """Get variant by ID."""
        return self.get(f'/variants/{quote(variant_id)}')

    def create_variant(self, product_id: str, data: Dict) -> Dict:
        """Create new variant for product."""
        return self.post(f'/products/{quote(product_id)}/variants', data)

    def update_variant(self, variant_id: str, data: Dict) -> Dict:
        """Update existing variant."""
        return self.patch(f'/variants/{quote(variant_id)}', data)

    def delete_variant(self, variant_id: str) -> Dict:
        """Delete variant."""
        return self.delete(f'/variants/{quote(variant_id)}')

    def bulk_create_variants(self, product_id: str, variants: List[Dict]) -> Dict:
        """Create multiple variants for a product."""
        return self.post(
            f'/products/{quote(product_id)}/variants/bulk',
            {'variants': variants}
        )

    # =========================================================================
    # ATTRIBUTES
    # =========================================================================

    def list_attributes(self, limit: int = 100, page: int = 1) -> Dict:
        """List product attributes with pagination using search endpoint."""
        # Plytix API uses POST /attributes/product/search for product attributes
        data = {
            'filters': [],
            'pagination': {
                'page': page,
                'page_size': limit,
            }
        }
        return self.post('/attributes/product/search', data)

    def get_attribute(self, attribute_id: str) -> Dict:
        """Get attribute by ID."""
        return self.get(f'/attributes/{quote(attribute_id)}')

    def create_attribute(self, data: Dict) -> Dict:
        """Create new attribute."""
        return self.post('/attributes', data)

    def update_attribute(self, attribute_id: str, data: Dict) -> Dict:
        """Update existing attribute."""
        return self.patch(f'/attributes/{quote(attribute_id)}', data)

    def delete_attribute(self, attribute_id: str) -> Dict:
        """Delete attribute."""
        return self.delete(f'/attributes/{quote(attribute_id)}')

    # Note: Attribute groups endpoints are not available in Plytix API v1
    # Attribute groups can be managed through the Plytix UI


# =============================================================================
# CLI COMMANDS
# =============================================================================

def handle_products(api: PlytixAPI, args) -> None:
    """Handle products commands."""
    if args.command == 'list':
        result = api.list_products(
            limit=args.limit,
            page=args.page,
            sort_by=args.sort_by,
            sort_order=args.sort_order
        )
        products = result.get('data', result.get('products', []))
        total = result.get('pagination', {}).get('total', len(products))
        format_output(products, 'products', args.format, total=total)

    elif args.command == 'get':
        result = api.get_product(args.id)
        product = result.get('data', result)
        format_output(product, 'products', args.format, detail=True)

    elif args.command == 'create':
        data = json.loads(args.data)
        result = api.create_product(data)
        format_success("Product created", {'id': result.get('data', result).get('id')})

    elif args.command == 'update':
        data = json.loads(args.data)
        result = api.update_product(args.id, data)
        format_success("Product updated", {'id': args.id})

    elif args.command == 'delete':
        api.delete_product(args.id)
        format_success("Product deleted", {'id': args.id})

    elif args.command == 'search':
        filters = json.loads(args.filters) if args.filters else None
        attributes = args.attributes.split(',') if args.attributes else None
        result = api.search_products(
            filters=filters,
            attributes=attributes,
            limit=args.limit,
            page=args.page
        )
        products = result.get('data', result.get('products', []))
        total = result.get('pagination', {}).get('total', len(products))
        format_output(products, 'products', args.format, total=total)

    elif args.command == 'bulk-update':
        updates = json.loads(args.data)
        result = api.bulk_update_products(updates)
        format_success("Bulk update complete", {'updated': len(updates)})

    elif args.command == 'add-assets':
        asset_ids = args.asset_ids.split(',')
        api.add_product_assets(args.id, asset_ids)
        format_success("Assets added to product", {'count': len(asset_ids)})

    elif args.command == 'add-categories':
        category_ids = args.category_ids.split(',')
        api.add_product_categories(args.id, category_ids)
        format_success("Product added to categories", {'count': len(category_ids)})


def handle_assets(api: PlytixAPI, args) -> None:
    """Handle assets commands."""
    if args.command == 'list':
        result = api.list_assets(
            limit=args.limit,
            page=args.page,
            file_type=getattr(args, 'file_type', None)
        )
        assets = result.get('data', result.get('assets', []))
        total = result.get('pagination', {}).get('total', len(assets))
        format_output(assets, 'assets', args.format, total=total)

    elif args.command == 'get':
        result = api.get_asset(args.id)
        asset = result.get('data', result)
        format_output(asset, 'assets', args.format, detail=True)

    elif args.command == 'upload':
        metadata = json.loads(args.metadata) if args.metadata else None
        if args.url:
            result = api.upload_asset_url(args.url, args.filename, metadata)
        else:
            result = api.upload_asset(args.file, metadata)
        format_success("Asset uploaded", {'id': result.get('data', result).get('id')})

    elif args.command == 'update':
        data = json.loads(args.data)
        result = api.update_asset(args.id, data)
        format_success("Asset updated", {'id': args.id})

    elif args.command == 'delete':
        api.delete_asset(args.id)
        format_success("Asset deleted", {'id': args.id})

    elif args.command == 'search':
        filters = json.loads(args.filters) if args.filters else None
        result = api.search_assets(
            filters=filters,
            limit=args.limit,
            page=args.page
        )
        assets = result.get('data', result.get('assets', []))
        total = result.get('pagination', {}).get('total', len(assets))
        format_output(assets, 'assets', args.format, total=total)

    elif args.command == 'download-url':
        result = api.get_asset_download_url(args.id)
        url = result.get('data', result).get('url', result.get('url'))
        print(f"Download URL: {url}")


def handle_categories(api: PlytixAPI, args) -> None:
    """Handle categories commands."""
    if args.command == 'list':
        result = api.list_categories(limit=args.limit, page=args.page)
        categories = result.get('data', result.get('categories', []))
        total = result.get('pagination', {}).get('total', len(categories))
        format_output(categories, 'categories', args.format, total=total)

    elif args.command == 'get':
        result = api.get_category(args.id)
        category = result.get('data', result)
        format_output(category, 'categories', args.format, detail=True)

    elif args.command == 'create':
        data = json.loads(args.data)
        result = api.create_category(data)
        format_success("Category created", {'id': result.get('data', result).get('id')})

    elif args.command == 'update':
        data = json.loads(args.data)
        result = api.update_category(args.id, data)
        format_success("Category updated", {'id': args.id})

    elif args.command == 'delete':
        api.delete_category(args.id)
        format_success("Category deleted", {'id': args.id})

    elif args.command == 'tree':
        result = api.get_category_tree()
        categories = result.get('data', result.get('categories', []))
        if args.format == 'json':
            format_output(categories, 'categories', args.format)
        else:
            from formatters import format_category_tree
            print("\nCategory Tree:")
            print("-" * 40)
            format_category_tree(categories)

    elif args.command == 'list-products':
        result = api.list_category_products(
            args.id,
            limit=args.limit,
            page=args.page
        )
        products = result.get('data', result.get('products', []))
        total = result.get('pagination', {}).get('total', len(products))
        format_output(products, 'products', args.format, total=total)


def handle_variants(api: PlytixAPI, args) -> None:
    """Handle variants commands."""
    if args.command == 'list':
        if not args.product_id:
            format_error("Product ID is required. Use --product-id <id>")
            sys.exit(1)
        result = api.list_variants(
            product_id=args.product_id,
            limit=args.limit,
            page=args.page
        )
        variants = result.get('data', result.get('variants', []))
        total = result.get('pagination', {}).get('total', len(variants))
        format_output(variants, 'variants', args.format, total=total)

    elif args.command == 'get':
        result = api.get_variant(args.id)
        variant = result.get('data', result)
        format_output(variant, 'variants', args.format, detail=True)

    elif args.command == 'create':
        data = json.loads(args.data)
        result = api.create_variant(args.product_id, data)
        format_success("Variant created", {'id': result.get('data', result).get('id')})

    elif args.command == 'update':
        data = json.loads(args.data)
        result = api.update_variant(args.id, data)
        format_success("Variant updated", {'id': args.id})

    elif args.command == 'delete':
        api.delete_variant(args.id)
        format_success("Variant deleted", {'id': args.id})

    elif args.command == 'bulk-create':
        variants = json.loads(args.data)
        result = api.bulk_create_variants(args.product_id, variants)
        format_success("Bulk create complete", {'created': len(variants)})


def handle_attributes(api: PlytixAPI, args) -> None:
    """Handle attributes commands."""
    if args.command == 'list':
        result = api.list_attributes(limit=args.limit, page=args.page)
        attributes = result.get('data', result.get('attributes', []))
        total = result.get('pagination', {}).get('total', len(attributes))
        format_output(attributes, 'attributes', args.format, total=total)

    elif args.command == 'get':
        result = api.get_attribute(args.id)
        attribute = result.get('data', result)
        format_output(attribute, 'attributes', args.format, detail=True)

    elif args.command == 'create':
        data = json.loads(args.data)
        result = api.create_attribute(data)
        format_success("Attribute created", {'id': result.get('data', result).get('id')})

    elif args.command == 'update':
        data = json.loads(args.data)
        result = api.update_attribute(args.id, data)
        format_success("Attribute updated", {'id': args.id})

    elif args.command == 'delete':
        api.delete_attribute(args.id)
        format_success("Attribute deleted", {'id': args.id})

    elif args.command in ('list-groups', 'get-group', 'create-group'):
        format_error("Attribute groups are not available via API. Use Plytix UI to manage groups.")
        sys.exit(1)


# =============================================================================
# MAIN
# =============================================================================

def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with all commands."""
    parser = argparse.ArgumentParser(
        description='Plytix PIM API CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Global options
    parser.add_argument(
        '--account', '-a',
        help='Account alias (prod, staging, etc.)'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['table', 'json', 'compact', 'summary'],
        default='table',
        help='Output format (default: table)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output'
    )

    subparsers = parser.add_subparsers(dest='domain', help='API domain')

    # =========================================================================
    # PRODUCTS
    # =========================================================================
    products = subparsers.add_parser('products', help='Product operations')
    products_sub = products.add_subparsers(dest='command')

    # products list
    p_list = products_sub.add_parser('list', help='List products')
    p_list.add_argument('--limit', '-l', type=int, default=50, help='Results per page')
    p_list.add_argument('--page', '-p', type=int, default=1, help='Page number')
    p_list.add_argument('--sort-by', help='Sort field')
    p_list.add_argument('--sort-order', choices=['asc', 'desc'], default='asc')

    # products get
    p_get = products_sub.add_parser('get', help='Get product by ID')
    p_get.add_argument('id', help='Product ID')

    # products create
    p_create = products_sub.add_parser('create', help='Create product')
    p_create.add_argument('--data', '-d', required=True, help='Product JSON data')

    # products update
    p_update = products_sub.add_parser('update', help='Update product')
    p_update.add_argument('id', help='Product ID')
    p_update.add_argument('--data', '-d', required=True, help='Update JSON data')

    # products delete
    p_delete = products_sub.add_parser('delete', help='Delete product')
    p_delete.add_argument('id', help='Product ID')

    # products search
    p_search = products_sub.add_parser('search', help='Search products')
    p_search.add_argument('--filters', help='Search filters JSON')
    p_search.add_argument('--attributes', help='Comma-separated attribute names')
    p_search.add_argument('--limit', '-l', type=int, default=50)
    p_search.add_argument('--page', '-p', type=int, default=1)

    # products bulk-update
    p_bulk = products_sub.add_parser('bulk-update', help='Bulk update products')
    p_bulk.add_argument('--data', '-d', required=True, help='Array of updates JSON')

    # products add-assets
    p_assets = products_sub.add_parser('add-assets', help='Add assets to product')
    p_assets.add_argument('id', help='Product ID')
    p_assets.add_argument('--asset-ids', required=True, help='Comma-separated asset IDs')

    # products add-categories
    p_cats = products_sub.add_parser('add-categories', help='Add product to categories')
    p_cats.add_argument('id', help='Product ID')
    p_cats.add_argument('--category-ids', required=True, help='Comma-separated category IDs')

    # =========================================================================
    # ASSETS
    # =========================================================================
    assets = subparsers.add_parser('assets', help='Asset operations')
    assets_sub = assets.add_subparsers(dest='command')

    # assets list
    a_list = assets_sub.add_parser('list', help='List assets')
    a_list.add_argument('--limit', '-l', type=int, default=50)
    a_list.add_argument('--page', '-p', type=int, default=1)
    a_list.add_argument('--file-type', help='Filter by file type')

    # assets get
    a_get = assets_sub.add_parser('get', help='Get asset by ID')
    a_get.add_argument('id', help='Asset ID')

    # assets upload
    a_upload = assets_sub.add_parser('upload', help='Upload asset')
    a_upload.add_argument('--file', help='Local file path')
    a_upload.add_argument('--url', help='URL to upload from')
    a_upload.add_argument('--filename', help='Override filename')
    a_upload.add_argument('--metadata', help='Metadata JSON')

    # assets update
    a_update = assets_sub.add_parser('update', help='Update asset')
    a_update.add_argument('id', help='Asset ID')
    a_update.add_argument('--data', '-d', required=True, help='Update JSON data')

    # assets delete
    a_delete = assets_sub.add_parser('delete', help='Delete asset')
    a_delete.add_argument('id', help='Asset ID')

    # assets search
    a_search = assets_sub.add_parser('search', help='Search assets')
    a_search.add_argument('--filters', help='Search filters JSON')
    a_search.add_argument('--limit', '-l', type=int, default=50)
    a_search.add_argument('--page', '-p', type=int, default=1)

    # assets download-url
    a_download = assets_sub.add_parser('download-url', help='Get download URL')
    a_download.add_argument('id', help='Asset ID')

    # =========================================================================
    # CATEGORIES
    # =========================================================================
    categories = subparsers.add_parser('categories', help='Category operations')
    categories_sub = categories.add_subparsers(dest='command')

    # categories list
    c_list = categories_sub.add_parser('list', help='List categories')
    c_list.add_argument('--limit', '-l', type=int, default=50)
    c_list.add_argument('--page', '-p', type=int, default=1)

    # categories get
    c_get = categories_sub.add_parser('get', help='Get category by ID')
    c_get.add_argument('id', help='Category ID')

    # categories create
    c_create = categories_sub.add_parser('create', help='Create category')
    c_create.add_argument('--data', '-d', required=True, help='Category JSON data')

    # categories update
    c_update = categories_sub.add_parser('update', help='Update category')
    c_update.add_argument('id', help='Category ID')
    c_update.add_argument('--data', '-d', required=True, help='Update JSON data')

    # categories delete
    c_delete = categories_sub.add_parser('delete', help='Delete category')
    c_delete.add_argument('id', help='Category ID')

    # categories tree
    categories_sub.add_parser('tree', help='Get category hierarchy tree')

    # categories list-products
    c_prods = categories_sub.add_parser('list-products', help='List products in category')
    c_prods.add_argument('id', help='Category ID')
    c_prods.add_argument('--limit', '-l', type=int, default=50)
    c_prods.add_argument('--page', '-p', type=int, default=1)

    # =========================================================================
    # VARIANTS
    # =========================================================================
    variants = subparsers.add_parser('variants', help='Variant operations')
    variants_sub = variants.add_subparsers(dest='command')

    # variants list
    v_list = variants_sub.add_parser('list', help='List variants for a product')
    v_list.add_argument('--product-id', required=True, help='Product ID (required)')
    v_list.add_argument('--limit', '-l', type=int, default=50)
    v_list.add_argument('--page', '-p', type=int, default=1)

    # variants get
    v_get = variants_sub.add_parser('get', help='Get variant by ID')
    v_get.add_argument('id', help='Variant ID')

    # variants create
    v_create = variants_sub.add_parser('create', help='Create variant')
    v_create.add_argument('product_id', help='Parent product ID')
    v_create.add_argument('--data', '-d', required=True, help='Variant JSON data')

    # variants update
    v_update = variants_sub.add_parser('update', help='Update variant')
    v_update.add_argument('id', help='Variant ID')
    v_update.add_argument('--data', '-d', required=True, help='Update JSON data')

    # variants delete
    v_delete = variants_sub.add_parser('delete', help='Delete variant')
    v_delete.add_argument('id', help='Variant ID')

    # variants bulk-create
    v_bulk = variants_sub.add_parser('bulk-create', help='Bulk create variants')
    v_bulk.add_argument('product_id', help='Parent product ID')
    v_bulk.add_argument('--data', '-d', required=True, help='Array of variants JSON')

    # =========================================================================
    # ATTRIBUTES
    # =========================================================================
    attributes = subparsers.add_parser('attributes', help='Attribute operations')
    attributes_sub = attributes.add_subparsers(dest='command')

    # attributes list
    attr_list = attributes_sub.add_parser('list', help='List attributes')
    attr_list.add_argument('--limit', '-l', type=int, default=50)
    attr_list.add_argument('--page', '-p', type=int, default=1)

    # attributes get
    attr_get = attributes_sub.add_parser('get', help='Get attribute by ID')
    attr_get.add_argument('id', help='Attribute ID')

    # attributes create
    attr_create = attributes_sub.add_parser('create', help='Create attribute')
    attr_create.add_argument('--data', '-d', required=True, help='Attribute JSON data')

    # attributes update
    attr_update = attributes_sub.add_parser('update', help='Update attribute')
    attr_update.add_argument('id', help='Attribute ID')
    attr_update.add_argument('--data', '-d', required=True, help='Update JSON data')

    # attributes delete
    attr_delete = attributes_sub.add_parser('delete', help='Delete attribute')
    attr_delete.add_argument('id', help='Attribute ID')

    # attributes list-groups
    attr_groups = attributes_sub.add_parser('list-groups', help='List attribute groups')
    attr_groups.add_argument('--limit', '-l', type=int, default=50)
    attr_groups.add_argument('--page', '-p', type=int, default=1)

    # attributes get-group
    attr_group = attributes_sub.add_parser('get-group', help='Get attribute group by ID')
    attr_group.add_argument('id', help='Group ID')

    # attributes create-group
    attr_create_group = attributes_sub.add_parser('create-group', help='Create attribute group')
    attr_create_group.add_argument('--data', '-d', required=True, help='Group JSON data')

    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.domain:
        parser.print_help()
        sys.exit(0)

    if not args.command:
        # Show domain-specific help
        parser.parse_args([args.domain, '--help'])
        sys.exit(0)

    try:
        api = PlytixAPI(account=args.account)

        handlers = {
            'products': handle_products,
            'assets': handle_assets,
            'categories': handle_categories,
            'variants': handle_variants,
            'attributes': handle_attributes,
        }

        handler = handlers.get(args.domain)
        if handler:
            handler(api, args)
        else:
            format_error(f"Unknown domain: {args.domain}")
            sys.exit(1)

    except PlytixAuthError as e:
        format_error(str(e))
        sys.exit(1)
    except PlytixAPIError as e:
        format_error(str(e), e.details if args.debug else None)
        sys.exit(1)
    except json.JSONDecodeError as e:
        format_error(f"Invalid JSON: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        sys.exit(130)


if __name__ == '__main__':
    main()
