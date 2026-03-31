# Plytix MCP — API Coverage Map

**MCP Tools**: 63 total (30 read-only, 33 write)

---

## Products (13 tools)

| MCP Tool | Method | Endpoint |
|----------|--------|----------|
| `plytix_search_products` | POST | /products/search |
| `plytix_get_product` | GET | /products/{id} |
| `plytix_find_products_by_attribute` | client-side | /products/search (iterates pages) |
| `plytix_create_product` | POST | /products |
| `plytix_update_product` | PATCH | /products/{id} |
| `plytix_delete_product` | DELETE | /products/{id} |
| `plytix_bulk_update_products` | POST | /products/bulk |
| `plytix_assign_product_family` | POST | /products/{id}/family |
| `plytix_add_product_assets` | POST | /products/{id}/assets |
| `plytix_remove_product_assets` | DELETE | /products/{id}/assets |
| `plytix_add_product_categories` | POST | /products/{id}/categories |
| `plytix_remove_product_categories` | DELETE | /products/{id}/categories |
| `plytix_add_product_relationships` | POST | /products/{id}/relationships/{rel_id} |
| `plytix_remove_product_relationships` | PATCH | /products/{id}/relationships/{rel_id}/unlink |

> **Note**: `plytix_get_product` returns assets, categories, relationships, and product_family_id.
> Use it instead of separate sub-tools.

---

## Assets (6 tools)

| MCP Tool | Method | Endpoint |
|----------|--------|----------|
| `plytix_search_assets` | POST | /assets/search |
| `plytix_get_asset` | GET | /assets/{id} |
| `plytix_get_asset_download_url` | GET | /assets/{id}/download |
| `plytix_upload_asset_url` | POST | /assets |
| `plytix_update_asset` | PATCH | /assets/{id} |
| `plytix_delete_asset` | DELETE | /assets/{id} |

---

## Categories — Product (8 tools)

| MCP Tool | Method | Endpoint |
|----------|--------|----------|
| `plytix_list_categories` | POST | /categories/product/search |
| `plytix_get_category` | GET | /categories/{id} |
| `plytix_get_category_tree` | client-side | /categories/product/search (builds tree) |
| `plytix_list_category_products` | GET | /categories/{id}/products |
| `plytix_create_category` | POST | /categories |
| `plytix_update_category` | PATCH | /categories/{id} |
| `plytix_delete_category` | DELETE | /categories/{id} |
| `plytix_add_product_subcategory` | POST | /categories/product/{parent_id} |

---

## Categories — File/Asset (5 tools)

| MCP Tool | Method | Endpoint |
|----------|--------|----------|
| `plytix_search_file_categories` | POST | /categories/file/search |
| `plytix_create_file_category` | POST | /categories/file |
| `plytix_add_file_subcategory` | POST | /categories/file/{parent_id} |
| `plytix_update_file_category` | PATCH | /categories/file/{id} |
| `plytix_delete_file_category` | DELETE | /categories/file/{id} |

---

## Variants (7 tools)

| MCP Tool | Method | Endpoint |
|----------|--------|----------|
| `plytix_list_variants` | GET | /products/{id}/variants |
| `plytix_get_variant` | GET | /variants/{id} |
| `plytix_create_variant` | POST | /products/{id}/variants |
| `plytix_bulk_create_variants` | POST | /products/{id}/variants/bulk |
| `plytix_update_variant` | PATCH | /variants/{id} |
| `plytix_delete_variant` | DELETE | /variants/{id} |
| `plytix_resync_variant_attributes` | POST | /products/{id}/variants/resync |

---

## Attributes (5 tools)

| MCP Tool | Method | Endpoint |
|----------|--------|----------|
| `plytix_list_attributes` | POST | /attributes/product/search |
| `plytix_get_attribute` | GET | /attributes/product/{id} |
| `plytix_create_attribute` | POST | /attributes/product |
| `plytix_update_attribute` | PATCH | /attributes/product/{id} |
| `plytix_delete_attribute` | DELETE | /attributes/product/{id} |

> **Note**: Attribute groups (/attributes/product/groups) always return 500 — upstream Plytix bug.

---

## Relationships (5 tools)

| MCP Tool | Method | Endpoint |
|----------|--------|----------|
| `plytix_search_relationships` | POST | /relationships/search |
| `plytix_get_relationship` | GET | /relationships/{id} |
| `plytix_create_relationship` | POST | /relationships |
| `plytix_update_relationship` | PATCH | /relationships/{id} |
| `plytix_delete_relationship` | DELETE | /relationships/{id} |

---

## Product Families (8 tools)

| MCP Tool | Method | Endpoint |
|----------|--------|----------|
| `plytix_search_product_families` | POST | /product_families/search |
| `plytix_get_product_family` | GET | /product_families/{id} |
| `plytix_get_family_attributes` | GET | /product_families/{id}/all_attributes |
| `plytix_create_product_family` | POST | /product_families |
| `plytix_update_product_family` | PATCH | /product_families/{id} |
| `plytix_delete_product_family` | DELETE | /product_families/{id} |
| `plytix_link_family_attributes` | POST | /product_families/{id}/attributes/link |
| `plytix_unlink_family_attributes` | POST | /product_families/{id}/attributes/unlink |

---

## Accounts (2 tools)

| MCP Tool | Method | Endpoint |
|----------|--------|----------|
| `plytix_list_account_members` | POST | /accounts/memberships/search |
| `plytix_list_api_credentials` | POST | /accounts/api-credentials/search |

---

## Available Filters (3 tools)

| MCP Tool | Method | Endpoint |
|----------|--------|----------|
| `plytix_get_product_filters` | GET | /filters/product |
| `plytix_get_asset_filters` | GET | /filters/asset |
| `plytix_get_relationship_filters` | GET | /filters/relationships |

---

## Read-Only Mode

Set `PLYTIX_READ_ONLY=true` to register ~30 read tools only (no create/update/delete).
