# Brainstorm: Non-SFTP EDI File Archiving to SFTP

**Date:** 2026-04-07
**Status:** Brainstorm
**Related:** EDI - VAN - Country Supplier, EDI - Cavenders (archive pattern reference)

---

## What We're Building

A real-time archiving mechanism for **all non-SFTP EDI trading partners** (VAN, AS2, or other webhook-based connections) that saves raw EDI files (ISA/GS/ST segments) to the SFTP server after each transaction (both inbound and outbound). This fills the gap where SFTP partners (Cavenders, Boot Barn) already have native archiving via Celigo's `backupDirectoryPath`, but non-SFTP partners (webhook-based) have no file archiving at all.

**Goal:** Every non-SFTP EDI transaction (inbound and outbound) produces a raw EDI file archived on the TWX EDI3 SFTP server, following the same `{archivePath}/{docType}/{YYYY}/{MM}/` structure as Cavenders. These files then flow through the existing B2B Dashboard 3-stage pipeline (SFTP sync → organize → MongoDB Atlas) without any pipeline changes.

**Rollout:** Test with one partner first (recommend **Country Supplier** — simplest VAN partner, 3 inbound flows), then roll out to all non-SFTP partners.

---

## Why This Approach

VAN inbound flows use webhooks — data arrives as JSON payloads pushed from ECGrid with no file system involved. Celigo has no native archive mechanism for webhooks like it does for SFTP (`backupDirectoryPath`). However, Celigo *does* store the raw EDI files internally (via S3), accessible through the `GET /v1/edi/documents/{documentNumber}/ediFile` API (added March 2026).

The chosen approach adds a **script hook + SFTP import step** to each VAN inbound flow:
1. A preMap/postMap hook script calls the `download_edi_file` API using data from the flow
2. The raw EDI content is passed to an SFTP import step
3. The SFTP import writes the file to the archive path on the TWX EDI3 server

This keeps the archive logic inline with the transaction processing (real-time, no delay) and reuses the existing SFTP connection and archive path conventions.

---

## Key Decisions

### 1. Archive Format
**Raw EDI files (ISA segments)** — not the Celigo-translated JSON. This matches what SFTP partners archive and what the B2B Dashboard pipeline expects.

### 2. Trigger Model
**Real-time within VAN flows** — archive happens as part of each inbound flow execution, not as a separate scheduled job. Ensures every transaction is archived immediately.

### 3. SFTP Write Mechanism
**Script hook + SFTP import step** added to each VAN inbound flow:
- Hook script calls `GET /v1/edi/documents/{documentNumber}/ediFile?documentType={documentType}`
- SFTP import writes the result as a file

### 4. Archive Path Convention
**Same as Cavenders:**
```
{{settings.integration.sftpArchiveInboundPath}}/{docType}/{YYYY}/{MM}/
```
Example: `/edi/archive/prod/country-supplier/inbound/850/2026/04/`

### 5. Field Mapping (from ediTransaction → download API)
- `documentNumber` field → `{documentNumber}` path param (e.g., `"IS38392"`)
- `documentType` field → `?documentType=` query param (e.g., `"850"`)
- Both fields are present in the webhook payload's ediTransaction data

---

## Affected Non-SFTP Partners (6+ known VAN)

| Partner | Integration ID | Inbound Flows |
|---------|---------------|---------------|
| Country Supplier | `67b365cc4d72856a82a333dc` | 850, 824, 997 |
| Galls | `680176652311c96be5affa88` | 850, 997 |
| D&B Supply | `6864561345a83ac93d4bc072` | TBD |
| Coastal Farm & Ranch | `68c46be22e6b2e5b5813b1f8` | TBD |
| Rocky Brands | `6807e03e7d181f7c98855103` | TBD |
| Family Center Farm & Home | `67b365e816e9b9f53af78d1b` | TBD |

All share the same ECGrid VAN connection: `67b36640382430a59724600d`

---

## Implementation Sketch (High-Level)

### Inbound Flows (webhook → NetSuite)
```
[Webhook export] → [Existing processing steps] → [NEW: Archive Step]
                                                       ↓
                                                 Hook script calls:
                                                 GET /edi/documents/{documentNumber}/ediFile
                                                       ↓
                                                 SFTP import writes to:
                                                 {sftpArchiveInboundPath}/{docType}/{YYYY}/{MM}/{filename}.edi
```

### Outbound Flows (NetSuite → VAN)
```
[NetSuite export] → [EDI generation steps] → [VAN import] → [NEW: Archive Step]
                                                                   ↓
                                                             Hook script calls:
                                                             GET /edi/documents/{documentNumber}/ediFile
                                                                   ↓
                                                             SFTP import writes to:
                                                             {sftpArchiveOutboundPath}/{docType}/{YYYY}/{MM}/{filename}.edi
```

**File naming:** `{partner}_{docType}_{controlNumber}_{timestamp}.edi`
Example: `country-supplier_850_000003898_20260407.edi`

---

## Risks & Mitigations

1. **Race condition:** When the webhook fires, Celigo may not have finished storing the raw EDI file to S3. The `download_edi_file` API call could return empty.
   - **Mitigation:** Use a **postSubmit** hook (runs after the main import succeeds) rather than preMap, giving Celigo more time to store the file. Add a short retry with backoff if the first call returns empty.

2. **API rate limiting:** Each archive step adds one extra API call per transaction. High-volume partners could hit Celigo rate limits.
   - **Mitigation:** The existing `CeligoClient` already has retry logic with exponential backoff for 429 responses. Monitor rate limit headers during testing.

3. **Flow execution time:** Adding an API call + SFTP write increases flow duration.
   - **Mitigation:** Archive step runs at the end of the flow after critical processing (SO creation, 997 ack) is complete. Fail-silently means it won't block critical operations.

---

## Bug to Fix First

**`download_edi_file` JSON parse error:** The `_make_request` method in `CeligoClient` always calls `json.loads(content)`, but `GET /edi/documents/{documentNumber}/ediFile` returns **raw EDI text** (not JSON). The method needs to handle non-JSON responses for this endpoint. The `Accept` header is also hardcoded to `application/json`.

This must be fixed before the archive feature can work.

---

## Resolved Questions

- **Archive format?** → Raw EDI files (ISA segments)
- **Trigger timing?** → Real-time within non-SFTP flows
- **SFTP write method?** → Script hook + SFTP import step in flow
- **Archive path?** → Same Cavenders convention: `{archivePath}/{docType}/{YYYY}/{MM}/`
- **Which API to use?** → `GET /v1/edi/documents/{documentNumber}/ediFile?documentType={documentType}`
- **Field mapping?** → `documentNumber` + `documentType` from ediTransaction record
- **SFTP connection?** → Reuse TWX EDI3 SFTP connection (`690385628852e20aee2a7953`)
- **Error handling?** → Fail silently (log + continue)
- **Deduplication?** → Leave to B2B Dashboard pipeline (SHA-256 checksums)
- **Direction scope?** → Both inbound and outbound
- **Partner scope?** → Any non-SFTP EDI partner (VAN, AS2, etc.)
- **Rollout?** → Test with one partner first (Country Supplier recommended)

## Open Questions

None — all resolved.
