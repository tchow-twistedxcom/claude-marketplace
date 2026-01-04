#!/usr/bin/env python3
"""
Mimecast API CLI

Command-line interface for Mimecast email security API operations.
Covers email security, user/group management, policy management, and reporting.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mimecast_auth import MimecastAuth
from mimecast_client import MimecastClient, MimecastError, create_client
from mimecast_formatter import format_output, print_json


class MimecastAPI:
    """Mimecast API client with all operations."""

    def __init__(self, profile=None):
        """Initialize API client with authentication."""
        self.client = create_client(profile=profile)

    # ==================== ACCOUNT ====================

    def get_account_info(self):
        """Get account information."""
        return self.client.get("/api/account/get-account")

    # ==================== DOMAIN MANAGEMENT (API 1.0) ====================

    def list_internal_domains(self):
        """List internal domains (API 1.0)."""
        return self.client.get("/api/domain/get-internal-domain")

    def get_domain(self, domain_id):
        """Get domain details by ID (API 1.0)."""
        data = {"id": domain_id}
        return self.client.get("/api/domain/get-internal-domain", data)

    # ==================== API 2.0 ENDPOINTS ====================
    # These use OAuth 2.0 authentication with the services.mimecast.com base URL

    # -------------------- Domain Management (API 2.0) --------------------

    def list_external_domains_v2(self):
        """List external domains (API 2.0 - Email Security Onboarding)."""
        return self.client.get_v2("/domain/cloud-gateway/v1/external-domains")

    def list_internal_domains_v2(self):
        """List internal domains (API 2.0 - Domain Management)."""
        return self.client.get_v2("/domain/cloud-gateway/v1/internal-domains")

    # -------------------- Directory Management (API 2.0) --------------------

    def list_groups_v2(self):
        """List directory groups (API 2.0 - Directory Management)."""
        return self.client.get_v2("/directory/cloud-gateway/v1/groups")

    def list_users_v2(self):
        """List users (API 2.0 - User Management)."""
        return self.client.get_v2("/user/cloud-gateway/v1/users")

    # -------------------- Policy Management (API 2.0) --------------------

    def list_greylisting_policies_v2(self):
        """List greylisting policies (API 2.0 - Email Security Onboarding)."""
        return self.client.get_v2("/policy-management/cloud-gateway/v1/greylisting/policies")

    # -------------------- TTP Security Events (API 2.0) --------------------

    def get_ttp_url_logs_v2(self, start, end, scan_result=None, route=None):
        """
        Get TTP URL protection logs (API 2.0 - Security Events).

        Args:
            start: Start date (YYYY-MM-DD or ISO format)
            end: End date (YYYY-MM-DD or ISO format)
            scan_result: Filter by result (clean, malicious, etc.)
            route: Filter by route (inbound, outbound, internal)
        """
        # Convert dates to ISO format if needed
        if start and 'T' not in start:
            start = f"{start}T00:00:00+0000"
        if end and 'T' not in end:
            end = f"{end}T23:59:59+0000"

        data = {"from": start, "to": end}
        if scan_result:
            data["scanResult"] = scan_result
        if route:
            data["route"] = route
        return self.client.post("/api/ttp/url/get-logs", data)

    def get_ttp_attachment_logs_v2(self, start, end, result=None, route=None):
        """
        Get TTP attachment protection logs (API 2.0 - Security Events).

        Args:
            start: Start date (YYYY-MM-DD or ISO format)
            end: End date (YYYY-MM-DD or ISO format)
            result: Filter by result (safe, malicious, etc.)
            route: Filter by route (inbound, outbound, internal)
        """
        if start and 'T' not in start:
            start = f"{start}T00:00:00+0000"
        if end and 'T' not in end:
            end = f"{end}T23:59:59+0000"

        data = {"from": start, "to": end}
        if result:
            data["result"] = result
        if route:
            data["route"] = route
        return self.client.post("/api/ttp/attachment/get-logs", data)

    def get_ttp_impersonation_logs_v2(self, start, end, action=None):
        """
        Get TTP impersonation protection logs (API 2.0 - Security Events).

        Args:
            start: Start date (YYYY-MM-DD or ISO format)
            end: End date (YYYY-MM-DD or ISO format)
            action: Filter by action taken
        """
        if start and 'T' not in start:
            start = f"{start}T00:00:00+0000"
        if end and 'T' not in end:
            end = f"{end}T23:59:59+0000"

        data = {"from": start, "to": end}
        if action:
            data["action"] = action
        return self.client.post("/api/ttp/impersonation/get-logs", data)

    def decode_ttp_url(self, url):
        """
        Decode a TTP-rewritten URL to get the original URL.

        Args:
            url: The TTP-rewritten URL to decode
        """
        return self.client.post("/api/ttp/url/decode-url", {"url": url})

    # -------------------- Managed URLs (URL Whitelist/Blacklist) --------------------

    def get_managed_urls(self, url_filter=None):
        """
        Get list of managed URLs (permitted/blocked).

        Args:
            url_filter: Optional URL pattern to filter results
        """
        data = {}
        if url_filter:
            data["url"] = url_filter
        return self.client.post("/api/ttp/url/get-managed-urls", data)

    def create_managed_url(self, url, action="permit", match_type="explicit",
                           comment=None, disable_rewrite=False, disable_log_click=False):
        """
        Add a URL to the managed URLs list (whitelist/blacklist).

        Args:
            url: The URL to manage (e.g., "http://vendors.com")
            action: "permit" (whitelist) or "block" (blacklist)
            match_type: "explicit" (exact match) or "domain" (all URLs on domain)
            comment: Optional comment/reason for the entry
            disable_rewrite: If True, don't rewrite the URL
            disable_log_click: If True, don't log clicks on this URL

        Returns:
            API response with created managed URL details
        """
        data = {
            "url": url,
            "action": action,
            "matchType": match_type,
        }
        if comment:
            data["comment"] = comment
        if disable_rewrite:
            data["disableRewrite"] = True
        if disable_log_click:
            data["disableLogClick"] = True

        return self.client.post("/api/ttp/url/create-managed-url", data)

    def delete_managed_url(self, url_id):
        """
        Delete a managed URL entry.

        Args:
            url_id: The ID of the managed URL to delete
        """
        return self.client.post("/api/ttp/url/delete-managed-url", {"id": url_id})

    # -------------------- Audit Events (API 2.0) --------------------

    def get_audit_events_v2(self, start, end, audit_type=None):
        """
        Get audit events (API 2.0 - Audit & Reporting).

        Args:
            start: Start date (YYYY-MM-DD or ISO format)
            end: End date (YYYY-MM-DD or ISO format)
            audit_type: Filter by audit type
        """
        if start and 'T' not in start:
            start = f"{start}T00:00:00+0000"
        if end and 'T' not in end:
            end = f"{end}T23:59:59+0000"

        data = {"startDateTime": start, "endDateTime": end}
        if audit_type:
            data["auditType"] = audit_type
        return self.client.post("/api/audit/get-audit-events", data)

    # -------------------- Message Tracking (API 2.0) --------------------

    def search_messages_v2(self, start, end, sender=None, recipient=None, subject=None,
                           message_id=None, route=None):
        """
        Search message tracking (API 2.0 - Message Finder).

        Args:
            start: Start date (YYYY-MM-DD or ISO format)
            end: End date (YYYY-MM-DD or ISO format)
            sender: Filter by sender address
            recipient: Filter by recipient address
            subject: Filter by subject
            message_id: Specific message ID to find
            route: Filter by route (inbound, outbound, internal)
        """
        if start and 'T' not in start:
            start = f"{start}T00:00:00+0000"
        if end and 'T' not in end:
            end = f"{end}T23:59:59+0000"

        if message_id:
            data = {"messageId": message_id}
        else:
            options = {"from": start, "to": end}
            if sender:
                options["senderAddress"] = sender
            if recipient:
                options["recipientAddress"] = recipient
            if subject:
                options["subject"] = subject
            if route:
                options["route"] = route
            data = {"advancedTrackAndTraceOptions": options}

        return self.client.post("/api/message-finder/search", data)

    # -------------------- Held Messages (API 2.0) --------------------

    def get_held_messages_v2(self, admin=True, start=None, end=None):
        """
        Get held messages (API 2.0 - Gateway).

        Args:
            admin: If True, get admin held queue
            start: Start date
            end: End date
        """
        data = {"admin": admin}
        if start:
            if 'T' not in start:
                start = f"{start}T00:00:00+0000"
            data["start"] = start
        if end:
            if 'T' not in end:
                end = f"{end}T23:59:59+0000"
            data["end"] = end
        return self.client.post("/api/gateway/get-hold-message-list", data)

    def release_held_message_v2(self, message_id, reason=None):
        """
        Release a held message (API 2.0 - Gateway).

        Args:
            message_id: ID of the held message
            reason: Release reason
        """
        data = {"id": message_id}
        if reason:
            data["reasonId"] = reason
        return self.client.post("/api/gateway/hold/release", data)

    # -------------------- Internal Users (API 2.0) --------------------

    def list_internal_users_v2(self, domain=None):
        """
        List internal users (API 2.0 - User Management).

        Args:
            domain: Filter by domain
        """
        data = {}
        if domain:
            data["domain"] = domain
        return self.client.post("/api/user/get-internal-users", data)

    # ==================== EMAIL SECURITY ====================

    def search_messages(self, search_by=None, value=None, start=None, end=None):
        """
        Search message tracking logs.

        Args:
            search_by: Field to search (from, to, subject, messageId, etc.)
            value: Search value
            start: Start date (ISO format or YYYY-MM-DD)
            end: End date (ISO format or YYYY-MM-DD)
        """
        data = {}
        if search_by and value:
            data["searchBy"] = {search_by: value}
        if start:
            data["start"] = start
        if end:
            data["end"] = end
        return self.client.get("/api/message-finder/search", data)

    def get_message_info(self, message_id):
        """Get detailed message information."""
        data = {"id": message_id}
        return self.client.get("/api/message/get-message-info", data)

    def get_held_messages(self, admin=False, start=None, end=None):
        """
        Get held messages list.

        Args:
            admin: If True, get admin held queue (default: user queue)
            start: Start date
            end: End date
        """
        data = {"admin": admin}
        if start:
            data["start"] = start
        if end:
            data["end"] = end
        return self.client.get("/api/gateway/get-hold-message-list", data)

    def release_held_message(self, message_id, reason_id=None):
        """
        Release a held message.

        Args:
            message_id: ID of held message
            reason_id: Optional release reason ID
        """
        data = {"id": message_id}
        if reason_id:
            data["reasonId"] = reason_id
        return self.client.post("/api/gateway/hold/release", data)

    def get_ttp_url_logs(self, start=None, end=None, route=None, scan_result=None):
        """
        Get TTP URL protection logs.

        Args:
            start: Start date (ISO format)
            end: End date (ISO format)
            route: Filter by route (inbound, outbound, internal)
            scan_result: Filter by result (clean, malicious, etc.)
        """
        data = {}
        if start:
            data["from"] = start
        if end:
            data["to"] = end
        if route:
            data["route"] = route
        if scan_result:
            data["scanResult"] = scan_result
        return self.client.get("/api/ttp/url/get-logs", data)

    def get_ttp_attachment_logs(self, start=None, end=None, route=None, result=None):
        """
        Get TTP attachment protection logs.

        Args:
            start: Start date (ISO format)
            end: End date (ISO format)
            route: Filter by route
            result: Filter by scan result
        """
        data = {}
        if start:
            data["from"] = start
        if end:
            data["to"] = end
        if route:
            data["route"] = route
        if result:
            data["result"] = result
        return self.client.get("/api/ttp/attachment/get-logs", data)

    def get_ttp_impersonation_logs(self, start=None, end=None, action=None):
        """
        Get TTP impersonation protection logs.

        Args:
            start: Start date
            end: End date
            action: Filter by action taken
        """
        data = {}
        if start:
            data["from"] = start
        if end:
            data["to"] = end
        if action:
            data["action"] = action
        return self.client.get("/api/ttp/impersonation/get-logs", data)

    def search_archive(self, query=None, start=None, end=None, sender=None,
                        recipient=None, subject=None, admin=False):
        """
        Search email archive using XML query format.

        Args:
            query: Raw XML query (overrides other params if provided)
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            sender: Filter by sender address
            recipient: Filter by recipient address
            subject: Filter by subject
            admin: If True, search all mailboxes (requires Archive|Search|Read permission)
        """
        # Build XML query if not provided
        if not query:
            xml_parts = ['<xmlquery trace="false">']
            xml_parts.append('<searchsource source="cloud"/>')

            if start:
                xml_parts.append(f'<mfromdate>{start}T00:00:00+0000</mfromdate>')
            if end:
                xml_parts.append(f'<mtodate>{end}T23:59:59+0000</mtodate>')
            if sender:
                xml_parts.append(f'<from><address displayable="true" headerencoded="false">{sender}</address></from>')
            if recipient:
                xml_parts.append(f'<to><address displayable="true" headerencoded="false">{recipient}</address></to>')
            if subject:
                xml_parts.append(f'<subject>{subject}</subject>')

            # Select fields to return
            xml_parts.append('<select>')
            xml_parts.append('<id/><smash/><status/><displayfrom/><displayto/><subject/><receiveddate/><size/><attachmentcount/>')
            xml_parts.append('</select>')
            xml_parts.append('</xmlquery>')
            query = ''.join(xml_parts)

        data = {"query": query, "admin": admin}
        return self.client.get("/api/archive/search", data)

    def get_archive_message_list(self, view="INBOX", mailbox=None, start=None, end=None):
        """
        Get message list from archive.

        Args:
            view: INBOX or SENT (required)
            mailbox: Email address (optional, defaults to logged-in user)
            start: Start date (format: YYYY-MM-DDTHH:MM:SS+0000)
            end: End date (format: YYYY-MM-DDTHH:MM:SS+0000)
        """
        data = {"view": view.upper()}
        if mailbox:
            data["mailbox"] = mailbox
        if start:
            # Convert YYYY-MM-DD to API format if needed
            if "T" not in start:
                start = f"{start}T00:00:00+0000"
            data["start"] = start
        if end:
            if "T" not in end:
                end = f"{end}T23:59:59+0000"
            data["end"] = end
        return self.client.get("/api/archive/get-message-list", data)

    def get_archive_message_detail(self, message_id):
        """
        Get archived message detail.

        Args:
            message_id: Archive message ID
        """
        data = {"id": message_id}
        return self.client.get("/api/archive/get-message-detail", data)

    def get_archive_message_part(self, message_id, part="message"):
        """
        Get message part (body or attachment).

        Args:
            message_id: Archive message ID
            part: Part to retrieve (message, attachment, etc.)
        """
        data = {"id": message_id, "part": part}
        return self.client.get("/api/archive/get-message-part", data)

    # ==================== USER MANAGEMENT ====================

    def list_users(self, domain=None):
        """
        List internal users.

        Args:
            domain: Filter by domain
        """
        data = {}
        if domain:
            data["domain"] = domain
        return self.client.get("/api/user/get-internal-users", data)

    def create_user(self, email, name=None, domain=None):
        """
        Create internal user.

        Args:
            email: User email address
            name: Display name
            domain: Domain for the user
        """
        data = {"emailAddress": email}
        if name:
            data["name"] = name
        if domain:
            data["domain"] = domain
        return self.client.post("/api/user/create-internal-user", data)

    def update_user(self, email, name=None, alias=None):
        """
        Update internal user.

        Args:
            email: User email address
            name: New display name
            alias: Email alias
        """
        data = {"emailAddress": email}
        if name:
            data["name"] = name
        if alias:
            data["alias"] = alias
        return self.client.post("/api/user/update-internal-user", data)

    def delete_user(self, email):
        """
        Delete internal user.

        Args:
            email: User email address
        """
        data = {"emailAddress": email}
        return self.client.post("/api/user/delete-internal-user", data)

    # ==================== GROUP MANAGEMENT ====================

    def list_groups(self):
        """List directory groups."""
        return self.client.get("/api/directory/get-groups")

    def create_group(self, description):
        """
        Create directory group.

        Args:
            description: Group description/name
        """
        data = {"description": description}
        return self.client.post("/api/directory/create-group", data)

    def add_group_member(self, group_id, email):
        """
        Add member to group.

        Args:
            group_id: Group ID
            email: Member email address
        """
        data = {"id": group_id, "emailAddress": email}
        return self.client.post("/api/directory/add-group-member", data)

    def remove_group_member(self, group_id, email):
        """
        Remove member from group.

        Args:
            group_id: Group ID
            email: Member email address
        """
        data = {"id": group_id, "emailAddress": email}
        return self.client.post("/api/directory/remove-group-member", data)

    # ==================== POLICY MANAGEMENT ====================

    def list_policies(self, policy_type=None):
        """
        List policies.

        Args:
            policy_type: Filter by policy type
        """
        data = {}
        if policy_type:
            data["type"] = policy_type
        return self.client.get("/api/policy/get-policies", data)

    def create_block_sender_policy(self, sender_email, description=None):
        """
        Create blocked sender policy.

        Args:
            sender_email: Email address to block
            description: Policy description
        """
        data = {
            "option": "block_sender",
            "policy": {
                "description": description or f"Block {sender_email}",
                "fromPart": "envelope_from",
                "fromType": "individual_email_address",
                "fromValue": sender_email
            }
        }
        return self.client.post("/api/policy/blockedsenders/create-policy", data)

    def create_permit_sender_policy(self, sender_email, description=None):
        """
        Create permitted sender policy.

        Args:
            sender_email: Email address to permit
            description: Policy description
        """
        data = {
            "option": "permit_sender",
            "policy": {
                "description": description or f"Permit {sender_email}",
                "fromPart": "envelope_from",
                "fromType": "individual_email_address",
                "fromValue": sender_email
            }
        }
        return self.client.post("/api/policy/permitsenders/create-policy", data)

    def get_anti_spoofing_policy(self):
        """Get anti-spoofing bypass policy."""
        return self.client.get("/api/policy/antispoofing-bypass/get-policy")

    def list_policy_definitions(self):
        """List available policy definitions."""
        return self.client.get("/api/policy/get-definitions")

    # ==================== QUARANTINE ====================

    def get_quarantine_messages(self, start=None, end=None, view="admin"):
        """
        Get quarantine messages list.

        Args:
            start: Start date (YYYY-MM-DD or ISO format)
            end: End date (YYYY-MM-DD or ISO format)
            view: View type (admin, user)
        """
        data = {"admin": view == "admin"}
        if start:
            if 'T' not in start:
                start = f"{start}T00:00:00+0000"
            data["start"] = start
        if end:
            if 'T' not in end:
                end = f"{end}T23:59:59+0000"
            data["end"] = end
        return self.client.post("/api/managedsender/get-hold-message-list", data)

    def release_quarantine_message(self, message_id, reason=None):
        """
        Release a message from quarantine.

        Args:
            message_id: ID of quarantined message
            reason: Release reason
        """
        data = {"id": message_id}
        if reason:
            data["reasonId"] = reason
        return self.client.post("/api/gateway/hold/release", data)

    def delete_quarantine_message(self, message_id):
        """
        Delete a message from quarantine.

        Args:
            message_id: ID of quarantined message
        """
        data = {"id": message_id}
        return self.client.post("/api/gateway/hold/delete", data)

    # ==================== MANAGED/BLOCKED SENDERS ====================

    def get_blocked_senders(self, policy_type=None):
        """
        Get blocked senders list.

        Args:
            policy_type: Filter by policy type
        """
        data = {"type": "blockedsenders"}
        if policy_type:
            data["policyType"] = policy_type
        return self.client.post("/api/policy/blockedsenders/get-policy", data)

    def get_permitted_senders(self, policy_type=None):
        """
        Get permitted senders list.

        Args:
            policy_type: Filter by policy type
        """
        data = {"type": "permitsenders"}
        if policy_type:
            data["policyType"] = policy_type
        return self.client.post("/api/policy/permitsenders/get-policy", data)

    def delete_blocked_sender(self, policy_id):
        """
        Delete a blocked sender policy.

        Args:
            policy_id: ID of the policy to delete
        """
        data = {"id": policy_id}
        return self.client.post("/api/policy/blockedsenders/delete-policy", data)

    def delete_permitted_sender(self, policy_id):
        """
        Delete a permitted sender policy.

        Args:
            policy_id: ID of the policy to delete
        """
        data = {"id": policy_id}
        return self.client.post("/api/policy/permitsenders/delete-policy", data)

    # ==================== DKIM ====================

    def get_dkim_status(self, domain=None):
        """
        Get DKIM signing status.

        Args:
            domain: Filter by domain
        """
        data = {}
        if domain:
            data["domain"] = domain
        return self.client.post("/api/dkim/get-dkim", data)

    def create_dkim(self, domain, selector=None):
        """
        Create DKIM configuration for a domain.

        Args:
            domain: Domain to configure DKIM for
            selector: DKIM selector (optional)
        """
        data = {"domain": domain}
        if selector:
            data["selector"] = selector
        return self.client.post("/api/dkim/create-dkim", data)

    # ==================== MESSAGE DELIVERY ====================

    def get_message_delivery_info(self, message_id):
        """
        Get detailed delivery information for a message.

        Args:
            message_id: Message ID to look up
        """
        data = {"id": message_id}
        return self.client.post("/api/message/get-message-info", data)

    def get_delivery_routes(self):
        """Get configured delivery routes."""
        return self.client.get("/api/gateway/get-delivery-routes")

    # ==================== REJECTION LOGS ====================

    def get_rejection_logs(self, start=None, end=None, reject_type=None):
        """
        Get message rejection logs.

        Args:
            start: Start date (YYYY-MM-DD or ISO format)
            end: End date (YYYY-MM-DD or ISO format)
            reject_type: Filter by rejection type
        """
        if start and 'T' not in start:
            start = f"{start}T00:00:00+0000"
        if end and 'T' not in end:
            end = f"{end}T23:59:59+0000"

        data = {}
        if start:
            data["from"] = start
        if end:
            data["to"] = end
        if reject_type:
            data["rejectType"] = reject_type
        return self.client.post("/api/gateway/get-rejection-logs", data)

    # ==================== REPORTING ====================

    def get_audit_events(self, start=None, end=None, audit_type=None):
        """
        Get audit events.

        Args:
            start: Start date
            end: End date
            audit_type: Filter by audit type
        """
        data = {}
        if start:
            data["startDateTime"] = start
        if end:
            data["endDateTime"] = end
        if audit_type:
            data["auditType"] = audit_type
        return self.client.get("/api/audit/get-audit-events", data)

    def get_siem_logs(self, log_type="receipt", start=None, end=None, file_format="key_value"):
        """
        Get SIEM logs for export.

        Args:
            log_type: Log type (receipt, process, delivery, ttp, etc.)
            start: Start date
            end: End date
            file_format: Output format (key_value, json)
        """
        data = {"type": log_type, "fileFormat": file_format}
        if start:
            data["startDateTime"] = start
        if end:
            data["endDateTime"] = end
        return self.client.get("/api/audit/get-siem-logs", data)

    def get_threat_intel(self, feed=None):
        """
        Get threat intelligence feed.

        Args:
            feed: Specific feed to retrieve
        """
        data = {}
        if feed:
            data["feedType"] = feed
        return self.client.get("/api/ttp/threat-intel/get-intel", data)


# ==================== DATE RANGE HELPERS ====================

def _get_cst_now():
    """Get current datetime in CST/CDT timezone."""
    from datetime import timezone
    # CST is UTC-6, CDT is UTC-5
    # For simplicity, we'll use UTC-6 (CST) as the base
    # A more robust solution would use pytz or zoneinfo
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Chicago"))
    except ImportError:
        # Fallback: manually offset by 6 hours for CST
        utc_now = datetime.now(timezone.utc)
        cst_offset = timedelta(hours=-6)
        return utc_now + cst_offset


def _resolve_date_range(args):
    """
    Resolve date range from various shortcut arguments.

    Supports:
        --days N     : Last N days
        --hours N    : Last N hours
        --today      : Today only
        --yesterday  : Yesterday only
        --week       : Last 7 days
        --month      : Last 30 days
        --start/--end: Explicit dates (takes precedence)

    Returns:
        Tuple of (start_date, end_date) as YYYY-MM-DD strings (in CST)
    """
    now = _get_cst_now()
    today = now.strftime('%Y-%m-%d')

    # Explicit dates take precedence
    start = getattr(args, 'start', None)
    end = getattr(args, 'end', None)

    if start and end:
        return start, end

    # Handle shortcuts
    if getattr(args, 'today', False):
        return today, today

    if getattr(args, 'yesterday', False):
        yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        return yesterday, yesterday

    if getattr(args, 'week', False):
        start = (now - timedelta(days=7)).strftime('%Y-%m-%d')
        return start, today

    if getattr(args, 'month', False):
        start = (now - timedelta(days=30)).strftime('%Y-%m-%d')
        return start, today

    days = getattr(args, 'days', None)
    if days:
        start = (now - timedelta(days=days)).strftime('%Y-%m-%d')
        return start, today

    hours = getattr(args, 'hours', None)
    if hours:
        start_dt = now - timedelta(hours=hours)
        start = start_dt.strftime('%Y-%m-%d')
        return start, today

    # Fall back to explicit start/end or defaults
    if start and not end:
        end = today
    elif end and not start:
        # Default to 7 days before end if only end provided
        end_dt = datetime.strptime(end, '%Y-%m-%d')
        start = (end_dt - timedelta(days=7)).strftime('%Y-%m-%d')

    return start, end


def _add_date_shortcuts(parser):
    """Add common date range shortcut arguments to a parser."""
    date_group = parser.add_argument_group('Date Range Shortcuts')
    date_group.add_argument("--days", type=int, metavar="N",
                            help="Last N days (e.g., --days 7)")
    date_group.add_argument("--hours", type=int, metavar="N",
                            help="Last N hours (e.g., --hours 24)")
    date_group.add_argument("--today", action="store_true",
                            help="Today only")
    date_group.add_argument("--yesterday", action="store_true",
                            help="Yesterday only")
    date_group.add_argument("--week", action="store_true",
                            help="Last 7 days")
    date_group.add_argument("--month", action="store_true",
                            help="Last 30 days")


# ==================== CLI COMMANDS ====================

def cmd_account_info(api, args):
    """Get account information."""
    result = api.get_account_info()
    format_output(result, args.output, 'account')


def cmd_domains_list(api, args):
    """List internal domains (API 1.0 - Domain Management)."""
    result = api.list_internal_domains()
    format_output(result, args.output, 'domains')


def cmd_domains_external(api, args):
    """List external domains (API 2.0 - Email Security Onboarding)."""
    result = api.list_external_domains_v2()
    # API 2.0 returns {"domains": [...]} not {"data": [...]}
    if 'domains' in result:
        result = {"data": result['domains']}
    format_output(result, args.output, 'domains')


def cmd_groups_list_v2(api, args):
    """List groups (API 2.0 - Directory Management)."""
    result = api.list_groups_v2()
    # API 2.0 returns {"groups": [...]} not {"data": [...]}
    if 'groups' in result:
        result = {"data": result['groups']}
    format_output(result, args.output, 'groups')


def cmd_messages_search(api, args):
    """Search messages."""
    search_by = None
    value = None
    if args.from_addr:
        search_by, value = "from", args.from_addr
    elif args.to_addr:
        search_by, value = "to", args.to_addr
    elif args.subject:
        search_by, value = "subject", args.subject

    result = api.search_messages(search_by, value, args.start, args.end)
    format_output(result, args.output, 'messages')


def cmd_messages_held(api, args):
    """List held messages."""
    result = api.get_held_messages(admin=args.admin, start=args.start, end=args.end)
    format_output(result, args.output, 'held')


def cmd_messages_release(api, args):
    """Release held message."""
    result = api.release_held_message(args.id, args.reason)
    format_output(result, args.output)


def cmd_messages_info(api, args):
    """Get message information."""
    result = api.get_message_info(args.id)
    format_output(result, args.output)


def cmd_ttp_urls(api, args):
    """Get TTP URL logs."""
    result = api.get_ttp_url_logs(args.start, args.end, args.route, args.result)
    format_output(result, args.output, 'ttp-urls')


def cmd_ttp_attachments(api, args):
    """Get TTP attachment logs."""
    result = api.get_ttp_attachment_logs(args.start, args.end, args.route, args.result)
    format_output(result, args.output, 'ttp-attachments')


def cmd_ttp_impersonation(api, args):
    """Get TTP impersonation logs."""
    result = api.get_ttp_impersonation_logs(args.start, args.end, args.action)
    format_output(result, args.output, 'ttp-impersonation')


def cmd_archive_search(api, args):
    """Search email archive."""
    # Resolve date range from shortcuts or explicit dates
    start, end = _resolve_date_range(args)

    result = api.search_archive(
        query=getattr(args, 'query', None),
        start=start,
        end=end,
        sender=getattr(args, 'sender', None),
        recipient=getattr(args, 'recipient', None),
        subject=getattr(args, 'subject', None),
        admin=getattr(args, 'admin', False)
    )

    # Apply max limit if specified
    max_results = getattr(args, 'max', None)
    if max_results and 'data' in result:
        data = result.get('data', [])
        if data and isinstance(data, list):
            result['data'] = data[:max_results]

    format_output(result, args.output, 'messages')


def cmd_archive_messages(api, args):
    """List messages from archive."""
    # Resolve date range from shortcuts or explicit dates
    start, end = _resolve_date_range(args)

    result = api.get_archive_message_list(
        view=getattr(args, 'view', 'INBOX'),
        mailbox=getattr(args, 'mailbox', None),
        start=start,
        end=end
    )
    format_output(result, args.output, 'messages')


def cmd_archive_detail(api, args):
    """Get archived message detail."""
    result = api.get_archive_message_detail(args.id)
    format_output(result, args.output)


def cmd_users_list(api, args):
    """List users."""
    result = api.list_users(domain=args.domain)
    format_output(result, args.output, 'users')


def cmd_users_create(api, args):
    """Create user."""
    result = api.create_user(args.email, name=args.name, domain=args.domain)
    format_output(result, args.output)


def cmd_users_update(api, args):
    """Update user."""
    result = api.update_user(args.email, name=args.name, alias=args.alias)
    format_output(result, args.output)


def cmd_users_delete(api, args):
    """Delete user."""
    result = api.delete_user(args.email)
    format_output(result, args.output)


def cmd_groups_list(api, args):
    """List groups."""
    result = api.list_groups()
    format_output(result, args.output, 'groups')


def cmd_groups_create(api, args):
    """Create group."""
    result = api.create_group(args.description)
    format_output(result, args.output)


def cmd_groups_add_member(api, args):
    """Add member to group."""
    result = api.add_group_member(args.group, args.email)
    format_output(result, args.output)


def cmd_groups_remove_member(api, args):
    """Remove member from group."""
    result = api.remove_group_member(args.group, args.email)
    format_output(result, args.output)


def cmd_policies_list(api, args):
    """List policies."""
    result = api.list_policies(policy_type=args.type)
    format_output(result, args.output, 'policies')


def cmd_policies_block_sender(api, args):
    """Create blocked sender policy."""
    result = api.create_block_sender_policy(args.email, args.description)
    format_output(result, args.output)


def cmd_policies_permit_sender(api, args):
    """Create permitted sender policy."""
    result = api.create_permit_sender_policy(args.email, args.description)
    format_output(result, args.output)


def cmd_policies_definitions(api, args):
    """List policy definitions."""
    result = api.list_policy_definitions()
    format_output(result, args.output)


def cmd_reports_audit(api, args):
    """Get audit events."""
    # Resolve date range from shortcuts or explicit dates
    start, end = _resolve_date_range(args)

    result = api.get_audit_events(start, end, getattr(args, 'type', None))

    # Apply client-side search/user filter if specified
    search = getattr(args, 'search', None)
    user_filter = getattr(args, 'user', None)

    if search or user_filter:
        data = result.get('data', [])
        filtered = []
        for item in data:
            # Skip if user filter doesn't match
            if user_filter:
                item_user = item.get('user', '')
                if user_filter.lower() not in item_user.lower():
                    continue
            # Skip if search doesn't match any field
            if search:
                search_lower = search.lower()
                if not any(search_lower in str(v).lower() for v in item.values()):
                    continue
            filtered.append(item)
        result['data'] = filtered

    format_output(result, args.output, 'audit')


def cmd_reports_siem(api, args):
    """Get SIEM logs."""
    # Resolve date range from shortcuts or explicit dates
    start, end = _resolve_date_range(args)

    result = api.get_siem_logs(args.type, start, end, args.format)
    format_output(result, args.output)


def cmd_reports_stats(api, args):
    """Get account statistics."""
    result = api.get_account_info()
    format_output(result, args.output, 'account')


def cmd_reports_threat_intel(api, args):
    """Get threat intelligence."""
    result = api.get_threat_intel(args.feed)
    format_output(result, args.output)


# ==================== API 2.0 COMMAND HANDLERS ====================

def _matches_search(log, search_term, fields):
    """Check if log matches search term in any of the specified fields."""
    if not search_term:
        return True
    search_lower = search_term.lower()
    for field in fields:
        value = str(log.get(field, '')).lower()
        if search_lower in value:
            return True
    return False


def _fetch_ttp_logs_paginated(api, endpoint, log_key, start, end, extra_params=None,
                               max_results=None, search=None, search_fields=None,
                               user_filter=None, quiet=False):
    """
    Fetch TTP logs with pagination, search, and early exit.

    Args:
        api: MimecastAPI instance
        endpoint: API endpoint path
        log_key: Key in response containing logs (e.g., 'clickLogs')
        start: Start date
        end: End date
        extra_params: Additional API parameters
        max_results: Stop after finding this many matches (None = unlimited)
        search: Search term to filter results client-side
        search_fields: Fields to search in
        user_filter: Filter by user email address
        quiet: Suppress progress output

    Returns:
        Tuple of (matched_logs, total_fetched, stats_dict)
    """
    all_logs = []
    matched_logs = []
    page_token = None
    pages = 0
    max_pages = 500  # Safety limit

    # Build base request
    if start and 'T' not in start:
        start = f"{start}T00:00:00+0000"
    if end and 'T' not in end:
        end = f"{end}T23:59:59+0000"

    stats = {'total': 0, 'matched': 0, 'by_result': {}}

    while pages < max_pages:
        data = {"from": start, "to": end}
        if extra_params:
            data.update(extra_params)
        if page_token:
            data['meta'] = {'pagination': {'pageToken': page_token}}

        result = api.client.post(endpoint, data)

        logs_data = result.get('data', [])
        if logs_data and log_key in logs_data[0]:
            logs = logs_data[0][log_key]
            all_logs.extend(logs)

            # Count by result type for stats
            for log in logs:
                result_type = log.get('scanResult', log.get('result', 'unknown'))
                stats['by_result'][result_type] = stats['by_result'].get(result_type, 0) + 1

            # Apply filters
            for log in logs:
                # User filter
                if user_filter:
                    user_email = log.get('userEmailAddress', log.get('recipientAddress', ''))
                    if user_filter.lower() not in user_email.lower():
                        continue

                # Search filter
                if search and search_fields:
                    if not _matches_search(log, search, search_fields):
                        continue

                matched_logs.append(log)

                # Early exit if we have enough
                if max_results and len(matched_logs) >= max_results:
                    if not quiet:
                        print(f"Found {len(matched_logs)} matches (limit reached)", file=sys.stderr)
                    stats['total'] = len(all_logs)
                    stats['matched'] = len(matched_logs)
                    return matched_logs, len(all_logs), stats

            if not quiet:
                print(f"Fetched {len(logs)} logs, total: {len(all_logs)}, matches: {len(matched_logs)}", file=sys.stderr)

        # Check for next page
        meta = result.get('meta', {})
        page_token = meta.get('pagination', {}).get('next')
        pages += 1
        if not page_token:
            break

    stats['total'] = len(all_logs)
    stats['matched'] = len(matched_logs)
    return matched_logs, len(all_logs), stats


def cmd_ttp_url_logs(api, args):
    """Get TTP URL protection logs with search and pagination."""
    # Resolve date range from shortcuts or explicit dates
    start, end = _resolve_date_range(args)

    if not start or not end:
        print("Error: Date range required. Use --days, --week, --today, or --start/--end", file=sys.stderr)
        sys.exit(1)

    extra_params = {}
    if getattr(args, 'result', None):
        extra_params['scanResult'] = args.result
    if getattr(args, 'route', None):
        extra_params['route'] = args.route

    search_fields = ['subject', 'url', 'userEmailAddress', 'senderAddress']

    logs, total, stats = _fetch_ttp_logs_paginated(
        api,
        endpoint="/api/ttp/url/get-logs",
        log_key="clickLogs",
        start=start,
        end=end,
        extra_params=extra_params if extra_params else None,
        max_results=getattr(args, 'max', None),
        search=getattr(args, 'search', None),
        search_fields=search_fields,
        user_filter=getattr(args, 'user', None),
        quiet=getattr(args, 'quiet', False)
    )

    # Show stats if requested
    if getattr(args, 'stats', False):
        print(f"\n=== Statistics ===", file=sys.stderr)
        print(f"Total fetched: {total}", file=sys.stderr)
        print(f"Matched: {stats['matched']}", file=sys.stderr)
        print(f"By result: {stats['by_result']}", file=sys.stderr)

    format_output({'data': logs}, args.output, 'ttp-urls')


def cmd_ttp_attachment_logs(api, args):
    """Get TTP attachment protection logs with search and pagination."""
    # Resolve date range from shortcuts or explicit dates
    start, end = _resolve_date_range(args)

    if not start or not end:
        print("Error: Date range required. Use --days, --week, --today, or --start/--end", file=sys.stderr)
        sys.exit(1)

    extra_params = {}
    if getattr(args, 'result', None):
        extra_params['result'] = args.result
    if getattr(args, 'route', None):
        extra_params['route'] = args.route

    search_fields = ['subject', 'fileName', 'recipientAddress', 'senderAddress']

    logs, total, stats = _fetch_ttp_logs_paginated(
        api,
        endpoint="/api/ttp/attachment/get-logs",
        log_key="attachmentLogs",
        start=start,
        end=end,
        extra_params=extra_params if extra_params else None,
        max_results=getattr(args, 'max', None),
        search=getattr(args, 'search', None),
        search_fields=search_fields,
        user_filter=getattr(args, 'user', None),
        quiet=getattr(args, 'quiet', False)
    )

    if getattr(args, 'stats', False):
        print(f"\n=== Statistics ===", file=sys.stderr)
        print(f"Total fetched: {total}", file=sys.stderr)
        print(f"Matched: {stats['matched']}", file=sys.stderr)
        print(f"By result: {stats['by_result']}", file=sys.stderr)

    format_output({'data': logs}, args.output, 'ttp-attachments')


def cmd_ttp_impersonation_logs(api, args):
    """Get TTP impersonation protection logs with search and pagination."""
    # Resolve date range from shortcuts or explicit dates
    start, end = _resolve_date_range(args)

    if not start or not end:
        print("Error: Date range required. Use --days, --week, --today, or --start/--end", file=sys.stderr)
        sys.exit(1)

    extra_params = {}
    if getattr(args, 'filter_action', None):
        extra_params['action'] = args.filter_action

    search_fields = ['subject', 'senderAddress', 'recipientAddress', 'impersonationType']

    logs, total, stats = _fetch_ttp_logs_paginated(
        api,
        endpoint="/api/ttp/impersonation/get-logs",
        log_key="impersonationLogs",
        start=start,
        end=end,
        extra_params=extra_params if extra_params else None,
        max_results=getattr(args, 'max', None),
        search=getattr(args, 'search', None),
        search_fields=search_fields,
        user_filter=getattr(args, 'user', None),
        quiet=getattr(args, 'quiet', False)
    )

    if getattr(args, 'stats', False):
        print(f"\n=== Statistics ===", file=sys.stderr)
        print(f"Total fetched: {total}", file=sys.stderr)
        print(f"Matched: {stats['matched']}", file=sys.stderr)
        print(f"By result: {stats['by_result']}", file=sys.stderr)

    format_output({'data': logs}, args.output, 'ttp-impersonation')


def cmd_ttp_decode_url(api, args):
    """Decode a TTP-rewritten URL."""
    result = api.decode_ttp_url(args.url)
    format_output(result, args.output)


def cmd_ttp_managed_list(api, args):
    """List managed URLs (whitelist/blacklist)."""
    result = api.get_managed_urls(url_filter=getattr(args, 'filter', None))
    format_output(result, args.output, 'managed-urls')


def cmd_ttp_managed_permit(api, args):
    """Add URL to permitted list (whitelist as false positive)."""
    result = api.create_managed_url(
        url=args.url,
        action="permit",
        match_type=getattr(args, 'match', 'explicit'),
        comment=getattr(args, 'comment', None),
        disable_rewrite=getattr(args, 'no_rewrite', False),
        disable_log_click=getattr(args, 'no_log', False)
    )
    if result.get('data'):
        print(f"✅ URL permitted successfully: {args.url}")
        format_output(result, args.output)
    else:
        print(f"Response: {result}")


def cmd_ttp_managed_block(api, args):
    """Add URL to blocked list."""
    result = api.create_managed_url(
        url=args.url,
        action="block",
        match_type=getattr(args, 'match', 'explicit'),
        comment=getattr(args, 'comment', None)
    )
    if result.get('data'):
        print(f"🚫 URL blocked successfully: {args.url}")
        format_output(result, args.output)
    else:
        print(f"Response: {result}")


def cmd_ttp_managed_delete(api, args):
    """Delete a managed URL entry."""
    result = api.delete_managed_url(args.id)
    print(f"Deleted managed URL: {args.id}")
    format_output(result, args.output)


def cmd_audit_events(api, args):
    """Get audit events (API 2.0)."""
    # Resolve date range from shortcuts or explicit dates
    start, end = _resolve_date_range(args)

    if not start or not end:
        print("Error: Date range required. Use --days, --week, --today, or --start/--end", file=sys.stderr)
        sys.exit(1)

    result = api.get_audit_events_v2(
        start=start,
        end=end,
        audit_type=getattr(args, 'type', None)
    )
    format_output(result, args.output, 'audit')


def cmd_message_track(api, args):
    """Search message tracking (API 2.0)."""
    # Resolve date range from shortcuts or explicit dates
    start, end = _resolve_date_range(args)

    if not start or not end:
        print("Error: Date range required. Use --days, --week, --today, or --start/--end", file=sys.stderr)
        sys.exit(1)

    result = api.search_messages_v2(
        start=start,
        end=end,
        sender=getattr(args, 'sender', None),
        recipient=getattr(args, 'recipient', None),
        subject=getattr(args, 'subject', None),
        message_id=getattr(args, 'message_id', None),
        route=getattr(args, 'route', None)
    )
    # Extract trackedEmails from response
    data = result.get('data', [])
    if data and 'trackedEmails' in data[0]:
        emails = data[0]['trackedEmails']
        format_output({'data': emails}, args.output, 'messages')
    else:
        format_output(result, args.output, 'messages')


def cmd_held_list(api, args):
    """List held messages (API 2.0)."""
    # Resolve date range from shortcuts or explicit dates
    start, end = _resolve_date_range(args)

    result = api.get_held_messages_v2(
        admin=getattr(args, 'admin', True),
        start=start,
        end=end
    )

    # Apply client-side search/filter if specified
    search = getattr(args, 'search', None)
    sender_filter = getattr(args, 'sender', None)
    subject_filter = getattr(args, 'subject', None)

    if search or sender_filter or subject_filter:
        data = result.get('data', [])
        filtered = []
        for item in data:
            # Skip if sender filter doesn't match
            if sender_filter:
                item_sender = item.get('from', {}).get('emailAddress', item.get('senderAddress', ''))
                if sender_filter.lower() not in item_sender.lower():
                    continue
            # Skip if subject filter doesn't match
            if subject_filter:
                item_subject = item.get('subject', '')
                if subject_filter.lower() not in item_subject.lower():
                    continue
            # Skip if search doesn't match any field
            if search:
                search_lower = search.lower()
                item_sender = item.get('from', {}).get('emailAddress', item.get('senderAddress', ''))
                item_subject = item.get('subject', '')
                item_to = item.get('to', {}).get('emailAddress', item.get('recipientAddress', ''))
                if not any(search_lower in str(v).lower() for v in [item_sender, item_subject, item_to]):
                    continue
            filtered.append(item)
        result['data'] = filtered

    format_output(result, args.output, 'held')


def cmd_held_release(api, args):
    """Release a held message (API 2.0)."""
    result = api.release_held_message_v2(args.id, getattr(args, 'reason', None))
    format_output(result, args.output)


def cmd_users_list_v2(api, args):
    """List internal users (API 2.0)."""
    result = api.list_internal_users_v2(domain=getattr(args, 'domain', None))
    format_output(result, args.output, 'users')


def cmd_users_cloud_gateway(api, args):
    """List cloud gateway users (API 2.0)."""
    result = api.list_users_v2()
    if 'users' in result:
        result = {'data': result['users']}
    format_output(result, args.output, 'users')


def cmd_domains_internal_v2(api, args):
    """List internal domains (API 2.0)."""
    result = api.list_internal_domains_v2()
    if 'domains' in result:
        result = {'data': result['domains']}
    format_output(result, args.output, 'domains')


def cmd_greylisting_policies(api, args):
    """List greylisting policies (API 2.0)."""
    result = api.list_greylisting_policies_v2()
    if 'policies' in result:
        result = {'data': result['policies']}
    format_output(result, args.output, 'policies')


# ==================== QUARANTINE COMMAND HANDLERS ====================

def cmd_quarantine_list(api, args):
    """List quarantine messages."""
    # Resolve date range from shortcuts or explicit dates
    start, end = _resolve_date_range(args)

    result = api.get_quarantine_messages(
        start=start,
        end=end,
        view="admin" if getattr(args, 'admin', False) else "user"
    )
    format_output(result, args.output, 'held')


def cmd_quarantine_release(api, args):
    """Release a quarantined message."""
    result = api.release_quarantine_message(args.id, getattr(args, 'reason', None))
    print(f"Released quarantine message: {args.id}")
    format_output(result, args.output)


def cmd_quarantine_delete(api, args):
    """Delete a quarantined message."""
    result = api.delete_quarantine_message(args.id)
    print(f"Deleted quarantine message: {args.id}")
    format_output(result, args.output)


# ==================== MANAGED SENDERS COMMAND HANDLERS ====================

def cmd_senders_blocked(api, args):
    """List blocked senders."""
    result = api.get_blocked_senders(policy_type=getattr(args, 'type', None))
    format_output(result, args.output, 'policies')


def cmd_senders_permitted(api, args):
    """List permitted senders."""
    result = api.get_permitted_senders(policy_type=getattr(args, 'type', None))
    format_output(result, args.output, 'policies')


def cmd_senders_unblock(api, args):
    """Remove a blocked sender policy."""
    result = api.delete_blocked_sender(args.id)
    print(f"Removed blocked sender: {args.id}")
    format_output(result, args.output)


def cmd_senders_unpermit(api, args):
    """Remove a permitted sender policy."""
    result = api.delete_permitted_sender(args.id)
    print(f"Removed permitted sender: {args.id}")
    format_output(result, args.output)


# ==================== DKIM COMMAND HANDLERS ====================

def cmd_dkim_status(api, args):
    """Get DKIM status."""
    result = api.get_dkim_status(domain=getattr(args, 'domain', None))
    format_output(result, args.output)


def cmd_dkim_create(api, args):
    """Create DKIM configuration."""
    result = api.create_dkim(args.domain, selector=getattr(args, 'selector', None))
    print(f"Created DKIM for domain: {args.domain}")
    format_output(result, args.output)


# ==================== DELIVERY COMMAND HANDLERS ====================

def cmd_delivery_info(api, args):
    """Get message delivery information."""
    result = api.get_message_delivery_info(args.id)
    format_output(result, args.output)


def cmd_delivery_routes(api, args):
    """List delivery routes."""
    result = api.get_delivery_routes()
    format_output(result, args.output)


# ==================== REJECTION COMMAND HANDLERS ====================

def cmd_rejection_logs(api, args):
    """Get rejection logs."""
    # Resolve date range from shortcuts or explicit dates
    start, end = _resolve_date_range(args)

    result = api.get_rejection_logs(
        start=start,
        end=end,
        reject_type=getattr(args, 'type', None)
    )
    format_output(result, args.output)


# ==================== TTP SUMMARY COMMAND HANDLER ====================

def cmd_ttp_summary(api, args):
    """Get TTP security summary - quick overview of threats detected."""
    # Resolve date range from shortcuts or explicit dates
    start, end = _resolve_date_range(args)

    if not start or not end:
        # Default to last 7 days if no date specified
        now = _get_cst_now()
        end = now.strftime('%Y-%m-%d')
        start = (now - timedelta(days=7)).strftime('%Y-%m-%d')

    quiet = not getattr(args, 'verbose', False)

    print(f"\n{'='*60}")
    print(f" TTP Security Summary: {start} to {end}")
    print(f"{'='*60}\n")

    # Fetch URL logs
    print("Fetching URL protection logs...", file=sys.stderr)
    url_logs, url_total, url_stats = _fetch_ttp_logs_paginated(
        api,
        endpoint="/api/ttp/url/get-logs",
        log_key="clickLogs",
        start=start,
        end=end,
        quiet=quiet
    )

    # Fetch attachment logs
    print("Fetching attachment protection logs...", file=sys.stderr)
    attach_logs, attach_total, attach_stats = _fetch_ttp_logs_paginated(
        api,
        endpoint="/api/ttp/attachment/get-logs",
        log_key="attachmentLogs",
        start=start,
        end=end,
        quiet=quiet
    )

    # Fetch impersonation logs
    print("Fetching impersonation protection logs...", file=sys.stderr)
    imp_logs, imp_total, imp_stats = _fetch_ttp_logs_paginated(
        api,
        endpoint="/api/ttp/impersonation/get-logs",
        log_key="impersonationLogs",
        start=start,
        end=end,
        quiet=quiet
    )

    # Calculate summary statistics
    url_malicious = url_stats['by_result'].get('malicious', 0)
    url_clean = url_stats['by_result'].get('clean', 0)
    attach_malicious = attach_stats['by_result'].get('malicious', 0)
    attach_safe = attach_stats['by_result'].get('safe', 0)
    imp_count = len(imp_logs)

    # Print summary
    print("\n📊 URL Protection:")
    print(f"   Total clicks scanned: {url_total}")
    print(f"   Clean: {url_clean}")
    print(f"   Malicious: {url_malicious}")
    if url_malicious > 0:
        print(f"   ⚠️  {url_malicious} malicious URLs detected!")

    print("\n📎 Attachment Protection:")
    print(f"   Total attachments scanned: {attach_total}")
    print(f"   Safe: {attach_safe}")
    print(f"   Malicious: {attach_malicious}")
    if attach_malicious > 0:
        print(f"   ⚠️  {attach_malicious} malicious attachments detected!")

    print("\n👤 Impersonation Protection:")
    print(f"   Impersonation attempts: {imp_count}")
    if imp_count > 0:
        print(f"   ⚠️  {imp_count} impersonation attempts detected!")

    # Show top affected users if there are malicious items
    if url_malicious > 0:
        print("\n🎯 Top affected users (malicious URLs):")
        user_counts = {}
        for log in url_logs:
            if log.get('scanResult') == 'malicious':
                user = log.get('userEmailAddress', 'unknown')
                user_counts[user] = user_counts.get(user, 0) + 1
        for user, count in sorted(user_counts.items(), key=lambda x: -x[1])[:5]:
            print(f"   • {user}: {count} clicks")

    # Show top malicious URLs
    if url_malicious > 0:
        print("\n🔗 Top malicious URLs:")
        url_counts = {}
        for log in url_logs:
            if log.get('scanResult') == 'malicious':
                url = log.get('url', 'unknown')
                url_counts[url] = url_counts.get(url, 0) + 1
        for url, count in sorted(url_counts.items(), key=lambda x: -x[1])[:5]:
            print(f"   • {url}: {count} detections")

    # Overall threat score
    total_threats = url_malicious + attach_malicious + imp_count
    print(f"\n{'='*60}")
    if total_threats == 0:
        print("✅ SECURITY STATUS: All clear - no threats detected")
    elif total_threats < 10:
        print(f"⚠️  SECURITY STATUS: {total_threats} potential threats detected")
    else:
        print(f"🚨 SECURITY STATUS: {total_threats} threats detected - review recommended")
    print(f"{'='*60}\n")

    # Return JSON data if requested
    if args.output == 'json':
        summary = {
            'period': {'start': start, 'end': end},
            'url_protection': {
                'total': url_total,
                'clean': url_clean,
                'malicious': url_malicious,
                'by_result': url_stats['by_result']
            },
            'attachment_protection': {
                'total': attach_total,
                'safe': attach_safe,
                'malicious': attach_malicious,
                'by_result': attach_stats['by_result']
            },
            'impersonation_protection': {
                'total': imp_count
            },
            'total_threats': total_threats
        }
        print_json(summary)


def main():
    parser = argparse.ArgumentParser(
        description="Mimecast API CLI - Email Security Operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s account info                              # Get account info
  %(prog)s users list                                # List all users
  %(prog)s messages search --from sender@example.com # Search messages
  %(prog)s ttp urls --start 2024-01-01               # Get URL protection logs
  %(prog)s policies block-sender --email spam@bad.com # Block sender
        """
    )

    parser.add_argument("--profile", "-p", default=None, help="Profile to use")
    parser.add_argument("--output", "-o", choices=["table", "json"], default="table",
                        help="Output format (default: table)")

    # Create parent parser for common arguments that can be used at end of command
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--output", "-o", choices=["table", "json"], default=None,
                               help="Output format (default: table)")

    subparsers = parser.add_subparsers(dest="resource", help="Resource type")

    # -------------------- ACCOUNT --------------------
    account_parser = subparsers.add_parser("account", help="Account operations")
    account_sub = account_parser.add_subparsers(dest="action")

    account_sub.add_parser("info", help="Get account information")

    # -------------------- DOMAINS --------------------
    domains_parser = subparsers.add_parser("domains", help="Domain operations")
    domains_sub = domains_parser.add_subparsers(dest="action")

    domains_sub.add_parser("list", help="List internal domains (API 1.0)")
    domains_sub.add_parser("external", help="List external domains (API 2.0)")
    domains_sub.add_parser("internal", help="List internal domains (API 2.0)")

    # -------------------- GROUPS V2 --------------------
    groupsv2_parser = subparsers.add_parser("groups-v2", help="Group operations (API 2.0)")
    groupsv2_sub = groupsv2_parser.add_subparsers(dest="action")

    groupsv2_sub.add_parser("list", help="List groups (Directory Management)")

    # -------------------- MESSAGES --------------------
    messages_parser = subparsers.add_parser("messages", help="Message operations")
    messages_sub = messages_parser.add_subparsers(dest="action")

    msg_search = messages_sub.add_parser("search", help="Search messages")
    msg_search.add_argument("--from", dest="from_addr", help="Search by sender")
    msg_search.add_argument("--to", dest="to_addr", help="Search by recipient")
    msg_search.add_argument("--subject", help="Search by subject")
    msg_search.add_argument("--start", help="Start date (YYYY-MM-DD)")
    msg_search.add_argument("--end", help="End date (YYYY-MM-DD)")

    msg_held = messages_sub.add_parser("held", help="List held messages", parents=[common_parser])
    msg_held.add_argument("--admin", action="store_true", help="Show admin queue")
    msg_held.add_argument("--start", help="Start date")
    msg_held.add_argument("--end", help="End date")
    _add_date_shortcuts(msg_held)  # Add --days, --hours, --today, --yesterday, --week, --month
    msg_held.add_argument("--search", help="Search in subject, sender, recipient")
    msg_held.add_argument("--sender", help="Filter by sender address")
    msg_held.add_argument("--subject", help="Filter by subject")

    msg_release = messages_sub.add_parser("release", help="Release held message")
    msg_release.add_argument("--id", required=True, help="Message ID")
    msg_release.add_argument("--reason", help="Release reason ID")

    msg_info = messages_sub.add_parser("info", help="Get message info")
    msg_info.add_argument("--id", required=True, help="Message ID")

    # -------------------- TTP --------------------
    ttp_parser = subparsers.add_parser("ttp", help="TTP protection logs")
    ttp_sub = ttp_parser.add_subparsers(dest="action")

    ttp_urls = ttp_sub.add_parser("urls", help="URL protection logs", parents=[common_parser])
    ttp_urls.add_argument("--start", help="Start date (YYYY-MM-DD)")
    ttp_urls.add_argument("--end", help="End date")
    _add_date_shortcuts(ttp_urls)  # Add --days, --hours, --today, --yesterday, --week, --month
    ttp_urls.add_argument("--route", choices=["inbound", "outbound", "internal"])
    ttp_urls.add_argument("--result", choices=["clean", "malicious"], help="Filter by scan result")
    ttp_urls.add_argument("--search", help="Search in subject, url, user, sender")
    ttp_urls.add_argument("--user", help="Filter by user email address")
    ttp_urls.add_argument("--max", type=int, help="Max results to return (stops early)")
    ttp_urls.add_argument("--stats", action="store_true", help="Show statistics summary")
    ttp_urls.add_argument("--quiet", "-q", action="store_true", help="Suppress progress output")

    ttp_attach = ttp_sub.add_parser("attachments", help="Attachment protection logs", parents=[common_parser])
    ttp_attach.add_argument("--start", help="Start date")
    ttp_attach.add_argument("--end", help="End date")
    _add_date_shortcuts(ttp_attach)  # Add --days, --hours, --today, --yesterday, --week, --month
    ttp_attach.add_argument("--route", choices=["inbound", "outbound", "internal"])
    ttp_attach.add_argument("--result", choices=["safe", "malicious"], help="Filter by result")
    ttp_attach.add_argument("--search", help="Search in subject, filename, recipient, sender")
    ttp_attach.add_argument("--user", help="Filter by recipient email address")
    ttp_attach.add_argument("--max", type=int, help="Max results to return (stops early)")
    ttp_attach.add_argument("--stats", action="store_true", help="Show statistics summary")
    ttp_attach.add_argument("--quiet", "-q", action="store_true", help="Suppress progress output")

    ttp_imp = ttp_sub.add_parser("impersonation", help="Impersonation protection logs", parents=[common_parser])
    ttp_imp.add_argument("--start", help="Start date")
    ttp_imp.add_argument("--end", help="End date")
    _add_date_shortcuts(ttp_imp)  # Add --days, --hours, --today, --yesterday, --week, --month
    ttp_imp.add_argument("--filter-action", dest="filter_action", help="Filter by action taken")
    ttp_imp.add_argument("--search", help="Search in subject, sender, recipient")
    ttp_imp.add_argument("--user", help="Filter by recipient email address")
    ttp_imp.add_argument("--max", type=int, help="Max results to return (stops early)")
    ttp_imp.add_argument("--stats", action="store_true", help="Show statistics summary")
    ttp_imp.add_argument("--quiet", "-q", action="store_true", help="Suppress progress output")

    ttp_decode = ttp_sub.add_parser("decode", help="Decode TTP-rewritten URL")
    ttp_decode.add_argument("--url", required=True, help="TTP-rewritten URL to decode")

    # Managed URLs (whitelist/blacklist)
    ttp_managed = ttp_sub.add_parser("managed", help="List managed URLs (whitelist/blacklist)")
    ttp_managed.add_argument("--filter", help="Filter by URL pattern")

    ttp_permit = ttp_sub.add_parser("permit", help="Permit URL (whitelist as false positive)")
    ttp_permit.add_argument("--url", required=True, help="URL to permit (e.g., http://vendors.com)")
    ttp_permit.add_argument("--match", choices=["explicit", "domain"], default="explicit",
                            help="Match type: explicit (exact) or domain (all URLs on domain)")
    ttp_permit.add_argument("--comment", help="Reason/comment for permitting (e.g., 'False positive - internal vendor site')")
    ttp_permit.add_argument("--no-rewrite", action="store_true", help="Don't rewrite the URL")
    ttp_permit.add_argument("--no-log", action="store_true", help="Don't log clicks on this URL")

    ttp_block = ttp_sub.add_parser("block", help="Block URL (add to blacklist)")
    ttp_block.add_argument("--url", required=True, help="URL to block")
    ttp_block.add_argument("--match", choices=["explicit", "domain"], default="explicit",
                           help="Match type: explicit (exact) or domain (all URLs on domain)")
    ttp_block.add_argument("--comment", help="Reason/comment for blocking")

    ttp_delete = ttp_sub.add_parser("unmanage", help="Remove URL from managed list")
    ttp_delete.add_argument("--id", required=True, help="Managed URL ID to delete")

    # TTP Summary command
    ttp_summary = ttp_sub.add_parser("summary", help="Security summary of all TTP protections", parents=[common_parser])
    ttp_summary.add_argument("--start", help="Start date (YYYY-MM-DD)")
    ttp_summary.add_argument("--end", help="End date (YYYY-MM-DD)")
    _add_date_shortcuts(ttp_summary)  # Add --days, --hours, --today, --yesterday, --week, --month
    ttp_summary.add_argument("--verbose", "-v", action="store_true", help="Show progress details")

    # -------------------- QUARANTINE --------------------
    quarantine_parser = subparsers.add_parser("quarantine", help="Quarantine operations")
    quarantine_sub = quarantine_parser.add_subparsers(dest="action")

    quar_list = quarantine_sub.add_parser("list", help="List quarantined messages", parents=[common_parser])
    quar_list.add_argument("--start", help="Start date")
    quar_list.add_argument("--end", help="End date")
    _add_date_shortcuts(quar_list)
    quar_list.add_argument("--admin", action="store_true", help="Show admin queue")

    quar_release = quarantine_sub.add_parser("release", help="Release quarantined message")
    quar_release.add_argument("--id", required=True, help="Message ID")
    quar_release.add_argument("--reason", help="Release reason")

    quar_delete = quarantine_sub.add_parser("delete", help="Delete quarantined message")
    quar_delete.add_argument("--id", required=True, help="Message ID")

    # -------------------- SENDERS (Blocked/Permitted) --------------------
    senders_parser = subparsers.add_parser("senders", help="Managed senders (blocked/permitted)")
    senders_sub = senders_parser.add_subparsers(dest="action")

    senders_blocked = senders_sub.add_parser("blocked", help="List blocked senders", parents=[common_parser])
    senders_blocked.add_argument("--type", help="Filter by policy type")

    senders_permitted = senders_sub.add_parser("permitted", help="List permitted senders", parents=[common_parser])
    senders_permitted.add_argument("--type", help="Filter by policy type")

    senders_unblock = senders_sub.add_parser("unblock", help="Remove blocked sender")
    senders_unblock.add_argument("--id", required=True, help="Policy ID")

    senders_unpermit = senders_sub.add_parser("unpermit", help="Remove permitted sender")
    senders_unpermit.add_argument("--id", required=True, help="Policy ID")

    # -------------------- DKIM --------------------
    dkim_parser = subparsers.add_parser("dkim", help="DKIM configuration")
    dkim_sub = dkim_parser.add_subparsers(dest="action")

    dkim_status = dkim_sub.add_parser("status", help="Get DKIM status", parents=[common_parser])
    dkim_status.add_argument("--domain", help="Filter by domain")

    dkim_create = dkim_sub.add_parser("create", help="Create DKIM configuration")
    dkim_create.add_argument("--domain", required=True, help="Domain to configure")
    dkim_create.add_argument("--selector", help="DKIM selector")

    # -------------------- DELIVERY --------------------
    delivery_parser = subparsers.add_parser("delivery", help="Message delivery operations")
    delivery_sub = delivery_parser.add_subparsers(dest="action")

    delivery_info = delivery_sub.add_parser("info", help="Get delivery info for message", parents=[common_parser])
    delivery_info.add_argument("--id", required=True, help="Message ID")

    delivery_sub.add_parser("routes", help="List delivery routes", parents=[common_parser])

    # -------------------- REJECTION --------------------
    rejection_parser = subparsers.add_parser("rejection", help="Rejection logs")
    rejection_sub = rejection_parser.add_subparsers(dest="action")

    rejection_logs = rejection_sub.add_parser("logs", help="Get rejection logs", parents=[common_parser])
    rejection_logs.add_argument("--start", help="Start date")
    rejection_logs.add_argument("--end", help="End date")
    _add_date_shortcuts(rejection_logs)
    rejection_logs.add_argument("--type", help="Filter by rejection type")

    # -------------------- TRACK (Message Tracking API 2.0) --------------------
    track_parser = subparsers.add_parser("track", help="Message tracking (API 2.0)")
    track_sub = track_parser.add_subparsers(dest="action")

    track_search = track_sub.add_parser("search", help="Search message tracking logs")
    track_search.add_argument("--start", help="Start date (YYYY-MM-DD)")
    track_search.add_argument("--end", help="End date (YYYY-MM-DD)")
    _add_date_shortcuts(track_search)  # Add --days, --hours, --today, --yesterday, --week, --month
    track_search.add_argument("--sender", help="Filter by sender address")
    track_search.add_argument("--recipient", help="Filter by recipient address")
    track_search.add_argument("--subject", help="Filter by subject")
    track_search.add_argument("--message-id", dest="message_id", help="Specific message ID")
    track_search.add_argument("--route", choices=["inbound", "outbound", "internal"],
                              help="Filter by route")

    # -------------------- AUDIT (API 2.0) --------------------
    audit_parser = subparsers.add_parser("audit", help="Audit events (API 2.0)")
    audit_sub = audit_parser.add_subparsers(dest="action")

    audit_events = audit_sub.add_parser("events", help="Get audit events")
    audit_events.add_argument("--start", help="Start date (YYYY-MM-DD)")
    audit_events.add_argument("--end", help="End date (YYYY-MM-DD)")
    _add_date_shortcuts(audit_events)  # Add --days, --hours, --today, --yesterday, --week, --month
    audit_events.add_argument("--type", help="Filter by audit type")

    # -------------------- ARCHIVE (Data Retention) --------------------
    archive_parser = subparsers.add_parser("archive", help="Archive/Data Retention operations")
    archive_sub = archive_parser.add_subparsers(dest="action")

    arch_search = archive_sub.add_parser("search", help="Search archive", parents=[common_parser])
    arch_search.add_argument("--query", "-q", help="Raw XML query (advanced)")
    arch_search.add_argument("--start", help="Start date (YYYY-MM-DD)")
    arch_search.add_argument("--end", help="End date (YYYY-MM-DD)")
    _add_date_shortcuts(arch_search)  # Add --days, --hours, --today, --yesterday, --week, --month
    arch_search.add_argument("--sender", help="Filter by sender address")
    arch_search.add_argument("--recipient", help="Filter by recipient address")
    arch_search.add_argument("--subject", help="Filter by subject")
    arch_search.add_argument("--admin", action="store_true",
                             help="Search all mailboxes (requires admin permission)")
    arch_search.add_argument("--max", type=int, help="Max results to return")

    arch_messages = archive_sub.add_parser("messages", help="List messages from archive", parents=[common_parser])
    arch_messages.add_argument("--view", default="INBOX", choices=["INBOX", "SENT"],
                               help="View type (default: INBOX)")
    arch_messages.add_argument("--mailbox", help="Mailbox address (defaults to logged-in user)")
    arch_messages.add_argument("--start", help="Start date (YYYY-MM-DD)")
    arch_messages.add_argument("--end", help="End date (YYYY-MM-DD)")
    _add_date_shortcuts(arch_messages)  # Add --days, --hours, --today, --yesterday, --week, --month

    arch_detail = archive_sub.add_parser("detail", help="Get message detail")
    arch_detail.add_argument("--id", required=True, help="Message ID")

    # -------------------- USERS --------------------
    users_parser = subparsers.add_parser("users", help="User operations")
    users_sub = users_parser.add_subparsers(dest="action")

    users_list = users_sub.add_parser("list", help="List users")
    users_list.add_argument("--domain", help="Filter by domain")

    users_create = users_sub.add_parser("create", help="Create user")
    users_create.add_argument("--email", required=True, help="Email address")
    users_create.add_argument("--name", help="Display name")
    users_create.add_argument("--domain", help="Domain")

    users_update = users_sub.add_parser("update", help="Update user")
    users_update.add_argument("--email", required=True, help="Email address")
    users_update.add_argument("--name", help="New name")
    users_update.add_argument("--alias", help="Email alias")

    users_delete = users_sub.add_parser("delete", help="Delete user")
    users_delete.add_argument("--email", required=True, help="Email address")

    users_sub.add_parser("cloud-gateway", help="List cloud gateway users (API 2.0)")

    # -------------------- GROUPS --------------------
    groups_parser = subparsers.add_parser("groups", help="Group operations")
    groups_sub = groups_parser.add_subparsers(dest="action")

    groups_sub.add_parser("list", help="List groups")

    groups_create = groups_sub.add_parser("create", help="Create group")
    groups_create.add_argument("--description", required=True, help="Group description")

    groups_add = groups_sub.add_parser("add-member", help="Add member to group")
    groups_add.add_argument("--group", required=True, help="Group ID")
    groups_add.add_argument("--email", required=True, help="Member email")

    groups_remove = groups_sub.add_parser("remove-member", help="Remove member")
    groups_remove.add_argument("--group", required=True, help="Group ID")
    groups_remove.add_argument("--email", required=True, help="Member email")

    # -------------------- POLICIES --------------------
    policies_parser = subparsers.add_parser("policies", help="Policy operations")
    policies_sub = policies_parser.add_subparsers(dest="action")

    pol_list = policies_sub.add_parser("list", help="List policies")
    pol_list.add_argument("--type", help="Filter by policy type")

    pol_block = policies_sub.add_parser("block-sender", help="Block sender")
    pol_block.add_argument("--email", required=True, help="Email to block")
    pol_block.add_argument("--description", help="Policy description")

    pol_permit = policies_sub.add_parser("permit-sender", help="Permit sender")
    pol_permit.add_argument("--email", required=True, help="Email to permit")
    pol_permit.add_argument("--description", help="Policy description")

    policies_sub.add_parser("definitions", help="List policy definitions")
    policies_sub.add_parser("greylisting", help="List greylisting policies (API 2.0)")

    # -------------------- REPORTS --------------------
    reports_parser = subparsers.add_parser("reports", help="Reporting operations")
    reports_sub = reports_parser.add_subparsers(dest="action")

    rep_audit = reports_sub.add_parser("audit", help="Audit events", parents=[common_parser])
    rep_audit.add_argument("--start", help="Start date")
    rep_audit.add_argument("--end", help="End date")
    _add_date_shortcuts(rep_audit)  # Add --days, --hours, --today, --yesterday, --week, --month
    rep_audit.add_argument("--type", help="Audit type")
    rep_audit.add_argument("--search", help="Search in audit entries")
    rep_audit.add_argument("--user", help="Filter by user email")

    rep_siem = reports_sub.add_parser("siem", help="SIEM logs", parents=[common_parser])
    rep_siem.add_argument("--type", default="receipt",
                          choices=["receipt", "process", "delivery", "ttp", "internal"],
                          help="Log type")
    rep_siem.add_argument("--start", help="Start date")
    rep_siem.add_argument("--end", help="End date")
    _add_date_shortcuts(rep_siem)  # Add --days, --hours, --today, --yesterday, --week, --month
    rep_siem.add_argument("--format", default="json", choices=["key_value", "json"])

    reports_sub.add_parser("stats", help="Account statistics")

    rep_threat = reports_sub.add_parser("threat-intel", help="Threat intelligence")
    rep_threat.add_argument("--feed", help="Specific feed type")

    args = parser.parse_args()

    # Handle output arg - subparser may override with None if not specified
    # Default to "table" if not set
    if args.output is None:
        args.output = "table"

    if not args.resource:
        parser.print_help()
        sys.exit(1)

    try:
        api = MimecastAPI(profile=args.profile)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Route to command handler
    cmd_map = {
        ("account", "info"): cmd_account_info,
        # Domains (API 2.0)
        ("domains", "list"): cmd_domains_list,
        ("domains", "external"): cmd_domains_external,
        ("domains", "internal"): cmd_domains_internal_v2,
        # Groups (API 2.0)
        ("groups-v2", "list"): cmd_groups_list_v2,
        # Messages (API 2.0)
        ("messages", "search"): cmd_messages_search,
        ("messages", "held"): cmd_held_list,
        ("messages", "release"): cmd_held_release,
        ("messages", "info"): cmd_messages_info,
        # Message Tracking (API 2.0)
        ("track", "search"): cmd_message_track,
        # TTP Protection (API 2.0)
        ("ttp", "urls"): cmd_ttp_url_logs,
        ("ttp", "attachments"): cmd_ttp_attachment_logs,
        ("ttp", "impersonation"): cmd_ttp_impersonation_logs,
        ("ttp", "decode"): cmd_ttp_decode_url,
        ("ttp", "managed"): cmd_ttp_managed_list,
        ("ttp", "permit"): cmd_ttp_managed_permit,
        ("ttp", "block"): cmd_ttp_managed_block,
        ("ttp", "unmanage"): cmd_ttp_managed_delete,
        ("ttp", "summary"): cmd_ttp_summary,
        # Quarantine
        ("quarantine", "list"): cmd_quarantine_list,
        ("quarantine", "release"): cmd_quarantine_release,
        ("quarantine", "delete"): cmd_quarantine_delete,
        # Managed Senders
        ("senders", "blocked"): cmd_senders_blocked,
        ("senders", "permitted"): cmd_senders_permitted,
        ("senders", "unblock"): cmd_senders_unblock,
        ("senders", "unpermit"): cmd_senders_unpermit,
        # DKIM
        ("dkim", "status"): cmd_dkim_status,
        ("dkim", "create"): cmd_dkim_create,
        # Delivery
        ("delivery", "info"): cmd_delivery_info,
        ("delivery", "routes"): cmd_delivery_routes,
        # Rejection
        ("rejection", "logs"): cmd_rejection_logs,
        # Audit Events (API 2.0)
        ("audit", "events"): cmd_audit_events,
        # Archive (Data Retention)
        ("archive", "search"): cmd_archive_search,
        ("archive", "messages"): cmd_archive_messages,
        ("archive", "detail"): cmd_archive_detail,
        # Users (API 2.0)
        ("users", "list"): cmd_users_list_v2,
        ("users", "create"): cmd_users_create,
        ("users", "update"): cmd_users_update,
        ("users", "delete"): cmd_users_delete,
        ("users", "cloud-gateway"): cmd_users_cloud_gateway,
        # Groups (API 1.0)
        ("groups", "list"): cmd_groups_list,
        ("groups", "create"): cmd_groups_create,
        ("groups", "add-member"): cmd_groups_add_member,
        ("groups", "remove-member"): cmd_groups_remove_member,
        # Policies
        ("policies", "list"): cmd_policies_list,
        ("policies", "block-sender"): cmd_policies_block_sender,
        ("policies", "permit-sender"): cmd_policies_permit_sender,
        ("policies", "definitions"): cmd_policies_definitions,
        ("policies", "greylisting"): cmd_greylisting_policies,
        # Reports
        ("reports", "audit"): cmd_audit_events,
        ("reports", "siem"): cmd_reports_siem,
        ("reports", "stats"): cmd_reports_stats,
        ("reports", "threat-intel"): cmd_reports_threat_intel,
    }

    cmd_key = (args.resource, args.action)
    if cmd_key not in cmd_map:
        # Check if resource parser has subcommands
        if args.resource:
            subparser = subparsers.choices.get(args.resource)
            if subparser:
                subparser.print_help()
        else:
            parser.print_help()
        sys.exit(1)

    try:
        cmd_map[cmd_key](api, args)
    except MimecastError as e:
        print(f"API Error: {e}", file=sys.stderr)
        if e.request_id:
            print(f"Request ID: {e.request_id}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
