"""
Mimecast Directory Sync Domain

Surfaces directory sync health: connection config, status, and event history.
Uses:
  - /api/directory/get-connection — connection config and last sync status
  - /api/audit/get-audit-events   — sync success/failure history
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from .base import BaseDomain

if TYPE_CHECKING:
    import argparse


class DirectorySyncDomain(BaseDomain):
    """Directory Sync domain — connection config, status, and sync history."""

    # ── API Methods ──────────────────────────────────────────────────────────

    def get_connection(self) -> dict:
        """Get directory sync connection configuration."""
        return self.client.post("/api/directory/get-connection")

    def get_sync_events(self, days: int = 7) -> list[dict]:
        """Fetch directory sync audit events from the last N days."""
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S+0000")
        end = now.strftime("%Y-%m-%dT%H:%M:%S+0000")

        result = self.client.get("/api/audit/get-audit-events", {
            "startDateTime": start,
            "endDateTime": end,
        }, paginate=True)

        all_events = result.get("data", [])
        return [
            e for e in all_events
            if "sync" in e.get("auditType", "").lower()
            or "directory" in e.get("auditType", "").lower()
        ]

    # ── CLI Command Handlers ─────────────────────────────────────────────────

    def cmd_status(self, args: argparse.Namespace) -> None:
        """Show directory sync connection config and current status."""
        from mimecast_formatter import format_output

        r = self.get_connection()
        connections = r.get("data", [])

        if not connections:
            print("No directory sync connections found.")
            return

        output_fmt = args.output
        if output_fmt != "table":
            format_output(connections, output_fmt, 'sync-connections')
            return

        for conn in connections:
            status = conn.get("status", "unknown")
            status_icon = "✓" if status != "error" else "✗"
            last_sync = conn.get("lastSync", "never")

            print(f"\nConnection: {conn.get('description', 'unnamed')}")
            print(f"  Status:        {status_icon} {status}")
            print(f"  Type:          {conn.get('serverType', 'unknown')}")
            print(f"  Last sync:     {last_sync}")
            print(f"  Sync running:  {conn.get('syncRunning', False)}")
            print()

            # Settings — highlight dangerous/misconfigured ones
            ack = conn.get("acknowledgeDisabledAccounts", False)
            delete = conn.get("deleteUsers", False)
            max_unlink = conn.get("maxUnlink", "unknown")

            print("  Configuration:")
            ack_warn = " ⚠  DISABLED — Azure AD disabled users NOT auto-disabled in Mimecast" if not ack else " ✓ enabled"
            del_warn = " (disabled users are kept)" if not delete else " ✓ enabled"
            print(f"    acknowledgeDisabledAccounts: {ack}{ack_warn}")
            print(f"    deleteUsers:                 {delete}{del_warn}")
            print(f"    syncGuestUsers:              {conn.get('syncGuestUsers', False)}")
            print(f"    maxUnlink:                   {max_unlink}")
            print(f"    syncContacts:                {conn.get('syncContacts', False)}")

    def cmd_history(self, args: argparse.Namespace) -> None:
        """Show recent sync event history."""
        from mimecast_formatter import format_output

        days = getattr(args, "days", 7)
        events = self.get_sync_events(days=days)

        output_fmt = args.output
        if output_fmt != "table":
            format_output(events, output_fmt, 'sync-history')
            return

        if not events:
            print(f"No directory sync events in the last {days} days.")
            return

        failures = [e for e in events if "failed" in e.get("auditType", "").lower()]
        successes = [e for e in events if "completed" in e.get("auditType", "").lower()]

        print(f"\nDirectory Sync History (last {days} days) — {len(events)} events")
        print(f"  Completed: {len(successes)}   Failed: {len(failures)}")
        if failures:
            print(f"  ⚠  {len(failures)} failure(s) detected")
        print()

        print(f"{'Time (UTC)':<28} {'Event':<32} {'Details'}")
        print("-" * 100)

        for e in sorted(events, key=lambda x: x.get("eventTime", ""), reverse=True):
            etype = e.get("auditType", "")
            time = e.get("eventTime", "")[:19].replace("T", " ")
            info = e.get("eventInfo", "")

            # Truncate info for table view
            if "Processed" in info:
                # Extract key counts
                m = re.search(r"Processed (.+?)by", info)
                detail = m.group(1).strip() if m else info[:60]
            elif "No changes" in info:
                detail = "No changes found"
            elif "Unable to connect" in info:
                detail = "✗ Unable to connect to directory service"
            else:
                detail = info[:60]

            icon = "✓" if "Completed" in etype else "✗"
            print(f"{time:<28} {icon} {etype:<30} {detail}")

    # ── Domain Registration ───────────────────────────────────────────────────

    def get_cmd_map(self) -> dict[tuple[str, str], Any]:
        return {
            ("sync", "status"):  self.cmd_status,
            ("sync", "history"): self.cmd_history,
        }

    @classmethod
    def register_parsers(cls, subparsers: Any, make_common_parser: Any) -> None:
        p = subparsers.add_parser(
            "sync",
            help="Directory sync status and history"
        )
        sub = p.add_subparsers(dest="action")
        sub.required = True

        sub.add_parser(
            "status",
            parents=[make_common_parser()],
            help="Show connection config and current sync status",
        )

        hist = sub.add_parser(
            "history",
            parents=[make_common_parser()],
            help="Show recent sync event history",
        )
        hist.add_argument(
            "--days", type=int, default=7,
            help="Number of days to look back (default: 7)",
        )
