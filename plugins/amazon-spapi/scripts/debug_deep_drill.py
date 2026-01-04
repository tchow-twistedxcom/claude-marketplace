#!/usr/bin/env python3
"""
Drill deep into problematic classifications to find usable sub-categories.
"""

import sys
from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient
from spapi_catalog import CatalogItemsAPI


def get_sub_classifications(api, brand_name: str, classification_id: str):
    """Get sub-classifications within a classification."""
    result = api.search_catalog_items(
        keywords=[brand_name],
        brand_names=[brand_name],
        classification_ids=[classification_id],
        included_data=["summaries"],
        page_size=1,
    )
    return result.get("refinements", {}).get("classifications", [])


def drill_until_usable(api, brand_name: str, classification_id: str, name: str, depth: int = 0, max_depth: int = 5):
    """Recursively drill down until all classifications are usable (<1000 items)."""
    indent = "  " * depth
    usable = []

    subs = get_sub_classifications(api, brand_name, classification_id)

    if not subs:
        # No more sub-classifications - this is a leaf
        # Get the count for this node
        result = api.search_catalog_items(
            keywords=[brand_name],
            brand_names=[brand_name],
            classification_ids=[classification_id],
            included_data=["identifiers"],
            page_size=1,
        )
        count = result.get("numberOfResults", 0)
        return [{
            "name": name,
            "id": classification_id,
            "count": count,
            "is_leaf": True
        }]

    for sub in subs:
        sub_name = sub.get("displayName")
        sub_count = sub.get("numberOfResults")
        sub_id = sub.get("classificationId")
        full_name = f"{name} > {sub_name}"

        print(f"{indent}📁 {sub_name}: {sub_count} products")

        if sub_count <= 1000:
            usable.append({
                "name": full_name,
                "id": sub_id,
                "count": sub_count
            })
        elif depth < max_depth:
            # Drill deeper
            sub_usable = drill_until_usable(api, brand_name, sub_id, full_name, depth + 1, max_depth)
            usable.extend(sub_usable)
        else:
            # Hit max depth, return as-is
            usable.append({
                "name": full_name,
                "id": sub_id,
                "count": sub_count,
                "warning": f"Exceeds 1000, at max depth {max_depth}"
            })

    return usable


def main():
    brand_name = sys.argv[1] if len(sys.argv) > 1 else "Twisted X"

    auth = SPAPIAuth(profile="production")
    client = SPAPIClient(auth)
    api = CatalogItemsAPI(client)

    # The 4 problematic classifications
    problematic = [
        ("Men > Shoes", "679255011"),
        ("Men > Shops", "7581669011"),
        ("Women > Shoes", "679337011"),
        ("Uniforms, Work & Safety > Shoes", "7586145011"),
    ]

    all_usable = []

    for name, class_id in problematic:
        print(f"\n{'='*60}")
        print(f"Drilling into: {name}")
        print(f"{'='*60}\n")

        usable = drill_until_usable(api, brand_name, class_id, name)
        all_usable.extend(usable)

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary - All Classifications After Deep Drill:")
    print(f"{'='*60}\n")

    total = 0
    usable_count = 0
    still_problematic = []

    for item in all_usable:
        count = item["count"]
        total += count
        if count <= 1000:
            usable_count += 1
            print(f"✅ {item['name']}: {count}")
        else:
            still_problematic.append(item)
            print(f"⚠️  {item['name']}: {count} (STILL EXCEEDS 1000)")

    print(f"\n  Total usable classifications: {usable_count}/{len(all_usable)}")
    print(f"  Total products in these: {total}")

    if still_problematic:
        print(f"\n  ⚠️ Still problematic: {len(still_problematic)}")
        for p in still_problematic:
            print(f"    - {p['name']}: {p['count']}")


if __name__ == "__main__":
    main()
