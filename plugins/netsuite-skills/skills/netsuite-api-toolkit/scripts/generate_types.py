#!/usr/bin/env python3
"""
Generate TypeScript interfaces from API responses.

Fetches actual API response and generates TypeScript interfaces,
type guards, and optional Zod schemas.

Usage:
    python3 generate_types.py --app homepage --action getOperationsStatus
    python3 generate_types.py --app homepage --action getOperationsStatus --output src/types/operations.generated.ts
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any
import requests

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


def to_pascal_case(name: str) -> str:
    """Convert string to PascalCase for interface names."""
    # Handle camelCase
    words = re.split(r'(?=[A-Z])|[_-]', name)
    return ''.join(word.capitalize() for word in words if word)


def infer_typescript_type(value: Any, key: str = "", depth: int = 0) -> tuple[str, list]:
    """
    Infer TypeScript type from Python value.
    Returns (type_string, list of nested interfaces)
    """
    nested_interfaces = []

    if value is None:
        return "null", nested_interfaces

    if isinstance(value, bool):
        return "boolean", nested_interfaces

    if isinstance(value, int) or isinstance(value, float):
        return "number", nested_interfaces

    if isinstance(value, str):
        # Check if it looks like a date
        if re.match(r'\d{4}-\d{2}-\d{2}', value):
            return "string", nested_interfaces  # Could return Date but string is safer
        return "string", nested_interfaces

    if isinstance(value, list):
        if len(value) == 0:
            return "unknown[]", nested_interfaces

        # Analyze first item
        first_item = value[0]
        inner_type, inner_nested = infer_typescript_type(first_item, key, depth + 1)

        if isinstance(first_item, dict) and key:
            # Create interface for array items
            interface_name = to_pascal_case(key) + "Item"
            interface_def = generate_interface(first_item, interface_name, depth + 1)
            nested_interfaces.append(interface_def)
            nested_interfaces.extend(inner_nested)
            return f"{interface_name}[]", nested_interfaces

        return f"{inner_type}[]", nested_interfaces

    if isinstance(value, dict):
        if key and depth < 2:  # Only create named interfaces for top-level nested objects
            interface_name = to_pascal_case(key)
            interface_def = generate_interface(value, interface_name, depth + 1)
            nested_interfaces.append(interface_def)

            # Get nested interfaces from the dict
            for k, v in value.items():
                _, inner_nested = infer_typescript_type(v, k, depth + 1)
                nested_interfaces.extend(inner_nested)

            return interface_name, nested_interfaces

        # Inline object type for deeper nesting
        fields = []
        for k, v in value.items():
            field_type, _ = infer_typescript_type(v, k, depth + 1)
            fields.append(f"{k}: {field_type}")
        return "{ " + "; ".join(fields) + " }", nested_interfaces

    return "unknown", nested_interfaces


def generate_interface(data: dict, name: str, depth: int = 0) -> str:
    """Generate a TypeScript interface from a dictionary."""
    lines = [f"export interface {name} {{"]

    for key, value in data.items():
        field_type, _ = infer_typescript_type(value, key, depth)

        # Add optional marker if value is null
        optional = "?" if value is None else ""

        # Add comment for sample value
        sample = str(value)[:40] if value is not None else "null"
        if len(str(value)) > 40:
            sample += "..."

        lines.append(f"  {key}{optional}: {field_type};  // e.g., {sample}")

    lines.append("}")
    return "\n".join(lines)


def generate_type_guard(interface_name: str, required_fields: list) -> str:
    """Generate a TypeScript type guard function."""
    checks = " &&\n    ".join([f"'{f}' in obj" for f in required_fields[:5]])  # Limit to 5 checks

    return f'''export function is{interface_name}(obj: unknown): obj is {interface_name} {{
  return (
    obj !== null &&
    typeof obj === 'object' &&
    {checks}
  );
}}'''


def generate_zod_schema(data: dict, name: str) -> str:
    """Generate a Zod schema from a dictionary."""
    lines = [f"export const {name}Schema = z.object({{"]

    for key, value in data.items():
        zod_type = _python_to_zod_type(value)
        lines.append(f"  {key}: {zod_type},")

    lines.append("});")
    lines.append(f"\nexport type {name} = z.infer<typeof {name}Schema>;")

    return "\n".join(lines)


def _python_to_zod_type(value: Any) -> str:
    """Convert Python value to Zod type."""
    if value is None:
        return "z.null()"
    if isinstance(value, bool):
        return "z.boolean()"
    if isinstance(value, int) or isinstance(value, float):
        return "z.number()"
    if isinstance(value, str):
        return "z.string()"
    if isinstance(value, list):
        if len(value) > 0:
            inner = _python_to_zod_type(value[0])
            return f"z.array({inner})"
        return "z.array(z.unknown())"
    if isinstance(value, dict):
        fields = ", ".join([f"{k}: {_python_to_zod_type(v)}" for k, v in value.items()])
        return f"z.object({{ {fields} }})"
    return "z.unknown()"


def generate_full_output(data: dict, base_name: str, include_guards: bool = True, include_zod: bool = False) -> str:
    """Generate complete TypeScript output."""
    timestamp = datetime.now().isoformat()

    output = [
        "/**",
        f" * Auto-generated TypeScript types from API response",
        f" * Generated: {timestamp}",
        f" * Source: {base_name}",
        " *",
        " * WARNING: This file is auto-generated. Do not edit manually.",
        " */",
        ""
    ]

    if include_zod:
        output.append("import { z } from 'zod';")
        output.append("")

    # Collect all interfaces
    all_interfaces = []
    nested_interfaces = []

    # Generate main interface
    main_interface = generate_interface(data, base_name)
    all_interfaces.append(main_interface)

    # Get nested interfaces
    for key, value in data.items():
        _, nested = infer_typescript_type(value, key, 0)
        nested_interfaces.extend(nested)

    # Remove duplicates while preserving order
    seen = set()
    unique_nested = []
    for interface in nested_interfaces:
        # Extract interface name for deduplication
        match = re.match(r'export interface (\w+)', interface)
        if match:
            name = match.group(1)
            if name not in seen:
                seen.add(name)
                unique_nested.append(interface)

    # Add nested interfaces first
    output.extend(unique_nested)
    if unique_nested:
        output.append("")

    # Add main interface
    output.append(main_interface)
    output.append("")

    # Add type guards
    if include_guards:
        required_fields = [k for k, v in data.items() if v is not None]
        guard = generate_type_guard(base_name, required_fields)
        output.append(guard)
        output.append("")

    # Add Zod schema
    if include_zod:
        schema = generate_zod_schema(data, base_name)
        output.append(schema)
        output.append("")

    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(
        description="Generate TypeScript interfaces from API responses"
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
        "--name",
        help="Interface name (default: derived from action)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--no-guards",
        action="store_true",
        help="Don't generate type guards"
    )
    parser.add_argument(
        "--zod",
        action="store_true",
        help="Generate Zod schemas"
    )

    args = parser.parse_args()

    # Fetch API response
    print(f"Fetching API response: {args.app}/{args.action} ({args.env})", file=sys.stderr)
    api_data = fetch_api_response(args.app, args.action, args.env)

    if api_data is None:
        print("\u274C Failed to fetch API response", file=sys.stderr)
        return 1

    # Derive interface name
    if args.name:
        base_name = args.name
    else:
        # Convert action to PascalCase and add "Response"
        action_pascal = to_pascal_case(args.action)
        base_name = f"{action_pascal}Data"

    # Generate output
    output = generate_full_output(
        api_data,
        base_name,
        include_guards=not args.no_guards,
        include_zod=args.zod
    )

    # Write output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"\u2705 Generated types written to: {args.output}", file=sys.stderr)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
