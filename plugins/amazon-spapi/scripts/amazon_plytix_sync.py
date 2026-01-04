#!/usr/bin/env python3
"""
Amazon → Plytix Sync CLI
========================

Production-grade sync tool for syncing Amazon catalog data to Plytix PIM.

Usage:
    # Sync by ASIN list
    python amazon_plytix_sync.py --asins B07X8Z63ZL,B08Y8Z63ZL

    # Sync from file
    python amazon_plytix_sync.py --asin-file asins.txt

    # Sync by brand
    python amazon_plytix_sync.py --brand "Twisted X"

    # Resume interrupted sync
    python amazon_plytix_sync.py --resume 20250101_120000

    # Dry run (no changes)
    python amazon_plytix_sync.py --asin-file asins.txt --dry-run

    # List previous runs
    python amazon_plytix_sync.py --list-runs

    # Verify setup
    python amazon_plytix_sync.py --verify
"""

import argparse
import logging
import sys
from pathlib import Path

# Add sync package to path
sys.path.insert(0, str(Path(__file__).parent))

from sync.models import SyncConfig
from sync.orchestrator import SyncOrchestrator
from sync.state import CheckpointManager


def setup_logging(level: str = "INFO", log_file: str = None):
    """Configure logging."""
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=handlers,
    )

    # Reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def main():
    parser = argparse.ArgumentParser(
        description="Sync Amazon catalog to Plytix PIM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input sources (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--asins",
        help="Comma-separated list of ASINs to sync"
    )
    input_group.add_argument(
        "--asin-file",
        help="Path to file containing ASINs (one per line)"
    )
    input_group.add_argument(
        "--brand",
        help="Brand name to search and sync all products"
    )
    input_group.add_argument(
        "--resume",
        metavar="RUN_ID",
        help="Resume a previous interrupted sync run"
    )

    # Options
    parser.add_argument(
        "--config",
        default="sync_config.yaml",
        help="Path to sync configuration file (default: sync_config.yaml)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying Plytix"
    )
    parser.add_argument(
        "--profile",
        default="production",
        help="SP-API profile name (default: production)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    parser.add_argument(
        "--log-file",
        help="Log to file in addition to console"
    )

    # Phase control
    parser.add_argument(
        "--rerun-phases",
        help="Comma-separated phases to rerun (images,hierarchy,canonical,attributes)"
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Skip extract phase (use existing raw_catalog.json)"
    )

    # Utility commands
    parser.add_argument(
        "--list-runs",
        action="store_true",
        help="List previous sync runs"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify Plytix setup (relationships exist)"
    )
    parser.add_argument(
        "--show-run",
        metavar="RUN_ID",
        help="Show details of a specific sync run"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)

    # Load configuration
    config_path = Path(__file__).parent / args.config
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    try:
        config = SyncConfig.from_yaml(str(config_path))
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    # Handle utility commands
    if args.list_runs:
        runs = CheckpointManager.list_runs(config.data_dir)
        if not runs:
            print("No previous sync runs found.")
        else:
            print("\nPrevious sync runs:")
            print("-" * 60)
            for run in runs:
                stats = run.get("stats", {})
                print(
                    f"  {run['run_id']}  "
                    f"Phase: {run['phase']}  "
                    f"Processed: {stats.get('processed_count', 0)}  "
                    f"Failed: {stats.get('failed_count', 0)}"
                )
            print()
        sys.exit(0)

    if args.verify:
        orchestrator = SyncOrchestrator(
            config=config,
            dry_run=True,
            spapi_profile=args.profile,
        )
        if orchestrator.verify_setup():
            print("✅ Plytix setup verified - all relationships exist")
            sys.exit(0)
        else:
            print("❌ Plytix setup incomplete - see warnings above")
            sys.exit(1)

    if args.show_run:
        checkpoint = CheckpointManager(config.data_dir, args.show_run)
        if not checkpoint.has_checkpoint():
            print(f"Run not found: {args.show_run}")
            sys.exit(1)

        checkpoint.load()
        results_file = checkpoint.get_data_file_path("sync_results.json")

        print(f"\nSync Run: {args.show_run}")
        print("-" * 60)
        print(f"  Phase: {checkpoint.current_phase.name}")
        print(f"  Processed: {len(checkpoint.processed_asins)}")
        print(f"  Pending: {len(checkpoint.pending_asins)}")
        print(f"  Failed: {len(checkpoint.failed_asins)}")

        if results_file.exists():
            import json
            with open(results_file) as f:
                results = json.load(f)
            print(f"\n  Products Created: {results.get('products_created', 0)}")
            print(f"  Products Updated: {results.get('products_updated', 0)}")
            print(f"  Images Uploaded: {results.get('images_uploaded', 0)}")
            print(f"  Hierarchies Linked: {results.get('hierarchies_linked', 0)}")
            print(f"  Canonicals Linked: {results.get('canonicals_linked', 0)}")
        print()
        sys.exit(0)

    # Prepare sync
    asins = None
    if args.asins:
        asins = [a.strip() for a in args.asins.split(",")]

    run_id = args.resume

    # Parse rerun phases
    rerun_phases = None
    if args.rerun_phases:
        rerun_phases = [p.strip().lower() for p in args.rerun_phases.split(",")]

    # Create orchestrator
    orchestrator = SyncOrchestrator(
        config=config,
        run_id=run_id,
        dry_run=args.dry_run,
        spapi_profile=args.profile,
        rerun_phases=rerun_phases,
        skip_extract=args.skip_extract,
    )

    # Print banner
    print()
    print("=" * 60)
    print("Amazon → Plytix Sync")
    print("=" * 60)
    print(f"  Run ID:      {orchestrator.checkpoint.run_id}")
    print(f"  Marketplace: {config.marketplace}")
    print(f"  Dry Run:     {args.dry_run}")

    if asins:
        print(f"  ASINs:       {len(asins)} products")
    elif args.asin_file:
        print(f"  ASIN File:   {args.asin_file}")
    elif args.brand:
        print(f"  Brand:       {args.brand}")
    elif run_id:
        print(f"  Resuming:    {run_id}")
    else:
        print("  Source:      No input specified")
        print()
        parser.print_help()
        sys.exit(1)

    print("=" * 60)
    print()

    # Run sync
    try:
        result = orchestrator.run(
            asins=asins,
            brand=args.brand,
            asin_file=args.asin_file,
        )

        # Print summary
        print()
        print("=" * 60)
        print("SYNC COMPLETE" if result.is_complete else "SYNC INCOMPLETE")
        print("=" * 60)
        print(f"  Duration:       {result.duration_seconds:.1f}s" if result.duration_seconds else "  Duration:       N/A")
        print(f"  Total Items:    {result.total_items}")
        print(f"  Processed:      {result.processed_items}")
        print(f"  Created:        {result.products_created}")
        print(f"  Updated:        {result.products_updated}")
        print(f"  Success Rate:   {result.success_rate * 100:.1f}%")

        if result.errors:
            print(f"  Errors:         {len(result.errors)}")
            for error in result.errors[:5]:
                print(f"    - {error}")

        print()
        print(f"  Results saved to: {orchestrator.checkpoint.get_data_file_path('sync_results.json')}")
        print("=" * 60)
        print()

        sys.exit(0 if result.is_complete else 1)

    except KeyboardInterrupt:
        print("\n\nSync interrupted - checkpoint saved")
        print(f"Resume with: python {sys.argv[0]} --resume {orchestrator.checkpoint.run_id}")
        sys.exit(130)

    except Exception as e:
        logger.exception(f"Sync failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
