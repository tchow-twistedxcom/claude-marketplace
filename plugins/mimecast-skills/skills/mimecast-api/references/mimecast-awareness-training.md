# Mimecast Awareness Training API Reference

## Overview

The Awareness Training API (API 1.0) provides access to Mimecast's Security Awareness For Employees
(SAFE) training platform. All endpoints require the **Awareness Training product** to be enabled in
the Mimecast admin console.

> **Authentication**: OAuth 2.0 is strongly recommended. HMAC (Legacy Auth) may not work for
> Awareness Training endpoints.

All endpoints use `POST` with a `{"data": [...]}` body wrapper.

---

## CLI Commands

All awareness training commands use the `awareness` resource:

```bash
python3 scripts/mimecast_api.py awareness <action> [options]
```

### campaigns — List Training Campaigns

```bash
python3 scripts/mimecast_api.py awareness campaigns [--source SOURCE] [--output table|json]
```

- `--source`: Filter campaigns by source (optional)
- Returns: Campaign ID, name, status, sent count, completed count, correct percentage

**API Endpoint**: `POST /api/awareness-training/campaign/get-campaigns`

---

### campaign-users — Per-User Campaign Data

```bash
python3 scripts/mimecast_api.py awareness campaign-users [--campaign-id ID] [--output table|json]
```

- `--campaign-id`: Specific campaign ID (optional — omit for all campaigns)
- Returns: Per-user training completion, score data

**API Endpoint**: `POST /api/awareness-training/campaign/get-user-data`

---

### performance — Company Training Performance Details

```bash
python3 scripts/mimecast_api.py awareness performance [--output table|json]
```

- Returns: Detailed company-wide training performance metrics

**API Endpoint**: `POST /api/awareness-training/company/get-performance-details`

---

### performance-summary — Company Training Performance Summary

```bash
python3 scripts/mimecast_api.py awareness performance-summary [--output table|json]
```

- Returns: Summary-level company training performance metrics

**API Endpoint**: `POST /api/awareness-training/company/get-performance-summary`

---

### phishing — Phishing Simulation Campaign Details

```bash
python3 scripts/mimecast_api.py awareness phishing [--campaign-id ID] [--output table|json]
```

- `--campaign-id`: Specific phishing campaign ID (optional)
- Returns: Campaign name, sent, opened, clicked, submitted, reported counts

**API Endpoint**: `POST /api/awareness-training/phishing/campaign/get-campaign`

---

### phishing-users — Per-User Phishing Simulation Data

```bash
python3 scripts/mimecast_api.py awareness phishing-users [--campaign-id ID] [--output table|json]
```

- `--campaign-id`: Specific phishing campaign ID (optional)
- Returns: Per-user phishing interaction data (opened, clicked, submitted, reported)

**API Endpoint**: `POST /api/awareness-training/phishing/campaign/get-user-data`

---

### safe-score — Per-User SAFE Scores

```bash
python3 scripts/mimecast_api.py awareness safe-score [--email EMAIL] [--output table|json]
```

- `--email`: Filter to a specific user (optional — omit for all users)
- Returns: Email, name, department, risk grade, knowledge score, engagement score

**API Endpoint**: `POST /api/awareness-training/company/get-safe-score-details`

---

### safe-score-summary — Company SAFE Score Summary

```bash
python3 scripts/mimecast_api.py awareness safe-score-summary [--output table|json]
```

- Returns: Company-level SAFE score aggregate statistics

**API Endpoint**: `POST /api/awareness-training/company/get-safe-score-summary`

---

### queue — Training Queue

```bash
python3 scripts/mimecast_api.py awareness queue [--output table|json]
```

- Returns: Users in the training queue with pending assignments

**API Endpoint**: `POST /api/awareness-training/queue/get-queue`

---

### training-details — User Training Details

```bash
python3 scripts/mimecast_api.py awareness training-details [--email EMAIL] [--output table|json]
```

- `--email`: User email address (optional — omit for all users)
- Returns: Detailed training history for the specified user

**API Endpoint**: `POST /api/awareness-training/user/get-training-details`

---

### watchlist — High-Risk User Watchlist

```bash
python3 scripts/mimecast_api.py awareness watchlist [--output table|json]
```

- Returns: High-risk users with email, name, department, risk level, risk score

**API Endpoint**: `POST /api/awareness-training/company/get-watchlist-details`

---

### watchlist-summary — High-Risk User Watchlist Summary

```bash
python3 scripts/mimecast_api.py awareness watchlist-summary [--output table|json]
```

- Returns: Summary statistics for the high-risk watchlist

**API Endpoint**: `POST /api/awareness-training/company/get-watchlist-summary`

---

## MCP Tools

The following MCP tools are available for AI-assisted workflows:

| Tool | Description |
|------|-------------|
| `mimecast_list_campaigns` | List awareness training campaigns |
| `mimecast_get_safe_scores` | Get per-user SAFE score details |
| `mimecast_get_phishing_results` | Get phishing simulation campaign results |
| `mimecast_get_watchlist` | Get high-risk user watchlist |

---

## API Endpoints Reference

| Action | Method | Endpoint |
|--------|--------|----------|
| campaigns | POST | `/api/awareness-training/campaign/get-campaigns` |
| campaign-users | POST | `/api/awareness-training/campaign/get-user-data` |
| performance | POST | `/api/awareness-training/company/get-performance-details` |
| performance-summary | POST | `/api/awareness-training/company/get-performance-summary` |
| phishing | POST | `/api/awareness-training/phishing/campaign/get-campaign` |
| phishing-users | POST | `/api/awareness-training/phishing/campaign/get-user-data` |
| safe-score | POST | `/api/awareness-training/company/get-safe-score-details` |
| safe-score-summary | POST | `/api/awareness-training/company/get-safe-score-summary` |
| queue | POST | `/api/awareness-training/queue/get-queue` |
| training-details | POST | `/api/awareness-training/user/get-training-details` |
| watchlist | POST | `/api/awareness-training/company/get-watchlist-details` |
| watchlist-summary | POST | `/api/awareness-training/company/get-watchlist-summary` |

---

## Notes

- **Product requirement**: All endpoints return an error if Awareness Training is not enabled.
- **OAuth required**: HMAC authentication is not supported for Awareness Training API.
- **Read-only**: All Awareness Training endpoints are read-only (no create/update/delete).
- **Rate limits**: Standard Mimecast rate limits apply (120 req/min). The client handles
  backoff automatically.
