#!/usr/bin/env python3
"""
Azure AD / Entra ID API CLI.

Comprehensive CLI for Microsoft Graph API operations on Azure AD resources:
- Users: List, get, search, create, update, delete, memberships, licenses
- Groups: List, get, members, owners, add/remove members
- Devices: List, get, search, owners, registered users
- Directory: Organization info, domains, licenses, roles

Usage:
    python azure_ad_api.py users list
    python azure_ad_api.py users get "user@domain.com"
    python azure_ad_api.py groups members GROUP_ID
    python azure_ad_api.py --format json users list
    python azure_ad_api.py -t prod devices list
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

import requests

from auth import AzureAuth, AuthError
from formatters import format_output, print_error, print_success, print_warning


class GraphAPIError(Exception):
    """Graph API error."""
    pass


class AzureADAPI:
    """Azure AD API client using Microsoft Graph."""

    BASE_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self, tenant: Optional[str] = None):
        """Initialize the API client."""
        self.auth = AzureAuth(tenant=tenant)
        self.config = self.auth.config

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
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

            raise GraphAPIError(f"API error ({e.response.status_code}): {error_detail}")

        except requests.exceptions.RequestException as e:
            raise GraphAPIError(f"Request failed: {e}")

    def _get_all_pages(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        max_pages: int = 100
    ) -> List[Dict]:
        """Get all pages of results."""
        all_items = []
        page_count = 0

        while endpoint and page_count < max_pages:
            if endpoint.startswith('http'):
                # Handle @odata.nextLink URLs
                response = requests.get(
                    endpoint,
                    headers=self.auth.get_auth_headers(),
                    timeout=self.config.get('defaults', {}).get('timeout', 30)
                )
                response.raise_for_status()
                result = response.json()
            else:
                result = self._request('GET', endpoint, params=params)

            items = result.get('value', [])
            all_items.extend(items)

            # Get next page link
            endpoint = result.get('@odata.nextLink')
            params = None  # nextLink includes all params
            page_count += 1

        return all_items

    # ========== USERS ==========

    def users_list(
        self,
        top: int = 100,
        select: Optional[str] = None,
        filter_query: Optional[str] = None,
        all_pages: bool = False
    ) -> Dict:
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

    def users_get(self, user_id: str, select: Optional[str] = None) -> Dict:
        """Get a specific user by ID or UPN."""
        params = {}
        if select:
            params["$select"] = select

        return self._request('GET', f'/users/{user_id}', params=params or None)

    def users_search(self, query: str, top: int = 25) -> Dict:
        """Search users by displayName or mail."""
        params = {
            "$top": top,
            "$filter": f"startswith(displayName,'{query}') or startswith(mail,'{query}')",
            "$select": "id,displayName,userPrincipalName,mail,jobTitle,department"
        }
        return self._request('GET', '/users', params=params)

    def users_create(self, user_data: Dict) -> Dict:
        """Create a new user."""
        required = ['displayName', 'mailNickname', 'userPrincipalName', 'passwordProfile']
        missing = [f for f in required if f not in user_data]
        if missing:
            raise GraphAPIError(f"Missing required fields: {missing}")

        return self._request('POST', '/users', data=user_data)

    def users_update(self, user_id: str, updates: Dict) -> Dict:
        """Update a user's properties."""
        return self._request('PATCH', f'/users/{user_id}', data=updates)

    def users_delete(self, user_id: str) -> Dict:
        """Delete a user."""
        return self._request('DELETE', f'/users/{user_id}')

    def users_manager(self, user_id: str) -> Dict:
        """Get user's manager."""
        return self._request('GET', f'/users/{user_id}/manager')

    def users_direct_reports(self, user_id: str) -> Dict:
        """Get user's direct reports."""
        return self._request('GET', f'/users/{user_id}/directReports')

    def users_member_of(self, user_id: str) -> Dict:
        """Get groups and roles the user is a member of."""
        return self._request('GET', f'/users/{user_id}/memberOf')

    def users_owned_devices(self, user_id: str) -> Dict:
        """Get devices owned by the user."""
        return self._request('GET', f'/users/{user_id}/ownedDevices')

    def users_registered_devices(self, user_id: str) -> Dict:
        """Get devices registered to the user."""
        return self._request('GET', f'/users/{user_id}/registeredDevices')

    def users_assign_license(self, user_id: str, sku_ids: List[str]) -> Dict:
        """Assign licenses to a user."""
        data = {
            "addLicenses": [{"skuId": sku_id} for sku_id in sku_ids],
            "removeLicenses": []
        }
        return self._request('POST', f'/users/{user_id}/assignLicense', data=data)

    def users_revoke_license(self, user_id: str, sku_ids: List[str]) -> Dict:
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
        select: Optional[str] = None,
        filter_query: Optional[str] = None,
        all_pages: bool = False
    ) -> Dict:
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

    def groups_get(self, group_id: str, select: Optional[str] = None) -> Dict:
        """Get a specific group."""
        params = {}
        if select:
            params["$select"] = select

        return self._request('GET', f'/groups/{group_id}', params=params or None)

    def groups_search(self, query: str, top: int = 25) -> Dict:
        """Search groups by displayName."""
        params = {
            "$top": top,
            "$filter": f"startswith(displayName,'{query}')",
            "$select": "id,displayName,mail,groupTypes,description"
        }
        return self._request('GET', '/groups', params=params)

    def groups_create(self, group_data: Dict) -> Dict:
        """Create a new group."""
        required = ['displayName', 'mailEnabled', 'mailNickname', 'securityEnabled']
        missing = [f for f in required if f not in group_data]
        if missing:
            raise GraphAPIError(f"Missing required fields: {missing}")

        return self._request('POST', '/groups', data=group_data)

    def groups_update(self, group_id: str, updates: Dict) -> Dict:
        """Update a group's properties."""
        return self._request('PATCH', f'/groups/{group_id}', data=updates)

    def groups_delete(self, group_id: str) -> Dict:
        """Delete a group."""
        return self._request('DELETE', f'/groups/{group_id}')

    def groups_members(self, group_id: str, all_pages: bool = False) -> Dict:
        """List group members."""
        if all_pages:
            items = self._get_all_pages(f"/groups/{group_id}/members")
            return {"value": items}

        return self._request('GET', f'/groups/{group_id}/members')

    def groups_add_member(self, group_id: str, member_id: str) -> Dict:
        """Add a member to a group."""
        data = {
            "@odata.id": f"{self.BASE_URL}/directoryObjects/{member_id}"
        }
        return self._request('POST', f'/groups/{group_id}/members/$ref', data=data)

    def groups_remove_member(self, group_id: str, member_id: str) -> Dict:
        """Remove a member from a group."""
        return self._request('DELETE', f'/groups/{group_id}/members/{member_id}/$ref')

    def groups_owners(self, group_id: str) -> Dict:
        """List group owners."""
        return self._request('GET', f'/groups/{group_id}/owners')

    def groups_add_owner(self, group_id: str, owner_id: str) -> Dict:
        """Add an owner to a group."""
        data = {
            "@odata.id": f"{self.BASE_URL}/directoryObjects/{owner_id}"
        }
        return self._request('POST', f'/groups/{group_id}/owners/$ref', data=data)

    def groups_member_of(self, group_id: str) -> Dict:
        """Get groups this group is a member of."""
        return self._request('GET', f'/groups/{group_id}/memberOf')

    # ========== DEVICES ==========

    def devices_list(
        self,
        top: int = 100,
        select: Optional[str] = None,
        filter_query: Optional[str] = None,
        all_pages: bool = False
    ) -> Dict:
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

    def devices_get(self, device_id: str, select: Optional[str] = None) -> Dict:
        """Get a specific device."""
        params = {}
        if select:
            params["$select"] = select

        return self._request('GET', f'/devices/{device_id}', params=params or None)

    def devices_search(self, query: str, top: int = 25) -> Dict:
        """Search devices by displayName."""
        params = {
            "$top": top,
            "$filter": f"startswith(displayName,'{query}')",
            "$select": "id,displayName,operatingSystem,operatingSystemVersion,trustType,isManaged"
        }
        return self._request('GET', '/devices', params=params)

    def devices_update(self, device_id: str, updates: Dict) -> Dict:
        """Update a device's properties."""
        return self._request('PATCH', f'/devices/{device_id}', data=updates)

    def devices_delete(self, device_id: str) -> Dict:
        """Delete a device."""
        return self._request('DELETE', f'/devices/{device_id}')

    def devices_registered_owners(self, device_id: str) -> Dict:
        """Get device's registered owners."""
        return self._request('GET', f'/devices/{device_id}/registeredOwners')

    def devices_registered_users(self, device_id: str) -> Dict:
        """Get device's registered users."""
        return self._request('GET', f'/devices/{device_id}/registeredUsers')

    def devices_member_of(self, device_id: str) -> Dict:
        """Get groups the device is a member of."""
        return self._request('GET', f'/devices/{device_id}/memberOf')

    # ========== DIRECTORY ==========

    def directory_organization(self) -> Dict:
        """Get organization information."""
        return self._request('GET', '/organization')

    def directory_domains(self) -> Dict:
        """List verified domains."""
        return self._request('GET', '/domains')

    def directory_licenses(self) -> Dict:
        """List available licenses (subscribed SKUs)."""
        return self._request('GET', '/subscribedSkus')

    def directory_license_details(self, sku_id: str) -> Dict:
        """Get license details."""
        return self._request('GET', f'/subscribedSkus/{sku_id}')

    def directory_roles(self) -> Dict:
        """List directory roles."""
        return self._request('GET', '/directoryRoles')

    def directory_role_members(self, role_id: str) -> Dict:
        """List members of a directory role."""
        return self._request('GET', f'/directoryRoles/{role_id}/members')

    def directory_deleted_users(self, top: int = 100) -> Dict:
        """List deleted users."""
        params = {"$top": top}
        return self._request('GET', '/directory/deletedItems/microsoft.graph.user', params=params)

    def directory_restore_user(self, user_id: str) -> Dict:
        """Restore a deleted user."""
        return self._request('POST', f'/directory/deletedItems/{user_id}/restore')


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
    users_create.add_argument('--password', required=True, help='Initial password')
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

    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.domain:
        parser.print_help()
        sys.exit(1)

    if not args.action:
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
                        'password': args.password,
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
