# Organizations API Reference

Client/tenant management and organizational data.

## Endpoints

### List Organizations
```bash
python ninjaone_api.py organizations list [--page-size N]
```

List all organizations (clients/tenants).

### Get Organization
```bash
python ninjaone_api.py organizations get ORG_ID
```

Get organization details by ID.

### Create Organization
```bash
python ninjaone_api.py organizations create --name NAME [--description DESC]
```

Create a new organization.

### Update Organization
```bash
python ninjaone_api.py organizations update ORG_ID [--name NAME] [--description DESC]
```

Update organization details.

### Organization Devices
```bash
python ninjaone_api.py organizations devices ORG_ID [--filter FILTER]
```

List all devices belonging to an organization.

### Organization Locations
```bash
python ninjaone_api.py organizations locations ORG_ID
```

List locations defined for an organization.

### Organization End Users
```bash
python ninjaone_api.py organizations end-users ORG_ID
```

List end users associated with an organization.

### Custom Fields
```bash
# Get custom fields
python ninjaone_api.py organizations custom-fields ORG_ID

# Update custom fields
python ninjaone_api.py organizations custom-fields ORG_ID --set '{"fieldName": "value"}'
```

### Backup Usage
```bash
python ninjaone_api.py organizations backup-usage ORG_ID
```

Get backup storage usage for organization.

## Response Fields

### Organization Object
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Organization ID |
| `name` | string | Organization name |
| `description` | string | Description |
| `nodeApprovalMode` | string | Device approval mode |
| `deviceCount` | integer | Number of devices |
| `created` | timestamp | Creation date |
| `lastModified` | timestamp | Last modification |

### Location Object
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Location ID |
| `name` | string | Location name |
| `address` | string | Street address |
| `city` | string | City |
| `state` | string | State/province |
| `country` | string | Country |
| `postalCode` | string | Postal/ZIP code |

### End User Object
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | End user ID |
| `firstName` | string | First name |
| `lastName` | string | Last name |
| `email` | string | Email address |
| `phone` | string | Phone number |
| `organizationId` | integer | Organization ID |

## Common Workflows

### Create New Client
```bash
# Create organization
python ninjaone_api.py organizations create \
  --name "Acme Corp" \
  --description "New MSP client"

# Verify creation
python ninjaone_api.py organizations list --format json | jq '.[] | select(.name == "Acme Corp")'
```

### Audit Client Devices
```bash
# Get all devices for client
python ninjaone_api.py organizations devices 123

# Get servers only
python ninjaone_api.py organizations devices 123 --filter "class = WINDOWS_SERVER"

# Export to JSON
python ninjaone_api.py organizations devices 123 --format json > acme_devices.json
```

### Client Inventory Report
```bash
# List all clients with device counts
python ninjaone_api.py organizations list --format table

# Get detailed info for specific client
python ninjaone_api.py organizations get 123 --format json
```

## API Notes

- Organizations represent clients/tenants in MSP scenarios
- Device approval mode controls how new agents are handled
- Custom fields must be defined in NinjaOne admin before use
- Backup usage requires NinjaOne backup module enabled
