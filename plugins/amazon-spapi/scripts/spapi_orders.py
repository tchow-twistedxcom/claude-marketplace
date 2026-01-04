#!/usr/bin/env python3
"""
Amazon SP-API Orders API Module

Provides classes for managing orders through the Selling Partner API.
Supports order retrieval, order items, buyer info, and shipping address.
"""

import json
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Iterator

from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient


class OrdersAPI:
    """Orders API operations for retrieving and managing orders."""

    def __init__(self, client: SPAPIClient):
        self.client = client
        self.auth = client.auth

    def get_orders(
        self,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        last_updated_after: Optional[str] = None,
        last_updated_before: Optional[str] = None,
        order_statuses: Optional[List[str]] = None,
        fulfillment_channels: Optional[List[str]] = None,
        payment_methods: Optional[List[str]] = None,
        buyer_email: Optional[str] = None,
        seller_order_id: Optional[str] = None,
        max_results_per_page: int = 100,
        easy_ship_shipment_statuses: Optional[List[str]] = None,
        electronic_invoice_statuses: Optional[List[str]] = None,
        next_token: Optional[str] = None,
        amazon_order_ids: Optional[List[str]] = None,
        actual_fulfillment_supply_source_id: Optional[str] = None,
        is_ispu: Optional[bool] = None,
        store_chain_store_id: Optional[str] = None,
        earliest_delivery_date_before: Optional[str] = None,
        earliest_delivery_date_after: Optional[str] = None,
        latest_delivery_date_before: Optional[str] = None,
        latest_delivery_date_after: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get orders based on filter criteria.

        Args:
            created_after: ISO 8601 datetime - orders created after
            created_before: ISO 8601 datetime - orders created before
            last_updated_after: ISO 8601 datetime - orders updated after
            last_updated_before: ISO 8601 datetime - orders updated before
            order_statuses: List of order statuses to filter
            fulfillment_channels: AFN (FBA), MFN (Merchant)
            payment_methods: COD, CVS, Other
            buyer_email: Email address of buyer
            seller_order_id: Seller's order identifier
            max_results_per_page: 1-100 (default 100)
            easy_ship_shipment_statuses: For Easy Ship orders
            electronic_invoice_statuses: For electronic invoices
            next_token: Pagination token
            amazon_order_ids: List of Amazon order IDs (max 50)
            actual_fulfillment_supply_source_id: Supply source filter
            is_ispu: Is In-Store Pickup
            store_chain_store_id: Store chain filter
            earliest_delivery_date_before: Delivery date filter
            earliest_delivery_date_after: Delivery date filter
            latest_delivery_date_before: Delivery date filter
            latest_delivery_date_after: Delivery date filter

        Returns:
            Orders response with payload containing Orders array
        """
        params = {
            "MarketplaceIds": self.auth.get_marketplace_id()
        }

        if created_after:
            params["CreatedAfter"] = created_after
        if created_before:
            params["CreatedBefore"] = created_before
        if last_updated_after:
            params["LastUpdatedAfter"] = last_updated_after
        if last_updated_before:
            params["LastUpdatedBefore"] = last_updated_before
        if order_statuses:
            params["OrderStatuses"] = ",".join(order_statuses)
        if fulfillment_channels:
            params["FulfillmentChannels"] = ",".join(fulfillment_channels)
        if payment_methods:
            params["PaymentMethods"] = ",".join(payment_methods)
        if buyer_email:
            params["BuyerEmail"] = buyer_email
        if seller_order_id:
            params["SellerOrderId"] = seller_order_id
        if max_results_per_page:
            params["MaxResultsPerPage"] = str(max_results_per_page)
        if easy_ship_shipment_statuses:
            params["EasyShipShipmentStatuses"] = ",".join(easy_ship_shipment_statuses)
        if electronic_invoice_statuses:
            params["ElectronicInvoiceStatuses"] = ",".join(electronic_invoice_statuses)
        if next_token:
            params["NextToken"] = next_token
        if amazon_order_ids:
            params["AmazonOrderIds"] = ",".join(amazon_order_ids)
        if actual_fulfillment_supply_source_id:
            params["ActualFulfillmentSupplySourceId"] = actual_fulfillment_supply_source_id
        if is_ispu is not None:
            params["IsISPU"] = str(is_ispu).lower()
        if store_chain_store_id:
            params["StoreChainStoreId"] = store_chain_store_id
        if earliest_delivery_date_before:
            params["EarliestDeliveryDateBefore"] = earliest_delivery_date_before
        if earliest_delivery_date_after:
            params["EarliestDeliveryDateAfter"] = earliest_delivery_date_after
        if latest_delivery_date_before:
            params["LatestDeliveryDateBefore"] = latest_delivery_date_before
        if latest_delivery_date_after:
            params["LatestDeliveryDateAfter"] = latest_delivery_date_after

        status, data = self.client.get(
            "/orders/v0/orders",
            "orders",
            params=params
        )
        return data

    def get_order(self, order_id: str) -> Dict[str, Any]:
        """
        Get details for a specific order.

        Args:
            order_id: Amazon order ID (e.g., 123-1234567-1234567)

        Returns:
            Order details
        """
        status, data = self.client.get(
            f"/orders/v0/orders/{order_id}",
            "orders.getOrder"
        )
        return data

    def get_order_items(
        self,
        order_id: str,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get order items for a specific order.

        Args:
            order_id: Amazon order ID
            next_token: Pagination token

        Returns:
            Order items with ASIN, quantity, price details
        """
        params = {}
        if next_token:
            params["NextToken"] = next_token

        status, data = self.client.get(
            f"/orders/v0/orders/{order_id}/orderItems",
            "orders.getOrderItems",
            params=params if params else None
        )
        return data

    def get_order_buyer_info(self, order_id: str) -> Dict[str, Any]:
        """
        Get buyer information for an order.
        Requires Restricted Data Token (RDT) for PII access.

        Args:
            order_id: Amazon order ID

        Returns:
            Buyer info including email, name (if available)
        """
        status, data = self.client.get(
            f"/orders/v0/orders/{order_id}/buyerInfo",
            "orders",
            use_rdt=True,
            rdt_path=f"/orders/v0/orders/{order_id}/buyerInfo",
            rdt_elements=["buyerInfo"]
        )
        return data

    def get_order_address(self, order_id: str) -> Dict[str, Any]:
        """
        Get shipping address for an order.
        Requires Restricted Data Token (RDT) for PII access.

        Args:
            order_id: Amazon order ID

        Returns:
            Shipping address details
        """
        status, data = self.client.get(
            f"/orders/v0/orders/{order_id}/address",
            "orders",
            use_rdt=True,
            rdt_path=f"/orders/v0/orders/{order_id}/address",
            rdt_elements=["shippingAddress"]
        )
        return data

    def get_order_items_buyer_info(
        self,
        order_id: str,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get buyer information for order items.
        Requires Restricted Data Token (RDT) for PII access.

        Args:
            order_id: Amazon order ID
            next_token: Pagination token

        Returns:
            Order items with buyer-specific info (gift message, etc.)
        """
        params = {}
        if next_token:
            params["NextToken"] = next_token

        status, data = self.client.get(
            f"/orders/v0/orders/{order_id}/orderItems/buyerInfo",
            "orders",
            params=params if params else None,
            use_rdt=True,
            rdt_path=f"/orders/v0/orders/{order_id}/orderItems/buyerInfo",
            rdt_elements=["buyerInfo"]
        )
        return data

    def get_order_regulated_info(self, order_id: str) -> Dict[str, Any]:
        """
        Get regulated information for an order.
        Used for regulated products (pharma, alcohol, etc.)

        Args:
            order_id: Amazon order ID

        Returns:
            Regulated product compliance info
        """
        status, data = self.client.get(
            f"/orders/v0/orders/{order_id}/regulatedInfo",
            "orders"
        )
        return data

    def update_shipment_status(
        self,
        order_id: str,
        marketplace_id: str,
        shipment_status: str,
        order_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update shipment status for an order (MFN only).

        Args:
            order_id: Amazon order ID
            marketplace_id: Marketplace ID
            shipment_status: ReadyForPickup or PickedUp
            order_items: List of order item statuses

        Returns:
            Update confirmation
        """
        data = {
            "marketplaceId": marketplace_id,
            "shipmentStatus": shipment_status,
            "orderItems": order_items
        }

        status, response = self.client.post(
            f"/orders/v0/orders/{order_id}/shipment",
            "orders",
            data=data
        )
        return response

    def confirm_shipment(
        self,
        order_id: str,
        package_detail: Dict[str, Any],
        cod_collection_method: Optional[str] = None,
        marketplace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Confirm shipment for an order.

        Args:
            order_id: Amazon order ID
            package_detail: Package and tracking information
            cod_collection_method: DirectPayment for COD orders
            marketplace_id: Override marketplace

        Returns:
            Confirmation response
        """
        data = {
            "marketplaceId": marketplace_id or self.auth.get_marketplace_id(),
            "packageDetail": package_detail
        }

        if cod_collection_method:
            data["codCollectionMethod"] = cod_collection_method

        status, response = self.client.post(
            f"/orders/v0/orders/{order_id}/shipmentConfirmation",
            "orders",
            data=data
        )
        return response

    def paginate_orders(
        self,
        created_after: Optional[str] = None,
        **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """
        Iterate through all orders with automatic pagination.

        Args:
            created_after: ISO 8601 datetime
            **kwargs: Additional filter parameters

        Yields:
            Individual order objects
        """
        next_token = None

        while True:
            response = self.get_orders(
                created_after=created_after,
                next_token=next_token,
                **kwargs
            )

            payload = response.get("payload", {})
            orders = payload.get("Orders", [])

            for order in orders:
                yield order

            next_token = payload.get("NextToken")
            if not next_token:
                break


# Order status constants
ORDER_STATUSES = [
    "PendingAvailability",  # Order placed, payment not completed
    "Pending",              # Payment being validated
    "Unshipped",            # Ready to ship
    "PartiallyShipped",     # Some items shipped
    "Shipped",              # All items shipped
    "InvoiceUnconfirmed",   # Invoice not yet confirmed (Japan)
    "Canceled",             # Order canceled
    "Unfulfillable"         # Cannot be fulfilled (FBA)
]

FULFILLMENT_CHANNELS = [
    "AFN",  # Amazon Fulfillment Network (FBA)
    "MFN"   # Merchant Fulfillment Network
]


# Helper functions
def get_recent_orders(
    client: SPAPIClient,
    days: int = 7,
    statuses: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Get orders from the last N days.

    Args:
        client: SPAPIClient instance
        days: Number of days to look back
        statuses: Optional list of order statuses

    Returns:
        List of orders
    """
    api = OrdersAPI(client)
    created_after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    orders = []
    for order in api.paginate_orders(created_after=created_after, order_statuses=statuses):
        orders.append(order)

    return orders


def get_unshipped_orders(client: SPAPIClient) -> List[Dict[str, Any]]:
    """Get all unshipped orders."""
    return get_recent_orders(client, days=30, statuses=["Unshipped"])


def get_order_with_items(client: SPAPIClient, order_id: str) -> Dict[str, Any]:
    """
    Get complete order details including all items.

    Args:
        client: SPAPIClient instance
        order_id: Amazon order ID

    Returns:
        Order with embedded OrderItems
    """
    api = OrdersAPI(client)

    order = api.get_order(order_id)
    items_response = api.get_order_items(order_id)

    order_data = order.get("payload", order)
    order_data["OrderItems"] = items_response.get("payload", {}).get("OrderItems", [])

    return order_data


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SP-API Orders Operations")
    parser.add_argument("command", choices=["list", "get", "items", "buyer", "address"],
                        help="Operation to perform")
    parser.add_argument("--order-id", help="Amazon order ID")
    parser.add_argument("--days", type=int, default=7, help="Days to look back")
    parser.add_argument("--status", action="append", help="Order status filter")
    parser.add_argument("--profile", default="production", help="Config profile")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    auth = SPAPIAuth(profile=args.profile)
    client = SPAPIClient(auth)
    api = OrdersAPI(client)

    try:
        if args.command == "list":
            created_after = (datetime.utcnow() - timedelta(days=args.days)).strftime("%Y-%m-%dT%H:%M:%SZ")
            result = api.get_orders(created_after=created_after, order_statuses=args.status)

        elif args.command == "get":
            if not args.order_id:
                print("Error: --order-id required", file=sys.stderr)
                sys.exit(1)
            result = api.get_order(args.order_id)

        elif args.command == "items":
            if not args.order_id:
                print("Error: --order-id required", file=sys.stderr)
                sys.exit(1)
            result = api.get_order_items(args.order_id)

        elif args.command == "buyer":
            if not args.order_id:
                print("Error: --order-id required", file=sys.stderr)
                sys.exit(1)
            result = api.get_order_buyer_info(args.order_id)

        elif args.command == "address":
            if not args.order_id:
                print("Error: --order-id required", file=sys.stderr)
                sys.exit(1)
            result = api.get_order_address(args.order_id)

        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            payload = result.get("payload", result)
            if isinstance(payload, dict) and "Orders" in payload:
                orders = payload["Orders"]
                print(f"Found {len(orders)} orders:")
                for o in orders[:10]:
                    print(f"  {o.get('AmazonOrderId')} - {o.get('OrderStatus')} - {o.get('OrderTotal', {}).get('Amount', 'N/A')}")
                if len(orders) > 10:
                    print(f"  ... and {len(orders) - 10} more")
            else:
                print(json.dumps(payload, indent=2, default=str))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
