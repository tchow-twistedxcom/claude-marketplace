#!/usr/bin/env python3
"""
Comprehensive compromise sweep for Azure AD / Entra ID.

Runs multiple detection vectors in sequence, correlates results client-side,
and produces a unified report of affected accounts with confidence levels.

Detection vectors:
  1. IP sweep       — sign-ins from known attacker IPs (--ips)
  2. MFA fatigue    — error 50199 failures followed by success within N minutes
  3. Risk detections — all risk events in time window (requires P1+)
  4. Risk IP cross-ref — IPs from risk detections used for sign-in sweep
  5. Audit anomalies  — password resets, MFA changes, consent grants per victim
  6. Auth methods     — current MFA enrollment per victim

Usage:
  python3 sweep.py --hours 48
  python3 sweep.py --ips 203.0.113.50,198.51.100.20 --hours 48
  python3 sweep.py --since 2026-03-30T00:00:00Z
  python3 sweep.py --hours 72 --mfa-window 15 --json > sweep_report.json
"""

import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

# Reuse existing modules
from azure_ad_api import AzureADAPI, build_time_filter
from formatters import print_error, print_warning


# Audit activity names that indicate post-compromise actions
SUSPICIOUS_AUDIT_ACTIVITIES = [
    'Reset user password',
    'Change user password',
    'Update user',
    'Register security info',
    'Delete security info',
    'Add service principal credentials',
    'Consent to application',
    'Add member to role',
    'Add app role assignment to user',
    'Update application',
]


def _values(response) -> list:
    """Extract 'value' list from Graph API response or return list directly."""
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        return response.get("value", [])
    return []


def collect_sign_ins_by_ip(api: AzureADAPI, ip: str, filter_base: str) -> list:
    """Fetch all sign-ins from a specific IP address."""
    f = f"ipAddress eq '{ip}'"
    if filter_base:
        f = f"{filter_base} and {f}"
    try:
        result = api.security_sign_ins(top=500, filter_query=f, all_pages=True)
        return _values(result)
    except Exception as e:
        print_warning(f"IP sweep failed for {ip}: {e}")
        return []


def collect_mfa_fatigue_victims(api: AzureADAPI, filter_base: str, window_minutes: int) -> dict:
    """
    Detect MFA fatigue: find users who had error 50199 (MFA push fatigue) failures
    followed by a successful sign-in within `window_minutes`.

    Returns: {upn: [{'failure_time': dt, 'success_time': dt, 'ip': str}]}
    """
    # Pull all 50199 failures in the time window
    f_fail = "status/errorCode eq 50199"
    if filter_base:
        f_fail = f"{filter_base} and {f_fail}"
    try:
        fail_result = api.security_sign_ins(top=1000, filter_query=f_fail, all_pages=True)
        failures = _values(fail_result)
    except Exception as e:
        print_warning(f"MFA fatigue query (failures) failed: {e}")
        failures = []

    if not failures:
        return {}

    # Pre-group failures by UPN once (O(n)) to avoid O(n²) re-scan per UPN
    failures_by_upn: dict = defaultdict(list)
    for s in failures:
        upn = s.get('userPrincipalName', '')
        if upn:
            failures_by_upn[upn].append(s)

    upns_with_failures = set(failures_by_upn.keys())

    victims = {}

    for upn in upns_with_failures:
        # Escape single quotes in UPN for OData filter safety
        safe_upn = upn.replace("'", "''")
        # For each UPN, pull their successes in the same window
        f_success = f"userPrincipalName eq '{safe_upn}' and status/errorCode eq 0"
        if filter_base:
            f_success = f"{filter_base} and {f_success}"
        try:
            succ_result = api.security_sign_ins(top=200, filter_query=f_success, all_pages=False)
            successes = _values(succ_result)
        except Exception as e:
            print(f"  [!] Success query failed for {upn}: {e}", file=sys.stderr)
            continue

        # Build timeline: failures for this UPN (pre-grouped for O(1) lookup)
        user_failures = failures_by_upn[upn]

        # Cross-reference: is any success within window_minutes of a failure?
        evidence = []
        for fail in user_failures:
            fail_time_str = fail.get('createdDateTime', '')
            try:
                fail_dt = datetime.fromisoformat(fail_time_str.replace('Z', '+00:00'))
            except ValueError:
                continue
            for succ in successes:
                succ_time_str = succ.get('createdDateTime', '')
                try:
                    succ_dt = datetime.fromisoformat(succ_time_str.replace('Z', '+00:00'))
                except ValueError:
                    continue
                delta = succ_dt - fail_dt
                if timedelta(0) < delta <= timedelta(minutes=window_minutes):
                    evidence.append({
                        'failure_time': fail_time_str,
                        'success_time': succ_time_str,
                        'failure_ip': fail.get('ipAddress', ''),
                        'success_ip': succ.get('ipAddress', ''),
                        'app': succ.get('appDisplayName', ''),
                    })
                    break  # One confirmed instance is enough
            if evidence:
                break

        if evidence:
            victims[upn] = evidence

    return victims


def collect_risk_detections(api: AzureADAPI, filter_base: str) -> list:
    """Fetch all risk detections in the time window."""
    try:
        result = api.security_risk_detections(
            top=500,
            filter_query=filter_base or None,
            all_pages=True
        )
        return _values(result)
    except Exception as e:
        print_warning(f"Risk detections unavailable (requires P1+): {e}")
        return []


def collect_suspicious_audit_events(api: AzureADAPI, upn: str, user_id: str, filter_base: str) -> list:
    """Fetch suspicious audit log entries for a specific user."""
    # Escape single quotes in UPN for OData filter safety
    safe_upn = upn.replace("'", "''")
    f = f"initiatedBy/user/id eq '{user_id}' or targetResources/any(t: t/userPrincipalName eq '{safe_upn}')"
    if filter_base:
        f = f"{filter_base} and ({f})"
    try:
        result = api.security_audit_logs(top=100, filter_query=f, all_pages=False)
        events = _values(result)
        return [e for e in events if e.get('activityDisplayName') in SUSPICIOUS_AUDIT_ACTIVITIES]
    except Exception as e:
        print(f"WARNING: collect_suspicious_audit_events failed for {upn}: {e}", file=sys.stderr)
        return []


def collect_auth_methods(api: AzureADAPI, upn: str) -> list:
    """Fetch current authentication methods for a user."""
    try:
        result = api.security_auth_methods(upn)
        return _values(result)
    except Exception as e:
        print(f"WARNING: collect_auth_methods failed for {upn}: {e}", file=sys.stderr)
        return []


def resolve_user_id(api: AzureADAPI, upn: str) -> str:
    """Resolve UPN to object ID. Returns empty string on failure."""
    try:
        user = api.users_get(upn)
        return user.get('id', '') if isinstance(user, dict) else ''
    except Exception:
        return ''


def _process_victim(api: AzureADAPI, upn: str, risk_filter_base: str) -> tuple:
    """
    Fetch audit anomalies and auth methods for a single victim account.

    Returns: (upn, audit_events, auth_methods)
    """
    user_id = resolve_user_id(api, upn)
    audit_events = []
    if user_id:
        audit_events = collect_suspicious_audit_events(api, upn, user_id, risk_filter_base)
    auth_methods = collect_auth_methods(api, upn)
    return (upn, audit_events, auth_methods)


def run_sweep(api: AzureADAPI, args) -> dict:
    """
    Execute the full sweep and return a structured results dict.
    """
    # Build base time filter
    filter_base = build_time_filter(
        'createdDateTime',
        hours=getattr(args, 'hours', None),
        days=getattr(args, 'days', None),
        since=getattr(args, 'since', None)
    )
    risk_filter_base = build_time_filter(
        'activityDateTime',
        hours=getattr(args, 'hours', None),
        days=getattr(args, 'days', None),
        since=getattr(args, 'since', None)
    )

    # victim_evidence: {upn: {vector: [evidence_items]}}
    victim_evidence = defaultdict(lambda: defaultdict(list))

    # ── Vector 1: IP sweep ──────────────────────────────────────────────────
    suspect_ips = set()
    if getattr(args, 'ips', None):
        suspect_ips.update(ip.strip() for ip in args.ips.split(',') if ip.strip())

    if suspect_ips:
        print(f"[1/5] IP sweep: querying {len(suspect_ips)} IP(s)...", file=sys.stderr, flush=True)
        all_v1_sign_ins: list = []
        with ThreadPoolExecutor(max_workers=min(len(suspect_ips), 10)) as executor:
            futures = {executor.submit(collect_sign_ins_by_ip, api, ip, filter_base): ip
                       for ip in suspect_ips}
            for future in as_completed(futures):
                ip = futures[future]
                try:
                    results = future.result()
                    all_v1_sign_ins.extend((ip, si) for si in results)
                except Exception as e:
                    print(f"  [!] Error sweeping IP {ip}: {e}", file=sys.stderr)
        for ip, si in all_v1_sign_ins:
            upn = si.get('userPrincipalName', '')
            if upn:
                victim_evidence[upn]['ip_sweep'].append({
                    'ip': ip,
                    'time': si.get('createdDateTime', ''),
                    'app': si.get('appDisplayName', ''),
                    'error_code': si.get('status', {}).get('errorCode', ''),
                })
    else:
        print("[1/5] IP sweep: skipped (no --ips provided)", file=sys.stderr, flush=True)

    # ── Vector 2: MFA fatigue ───────────────────────────────────────────────
    print(f"[2/5] MFA fatigue detection (window={args.mfa_window}m)...", file=sys.stderr, flush=True)
    fatigue_victims = collect_mfa_fatigue_victims(api, filter_base, args.mfa_window)
    for upn, evidence in fatigue_victims.items():
        victim_evidence[upn]['mfa_fatigue'].extend(evidence)

    # ── Vector 3: Risk detections ───────────────────────────────────────────
    print("[3/5] Risk detections (requires Entra ID P1+)...", file=sys.stderr, flush=True)
    risk_events = collect_risk_detections(api, risk_filter_base)
    for event in risk_events:
        upn = event.get('userPrincipalName', '')
        if upn:
            victim_evidence[upn]['risk_detection'].append({
                'type': event.get('riskEventType', ''),
                'level': event.get('riskLevel', ''),
                'ip': event.get('ipAddress', ''),
                'time': event.get('activityDateTime', ''),
            })
            # Collect IPs from risk events for cross-reference
            ip = event.get('ipAddress', '')
            if ip:
                suspect_ips.add(ip)

    # ── Vector 4: Risk IP cross-reference ──────────────────────────────────
    new_ips = suspect_ips - set(getattr(args, 'ips', '').split(',') if getattr(args, 'ips', None) else [])
    if new_ips:
        print(f"[4/5] Cross-referencing {len(new_ips)} IPs from risk events...", file=sys.stderr, flush=True)
        all_v4_sign_ins: list = []
        with ThreadPoolExecutor(max_workers=min(len(new_ips), 10)) as executor:
            futures = {executor.submit(collect_sign_ins_by_ip, api, ip, filter_base): ip
                       for ip in new_ips}
            for future in as_completed(futures):
                ip = futures[future]
                try:
                    results = future.result()
                    all_v4_sign_ins.extend((ip, si) for si in results)
                except Exception as e:
                    print(f"  [!] Error sweeping IP {ip}: {e}", file=sys.stderr)
        for ip, si in all_v4_sign_ins:
            upn = si.get('userPrincipalName', '')
            if upn:
                victim_evidence[upn]['ip_crossref'].append({
                    'ip': ip,
                    'time': si.get('createdDateTime', ''),
                    'app': si.get('appDisplayName', ''),
                    'error_code': si.get('status', {}).get('errorCode', ''),
                })
    else:
        print("[4/5] Cross-reference: no new IPs from risk detections", file=sys.stderr, flush=True)

    # ── Vectors 5+6: Audit anomalies + auth methods per victim ─────────────
    all_victims = list(victim_evidence.keys())
    if all_victims:
        print(f"[5/5] Audit logs + auth methods for {len(all_victims)} flagged account(s)...", file=sys.stderr, flush=True)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(_process_victim, api, upn, risk_filter_base): upn
                       for upn in all_victims}
            for future in as_completed(futures):
                victim_upn = futures[future]
                try:
                    upn, audit_events, auth_methods = future.result()
                    if audit_events:
                        victim_evidence[upn]['audit_anomalies'].extend([
                            {'activity': e.get('activityDisplayName', ''), 'time': e.get('activityDateTime', '')}
                            for e in audit_events
                        ])
                    if auth_methods:
                        victim_evidence[upn]['auth_methods'] = [
                            {'type': m.get('@odata.type', ''), 'display': m.get('displayName', m.get('phoneNumber', ''))}
                            for m in auth_methods
                        ]
                except Exception as e:
                    print(f"WARNING: Vector 5 failed for {victim_upn}: {e}", file=sys.stderr)
    else:
        print("[5/5] No flagged accounts — nothing to audit", file=sys.stderr, flush=True)

    return dict(victim_evidence)


def compute_confidence(evidence: dict) -> str:
    """Return HIGH/MEDIUM/LOW based on evidence weight."""
    score = 0
    if evidence.get('mfa_fatigue'):
        score += 3  # Strongest signal — confirmed MFA bypass
    if evidence.get('risk_detection'):
        score += 2
    if evidence.get('ip_sweep') or evidence.get('ip_crossref'):
        score += 1
    if evidence.get('audit_anomalies'):
        score += 1
    if score >= 3:
        return 'HIGH'
    elif score >= 2:
        return 'MEDIUM'
    return 'LOW'


def build_evidence_summary(evidence: dict) -> str:
    """Build a short evidence string for the table."""
    parts = []
    if evidence.get('mfa_fatigue'):
        parts.append('MFA fatigue (50199→0)')
    if evidence.get('risk_detection'):
        types = set(e['type'] for e in evidence['risk_detection'])
        parts.append(f"risk: {', '.join(sorted(types)[:2])}")
    if evidence.get('ip_sweep') or evidence.get('ip_crossref'):
        ips = set(e['ip'] for e in evidence.get('ip_sweep', []) + evidence.get('ip_crossref', []))
        parts.append(f"attacker IP ({', '.join(sorted(ips)[:2])})")
    if evidence.get('audit_anomalies'):
        acts = set(e['activity'] for e in evidence['audit_anomalies'])
        parts.append(f"audit: {', '.join(sorted(acts)[:2])}")
    return '; '.join(parts) or 'No specific evidence'


def print_report(results: dict, json_output: bool = False):
    """Print the sweep report."""
    if not results:
        print("\nNo compromised accounts found.")
        return

    if json_output:
        report = []
        for upn, evidence in sorted(results.items()):
            report.append({
                'upn': upn,
                'confidence': compute_confidence(evidence),
                'evidence': dict(evidence),
            })
        print(json.dumps(report, indent=2, default=str))
        return

    # Table output
    rows = []
    for upn, evidence in sorted(results.items()):
        rows.append({
            'upn': upn,
            'confidence': compute_confidence(evidence),
            'summary': build_evidence_summary(evidence),
        })

    # Sort by confidence (HIGH first)
    order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    rows.sort(key=lambda r: order[r['confidence']])

    # Column widths
    w_upn = max(len(r['upn']) for r in rows)
    w_upn = max(w_upn, 40)
    w_conf = 10

    print(f"\n{'=' * (w_upn + w_conf + 80)}")
    print(f"COMPROMISE SWEEP RESULTS — {len(rows)} account(s) flagged")
    print(f"{'=' * (w_upn + w_conf + 80)}")
    header = f"{'UPN'.ljust(w_upn)} | {'Confidence'.ljust(w_conf)} | Evidence"
    print(header)
    print('-' * len(header))
    for row in rows:
        print(f"{row['upn'].ljust(w_upn)} | {row['confidence'].ljust(w_conf)} | {row['summary']}")
    print()

    # Summary counts
    high = sum(1 for r in rows if r['confidence'] == 'HIGH')
    med = sum(1 for r in rows if r['confidence'] == 'MEDIUM')
    low = sum(1 for r in rows if r['confidence'] == 'LOW')
    print(f"HIGH confidence: {high}  |  MEDIUM: {med}  |  LOW: {low}")
    print()
    print("Next steps for HIGH/MEDIUM accounts:")
    print("  python3 azure_ad_api.py security revoke-sessions <UPN> --confirm")
    print("  python3 azure_ad_api.py security auth-methods <UPN>")
    print("  python3 azure_ad_api.py security audit-logs --user <UPN> --days 7")


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Azure AD comprehensive compromise sweep',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--ips', help='Comma-separated known attacker IP addresses')
    parser.add_argument('--mfa-window', type=int, default=10, dest='mfa_window',
                        help='Minutes between failure and success to flag as MFA fatigue (default: 10)')
    parser.add_argument('--json', action='store_true', help='Output JSON instead of table')
    parser.add_argument('-t', '--tenant', default='default', help='Tenant alias from config')

    time_group = parser.add_argument_group('time range (required — at least one)')
    time_group.add_argument('--hours', type=int, help='Look back N hours')
    time_group.add_argument('--days', type=int, help='Look back N days')
    time_group.add_argument('--since', help='ISO 8601 start datetime (e.g., 2026-03-30T00:00:00Z)')

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    if not any([args.hours, args.days, args.since]):
        parser.error("Specify a time range: --hours N, --days N, or --since DATETIME")

    api = AzureADAPI(tenant=args.tenant)

    try:
        results = run_sweep(api, args)
        print_report(results, json_output=args.json)
    except KeyboardInterrupt:
        print("\nSweep interrupted.", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
