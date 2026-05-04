# Celigo EDI Profiles

X12 and EDIFACT interchange envelope configuration (ISA/GS for X12, UNB/UNG for EDIFACT).

## CLI surface

```bash
python3 celigo_api.py edi list
python3 celigo_api.py edi get <id>
python3 celigo_api.py edi create --data '<json>'
python3 celigo_api.py edi update <id> --data '<partial-json>'   # fetch-merge-PUT
python3 celigo_api.py edi delete <id>
python3 celigo_api.py edi dependencies <id>
```

## Create payload example (X12)

```json
{
  "name": "ACME X12 Production",
  "fileType": "x12",
  "isa06": "ACMECORP",
  "isa08": "PARTNERCODE",
  "gs02": "ACMECORP"
}
```

## Key notes

- **`fileType` is immutable after creation.** The CLI rejects any `update` payload that
  includes `fileType` with a client-side error before hitting the API.
- `dependencies` returns flows, Trading Partner Connectors, and File Definitions that
  reference this profile. Check before deleting.
- `update` uses fetch-merge-PUT discipline (never sends partial payloads directly).
