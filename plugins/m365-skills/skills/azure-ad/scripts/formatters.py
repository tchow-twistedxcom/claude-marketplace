#!/usr/bin/env python3
"""
Output formatters for Azure AD API responses.

Supports:
- table: Human-readable formatted tables
- json: Raw JSON output
- csv: CSV format for exports
"""

import csv
import io
import json
import sys
from typing import Any, Dict, List, Optional, Union


def format_output(
    data: Union[Dict, List],
    format_type: str = "table",
    fields: Optional[List[str]] = None
) -> str:
    """
    Format data for output.

    Args:
        data: Data to format (dict or list of dicts)
        format_type: Output format (table, json, csv)
        fields: Fields to include (optional, for table/csv)

    Returns:
        Formatted string
    """
    if format_type == "json":
        return format_json(data)
    elif format_type == "csv":
        return format_csv(data, fields)
    else:
        return format_table(data, fields)


def format_json(data: Any) -> str:
    """Format data as JSON."""
    return json.dumps(data, indent=2, default=str)


def format_csv(data: Union[Dict, List], fields: Optional[List[str]] = None) -> str:
    """Format data as CSV."""
    if isinstance(data, dict):
        # Handle Graph API response format
        items = data.get('value', [data])
    else:
        items = data if isinstance(data, list) else [data]

    if not items:
        return ""

    # Determine fields
    if fields:
        headers = fields
    else:
        # Use all keys from first item
        headers = list(items[0].keys()) if items else []

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction='ignore')
    writer.writeheader()

    for item in items:
        # Flatten nested objects for CSV
        flat_item = flatten_dict(item)
        writer.writerow(flat_item)

    return output.getvalue()


def format_table(data: Union[Dict, List], fields: Optional[List[str]] = None) -> str:
    """Format data as a human-readable table."""
    if isinstance(data, dict):
        # Handle Graph API response format
        if 'value' in data:
            items = data['value']
            # Add count info
            count_info = f"Total: {len(items)} items"
            if '@odata.nextLink' in data:
                count_info += " (more available)"
        else:
            # Single object
            return format_single_object(data, fields)
    else:
        items = data if isinstance(data, list) else [data]
        count_info = f"Total: {len(items)} items"

    if not items:
        return "No results found."

    # Determine fields to display
    if fields:
        headers = fields
    else:
        # Default fields for common object types
        headers = get_default_fields(items[0])

    # Calculate column widths
    widths = {h: len(h) for h in headers}
    for item in items:
        for h in headers:
            value = get_nested_value(item, h)
            widths[h] = max(widths[h], len(str(value)[:50]))  # Cap at 50 chars

    # Build table
    lines = []

    # Header
    header_line = " | ".join(h.ljust(widths[h]) for h in headers)
    lines.append(header_line)
    lines.append("-" * len(header_line))

    # Rows
    for item in items:
        row_values = []
        for h in headers:
            value = get_nested_value(item, h)
            # Truncate long values
            str_value = str(value)[:50] if value is not None else ""
            row_values.append(str_value.ljust(widths[h]))
        lines.append(" | ".join(row_values))

    lines.append("")
    lines.append(count_info)

    return "\n".join(lines)


def format_single_object(obj: Dict, fields: Optional[List[str]] = None) -> str:
    """Format a single object as key-value pairs."""
    if fields:
        keys = fields
    else:
        keys = list(obj.keys())

    lines = []
    max_key_len = max(len(k) for k in keys) if keys else 0

    for key in keys:
        value = obj.get(key)
        if isinstance(value, (dict, list)):
            value = json.dumps(value, default=str)
        lines.append(f"{key.ljust(max_key_len)}: {value}")

    return "\n".join(lines)


def get_nested_value(obj: Dict, key: str) -> Any:
    """Get a value from a nested dictionary using dot notation."""
    keys = key.split('.')
    value = obj
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return None
    return value


def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """Flatten a nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # Convert lists to comma-separated strings
            items.append((new_key, ', '.join(str(i) for i in v)))
        else:
            items.append((new_key, v))
    return dict(items)


def get_default_fields(item: Dict) -> List[str]:
    """Get default display fields based on object type."""
    # Detect object type from @odata.type or common fields
    odata_type = item.get('@odata.type', '')

    if 'user' in odata_type.lower() or 'userPrincipalName' in item:
        return ['displayName', 'userPrincipalName', 'mail', 'jobTitle', 'department']

    elif 'group' in odata_type.lower() or ('displayName' in item and 'groupTypes' in item):
        return ['displayName', 'mail', 'groupTypes', 'membershipRule']

    elif 'device' in odata_type.lower() or 'deviceId' in item:
        return ['displayName', 'operatingSystem', 'operatingSystemVersion', 'trustType', 'isManaged']

    elif 'organization' in odata_type.lower() or 'verifiedDomains' in item:
        return ['displayName', 'id', 'city', 'country']

    elif 'subscribedSku' in odata_type.lower() or 'skuPartNumber' in item:
        return ['skuPartNumber', 'capabilityStatus', 'consumedUnits', 'prepaidUnits.enabled']

    elif 'directoryRole' in odata_type.lower() or 'roleTemplateId' in item:
        return ['displayName', 'description', 'id']

    elif 'domain' in odata_type.lower() or 'authenticationType' in item:
        return ['id', 'isDefault', 'isVerified', 'authenticationType']

    else:
        # Generic: show first 5 non-odata fields
        fields = [k for k in item.keys() if not k.startswith('@odata')]
        return fields[:5]


# User-specific formatters
def format_user_summary(user: Dict) -> str:
    """Format a user summary for display."""
    lines = [
        f"User: {user.get('displayName', 'N/A')}",
        f"  UPN: {user.get('userPrincipalName', 'N/A')}",
        f"  Email: {user.get('mail', 'N/A')}",
        f"  Job Title: {user.get('jobTitle', 'N/A')}",
        f"  Department: {user.get('department', 'N/A')}",
        f"  Office: {user.get('officeLocation', 'N/A')}",
        f"  Account Enabled: {user.get('accountEnabled', 'N/A')}",
    ]

    if user.get('assignedLicenses'):
        lines.append(f"  Licenses: {len(user['assignedLicenses'])}")

    return "\n".join(lines)


def format_group_summary(group: Dict) -> str:
    """Format a group summary for display."""
    group_type = "Security"
    if group.get('mailEnabled'):
        group_type = "Microsoft 365" if 'Unified' in group.get('groupTypes', []) else "Mail-enabled Security"

    lines = [
        f"Group: {group.get('displayName', 'N/A')}",
        f"  Type: {group_type}",
        f"  Email: {group.get('mail', 'N/A')}",
        f"  Description: {group.get('description', 'N/A')[:100]}",
    ]

    if group.get('membershipRule'):
        lines.append(f"  Dynamic Rule: {group.get('membershipRule')[:50]}...")

    return "\n".join(lines)


def format_device_summary(device: Dict) -> str:
    """Format a device summary for display."""
    lines = [
        f"Device: {device.get('displayName', 'N/A')}",
        f"  OS: {device.get('operatingSystem', 'N/A')} {device.get('operatingSystemVersion', '')}",
        f"  Trust Type: {device.get('trustType', 'N/A')}",
        f"  Managed: {device.get('isManaged', 'N/A')}",
        f"  Compliant: {device.get('isCompliant', 'N/A')}",
        f"  Last Activity: {device.get('approximateLastSignInDateTime', 'N/A')}",
    ]

    return "\n".join(lines)


def print_error(message: str):
    """Print an error message to stderr."""
    print(f"Error: {message}", file=sys.stderr)


def print_success(message: str):
    """Print a success message."""
    print(f"Success: {message}")


def print_warning(message: str):
    """Print a warning message to stderr."""
    print(f"Warning: {message}", file=sys.stderr)


if __name__ == '__main__':
    # Test formatters
    test_data = {
        "value": [
            {"displayName": "John Doe", "userPrincipalName": "john@example.com", "mail": "john@example.com"},
            {"displayName": "Jane Smith", "userPrincipalName": "jane@example.com", "mail": "jane@example.com"},
        ]
    }

    print("=== Table Format ===")
    print(format_output(test_data, "table"))

    print("\n=== JSON Format ===")
    print(format_output(test_data, "json"))

    print("\n=== CSV Format ===")
    print(format_output(test_data, "csv"))
