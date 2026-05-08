# Celigo File Definitions — EDI Formats

Extension of File Definitions to cover X12 and EDIFACT formats (schema versions 1 and 2).

## CLI surface

```bash
python3 celigo_api.py filedefinitions list
python3 celigo_api.py filedefinitions get <id>
python3 celigo_api.py filedefinitions create --data '<json>' [--schema-version 1|2]
python3 celigo_api.py filedefinitions update <id> --data '<partial-json>' [--schema-version 1|2]
python3 celigo_api.py filedefinitions delete <id>
python3 celigo_api.py filedefinitions dependencies <id>
```

## Supported formats

| `format` value | EDI-specific required fields |
|---|---|
| `delimited` | none |
| `fixed` | none |
| `x12` | `documentType`, `globalId` |
| `edifact` | `documentType`, `globalId` |

## Create payload example (X12 850)

```json
{
  "name": "850 Purchase Order",
  "format": "x12",
  "documentType": "850",
  "globalId": "004010850"
}
```

## Key notes

- For `x12` and `edifact` formats, `documentType` and `globalId` are required.
  The CLI validates this client-side before sending the request.
- `--schema-version 1` or `--schema-version 2` sets the `version` field.
  Schema version 2 is the default and recommended for new definitions.
- `dependencies` returns flows and exports/imports that reference this definition.
