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

# Brand Analytics reports (requires Brand Analytics role + Brand Registry)
BRAND_ANALYTICS_REPORT_TYPES = [
    "GET_BRAND_ANALYTICS_SEARCH_TERMS_REPORT",       # Top-clicked ASINs by search keyword
    "GET_BRAND_ANALYTICS_MARKET_BASKET_REPORT",      # ASINs frequently bought together
    "GET_BRAND_ANALYTICS_REPEAT_PURCHASE_REPORT",    # ASINs with repeat customers
    "GET_BRAND_ANALYTICS_ALTERNATE_PURCHASE_REPORT", # Alternative purchases
    "GET_SALES_AND_TRAFFIC_REPORT",                  # Search Query Performance (brand owner)
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


# Brand Analytics helper functions

def _align_date_to_period(dt: datetime, period: str, is_start: bool = True) -> datetime:
    """
    Align a datetime to the correct boundary for Brand Analytics reports.

    IMPORTANT: End dates are aligned BACKWARDS to the most recent complete period,
    since Amazon cannot provide data for future dates.

    Args:
        dt: The datetime to align
        period: WEEK, MONTH, or QUARTER
        is_start: If True, align to start boundary; if False, align to end boundary

    Returns:
        Aligned datetime
    """
    if period == "WEEK":
        # WEEK: Sunday start, Saturday end
        # weekday(): Monday=0, Tuesday=1, ..., Saturday=5, Sunday=6
        if is_start:
            # Go back to previous Sunday (or stay if already Sunday)
            days_since_sunday = (dt.weekday() + 1) % 7
            return dt - timedelta(days=days_since_sunday)
        else:
            # Go back to previous Saturday (or stay if already Saturday)
            # This ensures we don't request future dates
            days_since_saturday = (dt.weekday() + 2) % 7
            return dt - timedelta(days=days_since_saturday)

    elif period == "MONTH":
        if is_start:
            # First day of month
            return dt.replace(day=1)
        else:
            # Last day of previous month (or current month if we're past it)
            # Go to first of current month, then subtract 1 day
            if dt.day < 28:
                # Not near end of month, go to end of previous month
                first_of_month = dt.replace(day=1)
                return first_of_month - timedelta(days=1)
            else:
                # Near end of month, use current month's last day
                next_month = dt.replace(day=28) + timedelta(days=4)
                return next_month - timedelta(days=next_month.day)

    elif period == "QUARTER":
        quarter_starts = {1: 1, 2: 4, 3: 7, 4: 10}
        quarter = (dt.month - 1) // 3 + 1

        if is_start:
            return dt.replace(month=quarter_starts[quarter], day=1)
        else:
            # End of previous quarter (or current if we're at the end)
            end_months = {1: 3, 2: 6, 3: 9, 4: 12}
            end_month = end_months[quarter]
            # Check if we're near the end of the quarter
            if dt.month == end_month and dt.day >= 28:
                # Use current quarter end
                next_quarter_start = dt.replace(month=end_month, day=28) + timedelta(days=4)
                return next_quarter_start - timedelta(days=next_quarter_start.day)
            else:
                # Use previous quarter end
                prev_quarter = quarter - 1 if quarter > 1 else 4
                prev_quarter_end_month = end_months[prev_quarter]
                if prev_quarter == 4 and quarter == 1:
                    # Previous quarter 4 is in previous year
                    prev_end = dt.replace(year=dt.year-1, month=12, day=31)
                else:
                    next_q_start = dt.replace(month=prev_quarter_end_month, day=28) + timedelta(days=4)
                    prev_end = next_q_start - timedelta(days=next_q_start.day)
                return prev_end

    return dt


def get_brand_analytics_search_terms(
    client: SPAPIClient,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    report_period: str = "WEEK"
) -> Dict[str, Any]:
    """
    Get Brand Analytics Search Terms report.

    Returns top-clicked ASINs by search keyword for your brand.
    Requires Brand Analytics role and Brand Registry enrollment.

    Note: Dates are automatically aligned to period boundaries:
    - WEEK: start must be Sunday
    - MONTH: start must be 1st of month
    - QUARTER: start must be 1st of quarter

    Args:
        client: SPAPIClient instance
        start_date: ISO 8601 start date (will be aligned to period)
        end_date: ISO 8601 end date (will be aligned to period)
        report_period: WEEK, MONTH, or QUARTER

    Returns:
        Parsed report data with ASINs per search term
    """
    api = ReportsAPI(client)

    now = datetime.now(tz=None)  # Use local time, convert to UTC string

    # IMPORTANT: Search Terms report cannot span multiple periods per Amazon docs.
    # We must request exactly ONE period (1 week, 1 month, or 1 quarter).

    if not end_date:
        end_dt = now - timedelta(days=1)  # Yesterday (data may not be available for today)
    else:
        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00").replace("+00:00", ""))

    # Align end date to period boundary first
    end_dt = _align_date_to_period(end_dt, report_period, is_start=False)

    # Calculate start date as the beginning of the SAME period (single period only)
    if report_period == "WEEK":
        # Start is the Sunday of the same week as end (Saturday)
        start_dt = end_dt - timedelta(days=6)
    elif report_period == "MONTH":
        # Start is first day of the same month
        start_dt = end_dt.replace(day=1)
    elif report_period == "QUARTER":
        # Start is first day of the same quarter
        quarter = (end_dt.month - 1) // 3 + 1
        quarter_starts = {1: 1, 2: 4, 3: 7, 4: 10}
        start_dt = end_dt.replace(month=quarter_starts[quarter], day=1)
    else:
        start_dt = end_dt - timedelta(days=6)

    # Override with user-provided start_date if given (but warn it may fail)
    if start_date:
        start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00").replace("+00:00", ""))
        start_dt = _align_date_to_period(start_dt, report_period, is_start=True)

    start_date = start_dt.strftime("%Y-%m-%dT00:00:00Z")
    end_date = end_dt.strftime("%Y-%m-%dT23:59:59Z")

    content = api.create_and_download_report(
        report_type="GET_BRAND_ANALYTICS_SEARCH_TERMS_REPORT",
        data_start_time=start_date,
        data_end_time=end_date,
        report_options={"reportPeriod": report_period}
    )

    return _parse_brand_analytics_report(content)


def get_brand_analytics_market_basket(
    client: SPAPIClient,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    report_period: str = "WEEK"
) -> Dict[str, Any]:
    """
    Get Brand Analytics Market Basket report.

    Returns ASINs frequently purchased together with your products.
    Useful for discovering related ASINs in your brand's ecosystem.

    Note: Dates are automatically aligned to period boundaries.

    Args:
        client: SPAPIClient instance
        start_date: ISO 8601 start date (will be aligned to period)
        end_date: ISO 8601 end date (will be aligned to period)
        report_period: WEEK, MONTH, or QUARTER

    Returns:
        Parsed report data with co-purchased ASINs
    """
    api = ReportsAPI(client)

    now = datetime.now(tz=None)

    if not start_date:
        days_back = {"WEEK": 28, "MONTH": 60, "QUARTER": 180}.get(report_period, 30)
        start_dt = now - timedelta(days=days_back)
    else:
        start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00").replace("+00:00", ""))

    if not end_date:
        end_dt = now - timedelta(days=1)
    else:
        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00").replace("+00:00", ""))

    # Align dates to period boundaries
    start_dt = _align_date_to_period(start_dt, report_period, is_start=True)
    end_dt = _align_date_to_period(end_dt, report_period, is_start=False)

    start_date = start_dt.strftime("%Y-%m-%dT00:00:00Z")
    end_date = end_dt.strftime("%Y-%m-%dT23:59:59Z")

    content = api.create_and_download_report(
        report_type="GET_BRAND_ANALYTICS_MARKET_BASKET_REPORT",
        data_start_time=start_date,
        data_end_time=end_date,
        report_options={"reportPeriod": report_period}
    )

    return _parse_brand_analytics_report(content)


def get_brand_analytics_repeat_purchase(
    client: SPAPIClient,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    report_period: str = "MONTH"
) -> Dict[str, Any]:
    """
    Get Brand Analytics Repeat Purchase report.

    Returns ASINs with repeat customer purchases.

    Note: Dates are automatically aligned to period boundaries.

    Args:
        client: SPAPIClient instance
        start_date: ISO 8601 start date (will be aligned to period)
        end_date: ISO 8601 end date (will be aligned to period)
        report_period: WEEK, MONTH, or QUARTER

    Returns:
        Parsed report data with repeat purchase metrics per ASIN
    """
    api = ReportsAPI(client)

    now = datetime.now(tz=None)

    if not start_date:
        days_back = {"WEEK": 28, "MONTH": 90, "QUARTER": 180}.get(report_period, 90)
        start_dt = now - timedelta(days=days_back)
    else:
        start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00").replace("+00:00", ""))

    if not end_date:
        end_dt = now - timedelta(days=1)
    else:
        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00").replace("+00:00", ""))

    # Align dates to period boundaries
    start_dt = _align_date_to_period(start_dt, report_period, is_start=True)
    end_dt = _align_date_to_period(end_dt, report_period, is_start=False)

    start_date = start_dt.strftime("%Y-%m-%dT00:00:00Z")
    end_date = end_dt.strftime("%Y-%m-%dT23:59:59Z")

    content = api.create_and_download_report(
        report_type="GET_BRAND_ANALYTICS_REPEAT_PURCHASE_REPORT",
        data_start_time=start_date,
        data_end_time=end_date,
        report_options={"reportPeriod": report_period}
    )

    return _parse_brand_analytics_report(content)


def _parse_brand_analytics_report(content: str) -> Dict[str, Any]:
    """
    Parse Brand Analytics report content.

    Handles both JSON and tab-delimited formats.

    Args:
        content: Raw report content

    Returns:
        Parsed data with extracted ASINs
    """
    # Try JSON first (newer format)
    try:
        data = json.loads(content)
        return {
            "format": "json",
            "data": data,
            "asins": _extract_asins_from_json(data)
        }
    except json.JSONDecodeError:
        pass

    # Fall back to tab-delimited
    lines = content.strip().split('\n')
    if not lines:
        return {"format": "empty", "data": [], "asins": []}

    headers = lines[0].split('\t')

    # Find ASIN column(s)
    asin_columns = []
    for i, h in enumerate(headers):
        h_lower = h.lower()
        if 'asin' in h_lower:
            asin_columns.append(i)

    rows = []
    asins = set()

    for line in lines[1:]:
        fields = line.split('\t')
        row = {}
        for i, header in enumerate(headers):
            if i < len(fields):
                row[header] = fields[i]
                # Extract ASINs
                if i in asin_columns and fields[i]:
                    asin = fields[i].strip()
                    if asin and len(asin) == 10 and asin.startswith('B'):
                        asins.add(asin)
        rows.append(row)

    return {
        "format": "tsv",
        "headers": headers,
        "data": rows,
        "asins": list(asins)
    }


def _extract_asins_from_json(data: Any) -> List[str]:
    """
    Recursively extract ASINs from JSON data.

    Args:
        data: JSON data (dict, list, or primitive)

    Returns:
        List of unique ASINs found
    """
    asins = set()

    def _extract(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if 'asin' in key.lower() and isinstance(value, str):
                    if len(value) == 10 and value.startswith('B'):
                        asins.add(value)
                else:
                    _extract(value)
        elif isinstance(obj, list):
            for item in obj:
                _extract(item)

    _extract(data)
    return list(asins)


def extract_all_brand_asins(
    client: SPAPIClient,
    report_period: str = "WEEK"
) -> Dict[str, Any]:
    """
    Extract all ASINs from Brand Analytics reports.

    Combines Search Terms, Market Basket, and Repeat Purchase reports
    to get comprehensive ASIN coverage for your brand.

    Note: Each report uses appropriate period-aligned date ranges:
    - WEEK: Most recent complete week (Sunday-Saturday)
    - MONTH: Most recent complete month
    - QUARTER: Most recent complete quarter

    Per Amazon docs, Search Terms cannot span multiple periods,
    so we request only the most recent complete period.

    Args:
        client: SPAPIClient instance
        report_period: WEEK, MONTH, or QUARTER (default: WEEK)

    Returns:
        Combined results with deduplicated ASINs and source tracking
    """
    # Let helper functions handle date calculation and alignment
    # They will use appropriate defaults based on report_period

    results = {
        "search_terms": {"asins": [], "error": None},
        "market_basket": {"asins": [], "error": None},
        "repeat_purchase": {"asins": [], "error": None},
        "all_asins": [],
        "asin_sources": {},
        "period": report_period
    }

    # Search Terms Report - cannot span multiple periods per Amazon docs
    try:
        search_data = get_brand_analytics_search_terms(
            client,
            start_date=None,  # Let helper calculate aligned dates
            end_date=None,
            report_period=report_period
        )
        results["search_terms"]["asins"] = search_data.get("asins", [])
        results["search_terms"]["count"] = len(results["search_terms"]["asins"])
        for asin in results["search_terms"]["asins"]:
            results["asin_sources"].setdefault(asin, []).append("search_terms")
    except Exception as e:
        results["search_terms"]["error"] = str(e)

    # Market Basket Report - can span multiple periods
    try:
        basket_data = get_brand_analytics_market_basket(
            client,
            start_date=None,
            end_date=None,
            report_period=report_period
        )
        results["market_basket"]["asins"] = basket_data.get("asins", [])
        results["market_basket"]["count"] = len(results["market_basket"]["asins"])
        for asin in results["market_basket"]["asins"]:
            results["asin_sources"].setdefault(asin, []).append("market_basket")
    except Exception as e:
        results["market_basket"]["error"] = str(e)

    # Repeat Purchase Report - only supports WEEK, MONTH, QUARTER (not DAY)
    try:
        # Use MONTH for repeat purchase as it provides better data coverage
        repeat_period = report_period if report_period != "DAY" else "MONTH"
        repeat_data = get_brand_analytics_repeat_purchase(
            client,
            start_date=None,
            end_date=None,
            report_period=repeat_period
        )
        results["repeat_purchase"]["asins"] = repeat_data.get("asins", [])
        results["repeat_purchase"]["count"] = len(results["repeat_purchase"]["asins"])
        for asin in results["repeat_purchase"]["asins"]:
            results["asin_sources"].setdefault(asin, []).append("repeat_purchase")
    except Exception as e:
        results["repeat_purchase"]["error"] = str(e)

    # Combine and deduplicate
    all_asins = set()
    all_asins.update(results["search_terms"]["asins"])
    all_asins.update(results["market_basket"]["asins"])
    all_asins.update(results["repeat_purchase"]["asins"])

    results["all_asins"] = sorted(list(all_asins))
    results["total_unique_asins"] = len(results["all_asins"])

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SP-API Reports & Feeds Operations")
    parser.add_argument("command", choices=[
        "list-reports", "create-report", "get-report", "download",
        "list-feeds", "create-feed",
        # Brand Analytics commands
        "brand-search-terms", "brand-market-basket", "brand-repeat-purchase",
        "brand-extract-all"
    ], help="Operation to perform")
    parser.add_argument("--report-type", help="Report type")
    parser.add_argument("--report-id", help="Report ID")
    parser.add_argument("--document-id", help="Document ID")
    parser.add_argument("--start-date", help="Start date (ISO 8601)")
    parser.add_argument("--end-date", help="End date (ISO 8601)")
    parser.add_argument("--days", type=int, default=30, help="Days to look back")
    parser.add_argument("--period", default="WEEK", choices=["WEEK", "MONTH", "QUARTER"],
                        help="Report period for Brand Analytics")
    parser.add_argument("--profile", default="production", help="Config profile")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--asins-only", action="store_true", help="Output only ASINs (one per line)")

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

        # Brand Analytics commands
        # Note: Let helper functions handle date alignment per Amazon docs requirements
        elif args.command == "brand-search-terms":
            # Pass dates only if explicitly provided by user
            result = get_brand_analytics_search_terms(
                client,
                start_date=args.start_date,  # None if not provided - helper will calculate aligned dates
                end_date=args.end_date,
                report_period=args.period
            )

            if args.asins_only:
                for asin in result.get("asins", []):
                    print(asin)
                sys.exit(0)

        elif args.command == "brand-market-basket":
            result = get_brand_analytics_market_basket(
                client,
                start_date=args.start_date,
                end_date=args.end_date,
                report_period=args.period
            )

            if args.asins_only:
                for asin in result.get("asins", []):
                    print(asin)
                sys.exit(0)

        elif args.command == "brand-repeat-purchase":
            result = get_brand_analytics_repeat_purchase(
                client,
                start_date=args.start_date,
                end_date=args.end_date,
                report_period=args.period
            )

            if args.asins_only:
                for asin in result.get("asins", []):
                    print(asin)
                sys.exit(0)

        elif args.command == "brand-extract-all":
            print(f"Extracting ASINs from all Brand Analytics reports (period: {args.period})...",
                  file=sys.stderr)
            result = extract_all_brand_asins(client, report_period=args.period)

            if args.asins_only:
                for asin in result.get("all_asins", []):
                    print(asin)
                sys.exit(0)

            # Summary output
            if not args.json:
                print(f"\nBrand Analytics ASIN Extraction Summary:")
                print(f"  Search Terms: {result['search_terms'].get('count', 0)} ASINs")
                if result['search_terms'].get('error'):
                    print(f"    Error: {result['search_terms']['error']}")
                print(f"  Market Basket: {result['market_basket'].get('count', 0)} ASINs")
                if result['market_basket'].get('error'):
                    print(f"    Error: {result['market_basket']['error']}")
                print(f"  Repeat Purchase: {result['repeat_purchase'].get('count', 0)} ASINs")
                if result['repeat_purchase'].get('error'):
                    print(f"    Error: {result['repeat_purchase']['error']}")
                print(f"\n  Total Unique ASINs: {result['total_unique_asins']}")
                print(f"\nASINs: {', '.join(result['all_asins'][:20])}{'...' if len(result['all_asins']) > 20 else ''}")
                sys.exit(0)

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
