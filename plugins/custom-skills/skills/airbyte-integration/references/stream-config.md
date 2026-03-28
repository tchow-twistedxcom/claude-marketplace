# Airbyte Stream Configuration

Reference for managing streams on the SC and VC connections via the web_backend internal API.

## web_backend API

The `web_backend` API is Airbyte's internal API (not versioned, not in the public docs). It's used by the Airbyte UI and is more powerful than the public API for connection/stream management.

**Base**: `http://100.117.161.21:8100/api/v1/web_backend/`

**Auth**: same Bearer token as public API (`Host: localhost` header required)

### Get full connection config (with catalog)
```bash
curl -s -X POST "http://100.117.161.21:8100/api/v1/web_backend/connections/get" \
  -H "Authorization: Bearer $TOKEN" -H "Host: localhost" \
  -H "Content-Type: application/json" \
  -d '{"connectionId": "<conn_id>", "withRefreshedCatalog": false}'
```

Response includes `syncCatalog.streams[]` — each stream has:
- `stream.name` — stream name
- `config.selected` — bool
- `config.syncMode` — `"full_refresh"` or `"incremental"`
- `config.destinationSyncMode` — `"overwrite"` or `"append"` or `"append_dedup"`
- `config.cursorField` — cursor for incremental

### Update connection streams
```bash
curl -s -X POST "http://100.117.161.21:8100/api/v1/web_backend/connections/update" \
  -H "Authorization: Bearer $TOKEN" -H "Host: localhost" \
  -H "Content-Type: application/json" \
  -d '{
    "connectionId": "<conn_id>",
    "syncCatalog": {"streams": [<modified streams array>]},
    "skipReset": true
  }'
```

`skipReset: true` — avoids triggering a full reset when updating stream selection.

### Python pattern for stream updates

```python
import json, subprocess, tempfile, os

def api_post(url, token, data):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        fname = f.name
    try:
        r = subprocess.run(
            ["curl", "-s", "-X", "POST", url,
             "-H", f"Authorization: Bearer {token}",
             "-H", "Host: localhost", "-H", "Content-Type: application/json",
             "-d", f"@{fname}"],
            capture_output=True, text=True)
        return json.loads(r.stdout) if r.stdout.strip() else {}
    finally:
        os.unlink(fname)

BASE = "http://100.117.161.21:8100"

# Get current connection
conn = api_post(f"{BASE}/api/v1/web_backend/connections/get", token,
                {"connectionId": CONN_ID, "withRefreshedCatalog": False})
streams = conn["syncCatalog"]["streams"]

# Modify streams
for s in streams:
    name = s["stream"]["name"]
    cfg = s.setdefault("config", {})
    if name in INCREMENTAL_STREAMS:
        cfg["selected"] = True
        cfg["syncMode"] = "incremental"
        cfg["destinationSyncMode"] = "append"
    elif name in DISABLED_STREAMS:
        cfg["selected"] = False
    else:
        cfg["selected"] = True
        cfg["syncMode"] = "full_refresh"
        cfg["destinationSyncMode"] = "overwrite"

# Push update
api_post(f"{BASE}/api/v1/web_backend/connections/update", token, {
    "connectionId": CONN_ID,
    "syncCatalog": {"streams": streams},
    "skipReset": True,
})
```

## Seller Central (SC) Streams

Connection: `4dff2ab4-2683-4299-8af0-dc5e938be7d3`

### Incremental Streams (append mode — date-based cursors)
```
GET_SALES_AND_TRAFFIC_REPORT_BY_DATE
GET_SALES_AND_TRAFFIC_REPORT_BY_MONTH
GET_FLAT_FILE_ALL_ORDERS_DATA_BY_ORDER_DATE_GENERAL
GET_FLAT_FILE_ORDERS_DATA_BY_ORDER_DATE
GET_AMAZON_FULFILLED_SHIPMENTS_DATA_GENERAL
GET_FBA_FULFILLMENT_CUSTOMER_SHIPMENT_SALES_DATA
GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE
GET_DATE_RANGE_FINANCIAL_TRANSACTION_DATA
GET_SELLER_FEEDBACK_DATA
GET_BRAND_ANALYTICS_MARKET_BASKET_REPORT
GET_BRAND_ANALYTICS_REPEAT_PURCHASE_REPORT
GET_BRAND_ANALYTICS_SEARCH_TERMS_REPORT
GET_BRAND_ANALYTICS_ALTERNATE_PURCHASE_REPORT
GET_BRAND_ANALYTICS_ITEM_COMPARISON_REPORT
ListFinancialEventGroups
ListFinancialEvents
Orders
```

### Full-Refresh Streams (overwrite mode — snapshots)
```
GET_MERCHANT_LISTINGS_ALL_DATA
GET_MERCHANT_LISTINGS_DATA
GET_FLAT_FILE_OPEN_LISTINGS_DATA
GET_MERCHANT_CANCELLED_LISTINGS_DATA
GET_FBA_INVENTORY_PLANNING_DATA
GET_FBA_MYI_UNSUPPRESSED_INVENTORY_DATA
GET_FBA_FULFILLMENT_INVENTORY_SUMMARY_REPORT
```

### Streams Requiring Brand Registry (may 403)
```
GET_BRAND_ANALYTICS_MARKET_BASKET_REPORT
GET_BRAND_ANALYTICS_REPEAT_PURCHASE_REPORT
GET_BRAND_ANALYTICS_SEARCH_TERMS_REPORT
GET_BRAND_ANALYTICS_ALTERNATE_PURCHASE_REPORT
GET_BRAND_ANALYTICS_ITEM_COMPARISON_REPORT
```

## Vendor Central (VC) Streams

Connection: `bfa37c64-4107-40b0-9be1-7d7108c955da`

### Incremental Streams (append mode — monthly reports)
```
GET_VENDOR_SALES_REPORT
GET_VENDOR_INVENTORY_REPORT     # API max 15 days; use P14D step
GET_VENDOR_TRAFFIC_REPORT
GET_VENDOR_NET_PURE_PRODUCT_MARGIN_REPORT
GET_VENDOR_FORECASTING_REPORT
GET_VENDOR_FORECASTING_RETAIL_REPORT
GET_VENDOR_FORECASTING_FRESH_REPORT
VendorOrders
VendorOrdersStatus
GET_BRAND_ANALYTICS_MARKET_BASKET_REPORT
GET_BRAND_ANALYTICS_REPEAT_PURCHASE_REPORT
GET_BRAND_ANALYTICS_SEARCH_TERMS_REPORT
GET_BRAND_ANALYTICS_ALTERNATE_PURCHASE_REPORT
GET_BRAND_ANALYTICS_ITEM_COMPARISON_REPORT
```

### Full-Refresh Streams (overwrite mode)
```
GET_VENDOR_REAL_TIME_INVENTORY_REPORT
```

### VC Streams That May Fail (403/unavailable — acceptable)
```
GET_VENDOR_FORECASTING_REPORT        # Not available for all vendor accounts
GET_VENDOR_FORECASTING_FRESH_REPORT
VendorDirectFulfillmentShipping      # Only for direct fulfillment vendors
```

> **Vendor streams NOT to use**: Any "Seller" stream (Orders, ListFinancialEvents, etc.) — Vendor accounts always get 403 on Seller-only endpoints.

## Reset a Connection (clear cursor state)

```bash
# Via public API — triggers a full reset sync
curl -s -X POST "http://100.117.161.21:8100/api/public/v1/jobs" \
  -H "Authorization: Bearer $TOKEN" -H "Host: localhost" \
  -H "Content-Type: application/json" \
  -d '{"connectionId": "<conn_id>", "jobType": "reset"}'
```

**IMPORTANT**: Reset clears all cursor state so next sync re-reads from `start_date`. Use when:
- Changing `start_date` to earlier date
- Changing step size in manifest (need re-sync from beginning)
- Streams returning stale/wrong data

## Airbyte Snowflake Destination

Data lands in `AIRBYTE_RAW` database:
- SC streams → `SELLER_DATA` schema
- VC streams → `VENDOR_DATA` schema

Table names match stream names (lowercase with underscores).

### Verify row counts
```sql
SELECT TABLE_NAME, ROW_COUNT, LAST_ALTERED
FROM AIRBYTE_RAW.INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'SELLER_DATA'  -- or 'VENDOR_DATA'
ORDER BY TABLE_NAME;
```

### Signs of a bad sync
- `ROW_COUNT = 0` AND `LAST_ALTERED` near `CREATED` → table schema created, no data written
- `ROW_COUNT > 0` but `LAST_ALTERED` is old → incremental cursor not advancing
- Check `attempts.output` in DB for `streamCount` — should match expected streams

## Stream Error Detection (from orchestrator logs)

```python
def find_errored_streams(logs):
    streams = set()
    for line in logs.split("\n"):
        if "Exception while syncing stream" in line:
            parts = line.split("Exception while syncing stream ")
            if len(parts) > 1:
                stream = parts[1].strip().split()[0]
                streams.add(stream)
    return streams
```

Common errors:
- `403 Forbidden` → no API permission / wrong account type / need Brand Registry
- `400 Bad Request` with date range → step too large for that stream's API limits
- `OOMKilled (exit 137)` → container hit memory limit; increase `JOB_MAIN_CONTAINER_MEMORY_LIMIT` in ConfigMap + restart server
