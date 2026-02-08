# Example: Creating a Complete Multi-Day Trip

This example creates a 3-day trip to Tokyo with restaurants, attractions, lodging, transportation, notes, checklists, and a fully scheduled itinerary.

## Setup

```python
import requests

BASE = "http://localhost:8016"
s = requests.Session()

# Authenticate via X-Session-Token (preferred method)
# First, create a session key via Django shell:
#   docker compose exec server python manage.py shell -c "
#   from django.test import Client
#   c = Client()
#   c.login(username='myuser', password='mypass')
#   print(c.session.session_key)
#   "
SESSION_KEY = "<paste-session-key-here>"
s.headers.update({
    "X-Session-Token": SESSION_KEY,
    "Content-Type": "application/json",
})

# No CSRF refresh needed with X-Session-Token!
def rc():
    """No-op: X-Session-Token bypasses CSRF."""
    pass
```

## Step 1: Create Collection

```python
rc()
r = s.post(f"{BASE}/api/collections/", json={
    "name": "Tokyo Family Adventure",
    "description": "3-day exploration of Tokyo with focus on kid-friendly attractions, authentic Japanese cuisine, and cultural experiences. Staying in Shinjuku for central access to all major areas.",
    "start_date": "2025-04-10",
    "end_date": "2025-04-12",
    "is_public": False
})
CID = r.json()["id"]
```

## Step 2: Create Categories

```python
rc()
r = s.post(f"{BASE}/api/categories/", json={
    "name": "restaurant", "display_name": "Restaurant", "icon": "🍽️"
})
rest_cat = {"name": "restaurant", "display_name": "Restaurant", "icon": "🍽️"}

rc()
r = s.post(f"{BASE}/api/categories/", json={
    "name": "attraction", "display_name": "Attraction", "icon": "🎢"
})
attr_cat = {"name": "attraction", "display_name": "Attraction", "icon": "🎢"}

rc()
r = s.post(f"{BASE}/api/categories/", json={
    "name": "temple", "display_name": "Temple & Shrine", "icon": "⛩️"
})
temple_cat = {"name": "temple", "display_name": "Temple & Shrine", "icon": "⛩️"}
```

## Step 3: Create Locations (with full details)

```python
rc()
r = s.post(f"{BASE}/api/locations/", json={
    "name": "Ichiran Ramen Shibuya",
    "location": "1-22-7 Jinnan, Shibuya, Tokyo 150-0041, Japan",
    "description": "World-famous tonkotsu ramen chain with individual booths for focused eating. Customize every aspect of your ramen via a paper form: broth richness, noodle firmness, garlic level, spice, and green onion amount. The signature red secret sauce (hiden no tare) is a must. Kids love the private booth experience. Open 24 hours. Expect 10-20 min wait at peak times. ~¥1,000-1,500 per person.",
    "latitude": 35.6617,
    "longitude": 139.6983,
    "rating": 4.5,
    "link": "https://en.ichiran.com/shop/tokyo/shibuya/",
    "tags": ["ramen", "tonkotsu", "day-1-dinner", "shibuya", "kid-friendly", "24-hours"],
    "category": rest_cat,
    "collections": [CID],
    "is_public": False
})
ichiran_id = r.json()["id"]

rc()
r = s.post(f"{BASE}/api/locations/", json={
    "name": "Senso-ji Temple",
    "location": "2-3-1 Asakusa, Taito City, Tokyo 111-0032, Japan",
    "description": "Tokyo's oldest and most famous Buddhist temple, founded in 645 AD. Enter through the iconic Kaminarimon (Thunder Gate) with its massive red lantern. Walk the 250m Nakamise-dori shopping street for traditional snacks and souvenirs. The five-story pagoda is stunning at sunset. Free entry to temple grounds; main hall open 6AM-5PM (Apr-Sep). Allow 1.5-2 hours including shopping street.",
    "latitude": 35.7148,
    "longitude": 139.7967,
    "rating": 4.8,
    "link": "https://www.senso-ji.jp/english/",
    "tags": ["temple", "historic", "day-2-morning", "asakusa", "free", "photography"],
    "category": temple_cat,
    "collections": [CID],
    "is_public": False
})
sensoji_id = r.json()["id"]

rc()
r = s.post(f"{BASE}/api/locations/", json={
    "name": "teamLab Borderless",
    "location": "Azabudai Hills Garden Plaza B, 1-2-4 Azabudai, Minato-ku, Tokyo",
    "description": "Immersive digital art museum where artworks flow from room to room without boundaries. Kids are mesmerized by interactive installations that respond to touch and movement. The Crystal Universe and Infinity Mirror rooms are highlights. New Azabudai Hills location opened 2024. Book tickets online in advance — sells out weeks ahead. Adults ¥3,800, Children (4-12) ¥1,300. Allow 2-3 hours.",
    "latitude": 35.6604,
    "longitude": 139.7384,
    "rating": 4.7,
    "link": "https://www.teamlab.art/e/borderless-azabudai/",
    "tags": ["art", "interactive", "day-1-afternoon", "kids", "indoor", "must-book"],
    "category": attr_cat,
    "collections": [CID],
    "is_public": False
})
teamlab_id = r.json()["id"]
```

## Step 4: Create Visits (with specific times)

```python
# IMPORTANT: Always include timezone offset in datetimes!
# Naive datetimes (without offset) are stored as UTC, causing wrong display times.
# Tokyo is JST = UTC+9, so append "+09:00" to all Tokyo times.

rc()
r = s.post(f"{BASE}/api/visits/", json={
    "location": ichiran_id,
    "start_date": "2025-04-10T18:00:00+09:00",   # 6:00 PM JST
    "end_date": "2025-04-10T19:30:00+09:00",     # 7:30 PM JST
    "timezone": "Asia/Tokyo",                      # Required for timeline display
    "notes": "Arrive by 5:45 PM to beat dinner rush. Order extra noodles (kaedama) for ¥210."
})
ichiran_visit = r.json()["id"]

rc()
r = s.post(f"{BASE}/api/visits/", json={
    "location": sensoji_id,
    "start_date": "2025-04-11T08:30:00+09:00",   # 8:30 AM JST
    "end_date": "2025-04-11T10:30:00+09:00",     # 10:30 AM JST
    "timezone": "Asia/Tokyo",
    "notes": "Early morning is best to avoid crowds. Get melon pan from Kagetsudo on Nakamise-dori."
})
sensoji_visit = r.json()["id"]

rc()
r = s.post(f"{BASE}/api/visits/", json={
    "location": teamlab_id,
    "start_date": "2025-04-10T14:00:00+09:00",   # 2:00 PM JST
    "end_date": "2025-04-10T16:30:00+09:00",     # 4:30 PM JST
    "timezone": "Asia/Tokyo",
    "notes": "Tickets pre-booked for 2PM slot. Wear comfortable shoes — lots of walking. Some rooms have water — bring sandals."
})
teamlab_visit = r.json()["id"]
```

## Step 5: Create Transportation

```python
rc()
r = s.post(f"{BASE}/api/transportations/", json={
    "type": "plane",
    "name": "Flight LAX → NRT (Japan Airlines)",
    "description": "Non-stop flight, ~11.5 hours. JAL has excellent kids' amenities including activity packs and kid meals. Request bulkhead seats for extra legroom. Arrives next day due to timezone.",
    "date": "2025-04-09T11:00:00-07:00",      # 11:00 AM PDT departure
    "end_date": "2025-04-10T15:00:00+09:00",  # 3:00 PM JST arrival (next day)
    "start_timezone": "America/Los_Angeles",
    "end_timezone": "Asia/Tokyo",
    "flight_number": "JL015",
    "from_location": "Los Angeles International Airport (LAX)",
    "to_location": "Narita International Airport (NRT)",
    "origin_latitude": 33.9425,
    "origin_longitude": -118.4081,
    "destination_latitude": 35.7647,
    "destination_longitude": 140.3864,
    "start_code": "LAX",
    "end_code": "NRT",
    "link": "https://www.jal.co.jp/en/",
    "collection": CID,
    "is_public": False
})
flight_id = r.json()["id"]
```

## Step 6: Create Lodging

```python
rc()
r = s.post(f"{BASE}/api/lodging/", json={
    "name": "Park Hyatt Tokyo",
    "type": "hotel",
    "description": "Iconic luxury hotel from 'Lost in Translation'. Located on floors 39-52 of the Shinjuku Park Tower with panoramic city views. The New York Grill on the 52nd floor is perfect for a splurge dinner. Pool and gym on 47th floor. Excellent concierge for booking kids' activities. Central Shinjuku location with easy access to JR lines.",
    "check_in": "2025-04-10T15:00:00+09:00",   # 3:00 PM JST check-in
    "check_out": "2025-04-12T11:00:00+09:00",  # 11:00 AM JST check-out
    "timezone": "Asia/Tokyo",                    # Required — drives trip display timezone
    "latitude": 35.6869,
    "longitude": 139.6907,
    "location": "3-7-1-2 Nishi Shinjuku, Shinjuku-ku, Tokyo 163-1055, Japan",
    "rating": 4.8,
    "link": "https://www.hyatt.com/park-hyatt/tyoph-park-hyatt-tokyo",
    "collection": CID,
    "is_public": False
})
hotel_id = r.json()["id"]
```

## Step 7: Create Notes

```python
rc()
r = s.post(f"{BASE}/api/notes/", json={
    "name": "Day 1: Arrival, Art & Ramen",
    "content": """## Day 1 Plan (April 10)

**Afternoon** — Arrive NRT ~3PM. Take Narita Express to Shinjuku (~80 min, ¥3,250).
Check into Park Hyatt Tokyo.

**2:00 PM** — teamLab Borderless at Azabudai Hills (pre-booked tickets)
- Allow 2-3 hours for the immersive experience
- Wear comfortable shoes, some rooms have water floors
- Kids will love the interactive flower and crystal rooms

**6:00 PM** — Ichiran Ramen in Shibuya for dinner
- 15-min walk from Shibuya station
- Individual booth dining — unique experience for kids
- Customize ramen via paper form

**After dinner** — Walk through Shibuya Crossing (the world's busiest intersection)
and take photos from the Shibuya Sky observation deck if energy permits.""",
    "date": "2025-04-10",
    "links": [
        "https://www.teamlab.art/e/borderless-azabudai/",
        "https://en.ichiran.com/shop/tokyo/shibuya/",
        "https://www.shibuyasky.jp/en/"
    ],
    "collection": CID,
    "is_public": False
})
note1_id = r.json()["id"]
```

## Step 8: Create Checklist

```python
rc()
r = s.post(f"{BASE}/api/checklists/", json={
    "name": "Pre-Trip Bookings & Tasks",
    "items": [
        {"name": "Book teamLab Borderless tickets online (sells out weeks ahead)", "is_checked": False},
        {"name": "Reserve Ichiran Ramen — no reservation needed, but arrive early", "is_checked": False},
        {"name": "Buy Narita Express tickets (can pre-purchase online)", "is_checked": False},
        {"name": "Download offline maps for Tokyo", "is_checked": False},
        {"name": "Pack rain gear and comfortable walking shoes", "is_checked": False},
    ],
    "collection": CID,
    "is_public": False
})
checklist_id = r.json()["id"]

# IMPORTANT: The "items" field is REQUIRED — omitting it returns 400.
# Pass "items": [] for an empty checklist.
```

## Step 9: Create Itinerary Days

```python
for date, name, desc in [
    ("2025-04-10", "Day 1: Arrival, Art & Ramen",
     "Arrive Tokyo, check in, teamLab Borderless, Ichiran Ramen in Shibuya"),
    ("2025-04-11", "Day 2: Temples, Markets & Sushi",
     "Senso-ji Temple, Tsukiji Outer Market, conveyor belt sushi, Akihabara"),
    ("2025-04-12", "Day 3: Shinjuku & Departure",
     "Shinjuku Gyoen National Garden, last-minute shopping, airport transfer"),
]:
    rc()
    s.post(f"{BASE}/api/itinerary-days/", json={
        "collection": CID,
        "date": date,
        "name": name,
        "description": desc
    })
```

## Step 10: Create Itinerary Items (Link to Days)

```python
# IMPORTANT: Use "location" with Location UUIDs, NOT "visit" with Visit UUIDs.
# The frontend only resolves: location, transportation, lodging, note, checklist.
# Using "visit" causes "Item not found" errors in the UI.

# Day 1 items in order
items = [
    # (content_type, object_id, date, order)
    ("transportation", flight_id, "2025-04-10", 0),   # Arrival flight
    ("lodging", hotel_id, "2025-04-10", 1),            # Check-in
    ("location", teamlab_id, "2025-04-10", 2),         # teamLab 2PM (Location UUID!)
    ("location", ichiran_id, "2025-04-10", 3),         # Dinner 6PM (Location UUID!)
    ("note", note1_id, "2025-04-10", 4),               # Day plan note

    # Day 2 items
    ("location", sensoji_id, "2025-04-11", 0),         # Senso-ji 8:30AM (Location UUID!)

    # Global items (trip-wide)
    # ("checklist", checklist_id, None, 0),  # Use is_global=True
]

for ct, oid, date, order in items:
    rc()
    payload = {
        "collection": CID,
        "content_type": ct,
        "object_id": oid,
        "order": order,
    }
    if date:
        payload["date"] = date
        payload["is_global"] = False
    else:
        payload["is_global"] = True
    s.post(f"{BASE}/api/itineraries/", json=payload)

# Global checklist
rc()
s.post(f"{BASE}/api/itineraries/", json={
    "collection": CID,
    "content_type": "checklist",
    "object_id": checklist_id,
    "is_global": True,
    "order": 0
})
```

## Result

The trip now appears in AdventureLog with:
- Collection overview with dates and description
- Map with all locations pinned (restaurants, temples, attractions)
- Day-by-day itinerary timeline with ordered items
- Transportation segments with flight details
- Hotel with check-in/check-out times
- Rich notes with markdown formatting and links
- Pre-trip checklist accessible from any view
- Every location has description, coordinates, rating, website, and tags
