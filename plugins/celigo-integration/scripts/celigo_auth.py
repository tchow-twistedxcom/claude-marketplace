#!/usr/bin/env python3
"""
Celigo Authentication Helper

Manages API key authentication for Celigo integrator.io REST API.
Supports multiple environments (production, sandbox) and validates API access.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Configuration paths
SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
CONFIG_FILE = CONFIG_DIR / "celigo_config.json"
TEMPLATE_FILE = CONFIG_DIR / "celigo_config.template.json"


def load_config() -> dict:
    """Load configuration from config file."""
    if not CONFIG_FILE.exists():
        print(f"Error: Configuration file not found at {CONFIG_FILE}", file=sys.stderr)
        print(f"Copy {TEMPLATE_FILE.name} to {CONFIG_FILE.name} and add your API keys.", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_FILE) as f:
        return json.load(f)


def get_environment(config: dict, env_name: str = None) -> dict:
    """Get environment configuration."""
    env_name = env_name or config.get("defaults", {}).get("environment", "production")

    if env_name not in config.get("environments", {}):
        print(f"Error: Environment '{env_name}' not found in config.", file=sys.stderr)
        print(f"Available environments: {list(config.get('environments', {}).keys())}", file=sys.stderr)
        sys.exit(1)

    return config["environments"][env_name]


def test_api_key(api_url: str, api_key: str) -> dict:
    """Test API key by making a simple request."""
    test_url = f"{api_url}/integrations?limit=1"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        req = Request(test_url, headers=headers)
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            return {
                "valid": True,
                "status": response.status,
                "integration_count": len(data) if isinstance(data, list) else 0
            }
    except HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        return {
            "valid": False,
            "status": e.code,
            "error": e.reason,
            "details": error_body
        }
    except URLError as e:
        return {
            "valid": False,
            "status": None,
            "error": str(e.reason)
        }
    except Exception as e:
        return {
            "valid": False,
            "status": None,
            "error": str(e)
        }


def get_api_key(env_name: str = None) -> str:
    """Get API key for specified environment."""
    config = load_config()
    env = get_environment(config, env_name)

    api_key = env.get("api_key", "")
    if not api_key or api_key.startswith("YOUR_"):
        print(f"Error: API key not configured for environment '{env.get('name', env_name)}'", file=sys.stderr)
        print("Please update your config file with a valid API key.", file=sys.stderr)
        sys.exit(1)

    return api_key


def cmd_test(args):
    """Test API key validity."""
    config = load_config()
    env = get_environment(config, args.env)
    env_name = env.get("name", args.env)

    print(f"Testing API key for: {env_name}")
    print(f"API URL: {env.get('api_url', 'N/A')}")

    api_key = env.get("api_key", "")
    if not api_key or api_key.startswith("YOUR_"):
        print(f"\nError: API key not configured for '{env_name}'")
        sys.exit(1)

    result = test_api_key(env.get("api_url"), api_key)

    if result["valid"]:
        print(f"\nAPI Key: VALID")
        print(f"Status: {result['status']}")
        print(f"Found {result['integration_count']} integration(s)")
    else:
        print(f"\nAPI Key: INVALID")
        print(f"Status: {result['status']}")
        print(f"Error: {result['error']}")
        if result.get("details"):
            print(f"Details: {result['details'][:200]}")
        sys.exit(1)


def cmd_key(args):
    """Print API key (for use in scripts)."""
    api_key = get_api_key(args.env)
    print(api_key)


def cmd_info(args):
    """Show configuration information."""
    config = load_config()
    env = get_environment(config, args.env)
    env_name = env.get("name", args.env or config.get("defaults", {}).get("environment"))

    print(f"Environment: {env_name}")
    print(f"API URL: {env.get('api_url', 'N/A')}")

    api_key = env.get("api_key", "")
    if api_key and not api_key.startswith("YOUR_"):
        # Show masked key
        masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 16 else "****"
        print(f"API Key: {masked}")
    else:
        print("API Key: NOT CONFIGURED")

    print(f"\nDefaults:")
    defaults = config.get("defaults", {})
    print(f"  Environment: {defaults.get('environment', 'production')}")
    print(f"  Timeout: {defaults.get('timeout', 30)}s")
    print(f"  Max Retries: {defaults.get('max_retries', 3)}")

    print(f"\nAvailable Environments: {list(config.get('environments', {}).keys())}")


def cmd_curl(args):
    """Generate curl command for API request."""
    config = load_config()
    env = get_environment(config, args.env)
    api_key = get_api_key(args.env)
    api_url = env.get("api_url")

    endpoint = args.endpoint.lstrip("/")
    full_url = f"{api_url}/{endpoint}"

    curl_cmd = f'''curl -X GET "{full_url}" \\
  -H "Authorization: Bearer {api_key}" \\
  -H "Content-Type: application/json" \\
  -H "Accept: application/json"'''

    print(curl_cmd)


def main():
    parser = argparse.ArgumentParser(
        description="Celigo API Authentication Helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --test                    # Test API key
  %(prog)s --key                     # Print API key for use in scripts
  %(prog)s --info                    # Show configuration
  %(prog)s --curl /integrations      # Generate curl command
  %(prog)s --test --env sandbox      # Test sandbox environment
        """
    )

    parser.add_argument("--test", "-t", action="store_true",
                       help="Test API key validity")
    parser.add_argument("--key", "-k", action="store_true",
                       help="Print API key (for use in scripts)")
    parser.add_argument("--info", "-i", action="store_true",
                       help="Show configuration info")
    parser.add_argument("--curl", "-c", dest="endpoint", metavar="ENDPOINT",
                       help="Generate curl command for endpoint")
    parser.add_argument("--env", "-e", default=None,
                       help="Environment to use (default: from config)")

    args = parser.parse_args()

    if args.test:
        cmd_test(args)
    elif args.key:
        cmd_key(args)
    elif args.info:
        cmd_info(args)
    elif args.endpoint:
        cmd_curl(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
