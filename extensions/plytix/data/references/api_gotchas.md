# Plytix API Gotchas & Common Patterns

Common issues and workarounds when using the Plytix PIM MCP tools.

---

## API Limits Summary ⚠️ CRITICAL

| Limit | Value | Description |
|-------|-------|-------------|
| **Rate Limit** | Plan-based | Requests per 10s / per hour |
| **Search columns** | **50 max** | Attributes + properties in search |
| **Search attributes** | **20 max** | Custom attributes per search result |
| **Page size** | **100 max** | Items per page (default: 25) |
| **Token lifetime** | **15 minutes** | Auto-refreshed by MCP server |
| **Order + large results** | **10,000** | Returns 428 if ordering with >10K results |

---

## 0. Product Family Assignment ⚠️ CRITICAL

Family must be assigned via `plytix_assign_product_family` — NOT via create/update.
Both `plytix_create_product` and `plytix_update_product` silently ignore `product_family`.

**Correct flow:**
```
1. plytix_create_product → get product_id
2. plytix_assign_product_family(product_id, family_id)
```

Use the family's **ID** (not name). The response field is `product_family_id`.

---

## 1. Use `like` NOT `contains` for Text Search

`contains` is not a valid operator. Use `like` for substring matching.

```json
{"field": "sku", "operator": "like", "value": "AMZN"}
```

`like` is case-insensitive and matches substrings without wildcards.

---

## 2. Custom Attributes NOT Searchable as Filters

`plytix_search_products` can only filter by built-in fields (sku, label, gtin, status).
Custom attributes like `amazon_parent_asin` CANNOT be used as search filters.

**Solution:** Use `plytix_find_products_by_attribute` which fetches and filters locally.

---

## 3. Thumbnail Format

Pass `thumbnail` as an asset_id string — the server auto-wraps it to `{"id": asset_id}`.

---

## 4. Asset Linking Requires Attribute Label

`plytix_add_product_assets` links to a specific media gallery attribute.
Default is `assets`. For a custom gallery: pass `attribute_label="amazon_images"`.

The attribute must be of type `MediaGalleryAttribute`.

---

## 5. Date Attribute Format

DateAttribute values must use `YYYY-MM-DD` (not ISO timestamps like `2024-01-15T00:00:00Z`).

---

## 6. Dropdown Attribute Options

Options must be simple strings: `["US", "CA", "MX"]`
NOT objects: `[{"value": "US", "label": "United States"}]`

---

## 7. Asset Upload — Duplicates

`plytix_upload_asset_url` returns 409 if the URL already exists.
With `return_existing=True` (default), it returns the existing asset ID instead of an error.

---

## 8. Relationship Direction

`plytix_add_product_relationships` links FROM source TO targets.
For bidirectional visibility, call it from both sides.

---

## 9. search_products Does NOT Return product_family_id

Even if a family is assigned, `plytix_search_products` returns `product_family_id: null`.
Use `plytix_get_product` to get the actual value.

---

## 10. 428 Error — Large Result Sets with Ordering

If you order results and the filter matches >10,000 products, you get 428.
Fix: remove `sort_by` or add more restrictive filters.

---

## 11. Attribute Groups API — Unavailable

`/attributes/product/groups` always returns 500 Internal Server Error.
This is a confirmed upstream Plytix bug. Individual attribute tools work fine.

---

## 12. Filter Endpoint Naming

- `/filters/asset` — singular ✅
- `/filters/product` — singular ✅
- `/filters/relationships` — plural ✅

Use `plytix_get_product_filters`, `plytix_get_asset_filters`, `plytix_get_relationship_filters`.

---

## Search Column Prefixes

When passing `attributes` to `plytix_search_products`:
- Custom attributes: prefix with `attributes.` (e.g., `"attributes.amazon_asin"`)
- Relationship columns: prefix with `relationships.` (e.g., `"relationships.related_products"`)

---

## Common Pattern: Full Product Sync

```
1. plytix_search_products(filters=[...], attributes=["sku"])  → get IDs
2. plytix_get_product(id)  → full attributes, assets, categories, family
```
