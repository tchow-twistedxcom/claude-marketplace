# Parsers and Generators

Stateless, synchronous endpoints for EDI document parsing and generation using
file definitions. Unlike the `processors` resource (which processes data inside
a running flow), parsers/generators are standalone utility endpoints.

## Difference from `processors`

| | `processors` | `parsers` / `generators` |
|---|---|---|
| Execution context | Inside a flow (async) | Standalone (sync) |
| State | Stateful (part of job) | Stateless (fire and forget) |
| Use case | Data transformation in pipeline | One-off EDI conversion/testing |

## CLI Commands

```bash
# Parse raw EDI data using a file definition
python3 scripts/celigo_api.py parsers parse \
  --data '{"_fileDefinitionId": "<file_def_id>", "data": "ISA*00*..."}'

# Parse from a JSON file
python3 scripts/celigo_api.py parsers parse --file parse_request.json

# Generate EDI output from structured data
python3 scripts/celigo_api.py parsers generate \
  --data '{"_fileDefinitionId": "<file_def_id>", "data": [{"header": {...}, "lines": [...]}]}'

# Generate from a JSON file
python3 scripts/celigo_api.py parsers generate --file generate_request.json
```

## Request Format

### Parse Request
```json
{
  "_fileDefinitionId": "abc123",
  "data": "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *..."
}
```

### Generate Request
```json
{
  "_fileDefinitionId": "abc123",
  "data": [
    {
      "ISA_SenderID": "MYCOMPANY",
      "ISA_ReceiverID": "PARTNER",
      "GS_FunctionalGroup": "PO",
      "transactions": [...]
    }
  ]
}
```

## Supported Formats

Determined by the `fileType` of the referenced file definition:
- `x12` - EDI X12 (850, 856, 810, 846, etc.)
- `edifact` - UN/EDIFACT
- `fixed` - Fixed-width flat files
- `csv` - CSV/delimited files

## API Endpoints (Reference)

```
POST /v1/parsers     - Parse raw data using a file definition
POST /v1/generators  - Generate structured output using a file definition
```

Both endpoints are stateless (no resource created, no `_id` returned).
