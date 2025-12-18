# Users API Reference

Users (also called "account shares" or "ashares") represent people with access to your Celigo account. The API supports listing, inviting, updating permissions, and removing users.

## Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List all | GET | `/ashares` |
| Get one | GET | `/ashares/{id}` |
| Invite user | POST | `/ashares` |
| Update permissions | PUT | `/ashares/{id}` |
| Remove user | DELETE | `/ashares/{id}` |

## User Object

```json
{
  "_id": "share123",
  "_sharedWithUserId": "user456",
  "accepted": true,
  "accessLevel": "manage",
  "integrationAccessLevel": [
    {
      "_integrationId": "int123",
      "accessLevel": "manage"
    },
    {
      "_integrationId": "int456",
      "accessLevel": "monitor"
    }
  ],
  "disabled": false,
  "dismissed": false,
  "sharedWithUser": {
    "_id": "user456",
    "email": "user@example.com",
    "name": "John Doe",
    "lastSignIn": "2024-01-15T10:00:00.000Z"
  },
  "createdAt": "2024-01-01T00:00:00.000Z",
  "lastModified": "2024-01-15T12:00:00.000Z"
}
```

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `_id` | string | Share unique identifier |
| `_sharedWithUserId` | string | User's system ID |
| `accepted` | boolean | Invitation accepted |
| `accessLevel` | string | Account-wide permission |
| `integrationAccessLevel` | array | Per-integration permissions |
| `disabled` | boolean | User access disabled |
| `dismissed` | boolean | User dismissed invitation |
| `sharedWithUser` | object | User profile details |
| `createdAt` | string | When access was granted |
| `lastModified` | string | Last permission update |

## Access Levels

| Level | Description |
|-------|-------------|
| `monitor` | Read-only access to view integrations and flows |
| `manage` | Read/write access to create and modify resources |
| `administrator` | Full administrative access to the account |

## Operations

### List All Users

```bash
curl -X GET "https://api.integrator.io/v1/ashares" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:**
```json
[
  {
    "_id": "share123",
    "accepted": true,
    "accessLevel": "manage",
    "sharedWithUser": {
      "email": "user1@example.com",
      "name": "John Doe"
    }
  },
  {
    "_id": "share456",
    "accepted": false,
    "accessLevel": "monitor",
    "sharedWithUser": {
      "email": "user2@example.com",
      "name": "Jane Smith"
    }
  }
]
```

### Get User Details

```bash
curl -X GET "https://api.integrator.io/v1/ashares/{share_id}" \
  -H "Authorization: Bearer $API_KEY"
```

### Invite User

```bash
curl -X POST "https://api.integrator.io/v1/ashares" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "accessLevel": "manage",
    "integrationAccessLevel": [
      {
        "_integrationId": "int123",
        "accessLevel": "manage"
      },
      {
        "_integrationId": "int456",
        "accessLevel": "monitor"
      }
    ]
  }'
```

**Response:**
```json
{
  "_id": "share789",
  "accepted": false,
  "accessLevel": "manage",
  "integrationAccessLevel": [...],
  "createdAt": "2024-01-15T10:00:00.000Z"
}
```

### Update Permissions

```bash
curl -X PUT "https://api.integrator.io/v1/ashares/{share_id}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "accessLevel": "administrator",
    "integrationAccessLevel": [
      {
        "_integrationId": "int123",
        "accessLevel": "manage"
      }
    ]
  }'
```

### Disable User

```bash
curl -X PUT "https://api.integrator.io/v1/ashares/{share_id}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "disabled": true
  }'
```

### Remove User

```bash
curl -X DELETE "https://api.integrator.io/v1/ashares/{share_id}" \
  -H "Authorization: Bearer $API_KEY"
```

**Response:** 204 No Content

## Permission Patterns

### Account-Wide Access

Grant same permissions to all integrations:

```json
{
  "email": "user@example.com",
  "accessLevel": "manage"
}
```

### Integration-Specific Access

Override account-wide permissions per integration:

```json
{
  "email": "user@example.com",
  "accessLevel": "monitor",
  "integrationAccessLevel": [
    {
      "_integrationId": "int123",
      "accessLevel": "manage"
    }
  ]
}
```

### Read-Only Access

```json
{
  "email": "viewer@example.com",
  "accessLevel": "monitor",
  "integrationAccessLevel": []
}
```

### Full Admin Access

```json
{
  "email": "admin@example.com",
  "accessLevel": "administrator"
}
```

## Common Operations

### Audit User Access

```python
def audit_user_access():
    users = api_get("/ashares").json()

    report = []
    for user in users:
        report.append({
            "email": user['sharedWithUser']['email'],
            "name": user['sharedWithUser'].get('name'),
            "accessLevel": user['accessLevel'],
            "accepted": user['accepted'],
            "disabled": user.get('disabled', False),
            "lastSignIn": user['sharedWithUser'].get('lastSignIn'),
            "integrationAccess": len(user.get('integrationAccessLevel', []))
        })

    return report
```

### Bulk Invite Users

```python
def bulk_invite(emails, access_level="monitor", integration_ids=None):
    results = []

    for email in emails:
        payload = {
            "email": email,
            "accessLevel": access_level
        }

        if integration_ids:
            payload["integrationAccessLevel"] = [
                {"_integrationId": iid, "accessLevel": access_level}
                for iid in integration_ids
            ]

        result = api_post("/ashares", payload)
        results.append({"email": email, "status": result.status_code})

    return results
```

### Revoke Integration Access

```python
def revoke_integration_access(share_id, integration_id):
    user = api_get(f"/ashares/{share_id}").json()

    # Remove specific integration
    new_access = [
        ia for ia in user.get('integrationAccessLevel', [])
        if ia['_integrationId'] != integration_id
    ]

    api_put(f"/ashares/{share_id}", {
        "integrationAccessLevel": new_access
    })
```

### Find Inactive Users

```python
from datetime import datetime, timedelta

def find_inactive_users(days=90):
    users = api_get("/ashares").json()
    cutoff = datetime.now() - timedelta(days=days)

    inactive = []
    for user in users:
        last_sign_in = user['sharedWithUser'].get('lastSignIn')
        if last_sign_in:
            sign_in_date = datetime.fromisoformat(last_sign_in.replace('Z', '+00:00'))
            if sign_in_date < cutoff:
                inactive.append({
                    "email": user['sharedWithUser']['email'],
                    "lastSignIn": last_sign_in,
                    "share_id": user['_id']
                })
        else:
            # Never signed in
            inactive.append({
                "email": user['sharedWithUser']['email'],
                "lastSignIn": None,
                "share_id": user['_id']
            })

    return inactive
```

### Transfer Ownership

```python
def transfer_integration_ownership(integration_id, from_share_id, to_share_id):
    # Remove from current owner
    from_user = api_get(f"/ashares/{from_share_id}").json()
    new_from_access = [
        ia for ia in from_user.get('integrationAccessLevel', [])
        if ia['_integrationId'] != integration_id
    ]
    api_put(f"/ashares/{from_share_id}", {"integrationAccessLevel": new_from_access})

    # Add to new owner
    to_user = api_get(f"/ashares/{to_share_id}").json()
    new_to_access = to_user.get('integrationAccessLevel', [])
    new_to_access.append({
        "_integrationId": integration_id,
        "accessLevel": "manage"
    })
    api_put(f"/ashares/{to_share_id}", {"integrationAccessLevel": new_to_access})
```

## Error Handling

### User Not Found
```json
{
  "errors": [{
    "code": "not_found",
    "message": "User share not found"
  }]
}
```

### Invalid Email
```json
{
  "errors": [{
    "code": "validation_error",
    "message": "Invalid email address format"
  }]
}
```

### Already Invited
```json
{
  "errors": [{
    "code": "conflict",
    "message": "User already has access to this account"
  }]
}
```

### Cannot Remove Self
```json
{
  "errors": [{
    "code": "forbidden",
    "message": "Cannot remove your own access"
  }]
}
```

## Best Practices

1. **Principle of least privilege** - Grant minimum required access
2. **Use integration-specific access** - Limit scope when possible
3. **Regular access reviews** - Audit user permissions periodically
4. **Disable before delete** - Disable inactive users before removing
5. **Document access grants** - Track why users have access
6. **Monitor sign-in activity** - Identify inactive accounts
