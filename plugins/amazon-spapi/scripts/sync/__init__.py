"""
Amazon → Plytix Sync Package
============================

Production-grade ETL pipeline for syncing Amazon catalog data to Plytix PIM.

Modules:
    - extractors: SP-API data extraction
    - transformers: Data transformation and canonical matching
    - loaders: Plytix product/asset/relationship loading
    - state: Checkpoint and progress management
    - orchestrator: Main sync coordination
"""

from .models import (
    SyncConfig,
    AmazonProduct,
    PlytixProduct,
    CanonicalMatch,
    SyncResult,
    SyncPhase,
    SyncStatus,
)

__version__ = "1.0.0"
__all__ = [
    "SyncConfig",
    "AmazonProduct",
    "PlytixProduct",
    "CanonicalMatch",
    "SyncResult",
    "SyncPhase",
    "SyncStatus",
]
