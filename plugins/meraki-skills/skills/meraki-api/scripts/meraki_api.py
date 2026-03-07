#!/usr/bin/env python3
"""
Meraki Dashboard API CLI

Command-line interface for Cisco Meraki Dashboard API operations.
Covers organizations, networks, devices, clients, wireless, switches, and events.
"""

import argparse
import json
import sys
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode


# ─── Config ──────────────────────────────────────────────────────────────────

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "meraki_config.json"
DEFAULT_API_URL = "https://api.meraki.com/api/v1"


def load_config(config_path=None):
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def get_api_key(config_path=None):
    key = os.environ.get("MERAKI_API_KEY", "")
    if not key:
        cfg = load_config(config_path)
        key = cfg.get("api_key", "")
    if not key:
        print("ERROR: No API key found. Set MERAKI_API_KEY or configure config/meraki_config.json", file=sys.stderr)
        sys.exit(1)
    return key


def get_api_url(config_path=None):
    url = os.environ.get("MERAKI_API_URL", "")
    if not url:
        cfg = load_config(config_path)
        url = cfg.get("api_url", DEFAULT_API_URL)
    return url.rstrip("/")


# ─── HTTP Client ─────────────────────────────────────────────────────────────

class MerakiAPIError(Exception):
    pass


def api_request(method, endpoint, api_key, base_url, params=None, data=None):
    url = f"{base_url}/{endpoint.lstrip('/')}"
    if params:
        params = {k: v for k, v in params.items() if v is not None}
        if params:
            url += "?" + urlencode(params, doseq=True)

    body = json.dumps(data).encode() if data else None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Cisco-Meraki-API-Key": api_key,  # legacy header, some endpoints need it
    }

    req = Request(url, data=body, headers=headers, method=method.upper())
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return json.loads(raw) if raw.strip() else {}
    except HTTPError as e:
        body_text = e.read().decode(errors="replace")
        raise MerakiAPIError(f"HTTP {e.code} {e.reason}: {body_text}")
    except URLError as e:
        raise MerakiAPIError(f"Connection error: {e.reason}")


# ─── Output ──────────────────────────────────────────────────────────────────

def print_output(data, fmt="json"):
    if fmt == "json":
        print(json.dumps(data, indent=2))
    elif fmt == "compact":
        if isinstance(data, list):
            for item in data:
                print(json.dumps(item))
        else:
            print(json.dumps(data))
    elif fmt == "count":
        if isinstance(data, list):
            print(len(data))
        else:
            print(1)
    else:
        print(json.dumps(data, indent=2))


# ─── Organizations ────────────────────────────────────────────────────────────

def cmd_orgs(args, api_key, base_url):
    if args.action == "list":
        result = api_request("GET", "/organizations", api_key, base_url)
        print_output(result, args.format)

    elif args.action == "get":
        result = api_request("GET", f"/organizations/{args.org_id}", api_key, base_url)
        print_output(result, args.format)

    elif args.action == "inventory":
        params = {}
        if args.used_state:
            params["usedState"] = args.used_state
        if args.search:
            params["search"] = args.search
        result = api_request("GET", f"/organizations/{args.org_id}/inventory/devices",
                             api_key, base_url, params=params)
        print_output(result, args.format)

    elif args.action == "uplinks":
        result = api_request("GET", f"/organizations/{args.org_id}/uplinks/statuses",
                             api_key, base_url)
        print_output(result, args.format)

    elif args.action == "license":
        result = api_request("GET", f"/organizations/{args.org_id}/licenses/overview",
                             api_key, base_url)
        print_output(result, args.format)


# ─── Networks ─────────────────────────────────────────────────────────────────

def cmd_networks(args, api_key, base_url):
    if args.action == "list":
        params = {}
        if args.tags:
            params["tags[]"] = args.tags.split(",")
        result = api_request("GET", f"/organizations/{args.org_id}/networks",
                             api_key, base_url, params=params)
        print_output(result, args.format)

    elif args.action == "get":
        result = api_request("GET", f"/networks/{args.network_id}", api_key, base_url)
        print_output(result, args.format)

    elif args.action == "devices":
        result = api_request("GET", f"/networks/{args.network_id}/devices",
                             api_key, base_url)
        print_output(result, args.format)

    elif args.action == "clients":
        timespan = args.timespan or 86400
        result = api_request("GET", f"/networks/{args.network_id}/clients",
                             api_key, base_url,
                             params={"timespan": timespan, "perPage": 200})
        print_output(result, args.format)

    elif args.action == "alerts":
        result = api_request("GET", f"/networks/{args.network_id}/alerts/settings",
                             api_key, base_url)
        print_output(result, args.format)

    elif args.action == "events":
        params = {"perPage": 100}
        if args.timespan:
            params["timespan"] = args.timespan
        if args.product_type:
            params["productType"] = args.product_type
        if args.event_types:
            params["includedEventTypes[]"] = args.event_types.split(",")
        result = api_request("GET", f"/networks/{args.network_id}/events",
                             api_key, base_url, params=params)
        print_output(result, args.format)

    elif args.action == "health":
        result = api_request("GET", f"/networks/{args.network_id}/health",
                             api_key, base_url)
        print_output(result, args.format)

    elif args.action == "traffic":
        params = {"timespan": args.timespan or 86400}
        result = api_request("GET", f"/networks/{args.network_id}/traffic",
                             api_key, base_url, params=params)
        print_output(result, args.format)


# ─── Devices ──────────────────────────────────────────────────────────────────

def cmd_devices(args, api_key, base_url):
    if args.action == "get":
        result = api_request("GET", f"/devices/{args.serial}", api_key, base_url)
        print_output(result, args.format)

    elif args.action == "uplink":
        result = api_request("GET", f"/devices/{args.serial}/appliance/uplinks/settings",
                             api_key, base_url)
        print_output(result, args.format)

    elif args.action == "lldp-cdp":
        result = api_request("GET", f"/devices/{args.serial}/lldpCdp", api_key, base_url)
        print_output(result, args.format)

    elif args.action == "clients":
        params = {"timespan": args.timespan or 86400}
        result = api_request("GET", f"/devices/{args.serial}/clients",
                             api_key, base_url, params=params)
        print_output(result, args.format)

    elif args.action == "reboot":
        result = api_request("POST", f"/devices/{args.serial}/reboot", api_key, base_url)
        print(f"Reboot initiated for {args.serial}")
        print_output(result, args.format)


# ─── Switch ───────────────────────────────────────────────────────────────────

def cmd_switch(args, api_key, base_url):
    if args.action == "ports":
        result = api_request("GET", f"/devices/{args.serial}/switch/ports",
                             api_key, base_url)
        print_output(result, args.format)

    elif args.action == "port-statuses":
        result = api_request("GET", f"/devices/{args.serial}/switch/ports/statuses",
                             api_key, base_url)
        print_output(result, args.format)

    elif args.action == "routing":
        result = api_request("GET", f"/devices/{args.serial}/switch/routing/interfaces",
                             api_key, base_url)
        print_output(result, args.format)

    elif args.action == "dhcp":
        result = api_request("GET", f"/networks/{args.network_id}/switch/dhcp/v4/servers",
                             api_key, base_url)
        print_output(result, args.format)

    elif args.action == "vlans":
        result = api_request("GET", f"/networks/{args.network_id}/switch/stacks",
                             api_key, base_url)
        print_output(result, args.format)


# ─── Wireless ─────────────────────────────────────────────────────────────────

def cmd_wireless(args, api_key, base_url):
    if args.action == "ssids":
        result = api_request("GET", f"/networks/{args.network_id}/wireless/ssids",
                             api_key, base_url)
        print_output(result, args.format)

    elif args.action == "status":
        result = api_request("GET", f"/networks/{args.network_id}/wireless/status",
                             api_key, base_url)
        print_output(result, args.format)

    elif args.action == "clients":
        params = {"timespan": args.timespan or 86400, "perPage": 200}
        result = api_request("GET", f"/networks/{args.network_id}/wireless/clients/connectionStats",
                             api_key, base_url, params=params)
        print_output(result, args.format)

    elif args.action == "channel-utilization":
        params = {"timespan": args.timespan or 3600, "resolution": 3600}
        result = api_request("GET", f"/networks/{args.network_id}/wireless/channelUtilizationHistory",
                             api_key, base_url, params=params)
        print_output(result, args.format)

    elif args.action == "health":
        params = {"timespan": args.timespan or 3600}
        result = api_request("GET", f"/networks/{args.network_id}/wireless/failedConnections",
                             api_key, base_url, params=params)
        print_output(result, args.format)


# ─── Appliance ────────────────────────────────────────────────────────────────

def cmd_appliance(args, api_key, base_url):
    if args.action == "vlans":
        result = api_request("GET", f"/networks/{args.network_id}/appliance/vlans",
                             api_key, base_url)
        print_output(result, args.format)

    elif args.action == "firewall":
        result = api_request("GET", f"/networks/{args.network_id}/appliance/firewall/l3FirewallRules",
                             api_key, base_url)
        print_output(result, args.format)

    elif args.action == "uplinks":
        result = api_request("GET", f"/networks/{args.network_id}/appliance/uplinks/usageHistory",
                             api_key, base_url, params={"timespan": args.timespan or 86400})
        print_output(result, args.format)

    elif args.action == "vpn":
        result = api_request("GET", f"/networks/{args.network_id}/appliance/vpn/siteToSiteVpn",
                             api_key, base_url)
        print_output(result, args.format)

    elif args.action == "dhcp":
        result = api_request("GET", f"/networks/{args.network_id}/appliance/dhcp/subnets",
                             api_key, base_url)
        print_output(result, args.format)


# ─── Camera ───────────────────────────────────────────────────────────────────

def cmd_camera(args, api_key, base_url):
    if args.action == "snapshot":
        result = api_request("POST", f"/devices/{args.serial}/camera/generateSnapshot",
                             api_key, base_url)
        print_output(result, args.format)

    elif args.action == "video-link":
        result = api_request("GET", f"/devices/{args.serial}/camera/videoLink",
                             api_key, base_url)
        print_output(result, args.format)

    elif args.action == "analytics":
        params = {"timespan": args.timespan or 3600}
        result = api_request("GET", f"/devices/{args.serial}/camera/analytics/recent",
                             api_key, base_url, params=params)
        print_output(result, args.format)


# ─── Argument Parser ──────────────────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        prog="meraki_api.py",
        description="Cisco Meraki Dashboard API CLI",
    )
    parser.add_argument("--config", help="Path to meraki_config.json")
    parser.add_argument("--format", choices=["json", "compact", "count"], default="json",
                        help="Output format (default: json)")

    sub = parser.add_subparsers(dest="resource", required=True)

    # ── organizations ──
    p_orgs = sub.add_parser("organizations", aliases=["orgs"], help="Organization operations")
    p_orgs.add_argument("action", choices=["list", "get", "inventory", "uplinks", "license"])
    p_orgs.add_argument("--org-id", help="Organization ID")
    p_orgs.add_argument("--used-state", choices=["used", "unused"], help="Inventory filter")
    p_orgs.add_argument("--search", help="Search inventory by serial/MAC/model")

    # ── networks ──
    p_nets = sub.add_parser("networks", aliases=["nets"], help="Network operations")
    p_nets.add_argument("action", choices=["list", "get", "devices", "clients", "alerts", "events", "health", "traffic"])
    p_nets.add_argument("--org-id", help="Organization ID (required for list)")
    p_nets.add_argument("--network-id", help="Network ID")
    p_nets.add_argument("--tags", help="Comma-separated tags filter")
    p_nets.add_argument("--timespan", type=int, help="Timespan in seconds")
    p_nets.add_argument("--product-type", choices=["appliance", "switch", "wireless", "camera"],
                        help="Product type filter for events")
    p_nets.add_argument("--event-types", help="Comma-separated event types filter")

    # ── devices ──
    p_dev = sub.add_parser("devices", aliases=["dev"], help="Device operations")
    p_dev.add_argument("action", choices=["get", "uplink", "lldp-cdp", "clients", "reboot"])
    p_dev.add_argument("--serial", help="Device serial number")
    p_dev.add_argument("--timespan", type=int, help="Timespan in seconds")

    # ── switch ──
    p_sw = sub.add_parser("switch", aliases=["sw"], help="Switch operations")
    p_sw.add_argument("action", choices=["ports", "port-statuses", "routing", "dhcp", "vlans"])
    p_sw.add_argument("--serial", help="Switch serial number")
    p_sw.add_argument("--network-id", help="Network ID")

    # ── wireless ──
    p_wifi = sub.add_parser("wireless", aliases=["wifi"], help="Wireless operations")
    p_wifi.add_argument("action", choices=["ssids", "status", "clients", "channel-utilization", "health"])
    p_wifi.add_argument("--network-id", help="Network ID")
    p_wifi.add_argument("--timespan", type=int, help="Timespan in seconds")

    # ── appliance ──
    p_app = sub.add_parser("appliance", aliases=["mx"], help="MX appliance operations")
    p_app.add_argument("action", choices=["vlans", "firewall", "uplinks", "vpn", "dhcp"])
    p_app.add_argument("--network-id", help="Network ID")
    p_app.add_argument("--timespan", type=int, help="Timespan in seconds")

    # ── camera ──
    p_cam = sub.add_parser("camera", aliases=["mv"], help="Camera operations")
    p_cam.add_argument("action", choices=["snapshot", "video-link", "analytics"])
    p_cam.add_argument("--serial", help="Camera serial number")
    p_cam.add_argument("--timespan", type=int, help="Timespan in seconds")

    return parser


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = build_parser()
    args = parser.parse_args()

    api_key = get_api_key(args.config)
    base_url = get_api_url(args.config)

    resource = args.resource

    try:
        if resource in ("organizations", "orgs"):
            cmd_orgs(args, api_key, base_url)
        elif resource in ("networks", "nets"):
            cmd_networks(args, api_key, base_url)
        elif resource in ("devices", "dev"):
            cmd_devices(args, api_key, base_url)
        elif resource in ("switch", "sw"):
            cmd_switch(args, api_key, base_url)
        elif resource in ("wireless", "wifi"):
            cmd_wireless(args, api_key, base_url)
        elif resource in ("appliance", "mx"):
            cmd_appliance(args, api_key, base_url)
        elif resource in ("camera", "mv"):
            cmd_camera(args, api_key, base_url)
    except MerakiAPIError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
