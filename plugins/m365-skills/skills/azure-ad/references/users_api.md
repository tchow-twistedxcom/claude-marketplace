# Users API Reference

Azure AD User operations via Microsoft Graph API.

## Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List users | GET | `/users` |
| Get user | GET | `/users/{id}` |
| Create user | POST | `/users` |
| Update user | PATCH | `/users/{id}` |
| Delete user | DELETE | `/users/{id}` |
| Get manager | GET | `/users/{id}/manager` |
| Get direct reports | GET | `/users/{id}/directReports` |
| Get memberships | GET | `/users/{id}/memberOf` |
| Get owned devices | GET | `/users/{id}/ownedDevices` |
| Get registered devices | GET | `/users/{id}/registeredDevices` |
| Assign license | POST | `/users/{id}/assignLicense` |

## CLI Commands

### List Users

```bash
# List all users (default 100)
python3 azure_ad_api.py users list

# List with custom page size
python3 azure_ad_api.py users list --top 50

# Get all users (auto-pagination)
python3 azure_ad_api.py users list --all

# Filter by department
python3 azure_ad_api.py users list --filter "department eq 'Engineering'"

# Filter enabled accounts only
python3 azure_ad_api.py users list --filter "accountEnabled eq true"

# Select specific fields
python3 azure_ad_api.py users list --select "id,displayName,mail,department"

# Output as JSON
python3 azure_ad_api.py --format json users list

# Export to CSV
python3 azure_ad_api.py --format csv users list > users.csv
```

### Get User

```bash
# Get by UPN (email)
python3 azure_ad_api.py users get "john.doe@company.com"

# Get by Object ID
python3 azure_ad_api.py users get "12345678-1234-1234-1234-123456789012"

# Get specific fields
python3 azure_ad_api.py users get USER_ID --select "id,displayName,jobTitle,manager"
```

### Search Users

```bash
# Search by name
python3 azure_ad_api.py users search "John"

# Search with result limit
python3 azure_ad_api.py users search "Smith" --top 10
```

### Create User

```bash
python3 azure_ad_api.py users create \
  --display-name "John Doe" \
  --upn "john.doe@company.com" \
  --mail-nickname "john.doe" \
  --password "TempPassword123!" \
  --force-change
```

### Update User

```bash
# Update job title
python3 azure_ad_api.py users update USER_ID \
  --data '{"jobTitle": "Senior Developer"}'

# Update department
python3 azure_ad_api.py users update "john.doe@company.com" \
  --data '{"department": "Engineering", "officeLocation": "Building A"}'

# Disable account
python3 azure_ad_api.py users update USER_ID \
  --data '{"accountEnabled": false}'
```

### Delete User

```bash
# Delete requires confirmation flag
python3 azure_ad_api.py users delete USER_ID --confirm
```

### User Relationships

```bash
# Get manager
python3 azure_ad_api.py users manager "john.doe@company.com"

# Get direct reports
python3 azure_ad_api.py users direct-reports "manager@company.com"

# Get group memberships
python3 azure_ad_api.py users member-of USER_ID

# Get owned devices
python3 azure_ad_api.py users owned-devices USER_ID

# Get registered devices
python3 azure_ad_api.py users registered-devices USER_ID
```

### License Management

```bash
# Assign license (use SKU ID from directory licenses)
python3 azure_ad_api.py users assign-license USER_ID \
  --sku-ids "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

# Assign multiple licenses
python3 azure_ad_api.py users assign-license USER_ID \
  --sku-ids "SKU_ID_1,SKU_ID_2"

# Revoke license
python3 azure_ad_api.py users revoke-license USER_ID \
  --sku-ids "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

## User Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Unique identifier (GUID) |
| `displayName` | String | Full name |
| `userPrincipalName` | String | Sign-in name (UPN) |
| `mail` | String | Email address |
| `givenName` | String | First name |
| `surname` | String | Last name |
| `jobTitle` | String | Job title |
| `department` | String | Department |
| `officeLocation` | String | Office location |
| `companyName` | String | Company name |
| `accountEnabled` | Boolean | Account status |
| `assignedLicenses` | Array | Assigned licenses |
| `createdDateTime` | DateTime | Creation date |
| `lastSignInDateTime` | DateTime | Last sign-in |

## OData Filter Examples

```bash
# By department
--filter "department eq 'Sales'"

# By job title
--filter "jobTitle eq 'Manager'"

# Account enabled
--filter "accountEnabled eq true"

# Name starts with
--filter "startswith(displayName, 'John')"

# Created after date
--filter "createdDateTime ge 2024-01-01T00:00:00Z"

# Multiple conditions
--filter "department eq 'IT' and accountEnabled eq true"
```

## Required Permissions

| Operation | Permission |
|-----------|------------|
| List/Get | `User.Read.All` |
| Create/Update/Delete | `User.ReadWrite.All` |
| Assign licenses | `User.ReadWrite.All` + `Directory.ReadWrite.All` |
