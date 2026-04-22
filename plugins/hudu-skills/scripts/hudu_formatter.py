#!/usr/bin/env python3
"""Output formatting for Hudu API results."""

import json
import sys

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

# Column definitions per entity type: (header, key_path)
# key_path supports dot notation for nested fields
COLUMNS = {
    "companies": [
        ("ID", "id"),
        ("Name", "name"),
        ("Phone", "phone_number"),
        ("Website", "website"),
        ("City", "city"),
        ("State", "state"),
        ("Country", "country_name"),
    ],
    "articles": [
        ("ID", "id"),
        ("Name", "name"),
        ("Company ID", "company_id"),
        ("Draft", "draft"),
        ("Enabled", "enable_article"),
        ("Updated", "updated_at"),
    ],
    "assets": [
        ("ID", "id"),
        ("Name", "name"),
        ("Layout ID", "asset_layout_id"),
        ("Company ID", "company_id"),
        ("Archived", "archived"),
        ("Updated", "updated_at"),
    ],
    "asset_layouts": [
        ("ID", "id"),
        ("Name", "name"),
        ("Icon", "icon"),
        ("Color", "color"),
        ("Active", "active"),
        ("Created", "created_at"),
    ],
    "asset_passwords": [
        ("ID", "id"),
        ("Name", "name"),
        ("Company ID", "company_id"),
        ("Username", "username"),
        ("URL", "url"),
        ("Updated", "updated_at"),
    ],
    "procedures": [
        ("ID", "id"),
        ("Name", "name"),
        ("Company ID", "company_id"),
        ("Enabled", "aasm_state"),
        ("Updated", "updated_at"),
    ],
    "websites": [
        ("ID", "id"),
        ("Name", "name"),
        ("Company ID", "company_id"),
        ("URL", "website_url"),
        ("Paused", "paused"),
        ("Updated", "updated_at"),
    ],
    "networks": [
        ("ID", "id"),
        ("Name", "name"),
        ("Company ID", "company_id"),
        ("Address", "address"),
        ("Updated", "updated_at"),
    ],
    "users": [
        ("ID", "id"),
        ("Name", "name"),
        ("Email", "email"),
        ("Role", "role"),
        ("Created", "created_at"),
    ],
    "folders": [
        ("ID", "id"),
        ("Name", "name"),
        ("Company ID", "company_id"),
        ("Parent ID", "parent_folder_id"),
    ],
    "activity_logs": [
        ("ID", "id"),
        ("Action", "action"),
        ("Resource Type", "resource_type"),
        ("Resource ID", "resource_id"),
        ("User", "user_name"),
        ("Created", "created_at"),
    ],
}


def _get_val(record, key):
    val = record.get(key)
    if val is None:
        return ""
    if isinstance(val, bool):
        return "yes" if val else "no"
    return str(val)


def format_output(result, mode="table", entity_type=None):
    if mode == "json":
        print(json.dumps(result, indent=2, default=str))
        return

    if not HAS_TABULATE:
        print("tabulate not installed — falling back to JSON. Run: pip install tabulate", file=sys.stderr)
        print(json.dumps(result, indent=2, default=str))
        return

    if result is None:
        print("No result.")
        return

    # Single record (dict)
    if isinstance(result, dict):
        rows = [(k, v) for k, v in result.items() if not isinstance(v, (dict, list))]
        print(tabulate(rows, tablefmt="simple"))
        return

    # List of records
    if not isinstance(result, list) or len(result) == 0:
        print("No results.")
        return

    cols = COLUMNS.get(entity_type) if entity_type else None
    if cols:
        headers = [h for h, _ in cols]
        keys = [k for _, k in cols]
        rows = [[_get_val(r, k) for k in keys] for r in result]
        print(tabulate(rows, headers=headers, tablefmt="simple"))
    else:
        # Generic: use all scalar keys from first record
        first = result[0]
        keys = [k for k, v in first.items() if not isinstance(v, (dict, list))]
        headers = keys
        rows = [[_get_val(r, k) for k in keys] for r in result]
        print(tabulate(rows, headers=headers, tablefmt="simple"))

    print(f"\n{len(result)} record(s)")
