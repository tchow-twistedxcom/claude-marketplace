#!/usr/bin/env python3
"""
Azure AD / Entra ID API CLI.

Comprehensive CLI for Microsoft Graph API operations on Azure AD resources:
- Users: List, get, search, create, update, delete, memberships, licenses
- Groups: List, get, members, owners, add/remove members
- Devices: List, get, search, owners, registered users
- Directory: Organization info, domains, licenses, roles
- Security: Sign-in logs, risk detections, risky users, audit logs, auth methods
- Applications: App registrations, service principals, OAuth consent grants, guarded credential/SP writes
- Reports: MFA/auth-method registration report, Microsoft 365 usage reports
- Policy: Tenant security posture (authorization, security defaults, consent, cross-tenant)
- Calendar: User calendar events, calendar view, calendars
- Threat: Threat assessment requests, Microsoft Defender Threat Intelligence

Usage:
    python azure_ad_api.py users list
    python azure_ad_api.py users get "user@domain.com"
    python azure_ad_api.py groups members GROUP_ID
    python azure_ad_api.py --format json users list
    python azure_ad_api.py -t prod devices list
    python azure_ad_api.py security sign-ins --hours 24
    python azure_ad_api.py security risky-users --risk-level high
    python azure_ad_api.py applications oauth-grants --all
    python azure_ad_api.py reports mfa-registration --filter "isMfaRegistered eq false" --all
    python azure_ad_api.py policy posture
    python azure_ad_api.py threat assessments
"""

import argparse
import csv
import getpass
import io
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from auth import AzureAuth, AuthError
from formatters import format_output, print_error, print_success, print_warning


def build_time_filter(
    field: str = "createdDateTime",
    hours: int | None = None,
    days: int | None = None,
    since: str | None = None,
) -> str | None:
    """
    Build an OData time filter string.

    Args:
        field: The datetime field to filter on (default: "createdDateTime")
        hours: Number of hours to look back from now
        days: Number of days to look back from now
        since: ISO 8601 datetime string to filter from

    Returns:
        OData filter string like "createdDateTime ge 2026-04-06T00:00:00Z"
        or None if no time constraint is provided
    """
    if since:
        if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', since):
            raise ValueError(f"Invalid --since format (expected ISO 8601): {since!r}")
        return f"{field} ge {since}"
    if days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
        return f"{field} ge {cutoff_str}"
    if hours:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
        return f"{field} ge {cutoff_str}"
    return None


class GraphAPIError(Exception):
    """Graph API error."""
    pass


class AzureADAPI:
    """Azure AD API client using Microsoft Graph."""

    BASE_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self, tenant: str | None = None):
        """Initialize the API client."""
        self.auth = AzureAuth(tenant=tenant)
        self.config = self.auth.config

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        data: dict | None = None,
        headers: dict | None = None
    ) -> dict[str, Any]:
        """Make an authenticated request to Graph API."""
        url = f"{self.BASE_URL}{endpoint}"
        auth_headers = self.auth.get_auth_headers()

        if headers:
            auth_headers.update(headers)

        timeout = self.config.get('defaults', {}).get('timeout', 30)

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=auth_headers,
                params=params,
                json=data,
                timeout=timeout
            )

            # Handle no content responses
            if response.status_code == 204:
                return {"status": "success", "message": "Operation completed successfully"}

            response.raise_for_status()

            # Handle empty responses
            if not response.text:
                return {}

            return response.json()

        except requests.exceptions.HTTPError as e:
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = error_body.get('error', {}).get('message', str(e))
            except Exception:
                error_detail = e.response.text[:500] if e.response.text else str(e)

            raise GraphAPIError(f"API error ({e.response.status_code}): {error_detail}") from e

        except requests.exceptions.RequestException as e:
            raise GraphAPIError(f"Request failed: {e}") from e

    # Allowed base URL for @odata.nextLink validation (SSRF guard)
    GRAPH_BASE = "https://graph.microsoft.com/"

    def _get_all_pages(
        self,
        endpoint: str,
        params: dict | None = None,
        max_pages: int = 500
    ) -> list[dict]:
        """Get all pages of results."""
        all_items = []
        page_count = 0

        while endpoint and page_count < max_pages:
            if endpoint.startswith('http'):
                # Validate @odata.nextLink URL to prevent SSRF token exfiltration
                if not endpoint.startswith(self.GRAPH_BASE):
                    raise ValueError(
                        f"Unexpected nextLink host (possible SSRF): {endpoint[:100]}"
                    )
                try:
                    response = requests.get(
                        endpoint,
                        headers=self.auth.get_auth_headers(),
                        timeout=self.config.get('defaults', {}).get('timeout', 60)
                    )
                    response.raise_for_status()
                    result = response.json()
                except requests.exceptions.HTTPError as e:
                    error_detail = ""
                    try:
                        error_body = e.response.json()
                        error_detail = error_body.get('error', {}).get('message', str(e))
                    except Exception:
                        error_detail = e.response.text[:500] if e.response.text else str(e)
                    raise GraphAPIError(f"API error ({e.response.status_code}): {error_detail}") from e
                except requests.exceptions.RequestException as e:
                    raise GraphAPIError(f"Request failed: {e}") from e
            else:
                result = self._request('GET', endpoint, params=params)

            items = result.get('value', [])
            all_items.extend(items)

            # Get next page link
            endpoint = result.get('@odata.nextLink')
            params = None  # nextLink includes all params
            page_count += 1

        if page_count >= max_pages and endpoint:
            print(
                f"WARNING: _get_all_pages hit max_pages={max_pages} — results are TRUNCATED",
                file=sys.stderr
            )

        return all_items

    # ========== USERS ==========

    def users_list(
        self,
        top: int = 100,
        select: str | None = None,
        filter_query: str | None = None,
        all_pages: bool = False
    ) -> dict:
        """List all users."""
        params = {"$top": top}

        if select:
            params["$select"] = select
        else:
            params["$select"] = "id,displayName,userPrincipalName,mail,jobTitle,department,accountEnabled"

        if filter_query:
            params["$filter"] = filter_query

        if all_pages:
            items = self._get_all_pages("/users", params)
            return {"value": items}

        return self._request('GET', '/users', params=params)

    def users_get(self, user_id: str, select: str | None = None) -> dict:
        """Get a specific user by ID or UPN."""
        params = {}
        if select:
            params["$select"] = select

        return self._request('GET', f'/users/{user_id}', params=params or None)

    def users_search(self, query: str, top: int = 25) -> dict:
        """Search users by displayName or mail."""
        safe_query = query.replace("'", "''")
        params = {
            "$top": top,
            "$filter": f"startswith(displayName,'{safe_query}') or startswith(mail,'{safe_query}')",
            "$select": "id,displayName,userPrincipalName,mail,jobTitle,department"
        }
        return self._request('GET', '/users', params=params)

    def users_create(self, user_data: dict) -> dict:
        """Create a new user."""
        required = ['displayName', 'mailNickname', 'userPrincipalName', 'passwordProfile']
        missing = [f for f in required if f not in user_data]
        if missing:
            raise GraphAPIError(f"Missing required fields: {missing}")

        return self._request('POST', '/users', data=user_data)

    def users_update(self, user_id: str, updates: dict) -> dict:
        """Update a user's properties."""
        return self._request('PATCH', f'/users/{user_id}', data=updates)

    def users_delete(self, user_id: str) -> dict:
        """Delete a user."""
        return self._request('DELETE', f'/users/{user_id}')

    def users_manager(self, user_id: str) -> dict:
        """Get user's manager."""
        return self._request('GET', f'/users/{user_id}/manager')

    def users_direct_reports(self, user_id: str) -> dict:
        """Get user's direct reports."""
        return self._request('GET', f'/users/{user_id}/directReports')

    def users_member_of(self, user_id: str) -> dict:
        """Get groups and roles the user is a member of."""
        return self._request('GET', f'/users/{user_id}/memberOf')

    def users_owned_devices(self, user_id: str) -> dict:
        """Get devices owned by the user."""
        return self._request('GET', f'/users/{user_id}/ownedDevices')

    def users_registered_devices(self, user_id: str) -> dict:
        """Get devices registered to the user."""
        return self._request('GET', f'/users/{user_id}/registeredDevices')

    def users_assign_license(self, user_id: str, sku_ids: list[str]) -> dict:
        """Assign licenses to a user."""
        data = {
            "addLicenses": [{"skuId": sku_id} for sku_id in sku_ids],
            "removeLicenses": []
        }
        return self._request('POST', f'/users/{user_id}/assignLicense', data=data)

    def users_revoke_license(self, user_id: str, sku_ids: list[str]) -> dict:
        """Remove licenses from a user."""
        data = {
            "addLicenses": [],
            "removeLicenses": sku_ids
        }
        return self._request('POST', f'/users/{user_id}/assignLicense', data=data)

    # ========== GROUPS ==========

    def groups_list(
        self,
        top: int = 100,
        select: str | None = None,
        filter_query: str | None = None,
        all_pages: bool = False
    ) -> dict:
        """List all groups."""
        params = {"$top": top}

        if select:
            params["$select"] = select
        else:
            params["$select"] = "id,displayName,mail,groupTypes,securityEnabled,mailEnabled,description"

        if filter_query:
            params["$filter"] = filter_query

        if all_pages:
            items = self._get_all_pages("/groups", params)
            return {"value": items}

        return self._request('GET', '/groups', params=params)

    def groups_get(self, group_id: str, select: str | None = None) -> dict:
        """Get a specific group."""
        params = {}
        if select:
            params["$select"] = select

        return self._request('GET', f'/groups/{group_id}', params=params or None)

    def groups_search(self, query: str, top: int = 25) -> dict:
        """Search groups by displayName."""
        safe_query = query.replace("'", "''")
        params = {
            "$top": top,
            "$filter": f"startswith(displayName,'{safe_query}')",
            "$select": "id,displayName,mail,groupTypes,description"
        }
        return self._request('GET', '/groups', params=params)

    def groups_create(self, group_data: dict) -> dict:
        """Create a new group."""
        required = ['displayName', 'mailEnabled', 'mailNickname', 'securityEnabled']
        missing = [f for f in required if f not in group_data]
        if missing:
            raise GraphAPIError(f"Missing required fields: {missing}")

        return self._request('POST', '/groups', data=group_data)

    def groups_update(self, group_id: str, updates: dict) -> dict:
        """Update a group's properties."""
        return self._request('PATCH', f'/groups/{group_id}', data=updates)

    def groups_delete(self, group_id: str) -> dict:
        """Delete a group."""
        return self._request('DELETE', f'/groups/{group_id}')

    def groups_members(self, group_id: str, all_pages: bool = False) -> dict:
        """List group members."""
        if all_pages:
            items = self._get_all_pages(f"/groups/{group_id}/members")
            return {"value": items}

        return self._request('GET', f'/groups/{group_id}/members')

    def groups_add_member(self, group_id: str, member_id: str) -> dict:
        """Add a member to a group."""
        data = {
            "@odata.id": f"{self.BASE_URL}/directoryObjects/{member_id}"
        }
        return self._request('POST', f'/groups/{group_id}/members/$ref', data=data)

    def groups_remove_member(self, group_id: str, member_id: str) -> dict:
        """Remove a member from a group."""
        return self._request('DELETE', f'/groups/{group_id}/members/{member_id}/$ref')

    def groups_owners(self, group_id: str) -> dict:
        """List group owners."""
        return self._request('GET', f'/groups/{group_id}/owners')

    def groups_add_owner(self, group_id: str, owner_id: str) -> dict:
        """Add an owner to a group."""
        data = {
            "@odata.id": f"{self.BASE_URL}/directoryObjects/{owner_id}"
        }
        return self._request('POST', f'/groups/{group_id}/owners/$ref', data=data)

    def groups_member_of(self, group_id: str) -> dict:
        """Get groups this group is a member of."""
        return self._request('GET', f'/groups/{group_id}/memberOf')

    # ========== DEVICES ==========

    def devices_list(
        self,
        top: int = 100,
        select: str | None = None,
        filter_query: str | None = None,
        all_pages: bool = False
    ) -> dict:
        """List all devices."""
        params = {"$top": top}

        if select:
            params["$select"] = select
        else:
            params["$select"] = "id,displayName,operatingSystem,operatingSystemVersion,trustType,isManaged,isCompliant,approximateLastSignInDateTime"

        if filter_query:
            params["$filter"] = filter_query

        if all_pages:
            items = self._get_all_pages("/devices", params)
            return {"value": items}

        return self._request('GET', '/devices', params=params)

    def devices_get(self, device_id: str, select: str | None = None) -> dict:
        """Get a specific device."""
        params = {}
        if select:
            params["$select"] = select

        return self._request('GET', f'/devices/{device_id}', params=params or None)

    def devices_search(self, query: str, top: int = 25) -> dict:
        """Search devices by displayName."""
        safe_query = query.replace("'", "''")
        params = {
            "$top": top,
            "$filter": f"startswith(displayName,'{safe_query}')",
            "$select": "id,displayName,operatingSystem,operatingSystemVersion,trustType,isManaged"
        }
        return self._request('GET', '/devices', params=params)

    def devices_update(self, device_id: str, updates: dict) -> dict:
        """Update a device's properties."""
        return self._request('PATCH', f'/devices/{device_id}', data=updates)

    def devices_delete(self, device_id: str) -> dict:
        """Delete a device."""
        return self._request('DELETE', f'/devices/{device_id}')

    def devices_registered_owners(self, device_id: str) -> dict:
        """Get device's registered owners."""
        return self._request('GET', f'/devices/{device_id}/registeredOwners')

    def devices_registered_users(self, device_id: str) -> dict:
        """Get device's registered users."""
        return self._request('GET', f'/devices/{device_id}/registeredUsers')

    def devices_member_of(self, device_id: str) -> dict:
        """Get groups the device is a member of."""
        return self._request('GET', f'/devices/{device_id}/memberOf')

    # ========== DIRECTORY ==========

    def directory_organization(self) -> dict:
        """Get organization information."""
        return self._request('GET', '/organization')

    def directory_domains(self) -> dict:
        """List verified domains."""
        return self._request('GET', '/domains')

    def directory_licenses(self) -> dict:
        """List available licenses (subscribed SKUs)."""
        return self._request('GET', '/subscribedSkus')

    def directory_license_details(self, sku_id: str) -> dict:
        """Get license details."""
        return self._request('GET', f'/subscribedSkus/{sku_id}')

    def directory_roles(self) -> dict:
        """List directory roles."""
        return self._request('GET', '/directoryRoles')

    def directory_role_members(self, role_id: str) -> dict:
        """List members of a directory role."""
        return self._request('GET', f'/directoryRoles/{role_id}/members')

    def directory_deleted_users(self, top: int = 100) -> dict:
        """List deleted users."""
        params = {"$top": top}
        return self._request('GET', '/directory/deletedItems/microsoft.graph.user', params=params)

    def directory_restore_user(self, user_id: str) -> dict:
        """Restore a deleted user."""
        return self._request('POST', f'/directory/deletedItems/{user_id}/restore')

    # ========== SECURITY ==========

    def security_sign_ins(
        self,
        top: int = 100,
        filter_query: str | None = None,
        all_pages: bool = False,
    ) -> dict:
        """Fetch sign-in audit logs. Requires AuditLog.Read.All permission."""
        params: dict = {"$top": top, "$orderby": "createdDateTime desc"}
        if filter_query:
            params["$filter"] = filter_query
        if all_pages:
            items = self._get_all_pages("/auditLogs/signIns", params)
            return {"value": items, "@count": len(items)}
        return self._request('GET', '/auditLogs/signIns', params=params)

    def security_risk_detections(
        self,
        top: int = 100,
        filter_query: str | None = None,
        all_pages: bool = False,
    ) -> dict:
        """Fetch Identity Protection risk detections. Requires IdentityRiskEvent.Read.All."""
        params: dict = {"$top": top, "$orderby": "detectedDateTime desc"}
        if filter_query:
            params["$filter"] = filter_query
        if all_pages:
            items = self._get_all_pages("/identityProtection/riskDetections", params)
            return {"value": items, "@count": len(items)}
        return self._request('GET', '/identityProtection/riskDetections', params=params)

    def security_risky_users(
        self,
        top: int = 100,
        filter_query: str | None = None,
    ) -> dict:
        """Fetch risky users from Identity Protection. Requires IdentityRiskyUser.Read.All."""
        params: dict = {"$top": top}
        if filter_query:
            params["$filter"] = filter_query
        return self._request('GET', '/identityProtection/riskyUsers', params=params)

    def security_audit_logs(
        self,
        top: int = 100,
        filter_query: str | None = None,
        all_pages: bool = False,
    ) -> dict:
        """Fetch directory audit logs. Requires AuditLog.Read.All permission."""
        params: dict = {"$top": top, "$orderby": "activityDateTime desc"}
        if filter_query:
            params["$filter"] = filter_query
        if all_pages:
            items = self._get_all_pages("/auditLogs/directoryAudits", params)
            return {"value": items, "@count": len(items)}
        return self._request('GET', '/auditLogs/directoryAudits', params=params)

    def security_auth_methods(self, upn: str) -> dict:
        """Fetch authentication methods for a user. Requires UserAuthenticationMethod.Read.All."""
        return self._request('GET', f'/users/{upn}/authentication/methods')

    # ========== SHARED HELPERS (reports / credentials) ==========

    def _request_csv(self, endpoint: str, params: dict | None = None) -> str:
        """GET a Graph endpoint that returns CSV via a 302 redirect.

        Microsoft 365 usage reports respond with HTTP 302 pointing at a short-lived,
        pre-authenticated download URL that serves CSV. The redirect is followed manually
        WITHOUT the Authorization header so the bearer token is never sent to the storage
        host (the redirect target carries its own SAS token and needs no bearer).
        """
        url = f"{self.BASE_URL}{endpoint}"
        auth_headers = self.auth.get_auth_headers()
        timeout = self.config.get('defaults', {}).get('timeout', 60)
        try:
            response = requests.get(
                url, headers=auth_headers, params=params,
                timeout=timeout, allow_redirects=False,
            )
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get('Location')
                if not location:
                    raise GraphAPIError("Usage report redirect is missing a Location header")
                if not location.startswith('https://'):
                    raise ValueError(f"Refusing non-HTTPS report redirect: {location[:100]}")
                response = requests.get(location, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.exceptions.HTTPError as e:
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = error_body.get('error', {}).get('message', str(e))
            except Exception:
                error_detail = e.response.text[:500] if e.response.text else str(e)
            raise GraphAPIError(f"API error ({e.response.status_code}): {error_detail}") from e
        except requests.exceptions.RequestException as e:
            raise GraphAPIError(f"Request failed: {e}") from e

    @staticmethod
    def _parse_csv(text: str) -> list[dict]:
        """Parse a CSV string (with a header row) into a list of dict rows."""
        if not text or not text.strip():
            return []
        reader = csv.DictReader(io.StringIO(text))
        return [dict(row) for row in reader]

    @staticmethod
    def _add_days_ago(creds: list[dict] | None) -> list[dict]:
        """Annotate each credential with 'addedDaysAgo' computed from its startDateTime.

        Secrets or certificates added near a compromise window are a common
        attacker-persistence signal that survives password resets and session revocation.
        """
        now = datetime.now(timezone.utc)
        enriched: list[dict] = []
        for cred in creds or []:
            item = dict(cred)
            item['addedDaysAgo'] = None
            start = cred.get('startDateTime')
            if start:
                try:
                    dt = datetime.fromisoformat(str(start).replace('Z', '+00:00'))
                    item['addedDaysAgo'] = (now - dt).days
                except (ValueError, TypeError):
                    pass
            enriched.append(item)
        return enriched

    # ========== APPLICATIONS ==========

    def applications_apps_list(
        self,
        top: int = 50,
        all_pages: bool = False,
        include_credentials: bool = False,
    ) -> dict:
        """List app registrations. Requires Application.Read.All or Directory.Read.All."""
        select = "id,appId,displayName,signInAudience,createdDateTime,publisherDomain"
        if include_credentials:
            select += ",keyCredentials,passwordCredentials"
        params = {"$top": top, "$select": select}
        if all_pages:
            items = self._get_all_pages("/applications", params)
            return {"value": items, "@count": len(items)}
        return self._request('GET', '/applications', params=params)

    def applications_apps_get(self, app_object_id: str) -> dict:
        """Get a single application by object ID. Requires Application.Read.All."""
        return self._request('GET', f'/applications/{app_object_id}')

    def applications_apps_credentials(self, app_object_id: str) -> dict:
        """Return an application's key/password credentials with an 'addedDaysAgo' flag."""
        result = self._request(
            'GET', f'/applications/{app_object_id}',
            params={"$select": "appId,displayName,keyCredentials,passwordCredentials"},
        )
        return {
            "appId": result.get('appId'),
            "displayName": result.get('displayName'),
            "keyCredentials": self._add_days_ago(result.get('keyCredentials')),
            "passwordCredentials": self._add_days_ago(result.get('passwordCredentials')),
        }

    def applications_sp_list(self, top: int = 50, all_pages: bool = False) -> dict:
        """List service principals (enterprise apps). Requires Application.Read.All."""
        select = "id,appId,displayName,accountEnabled,servicePrincipalType,appRoleAssignmentRequired"
        params = {"$top": top, "$select": select}
        if all_pages:
            items = self._get_all_pages("/servicePrincipals", params)
            return {"value": items, "@count": len(items)}
        return self._request('GET', '/servicePrincipals', params=params)

    def applications_sp_get(self, sp_object_id: str) -> dict:
        """Get a single service principal by object ID. Requires Application.Read.All."""
        return self._request('GET', f'/servicePrincipals/{sp_object_id}')

    def applications_sp_app_roles(self, sp_object_id: str) -> dict:
        """List app-role assignments granted TO a service principal."""
        return self._request('GET', f'/servicePrincipals/{sp_object_id}/appRoleAssignedTo')

    def applications_oauth_grants(self, top: int = 200, all_pages: bool = False) -> dict:
        """List tenant-wide OAuth2 permission grants. Requires Directory.Read.All.

        Primary signal for illicit-consent-grant attacks.
        """
        params = {"$top": top}
        if all_pages:
            items = self._get_all_pages("/oauth2PermissionGrants", params)
            return {"value": items, "@count": len(items)}
        return self._request('GET', '/oauth2PermissionGrants', params=params)

    def applications_sp_set_enabled(self, sp_object_id: str, enabled: bool) -> dict:
        """Enable or disable a service principal. Requires Application.ReadWrite.All.

        Disabling (accountEnabled=false) immediately blocks the enterprise app from
        authenticating. Reversible by enabling again.
        """
        return self._request(
            'PATCH', f'/servicePrincipals/{sp_object_id}',
            data={"accountEnabled": enabled},
        )

    def applications_apps_remove_password(self, app_object_id: str, key_id: str) -> dict:
        """Remove a client secret (password credential) by keyId. Requires Application.ReadWrite.All."""
        return self._request(
            'POST', f'/applications/{app_object_id}/removePassword',
            data={"keyId": key_id},
        )

    def applications_apps_remove_key(self, app_object_id: str, key_id: str) -> dict:
        """Remove a certificate (key credential) by keyId. Requires Application.ReadWrite.All.

        Graph v1.0 has no single-key remove on /applications, so this fetches the current
        keyCredentials, drops the one matching key_id, and PATCHes back the remainder.
        """
        current = self._request(
            'GET', f'/applications/{app_object_id}', params={"$select": "keyCredentials"},
        )
        creds = current.get('keyCredentials') or []
        remaining = [c for c in creds if c.get('keyId') != key_id]
        if len(remaining) == len(creds):
            raise GraphAPIError(
                f"No keyCredential with keyId {key_id} found on application {app_object_id}"
            )
        return self._request(
            'PATCH', f'/applications/{app_object_id}', data={"keyCredentials": remaining},
        )

    # ========== REPORTS ==========

    USAGE_REPORTS = {
        "office365-active": "getOffice365ActiveUserDetail",
        "email-activity": "getEmailActivityUserDetail",
        "mailbox-usage": "getMailboxUsageDetail",
    }

    def reports_mfa_registration(
        self,
        top: int = 100,
        filter_query: str | None = None,
        all_pages: bool = False,
    ) -> dict:
        """Auth-method / MFA registration report (JSON). Requires AuditLog.Read.All."""
        endpoint = "/reports/authenticationMethods/userRegistrationDetails"
        params: dict = {"$top": top}
        if filter_query:
            params["$filter"] = filter_query
        if all_pages:
            items = self._get_all_pages(endpoint, params)
            return {"value": items, "@count": len(items)}
        return self._request('GET', endpoint, params=params)

    def reports_usage(self, report: str, period: str = "D7") -> dict:
        """Fetch a Microsoft 365 usage report (CSV via 302) and parse it to rows.

        Requires Reports.Read.All. 'report' is one of USAGE_REPORTS; 'period' is one of
        D7, D30, D90, D180.
        """
        fn = self.USAGE_REPORTS.get(report)
        if not fn:
            raise GraphAPIError(
                f"Unknown usage report {report!r}. Choose from: {', '.join(self.USAGE_REPORTS)}"
            )
        if period not in ("D7", "D30", "D90", "D180"):
            raise GraphAPIError(f"Invalid period {period!r}. Choose from: D7, D30, D90, D180")
        endpoint = f"/reports/{fn}(period='{period}')"
        rows = self._parse_csv(self._request_csv(endpoint))
        return {"report": report, "period": period, "value": rows, "@count": len(rows)}

    # ========== POLICY ==========

    # Guest role that grants guests the same directory access as members (most permissive).
    GUEST_ROLE_SAME_AS_MEMBER = "a0b1b346-4d3e-4e8b-98f8-753987be4970"

    def policy_authorization(self) -> dict:
        """Authorization policy (user consent + guest defaults). Requires Policy.Read.All."""
        return self._request('GET', '/policies/authorizationPolicy')

    def policy_security_defaults(self) -> dict:
        """Security defaults enforcement policy. Requires Policy.Read.All."""
        return self._request('GET', '/policies/identitySecurityDefaultsEnforcementPolicy')

    def policy_authentication_methods(self) -> dict:
        """Authentication methods policy (which MFA methods are enabled). Requires Policy.Read.All."""
        return self._request('GET', '/policies/authenticationMethodsPolicy')

    def policy_permission_grants(self) -> dict:
        """Permission grant policies (app consent framework). Requires Policy.Read.All."""
        return self._request('GET', '/policies/permissionGrantPolicies')

    def policy_cross_tenant(self) -> dict:
        """Cross-tenant access policy, including its default config. Requires Policy.Read.All."""
        result = self._request('GET', '/policies/crossTenantAccessPolicy')
        try:
            result = dict(result)
            result['default'] = self._request('GET', '/policies/crossTenantAccessPolicy/default')
        except GraphAPIError:
            pass
        return result

    def policy_admin_consent_request(self) -> dict:
        """Admin consent request policy. Requires Policy.Read.All."""
        return self._request('GET', '/policies/adminConsentRequestPolicy')

    def policy_posture(self) -> dict:
        """Aggregate key tenant policies and flag risky settings. Requires Policy.Read.All."""
        findings: list[dict] = []
        security_defaults = self.policy_security_defaults()
        authorization = self.policy_authorization()

        if security_defaults.get('isEnabled') is False:
            findings.append({
                "finding": "Security defaults disabled",
                "severity": "medium",
                "detail": "identitySecurityDefaultsEnforcementPolicy.isEnabled is false. "
                          "Baseline MFA may not be enforced (acceptable only if Conditional "
                          "Access covers it).",
            })

        role_perms = authorization.get('defaultUserRolePermissions') or {}
        if role_perms.get('allowedToCreateApps') is True:
            findings.append({
                "finding": "Users can register applications",
                "severity": "medium",
                "detail": "authorizationPolicy.defaultUserRolePermissions.allowedToCreateApps is "
                          "true. Enables rogue app registrations.",
            })

        assigned = authorization.get('permissionGrantPoliciesAssigned') or []
        user_consent = [p for p in assigned if 'ManagePermissionGrantsForSelf' in str(p)]
        if user_consent:
            findings.append({
                "finding": "User consent to applications is permitted",
                "severity": "high",
                "detail": "authorizationPolicy.permissionGrantPoliciesAssigned grants user "
                          f"consent ({', '.join(user_consent)}). Enables illicit-consent-grant "
                          "phishing.",
            })

        if authorization.get('guestUserRoleId') == self.GUEST_ROLE_SAME_AS_MEMBER:
            findings.append({
                "finding": "Guests have member-level directory access",
                "severity": "high",
                "detail": "authorizationPolicy.guestUserRoleId grants guests the same access as "
                          "members. Guests can enumerate the directory.",
            })

        return {
            "findings": findings,
            "findingCount": len(findings),
            "securityDefaultsEnabled": security_defaults.get('isEnabled'),
            "allowedToCreateApps": role_perms.get('allowedToCreateApps'),
            "permissionGrantPoliciesAssigned": assigned,
            "guestUserRoleId": authorization.get('guestUserRoleId'),
        }

    # ========== CALENDAR ==========

    CALENDAR_SELECT = (
        "id,subject,organizer,start,end,location,isOnlineMeeting,onlineMeetingUrl,webLink"
    )

    def calendar_events(self, user_id: str, top: int = 50) -> dict:
        """List a user's calendar events. Requires Calendars.Read (app-only reads all mailboxes)."""
        params = {"$top": top, "$orderby": "start/dateTime desc", "$select": self.CALENDAR_SELECT}
        return self._request('GET', f'/users/{user_id}/events', params=params)

    def calendar_view(self, user_id: str, start: str, end: str, top: int = 50) -> dict:
        """Calendar view over a start/end window (expands recurring series). Requires Calendars.Read."""
        params = {
            "startDateTime": start,
            "endDateTime": end,
            "$top": top,
            "$orderby": "start/dateTime",
            "$select": self.CALENDAR_SELECT,
        }
        return self._request('GET', f'/users/{user_id}/calendarView', params=params)

    def calendar_calendars(self, user_id: str) -> dict:
        """List a user's calendars. Requires Calendars.Read."""
        return self._request('GET', f'/users/{user_id}/calendars')

    # ========== THREAT ==========

    def _ti_request(self, endpoint: str, params: dict | None = None) -> dict:
        """GET a Defender Threat Intelligence endpoint, degrading gracefully when unlicensed.

        MDTI requires a premium + API add-on license; without it Graph returns Forbidden.
        Return a clear 'unavailable' object instead of raising in that case.
        """
        try:
            return self._request('GET', endpoint, params=params)
        except GraphAPIError as e:
            text = str(e)
            if '(403)' in text or 'forbidden' in text.lower() or 'license' in text.lower():
                return {
                    "status": "unavailable",
                    "message": (
                        "Microsoft Defender Threat Intelligence is unavailable. It requires an "
                        "MDTI premium plus API add-on license on the tenant. Confirm licensing "
                        f"before relying on these endpoints. Underlying error: {e}"
                    ),
                }
            raise

    def threat_assessments(self) -> dict:
        """List submitted threat assessment requests. Requires ThreatAssessment.Read.All."""
        return self._request('GET', '/informationProtection/threatAssessmentRequests')

    def threat_assessment(self, request_id: str) -> dict:
        """Get one threat assessment request. Requires ThreatAssessment.Read.All."""
        return self._request('GET', f'/informationProtection/threatAssessmentRequests/{request_id}')

    def threat_assessment_results(self, request_id: str) -> dict:
        """Get the result detail for a threat assessment. Requires ThreatAssessment.Read.All."""
        return self._request(
            'GET', f'/informationProtection/threatAssessmentRequests/{request_id}/results'
        )

    def threat_intel_articles(self, top: int = 20) -> dict:
        """MDTI threat articles (license-gated). Requires ThreatIntelligence.Read.All."""
        return self._ti_request('/security/threatIntelligence/articles', params={"$top": top})

    def threat_intel_host(self, host: str) -> dict:
        """MDTI host reputation/enrichment (license-gated). Requires ThreatIntelligence.Read.All."""
        return self._ti_request(f'/security/threatIntelligence/hosts/{host}')

    def threat_intel_profiles(self, top: int = 20) -> dict:
        """MDTI intel profiles (license-gated). Requires ThreatIntelligence.Read.All."""
        return self._ti_request('/security/threatIntelligence/intelProfiles', params={"$top": top})

    def threat_intel_vulnerability(self, cve: str) -> dict:
        """MDTI vulnerability detail by CVE (license-gated). Requires ThreatIntelligence.Read.All."""
        return self._ti_request(f'/security/threatIntelligence/vulnerabilities/{cve}')


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Azure AD / Entra ID API CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s users list
  %(prog)s users get "user@domain.com"
  %(prog)s users search "John"
  %(prog)s groups list --all
  %(prog)s groups members GROUP_ID
  %(prog)s devices list --filter "operatingSystem eq 'Windows'"
  %(prog)s directory organization
  %(prog)s --format json users list > users.json
  %(prog)s -t prod users list
        """
    )

    parser.add_argument(
        '-t', '--tenant',
        help='Tenant name or alias (uses default if not specified)'
    )
    parser.add_argument(
        '-f', '--format',
        choices=['table', 'json', 'csv'],
        default='table',
        help='Output format (default: table)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output'
    )

    subparsers = parser.add_subparsers(dest='domain', help='API domain')

    # ===== USERS COMMANDS =====
    users_parser = subparsers.add_parser('users', help='User operations')
    users_sub = users_parser.add_subparsers(dest='action', help='Action')

    # users list
    users_list = users_sub.add_parser('list', help='List all users')
    users_list.add_argument('--top', type=int, default=100, help='Number of results')
    users_list.add_argument('--filter', dest='filter_query', help='OData filter query')
    users_list.add_argument('--select', help='Fields to select')
    users_list.add_argument('--all', action='store_true', help='Get all pages')

    # users get
    users_get = users_sub.add_parser('get', help='Get a specific user')
    users_get.add_argument('user_id', help='User ID or UPN')
    users_get.add_argument('--select', help='Fields to select')

    # users search
    users_search = users_sub.add_parser('search', help='Search users')
    users_search.add_argument('query', help='Search query')
    users_search.add_argument('--top', type=int, default=25, help='Number of results')

    # users create
    users_create = users_sub.add_parser('create', help='Create a user')
    users_create.add_argument('--display-name', required=True, help='Display name')
    users_create.add_argument('--upn', required=True, help='User principal name')
    users_create.add_argument('--mail-nickname', required=True, help='Mail nickname')
    users_create.add_argument('--force-change', action='store_true', help='Force password change on sign-in')

    # users update
    users_update = users_sub.add_parser('update', help='Update a user')
    users_update.add_argument('user_id', help='User ID or UPN')
    users_update.add_argument('--data', required=True, help='JSON data to update')

    # users delete
    users_delete = users_sub.add_parser('delete', help='Delete a user')
    users_delete.add_argument('user_id', help='User ID or UPN')
    users_delete.add_argument('--confirm', action='store_true', required=True, help='Confirm deletion')

    # users manager
    users_manager = users_sub.add_parser('manager', help="Get user's manager")
    users_manager.add_argument('user_id', help='User ID or UPN')

    # users direct-reports
    users_dr = users_sub.add_parser('direct-reports', help="Get user's direct reports")
    users_dr.add_argument('user_id', help='User ID or UPN')

    # users member-of
    users_mo = users_sub.add_parser('member-of', help="Get user's group memberships")
    users_mo.add_argument('user_id', help='User ID or UPN')

    # users owned-devices
    users_od = users_sub.add_parser('owned-devices', help="Get user's owned devices")
    users_od.add_argument('user_id', help='User ID or UPN')

    # users registered-devices
    users_rd = users_sub.add_parser('registered-devices', help="Get user's registered devices")
    users_rd.add_argument('user_id', help='User ID or UPN')

    # users assign-license
    users_al = users_sub.add_parser('assign-license', help='Assign license to user')
    users_al.add_argument('user_id', help='User ID or UPN')
    users_al.add_argument('--sku-ids', required=True, help='Comma-separated SKU IDs')

    # users revoke-license
    users_rl = users_sub.add_parser('revoke-license', help='Remove license from user')
    users_rl.add_argument('user_id', help='User ID or UPN')
    users_rl.add_argument('--sku-ids', required=True, help='Comma-separated SKU IDs')

    # ===== GROUPS COMMANDS =====
    groups_parser = subparsers.add_parser('groups', help='Group operations')
    groups_sub = groups_parser.add_subparsers(dest='action', help='Action')

    # groups list
    groups_list = groups_sub.add_parser('list', help='List all groups')
    groups_list.add_argument('--top', type=int, default=100, help='Number of results')
    groups_list.add_argument('--filter', dest='filter_query', help='OData filter query')
    groups_list.add_argument('--select', help='Fields to select')
    groups_list.add_argument('--all', action='store_true', help='Get all pages')

    # groups get
    groups_get = groups_sub.add_parser('get', help='Get a specific group')
    groups_get.add_argument('group_id', help='Group ID')
    groups_get.add_argument('--select', help='Fields to select')

    # groups search
    groups_search = groups_sub.add_parser('search', help='Search groups')
    groups_search.add_argument('query', help='Search query')
    groups_search.add_argument('--top', type=int, default=25, help='Number of results')

    # groups create
    groups_create = groups_sub.add_parser('create', help='Create a group')
    groups_create.add_argument('--display-name', required=True, help='Display name')
    groups_create.add_argument('--mail-nickname', required=True, help='Mail nickname')
    groups_create.add_argument('--description', help='Group description')
    groups_create.add_argument('--security', action='store_true', default=True, help='Security group')
    groups_create.add_argument('--m365', action='store_true', help='Microsoft 365 group')

    # groups update
    groups_update = groups_sub.add_parser('update', help='Update a group')
    groups_update.add_argument('group_id', help='Group ID')
    groups_update.add_argument('--data', required=True, help='JSON data to update')

    # groups delete
    groups_delete = groups_sub.add_parser('delete', help='Delete a group')
    groups_delete.add_argument('group_id', help='Group ID')
    groups_delete.add_argument('--confirm', action='store_true', required=True, help='Confirm deletion')

    # groups members
    groups_members = groups_sub.add_parser('members', help='List group members')
    groups_members.add_argument('group_id', help='Group ID')
    groups_members.add_argument('--all', action='store_true', help='Get all pages')

    # groups add-member
    groups_am = groups_sub.add_parser('add-member', help='Add member to group')
    groups_am.add_argument('group_id', help='Group ID')
    groups_am.add_argument('member_id', help='Member ID (user or group)')

    # groups remove-member
    groups_rm = groups_sub.add_parser('remove-member', help='Remove member from group')
    groups_rm.add_argument('group_id', help='Group ID')
    groups_rm.add_argument('member_id', help='Member ID')

    # groups owners
    groups_owners = groups_sub.add_parser('owners', help='List group owners')
    groups_owners.add_argument('group_id', help='Group ID')

    # groups add-owner
    groups_ao = groups_sub.add_parser('add-owner', help='Add owner to group')
    groups_ao.add_argument('group_id', help='Group ID')
    groups_ao.add_argument('owner_id', help='Owner ID')

    # groups member-of
    groups_mo = groups_sub.add_parser('member-of', help='Get parent groups')
    groups_mo.add_argument('group_id', help='Group ID')

    # ===== DEVICES COMMANDS =====
    devices_parser = subparsers.add_parser('devices', help='Device operations')
    devices_sub = devices_parser.add_subparsers(dest='action', help='Action')

    # devices list
    devices_list = devices_sub.add_parser('list', help='List all devices')
    devices_list.add_argument('--top', type=int, default=100, help='Number of results')
    devices_list.add_argument('--filter', dest='filter_query', help='OData filter query')
    devices_list.add_argument('--select', help='Fields to select')
    devices_list.add_argument('--all', action='store_true', help='Get all pages')

    # devices get
    devices_get = devices_sub.add_parser('get', help='Get a specific device')
    devices_get.add_argument('device_id', help='Device ID')
    devices_get.add_argument('--select', help='Fields to select')

    # devices search
    devices_search = devices_sub.add_parser('search', help='Search devices')
    devices_search.add_argument('query', help='Search query')
    devices_search.add_argument('--top', type=int, default=25, help='Number of results')

    # devices update
    devices_update = devices_sub.add_parser('update', help='Update a device')
    devices_update.add_argument('device_id', help='Device ID')
    devices_update.add_argument('--data', required=True, help='JSON data to update')

    # devices delete
    devices_delete = devices_sub.add_parser('delete', help='Delete a device')
    devices_delete.add_argument('device_id', help='Device ID')
    devices_delete.add_argument('--confirm', action='store_true', required=True, help='Confirm deletion')

    # devices registered-owners
    devices_ro = devices_sub.add_parser('registered-owners', help='Get device owners')
    devices_ro.add_argument('device_id', help='Device ID')

    # devices registered-users
    devices_ru = devices_sub.add_parser('registered-users', help='Get device registered users')
    devices_ru.add_argument('device_id', help='Device ID')

    # devices member-of
    devices_mo = devices_sub.add_parser('member-of', help='Get device group memberships')
    devices_mo.add_argument('device_id', help='Device ID')

    # ===== DIRECTORY COMMANDS =====
    dir_parser = subparsers.add_parser('directory', help='Directory operations')
    dir_sub = dir_parser.add_subparsers(dest='action', help='Action')

    # directory organization
    dir_sub.add_parser('organization', help='Get organization info')

    # directory domains
    dir_sub.add_parser('domains', help='List verified domains')

    # directory licenses
    dir_sub.add_parser('licenses', help='List available licenses')

    # directory license-details
    dir_ld = dir_sub.add_parser('license-details', help='Get license details')
    dir_ld.add_argument('sku_id', help='SKU ID')

    # directory roles
    dir_sub.add_parser('roles', help='List directory roles')

    # directory role-members
    dir_rm = dir_sub.add_parser('role-members', help='List role members')
    dir_rm.add_argument('role_id', help='Role ID')

    # directory deleted-users
    dir_du = dir_sub.add_parser('deleted-users', help='List deleted users')
    dir_du.add_argument('--top', type=int, default=100, help='Number of results')

    # directory restore-user
    dir_ru = dir_sub.add_parser('restore-user', help='Restore deleted user')
    dir_ru.add_argument('user_id', help='User ID')
    dir_ru.add_argument('--confirm', action='store_true', required=True, help='Confirm restore')

    # ===== SECURITY COMMANDS =====
    security_parser = subparsers.add_parser('security', help='Security and audit log operations')
    security_sub = security_parser.add_subparsers(dest='security_action', required=True)

    # security sign-ins
    p = security_sub.add_parser('sign-ins', help='Fetch sign-in audit logs')
    p.add_argument('--top', type=int, default=100, help='Number of records (default: 100)')
    p.add_argument('--hours', type=int, help='Look back N hours')
    p.add_argument('--since', help='ISO 8601 datetime to filter from')
    p.add_argument('--user', help='Filter by UPN or email')
    p.add_argument('--ip', help='Filter by IP address')
    p.add_argument('--app', help='Filter by application display name')
    p.add_argument('--error-code', dest='error_code', type=int, help='Filter by error code')
    p.add_argument('--country', help='Filter by country (location/countryOrRegion)')
    p.add_argument('--risk-level', dest='risk_level',
                   choices=['low', 'medium', 'high', 'none'],
                   help='Filter by risk level')
    p.add_argument('--all', action='store_true', dest='all_pages', help='Fetch all pages')

    # security risky-users
    p = security_sub.add_parser('risky-users', help='Fetch risky users from Identity Protection')
    p.add_argument('--top', type=int, default=100)
    p.add_argument('--risk-level', choices=['low', 'medium', 'high', 'none'],
                   dest='risk_level', help='Filter by risk level')
    p.add_argument('--risk-state', dest='risk_state',
                   choices=['atRisk', 'confirmedCompromised', 'remediated', 'dismissed'],
                   help='Filter by risk state')

    # security risk-detections
    p = security_sub.add_parser('risk-detections', help='Fetch risk detection events')
    p.add_argument('--top', type=int, default=100)
    p.add_argument('--hours', type=int)

    # security audit-logs
    p = security_sub.add_parser('audit-logs', help='Fetch directory audit logs')
    p.add_argument('--top', type=int, default=100)
    p.add_argument('--hours', type=int)
    p.add_argument('--user', help='Filter by initiated user UPN')
    p.add_argument('--category', help='Filter by activity category')

    # security auth-methods
    p = security_sub.add_parser('auth-methods', help='Get authentication methods for a user')
    p.add_argument('upn', help='User principal name')

    # ===== APPLICATIONS COMMANDS =====
    apps_parser = subparsers.add_parser(
        'applications', help='App registrations, service principals, OAuth consent'
    )
    apps_sub = apps_parser.add_subparsers(dest='action', help='Action')

    p = apps_sub.add_parser('apps-list', help='List app registrations')
    p.add_argument('--top', type=int, default=50, help='Number of results (default: 50)')
    p.add_argument('--all', action='store_true', help='Get all pages')
    p.add_argument('--include-credentials', action='store_true', dest='include_credentials',
                   help='Include key/password credentials in the listing')

    p = apps_sub.add_parser('apps-get', help='Get a single application')
    p.add_argument('app_object_id', help='Application object ID')

    p = apps_sub.add_parser('apps-credentials',
                            help="Application credentials with an 'added N days ago' flag")
    p.add_argument('app_object_id', help='Application object ID')

    p = apps_sub.add_parser('sp-list', help='List service principals (enterprise apps)')
    p.add_argument('--top', type=int, default=50, help='Number of results (default: 50)')
    p.add_argument('--all', action='store_true', help='Get all pages')

    p = apps_sub.add_parser('sp-get', help='Get a single service principal')
    p.add_argument('sp_object_id', help='Service principal object ID')

    p = apps_sub.add_parser('sp-app-roles', help='App roles granted to a service principal')
    p.add_argument('sp_object_id', help='Service principal object ID')

    p = apps_sub.add_parser('oauth-grants', help='Tenant-wide OAuth2 permission grants')
    p.add_argument('--top', type=int, default=200, help='Number of results (default: 200)')
    p.add_argument('--all', action='store_true', help='Get all pages')

    p = apps_sub.add_parser('sp-disable', help='Disable a service principal (guarded write)')
    p.add_argument('sp_object_id', help='Service principal object ID')
    p.add_argument('--confirm', action='store_true', required=True, help='Confirm disable')

    p = apps_sub.add_parser('sp-enable', help='Re-enable a service principal (guarded write)')
    p.add_argument('sp_object_id', help='Service principal object ID')
    p.add_argument('--confirm', action='store_true', required=True, help='Confirm enable')

    p = apps_sub.add_parser('apps-remove-password',
                            help='Remove a client secret by keyId (guarded write)')
    p.add_argument('app_object_id', help='Application object ID')
    p.add_argument('--key-id', dest='key_id', required=True, help='keyId of the password credential')
    p.add_argument('--confirm', action='store_true', required=True, help='Confirm removal')

    p = apps_sub.add_parser('apps-remove-key',
                            help='Remove a certificate by keyId (guarded write)')
    p.add_argument('app_object_id', help='Application object ID')
    p.add_argument('--key-id', dest='key_id', required=True, help='keyId of the key credential')
    p.add_argument('--confirm', action='store_true', required=True, help='Confirm removal')

    # ===== REPORTS COMMANDS =====
    reports_parser = subparsers.add_parser(
        'reports', help='Usage reports and MFA registration report'
    )
    reports_sub = reports_parser.add_subparsers(dest='action', help='Action')

    p = reports_sub.add_parser('mfa-registration',
                               help='Auth-method / MFA registration report (JSON)')
    p.add_argument('--top', type=int, default=100, help='Number of results (default: 100)')
    p.add_argument('--filter', dest='filter_query',
                   help='OData filter (e.g. "isMfaRegistered eq false")')
    p.add_argument('--all', action='store_true', help='Get all pages')

    p = reports_sub.add_parser('usage', help='Microsoft 365 usage report (CSV parsed to rows)')
    p.add_argument('--report', required=True,
                   choices=['office365-active', 'email-activity', 'mailbox-usage'],
                   help='Which usage report to fetch')
    p.add_argument('--period', default='D7', choices=['D7', 'D30', 'D90', 'D180'],
                   help='Reporting period (default: D7)')

    # ===== POLICY COMMANDS =====
    policy_parser = subparsers.add_parser('policy', help='Tenant security policy posture')
    policy_sub = policy_parser.add_subparsers(dest='action', help='Action')
    policy_sub.add_parser('authorization', help='Authorization policy (consent + guest defaults)')
    policy_sub.add_parser('security-defaults', help='Security defaults enforcement policy')
    policy_sub.add_parser('authentication-methods', help='Authentication methods policy')
    policy_sub.add_parser('permission-grants', help='Permission grant policies')
    policy_sub.add_parser('cross-tenant', help='Cross-tenant access policy (incl. default)')
    policy_sub.add_parser('admin-consent-request', help='Admin consent request policy')
    policy_sub.add_parser('posture', help='Aggregate posture check with flagged risky settings')

    # ===== CALENDAR COMMANDS =====
    calendar_parser = subparsers.add_parser('calendar', help='User calendar reads')
    calendar_sub = calendar_parser.add_subparsers(dest='action', help='Action')

    p = calendar_sub.add_parser('events', help="List a user's calendar events")
    p.add_argument('user_id', help='User ID or UPN')
    p.add_argument('--top', type=int, default=50, help='Number of results (default: 50)')

    p = calendar_sub.add_parser('view', help='Calendar view over a start/end window')
    p.add_argument('user_id', help='User ID or UPN')
    p.add_argument('--start', required=True,
                   help='Window start (UTC ISO 8601, e.g. 2026-06-01T00:00:00Z)')
    p.add_argument('--end', required=True, help='Window end (UTC ISO 8601)')
    p.add_argument('--top', type=int, default=50, help='Number of results (default: 50)')

    p = calendar_sub.add_parser('calendars', help="List a user's calendars")
    p.add_argument('user_id', help='User ID or UPN')

    # ===== THREAT COMMANDS =====
    threat_parser = subparsers.add_parser(
        'threat', help='Threat assessment + Defender Threat Intelligence'
    )
    threat_sub = threat_parser.add_subparsers(dest='action', help='Action')
    threat_sub.add_parser('assessments', help='List submitted threat assessment requests')

    p = threat_sub.add_parser('assessment', help='Get one threat assessment request')
    p.add_argument('request_id', help='Threat assessment request ID')

    p = threat_sub.add_parser('assessment-results', help='Get result detail for an assessment')
    p.add_argument('request_id', help='Threat assessment request ID')

    p = threat_sub.add_parser('intel-articles', help='MDTI threat articles (license-gated)')
    p.add_argument('--top', type=int, default=20, help='Number of results (default: 20)')

    p = threat_sub.add_parser('intel-host', help='MDTI host reputation/enrichment (license-gated)')
    p.add_argument('host', help='Host name or IP')

    p = threat_sub.add_parser('intel-profiles', help='MDTI intel profiles (license-gated)')
    p.add_argument('--top', type=int, default=20, help='Number of results (default: 20)')

    p = threat_sub.add_parser('intel-vulnerability',
                              help='MDTI vulnerability detail by CVE (license-gated)')
    p.add_argument('cve', help='CVE identifier (e.g. CVE-2024-12345)')

    return parser


def handle_security(api: AzureADAPI, args: argparse.Namespace) -> dict | None:
    """Handle security subcommand dispatch."""
    if args.security_action == 'sign-ins':
        filter_parts = []
        time_f = build_time_filter(
            field='createdDateTime',
            hours=getattr(args, 'hours', None),
            since=getattr(args, 'since', None),
        )
        if time_f:
            filter_parts.append(time_f)
        if getattr(args, 'user', None):
            safe_user = args.user.replace("'", "''")
            filter_parts.append(f"userPrincipalName eq '{safe_user}'")
        if getattr(args, 'ip', None):
            if not re.match(r'^[\d.:/\[\]a-fA-F%]+$', args.ip):
                raise ValueError(f"Invalid IP address format: {args.ip!r}")
            filter_parts.append(f"ipAddress eq '{args.ip}'")
        if getattr(args, 'app', None):
            safe_app = args.app.replace("'", "''")
            filter_parts.append(f"appDisplayName eq '{safe_app}'")
        if getattr(args, 'error_code', None) is not None:
            filter_parts.append(f"status/errorCode eq {args.error_code}")
        if getattr(args, 'country', None):
            safe_country = args.country.replace("'", "''")
            filter_parts.append(f"location/countryOrRegion eq '{safe_country}'")
        if getattr(args, 'risk_level', None):
            filter_parts.append(f"riskLevelDuringSignIn eq '{args.risk_level}'")
        fq = ' and '.join(filter_parts) if filter_parts else None
        return api.security_sign_ins(
            top=args.top,
            filter_query=fq,
            all_pages=getattr(args, 'all_pages', False),
        )
    elif args.security_action == 'risky-users':
        filter_parts = []
        if getattr(args, 'risk_level', None):
            filter_parts.append(f"riskLevel eq '{args.risk_level}'")
        if getattr(args, 'risk_state', None):
            filter_parts.append(f"riskState eq '{args.risk_state}'")
        fq = ' and '.join(filter_parts) if filter_parts else None
        return api.security_risky_users(top=args.top, filter_query=fq)
    elif args.security_action == 'risk-detections':
        fq = build_time_filter(field='detectedDateTime', hours=getattr(args, 'hours', None))
        return api.security_risk_detections(top=args.top, filter_query=fq)
    elif args.security_action == 'audit-logs':
        filter_parts = []
        time_f = build_time_filter(
            field='activityDateTime',
            hours=getattr(args, 'hours', None),
        )
        if time_f:
            filter_parts.append(time_f)
        if getattr(args, 'user', None):
            safe_user = args.user.replace("'", "''")
            filter_parts.append(f"initiatedBy/user/userPrincipalName eq '{safe_user}'")
        if getattr(args, 'category', None):
            safe_category = args.category.replace("'", "''")
            filter_parts.append(f"category eq '{safe_category}'")
        fq = ' and '.join(filter_parts) if filter_parts else None
        return api.security_audit_logs(top=args.top, filter_query=fq)
    elif args.security_action == 'auth-methods':
        return api.security_auth_methods(args.upn)
    return None


def handle_applications(api: AzureADAPI, args: argparse.Namespace) -> dict | None:
    """Handle applications subcommand dispatch."""
    if args.action == 'apps-list':
        return api.applications_apps_list(
            top=args.top, all_pages=args.all,
            include_credentials=getattr(args, 'include_credentials', False),
        )
    elif args.action == 'apps-get':
        return api.applications_apps_get(args.app_object_id)
    elif args.action == 'apps-credentials':
        return api.applications_apps_credentials(args.app_object_id)
    elif args.action == 'sp-list':
        return api.applications_sp_list(top=args.top, all_pages=args.all)
    elif args.action == 'sp-get':
        return api.applications_sp_get(args.sp_object_id)
    elif args.action == 'sp-app-roles':
        return api.applications_sp_app_roles(args.sp_object_id)
    elif args.action == 'oauth-grants':
        return api.applications_oauth_grants(top=args.top, all_pages=args.all)
    elif args.action == 'sp-disable':
        result = api.applications_sp_set_enabled(args.sp_object_id, False)
        print_success(f"Service principal disabled: {args.sp_object_id}")
        return result
    elif args.action == 'sp-enable':
        result = api.applications_sp_set_enabled(args.sp_object_id, True)
        print_success(f"Service principal enabled: {args.sp_object_id}")
        return result
    elif args.action == 'apps-remove-password':
        result = api.applications_apps_remove_password(args.app_object_id, args.key_id)
        print_success(f"Client secret {args.key_id} removed from {args.app_object_id}")
        return result
    elif args.action == 'apps-remove-key':
        result = api.applications_apps_remove_key(args.app_object_id, args.key_id)
        print_success(f"Certificate {args.key_id} removed from {args.app_object_id}")
        return result
    return None


def handle_reports(api: AzureADAPI, args: argparse.Namespace) -> dict | None:
    """Handle reports subcommand dispatch."""
    if args.action == 'mfa-registration':
        return api.reports_mfa_registration(
            top=args.top,
            filter_query=getattr(args, 'filter_query', None),
            all_pages=args.all,
        )
    elif args.action == 'usage':
        return api.reports_usage(report=args.report, period=args.period)
    return None


def handle_policy(api: AzureADAPI, args: argparse.Namespace) -> dict | None:
    """Handle policy subcommand dispatch."""
    dispatch = {
        'authorization': api.policy_authorization,
        'security-defaults': api.policy_security_defaults,
        'authentication-methods': api.policy_authentication_methods,
        'permission-grants': api.policy_permission_grants,
        'cross-tenant': api.policy_cross_tenant,
        'admin-consent-request': api.policy_admin_consent_request,
        'posture': api.policy_posture,
    }
    handler = dispatch.get(args.action)
    return handler() if handler else None


def handle_calendar(api: AzureADAPI, args: argparse.Namespace) -> dict | None:
    """Handle calendar subcommand dispatch."""
    if args.action == 'events':
        return api.calendar_events(args.user_id, top=args.top)
    elif args.action == 'view':
        return api.calendar_view(args.user_id, args.start, args.end, top=args.top)
    elif args.action == 'calendars':
        return api.calendar_calendars(args.user_id)
    return None


def handle_threat(api: AzureADAPI, args: argparse.Namespace) -> dict | None:
    """Handle threat subcommand dispatch."""
    if args.action == 'assessments':
        return api.threat_assessments()
    elif args.action == 'assessment':
        return api.threat_assessment(args.request_id)
    elif args.action == 'assessment-results':
        return api.threat_assessment_results(args.request_id)
    elif args.action == 'intel-articles':
        return api.threat_intel_articles(top=args.top)
    elif args.action == 'intel-host':
        return api.threat_intel_host(args.host)
    elif args.action == 'intel-profiles':
        return api.threat_intel_profiles(top=args.top)
    elif args.action == 'intel-vulnerability':
        return api.threat_intel_vulnerability(args.cve)
    return None


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.domain:
        parser.print_help()
        sys.exit(1)

    # Security domain uses security_action instead of action
    if args.domain != 'security' and not args.action:
        # Show domain help
        parser.parse_args([args.domain, '-h'])
        sys.exit(1)

    try:
        api = AzureADAPI(tenant=args.tenant)
        result = None

        # ===== USERS =====
        if args.domain == 'users':
            if args.action == 'list':
                result = api.users_list(
                    top=args.top,
                    select=args.select,
                    filter_query=args.filter_query,
                    all_pages=args.all
                )
            elif args.action == 'get':
                result = api.users_get(args.user_id, select=args.select)
            elif args.action == 'search':
                result = api.users_search(args.query, top=args.top)
            elif args.action == 'create':
                user_data = {
                    'displayName': args.display_name,
                    'mailNickname': args.mail_nickname,
                    'userPrincipalName': args.upn,
                    'passwordProfile': {
                        'password': os.environ.get('AZURE_INITIAL_PASSWORD') or getpass.getpass('Initial password: '),
                        'forceChangePasswordNextSignIn': args.force_change
                    },
                    'accountEnabled': True
                }
                result = api.users_create(user_data)
                print_success(f"User created: {result.get('userPrincipalName')}")
            elif args.action == 'update':
                updates = json.loads(args.data)
                result = api.users_update(args.user_id, updates)
                print_success(f"User updated: {args.user_id}")
            elif args.action == 'delete':
                result = api.users_delete(args.user_id)
                print_success(f"User deleted: {args.user_id}")
            elif args.action == 'manager':
                result = api.users_manager(args.user_id)
            elif args.action == 'direct-reports':
                result = api.users_direct_reports(args.user_id)
            elif args.action == 'member-of':
                result = api.users_member_of(args.user_id)
            elif args.action == 'owned-devices':
                result = api.users_owned_devices(args.user_id)
            elif args.action == 'registered-devices':
                result = api.users_registered_devices(args.user_id)
            elif args.action == 'assign-license':
                sku_ids = [s.strip() for s in args.sku_ids.split(',')]
                result = api.users_assign_license(args.user_id, sku_ids)
                print_success(f"Licenses assigned to {args.user_id}")
            elif args.action == 'revoke-license':
                sku_ids = [s.strip() for s in args.sku_ids.split(',')]
                result = api.users_revoke_license(args.user_id, sku_ids)
                print_success(f"Licenses revoked from {args.user_id}")

        # ===== GROUPS =====
        elif args.domain == 'groups':
            if args.action == 'list':
                result = api.groups_list(
                    top=args.top,
                    select=args.select,
                    filter_query=args.filter_query,
                    all_pages=args.all
                )
            elif args.action == 'get':
                result = api.groups_get(args.group_id, select=args.select)
            elif args.action == 'search':
                result = api.groups_search(args.query, top=args.top)
            elif args.action == 'create':
                group_data = {
                    'displayName': args.display_name,
                    'mailNickname': args.mail_nickname,
                    'mailEnabled': args.m365,
                    'securityEnabled': args.security or not args.m365,
                }
                if args.description:
                    group_data['description'] = args.description
                if args.m365:
                    group_data['groupTypes'] = ['Unified']

                result = api.groups_create(group_data)
                print_success(f"Group created: {result.get('displayName')}")
            elif args.action == 'update':
                updates = json.loads(args.data)
                result = api.groups_update(args.group_id, updates)
                print_success(f"Group updated: {args.group_id}")
            elif args.action == 'delete':
                result = api.groups_delete(args.group_id)
                print_success(f"Group deleted: {args.group_id}")
            elif args.action == 'members':
                result = api.groups_members(args.group_id, all_pages=args.all)
            elif args.action == 'add-member':
                result = api.groups_add_member(args.group_id, args.member_id)
                print_success(f"Member {args.member_id} added to group")
            elif args.action == 'remove-member':
                result = api.groups_remove_member(args.group_id, args.member_id)
                print_success(f"Member {args.member_id} removed from group")
            elif args.action == 'owners':
                result = api.groups_owners(args.group_id)
            elif args.action == 'add-owner':
                result = api.groups_add_owner(args.group_id, args.owner_id)
                print_success(f"Owner {args.owner_id} added to group")
            elif args.action == 'member-of':
                result = api.groups_member_of(args.group_id)

        # ===== DEVICES =====
        elif args.domain == 'devices':
            if args.action == 'list':
                result = api.devices_list(
                    top=args.top,
                    select=args.select,
                    filter_query=args.filter_query,
                    all_pages=args.all
                )
            elif args.action == 'get':
                result = api.devices_get(args.device_id, select=args.select)
            elif args.action == 'search':
                result = api.devices_search(args.query, top=args.top)
            elif args.action == 'update':
                updates = json.loads(args.data)
                result = api.devices_update(args.device_id, updates)
                print_success(f"Device updated: {args.device_id}")
            elif args.action == 'delete':
                result = api.devices_delete(args.device_id)
                print_success(f"Device deleted: {args.device_id}")
            elif args.action == 'registered-owners':
                result = api.devices_registered_owners(args.device_id)
            elif args.action == 'registered-users':
                result = api.devices_registered_users(args.device_id)
            elif args.action == 'member-of':
                result = api.devices_member_of(args.device_id)

        # ===== DIRECTORY =====
        elif args.domain == 'directory':
            if args.action == 'organization':
                result = api.directory_organization()
            elif args.action == 'domains':
                result = api.directory_domains()
            elif args.action == 'licenses':
                result = api.directory_licenses()
            elif args.action == 'license-details':
                result = api.directory_license_details(args.sku_id)
            elif args.action == 'roles':
                result = api.directory_roles()
            elif args.action == 'role-members':
                result = api.directory_role_members(args.role_id)
            elif args.action == 'deleted-users':
                result = api.directory_deleted_users(top=args.top)
            elif args.action == 'restore-user':
                result = api.directory_restore_user(args.user_id)
                print_success(f"User restored: {args.user_id}")

        # ===== SECURITY =====
        elif args.domain == 'security':
            result = handle_security(api, args)

        # ===== APPLICATIONS =====
        elif args.domain == 'applications':
            result = handle_applications(api, args)

        # ===== REPORTS =====
        elif args.domain == 'reports':
            result = handle_reports(api, args)

        # ===== POLICY =====
        elif args.domain == 'policy':
            result = handle_policy(api, args)

        # ===== CALENDAR =====
        elif args.domain == 'calendar':
            result = handle_calendar(api, args)

        # ===== THREAT =====
        elif args.domain == 'threat':
            result = handle_threat(api, args)

        # Output result
        if result:
            output = format_output(result, args.format)
            print(output)

    except AuthError as e:
        print_error(str(e))
        sys.exit(1)
    except GraphAPIError as e:
        print_error(str(e))
        sys.exit(1)
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON: {e}")
        sys.exit(1)
    except Exception as e:
        if args.debug:
            raise
        print_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
