#!/usr/bin/env python3
"""
Amazon Selling Partner API CLI

Unified command-line interface for SP-API operations.
Supports vendor, seller, catalog, inventory, reports, and notification operations.

Usage:
    python3 spapi_api.py <command> <subcommand> [options]

Examples:
    python3 spapi_api.py vendor-orders list --created-after 2024-01-01
    python3 spapi_api.py catalog search --keywords laptop
    python3 spapi_api.py reports create --type GET_VENDOR_INVENTORY_REPORT
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

# Import modules
from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient
from spapi_vendor import (
    VendorOrdersAPI, VendorShipmentsAPI, VendorInvoicesAPI,
    VendorTransactionStatusAPI
)
from spapi_orders import OrdersAPI, get_recent_orders, get_order_with_items
from spapi_catalog import (
    CatalogItemsAPI, ListingsItemsAPI, ProductTypeDefinitionsAPI,
    search_by_asin, search_by_keywords
)
from spapi_inventory import (
    FBAInventoryAPI, FulfillmentInboundAPI, FulfillmentOutboundAPI,
    get_all_inventory, get_low_inventory
)
from spapi_reports import ReportsAPI, FeedsAPI, VENDOR_REPORT_TYPES, SELLER_REPORT_TYPES
from spapi_notifications import (
    NotificationsAPI, ProductPricingAPI, FinancesAPI,
    NOTIFICATION_TYPES
)


def format_output(data: Any, output_format: str = "json", indent: int = 2) -> str:
    """Format output based on requested format."""
    if output_format == "json":
        return json.dumps(data, indent=indent, default=str)
    elif output_format == "table":
        # Simple table formatting
        if isinstance(data, list):
            if not data:
                return "No results"
            if isinstance(data[0], dict):
                headers = list(data[0].keys())[:5]  # First 5 columns
                lines = ["\t".join(headers)]
                for row in data[:20]:
                    lines.append("\t".join(str(row.get(h, ""))[:30] for h in headers))
                if len(data) > 20:
                    lines.append(f"... and {len(data) - 20} more rows")
                return "\n".join(lines)
        return json.dumps(data, indent=indent, default=str)
    return str(data)


def get_date_range(days: int = 30) -> tuple:
    """Get ISO 8601 date range for the last N days."""
    from datetime import timezone
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return start.strftime("%Y-%m-%dT00:00:00Z"), end.strftime("%Y-%m-%dT23:59:59Z")


# Command handlers
def handle_vendor_orders(args, client: SPAPIClient) -> Dict[str, Any]:
    """Handle vendor-orders commands."""
    api = VendorOrdersAPI(client)

    if args.action == "list":
        start, end = get_date_range(args.days)
        return api.get_purchase_orders(
            created_after=args.created_after or start,
            created_before=args.created_before or end,
            purchase_order_state=args.status,
            limit=args.limit
        )

    elif args.action == "get":
        if not args.po_number:
            raise ValueError("--po-number required")
        return api.get_purchase_order(args.po_number)

    elif args.action == "acknowledge":
        if not args.po_number or not args.file:
            raise ValueError("--po-number and --file required")
        with open(args.file) as f:
            data = json.load(f)
        return api.submit_acknowledgement(data)

    elif args.action == "status":
        return api.get_purchase_orders_status(
            purchase_order_number=args.po_number
        )


def handle_vendor_shipments(args, client: SPAPIClient) -> Dict[str, Any]:
    """Handle vendor-shipments commands."""
    api = VendorShipmentsAPI(client)

    if args.action == "submit":
        if not args.file:
            raise ValueError("--file required")
        with open(args.file) as f:
            data = json.load(f)
        return api.submit_shipment_confirmations(data)

    elif args.action == "details":
        return api.get_shipment_details(
            shipment_id=args.shipment_id,
            po_number=args.po_number
        )

    elif args.action == "labels":
        if not args.po_number:
            raise ValueError("--po-number required")
        return api.get_shipment_labels(args.po_number)


def handle_vendor_invoices(args, client: SPAPIClient) -> Dict[str, Any]:
    """Handle vendor-invoices commands."""
    api = VendorInvoicesAPI(client)

    if args.action == "submit":
        if not args.file:
            raise ValueError("--file required")
        with open(args.file) as f:
            data = json.load(f)
        return api.submit_invoices(data)


def handle_orders(args, client: SPAPIClient) -> Dict[str, Any]:
    """Handle orders commands."""
    api = OrdersAPI(client)

    if args.action == "list":
        start, _ = get_date_range(args.days)
        return api.get_orders(
            created_after=args.created_after or start,
            order_statuses=[args.status] if args.status else None,
            max_results_per_page=args.limit
        )

    elif args.action == "get":
        if not args.order_id:
            raise ValueError("--order-id required")
        return get_order_with_items(client, args.order_id)

    elif args.action == "items":
        if not args.order_id:
            raise ValueError("--order-id required")
        return api.get_order_items(args.order_id)

    elif args.action == "buyer":
        if not args.order_id:
            raise ValueError("--order-id required")
        return api.get_order_buyer_info(args.order_id)


def handle_catalog(args, client: SPAPIClient) -> Dict[str, Any]:
    """Handle catalog commands."""
    api = CatalogItemsAPI(client)

    if args.action == "search":
        if not args.keywords:
            raise ValueError("--keywords required")
        return search_by_keywords(client, args.keywords.split(","), args.limit)

    elif args.action == "get":
        if not args.asin:
            raise ValueError("--asin required")
        return search_by_asin(client, args.asin)


def handle_listings(args, client: SPAPIClient) -> Dict[str, Any]:
    """Handle listings commands."""
    api = ListingsItemsAPI(client)

    if args.action == "get":
        if not args.seller_id or not args.sku:
            raise ValueError("--seller-id and --sku required")
        return api.get_listings_item(
            seller_id=args.seller_id,
            sku=args.sku,
            included_data=["summaries", "attributes", "issues", "offers"]
        )

    elif args.action == "create":
        if not all([args.seller_id, args.sku, args.product_type, args.file]):
            raise ValueError("--seller-id, --sku, --product-type, and --file required")
        with open(args.file) as f:
            attributes = json.load(f)
        return api.put_listings_item(
            seller_id=args.seller_id,
            sku=args.sku,
            marketplace_ids=[client.auth.get_marketplace_id()],
            product_type=args.product_type,
            attributes=attributes
        )

    elif args.action == "delete":
        if not args.seller_id or not args.sku:
            raise ValueError("--seller-id and --sku required")
        return api.delete_listings_item(
            seller_id=args.seller_id,
            sku=args.sku,
            marketplace_ids=[client.auth.get_marketplace_id()]
        )


def handle_inventory(args, client: SPAPIClient) -> Dict[str, Any]:
    """Handle inventory commands."""
    if args.action == "list":
        return get_all_inventory(client)

    elif args.action == "low":
        return get_low_inventory(client, args.threshold)

    elif args.action == "sku":
        if not args.sku:
            raise ValueError("--sku required")
        api = FBAInventoryAPI(client)
        return api.get_inventory_summaries(seller_skus=args.sku, details=True)


def handle_reports(args, client: SPAPIClient) -> Dict[str, Any]:
    """Handle reports commands."""
    api = ReportsAPI(client)

    if args.action == "list":
        return api.get_reports(
            report_types=[args.type] if args.type else None,
            processing_statuses=[args.status] if args.status else None,
            page_size=args.limit
        )

    elif args.action == "create":
        if not args.type:
            raise ValueError("--type required")
        start, end = get_date_range(args.days)
        return api.create_report(
            report_type=args.type,
            data_start_time=args.start_date or start,
            data_end_time=args.end_date or end
        )

    elif args.action == "get":
        if not args.report_id:
            raise ValueError("--report-id required")
        return api.get_report(args.report_id)

    elif args.action == "download":
        if not args.document_id:
            raise ValueError("--document-id required")
        content = api.download_report(args.document_id)
        print(content)
        return {"status": "downloaded"}

    elif args.action == "types":
        return {
            "vendor": VENDOR_REPORT_TYPES,
            "seller": SELLER_REPORT_TYPES
        }


def handle_feeds(args, client: SPAPIClient) -> Dict[str, Any]:
    """Handle feeds commands."""
    api = FeedsAPI(client)

    if args.action == "list":
        return api.get_feeds(
            feed_types=[args.type] if args.type else None,
            processing_statuses=[args.status] if args.status else None,
            page_size=args.limit
        )

    elif args.action == "get":
        if not args.feed_id:
            raise ValueError("--feed-id required")
        return api.get_feed(args.feed_id)

    elif args.action == "submit":
        if not args.type or not args.file:
            raise ValueError("--type and --file required")
        with open(args.file, "rb") as f:
            content = f.read()
        return api.submit_feed(
            feed_type=args.type,
            content=content,
            wait=not args.no_wait
        )


def handle_notifications(args, client: SPAPIClient) -> Dict[str, Any]:
    """Handle notifications commands."""
    api = NotificationsAPI(client)

    if args.action == "destinations":
        return api.get_destinations()

    elif args.action == "create-destination":
        if not args.name:
            raise ValueError("--name required")
        if args.sqs_arn:
            return api.create_destination(
                name=args.name,
                resource_specification={"sqs": {"arn": args.sqs_arn}}
            )
        elif args.eventbridge_account and args.eventbridge_region:
            return api.create_destination(
                name=args.name,
                resource_specification={
                    "eventBridge": {
                        "accountId": args.eventbridge_account,
                        "region": args.eventbridge_region
                    }
                }
            )
        else:
            raise ValueError("--sqs-arn or (--eventbridge-account and --eventbridge-region) required")

    elif args.action == "subscriptions":
        if not args.notification_type:
            raise ValueError("--notification-type required")
        return api.get_subscription(args.notification_type)

    elif args.action == "subscribe":
        if not args.notification_type or not args.destination_id:
            raise ValueError("--notification-type and --destination-id required")
        return api.create_subscription(
            notification_type=args.notification_type,
            destination_id=args.destination_id
        )

    elif args.action == "types":
        return {"notification_types": NOTIFICATION_TYPES}


def handle_pricing(args, client: SPAPIClient) -> Dict[str, Any]:
    """Handle pricing commands."""
    api = ProductPricingAPI(client)

    if args.action == "competitive":
        if not args.asin:
            raise ValueError("--asin required")
        return api.get_competitive_pricing(
            item_type="Asin",
            asins=args.asin
        )

    elif args.action == "offers":
        if not args.asin:
            raise ValueError("--asin required")
        return api.get_item_offers(args.asin[0])


def handle_finances(args, client: SPAPIClient) -> Dict[str, Any]:
    """Handle finances commands."""
    api = FinancesAPI(client)
    start, _ = get_date_range(args.days)

    if args.action == "events":
        return api.list_financial_events(posted_after=start)

    elif args.action == "groups":
        return api.list_financial_event_groups(
            financial_event_group_started_after=start
        )

    elif args.action == "order":
        if not args.order_id:
            raise ValueError("--order-id required")
        return api.list_financial_events_by_order(args.order_id)


def main():
    parser = argparse.ArgumentParser(
        description="Amazon Selling Partner API CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Vendor Operations
  spapi_api.py vendor-orders list --days 7
  spapi_api.py vendor-orders get --po-number PO123456
  spapi_api.py vendor-shipments submit --file asn.json
  spapi_api.py vendor-invoices submit --file invoice.json

  # Seller Operations
  spapi_api.py orders list --status Unshipped
  spapi_api.py catalog search --keywords "laptop bag"
  spapi_api.py inventory list
  spapi_api.py inventory low --threshold 5

  # Reports & Feeds
  spapi_api.py reports create --type GET_VENDOR_INVENTORY_REPORT
  spapi_api.py reports list --status DONE
  spapi_api.py feeds submit --type POST_INVENTORY_AVAILABILITY_DATA --file feed.xml

  # Notifications
  spapi_api.py notifications destinations
  spapi_api.py notifications subscribe --notification-type ORDER_CHANGE --destination-id dest123
        """
    )

    # Global options
    parser.add_argument("--profile", default="production", help="Config profile (default: production)")
    parser.add_argument("--output", "-o", choices=["json", "table"], default="json", help="Output format")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    subparsers = parser.add_subparsers(dest="command", help="Command category")

    # Vendor Orders
    vendor_orders = subparsers.add_parser("vendor-orders", help="Vendor purchase order operations")
    vendor_orders.add_argument("action", choices=["list", "get", "acknowledge", "status"])
    vendor_orders.add_argument("--po-number", help="Purchase order number")
    vendor_orders.add_argument("--created-after", help="Filter by creation date (ISO 8601)")
    vendor_orders.add_argument("--created-before", help="Filter by creation date (ISO 8601)")
    vendor_orders.add_argument("--status", help="PO status filter")
    vendor_orders.add_argument("--days", type=int, default=30, help="Days to look back")
    vendor_orders.add_argument("--limit", type=int, default=100, help="Max results")
    vendor_orders.add_argument("--file", help="JSON file for acknowledgement")

    # Vendor Shipments
    vendor_shipments = subparsers.add_parser("vendor-shipments", help="Vendor shipment operations")
    vendor_shipments.add_argument("action", choices=["submit", "details", "labels"])
    vendor_shipments.add_argument("--shipment-id", help="Shipment ID")
    vendor_shipments.add_argument("--po-number", help="Purchase order number")
    vendor_shipments.add_argument("--file", help="JSON file for ASN")

    # Vendor Invoices
    vendor_invoices = subparsers.add_parser("vendor-invoices", help="Vendor invoice operations")
    vendor_invoices.add_argument("action", choices=["submit"])
    vendor_invoices.add_argument("--file", required=True, help="JSON file for invoice")

    # Orders (Seller)
    orders = subparsers.add_parser("orders", help="Seller order operations")
    orders.add_argument("action", choices=["list", "get", "items", "buyer"])
    orders.add_argument("--order-id", help="Amazon order ID")
    orders.add_argument("--created-after", help="Filter by creation date (ISO 8601)")
    orders.add_argument("--status", help="Order status filter")
    orders.add_argument("--days", type=int, default=7, help="Days to look back")
    orders.add_argument("--limit", type=int, default=100, help="Max results")

    # Catalog
    catalog = subparsers.add_parser("catalog", help="Catalog item operations")
    catalog.add_argument("action", choices=["search", "get"])
    catalog.add_argument("--keywords", help="Search keywords (comma-separated)")
    catalog.add_argument("--asin", help="Amazon ASIN")
    catalog.add_argument("--limit", type=int, default=20, help="Max results")

    # Listings
    listings = subparsers.add_parser("listings", help="Listing operations")
    listings.add_argument("action", choices=["get", "create", "delete"])
    listings.add_argument("--seller-id", help="Seller ID")
    listings.add_argument("--sku", help="Seller SKU")
    listings.add_argument("--product-type", help="Amazon product type")
    listings.add_argument("--file", help="JSON file for attributes")

    # Inventory
    inventory = subparsers.add_parser("inventory", help="FBA inventory operations")
    inventory.add_argument("action", choices=["list", "low", "sku"])
    inventory.add_argument("--sku", nargs="+", help="Seller SKU(s)")
    inventory.add_argument("--threshold", type=int, default=10, help="Low inventory threshold")

    # Reports
    reports = subparsers.add_parser("reports", help="Report operations")
    reports.add_argument("action", choices=["list", "create", "get", "download", "types"])
    reports.add_argument("--type", help="Report type")
    reports.add_argument("--report-id", help="Report ID")
    reports.add_argument("--document-id", help="Document ID for download")
    reports.add_argument("--status", help="Processing status filter")
    reports.add_argument("--start-date", help="Data start date (ISO 8601)")
    reports.add_argument("--end-date", help="Data end date (ISO 8601)")
    reports.add_argument("--days", type=int, default=30, help="Days for date range")
    reports.add_argument("--limit", type=int, default=10, help="Max results")

    # Feeds
    feeds = subparsers.add_parser("feeds", help="Feed operations")
    feeds.add_argument("action", choices=["list", "get", "submit"])
    feeds.add_argument("--type", help="Feed type")
    feeds.add_argument("--feed-id", help="Feed ID")
    feeds.add_argument("--status", help="Processing status filter")
    feeds.add_argument("--file", help="Feed content file")
    feeds.add_argument("--no-wait", action="store_true", help="Don't wait for completion")
    feeds.add_argument("--limit", type=int, default=10, help="Max results")

    # Notifications
    notifications = subparsers.add_parser("notifications", help="Notification operations")
    notifications.add_argument("action", choices=["destinations", "create-destination", "subscriptions", "subscribe", "types"])
    notifications.add_argument("--name", help="Destination name")
    notifications.add_argument("--sqs-arn", help="SQS queue ARN")
    notifications.add_argument("--eventbridge-account", help="EventBridge AWS account ID")
    notifications.add_argument("--eventbridge-region", help="EventBridge AWS region")
    notifications.add_argument("--notification-type", help="Notification type")
    notifications.add_argument("--destination-id", help="Destination ID")

    # Pricing
    pricing = subparsers.add_parser("pricing", help="Pricing operations")
    pricing.add_argument("action", choices=["competitive", "offers"])
    pricing.add_argument("--asin", nargs="+", help="ASIN(s)")

    # Finances
    finances = subparsers.add_parser("finances", help="Financial operations")
    finances.add_argument("action", choices=["events", "groups", "order"])
    finances.add_argument("--order-id", help="Amazon order ID")
    finances.add_argument("--days", type=int, default=30, help="Days to look back")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        # Initialize client
        auth = SPAPIAuth(profile=args.profile)
        client = SPAPIClient(auth)

        # Route to handler
        handlers = {
            "vendor-orders": handle_vendor_orders,
            "vendor-shipments": handle_vendor_shipments,
            "vendor-invoices": handle_vendor_invoices,
            "orders": handle_orders,
            "catalog": handle_catalog,
            "listings": handle_listings,
            "inventory": handle_inventory,
            "reports": handle_reports,
            "feeds": handle_feeds,
            "notifications": handle_notifications,
            "pricing": handle_pricing,
            "finances": handle_finances
        }

        handler = handlers.get(args.command)
        if not handler:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            sys.exit(1)

        result = handler(args, client)

        # Output result
        output = format_output(result, args.output)
        print(output)

    except FileNotFoundError as e:
        print(f"File not found: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        if args.debug:
            raise
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
