---
module: Celigo Integration
date: 2026-02-19
problem_type: integration_issue
component: tooling
symptoms:
  - "CSV output contained raw export data instead of AI-summarized content"
  - "AI Agent import processed 3003 records but output was identical to input"
  - "aiSummary column missing from CSV — only raw job fields present"
root_cause: config_error
resolution_type: config_change
severity: high
tags: [celigo, ai-agent, response-mapping, csv-output, page-processor, flow-configuration]
---

# Troubleshooting: Celigo AI Agent Output Not Flowing to CSV Step

## Problem
A Celigo flow with an AI Agent import step (OpenAI gpt-4.1-nano) processed records successfully but the AI's output was silently discarded. The CSV file written by the subsequent FTP import step contained only raw export data with no AI summarization.

## Environment
- Module: Celigo Integration — AI Test flow
- Affected Component: Flow `pageProcessors` response mapping configuration
- Flow ID: `698b4a31ae386aee54914746`
- Date: 2026-02-19

## Symptoms
- AI Agent import reported 3,003 successful records (no failures)
- CSV output (`error-health-summary-*.csv`) contained 1,335 rows of raw job data
- No `aiSummary` column in CSV — only raw fields from the export step
- OpenAI API calls were being made per-record (burning tokens) but responses were thrown away

## What Didn't Work

**Attempted Solution 1:** Checking the AI Agent import configuration
- Verified AI agent had correct instructions, model (gpt-4.1-nano), and output format (text)
- **Why it failed:** The AI agent itself was working correctly — the problem was in how the flow passed data between steps, not in the AI agent configuration.

**Attempted Solution 2:** Checking the CSV import configuration
- Verified FTP import had correct file format (CSV), delimiter, and header settings
- **Why it failed:** The CSV step was also working correctly — it faithfully wrote whatever data it received. The problem was upstream in the flow's response mapping.

## Solution

The root cause was an **empty `responseMapping`** on the AI Agent's page processor entry in the flow definition. The AI Agent returns its text output in a `_text` field, but the empty mapping meant this response was discarded and the original record passed through unchanged.

**Configuration change:**

```json
// Before (broken - AI response discarded):
{
  "pageProcessors": [
    {
      "type": "import",
      "_importId": "698b4eb6adf72c4591f9685f",
      "responseMapping": {
        "fields": [],
        "lists": []
      }
    }
  ]
}

// After (fixed - AI _text mapped to aiSummary field):
{
  "pageProcessors": [
    {
      "type": "import",
      "_importId": "698b4eb6adf72c4591f9685f",
      "responseMapping": {
        "fields": [
          {
            "extract": "_text",
            "generate": "aiSummary"
          }
        ],
        "lists": []
      }
    }
  ]
}
```

**Applied via CLI:**
```bash
python3 scripts/celigo_api.py flows update 698b4a31ae386aee54914746 --data '{
  "pageProcessors": [
    {
      "type": "import",
      "_importId": "698b4eb6adf72c4591f9685f",
      "responseMapping": {
        "fields": [{"extract": "_text", "generate": "aiSummary"}],
        "lists": []
      }
    },
    {
      "type": "import",
      "_importId": "699605c7783ea4efe70cc4ff",
      "responseMapping": {"fields": [], "lists": []}
    }
  ]
}'
```

## Why This Works

1. **Celigo flow data pipeline:** Export → (record) → PageProcessor1 → (response mapping) → PageProcessor2 → (output)
2. **Response mapping** captures output from one step and adds it to the record before passing to the next step. Without it, the original record passes through unmodified.
3. **AI Agent imports** return their text output in the `_text` field. The mapping `extract: "_text"` captures this and `generate: "aiSummary"` adds it as a new field on the record.
4. The CSV step then receives the record with the `aiSummary` field and includes it as a column.

**Key insight:** Celigo AI Agent imports are "silent" by default — they process records but don't automatically inject their output back into the data pipeline. You must explicitly map the response.

## Prevention

- **Always configure `responseMapping`** when chaining page processors — empty mappings silently discard step output
- For AI Agent imports, map `_text` to a named field (e.g., `aiSummary`, `aiResponse`)
- After building a flow, run a small test and download the CSV to verify expected columns appear
- Debug by downloading the CSV from SFTP and checking headers — missing columns indicate response mapping gaps
- The Celigo UI flow builder shows response mappings visually — check this first when output isn't flowing between steps

## Related Issues

- See also: [celigo-put-full-replace-CeligoIntegration-20260219.md](./celigo-put-full-replace-CeligoIntegration-20260219.md) — discovered during the same session; the fetch-merge-PUT pattern was needed to safely update the flow's pageProcessors without destroying other fields
