#!/usr/bin/env python3
"""
Validate NetSuite API Gateway configuration files.

Validates:
- oauth.json - OAuth 1.0a credentials for all environments
- oauth2.json - OAuth 2.0 credentials and certificate paths
- apps.json - Application configurations and restletId overrides

Usage:
    python3 validate_config.py
    python3 validate_config.py --config oauth2.json
    python3 validate_config.py --gateway-path ~/NetSuiteApiGateway
"""

import argparse
import json
import os
import sys
from pathlib import Path

DEFAULT_GATEWAY_PATH = os.path.expanduser("~/NetSuiteApiGateway")
REQUIRED_ENVIRONMENTS = ["production", "sandbox", "sandbox2"]


def load_json_file(filepath: str) -> dict | None:
    """Load and parse a JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"\u274C JSON parse error in {filepath}: {e}")
        return None


def validate_oauth_json(gateway_path: str) -> dict:
    """Validate OAuth 1.0a configuration."""
    filepath = os.path.join(gateway_path, "config", "oauth.json")
    result = {
        "file": "oauth.json",
        "exists": False,
        "valid": False,
        "errors": [],
        "warnings": [],
        "environments": {}
    }

    data = load_json_file(filepath)
    if data is None:
        result["errors"].append(f"File not found: {filepath}")
        return result

    result["exists"] = True

    # Check for environments section
    if "environments" not in data:
        result["errors"].append("Missing 'environments' section")
        return result

    envs = data["environments"]

    # Required fields for each environment
    required_fields = ["realm", "accountId", "tokenEndpoint", "baseUrl", "credentials"]
    credential_fields = ["consumerKey", "consumerSecret", "tokenId", "tokenSecret"]

    for env in REQUIRED_ENVIRONMENTS:
        env_result = {"present": False, "fields_valid": False, "credentials_valid": False}

        if env not in envs:
            result["warnings"].append(f"Environment '{env}' not configured")
            result["environments"][env] = env_result
            continue

        env_result["present"] = True
        env_config = envs[env]

        # Check required fields
        missing_fields = [f for f in required_fields if f not in env_config]
        if missing_fields:
            result["errors"].append(f"[{env}] Missing fields: {', '.join(missing_fields)}")
        else:
            env_result["fields_valid"] = True

        # Check credentials
        if "credentials" in env_config:
            creds = env_config["credentials"]
            missing_creds = [f for f in credential_fields if f not in creds]
            if missing_creds:
                result["errors"].append(f"[{env}] Missing credentials: {', '.join(missing_creds)}")
            else:
                # Check if credentials use env vars
                for field in credential_fields:
                    value = creds.get(field, "")
                    if "${" in value:
                        env_result["credentials_valid"] = True  # Uses env vars
                    elif value and len(value) > 10:
                        env_result["credentials_valid"] = True  # Has actual value

        result["environments"][env] = env_result

    # Determine overall validity
    result["valid"] = len(result["errors"]) == 0

    return result


def validate_oauth2_json(gateway_path: str) -> dict:
    """Validate OAuth 2.0 configuration."""
    filepath = os.path.join(gateway_path, "config", "oauth2.json")
    result = {
        "file": "oauth2.json",
        "exists": False,
        "valid": False,
        "errors": [],
        "warnings": [],
        "environments": {}
    }

    data = load_json_file(filepath)
    if data is None:
        result["errors"].append(f"File not found: {filepath}")
        return result

    result["exists"] = True

    # Check for environments section
    if "environments" not in data:
        result["errors"].append("Missing 'environments' section")
        return result

    envs = data["environments"]

    # Required fields for OAuth 2.0
    required_fields = ["realm", "accountId", "tokenEndpoint", "baseUrl", "credentials"]
    credential_fields = ["clientId", "certificatePath"]

    for env in REQUIRED_ENVIRONMENTS:
        env_result = {"present": False, "fields_valid": False, "certificate_exists": False}

        if env not in envs:
            result["warnings"].append(f"Environment '{env}' not configured for OAuth 2.0")
            result["environments"][env] = env_result
            continue

        env_result["present"] = True
        env_config = envs[env]

        # Check required fields
        missing_fields = [f for f in required_fields if f not in env_config]
        if missing_fields:
            result["errors"].append(f"[{env}] Missing fields: {', '.join(missing_fields)}")
        else:
            env_result["fields_valid"] = True

        # Check credentials
        if "credentials" in env_config:
            creds = env_config["credentials"]
            missing_creds = [f for f in credential_fields if f not in creds]
            if missing_creds:
                result["errors"].append(f"[{env}] Missing credentials: {', '.join(missing_creds)}")

            # Verify certificate path exists
            if "certificatePath" in creds:
                cert_path = creds["certificatePath"]
                # Handle relative paths
                if cert_path.startswith("./"):
                    cert_path = os.path.join(gateway_path, cert_path[2:])
                elif not cert_path.startswith("/"):
                    cert_path = os.path.join(gateway_path, cert_path)

                if os.path.exists(cert_path):
                    env_result["certificate_exists"] = True
                else:
                    result["errors"].append(f"[{env}] Certificate not found: {creds['certificatePath']}")

        result["environments"][env] = env_result

    # Determine overall validity
    result["valid"] = len(result["errors"]) == 0

    return result


def validate_apps_json(gateway_path: str) -> dict:
    """Validate apps configuration."""
    filepath = os.path.join(gateway_path, "config", "apps.json")
    result = {
        "file": "apps.json",
        "exists": False,
        "valid": False,
        "errors": [],
        "warnings": [],
        "apps": {}
    }

    data = load_json_file(filepath)
    if data is None:
        result["errors"].append(f"File not found: {filepath}")
        return result

    result["exists"] = True

    # Check for apps section
    if "apps" not in data:
        result["errors"].append("Missing 'apps' section")
        return result

    apps = data["apps"]
    required_fields = ["name", "restletId", "deployId", "enabled"]

    for app_id, app_config in apps.items():
        app_result = {"fields_valid": False, "has_overrides": False, "override_envs": []}

        # Check required fields
        missing_fields = [f for f in required_fields if f not in app_config]
        if missing_fields:
            result["errors"].append(f"[{app_id}] Missing fields: {', '.join(missing_fields)}")
        else:
            app_result["fields_valid"] = True

        # Check for restletId overrides
        if "restletIdOverrides" in app_config:
            app_result["has_overrides"] = True
            overrides = app_config["restletIdOverrides"]

            for env, override_id in overrides.items():
                app_result["override_envs"].append(env)

                # Validate override format
                if not isinstance(override_id, (str, int)):
                    result["errors"].append(f"[{app_id}] Invalid restletId override for {env}")

        result["apps"][app_id] = app_result

    # Determine overall validity
    result["valid"] = len(result["errors"]) == 0

    return result


def print_result(result: dict, verbose: bool = False):
    """Print validation result for a config file."""
    file_name = result["file"]
    status = "\u2705 VALID" if result["valid"] else "\u274C INVALID"

    print(f"\n{file_name}: {status}")

    if not result["exists"]:
        print("   File not found")
        return

    # Print errors
    for error in result["errors"]:
        print(f"   \u274C {error}")

    # Print warnings
    for warning in result["warnings"]:
        print(f"   \u26A0\uFE0F  {warning}")

    # Print environment details
    if "environments" in result and verbose:
        print("   Environments:")
        for env, env_result in result["environments"].items():
            if env_result["present"]:
                status = "\u2705" if env_result.get("fields_valid") else "\u274C"
                print(f"      {status} {env}")
            else:
                print(f"      \u26A0\uFE0F  {env} (not configured)")

    # Print app details
    if "apps" in result and verbose:
        print("   Apps:")
        for app_id, app_result in result["apps"].items():
            status = "\u2705" if app_result["fields_valid"] else "\u274C"
            overrides = f" (overrides: {', '.join(app_result['override_envs'])})" if app_result["has_overrides"] else ""
            print(f"      {status} {app_id}{overrides}")


def main():
    parser = argparse.ArgumentParser(
        description="Validate NetSuite API Gateway configuration files"
    )
    parser.add_argument(
        "--gateway-path",
        default=DEFAULT_GATEWAY_PATH,
        help=f"Path to gateway directory (default: {DEFAULT_GATEWAY_PATH})"
    )
    parser.add_argument(
        "--config",
        choices=["oauth.json", "oauth2.json", "apps.json"],
        help="Validate specific config only"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    if not os.path.exists(args.gateway_path):
        print(f"\u274C Gateway path not found: {args.gateway_path}")
        return 1

    print(f"Validating gateway config: {args.gateway_path}")
    print("=" * 60)

    results = []

    if args.config is None or args.config == "oauth.json":
        results.append(validate_oauth_json(args.gateway_path))

    if args.config is None or args.config == "oauth2.json":
        results.append(validate_oauth2_json(args.gateway_path))

    if args.config is None or args.config == "apps.json":
        results.append(validate_apps_json(args.gateway_path))

    if args.json:
        print(json.dumps(results, indent=2))
        return 0 if all(r["valid"] for r in results) else 1

    for result in results:
        print_result(result, args.verbose)

    print("\n" + "=" * 60)
    all_valid = all(r["valid"] for r in results)
    if all_valid:
        print("\u2705 ALL CONFIGURATIONS VALID")
    else:
        print("\u274C CONFIGURATION ERRORS FOUND")
    print("=" * 60)

    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
