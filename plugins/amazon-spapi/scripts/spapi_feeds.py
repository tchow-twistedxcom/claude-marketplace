#!/usr/bin/env python3
"""
Amazon SP-API Feeds API

Provides functionality for submitting and managing feeds including:
- JSON_LISTINGS_FEED for bulk listing updates
- Feed document upload/download
- Feed status tracking

Reference: https://developer-docs.amazon.com/sp-api/docs/feeds-api-v2021-06-30-reference
"""

import json
import gzip
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from spapi_client import SPAPIClient, SPAPIError


class FeedsAPI:
    """Amazon SP-API Feeds API wrapper."""

    def __init__(self, client: SPAPIClient):
        self.client = client
        self.marketplace_id = client.auth.get_marketplace_id(client.profile)

    def create_feed_document(self, content_type: str = "application/json; charset=UTF-8") -> Dict:
        """
        Create a feed document to get an upload URL.

        Args:
            content_type: MIME type of the feed content

        Returns:
            Dict with feedDocumentId and url for upload
        """
        path = "/feeds/2021-06-30/documents"
        data = {"contentType": content_type}

        status, response = self.client.post(path, "feeds", data=data)
        return response

    def upload_feed_document(self, url: str, content: str, content_type: str = "application/json; charset=UTF-8") -> bool:
        """
        Upload feed content to the provided URL.

        Args:
            url: Pre-signed URL from create_feed_document
            content: Feed content (JSON string)
            content_type: MIME type

        Returns:
            True if upload successful
        """
        # Compress the content
        compressed = gzip.compress(content.encode('utf-8'))

        headers = {
            "Content-Type": content_type,
            "Content-Encoding": "gzip"
        }

        req = Request(url, data=compressed, headers=headers, method="PUT")
        with urlopen(req, timeout=60) as resp:
            return resp.status == 200

    def create_feed(
        self,
        feed_document_id: str,
        feed_type: str,
        marketplace_ids: List[str] = None
    ) -> Dict:
        """
        Create a feed using an uploaded feed document.

        Args:
            feed_document_id: ID from create_feed_document
            feed_type: Feed type (e.g., JSON_LISTINGS_FEED)
            marketplace_ids: List of marketplace IDs (defaults to account marketplace)

        Returns:
            Dict with feedId
        """
        path = "/feeds/2021-06-30/feeds"
        data = {
            "feedType": feed_type,
            "marketplaceIds": marketplace_ids or [self.marketplace_id],
            "inputFeedDocumentId": feed_document_id
        }

        status, response = self.client.post(path, "feeds", data=data)
        return response

    def get_feed(self, feed_id: str) -> Dict:
        """
        Get feed status and details.

        Args:
            feed_id: Feed ID from create_feed

        Returns:
            Feed details including processingStatus
        """
        path = f"/feeds/2021-06-30/feeds/{feed_id}"
        status, response = self.client.get(path, "feeds.getFeed")
        return response

    def get_feed_document(self, feed_document_id: str) -> Dict:
        """
        Get feed document details and download URL.

        Args:
            feed_document_id: Feed document ID

        Returns:
            Dict with url for downloading results
        """
        path = f"/feeds/2021-06-30/documents/{feed_document_id}"
        status, response = self.client.get(path, "feeds.getFeed")
        return response

    def download_feed_result(self, url: str) -> str:
        """
        Download feed processing result.

        Args:
            url: Download URL from get_feed_document

        Returns:
            Feed result content
        """
        req = Request(url, method="GET")
        with urlopen(req, timeout=60) as resp:
            content = resp.read()
            # Check if gzipped
            if content[:2] == b'\x1f\x8b':
                content = gzip.decompress(content)
            return content.decode('utf-8')

    def wait_for_feed(
        self,
        feed_id: str,
        max_wait: int = 600,
        poll_interval: int = 10
    ) -> Dict:
        """
        Wait for a feed to complete processing.

        Args:
            feed_id: Feed ID to monitor
            max_wait: Maximum wait time in seconds
            poll_interval: Seconds between status checks

        Returns:
            Final feed status

        Raises:
            TimeoutError: If feed doesn't complete within max_wait
        """
        start_time = time.time()

        while time.time() - start_time < max_wait:
            feed = self.get_feed(feed_id)
            status = feed.get("processingStatus")

            if status in ("DONE", "CANCELLED", "FATAL"):
                return feed

            time.sleep(poll_interval)

        raise TimeoutError(f"Feed {feed_id} did not complete within {max_wait} seconds")

    def submit_json_listings_feed(
        self,
        messages: List[Dict],
        seller_id: str,
        wait_for_completion: bool = False
    ) -> Dict:
        """
        Submit a JSON_LISTINGS_FEED.

        Args:
            messages: List of listing messages
            seller_id: Seller ID
            wait_for_completion: Whether to wait for feed to complete

        Returns:
            Dict with feedId and optionally final status
        """
        # Build feed content
        feed_content = {
            "header": {
                "sellerId": seller_id,
                "version": "2.0"
            },
            "messages": messages
        }

        # Create feed document
        doc = self.create_feed_document()
        feed_document_id = doc["feedDocumentId"]
        upload_url = doc["url"]

        # Upload content
        content_json = json.dumps(feed_content, indent=2)
        self.upload_feed_document(upload_url, content_json)

        # Create the feed
        feed = self.create_feed(feed_document_id, "JSON_LISTINGS_FEED")
        feed_id = feed["feedId"]

        result = {
            "feedId": feed_id,
            "feedDocumentId": feed_document_id,
            "messageCount": len(messages)
        }

        # Optionally wait for completion
        if wait_for_completion:
            final_status = self.wait_for_feed(feed_id)
            result["processingStatus"] = final_status.get("processingStatus")
            result["resultFeedDocumentId"] = final_status.get("resultFeedDocumentId")

            # Download result if available
            if result.get("resultFeedDocumentId"):
                result_doc = self.get_feed_document(result["resultFeedDocumentId"])
                if result_doc.get("url"):
                    result["result"] = self.download_feed_result(result_doc["url"])

        return result


def build_relationship_message(
    message_id: int,
    sku: str,
    parent_sku: str = None,
    parent_asin: str = None,
    operation_type: str = "PARTIAL_UPDATE"
) -> Dict:
    """
    Build a JSON_LISTINGS_FEED message for parent-child relationship.

    Args:
        message_id: Unique message ID (1-based)
        sku: Child SKU
        parent_sku: Parent SKU (preferred)
        parent_asin: Parent ASIN (alternative if no parent SKU)
        operation_type: PARTIAL_UPDATE, UPDATE, or DELETE

    Returns:
        Feed message dict
    """
    message = {
        "messageId": message_id,
        "sku": sku,
        "operationType": operation_type,
        "attributes": {}
    }

    # Build relationship attribute
    if parent_sku:
        message["attributes"]["child_parent_sku_relationship"] = [
            {
                "child_relationship_type": "variation",
                "parent_sku": parent_sku,
                "marketplace_id": "ATVPDKIKX0DER"
            }
        ]
    elif parent_asin:
        # Note: Using ASIN instead of SKU - may not work in all cases
        # This is for Vendor Central parents where seller has no SKU
        message["attributes"]["parentage_level"] = [
            {
                "value": "child",
                "marketplace_id": "ATVPDKIKX0DER"
            }
        ]
        # Alternative approach - try using the ASIN directly
        message["attributes"]["child_parent_sku_relationship"] = [
            {
                "child_relationship_type": "variation",
                "parent_asin": parent_asin,
                "marketplace_id": "ATVPDKIKX0DER"
            }
        ]

    return message


if __name__ == "__main__":
    print("SP-API Feeds Module")
    print("Provides functionality for submitting JSON_LISTINGS_FEED and other feeds.")
    print("\nUsage:")
    print("  from spapi_feeds import FeedsAPI, build_relationship_message")
    print("  feeds = FeedsAPI(client)")
    print("  messages = [build_relationship_message(1, 'SKU123', parent_sku='PARENT-SKU')]")
    print("  result = feeds.submit_json_listings_feed(messages, seller_id)")
