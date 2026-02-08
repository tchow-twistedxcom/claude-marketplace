---
name: AdventureLog Trip Planner
description: "This skill should be used when the user asks to \"plan a trip\", \"create a vacation itinerary\", \"build a travel plan\", \"set up a trip in adventurelog\", \"create an adventure\", \"plan my vacation\", \"organize a journey\", or mentions \"adventurelog\" in the context of trip creation. Provides complete API workflow for creating rich, fully-detailed trips in AdventureLog with all fields populated."
version: 1.0.0
---

# AdventureLog Trip Planner

Create rich, fully-detailed trips in AdventureLog via its REST API. Every entity should be populated with maximum detail — descriptions as informative paragraphs, GPS coordinates for every location, ratings, price estimates, website links, and meaningful tags.

## When to Use

- User wants to plan a trip, vacation, or journey and have it created in AdventureLog
- User wants to build an itinerary with day-by-day scheduling
- User mentions AdventureLog in context of trip/travel planning
- User wants to populate an existing AdventureLog collection with locations, lodging, transport

## Prerequisites

AdventureLog must be running (check with `docker ps | grep adventurelog`). Determine the backend URL from the environment (typically `http://localhost:8016` for dev, or check `.env` for `BACKEND_PORT`). **Ask the user for their credentials** — never reset or change passwords without explicit permission.

## Authentication Flow

AdventureLog uses Django session auth. There are two methods — **prefer the X-Session-Token approach** as it's more reliable and bypasses CSRF.

### Method 1: X-Session-Token Header (Preferred)

The `X-Session-Token` header bypasses CSRF checks entirely via `DisableCSRFForSessionTokenMiddleware`. Create a session via Django shell, then use the session key as a header.

```python
# Step 1: Create a session key via Django management shell
# Run inside the backend container:
#   python manage.py shell -c "
#   from django.test import Client
#   c = Client()
#   c.login(username='USERNAME', password='PASSWORD')
#   print(c.session.session_key)
#   "

import requests
BASE = "http://localhost:8016"
SESSION_KEY = "<session-key-from-above>"

s = requests.Session()
s.headers.update({
    "X-Session-Token": SESSION_KEY,
    "Content-Type": "application/json",
})

# Verify auth works
r = s.get(f"{BASE}/api/collections/")
assert r.status_code == 200, f"Auth failed: {r.status_code}"
```

**No CSRF refresh needed** — the `X-Session-Token` header disables CSRF enforcement for all requests.

**Important**: Use `Client().login()` to create sessions, NOT `SessionStore().create()` — the latter doesn't properly set authentication hashes and will return 400 "User is not authenticated".

### Method 2: Form Login (Fallback)

Use this when Django shell access is unavailable. **Warning**: May fail in dev environments with staticfiles errors (e.g., missing `allauth_ui/output.css` manifest entry).

```python
import requests
BASE = "http://localhost:8016"
s = requests.Session()

csrf = s.get(f"{BASE}/csrf/").json()["csrfToken"]
s.headers.update({"X-CSRFToken": csrf, "Referer": BASE})
s.post(f"{BASE}/accounts/login/",
    data={"csrfmiddlewaretoken": csrf, "login": USERNAME, "password": PASSWORD},
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    allow_redirects=False)

# With form login, CSRF must be refreshed before every write operation:
def refresh_csrf():
    csrf = s.get(f"{BASE}/csrf/").json()["csrfToken"]
    s.headers.update({"X-CSRFToken": csrf, "Content-Type": "application/json"})
```

### Authentication Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 400 "User is not authenticated" | Session not properly created | Use `Client().login()`, not `SessionStore().create()` |
| 403 on writes with cookie auth | CSRF enforcement | Switch to `X-Session-Token` header |
| 500 on `/accounts/login/` | Missing staticfiles manifest | Use X-Session-Token method instead, or run `collectstatic` |
| 403 with valid session cookie | `SessionAuthentication` requires CSRF | Use `X-Session-Token` header which bypasses CSRF |

## Timezone Handling (Critical)

Datetimes in AdventureLog are stored in Django's DateTimeField. **Naive datetimes (without timezone offset) are stored as UTC.** This means `"2025-04-10T18:00:00"` is interpreted as 6 PM UTC — NOT 6 PM local time. This causes items to display at the wrong time in the frontend.

### Rules

1. **Always include a timezone offset** in all datetime values:
   - Tokyo 6 PM: `"2025-04-10T18:00:00+09:00"` (correct)
   - Seattle 12 PM: `"2026-03-14T12:00:00-07:00"` (correct, PDT)
   - Or convert to UTC: `"2025-04-10T09:00:00Z"` (also correct — 6 PM JST)
   - **Never**: `"2025-04-10T18:00:00"` (naive — stored as UTC, displays wrong)

2. **Always set the `timezone` field** on Visits and Lodging:
   - This tells the frontend what timezone to display times in
   - Example: `"timezone": "Asia/Tokyo"`, `"timezone": "America/Los_Angeles"`
   - The frontend timeline view derives the trip's display timezone from lodging/transportation timezone data

3. **Always set `start_timezone` and `end_timezone`** on Transportation:
   - Departure and arrival may be in different timezones (e.g., cross-country flight)
   - Example: `"start_timezone": "America/Chicago"`, `"end_timezone": "America/Los_Angeles"`

### Why This Matters

The itinerary timeline view positions items vertically by their actual start/end times. If times are stored wrong, items appear at absurd hours (e.g., a noon lunch showing at 5 AM). The timeline also displays all times in the trip's **destination timezone** (derived from lodging → transportation end_timezone → browser default fallback), so the `timezone` fields must be set correctly.

## Trip Creation Workflow

Follow this exact order to satisfy foreign key and ownership constraints:

### Step 1: Create Collection (Trip Container)

```
POST /api/collections/
```

| Field | Required | Detail |
|-------|----------|--------|
| `name` | Yes | Trip name (max 200 chars) |
| `description` | Recommended | Rich overview of the trip — destinations, purpose, highlights |
| `start_date` | Recommended | Format: `YYYY-MM-DD` |
| `end_date` | Recommended | Format: `YYYY-MM-DD` |
| `link` | Optional | External booking/planning URL |
| `is_public` | No | Default `false` |

Save the returned `id` (UUID) — all other entities reference this collection.

### Step 2: Create Categories

Categories are per-user. Create before locations. Common categories for trips:

```
POST /api/categories/
```

| Field | Required | Example |
|-------|----------|---------|
| `name` | Yes | `"restaurant"` (auto-lowercased) |
| `display_name` | Yes | `"Restaurant"` |
| `icon` | Recommended | `"🍽️"` |

Suggested categories: restaurant/Restaurant/🍽️, attraction/Attraction/🎢, museum/Museum/🏛️, park/Park/🌲, shopping/Shopping/🛍️, nightlife/Nightlife/🌙, beach/Beach/🏖️, hotel/Hotel/🏨, cafe/Cafe/☕

**Validation**: `(name, user)` must be unique. If category already exists, it can be reused.

### Step 3: Create Locations (Places of Interest)

```
POST /api/locations/
```

**IMPORTANT — Populate ALL fields for richness:**

| Field | Required | Richness Guideline |
|-------|----------|--------------------|
| `name` | Yes | Official business/place name |
| `location` | Yes | Full street address with city, state/province, country |
| `description` | Yes | **2-4 sentence paragraph**: What it is, why visit, signature items/experiences, practical tips (hours, reservations, wait times), approximate cost per person |
| `latitude` | Yes | Decimal degrees (e.g., `49.2827`). Research accurate coordinates. |
| `longitude` | Yes | Decimal degrees (e.g., `-123.1207`). Research accurate coordinates. |
| `rating` | Recommended | 1.0-5.0 based on reputation/reviews |
| `link` | Recommended | Official website URL |
| `tags` | Recommended | Array of strings: day label, cuisine type, category, neighborhood (e.g., `["japanese", "sushi", "day-1-dinner", "downtown"]`) |
| `category` | Yes | Dict: `{"name": "restaurant", "display_name": "Restaurant", "icon": "🍽️"}` |
| `collections` | Yes | Array of collection UUIDs: `["<collection-id>"]` |
| `is_public` | No | Default `false` |

**Category format**: Must be a dict (not UUID string). Use the same dict format used during creation.

### Step 4: Create Visits (Date/Time Records for Locations)

Every location that appears on a specific day needs a Visit. Visits connect locations to the itinerary timeline.

```
POST /api/visits/
```

| Field | Required | Detail |
|-------|----------|--------|
| `location` | Yes | Location UUID |
| `start_date` | Yes | ISO 8601 with offset: `"2025-03-15T12:00:00-07:00"` (see Timezone Handling) |
| `end_date` | Recommended | ISO 8601 with offset: `"2025-03-15T14:00:00-07:00"` |
| `timezone` | **Yes** | IANA timezone, e.g., `"America/Los_Angeles"`. **Required for correct timeline display.** |
| `notes` | Optional | Visit-specific notes (what to order, tips) |

**Timezone warning**: Naive datetimes without offset (e.g., `"2025-03-15T12:00:00"`) are stored as UTC and will display at the wrong time. Always include the offset. See the **Timezone Handling** section above.

Save returned `id` — needed for itinerary items.

### Step 5: Create Transportation

```
POST /api/transportations/
```

| Field | Required | Richness Guideline |
|-------|----------|--------------------|
| `type` | Yes | One of: `car`, `plane`, `train`, `bus`, `boat`, `bike`, `walking`, `other` |
| `name` | Yes | Descriptive name (e.g., "Flight SEA → YVR", "Drive to Richmond") |
| `description` | Recommended | Route details, tips, traffic notes, border crossing info |
| `date` | Recommended | Departure datetime with offset: `"2025-03-15T13:00:00-07:00"` |
| `end_date` | Recommended | Arrival datetime with offset: `"2025-03-15T16:30:00-07:00"` |
| `start_timezone` | **Yes** | Departure timezone, e.g., `"America/Los_Angeles"` |
| `end_timezone` | **Yes** | Arrival timezone, e.g., `"America/Vancouver"`. **Used to derive trip display timezone.** |
| `flight_number` | If flight | e.g., `"AC8832"` |
| `from_location` | Yes | Origin address/name |
| `to_location` | Yes | Destination address/name |
| `origin_latitude` / `origin_longitude` | Recommended | Origin GPS |
| `destination_latitude` / `destination_longitude` | Recommended | Destination GPS |
| `start_code` / `end_code` | If applicable | Airport/station codes (e.g., `"SEA"`, `"YVR"`) |
| `link` | Optional | Booking confirmation URL |
| `collection` | Yes | Collection UUID |

### Step 6: Create Lodging

```
POST /api/lodging/
```

| Field | Required | Richness Guideline |
|-------|----------|--------------------|
| `name` | Yes | Hotel/property name |
| `type` | Recommended | One of: `hotel`, `hostel`, `resort`, `bnb`, `campground`, `cabin`, `apartment`, `house`, `villa`, `motel`, `other` |
| `description` | Recommended | Property highlights, amenities, location benefits, room tips |
| `check_in` | Yes | ISO 8601 with offset: `"2025-03-15T15:00:00-07:00"` (see Timezone Handling) |
| `check_out` | Yes | ISO 8601 with offset: `"2025-03-18T11:00:00-07:00"` |
| `timezone` | **Yes** | IANA timezone, e.g., `"America/Vancouver"`. **Primary source for trip display timezone.** |
| `reservation_number` | If known | Booking confirmation number |
| `latitude` / `longitude` | Yes | Hotel GPS coordinates |
| `location` | Yes | Full street address |
| `rating` | Recommended | 1.0-5.0 |
| `link` | Recommended | Booking or hotel website URL |
| `collection` | Yes | Collection UUID |

### Step 7: Create Notes

```
POST /api/notes/
```

| Field | Detail |
|-------|--------|
| `name` | Note title (e.g., "Day 1: Downtown Exploration") |
| `content` | Markdown-formatted content with detailed day plan, tips, timings |
| `date` | Associated date (`YYYY-MM-DD`) |
| `links` | Array of relevant URLs (restaurant sites, booking pages, maps) |
| `collection` | Collection UUID |

### Step 8: Create Checklists

```
POST /api/checklists/
```

Checklists include their items inline in a single request. The `items` field is **required** (pass `[]` if empty).

| Field | Required | Detail |
|-------|----------|--------|
| `name` | Yes | e.g., "Packing List", "Pre-Trip Bookings", "Documents" |
| `items` | Yes | Array of `{"name": "...", "is_checked": false}` objects. **Cannot be omitted** — pass `[]` for empty. |
| `date` | No | Optional associated date |
| `collection` | Yes | Collection UUID |
| `is_public` | No | Default `false` |

### Step 9: Create Itinerary Days

```
POST /api/itinerary-days/
```

One per date within the trip range. Provides day-level metadata.

| Field | Detail |
|-------|--------|
| `collection` | Collection UUID |
| `date` | `YYYY-MM-DD` (must be within collection start/end dates) |
| `name` | Day title: "Day 1: Arrival & Downtown", "Day 2: Nature & Adventure" |
| `description` | Day theme/overview paragraph |

### Step 10: Create Itinerary Items (Link Everything to Days)

```
POST /api/itineraries/
```

This connects visits, transportation, lodging, notes, and checklists to specific days.

| Field | Detail |
|-------|--------|
| `collection` | Collection UUID |
| `content_type` | String: `"location"`, `"transportation"`, `"lodging"`, `"note"`, `"checklist"` |
| `object_id` | UUID of the referenced entity |
| `date` | `YYYY-MM-DD` for day-specific items |
| `is_global` | `true` for trip-wide items (no date), `false` for day-specific |
| `order` | Integer for display order within the day (0-based) |

**Critical**: For locations, use `content_type: "location"` with the **Location UUID**. Do NOT use `content_type: "visit"` — the frontend only resolves `location`, `transportation`, `lodging`, `note`, and `checklist` types. Visit-type itinerary items will show as "Item not found" in the UI.

## Richness Checklist

Before marking a trip complete, verify:

- [ ] Collection has description, start/end dates
- [ ] Every location has: address, lat/lng, 2+ sentence description, rating, tags, link
- [ ] Every lodging has: check-in/check-out datetimes **with timezone offset**, timezone field, address, lat/lng, type, description
- [ ] Every transport has: departure/arrival times **with timezone offset**, start_timezone/end_timezone, origin/destination with coordinates, type
- [ ] Notes contain detailed markdown with practical tips, timing suggestions, links
- [ ] Visits created for every location with start/end datetimes **including timezone offset** and timezone field set
- [ ] All datetimes include timezone offset (no naive datetimes) — verify with: offset present OR `Z` suffix
- [ ] Itinerary days labeled with descriptive names
- [ ] Itinerary items link all visits, transport, lodging, notes to correct days with proper ordering
- [ ] Tags are meaningful and filterable (cuisine type, day label, neighborhood, activity type)

## Validation Rules Quick Reference

- **Category ownership**: Categories must belong to the same user as locations
- **Collection ownership**: All items in a collection must belong to the collection owner
- **Date ordering**: `start_date <= end_date`, `check_in <= check_out`, `date <= end_date`
- **Itinerary XOR**: Items are either `is_global=true` (no date) OR have a date (not both)
- **Public cascade**: If collection `is_public=true`, all linked items must also be public

## Known Pitfalls

These are real issues encountered during trip creation — avoid them:

| Pitfall | What Happens | Prevention |
|---------|-------------|------------|
| Using `SessionStore().create()` for auth | 400 "User is not authenticated" | Always use `Client().login()` to create sessions |
| Using session cookie instead of header | 403 CSRF failure on writes | Use `X-Session-Token` header, not `sessionid` cookie |
| Form login in dev environment | 500 staticfiles manifest error | Use X-Session-Token method instead |
| Omitting `items` on checklist | 400 validation error | Always include `"items": []` even if empty |
| Passing category as UUID string | 400 validation error | Must be dict: `{"name": "...", "display_name": "...", "icon": "..."}` |
| Using `content_type: "visit"` in itinerary | "Item not found" in frontend UI | Use `content_type: "location"` with **Location UUID** |
| Creating items for wrong user | 404 / items invisible in frontend | Verify session belongs to correct user; API filters by authenticated user |
| Changing user passwords without asking | Locks user out of their account | **Always ask the user for credentials** — never reset passwords |
| Using naive datetimes (no offset) | Times display wrong — e.g., noon PDT lunch shows at 7 PM | Always include timezone offset: `T12:00:00-07:00` or convert to UTC with `Z` |
| Omitting `timezone` on Visits/Lodging | Timeline displays times in browser timezone, not trip destination | Always set `timezone` field (e.g., `"America/Los_Angeles"`) |

## Additional Resources

### Reference Files
- **`references/api-reference.md`** — Complete field-by-field API reference with types, constraints, all choices
- **`references/example-workflow.md`** — Full example of creating a multi-day trip with every entity type
