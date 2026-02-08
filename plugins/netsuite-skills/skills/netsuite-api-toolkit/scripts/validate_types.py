#!/usr/bin/env python3
"""
Validate TypeScript interfaces against actual API responses.

Compares TypeScript type definitions with live API responses to detect:
- Missing fields in types
- Extra fields in API response
- Type mismatches
- Nested structure differences

Usage:
    python3 validate_types.py --types-file src/types/operations.ts --app homepage --action getOperationsStatus
"""

import argparse
import json
import re
import sys
import requests
from typing import Any

GATEWAY_URL = "http://localhost:3001"


def fetch_api_response(app: str, action: str, env: str) -> dict | None:
    """Fetch actual API response."""
    try:
        url = f"{GATEWAY_URL}/api/{app}?action={action}"
        headers = {
            "Content-Type": "application/json",
            "X-NetSuite-Environment": env
        }
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            data = response.json()
            if data.get("success") and "data" in data:
                return data["data"]
        return None

    except Exception as e:
        print(f"\u274C Failed to fetch API: {e}")
        return None


def parse_typescript_interfaces(filepath: str) -> dict:
    """Parse TypeScript interfaces from a file."""
    interfaces = {}

    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"\u274C File not found: {filepath}")
        return interfaces

    # Simple regex to extract interface definitions
    # This is a basic parser - won't handle all TypeScript syntax
    interface_pattern = r'export\s+interface\s+(\w+)\s*\{([^}]+)\}'

    for match in re.finditer(interface_pattern, content, re.DOTALL):
        name = match.group(1)
        body = match.group(2)

        fields = {}
        # Parse field definitions
        field_pattern = r'(\w+)(\?)?:\s*([^;]+);'

        for field_match in re.finditer(field_pattern, body):
            field_name = field_match.group(1)
            optional = field_match.group(2) == '?'
            field_type = field_match.group(3).strip()

            fields[field_name] = {
                "type": field_type,
                "optional": optional
            }

        interfaces[name] = fields

    return interfaces


def infer_type(value: Any) -> str:
    """Infer TypeScript type from Python value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) or isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        if len(value) > 0:
            inner = infer_type(value[0])
            return f"{inner}[]"
        return "unknown[]"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def extract_response_structure(data: Any, prefix: str = "") -> dict:
    """Extract field structure from API response."""
    fields = {}

    if isinstance(data, dict):
        for key, value in data.items():
            field_path = f"{prefix}.{key}" if prefix else key
            fields[key] = {
                "type": infer_type(value),
                "value_sample": str(value)[:50] if value is not None else "null",
                "nested": None
            }

            # Recursively extract nested structures
            if isinstance(value, dict):
                fields[key]["nested"] = extract_response_structure(value, field_path)
            elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                fields[key]["nested"] = extract_response_structure(value[0], f"{field_path}[]")

    return fields


def compare_structures(ts_fields: dict, api_fields: dict, interface_name: str) -> dict:
    """Compare TypeScript interface with API response structure."""
    result = {
        "interface": interface_name,
        "matches": [],
        "missing_in_types": [],
        "missing_in_api": [],
        "type_mismatches": []
    }

    ts_keys = set(ts_fields.keys())
    api_keys = set(api_fields.keys())

    # Fields in API but not in TypeScript types
    for key in api_keys - ts_keys:
        result["missing_in_types"].append({
            "field": key,
            "api_type": api_fields[key]["type"],
            "sample": api_fields[key]["value_sample"]
        })

    # Fields in TypeScript but not in API
    for key in ts_keys - api_keys:
        ts_field = ts_fields[key]
        if not ts_field["optional"]:
            result["missing_in_api"].append({
                "field": key,
                "ts_type": ts_field["type"],
                "optional": ts_field["optional"]
            })

    # Fields in both - check types
    for key in ts_keys & api_keys:
        ts_type = ts_fields[key]["type"]
        api_type = api_fields[key]["type"]

        # Simple type comparison (not perfect, but catches obvious mismatches)
        if _types_compatible(ts_type, api_type):
            result["matches"].append(key)
        else:
            result["type_mismatches"].append({
                "field": key,
                "ts_type": ts_type,
                "api_type": api_type
            })

    return result


def _types_compatible(ts_type: str, api_type: str) -> bool:
    """Check if TypeScript type is compatible with inferred API type."""
    # Normalize types
    ts_type = ts_type.lower().replace(" ", "")
    api_type = api_type.lower().replace(" ", "")

    # Direct match
    if ts_type == api_type:
        return True

    # Handle arrays
    if api_type.endswith("[]") and ts_type.endswith("[]"):
        return True

    # Handle optional types
    if "|null" in ts_type or "|undefined" in ts_type:
        base_ts = ts_type.split("|")[0]
        return _types_compatible(base_ts, api_type)

    # Object types are generally compatible with interfaces
    if api_type == "object" and not ts_type.startswith(("string", "number", "boolean")):
        return True

    # Union types
    if "|" in ts_type:
        parts = ts_type.split("|")
        return any(_types_compatible(p.strip(), api_type) for p in parts)

    return False


def print_comparison(result: dict, verbose: bool = False):
    """Print comparison results."""
    print(f"\n{'=' * 70}")
    print(f"TYPE VALIDATION: {result['interface']}")
    print(f"{'=' * 70}")

    # Summary
    total_matches = len(result["matches"])
    total_issues = len(result["missing_in_types"]) + len(result["missing_in_api"]) + len(result["type_mismatches"])

    if total_issues == 0:
        print(f"\u2705 All fields match ({total_matches} fields)")
    else:
        print(f"\u274C Found {total_issues} issue(s)")

    # Missing in types (API has fields that TypeScript doesn't)
    if result["missing_in_types"]:
        print(f"\n\u26A0\uFE0F  Fields in API but NOT in TypeScript ({len(result['missing_in_types'])}):")
        for item in result["missing_in_types"]:
            print(f"   + {item['field']}: {item['api_type']}  (sample: {item['sample']})")

    # Missing in API (TypeScript expects fields that API doesn't return)
    if result["missing_in_api"]:
        print(f"\n\u274C Fields in TypeScript but NOT in API ({len(result['missing_in_api'])}):")
        for item in result["missing_in_api"]:
            opt = " (optional)" if item["optional"] else " (REQUIRED)"
            print(f"   - {item['field']}: {item['ts_type']}{opt}")

    # Type mismatches
    if result["type_mismatches"]:
        print(f"\n\u274C Type mismatches ({len(result['type_mismatches'])}):")
        for item in result["type_mismatches"]:
            print(f"   \u2260 {item['field']}: TS expects '{item['ts_type']}', API returns '{item['api_type']}'")

    # Matches (verbose only)
    if verbose and result["matches"]:
        print(f"\n\u2705 Matching fields ({len(result['matches'])}):")
        for field in sorted(result["matches"]):
            print(f"   \u2713 {field}")


def main():
    parser = argparse.ArgumentParser(
        description="Validate TypeScript interfaces against API responses"
    )
    parser.add_argument(
        "--types-file",
        required=True,
        help="Path to TypeScript types file"
    )
    parser.add_argument(
        "--interface",
        help="Specific interface to validate (default: auto-detect)"
    )
    parser.add_argument(
        "--app",
        default="homepage",
        help="App ID (default: homepage)"
    )
    parser.add_argument(
        "--action",
        default="getOperationsStatus",
        help="API action (default: getOperationsStatus)"
    )
    parser.add_argument(
        "--env",
        default="sandbox2",
        help="Target environment (default: sandbox2)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show all matching fields"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    # Parse TypeScript interfaces
    print(f"Parsing types from: {args.types_file}")
    interfaces = parse_typescript_interfaces(args.types_file)

    if not interfaces:
        print("\u274C No interfaces found in file")
        return 1

    print(f"Found {len(interfaces)} interface(s): {', '.join(interfaces.keys())}")

    # Fetch API response
    print(f"\nFetching API response: {args.app}/{args.action} ({args.env})")
    api_data = fetch_api_response(args.app, args.action, args.env)

    if api_data is None:
        print("\u274C Failed to fetch API response")
        return 1

    # Extract API structure
    api_fields = extract_response_structure(api_data)
    print(f"API response has {len(api_fields)} top-level field(s)")

    # Compare with specified interface or auto-detect
    if args.interface:
        if args.interface not in interfaces:
            print(f"\u274C Interface '{args.interface}' not found")
            return 1
        ts_fields = interfaces[args.interface]
        result = compare_structures(ts_fields, api_fields, args.interface)
        results = [result]
    else:
        # Compare with all interfaces and find best match
        results = []
        for name, ts_fields in interfaces.items():
            result = compare_structures(ts_fields, api_fields, name)
            results.append(result)

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    for result in results:
        print_comparison(result, args.verbose)

    # Return non-zero if any issues found
    total_issues = sum(
        len(r["missing_in_types"]) + len(r["missing_in_api"]) + len(r["type_mismatches"])
        for r in results
    )

    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
