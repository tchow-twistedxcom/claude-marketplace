#!/usr/bin/env python3
"""
Retry Canonical Link Failures
=============================

Retries only the canonical links that failed due to rate limiting.
Uses the canonical_failures.json from a previous sync run.

This script is designed to be run after a sync that experienced rate
limiting during the LINK_CANONICAL phase. It reads the saved failures
and retries each one with appropriate delays to avoid further rate limits.

Usage:
    # Preview what will be retried
    python retry_canonical_failures.py --run-id 20251226_130220 --dry-run

    # Execute the retry
    python retry_canonical_failures.py --run-id 20251226_130220

    # With custom config
    python retry_canonical_failures.py --run-id 20251226_130220 --config my_config.yaml

Features:
    - Reads canonical_failures.json from the specified run
    - Creates both forward (Canonical → Amazon) and reverse (Amazon → Canonical) links
    - Handles rate limits with automatic wait and retry
    - Saves any remaining failures to canonical_failures_remaining.json
    - Safe to run multiple times (idempotent)

Output:
    - Progress messages for each canonical being retried
    - Summary of succeeded/failed counts
    - Remaining failures file if any still fail
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))
plytix_path = Path(__file__).parent.parent.parent / "plytix-skills" / "skills" / "plytix-api" / "scripts"
sys.path.insert(0, str(plytix_path))

from plytix_api import PlytixAPI
from sync.models import SyncConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Rate limit handling
MAX_RETRY_WAIT = 120  # Wait up to 2 minutes for rate limits
DELAY_BETWEEN_OPS = 0.5  # Delay between operations


def load_failures(run_dir: Path) -> list:
    """Load canonical failures from JSON file."""
    failures_file = run_dir / "canonical_failures.json"
    if not failures_file.exists():
        raise FileNotFoundError(f"No failures file found: {failures_file}")

    with open(failures_file) as f:
        return json.load(f)


def get_relationship_id(api: PlytixAPI, relationship_label: str) -> str:
    """Get the relationship ID from its label."""
    result = api.list_relationships(limit=100)
    relationships = result.get("data", [])
    for rel in relationships:
        if rel.get("label") == relationship_label:
            return rel.get("id")
    raise ValueError(f"Relationship '{relationship_label}' not found")


def retry_link(api: PlytixAPI, relationship_id: str, canonical_id: str, amazon_ids: list) -> tuple:
    """
    Retry linking a canonical product to its Amazon products.

    Returns:
        (success: bool, error: str or None)
    """
    try:
        # Forward link: Canonical → Amazon
        api.add_product_relationships(
            product_id=canonical_id,
            relationship_id=relationship_id,
            related_product_ids=amazon_ids,
        )

        # Reverse links: Amazon → Canonical
        for amazon_id in amazon_ids:
            time.sleep(DELAY_BETWEEN_OPS)
            try:
                api.add_product_relationships(
                    product_id=amazon_id,
                    relationship_id=relationship_id,
                    related_product_ids=[canonical_id],
                )
            except Exception as e:
                # Log but continue - reverse links are less critical
                logger.debug(f"Reverse link warning for {amazon_id}: {e}")

        return True, None

    except Exception as e:
        error_str = str(e)

        # Check for rate limit
        if "429" in error_str or "rate" in error_str.lower():
            import re
            match = re.search(r'(\d+)', error_str)
            if match:
                wait_time = int(match.group(1))
                if wait_time <= MAX_RETRY_WAIT:
                    logger.info(f"Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time + 1)
                    # Retry once after waiting
                    return retry_link(api, relationship_id, canonical_id, amazon_ids)
                else:
                    return False, f"Rate limit too long: {wait_time}s"

        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="Retry failed canonical links")
    parser.add_argument("--run-id", required=True, help="Sync run ID to retry failures from")
    parser.add_argument("--config", default="sync_config.yaml", help="Config file path")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    args = parser.parse_args()

    # Load config
    config_path = Path(__file__).parent / args.config
    config = SyncConfig.from_yaml(str(config_path))

    # Load failures
    run_dir = Path(config.data_dir) / args.run_id
    failures = load_failures(run_dir)

    logger.info(f"Loaded {len(failures)} canonical failures to retry")

    if args.dry_run:
        logger.info("DRY RUN - would retry these canonicals:")
        for f in failures[:10]:
            logger.info(f"  {f['canonical_id']} -> {len(f['amazon_product_ids'])} Amazon products")
        if len(failures) > 10:
            logger.info(f"  ... and {len(failures) - 10} more")
        return

    # Initialize API
    api = PlytixAPI()

    # Get relationship ID
    relationship_label = config.amazon_listings_relationship
    logger.info(f"Looking up relationship: {relationship_label}")
    relationship_id = get_relationship_id(api, relationship_label)
    logger.info(f"Found relationship ID: {relationship_id}")

    # Retry each failure
    success_count = 0
    failed_count = 0
    still_failed = []

    for i, failure in enumerate(failures, 1):
        canonical_id = failure["canonical_id"]
        amazon_ids = failure["amazon_product_ids"]

        logger.info(f"[{i}/{len(failures)}] Retrying {canonical_id} with {len(amazon_ids)} Amazon products...")

        time.sleep(DELAY_BETWEEN_OPS)
        success, error = retry_link(api, relationship_id, canonical_id, amazon_ids)

        if success:
            success_count += 1
            logger.info(f"  ✓ Linked successfully")
        else:
            failed_count += 1
            still_failed.append({**failure, "error": error})
            logger.warning(f"  ✗ Failed: {error}")

    # Summary
    logger.info("")
    logger.info("=" * 50)
    logger.info("RETRY COMPLETE")
    logger.info("=" * 50)
    logger.info(f"  Succeeded: {success_count}")
    logger.info(f"  Failed:    {failed_count}")

    # Save remaining failures
    if still_failed:
        remaining_file = run_dir / "canonical_failures_remaining.json"
        with open(remaining_file, "w") as f:
            json.dump(still_failed, f, indent=2)
        logger.info(f"  Remaining failures saved to: {remaining_file}")


if __name__ == "__main__":
    main()
