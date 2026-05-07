---
name: celigo-edi-audit
description: Run an EDI cross-system audit to reconcile Celigo job history against NetSuite EDI History records for both inbound and outbound EDI documents
---

# /celigo-edi-audit

Runs `scripts/edi_audit.py` to reconcile Celigo EDI job history against NetSuite EDI History records, surfacing mismatches across inbound (850/856/860) and outbound (810/846/855/820) flows.

## Usage

```
/celigo-edi-audit [--since WINDOW] [--partner NAME] [--direction inbound|outbound|both]
```

## What it checks

**Inbound (850/856/860):**
- Every successful Celigo job has a matching NetSuite `customrecord_twx_edi_history` row
- Each NS row has `status=2` (success)
- For 850 Purchase Orders: each row has a non-null linked Sales Order transaction

**Outbound (810/846/855/820):**
- Every NetSuite EDI History row marked `status=2` (sent) has a corresponding Celigo job

## Failure buckets

| Bucket | Meaning |
|--------|---------|
| `celigo_success_ns_missing` | Celigo processed successfully but no NS record found |
| `ns_sent_celigo_missing` | NS shows document sent but no Celigo job found |
| `ns_status_error` | NS received but processing failed, or 850 SO link missing |

## Examples

```bash
# Audit last 24 hours (default)
python3 scripts/edi_audit.py

# Audit last 7 days for a specific partner
python3 scripts/edi_audit.py --since 7d --partner "ACME Corp"

# Inbound only
python3 scripts/edi_audit.py --direction inbound

# CI mode: exit 1 if mismatches found
python3 scripts/edi_audit.py --exit-nonzero-on-mismatch

# JSON-only output for piping
python3 scripts/edi_audit.py --json-only | jq '.buckets.celigo_success_ns_missing'
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--since` | `24h` | Audit window start (ISO 8601 or relative: `24h`, `7d`) |
| `--until` | now | Audit window end |
| `--partner` | all | Filter to integrations matching this partner name (substring) |
| `--direction` | `both` | `inbound`, `outbound`, or `both` |
| `--env` | config default | Celigo environment (`production`/`sandbox`) |
| `--json-only` | false | Suppress human-readable summary |
| `--exit-nonzero-on-mismatch` | false | Exit code 1 when mismatches found (CI) |

## Prerequisites

- Celigo API key configured in `config/celigo_config.json`
- NetSuite API gateway accessible at `https://nsapi.twistedx.tech/api/suiteapi`

## How to run from this skill

When the user asks to audit EDI or reconcile Celigo with NetSuite, run:

```bash
cd plugins/celigo-integration
python3 scripts/edi_audit.py [flags]
```

Parse the JSON output and surface the bucket counts and any mismatch details in your response.
