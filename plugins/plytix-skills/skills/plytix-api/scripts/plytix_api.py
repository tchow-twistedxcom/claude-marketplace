#!/usr/bin/env python3
"""
Plytix PIM API CLI

Comprehensive CLI for Plytix Product Information Management system.
Supports Products, Assets, Categories, Variants, Attributes, and Relationships.

Usage:
    python plytix_api.py <domain> <command> [options]

Examples:
    python plytix_api.py products list --limit 50
    python plytix_api.py products get <product_id>
    python plytix_api.py assets upload /path/to/image.jpg
    python plytix_api.py categories tree

=============================================================================
API LIMITATIONS & GOTCHAS (Reference)
=============================================================================

1. SEARCH FILTERS - Custom Attributes NOT Supported
   - search_products() can only filter by built-in fields (sku, label, gtin, status)
   - Custom attributes like 'amazon_parent_asin' CANNOT be used as search filters
   - Workaround: Use find_products_by_attribute() which fetches and filters locally

2. THUMBNAIL FORMAT
   - update_product(thumbnail=...) requires {'id': 'asset_id'} format, not string
   - This wrapper auto-wraps strings: 'asset123' → {'id': 'asset123'}

3. ASSET LINKING
   - add_product_assets() requires attribute_label (default: 'assets')
   - The attribute must be a MediaGallery type in Plytix schema
   - Creating custom media gallery: use create_attribute() with type 'MediaGalleryAttribute'

4. DATE ATTRIBUTES
   - DateAttribute values must be '%Y-%m-%d' format (e.g., '2025-12-23')
   - Using ISO format with time (isoformat()) will cause validation errors

5. DROPDOWN ATTRIBUTES
   - Options must be simple strings: ['US', 'CA', 'MX']
   - NOT objects: [{'value': 'US', 'label': 'United States'}]

6. ASSET UPLOAD - Duplicates
   - upload_asset_url() returns 409 Conflict if asset URL already exists
   - With return_existing=True (default), returns {'id': existing_id, 'status': 'existing'}

7. RELATIONSHIPS
   - add_product_relationships() links FROM source product TO related products
   - The source product "has" the related products
   - For bidirectional relationships, link from both sides

8. RATE LIMITING
   - API returns 429 when rate limited
   - Check Retry-After header for wait time

9. SEARCH vs GET
   - search_products() returns basic fields only, NOT full attributes
   - Use get_product(id) to retrieve complete attribute data
   - The 'attributes' param in search specifies which attrs to include (still limited)
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
        timeout: int = 30,
        _retry: bool = True
    ) -> Dict:
        """
        Make authenticated API request with automatic token refresh.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint (e.g., /products)
            data: Request body data
            params: Query parameters
            timeout: Request timeout in seconds
            _retry: Internal flag for token refresh retry

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
                error_msg = error_json.get('message', error_json.get('msg', error_json.get('error', str(e))))
                details = error_json
            except (json.JSONDecodeError, KeyError, TypeError):
                error_msg = error_body[:500] if error_body else str(e)
                details = {'raw': error_body}

            # Handle token expiration - auto-refresh and retry
            if e.code == 401 and _retry:
                error_str = str(error_msg).lower()
                if 'token' in error_str or 'expired' in error_str or 'unauthorized' in error_str:
                    self.auth.clear_cache()
                    return self._request(method, endpoint, data, params, timeout, _retry=False)

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
        """
        Get product by ID.

        Returns:
            Product dict with 'id', 'sku', 'label', 'attributes', 'assets', etc.
            Returns empty dict if product not found.
        """
        response = self.get(f'/products/{quote(product_id)}')
        # API returns {'data': [product]} - extract the product
        if response and 'data' in response and response['data']:
            return response['data'][0]
        return {}

    def create_product(self, data: Dict) -> Dict:
        """Create new product."""
        return self.post('/products', data)

    def update_product(self, product_id: str, data: Dict) -> Dict:
        """
        Update existing product.

        Args:
            product_id: Product ID
            data: Fields to update. Common fields:
                - sku: Product SKU
                - label: Product label/name
                - status: 'draft', 'completed', etc.
                - thumbnail: Asset ID (string) or {'id': asset_id} - auto-wrapped if string
                - gtin: GTIN/UPC/EAN code
                - attributes: Dict of {attribute_label: value}

        Returns:
            Updated product data

        Notes:
            - Thumbnail is auto-wrapped: 'asset123' becomes {'id': 'asset123'}
        """
        # Auto-wrap thumbnail if it's a string (Plytix requires {'id': ...} format)
        if 'thumbnail' in data:
            thumb = data['thumbnail']
            if isinstance(thumb, str):
                data = {**data, 'thumbnail': {'id': thumb}}
            elif thumb is None:
                # Allow clearing thumbnail
                pass
            elif not isinstance(thumb, dict) or 'id' not in thumb:
                raise PlytixAPIError(
                    "thumbnail must be asset_id string or {'id': asset_id}",
                    details={'field': 'thumbnail', 'received': type(thumb).__name__}
                )
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
            filters: List of filter dicts with keys: 'field', 'operator', 'value'
                     Operators: like, !like, eq, !eq, in, !in, gt, gte, lt, lte
                     For text search use 'like', NOT 'contains'
            attributes: List of attribute names to include in results.
                        IMPORTANT: If not specified, product attributes will be EMPTY!
                        Example: ['sku', 'amazon_long_description', 'brand']
            limit: Results per page (max 100)
            page: Page number (1-indexed)

        Returns:
            Dict with 'data' (list of products) and 'pagination' info.
            Each product contains: id, sku, thumbnail, categories, etc.

        Note:
            The search endpoint returns basic product info but NOT attribute values.
            To get full attribute data, use get_product(product_id) after searching.

        Filter Structure:
            Plytix uses nested arrays: [[AND conditions], [AND conditions], ...]
            Outer array = OR conditions, inner array = AND conditions

        Example:
            # Search for SKU containing 'MCA' with attributes
            results = api.search_products(
                filters=[{'field': 'sku', 'operator': 'like', 'value': 'MCA'}],
                attributes=['sku', 'brand', 'amazon_long_description']
            )
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

    def find_products_by_attribute(
        self,
        attribute_name: str,
        value: str,
        operator: str = 'eq',
        sku_pattern: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Find products by custom attribute value.

        IMPORTANT: Plytix search API does NOT support filtering by custom attributes.
        This method works around that limitation by:
        1. Optionally filtering by SKU pattern first (using API filter)
        2. Fetching full product details for each match
        3. Filtering locally by attribute value

        This is slower than native API filtering, but necessary for custom attributes.

        Args:
            attribute_name: The attribute label to match (e.g., 'amazon_parent_asin')
            value: The value to match
            operator: Match operator - 'eq' (exact), 'like' (contains), 'startswith', 'endswith'
            sku_pattern: Optional SKU pattern to pre-filter (speeds up search)
            limit: Maximum products to return

        Returns:
            List of matching products with full attribute data

        Example:
            # Find all products where amazon_parent_asin = 'B077QMJFG9'
            children = api.find_products_by_attribute('amazon_parent_asin', 'B077QMJFG9')

            # Find products with SKU starting with 'AMZN-' and specific parent
            children = api.find_products_by_attribute(
                'amazon_parent_asin', 'B077QMJFG9',
                sku_pattern='AMZN-%'
            )
        """
        matching = []
        page = 1

        # Build optional SKU filter
        filters = []
        if sku_pattern:
            filters.append({'field': 'sku', 'operator': 'like', 'value': sku_pattern})

        while len(matching) < limit:
            # Fetch page of products
            result = self.search_products(
                filters=filters if filters else None,
                attributes=[attribute_name],
                limit=100,
                page=page
            )
            products = result.get('data', [])
            if not products:
                break

            # Filter by attribute value
            for p in products:
                if len(matching) >= limit:
                    break

                # Get full product to check attribute
                full_product = self.get_product(p['id'])
                attrs = full_product.get('attributes', {})
                attr_value = attrs.get(attribute_name)

                # Check match
                match = False
                if operator == 'eq':
                    match = attr_value == value
                elif operator == 'like':
                    match = value.lower() in str(attr_value or '').lower()
                elif operator == 'startswith':
                    match = str(attr_value or '').startswith(value)
                elif operator == 'endswith':
                    match = str(attr_value or '').endswith(value)

                if match:
                    matching.append(full_product)

            # Check if more pages
            pagination = result.get('pagination', {})
            total = pagination.get('total_count', pagination.get('total', 0))
            if page * 100 >= total:
                break
            page += 1

        return matching

    def add_product_assets(
        self,
        product_id: str,
        asset_ids: List[str],
        attribute_label: str = 'assets'
    ) -> List[Dict]:
        """
        Link assets to a product via a media gallery attribute.

        Plytix requires assets to be linked to a specific media gallery attribute
        (e.g., 'assets', 'amazon_images', 'product_photos').

        Args:
            product_id: Plytix product ID
            asset_ids: List of asset IDs to link
            attribute_label: Media gallery attribute name to link to (default: 'assets')

        Returns:
            List of API responses for each asset link

        Example:
            # Link to default 'assets' attribute
            api.add_product_assets(product_id, [asset_id1, asset_id2])

            # Link to custom media gallery
            api.add_product_assets(product_id, [asset_id], attribute_label='amazon_images')
        """
        results = []
        for asset_id in asset_ids:
            try:
                data = {'id': asset_id, 'attribute_label': attribute_label}
                result = self.post(f'/products/{quote(product_id)}/assets', data)
                results.append({'asset_id': asset_id, 'status': 'linked', 'response': result})
            except PlytixAPIError as e:
                if 'already' in str(e).lower():
                    results.append({'asset_id': asset_id, 'status': 'already_linked'})
                else:
                    results.append({'asset_id': asset_id, 'status': 'error', 'error': str(e)})
        return results

    def add_product_categories(self, product_id: str, category_ids: List[str]) -> Dict:
        """Add product to categories."""
        return self.post(f'/products/{quote(product_id)}/categories', {'categories': category_ids})

    def remove_product_assets(self, product_id: str, asset_ids: List[str]) -> Dict:
        """
        Remove assets from product.

        Note: This endpoint may return 405 (Method Not Allowed) in some Plytix
        configurations. As a workaround, you can unlink assets by clearing
        the media gallery attribute that references them.

        Args:
            product_id: Product ID
            asset_ids: List of asset IDs to unlink

        Returns:
            API response

        Raises:
            PlytixAPIError: May raise 405 if endpoint not supported
        """
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

    def get_product_assets(self, product_id: str) -> List[Dict]:
        """
        Get assets linked to a product.

        Note: There is no separate endpoint for product assets. This method
        retrieves the full product and extracts the assets list.

        Args:
            product_id: Product ID

        Returns:
            List of asset objects with id, filename, file_size, etc.
        """
        product = self.get_product(product_id)
        return product.get('assets', [])

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

    def upload_asset_url(
        self,
        url: str,
        filename: str = None,
        metadata: Dict = None,
        return_existing: bool = True
    ) -> Dict:
        """
        Upload asset from URL.

        Args:
            url: Public URL of the image/file to import
            filename: Optional custom filename (otherwise derived from URL)
            metadata: Optional metadata dict (e.g., {'tags': ['product']})
            return_existing: If True and asset already exists, return existing asset info
                           instead of raising an error

        Returns:
            Asset dict with 'id', 'filename', 'url', etc.

        Raises:
            PlytixAPIError: If upload fails (unless 409 Conflict and return_existing=True)

        Example:
            asset = api.upload_asset_url('https://example.com/image.jpg')
            asset_id = asset['id']

        Notes:
            - If asset with same URL already exists, raises 409 Conflict with existing
              asset ID in error details: {'errors': [{'field': 'asset.id', 'msg': 'ID'}]}
            - When return_existing=True, extracts the ID and returns {'id': existing_id, 'status': 'existing'}
        """
        data = {'url': url}
        if filename:
            data['filename'] = filename
        if metadata:
            data.update(metadata)

        try:
            result = self.post('/assets', data)
            # Unwrap response: API returns {'data': [{'id': '...', ...}]}
            if isinstance(result, dict) and 'data' in result:
                data_list = result['data']
                if isinstance(data_list, list) and data_list:
                    return data_list[0]  # Return first asset dict
            return result
        except PlytixAPIError as e:
            # Handle 409 Conflict - asset already exists
            if e.status_code == 409 and return_existing:
                # Extract existing asset ID from error details
                # Structure: {'error': {'errors': [{'field': 'asset.id', 'msg': 'ID'}], ...}}
                details = e.details or {}
                error_info = details.get('error', details)  # Handle both wrapped and unwrapped
                errors = error_info.get('errors', [])
                for err in errors:
                    if err.get('field') == 'asset.id':
                        existing_id = err.get('msg')
                        if existing_id:
                            return {'id': existing_id, 'status': 'existing', 'url': url}
            raise

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
            limit: Results per page (max 100)
            page: Page number

        Valid Operators:
            Text fields: 'eq', '!eq', 'like', '!like' (NOT 'contains' - use 'like' instead)
            Multi-select: 'in', '!in'
            Date fields: 'eq', 'gt', 'gte', 'lt', 'lte', 'last_days'

        Common Searchable Fields:
            - 'filename': Asset filename (use 'like' for partial match)
            - 'extension': File extension
            - 'created': Creation date
            - 'modified': Last modified date

        Filter Structure:
            Plytix uses nested arrays: [[AND conditions], [AND conditions], ...]

        Example:
            # Find assets by filename pattern
            api.search_assets(filters=[
                {'field': 'filename', 'operator': 'like', 'value': 'product-123'}
            ])

        Note:
            The 'public_url' field is NOT directly searchable. To find assets by
            URL, search by filename instead (last part of URL path).
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
        return self.get(f'/attributes/product/{quote(attribute_id)}')

    def create_attribute(self, data: Dict) -> Dict:
        """
        Create new product attribute.

        Args:
            data: Attribute definition with:
                - name: Display name (human readable)
                - label: Internal identifier (slug, auto-generated if not provided)
                - type_class: TextAttribute, DropdownAttribute, BooleanAttribute,
                              HtmlAttribute, DateAttribute, NumberAttribute
                - description: Optional description
                - options: Required for DropdownAttribute type
                - groups: Optional list of group UUIDs

        Returns:
            Created attribute data

        Notes:
            - DateAttribute: Values must be in '%Y-%m-%d' format (e.g., '2025-12-23'),
              NOT ISO timestamps. Using isoformat() will cause validation errors.
            - DropdownAttribute: Options must be simple strings, not objects.
              Correct: ['US', 'CA', 'MX']
              Wrong: [{'value': 'US', 'label': 'United States'}]
        """
        return self.post('/attributes/product', data)

    def update_attribute(self, attribute_id: str, data: Dict) -> Dict:
        """Update existing attribute."""
        return self.patch(f'/attributes/product/{quote(attribute_id)}', data)

    def delete_attribute(self, attribute_id: str) -> Dict:
        """Delete attribute."""
        return self.delete(f'/attributes/product/{quote(attribute_id)}')

    # Note: Attribute groups endpoints are not available in Plytix API v1
    # Attribute groups can be managed through the Plytix UI

    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================

    def list_relationships(self, limit: int = 100, page: int = 1) -> Dict:
        """
        List product relationships with pagination.

        Returns:
            Dict with 'data' (list of relationships) and 'pagination' info.
            Each relationship has: id, name, label, bidirectional
        """
        data = {
            'filters': [],
            'pagination': {
                'page': page,
                'page_size': limit,
            }
        }
        return self.post('/relationships/search', data)

    def get_relationship(self, relationship_id: str) -> Dict:
        """Get relationship by ID."""
        return self.get(f'/relationships/{quote(relationship_id)}')

    def search_relationships(
        self,
        filters: List[Dict] = None,
        limit: int = 100,
        page: int = 1
    ) -> Dict:
        """
        Search relationships with filters.

        Args:
            filters: List of filter dicts with keys: 'field', 'operator', 'value'
                     Example: [{'field': 'name', 'operator': 'like', 'value': 'Amazon'}]
            limit: Results per page
            page: Page number

        Returns:
            Dict with 'data' (list of relationships) and 'pagination' info.
        """
        wrapped_filters = []
        if filters:
            if isinstance(filters, list) and filters:
                if isinstance(filters[0], dict):
                    wrapped_filters = [filters]
                else:
                    wrapped_filters = filters
        data = {
            'filters': wrapped_filters,
            'pagination': {'page': page, 'page_size': limit}
        }
        return self.post('/relationships/search', data)

    def get_relationship_by_name(self, name: str) -> Optional[Dict]:
        """
        Find a relationship by name.

        Args:
            name: Relationship name to search for (case-insensitive contains)

        Returns:
            First matching relationship or None
        """
        result = self.search_relationships(
            filters=[{'field': 'name', 'operator': 'like', 'value': name}]
        )
        relationships = result.get('data', [])
        for rel in relationships:
            if rel.get('name', '').lower() == name.lower():
                return rel
        return relationships[0] if relationships else None

    def add_product_relationships(
        self,
        product_id: str,
        relationship_id: str,
        related_product_ids: List[str],
        quantity: int = 1
    ) -> Dict:
        """
        Link products to a product via a relationship.

        Args:
            product_id: The product to add relationships to
            relationship_id: The relationship type ID (e.g., "Amazon Hierarchy")
            related_product_ids: List of product IDs to link
            quantity: Quantity for each relationship (default: 1)

        Returns:
            API response
        """
        # Format: {"product_relationships": [{"product_id": "...", "quantity": 1}]}
        product_relationships = [
            {"product_id": pid, "quantity": quantity}
            for pid in related_product_ids
        ]
        return self.post(
            f'/products/{quote(product_id)}/relationships/{quote(relationship_id)}',
            {'product_relationships': product_relationships}
        )

    def get_product_relationships(self, product_id: str) -> List[Dict]:
        """
        Get all relationships for a product.

        Note: There is no separate endpoint for product relationships. This method
        retrieves the full product and extracts the relationships list.

        Args:
            product_id: Product ID

        Returns:
            List of relationship objects, each with:
                - relationship_id: The relationship type ID
                - relationship_label: The relationship type label (e.g., 'amazon_listings')
                - related_products: List of {product_id, quantity, last_modified}
        """
        product = self.get_product(product_id)
        return product.get('relationships', [])

    def remove_product_relationships(
        self,
        product_id: str,
        relationship_id: str,
        related_product_ids: List[str]
    ) -> Dict:
        """
        Remove relationship links from a product.

        Args:
            product_id: The product to remove relationships from
            relationship_id: The relationship type ID
            related_product_ids: List of product IDs to unlink

        Returns:
            API response
        """
        return self._request(
            'DELETE',
            f'/products/{quote(product_id)}/relationships/{quote(relationship_id)}',
            data={'products': related_product_ids}
        )

    def create_relationship(self, data: Dict) -> Dict:
        """
        Create a new relationship type.

        Args:
            data: Relationship definition with:
                - name: Display name
                - label: Internal identifier (slug)
                - bidirectional: Whether relationship goes both ways

        Returns:
            Created relationship data
        """
        return self.post('/relationships', data)

    def update_relationship(self, relationship_id: str, data: Dict) -> Dict:
        """Update existing relationship type."""
        return self.patch(f'/relationships/{quote(relationship_id)}', data)

    def delete_relationship(self, relationship_id: str) -> Dict:
        """Delete relationship type."""
        return self.delete(f'/relationships/{quote(relationship_id)}')

    # =========================================================================
    # PRODUCT FAMILIES
    # =========================================================================

    def list_product_families(self, limit: int = 100, page: int = 1) -> Dict:
        """
        List product families with pagination.

        Returns:
            Dict with 'data' (list of families) and 'pagination' info.
            Each family has: id, name, label, attributes
        """
        data = {
            'filters': [],
            'pagination': {
                'page': page,
                'page_size': limit,
            }
        }
        return self.post('/product_families/search', data)

    def get_product_family(self, family_id: str) -> Dict:
        """Get product family by ID."""
        return self.get(f'/product_families/{quote(family_id)}')

    def create_product_family(self, data: Dict) -> Dict:
        """
        Create a new product family.

        Args:
            data: Family definition with:
                - name: Display name (e.g., "8 - Amazon")
                - label: Internal identifier (slug, auto-generated if not provided)
                - description: Optional description

        Returns:
            Created family data including 'id'
        """
        return self.post('/product_families', data)

    def update_product_family(self, family_id: str, data: Dict) -> Dict:
        """Update existing product family."""
        return self.patch(f'/product_families/{quote(family_id)}', data)

    def delete_product_family(self, family_id: str) -> Dict:
        """Delete product family."""
        return self.delete(f'/product_families/{quote(family_id)}')

    def search_product_families(
        self,
        filters: List[Dict] = None,
        limit: int = 100,
        page: int = 1
    ) -> Dict:
        """
        Search product families with filters.

        Args:
            filters: List of filter dicts with keys: 'field', 'operator', 'value'
            limit: Results per page
            page: Page number

        Returns:
            Dict with 'data' (list of families) and 'pagination' info.
        """
        wrapped_filters = []
        if filters:
            if isinstance(filters, list) and filters:
                if isinstance(filters[0], dict):
                    wrapped_filters = [filters]
                else:
                    wrapped_filters = filters
        data = {
            'filters': wrapped_filters,
            'pagination': {'page': page, 'page_size': limit}
        }
        return self.post('/product_families/search', data)

    def link_family_attributes(
        self,
        family_id: str,
        attribute_ids: List[str]
    ) -> Dict:
        """
        Link attributes to a product family.

        Args:
            family_id: Product family ID
            attribute_ids: List of attribute IDs to link

        Returns:
            API response
        """
        return self.post(
            f'/product_families/{quote(family_id)}/attributes/link',
            {'attributes': attribute_ids}
        )

    def unlink_family_attributes(
        self,
        family_id: str,
        attribute_ids: List[str]
    ) -> Dict:
        """
        Unlink attributes from a product family.

        Args:
            family_id: Product family ID
            attribute_ids: List of attribute IDs to unlink

        Returns:
            API response
        """
        return self.post(
            f'/product_families/{quote(family_id)}/attributes/unlink',
            {'attributes': attribute_ids}
        )

    def get_family_attributes(self, family_id: str) -> Dict:
        """
        Get attributes directly linked to a product family.

        Returns only attributes explicitly assigned to this family,
        not inherited from parent families.
        """
        return self.get(f'/product_families/{quote(family_id)}/attributes')

    def get_family_all_attributes(self, family_id: str) -> Dict:
        """
        Get all attributes available to a product family.

        Includes attributes inherited from parent families and
        system-wide default attributes.
        """
        return self.get(f'/product_families/{quote(family_id)}/all_attributes')

    def assign_product_family(self, product_id: str, family_id: str) -> Dict:
        """
        Assign a product family to a product.

        Args:
            product_id: Product ID
            family_id: Product family ID to assign

        Returns:
            API response

        Note:
            This can also be done via update_product() with 'product_family' field.
        """
        return self.post(
            f'/products/{quote(product_id)}/family',
            {'product_family_id': family_id}
        )

    # =========================================================================
    # FILE CATEGORIES (Asset Categories)
    # =========================================================================

    def list_file_categories(self, limit: int = 100, page: int = 1) -> Dict:
        """List file/asset categories with pagination."""
        data = {
            'filters': [],
            'pagination': {
                'page': page,
                'page_size': limit,
            }
        }
        return self.post('/categories/file/search', data)

    def create_file_category(self, data: Dict) -> Dict:
        """
        Create a new file/asset category.

        Args:
            data: Category definition with:
                - name: Display name
                - label: Internal identifier (slug)
                - description: Optional description

        Returns:
            Created category data
        """
        return self.post('/categories/file', data)

    def add_file_subcategory(self, parent_id: str, data: Dict) -> Dict:
        """
        Add a subcategory under a parent file category.

        Args:
            parent_id: Parent category ID
            data: Subcategory definition

        Returns:
            Created subcategory data
        """
        return self.post(f'/categories/file/{quote(parent_id)}', data)

    def update_file_category(self, category_id: str, data: Dict) -> Dict:
        """Update existing file category."""
        return self.patch(f'/categories/file/{quote(category_id)}', data)

    def delete_file_category(self, category_id: str) -> Dict:
        """Delete file category."""
        return self.delete(f'/categories/file/{quote(category_id)}')

    def search_file_categories(
        self,
        filters: List[Dict] = None,
        limit: int = 100,
        page: int = 1
    ) -> Dict:
        """Search file categories with filters."""
        wrapped_filters = []
        if filters:
            if isinstance(filters, list) and filters:
                if isinstance(filters[0], dict):
                    wrapped_filters = [filters]
                else:
                    wrapped_filters = filters
        data = {
            'filters': wrapped_filters,
            'pagination': {'page': page, 'page_size': limit}
        }
        return self.post('/categories/file/search', data)

    # =========================================================================
    # PRODUCT CATEGORIES - Additional endpoints
    # =========================================================================

    def add_product_subcategory(self, parent_id: str, data: Dict) -> Dict:
        """
        Add a subcategory under a parent product category.

        Args:
            parent_id: Parent category ID
            data: Subcategory definition with 'name', 'label', etc.

        Returns:
            Created subcategory data
        """
        return self.post(f'/categories/product/{quote(parent_id)}', data)

    def get_product_category_list(self, product_id: str) -> List[str]:
        """
        Get list of category IDs a product belongs to.

        Note: This extracts categories from the full product data.
        """
        product = self.get_product(product_id)
        return product.get('categories', [])

    # =========================================================================
    # VARIANTS - Additional endpoints
    # =========================================================================

    def resync_variant_attributes(self, product_id: str) -> Dict:
        """
        Resync variant attributes with the parent product.

        This ensures variant attributes are synchronized with their
        parent product's attribute configuration.

        Args:
            product_id: Parent product ID

        Returns:
            API response
        """
        return self.post(f'/products/{quote(product_id)}/variants/resync', {})

    # =========================================================================
    # ATTRIBUTE GROUPS
    # =========================================================================

    def list_attribute_groups(self, limit: int = 100, page: int = 1) -> Dict:
        """
        List attribute groups with pagination.

        Note: Attribute groups organize related attributes in the Plytix UI.
        """
        data = {
            'filters': [],
            'pagination': {
                'page': page,
                'page_size': limit,
            }
        }
        return self.post('/attributes/product/groups/search', data)

    def get_attribute_group(self, group_id: str) -> Dict:
        """Get attribute group by ID."""
        return self.get(f'/attributes/product/groups/{quote(group_id)}')

    def create_attribute_group(self, data: Dict) -> Dict:
        """
        Create a new attribute group.

        Args:
            data: Group definition with:
                - name: Display name
                - label: Internal identifier
                - attributes: Optional list of attribute IDs to include

        Returns:
            Created group data
        """
        return self.post('/attributes/product/groups', data)

    def update_attribute_group(self, group_id: str, data: Dict) -> Dict:
        """Update existing attribute group."""
        return self.patch(f'/attributes/product/groups/{quote(group_id)}', data)

    def delete_attribute_group(self, group_id: str) -> Dict:
        """Delete attribute group."""
        return self.delete(f'/attributes/product/groups/{quote(group_id)}')

    def search_attribute_groups(
        self,
        filters: List[Dict] = None,
        limit: int = 100,
        page: int = 1
    ) -> Dict:
        """Search attribute groups with filters."""
        wrapped_filters = []
        if filters:
            if isinstance(filters, list) and filters:
                if isinstance(filters[0], dict):
                    wrapped_filters = [filters]
                else:
                    wrapped_filters = filters
        data = {
            'filters': wrapped_filters,
            'pagination': {'page': page, 'page_size': limit}
        }
        return self.post('/attributes/product/groups/search', data)

    # =========================================================================
    # ACCOUNTS
    # =========================================================================

    def search_account_memberships(
        self,
        filters: List[Dict] = None,
        limit: int = 100,
        page: int = 1
    ) -> Dict:
        """
        Search account memberships.

        Returns information about users/members in the account.
        """
        wrapped_filters = []
        if filters:
            if isinstance(filters, list) and filters:
                if isinstance(filters[0], dict):
                    wrapped_filters = [filters]
                else:
                    wrapped_filters = filters
        data = {
            'filters': wrapped_filters,
            'pagination': {'page': page, 'page_size': limit}
        }
        return self.post('/accounts/memberships/search', data)

    def search_api_credentials(
        self,
        filters: List[Dict] = None,
        limit: int = 100,
        page: int = 1
    ) -> Dict:
        """
        Search API credentials.

        Returns information about API keys and access tokens.
        """
        wrapped_filters = []
        if filters:
            if isinstance(filters, list) and filters:
                if isinstance(filters[0], dict):
                    wrapped_filters = [filters]
                else:
                    wrapped_filters = filters
        data = {
            'filters': wrapped_filters,
            'pagination': {'page': page, 'page_size': limit}
        }
        return self.post('/accounts/api-credentials/search', data)

    # =========================================================================
    # AVAILABLE FILTERS
    # =========================================================================

    def get_asset_filters(self) -> Dict:
        """
        Get available filter fields for assets.

        Returns list of fields that can be used in asset search filters.
        """
        return self.get('/filters/asset')

    def get_product_filters(self) -> Dict:
        """
        Get available filter fields for products.

        Returns list of fields that can be used in product search filters.
        """
        return self.get('/filters/product')  # Note: singular, not plural

    def get_relationship_filters(self) -> Dict:
        """
        Get available filter fields for relationships.

        Returns list of fields that can be used in relationship search filters.
        """
        return self.get('/filters/relationships')


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

    elif args.command == 'list-groups':
        result = api.list_attribute_groups(limit=args.limit, page=args.page)
        groups = result.get('data', [])
        total = result.get('pagination', {}).get('total', len(groups))
        format_output(groups, 'attribute_groups', args.format, total=total)

    elif args.command == 'get-group':
        result = api.get_attribute_group(args.id)
        group = result.get('data', result)
        format_output(group, 'attribute_groups', args.format, detail=True)

    elif args.command == 'create-group':
        data = json.loads(args.data)
        result = api.create_attribute_group(data)
        format_success("Attribute group created", {'id': result.get('data', result).get('id')})

    elif args.command == 'update-group':
        data = json.loads(args.data)
        result = api.update_attribute_group(args.id, data)
        format_success("Attribute group updated", {'id': args.id})

    elif args.command == 'delete-group':
        api.delete_attribute_group(args.id)
        format_success("Attribute group deleted", {'id': args.id})


def handle_families(api: PlytixAPI, args) -> None:
    """Handle product families commands."""
    if args.command == 'list':
        result = api.list_product_families(limit=args.limit, page=args.page)
        families = result.get('data', [])
        total = result.get('pagination', {}).get('total', len(families))
        format_output(families, 'families', args.format, total=total)

    elif args.command == 'get':
        result = api.get_product_family(args.id)
        family = result.get('data', result)
        format_output(family, 'families', args.format, detail=True)

    elif args.command == 'create':
        data = json.loads(args.data)
        result = api.create_product_family(data)
        format_success("Product family created", {'id': result.get('data', result).get('id')})

    elif args.command == 'update':
        data = json.loads(args.data)
        result = api.update_product_family(args.id, data)
        format_success("Product family updated", {'id': args.id})

    elif args.command == 'delete':
        api.delete_product_family(args.id)
        format_success("Product family deleted", {'id': args.id})

    elif args.command == 'search':
        filters = json.loads(args.filters) if args.filters else None
        result = api.search_product_families(
            filters=filters,
            limit=args.limit,
            page=args.page
        )
        families = result.get('data', [])
        total = result.get('pagination', {}).get('total', len(families))
        format_output(families, 'families', args.format, total=total)

    elif args.command == 'link-attributes':
        attribute_ids = args.attribute_ids.split(',')
        api.link_family_attributes(args.id, attribute_ids)
        format_success("Attributes linked to family", {'count': len(attribute_ids)})

    elif args.command == 'unlink-attributes':
        attribute_ids = args.attribute_ids.split(',')
        api.unlink_family_attributes(args.id, attribute_ids)
        format_success("Attributes unlinked from family", {'count': len(attribute_ids)})

    elif args.command == 'get-attributes':
        result = api.get_family_attributes(args.id)
        attributes = result.get('data', result)
        format_output(attributes, 'attributes', args.format)

    elif args.command == 'get-all-attributes':
        result = api.get_family_all_attributes(args.id)
        attributes = result.get('data', result)
        format_output(attributes, 'attributes', args.format)


def handle_relationships(api: PlytixAPI, args) -> None:
    """Handle relationships commands."""
    if args.command == 'list':
        result = api.list_relationships(limit=args.limit, page=args.page)
        relationships = result.get('data', [])
        total = result.get('pagination', {}).get('total', len(relationships))
        format_output(relationships, 'relationships', args.format, total=total)

    elif args.command == 'get':
        result = api.get_relationship(args.id)
        relationship = result.get('data', result)
        format_output(relationship, 'relationships', args.format, detail=True)

    elif args.command == 'create':
        data = json.loads(args.data)
        result = api.create_relationship(data)
        format_success("Relationship created", {'id': result.get('data', result).get('id')})

    elif args.command == 'update':
        data = json.loads(args.data)
        result = api.update_relationship(args.id, data)
        format_success("Relationship updated", {'id': args.id})

    elif args.command == 'delete':
        api.delete_relationship(args.id)
        format_success("Relationship deleted", {'id': args.id})

    elif args.command == 'search':
        filters = json.loads(args.filters) if args.filters else None
        result = api.search_relationships(
            filters=filters,
            limit=args.limit,
            page=args.page
        )
        relationships = result.get('data', [])
        total = result.get('pagination', {}).get('total', len(relationships))
        format_output(relationships, 'relationships', args.format, total=total)


def handle_file_categories(api: PlytixAPI, args) -> None:
    """Handle file/asset categories commands."""
    if args.command == 'list':
        result = api.list_file_categories(limit=args.limit, page=args.page)
        categories = result.get('data', [])
        total = result.get('pagination', {}).get('total', len(categories))
        format_output(categories, 'file_categories', args.format, total=total)

    elif args.command == 'create':
        data = json.loads(args.data)
        result = api.create_file_category(data)
        format_success("File category created", {'id': result.get('data', result).get('id')})

    elif args.command == 'add-subcategory':
        data = json.loads(args.data)
        result = api.add_file_subcategory(args.id, data)
        format_success("Subcategory created", {'id': result.get('data', result).get('id')})

    elif args.command == 'update':
        data = json.loads(args.data)
        result = api.update_file_category(args.id, data)
        format_success("File category updated", {'id': args.id})

    elif args.command == 'delete':
        api.delete_file_category(args.id)
        format_success("File category deleted", {'id': args.id})

    elif args.command == 'search':
        filters = json.loads(args.filters) if args.filters else None
        result = api.search_file_categories(
            filters=filters,
            limit=args.limit,
            page=args.page
        )
        categories = result.get('data', [])
        total = result.get('pagination', {}).get('total', len(categories))
        format_output(categories, 'file_categories', args.format, total=total)


def handle_accounts(api: PlytixAPI, args) -> None:
    """Handle accounts commands."""
    if args.command == 'list-members':
        filters = json.loads(args.filters) if args.filters else None
        result = api.search_account_memberships(
            filters=filters,
            limit=args.limit,
            page=args.page
        )
        members = result.get('data', [])
        total = result.get('pagination', {}).get('total', len(members))
        format_output(members, 'members', args.format, total=total)

    elif args.command == 'list-credentials':
        filters = json.loads(args.filters) if args.filters else None
        result = api.search_api_credentials(
            filters=filters,
            limit=args.limit,
            page=args.page
        )
        credentials = result.get('data', [])
        total = result.get('pagination', {}).get('total', len(credentials))
        format_output(credentials, 'credentials', args.format, total=total)


def handle_filters(api: PlytixAPI, args) -> None:
    """Handle available filters commands."""
    if args.command == 'products':
        result = api.get_product_filters()
        filters = result.get('data', result)
        format_output(filters, 'filters', args.format)

    elif args.command == 'assets':
        result = api.get_asset_filters()
        filters = result.get('data', result)
        format_output(filters, 'filters', args.format)

    elif args.command == 'relationships':
        result = api.get_relationship_filters()
        filters = result.get('data', result)
        format_output(filters, 'filters', args.format)


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

    # attributes update-group
    attr_update_group = attributes_sub.add_parser('update-group', help='Update attribute group')
    attr_update_group.add_argument('id', help='Group ID')
    attr_update_group.add_argument('--data', '-d', required=True, help='Update JSON data')

    # attributes delete-group
    attr_delete_group = attributes_sub.add_parser('delete-group', help='Delete attribute group')
    attr_delete_group.add_argument('id', help='Group ID')

    # =========================================================================
    # PRODUCT FAMILIES
    # =========================================================================
    families = subparsers.add_parser('families', help='Product family operations')
    families_sub = families.add_subparsers(dest='command')

    # families list
    f_list = families_sub.add_parser('list', help='List product families')
    f_list.add_argument('--limit', '-l', type=int, default=50)
    f_list.add_argument('--page', '-p', type=int, default=1)

    # families get
    f_get = families_sub.add_parser('get', help='Get product family by ID')
    f_get.add_argument('id', help='Family ID')

    # families create
    f_create = families_sub.add_parser('create', help='Create product family')
    f_create.add_argument('--data', '-d', required=True, help='Family JSON data')

    # families update
    f_update = families_sub.add_parser('update', help='Update product family')
    f_update.add_argument('id', help='Family ID')
    f_update.add_argument('--data', '-d', required=True, help='Update JSON data')

    # families delete
    f_delete = families_sub.add_parser('delete', help='Delete product family')
    f_delete.add_argument('id', help='Family ID')

    # families search
    f_search = families_sub.add_parser('search', help='Search product families')
    f_search.add_argument('--filters', help='Search filters JSON')
    f_search.add_argument('--limit', '-l', type=int, default=50)
    f_search.add_argument('--page', '-p', type=int, default=1)

    # families link-attributes
    f_link = families_sub.add_parser('link-attributes', help='Link attributes to family')
    f_link.add_argument('id', help='Family ID')
    f_link.add_argument('--attribute-ids', required=True, help='Comma-separated attribute IDs')

    # families unlink-attributes
    f_unlink = families_sub.add_parser('unlink-attributes', help='Unlink attributes from family')
    f_unlink.add_argument('id', help='Family ID')
    f_unlink.add_argument('--attribute-ids', required=True, help='Comma-separated attribute IDs')

    # families get-attributes
    f_attrs = families_sub.add_parser('get-attributes', help='Get family attributes')
    f_attrs.add_argument('id', help='Family ID')

    # families get-all-attributes
    f_all_attrs = families_sub.add_parser('get-all-attributes', help='Get all family attributes (including inherited)')
    f_all_attrs.add_argument('id', help='Family ID')

    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    relationships = subparsers.add_parser('relationships', help='Relationship operations')
    relationships_sub = relationships.add_subparsers(dest='command')

    # relationships list
    r_list = relationships_sub.add_parser('list', help='List relationships')
    r_list.add_argument('--limit', '-l', type=int, default=50)
    r_list.add_argument('--page', '-p', type=int, default=1)

    # relationships get
    r_get = relationships_sub.add_parser('get', help='Get relationship by ID')
    r_get.add_argument('id', help='Relationship ID')

    # relationships create
    r_create = relationships_sub.add_parser('create', help='Create relationship')
    r_create.add_argument('--data', '-d', required=True, help='Relationship JSON data')

    # relationships update
    r_update = relationships_sub.add_parser('update', help='Update relationship')
    r_update.add_argument('id', help='Relationship ID')
    r_update.add_argument('--data', '-d', required=True, help='Update JSON data')

    # relationships delete
    r_delete = relationships_sub.add_parser('delete', help='Delete relationship')
    r_delete.add_argument('id', help='Relationship ID')

    # relationships search
    r_search = relationships_sub.add_parser('search', help='Search relationships')
    r_search.add_argument('--filters', help='Search filters JSON')
    r_search.add_argument('--limit', '-l', type=int, default=50)
    r_search.add_argument('--page', '-p', type=int, default=1)

    # =========================================================================
    # FILE CATEGORIES
    # =========================================================================
    file_cats = subparsers.add_parser('file-categories', help='File/asset category operations')
    file_cats_sub = file_cats.add_subparsers(dest='command')

    # file-categories list
    fc_list = file_cats_sub.add_parser('list', help='List file categories')
    fc_list.add_argument('--limit', '-l', type=int, default=50)
    fc_list.add_argument('--page', '-p', type=int, default=1)

    # file-categories create
    fc_create = file_cats_sub.add_parser('create', help='Create file category')
    fc_create.add_argument('--data', '-d', required=True, help='Category JSON data')

    # file-categories add-subcategory
    fc_sub = file_cats_sub.add_parser('add-subcategory', help='Add subcategory to file category')
    fc_sub.add_argument('id', help='Parent category ID')
    fc_sub.add_argument('--data', '-d', required=True, help='Subcategory JSON data')

    # file-categories update
    fc_update = file_cats_sub.add_parser('update', help='Update file category')
    fc_update.add_argument('id', help='Category ID')
    fc_update.add_argument('--data', '-d', required=True, help='Update JSON data')

    # file-categories delete
    fc_delete = file_cats_sub.add_parser('delete', help='Delete file category')
    fc_delete.add_argument('id', help='Category ID')

    # file-categories search
    fc_search = file_cats_sub.add_parser('search', help='Search file categories')
    fc_search.add_argument('--filters', help='Search filters JSON')
    fc_search.add_argument('--limit', '-l', type=int, default=50)
    fc_search.add_argument('--page', '-p', type=int, default=1)

    # =========================================================================
    # ACCOUNTS
    # =========================================================================
    accounts = subparsers.add_parser('accounts', help='Account operations')
    accounts_sub = accounts.add_subparsers(dest='command')

    # accounts list-members
    acc_members = accounts_sub.add_parser('list-members', help='List account memberships')
    acc_members.add_argument('--filters', help='Search filters JSON')
    acc_members.add_argument('--limit', '-l', type=int, default=50)
    acc_members.add_argument('--page', '-p', type=int, default=1)

    # accounts list-credentials
    acc_creds = accounts_sub.add_parser('list-credentials', help='List API credentials')
    acc_creds.add_argument('--filters', help='Search filters JSON')
    acc_creds.add_argument('--limit', '-l', type=int, default=50)
    acc_creds.add_argument('--page', '-p', type=int, default=1)

    # =========================================================================
    # AVAILABLE FILTERS
    # =========================================================================
    filters_cmd = subparsers.add_parser('filters', help='Get available filter fields')
    filters_sub = filters_cmd.add_subparsers(dest='command')

    # filters products
    filters_sub.add_parser('products', help='Get available product filter fields')

    # filters assets
    filters_sub.add_parser('assets', help='Get available asset filter fields')

    # filters relationships
    filters_sub.add_parser('relationships', help='Get available relationship filter fields')

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
            'families': handle_families,
            'relationships': handle_relationships,
            'file-categories': handle_file_categories,
            'accounts': handle_accounts,
            'filters': handle_filters,
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
