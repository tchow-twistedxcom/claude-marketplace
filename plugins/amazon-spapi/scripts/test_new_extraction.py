#!/usr/bin/env python3
"""Test the new hierarchical classification extraction."""

import sys
sys.path.insert(0, "sync")

from sync.models import SyncConfig
from sync.extractors.catalog_extractor import CatalogExtractor
import logging

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def test_extraction(brand_name: str, max_results: int = 0):
    """Test the new extraction method."""
    config = SyncConfig()
    extractor = CatalogExtractor(config, profile="production")

    print(f"\n{'='*60}")
    print(f"Testing extraction for: {brand_name}")
    print(f"Max results: {max_results if max_results else 'unlimited'}")
    print(f"{'='*60}\n")

    # Just test ASIN discovery, not full extraction
    asins = extractor._search_brand_by_categories(brand_name, max_results if max_results else float('inf'))

    print(f"\n{'='*60}")
    print(f"Results:")
    print(f"  Total unique ASINs found: {len(asins)}")
    print(f"{'='*60}\n")

    return asins


if __name__ == "__main__":
    brand = sys.argv[1] if len(sys.argv) > 1 else "Twisted X"
    max_res = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    asins = test_extraction(brand, max_res)

    # Show sample ASINs
    print("Sample ASINs (first 20):")
    for asin in asins[:20]:
        print(f"  {asin}")
