#!/usr/bin/env python3
"""
Migrate Hudu asset-passwords → 1Password (Engineering - Twisted X vault).

Usage:
  python3 migrate_to_1password.py --dry-run     # preview only
  python3 migrate_to_1password.py --execute     # create items in 1Password
  python3 migrate_to_1password.py --execute --skip-existing  # skip duplicates silently
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

VAULT = "Engineering - Twisted X"
IMPORT_TAG = "hudu-import"

# Folder → 1Password tag mapping (Hudu folder names)
FOLDER_TAG_MAP = {
    "API Keys": "api-keys",
    "Cleo Gateway": "cleo-gateway",
    "EDI": "edi",
    "FTP": "ftp",
    "Locally": "local",
    "Microsoft 365": "microsoft-365",
    "NetSuite": "netsuite",
    "WiFi": "wifi",
}


def load_hudu_passwords():
    script_dir = Path(__file__).parent
    auth_mod = script_dir / "hudu_auth.py"
    # Use hudu_api.py to fetch all passwords
    result = subprocess.run(
        [sys.executable, str(script_dir / "hudu_api.py"), "--output", "json", "asset-passwords", "list"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Error fetching Hudu passwords: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def get_existing_op_titles():
    result = subprocess.run(
        ["op", "item", "list", "--vault", VAULT, "--format", "json"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Error listing 1Password items: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    items = json.loads(result.stdout)
    return {item["title"] for item in items}


def build_otp_uri(name: str, secret: str) -> str:
    label = urllib.parse.quote(name, safe="")
    return f"otpauth://totp/{label}?secret={secret}"


def build_op_create_cmd(pw: dict) -> list[str]:
    tags = [IMPORT_TAG]
    folder = pw.get("password_folder_name") or ""
    if folder and folder in FOLDER_TAG_MAP:
        tags.append(FOLDER_TAG_MAP[folder])
    elif folder:
        tags.append(folder.lower().replace(" ", "-"))

    cmd = [
        "op", "item", "create",
        "--category", "Login",
        "--title", pw["name"],
        "--vault", VAULT,
        "--tags", ",".join(tags),
    ]

    login_url = pw.get("login_url") or ""
    if login_url:
        cmd += ["--url", login_url]

    fields = []

    username = pw.get("username") or ""
    if username:
        fields.append(f"username[text]={username}")

    password = pw.get("password") or ""
    if password:
        fields.append(f"password[password]={password}")

    otp = pw.get("otp_secret") or ""
    if otp:
        fields.append(f"one-time password[otp]={build_otp_uri(pw['name'], otp)}")

    description = pw.get("description") or ""
    if description:
        fields.append(f"notesPlain={description}")

    cmd += fields
    return cmd


def run_migration(passwords: list, existing_titles: set, execute: bool, skip_existing: bool):
    created = 0
    skipped = 0
    errors = 0

    for pw in passwords:
        title = pw["name"]
        is_duplicate = title in existing_titles

        if is_duplicate:
            if skip_existing:
                print(f"  SKIP (exists)  {title}")
                skipped += 1
                continue
            else:
                # Append (Hudu) suffix to disambiguate
                title = f"{title} (Hudu)"
                pw = {**pw, "name": title}

        cmd = build_op_create_cmd(pw)

        folder = pw.get("password_folder_name") or "(no folder)"
        has_otp = "  +OTP" if pw.get("otp_secret") else ""
        has_url = f"  url={pw.get('login_url')}" if pw.get("login_url") else ""

        if not execute:
            print(f"  CREATE  [{folder}] {title}{has_otp}{has_url}")
            created += 1
            continue

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            item_id = ""
            try:
                out = json.loads(result.stdout)
                item_id = out.get("id", "")
            except Exception:
                pass
            print(f"  OK  [{folder}] {title}  {item_id}{has_otp}")
            created += 1
        else:
            print(f"  ERROR  {title}: {result.stderr.strip()}", file=sys.stderr)
            errors += 1

    return created, skipped, errors


def main():
    parser = argparse.ArgumentParser(description="Migrate Hudu passwords to 1Password")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Preview without creating items")
    mode.add_argument("--execute", action="store_true", help="Create items in 1Password")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip items whose title already exists in 1Password (default: append ' (Hudu)' suffix)")
    args = parser.parse_args()

    print("Fetching Hudu passwords...")
    passwords = load_hudu_passwords()
    print(f"  Found {len(passwords)} passwords in Hudu\n")

    print("Fetching existing 1Password items...")
    existing_titles = get_existing_op_titles()
    print(f"  Found {len(existing_titles)} existing items in '{VAULT}'\n")

    duplicates = [p for p in passwords if p["name"] in existing_titles]
    if duplicates:
        print(f"Note: {len(duplicates)} Hudu password(s) share a title with existing 1Password items:")
        for p in duplicates:
            print(f"  - {p['name']}")
        if not args.skip_existing:
            print("  → Will import with ' (Hudu)' suffix\n")
        else:
            print("  → Will skip these (--skip-existing)\n")

    action = "DRY RUN" if args.dry_run else "CREATING"
    print(f"--- {action} {len(passwords)} items ---")
    created, skipped, errors = run_migration(passwords, existing_titles, args.execute, args.skip_existing)

    print(f"\n{'--- Summary ---'}")
    if args.dry_run:
        print(f"  Would create: {created}")
        print(f"  Would skip:   {skipped}")
    else:
        print(f"  Created:  {created}")
        print(f"  Skipped:  {skipped}")
        print(f"  Errors:   {errors}")


if __name__ == "__main__":
    main()
