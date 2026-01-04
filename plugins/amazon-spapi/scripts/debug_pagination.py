#!/usr/bin/env python3
"""
Debug script to test SP-API Catalog pagination behavior.
"""

import json
import sys
from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient
from spapi_catalog import CatalogItemsAPI


def test_pagination(brand_name: str, max_pages: int = 60):
    """Test pagination and log every response."""
    auth = SPAPIAuth(profile="production")
    client = SPAPIClient(auth)
    api = CatalogItemsAPI(client)

    page_num = 0
    page_token = None
    total_items = 0

    print(f"\n{'='*60}")
    print(f"Testing pagination for brand: {brand_name}")
    print(f"{'='*60}\n")

    while page_num < max_pages:
        page_num += 1

        try:
            result = api.search_catalog_items(
                keywords=[brand_name],
                brand_names=[brand_name],
                included_data=["identifiers"],
                page_size=20,
                page_token=page_token,
            )

            items = result.get("items", [])
            total_items += len(items)

            # Get pagination info
            pagination = result.get("pagination", {})
            next_token = pagination.get("nextToken")
            prev_token = pagination.get("previousToken")

            # Get numberOfResults from first page
            number_of_results = result.get("numberOfResults")

            # Get refinements
            refinements = result.get("refinements", {})
            brands = refinements.get("brands", [])
            classifications = refinements.get("classifications", [])

            print(f"Page {page_num}:")
            print(f"  Items on page: {len(items)}")
            print(f"  Total so far: {total_items}")
            if number_of_results:
                print(f"  numberOfResults (from API): {number_of_results}")
            print(f"  hasNextToken: {bool(next_token)}")
            print(f"  hasPrevToken: {bool(prev_token)}")

            if page_num == 1:
                print(f"\n  Refinements available:")
                print(f"    Brands: {len(brands)}")
                for b in brands[:5]:
                    print(f"      - {b.get('brandName')}: {b.get('numberOfResults')} products")
                print(f"    Classifications: {len(classifications)}")
                for c in classifications[:5]:
                    print(f"      - {c.get('displayName')}: {c.get('numberOfResults')} products")
                print()

            if not next_token:
                print(f"\n*** PAGINATION STOPPED at page {page_num} ***")
                print(f"Total items retrieved: {total_items}")
                break

            page_token = next_token

        except Exception as e:
            print(f"Error on page {page_num}: {e}")
            break

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Pages retrieved: {page_num}")
    print(f"  Total items: {total_items}")
    print(f"{'='*60}\n")

    return total_items


def test_with_classification(brand_name: str, classification_id: str, max_pages: int = 60):
    """Test pagination within a specific classification/category."""
    auth = SPAPIAuth(profile="production")
    client = SPAPIClient(auth)
    api = CatalogItemsAPI(client)

    page_num = 0
    page_token = None
    total_items = 0

    print(f"\n{'='*60}")
    print(f"Testing pagination with classification: {classification_id}")
    print(f"{'='*60}\n")

    while page_num < max_pages:
        page_num += 1

        try:
            result = api.search_catalog_items(
                keywords=[brand_name],
                brand_names=[brand_name],
                classification_ids=[classification_id],
                included_data=["identifiers"],
                page_size=20,
                page_token=page_token,
            )

            items = result.get("items", [])
            total_items += len(items)

            # Get pagination info
            pagination = result.get("pagination", {})
            next_token = pagination.get("nextToken")

            number_of_results = result.get("numberOfResults")

            print(f"Page {page_num}: {len(items)} items (total: {total_items}), "
                  f"numberOfResults: {number_of_results}, hasNext: {bool(next_token)}")

            if not next_token:
                print(f"\n*** PAGINATION STOPPED at page {page_num} ***")
                break

            page_token = next_token

        except Exception as e:
            print(f"Error on page {page_num}: {e}")
            break

    return total_items


if __name__ == "__main__":
    brand = sys.argv[1] if len(sys.argv) > 1 else "Twisted X"

    # Test without classification
    total = test_pagination(brand)

    # If we hit the limit, try with a classification
    if total >= 990:
        print("\nHit ~1000 limit. Testing with classification filter...")
        # First get classifications
        auth = SPAPIAuth(profile="production")
        client = SPAPIClient(auth)
        api = CatalogItemsAPI(client)

        result = api.search_catalog_items(
            keywords=[brand],
            brand_names=[brand],
            included_data=["summaries"],
            page_size=1,
        )

        classifications = result.get("refinements", {}).get("classifications", [])
        if classifications:
            # Test with largest classification
            largest = classifications[0]
            print(f"\nTesting with largest classification: {largest.get('displayName')}")
            print(f"Expected items: {largest.get('numberOfResults')}")

            test_with_classification(brand, largest.get("classificationId"))
