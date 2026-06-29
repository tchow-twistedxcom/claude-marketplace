# Calendar API Reference

User calendar reads via Microsoft Graph API. Useful for meeting and invite forensics (attacker
created calendar invites, malicious meeting links, or calendar-based phishing). Uses `Calendars.Read`
(granted), Graph v1.0, app-only.

## Endpoints

| Operation | Method | Endpoint | Permission |
|-----------|--------|----------|------------|
| List events | GET | `/users/{id}/events` | `Calendars.Read` |
| Calendar view (time window) | GET | `/users/{id}/calendarView?startDateTime=...&endDateTime=...` | `Calendars.Read` |
| List calendars | GET | `/users/{id}/calendars` | `Calendars.Read` |

`{id}` is a user object ID or UPN (app-only has no "me").

## CLI Commands

```bash
# List a user's events
python3 azure_ad_api.py calendar events user@domain.com --top 50

# Calendar view for a bounded window (both start and end are required, UTC ISO 8601)
python3 azure_ad_api.py calendar view user@domain.com \
  --start 2026-06-01T00:00:00Z --end 2026-06-29T00:00:00Z

# List the user's calendars
python3 azure_ad_api.py calendar calendars user@domain.com
```

## MCP Tools

| Tool | Purpose |
|------|---------|
| `azure_ad_user_events` | List a user's calendar events |
| `azure_ad_calendar_view` | Events in a start/end window (expands recurring series) |
| `azure_ad_user_calendars` | List the user's calendars |

## Caveats

- **App-only `Calendars.Read` reads EVERY mailbox in the tenant by default.** This is broad. To scope
  the app to a subset of mailboxes, an Exchange administrator must configure an **Application Access
  Policy** (`New-ApplicationAccessPolicy` in Exchange Online PowerShell) bound to a mail-enabled
  security group. Changes can take more than an hour to take effect in Graph even after
  `Test-ApplicationAccessPolicy` passes. This is an Exchange admin action, not a Graph call, and is
  out of scope for this skill.
- `calendarView` **requires** both `startDateTime` and `endDateTime` and expands recurring events
  into individual instances. Prefer it over `/events` for a bounded time window.
