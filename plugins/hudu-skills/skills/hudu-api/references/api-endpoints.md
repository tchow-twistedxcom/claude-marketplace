# Hudu REST API Endpoint Reference

Base URL: `https://<tenant>.huducloud.com/api/v1`
Auth: `x-api-key: <API_KEY>` header on all requests

## Pagination

All list endpoints support `?page=N&page_size=M` (max 100 per page).

## Endpoints

| Resource | Method | Path | Notes |
|---|---|---|---|
| API Info | GET | `/api_info` | Version + tenant name |
| Companies | GET | `/companies` | `?name=`, `?search=`, `?page=`, `?page_size=` |
| Companies | GET | `/companies/{id}` | |
| Companies | POST | `/companies` | Body: `{"company": {...}}` |
| Companies | PUT | `/companies/{id}` | |
| Companies | DELETE | `/companies/{id}` | |
| Companies | PUT | `/companies/{id}/archive` | |
| Companies | PUT | `/companies/{id}/unarchive` | |
| Articles | GET | `/articles` | `?company_id=`, `?name=`, `?search=`, `?draft=` |
| Articles | GET | `/articles/{id}` | |
| Articles | POST | `/articles` | Body: `{"article": {"name","content","company_id"}}` |
| Articles | PUT | `/articles/{id}` | |
| Articles | DELETE | `/articles/{id}` | |
| Articles | PUT | `/articles/{id}/archive` | |
| Assets | GET | `/assets` | `?company_id=`, `?asset_layout_id=`, `?name=`, `?search=`, `?archived=`; no standalone `/assets/{id}` — use `?id=` filter |
| Assets | POST | `/companies/{company_id}/assets` | Body: `{"asset": {"name","asset_layout_id"}}` |
| Assets | GET | `/companies/{company_id}/assets/{id}` | |
| Assets | PUT | `/companies/{company_id}/assets/{id}` | |
| Assets | DELETE | `/companies/{company_id}/assets/{id}` | |
| Assets | PUT | `/companies/{company_id}/assets/{id}/archive` | |
| Asset Layouts | GET | `/asset_layouts` | `?search=` |
| Asset Layouts | GET | `/asset_layouts/{id}` | |
| Asset Layouts | POST | `/asset_layouts` | Body: `{"asset_layout": {...}}` |
| Asset Layouts | PUT | `/asset_layouts/{id}` | |
| Asset Passwords | GET | `/asset_passwords` | `?company_id=`, `?name=`, `?search=` |
| Asset Passwords | GET | `/asset_passwords/{id}` | |
| Asset Passwords | POST | `/asset_passwords` | Body: `{"asset_password": {"name","company_id","password"}}` |
| Asset Passwords | PUT | `/asset_passwords/{id}` | |
| Asset Passwords | DELETE | `/asset_passwords/{id}` | |
| Procedures | GET | `/procedures` | `?company_id=`, `?name=`, `?search=` |
| Procedures | GET | `/procedures/{id}` | |
| Procedures | POST | `/procedures` | Body: `{"procedure": {...}}` |
| Procedures | PUT | `/procedures/{id}` | |
| Procedures | DELETE | `/procedures/{id}` | |
| Websites | GET | `/websites` | `?company_id=`, `?search=`, `?paused=` |
| Websites | GET | `/websites/{id}` | |
| Websites | POST | `/websites` | Body: `{"website": {"name","website_url"}}` |
| Websites | PUT | `/websites/{id}` | |
| Websites | DELETE | `/websites/{id}` | |
| Networks | GET | `/networks` | `?company_id=`, `?search=` |
| Networks | GET | `/networks/{id}` | |
| Users | GET | `/users` | `?search=` |
| Users | GET | `/users/{id}` | |
| Folders | GET | `/folders` | `?company_id=`, `?search=` |
| Folders | GET | `/folders/{id}` | |
| Activity Logs | GET | `/activity_logs` | `?user_id=`, `?resource_type=`, `?resource_id=`, `?start_date=`, `?end_date=` |
