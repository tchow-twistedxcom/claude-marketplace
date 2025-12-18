# Devices API Reference

Azure AD Device operations via Microsoft Graph API.

## Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List devices | GET | `/devices` |
| Get device | GET | `/devices/{id}` |
| Update device | PATCH | `/devices/{id}` |
| Delete device | DELETE | `/devices/{id}` |
| Get registered owners | GET | `/devices/{id}/registeredOwners` |
| Get registered users | GET | `/devices/{id}/registeredUsers` |
| Get memberships | GET | `/devices/{id}/memberOf` |

## CLI Commands

### List Devices

```bash
# List all devices (default 100)
python3 azure_ad_api.py devices list

# List with custom page size
python3 azure_ad_api.py devices list --top 50

# Get all devices (auto-pagination)
python3 azure_ad_api.py devices list --all

# Filter Windows devices
python3 azure_ad_api.py devices list --filter "operatingSystem eq 'Windows'"

# Filter compliant devices
python3 azure_ad_api.py devices list --filter "isCompliant eq true"

# Filter managed devices
python3 azure_ad_api.py devices list --filter "isManaged eq true"

# Select specific fields
python3 azure_ad_api.py devices list --select "id,displayName,operatingSystem"

# Output as JSON
python3 azure_ad_api.py --format json devices list

# Export to CSV
python3 azure_ad_api.py --format csv devices list > devices.csv
```

### Get Device

```bash
# Get by Device ID
python3 azure_ad_api.py devices get DEVICE_ID

# Get specific fields
python3 azure_ad_api.py devices get DEVICE_ID \
  --select "id,displayName,operatingSystem,operatingSystemVersion"
```

### Search Devices

```bash
# Search by name
python3 azure_ad_api.py devices search "LAPTOP"

# Search with result limit
python3 azure_ad_api.py devices search "WIN" --top 10
```

### Update Device

```bash
# Update display name
python3 azure_ad_api.py devices update DEVICE_ID \
  --data '{"displayName": "New Device Name"}'

# Update account enabled
python3 azure_ad_api.py devices update DEVICE_ID \
  --data '{"accountEnabled": false}'
```

### Delete Device

```bash
# Delete requires confirmation flag
python3 azure_ad_api.py devices delete DEVICE_ID --confirm
```

### Device Relationships

```bash
# Get registered owners
python3 azure_ad_api.py devices registered-owners DEVICE_ID

# Get registered users
python3 azure_ad_api.py devices registered-users DEVICE_ID

# Get group memberships
python3 azure_ad_api.py devices member-of DEVICE_ID
```

## Device Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Unique identifier (GUID) |
| `deviceId` | String | Device identifier |
| `displayName` | String | Device name |
| `operatingSystem` | String | OS type (Windows, iOS, Android, MacOS) |
| `operatingSystemVersion` | String | OS version |
| `trustType` | String | Join type (AzureAd, ServerAd, Workplace) |
| `isManaged` | Boolean | MDM managed |
| `isCompliant` | Boolean | Compliance status |
| `isRooted` | Boolean | Rooted/jailbroken |
| `managementType` | String | Management type |
| `manufacturer` | String | Device manufacturer |
| `model` | String | Device model |
| `accountEnabled` | Boolean | Account status |
| `approximateLastSignInDateTime` | DateTime | Last activity |
| `registrationDateTime` | DateTime | Registration date |
| `profileType` | String | Profile type |

## Trust Types

| Trust Type | Description |
|------------|-------------|
| `AzureAd` | Azure AD joined |
| `ServerAd` | Hybrid Azure AD joined (domain joined) |
| `Workplace` | Azure AD registered (BYOD) |

## OData Filter Examples

```bash
# By operating system
--filter "operatingSystem eq 'Windows'"
--filter "operatingSystem eq 'iOS'"
--filter "operatingSystem eq 'Android'"
--filter "operatingSystem eq 'MacOS'"

# By compliance status
--filter "isCompliant eq true"
--filter "isCompliant eq false"

# By managed status
--filter "isManaged eq true"

# By trust type
--filter "trustType eq 'AzureAd'"
--filter "trustType eq 'ServerAd'"
--filter "trustType eq 'Workplace'"

# By account status
--filter "accountEnabled eq true"

# Name starts with
--filter "startswith(displayName, 'LAPTOP')"

# OS version contains
--filter "startswith(operatingSystemVersion, '10.0')"

# Active devices (recent sign-in)
--filter "approximateLastSignInDateTime ge 2024-01-01T00:00:00Z"

# Stale devices (no recent activity)
--filter "approximateLastSignInDateTime le 2023-06-01T00:00:00Z"

# Multiple conditions
--filter "operatingSystem eq 'Windows' and isManaged eq true and isCompliant eq true"
```

## Device Analysis Use Cases

### Find Stale Devices

```bash
# Devices inactive for 90+ days
python3 azure_ad_api.py devices list \
  --filter "approximateLastSignInDateTime le 2024-09-01T00:00:00Z" \
  --all
```

### Compliance Report

```bash
# Non-compliant devices
python3 azure_ad_api.py devices list \
  --filter "isCompliant eq false" \
  --format csv > non_compliant_devices.csv
```

### OS Inventory

```bash
# Windows devices
python3 azure_ad_api.py devices list \
  --filter "operatingSystem eq 'Windows'" \
  --select "displayName,operatingSystemVersion,isManaged" \
  --all
```

### Unmanaged Devices

```bash
# Azure AD joined but not MDM managed
python3 azure_ad_api.py devices list \
  --filter "trustType eq 'AzureAd' and isManaged eq false"
```

## Required Permissions

| Operation | Permission |
|-----------|------------|
| List/Get | `Device.Read.All` |
| Update/Delete | `Device.ReadWrite.All` |
| Read owners/users | `Device.Read.All` |
