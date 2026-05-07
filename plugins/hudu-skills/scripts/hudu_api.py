#!/usr/bin/env python3
"""
Hudu API CLI — manage Hudu documentation platform resources.

Usage:
    python3 hudu_api.py <resource> <action> [options]
    python3 hudu_api.py upsert <layout> [options]

Examples:
    python3 hudu_api.py companies list
    python3 hudu_api.py upsert "Software License" --company "Acme" --dry-run
    python3 hudu_api.py upsert "Software License" --describe
    python3 hudu_api.py asset-layouts show "Software License"
"""

import argparse
import json
import re
import sys
import time
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
# Upsert helpers
# ─────────────────────────────────────────────────────────────────────────────

def _slug_for_label(label: str) -> str:
    """Normalize a Hudu field label to a CLI flag slug (lowercase, non-alnum → hyphens)."""
    s = label.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


_SCHEMA_TTL_NORMAL = 24 * 3600   # 24 hours for normal operations
_SCHEMA_TTL_DESCRIBE = 3600      # 1 hour for --describe


def _schema_cache_path(layout_id) -> Path:
    cache_dir = Path.home() / ".cache" / "hudu-skills" / "layouts"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{layout_id}.json"


def _load_layout_schema(client, layout_name_or_id, refresh=False, ttl=None):
    """Fetch, cache, and return the asset layout dict (including fields array)."""
    if ttl is None:
        ttl = _SCHEMA_TTL_NORMAL

    # Resolve name → id
    try:
        layout_id = int(layout_name_or_id)
    except (ValueError, TypeError):
        layouts = client.list_asset_layouts(search=layout_name_or_id)
        matches = [l for l in layouts
                   if l.get("name", "").lower() == layout_name_or_id.lower()]
        if not matches:
            sys.exit(f"No asset layout found with name: {layout_name_or_id!r}\n"
                     f"Run: python3 scripts/hudu_api.py asset-layouts list")
        if len(matches) > 1:
            ids = [f"  ID={l['id']}: {l['name']}" for l in matches]
            sys.exit(f"Multiple layouts matched {layout_name_or_id!r}:\n" + "\n".join(ids))
        layout_id = matches[0]["id"]

    cache_path = _schema_cache_path(layout_id)

    if not refresh and cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < ttl:
            with open(cache_path) as f:
                return json.load(f)

    fresh = client.get_asset_layout(layout_id)
    with open(cache_path, "w") as f:
        json.dump(fresh, f)
    return fresh


def _label_for_slug(schema_fields, slug):
    """Return the Hudu field label matching a CLI slug, or None."""
    for field in schema_fields:
        if _slug_for_label(field.get("label", "")) == slug:
            return field["label"]
    return None


def _resolve_json_input(args) -> dict:
    """Merge JSON data from --file and --data flags. --file wins on key conflicts."""
    data = {}
    if getattr(args, "file", None):
        try:
            with open(args.file) as f:
                data = json.load(f)
        except FileNotFoundError:
            sys.exit(f"File not found: {args.file}")
        except json.JSONDecodeError as e:
            sys.exit(f"Invalid JSON in --file: {e}")
    if getattr(args, "data", None):
        try:
            data.update(json.loads(args.data))
        except json.JSONDecodeError as e:
            sys.exit(f"Invalid JSON in --data: {e}")
    return data


def _build_label_value_map(args1, args2, schema_fields):
    """
    Build a {label: value} map from all input sources.
    Priority (highest wins): dynamic --<slug> flags > --field SLUG=VALUE > --data/--file.
    """
    payload = _resolve_json_input(args1)
    lv_map = {}
    # Base: any fields/custom_fields from --file/--data
    for entry in payload.get("fields", []) + payload.get("custom_fields", []):
        if "label" in entry:
            lv_map[entry["label"]] = entry.get("value", "")

    # --field SLUG=VALUE overrides file/data
    for kv in (getattr(args1, "fields", None) or []):
        if "=" not in kv:
            sys.exit(f"--field must be SLUG=VALUE, got: {kv!r}")
        slug, _, value = kv.partition("=")
        label = _label_for_slug(schema_fields, slug.strip())
        if not label:
            sys.exit(f"Unknown field slug {slug!r}. Run with --describe to see available slugs.")
        lv_map[label] = value

    # Dynamic --<slug> flags (pass 2) override everything
    if args2:
        for field in schema_fields:
            slug = _slug_for_label(field["label"])
            attr = slug.replace("-", "_")
            val = getattr(args2, attr, None)
            if val is not None:
                lv_map[field["label"]] = val

    return lv_map


def _build_fields_payload(schema_fields, lv_map):
    """Convert {label: value} map → API format [{asset_layout_field_id, value}]."""
    field_id_map = {f["label"]: f["id"] for f in schema_fields}
    return [
        {"asset_layout_field_id": field_id_map[label],
         "value": str(value) if value is not None else ""}
        for label, value in lv_map.items()
        if label in field_id_map
    ]


def _merge_label_value_maps(existing_asset_fields, new_lv_map):
    """Merge new {label: value} into existing asset fields, preserving untouched fields."""
    merged = {}
    for f in (existing_asset_fields or []):
        label = f.get("label")
        val = f.get("value")
        if label and val is not None:
            merged[label] = val
    merged.update(new_lv_map)
    return merged


def _find_match_value(lv_map, schema_fields, slug):
    """Get the value for a given slug from a {label: value} dict."""
    label = _label_for_slug(schema_fields, slug)
    if not label:
        return None
    label_lower = label.lower()
    for k, v in lv_map.items():
        if k.lower() == label_lower:
            return v
    return None


def _resolve_company(client, args1):
    """Resolve company_id from --company name or --company-id. Returns (company_id, company_name)."""
    if getattr(args1, "company_id", None):
        return args1.company_id, None
    company_name = getattr(args1, "company", None)
    if not company_name:
        sys.exit("--company <name> or --company-id <id> is required for upsert")
    companies = client.list_companies(search=company_name)
    exact = [c for c in companies if c.get("name", "").lower() == company_name.lower()]
    if not exact:
        suggestions = [c["name"] for c in companies[:5]]
        sys.exit(f"No company found with name {company_name!r}.\n"
                 f"Did you mean: {suggestions}")
    if len(exact) > 1:
        ids = [f"  ID={c['id']}: {c['name']}" for c in exact]
        sys.exit(f"Multiple companies matched {company_name!r}:\n" + "\n".join(ids))
    return exact[0]["id"], exact[0]["name"]


def _default_match_slugs(layout_name):
    """Return default match-on slugs for a layout from layout-defaults.json or fall back to name."""
    defaults_path = Path(__file__).parent.parent / "config" / "layout-defaults.json"
    if defaults_path.exists():
        with open(defaults_path) as f:
            defaults = json.load(f)
        match = defaults.get(layout_name)
        if match:
            if isinstance(match, list):
                return [s.strip() for s in match]
            if isinstance(match, str):
                return [s.strip() for s in match.split(",")]
    return ["name"]


def _search_existing_assets(client, company_id, layout_id, asset_name,
                             lv_map, schema_fields, match_slugs):
    """Search for existing assets. Returns list of matching full asset records."""
    # Use first match slug's value as server-side search term for efficiency
    search_val = None
    for slug in match_slugs:
        if slug == "name":
            search_val = asset_name
            break
        val = _find_match_value(lv_map, schema_fields, slug)
        if val:
            search_val = str(val)
            break

    results = client.list_assets(
        company_id=company_id,
        asset_layout_id=layout_id,
        search=search_val,
    )

    # list_assets returns fields: null — fetch full records when matching on custom fields
    needs_fields = any(s != "name" for s in match_slugs)
    if needs_fields and results:
        detailed = []
        for a in results:
            full = client.get_asset(a["id"], company_id)
            if full:
                detailed.append(full)
        results = detailed

    def matches(asset):
        for slug in match_slugs:
            if slug == "name":
                if asset_name and asset.get("name", "").lower() != asset_name.lower():
                    return False
            else:
                label = _label_for_slug(schema_fields, slug)
                wanted = _find_match_value(lv_map, schema_fields, slug)
                if not wanted:
                    continue
                asset_field_val = next(
                    (str(f.get("value", "")) for f in asset.get("fields", [])
                     if label and f.get("label", "").lower() == label.lower()),
                    ""
                )
                if asset_field_val.lower() != str(wanted).lower():
                    return False
        return True

    return [a for a in results if matches(a)]


def _print_layout_describe(schema):
    name = schema.get("name", "?")
    layout_id = schema.get("id", "?")
    fields = schema.get("fields", [])
    print(f"Layout: {name} (ID: {layout_id})")
    print(f"Fields: {len(fields)}\n")
    print(f"  {'Slug':<32} {'Label':<32} {'Type':<16} Required")
    print(f"  {'-'*32} {'-'*32} {'-'*16} --------")
    for f in fields:
        slug = _slug_for_label(f.get("label", ""))
        label = f.get("label", "")
        ftype = f.get("field_type", f.get("fieldType", "text"))
        required = "yes" if f.get("required") else "no"
        print(f"  {slug:<32} {label:<32} {ftype:<16} {required}")
    print()
    if fields:
        example = " ".join(f"--{_slug_for_label(f['label'])} <value>" for f in fields[:3])
        print(f"Example:\n  python3 scripts/hudu_api.py upsert {name!r} "
              f"--company <name> {example}")


# ─────────────────────────────────────────────────────────────────────────────
# Upsert two-pass handler
# ─────────────────────────────────────────────────────────────────────────────

# Slugs reserved by global upsert flags — not injected as dynamic schema flags
_UPSERT_RESERVED_SLUGS = frozenset({
    "profile", "output", "name", "company", "company-id", "asset-id",
    "match-on", "field", "data", "file", "dry-run", "refresh-schema", "describe",
})


def handle_upsert_command(argv):
    """Two-pass argparse for 'upsert <layout>'. Called from main() before standard dispatch."""
    # Strip script name and the "upsert" token (remove first occurrence)
    raw = list(argv[1:])
    if "upsert" in raw:
        raw.remove("upsert")

    # Quick help when no layout given
    if not raw or raw == ["--help"] or raw == ["-h"]:
        print("usage: hudu_api.py upsert <layout> [options]\n")
        print("Upsert an asset of any layout type with search-before-create and dry-run.\n")
        print("Pass 1 flags (always available):")
        print("  layout              Asset layout name or numeric ID (required)")
        print("  --company NAME      Company name (required unless --company-id given)")
        print("  --company-id ID     Company ID override")
        print("  --name NAME         Asset name (derived from --vendor/--product if omitted)")
        print("  --asset-id ID       Force update to this specific asset ID")
        print("  --match-on SLUGS    Comma-separated field slugs for duplicate detection")
        print("  --field SLUG=VAL    Set a custom field by slug (repeatable escape hatch)")
        print("  --data JSON         Inline JSON payload override")
        print("  --file PATH         JSON file payload override")
        print("  --dry-run           Print resolved payload + match report, no API call")
        print("  --refresh-schema    Bust the cached layout schema")
        print("  --describe          Print the layout's field schema (slugs, types)")
        print("  --output table|json Output format")
        print("  --profile NAME      Config profile")
        print("\nTo see layout-specific field flags:")
        print('  python3 scripts/hudu_api.py upsert "Software License" --describe')
        return

    # ── Pass 1 ──────────────────────────────────────────────────────────────
    p1 = argparse.ArgumentParser(prog="hudu_api.py upsert", add_help=False)
    p1.add_argument("layout")
    p1.add_argument("--profile", "-p", default=None)
    p1.add_argument("--output", "-o", choices=["table", "json"], default="table")
    p1.add_argument("--name")
    p1.add_argument("--company")
    p1.add_argument("--company-id", type=int, dest="company_id")
    p1.add_argument("--asset-id", type=int, dest="asset_id")
    p1.add_argument("--match-on", dest="match_on")
    p1.add_argument("--field", action="append", dest="fields", metavar="SLUG=VALUE")
    p1.add_argument("--data")
    p1.add_argument("--file")
    p1.add_argument("--dry-run", action="store_true", dest="dry_run")
    p1.add_argument("--refresh-schema", action="store_true", dest="refresh_schema")
    p1.add_argument("--describe", action="store_true")

    args1, unknown = p1.parse_known_args(raw)

    # Set up client using pass-1 profile
    auth = HuduAuth(profile=args1.profile)
    client = HuduClient(auth)

    # Fetch schema (with optional cache bust; --describe uses 1h TTL)
    describe_ttl = _SCHEMA_TTL_DESCRIBE if args1.describe else _SCHEMA_TTL_NORMAL
    schema = _load_layout_schema(client, args1.layout,
                                  refresh=args1.refresh_schema, ttl=describe_ttl)
    schema_fields = schema.get("fields", [])

    # --describe: print schema and exit
    if args1.describe:
        _print_layout_describe(schema)
        return

    # ── Pass 2: register dynamic --<slug> flags from schema ─────────────────
    p2 = argparse.ArgumentParser(prog=f"hudu_api.py upsert {args1.layout!r}")
    slug_collision = set()
    for field in schema_fields:
        slug = _slug_for_label(field.get("label", ""))
        if not slug or slug in _UPSERT_RESERVED_SLUGS or slug in slug_collision:
            continue
        slug_collision.add(slug)
        dest = slug.replace("-", "_")
        ftype = field.get("field_type", field.get("fieldType", "text"))
        p2.add_argument(f"--{slug}", dest=dest,
                        help=f"{field['label']} ({ftype})")

    # Handle --help after schema is loaded so it shows real field flags
    if "--help" in unknown or "-h" in unknown:
        p2.print_help()
        return

    args2 = p2.parse_args(unknown)

    # ── Execute upsert ───────────────────────────────────────────────────────
    cmd_upsert_do(client, args1, args2, schema)


def cmd_upsert_do(client, args1, args2, schema):
    """Execute the upsert: resolve company, build payload, search, create or update."""
    schema_fields = schema.get("fields", [])
    layout_id = schema["id"]
    layout_name = schema.get("name", str(args1.layout))

    # Resolve company
    company_id, _ = _resolve_company(client, args1)

    # Build {label: value} map from all input sources
    lv_map = _build_label_value_map(args1, args2, schema_fields)

    # Determine asset name
    asset_name = args1.name
    if not asset_name:
        for candidate_slug in ("vendor", "product-name", "product", "application", "app-name"):
            val = _find_match_value(lv_map, schema_fields, candidate_slug)
            if val:
                asset_name = str(val)
                break
    if not asset_name:
        primary_slugs = [s for s in _default_match_slugs(layout_name) if s != "name"]
        if args1.match_on:
            primary_slugs = [s.strip() for s in args1.match_on.split(",")
                             if s.strip() not in ("company", "name")]
        for slug in primary_slugs:
            val = _find_match_value(lv_map, schema_fields, slug)
            if val:
                asset_name = str(val)
                break
    if not asset_name and lv_map:
        for v in lv_map.values():
            if v:
                asset_name = str(v)
                break
    if not asset_name:
        sys.exit("Cannot determine asset name. Provide --name <name>, --vendor <name>, "
                 "or another identifying field.")

    # Determine match-on slugs (strip implicit "company" — always filtered by company_id)
    if args1.match_on:
        match_slugs = [s.strip() for s in args1.match_on.split(",")
                       if s.strip() and s.strip() != "company"]
    else:
        match_slugs = [s for s in _default_match_slugs(layout_name) if s != "company"]

    # Search for duplicates
    candidates = _search_existing_assets(
        client, company_id, layout_id, asset_name,
        lv_map, schema_fields, match_slugs
    )

    # --asset-id override
    if args1.asset_id:
        forced = [a for a in candidates if a.get("id") == args1.asset_id]
        if not forced:
            forced_asset = client.get_asset(args1.asset_id, company_id)
            candidates = [forced_asset] if forced_asset else []
        else:
            candidates = forced

    if len(candidates) == 0:
        operation = "POST"
        target_id = None
        target_asset = None
    elif len(candidates) == 1:
        operation = "PUT"
        target_id = candidates[0]["id"]
        # Ensure we have the full record with fields for merge (list_assets returns fields: null)
        target_asset = candidates[0]
        if target_asset.get("fields") is None:
            target_asset = client.get_asset(target_id, company_id) or target_asset
    else:
        print(f"Ambiguous: {len(candidates)} matching assets found. "
              f"Use --asset-id to specify one:")
        for a in candidates[:8]:
            cf_preview = {_slug_for_label(f["label"]): f.get("value")
                          for f in a.get("fields", [])[:3]}
            print(f"  ID={a['id']} name={a.get('name')!r} fields={cf_preview}")
        sys.exit(1)

    # Merge fields (fetch-merge-PUT to avoid dropping existing fields)
    if operation == "PUT" and target_asset:
        merged_lv_map = _merge_label_value_maps(target_asset.get("fields", []), lv_map)
    else:
        merged_lv_map = lv_map

    # Convert to Hudu API format: [{asset_layout_field_id, value}]
    fields_payload = _build_fields_payload(schema_fields, merged_lv_map)

    # Dry-run gate: show human-readable labels, not field IDs
    if args1.dry_run:
        if operation == "POST":
            report = f"0 matches → would POST /companies/{company_id}/assets"
        else:
            report = (f"1 match (ID={target_id}, name={target_asset.get('name')!r}) "
                      f"→ would PUT /companies/{company_id}/assets/{target_id}")
        display_payload = {
            "asset": {
                "name": asset_name,
                "asset_layout_id": layout_id,
                "fields": merged_lv_map,
            }
        }
        print(f"[DRY RUN] {report}")
        print(f"[DRY RUN] Payload:")
        print(json.dumps(display_payload, indent=2))
        return

    if operation == "POST":
        result = client.create_asset(company_id, asset_name, layout_id, fields=fields_payload)
        new_id = result.get("id") if isinstance(result, dict) else "?"
        if args1.output != "json":
            print(f"Created {layout_name} asset ID={new_id}: {asset_name}")
        format_output(result, args1.output)
    else:
        result = client.update_asset(target_id, company_id=company_id,
                                      name=asset_name, fields=fields_payload)
        if args1.output != "json":
            print(f"Updated {layout_name} asset ID={target_id}: {asset_name}")
        format_output(result, args1.output)


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

def cmd_asset_layouts_create(client, args):
    data = _resolve_json_input(args)
    name = args.name or data.pop("name", None)
    if not name:
        sys.exit("--name is required for asset-layouts create")
    result = client.create_asset_layout(name, **data)
    format_output(result, args.output)
    if isinstance(result, dict) and args.output != "json":
        print(f"\nCreated asset layout ID: {result.get('id')}")

def cmd_asset_layouts_update(client, args):
    data = _resolve_json_input(args)
    result = client.update_asset_layout(args.id, **data)
    format_output(result, args.output)

def cmd_asset_layouts_show(client, args):
    """Show field schema for a layout by name or numeric ID."""
    try:
        layout_id = int(args.id_or_name)
        schema = client.get_asset_layout(layout_id)
    except (ValueError, TypeError):
        layouts = client.list_asset_layouts(search=args.id_or_name)
        matches = [l for l in layouts
                   if l.get("name", "").lower() == args.id_or_name.lower()]
        if not matches:
            sys.exit(f"No layout found with name: {args.id_or_name!r}")
        schema = matches[0]
    _print_layout_describe(schema)


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
# Expirations
# ─────────────────────────────────────────────────────────────────────────────

def cmd_expirations_list(client, args):
    result = client.list_expirations(
        company_id=getattr(args, "company_id", None),
        expiration_type=getattr(args, "type", None),
        search=getattr(args, "search", None),
    )
    format_output(result, args.output, "expirations")


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
    ("asset-layouts", "create"): cmd_asset_layouts_create,
    ("asset-layouts", "update"): cmd_asset_layouts_update,
    ("asset-layouts", "show"): cmd_asset_layouts_show,
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
    ("expirations", "list"): cmd_expirations_list,
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
  asset-layouts  list / get / create / update / show
  asset-passwords list / get / create / delete
  expirations    list
  procedures     list / get / delete
  websites       list / get / delete
  networks       list / get
  users          list / get
  folders        list / get
  activity-logs  list
  upsert <layout> ...   (see: hudu_api.py upsert --help)

Examples:
  python3 hudu_api.py companies list
  python3 hudu_api.py upsert "Software License" --company "Acme" --dry-run
  python3 hudu_api.py upsert "Software License" --describe
  python3 hudu_api.py asset-layouts show "Software License"
  python3 hudu_api.py expirations list --company-id 42
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
    p = als.add_parser("create"); p.add_argument("--name", required=True)
    p.add_argument("--data"); p.add_argument("--file")
    p = als.add_parser("update"); p.add_argument("--id", type=int, required=True)
    p.add_argument("--data"); p.add_argument("--file")
    p = als.add_parser("show"); p.add_argument("id_or_name", help="Layout name or numeric ID")

    # ── asset-passwords ──
    ap = sub.add_parser("asset-passwords")
    aps = ap.add_subparsers(dest="action")
    p = aps.add_parser("list"); p.add_argument("--company-id", type=int, dest="company_id"); p.add_argument("--search")
    p = aps.add_parser("get"); p.add_argument("--id", type=int, required=True)
    p = aps.add_parser("create"); p.add_argument("--name", required=True)
    p.add_argument("--company-id", type=int, dest="company_id", required=True)
    p.add_argument("--password"); p.add_argument("--username"); p.add_argument("--url")
    p = aps.add_parser("delete"); p.add_argument("--id", type=int, required=True)

    # ── expirations ──
    ex = sub.add_parser("expirations")
    exs = ex.add_subparsers(dest="action")
    p = exs.add_parser("list")
    p.add_argument("--company-id", type=int, dest="company_id")
    p.add_argument("--type", dest="type", help="Filter by expiration type")
    p.add_argument("--search")

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
    # Intercept 'upsert' before standard argparse (it uses two-pass schema-aware parsing)
    non_flags = [a for a in sys.argv[1:] if not a.startswith("-")]
    if non_flags and non_flags[0] == "upsert":
        handle_upsert_command(sys.argv)
        return

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
