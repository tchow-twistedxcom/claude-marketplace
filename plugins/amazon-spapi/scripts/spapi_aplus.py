#!/usr/bin/env python3
"""
Amazon SP-API A+ Content API Module

Provides classes for managing A+ Content (Enhanced Brand Content / EBC)
including content creation, ASIN association, and approval workflows.

A+ Content Types:
- EBC: Enhanced Brand Content (Seller Central)
- EMC: Enhanced Marketing Content (Vendor Central)

Content Module Types:
- STANDARD_TEXT: Text blocks
- STANDARD_IMAGE: Image blocks
- STANDARD_COMPARISON_TABLE: Product comparison
- STANDARD_FOUR_IMAGE_TEXT: 4 images with text
- STANDARD_HEADER_IMAGE_TEXT: Header with image
- STANDARD_IMAGE_SIDEBAR: Image with sidebar text
- STANDARD_IMAGE_TEXT_OVERLAY: Text over image
- STANDARD_MULTIPLE_IMAGE_TEXT: Multiple images with text
- STANDARD_PRODUCT_DESCRIPTION: Product description
- STANDARD_SINGLE_IMAGE_HIGHLIGHTS: Single image with bullet points
- STANDARD_SINGLE_IMAGE_SPECS_DETAIL: Single image with specs
- STANDARD_SINGLE_SIDE_IMAGE: Side image
- STANDARD_TECH_SPECS: Technical specifications
- STANDARD_THREE_IMAGE_TEXT: 3 images with text

API Version: 2020-11-01
"""

import json
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from urllib.parse import quote

from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient, SPAPIError


# A+ Content API base path
APLUS_API_VERSION = "2020-11-01"
APLUS_BASE_PATH = f"/aplus/{APLUS_API_VERSION}"


class AplusContentAPI:
    """A+ Content API for managing Enhanced Brand Content."""

    def __init__(self, client: SPAPIClient):
        """
        Initialize A+ Content API.

        Args:
            client: SPAPIClient instance
        """
        self.client = client
        self.auth = client.auth

    # =========================================================================
    # Content Document Operations
    # =========================================================================

    def search_content_documents(
        self,
        marketplace_id: Optional[str] = None,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for A+ Content documents.

        Args:
            marketplace_id: Marketplace ID (defaults to configured)
            page_token: Pagination token

        Returns:
            Search results with content documents list
        """
        if marketplace_id is None:
            marketplace_id = self.auth.get_marketplace_id()

        params = {"marketplaceId": marketplace_id}
        if page_token:
            params["pageToken"] = page_token

        path = f"{APLUS_BASE_PATH}/contentDocuments"
        status, response = self.client.get(path, "aplusContent", params=params)
        return response

    def get_content_document(
        self,
        content_reference_key: str,
        marketplace_id: Optional[str] = None,
        included_data_set: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get A+ Content document by reference key.

        Args:
            content_reference_key: Content reference key
            marketplace_id: Marketplace ID (defaults to configured)
            included_data_set: Additional data to include
                               Options: CONTENTS, METADATA

        Returns:
            Content document details
        """
        if marketplace_id is None:
            marketplace_id = self.auth.get_marketplace_id()

        params = {"marketplaceId": marketplace_id}
        if included_data_set:
            params["includedDataSet"] = ",".join(included_data_set)

        path = f"{APLUS_BASE_PATH}/contentDocuments/{quote(content_reference_key)}"
        status, response = self.client.get(path, "aplusContent", params=params)
        return response

    def create_content_document(
        self,
        content_document: Dict[str, Any],
        marketplace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new A+ Content document.

        Args:
            content_document: Content document structure with:
                - name: Display name
                - contentType: EBC or EMC
                - contentSubType: Optional sub-type
                - locale: Content locale (e.g., en_US)
                - contentModuleList: List of content modules

            marketplace_id: Marketplace ID (defaults to configured)

        Returns:
            Created content document with reference key

        Content Document Structure:
            {
                "name": "My Product A+ Content",
                "contentType": "EBC",
                "locale": "en_US",
                "contentModuleList": [
                    {
                        "contentModuleType": "STANDARD_HEADER_IMAGE_TEXT",
                        "standardHeaderImageTextModule": {
                            "headline": {"value": "About Our Product"},
                            "block": {
                                "image": {"uploadDestinationId": "..."},
                                "headline": {"value": "Feature 1"}
                            }
                        }
                    }
                ]
            }
        """
        if marketplace_id is None:
            marketplace_id = self.auth.get_marketplace_id()

        params = {"marketplaceId": marketplace_id}
        data = {"contentDocument": content_document}

        path = f"{APLUS_BASE_PATH}/contentDocuments"
        status, response = self.client.post(path, "aplusContent", params=params, data=data)
        return response

    def update_content_document(
        self,
        content_reference_key: str,
        content_document: Dict[str, Any],
        marketplace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing A+ Content document.

        Args:
            content_reference_key: Content reference key to update
            content_document: Updated content document structure
            marketplace_id: Marketplace ID (defaults to configured)

        Returns:
            Updated content document
        """
        if marketplace_id is None:
            marketplace_id = self.auth.get_marketplace_id()

        params = {"marketplaceId": marketplace_id}
        data = {"contentDocument": content_document}

        path = f"{APLUS_BASE_PATH}/contentDocuments/{quote(content_reference_key)}"
        status, response = self.client.post(path, "aplusContent", params=params, data=data)
        return response

    # =========================================================================
    # ASIN Association
    # =========================================================================

    def get_content_document_asin_relations(
        self,
        content_reference_key: str,
        marketplace_id: Optional[str] = None,
        included_data_set: Optional[List[str]] = None,
        asin_set: Optional[List[str]] = None,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get ASINs associated with a content document.

        Args:
            content_reference_key: Content reference key
            marketplace_id: Marketplace ID (defaults to configured)
            included_data_set: Additional data to include
            asin_set: Filter by specific ASINs
            page_token: Pagination token

        Returns:
            List of ASIN relations
        """
        if marketplace_id is None:
            marketplace_id = self.auth.get_marketplace_id()

        params = {"marketplaceId": marketplace_id}
        if included_data_set:
            params["includedDataSet"] = ",".join(included_data_set)
        if asin_set:
            params["asinSet"] = ",".join(asin_set)
        if page_token:
            params["pageToken"] = page_token

        path = f"{APLUS_BASE_PATH}/contentDocuments/{quote(content_reference_key)}/asins"
        status, response = self.client.get(path, "aplusContent", params=params)
        return response

    def post_content_document_asin_relations(
        self,
        content_reference_key: str,
        asin_set: List[str],
        marketplace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Associate ASINs with a content document.

        Args:
            content_reference_key: Content reference key
            asin_set: List of ASINs to associate
            marketplace_id: Marketplace ID (defaults to configured)

        Returns:
            Association result
        """
        if marketplace_id is None:
            marketplace_id = self.auth.get_marketplace_id()

        params = {"marketplaceId": marketplace_id}
        data = {"asinSet": asin_set}

        path = f"{APLUS_BASE_PATH}/contentDocuments/{quote(content_reference_key)}/asins"
        status, response = self.client.post(path, "aplusContent", params=params, data=data)
        return response

    # =========================================================================
    # Approval Workflow
    # =========================================================================

    def post_content_document_approval_submission(
        self,
        content_reference_key: str,
        marketplace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit content document for approval.

        Args:
            content_reference_key: Content reference key
            marketplace_id: Marketplace ID (defaults to configured)

        Returns:
            Approval submission result
        """
        if marketplace_id is None:
            marketplace_id = self.auth.get_marketplace_id()

        params = {"marketplaceId": marketplace_id}

        path = f"{APLUS_BASE_PATH}/contentDocuments/{quote(content_reference_key)}/approvalSubmissions"
        status, response = self.client.post(path, "aplusContent", params=params)
        return response

    def post_content_document_suspend_submission(
        self,
        content_reference_key: str,
        marketplace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suspend (unpublish) content document.

        Args:
            content_reference_key: Content reference key
            marketplace_id: Marketplace ID (defaults to configured)

        Returns:
            Suspend submission result
        """
        if marketplace_id is None:
            marketplace_id = self.auth.get_marketplace_id()

        params = {"marketplaceId": marketplace_id}

        path = f"{APLUS_BASE_PATH}/contentDocuments/{quote(content_reference_key)}/suspendSubmissions"
        status, response = self.client.post(path, "aplusContent", params=params)
        return response

    # =========================================================================
    # Publish Records
    # =========================================================================

    def search_content_publish_records(
        self,
        marketplace_id: Optional[str] = None,
        asin: Optional[str] = None,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search A+ Content publish records.

        Args:
            marketplace_id: Marketplace ID (defaults to configured)
            asin: Filter by ASIN
            page_token: Pagination token

        Returns:
            Publish records list
        """
        if marketplace_id is None:
            marketplace_id = self.auth.get_marketplace_id()

        data = {}
        if asin:
            data["asin"] = asin
        if page_token:
            data["pageToken"] = page_token

        path = f"{APLUS_BASE_PATH}/contentPublishRecords/{quote(marketplace_id)}/search"
        status, response = self.client.post(path, "aplusContent", data=data)
        return response

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def list_all_content_documents(
        self,
        marketplace_id: Optional[str] = None,
        max_pages: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all A+ Content documents with pagination.

        Args:
            marketplace_id: Marketplace ID (defaults to configured)
            max_pages: Maximum pages to fetch

        Returns:
            List of all content documents
        """
        all_documents = []
        page_token = None
        page = 0

        while page < max_pages:
            result = self.search_content_documents(
                marketplace_id=marketplace_id,
                page_token=page_token
            )

            documents = result.get("contentMetadataRecords", [])
            all_documents.extend(documents)

            page_token = result.get("nextPageToken")
            if not page_token:
                break

            page += 1

        return all_documents

    def get_content_for_asin(
        self,
        asin: str,
        marketplace_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get A+ Content associated with a specific ASIN.

        Args:
            asin: Amazon ASIN
            marketplace_id: Marketplace ID (defaults to configured)

        Returns:
            Content document if found, None otherwise
        """
        # Search publish records for this ASIN
        result = self.search_content_publish_records(
            marketplace_id=marketplace_id,
            asin=asin
        )

        records = result.get("publishRecordList", [])
        if not records:
            return None

        # Get the most recent published content
        for record in records:
            content_key = record.get("contentReferenceKey")
            if content_key:
                try:
                    return self.get_content_document(
                        content_reference_key=content_key,
                        marketplace_id=marketplace_id,
                        included_data_set=["CONTENTS", "METADATA"]
                    )
                except SPAPIError:
                    continue

        return None


# CLI interface for testing
def main():
    """CLI interface for A+ Content API operations."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Amazon SP-API A+ Content operations"
    )
    parser.add_argument(
        "--profile",
        default="production",
        help="SP-API config profile"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List content
    list_cmd = subparsers.add_parser("list", help="List A+ Content documents")

    # Get content
    get_cmd = subparsers.add_parser("get", help="Get A+ Content by reference key")
    get_cmd.add_argument("content_key", help="Content reference key")

    # Get content for ASIN
    asin_cmd = subparsers.add_parser("asin", help="Get A+ Content for an ASIN")
    asin_cmd.add_argument("asin", help="Amazon ASIN")

    # List ASINs for content
    asins_cmd = subparsers.add_parser("asins", help="List ASINs for content")
    asins_cmd.add_argument("content_key", help="Content reference key")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize API
    auth = SPAPIAuth(profile=args.profile)
    client = SPAPIClient(auth)
    api = AplusContentAPI(client)

    try:
        if args.command == "list":
            documents = api.list_all_content_documents()
            print(f"Found {len(documents)} A+ Content documents:\n")
            for doc in documents:
                print(f"  Key: {doc.get('contentReferenceKey')}")
                print(f"  Name: {doc.get('name')}")
                print(f"  Type: {doc.get('contentType')}")
                print(f"  Status: {doc.get('status')}")
                print()

        elif args.command == "get":
            result = api.get_content_document(
                args.content_key,
                included_data_set=["CONTENTS", "METADATA"]
            )
            print(json.dumps(result, indent=2, default=str))

        elif args.command == "asin":
            result = api.get_content_for_asin(args.asin)
            if result:
                print(json.dumps(result, indent=2, default=str))
            else:
                print(f"No A+ Content found for ASIN {args.asin}")

        elif args.command == "asins":
            result = api.get_content_document_asin_relations(args.content_key)
            asins = result.get("asinMetadataSet", [])
            print(f"ASINs for {args.content_key}:\n")
            for asin_data in asins:
                print(f"  {asin_data.get('asin')}")

    except SPAPIError as e:
        print(f"API Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
