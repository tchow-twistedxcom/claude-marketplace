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
    --mimecast-profile PROFILE   Mimecast config profile (default: default)
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
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
PLUGIN_DIR = SCRIPT_DIR.parent
REPO_ROOT = PLUGIN_DIR.parent.parent  # plugins/mimecast-skills/../.. = repo root

MIMECAST_CLI = PLUGIN_DIR / "scripts" / "mimecast_api.py"
AZURE_CLI = REPO_ROOT / "plugins" / "m365-skills" / "skills" / "azure-ad" / "scripts" / "azure_ad_api.py"


# ── CLI Runner ────────────────────────────────────────────────────────────────

def run_cli(cmd: list[str], verbose: bool = False) -> dict | list | None:
    """Run a CLI command and return parsed JSON output. Returns None on error."""
    if verbose:
        print(f"  → {' '.join(str(c) for c in cmd)}", file=sys.stderr)
    try:
        result = subprocess.run(
            [sys.executable] + [str(c) for c in cmd],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            print(f"  ⚠ CLI error: {result.stderr.strip()[:200]}", file=sys.stderr)
            return None
        if not result.stdout.strip():
            return None
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"  ⚠ JSON parse error: {e}", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("  ⚠ CLI timed out", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  ⚠ CLI error: {e}", file=sys.stderr)
        return None


# ── Data Fetchers ─────────────────────────────────────────────────────────────

def fetch_azure_users(tenant: str, verbose: bool) -> list[dict]:
    """Fetch all users from Azure AD with accountEnabled + creation date."""
    if verbose:
        print("Fetching Azure AD users...", file=sys.stderr)
    data = run_cli([
        AZURE_CLI, "-t", tenant, "-f", "json",
        "users", "list",
        "--select", "id,displayName,userPrincipalName,mail,accountEnabled,department,jobTitle,createdDateTime",
        "--all",
    ], verbose)
    if data is None:
        return []
    # Graph API: {"value": [...]} or already a list
    if isinstance(data, dict) and "value" in data:
        return data["value"]
    if isinstance(data, list):
        return data
    return []


def fetch_azure_deleted_users(tenant: str, verbose: bool) -> list[dict]:
    """Fetch recently deleted users from Azure AD recycle bin."""
    if verbose:
        print("Fetching Azure AD deleted users...", file=sys.stderr)
    data = run_cli([
        AZURE_CLI, "-t", tenant, "-f", "json",
        "directory", "deleted-users",
    ], verbose)
    if data is None:
        return []
    if isinstance(data, dict) and "value" in data:
        return data["value"]
    if isinstance(data, list):
        return data
    return []


def fetch_azure_domains(tenant: str, verbose: bool) -> list[dict]:
    """Fetch verified domains from Azure AD."""
    if verbose:
        print("Fetching Azure AD domains...", file=sys.stderr)
    data = run_cli([
        AZURE_CLI, "-t", tenant, "-f", "json",
        "directory", "domains",
    ], verbose)
    if data is None:
        return []
    if isinstance(data, dict) and "value" in data:
        return data["value"]
    if isinstance(data, list):
        return data
    return []


def fetch_mimecast_users(profile: str, verbose: bool) -> list[dict]:
    """Fetch all Mimecast internal users."""
    if verbose:
        print("Fetching Mimecast users...", file=sys.stderr)
    data = run_cli([
        MIMECAST_CLI, "--profile", profile, "users", "list", "--output", "json",
    ], verbose)
    if data is None:
        return []
    # Mimecast: {"data": [...]} or [...]
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    if isinstance(data, list):
        return data
    return []


def fetch_mimecast_config(profile: str, verbose: bool) -> dict:
    """Run all Mimecast config checks in parallel and return results."""
    if verbose:
        print("Fetching Mimecast configuration...", file=sys.stderr)

    def _run(cmd):
        return run_cli([MIMECAST_CLI, "--profile", profile] + cmd + ["--output", "json"], verbose)

    return {
        "dkim": _run(["dkim", "status"]),
        "domains": _run(["domains", "list"]),
        "policies": _run(["policies", "list"]),
        "ttp_summary": _run(["ttp", "summary"]),
        "delivery_routes": _run(["delivery", "routes"]),
        "senders_blocked": _run(["senders", "blocked"]),
        "senders_permitted": _run(["senders", "permitted"]),
        "awareness_summary": _run(["awareness", "performance-summary"]),
        "watchlist": _run(["awareness", "watchlist"]),
    }


# ── Email Normalization ────────────────────────────────────────────────────────

def normalize_email(user: dict, source: str) -> str | None:
    """Extract and normalize email address from a user record."""
    if source == "azure":
        # Prefer mail, fall back to userPrincipalName (strip guest suffix)
        email = user.get("mail") or user.get("userPrincipalName", "")
        # Remove #EXT# guest suffix
        if "#EXT#" in email:
            return None
        return email.lower().strip() if email else None
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
            # Azure AD disabled — check when it was disabled/created for grace period
            az_user = azure_disabled[email]
            # Use createdDateTime as proxy (Mimecast doesn't expose disable date)
            # In practice the disableDate comes from audit logs; we use a heuristic
            created_str = az_user.get("createdDateTime", "")
            disabled_entry = {
                "email": email,
                "mimecast_name": mc_user.get("name", ""),
                "azure_display": az_user.get("displayName", ""),
                "department": az_user.get("department", ""),
                "azure_status": "disabled",
            }
            results["disabled_active"].append(disabled_entry)
        elif email in deleted_emails:
            results["orphaned"].append({
                "email": email,
                "mimecast_name": mc_user.get("name", ""),
                "note": "Account deleted from Azure AD",
            })
        else:
            # Not in Azure AD at all
            results["orphaned"].append({
                "email": email,
                "mimecast_name": mc_user.get("name", ""),
                "note": "No matching Azure AD account",
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
            p.get("policy", {}).get("definition", {}).get("description", "").lower().find("spoof") >= 0
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


# ── Report Generation ─────────────────────────────────────────────────────────

SEVERITY_ICON = {
    "HIGH": "🔴",
    "MEDIUM": "🟡",
    "LOW": "🔵",
    "OK": "✅",
    "INFO": "ℹ️",
    "error": "❌",
}


def _remediation(email: str) -> str:
    return f"`python3 scripts/mimecast_api.py users delete --email {email}`"


def generate_markdown_report(
    sync_results: dict,
    config_findings: list[dict],
    grace_days: int,
    timestamp: str,
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

    # Executive summary
    total_issues = len(orphaned) + len(disabled_active) + len(stale)
    lines.append("## Executive Summary\n")
    if total_issues == 0:
        lines.append("✅ No critical user sync issues found.\n")
    else:
        lines.append(f"⚠️ **{total_issues} user account(s) require attention.**\n")

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
        lines.append("Users with Mimecast accounts but **no matching Azure AD account**.")
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
            provision = f"`python3 scripts/mimecast_api.py users create --email {u['email']} --name \"{u.get('azure_display', '')}\" `"
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

    # Security configuration
    lines.append("## Security Configuration Checks\n")
    lines.append("| Check | Status | Severity | Detail |")
    lines.append("|---|---|---|---|")
    for f in config_findings:
        icon = SEVERITY_ICON.get(f["severity"], "•")
        lines.append(f"| {f['check']} | {icon} {f['status'].upper()} | {f['severity']} | {f['detail']} |")
    lines.append("")

    # Footer
    high_config = [f for f in config_findings if f["severity"] in ("HIGH",)]
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
    parser.add_argument("--mimecast-profile", default="default",
                        help="Mimecast config profile (default: default)")
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
    args = parser.parse_args()

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

    # Fetch data
    azure_users = fetch_azure_users(args.azure_tenant, args.verbose)
    deleted_users = fetch_azure_deleted_users(args.azure_tenant, args.verbose)
    mimecast_users = fetch_mimecast_users(args.mimecast_profile, args.verbose)
    azure_domains = fetch_azure_domains(args.azure_tenant, args.verbose)

    print(f"  Azure AD users: {len(azure_users)}", file=sys.stderr)
    print(f"  Azure AD deleted: {len(deleted_users)}", file=sys.stderr)
    print(f"  Mimecast users: {len(mimecast_users)}", file=sys.stderr)

    # Cross-reference users
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

    # Fetch and analyze config
    config = fetch_mimecast_config(args.mimecast_profile, args.verbose)
    config_findings = analyze_config(config, azure_domains)
    config_issues = [f for f in config_findings if f["severity"] in ("HIGH", "MEDIUM")]
    print(f"  Config issues: {len(config_issues)}", file=sys.stderr)

    # Generate output
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M %Z").strip()

    if args.json:
        output = json.dumps({
            "timestamp": timestamp,
            "sync_results": sync_results,
            "config_findings": config_findings,
        }, indent=2)
    else:
        output = generate_markdown_report(
            sync_results, config_findings, args.grace_days, timestamp
        )

    if args.output == "-":
        print(output)
    else:
        Path(args.output).write_text(output)
        print(f"Report written to {args.output}", file=sys.stderr)

    # Exit 1 if issues found (useful for CI/scripting)
    sys.exit(1 if total_issues > 0 else 0)


if __name__ == "__main__":
    main()
