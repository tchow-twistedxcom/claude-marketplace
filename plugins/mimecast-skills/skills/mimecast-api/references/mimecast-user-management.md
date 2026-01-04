# Mimecast User & Group Management Reference

## User Operations

### List Internal Users

List all internal users in the Mimecast directory.

```bash
# List all users
python3 scripts/mimecast_api.py users list

# Filter by domain
python3 scripts/mimecast_api.py users list --domain example.com

# JSON output
python3 scripts/mimecast_api.py users list --output json
```

**API Endpoint:** `POST /api/user/get-internal-users`

**Response Fields:**
| Field | Description |
|-------|-------------|
| `emailAddress` | User's email address |
| `name` | Display name |
| `domain` | Email domain |
| `internal` | Internal user flag |
| `created` | Creation timestamp |

### Create User

Create a new internal user.

```bash
# Create with email only
python3 scripts/mimecast_api.py users create --email user@example.com

# Create with name
python3 scripts/mimecast_api.py users create --email user@example.com --name "John Doe"

# Create with domain
python3 scripts/mimecast_api.py users create --email user@example.com --name "John Doe" --domain example.com
```

**API Endpoint:** `POST /api/user/create-internal-user`

### Update User

Update an existing internal user.

```bash
# Update name
python3 scripts/mimecast_api.py users update --email user@example.com --name "Jane Doe"

# Add email alias
python3 scripts/mimecast_api.py users update --email user@example.com --alias alias@example.com
```

**API Endpoint:** `POST /api/user/update-internal-user`

### Delete User

Delete an internal user.

```bash
python3 scripts/mimecast_api.py users delete --email user@example.com
```

**API Endpoint:** `POST /api/user/delete-internal-user`

---

## Group Operations

### List Groups

List all directory groups.

```bash
python3 scripts/mimecast_api.py groups list

# JSON output
python3 scripts/mimecast_api.py groups list --output json
```

**API Endpoint:** `POST /api/directory/get-groups`

**Response Fields:**
| Field | Description |
|-------|-------------|
| `id` | Group ID |
| `description` | Group name/description |
| `source` | Directory source |
| `folderCount` | Number of folders |

### Create Group

Create a new directory group.

```bash
python3 scripts/mimecast_api.py groups create --description "Sales Team"
python3 scripts/mimecast_api.py groups create --description "Engineering Department"
```

**API Endpoint:** `POST /api/directory/create-group`

### Add Group Member

Add a user to a group.

```bash
python3 scripts/mimecast_api.py groups add-member --group GROUP_ID --email user@example.com
```

**API Endpoint:** `POST /api/directory/add-group-member`

### Remove Group Member

Remove a user from a group.

```bash
python3 scripts/mimecast_api.py groups remove-member --group GROUP_ID --email user@example.com
```

**API Endpoint:** `POST /api/directory/remove-group-member`

---

## Common Workflows

### Onboard New Employee

```bash
# 1. Create user
python3 scripts/mimecast_api.py users create \
    --email newuser@company.com \
    --name "New Employee"

# 2. Add to appropriate groups
python3 scripts/mimecast_api.py groups add-member \
    --group DEPT_GROUP_ID \
    --email newuser@company.com

python3 scripts/mimecast_api.py groups add-member \
    --group ALL_STAFF_GROUP_ID \
    --email newuser@company.com
```

### Offboard Employee

```bash
# 1. Remove from all groups
python3 scripts/mimecast_api.py groups remove-member \
    --group GROUP_ID \
    --email user@company.com

# 2. Delete user
python3 scripts/mimecast_api.py users delete --email user@company.com
```

### Bulk User Export

```bash
# Export all users to JSON
python3 scripts/mimecast_api.py users list --output json > users_export.json

# Filter by domain and export
python3 scripts/mimecast_api.py users list --domain example.com --output json > domain_users.json
```

### Create Department Structure

```bash
# Create department groups
python3 scripts/mimecast_api.py groups create --description "Engineering"
python3 scripts/mimecast_api.py groups create --description "Sales"
python3 scripts/mimecast_api.py groups create --description "Marketing"
python3 scripts/mimecast_api.py groups create --description "Finance"

# List to get group IDs
python3 scripts/mimecast_api.py groups list --output json
```
