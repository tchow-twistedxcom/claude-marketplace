#!/usr/bin/env python3
"""
Debug script to explore sub-classifications within a main category.
"""

import sys
from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient
from spapi_catalog import CatalogItemsAPI


def get_sub_classifications(brand_name: str, parent_classification_id: str):
    """Get sub-classifications within a parent classification."""
    auth = SPAPIAuth(profile="production")
    client = SPAPIClient(auth)
    api = CatalogItemsAPI(client)

    # Search within the parent classification to get its refinements
    result = api.search_catalog_items(
        keywords=[brand_name],
        brand_names=[brand_name],
        classification_ids=[parent_classification_id],
        included_data=["summaries"],
        page_size=1,
    )

    refinements = result.get("refinements", {})
    classifications = refinements.get("classifications", [])

    print(f"\nSub-classifications within {parent_classification_id}:")
    print(f"  Total: {len(classifications)}")
    for c in classifications:
        print(f"  - {c.get('displayName')}: {c.get('numberOfResults')} products (id: {c.get('classificationId')})")

    return classifications


def explore_all_classifications(brand_name: str, max_depth: int = 2):
    """Explore classifications recursively."""
    auth = SPAPIAuth(profile="production")
    client = SPAPIClient(auth)
    api = CatalogItemsAPI(client)

    # Get top-level classifications
    result = api.search_catalog_items(
        keywords=[brand_name],
        brand_names=[brand_name],
        included_data=["summaries"],
        page_size=1,
    )

    refinements = result.get("refinements", {})
    top_classifications = refinements.get("classifications", [])

    print(f"\n{'='*60}")
    print(f"Classification Tree for: {brand_name}")
    print(f"{'='*60}\n")

    all_leaf_classifications = []

    for top_class in top_classifications:
        name = top_class.get("displayName")
        count = top_class.get("numberOfResults")
        class_id = top_class.get("classificationId")
        print(f"📁 {name}: {count} products")

        # Get sub-classifications
        sub_classes = get_sub_classifications(brand_name, class_id)

        if sub_classes:
            for sub in sub_classes:
                sub_name = sub.get("displayName")
                sub_count = sub.get("numberOfResults")
                sub_id = sub.get("classificationId")
                print(f"  └── 📁 {sub_name}: {sub_count} products")

                # Check if this is small enough (<1000) or needs further subdivision
                if sub_count <= 1000:
                    all_leaf_classifications.append({
                        "name": f"{name} > {sub_name}",
                        "id": sub_id,
                        "count": sub_count
                    })
                elif max_depth > 1:
                    # Try to get more granular classifications
                    sub_sub_classes = get_sub_classifications(brand_name, sub_id)
                    if sub_sub_classes:
                        for sub_sub in sub_sub_classes:
                            ss_name = sub_sub.get("displayName")
                            ss_count = sub_sub.get("numberOfResults")
                            ss_id = sub_sub.get("classificationId")
                            print(f"      └── 📁 {ss_name}: {ss_count} products")
                            all_leaf_classifications.append({
                                "name": f"{name} > {sub_name} > {ss_name}",
                                "id": ss_id,
                                "count": ss_count
                            })
                    else:
                        all_leaf_classifications.append({
                            "name": f"{name} > {sub_name}",
                            "id": sub_id,
                            "count": sub_count,
                            "warning": "Still >1000, no sub-classifications"
                        })
        else:
            # No sub-classifications, use top-level
            all_leaf_classifications.append({
                "name": name,
                "id": class_id,
                "count": count
            })

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary of Leaf Classifications:")
    print(f"{'='*60}")

    total_expected = 0
    usable_count = 0
    problematic = []

    for leaf in all_leaf_classifications:
        count = leaf["count"]
        total_expected += count
        if count <= 1000:
            usable_count += 1
            print(f"  ✅ {leaf['name']}: {count}")
        else:
            problematic.append(leaf)
            print(f"  ⚠️  {leaf['name']}: {count} (EXCEEDS 1000 LIMIT)")

    print(f"\n  Total classifications: {len(all_leaf_classifications)}")
    print(f"  Usable (<1000): {usable_count}")
    print(f"  Problematic (>1000): {len(problematic)}")
    print(f"  Total expected products: {total_expected}")

    return all_leaf_classifications


if __name__ == "__main__":
    brand = sys.argv[1] if len(sys.argv) > 1 else "Twisted X"
    explore_all_classifications(brand, max_depth=2)
