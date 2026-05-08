#!/usr/bin/env python3
"""
Mimecast Output Formatters

Provides consistent output formatting for CLI commands.
Supports table and JSON formats.
"""

import json
from datetime import datetime


def format_timestamp(ts):
    """Format timestamp to readable string."""
    if not ts:
        return 'N/A'
    try:
        if isinstance(ts, str):
            # Try to parse ISO format
            if 'T' in ts:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
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


def print_users_table(users):
    """Print users in table format."""
    headers = ['Email', 'Name', 'Domain', 'Internal', 'Created']
    rows = []
    for u in users:
        rows.append([
            truncate(u.get('emailAddress', 'N/A'), 35),
            truncate(u.get('name', 'N/A'), 25),
            truncate(u.get('domain', 'N/A'), 20),
            'Yes' if u.get('internal', False) else 'No',
            format_timestamp(u.get('created'))
        ])
    print_table(headers, rows)


def print_groups_table(groups):
    """Print groups in table format."""
    headers = ['ID', 'Name', 'Description', 'Source', 'Members']
    rows = []
    for g in groups:
        rows.append([
            truncate(g.get('id', 'N/A'), 20),
            truncate(g.get('description', g.get('name', 'N/A')), 30),
            truncate(g.get('source', ''), 20),
            g.get('folderCount', g.get('memberCount', 'N/A'))
        ])
    print_table(headers, rows)


def print_messages_table(messages):
    """Print messages/tracking in table format."""
    headers = ['ID', 'From', 'To', 'Subject', 'Status', 'Date']
    rows = []
    for m in messages:
        rows.append([
            truncate(m.get('id', 'N/A'), 15),
            truncate(m.get('from', m.get('fromAddress', 'N/A')), 25),
            truncate(m.get('to', m.get('toAddress', 'N/A')), 25),
            truncate(m.get('subject', 'N/A'), 30),
            m.get('status', m.get('deliveryStatus', 'N/A')),
            format_timestamp(m.get('received', m.get('transmissionDate')))
        ])
    print_table(headers, rows)


def print_held_messages_table(messages):
    """Print held messages in table format."""
    headers = ['ID', 'From', 'To', 'Subject', 'Reason', 'Date']
    rows = []
    for m in messages:
        rows.append([
            truncate(m.get('id', 'N/A'), 15),
            truncate(m.get('from', m.get('fromEnv', {}).get('emailAddress', 'N/A')), 25),
            truncate(m.get('to', m.get('toEnv', {}).get('emailAddress', 'N/A')), 25),
            truncate(m.get('subject', 'N/A'), 30),
            truncate(m.get('reason', m.get('reasonCode', 'N/A')), 15),
            format_timestamp(m.get('dateReceived'))
        ])
    print_table(headers, rows)


def print_ttp_url_table(logs):
    """Print TTP URL protection logs in table format."""
    headers = ['URL', 'Action', 'Category', 'User', 'Date']
    rows = []
    for l in logs:
        rows.append([
            truncate(l.get('url', 'N/A'), 40),
            l.get('action', l.get('scanResult', 'N/A')),
            l.get('category', l.get('urlCategory', 'N/A')),
            truncate(l.get('userEmailAddress', l.get('user', 'N/A')), 25),
            format_timestamp(l.get('date', l.get('eventTime')))
        ])
    print_table(headers, rows)


def print_ttp_attachment_table(logs):
    """Print TTP attachment protection logs in table format."""
    headers = ['Filename', 'Result', 'Type', 'Sender', 'Date']
    rows = []
    for l in logs:
        rows.append([
            truncate(l.get('fileName', 'N/A'), 30),
            l.get('result', l.get('scanResult', 'N/A')),
            truncate(l.get('fileType', 'N/A'), 15),
            truncate(l.get('senderAddress', 'N/A'), 25),
            format_timestamp(l.get('date', l.get('eventTime')))
        ])
    print_table(headers, rows)


def print_ttp_impersonation_table(logs):
    """Print TTP impersonation protection logs in table format."""
    headers = ['Subject', 'Sender', 'Action', 'Type', 'Date']
    rows = []
    for l in logs:
        rows.append([
            truncate(l.get('subject', 'N/A'), 35),
            truncate(l.get('senderAddress', l.get('from', 'N/A')), 25),
            l.get('action', l.get('actionTriggered', 'N/A')),
            l.get('impersonationType', l.get('taggedMalicious', 'N/A')),
            format_timestamp(l.get('eventTime', l.get('date')))
        ])
    print_table(headers, rows)


def print_policies_table(policies):
    """Print policies in table format."""
    headers = ['ID', 'Description', 'Type', 'Enabled', 'From', 'To']
    rows = []
    for p in policies:
        rows.append([
            truncate(p.get('id', 'N/A'), 15),
            truncate(p.get('policy', {}).get('description', p.get('description', 'N/A')), 30),
            p.get('policyType', p.get('type', 'N/A')),
            'Yes' if p.get('enabled', True) else 'No',
            truncate(p.get('from', {}).get('type', 'N/A'), 15),
            truncate(p.get('to', {}).get('type', 'N/A'), 15)
        ])
    print_table(headers, rows)


def print_audit_table(events):
    """Print audit events in table format."""
    headers = ['ID', 'Event', 'User', 'Source', 'Date']
    rows = []
    for e in events:
        rows.append([
            truncate(e.get('id', 'N/A'), 15),
            truncate(e.get('auditType', e.get('eventType', 'N/A')), 25),
            truncate(e.get('user', 'N/A'), 25),
            truncate(e.get('source', 'N/A'), 15),
            format_timestamp(e.get('eventTime'))
        ])
    print_table(headers, rows)


def print_domains_table(domains):
    """Print domains in table format."""
    headers = ['ID', 'Domain', 'Send Only', 'Local', 'Inbound Type']
    rows = []
    for d in domains:
        rows.append([
            truncate(d.get('id', 'N/A'), 20),
            d.get('domain', 'N/A'),
            'Yes' if d.get('sendOnly', False) else 'No',
            'Yes' if d.get('local', False) else 'No',
            d.get('inboundType', 'N/A')
        ])
    print_table(headers, rows)


def print_account_info(account):
    """Print account information."""
    print(f"Account Code: {account.get('accountCode', 'N/A')}")
    print(f"Account Name: {account.get('accountName', 'N/A')}")
    print(f"Type: {account.get('type', 'N/A')}")
    print(f"Region: {account.get('region', 'N/A')}")
    print(f"Gateway: {account.get('gateway', 'N/A')}")
    print(f"Mailboxes: {account.get('mailboxes', 'N/A')}")
    print(f"Max Retention: {account.get('maxRetention', 'N/A')} days")
    if account.get('packages'):
        print(f"Packages: {', '.join(account.get('packages', []))}")


# ==================== AWARENESS TRAINING FORMATTERS ====================

def print_campaigns_table(campaigns):
    """Print awareness training campaigns table."""
    headers = ['Campaign ID', 'Name', 'Status', 'Sent', 'Completed', 'Correct%']
    rows = []
    for c in campaigns:
        sent = c.get('sent', c.get('totalSent', 0))
        completed = c.get('completed', c.get('totalCompleted', 0))
        correct = c.get('correctPct', c.get('correctPercentage', 'N/A'))
        rows.append([
            truncate(str(c.get('campaignId', c.get('id', 'N/A'))), 30),
            truncate(str(c.get('name', c.get('campaignName', 'N/A'))), 40),
            str(c.get('status', 'N/A')),
            str(sent),
            str(completed),
            f"{correct}%" if correct != 'N/A' else 'N/A',
        ])
    print_table(headers, rows)


def print_safe_scores_table(scores):
    """Print per-user SAFE score table."""
    headers = ['Email', 'Name', 'Department', 'Risk Grade', 'Knowledge', 'Engagement']
    rows = []
    for s in scores:
        rows.append([
            truncate(str(s.get('emailAddress', s.get('email', 'N/A'))), 40),
            truncate(str(s.get('name', 'N/A')), 30),
            truncate(str(s.get('department', 'N/A')), 20),
            str(s.get('riskGrade', s.get('safeGrade', 'N/A'))),
            str(s.get('knowledgeScore', s.get('knowledge', 'N/A'))),
            str(s.get('engagementScore', s.get('engagement', 'N/A'))),
        ])
    print_table(headers, rows)


def print_phishing_table(campaigns):
    """Print phishing campaign results table."""
    headers = ['Campaign', 'Sent', 'Opened', 'Clicked', 'Submitted', 'Reported']
    rows = []
    for c in campaigns:
        rows.append([
            truncate(str(c.get('name', c.get('campaignName', 'N/A'))), 35),
            str(c.get('sent', c.get('totalSent', 0))),
            str(c.get('opened', c.get('totalOpened', 0))),
            str(c.get('clicked', c.get('totalClicked', 0))),
            str(c.get('submitted', c.get('totalSubmitted', 0))),
            str(c.get('reported', c.get('totalReported', 0))),
        ])
    print_table(headers, rows)


def print_watchlist_table(users):
    """Print high-risk user watchlist table."""
    headers = ['Email', 'Name', 'Department', 'Risk Level', 'Risk Score']
    rows = []
    for u in users:
        rows.append([
            truncate(str(u.get('emailAddress', u.get('email', 'N/A'))), 40),
            truncate(str(u.get('name', 'N/A')), 30),
            truncate(str(u.get('department', 'N/A')), 20),
            str(u.get('riskLevel', u.get('risk', 'N/A'))),
            str(u.get('riskScore', 'N/A')),
        ])
    print_table(headers, rows)


def format_output(data, format_type='table', resource_type=None):
    """
    Format and print data based on format type.

    Args:
        data: Data to format (list or dict)
        format_type: One of 'table', 'json'
        resource_type: Type of resource for specialized formatting
    """
    if format_type == 'json':
        print_json(data)
        return

    # Handle Mimecast response format: {"data": [...]}
    if isinstance(data, dict) and 'data' in data:
        items = data['data']
    elif isinstance(data, list):
        items = data
    else:
        items = [data] if data else []

    if not items:
        print("No results found.")
        return

    # Use specialized formatter based on resource type
    if resource_type == 'users':
        print_users_table(items)
    elif resource_type == 'groups':
        print_groups_table(items)
    elif resource_type == 'messages':
        print_messages_table(items)
    elif resource_type == 'held':
        print_held_messages_table(items)
    elif resource_type == 'ttp-urls':
        print_ttp_url_table(items)
    elif resource_type == 'ttp-attachments':
        print_ttp_attachment_table(items)
    elif resource_type == 'ttp-impersonation':
        print_ttp_impersonation_table(items)
    elif resource_type == 'policies':
        print_policies_table(items)
    elif resource_type == 'audit':
        print_audit_table(items)
    elif resource_type == 'domains':
        print_domains_table(items)
    elif resource_type == 'account':
        if items:
            print_account_info(items[0] if isinstance(items, list) else items)
    elif resource_type == 'awareness-campaigns':
        print_campaigns_table(items)
    elif resource_type == 'awareness-safe-scores':
        print_safe_scores_table(items)
    elif resource_type == 'awareness-phishing':
        print_phishing_table(items)
    elif resource_type in ('awareness-phishing-users', 'awareness-campaign-users',
                           'awareness-watchlist'):
        print_watchlist_table(items)
    else:
        # Generic table output
        if items and isinstance(items[0], dict):
            headers = list(items[0].keys())[:6]
            rows = [[truncate(str(item.get(h, '')), 30) for h in headers] for item in items]
            print_table(headers, rows)
        else:
            print_json(data)
