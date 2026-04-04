"""
Mimecast Awareness Training Domain

Covers all 12 Awareness Training API 1.0 endpoints:
- Campaigns (list + user data)
- Phishing simulations (campaigns + user data)
- SAFE scores (details + summary)
- Company performance (details + summary)
- Training queue
- User training details
- Watchlist (details + summary)

All endpoints require the Awareness Training product to be enabled in the
Mimecast admin console. HMAC auth may not work — OAuth 2.0 is recommended.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from .base import BaseDomain
from .utils import add_date_shortcuts, resolve_date_range

if TYPE_CHECKING:
    import argparse


class AwarenessTrainingDomain(BaseDomain):
    """Awareness Training API domain — campaigns, phishing, SAFE scores, watchlist."""

    # ── API Methods ──────────────────────────────────────────────────────────

    def get_campaigns(self, source: str | None = None) -> dict:
        """Get all awareness training campaigns."""
        data: dict = {}
        if source is not None:
            data["source"] = source
        return self.client.post("/api/awareness-training/campaign/get-campaigns", data)

    def get_campaign_user_data(self, campaign_id: str | None = None) -> dict:
        """Get per-user training data for a campaign."""
        data: dict = {}
        if campaign_id is not None:
            data["campaignId"] = campaign_id
        return self.client.post("/api/awareness-training/campaign/get-user-data", data)

    def get_performance_details(self) -> dict:
        """Get company-wide training performance details."""
        return self.client.post("/api/awareness-training/company/get-performance-details")

    def get_performance_summary(self) -> dict:
        """Get company-wide training performance summary."""
        return self.client.post("/api/awareness-training/company/get-performance-summary")

    def get_phishing_campaign(self, campaign_id: str | None = None) -> dict:
        """Get phishing simulation campaign details."""
        data: dict = {}
        if campaign_id is not None:
            data["campaignId"] = campaign_id
        return self.client.post("/api/awareness-training/phishing/campaign/get-campaign", data)

    def get_phishing_user_data(self, campaign_id: str | None = None) -> dict:
        """Get per-user phishing simulation data."""
        data: dict = {}
        if campaign_id is not None:
            data["campaignId"] = campaign_id
        return self.client.post(
            "/api/awareness-training/phishing/campaign/get-user-data", data
        )

    def get_safe_score_details(self, email: str | None = None) -> dict:
        """Get per-user SAFE score details."""
        data: dict = {}
        if email is not None:
            data["emailAddress"] = email
        return self.client.post(
            "/api/awareness-training/company/get-safe-score-details", data
        )

    def get_safe_score_summary(self) -> dict:
        """Get company SAFE score summary."""
        return self.client.post(
            "/api/awareness-training/company/get-safe-score-summary"
        )

    def get_training_queue(self) -> dict:
        """Get the awareness training queue."""
        return self.client.post("/api/awareness-training/queue/get-queue")

    def get_user_training_details(self, email: str | None = None) -> dict:
        """Get training details for a specific user."""
        data: dict = {}
        if email is not None:
            data["emailAddress"] = email
        return self.client.post(
            "/api/awareness-training/user/get-training-details", data
        )

    def get_watchlist_details(self) -> dict:
        """Get high-risk user watchlist details."""
        return self.client.post(
            "/api/awareness-training/company/get-watchlist-details"
        )

    def get_watchlist_summary(self) -> dict:
        """Get high-risk user watchlist summary."""
        return self.client.post(
            "/api/awareness-training/company/get-watchlist-summary"
        )

    # ── CLI Command Handlers ─────────────────────────────────────────────────

    def cmd_campaigns(self, args: argparse.Namespace) -> None:
        from mimecast_formatter import format_output
        result = self.get_campaigns(source=getattr(args, 'source', None))
        format_output(result, args.output, 'awareness-campaigns')

    def cmd_campaign_users(self, args: argparse.Namespace) -> None:
        from mimecast_formatter import format_output
        result = self.get_campaign_user_data(campaign_id=getattr(args, 'campaign_id', None))
        format_output(result, args.output, 'awareness-campaign-users')

    def cmd_performance(self, args: argparse.Namespace) -> None:
        from mimecast_formatter import format_output
        result = self.get_performance_details()
        format_output(result, args.output)

    def cmd_performance_summary(self, args: argparse.Namespace) -> None:
        from mimecast_formatter import format_output
        result = self.get_performance_summary()
        format_output(result, args.output)

    def cmd_phishing(self, args: argparse.Namespace) -> None:
        from mimecast_formatter import format_output
        result = self.get_phishing_campaign(campaign_id=getattr(args, 'campaign_id', None))
        format_output(result, args.output, 'awareness-phishing')

    def cmd_phishing_users(self, args: argparse.Namespace) -> None:
        from mimecast_formatter import format_output
        result = self.get_phishing_user_data(campaign_id=getattr(args, 'campaign_id', None))
        format_output(result, args.output, 'awareness-phishing-users')

    def cmd_safe_score(self, args: argparse.Namespace) -> None:
        from mimecast_formatter import format_output
        result = self.get_safe_score_details(email=getattr(args, 'email', None))
        format_output(result, args.output, 'awareness-safe-scores')

    def cmd_safe_score_summary(self, args: argparse.Namespace) -> None:
        from mimecast_formatter import format_output
        result = self.get_safe_score_summary()
        format_output(result, args.output)

    def cmd_queue(self, args: argparse.Namespace) -> None:
        from mimecast_formatter import format_output
        result = self.get_training_queue()
        format_output(result, args.output)

    def cmd_training_details(self, args: argparse.Namespace) -> None:
        from mimecast_formatter import format_output
        result = self.get_user_training_details(email=getattr(args, 'email', None))
        format_output(result, args.output)

    def cmd_watchlist(self, args: argparse.Namespace) -> None:
        from mimecast_formatter import format_output
        result = self.get_watchlist_details()
        format_output(result, args.output, 'awareness-watchlist')

    def cmd_watchlist_summary(self, args: argparse.Namespace) -> None:
        from mimecast_formatter import format_output
        result = self.get_watchlist_summary()
        format_output(result, args.output)

    # ── Domain Registration ───────────────────────────────────────────────────

    def get_cmd_map(self) -> dict[tuple[str, str], Any]:
        return {
            ("awareness", "campaigns"):           self.cmd_campaigns,
            ("awareness", "campaign-users"):      self.cmd_campaign_users,
            ("awareness", "performance"):         self.cmd_performance,
            ("awareness", "performance-summary"): self.cmd_performance_summary,
            ("awareness", "phishing"):            self.cmd_phishing,
            ("awareness", "phishing-users"):      self.cmd_phishing_users,
            ("awareness", "safe-score"):          self.cmd_safe_score,
            ("awareness", "safe-score-summary"):  self.cmd_safe_score_summary,
            ("awareness", "queue"):               self.cmd_queue,
            ("awareness", "training-details"):    self.cmd_training_details,
            ("awareness", "watchlist"):           self.cmd_watchlist,
            ("awareness", "watchlist-summary"):   self.cmd_watchlist_summary,
        }

    @classmethod
    def register_parsers(cls, subparsers: Any, make_common_parser: Any) -> None:
        """Register awareness training subparsers."""
        p = subparsers.add_parser(
            "awareness",
            help="Awareness Training operations (requires Awareness Training product)"
        )
        sub = p.add_subparsers(dest="action")
        sub.required = True

        # campaigns
        c = sub.add_parser("campaigns", parents=[make_common_parser()],
                           help="List training campaigns")
        c.add_argument("--source", help="Filter by campaign source")

        # campaign-users
        cu = sub.add_parser("campaign-users", parents=[make_common_parser()],
                            help="Get per-user data for a campaign")
        cu.add_argument("--campaign-id", dest="campaign_id",
                        help="Campaign ID (optional, omit for all)")

        # performance
        sub.add_parser("performance", parents=[make_common_parser()],
                       help="Company training performance details")

        sub.add_parser("performance-summary", parents=[make_common_parser()],
                       help="Company training performance summary")

        # phishing
        ph = sub.add_parser("phishing", parents=[make_common_parser()],
                             help="Phishing simulation campaign details")
        ph.add_argument("--campaign-id", dest="campaign_id",
                        help="Phishing campaign ID (optional)")

        phu = sub.add_parser("phishing-users", parents=[make_common_parser()],
                              help="Per-user phishing simulation data")
        phu.add_argument("--campaign-id", dest="campaign_id",
                         help="Phishing campaign ID (optional)")

        # SAFE scores
        ss = sub.add_parser("safe-score", parents=[make_common_parser()],
                            help="Per-user SAFE score details")
        ss.add_argument("--email", help="Filter to specific user email")

        sub.add_parser("safe-score-summary", parents=[make_common_parser()],
                       help="Company SAFE score summary")

        # queue
        sub.add_parser("queue", parents=[make_common_parser()],
                       help="Training queue")

        # training-details
        td = sub.add_parser("training-details", parents=[make_common_parser()],
                             help="Training details for a user")
        td.add_argument("--email", help="User email address")

        # watchlist
        sub.add_parser("watchlist", parents=[make_common_parser()],
                       help="High-risk user watchlist details")

        sub.add_parser("watchlist-summary", parents=[make_common_parser()],
                       help="High-risk user watchlist summary")
