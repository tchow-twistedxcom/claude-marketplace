# Ticketing API Reference

Ticket management and service desk operations.

## Endpoints

### List Tickets
```bash
python ninjaone_api.py tickets list [--status STATUS] [--priority PRIORITY] [--org-id ORG_ID]
```

**Parameters:**
- `--status`: Filter by status name
- `--priority`: Filter by priority name
- `--org-id`: Filter by organization

**Example:**
```bash
python ninjaone_api.py tickets list --status "Open" --priority "High"
```

### Get Ticket
```bash
python ninjaone_api.py tickets get TICKET_ID
```

Get ticket details by ID.

### Create Ticket
```bash
python ninjaone_api.py tickets create --org-id ORG_ID --subject SUBJECT --description DESC [--priority PRIORITY] [--type TYPE] [--device-id ID]
```

**Parameters:**
- `--org-id`: Organization ID (required)
- `--subject`: Ticket subject (required)
- `--description`: Ticket description (required)
- `--priority`: Priority name or ID
- `--type`: Ticket type name or ID
- `--device-id`: Associated device ID

**Example:**
```bash
python ninjaone_api.py tickets create \
  --org-id 123 \
  --subject "Server Offline" \
  --description "Production server not responding to pings" \
  --priority "Critical" \
  --device-id 12345
```

### Update Ticket
```bash
python ninjaone_api.py tickets update TICKET_ID [--status STATUS] [--priority PRIORITY] [--assignee EMAIL]
```

**Parameters:**
- `--status`: New status name or ID
- `--priority`: New priority name or ID
- `--assignee`: Assignee email address

### Delete Ticket
```bash
python ninjaone_api.py tickets delete TICKET_ID
```

Delete a ticket (requires permission).

### Add Comment
```bash
python ninjaone_api.py tickets add-comment TICKET_ID --comment TEXT [--public]
```

**Parameters:**
- `--comment`: Comment text (required)
- `--public`: Make comment visible to end users

### Ticket Log
```bash
python ninjaone_api.py tickets log TICKET_ID
```

Get ticket activity history.

### List Statuses
```bash
python ninjaone_api.py tickets statuses
```

Get available ticket statuses.

### List Attributes
```bash
python ninjaone_api.py tickets attributes
```

Get ticket form attributes (types, priorities, etc.).

## Response Fields

### Ticket Object
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Ticket ID |
| `subject` | string | Ticket subject |
| `description` | string | Description |
| `status` | object | Status (id, name) |
| `priority` | object | Priority (id, name) |
| `type` | object | Type (id, name) |
| `clientId` | integer | Organization ID |
| `deviceId` | integer | Associated device |
| `assignee` | object | Assigned user |
| `createTime` | timestamp | Creation time |
| `lastUpdated` | timestamp | Last update |

### Comment Object
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Comment ID |
| `body` | string | Comment text |
| `public` | boolean | End-user visible |
| `author` | object | Comment author |
| `createTime` | timestamp | Creation time |

### Log Entry Object
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Entry ID |
| `type` | string | Entry type |
| `description` | string | Activity description |
| `user` | object | User who made change |
| `timestamp` | timestamp | Activity time |

## Common Workflows

### Incident Management
```bash
# Create incident ticket
python ninjaone_api.py tickets create \
  --org-id 123 \
  --subject "Network Outage" \
  --description "Multiple devices offline in building A" \
  --priority "Critical"

# Get ticket ID from response, then add updates
python ninjaone_api.py tickets add-comment 456 --comment "Investigating root cause"

# Update status as work progresses
python ninjaone_api.py tickets update 456 --status "In Progress"

# Close when resolved
python ninjaone_api.py tickets update 456 --status "Resolved"
python ninjaone_api.py tickets add-comment 456 --comment "Root cause: Switch failure. Replaced switch." --public
```

### Alert-to-Ticket Workflow
```bash
# Get critical alerts
python ninjaone_api.py alerts list --severity CRITICAL

# Create ticket for alert
python ninjaone_api.py tickets create \
  --org-id 123 \
  --subject "Critical Alert: Disk Space Low" \
  --description "Device 12345 disk space below threshold" \
  --device-id 12345 \
  --priority "High"

# Reset the alert
python ninjaone_api.py alerts reset ALERT_UID
```

### Ticket Reporting
```bash
# List all open tickets
python ninjaone_api.py tickets list --status "Open" --format table

# Export tickets by organization
python ninjaone_api.py tickets list --org-id 123 --format json > org_tickets.json

# Count tickets by status
python ninjaone_api.py tickets list --format summary
```

### Ticket Assignment
```bash
# Get ticket details
python ninjaone_api.py tickets get 456

# Assign to technician
python ninjaone_api.py tickets update 456 --assignee "tech@company.com"

# Add assignment note
python ninjaone_api.py tickets add-comment 456 --comment "Assigned to John for investigation"
```

## Status and Priority Values

### Common Statuses
- Open
- In Progress
- Pending
- Resolved
- Closed

### Common Priorities
- Critical
- High
- Medium
- Low

**Note:** Actual values depend on your NinjaOne ticketing configuration.

## API Notes

- Ticket attributes (statuses, priorities, types) are customizable in NinjaOne
- Use `tickets attributes` to get available options
- Public comments are visible to end users via client portal
- Ticket deletion may be restricted based on permissions
- Device association links tickets to specific endpoints
