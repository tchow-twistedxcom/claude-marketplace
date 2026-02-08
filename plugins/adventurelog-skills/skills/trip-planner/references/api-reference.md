# AdventureLog API Reference

Complete field-by-field reference for all trip-planning endpoints. Base URL is the backend (e.g., `http://localhost:8016`).

## Authentication

### Method 1: X-Session-Token Header (Preferred)

Bypasses CSRF entirely. Create a session via Django shell, use the key as a header on every request.

```bash
# Inside the backend container:
docker compose exec server python manage.py shell -c "
from django.test import Client
c = Client()
c.login(username='USERNAME', password='PASSWORD')
print(c.session.session_key)
"
```

```
Header: X-Session-Token: <session-key>
```

**Middleware chain**: `XSessionTokenMiddleware` injects the token as a session cookie → `DisableCSRFForSessionTokenMiddleware` skips CSRF checks → `SessionMiddleware` loads the session → `AuthenticationMiddleware` authenticates the user.

**Important**: Use `Client().login()` to create sessions. `SessionStore().create()` does NOT properly set `_auth_user_hash` and will fail with 400 "User is not authenticated".

### Method 2: Form Login (Fallback)

```
GET /csrf/
Response: {"csrfToken": "abc123..."}
```

```
POST /accounts/login/
Content-Type: application/x-www-form-urlencoded
Body: csrfmiddlewaretoken=<token>&login=<username>&password=<password>
Headers: X-CSRFToken: <token>, Referer: <base-url>
```

**Warning**: Form login may return 500 in dev environments due to missing staticfiles manifest (`allauth_ui/output.css`). If this happens, use Method 1 instead.

**Important**: Use form-encoded POST to `/accounts/login/`, not `/auth/_allauth/browser/v1/auth/login`. The allauth headless endpoint may not be available in dev.

---

## Collections

### `POST /api/collections/`

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | — | Max 200 chars |
| `description` | string | No | null | Free text |
| `start_date` | date | No | null | `YYYY-MM-DD` |
| `end_date` | date | No | null | `YYYY-MM-DD`, must be >= start_date |
| `is_public` | boolean | No | false | Cascades to all linked items |
| `link` | url | No | null | Max 2083 chars |
| `is_archived` | boolean | No | false | Soft archive |

**Response**: Returns full collection object with `id` (UUID).

### Other Collection Endpoints
- `GET /api/collections/` — List user's collections
- `GET /api/collections/{id}/` — Get single collection
- `PATCH /api/collections/{id}/` — Update collection
- `DELETE /api/collections/{id}/` — Delete collection

---

## Categories

### `POST /api/categories/`

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | — | Max 200, auto-lowercased |
| `display_name` | string | Yes | — | Max 200 |
| `icon` | string | No | `"🌍"` | Max 200, typically emoji |

**Constraints**: `(name, user)` must be unique. If a category with the same name exists for the user, reuse it.

**Response**: Returns `id` (UUID), `name`, `display_name`, `icon`.

---

## Locations

### `POST /api/locations/`

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | — | Max 200 |
| `location` | string | No | null | Address text, max 200 |
| `description` | string | No | null | Free text |
| `latitude` | decimal | No | null | 9 digits, 6 decimal places |
| `longitude` | decimal | No | null | 9 digits, 6 decimal places |
| `rating` | float | No | null | Typically 1.0-5.0 |
| `price` | money | No | null | `{"amount": "25.00", "currency": "USD"}` |
| `link` | url | No | null | Max 2083 |
| `tags` | array[string] | No | null | e.g., `["japanese", "day-1"]` |
| `category` | dict | No | auto 'general' | `{"name": "...", "display_name": "...", "icon": "..."}` |
| `collections` | array[uuid] | No | [] | Collection IDs to link to |
| `is_public` | boolean | No | false | — |

**Category format**: Must be a dictionary, NOT a UUID string. The serializer expects the full category dict and will find-or-create.

**Auto-behaviors**:
- If lat/lng provided, background thread reverse-geocodes to populate city/region/country
- If no category provided, auto-creates/assigns 'general' category

**Response**: Returns full location with `id` (UUID), nested `category`, `visits`, `images`.

---

## Visits

### `POST /api/visits/`

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `location` | uuid | Yes | — | Must be accessible by user |
| `start_date` | datetime | No | null | ISO 8601 **with offset**: `"2025-03-15T12:00:00-07:00"` |
| `end_date` | datetime | No | null | Must be >= start_date, **with offset** |
| `timezone` | string | Recommended | null | IANA timezone, e.g., `"America/Vancouver"`. Controls timeline display timezone. |
| `notes` | string | No | null | Visit-specific notes |

**Validation**: start_date must be <= end_date.

**Timezone warning**: Naive datetimes without offset (e.g., `"2025-03-15T12:00:00"`) are stored as UTC by Django. A noon lunch in Seattle would display at 7 PM PDT. Always include the offset (`-07:00` for PDT, `+09:00` for JST, etc.) or use UTC with `Z` suffix.

**Timeline impact**: Visit start/end times directly control positioning on the itinerary timeline view. The `timezone` field determines what timezone the timeline displays in (derived from lodging timezone → transportation end_timezone → browser default).

**Response**: Returns `id` (UUID), `location`, dates, `notes`.

---

## Transportation

### `POST /api/transportations/`

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `type` | string | Yes | — | Choices: `car`, `plane`, `train`, `bus`, `boat`, `bike`, `walking`, `other` |
| `name` | string | Yes | — | Max 200 |
| `description` | string | No | null | Free text |
| `date` | datetime | No | null | Departure time **with offset**: `"2025-03-15T13:00:00-07:00"` |
| `end_date` | datetime | No | null | Arrival time **with offset**, must be >= date |
| `start_timezone` | string | Recommended | null | Departure IANA timezone (e.g., `"America/Chicago"`) |
| `end_timezone` | string | Recommended | null | Arrival IANA timezone. **Used as fallback for trip display timezone.** |
| `flight_number` | string | No | null | Max 100 |
| `from_location` | string | No | null | Origin text, max 200 |
| `to_location` | string | No | null | Destination text, max 200 |
| `origin_latitude` | decimal | No | null | 9,6 |
| `origin_longitude` | decimal | No | null | 9,6 |
| `destination_latitude` | decimal | No | null | 9,6 |
| `destination_longitude` | decimal | No | null | 9,6 |
| `start_code` | string | No | null | Airport/station code, max 100 |
| `end_code` | string | No | null | Airport/station code, max 100 |
| `rating` | float | No | null | — |
| `price` | money | No | null | `{"amount": "...", "currency": "USD"}` |
| `link` | url | No | null | Max 2083 |
| `is_public` | boolean | No | false | — |
| `collection` | uuid | No | null | Parent collection |

**Computed properties** (read-only):
- `distance` — Calculated from origin/destination coordinates
- `travel_duration_minutes` — Calculated from date/end_date

---

## Lodging

### `POST /api/lodging/`

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | — | Max 200 |
| `type` | string | No | `"other"` | Choices: `hotel`, `hostel`, `resort`, `bnb`, `campground`, `cabin`, `apartment`, `house`, `villa`, `motel`, `other` |
| `description` | string | No | null | Free text |
| `check_in` | datetime | No | null | ISO 8601 **with offset**: `"2025-03-15T15:00:00-07:00"` |
| `check_out` | datetime | No | null | Must be >= check_in, **with offset** |
| `timezone` | string | Recommended | null | IANA timezone. **Primary source for trip display timezone** in the timeline view. |
| `reservation_number` | string | No | null | Max 100 |
| `latitude` | decimal | No | null | 9,6 |
| `longitude` | decimal | No | null | 9,6 |
| `location` | string | No | null | Address, max 200 |
| `rating` | float | No | null | — |
| `price` | money | No | null | `{"amount": "...", "currency": "USD"}` |
| `link` | url | No | null | Max 2083 |
| `is_public` | boolean | No | false | — |
| `collection` | uuid | No | null | Parent collection |

---

## Notes

### `POST /api/notes/`

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | — | Max 200 |
| `content` | string | No | null | Markdown supported |
| `date` | date | No | null | `YYYY-MM-DD` |
| `links` | array[url] | No | null | Array of URL strings |
| `is_public` | boolean | No | false | — |
| `collection` | uuid | No | null | Parent collection |

---

## Checklists

### `POST /api/checklists/`

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | — | Max 200 |
| `items` | array | Yes | — | Array of ChecklistItem objects (can be empty `[]`) |
| `date` | date | No | null | `YYYY-MM-DD` |
| `is_public` | boolean | No | false | — |
| `collection` | uuid | No | null | Parent collection |

**Important**: The `items` field is required even if empty. Pass `[]` for an empty checklist, or include items inline:
```json
{"name": "My Checklist", "items": [{"name": "Item 1", "is_checked": false}], "collection": "<uuid>"}
```

### ChecklistItem (nested in items array)

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `name` | string | Yes | Max 200 |
| `is_checked` | boolean | No | false |

---

## Itinerary Days

### `POST /api/itinerary-days/`

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `collection` | uuid | Yes | — | Must own or be shared |
| `date` | date | Yes | — | `YYYY-MM-DD`, unique per collection |
| `name` | string | No | null | Max 200, day title |
| `description` | string | No | null | Day theme/notes |

**Constraint**: `(collection, date)` must be unique.

---

## Itinerary Items

### `POST /api/itineraries/`

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `collection` | uuid | Yes | — | — |
| `content_type` | string | Yes | — | `"location"`, `"transportation"`, `"lodging"`, `"note"`, `"checklist"` |
| `object_id` | uuid | Yes | — | UUID of referenced entity |
| `date` | date | Conditional | null | Required if `is_global=false` |
| `is_global` | boolean | No | false | XOR with date: either global or dated |
| `order` | integer | No | auto | Display order within day |

**XOR rule**: Either `is_global=true` (no date) OR date is set (not both, not neither unless global).

**Critical**: For locations, use `content_type: "location"` with the **Location UUID**. Do NOT use `content_type: "visit"` — the frontend only resolves `location`, `transportation`, `lodging`, `note`, and `checklist` types. Using `"visit"` will cause "Item not found" errors in the UI and locations appearing as unscheduled.

### Reorder Items
```
POST /api/itineraries/reorder/
Body: {"items": [{"id": "<uuid>", "date": "YYYY-MM-DD", "order": 0}, ...]}
```

### Auto-Generate Itinerary
```
POST /api/itineraries/auto-generate/
Body: {"collection_id": "<uuid>"}
```
Only works if collection has 0 existing itinerary items. Scans all dated entities and creates items.

---

## Common Patterns

### Money Fields
```json
{"amount": "25.00", "currency": "USD"}
```
Supported wherever `price` field exists (Location, Transportation, Lodging).

### CSRF Handling

**With X-Session-Token (preferred)**: No CSRF handling needed. The middleware disables CSRF enforcement automatically.

**With form login**: Refresh CSRF before every write operation:
```python
csrf = s.get(f"{BASE}/csrf/").json()["csrfToken"]
s.headers.update({"X-CSRFToken": csrf, "Content-Type": "application/json"})
```

### Error Handling
- `400` — Validation error, check response body for field-level errors
- `400` `"User is not authenticated"` — Session invalid or improperly created (use `Client().login()`)
- `401` — Not authenticated, re-login
- `403` — CSRF failure (switch to X-Session-Token) or permission denied (wrong user)
- `404` — Object not found or not accessible to user (API filters by authenticated user)
- `409` — Conflict (duplicate unique constraint)
- `500` on `/accounts/login/` — Staticfiles manifest error in dev (use X-Session-Token method instead)
