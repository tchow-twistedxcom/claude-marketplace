#!/usr/bin/env python3
"""
NinjaOne API CLI

Command-line interface for NinjaOne RMM API operations.
Covers devices, organizations, queries, management, ticketing, alerts, policies, and webhooks.
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from auth import NinjaOneAuth, NinjaOneAuthError
from formatters import format_output, print_json


class NinjaOneAPIError(Exception):
    """Error from NinjaOne API."""
    pass


class NinjaOneAPI:
    """NinjaOne API client."""

    def __init__(self, config_path=None):
        """Initialize API client with authentication."""
        self.auth = NinjaOneAuth(config_path)
        self.base_url = self.auth.get_api_url().rstrip('/')
        self.defaults = self.auth.get_defaults()

    def _request(self, method, endpoint, data=None, params=None):
        """
        Make an API request.

        Args:
            method: HTTP method (GET, POST, PATCH, PUT, DELETE)
            endpoint: API endpoint (e.g., '/v2/devices')
            data: Request body (dict, will be JSON encoded)
            params: Query parameters (dict)

        Returns:
            Response data (dict or list)
        """
        url = f"{self.base_url}{endpoint}"

        if params:
            # Filter out None values
            params = {k: v for k, v in params.items() if v is not None}
            if params:
                url += '?' + urlencode(params)

        headers = self.auth.get_headers()

        body = None
        if data is not None:
            body = json.dumps(data).encode('utf-8')

        req = Request(url, data=body, headers=headers, method=method)

        try:
            timeout = self.defaults.get('timeout', 30)
            with urlopen(req, timeout=timeout) as response:
                content = response.read().decode('utf-8')
                if content:
                    return json.loads(content)
                return {}
        except HTTPError as e:
            error_body = e.read().decode('utf-8')
            try:
                error_json = json.loads(error_body)
                error_msg = error_json.get('message', error_json.get('error', str(e)))
            except (json.JSONDecodeError, KeyError, TypeError):
                error_msg = error_body[:500] if error_body else str(e)
            raise NinjaOneAPIError(f"API error ({e.code}): {error_msg}")
        except URLError as e:
            raise NinjaOneAPIError(f"Network error: {e}")

    def get(self, endpoint, params=None):
        """Make GET request."""
        return self._request('GET', endpoint, params=params)

    def post(self, endpoint, data=None, params=None):
        """Make POST request."""
        return self._request('POST', endpoint, data=data, params=params)

    def patch(self, endpoint, data=None):
        """Make PATCH request."""
        return self._request('PATCH', endpoint, data=data)

    def put(self, endpoint, data=None):
        """Make PUT request."""
        return self._request('PUT', endpoint, data=data)

    def delete(self, endpoint):
        """Make DELETE request."""
        return self._request('DELETE', endpoint)

    # ==================== DEVICES ====================

    def list_devices(self, page_size=None, after=None, df=None):
        """List all devices."""
        params = {
            'pageSize': page_size or self.defaults.get('page_size', 100),
            'after': after,
            'df': df  # Device filter
        }
        return self.get('/v2/devices', params)

    def get_device(self, device_id):
        """Get device by ID."""
        return self.get(f'/v2/device/{device_id}')

    def get_device_detailed(self, device_id):
        """Get detailed device information."""
        return self.get(f'/v2/device/{device_id}/detailed')

    def search_devices(self, df=None, page_size=None):
        """Search devices with filter."""
        params = {
            'df': df,
            'pageSize': page_size or self.defaults.get('page_size', 100)
        }
        return self.get('/v2/devices-detailed', params)

    def get_device_activities(self, device_id, older_than=None, newer_than=None, activity_type=None):
        """Get device activities."""
        params = {
            'olderThan': older_than,
            'newerThan': newer_than,
            'type': activity_type
        }
        return self.get(f'/v2/device/{device_id}/activities', params)

    def get_device_alerts(self, device_id):
        """Get device alerts."""
        return self.get(f'/v2/device/{device_id}/alerts')

    def get_device_software(self, device_id):
        """Get installed software on device."""
        return self.get(f'/v2/device/{device_id}/software')

    def get_device_os_patches(self, device_id, status=None):
        """Get OS patches for device."""
        params = {'status': status}
        return self.get(f'/v2/device/{device_id}/os-patches', params)

    def get_device_software_patches(self, device_id, status=None):
        """Get third-party software patches for device."""
        params = {'status': status}
        return self.get(f'/v2/device/{device_id}/software-patches', params)

    def get_device_disks(self, device_id):
        """Get disk drives for device."""
        return self.get(f'/v2/device/{device_id}/disks')

    def get_device_volumes(self, device_id):
        """Get volumes for device."""
        return self.get(f'/v2/device/{device_id}/volumes')

    def get_device_processors(self, device_id):
        """Get processors for device."""
        return self.get(f'/v2/device/{device_id}/processors')

    def get_device_network(self, device_id):
        """Get network interfaces for device."""
        return self.get(f'/v2/device/{device_id}/network-interfaces')

    def get_device_services(self, device_id, name=None, state=None):
        """Get Windows services on device."""
        params = {'name': name, 'state': state}
        return self.get(f'/v2/device/{device_id}/windows-services', params)

    def get_device_custom_fields(self, device_id):
        """Get custom fields for device."""
        return self.get(f'/v2/device/{device_id}/custom-fields')

    def update_device_custom_fields(self, device_id, fields):
        """Update custom fields for device."""
        return self.patch(f'/v2/device/{device_id}/custom-fields', fields)

    def get_device_last_user(self, device_id):
        """Get last logged on user for device."""
        return self.get(f'/v2/device/{device_id}/last-logged-on-user')

    # ==================== ORGANIZATIONS ====================

    def list_organizations(self, page_size=None, after=None):
        """List all organizations."""
        params = {
            'pageSize': page_size or self.defaults.get('page_size', 100),
            'after': after
        }
        return self.get('/v2/organizations', params)

    def find_organization_by_name(self, name):
        """
        Find organization by name (case-insensitive partial match).

        Returns:
            Organization dict if found, None otherwise
        """
        orgs = self.list_organizations(page_size=1000)
        name_lower = name.lower()

        # Try exact match first
        for org in orgs:
            if org.get('name', '').lower() == name_lower:
                return org

        # Try partial match
        matches = [org for org in orgs if name_lower in org.get('name', '').lower()]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            raise NinjaOneAPIError(
                f"Multiple organizations match '{name}': " +
                ", ".join(f"{o.get('name')} (ID: {o.get('id')})" for o in matches[:5])
            )

        return None

    def get_organization(self, org_id):
        """Get organization by ID."""
        return self.get(f'/v2/organization/{org_id}')

    def create_organization(self, data):
        """Create a new organization."""
        return self.post('/v2/organizations', data)

    def update_organization(self, org_id, data):
        """Update an organization."""
        return self.patch(f'/v2/organization/{org_id}', data)

    def get_organization_devices(self, org_id, page_size=None, after=None):
        """Get devices for an organization."""
        params = {
            'pageSize': page_size or self.defaults.get('page_size', 100),
            'after': after
        }
        return self.get(f'/v2/organization/{org_id}/devices', params)

    def get_organization_locations(self, org_id):
        """Get locations for an organization."""
        return self.get(f'/v2/organization/{org_id}/locations')

    def get_organization_end_users(self, org_id):
        """Get end users for an organization."""
        return self.get(f'/v2/organization/{org_id}/end-users')

    def get_organization_custom_fields(self, org_id):
        """Get custom fields for an organization."""
        return self.get(f'/v2/organization/{org_id}/custom-fields')

    def update_organization_custom_fields(self, org_id, fields):
        """Update custom fields for an organization."""
        return self.patch(f'/v2/organization/{org_id}/custom-fields', fields)

    def get_organization_backup_usage(self, org_id):
        """Get backup usage for an organization."""
        return self.get(f'/v2/organization/{org_id}/backup/usage')

    # ==================== QUERIES/REPORTS ====================

    def query_antivirus_status(self, df=None):
        """Get antivirus status report."""
        params = {'df': df}
        return self.get('/v2/queries/antivirus-status', params)

    def query_antivirus_threats(self, df=None):
        """Get antivirus threats report."""
        params = {'df': df}
        return self.get('/v2/queries/antivirus-threats', params)

    def query_computer_systems(self, df=None):
        """Get computer systems inventory."""
        params = {'df': df}
        return self.get('/v2/queries/computer-systems', params)

    def query_disk_drives(self, df=None):
        """Get disk drives report."""
        params = {'df': df}
        return self.get('/v2/queries/disks', params)

    def query_volumes(self, df=None):
        """Get volumes report."""
        params = {'df': df}
        return self.get('/v2/queries/volumes', params)

    def query_software(self, df=None):
        """Get software inventory report."""
        params = {'df': df}
        return self.get('/v2/queries/software', params)

    def query_os_patches(self, df=None, status=None):
        """Get OS patches report."""
        params = {'df': df, 'status': status}
        return self.get('/v2/queries/os-patches', params)

    def query_software_patches(self, df=None, status=None):
        """Get third-party software patches report."""
        params = {'df': df, 'status': status}
        return self.get('/v2/queries/software-patches', params)

    def query_windows_services(self, df=None, name=None, state=None):
        """Get Windows services report."""
        params = {'df': df, 'name': name, 'state': state}
        return self.get('/v2/queries/windows-services', params)

    def query_device_health(self, df=None):
        """Get device health report."""
        params = {'df': df}
        return self.get('/v2/queries/device-health', params)

    def query_custom_fields(self, df=None):
        """Get custom fields report."""
        params = {'df': df}
        return self.get('/v2/queries/custom-fields', params)

    def query_custom_fields_detailed(self, df=None):
        """Get detailed custom fields report."""
        params = {'df': df}
        return self.get('/v2/queries/custom-fields-detailed', params)

    def query_processors(self, df=None):
        """Get processors report."""
        params = {'df': df}
        return self.get('/v2/queries/processors', params)

    def query_network_interfaces(self, df=None):
        """Get network interfaces report."""
        params = {'df': df}
        return self.get('/v2/queries/network-interfaces', params)

    def query_logged_on_users(self, df=None):
        """Get logged on users report."""
        params = {'df': df}
        return self.get('/v2/queries/logged-on-users', params)

    def query_operating_systems(self, df=None):
        """Get operating systems report."""
        params = {'df': df}
        return self.get('/v2/queries/operating-systems', params)

    def query_raid_controllers(self, df=None):
        """Get RAID controllers report."""
        params = {'df': df}
        return self.get('/v2/queries/raid-controllers', params)

    def query_raid_drives(self, df=None):
        """Get RAID drives report."""
        params = {'df': df}
        return self.get('/v2/queries/raid-drives', params)

    def query_backup_usage(self, df=None):
        """Get backup usage report."""
        params = {'df': df}
        return self.get('/v2/queries/backup/usage', params)

    def query_policy_overrides(self, df=None):
        """Get policy overrides report."""
        params = {'df': df}
        return self.get('/v2/queries/policy-overrides', params)

    # ==================== MANAGEMENT ====================

    def reboot_device(self, device_id, reason=None):
        """Reboot a device."""
        data = {'reason': reason} if reason else {}
        return self.post(f'/v2/device/{device_id}/reboot', data)

    def run_script(self, device_id, script_id, parameters=None, run_as=None):
        """Run a script on a device."""
        data = {
            'id': script_id,
            'parameters': parameters or {},
            'runAs': run_as
        }
        return self.post(f'/v2/device/{device_id}/script/run', data)

    def scan_os_patches(self, device_id):
        """Trigger OS patch scan on device."""
        return self.post(f'/v2/device/{device_id}/os-patches/scan')

    def apply_os_patches(self, device_id):
        """Apply OS patches on device."""
        return self.post(f'/v2/device/{device_id}/os-patches/apply')

    def scan_software_patches(self, device_id):
        """Trigger software patch scan on device."""
        return self.post(f'/v2/device/{device_id}/software-patches/scan')

    def apply_software_patches(self, device_id):
        """Apply software patches on device."""
        return self.post(f'/v2/device/{device_id}/software-patches/apply')

    def control_service(self, device_id, service_name, action):
        """Control a Windows service (start/stop/restart)."""
        return self.post(f'/v2/device/{device_id}/windows-service/{service_name}/{action}')

    def set_maintenance(self, device_id, enabled, end_time=None):
        """Set maintenance mode for device."""
        data = {
            'enabled': enabled,
            'endTime': end_time
        }
        return self.post(f'/v2/device/{device_id}/maintenance', data)

    def approve_device(self, device_id, mode='APPROVE'):
        """Approve or reject a device."""
        return self.post(f'/v2/devices/approval/{mode}', {'deviceIds': [device_id]})

    def update_device(self, device_id, data):
        """Update device information."""
        return self.patch(f'/v2/device/{device_id}', data)

    # ==================== ALERTS ====================

    def list_alerts(self, df=None, source_type=None, lang=None):
        """List all alerts."""
        params = {'df': df, 'sourceType': source_type, 'lang': lang}
        return self.get('/v2/alerts', params)

    def get_alert(self, alert_uid):
        """Get alert by UID."""
        return self.get(f'/v2/alert/{alert_uid}')

    def reset_alert(self, alert_uid):
        """Reset an alert."""
        return self.post(f'/v2/alert/{alert_uid}/reset')

    def delete_alert(self, alert_uid):
        """Delete an alert."""
        return self.delete(f'/v2/alert/{alert_uid}')

    # ==================== TICKETING ====================

    def list_tickets(self, board_id=None, page_size=None, page=None):
        """List tickets."""
        params = {
            'boardId': board_id,
            'pageSize': page_size or self.defaults.get('page_size', 100),
            'page': page
        }
        return self.get('/v2/ticketing/tickets', params)

    def get_ticket(self, ticket_id):
        """Get ticket by ID."""
        return self.get(f'/v2/ticketing/ticket/{ticket_id}')

    def create_ticket(self, data):
        """Create a new ticket."""
        return self.post('/v2/ticketing/ticket', data)

    def update_ticket(self, ticket_id, data):
        """Update a ticket."""
        return self.patch(f'/v2/ticketing/ticket/{ticket_id}', data)

    def delete_ticket(self, ticket_id):
        """Delete a ticket."""
        return self.delete(f'/v2/ticketing/ticket/{ticket_id}')

    def add_ticket_comment(self, ticket_id, body, html_body=None):
        """Add a comment to a ticket."""
        data = {'body': body}
        if html_body:
            data['htmlBody'] = html_body
        return self.post(f'/v2/ticketing/ticket/{ticket_id}/comment', data)

    def get_ticket_log_entries(self, ticket_id):
        """Get log entries for a ticket."""
        return self.get(f'/v2/ticketing/ticket/{ticket_id}/log-entries')

    def list_ticket_statuses(self, board_id=None):
        """List ticket statuses."""
        params = {'boardId': board_id}
        return self.get('/v2/ticketing/statuses', params)

    def list_ticket_attributes(self):
        """List ticket attributes."""
        return self.get('/v2/ticketing/attributes')

    def list_ticket_forms(self):
        """List ticket forms."""
        return self.get('/v2/ticketing/ticket-forms')

    def list_trigger_boards(self):
        """List trigger boards."""
        return self.get('/v2/ticketing/trigger/boards')

    # ==================== POLICIES ====================

    def list_policies(self):
        """List all policies."""
        return self.get('/v2/policies')

    def get_policy(self, policy_id):
        """Get policy by ID."""
        return self.get(f'/v2/policy/{policy_id}')

    def get_device_policy_overrides(self, device_id):
        """Get policy overrides for device."""
        return self.get(f'/v2/device/{device_id}/policy/overrides')

    # ==================== WEBHOOKS ====================

    def configure_webhook(self, url, event_types=None):
        """Configure webhook."""
        data = {
            'url': url,
            'eventTypes': event_types or []
        }
        return self.put('/v2/webhook', data)

    def disable_webhook(self):
        """Disable webhook."""
        return self.delete('/v2/webhook')

    # ==================== CONTACTS ====================

    def list_contacts(self, page_size=None):
        """List all contacts."""
        params = {'pageSize': page_size or self.defaults.get('page_size', 100)}
        return self.get('/v2/contacts', params)

    def get_contact(self, contact_id):
        """Get contact by ID."""
        return self.get(f'/v2/contact/{contact_id}')

    def create_contact(self, data):
        """Create a new contact."""
        return self.post('/v2/contacts', data)

    def update_contact(self, contact_id, data):
        """Update a contact."""
        return self.patch(f'/v2/contact/{contact_id}', data)

    def delete_contact(self, contact_id):
        """Delete a contact."""
        return self.delete(f'/v2/contact/{contact_id}')

    # ==================== USERS ====================

    def list_users(self):
        """List all users."""
        return self.get('/v2/users')

    def list_technicians(self):
        """List all technicians."""
        return self.get('/v2/users/technicians')

    def list_end_users(self, org_id=None):
        """List end users."""
        params = {'organizationId': org_id}
        return self.get('/v2/users/end-users', params)

    # ==================== GROUPS ====================

    def list_groups(self):
        """List all groups."""
        return self.get('/v2/groups')

    def get_group_devices(self, group_id):
        """Get devices in a group."""
        return self.get(f'/v2/group/{group_id}/device-ids')

    # ==================== ACTIVITIES ====================

    def list_activities(self, older_than=None, newer_than=None, activity_type=None, status=None, df=None):
        """List activities."""
        params = {
            'olderThan': older_than,
            'newerThan': newer_than,
            'type': activity_type,
            'status': status,
            'df': df
        }
        return self.get('/v2/activities', params)

    # ==================== JOBS ====================

    def list_jobs(self, df=None, job_type=None):
        """List jobs."""
        params = {'df': df, 'jobType': job_type}
        return self.get('/v2/jobs', params)

    def get_device_jobs(self, device_id):
        """Get jobs for a device."""
        return self.get(f'/v2/device/{device_id}/jobs')

    # ==================== SCRIPTS ====================

    def list_scripts(self):
        """List automation scripts."""
        return self.get('/v2/automation/scripts')

    # ==================== LOCATIONS ====================

    def create_location(self, org_id, data):
        """Create a location."""
        return self.post(f'/v2/organization/{org_id}/locations', data)

    def update_location(self, org_id, location_id, data):
        """Update a location."""
        return self.patch(f'/v2/organization/{org_id}/location/{location_id}', data)

    # ==================== ROLES ====================

    def list_roles(self):
        """List all roles."""
        return self.get('/v2/roles')

    def list_node_roles(self):
        """List node roles."""
        return self.get('/v2/noderole/list')


def create_parser():
    """Create argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        description='NinjaOne RMM API CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--config', '-c', help='Path to config file')
    parser.add_argument('--format', '-f', choices=['table', 'json', 'compact', 'summary'],
                        default='table', help='Output format (default: table)')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # ==================== DEVICES ====================
    devices = subparsers.add_parser('devices', help='Device operations')
    devices_sub = devices.add_subparsers(dest='action')

    # devices list
    dev_list = devices_sub.add_parser('list', help='List all devices')
    dev_list.add_argument('--limit', '-l', type=int, help='Results per page')
    dev_list.add_argument('--filter', '--df', dest='df', help='Device filter')

    # devices get
    dev_get = devices_sub.add_parser('get', help='Get device by ID')
    dev_get.add_argument('device_id', help='Device ID')

    # devices detailed
    dev_detailed = devices_sub.add_parser('detailed', help='Get detailed device info')
    dev_detailed.add_argument('device_id', help='Device ID')

    # devices search
    dev_search = devices_sub.add_parser('search', help='Search devices')
    dev_search.add_argument('--filter', '--df', dest='df', help='Device filter')
    dev_search.add_argument('--limit', '-l', type=int, help='Results per page')

    # devices activities
    dev_activities = devices_sub.add_parser('activities', help='Get device activities')
    dev_activities.add_argument('device_id', help='Device ID')

    # devices alerts
    dev_alerts = devices_sub.add_parser('alerts', help='Get device alerts')
    dev_alerts.add_argument('device_id', help='Device ID')

    # devices software
    dev_software = devices_sub.add_parser('software', help='Get installed software')
    dev_software.add_argument('device_id', help='Device ID')

    # devices os-patches
    dev_os_patches = devices_sub.add_parser('os-patches', help='Get OS patches')
    dev_os_patches.add_argument('device_id', help='Device ID')
    dev_os_patches.add_argument('--status', help='Filter by status')

    # devices software-patches
    dev_sw_patches = devices_sub.add_parser('software-patches', help='Get software patches')
    dev_sw_patches.add_argument('device_id', help='Device ID')
    dev_sw_patches.add_argument('--status', help='Filter by status')

    # devices disks
    dev_disks = devices_sub.add_parser('disks', help='Get disk drives')
    dev_disks.add_argument('device_id', help='Device ID')

    # devices volumes
    dev_volumes = devices_sub.add_parser('volumes', help='Get volumes')
    dev_volumes.add_argument('device_id', help='Device ID')

    # devices processors
    dev_proc = devices_sub.add_parser('processors', help='Get processors')
    dev_proc.add_argument('device_id', help='Device ID')

    # devices network
    dev_net = devices_sub.add_parser('network', help='Get network interfaces')
    dev_net.add_argument('device_id', help='Device ID')

    # devices services
    dev_svc = devices_sub.add_parser('services', help='Get Windows services')
    dev_svc.add_argument('device_id', help='Device ID')
    dev_svc.add_argument('--name', help='Filter by service name')
    dev_svc.add_argument('--state', help='Filter by state')

    # devices custom-fields
    dev_cf = devices_sub.add_parser('custom-fields', help='Get custom fields')
    dev_cf.add_argument('device_id', help='Device ID')

    # ==================== ORGANIZATIONS ====================
    orgs = subparsers.add_parser('organizations', aliases=['orgs'], help='Organization operations')
    orgs_sub = orgs.add_subparsers(dest='action')

    # organizations list
    org_list = orgs_sub.add_parser('list', help='List organizations')
    org_list.add_argument('--limit', '-l', type=int, help='Results per page')

    # organizations get
    org_get = orgs_sub.add_parser('get', help='Get organization')
    org_get.add_argument('org_id', help='Organization ID')

    # organizations create
    org_create = orgs_sub.add_parser('create', help='Create organization')
    org_create.add_argument('--data', required=True, help='Organization data (JSON)')

    # organizations devices
    org_devices = orgs_sub.add_parser('devices', help='Get organization devices')
    org_devices.add_argument('org_id', help='Organization ID')

    # organizations locations
    org_locations = orgs_sub.add_parser('locations', help='Get organization locations')
    org_locations.add_argument('org_id', help='Organization ID')

    # organizations end-users
    org_users = orgs_sub.add_parser('end-users', help='Get organization end users')
    org_users.add_argument('org_id', help='Organization ID')

    # organizations custom-fields
    org_cf = orgs_sub.add_parser('custom-fields', help='Get organization custom fields')
    org_cf.add_argument('org_id', help='Organization ID')

    # ==================== QUERIES ====================
    queries = subparsers.add_parser('queries', help='Query/report operations')
    queries_sub = queries.add_subparsers(dest='action')

    # Add query commands
    for query_name in ['antivirus-status', 'antivirus-threats', 'computer-systems',
                       'disk-drives', 'volumes', 'software', 'os-patches',
                       'software-patches', 'windows-services', 'device-health',
                       'custom-fields', 'processors', 'network-interfaces',
                       'logged-on-users', 'operating-systems', 'raid-controllers',
                       'raid-drives', 'backup-usage', 'policy-overrides']:
        q = queries_sub.add_parser(query_name, help=f'Run {query_name} query')
        q.add_argument('--filter', '--df', dest='df',
                       help='Device filter (e.g., "class = WINDOWS_SERVER")')
        q.add_argument('--org-id', type=int, dest='org_id',
                       help='Filter by organization ID (convenience for --filter "org = ID")')
        q.add_argument('--org-name', dest='org_name',
                       help='Filter by organization name (looks up ID automatically)')

    # ==================== MANAGEMENT ====================
    mgmt = subparsers.add_parser('management', aliases=['mgmt'], help='Management operations')
    mgmt_sub = mgmt.add_subparsers(dest='action')

    # management reboot
    mgmt_reboot = mgmt_sub.add_parser('reboot', help='Reboot device')
    mgmt_reboot.add_argument('device_id', help='Device ID')
    mgmt_reboot.add_argument('--reason', help='Reboot reason')

    # management run-script
    mgmt_script = mgmt_sub.add_parser('run-script', help='Run script on device')
    mgmt_script.add_argument('device_id', help='Device ID')
    mgmt_script.add_argument('script_id', help='Script ID')
    mgmt_script.add_argument('--parameters', help='Script parameters (JSON)')
    mgmt_script.add_argument('--run-as', help='Run as user')

    # management scan-os-patches
    mgmt_scan_os = mgmt_sub.add_parser('scan-os-patches', help='Scan OS patches')
    mgmt_scan_os.add_argument('device_id', help='Device ID')

    # management apply-os-patches
    mgmt_apply_os = mgmt_sub.add_parser('apply-os-patches', help='Apply OS patches')
    mgmt_apply_os.add_argument('device_id', help='Device ID')

    # management scan-software-patches
    mgmt_scan_sw = mgmt_sub.add_parser('scan-software-patches', help='Scan software patches')
    mgmt_scan_sw.add_argument('device_id', help='Device ID')

    # management apply-software-patches
    mgmt_apply_sw = mgmt_sub.add_parser('apply-software-patches', help='Apply software patches')
    mgmt_apply_sw.add_argument('device_id', help='Device ID')

    # management control-service
    mgmt_svc = mgmt_sub.add_parser('control-service', help='Control Windows service')
    mgmt_svc.add_argument('device_id', help='Device ID')
    mgmt_svc.add_argument('service_name', help='Service name')
    mgmt_svc.add_argument('action', choices=['start', 'stop', 'restart'], help='Action')

    # management maintenance
    mgmt_maint = mgmt_sub.add_parser('maintenance', help='Set maintenance mode')
    mgmt_maint.add_argument('device_id', help='Device ID')
    mgmt_maint.add_argument('--enable', action='store_true', help='Enable maintenance')
    mgmt_maint.add_argument('--disable', action='store_true', help='Disable maintenance')
    mgmt_maint.add_argument('--end-time', help='End time (ISO format)')

    # management approve
    mgmt_approve = mgmt_sub.add_parser('approve', help='Approve device')
    mgmt_approve.add_argument('device_id', help='Device ID')
    mgmt_approve.add_argument('--reject', action='store_true', help='Reject instead of approve')

    # ==================== ALERTS ====================
    alerts = subparsers.add_parser('alerts', help='Alert operations')
    alerts_sub = alerts.add_subparsers(dest='action')

    # alerts list
    alert_list = alerts_sub.add_parser('list', help='List alerts')
    alert_list.add_argument('--filter', '--df', dest='df', help='Device filter')

    # alerts get
    alert_get = alerts_sub.add_parser('get', help='Get alert')
    alert_get.add_argument('alert_uid', help='Alert UID')

    # alerts reset
    alert_reset = alerts_sub.add_parser('reset', help='Reset alert')
    alert_reset.add_argument('alert_uid', help='Alert UID')

    # alerts delete
    alert_delete = alerts_sub.add_parser('delete', help='Delete alert')
    alert_delete.add_argument('alert_uid', help='Alert UID')

    # ==================== TICKETS ====================
    tickets = subparsers.add_parser('tickets', help='Ticketing operations')
    tickets_sub = tickets.add_subparsers(dest='action')

    # tickets list
    tkt_list = tickets_sub.add_parser('list', help='List tickets')
    tkt_list.add_argument('--board-id', help='Board ID')
    tkt_list.add_argument('--limit', '-l', type=int, help='Results per page')

    # tickets get
    tkt_get = tickets_sub.add_parser('get', help='Get ticket')
    tkt_get.add_argument('ticket_id', help='Ticket ID')

    # tickets create
    tkt_create = tickets_sub.add_parser('create', help='Create ticket')
    tkt_create.add_argument('--data', required=True, help='Ticket data (JSON)')

    # tickets update
    tkt_update = tickets_sub.add_parser('update', help='Update ticket')
    tkt_update.add_argument('ticket_id', help='Ticket ID')
    tkt_update.add_argument('--data', required=True, help='Update data (JSON)')

    # tickets delete
    tkt_delete = tickets_sub.add_parser('delete', help='Delete ticket')
    tkt_delete.add_argument('ticket_id', help='Ticket ID')

    # tickets add-comment
    tkt_comment = tickets_sub.add_parser('add-comment', help='Add comment to ticket')
    tkt_comment.add_argument('ticket_id', help='Ticket ID')
    tkt_comment.add_argument('body', help='Comment body')

    # tickets log
    tkt_log = tickets_sub.add_parser('log', help='Get ticket log entries')
    tkt_log.add_argument('ticket_id', help='Ticket ID')

    # tickets statuses
    tickets_sub.add_parser('statuses', help='List ticket statuses')

    # tickets attributes
    tickets_sub.add_parser('attributes', help='List ticket attributes')

    # ==================== POLICIES ====================
    policies = subparsers.add_parser('policies', help='Policy operations')
    policies_sub = policies.add_subparsers(dest='action')

    # policies list
    policies_sub.add_parser('list', help='List policies')

    # policies get
    pol_get = policies_sub.add_parser('get', help='Get policy')
    pol_get.add_argument('policy_id', help='Policy ID')

    # ==================== WEBHOOKS ====================
    webhooks = subparsers.add_parser('webhooks', help='Webhook operations')
    webhooks_sub = webhooks.add_subparsers(dest='action')

    # webhooks configure
    wh_config = webhooks_sub.add_parser('configure', help='Configure webhook')
    wh_config.add_argument('url', help='Webhook URL')
    wh_config.add_argument('--events', help='Event types (comma-separated)')

    # webhooks disable
    webhooks_sub.add_parser('disable', help='Disable webhook')

    # ==================== CONTACTS ====================
    contacts = subparsers.add_parser('contacts', help='Contact operations')
    contacts_sub = contacts.add_subparsers(dest='action')

    # contacts list
    contacts_sub.add_parser('list', help='List contacts')

    # contacts get
    con_get = contacts_sub.add_parser('get', help='Get contact')
    con_get.add_argument('contact_id', help='Contact ID')

    # contacts create
    con_create = contacts_sub.add_parser('create', help='Create contact')
    con_create.add_argument('--data', required=True, help='Contact data (JSON)')

    # contacts delete
    con_delete = contacts_sub.add_parser('delete', help='Delete contact')
    con_delete.add_argument('contact_id', help='Contact ID')

    # ==================== USERS ====================
    users = subparsers.add_parser('users', help='User operations')
    users_sub = users.add_subparsers(dest='action')

    users_sub.add_parser('list', help='List all users')
    users_sub.add_parser('technicians', help='List technicians')

    end_users = users_sub.add_parser('end-users', help='List end users')
    end_users.add_argument('--org-id', help='Filter by organization')

    # ==================== GROUPS ====================
    groups = subparsers.add_parser('groups', help='Group operations')
    groups_sub = groups.add_subparsers(dest='action')

    groups_sub.add_parser('list', help='List groups')

    grp_devices = groups_sub.add_parser('devices', help='Get devices in group')
    grp_devices.add_argument('group_id', help='Group ID')

    # ==================== ACTIVITIES ====================
    activities = subparsers.add_parser('activities', help='Activity operations')
    activities_sub = activities.add_subparsers(dest='action')

    act_list = activities_sub.add_parser('list', help='List activities')
    act_list.add_argument('--filter', '--df', dest='df', help='Device filter')
    act_list.add_argument('--type', dest='activity_type', help='Activity type')
    act_list.add_argument('--status', help='Status filter')

    # ==================== JOBS ====================
    jobs = subparsers.add_parser('jobs', help='Job operations')
    jobs_sub = jobs.add_subparsers(dest='action')

    job_list = jobs_sub.add_parser('list', help='List jobs')
    job_list.add_argument('--filter', '--df', dest='df', help='Device filter')

    job_device = jobs_sub.add_parser('device', help='Get device jobs')
    job_device.add_argument('device_id', help='Device ID')

    # ==================== SCRIPTS ====================
    scripts = subparsers.add_parser('scripts', help='Script operations')
    scripts_sub = scripts.add_subparsers(dest='action')

    scripts_sub.add_parser('list', help='List automation scripts')

    # ==================== ROLES ====================
    roles = subparsers.add_parser('roles', help='Role operations')
    roles_sub = roles.add_subparsers(dest='action')

    roles_sub.add_parser('list', help='List roles')
    roles_sub.add_parser('node-roles', help='List node roles')

    # ==================== REPORTS ====================
    reports = subparsers.add_parser('reports', help='Generate reports')
    reports_sub = reports.add_subparsers(dest='action')

    # reports hardware
    hw_report = reports_sub.add_parser('hardware',
        help='Hardware utilization report (storage & memory)')
    hw_report.add_argument('--org-id', type=int, dest='org_id',
                           help='Filter by organization ID')
    hw_report.add_argument('--org-name', dest='org_name',
                           help='Filter by organization name')
    hw_report.add_argument('--filter', '--df', dest='df',
                           help='Device filter')
    hw_report.add_argument('--storage-warning', type=int, default=80,
                           help='Storage warning threshold %% (default: 80)')
    hw_report.add_argument('--storage-critical', type=int, default=90,
                           help='Storage critical threshold %% (default: 90)')
    hw_report.add_argument('--memory-warning', type=int, default=16,
                           help='Memory warning threshold GB (default: 16)')
    hw_report.add_argument('--memory-critical', type=int, default=8,
                           help='Memory critical threshold GB (default: 8)')

    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        api = NinjaOneAPI(args.config)
        result = None
        resource_type = None

        # ==================== DEVICES ====================
        if args.command == 'devices':
            resource_type = 'devices'
            if args.action == 'list':
                result = api.list_devices(page_size=args.limit, df=args.df)
            elif args.action == 'get':
                result = api.get_device(args.device_id)
            elif args.action == 'detailed':
                result = api.get_device_detailed(args.device_id)
            elif args.action == 'search':
                result = api.search_devices(df=args.df, page_size=args.limit)
            elif args.action == 'activities':
                result = api.get_device_activities(args.device_id)
            elif args.action == 'alerts':
                result = api.get_device_alerts(args.device_id)
                resource_type = 'alerts'
            elif args.action == 'software':
                result = api.get_device_software(args.device_id)
                resource_type = 'software'
            elif args.action == 'os-patches':
                result = api.get_device_os_patches(args.device_id, status=args.status)
                resource_type = 'patches'
            elif args.action == 'software-patches':
                result = api.get_device_software_patches(args.device_id, status=args.status)
                resource_type = 'patches'
            elif args.action == 'disks':
                result = api.get_device_disks(args.device_id)
            elif args.action == 'volumes':
                result = api.get_device_volumes(args.device_id)
            elif args.action == 'processors':
                result = api.get_device_processors(args.device_id)
            elif args.action == 'network':
                result = api.get_device_network(args.device_id)
            elif args.action == 'services':
                result = api.get_device_services(args.device_id, name=args.name, state=args.state)
                resource_type = 'services'
            elif args.action == 'custom-fields':
                result = api.get_device_custom_fields(args.device_id)

        # ==================== ORGANIZATIONS ====================
        elif args.command in ('organizations', 'orgs'):
            resource_type = 'organizations'
            if args.action == 'list':
                result = api.list_organizations(page_size=args.limit)
            elif args.action == 'get':
                result = api.get_organization(args.org_id)
            elif args.action == 'create':
                data = json.loads(args.data)
                result = api.create_organization(data)
            elif args.action == 'devices':
                result = api.get_organization_devices(args.org_id)
                resource_type = 'devices'
            elif args.action == 'locations':
                result = api.get_organization_locations(args.org_id)
            elif args.action == 'end-users':
                result = api.get_organization_end_users(args.org_id)
            elif args.action == 'custom-fields':
                result = api.get_organization_custom_fields(args.org_id)

        # ==================== QUERIES ====================
        elif args.command == 'queries':
            resource_type = f'query-{args.action}'

            # Build device filter from org_id, org_name, or df
            df = args.df
            if hasattr(args, 'org_name') and args.org_name:
                org = api.find_organization_by_name(args.org_name)
                if not org:
                    raise NinjaOneAPIError(f"Organization not found: {args.org_name}")
                org_filter = f"org = {org['id']}"
                df = f"{df} AND {org_filter}" if df else org_filter
                print(f"Resolved '{args.org_name}' to organization ID {org['id']}", file=sys.stderr)
            elif hasattr(args, 'org_id') and args.org_id:
                org_filter = f"org = {args.org_id}"
                df = f"{df} AND {org_filter}" if df else org_filter

            query_map = {
                'antivirus-status': api.query_antivirus_status,
                'antivirus-threats': api.query_antivirus_threats,
                'computer-systems': api.query_computer_systems,
                'disk-drives': api.query_disk_drives,
                'volumes': api.query_volumes,
                'software': api.query_software,
                'os-patches': api.query_os_patches,
                'software-patches': api.query_software_patches,
                'windows-services': api.query_windows_services,
                'device-health': api.query_device_health,
                'custom-fields': api.query_custom_fields,
                'processors': api.query_processors,
                'network-interfaces': api.query_network_interfaces,
                'logged-on-users': api.query_logged_on_users,
                'operating-systems': api.query_operating_systems,
                'raid-controllers': api.query_raid_controllers,
                'raid-drives': api.query_raid_drives,
                'backup-usage': api.query_backup_usage,
                'policy-overrides': api.query_policy_overrides,
            }
            if args.action in query_map:
                result = query_map[args.action](df=df)

        # ==================== MANAGEMENT ====================
        elif args.command in ('management', 'mgmt'):
            if args.action == 'reboot':
                result = api.reboot_device(args.device_id, reason=args.reason)
            elif args.action == 'run-script':
                params = json.loads(args.parameters) if args.parameters else None
                result = api.run_script(args.device_id, args.script_id, parameters=params, run_as=args.run_as)
            elif args.action == 'scan-os-patches':
                result = api.scan_os_patches(args.device_id)
            elif args.action == 'apply-os-patches':
                result = api.apply_os_patches(args.device_id)
            elif args.action == 'scan-software-patches':
                result = api.scan_software_patches(args.device_id)
            elif args.action == 'apply-software-patches':
                result = api.apply_software_patches(args.device_id)
            elif args.action == 'control-service':
                result = api.control_service(args.device_id, args.service_name, args.action)
            elif args.action == 'maintenance':
                enabled = args.enable or not args.disable
                result = api.set_maintenance(args.device_id, enabled, end_time=args.end_time)
            elif args.action == 'approve':
                mode = 'REJECT' if args.reject else 'APPROVE'
                result = api.approve_device(args.device_id, mode=mode)

        # ==================== ALERTS ====================
        elif args.command == 'alerts':
            resource_type = 'alerts'
            if args.action == 'list':
                result = api.list_alerts(df=args.df)
            elif args.action == 'get':
                result = api.get_alert(args.alert_uid)
            elif args.action == 'reset':
                result = api.reset_alert(args.alert_uid)
            elif args.action == 'delete':
                result = api.delete_alert(args.alert_uid)

        # ==================== TICKETS ====================
        elif args.command == 'tickets':
            resource_type = 'tickets'
            if args.action == 'list':
                result = api.list_tickets(board_id=args.board_id, page_size=args.limit)
            elif args.action == 'get':
                result = api.get_ticket(args.ticket_id)
            elif args.action == 'create':
                data = json.loads(args.data)
                result = api.create_ticket(data)
            elif args.action == 'update':
                data = json.loads(args.data)
                result = api.update_ticket(args.ticket_id, data)
            elif args.action == 'delete':
                result = api.delete_ticket(args.ticket_id)
            elif args.action == 'add-comment':
                result = api.add_ticket_comment(args.ticket_id, args.body)
            elif args.action == 'log':
                result = api.get_ticket_log_entries(args.ticket_id)
            elif args.action == 'statuses':
                result = api.list_ticket_statuses()
            elif args.action == 'attributes':
                result = api.list_ticket_attributes()

        # ==================== POLICIES ====================
        elif args.command == 'policies':
            resource_type = 'policies'
            if args.action == 'list':
                result = api.list_policies()
            elif args.action == 'get':
                result = api.get_policy(args.policy_id)

        # ==================== WEBHOOKS ====================
        elif args.command == 'webhooks':
            if args.action == 'configure':
                events = args.events.split(',') if args.events else None
                result = api.configure_webhook(args.url, event_types=events)
            elif args.action == 'disable':
                result = api.disable_webhook()

        # ==================== CONTACTS ====================
        elif args.command == 'contacts':
            if args.action == 'list':
                result = api.list_contacts()
            elif args.action == 'get':
                result = api.get_contact(args.contact_id)
            elif args.action == 'create':
                data = json.loads(args.data)
                result = api.create_contact(data)
            elif args.action == 'delete':
                result = api.delete_contact(args.contact_id)

        # ==================== USERS ====================
        elif args.command == 'users':
            if args.action == 'list':
                result = api.list_users()
            elif args.action == 'technicians':
                result = api.list_technicians()
            elif args.action == 'end-users':
                result = api.list_end_users(org_id=args.org_id)

        # ==================== GROUPS ====================
        elif args.command == 'groups':
            if args.action == 'list':
                result = api.list_groups()
            elif args.action == 'devices':
                result = api.get_group_devices(args.group_id)

        # ==================== ACTIVITIES ====================
        elif args.command == 'activities':
            if args.action == 'list':
                result = api.list_activities(df=args.df, activity_type=args.activity_type, status=args.status)

        # ==================== JOBS ====================
        elif args.command == 'jobs':
            if args.action == 'list':
                result = api.list_jobs(df=args.df)
            elif args.action == 'device':
                result = api.get_device_jobs(args.device_id)

        # ==================== SCRIPTS ====================
        elif args.command == 'scripts':
            if args.action == 'list':
                result = api.list_scripts()

        # ==================== ROLES ====================
        elif args.command == 'roles':
            if args.action == 'list':
                result = api.list_roles()
            elif args.action == 'node-roles':
                result = api.list_node_roles()

        # ==================== REPORTS ====================
        elif args.command == 'reports':
            if args.action == 'hardware':
                # Build device filter
                df = args.df
                org_name_resolved = None
                if args.org_name:
                    org = api.find_organization_by_name(args.org_name)
                    if not org:
                        raise NinjaOneAPIError(f"Organization not found: {args.org_name}")
                    org_filter = f"org = {org['id']}"
                    df = f"{df} AND {org_filter}" if df else org_filter
                    org_name_resolved = org.get('name', args.org_name)
                elif args.org_id:
                    org_filter = f"org = {args.org_id}"
                    df = f"{df} AND {org_filter}" if df else org_filter

                # Gather data
                print("Gathering hardware data...", file=sys.stderr)
                volumes_response = api.query_volumes(df=df)
                systems_response = api.query_computer_systems(df=df)

                # Handle wrapped results
                volumes_data = volumes_response.get('results', volumes_response) if isinstance(volumes_response, dict) else volumes_response
                systems_data = systems_response.get('results', systems_response) if isinstance(systems_response, dict) else systems_response

                # Build device lookup from systems
                device_info = {}
                for sys_rec in systems_data:
                    dev_id = sys_rec.get('deviceId')
                    if dev_id:
                        ram_gb = sys_rec.get('totalPhysicalMemory', 0) / (1024**3)
                        device_info[dev_id] = {
                            'name': sys_rec.get('name', sys_rec.get('dnsHostName', f'Device {dev_id}')),
                            'ram_gb': ram_gb,
                            'manufacturer': sys_rec.get('manufacturer', 'Unknown'),
                            'model': sys_rec.get('model', 'Unknown'),
                        }

                # System partition patterns to ignore
                system_partition_patterns = [
                    'Recovery',           # Windows Recovery partition
                    'EFI',                # EFI System Partition
                    'SYSTEM_DRV',         # Dell system partition
                    'System Reserved',    # Windows system reserved
                    'LVM2_member',        # Linux LVM metadata
                    '/boot',              # Linux boot partition
                    '/System/Volumes',    # macOS system volumes
                    'Preboot',            # macOS preboot
                    'VM',                 # macOS VM partition
                    'Update',             # macOS/Windows update partitions
                ]

                def is_system_partition(vol):
                    """Check if volume is a system/recovery partition to ignore."""
                    name = vol.get('name', '')
                    label = vol.get('label', '')
                    drive_letter = vol.get('driveLetter', '')
                    capacity = vol.get('capacity', 0)

                    # Skip very small partitions (< 1GB) - likely system partitions
                    if capacity < 1 * (1024**3):
                        return True

                    # Skip partitions with no drive letter on Windows (except named data volumes)
                    if not drive_letter and vol.get('deviceType') == 'Local Disk':
                        return True

                    # Check against known system partition patterns
                    for pattern in system_partition_patterns:
                        if pattern.lower() in name.lower() or pattern.lower() in label.lower():
                            return True

                    return False

                # Analyze storage
                storage_issues = {'critical': [], 'warning': []}
                for vol in volumes_data:
                    # Skip system partitions
                    if is_system_partition(vol):
                        continue

                    dev_id = vol.get('deviceId')
                    capacity = vol.get('capacity', 0)
                    free_space = vol.get('freeSpace', 0)
                    if capacity > 0:
                        used_pct = ((capacity - free_space) / capacity) * 100
                        vol_info = {
                            'device_id': dev_id,
                            'device_name': device_info.get(dev_id, {}).get('name', f'Device {dev_id}'),
                            'drive': vol.get('driveLetter') or vol.get('name', 'Unknown'),
                            'label': vol.get('label', ''),
                            'capacity_gb': round(capacity / (1024**3), 1),
                            'free_gb': round(free_space / (1024**3), 1),
                            'used_pct': round(used_pct, 1),
                        }
                        if used_pct >= args.storage_critical:
                            storage_issues['critical'].append(vol_info)
                        elif used_pct >= args.storage_warning:
                            storage_issues['warning'].append(vol_info)

                # Analyze memory
                memory_issues = {'critical': [], 'warning': []}
                for dev_id, info in device_info.items():
                    ram_gb = info['ram_gb']
                    mem_info = {
                        'device_id': dev_id,
                        'device_name': info['name'],
                        'ram_gb': round(ram_gb, 1),
                        'manufacturer': info['manufacturer'],
                        'model': info['model'],
                    }
                    if ram_gb < args.memory_critical:
                        memory_issues['critical'].append(mem_info)
                    elif ram_gb < args.memory_warning:
                        memory_issues['warning'].append(mem_info)

                # Generate report
                org_display = org_name_resolved if org_name_resolved else (f'Org ID {args.org_id}' if args.org_id else 'All Organizations')
                report = {
                    'summary': {
                        'organization': org_display,
                        'total_devices': len(device_info),
                        'storage_critical_count': len(storage_issues['critical']),
                        'storage_warning_count': len(storage_issues['warning']),
                        'memory_critical_count': len(memory_issues['critical']),
                        'memory_warning_count': len(memory_issues['warning']),
                        'thresholds': {
                            'storage_warning_pct': args.storage_warning,
                            'storage_critical_pct': args.storage_critical,
                            'memory_warning_gb': args.memory_warning,
                            'memory_critical_gb': args.memory_critical,
                        }
                    },
                    'storage_issues': storage_issues,
                    'memory_issues': memory_issues,
                }

                # Sort by severity
                for level in ['critical', 'warning']:
                    report['storage_issues'][level].sort(key=lambda x: -x['used_pct'])
                    report['memory_issues'][level].sort(key=lambda x: x['ram_gb'])

                result = report
                resource_type = 'hardware-report'

        # Output result
        if result is not None:
            format_output(result, args.format, resource_type)
        else:
            print("No action specified. Use --help for available commands.")

    except NinjaOneAuthError as e:
        print(f"Authentication error: {e}", file=sys.stderr)
        sys.exit(1)
    except NinjaOneAPIError as e:
        print(f"API error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
