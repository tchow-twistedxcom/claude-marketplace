#!/usr/bin/env python3
"""
Amazon SP-API Vendor APIs

Covers:
- Vendor Orders API - Purchase order management
- Vendor Shipments API - ASN and shipment confirmations
- Vendor Invoices API - Invoice submission
- Vendor Transaction Status API - Transaction tracking
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone


class VendorOrdersAPI:
    """
    Vendor Orders API for purchase order management.

    Endpoints:
    - GET /vendor/orders/v1/purchaseOrders - List purchase orders
    - GET /vendor/orders/v1/purchaseOrders/{purchaseOrderNumber} - Get specific order
    - POST /vendor/orders/v1/acknowledgements - Submit acknowledgements
    - GET /vendor/orders/v1/purchaseOrdersStatus - Get order status
    """

    def __init__(self, client):
        """
        Initialize Vendor Orders API.

        Args:
            client: SPAPIClient instance
        """
        self.client = client
        self.api_name = "vendorOrders"
        self.base_path = "/vendor/orders/v1"

    def get_purchase_orders(self,
                            limit: int = 100,
                            created_after: str = None,
                            created_before: str = None,
                            sort_order: str = "DESC",
                            next_token: str = None,
                            include_details: bool = True,
                            changed_after: str = None,
                            changed_before: str = None,
                            po_item_state: str = None,
                            is_po_changed: bool = None,
                            purchase_order_state: str = None,
                            ordering_vendor_code: str = None) -> Tuple[int, Any]:
        """
        Get purchase orders with filters.

        Args:
            limit: Max results per page (1-100)
            created_after: ISO 8601 datetime - orders created after
            created_before: ISO 8601 datetime - orders created before
            sort_order: ASC or DESC (default DESC)
            next_token: Pagination token
            include_details: Include order details (default True)
            changed_after: ISO 8601 datetime - orders changed after
            changed_before: ISO 8601 datetime - orders changed before
            po_item_state: Filter by item state
            is_po_changed: Filter by changed status
            purchase_order_state: Filter by order state
            ordering_vendor_code: Filter by vendor code

        Returns:
            Tuple of (status_code, response_data)
        """
        params = {
            "limit": limit,
            "createdAfter": created_after,
            "createdBefore": created_before,
            "sortOrder": sort_order,
            "nextToken": next_token,
            "includeDetails": str(include_details).lower() if include_details is not None else None,
            "changedAfter": changed_after,
            "changedBefore": changed_before,
            "poItemState": po_item_state,
            "isPOChanged": str(is_po_changed).lower() if is_po_changed is not None else None,
            "purchaseOrderState": purchase_order_state,
            "orderingVendorCode": ordering_vendor_code
        }
        return self.client.get(
            f"{self.base_path}/purchaseOrders",
            self.api_name,
            params=params
        )

    def get_purchase_order(self, purchase_order_number: str) -> Tuple[int, Any]:
        """
        Get a specific purchase order.

        Args:
            purchase_order_number: The PO number to retrieve

        Returns:
            Tuple of (status_code, response_data)
        """
        return self.client.get(
            f"{self.base_path}/purchaseOrders/{purchase_order_number}",
            self.api_name
        )

    def submit_acknowledgement(self, acknowledgements: List[Dict]) -> Tuple[int, Any]:
        """
        Submit purchase order acknowledgements.

        Args:
            acknowledgements: List of acknowledgement objects containing:
                - purchaseOrderNumber: The PO number
                - sellingParty: Vendor party info
                - acknowledgementDate: ISO 8601 datetime
                - items: List of item acknowledgements

        Returns:
            Tuple of (status_code, response_data)
        """
        data = {"acknowledgements": acknowledgements}
        return self.client.post(
            f"{self.base_path}/acknowledgements",
            self.api_name,
            data=data
        )

    def get_purchase_orders_status(self,
                                   limit: int = 100,
                                   sort_order: str = "DESC",
                                   next_token: str = None,
                                   created_after: str = None,
                                   created_before: str = None,
                                   updated_after: str = None,
                                   updated_before: str = None,
                                   purchase_order_number: str = None,
                                   purchase_order_status: str = None,
                                   item_confirmation_status: str = None,
                                   item_receive_status: str = None,
                                   ordering_vendor_code: str = None,
                                   ship_to_party_id: str = None) -> Tuple[int, Any]:
        """
        Get purchase order status.

        Args:
            limit: Max results per page
            sort_order: ASC or DESC
            next_token: Pagination token
            created_after: Filter by creation date
            created_before: Filter by creation date
            updated_after: Filter by update date
            updated_before: Filter by update date
            purchase_order_number: Filter by specific PO
            purchase_order_status: Filter by status
            item_confirmation_status: Filter by item confirmation
            item_receive_status: Filter by receive status
            ordering_vendor_code: Filter by vendor code
            ship_to_party_id: Filter by ship-to party

        Returns:
            Tuple of (status_code, response_data)
        """
        params = {
            "limit": limit,
            "sortOrder": sort_order,
            "nextToken": next_token,
            "createdAfter": created_after,
            "createdBefore": created_before,
            "updatedAfter": updated_after,
            "updatedBefore": updated_before,
            "purchaseOrderNumber": purchase_order_number,
            "purchaseOrderStatus": purchase_order_status,
            "itemConfirmationStatus": item_confirmation_status,
            "itemReceiveStatus": item_receive_status,
            "orderingVendorCode": ordering_vendor_code,
            "shipToPartyId": ship_to_party_id
        }
        return self.client.get(
            f"{self.base_path}/purchaseOrdersStatus",
            self.api_name,
            params=params
        )


class VendorShipmentsAPI:
    """
    Vendor Shipments API for ASN and shipment management.

    Endpoints:
    - POST /vendor/shipping/v1/shipmentConfirmations - Submit shipment confirmations
    - POST /vendor/shipping/v1/shipments - Submit shipment details
    - GET /vendor/shipping/v1/shipments - Get shipment details
    - GET /vendor/shipping/v1/transportLabels - Get transport labels
    """

    def __init__(self, client):
        """
        Initialize Vendor Shipments API.

        Args:
            client: SPAPIClient instance
        """
        self.client = client
        self.api_name = "vendorShipments"
        self.base_path = "/vendor/shipping/v1"

    def submit_shipment_confirmations(self, shipment_confirmations: List[Dict]) -> Tuple[int, Any]:
        """
        Submit shipment confirmations (ASN).

        Args:
            shipment_confirmations: List of shipment confirmation objects containing:
                - purchaseOrderNumber: The PO number
                - shipmentIdentifier: Your shipment ID
                - shipmentConfirmationType: Original, Replace, or Delete
                - shipmentType: TruckLoad, LessThanTruckLoad, SmallParcel
                - shipmentStructure: Pallet, LooseCase, PalletizedAssortmentCase
                - transportationDetails: Carrier info, tracking, BOL
                - shipFromParty: Origin warehouse
                - shipToParty: Amazon FC
                - shipmentConfirmationDate: Confirmation timestamp
                - shippedDate: Ship date
                - estimatedDeliveryDate: ETA
                - shippedItems: List of shipped items

        Returns:
            Tuple of (status_code, response_data)
        """
        data = {"shipmentConfirmations": shipment_confirmations}
        return self.client.post(
            f"{self.base_path}/shipmentConfirmations",
            self.api_name,
            data=data
        )

    def submit_shipments(self, shipments: List[Dict]) -> Tuple[int, Any]:
        """
        Submit shipment details.

        Args:
            shipments: List of shipment objects

        Returns:
            Tuple of (status_code, response_data)
        """
        data = {"shipments": shipments}
        return self.client.post(
            f"{self.base_path}/shipments",
            self.api_name,
            data=data
        )

    def get_shipment_details(self,
                             limit: int = 10,
                             sort_order: str = "ASC",
                             next_token: str = None,
                             created_after: str = None,
                             created_before: str = None,
                             shipment_confirmed_before: str = None,
                             shipment_confirmed_after: str = None,
                             package_label_created_before: str = None,
                             package_label_created_after: str = None,
                             shipped_before: str = None,
                             shipped_after: str = None,
                             estimated_delivery_before: str = None,
                             estimated_delivery_after: str = None,
                             shipment_delivery_before: str = None,
                             shipment_delivery_after: str = None,
                             requested_pick_up_before: str = None,
                             requested_pick_up_after: str = None,
                             scheduled_pick_up_before: str = None,
                             scheduled_pick_up_after: str = None,
                             current_shipment_status: str = None,
                             vendor_shipment_identifier: str = None,
                             buyer_reference_number: str = None,
                             buyer_warehouse_code: str = None,
                             seller_warehouse_code: str = None) -> Tuple[int, Any]:
        """
        Get shipment details with extensive filters.

        Args:
            limit: Max results (1-50)
            sort_order: ASC or DESC
            next_token: Pagination token
            created_after/before: Filter by creation date
            shipment_confirmed_after/before: Filter by confirmation date
            package_label_created_after/before: Filter by label creation
            shipped_after/before: Filter by ship date
            estimated_delivery_after/before: Filter by ETA
            shipment_delivery_after/before: Filter by delivery date
            requested_pick_up_after/before: Filter by pickup request
            scheduled_pick_up_after/before: Filter by scheduled pickup
            current_shipment_status: Filter by status
            vendor_shipment_identifier: Filter by vendor shipment ID
            buyer_reference_number: Filter by buyer reference
            buyer_warehouse_code: Filter by buyer warehouse
            seller_warehouse_code: Filter by seller warehouse

        Returns:
            Tuple of (status_code, response_data)
        """
        params = {
            "limit": limit,
            "sortOrder": sort_order,
            "nextToken": next_token,
            "createdAfter": created_after,
            "createdBefore": created_before,
            "shipmentConfirmedBefore": shipment_confirmed_before,
            "shipmentConfirmedAfter": shipment_confirmed_after,
            "packageLabelCreatedBefore": package_label_created_before,
            "packageLabelCreatedAfter": package_label_created_after,
            "shippedBefore": shipped_before,
            "shippedAfter": shipped_after,
            "estimatedDeliveryBefore": estimated_delivery_before,
            "estimatedDeliveryAfter": estimated_delivery_after,
            "shipmentDeliveryBefore": shipment_delivery_before,
            "shipmentDeliveryAfter": shipment_delivery_after,
            "requestedPickUpBefore": requested_pick_up_before,
            "requestedPickUpAfter": requested_pick_up_after,
            "scheduledPickUpBefore": scheduled_pick_up_before,
            "scheduledPickUpAfter": scheduled_pick_up_after,
            "currentShipmentStatus": current_shipment_status,
            "vendorShipmentIdentifier": vendor_shipment_identifier,
            "buyerReferenceNumber": buyer_reference_number,
            "buyerWarehouseCode": buyer_warehouse_code,
            "sellerWarehouseCode": seller_warehouse_code
        }
        return self.client.get(
            f"{self.base_path}/shipments",
            self.api_name,
            params=params
        )

    def get_shipment_labels(self,
                            purchase_order_number: str = None,
                            limit: int = 10,
                            sort_order: str = "ASC",
                            next_token: str = None) -> Tuple[int, Any]:
        """
        Get transportation labels.

        Args:
            purchase_order_number: Filter by PO number
            limit: Max results
            sort_order: ASC or DESC
            next_token: Pagination token

        Returns:
            Tuple of (status_code, response_data)
        """
        params = {
            "purchaseOrderNumber": purchase_order_number,
            "limit": limit,
            "sortOrder": sort_order,
            "nextToken": next_token
        }
        return self.client.get(
            f"{self.base_path}/transportLabels",
            self.api_name,
            params=params
        )


class VendorInvoicesAPI:
    """
    Vendor Invoices API for invoice submission.

    Endpoints:
    - POST /vendor/payments/v1/invoices - Submit invoices
    """

    def __init__(self, client):
        """
        Initialize Vendor Invoices API.

        Args:
            client: SPAPIClient instance
        """
        self.client = client
        self.api_name = "vendorInvoices"
        self.base_path = "/vendor/payments/v1"

    def submit_invoices(self, invoices: List[Dict]) -> Tuple[int, Any]:
        """
        Submit vendor invoices.

        Args:
            invoices: List of invoice objects containing:
                - invoiceType: Invoice, CreditNote
                - id: Your invoice ID
                - referenceNumber: Related PO number
                - date: Invoice date
                - remitToParty: Vendor payment info
                - shipToParty: Amazon FC
                - billToParty: Amazon billing
                - invoiceTotal: Total amount
                - items: Line items

        Returns:
            Tuple of (status_code, response_data)
        """
        data = {"invoices": invoices}
        return self.client.post(
            f"{self.base_path}/invoices",
            self.api_name,
            data=data
        )


class VendorTransactionStatusAPI:
    """
    Vendor Transaction Status API for tracking submissions.

    Endpoints:
    - GET /vendor/transactions/v1/transactions/{transactionId} - Get transaction status
    """

    def __init__(self, client):
        """
        Initialize Vendor Transaction Status API.

        Args:
            client: SPAPIClient instance
        """
        self.client = client
        self.api_name = "vendorTransactionStatus"
        self.base_path = "/vendor/transactions/v1"

    def get_transaction(self, transaction_id: str) -> Tuple[int, Any]:
        """
        Get transaction status.

        Args:
            transaction_id: The transaction ID from a submission response

        Returns:
            Tuple of (status_code, response_data)

        Response includes:
            - transactionId: The transaction ID
            - status: Processing, Success, Failure
            - errors: List of errors if failed
        """
        return self.client.get(
            f"{self.base_path}/transactions/{transaction_id}",
            self.api_name
        )


# Convenience functions for common operations

def acknowledge_purchase_order(client, po_number: str, vendor_code: str,
                               items: List[Dict],
                               acknowledgement_date: str = None) -> Tuple[int, Any]:
    """
    Helper to acknowledge a purchase order.

    Args:
        client: SPAPIClient instance
        po_number: Purchase order number
        vendor_code: Vendor party ID
        items: List of item acknowledgements with:
            - itemSequenceNumber
            - amazonProductIdentifier or vendorProductIdentifier
            - acknowledgementStatus (confirmationStatus, acceptedQuantity, etc.)
        acknowledgement_date: ISO 8601 datetime (defaults to now)

    Returns:
        Tuple of (status_code, response_data)
    """
    if acknowledgement_date is None:
        acknowledgement_date = datetime.now(timezone.utc).isoformat()

    api = VendorOrdersAPI(client)
    acknowledgements = [{
        "purchaseOrderNumber": po_number,
        "sellingParty": {"partyId": vendor_code},
        "acknowledgementDate": acknowledgement_date,
        "items": items
    }]
    return api.submit_acknowledgement(acknowledgements)


def submit_asn(client, po_number: str, shipment_id: str,
               vendor_code: str, ship_from: Dict, ship_to_fc: str,
               items: List[Dict], carrier_info: Dict = None,
               ship_date: str = None, eta: str = None) -> Tuple[int, Any]:
    """
    Helper to submit an ASN (Advance Ship Notice).

    Args:
        client: SPAPIClient instance
        po_number: Purchase order number
        shipment_id: Your shipment identifier
        vendor_code: Vendor party ID
        ship_from: Ship from address dict
        ship_to_fc: Amazon FC code
        items: List of shipped items
        carrier_info: Transportation details (carrier, tracking, BOL)
        ship_date: Ship date ISO 8601 (defaults to now)
        eta: Estimated delivery ISO 8601

    Returns:
        Tuple of (status_code, response_data)
    """
    if ship_date is None:
        ship_date = datetime.now(timezone.utc).isoformat()

    api = VendorShipmentsAPI(client)
    confirmation = {
        "purchaseOrderNumber": po_number,
        "shipmentIdentifier": shipment_id,
        "shipmentConfirmationType": "Original",
        "shipmentType": "TruckLoad",
        "shipmentStructure": "PalletizedAssortmentCase",
        "shipFromParty": {
            "partyId": vendor_code,
            "address": ship_from
        },
        "shipToParty": {"partyId": ship_to_fc},
        "shipmentConfirmationDate": ship_date,
        "shippedDate": ship_date,
        "shippedItems": items
    }

    if carrier_info:
        confirmation["transportationDetails"] = carrier_info
    if eta:
        confirmation["estimatedDeliveryDate"] = eta

    return api.submit_shipment_confirmations([confirmation])


def submit_invoice(client, invoice_id: str, po_number: str,
                   vendor_code: str, vendor_address: Dict,
                   amazon_fc: str, amazon_billing: str,
                   items: List[Dict], total_amount: str,
                   currency: str = "USD",
                   invoice_date: str = None) -> Tuple[int, Any]:
    """
    Helper to submit a vendor invoice.

    Args:
        client: SPAPIClient instance
        invoice_id: Your invoice ID
        po_number: Related PO number
        vendor_code: Vendor party ID
        vendor_address: Remit-to address dict
        amazon_fc: Ship-to FC code
        amazon_billing: Bill-to party ID
        items: Line items with ASIN, qty, price
        total_amount: Invoice total as string
        currency: Currency code (default USD)
        invoice_date: Invoice date ISO 8601 (defaults to now)

    Returns:
        Tuple of (status_code, response_data)
    """
    if invoice_date is None:
        invoice_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z")

    api = VendorInvoicesAPI(client)
    invoice = {
        "invoiceType": "Invoice",
        "id": invoice_id,
        "referenceNumber": po_number,
        "date": invoice_date,
        "remitToParty": {
            "partyId": vendor_code,
            "address": vendor_address
        },
        "shipToParty": {"partyId": amazon_fc},
        "billToParty": {"partyId": amazon_billing},
        "invoiceTotal": {
            "currencyCode": currency,
            "amount": total_amount
        },
        "items": items
    }
    return api.submit_invoices([invoice])


# CLI interface for testing
if __name__ == "__main__":
    print("SP-API Vendor APIs Module")
    print("\nAvailable APIs:")
    print("  - VendorOrdersAPI: Purchase order management")
    print("  - VendorShipmentsAPI: ASN and shipment confirmations")
    print("  - VendorInvoicesAPI: Invoice submission")
    print("  - VendorTransactionStatusAPI: Transaction tracking")
    print("\nHelper functions:")
    print("  - acknowledge_purchase_order()")
    print("  - submit_asn()")
    print("  - submit_invoice()")
