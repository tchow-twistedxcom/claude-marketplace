"""
Mimecast Domain Utilities

Shared helpers for domain modules: argparse factory, date shortcuts, date resolution.
"""

import argparse
from datetime import datetime, timedelta


def make_common_parser() -> argparse.ArgumentParser:
    """Factory: create a fresh argparse parent parser with --output and --profile flags.

    IMPORTANT: Must be called once per sub-parser that needs these flags.
    Argparse parent parsers are stateful — sharing one instance across multiple
    add_parser(..., parents=[...]) calls causes duplicate action errors.

    Returns:
        A new ArgumentParser with add_help=False, with --output and --profile args.
    """
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument(
        "--output", "-o",
        choices=["table", "json", "csv"],
        default=None,
        help="Output format: table (default), json, or csv"
    )
    p.add_argument(
        "--profile",
        default=None,
        help="Config profile name (default: from mimecast_config.json)"
    )
    return p


def _get_cst_now():
    """Get current datetime in CST/CDT timezone."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Chicago"))
    except ImportError:
        from datetime import timezone
        utc_now = datetime.now(timezone.utc)
        return utc_now + timedelta(hours=-6)  # Fallback: CST (UTC-6)


def resolve_date_range(args) -> tuple[str | None, str | None]:
    """Resolve date range from argparse namespace with date shortcut flags.

    Supports:
        --days N     : Last N days
        --hours N    : Last N hours
        --today      : Today only
        --yesterday  : Yesterday only
        --week       : Last 7 days
        --month      : Last 30 days
        --start/--end: Explicit dates (takes precedence over shortcuts)

    Returns:
        Tuple of (start_date, end_date) as YYYY-MM-DD strings.
    """
    now = _get_cst_now()
    today = now.strftime('%Y-%m-%d')

    start = getattr(args, 'start', None)
    end = getattr(args, 'end', None)

    if start and end:
        return start, end

    if getattr(args, 'today', False):
        return today, today

    if getattr(args, 'yesterday', False):
        yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        return yesterday, yesterday

    if getattr(args, 'week', False):
        return (now - timedelta(days=7)).strftime('%Y-%m-%d'), today

    if getattr(args, 'month', False):
        return (now - timedelta(days=30)).strftime('%Y-%m-%d'), today

    days = getattr(args, 'days', None)
    if days:
        return (now - timedelta(days=days)).strftime('%Y-%m-%d'), today

    hours = getattr(args, 'hours', None)
    if hours:
        return (now - timedelta(hours=hours)).strftime('%Y-%m-%d'), today

    if start and not end:
        end = today
    elif end and not start:
        end_dt = datetime.strptime(end, '%Y-%m-%d')
        start = (end_dt - timedelta(days=7)).strftime('%Y-%m-%d')

    return start, end


def add_date_shortcuts(parser: argparse.ArgumentParser) -> None:
    """Add --days/--hours/--today/--yesterday/--week/--month to a parser."""
    date_group = parser.add_argument_group('Date Range Shortcuts')
    date_group.add_argument("--days", type=int, metavar="N",
                            help="Last N days (e.g., --days 7)")
    date_group.add_argument("--hours", type=int, metavar="N",
                            help="Last N hours (e.g., --hours 24)")
    date_group.add_argument("--today", action="store_true",
                            help="Today only")
    date_group.add_argument("--yesterday", action="store_true",
                            help="Yesterday only")
    date_group.add_argument("--week", action="store_true",
                            help="Last 7 days")
    date_group.add_argument("--month", action="store_true",
                            help="Last 30 days")


def add_limit_arg(parser: argparse.ArgumentParser, default: int = 100) -> None:
    """Add --limit/-n argument to a parser."""
    parser.add_argument(
        "--limit", "-n",
        type=int,
        default=default,
        metavar="N",
        help=f"Maximum number of results to return (default: {default})"
    )
