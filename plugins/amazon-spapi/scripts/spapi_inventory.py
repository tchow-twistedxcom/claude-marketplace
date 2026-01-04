#!/usr/bin/env python3
"""
Amazon SP-API FBA Inventory API Module

Provides classes for managing FBA inventory levels, summaries,
and fulfillment operations.
"""

import json
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List, Iterator

from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient


class FBAInventoryAPI:
    """FBA Inventory API for inventory management."""

    def __init__(self, client: SPAPIClient):
        self.client = client
        self.auth = client.auth

    def get_inventory_summaries(
        self,
        granularity_type: str = "Marketplace",
        granularity_id: Optional[str] = None,
        marketplace_ids: Optional[List[str]] = None,
        details: bool = False,
        start_date_time: Optional[str] = None,
        seller_skus: Optional[List[str]] = None,
        seller_sku: Optional[str] = None,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get inventory summaries with aggregated data.

        Args:
            granularity_type: Marketplace or Warehouse
            granularity_id: Marketplace ID or FC code
            marketplace_ids: List of marketplace IDs
            details: Include additional details
            start_date_time: Filter by inventory age
            seller_skus: List of seller SKUs
            seller_sku: Single seller SKU
            next_token: Pagination token

        Returns:
            Inventory summaries with quantities
        """
        marketplace_id = self.auth.get_marketplace_id()
        if marketplace_ids is None:
            marketplace_ids = [marketplace_id]

        params = {
            "granularityType": granularity_type,
            "granularityId": granularity_id or marketplace_id,
            "marketplaceIds": ",".join(marketplace_ids),
            "details": str(details).lower()
        }

        if start_date_time:
            params["startDateTime"] = start_date_time
        if seller_skus:
            params["sellerSkus"] = ",".join(seller_skus)
        if seller_sku:
            params["sellerSku"] = seller_sku
        if next_token:
            params["nextToken"] = next_token

        status, data = self.client.get(
            "/fba/inventory/v1/summaries",
            "fbaInventory",
            params=params
        )
        return data

    def add_inventory(
        self,
        x_amzn_idempotency_token: str,
        seller_sku: str,
        marketplace_id: str,
        quantity: int
    ) -> Dict[str, Any]:
        """
        Add inventory to FBA.

        Note: This is typically done through inbound shipments.

        Args:
            x_amzn_idempotency_token: Idempotency token
            seller_sku: Seller SKU
            marketplace_id: Marketplace ID
            quantity: Quantity to add

        Returns:
            Operation result
        """
        data = {
            "sellerSku": seller_sku,
            "marketplaceId": marketplace_id,
            "quantity": quantity
        }

        status, response = self.client.post(
            "/fba/inventory/v1/items",
            "fbaInventory",
            data=data,
            headers={"x-amzn-idempotency-token": x_amzn_idempotency_token}
        )
        return response

    def paginate_inventory(
        self,
        details: bool = False,
        seller_skus: Optional[List[str]] = None
    ) -> Iterator[Dict[str, Any]]:
        """
        Iterate through all inventory summaries.

        Args:
            details: Include additional details
            seller_skus: Filter by SKUs

        Yields:
            Individual inventory summary objects
        """
        next_token = None

        while True:
            response = self.get_inventory_summaries(
                details=details,
                seller_skus=seller_skus,
                next_token=next_token
            )

            payload = response.get("payload", {})
            summaries = payload.get("inventorySummaries", [])

            for summary in summaries:
                yield summary

            pagination = payload.get("pagination", {})
            next_token = pagination.get("nextToken")
            if not next_token:
                break


class FulfillmentInboundAPI:
    """Fulfillment Inbound API for shipments to Amazon FCs."""

    def __init__(self, client: SPAPIClient):
        self.client = client
        self.auth = client.auth

    def get_inbound_guidance(
        self,
        marketplace_id: str,
        seller_sku_list: Optional[List[str]] = None,
        asin_list: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get inbound guidance for items.

        Args:
            marketplace_id: Marketplace ID
            seller_sku_list: List of seller SKUs
            asin_list: List of ASINs

        Returns:
            Inbound eligibility and guidance
        """
        params = {
            "MarketplaceId": marketplace_id
        }

        if seller_sku_list:
            params["SellerSKUList"] = ",".join(seller_sku_list)
        if asin_list:
            params["ASINList"] = ",".join(asin_list)

        status, data = self.client.get(
            "/fba/inbound/v0/itemsGuidance",
            "fbaInbound",
            params=params
        )
        return data

    def create_inbound_shipment_plan(
        self,
        ship_from_address: Dict[str, Any],
        label_prep_preference: str,
        inbound_shipment_plan_request_items: List[Dict[str, Any]],
        ship_to_country_code: Optional[str] = None,
        ship_to_country_subdivision_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an inbound shipment plan.

        Args:
            ship_from_address: Origin address
            label_prep_preference: SELLER_LABEL, AMAZON_LABEL_ONLY, AMAZON_LABEL_PREFERRED
            inbound_shipment_plan_request_items: Items to ship
            ship_to_country_code: Destination country
            ship_to_country_subdivision_code: State/province

        Returns:
            Shipment plans with destination assignments
        """
        data = {
            "ShipFromAddress": ship_from_address,
            "LabelPrepPreference": label_prep_preference,
            "InboundShipmentPlanRequestItems": inbound_shipment_plan_request_items
        }

        if ship_to_country_code:
            data["ShipToCountryCode"] = ship_to_country_code
        if ship_to_country_subdivision_code:
            data["ShipToCountrySubdivisionCode"] = ship_to_country_subdivision_code

        status, response = self.client.post(
            "/fba/inbound/v0/plans",
            "fbaInbound",
            data=data
        )
        return response

    def create_inbound_shipment(
        self,
        shipment_id: str,
        inbound_shipment_header: Dict[str, Any],
        inbound_shipment_items: List[Dict[str, Any]],
        marketplace_id: str
    ) -> Dict[str, Any]:
        """
        Create an inbound shipment.

        Args:
            shipment_id: Shipment ID from plan
            inbound_shipment_header: Shipment header info
            inbound_shipment_items: Items in shipment
            marketplace_id: Marketplace ID

        Returns:
            Shipment creation result
        """
        data = {
            "InboundShipmentHeader": inbound_shipment_header,
            "InboundShipmentItems": inbound_shipment_items,
            "MarketplaceId": marketplace_id
        }

        status, response = self.client.post(
            f"/fba/inbound/v0/shipments/{shipment_id}",
            "fbaInbound",
            data=data
        )
        return response

    def update_inbound_shipment(
        self,
        shipment_id: str,
        inbound_shipment_header: Dict[str, Any],
        inbound_shipment_items: List[Dict[str, Any]],
        marketplace_id: str
    ) -> Dict[str, Any]:
        """
        Update an inbound shipment.

        Args:
            shipment_id: Shipment ID
            inbound_shipment_header: Updated header
            inbound_shipment_items: Updated items
            marketplace_id: Marketplace ID

        Returns:
            Update result
        """
        data = {
            "InboundShipmentHeader": inbound_shipment_header,
            "InboundShipmentItems": inbound_shipment_items,
            "MarketplaceId": marketplace_id
        }

        status, response = self.client.put(
            f"/fba/inbound/v0/shipments/{shipment_id}",
            "fbaInbound",
            data=data
        )
        return response

    def get_shipments(
        self,
        shipment_status_list: Optional[List[str]] = None,
        shipment_id_list: Optional[List[str]] = None,
        last_updated_after: Optional[str] = None,
        last_updated_before: Optional[str] = None,
        query_type: str = "SHIPMENT",
        next_token: Optional[str] = None,
        marketplace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get inbound shipments.

        Args:
            shipment_status_list: Filter by status
            shipment_id_list: Filter by IDs
            last_updated_after: Filter by update time
            last_updated_before: Filter by update time
            query_type: SHIPMENT, DATE_RANGE, or NEXT_TOKEN
            next_token: Pagination token
            marketplace_id: Marketplace ID

        Returns:
            List of shipments
        """
        params = {
            "QueryType": query_type,
            "MarketplaceId": marketplace_id or self.auth.get_marketplace_id()
        }

        if shipment_status_list:
            params["ShipmentStatusList"] = ",".join(shipment_status_list)
        if shipment_id_list:
            params["ShipmentIdList"] = ",".join(shipment_id_list)
        if last_updated_after:
            params["LastUpdatedAfter"] = last_updated_after
        if last_updated_before:
            params["LastUpdatedBefore"] = last_updated_before
        if next_token:
            params["NextToken"] = next_token

        status, data = self.client.get(
            "/fba/inbound/v0/shipments",
            "fbaInbound",
            params=params
        )
        return data

    def get_shipment_items(
        self,
        shipment_id: str,
        marketplace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get items in a shipment.

        Args:
            shipment_id: Shipment ID
            marketplace_id: Marketplace ID

        Returns:
            Shipment items
        """
        params = {
            "MarketplaceId": marketplace_id or self.auth.get_marketplace_id()
        }

        status, data = self.client.get(
            f"/fba/inbound/v0/shipments/{shipment_id}/items",
            "fbaInbound",
            params=params
        )
        return data


class FulfillmentOutboundAPI:
    """Fulfillment Outbound API for Multi-Channel Fulfillment (MCF)."""

    def __init__(self, client: SPAPIClient):
        self.client = client
        self.auth = client.auth

    def get_fulfillment_preview(
        self,
        address: Dict[str, Any],
        items: List[Dict[str, Any]],
        marketplace_id: Optional[str] = None,
        shipping_speed_categories: Optional[List[str]] = None,
        include_cod_fulfillment_preview: bool = False,
        include_delivery_windows: bool = False
    ) -> Dict[str, Any]:
        """
        Get fulfillment preview for MCF order.

        Args:
            address: Destination address
            items: Items to fulfill
            marketplace_id: Marketplace ID
            shipping_speed_categories: Standard, Expedited, Priority
            include_cod_fulfillment_preview: Include COD options
            include_delivery_windows: Include delivery windows

        Returns:
            Fulfillment previews with estimates
        """
        data = {
            "marketplaceId": marketplace_id or self.auth.get_marketplace_id(),
            "address": address,
            "items": items,
            "includeCODFulfillmentPreview": include_cod_fulfillment_preview,
            "includeDeliveryWindows": include_delivery_windows
        }

        if shipping_speed_categories:
            data["shippingSpeedCategories"] = shipping_speed_categories

        status, response = self.client.post(
            "/fba/outbound/2020-07-01/fulfillmentOrders/preview",
            "fbaOutbound",
            data=data
        )
        return response

    def create_fulfillment_order(
        self,
        seller_fulfillment_order_id: str,
        displayable_order_id: str,
        displayable_order_date: str,
        displayable_order_comment: str,
        shipping_speed_category: str,
        destination_address: Dict[str, Any],
        items: List[Dict[str, Any]],
        marketplace_id: Optional[str] = None,
        fulfillment_action: str = "Ship",
        notification_emails: Optional[List[str]] = None,
        cod_settings: Optional[Dict[str, Any]] = None,
        delivery_window: Optional[Dict[str, Any]] = None,
        feature_constraints: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Create a fulfillment order for MCF.

        Args:
            seller_fulfillment_order_id: Seller's order ID
            displayable_order_id: Customer-visible order ID
            displayable_order_date: Order date
            displayable_order_comment: Comment for customer
            shipping_speed_category: Standard, Expedited, Priority
            destination_address: Ship-to address
            items: Items to fulfill
            marketplace_id: Marketplace ID
            fulfillment_action: Ship or Hold
            notification_emails: Email addresses for notifications
            cod_settings: COD configuration
            delivery_window: Requested delivery window
            feature_constraints: Feature requirements

        Returns:
            Fulfillment order creation result
        """
        data = {
            "marketplaceId": marketplace_id or self.auth.get_marketplace_id(),
            "sellerFulfillmentOrderId": seller_fulfillment_order_id,
            "displayableOrderId": displayable_order_id,
            "displayableOrderDate": displayable_order_date,
            "displayableOrderComment": displayable_order_comment,
            "shippingSpeedCategory": shipping_speed_category,
            "destinationAddress": destination_address,
            "fulfillmentAction": fulfillment_action,
            "items": items
        }

        if notification_emails:
            data["notificationEmails"] = notification_emails
        if cod_settings:
            data["codSettings"] = cod_settings
        if delivery_window:
            data["deliveryWindow"] = delivery_window
        if feature_constraints:
            data["featureConstraints"] = feature_constraints

        status, response = self.client.post(
            "/fba/outbound/2020-07-01/fulfillmentOrders",
            "fbaOutbound",
            data=data
        )
        return response

    def get_fulfillment_order(self, seller_fulfillment_order_id: str) -> Dict[str, Any]:
        """
        Get a fulfillment order.

        Args:
            seller_fulfillment_order_id: Seller's order ID

        Returns:
            Fulfillment order details
        """
        status, data = self.client.get(
            f"/fba/outbound/2020-07-01/fulfillmentOrders/{seller_fulfillment_order_id}",
            "fbaOutbound"
        )
        return data

    def list_all_fulfillment_orders(
        self,
        query_start_date: Optional[str] = None,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List all fulfillment orders.

        Args:
            query_start_date: Filter by start date
            next_token: Pagination token

        Returns:
            List of fulfillment orders
        """
        params = {}
        if query_start_date:
            params["queryStartDate"] = query_start_date
        if next_token:
            params["nextToken"] = next_token

        status, data = self.client.get(
            "/fba/outbound/2020-07-01/fulfillmentOrders",
            "fbaOutbound",
            params=params if params else None
        )
        return data

    def cancel_fulfillment_order(self, seller_fulfillment_order_id: str) -> Dict[str, Any]:
        """
        Cancel a fulfillment order.

        Args:
            seller_fulfillment_order_id: Seller's order ID

        Returns:
            Cancellation result
        """
        status, response = self.client.put(
            f"/fba/outbound/2020-07-01/fulfillmentOrders/{seller_fulfillment_order_id}/cancel",
            "fbaOutbound"
        )
        return response


# Inventory statuses
SHIPMENT_STATUSES = [
    "WORKING",      # In preparation
    "SHIPPED",      # Shipped to FC
    "RECEIVING",    # Receiving at FC
    "CANCELLED",    # Cancelled
    "DELETED",      # Deleted
    "CLOSED",       # Completed
    "ERROR",        # Error occurred
    "IN_TRANSIT",   # In transit to FC
    "DELIVERED",    # Delivered to FC
    "CHECKED_IN"    # Checked in at FC
]

SHIPPING_SPEED_CATEGORIES = [
    "Standard",     # 3-5 days
    "Expedited",    # 2-3 days
    "Priority",     # 1 day
    "ScheduledDelivery"  # Specific window
]


# Helper functions
def get_all_inventory(client: SPAPIClient) -> List[Dict[str, Any]]:
    """
    Get all FBA inventory.

    Args:
        client: SPAPIClient instance

    Returns:
        List of all inventory summaries
    """
    api = FBAInventoryAPI(client)
    return list(api.paginate_inventory(details=True))


def get_inventory_for_skus(
    client: SPAPIClient,
    skus: List[str]
) -> List[Dict[str, Any]]:
    """
    Get inventory for specific SKUs.

    Args:
        client: SPAPIClient instance
        skus: List of seller SKUs

    Returns:
        Inventory summaries for specified SKUs
    """
    api = FBAInventoryAPI(client)
    result = api.get_inventory_summaries(
        seller_skus=skus,
        details=True
    )
    return result.get("payload", {}).get("inventorySummaries", [])


def get_low_inventory(
    client: SPAPIClient,
    threshold: int = 10
) -> List[Dict[str, Any]]:
    """
    Get items with low inventory.

    Args:
        client: SPAPIClient instance
        threshold: Minimum quantity threshold

    Returns:
        Items with inventory below threshold
    """
    api = FBAInventoryAPI(client)
    low_items = []

    for summary in api.paginate_inventory(details=True):
        total = summary.get("totalQuantity", 0)
        if total < threshold:
            low_items.append(summary)

    return low_items


def create_mcf_order(
    client: SPAPIClient,
    order_id: str,
    address: Dict[str, Any],
    items: List[Dict[str, Any]],
    shipping_speed: str = "Standard"
) -> Dict[str, Any]:
    """
    Create a Multi-Channel Fulfillment order.

    Args:
        client: SPAPIClient instance
        order_id: Seller's order ID
        address: Ship-to address
        items: Items with SKU and quantity
        shipping_speed: Standard, Expedited, or Priority

    Returns:
        MCF order creation result
    """
    api = FulfillmentOutboundAPI(client)
    return api.create_fulfillment_order(
        seller_fulfillment_order_id=order_id,
        displayable_order_id=order_id,
        displayable_order_date=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        displayable_order_comment="Multi-Channel Fulfillment Order",
        shipping_speed_category=shipping_speed,
        destination_address=address,
        items=items
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SP-API FBA Inventory Operations")
    parser.add_argument("command", choices=["list", "sku", "low", "shipments", "mcf-orders"],
                        help="Operation to perform")
    parser.add_argument("--sku", action="append", help="Seller SKU (can specify multiple)")
    parser.add_argument("--threshold", type=int, default=10, help="Low inventory threshold")
    parser.add_argument("--profile", default="production", help="Config profile")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    auth = SPAPIAuth(profile=args.profile)
    client = SPAPIClient(auth)

    try:
        if args.command == "list":
            result = get_all_inventory(client)

        elif args.command == "sku":
            if not args.sku:
                print("Error: --sku required", file=sys.stderr)
                sys.exit(1)
            result = get_inventory_for_skus(client, args.sku)

        elif args.command == "low":
            result = get_low_inventory(client, args.threshold)

        elif args.command == "shipments":
            api = FulfillmentInboundAPI(client)
            response = api.get_shipments()
            result = response.get("payload", {}).get("ShipmentData", [])

        elif args.command == "mcf-orders":
            api = FulfillmentOutboundAPI(client)
            response = api.list_all_fulfillment_orders()
            result = response.get("payload", {}).get("fulfillmentOrders", [])

        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            if isinstance(result, list):
                print(f"Found {len(result)} items:")
                for item in result[:10]:
                    sku = item.get("sellerSku", item.get("sellerFulfillmentOrderId", "N/A"))
                    qty = item.get("totalQuantity", item.get("receivedQuantity", "N/A"))
                    print(f"  {sku}: {qty}")
                if len(result) > 10:
                    print(f"  ... and {len(result) - 10} more")
            else:
                print(json.dumps(result, indent=2, default=str))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
