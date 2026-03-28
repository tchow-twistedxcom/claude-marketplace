#!/usr/bin/env python3
"""
Disk usage report across all NinjaOne-monitored servers.

Usage:
  python3 disk_report.py              # All drives, warn at 80%
  python3 disk_report.py --threshold 90  # Custom warning threshold
  python3 disk_report.py --critical      # Only show critical (>=90%)
"""

import argparse
import json
from urllib.request import urlopen
from urllib.error import URLError

NINJAONE_API = "http://localhost:3050"


def get(url, timeout=15):
    try:
        with urlopen(url, timeout=timeout) as r:
            return json.loads(r.read())
    except URLError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def fmt_gb(mb):
    if mb is None:
        return "N/A"
    gb = mb / 1024
    return f"{gb:.1f} GB"


def pct_bar(used_pct, width=20):
    filled = int(used_pct / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    if used_pct >= 90:
        color = "\033[91m"
    elif used_pct >= 75:
        color = "\033[93m"
    else:
        color = "\033[92m"
    return f"{color}{bar}\033[0m {used_pct:.1f}%"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=80.0)
    parser.add_argument("--critical", action="store_true", help="Only show >=90% full")
    args = parser.parse_args()

    warn_at = 90.0 if args.critical else args.threshold

    print("\n\033[1m=== Disk Usage Report ===\033[0m\n")

    data = get(f"{NINJAONE_API}/api/queries/disk-drives")
    if isinstance(data, dict) and data.get("error"):
        print(f"\033[91mError: {data['error']}\033[0m")
        return

    # data is list of drive objects: {deviceName, driveName, capacity, freeSpace, ...}
    drives = data if isinstance(data, list) else data.get("results", [])

    warnings = []
    for d in drives:
        cap = d.get("capacity") or d.get("size")
        free = d.get("freeSpace") or d.get("free")
        if not cap or cap == 0:
            continue
        used_pct = (1 - free / cap) * 100
        device = d.get("deviceName", d.get("hostname", "unknown"))
        drive = d.get("driveName", d.get("name", "?"))
        if used_pct >= warn_at:
            warnings.append((used_pct, device, drive, cap, free))

    if not warnings:
        print(f"  \033[92m✓ No drives above {warn_at:.0f}% threshold\033[0m")
    else:
        warnings.sort(reverse=True)
        print(f"  {'Device':<25} {'Drive':<8} {'Used':<26} {'Free':>10} {'Cap':>10}")
        print(f"  {'-'*25} {'-'*8} {'-'*26} {'-'*10} {'-'*10}")
        for used_pct, device, drive, cap, free in warnings:
            used_mb = cap - free
            print(f"  {device:<25} {drive:<8} {pct_bar(used_pct):<35} {fmt_gb(free):>10} {fmt_gb(cap):>10}")

    print(f"\n  Checked {len(drives)} drives across all devices\n")


if __name__ == "__main__":
    main()
