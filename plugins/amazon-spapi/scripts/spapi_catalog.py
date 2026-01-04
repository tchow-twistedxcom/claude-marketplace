#!/usr/bin/env python3
"""
Amazon SP-API Catalog & Listings API Module

Provides classes for catalog search, product information retrieval,
listings management, and product type definitions.
"""

import json
import sys
from typing import Optional, Dict, Any, List

from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient


class CatalogItemsAPI:
    """Catalog Items API for searching and retrieving product information."""

    def __init__(self, client: SPAPIClient):
        self.client = client
        self.auth = client.auth

    def search_catalog_items(
        self,
        keywords: Optional[List[str]] = None,
        marketplace_ids: Optional[List[str]] = None,
        included_data: Optional[List[str]] = None,
        brand_names: Optional[List[str]] = None,
        classification_ids: Optional[List[str]] = None,
        page_size: int = 20,
        page_token: Optional[str] = None,
        keywords_locale: Optional[str] = None,
        locale: Optional[str] = None,
        sellers: Optional[List[str]] = None,
        identifiers: Optional[List[str]] = None,
        identifiers_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search the Amazon catalog for items.

        Args:
            keywords: List of keywords to search
            marketplace_ids: List of marketplace IDs (defaults to configured)
            included_data: Data to include (summaries, identifiers, images,
                          productTypes, salesRanks, variations, attributes,
                          dimensions, relationships)
            brand_names: Filter by brand names
            classification_ids: Filter by browse node IDs
            page_size: Results per page (1-20)
            page_token: Pagination token
            keywords_locale: Locale for keywords
            locale: Locale for results
            sellers: Filter by seller IDs
            identifiers: ASINs, UPCs, EANs, etc.
            identifiers_type: Type of identifiers (ASIN, UPC, EAN, ISBN)

        Returns:
            Search results with items and pagination
        """
        if marketplace_ids is None:
            marketplace_ids = [self.auth.get_marketplace_id()]

        params = {
            "marketplaceIds": ",".join(marketplace_ids),
            "pageSize": str(page_size)
        }

        if keywords:
            params["keywords"] = ",".join(keywords)
        if included_data:
            params["includedData"] = ",".join(included_data)
        if brand_names:
            params["brandNames"] = ",".join(brand_names)
        if classification_ids:
            params["classificationIds"] = ",".join(classification_ids)
        if page_token:
            params["pageToken"] = page_token
        if keywords_locale:
            params["keywordsLocale"] = keywords_locale
        if locale:
            params["locale"] = locale
        if sellers:
            params["sellerId"] = ",".join(sellers)
        if identifiers:
            params["identifiers"] = ",".join(identifiers)
        if identifiers_type:
            params["identifiersType"] = identifiers_type

        status, data = self.client.get(
            "/catalog/2022-04-01/items",
            "catalogItems",
            params=params
        )
        return data

    def get_catalog_item(
        self,
        asin: str,
        marketplace_ids: Optional[List[str]] = None,
        included_data: Optional[List[str]] = None,
        locale: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get details for a specific catalog item.

        Args:
            asin: Amazon Standard Identification Number
            marketplace_ids: List of marketplace IDs
            included_data: Data sections to include
            locale: Locale for results

        Returns:
            Catalog item details
        """
        if marketplace_ids is None:
            marketplace_ids = [self.auth.get_marketplace_id()]

        params = {
            "marketplaceIds": ",".join(marketplace_ids)
        }

        if included_data:
            params["includedData"] = ",".join(included_data)
        if locale:
            params["locale"] = locale

        status, data = self.client.get(
            f"/catalog/2022-04-01/items/{asin}",
            "catalogItems",
            params=params
        )
        return data


class ListingsItemsAPI:
    """Listings Items API for managing seller listings."""

    def __init__(self, client: SPAPIClient):
        self.client = client
        self.auth = client.auth

    def get_listings_item(
        self,
        seller_id: str,
        sku: str,
        marketplace_ids: Optional[List[str]] = None,
        issue_locale: Optional[str] = None,
        included_data: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get a listings item.

        Args:
            seller_id: Seller identifier
            sku: Stock Keeping Unit
            marketplace_ids: List of marketplace IDs
            issue_locale: Locale for issue messages
            included_data: Data to include (summaries, attributes, issues,
                          offers, fulfillmentAvailability, procurement)

        Returns:
            Listings item details
        """
        if marketplace_ids is None:
            marketplace_ids = [self.auth.get_marketplace_id()]

        params = {
            "marketplaceIds": ",".join(marketplace_ids)
        }

        if issue_locale:
            params["issueLocale"] = issue_locale
        if included_data:
            params["includedData"] = ",".join(included_data)

        status, data = self.client.get(
            f"/listings/2021-08-01/items/{seller_id}/{sku}",
            "listingsItems",
            params=params
        )
        return data

    def put_listings_item(
        self,
        seller_id: str,
        sku: str,
        marketplace_ids: List[str],
        product_type: str,
        attributes: Dict[str, Any],
        requirements: Optional[str] = None,
        issue_locale: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create or update a listings item.

        Args:
            seller_id: Seller identifier
            sku: Stock Keeping Unit
            marketplace_ids: List of marketplace IDs
            product_type: Amazon product type
            attributes: Product attributes per schema
            requirements: LISTING or LISTING_OFFER_ONLY
            issue_locale: Locale for issue messages

        Returns:
            Submission result with status and issues
        """
        params = {
            "marketplaceIds": ",".join(marketplace_ids)
        }

        if issue_locale:
            params["issueLocale"] = issue_locale

        data = {
            "productType": product_type,
            "requirements": requirements or "LISTING",
            "attributes": attributes
        }

        status, response = self.client.put(
            f"/listings/2021-08-01/items/{seller_id}/{sku}",
            "listingsItems",
            params=params,
            data=data
        )
        return response

    def patch_listings_item(
        self,
        seller_id: str,
        sku: str,
        marketplace_ids: List[str],
        product_type: str,
        patches: List[Dict[str, Any]],
        issue_locale: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Partially update a listings item.

        Args:
            seller_id: Seller identifier
            sku: Stock Keeping Unit
            marketplace_ids: List of marketplace IDs
            product_type: Amazon product type
            patches: List of JSON Patch operations

        Returns:
            Update result with status and issues
        """
        params = {
            "marketplaceIds": ",".join(marketplace_ids)
        }

        if issue_locale:
            params["issueLocale"] = issue_locale

        data = {
            "productType": product_type,
            "patches": patches
        }

        status, response = self.client.patch(
            f"/listings/2021-08-01/items/{seller_id}/{sku}",
            "listingsItems",
            params=params,
            data=data
        )
        return response

    def delete_listings_item(
        self,
        seller_id: str,
        sku: str,
        marketplace_ids: List[str],
        issue_locale: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete a listings item.

        Args:
            seller_id: Seller identifier
            sku: Stock Keeping Unit
            marketplace_ids: List of marketplace IDs
            issue_locale: Locale for issue messages

        Returns:
            Deletion result
        """
        params = {
            "marketplaceIds": ",".join(marketplace_ids)
        }

        if issue_locale:
            params["issueLocale"] = issue_locale

        status, response = self.client.delete(
            f"/listings/2021-08-01/items/{seller_id}/{sku}",
            "listingsItems",
            params=params
        )
        return response


class ProductTypeDefinitionsAPI:
    """Product Type Definitions API for schema information."""

    def __init__(self, client: SPAPIClient):
        self.client = client
        self.auth = client.auth

    def search_definitions_product_types(
        self,
        keywords: Optional[List[str]] = None,
        marketplace_ids: Optional[List[str]] = None,
        item_name: Optional[str] = None,
        locale: Optional[str] = None,
        search_locale: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for product types.

        Args:
            keywords: Keywords to search
            marketplace_ids: List of marketplace IDs
            item_name: Item name to match
            locale: Locale for results
            search_locale: Locale for search keywords

        Returns:
            List of matching product types
        """
        if marketplace_ids is None:
            marketplace_ids = [self.auth.get_marketplace_id()]

        params = {
            "marketplaceIds": ",".join(marketplace_ids)
        }

        if keywords:
            params["keywords"] = ",".join(keywords)
        if item_name:
            params["itemName"] = item_name
        if locale:
            params["locale"] = locale
        if search_locale:
            params["searchLocale"] = search_locale

        status, data = self.client.get(
            "/definitions/2020-09-01/productTypes",
            "productTypeDefinitions",
            params=params
        )
        return data

    def get_definitions_product_type(
        self,
        product_type: str,
        marketplace_ids: Optional[List[str]] = None,
        seller_id: Optional[str] = None,
        product_type_version: str = "LATEST",
        requirements: str = "LISTING",
        requirements_enforced: str = "ENFORCED",
        locale: str = "DEFAULT"
    ) -> Dict[str, Any]:
        """
        Get product type definition/schema.

        Args:
            product_type: Amazon product type name
            marketplace_ids: List of marketplace IDs
            seller_id: Seller identifier for specific requirements
            product_type_version: Version (LATEST or specific)
            requirements: LISTING, LISTING_PRODUCT_ONLY, LISTING_OFFER_ONLY
            requirements_enforced: ENFORCED or NOT_ENFORCED
            locale: Locale for schema labels

        Returns:
            Product type schema with JSON Schema definition
        """
        if marketplace_ids is None:
            marketplace_ids = [self.auth.get_marketplace_id()]

        params = {
            "marketplaceIds": ",".join(marketplace_ids),
            "productTypeVersion": product_type_version,
            "requirements": requirements,
            "requirementsEnforced": requirements_enforced,
            "locale": locale
        }

        if seller_id:
            params["sellerId"] = seller_id

        status, data = self.client.get(
            f"/definitions/2020-09-01/productTypes/{product_type}",
            "productTypeDefinitions",
            params=params
        )
        return data


# Included data options
CATALOG_INCLUDED_DATA = [
    "attributes",
    "dimensions",
    "identifiers",
    "images",
    "productTypes",
    "relationships",
    "salesRanks",
    "summaries",
    "variations"
]

LISTINGS_INCLUDED_DATA = [
    "attributes",
    "fulfillmentAvailability",
    "issues",
    "offers",
    "procurement",
    "summaries"
]


# Helper functions
def search_by_asin(client: SPAPIClient, asin: str) -> Dict[str, Any]:
    """
    Get full catalog item details by ASIN.

    Args:
        client: SPAPIClient instance
        asin: Amazon Standard Identification Number

    Returns:
        Catalog item with all data
    """
    api = CatalogItemsAPI(client)
    return api.get_catalog_item(
        asin=asin,
        included_data=CATALOG_INCLUDED_DATA
    )


def search_by_keywords(
    client: SPAPIClient,
    keywords: List[str],
    max_results: int = 20
) -> List[Dict[str, Any]]:
    """
    Search catalog by keywords.

    Args:
        client: SPAPIClient instance
        keywords: Search keywords
        max_results: Maximum results to return

    Returns:
        List of matching catalog items
    """
    api = CatalogItemsAPI(client)
    result = api.search_catalog_items(
        keywords=keywords,
        included_data=["summaries", "images", "productTypes"],
        page_size=min(max_results, 20)
    )
    return result.get("items", [])


def get_listing(client: SPAPIClient, seller_id: str, sku: str) -> Dict[str, Any]:
    """
    Get listing details.

    Args:
        client: SPAPIClient instance
        seller_id: Seller identifier
        sku: Stock Keeping Unit

    Returns:
        Listing item with all data
    """
    api = ListingsItemsAPI(client)
    return api.get_listings_item(
        seller_id=seller_id,
        sku=sku,
        included_data=LISTINGS_INCLUDED_DATA
    )


def create_listing(
    client: SPAPIClient,
    seller_id: str,
    sku: str,
    product_type: str,
    attributes: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a new listing.

    Args:
        client: SPAPIClient instance
        seller_id: Seller identifier
        sku: Stock Keeping Unit
        product_type: Amazon product type
        attributes: Product attributes

    Returns:
        Creation result
    """
    api = ListingsItemsAPI(client)
    return api.put_listings_item(
        seller_id=seller_id,
        sku=sku,
        marketplace_ids=[client.auth.get_marketplace_id()],
        product_type=product_type,
        attributes=attributes
    )


def update_listing_price(
    client: SPAPIClient,
    seller_id: str,
    sku: str,
    product_type: str,
    price: float,
    currency: str = "USD"
) -> Dict[str, Any]:
    """
    Update listing price using patch.

    Args:
        client: SPAPIClient instance
        seller_id: Seller identifier
        sku: Stock Keeping Unit
        product_type: Amazon product type
        price: New price
        currency: Currency code

    Returns:
        Update result
    """
    api = ListingsItemsAPI(client)
    patches = [
        {
            "op": "replace",
            "path": "/attributes/purchasable_offer",
            "value": [{
                "currency": currency,
                "our_price": [{
                    "schedule": [{
                        "value_with_tax": price
                    }]
                }]
            }]
        }
    ]

    return api.patch_listings_item(
        seller_id=seller_id,
        sku=sku,
        marketplace_ids=[client.auth.get_marketplace_id()],
        product_type=product_type,
        patches=patches
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SP-API Catalog & Listings Operations")
    parser.add_argument("command", choices=["search", "get", "listing", "product-type"],
                        help="Operation to perform")
    parser.add_argument("--keywords", help="Search keywords (comma-separated)")
    parser.add_argument("--asin", help="Amazon ASIN")
    parser.add_argument("--sku", help="Seller SKU")
    parser.add_argument("--seller-id", help="Seller ID")
    parser.add_argument("--product-type", help="Product type name")
    parser.add_argument("--profile", default="production", help="Config profile")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    auth = SPAPIAuth(profile=args.profile)
    client = SPAPIClient(auth)

    try:
        if args.command == "search":
            if not args.keywords:
                print("Error: --keywords required", file=sys.stderr)
                sys.exit(1)
            keywords = args.keywords.split(",")
            result = search_by_keywords(client, keywords)

        elif args.command == "get":
            if not args.asin:
                print("Error: --asin required", file=sys.stderr)
                sys.exit(1)
            result = search_by_asin(client, args.asin)

        elif args.command == "listing":
            if not args.seller_id or not args.sku:
                print("Error: --seller-id and --sku required", file=sys.stderr)
                sys.exit(1)
            result = get_listing(client, args.seller_id, args.sku)

        elif args.command == "product-type":
            if not args.product_type:
                print("Error: --product-type required", file=sys.stderr)
                sys.exit(1)
            api = ProductTypeDefinitionsAPI(client)
            result = api.get_definitions_product_type(args.product_type)

        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            if isinstance(result, list):
                print(f"Found {len(result)} items:")
                for item in result[:10]:
                    asin = item.get("asin", "N/A")
                    title = "N/A"
                    summaries = item.get("summaries", [])
                    if summaries:
                        title = summaries[0].get("itemName", "N/A")[:50]
                    print(f"  {asin} - {title}")
            else:
                print(json.dumps(result, indent=2, default=str))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
