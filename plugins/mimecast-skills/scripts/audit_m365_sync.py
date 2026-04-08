#!/usr/bin/env python3
"""
Mimecast ↔ Microsoft 365 / Azure AD Configuration Audit

Cross-references Azure AD (Entra ID) users against Mimecast to identify user sync
drift, orphaned accounts, and untracked employee lifecycle issues. Also checks
Mimecast security configuration posture against M365.

Usage:
    cd plugins/mimecast-skills
    python3 scripts/audit_m365_sync.py [options]

Options:
    --mimecast-profile PROFILE   Mimecast config profile (default: production)
    --azure-tenant TENANT        Azure AD tenant alias (default: default)
    --grace-days N               Days after Azure AD disable to flag as grace period (default: 90)
    --exclude-domains DOMAINS    Comma-separated domains to exclude from comparison
    --output FILE                Write report to file (default: stdout)
    --json                       Output raw JSON findings instead of markdown report
    --verbose                    Show detailed progress
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

# ── Exclusion Patterns ────────────────────────────────────────────────────────

# Azure AD accounts whose UPN local-part starts with these are service accounts
AZURE_SVC_PREFIXES = (
    "svc-", "sync_", "ntservice", "dnsuser", "ncldap", "snipe",
)
# Azure AD accounts whose UPN local-part contains these are service accounts
AZURE_SVC_CONTAINS = ("ldapsync",)

# Mimecast email-address prefixes that are domain infrastructure, not people
MIMECAST_INFRA_PREFIXES = (
    "abuse@", "postmaster@", "noreply@", "no-reply@",
    "mailer-daemon@", "bounces@", "journaling@",
)
# Mimecast account-name strings that identify non-person accounts
MIMECAST_INFRA_NAMES = (
    "domain abuse address", "domain postmaster address",
    "mimecast journaling", "ingestion user",
)
# Mimecast email local-part prefixes that are Mimecast-internal accounts
MIMECAST_INTERNAL_PREFIXES = ("api-", "ingest_")


# ── Paths ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
PLUGIN_DIR = SCRIPT_DIR.parent
REPO_ROOT = PLUGIN_DIR.parent.parent  # plugins/mimecast-skills/../.. = repo root

MIMECAST_CLI = PLUGIN_DIR / "scripts" / "mimecast_api.py"
AZURE_CLI = Path(os.environ.get(
    "AZURE_AD_CLI_PATH",
    str(REPO_ROOT / "plugins" / "m365-skills" / "skills" / "azure-ad" / "scripts" / "azure_ad_api.py"),
))


# ── CLI Runner ────────────────────────────────────────────────────────────────

# Sentinel returned by run_cli() on error — distinct from a valid empty list/None result.
# Callers check: if isinstance(result, dict) and result.get("_error"):
_CLI_ERROR_KEY = "_error"


def _cli_error(error_type: str, msg: str) -> dict:
    """Return a sentinel error dict for run_cli() callers to detect."""
    return {_CLI_ERROR_KEY: True, "_error_type": error_type, "_error_msg": msg}


def _is_cli_error(data) -> bool:
    """Return True if data is a run_cli() error sentinel."""
    return isinstance(data, dict) and data.get(_CLI_ERROR_KEY) is True


def run_cli(cmd: list[str], verbose: bool = False, timeout: int = 60) -> dict | list | None:
    """
    Run a CLI command and return parsed JSON output.

    On success returns the parsed JSON (dict or list).
    On error returns a sentinel dict: {"_error": True, "_error_type": ..., "_error_msg": ...}
    Error types: "non_zero_exit" (auth failures, API errors), "json_parse", "timeout", "exception"
    """
    if verbose:
        print(f"  → {' '.join(str(c) for c in cmd)}", file=sys.stderr)
    try:
        result = subprocess.run(
            [sys.executable] + [str(c) for c in cmd],
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            cmd_name = Path(cmd[1]).name if len(cmd) > 1 else "unknown"
            stderr_snippet = result.stderr.strip()[:200]
            print(f"  ⚠ CLI error ({cmd_name}): {stderr_snippet}", file=sys.stderr)
            return _cli_error("non_zero_exit", f"{cmd_name}: {stderr_snippet}")
        if not result.stdout.strip():
            return None
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"  ⚠ JSON parse error: {e}", file=sys.stderr)
        return _cli_error("json_parse", str(e))
    except subprocess.TimeoutExpired:
        cmd_name = f"{Path(cmd[1]).name} {' '.join(str(c) for c in cmd[2:4])}" if len(cmd) > 1 else "unknown"
        msg = f"CLI timed out after {timeout}s: {cmd_name}"
        print(f"  ⚠ {msg}", file=sys.stderr)
        return _cli_error("timeout", msg)
    except Exception as e:
        print(f"  ⚠ CLI error: {e}", file=sys.stderr)
        return _cli_error("exception", str(e))


# ── Data Fetchers ─────────────────────────────────────────────────────────────

def fetch_azure_users(tenant: str, verbose: bool) -> list[dict]:
    """Fetch all users from Azure AD with accountEnabled + creation date."""
    if verbose:
        print("Fetching Azure AD users...", file=sys.stderr)
    data = run_cli([
        AZURE_CLI, "-t", tenant, "-f", "json",
        "users", "list",
        "--select", "id,displayName,userPrincipalName,mail,accountEnabled,userType,department,jobTitle,createdDateTime,signInActivity",
        "--all",
    ], verbose, timeout=180)
    if _is_cli_error(data):
        raise RuntimeError(f"[{data['_error_type']}] {data['_error_msg']}")
    if data is None:
        return []
    return _unwrap_graph_list(data)


def fetch_azure_deleted_users(tenant: str, verbose: bool) -> list[dict]:
    """Fetch recently deleted users from Azure AD recycle bin."""
    if verbose:
        print("Fetching Azure AD deleted users...", file=sys.stderr)
    data = run_cli([
        AZURE_CLI, "-t", tenant, "-f", "json",
        "directory", "deleted-users",
    ], verbose, timeout=60)
    if _is_cli_error(data):
        raise RuntimeError(f"[{data['_error_type']}] {data['_error_msg']}")
    if data is None:
        return []
    return _unwrap_graph_list(data)


def fetch_azure_domains(tenant: str, verbose: bool) -> list[dict]:
    """Fetch verified domains from Azure AD."""
    if verbose:
        print("Fetching Azure AD domains...", file=sys.stderr)
    data = run_cli([
        AZURE_CLI, "-t", tenant, "-f", "json",
        "directory", "domains",
    ], verbose, timeout=60)
    if _is_cli_error(data):
        raise RuntimeError(f"[{data['_error_type']}] {data['_error_msg']}")
    if data is None:
        return []
    return _unwrap_graph_list(data)


def filter_azure_users(users: list[dict], svc_prefixes: tuple = AZURE_SVC_PREFIXES) -> dict:
    """
    Split Azure AD users into employees vs. non-employees.

    Azure AD often contains more than just employees:
      - Guest (B2B) accounts — external contacts invited via Entra B2B
      - Service accounts — svc-*, sync_*, ntservice*, dnsuser*, etc.
      - Infrastructure accounts — LDAP sync, directory sync service accounts

    Returns dict with keys:
      employees      — Members with real email addresses (used for comparison)
      guests         — B2B external invites (userType=Guest or #EXT# in UPN)
      service_accts  — Internal service/infrastructure accounts
    """
    employees, guests, service_accts = [], [], []

    for u in users:
        upn = (u.get("userPrincipalName") or "").lower()
        display = (u.get("displayName") or "").lower()
        user_type = (u.get("userType") or "Member")

        # Guest / B2B externals
        if user_type == "Guest" or "#EXT#" in upn:
            guests.append(u)
            continue

        # Service / infrastructure accounts by UPN pattern
        local = upn.split("@")[0]
        if (
            any(local.startswith(p) for p in svc_prefixes)
            or any(s in local for s in AZURE_SVC_CONTAINS)
            or "synchronization service account" in display
        ):
            service_accts.append(u)
            continue

        employees.append(u)

    return {
        "employees": employees,
        "guests": guests,
        "service_accts": service_accts,
    }


def fetch_mimecast_users(profile: str, verbose: bool) -> list[dict]:
    """Fetch all Mimecast internal users."""
    if verbose:
        print("Fetching Mimecast users...", file=sys.stderr)
    data = run_cli([
        MIMECAST_CLI, "--profile", profile, "--output", "json", "users", "list", "--all",
    ], verbose, timeout=180)
    if _is_cli_error(data):
        raise RuntimeError(f"[{data['_error_type']}] {data['_error_msg']}")
    if data is None:
        return []
    # Mimecast v1: {"data": [{"users": [...]}]} — flatten nested pages
    if isinstance(data, dict) and "data" in data:
        items = data["data"]
        result = []
        for item in items:
            if isinstance(item, dict) and "users" in item:
                result.extend(item["users"])
            elif isinstance(item, dict) and item:
                result.append(item)
        return result if result else items
    if isinstance(data, list):
        return data
    return []


def _is_mimecast_infra(user: dict) -> bool:
    """Return True if this Mimecast account is domain infrastructure, not a person."""
    email = (user.get("emailAddress") or "").lower()
    name = (user.get("name") or "").lower()
    local_prefix = email.split("@")[0] + "@" if "@" in email else ""

    return (
        any(email.startswith(p) for p in MIMECAST_INFRA_PREFIXES)
        or any(s in name for s in MIMECAST_INFRA_NAMES)
        or any(local_prefix.startswith(p) for p in MIMECAST_INTERNAL_PREFIXES)
    )


def segment_mimecast_users(users: list[dict]) -> dict:
    """
    Split raw Mimecast user list into meaningful categories.

    Mimecast's /api/user/get-internal-users returns everything it manages:
      - Actual user accounts (created_by_ldap_sync, created_manually, created_by_import)
      - Aliases — secondary email addresses for existing users (alias=True)
      - Distribution lists — email groups synced from LDAP (addressType=dl_from_ldap)
      - Email-auto-created — entries generated from mail traffic with no guaranteed mailbox
      - Infrastructure accounts — abuse@, postmaster@, api-*, ingest_*, journaling@

    Only real user accounts should be compared against Azure AD.

    Returns dict with keys:
      real_users  — list to compare against Azure AD
      aliases     — secondary address entries
      dls         — distribution lists
      email_auto  — auto-created from mail traffic
      infra       — domain infrastructure accounts (abuse@, postmaster@, api-*, etc.)
    """
    aliases = [u for u in users if u.get("alias")]
    dls = [u for u in users if not u.get("alias") and u.get("addressType") == "dl_from_ldap"]
    email_auto = [
        u for u in users
        if not u.get("alias")
        and u.get("addressType") == "created_by_email"
    ]
    # From remaining accounts, split out infrastructure vs. real users
    candidates = [
        u for u in users
        if not u.get("alias")
        and u.get("addressType") not in ("dl_from_ldap", "created_by_email")
    ]
    infra, real_users = [], []
    for u in candidates:
        (infra if _is_mimecast_infra(u) else real_users).append(u)

    return {
        "real_users": real_users,
        "aliases": aliases,
        "dls": dls,
        "email_auto": email_auto,
        "infra": infra,
    }


def _unwrap_graph_list(response: dict | list | None) -> list:
    """Extract the 'value' list from a Graph API response, or return the list directly."""
    if response is None:
        return []
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        return response.get("value", [])
    return []


def _mimecast_run(cmd: list[str], profile: str, verbose: bool) -> dict | list | None:
    """Run a Mimecast CLI command with standard profile/output flags."""
    return run_cli([MIMECAST_CLI, "--profile", profile, "--output", "json"] + cmd, verbose)


def fetch_mimecast_config(profile: str, verbose: bool) -> dict:
    """Run all Mimecast config checks in parallel and return results."""
    if verbose:
        print("Fetching Mimecast configuration...", file=sys.stderr)

    def _run(cmd):
        return _mimecast_run(cmd, profile, verbose)

    checks = {
        "dkim": ["dkim", "status"],
        "domains": ["domains", "list"],
        "policies": ["policies", "list"],
        "ttp_summary": ["ttp", "summary"],
        "delivery_routes": ["delivery", "routes"],
        "senders_blocked": ["senders", "blocked"],
        "senders_permitted": ["senders", "permitted"],
        "awareness_summary": ["awareness", "performance-summary"],
        "watchlist": ["awareness", "watchlist"],
    }

    results = {}
    with ThreadPoolExecutor(max_workers=len(checks)) as executor:
        futures = {executor.submit(_run, cmd): key for key, cmd in checks.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                data = future.result()
                if _is_cli_error(data):
                    print(
                        f"WARNING: config check '{key}' failed "
                        f"[{data['_error_type']}]: {data['_error_msg']}",
                        file=sys.stderr,
                    )
                    results[key] = None
                else:
                    results[key] = data
            except Exception as e:
                print(f"WARNING: worker failed for {key}: {e}", file=sys.stderr)
                results[key] = None
    return results


def fetch_sync_health(profile: str, verbose: bool) -> dict:
    """Fetch directory sync connection config and recent event history."""
    if verbose:
        print("Fetching directory sync health...", file=sys.stderr)

    def _safe(data, label: str):
        """Convert error sentinels to None so analyze_sync_health handles them consistently."""
        if _is_cli_error(data):
            print(
                f"WARNING: sync health '{label}' failed "
                f"[{data['_error_type']}]: {data['_error_msg']}",
                file=sys.stderr,
            )
            return None
        return data

    checks = {
        "connection": ["sync", "status"],
        "history":    ["sync", "history", "--days", "2"],
    }

    def _run(cmd):
        return _mimecast_run(cmd, profile, verbose)

    raw: dict = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(_run, cmd): key for key, cmd in checks.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                raw[key] = future.result()
            except Exception as e:
                print(f"WARNING: sync health worker failed for {key}: {e}", file=sys.stderr)
                raw[key] = None

    return {k: _safe(raw.get(k), k) for k in checks}


# ── Email Normalization ────────────────────────────────────────────────────────

def normalize_email(user: dict, source: Literal["azure", "mimecast"]) -> str | None:
    """Extract and normalize email address from a user record."""
    if source == "azure":
        mail = user.get("mail", "")
        upn = user.get("userPrincipalName", "")
        email = mail or upn
        if not email or "#EXT#" in email:
            return None
        # Skip .onmicrosoft.com UPNs when no primary mail — they won't match Mimecast addresses
        if not mail and upn.lower().endswith(".onmicrosoft.com"):
            return None
        return email.lower().strip()
    else:  # mimecast
        email = user.get("emailAddress", "")
        return email.lower().strip() if email else None


def should_exclude(email: str | None, excluded_domains: set[str]) -> bool:
    """Return True if this email should be excluded from comparison."""
    if not email:
        return True
    domain = email.split("@")[-1] if "@" in email else ""
    return domain in excluded_domains


# ── Cross-Reference ────────────────────────────────────────────────────────────

def cross_reference(
    azure_users: list[dict],
    mimecast_users: list[dict],
    deleted_azure_users: list[dict],
    excluded_domains: set[str],
    grace_days: int,
) -> dict:
    """
    Cross-reference Azure AD users against Mimecast users and categorize findings.

    mimecast_users should be pre-filtered to real user accounts only (no aliases or DLs).

    Categories:
        active         - In both Azure AD (enabled) and Mimecast
        orphaned       - In Mimecast but NOT in Azure AD (even deleted)
        missing        - Azure AD enabled, NOT in Mimecast
        disabled_active - Azure AD disabled, still in Mimecast
        grace_period   - Azure AD disabled within grace_days, still in Mimecast
        stale_grace    - Azure AD disabled > grace_days ago, still in Mimecast
    """
    now = datetime.now(tz=timezone.utc)
    grace_cutoff = now - timedelta(days=grace_days)

    # Build Azure AD lookup: email → user
    azure_by_email: dict[str, dict] = {}
    azure_disabled: dict[str, dict] = {}  # email → disabled user

    for u in azure_users:
        email = normalize_email(u, "azure")
        if not email or should_exclude(email, excluded_domains):
            continue
        if u.get("accountEnabled", True):
            azure_by_email[email] = u
        else:
            azure_disabled[email] = u

    # Build deleted Azure AD lookup
    deleted_emails: set[str] = set()
    for u in deleted_azure_users:
        email = normalize_email(u, "azure")
        if email:
            deleted_emails.add(email)

    # Build Mimecast lookup: email → user
    mimecast_by_email: dict[str, dict] = {}
    for u in mimecast_users:
        email = normalize_email(u, "mimecast")
        if not email or should_exclude(email, excluded_domains):
            continue
        mimecast_by_email[email] = u

    results = {
        "active": [],
        "orphaned": [],
        "missing": [],
        "disabled_active": [],
        "grace_period": [],
        "stale_grace": [],
    }

    # Check Mimecast users against Azure AD
    for email, mc_user in mimecast_by_email.items():
        if email in azure_by_email:
            results["active"].append({
                "email": email,
                "mimecast_name": mc_user.get("name", ""),
                "azure_display": azure_by_email[email].get("displayName", ""),
                "department": azure_by_email[email].get("department", ""),
            })
        elif email in azure_disabled:
            az_user = azure_disabled[email]
            disabled_entry = {
                "email": email,
                "mimecast_name": mc_user.get("name", ""),
                "azure_display": az_user.get("displayName", ""),
                "department": az_user.get("department", ""),
                "azure_status": "disabled",
            }
            # Use lastSignInDateTime as the boundary for grace period — this reflects
            # when the user was last active, not when the account was created.
            # Falls back to createdDateTime when signInActivity is absent (e.g. accounts
            # that never signed in or where AuditLog.Read.All is not granted).
            last_sign_in = (
                az_user.get("signInActivity", {}).get("lastSignInDateTime")
                or az_user.get("createdDateTime", "")
            )
            if last_sign_in:
                try:
                    boundary_dt = datetime.fromisoformat(last_sign_in.replace("Z", "+00:00"))
                    if boundary_dt > grace_cutoff:
                        results["grace_period"].append(disabled_entry)
                    else:
                        results["stale_grace"].append(disabled_entry)
                except ValueError:
                    results["disabled_active"].append(disabled_entry)
            else:
                results["disabled_active"].append(disabled_entry)
        else:
            note = "Account deleted from Azure AD" if email in deleted_emails else "No matching Azure AD account"
            results["orphaned"].append({
                "email": email,
                "mimecast_name": mc_user.get("name", ""),
                "note": note,
            })

    # Check Azure AD active users against Mimecast
    for email, az_user in azure_by_email.items():
        if email not in mimecast_by_email:
            results["missing"].append({
                "email": email,
                "azure_display": az_user.get("displayName", ""),
                "department": az_user.get("department", ""),
                "job_title": az_user.get("jobTitle", ""),
            })

    return results


# ── Config Analysis ────────────────────────────────────────────────────────────

def analyze_config(config: dict, azure_domains: list[dict]) -> list[dict]:
    """Analyze Mimecast configuration and return list of findings."""
    findings = []

    # DKIM check
    dkim_data = config.get("dkim")
    if dkim_data is None:
        findings.append({
            "check": "DKIM",
            "status": "error",
            "severity": "HIGH",
            "detail": "Could not retrieve DKIM status",
        })
    else:
        items = dkim_data.get("data", dkim_data) if isinstance(dkim_data, dict) else dkim_data
        if isinstance(items, list):
            no_dkim = [d for d in items if not d.get("dkimEnabled", True)]
            if no_dkim:
                findings.append({
                    "check": "DKIM",
                    "status": "warning",
                    "severity": "HIGH",
                    "detail": f"{len(no_dkim)} domain(s) have DKIM disabled: {[d.get('domain', '?') for d in no_dkim]}",
                })
            else:
                findings.append({
                    "check": "DKIM",
                    "status": "ok",
                    "severity": "OK",
                    "detail": f"DKIM enabled on all {len(items)} configured domain(s)",
                })

    # Domain alignment check
    mimecast_domains_data = config.get("domains")
    if mimecast_domains_data and azure_domains:
        mc_domains = set()
        items = mimecast_domains_data.get("data", []) if isinstance(mimecast_domains_data, dict) else []
        for d in items:
            domain = d.get("domain", d.get("name", ""))
            if domain:
                mc_domains.add(domain.lower())

        az_domains = {
            d.get("id", "").lower()
            for d in azure_domains
            if d.get("isVerified")
        }

        az_only = az_domains - mc_domains
        mc_only = mc_domains - az_domains
        if az_only:
            findings.append({
                "check": "Domain alignment",
                "status": "warning",
                "severity": "MEDIUM",
                "detail": f"Azure AD domains not in Mimecast: {sorted(az_only)}",
            })
        if mc_only:
            findings.append({
                "check": "Domain alignment",
                "status": "warning",
                "severity": "LOW",
                "detail": f"Mimecast domains not in Azure AD: {sorted(mc_only)}",
            })
        if not az_only and not mc_only:
            findings.append({
                "check": "Domain alignment",
                "status": "ok",
                "severity": "OK",
                "detail": f"Domains aligned between Azure AD ({len(az_domains)}) and Mimecast ({len(mc_domains)})",
            })

    # TTP summary check
    ttp = config.get("ttp_summary")
    if ttp is None:
        findings.append({
            "check": "TTP protection",
            "status": "error",
            "severity": "HIGH",
            "detail": "Could not retrieve TTP status — verify TTP URL/attachment/impersonation protection is enabled",
        })
    else:
        # ttp summary returns structured text — check for key indicators
        findings.append({
            "check": "TTP protection",
            "status": "ok",
            "severity": "OK",
            "detail": "TTP summary retrieved successfully — review report for threat counts",
        })

    # Anti-spoofing / policies check
    policies_data = config.get("policies")
    if policies_data is not None:
        items = policies_data.get("data", []) if isinstance(policies_data, dict) else []
        has_antispoofing = any(
            "spoof" in p.get("policy", {}).get("definition", {}).get("description", "").lower()
            or "antispoofing" in str(p).lower()
            for p in items
        )
        if not has_antispoofing and items:
            findings.append({
                "check": "Anti-spoofing",
                "status": "warning",
                "severity": "HIGH",
                "detail": "No anti-spoofing policies detected — review impersonation protection settings",
            })

    # Delivery routes check
    routes_data = config.get("delivery_routes")
    if routes_data is None:
        findings.append({
            "check": "Delivery routes",
            "status": "error",
            "severity": "MEDIUM",
            "detail": "Could not retrieve delivery routes",
        })
    else:
        items = routes_data.get("data", []) if isinstance(routes_data, dict) else []
        if not items:
            findings.append({
                "check": "Delivery routes",
                "status": "warning",
                "severity": "MEDIUM",
                "detail": "No delivery routes configured — verify M365 routing is correct",
            })
        else:
            findings.append({
                "check": "Delivery routes",
                "status": "ok",
                "severity": "OK",
                "detail": f"{len(items)} delivery route(s) configured",
            })

    # Awareness training check
    awareness = config.get("awareness_summary")
    if awareness is None:
        findings.append({
            "check": "Awareness training",
            "status": "warning",
            "severity": "LOW",
            "detail": "Awareness Training data unavailable — product may not be enabled",
        })

    # High-risk watchlist
    watchlist_data = config.get("watchlist")
    if watchlist_data is not None:
        items = watchlist_data.get("data", []) if isinstance(watchlist_data, dict) else []
        if items:
            findings.append({
                "check": "High-risk users",
                "status": "warning",
                "severity": "MEDIUM",
                "detail": f"{len(items)} high-risk user(s) on Mimecast watchlist",
            })
        else:
            findings.append({
                "check": "High-risk users",
                "status": "ok",
                "severity": "OK",
                "detail": "No users on high-risk watchlist",
            })

    return findings


# ── Sync Health Analysis ──────────────────────────────────────────────────────

def analyze_sync_health(sync_health: dict) -> list[dict]:
    """Analyze directory sync config and history for issues."""
    findings = []

    conn_data = sync_health.get("connection")
    history_data = sync_health.get("history")

    if not conn_data:
        findings.append({
            "check": "Directory sync connection",
            "status": "error",
            "severity": "HIGH",
            "detail": "Could not retrieve directory sync configuration",
        })
        return findings

    connections = conn_data.get("data", []) if isinstance(conn_data, dict) else []
    if not connections:
        findings.append({
            "check": "Directory sync connection",
            "status": "not configured",
            "severity": "HIGH",
            "detail": "No directory sync connections found — user lifecycle not automated",
        })
        return findings

    for i, conn in enumerate(connections):
        conn_name = conn.get("description", "unknown")
        conn_prefix = f"connection_{i}"

        # Check acknowledgeDisabledAccounts
        if not conn.get("acknowledgeDisabledAccounts", False):
            findings.append({
                "check": f"{conn_prefix}: Acknowledge Disabled Accounts",
                "status": "disabled",
                "severity": "HIGH",
                "detail": (
                    f"Connection '{conn_name}': acknowledgeDisabledAccounts=false — "
                    "Azure AD disabled users are NOT automatically disabled in Mimecast. "
                    "Fix: Administration → Services → Directory Sync → enable 'Acknowledge Disabled Accounts'"
                ),
            })
        else:
            findings.append({
                "check": f"{conn_prefix}: Acknowledge Disabled Accounts",
                "status": "enabled",
                "severity": "OK",
                "detail": f"Connection '{conn_name}': disabled Azure AD users are auto-disabled in Mimecast",
            })

        # Check deleteUsers
        if not conn.get("deleteUsers", False):
            findings.append({
                "check": f"{conn_prefix}: Delete Users on Removal",
                "status": "disabled",
                "severity": "MEDIUM",
                "detail": (
                    f"Connection '{conn_name}': deleteUsers=false — "
                    "Users deleted from Azure AD persist in Mimecast indefinitely"
                ),
            })
        else:
            findings.append({
                "check": f"{conn_prefix}: Delete Users on Removal",
                "status": "enabled",
                "severity": "OK",
                "detail": f"Connection '{conn_name}': deleted Azure AD users are removed from Mimecast",
            })

        # Check maxUnlink threshold
        max_unlink = conn.get("maxUnlink", "")
        if max_unlink == "unlink_10":
            findings.append({
                "check": f"{conn_prefix}: Max Unlink Threshold",
                "status": "low",
                "severity": "LOW",
                "detail": (
                    f"Connection '{conn_name}': maxUnlink=unlink_10 — "
                    "Only 10 accounts can be unlinked per sync. "
                    "With 48+ disabled accounts, remediation will take multiple sync cycles"
                ),
            })

        # Check sync status
        conn_status = conn.get("status", "unknown")
        if conn_status == "error":
            findings.append({
                "check": f"{conn_prefix}: Directory sync status",
                "status": "error",
                "severity": "MEDIUM",
                "detail": f"Connection '{conn_name}' is in error state — check sync history for details",
            })
        else:
            findings.append({
                "check": f"{conn_prefix}: Directory sync status",
                "status": conn_status,
                "severity": "OK",
                "detail": f"Connection '{conn_name}': last sync {conn.get('lastSync', 'unknown')}",
            })

    # Check recent failures from history
    if history_data:
        history_events = history_data.get("data", []) if isinstance(history_data, dict) else []
        recent_failures = [
            e for e in history_events
            if "failed" in e.get("auditType", "").lower()
        ]
        if recent_failures:
            fail_times = [e.get("eventTime", "")[:16].replace("T", " ") for e in recent_failures]
            findings.append({
                "check": "Recent sync failures",
                "status": "failures detected",
                "severity": "MEDIUM",
                "detail": f"{len(recent_failures)} failure(s) in last 48h: {', '.join(fail_times)}. "
                          "Cause: 'Unable to connect to directory service' — likely transient Azure AD issue",
            })
        else:
            findings.append({
                "check": "Recent sync failures",
                "status": "none",
                "severity": "OK",
                "detail": "No sync failures in last 48h",
            })

    return findings


# ── Report Generation ─────────────────────────────────────────────────────────

SEVERITY_ICON = {
    "HIGH": "🔴",
    "MEDIUM": "🟡",
    "LOW": "🔵",
    "OK": "✅",
    "INFO": "ℹ️",
    "ERROR": "❌",
}


def _remediation(email: str) -> str:
    return f"`python3 scripts/mimecast_api.py users delete --email {shlex.quote(email)}`"


def generate_markdown_report(
    sync_results: dict,
    config_findings: list[dict],
    sync_health_findings: list[dict],
    grace_days: int,
    timestamp: str,
    mimecast_segments: dict | None = None,
    azure_segments: dict | None = None,
    fetch_errors: dict | None = None,
) -> str:
    lines = []
    r = sync_results

    orphaned = r["orphaned"]
    missing = r["missing"]
    disabled_active = r["disabled_active"]
    active = r["active"]
    grace = r["grace_period"]
    stale = r["stale_grace"]

    # Header
    lines.append("# Mimecast ↔ M365 Configuration Audit")
    lines.append(f"Generated: {timestamp}\n")

    # Data quality warning — must appear before executive summary
    if fetch_errors:
        lines.append("## ⚠️ Data Quality Warning\n")
        lines.append(
            f"**{len(fetch_errors)} data source(s) failed to fetch.** "
            "Results below may include false positives due to incomplete data. "
            "Verify findings manually before taking action.\n"
        )
        lines.append("| Failed Source | Error |")
        lines.append("|---|---|")
        for source, err in fetch_errors.items():
            lines.append(f"| `{source}` | {err} |")
        lines.append("")

    # Executive summary
    total_issues = len(orphaned) + len(disabled_active) + len(stale)
    lines.append("## Executive Summary\n")
    if total_issues == 0:
        lines.append("✅ No critical user sync issues found.\n")
    else:
        lines.append(f"⚠️ **{total_issues} user account(s) require attention.**\n")

    # Account count breakdown (explain why raw numbers look misleading)
    if mimecast_segments or azure_segments:
        lines.append("## Account Filtering Applied\n")
        lines.append(
            "Both Azure AD and Mimecast contain non-employee entries. "
            "The comparison below uses only **real user accounts** from each side.\n"
        )

    if azure_segments:
        total_az = sum(len(v) for v in azure_segments.values())
        lines.append("**Azure AD**\n")
        lines.append("| Category | Count | Included in Comparison |")
        lines.append("|---|---|---|")
        lines.append(f"| Employees (Member accounts) | {len(azure_segments['employees'])} | ✅ Yes |")
        lines.append(f"| Guests / B2B externals | {len(azure_segments['guests'])} | ❌ No — external contacts, not employees |")
        lines.append(f"| Service accounts (svc-*, sync_*, etc.) | {len(azure_segments['service_accts'])} | ❌ No — infrastructure, no mailbox needed |")
        lines.append(f"| **Total Azure AD entries** | **{total_az}** | |")
        lines.append("")

    if mimecast_segments:
        total_mc = sum(len(v) for v in mimecast_segments.values())
        lines.append("**Mimecast**\n")
        lines.append("| Category | Count | Included in Comparison |")
        lines.append("|---|---|---|")
        lines.append(f"| Real user accounts (LDAP-synced, manual, imported) | {len(mimecast_segments['real_users'])} | ✅ Yes |")
        lines.append(f"| Aliases (secondary email addresses) | {len(mimecast_segments['aliases'])} | ❌ No — same person, different address |")
        lines.append(f"| Distribution lists (LDAP groups) | {len(mimecast_segments['dls'])} | ❌ No — groups, not individuals |")
        lines.append(f"| Email-auto-created (from mail traffic) | {len(mimecast_segments['email_auto'])} | ❌ No — no guaranteed mailbox |")
        lines.append(f"| Infrastructure (abuse@, postmaster@, api-*, ingest_*) | {len(mimecast_segments['infra'])} | ❌ No — domain/system accounts |")
        lines.append(f"| **Total Mimecast entries** | **{total_mc}** | |")
        lines.append("")

    # User sync summary table
    lines.append("## User Sync Summary\n")
    lines.append("| Category | Count | Severity |")
    lines.append("|---|---|---|")
    lines.append(f"| ✅ Active (synced) | {len(active)} | OK |")
    lines.append(f"| 🔴 Orphaned in Mimecast | {len(orphaned)} | HIGH |")
    lines.append(f"| 🟡 Missing from Mimecast | {len(missing)} | MEDIUM |")
    lines.append(f"| 🔴 Disabled in Azure AD but active in Mimecast | {len(disabled_active)} | HIGH |")
    lines.append(f"| ℹ️ Grace period (<{grace_days} days) | {len(grace)} | INFO |")
    lines.append(f"| 🔴 Stale grace (>{grace_days} days) | {len(stale)} | HIGH |")
    lines.append("")

    # Orphaned users
    if orphaned:
        lines.append("## 🔴 Orphaned in Mimecast\n")
        lines.append("Real user accounts in Mimecast with **no matching Azure AD account**.")
        lines.append("Aliases, distribution lists, and email-auto-created entries are excluded from this list.")
        lines.append("These are likely departed employees whose Mimecast accounts were never removed.\n")
        lines.append("| Email | Mimecast Name | Note | Remediation |")
        lines.append("|---|---|---|---|")
        for u in orphaned:
            lines.append(f"| {u['email']} | {u.get('mimecast_name', '')} | {u.get('note', '')} | {_remediation(u['email'])} |")
        lines.append("")

    # Disabled but active in Mimecast
    if disabled_active:
        lines.append("## 🔴 Disabled in Azure AD but Active in Mimecast\n")
        lines.append("Azure AD accounts are **disabled** but Mimecast accounts still exist.")
        lines.append("These employees have left or been offboarded but retain Mimecast access.\n")
        lines.append("| Email | Name | Department | Remediation |")
        lines.append("|---|---|---|---|")
        for u in disabled_active:
            lines.append(f"| {u['email']} | {u.get('azure_display', '')} | {u.get('department', '')} | {_remediation(u['email'])} |")
        lines.append("")

    # Missing from Mimecast
    if missing:
        lines.append("## 🟡 Missing from Mimecast (Active Azure AD Users)\n")
        lines.append("Azure AD accounts are **active** but these users have no Mimecast account.")
        lines.append("These employees are not protected by Mimecast email security.\n")
        lines.append("| Email | Display Name | Department | Job Title | Remediation |")
        lines.append("|---|---|---|---|---|")
        for u in missing:
            provision = (
                f"`python3 scripts/mimecast_api.py users create "
                f"--email {shlex.quote(u['email'])} "
                f"--name {shlex.quote(u.get('azure_display', ''))}`"
            )
            lines.append(f"| {u['email']} | {u.get('azure_display', '')} | {u.get('department', '')} | {u.get('job_title', '')} | {provision} |")
        lines.append("")

    # Grace period
    if grace:
        lines.append("## ℹ️ Grace Period Mailboxes\n")
        lines.append(f"Azure AD disabled within the last {grace_days} days — mailbox transition period is active.\n")
        lines.append("| Email | Name |")
        lines.append("|---|---|")
        for u in grace:
            lines.append(f"| {u['email']} | {u.get('mimecast_name', '')} |")
        lines.append("")

    # Stale grace
    if stale:
        lines.append("## 🔴 Stale Grace Period (Expired Transition Window)\n")
        lines.append(f"Azure AD disabled **more than {grace_days} days ago** — transition window has expired.\n")
        lines.append("| Email | Name | Remediation |")
        lines.append("|---|---|---|")
        for u in stale:
            lines.append(f"| {u['email']} | {u.get('mimecast_name', '')} | {_remediation(u['email'])} |")
        lines.append("")

    # Directory sync health
    if sync_health_findings:
        lines.append("## Directory Sync Health\n")
        lines.append("| Check | Status | Severity | Detail |")
        lines.append("|---|---|---|---|")
        for f in sync_health_findings:
            icon = SEVERITY_ICON.get(f["severity"], "•")
            lines.append(f"| {f['check']} | {icon} {f['status'].upper()} | {f['severity']} | {f['detail']} |")
        lines.append("")

    # Security configuration
    lines.append("## Security Configuration Checks\n")
    lines.append("| Check | Status | Severity | Detail |")
    lines.append("|---|---|---|---|")
    for f in config_findings:
        icon = SEVERITY_ICON.get(f["severity"], "•")
        lines.append(f"| {f['check']} | {icon} {f['status'].upper()} | {f['severity']} | {f['detail']} |")
    lines.append("")

    # Footer
    all_findings = sync_health_findings + config_findings
    high_config = [f for f in all_findings if f["severity"] in {"HIGH"}]
    if high_config:
        lines.append("### ⚠️ High-Severity Configuration Issues\n")
        for f in high_config:
            lines.append(f"- **{f['check']}**: {f['detail']}")
        lines.append("")

    lines.append("---")
    lines.append("*Generated by `audit_m365_sync.py` — Mimecast ↔ M365 Configuration Audit*")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Mimecast ↔ Azure AD configuration audit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--mimecast-profile", default="production",
                        help="Mimecast config profile (default: production)")
    parser.add_argument("--azure-tenant", default="default",
                        help="Azure AD tenant alias (default: default)")
    parser.add_argument("--grace-days", type=int, default=90,
                        help="Days after Azure AD disable to flag as grace period (default: 90)")
    parser.add_argument("--exclude-domains", default="",
                        help="Comma-separated domains to exclude (e.g. 'service.local,noreply.co.com')")
    parser.add_argument("--output", default="-",
                        help="Output file path (default: stdout)")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON findings instead of markdown")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detailed progress")
    parser.add_argument("--svc-prefixes", default="",
                        help=(
                            "Comma-separated list of Azure AD UPN local-part prefixes to treat as "
                            "service accounts (overrides built-in defaults: svc-, sync_, ntservice, etc.). "
                            "Example: --svc-prefixes 'svc-,admin-,bot-'"
                        ))
    args = parser.parse_args()

    # Resolve --svc-prefixes override without mutating the module constant
    svc_prefixes = (
        tuple(p.strip() for p in args.svc_prefixes.split(",") if p.strip())
        if args.svc_prefixes and args.svc_prefixes.strip()
        else AZURE_SVC_PREFIXES
    )

    excluded_domains = {d.strip().lower() for d in args.exclude_domains.split(",") if d.strip()}

    # Validate CLI paths exist
    if not MIMECAST_CLI.exists():
        print(f"Error: Mimecast CLI not found at {MIMECAST_CLI}", file=sys.stderr)
        sys.exit(2)
    if not AZURE_CLI.exists():
        print(f"Error: Azure AD CLI not found at {AZURE_CLI}", file=sys.stderr)
        sys.exit(2)

    print("Mimecast ↔ M365 Configuration Audit", file=sys.stderr)
    print("=" * 40, file=sys.stderr)

    # Fetch data — all 4 sources are independent, run in parallel
    fetch_tasks = {
        "azure_users_raw": lambda: fetch_azure_users(args.azure_tenant, args.verbose),
        "deleted_users": lambda: fetch_azure_deleted_users(args.azure_tenant, args.verbose),
        "mimecast_raw": lambda: fetch_mimecast_users(args.mimecast_profile, args.verbose),
        "azure_domains": lambda: fetch_azure_domains(args.azure_tenant, args.verbose),
    }
    fetch_results: dict = {}
    fetch_errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fn): key for key, fn in fetch_tasks.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                fetch_results[key] = future.result()
            except Exception as e:
                print(f"WARNING: worker failed for {key}: {e}", file=sys.stderr)
                fetch_results[key] = []
                fetch_errors[key] = str(e)  # track which fetches failed
    azure_users_raw = fetch_results["azure_users_raw"]
    deleted_users = fetch_results["deleted_users"]
    mimecast_raw = fetch_results["mimecast_raw"]
    azure_domains = fetch_results["azure_domains"]

    # Segment Azure AD: filter out Guests and service accounts
    azure_segments = filter_azure_users(azure_users_raw, svc_prefixes=svc_prefixes)
    azure_users = azure_segments["employees"]

    # Segment Mimecast: filter out aliases, DLs, email-auto, and infra accounts
    mimecast_segments = segment_mimecast_users(mimecast_raw)
    mimecast_users = mimecast_segments["real_users"]

    print(f"  Azure AD total:          {len(azure_users_raw)}", file=sys.stderr)
    print(f"    ├─ Employees (Members): {len(azure_users)}", file=sys.stderr)
    print(f"    ├─ Guests (B2B):        {len(azure_segments['guests'])}", file=sys.stderr)
    print(f"    └─ Service accounts:    {len(azure_segments['service_accts'])}", file=sys.stderr)
    print(f"  Azure AD deleted: {len(deleted_users)}", file=sys.stderr)
    print(f"  Mimecast total entries:  {len(mimecast_raw)}", file=sys.stderr)
    print(f"    ├─ Real user accounts:  {len(mimecast_users)}", file=sys.stderr)
    print(f"    ├─ Aliases:             {len(mimecast_segments['aliases'])}", file=sys.stderr)
    print(f"    ├─ Distribution lists:  {len(mimecast_segments['dls'])}", file=sys.stderr)
    print(f"    ├─ Email-auto-created:  {len(mimecast_segments['email_auto'])}", file=sys.stderr)
    print(f"    └─ Infra (abuse/api/…): {len(mimecast_segments['infra'])}", file=sys.stderr)

    # Cross-reference employees only
    sync_results = cross_reference(
        azure_users, mimecast_users, deleted_users,
        excluded_domains, args.grace_days,
    )

    total_issues = (
        len(sync_results["orphaned"]) +
        len(sync_results["disabled_active"]) +
        len(sync_results["stale_grace"])
    )
    print(f"  User sync issues: {total_issues}", file=sys.stderr)

    # Fetch config and sync health in parallel — they are independent
    with ThreadPoolExecutor(max_workers=2) as executor:
        f_config = executor.submit(fetch_mimecast_config, args.mimecast_profile, args.verbose)
        f_health = executor.submit(fetch_sync_health, args.mimecast_profile, args.verbose)
    try:
        config = f_config.result()
    except Exception as e:
        print(f"WARNING: fetch_mimecast_config failed: {e}", file=sys.stderr)
        config = {}
        fetch_errors["mimecast_config"] = str(e)
    try:
        sync_health = f_health.result()
    except Exception as e:
        print(f"WARNING: fetch_sync_health failed: {e}", file=sys.stderr)
        sync_health = {}
        fetch_errors["sync_health"] = str(e)
    config_findings = analyze_config(config, azure_domains)
    sync_health_findings = analyze_sync_health(sync_health)

    all_config_issues = [
        f for f in config_findings + sync_health_findings
        if f["severity"] in ("HIGH", "MEDIUM")
    ]
    print(f"  Config issues: {len(all_config_issues)}", file=sys.stderr)

    # Generate output
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M %Z").strip()

    if args.json:
        output = json.dumps({
            "timestamp": timestamp,
            "sync_results": sync_results,
            "config_findings": config_findings,
            "sync_health_findings": sync_health_findings,
            "fetch_errors": fetch_errors,
        }, indent=2)
    else:
        output = generate_markdown_report(
            sync_results, config_findings, sync_health_findings,
            args.grace_days, timestamp, mimecast_segments, azure_segments,
            fetch_errors=fetch_errors,
        )

    if args.output == "-":
        print(output)
    else:
        Path(args.output).write_text(output)
        print(f"Report written to {args.output}", file=sys.stderr)

    # Exit 1 if issues found; exit 2 if data fetch failures occurred
    # When fetch errors are present and issues were found, warn that findings may be false positives
    if fetch_errors:
        print(
            f"WARNING: {len(fetch_errors)} data source(s) failed to fetch: {list(fetch_errors.keys())}. "
            "Findings may include false positives due to incomplete data.",
            file=sys.stderr,
        )
        if total_issues > 0:
            sys.exit(2)  # Data quality issue — distinguish from confirmed sync problems
    sys.exit(1 if total_issues > 0 else 0)


if __name__ == "__main__":
    main()
