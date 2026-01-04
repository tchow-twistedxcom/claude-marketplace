#!/usr/bin/env python3
"""
Amazon SP-API Notifications API Module

Provides classes for managing event subscriptions, destinations,
and real-time notifications for orders, inventory, and other events.
"""

import json
import sys
from typing import Optional, Dict, Any, List

from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient


class NotificationsAPI:
    """Notifications API for managing event subscriptions."""

    def __init__(self, client: SPAPIClient):
        self.client = client
        self.auth = client.auth

    # Destination Management
    def get_destinations(self) -> Dict[str, Any]:
        """
        Get all notification destinations.

        Returns:
            List of configured destinations
        """
        status, data = self.client.get(
            "/notifications/v1/destinations",
            "notifications"
        )
        return data

    def get_destination(self, destination_id: str) -> Dict[str, Any]:
        """
        Get a specific destination.

        Args:
            destination_id: Destination ID

        Returns:
            Destination details
        """
        status, data = self.client.get(
            f"/notifications/v1/destinations/{destination_id}",
            "notifications"
        )
        return data

    def create_destination(
        self,
        name: str,
        resource_specification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a notification destination.

        Args:
            name: Destination name
            resource_specification: SQS or EventBridge configuration

        Example resource_specification for SQS:
            {
                "sqs": {
                    "arn": "arn:aws:sqs:us-east-1:123456789:my-queue"
                }
            }

        Example for EventBridge:
            {
                "eventBridge": {
                    "accountId": "123456789",
                    "region": "us-east-1"
                }
            }

        Returns:
            Created destination with destinationId
        """
        data = {
            "name": name,
            "resourceSpecification": resource_specification
        }

        status, response = self.client.post(
            "/notifications/v1/destinations",
            "notifications",
            data=data
        )
        return response

    def delete_destination(self, destination_id: str) -> Dict[str, Any]:
        """
        Delete a notification destination.

        Args:
            destination_id: Destination ID

        Returns:
            Deletion result
        """
        status, response = self.client.delete(
            f"/notifications/v1/destinations/{destination_id}",
            "notifications"
        )
        return response

    # Subscription Management
    def get_subscription(self, notification_type: str) -> Dict[str, Any]:
        """
        Get subscription for a notification type.

        Args:
            notification_type: Type of notification (see NOTIFICATION_TYPES)

        Returns:
            Subscription details
        """
        status, data = self.client.get(
            f"/notifications/v1/subscriptions/{notification_type}",
            "notifications"
        )
        return data

    def create_subscription(
        self,
        notification_type: str,
        destination_id: str,
        payload_version: str = "1.0",
        processing_directive: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a subscription for a notification type.

        Args:
            notification_type: Type of notification
            destination_id: Destination ID for notifications
            payload_version: Notification payload version
            processing_directive: Optional filtering rules

        Returns:
            Created subscription with subscriptionId
        """
        data = {
            "destinationId": destination_id,
            "payloadVersion": payload_version
        }

        if processing_directive:
            data["processingDirective"] = processing_directive

        status, response = self.client.post(
            f"/notifications/v1/subscriptions/{notification_type}",
            "notifications",
            data=data
        )
        return response

    def delete_subscription(
        self,
        notification_type: str,
        subscription_id: str
    ) -> Dict[str, Any]:
        """
        Delete a subscription.

        Args:
            notification_type: Type of notification
            subscription_id: Subscription ID

        Returns:
            Deletion result
        """
        status, response = self.client.delete(
            f"/notifications/v1/subscriptions/{notification_type}/{subscription_id}",
            "notifications"
        )
        return response


class ProductPricingAPI:
    """Product Pricing API for pricing data and estimates."""

    def __init__(self, client: SPAPIClient):
        self.client = client
        self.auth = client.auth

    def get_competitive_pricing(
        self,
        item_type: str,
        asins: Optional[List[str]] = None,
        skus: Optional[List[str]] = None,
        marketplace_id: Optional[str] = None,
        customer_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get competitive pricing for items.

        Args:
            item_type: Asin or Sku
            asins: List of ASINs (if item_type is Asin)
            skus: List of SKUs (if item_type is Sku)
            marketplace_id: Marketplace ID
            customer_type: Consumer or Business

        Returns:
            Competitive pricing data
        """
        params = {
            "MarketplaceId": marketplace_id or self.auth.get_marketplace_id(),
            "ItemType": item_type
        }

        if item_type == "Asin" and asins:
            params["Asins"] = ",".join(asins)
        elif item_type == "Sku" and skus:
            params["Skus"] = ",".join(skus)

        if customer_type:
            params["CustomerType"] = customer_type

        status, data = self.client.get(
            "/products/pricing/v0/competitivePrice",
            "pricing",
            params=params
        )
        return data

    def get_item_offers(
        self,
        asin: str,
        item_condition: str = "New",
        marketplace_id: Optional[str] = None,
        customer_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get offers for an item.

        Args:
            asin: Amazon ASIN
            item_condition: New, Used, Collectible, Refurbished, Club
            marketplace_id: Marketplace ID
            customer_type: Consumer or Business

        Returns:
            Item offers with pricing
        """
        params = {
            "MarketplaceId": marketplace_id or self.auth.get_marketplace_id(),
            "ItemCondition": item_condition
        }

        if customer_type:
            params["CustomerType"] = customer_type

        status, data = self.client.get(
            f"/products/pricing/v0/items/{asin}/offers",
            "pricing",
            params=params
        )
        return data

    def get_listing_offers(
        self,
        seller_sku: str,
        item_condition: str = "New",
        marketplace_id: Optional[str] = None,
        customer_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get offers for a listing.

        Args:
            seller_sku: Seller SKU
            item_condition: Item condition
            marketplace_id: Marketplace ID
            customer_type: Consumer or Business

        Returns:
            Listing offers with pricing
        """
        params = {
            "MarketplaceId": marketplace_id or self.auth.get_marketplace_id(),
            "ItemCondition": item_condition
        }

        if customer_type:
            params["CustomerType"] = customer_type

        status, data = self.client.get(
            f"/products/pricing/v0/listings/{seller_sku}/offers",
            "pricing",
            params=params
        )
        return data

    def get_pricing(
        self,
        item_type: str,
        asins: Optional[List[str]] = None,
        skus: Optional[List[str]] = None,
        marketplace_id: Optional[str] = None,
        item_condition: Optional[str] = None,
        offer_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get pricing for items.

        Args:
            item_type: Asin or Sku
            asins: List of ASINs
            skus: List of SKUs
            marketplace_id: Marketplace ID
            item_condition: Item condition filter
            offer_type: B2C or B2B

        Returns:
            Pricing data
        """
        params = {
            "MarketplaceId": marketplace_id or self.auth.get_marketplace_id(),
            "ItemType": item_type
        }

        if item_type == "Asin" and asins:
            params["Asins"] = ",".join(asins)
        elif item_type == "Sku" and skus:
            params["Skus"] = ",".join(skus)

        if item_condition:
            params["ItemCondition"] = item_condition
        if offer_type:
            params["OfferType"] = offer_type

        status, data = self.client.get(
            "/products/pricing/v0/price",
            "pricing",
            params=params
        )
        return data


class FinancesAPI:
    """Finances API for financial events and settlements."""

    def __init__(self, client: SPAPIClient):
        self.client = client
        self.auth = client.auth

    def list_financial_events(
        self,
        posted_after: Optional[str] = None,
        posted_before: Optional[str] = None,
        max_results_per_page: int = 100,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List financial events.

        Args:
            posted_after: ISO 8601 datetime
            posted_before: ISO 8601 datetime
            max_results_per_page: 1-100
            next_token: Pagination token

        Returns:
            Financial events
        """
        params = {
            "MaxResultsPerPage": str(max_results_per_page)
        }

        if posted_after:
            params["PostedAfter"] = posted_after
        if posted_before:
            params["PostedBefore"] = posted_before
        if next_token:
            params["NextToken"] = next_token

        status, data = self.client.get(
            "/finances/v0/financialEvents",
            "finances",
            params=params
        )
        return data

    def list_financial_events_by_group(
        self,
        event_group_id: str,
        posted_after: Optional[str] = None,
        posted_before: Optional[str] = None,
        max_results_per_page: int = 100,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List financial events for a group.

        Args:
            event_group_id: Financial event group ID
            posted_after: ISO 8601 datetime
            posted_before: ISO 8601 datetime
            max_results_per_page: 1-100
            next_token: Pagination token

        Returns:
            Financial events for group
        """
        params = {
            "MaxResultsPerPage": str(max_results_per_page)
        }

        if posted_after:
            params["PostedAfter"] = posted_after
        if posted_before:
            params["PostedBefore"] = posted_before
        if next_token:
            params["NextToken"] = next_token

        status, data = self.client.get(
            f"/finances/v0/financialEventGroups/{event_group_id}/financialEvents",
            "finances",
            params=params
        )
        return data

    def list_financial_events_by_order(
        self,
        order_id: str,
        max_results_per_page: int = 100,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List financial events for an order.

        Args:
            order_id: Amazon order ID
            max_results_per_page: 1-100
            next_token: Pagination token

        Returns:
            Financial events for order
        """
        params = {
            "MaxResultsPerPage": str(max_results_per_page)
        }

        if next_token:
            params["NextToken"] = next_token

        status, data = self.client.get(
            f"/finances/v0/orders/{order_id}/financialEvents",
            "finances",
            params=params
        )
        return data

    def list_financial_event_groups(
        self,
        financial_event_group_started_after: Optional[str] = None,
        financial_event_group_started_before: Optional[str] = None,
        max_results_per_page: int = 10,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List financial event groups (settlement periods).

        Args:
            financial_event_group_started_after: ISO 8601 datetime
            financial_event_group_started_before: ISO 8601 datetime
            max_results_per_page: 1-100
            next_token: Pagination token

        Returns:
            Financial event groups
        """
        params = {
            "MaxResultsPerPage": str(max_results_per_page)
        }

        if financial_event_group_started_after:
            params["FinancialEventGroupStartedAfter"] = financial_event_group_started_after
        if financial_event_group_started_before:
            params["FinancialEventGroupStartedBefore"] = financial_event_group_started_before
        if next_token:
            params["NextToken"] = next_token

        status, data = self.client.get(
            "/finances/v0/financialEventGroups",
            "finances",
            params=params
        )
        return data


# Notification types
NOTIFICATION_TYPES = [
    "ANY_OFFER_CHANGED",              # Buy Box or pricing changes
    "B2B_ANY_OFFER_CHANGED",          # B2B pricing changes
    "BRANDED_ITEM_CONTENT_CHANGE",    # Brand content updates
    "FBA_OUTBOUND_SHIPMENT_STATUS",   # FBA shipment updates
    "FEE_PROMOTION_NOTIFICATION",     # Fee changes
    "FEED_PROCESSING_FINISHED",       # Feed completion
    "FULFILLMENT_ORDER_STATUS",       # MCF status updates
    "ITEM_INVENTORY_EVENT_CHANGE",    # Inventory changes
    "ITEM_PRODUCT_TYPE_CHANGE",       # Product type changes
    "ITEM_SALES_EVENT_CHANGE",        # Sales changes
    "LISTINGS_ITEM_ISSUES_CHANGE",    # Listing issues
    "LISTINGS_ITEM_STATUS_CHANGE",    # Listing status changes
    "LISTINGS_ITEM_MFN_QUANTITY_CHANGE",  # MFN quantity changes
    "ORDER_CHANGE",                   # Order status changes
    "ORDER_STATUS_CHANGE",            # Order lifecycle events
    "PRICING_HEALTH_NOTIFICATION",    # Pricing health alerts
    "PRODUCT_TYPE_DEFINITIONS_CHANGE", # Product type schema changes
    "REPORT_PROCESSING_FINISHED"      # Report ready
]

# Event Bridge regions
EVENT_BRIDGE_REGIONS = {
    "NA": "us-east-1",
    "EU": "eu-west-1",
    "FE": "us-west-2"
}


# Helper functions
def create_sqs_destination(
    client: SPAPIClient,
    name: str,
    sqs_arn: str
) -> Dict[str, Any]:
    """
    Create an SQS notification destination.

    Args:
        client: SPAPIClient instance
        name: Destination name
        sqs_arn: SQS queue ARN

    Returns:
        Created destination
    """
    api = NotificationsAPI(client)
    return api.create_destination(
        name=name,
        resource_specification={
            "sqs": {"arn": sqs_arn}
        }
    )


def create_eventbridge_destination(
    client: SPAPIClient,
    name: str,
    account_id: str,
    region: str
) -> Dict[str, Any]:
    """
    Create an EventBridge notification destination.

    Args:
        client: SPAPIClient instance
        name: Destination name
        account_id: AWS account ID
        region: AWS region

    Returns:
        Created destination
    """
    api = NotificationsAPI(client)
    return api.create_destination(
        name=name,
        resource_specification={
            "eventBridge": {
                "accountId": account_id,
                "region": region
            }
        }
    )


def subscribe_to_notifications(
    client: SPAPIClient,
    notification_type: str,
    destination_id: str
) -> Dict[str, Any]:
    """
    Subscribe to a notification type.

    Args:
        client: SPAPIClient instance
        notification_type: Type of notification
        destination_id: Destination ID

    Returns:
        Subscription details
    """
    api = NotificationsAPI(client)
    return api.create_subscription(
        notification_type=notification_type,
        destination_id=destination_id
    )


def get_competitive_pricing(
    client: SPAPIClient,
    asins: List[str]
) -> Dict[str, Any]:
    """
    Get competitive pricing for ASINs.

    Args:
        client: SPAPIClient instance
        asins: List of ASINs

    Returns:
        Competitive pricing data
    """
    api = ProductPricingAPI(client)
    return api.get_competitive_pricing(
        item_type="Asin",
        asins=asins
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SP-API Notifications & Pricing Operations")
    parser.add_argument("command", choices=["destinations", "subscriptions", "pricing",
                                            "finances", "events"],
                        help="Operation to perform")
    parser.add_argument("--notification-type", help="Notification type")
    parser.add_argument("--destination-id", help="Destination ID")
    parser.add_argument("--asin", action="append", help="ASIN (can specify multiple)")
    parser.add_argument("--days", type=int, default=30, help="Days to look back")
    parser.add_argument("--profile", default="production", help="Config profile")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    auth = SPAPIAuth(profile=args.profile)
    client = SPAPIClient(auth)

    try:
        if args.command == "destinations":
            api = NotificationsAPI(client)
            result = api.get_destinations()

        elif args.command == "subscriptions":
            if not args.notification_type:
                print("Error: --notification-type required", file=sys.stderr)
                sys.exit(1)
            api = NotificationsAPI(client)
            result = api.get_subscription(args.notification_type)

        elif args.command == "pricing":
            if not args.asin:
                print("Error: --asin required", file=sys.stderr)
                sys.exit(1)
            result = get_competitive_pricing(client, args.asin)

        elif args.command == "finances":
            api = FinancesAPI(client)
            from datetime import datetime, timedelta
            posted_after = (datetime.utcnow() - timedelta(days=args.days)).strftime("%Y-%m-%dT00:00:00Z")
            result = api.list_financial_event_groups(
                financial_event_group_started_after=posted_after
            )

        elif args.command == "events":
            api = FinancesAPI(client)
            from datetime import datetime, timedelta
            posted_after = (datetime.utcnow() - timedelta(days=args.days)).strftime("%Y-%m-%dT00:00:00Z")
            result = api.list_financial_events(posted_after=posted_after)

        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            payload = result.get("payload", result)
            print(json.dumps(payload, indent=2, default=str))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
