#!/usr/bin/env python3
"""
OS patch compliance report across all NinjaOne-monitored servers.

Usage:
  python3 patch_report.py              # Full patch compliance report
  python3 patch_report.py --critical   # Critical patches only
"""

import argparse
import json
from urllib.request import urlopen
from urllib.error import URLError

NINJAONE_API = "http://localhost:3050"


def get(url, timeout=20):
    try:
        with urlopen(url, timeout=timeout) as r:
            return json.loads(r.read())
    except URLError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--critical", action="store_true")
    args = parser.parse_args()

    print("\n\033[1m=== OS Patch Compliance Report ===\033[0m\n")

    data = get(f"{NINJAONE_API}/api/queries/os-patches")
    if isinstance(data, dict) and data.get("error"):
        print(f"\033[91mError: {data['error']}\033[0m")
        return

    patches = data if isinstance(data, list) else data.get("results", [])

    if args.critical:
        patches = [p for p in patches if (p.get("severity") or "").upper() in ("CRITICAL", "IMPORTANT")]

    by_device = {}
    for p in patches:
        dev = p.get("deviceName", p.get("hostname", "unknown"))
        by_device.setdefault(dev, []).append(p)

    if not by_device:
        print("  \033[92m✓ No pending patches found\033[0m\n")
        return

    total = sum(len(v) for v in by_device.values())
    print(f"  Pending patches: \033[93m{total}\033[0m across {len(by_device)} devices\n")

    sev_color = {"CRITICAL": "\033[91m", "IMPORTANT": "\033[91m", "MODERATE": "\033[93m", "LOW": "\033[94m"}
    reset = "\033[0m"

    for device, device_patches in sorted(by_device.items(), key=lambda x: -len(x[1])):
        print(f"  \033[1m{device}\033[0m — {len(device_patches)} pending")
        for p in sorted(device_patches, key=lambda x: x.get("severity", ""))[: 5]:
            sev = (p.get("severity") or "N/A").upper()
            name = (p.get("title") or p.get("name") or "")[:70]
            col = sev_color.get(sev, "")
            print(f"    {col}[{sev}]{reset} {name}")
        if len(device_patches) > 5:
            print(f"    ... and {len(device_patches) - 5} more")
        print()


if __name__ == "__main__":
    main()
