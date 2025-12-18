#!/usr/bin/env python3
"""
NinjaOne Output Formatters

Provides consistent output formatting for CLI commands.
Supports table, JSON, compact, and summary formats.
"""

import json
import sys
from datetime import datetime


def format_timestamp(ts):
    """Format Unix timestamp to readable string."""
    if not ts:
        return 'N/A'
    try:
        if isinstance(ts, str):
            return ts
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError, OSError):
        return str(ts)


def truncate(text, max_len=50):
    """Truncate text with ellipsis if too long."""
    if not text:
        return ''
    text = str(text)
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + '...'


def format_bytes(size):
    """Format bytes to human readable size."""
    if not size:
        return 'N/A'
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(size) < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def print_json(data):
    """Print data as formatted JSON."""
    print(json.dumps(data, indent=2, default=str))


def print_table(headers, rows, widths=None):
    """
    Print data as formatted table.

    Args:
        headers: List of column headers
        rows: List of row data (each row is a list)
        widths: Optional list of column widths
    """
    if not rows:
        print("No results found.")
        return

    # Calculate column widths if not provided
    if not widths:
        widths = []
        for i, header in enumerate(headers):
            col_width = len(str(header))
            for row in rows:
                if i < len(row):
                    col_width = max(col_width, len(str(row[i] or '')))
            widths.append(min(col_width, 50))  # Cap at 50 chars

    # Print header
    header_line = ' | '.join(str(h).ljust(w) for h, w in zip(headers, widths))
    print(header_line)
    print('-' * len(header_line))

    # Print rows
    for row in rows:
        row_data = []
        for i, (cell, width) in enumerate(zip(row, widths)):
            cell_str = truncate(str(cell or ''), width)
            row_data.append(cell_str.ljust(width))
        print(' | '.join(row_data))


def print_compact(items, key_field='id', name_field='name'):
    """Print items in compact format (one per line)."""
    if not items:
        print("No results found.")
        return

    for item in items:
        key = item.get(key_field, 'N/A')
        name = item.get(name_field, item.get('systemName', 'N/A'))
        print(f"{key}: {name}")


def print_summary(items, title='Results'):
    """Print summary statistics."""
    if not items:
        print(f"{title}: 0 items")
        return

    print(f"{title}: {len(items)} items")


def print_device_table(devices):
    """Print devices in table format."""
    headers = ['ID', 'Name', 'Org', 'Status', 'OS', 'Last Contact']
    rows = []
    for d in devices:
        rows.append([
            d.get('id', 'N/A'),
            truncate(d.get('systemName', d.get('dnsName', 'N/A')), 30),
            truncate(d.get('organizationId', 'N/A'), 15),
            d.get('offline', 'N/A') and 'Offline' or 'Online',
            truncate(d.get('os', {}).get('name', 'N/A') if isinstance(d.get('os'), dict) else d.get('os', 'N/A'), 20),
            format_timestamp(d.get('lastContact'))
        ])
    print_table(headers, rows)


def print_organization_table(orgs):
    """Print organizations in table format."""
    headers = ['ID', 'Name', 'Description', 'Devices']
    rows = []
    for o in orgs:
        rows.append([
            o.get('id', 'N/A'),
            truncate(o.get('name', 'N/A'), 30),
            truncate(o.get('description', ''), 30),
            o.get('deviceCount', 'N/A')
        ])
    print_table(headers, rows)


def print_alert_table(alerts):
    """Print alerts in table format."""
    headers = ['UID', 'Device', 'Severity', 'Message', 'Created']
    rows = []
    for a in alerts:
        rows.append([
            a.get('uid', 'N/A'),
            a.get('deviceId', 'N/A'),
            a.get('severity', 'N/A'),
            truncate(a.get('message', 'N/A'), 40),
            format_timestamp(a.get('createTime'))
        ])
    print_table(headers, rows)


def print_ticket_table(tickets):
    """Print tickets in table format."""
    headers = ['ID', 'Subject', 'Status', 'Priority', 'Org', 'Created']
    rows = []
    for t in tickets:
        rows.append([
            t.get('id', 'N/A'),
            truncate(t.get('subject', t.get('summary', 'N/A')), 35),
            t.get('status', {}).get('name', t.get('status', 'N/A')) if isinstance(t.get('status'), dict) else t.get('status', 'N/A'),
            t.get('priority', {}).get('name', t.get('priority', 'N/A')) if isinstance(t.get('priority'), dict) else t.get('priority', 'N/A'),
            t.get('clientId', t.get('organizationId', 'N/A')),
            format_timestamp(t.get('createTime', t.get('created')))
        ])
    print_table(headers, rows)


def print_software_table(software):
    """Print software inventory in table format."""
    headers = ['Name', 'Version', 'Publisher', 'Install Date']
    rows = []
    for s in software:
        rows.append([
            truncate(s.get('name', 'N/A'), 35),
            truncate(s.get('version', 'N/A'), 20),
            truncate(s.get('publisher', 'N/A'), 25),
            format_timestamp(s.get('installDate'))
        ])
    print_table(headers, rows)


def print_patch_table(patches):
    """Print patches in table format."""
    headers = ['KB/ID', 'Title', 'Status', 'Severity', 'Type']
    rows = []
    for p in patches:
        rows.append([
            p.get('kb', p.get('id', 'N/A')),
            truncate(p.get('title', p.get('name', 'N/A')), 40),
            p.get('status', 'N/A'),
            p.get('severity', 'N/A'),
            p.get('type', 'N/A')
        ])
    print_table(headers, rows)


def print_service_table(services):
    """Print Windows services in table format."""
    headers = ['Name', 'Display Name', 'State', 'Start Type']
    rows = []
    for s in services:
        rows.append([
            truncate(s.get('name', 'N/A'), 25),
            truncate(s.get('displayName', 'N/A'), 35),
            s.get('state', 'N/A'),
            s.get('startType', 'N/A')
        ])
    print_table(headers, rows)


def print_policy_table(policies):
    """Print policies in table format."""
    headers = ['ID', 'Name', 'Description', 'Node Class']
    rows = []
    for p in policies:
        rows.append([
            p.get('id', 'N/A'),
            truncate(p.get('name', 'N/A'), 30),
            truncate(p.get('description', ''), 30),
            p.get('nodeClass', 'N/A')
        ])
    print_table(headers, rows)


def print_query_result(data, query_type):
    """Print query/report results with appropriate formatting."""
    if not data:
        print("No results found.")
        return

    # Handle different response structures
    results = data if isinstance(data, list) else data.get('results', data.get('data', [data]))

    if not results:
        print("No results found.")
        return

    # Get headers from first result
    if results and isinstance(results[0], dict):
        # Use first few meaningful keys as headers
        first = results[0]
        headers = list(first.keys())[:8]  # Limit to 8 columns

        rows = []
        for item in results:
            row = [truncate(str(item.get(h, '')), 25) for h in headers]
            rows.append(row)

        print_table(headers, rows)
    else:
        # Fallback to JSON
        print_json(results)


def format_output(data, format_type='table', resource_type=None):
    """
    Format and print data based on format type.

    Args:
        data: Data to format (list or dict)
        format_type: One of 'table', 'json', 'compact', 'summary'
        resource_type: Type of resource for specialized formatting
    """
    if format_type == 'json':
        print_json(data)
        return

    # Handle list data
    items = data if isinstance(data, list) else [data] if data else []

    if format_type == 'summary':
        print_summary(items, resource_type or 'Results')
        return

    if format_type == 'compact':
        print_compact(items)
        return

    # Table format - use specialized formatter if available
    if resource_type == 'devices':
        print_device_table(items)
    elif resource_type == 'organizations':
        print_organization_table(items)
    elif resource_type == 'alerts':
        print_alert_table(items)
    elif resource_type == 'tickets':
        print_ticket_table(items)
    elif resource_type == 'software':
        print_software_table(items)
    elif resource_type == 'patches':
        print_patch_table(items)
    elif resource_type == 'services':
        print_service_table(items)
    elif resource_type == 'policies':
        print_policy_table(items)
    elif resource_type and resource_type.startswith('query'):
        print_query_result(data, resource_type)
    else:
        # Generic table output
        if items and isinstance(items[0], dict):
            headers = list(items[0].keys())[:6]
            rows = [[truncate(str(item.get(h, '')), 30) for h in headers] for item in items]
            print_table(headers, rows)
        else:
            print_json(data)
