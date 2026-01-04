---
name: spapi-reports-feeds
description: "Manage Amazon reports and feeds. Use when requesting reports, checking report status, downloading report documents, or submitting bulk data feeds."
license: MIT
version: 1.0.0
---

# Amazon SP-API Reports & Feeds

This skill provides guidance for managing Amazon reports and data feeds through the Selling Partner API.

## When to Use This Skill

Activate this skill when working with:
- Report generation and download
- Bulk data feeds submission
- Data Kiosk GraphQL queries
- Scheduled reports
- Large-scale data operations

## Core APIs

- **Reports API** - Generate and download reports
- **Feeds API** - Submit bulk data updates
- **Data Kiosk API** - GraphQL-based analytics

## Reports Workflow

```python
from spapi_auth import SPAPIAuth
from spapi_client import SPAPIClient
import time

auth = SPAPIAuth()
client = SPAPIClient(auth)

# 1. Create report request
status, data = client.post(
    "/reports/2021-06-30/reports",
    "reports",
    data={
        "reportType": "GET_VENDOR_INVENTORY_REPORT",
        "marketplaceIds": [auth.get_marketplace_id()],
        "dataStartTime": "2024-01-01T00:00:00Z",
        "dataEndTime": "2024-01-31T23:59:59Z"
    }
)
report_id = data.get("reportId")

# 2. Poll for completion
while True:
    status, report = client.get(
        f"/reports/2021-06-30/reports/{report_id}",
        "reports.getReport"
    )

    report_status = report.get("processingStatus")
    if report_status == "DONE":
        document_id = report.get("reportDocumentId")
        break
    elif report_status in ("CANCELLED", "FATAL"):
        raise RuntimeError(f"Report failed: {report_status}")

    time.sleep(30)

# 3. Get document URL
status, doc = client.get(
    f"/reports/2021-06-30/documents/{document_id}",
    "reports"
)
download_url = doc.get("url")
compression = doc.get("compressionAlgorithm")  # GZIP if compressed
```

## Vendor Report Types

| Report Type | Description |
|-------------|-------------|
| GET_VENDOR_INVENTORY_REPORT | Inventory levels |
| GET_VENDOR_SALES_REPORT | Sales data |
| GET_VENDOR_TRAFFIC_REPORT | Traffic/conversion |
| GET_VENDOR_FORECASTING_REPORT | Demand forecast |
| GET_VENDOR_REAL_TIME_INVENTORY_REPORT | Real-time inventory |

## Feeds Workflow

```python
# 1. Create feed document
status, doc = client.post(
    "/feeds/2021-06-30/documents",
    "feeds",
    data={"contentType": "text/xml; charset=UTF-8"}
)
feed_document_id = doc.get("feedDocumentId")
upload_url = doc.get("url")

# 2. Upload content to presigned URL
import urllib.request
req = urllib.request.Request(upload_url, data=feed_content, method="PUT")
req.add_header("Content-Type", "text/xml; charset=UTF-8")
urllib.request.urlopen(req)

# 3. Create feed
status, feed = client.post(
    "/feeds/2021-06-30/feeds",
    "feeds",
    data={
        "feedType": "POST_PRODUCT_DATA",
        "marketplaceIds": [auth.get_marketplace_id()],
        "inputFeedDocumentId": feed_document_id
    }
)
feed_id = feed.get("feedId")
```

## Rate Limits

| Operation | Rate |
|-----------|------|
| createReport | 0.0167/sec |
| getReport | 2/sec |
| getReports | 0.0222/sec |
| createFeed | 0.0167/sec |
| getFeed | 2/sec |

## Related Skills

- `spapi-vendor-orders` - Order-related reports
- `spapi-integration-patterns` - Async patterns
