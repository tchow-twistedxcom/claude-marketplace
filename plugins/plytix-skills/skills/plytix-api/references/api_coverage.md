# Plytix API Coverage Audit

**Last Updated**: 2025-12-25
**Official API Docs**: https://apidocs.plytix.com

## Coverage Summary

| Resource | Endpoints | Covered | Missing | Coverage |
|----------|-----------|---------|---------|----------|
| Authentication | 1 | 1 | 0 | 100% |
| Products | 15 | 15 | 0 | 100% |
| Assets | 4 | 4 | 0 | 100% |
| Categories (Product) | 5 | 5 | 0 | 100% |
| Categories (Asset/File) | 5 | 5 | 0 | 100% |
| Variants | 6 | 6 | 0 | 100% |
| Attributes | 4 | 4 | 0 | 100% |
| Attribute Groups | 5 | 5 | 0 | 100% |
| Relationships | 5 | 5 | 0 | 100% |
| Product Families | 9 | 9 | 0 | 100% |
| Accounts | 2 | 2 | 0 | 100% |
| Available Filters | 3 | 3 | 0 | 100% |

**Overall: 100% coverage of documented endpoints**

---

## Detailed Endpoint Comparison

### Authentication ✅ 100%
| Endpoint | Method | Status | Implementation |
|----------|--------|--------|----------------|
| /auth/api/get-token | POST | ✅ | `auth.py` |

### Products ✅ 100%
| Endpoint | Method | Status | Implementation |
|----------|--------|--------|----------------|
| /products | POST | ✅ | `create_product()` |
| /products/{id} | GET | ✅ | `get_product()` |
| /products/{id} | PATCH | ✅ | `update_product()` |
| /products/{id} | DELETE | ✅ | `delete_product()` |
| /products/search | POST | ✅ | `search_products()`, `list_products()` |
| /products/bulk | POST | ✅ | `bulk_update_products()` |
| /products/{id}/assets | GET | ✅ | `get_product_assets()` |
| /products/{id}/assets | POST | ✅ | `add_product_assets()` |
| /products/{id}/assets | DELETE | ✅ | `remove_product_assets()` |
| /products/{id}/categories | POST | ✅ | `add_product_categories()` |
| /products/{id}/categories | DELETE | ✅ | `remove_product_categories()` |
| /products/{id}/categories | GET | ✅ | `get_product_category_list()` |
| /products/{id}/relationships/{id} | POST | ✅ | `add_product_relationships()` |
| /products/{id}/relationships/{id}/unlink | PATCH | ✅ | `remove_product_relationships()` |
| /products/{id}/family | POST | ✅ | `assign_product_family()` |
| /products/{id}/variants/resync | POST | ✅ | `resync_variant_attributes()` |

### Assets ✅ 100%
| Endpoint | Method | Status | Implementation |
|----------|--------|--------|----------------|
| /assets | POST | ✅ | `upload_asset()`, `upload_asset_url()` |
| /assets/{id} | GET | ✅ | `get_asset()` |
| /assets/{id} | DELETE | ✅ | `delete_asset()` |
| /assets/search | POST | ✅ | `search_assets()`, `list_assets()` |

### Categories (Product) ✅ 100%
| Endpoint | Method | Status | Implementation |
|----------|--------|--------|----------------|
| /categories/product | POST | ✅ | `create_category()` |
| /categories/product/{id} | PATCH | ✅ | `update_category()` |
| /categories/product/{id} | DELETE | ✅ | `delete_category()` |
| /categories/product/search | POST | ✅ | `list_categories()` |
| /categories/product/{id} | POST | ✅ | `add_product_subcategory()` |

### Categories (Asset/File) ✅ 100%
| Endpoint | Method | Status | Implementation |
|----------|--------|--------|----------------|
| /categories/file | POST | ✅ | `create_file_category()` |
| /categories/file/{id} | POST | ✅ | `add_file_subcategory()` |
| /categories/file/{id} | PATCH | ✅ | `update_file_category()` |
| /categories/file/{id} | DELETE | ✅ | `delete_file_category()` |
| /categories/file/search | POST | ✅ | `search_file_categories()`, `list_file_categories()` |

### Variants ✅ 100%
| Endpoint | Method | Status | Implementation |
|----------|--------|--------|----------------|
| /products/{id}/variants | GET | ✅ | `list_variants()` |
| /products/{id}/variants | POST | ✅ | `create_variant()` |
| /products/{id}/variants/bulk | POST | ✅ | `bulk_create_variants()` |
| /products/{id}/variants/resync | POST | ✅ | `resync_variant_attributes()` |
| /variants/{id} | GET | ✅ | `get_variant()` |
| /variants/{id} | PATCH | ✅ | `update_variant()` |
| /variants/{id} | DELETE | ✅ | `delete_variant()` |

### Attributes ✅ 100%
| Endpoint | Method | Status | Implementation |
|----------|--------|--------|----------------|
| /attributes/product | POST | ✅ | `create_attribute()` |
| /attributes/product/{id} | GET | ✅ | `get_attribute()` |
| /attributes/product/{id} | PATCH | ✅ | `update_attribute()` |
| /attributes/product/{id} | DELETE | ✅ | `delete_attribute()` |
| /attributes/product/search | POST | ✅ | `list_attributes()` |

### Attribute Groups ⚠️ 100% (API Unstable)
| Endpoint | Method | Status | Implementation |
|----------|--------|--------|----------------|
| /attributes/product/groups | POST | ⚠️ | `create_attribute_group()` |
| /attributes/product/groups/{id} | GET | ⚠️ | `get_attribute_group()` |
| /attributes/product/groups/{id} | PATCH | ⚠️ | `update_attribute_group()` |
| /attributes/product/groups/{id} | DELETE | ⚠️ | `delete_attribute_group()` |
| /attributes/product/groups/search | POST | ⚠️ | `list_attribute_groups()`, `search_attribute_groups()` |

> **Note**: These endpoints are implemented but the Plytix API returns 500 errors. See api_gotchas.md #11.

### Relationships ✅ 100%
| Endpoint | Method | Status | Implementation |
|----------|--------|--------|----------------|
| /relationships | POST | ✅ | `create_relationship()` |
| /relationships/{id} | GET | ✅ | `get_relationship()` |
| /relationships/{id} | PATCH | ✅ | `update_relationship()` |
| /relationships/{id} | DELETE | ✅ | `delete_relationship()` |
| /relationships/search | POST | ✅ | `search_relationships()`, `list_relationships()` |

### Product Families ✅ 100%
| Endpoint | Method | Status | Implementation |
|----------|--------|--------|----------------|
| /product_families | POST | ✅ | `create_product_family()` |
| /product_families/{id} | GET | ✅ | `get_product_family()` |
| /product_families/{id} | PATCH | ✅ | `update_product_family()` |
| /product_families/{id} | DELETE | ✅ | `delete_product_family()` |
| /product_families/search | POST | ✅ | `search_product_families()`, `list_product_families()` |
| /product_families/{id}/attributes/link | POST | ✅ | `link_family_attributes()` |
| /product_families/{id}/attributes/unlink | POST | ✅ | `unlink_family_attributes()` |
| /product_families/{id}/attributes | GET | ✅ | `get_family_attributes()` |
| /product_families/{id}/all_attributes | GET | ✅ | `get_family_all_attributes()` |

### Accounts ✅ 100%
| Endpoint | Method | Status | Implementation |
|----------|--------|--------|----------------|
| /accounts/memberships/search | POST | ✅ | `search_account_memberships()` |
| /accounts/api-credentials/search | POST | ✅ | `search_api_credentials()` |

### 🆕 Products V2 BETA ⚠️ (Experimental)
| Endpoint | Method | Status | Implementation |
|----------|--------|--------|----------------|
| /api/v2/products/{id}/assets | GET | ⚠️ | Not yet implemented |
| /api/v2/products/{id}/assets/{id} | DELETE | ⚠️ | Not yet implemented |

> **Note**: V2 API is in open beta. These endpoints provide improved asset handling but may change before GA release. The V1 equivalents continue to work.

### Available Filters ✅ 100%
| Endpoint | Method | Status | Implementation |
|----------|--------|--------|----------------|
| /filters/asset | GET | ✅ | `get_asset_filters()` |
| /filters/products | GET | ✅ | `get_product_filters()` |
| /filters/relationships | GET | ✅ | `get_relationship_filters()` |

---

## CLI Commands Reference

### New CLI Domains

**Product Families** (`families`)
```bash
python plytix_api.py families list [--limit N] [--page N]
python plytix_api.py families get <id>
python plytix_api.py families create --data '<json>'
python plytix_api.py families update <id> --data '<json>'
python plytix_api.py families delete <id>
python plytix_api.py families search [--filters '<json>']
python plytix_api.py families link-attributes <id> --attribute-ids "id1,id2"
python plytix_api.py families unlink-attributes <id> --attribute-ids "id1,id2"
python plytix_api.py families get-attributes <id>
python plytix_api.py families get-all-attributes <id>
```

**Relationships** (`relationships`)
```bash
python plytix_api.py relationships list [--limit N] [--page N]
python plytix_api.py relationships get <id>
python plytix_api.py relationships create --data '<json>'
python plytix_api.py relationships update <id> --data '<json>'
python plytix_api.py relationships delete <id>
python plytix_api.py relationships search [--filters '<json>']
```

**File Categories** (`file-categories`)
```bash
python plytix_api.py file-categories list [--limit N] [--page N]
python plytix_api.py file-categories create --data '<json>'
python plytix_api.py file-categories add-subcategory <parent_id> --data '<json>'
python plytix_api.py file-categories update <id> --data '<json>'
python plytix_api.py file-categories delete <id>
python plytix_api.py file-categories search [--filters '<json>']
```

**Accounts** (`accounts`)
```bash
python plytix_api.py accounts list-members [--filters '<json>'] [--limit N] [--page N]
python plytix_api.py accounts list-credentials [--filters '<json>'] [--limit N] [--page N]
```

**Available Filters** (`filters`)
```bash
python plytix_api.py filters products
python plytix_api.py filters assets
python plytix_api.py filters relationships
```

### Updated Attribute Groups Commands
```bash
python plytix_api.py attributes list-groups [--limit N] [--page N]
python plytix_api.py attributes get-group <id>
python plytix_api.py attributes create-group --data '<json>'
python plytix_api.py attributes update-group <id> --data '<json>'
python plytix_api.py attributes delete-group <id>
```
