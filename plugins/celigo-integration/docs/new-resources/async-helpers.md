# Celigo Async Helpers

Three-phase pattern (submit → poll → result) for long-running Celigo operations.

## CLI surface

```bash
# Submit a long-running operation, get a job ID back
python3 celigo_api.py async submit <operation> --data '<json>'

# Check job status
python3 celigo_api.py async poll <job-id>

# Fetch the final result (errors if not done yet)
python3 celigo_api.py async result <job-id>

# Convenience: submit + poll until done + return result
python3 celigo_api.py async wait <operation> --data '<json>' --timeout 120 --interval 2
```

## Key notes

- `wait` defaults to a 2s poll interval and 120s timeout.
- When a long-running operation is expected (e.g., large data load), use `submit` + `poll`
  manually instead of `wait` to avoid blocking the CLI.
- `poll` status values: `pending`, `running`, `done`, `failed`.
- Operations are Celigo-defined; consult the API docs for valid operation names.
