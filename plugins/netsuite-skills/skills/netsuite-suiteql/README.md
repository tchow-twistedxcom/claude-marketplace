# NetSuite SuiteQL Skill - Installation & Quick Start

## Installation

### Option 1: Install directly
```bash
cp -r netsuite-suiteql ~/.claude/skills/
```

### Option 2: Extract from zip
```bash
unzip netsuite-suiteql.zip
cp -r netsuite-suiteql ~/.claude/skills/
```

## Quick Start

The skill is now available in Claude Code. To use it:

1. **Invoke the skill:**
   ```
   /skill netsuite-suiteql
   ```

2. **Run a query directly:**
   ```bash
   python3 ~/.claude/skills/netsuite-suiteql/scripts/query_netsuite.py 'SELECT id, companyname FROM customer WHERE ROWNUM <= 5'
   ```

## Prerequisites

The NetSuite API Gateway must be running:
```bash
cd ~/NetSuiteApiGateway
docker compose up -d
```

**Authentication is automatic** - The gateway handles OAuth 1.0a and OAuth 2.0 authentication for you. No session cookies or manual login required!

## Multi-Account Support

The skill supports querying multiple NetSuite accounts:

| Account | Alias | Auth Type | Environments |
|---------|-------|-----------|--------------|
| twistedx | twx | OAuth 1.0a | production, sandbox, sandbox2 |
| dutyman | dm | OAuth 2.0 M2M | production, sandbox |

### Query Different Accounts

```bash
# Query Twisted X sandbox2 (default)
python3 query_netsuite.py 'SELECT id, companyname FROM customer WHERE ROWNUM <= 5'

# Query Dutyman production
python3 query_netsuite.py 'SELECT id, companyname FROM customer WHERE ROWNUM <= 5' --account dm --env prod

# Query Twisted X production
python3 query_netsuite.py 'SELECT id, companyname FROM customer WHERE ROWNUM <= 5' --account twx --env prod
```

### List Available Accounts

```bash
python3 query_netsuite.py --list-accounts
```

## Usage Examples

### Basic query (default: twistedx/sandbox2)
```bash
cd ~/.claude/skills/netsuite-suiteql/scripts
python3 query_netsuite.py 'SELECT * FROM customrecord_pri_frgt_cnt WHERE ROWNUM <= 10'
```

### Query specific account and environment
```bash
python3 query_netsuite.py 'SELECT id, companyname FROM customer WHERE ROWNUM <= 5' --account dm --env prod
```

### Parameterized query
```bash
python3 query_netsuite.py 'SELECT * FROM customrecord_pri_frgt_cnt WHERE id = ?' --params 12345
```

### Query with formatting
```bash
python3 query_netsuite.py 'SELECT id, companyname FROM customer WHERE ROWNUM <= 5' --format table
```

### JSON output for scripting
```bash
python3 query_netsuite.py 'SELECT id FROM customer WHERE ROWNUM <= 3' --format json
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--account <account>` | Account to query: `twistedx`/`twx` or `dutyman`/`dm` (default: twistedx) |
| `--env <environment>` | Environment: `prod`, `sb1`, `sb2` (default: sb2) |
| `--params <p1,p2,...>` | Comma-separated parameter values for ? placeholders |
| `--all-rows` | Fetch all rows with automatic pagination |
| `--format <format>` | Output format: `json`, `table`, `csv` (default: table) |
| `--list-accounts` | List available accounts and environments |

## Documentation

- **SKILL.md** - Complete skill documentation with workflows and best practices
- **references/common_queries.md** - Library of pre-built query patterns
- **references/table_reference.md** - NetSuite schema and field reference
- **references/suiteql_functions.md** - Supported/unsupported SQL functions with alternatives

## Purpose

This skill enables rapid ad hoc SuiteQL query testing during NetSuite Record Display development, particularly for:
- Testing container flowchart queries
- Verifying custom record data structures
- Exploring transaction relationships
- Debugging data issues
- Validating SuiteQL syntax and performance

For more details, see SKILL.md.
