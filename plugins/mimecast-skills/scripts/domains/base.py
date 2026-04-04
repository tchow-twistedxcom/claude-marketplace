"""
Mimecast Domain Base Classes

Provides BaseDomain ABC for the domain module system.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class BaseDomain(ABC):
    """Abstract base class for all Mimecast domain modules.

    Each domain module implements a subset of the Mimecast API.
    Domains are instantiated with a shared MimecastClient instance.
    """

    def __init__(self, client: Any):
        """Initialize domain with shared API client.

        Args:
            client: MimecastClient instance for making API calls
        """
        self.client = client

    @abstractmethod
    def get_cmd_map(self) -> dict[tuple[str, str], Callable]:
        """Return the command map for this domain.

        Returns:
            Dict mapping (resource, action) tuples to bound handler methods.
            Example: {("awareness", "campaigns"): self.cmd_campaigns}
        """
        ...

    @classmethod
    @abstractmethod
    def register_parsers(cls, subparsers: Any, make_common_parser: Callable) -> None:
        """Register argparse subparsers for this domain's commands.

        Args:
            subparsers: The top-level argparse subparsers action
            make_common_parser: Factory function that returns a fresh argparse parent
                parser with --output and --profile flags. MUST call this function
                per sub-parser (argparse parents are stateful — sharing one instance
                causes duplicate action errors).

        Example:
            p = subparsers.add_parser("myresource", help="My resource ops")
            sub = p.add_subparsers(dest="action")
            list_p = sub.add_parser("list", parents=[make_common_parser()])
            list_p.add_argument("--filter", help="Filter by name")
        """
        ...
