# NetSuite Execution Logs

Query script execution logs from NetSuite without accessing the UI.

## Quick Start

```bash
# Ensure gateway is running
cd ~/NetSuiteApiGateway && docker compose up -d

# Query recent DEBUG logs
python3 scripts/query_execution_logs.py --level DEBUG --hours 1 --account dm

# Query logs for specific script
python3 scripts/query_execution_logs.py --script customscript_pri_qt_sl_render_query --hours 1 --account dm --format detailed
```

## Options

| Option | Description |
|--------|-------------|
| `--script <id>` | Filter by script ID |
| `--level <level>` | DEBUG, AUDIT, ERROR, EMERGENCY |
| `--hours <n>` | Logs from last N hours |
| `--title <pattern>` | Search log titles |
| `--account <a>` | dm (dutyman) or twx (twistedx) |
| `--env <e>` | prod, sb1, sb2 |
| `--format <f>` | table, json, detailed |

## Examples

```bash
# Get all errors from last 24 hours
python3 scripts/query_execution_logs.py --level ERROR --hours 24 --account dm

# Search for specific log messages
python3 scripts/query_execution_logs.py --title "DEBUG-USER" --hours 1 --account dm

# Export to JSON
python3 scripts/query_execution_logs.py --hours 1 --format json > logs.json
```

See [SKILL.md](SKILL.md) for full documentation.
