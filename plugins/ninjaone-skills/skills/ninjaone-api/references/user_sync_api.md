# Azure AD User Sync API Reference

Syncs Azure AD user information to NinjaOne device custom fields based on logged-on user data.

## Overview

This tool matches NinjaOne device logged-on users to Azure AD accounts and associates user information with devices via custom fields. It enables automated population of user details (display name, email, department, job title) on device records.

## Prerequisites

### NinjaOne Admin Console
Create custom fields before running sync:
1. **adDisplayName** - Text field, device-level
2. **adEmail** - Text field, device-level
3. (Optional) **adDepartment** - Text field, device-level
4. (Optional) **adJobTitle** - Text field, device-level

### Azure AD Configuration
The M365 skill must be configured with valid credentials and `User.Read.All` permission.

## Commands

### Report Mode
Preview matches without making any changes.

```bash
python ad_user_sync.py report [OPTIONS]
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--org-id` | int | - | Filter by organization ID |
| `--org-name` | string | - | Filter by organization name (auto-resolves) |
| `--filter`, `--df` | string | - | Device filter expression |
| `--format`, `-f` | choice | table | Output format: `table` or `json` |

**Examples:**
```bash
# Report for specific organization
python ad_user_sync.py report --org-name "Twisted X"

# Report with JSON output
python ad_user_sync.py report --org-id 2 --format json

# Filter to specific device class
python ad_user_sync.py report --org-name "Acme" --filter "class = WINDOWS_WORKSTATION"
```

### Sync Mode
Update NinjaOne device custom fields with matched AD user data.

```bash
python ad_user_sync.py sync [OPTIONS]
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--org-id` | int | - | Filter by organization ID |
| `--org-name` | string | - | Filter by organization name |
| `--filter`, `--df` | string | - | Device filter expression |
| `--display-name-field` | string | adDisplayName | Custom field for AD display name |
| `--email-field` | string | adEmail | Custom field for AD email |
| `--department-field` | string | - | Optional: Custom field for department |
| `--job-title-field` | string | - | Optional: Custom field for job title |
| `--rate-limit` | float | 0.5 | Seconds between API calls |
| `--format`, `-f` | choice | table | Output format: `table` or `json` |

**Examples:**
```bash
# Sync with default field names
python ad_user_sync.py sync --org-name "Twisted X"

# Sync with custom field names
python ad_user_sync.py sync --org-id 2 --display-name-field "UserName" --email-field "UserEmail"

# Sync with all fields including department and job title
python ad_user_sync.py sync --org-name "Acme" \
  --display-name-field "adDisplayName" \
  --email-field "adEmail" \
  --department-field "adDepartment" \
  --job-title-field "adJobTitle"

# Slower rate limit for API throttling
python ad_user_sync.py sync --org-name "Large Org" --rate-limit 1.0
```

## How Matching Works

### Username Normalization
NinjaOne usernames are normalized before AD lookup:

| NinjaOne Format | Normalized |
|-----------------|------------|
| `DOMAIN\username` | `username` |
| `DOMAIN/username` | `username` |
| `user@domain.com` | `user@domain.com` |
| `username` | `username` |

### AD User Cache
Azure AD users are indexed by multiple keys for flexible matching:
- Full UPN: `jsmith@company.com`
- Email address (if different from UPN)
- Username part: `jsmith`

### Match Strategy
1. Extract logged-on user from NinjaOne device
2. Normalize username (strip domain prefix)
3. Look up in AD cache by:
   - Exact match on normalized username
   - Variation without dots (`john.smith` → `johnsmith`)
   - First part before dot (`john.smith` → `john`)

## Output Formats

### Report Table
```
================================================================================
AZURE AD USER SYNC REPORT
================================================================================
Devices Analyzed: 92
Users Matched:    72 (78.3%)
Users Not Found:  20

--------------------------------------------------------------------------------
MATCHED DEVICES (showing up to 20)
--------------------------------------------------------------------------------
Device Name               NinjaOne User        AD Display Name      AD Email
--------------------------------------------------------------------------------
JSMITH-L                  DOMAIN\jsmith        John Smith           jsmith@company.com
...
```

### Report JSON
```json
{
  "summary": {
    "devices_analyzed": 92,
    "users_matched": 72,
    "users_not_found": 20,
    "match_rate": 78.3
  },
  "matched": [
    {
      "device_id": 123,
      "device_name": "JSMITH-L",
      "ninja_user": "DOMAIN\\jsmith",
      "ad_user": {
        "displayName": "John Smith",
        "email": "jsmith@company.com",
        "department": "Engineering",
        "jobTitle": "Software Engineer"
      }
    }
  ],
  "unmatched": [
    {
      "device_id": 456,
      "device_name": "MACBOOK-1",
      "ninja_user": "localuser (console)",
      "reason": "No AD user found"
    }
  ]
}
```

### Sync Result
```
================================================================================
AZURE AD USER SYNC COMPLETE
================================================================================
Devices Updated:  72
Devices Skipped:  20
Errors:           0

Field Mapping:
  displayName -> adDisplayName
  email -> adEmail
================================================================================
```

## Common Workflows

### Initial Assessment
```bash
# Run report first to see match rates
python ad_user_sync.py report --org-name "Company" --format json > assessment.json

# Review unmatched devices
jq '.unmatched' assessment.json
```

### Production Sync
```bash
# Sync all matched devices
python ad_user_sync.py sync --org-name "Company"

# Verify via NinjaOne queries
python ninjaone_api.py queries custom-fields --org-name "Company"
```

### Multi-Organization Sync
```bash
# Sync multiple organizations
for org in "Org A" "Org B" "Org C"; do
  echo "Syncing $org..."
  python ad_user_sync.py sync --org-name "$org" --rate-limit 0.5
done
```

## Unmatched Device Categories

Common reasons for unmatched devices:

| Category | Example | Resolution |
|----------|---------|------------|
| Mac local users | `phoenixliu (console)` | Create matching AD account or ignore |
| Service accounts | `ntservice` | Generally ignored (system accounts) |
| Local accounts | `Administrator` | N/A - no AD correlation |
| Azure AD format | `AzureAD\User` | May need username normalization enhancement |

## API Notes

- Report mode makes read-only API calls (safe to run anytime)
- Sync mode updates custom fields via `PATCH /device/{id}/custom-fields`
- Rate limiting prevents API throttling (default 0.5s between calls)
- Both NinjaOne and Azure AD credentials required
- Azure AD queries use `User.Read.All` permission

## Troubleshooting

### Low Match Rate
1. Check AD user list includes expected accounts
2. Verify username format consistency
3. Review unmatched list for patterns

### Import Errors
If you see `cannot import name` errors:
- Both NinjaOne and Azure AD APIs have `auth.py` files
- The script handles this automatically via sys.modules manipulation
- Ensure both plugin directories exist

### Custom Field Errors
If sync fails with field errors:
1. Verify custom fields exist in NinjaOne Admin
2. Check field names match CLI arguments exactly
3. Ensure fields are device-level (not org-level)
