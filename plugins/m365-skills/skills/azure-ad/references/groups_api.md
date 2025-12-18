# Groups API Reference

Azure AD Group operations via Microsoft Graph API.

## Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List groups | GET | `/groups` |
| Get group | GET | `/groups/{id}` |
| Create group | POST | `/groups` |
| Update group | PATCH | `/groups/{id}` |
| Delete group | DELETE | `/groups/{id}` |
| List members | GET | `/groups/{id}/members` |
| Add member | POST | `/groups/{id}/members/$ref` |
| Remove member | DELETE | `/groups/{id}/members/{id}/$ref` |
| List owners | GET | `/groups/{id}/owners` |
| Add owner | POST | `/groups/{id}/owners/$ref` |
| Get parent groups | GET | `/groups/{id}/memberOf` |

## CLI Commands

### List Groups

```bash
# List all groups (default 100)
python3 azure_ad_api.py groups list

# List with custom page size
python3 azure_ad_api.py groups list --top 50

# Get all groups (auto-pagination)
python3 azure_ad_api.py groups list --all

# Filter security groups
python3 azure_ad_api.py groups list --filter "securityEnabled eq true"

# Filter Microsoft 365 groups
python3 azure_ad_api.py groups list --filter "groupTypes/any(c:c eq 'Unified')"

# Select specific fields
python3 azure_ad_api.py groups list --select "id,displayName,mail"

# Output as JSON
python3 azure_ad_api.py --format json groups list
```

### Get Group

```bash
# Get by Group ID
python3 azure_ad_api.py groups get GROUP_ID

# Get specific fields
python3 azure_ad_api.py groups get GROUP_ID --select "id,displayName,members"
```

### Search Groups

```bash
# Search by name
python3 azure_ad_api.py groups search "IT Team"

# Search with result limit
python3 azure_ad_api.py groups search "Admin" --top 10
```

### Create Group

```bash
# Create security group
python3 azure_ad_api.py groups create \
  --display-name "IT Admins" \
  --mail-nickname "it-admins" \
  --description "IT Administrators group" \
  --security

# Create Microsoft 365 group
python3 azure_ad_api.py groups create \
  --display-name "Project Alpha" \
  --mail-nickname "project-alpha" \
  --description "Project Alpha team" \
  --m365
```

### Update Group

```bash
# Update description
python3 azure_ad_api.py groups update GROUP_ID \
  --data '{"description": "Updated description"}'

# Update display name
python3 azure_ad_api.py groups update GROUP_ID \
  --data '{"displayName": "New Group Name"}'
```

### Delete Group

```bash
# Delete requires confirmation flag
python3 azure_ad_api.py groups delete GROUP_ID --confirm
```

### Member Management

```bash
# List all members
python3 azure_ad_api.py groups members GROUP_ID

# List all members with pagination
python3 azure_ad_api.py groups members GROUP_ID --all

# Add member (user or group ID)
python3 azure_ad_api.py groups add-member GROUP_ID USER_ID

# Remove member
python3 azure_ad_api.py groups remove-member GROUP_ID USER_ID
```

### Owner Management

```bash
# List owners
python3 azure_ad_api.py groups owners GROUP_ID

# Add owner
python3 azure_ad_api.py groups add-owner GROUP_ID USER_ID
```

### Group Relationships

```bash
# Get parent groups (nested group membership)
python3 azure_ad_api.py groups member-of GROUP_ID
```

## Group Types

| Type | mailEnabled | securityEnabled | groupTypes |
|------|-------------|-----------------|------------|
| Security | false | true | [] |
| Mail-enabled Security | true | true | [] |
| Microsoft 365 | true | false | ["Unified"] |
| Distribution | true | false | [] |

## Group Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | String | Unique identifier (GUID) |
| `displayName` | String | Group name |
| `description` | String | Group description |
| `mail` | String | Email address |
| `mailEnabled` | Boolean | Mail-enabled |
| `mailNickname` | String | Mail alias |
| `securityEnabled` | Boolean | Security group |
| `groupTypes` | Array | ["Unified"] for M365 |
| `visibility` | String | Public/Private |
| `membershipRule` | String | Dynamic membership rule |
| `createdDateTime` | DateTime | Creation date |

## OData Filter Examples

```bash
# Security groups only
--filter "securityEnabled eq true"

# Mail-enabled groups
--filter "mailEnabled eq true"

# Microsoft 365 groups
--filter "groupTypes/any(c:c eq 'Unified')"

# Dynamic groups
--filter "membershipRuleProcessingState eq 'On'"

# Name starts with
--filter "startswith(displayName, 'Project')"

# Contains mail
--filter "mail ne null"

# Multiple conditions
--filter "securityEnabled eq true and mailEnabled eq false"
```

## Dynamic Group Membership Rules

Dynamic groups use membership rules to automatically add/remove members.

Example rules:
```
# All users in Engineering department
user.department -eq "Engineering"

# All users with Manager title
user.jobTitle -contains "Manager"

# All devices running Windows
device.operatingSystem -eq "Windows"

# Users in specific location
user.country -eq "United States"
```

## Required Permissions

| Operation | Permission |
|-----------|------------|
| List/Get | `Group.Read.All` |
| Create/Update/Delete | `Group.ReadWrite.All` |
| Manage members | `Group.ReadWrite.All` or `GroupMember.ReadWrite.All` |
