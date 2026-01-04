#!/usr/bin/env python3
"""
Amazon SP-API Reports & Feeds API Module

Provides classes for generating reports, submitting feeds,
and managing bulk data operations.
"""

import gzip
import io
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union

from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient


class ReportsAPI:
    """Reports API for generating and downloading reports."""

    def __init__(self, client: SPAPIClient):
        self.client = client
        self.auth = client.auth

    def create_report(
        self,
        report_type: str,
        marketplace_ids: Optional[List[str]] = None,
        data_start_time: Optional[str] = None,
        data_end_time: Optional[str] = None,
        report_options: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a report request.

        Args:
            report_type: Type of report (see REPORT_TYPES)
            marketplace_ids: List of marketplace IDs
            data_start_time: ISO 8601 start time
            data_end_time: ISO 8601 end time
            report_options: Report-specific options

        Returns:
            Report creation response with reportId
        """
        if marketplace_ids is None:
            marketplace_ids = [self.auth.get_marketplace_id()]

        data = {
            "reportType": report_type,
            "marketplaceIds": marketplace_ids
        }

        if data_start_time:
            data["dataStartTime"] = data_start_time
        if data_end_time:
            data["dataEndTime"] = data_end_time
        if report_options:
            data["reportOptions"] = report_options

        status, response = self.client.post(
            "/reports/2021-06-30/reports",
            "reports",
            data=data
        )
        return response

    def get_report(self, report_id: str) -> Dict[str, Any]:
        """
        Get report status and details.

        Args:
            report_id: Report ID from create_report

        Returns:
            Report status and metadata
        """
        status, data = self.client.get(
            f"/reports/2021-06-30/reports/{report_id}",
            "reports.getReport"
        )
        return data

    def get_reports(
        self,
        report_types: Optional[List[str]] = None,
        processing_statuses: Optional[List[str]] = None,
        marketplace_ids: Optional[List[str]] = None,
        page_size: int = 10,
        created_since: Optional[str] = None,
        created_until: Optional[str] = None,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a list of reports.

        Args:
            report_types: Filter by report types
            processing_statuses: IN_QUEUE, IN_PROGRESS, DONE, CANCELLED, FATAL
            marketplace_ids: List of marketplace IDs
            page_size: Results per page (1-100)
            created_since: ISO 8601 datetime
            created_until: ISO 8601 datetime
            next_token: Pagination token

        Returns:
            List of reports
        """
        params = {
            "pageSize": str(page_size)
        }

        if report_types:
            params["reportTypes"] = ",".join(report_types)
        if processing_statuses:
            params["processingStatuses"] = ",".join(processing_statuses)
        if marketplace_ids:
            params["marketplaceIds"] = ",".join(marketplace_ids)
        if created_since:
            params["createdSince"] = created_since
        if created_until:
            params["createdUntil"] = created_until
        if next_token:
            params["nextToken"] = next_token

        status, data = self.client.get(
            "/reports/2021-06-30/reports",
            "reports.getReports",
            params=params
        )
        return data

    def cancel_report(self, report_id: str) -> Dict[str, Any]:
        """
        Cancel a report.

        Args:
            report_id: Report ID

        Returns:
            Cancellation result
        """
        status, response = self.client.delete(
            f"/reports/2021-06-30/reports/{report_id}",
            "reports"
        )
        return response

    def get_report_document(self, report_document_id: str) -> Dict[str, Any]:
        """
        Get report document download URL.

        Args:
            report_document_id: Document ID from completed report

        Returns:
            Download URL and compression info
        """
        status, data = self.client.get(
            f"/reports/2021-06-30/documents/{report_document_id}",
            "reports"
        )
        return data

    def download_report(
        self,
        report_document_id: str,
        decompress: bool = True
    ) -> Union[str, bytes]:
        """
        Download report content.

        Args:
            report_document_id: Document ID
            decompress: Decompress GZIP content

        Returns:
            Report content as string or bytes
        """
        doc_info = self.get_report_document(report_document_id)
        url = doc_info.get("url")
        compression = doc_info.get("compressionAlgorithm")

        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            content = response.read()

        if decompress and compression == "GZIP":
            content = gzip.decompress(content)

        return content.decode("utf-8") if isinstance(content, bytes) else content

    def wait_for_report(
        self,
        report_id: str,
        timeout: int = 600,
        poll_interval: int = 30
    ) -> Dict[str, Any]:
        """
        Wait for a report to complete.

        Args:
            report_id: Report ID
            timeout: Maximum wait time in seconds
            poll_interval: Poll interval in seconds

        Returns:
            Completed report details

        Raises:
            TimeoutError: If report doesn't complete in time
            RuntimeError: If report fails
        """
        start_time = time.time()

        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Report {report_id} timed out after {timeout}s")

            report = self.get_report(report_id)
            status = report.get("processingStatus")

            if status == "DONE":
                return report
            elif status in ("CANCELLED", "FATAL"):
                raise RuntimeError(f"Report {report_id} failed with status: {status}")

            time.sleep(poll_interval)

    def create_and_download_report(
        self,
        report_type: str,
        marketplace_ids: Optional[List[str]] = None,
        data_start_time: Optional[str] = None,
        data_end_time: Optional[str] = None,
        report_options: Optional[Dict[str, str]] = None,
        timeout: int = 600
    ) -> str:
        """
        Create report, wait for completion, and download content.

        Args:
            report_type: Type of report
            marketplace_ids: List of marketplace IDs
            data_start_time: ISO 8601 start time
            data_end_time: ISO 8601 end time
            report_options: Report-specific options
            timeout: Maximum wait time

        Returns:
            Report content as string
        """
        # Create report
        create_response = self.create_report(
            report_type=report_type,
            marketplace_ids=marketplace_ids,
            data_start_time=data_start_time,
            data_end_time=data_end_time,
            report_options=report_options
        )
        report_id = create_response.get("reportId")

        # Wait for completion
        report = self.wait_for_report(report_id, timeout=timeout)

        # Download content
        document_id = report.get("reportDocumentId")
        return self.download_report(document_id)


class FeedsAPI:
    """Feeds API for submitting bulk data updates."""

    def __init__(self, client: SPAPIClient):
        self.client = client
        self.auth = client.auth

    def create_feed_document(
        self,
        content_type: str = "text/xml; charset=UTF-8"
    ) -> Dict[str, Any]:
        """
        Create a feed document for upload.

        Args:
            content_type: Content type of feed data

        Returns:
            Feed document with upload URL
        """
        data = {
            "contentType": content_type
        }

        status, response = self.client.post(
            "/feeds/2021-06-30/documents",
            "feeds",
            data=data
        )
        return response

    def upload_feed_content(
        self,
        upload_url: str,
        content: Union[str, bytes],
        content_type: str = "text/xml; charset=UTF-8"
    ) -> None:
        """
        Upload feed content to presigned URL.

        Args:
            upload_url: Presigned upload URL
            content: Feed content
            content_type: Content type
        """
        if isinstance(content, str):
            content = content.encode("utf-8")

        req = urllib.request.Request(upload_url, data=content, method="PUT")
        req.add_header("Content-Type", content_type)

        with urllib.request.urlopen(req) as response:
            pass

    def create_feed(
        self,
        feed_type: str,
        input_feed_document_id: str,
        marketplace_ids: Optional[List[str]] = None,
        feed_options: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a feed submission.

        Args:
            feed_type: Type of feed (see FEED_TYPES)
            input_feed_document_id: Document ID from create_feed_document
            marketplace_ids: List of marketplace IDs
            feed_options: Feed-specific options

        Returns:
            Feed creation response with feedId
        """
        if marketplace_ids is None:
            marketplace_ids = [self.auth.get_marketplace_id()]

        data = {
            "feedType": feed_type,
            "marketplaceIds": marketplace_ids,
            "inputFeedDocumentId": input_feed_document_id
        }

        if feed_options:
            data["feedOptions"] = feed_options

        status, response = self.client.post(
            "/feeds/2021-06-30/feeds",
            "feeds",
            data=data
        )
        return response

    def get_feed(self, feed_id: str) -> Dict[str, Any]:
        """
        Get feed status.

        Args:
            feed_id: Feed ID

        Returns:
            Feed status and details
        """
        status, data = self.client.get(
            f"/feeds/2021-06-30/feeds/{feed_id}",
            "feeds.getFeed"
        )
        return data

    def get_feeds(
        self,
        feed_types: Optional[List[str]] = None,
        marketplace_ids: Optional[List[str]] = None,
        page_size: int = 10,
        processing_statuses: Optional[List[str]] = None,
        created_since: Optional[str] = None,
        created_until: Optional[str] = None,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a list of feeds.

        Args:
            feed_types: Filter by feed types
            marketplace_ids: List of marketplace IDs
            page_size: Results per page (1-100)
            processing_statuses: IN_QUEUE, IN_PROGRESS, DONE, CANCELLED, FATAL
            created_since: ISO 8601 datetime
            created_until: ISO 8601 datetime
            next_token: Pagination token

        Returns:
            List of feeds
        """
        params = {
            "pageSize": str(page_size)
        }

        if feed_types:
            params["feedTypes"] = ",".join(feed_types)
        if marketplace_ids:
            params["marketplaceIds"] = ",".join(marketplace_ids)
        if processing_statuses:
            params["processingStatuses"] = ",".join(processing_statuses)
        if created_since:
            params["createdSince"] = created_since
        if created_until:
            params["createdUntil"] = created_until
        if next_token:
            params["nextToken"] = next_token

        status, data = self.client.get(
            "/feeds/2021-06-30/feeds",
            "feeds.getFeeds",
            params=params
        )
        return data

    def cancel_feed(self, feed_id: str) -> Dict[str, Any]:
        """
        Cancel a feed.

        Args:
            feed_id: Feed ID

        Returns:
            Cancellation result
        """
        status, response = self.client.delete(
            f"/feeds/2021-06-30/feeds/{feed_id}",
            "feeds"
        )
        return response

    def get_feed_document(self, feed_document_id: str) -> Dict[str, Any]:
        """
        Get feed result document.

        Args:
            feed_document_id: Document ID from completed feed

        Returns:
            Download URL for result document
        """
        status, data = self.client.get(
            f"/feeds/2021-06-30/documents/{feed_document_id}",
            "feeds"
        )
        return data

    def wait_for_feed(
        self,
        feed_id: str,
        timeout: int = 600,
        poll_interval: int = 30
    ) -> Dict[str, Any]:
        """
        Wait for a feed to complete.

        Args:
            feed_id: Feed ID
            timeout: Maximum wait time in seconds
            poll_interval: Poll interval in seconds

        Returns:
            Completed feed details

        Raises:
            TimeoutError: If feed doesn't complete in time
            RuntimeError: If feed fails
        """
        start_time = time.time()

        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Feed {feed_id} timed out after {timeout}s")

            feed = self.get_feed(feed_id)
            status = feed.get("processingStatus")

            if status == "DONE":
                return feed
            elif status in ("CANCELLED", "FATAL"):
                raise RuntimeError(f"Feed {feed_id} failed with status: {status}")

            time.sleep(poll_interval)

    def submit_feed(
        self,
        feed_type: str,
        content: Union[str, bytes],
        marketplace_ids: Optional[List[str]] = None,
        content_type: str = "text/xml; charset=UTF-8",
        wait: bool = True,
        timeout: int = 600
    ) -> Dict[str, Any]:
        """
        Submit a feed: create document, upload, create feed.

        Args:
            feed_type: Type of feed
            content: Feed content
            marketplace_ids: List of marketplace IDs
            content_type: Content type
            wait: Wait for completion
            timeout: Maximum wait time if waiting

        Returns:
            Feed details (completed if wait=True)
        """
        # Create document
        doc = self.create_feed_document(content_type)
        document_id = doc.get("feedDocumentId")
        upload_url = doc.get("url")

        # Upload content
        self.upload_feed_content(upload_url, content, content_type)

        # Create feed
        feed_response = self.create_feed(
            feed_type=feed_type,
            input_feed_document_id=document_id,
            marketplace_ids=marketplace_ids
        )
        feed_id = feed_response.get("feedId")

        if wait:
            return self.wait_for_feed(feed_id, timeout=timeout)

        return feed_response


# Report types (common ones)
VENDOR_REPORT_TYPES = [
    "GET_VENDOR_INVENTORY_REPORT",
    "GET_VENDOR_SALES_REPORT",
    "GET_VENDOR_TRAFFIC_REPORT",
    "GET_VENDOR_FORECASTING_REPORT",
    "GET_VENDOR_REAL_TIME_INVENTORY_REPORT",
    "GET_VENDOR_NET_PURE_PRODUCT_MARGIN_REPORT"
]

SELLER_REPORT_TYPES = [
    "GET_FLAT_FILE_OPEN_LISTINGS_DATA",
    "GET_MERCHANT_LISTINGS_ALL_DATA",
    "GET_MERCHANT_LISTINGS_DATA",
    "GET_MERCHANT_CANCELLED_LISTINGS_DATA",
    "GET_FBA_INVENTORY_PLANNING_DATA",
    "GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA",
    "GET_FBA_FULFILLMENT_INVENTORY_SUMMARY_REPORT"
]

ORDER_REPORT_TYPES = [
    "GET_FLAT_FILE_ALL_ORDERS_DATA_BY_ORDER_DATE_GENERAL",
    "GET_FLAT_FILE_ORDERS_DATA_BY_ORDER_DATE",
    "GET_AMAZON_FULFILLED_SHIPMENTS_DATA_GENERAL",
    "GET_FBA_FULFILLMENT_CUSTOMER_SHIPMENT_SALES_DATA"
]

FINANCIAL_REPORT_TYPES = [
    "GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE",
    "GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE_V2",
    "GET_DATE_RANGE_FINANCIAL_TRANSACTION_DATA"
]

# Feed types
FEED_TYPES = [
    "POST_PRODUCT_DATA",           # Product listings
    "POST_INVENTORY_AVAILABILITY_DATA",  # Inventory
    "POST_PRODUCT_PRICING_DATA",   # Pricing
    "POST_ORDER_FULFILLMENT_DATA", # Shipment confirmations
    "POST_FLAT_FILE_LISTINGS_DATA" # Flat file listings
]


# Helper functions
def get_inventory_report(
    client: SPAPIClient,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """
    Get vendor inventory report.

    Args:
        client: SPAPIClient instance
        start_date: ISO 8601 start date
        end_date: ISO 8601 end date

    Returns:
        Report content
    """
    api = ReportsAPI(client)

    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00Z")
    if not end_date:
        end_date = datetime.utcnow().strftime("%Y-%m-%dT23:59:59Z")

    return api.create_and_download_report(
        report_type="GET_VENDOR_INVENTORY_REPORT",
        data_start_time=start_date,
        data_end_time=end_date
    )


def get_sales_report(
    client: SPAPIClient,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """
    Get vendor sales report.

    Args:
        client: SPAPIClient instance
        start_date: ISO 8601 start date
        end_date: ISO 8601 end date

    Returns:
        Report content
    """
    api = ReportsAPI(client)

    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00Z")
    if not end_date:
        end_date = datetime.utcnow().strftime("%Y-%m-%dT23:59:59Z")

    return api.create_and_download_report(
        report_type="GET_VENDOR_SALES_REPORT",
        data_start_time=start_date,
        data_end_time=end_date
    )


def submit_inventory_feed(
    client: SPAPIClient,
    inventory_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Submit inventory update feed.

    Args:
        client: SPAPIClient instance
        inventory_data: List of SKU/quantity updates

    Returns:
        Feed result
    """
    api = FeedsAPI(client)

    # Build XML feed
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<AmazonEnvelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="amzn-envelope.xsd">',
        '<Header><DocumentVersion>1.01</DocumentVersion><MerchantIdentifier>MERCHANT_ID</MerchantIdentifier></Header>',
        '<MessageType>Inventory</MessageType>'
    ]

    for i, item in enumerate(inventory_data, 1):
        xml_parts.append(f'''<Message>
<MessageID>{i}</MessageID>
<OperationType>Update</OperationType>
<Inventory>
<SKU>{item["sku"]}</SKU>
<Quantity>{item["quantity"]}</Quantity>
</Inventory>
</Message>''')

    xml_parts.append('</AmazonEnvelope>')
    xml_content = "\n".join(xml_parts)

    return api.submit_feed(
        feed_type="POST_INVENTORY_AVAILABILITY_DATA",
        content=xml_content
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SP-API Reports & Feeds Operations")
    parser.add_argument("command", choices=["list-reports", "create-report", "get-report", "download",
                                            "list-feeds", "create-feed"],
                        help="Operation to perform")
    parser.add_argument("--report-type", help="Report type")
    parser.add_argument("--report-id", help="Report ID")
    parser.add_argument("--document-id", help="Document ID")
    parser.add_argument("--start-date", help="Start date (ISO 8601)")
    parser.add_argument("--end-date", help="End date (ISO 8601)")
    parser.add_argument("--days", type=int, default=30, help="Days to look back")
    parser.add_argument("--profile", default="production", help="Config profile")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    auth = SPAPIAuth(profile=args.profile)
    client = SPAPIClient(auth)
    reports_api = ReportsAPI(client)

    try:
        if args.command == "list-reports":
            result = reports_api.get_reports()

        elif args.command == "create-report":
            if not args.report_type:
                print("Error: --report-type required", file=sys.stderr)
                sys.exit(1)

            start = args.start_date
            end = args.end_date
            if not start:
                start = (datetime.utcnow() - timedelta(days=args.days)).strftime("%Y-%m-%dT00:00:00Z")
            if not end:
                end = datetime.utcnow().strftime("%Y-%m-%dT23:59:59Z")

            result = reports_api.create_report(
                report_type=args.report_type,
                data_start_time=start,
                data_end_time=end
            )

        elif args.command == "get-report":
            if not args.report_id:
                print("Error: --report-id required", file=sys.stderr)
                sys.exit(1)
            result = reports_api.get_report(args.report_id)

        elif args.command == "download":
            if not args.document_id:
                print("Error: --document-id required", file=sys.stderr)
                sys.exit(1)
            content = reports_api.download_report(args.document_id)
            print(content)
            sys.exit(0)

        elif args.command == "list-feeds":
            feeds_api = FeedsAPI(client)
            result = feeds_api.get_feeds()

        elif args.command == "create-feed":
            print("Use the Python API directly for feed creation", file=sys.stderr)
            sys.exit(1)

        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            if "reports" in result:
                reports = result["reports"]
                print(f"Found {len(reports)} reports:")
                for r in reports[:10]:
                    print(f"  {r.get('reportId')} - {r.get('reportType')} - {r.get('processingStatus')}")
            elif "feeds" in result:
                feeds = result["feeds"]
                print(f"Found {len(feeds)} feeds:")
                for f in feeds[:10]:
                    print(f"  {f.get('feedId')} - {f.get('feedType')} - {f.get('processingStatus')}")
            else:
                print(json.dumps(result, indent=2, default=str))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
