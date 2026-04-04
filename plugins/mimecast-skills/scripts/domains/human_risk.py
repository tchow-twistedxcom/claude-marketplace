"""
Mimecast Human Risk Domain

Surfaces per-user human risk grades from the Awareness Training product.
Uses /api/awareness-training/company/get-safe-score-details which returns
a full-pagination view of all users with risk component grades.

Risk components per user:
- risk        — overall human risk grade (A–F)
- humanError  — phishing/click susceptibility
- sentiment   — security culture / attitude indicator
- engagement  — training module completion rate
- knowledge   — knowledge assessment results
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from .base import BaseDomain

if TYPE_CHECKING:
    import argparse

GRADE_ORDER = ["A", "B", "C", "D", "F"]
COMPONENTS = ["risk", "humanError", "sentiment", "engagement", "knowledge"]
COMPONENT_LABELS = {
    "risk": "Risk",
    "humanError": "Error",
    "sentiment": "Sentiment",
    "engagement": "Engagement",
    "knowledge": "Knowledge",
}


class HumanRiskDomain(BaseDomain):
    """Human Risk domain — per-user risk grades from Awareness Training product."""

    # ── API Methods ──────────────────────────────────────────────────────────

    def get_safe_score_details(self) -> list[dict]:
        """Fetch all users with full pagination. Returns flat list of user dicts."""
        result = self.client.get(
            "/api/awareness-training/company/get-safe-score-details",
            paginate=True,
        )
        return result.get("data", [])

    # ── CLI Command Handlers ─────────────────────────────────────────────────

    def cmd_summary(self, args: argparse.Namespace) -> None:
        """Print grade distribution across all risk components."""
        users = self.get_safe_score_details()
        if not users:
            print("No user data returned.", file=sys.stderr)
            return

        if getattr(args, "output", "table") == "json":
            import json
            summary = _build_summary(users)
            print(json.dumps(summary, indent=2))
            return

        total = len(users)
        print(f"\nHuman Risk Summary — {total} users\n")
        print(f"{'Grade':<8}", end="")
        for comp in COMPONENTS:
            print(f"{COMPONENT_LABELS[comp]:>12}", end="")
        print()
        print("-" * (8 + 12 * len(COMPONENTS)))

        for grade in GRADE_ORDER:
            counts = {c: sum(1 for u in users if u.get(c) == grade) for c in COMPONENTS}
            pcts = {c: f"{counts[c]:>4} ({counts[c]*100//total:>2}%)" for c in COMPONENTS}
            print(f"{grade:<8}", end="")
            for comp in COMPONENTS:
                print(f"{pcts[comp]:>12}", end="")
            print()

        # High-risk callout
        f_count = sum(1 for u in users if u.get("risk") == "F")
        if f_count:
            print(f"\n⚠  {f_count} users ({f_count*100//total}%) are HIGH RISK (F grade overall)")

    def cmd_users(self, args: argparse.Namespace) -> None:
        """List users with risk grades, optionally filtered."""
        users = self.get_safe_score_details()

        grade_filter = getattr(args, "grade", None)
        dept_filter = getattr(args, "department", None)
        component = getattr(args, "component", "risk")
        active_only = getattr(args, "active", False)

        if active_only:
            users = [u for u in users if u.get("userState") == "ACTIVE"]
        if grade_filter:
            grade_filter = grade_filter.upper()
            users = [u for u in users if u.get(component, "").upper() == grade_filter]
        if dept_filter:
            users = [u for u in users if dept_filter.lower() in (u.get("department") or "").lower()]

        # Sort: worst grade first within each component
        users = sorted(users, key=lambda u: GRADE_ORDER.index(u.get(component, "F"))
                       if u.get(component) in GRADE_ORDER else 99)

        if getattr(args, "output", "table") == "json":
            import json
            print(json.dumps(users, indent=2))
            return

        if not users:
            print("No users match the filter criteria.")
            return

        col_w = {"email": 36, "name": 24, "dept": 16}
        header = (f"{'Email':<{col_w['email']}} {'Name':<{col_w['name']}} "
                  f"{'Dept':<{col_w['dept']}}")
        for comp in COMPONENTS:
            header += f"  {COMPONENT_LABELS[comp]:<10}"
        print(f"\n{header}")
        print("-" * len(header))

        for u in users:
            row = (f"{u.get('emailAddress',''):<{col_w['email']}} "
                   f"{(u.get('name') or '')[:col_w['name']]:<{col_w['name']}} "
                   f"{(u.get('department') or '')[:col_w['dept']]:<{col_w['dept']}}")
            for comp in COMPONENTS:
                grade = u.get(comp, "?")
                row += f"  {grade:<10}"
            print(row)

        print(f"\n{len(users)} users")

    def cmd_high_risk(self, args: argparse.Namespace) -> None:
        """Shortcut: list users with F overall risk grade."""
        # Inject grade=F and delegate to cmd_users
        args.grade = "F"
        args.component = "risk"
        self.cmd_users(args)

    # ── Domain Registration ───────────────────────────────────────────────────

    def get_cmd_map(self) -> dict[tuple[str, str], Any]:
        return {
            ("human-risk", "summary"):   self.cmd_summary,
            ("human-risk", "users"):     self.cmd_users,
            ("human-risk", "high-risk"): self.cmd_high_risk,
        }

    @classmethod
    def register_parsers(cls, subparsers: Any, make_common_parser: Any) -> None:
        p = subparsers.add_parser(
            "human-risk",
            help="Human Risk scores (requires Awareness Training product)"
        )
        sub = p.add_subparsers(dest="action")
        sub.required = True

        # summary
        sub.add_parser(
            "summary",
            parents=[make_common_parser()],
            help="Grade distribution across all risk components",
        )

        # users
        u = sub.add_parser(
            "users",
            parents=[make_common_parser()],
            help="List users with risk grades",
        )
        u.add_argument("--grade", choices=["A", "B", "C", "D", "F"],
                       help="Filter by grade (applied to --component)")
        u.add_argument(
            "--component",
            choices=COMPONENTS,
            default="risk",
            help="Which component to filter/sort by (default: risk)",
        )
        u.add_argument("--department", help="Filter by department name (substring match)")
        u.add_argument("--active", action="store_true", help="Only show ACTIVE users")

        # high-risk
        hr = sub.add_parser(
            "high-risk",
            parents=[make_common_parser()],
            help="List F-grade users (highest risk)",
        )
        hr.add_argument("--department", help="Filter by department name")
        hr.add_argument("--active", action="store_true", help="Only show ACTIVE users")


# ── Helpers ────────────────────────────────────────────────────────────────

def _build_summary(users: list[dict]) -> dict:
    total = len(users)
    summary: dict = {"total": total, "components": {}}
    for comp in COMPONENTS:
        dist = {g: 0 for g in GRADE_ORDER}
        for u in users:
            g = u.get(comp)
            if g in dist:
                dist[g] += 1
        summary["components"][comp] = {
            g: {"count": dist[g], "pct": round(dist[g] * 100 / total, 1) if total else 0}
            for g in GRADE_ORDER
        }
    return summary
