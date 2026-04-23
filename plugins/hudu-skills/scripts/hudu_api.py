#!/usr/bin/env python3
"""
Hudu API CLI — manage Hudu documentation platform resources.

Usage:
    python3 hudu_api.py <resource> <action> [options]

Examples:
    python3 hudu_api.py companies list
    python3 hudu_api.py companies get --id 42
    python3 hudu_api.py articles search --query "firewall"
    python3 hudu_api.py assets list --company-id 42
    python3 hudu_api.py asset-passwords list --company-id 42 --output json
"""

import argparse
import sys
from pathlib import Path

# Allow running from any directory
sys.path.insert(0, str(Path(__file__).parent))

from hudu_auth import HuduAuth
from hudu_client import HuduClient
from hudu_formatter import format_output


def make_client(args):
    auth = HuduAuth(profile=getattr(args, "profile", None))
    return HuduClient(auth)


# ─────────────────────────────────────────────────────────────────────────────
# Companies
# ─────────────────────────────────────────────────────────────────────────────

def cmd_companies_list(client, args):
    result = client.list_companies(name=args.name, search=args.search)
    format_output(result, args.output, "companies")

def cmd_companies_get(client, args):
    result = client.get_company(args.id)
    format_output(result, args.output)

def cmd_companies_create(client, args):
    result = client.create_company(args.name, phone_number=args.phone, website=args.website,
                                    city=args.city, state=args.state)
    format_output(result, args.output)

def cmd_companies_update(client, args):
    kwargs = {k: v for k, v in vars(args).items()
              if k not in ("id", "profile", "output", "resource", "action") and v is not None}
    result = client.update_company(args.id, **kwargs)
    format_output(result, args.output)

def cmd_companies_delete(client, args):
    client.delete_company(args.id)
    print(f"Company {args.id} deleted.")

def cmd_companies_archive(client, args):
    client.archive_company(args.id)
    print(f"Company {args.id} archived.")

def cmd_companies_unarchive(client, args):
    client.unarchive_company(args.id)
    print(f"Company {args.id} unarchived.")


# ─────────────────────────────────────────────────────────────────────────────
# Articles
# ─────────────────────────────────────────────────────────────────────────────

def cmd_articles_list(client, args):
    result = client.list_articles(company_id=args.company_id, name=args.name, search=args.search)
    format_output(result, args.output, "articles")

def cmd_articles_get(client, args):
    result = client.get_article(args.id)
    format_output(result, args.output)

def cmd_articles_search(client, args):
    result = client.list_articles(search=args.query, company_id=args.company_id)
    format_output(result, args.output, "articles")

def cmd_articles_create(client, args):
    result = client.create_article(args.name, args.content, company_id=args.company_id)
    format_output(result, args.output)
    if isinstance(result, dict) and args.output != "json":
        print(f"\nCreated article ID: {result.get('id')}")

def cmd_articles_update(client, args):
    kwargs = {k: v for k, v in vars(args).items()
              if k not in ("id", "profile", "output", "resource", "action") and v is not None}
    result = client.update_article(args.id, **kwargs)
    format_output(result, args.output)

def cmd_articles_delete(client, args):
    client.delete_article(args.id)
    print(f"Article {args.id} deleted.")

def cmd_articles_archive(client, args):
    client.archive_article(args.id)
    print(f"Article {args.id} archived.")


# ─────────────────────────────────────────────────────────────────────────────
# Assets
# ─────────────────────────────────────────────────────────────────────────────

def cmd_assets_list(client, args):
    result = client.list_assets(company_id=args.company_id, asset_layout_id=args.layout_id,
                                 name=args.name, search=args.search, archived=args.archived)
    format_output(result, args.output, "assets")

def cmd_assets_get(client, args):
    result = client.get_asset(args.id)
    format_output(result, args.output)

def cmd_assets_create(client, args):
    result = client.create_asset(args.company_id, args.name, args.layout_id)
    format_output(result, args.output)
    if isinstance(result, dict) and args.output != "json":
        print(f"\nCreated asset ID: {result.get('id')}")

def cmd_assets_update(client, args):
    kwargs = {k: v for k, v in vars(args).items()
              if k not in ("id", "profile", "output", "resource", "action") and v is not None}
    result = client.update_asset(args.id, **kwargs)
    format_output(result, args.output)

def cmd_assets_delete(client, args):
    client.delete_asset(args.id)
    print(f"Asset {args.id} deleted.")

def cmd_assets_archive(client, args):
    client.archive_asset(args.id)
    print(f"Asset {args.id} archived.")


# ─────────────────────────────────────────────────────────────────────────────
# Asset Layouts
# ─────────────────────────────────────────────────────────────────────────────

def cmd_asset_layouts_list(client, args):
    result = client.list_asset_layouts(search=args.search)
    format_output(result, args.output, "asset_layouts")

def cmd_asset_layouts_get(client, args):
    result = client.get_asset_layout(args.id)
    format_output(result, args.output)


# ─────────────────────────────────────────────────────────────────────────────
# Asset Passwords
# ─────────────────────────────────────────────────────────────────────────────

def cmd_asset_passwords_list(client, args):
    result = client.list_asset_passwords(company_id=args.company_id, search=args.search)
    format_output(result, args.output, "asset_passwords")

def cmd_asset_passwords_get(client, args):
    result = client.get_asset_password(args.id)
    format_output(result, args.output)

def cmd_asset_passwords_create(client, args):
    result = client.create_asset_password(args.name, args.company_id, password=args.password,
                                           username=args.username, url=args.url)
    format_output(result, args.output)
    if isinstance(result, dict) and args.output != "json":
        print(f"\nCreated password ID: {result.get('id')}")

def cmd_asset_passwords_delete(client, args):
    client.delete_asset_password(args.id)
    print(f"Password {args.id} deleted.")


# ─────────────────────────────────────────────────────────────────────────────
# Procedures
# ─────────────────────────────────────────────────────────────────────────────

def cmd_procedures_list(client, args):
    result = client.list_procedures(company_id=args.company_id, search=args.search)
    format_output(result, args.output, "procedures")

def cmd_procedures_get(client, args):
    result = client.get_procedure(args.id)
    format_output(result, args.output)

def cmd_procedures_delete(client, args):
    client.delete_procedure(args.id)
    print(f"Procedure {args.id} deleted.")


# ─────────────────────────────────────────────────────────────────────────────
# Websites
# ─────────────────────────────────────────────────────────────────────────────

def cmd_websites_list(client, args):
    result = client.list_websites(company_id=args.company_id, search=args.search)
    format_output(result, args.output, "websites")

def cmd_websites_get(client, args):
    result = client.get_website(args.id)
    format_output(result, args.output)

def cmd_websites_delete(client, args):
    client.delete_website(args.id)
    print(f"Website {args.id} deleted.")


# ─────────────────────────────────────────────────────────────────────────────
# Networks, Users, Folders (read-only)
# ─────────────────────────────────────────────────────────────────────────────

def cmd_networks_list(client, args):
    result = client.list_networks(company_id=args.company_id, search=args.search)
    format_output(result, args.output, "networks")

def cmd_networks_get(client, args):
    result = client.get_network(args.id)
    format_output(result, args.output)

def cmd_users_list(client, args):
    result = client.list_users(search=args.search)
    format_output(result, args.output, "users")

def cmd_users_get(client, args):
    result = client.get_user(args.id)
    format_output(result, args.output)

def cmd_folders_list(client, args):
    result = client.list_folders(company_id=args.company_id, search=args.search)
    format_output(result, args.output, "folders")

def cmd_folders_get(client, args):
    result = client.get_folder(args.id)
    format_output(result, args.output)


# ─────────────────────────────────────────────────────────────────────────────
# Activity Logs
# ─────────────────────────────────────────────────────────────────────────────

def cmd_activity_logs_list(client, args):
    result = client.list_activity_logs(user_id=args.user_id, resource_type=args.resource_type,
                                        start_date=args.start_date, end_date=args.end_date)
    format_output(result, args.output, "activity_logs")


# ─────────────────────────────────────────────────────────────────────────────
# Dispatch table
# ─────────────────────────────────────────────────────────────────────────────

DISPATCH = {
    ("companies", "list"): cmd_companies_list,
    ("companies", "get"): cmd_companies_get,
    ("companies", "create"): cmd_companies_create,
    ("companies", "update"): cmd_companies_update,
    ("companies", "delete"): cmd_companies_delete,
    ("companies", "archive"): cmd_companies_archive,
    ("companies", "unarchive"): cmd_companies_unarchive,
    ("articles", "list"): cmd_articles_list,
    ("articles", "get"): cmd_articles_get,
    ("articles", "search"): cmd_articles_search,
    ("articles", "create"): cmd_articles_create,
    ("articles", "update"): cmd_articles_update,
    ("articles", "delete"): cmd_articles_delete,
    ("articles", "archive"): cmd_articles_archive,
    ("assets", "list"): cmd_assets_list,
    ("assets", "get"): cmd_assets_get,
    ("assets", "create"): cmd_assets_create,
    ("assets", "update"): cmd_assets_update,
    ("assets", "delete"): cmd_assets_delete,
    ("assets", "archive"): cmd_assets_archive,
    ("asset-layouts", "list"): cmd_asset_layouts_list,
    ("asset-layouts", "get"): cmd_asset_layouts_get,
    ("asset-passwords", "list"): cmd_asset_passwords_list,
    ("asset-passwords", "get"): cmd_asset_passwords_get,
    ("asset-passwords", "create"): cmd_asset_passwords_create,
    ("asset-passwords", "delete"): cmd_asset_passwords_delete,
    ("procedures", "list"): cmd_procedures_list,
    ("procedures", "get"): cmd_procedures_get,
    ("procedures", "delete"): cmd_procedures_delete,
    ("websites", "list"): cmd_websites_list,
    ("websites", "get"): cmd_websites_get,
    ("websites", "delete"): cmd_websites_delete,
    ("networks", "list"): cmd_networks_list,
    ("networks", "get"): cmd_networks_get,
    ("users", "list"): cmd_users_list,
    ("users", "get"): cmd_users_get,
    ("folders", "list"): cmd_folders_list,
    ("folders", "get"): cmd_folders_get,
    ("activity-logs", "list"): cmd_activity_logs_list,
}


# ─────────────────────────────────────────────────────────────────────────────
# Argparse
# ─────────────────────────────────────────────────────────────────────────────

def build_parser():
    root = argparse.ArgumentParser(
        prog="hudu_api.py",
        description="Hudu REST API CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Resources and actions:
  companies      list / get / create / update / delete / archive / unarchive
  articles       list / get / search / create / update / delete / archive
  assets         list / get / create / update / delete / archive
  asset-layouts  list / get
  asset-passwords list / get / create / delete
  procedures     list / get / delete
  websites       list / get / delete
  networks       list / get
  users          list / get
  folders        list / get
  activity-logs  list

Examples:
  python3 hudu_api.py companies list
  python3 hudu_api.py companies list --search "Acme"
  python3 hudu_api.py articles search --query "firewall" --output json
  python3 hudu_api.py assets list --company-id 42 --layout-id 7
  python3 hudu_api.py asset-passwords list --company-id 42
  python3 hudu_api.py articles create --name "VPN Setup" --content "<p>...</p>" --company-id 42
"""
    )
    root.add_argument("--profile", "-p", default=None, help="Config profile name")
    root.add_argument("--output", "-o", choices=["table", "json"], default="table")

    sub = root.add_subparsers(dest="resource")

    # ── companies ──
    c = sub.add_parser("companies")
    cs = c.add_subparsers(dest="action")
    p = cs.add_parser("list"); p.add_argument("--name"); p.add_argument("--search")
    p = cs.add_parser("get"); p.add_argument("--id", type=int, required=True)
    p = cs.add_parser("create"); p.add_argument("--name", required=True)
    p.add_argument("--phone"); p.add_argument("--website"); p.add_argument("--city"); p.add_argument("--state")
    p = cs.add_parser("update"); p.add_argument("--id", type=int, required=True)
    p.add_argument("--name"); p.add_argument("--phone"); p.add_argument("--website")
    p = cs.add_parser("delete"); p.add_argument("--id", type=int, required=True)
    p = cs.add_parser("archive"); p.add_argument("--id", type=int, required=True)
    p = cs.add_parser("unarchive"); p.add_argument("--id", type=int, required=True)

    # ── articles ──
    a = sub.add_parser("articles")
    as_ = a.add_subparsers(dest="action")
    p = as_.add_parser("list"); p.add_argument("--company-id", type=int, dest="company_id")
    p.add_argument("--name"); p.add_argument("--search")
    p = as_.add_parser("get"); p.add_argument("--id", type=int, required=True)
    p = as_.add_parser("search"); p.add_argument("--query", required=True)
    p.add_argument("--company-id", type=int, dest="company_id")
    p = as_.add_parser("create"); p.add_argument("--name", required=True)
    p.add_argument("--content", required=True); p.add_argument("--company-id", type=int, dest="company_id")
    p = as_.add_parser("update"); p.add_argument("--id", type=int, required=True)
    p.add_argument("--name"); p.add_argument("--content")
    p = as_.add_parser("delete"); p.add_argument("--id", type=int, required=True)
    p = as_.add_parser("archive"); p.add_argument("--id", type=int, required=True)

    # ── assets ──
    a = sub.add_parser("assets")
    as_ = a.add_subparsers(dest="action")
    p = as_.add_parser("list"); p.add_argument("--company-id", type=int, dest="company_id")
    p.add_argument("--layout-id", type=int, dest="layout_id")
    p.add_argument("--name"); p.add_argument("--search"); p.add_argument("--archived", action="store_true")
    p = as_.add_parser("get"); p.add_argument("--id", type=int, required=True)
    p = as_.add_parser("create"); p.add_argument("--company-id", type=int, dest="company_id", required=True)
    p.add_argument("--name", required=True); p.add_argument("--layout-id", type=int, dest="layout_id", required=True)
    p = as_.add_parser("update"); p.add_argument("--id", type=int, required=True); p.add_argument("--name")
    p = as_.add_parser("delete"); p.add_argument("--id", type=int, required=True)
    p = as_.add_parser("archive"); p.add_argument("--id", type=int, required=True)

    # ── asset-layouts ──
    al = sub.add_parser("asset-layouts")
    als = al.add_subparsers(dest="action")
    p = als.add_parser("list"); p.add_argument("--search")
    p = als.add_parser("get"); p.add_argument("--id", type=int, required=True)

    # ── asset-passwords ──
    ap = sub.add_parser("asset-passwords")
    aps = ap.add_subparsers(dest="action")
    p = aps.add_parser("list"); p.add_argument("--company-id", type=int, dest="company_id"); p.add_argument("--search")
    p = aps.add_parser("get"); p.add_argument("--id", type=int, required=True)
    p = aps.add_parser("create"); p.add_argument("--name", required=True)
    p.add_argument("--company-id", type=int, dest="company_id", required=True)
    p.add_argument("--password"); p.add_argument("--username"); p.add_argument("--url")
    p = aps.add_parser("delete"); p.add_argument("--id", type=int, required=True)

    # ── procedures ──
    pr = sub.add_parser("procedures")
    prs = pr.add_subparsers(dest="action")
    p = prs.add_parser("list"); p.add_argument("--company-id", type=int, dest="company_id"); p.add_argument("--search")
    p = prs.add_parser("get"); p.add_argument("--id", type=int, required=True)
    p = prs.add_parser("delete"); p.add_argument("--id", type=int, required=True)

    # ── websites ──
    w = sub.add_parser("websites")
    ws = w.add_subparsers(dest="action")
    p = ws.add_parser("list"); p.add_argument("--company-id", type=int, dest="company_id"); p.add_argument("--search")
    p = ws.add_parser("get"); p.add_argument("--id", type=int, required=True)
    p = ws.add_parser("delete"); p.add_argument("--id", type=int, required=True)

    # ── networks ──
    n = sub.add_parser("networks")
    ns = n.add_subparsers(dest="action")
    p = ns.add_parser("list"); p.add_argument("--company-id", type=int, dest="company_id"); p.add_argument("--search")
    p = ns.add_parser("get"); p.add_argument("--id", type=int, required=True)

    # ── users ──
    u = sub.add_parser("users")
    us = u.add_subparsers(dest="action")
    p = us.add_parser("list"); p.add_argument("--search")
    p = us.add_parser("get"); p.add_argument("--id", type=int, required=True)

    # ── folders ──
    fo = sub.add_parser("folders")
    fos = fo.add_subparsers(dest="action")
    p = fos.add_parser("list"); p.add_argument("--company-id", type=int, dest="company_id"); p.add_argument("--search")
    p = fos.add_parser("get"); p.add_argument("--id", type=int, required=True)

    # ── activity-logs ──
    al2 = sub.add_parser("activity-logs")
    al2s = al2.add_subparsers(dest="action")
    p = al2s.add_parser("list")
    p.add_argument("--user-id", type=int, dest="user_id")
    p.add_argument("--resource-type", dest="resource_type")
    p.add_argument("--start-date", dest="start_date")
    p.add_argument("--end-date", dest="end_date")

    return root


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.resource:
        parser.print_help()
        sys.exit(0)

    # Propagate profile/output down to subparsers that don't inherit them
    for attr in ("profile", "output"):
        if not hasattr(args, attr):
            setattr(args, attr, getattr(args, attr, "table" if attr == "output" else None))

    action = getattr(args, "action", None)
    if not action:
        parser.parse_args([args.resource, "--help"])
        sys.exit(0)

    key = (args.resource, args.action)
    handler = DISPATCH.get(key)
    if not handler:
        sys.exit(f"Unknown: {args.resource} {args.action}")

    client = make_client(args)
    handler(client, args)


if __name__ == "__main__":
    main()
