#!/usr/bin/env python3
"""
Infrastructure health check — queries Tailscale, NinjaOne API, and Portainer MCP.

Usage:
  python3 health_check.py              # Full report
  python3 health_check.py --alerts     # Alerts only
  python3 health_check.py --servers    # Servers only
  python3 health_check.py --containers # Containers only
"""

import argparse
import json
import subprocess
import sys
from urllib.request import urlopen
from urllib.error import URLError

NINJAONE_API = "http://localhost:3050"
DASHBOARD_API = "http://localhost:3060/api"


def get(url, timeout=10):
    try:
        with urlopen(url, timeout=timeout) as r:
            return json.loads(r.read())
    except URLError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def tailscale_status():
    try:
        out = subprocess.check_output(["tailscale", "status", "--json"], timeout=10)
        data = json.loads(out)
        devices = []
        if data.get("Self"):
            s = data["Self"]
            devices.append({"hostname": s.get("HostName", ""), "os": s.get("OS", ""), "online": True, "self": True})
        for peer in data.get("Peer", {}).values():
            devices.append({
                "hostname": peer.get("HostName", ""),
                "os": peer.get("OS", ""),
                "online": peer.get("Online", False),
                "tags": peer.get("Tags", []),
                "lastSeen": peer.get("LastSeen", ""),
            })
        return devices
    except Exception as e:
        return [{"error": str(e)}]


def fmt_severity(s):
    s = (s or "N/A").upper()
    colors = {"CRITICAL": "\033[91m", "MAJOR": "\033[91m", "MODERATE": "\033[93m", "MINOR": "\033[94m"}
    reset = "\033[0m"
    return f"{colors.get(s, '')}{s}{reset}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--alerts", action="store_true")
    parser.add_argument("--servers", action="store_true")
    parser.add_argument("--containers", action="store_true")
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args()
    all_sections = not any([args.alerts, args.servers, args.containers])

    print("\n\033[1m=== Infrastructure Health Check ===\033[0m\n")

    # ── Servers ─────────────────────────────────────────────────────────────
    if all_sections or args.servers:
        print("\033[1m● Servers (Tailscale)\033[0m")
        devices = tailscale_status()
        tagged = [d for d in devices if d.get("tags") and not d.get("error")]
        online = [d for d in tagged if d.get("online")]
        offline = [d for d in tagged if not d.get("online")]
        print(f"  Online : {len(online)}  Offline: {len(offline)}")
        if offline:
            print("  \033[91mOffline servers:\033[0m")
            for d in offline:
                last = d.get("lastSeen", "unknown")[:16]
                print(f"    ✗ {d['hostname']} (last seen {last})")
        for d in online:
            print(f"    ✓ {d['hostname']} [{d.get('os','')}]")
        print()

    # ── Alerts ───────────────────────────────────────────────────────────────
    if all_sections or args.alerts:
        print("\033[1m● Active Alerts (NinjaOne)\033[0m")
        alerts = get(f"{NINJAONE_API}/api/alerts")
        if isinstance(alerts, list):
            by_sev = {}
            for a in alerts:
                sev = (a.get("severity") or "N/A").upper()
                by_sev[sev] = by_sev.get(sev, 0) + 1
            total = len(alerts)
            if total == 0:
                print("  \033[92m✓ No active alerts\033[0m")
            else:
                summary = "  " + "  ".join(f"{fmt_severity(k)}: {v}" for k, v in sorted(by_sev.items()))
                print(f"  Total: {total}")
                print(summary)
                # Show top 5 most severe
                sev_order = {"CRITICAL": 0, "MAJOR": 1, "MODERATE": 2, "MINOR": 3}
                top = sorted(alerts, key=lambda a: sev_order.get((a.get("severity") or "").upper(), 9))[:5]
                print("  Recent critical/moderate:")
                for a in top:
                    msg = a.get("message", "")[:80]
                    print(f"    [{fmt_severity(a.get('severity','?'))}] {msg}")
        else:
            print(f"  \033[91mError: {alerts.get('error')}\033[0m")
        print()

    # ── Containers ───────────────────────────────────────────────────────────
    if all_sections or args.containers:
        print("\033[1m● Containers (Portainer)\033[0m")
        containers = get(f"{DASHBOARD_API}/containers")
        if isinstance(containers, list):
            running = [c for c in containers if c.get("state") == "running"]
            stopped = [c for c in containers if c.get("state") in ("exited", "dead")]
            other = [c for c in containers if c.get("state") not in ("running", "exited", "dead")]
            print(f"  Running: {len(running)}  Stopped: {len(stopped)}  Other: {len(other)}")
            if stopped:
                print("  \033[91mStopped containers:\033[0m")
                for c in stopped[:10]:
                    print(f"    ✗ {c['name']} [{c['envName']}] — {c['status']}")
        else:
            print(f"  \033[91mError: {containers.get('error','unknown')}\033[0m")
        print()

    print("\033[90mDashboard: http://100.90.23.64:3060\033[0m\n")


if __name__ == "__main__":
    main()
