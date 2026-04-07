# Security & Incident Response API Reference

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auditLogs/signIns` | List sign-in logs |
| GET | `/auditLogs/signIns/{id}` | Get specific sign-in event |
| GET | `/identityProtection/riskDetections` | List risk detections |
| GET | `/identityProtection/riskyUsers` | List risky users |
| GET | `/identityProtection/riskyUsers/{id}/history` | Get user risk history |
| GET | `/auditLogs/directoryAudits` | List directory audit logs |
| GET | `/users/{id}/authentication/methods` | Get user's auth methods |
| GET | `/identity/conditionalAccess/policies` | List CA policies |
| GET | `/identity/conditionalAccess/policies/{id}` | Get specific CA policy |
| GET | `/identity/conditionalAccess/namedLocations` | List named locations |
| POST | `/users/{id}/revokeSignInSessions` | Revoke all sessions |
| POST | `/identityProtection/riskyUsers/confirmCompromised` | Confirm compromise |
| POST | `/identityProtection/riskyUsers/dismiss` | Dismiss risk |

## CLI Commands

### Sign-In Logs

```bash
# Recent sign-ins (last 24 hours)
python3 azure_ad_api.py security sign-ins --hours 24

# Failed sign-ins for a specific user
python3 azure_ad_api.py security sign-ins --user "user@domain.com" --status failure --days 7

# High-risk sign-ins in the last 48 hours
python3 azure_ad_api.py security sign-ins --risk high --hours 48

# Sign-ins from a specific app, JSON output
python3 azure_ad_api.py --format json security sign-ins --app "Microsoft Azure Management" --hours 24

# Get a specific sign-in event
python3 azure_ad_api.py security sign-in-get EVENT_ID

# Non-interactive sign-ins (token refresh, background)
python3 azure_ad_api.py security sign-ins --filter "signInEventTypes/any(t: t eq 'nonInteractiveUser')" --hours 24

# Service principal sign-ins
python3 azure_ad_api.py security sign-ins --filter "signInEventTypes/any(t: t eq 'servicePrincipal')" --hours 24
```

### Risk Detections

```bash
# All high-risk detections
python3 azure_ad_api.py security risk-detections --risk-level high

# Risk detections for a specific user
python3 azure_ad_api.py security risk-detections --user "user@domain.com"

# Unresolved risk detections in the last 7 days
python3 azure_ad_api.py security risk-detections --filter "riskState eq 'atRisk'" --days 7
```

### Risky Users

```bash
# All currently at-risk users
python3 azure_ad_api.py security risky-users --state atRisk

# High-risk users
python3 azure_ad_api.py security risky-users --risk-level high

# Users confirmed as compromised
python3 azure_ad_api.py security risky-users --state confirmedCompromised

# Risk history for a specific user
python3 azure_ad_api.py security risky-user-history USER_OBJECT_ID
```

### Audit Logs

```bash
# Recent audit activity (last 72 hours)
python3 azure_ad_api.py security audit-logs --hours 72

# Password reset activity
python3 azure_ad_api.py security audit-logs --filter "activityDisplayName eq 'Reset user password'" --days 7

# Role assignment changes
python3 azure_ad_api.py security audit-logs --category RoleManagement --days 30

# Failed audit events
python3 azure_ad_api.py security audit-logs --result failure --days 7

# Activity initiated by a specific user (use raw filter)
python3 azure_ad_api.py security audit-logs --filter "initiatedBy/user/id eq 'USER_OBJECT_ID'" --days 7
```

### Authentication Methods

```bash
# Check a user's enrolled MFA methods
python3 azure_ad_api.py security auth-methods "user@domain.com"
python3 azure_ad_api.py security auth-methods USER_OBJECT_ID
```

### Conditional Access

```bash
# List all enabled policies
python3 azure_ad_api.py security ca-policies --state enabled

# Get all policies (including report-only)
python3 azure_ad_api.py security ca-policies

# Get a specific policy's full configuration
python3 azure_ad_api.py --format json security ca-policy-get POLICY_ID

# List named locations (trusted networks)
python3 azure_ad_api.py security named-locations
python3 azure_ad_api.py --format json security named-locations
```

### Incident Response Actions

```bash
# Revoke all sessions (invalidates all refresh tokens immediately)
python3 azure_ad_api.py security revoke-sessions "user@domain.com" --confirm

# Confirm a user as compromised (sets risk to high, forces CA risk policies)
python3 azure_ad_api.py security confirm-compromised USER_OBJECT_ID --confirm

# Confirm multiple users as compromised
python3 azure_ad_api.py security confirm-compromised "ID1,ID2,ID3" --confirm

# Dismiss risk after remediation (sets risk to none)
python3 azure_ad_api.py security dismiss-risk USER_OBJECT_ID --confirm
```

## Entity Properties

### Sign-In Event (`signIn`)

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Unique sign-in event ID |
| `createdDateTime` | datetime | When the sign-in occurred |
| `userPrincipalName` | string | User who signed in |
| `userId` | string | User object ID |
| `appDisplayName` | string | Application accessed |
| `ipAddress` | string | Source IP address |
| `location` | object | `city`, `state`, `countryOrRegion`, `geoCoordinates` |
| `status` | object | `errorCode` (0=success), `failureReason`, `additionalDetails` |
| `clientAppUsed` | string | e.g., "Browser", "Mobile Apps and Desktop clients" |
| `isInteractive` | boolean | Whether user interaction was required |
| `riskLevelDuringSignIn` | string | `none`, `low`, `medium`, `high` |
| `riskLevelAggregated` | string | Aggregated risk level |
| `riskState` | string | `none`, `atRisk`, `confirmedCompromised`, `remediated` |
| `conditionalAccessStatus` | string | `success`, `failure`, `notApplied` |
| `appliedConditionalAccessPolicies` | array | Policies evaluated with their results |
| `deviceDetail` | object | `operatingSystem`, `browser`, `isCompliant`, `isManaged`, `trustType` |
| `signInEventTypes` | array | `interactiveUser`, `nonInteractiveUser`, `servicePrincipal`, `managedIdentity` |
| `correlationId` | string | For cross-referencing with audit logs |

### Risk Detection (`riskDetection`)

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Detection ID |
| `requestId` | string | Sign-in request ID |
| `correlationId` | string | For cross-referencing |
| `riskEventType` | string | e.g., `unfamiliarFeatures`, `anonymizedIPAddress`, `leakedCredentials`, `impossibleTravel`, `maliciousIPAddress` |
| `riskLevel` | string | `low`, `medium`, `high`, `hidden`, `none` |
| `riskState` | string | `atRisk`, `confirmedCompromised`, `remediated`, `dismissed`, `confirmedSafe` |
| `riskDetail` | string | Reason for current state |
| `detectionTimingType` | string | `realtime`, `nearRealtime`, `offline` |
| `activity` | string | `signin` or `user` |
| `ipAddress` | string | Source IP of risky activity |
| `location` | object | `city`, `state`, `countryOrRegion` |
| `activityDateTime` | datetime | When the risky activity occurred |
| `userId` | string | Affected user object ID |
| `userPrincipalName` | string | Affected user UPN |
| `additionalInfo` | string | JSON string with extra details (userAgent, etc.) |

### Risky User (`riskyUser`)

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | User object ID |
| `userDisplayName` | string | User display name |
| `userPrincipalName` | string | User UPN |
| `riskLevel` | string | `low`, `medium`, `high`, `hidden`, `none` |
| `riskState` | string | `none`, `confirmedSafe`, `remediated`, `dismissed`, `atRisk`, `confirmedCompromised` |
| `riskDetail` | string | Reason for current risk state |
| `riskLastUpdatedDateTime` | datetime | Last risk assessment |
| `isDeleted` | boolean | Whether user account is deleted |

### Directory Audit Log (`directoryAudit`)

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Audit event ID |
| `activityDisplayName` | string | Human-readable action (e.g., "Reset user password", "Add member to group") |
| `activityDateTime` | datetime | When the action occurred |
| `category` | string | `UserManagement`, `GroupManagement`, `RoleManagement`, `ApplicationManagement`, `Policy` |
| `result` | string | `success`, `failure` |
| `resultReason` | string | Description of result |
| `correlationId` | string | For cross-referencing with sign-in logs |
| `loggedByService` | string | e.g., "Core Directory", "PIM", "Self-service Password Management" |
| `operationType` | string | `Update`, `Add`, `Delete` |
| `initiatedBy` | object | `user.id`, `user.displayName`, `user.userPrincipalName`, `user.ipAddress` / `app.appId`, `app.displayName` |
| `targetResources` | array | Affected resources with `id`, `displayName`, `type`, `modifiedProperties` |

### Conditional Access Policy (`conditionalAccessPolicy`)

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Policy ID |
| `displayName` | string | Policy name |
| `state` | string | `enabled`, `disabled`, `enabledForReportingButNotEnforced` |
| `createdDateTime` | datetime | Policy creation time |
| `modifiedDateTime` | datetime | Last modification (check during incident) |
| `conditions.users` | object | `includeUsers`, `excludeUsers`, `includeGroups`, `excludeGroups` |
| `conditions.signInRiskLevels` | array | Risk levels that trigger the policy |
| `conditions.userRiskLevels` | array | User risk levels that trigger the policy |
| `grantControls.builtInControls` | array | e.g., `["mfa"]`, `["block"]`, `["passwordChange"]` |
| `sessionControls.signInFrequency` | object | How often re-auth is required |

## OData Filter Examples

### Sign-In Logs

```
# Specific user
userPrincipalName eq 'user@contoso.com'

# Failed sign-ins
status/errorCode ne 0

# High risk only
riskLevelDuringSignIn eq 'high'

# From a specific IP
ipAddress eq '203.0.113.50'

# From a specific country
location/countryOrRegion eq 'RU'

# After a specific time
createdDateTime ge 2026-03-30T00:00:00Z

# Non-interactive (background) sign-ins
signInEventTypes/any(t: t eq 'nonInteractiveUser')

# Combined: failed + specific user + last 24h
userPrincipalName eq 'user@domain.com' and status/errorCode ne 0 and createdDateTime ge 2026-03-31T00:00:00Z
```

### Risky Users

```
# Users currently at risk
riskState eq 'atRisk'

# Confirmed compromised
riskState eq 'confirmedCompromised'

# High risk level
riskLevel eq 'high'
```

### Audit Logs

```
# By category
category eq 'RoleManagement'

# By activity
activityDisplayName eq 'Reset user password'

# By initiating user
initiatedBy/user/id eq 'USER_OBJECT_ID'

# By initiating app
initiatedBy/app/displayName eq 'Microsoft Azure AD'

# Time range
activityDateTime ge 2026-03-30T00:00:00Z
```

## Required Permissions

| Permission | Purpose | License |
|------------|---------|---------|
| `AuditLog.Read.All` | Sign-in logs, directory audits | Entra ID P1+ |
| `IdentityRiskEvent.Read.All` | Risk detections | Entra ID P1+ |
| `IdentityRiskyUser.ReadWrite.All` | Risky users + confirm/dismiss | Entra ID P2 |
| `User.RevokeSessions.All` | Session revocation | Any |
| `UserAuthenticationMethod.Read.All` | Authentication methods | Any |
| `Policy.Read.All` | CA policies + named locations | Any |

All are **Application permissions** — no user interaction required with the existing client credentials flow. Grant via Azure portal → App registrations → [your app] → API permissions → Add permission → Grant admin consent.

## Incident Response Playbook

### Phase 1: Detect — Identify Scope

```bash
# Check for high-risk sign-ins in last 24 hours
python3 azure_ad_api.py security sign-ins --hours 24 --risk high

# Check for users currently at risk
python3 azure_ad_api.py security risky-users --state atRisk

# Check for new high-risk detections
python3 azure_ad_api.py security risk-detections --risk-level high --hours 24
```

### Phase 2: Investigate — Understand What Happened

```bash
# Get all sign-ins for the suspect user (last 48h)
python3 azure_ad_api.py security sign-ins --user "user@domain.com" --hours 48

# Focus on failed sign-ins (password spray / brute force indicators)
python3 azure_ad_api.py security sign-ins --user "user@domain.com" --status failure --hours 48

# Check user's current auth methods (did attacker add new MFA?)
python3 azure_ad_api.py security auth-methods "user@domain.com"

# Review risk history
python3 azure_ad_api.py security risky-user-history USER_OBJECT_ID

# Check what directory changes the user made
python3 azure_ad_api.py security audit-logs \
  --filter "initiatedBy/user/id eq 'USER_OBJECT_ID'" --days 7

# Check what CA policies were in effect (was MFA enforced?)
python3 azure_ad_api.py security ca-policies --state enabled

# Check trusted named locations (did attacker sign in from a "trusted" IP?)
python3 azure_ad_api.py --format json security named-locations

# Cross-reference user's devices
python3 azure_ad_api.py users owned-devices "user@domain.com"

# Check privilege level
python3 azure_ad_api.py users member-of "user@domain.com"
```

### Phase 3: Contain — Stop the Threat

```bash
# Revoke all active sessions (invalidates all tokens)
python3 azure_ad_api.py security revoke-sessions "user@domain.com" --confirm

# Confirm as compromised (triggers risk-based CA policies — forces password change + MFA re-reg)
python3 azure_ad_api.py security confirm-compromised USER_OBJECT_ID --confirm

# Disable account if needed (most severe containment)
python3 azure_ad_api.py users update "user@domain.com" --data '{"accountEnabled": false}'
```

### Phase 4: Remediate — Clean Up and Restore

```bash
# After password reset and MFA re-registration, dismiss risk
python3 azure_ad_api.py security dismiss-risk USER_OBJECT_ID --confirm

# Re-enable account
python3 azure_ad_api.py users update "user@domain.com" --data '{"accountEnabled": true}'

# Verify no suspicious auth methods remain
python3 azure_ad_api.py security auth-methods "user@domain.com"

# Final: check user shows as remediated
python3 azure_ad_api.py security risky-users \
  --filter "userPrincipalName eq 'user@domain.com'"
```

### Notes

- **`revokeSignInSessions` has a ~2 minute propagation delay** before tokens are actually invalidated.
- **`confirmCompromised` + risk-based CA** is more powerful than just revoking sessions — it forces password change through policy.
- **Sign-in log retention**: 30 days (P1/P2 license), 7 days (free/basic).
- **`auditLogs/signIns` default** only returns interactive user sign-ins. Use `signInEventTypes` filter for service principal / non-interactive.
- **`identityProtection/riskyUsers`** requires Entra ID P2. The endpoint will return HTTP 403 if your tenant only has P1.
