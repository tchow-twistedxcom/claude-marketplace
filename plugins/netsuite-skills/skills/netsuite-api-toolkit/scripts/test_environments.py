#!/usr/bin/env python3
"""
Test NetSuite API Gateway environment routing.

Tests all 3 environments (production, sandbox, sandbox2) to verify:
- Environment header is being read correctly
- OAuth credentials work for each environment
- Correct account ID is returned

Usage:
    python3 test_environments.py
    python3 test_environments.py --env sandbox2
    python3 test_environments.py --app homepage
"""

import argparse
import json
import sys
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

GATEWAY_URL = "http://localhost:3001"
ENVIRONMENTS = ["production", "sandbox", "sandbox2"]

# Expected account IDs per environment
EXPECTED_ACCOUNTS = {
    "production": "4138030",
    "sandbox": "4138030_SB1",
    "sandbox2": "4138030_SB2"
}


def test_environment(app: str, env: str, verbose: bool = False) -> dict:
    """Test a single environment and return results."""
    result = {
        "environment": env,
        "success": False,
        "response_code": None,
        "error": None,
        "account_id": None,
        "expected_account": EXPECTED_ACCOUNTS.get(env),
        "account_match": False
    }

    try:
        url = f"{GATEWAY_URL}/api/{app}?action=getConfig"
        headers = {
            "X-NetSuite-Environment": env,
            "Content-Type": "application/json"
        }

        if verbose:
            print(f"\n[{env}] Testing: {url}")
            print(f"[{env}] Headers: {headers}")

        response = requests.get(url, headers=headers, timeout=30)
        result["response_code"] = response.status_code

        if response.status_code == 200:
            data = response.json()
            result["success"] = data.get("success", False)

            # Try to extract account ID from response
            if "data" in data:
                config_data = data["data"]
                if isinstance(config_data, dict):
                    result["account_id"] = config_data.get("accountId") or config_data.get("account_id")

            # Check environment in response
            if "environment" in data:
                result["response_environment"] = data["environment"]

            # Verify account ID matches expected
            if result["account_id"] and result["expected_account"]:
                result["account_match"] = result["account_id"] == result["expected_account"]

            if not result["success"]:
                result["error"] = data.get("error", {}).get("message", "Unknown error")
        else:
            try:
                error_data = response.json()
                result["error"] = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
            except:
                result["error"] = f"HTTP {response.status_code}"

    except requests.exceptions.ConnectionError:
        result["error"] = "Connection refused - is gateway running?"
    except requests.exceptions.Timeout:
        result["error"] = "Request timeout"
    except Exception as e:
        result["error"] = str(e)

    return result


def test_all_environments(app: str, verbose: bool = False) -> list:
    """Test all environments in parallel."""
    results = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(test_environment, app, env, verbose): env
            for env in ENVIRONMENTS
        }

        for future in as_completed(futures):
            results.append(future.result())

    # Sort by environment name for consistent output
    results.sort(key=lambda x: x["environment"])
    return results


def print_results(results: list, verbose: bool = False):
    """Print test results in a formatted table."""
    print("\n" + "=" * 70)
    print("ENVIRONMENT ROUTING TEST RESULTS")
    print("=" * 70)

    all_passed = True

    for r in results:
        env = r["environment"]
        status = "PASS" if r["success"] else "FAIL"
        status_icon = "\u2705" if r["success"] else "\u274C"

        if not r["success"]:
            all_passed = False

        print(f"\n{status_icon} {env.upper()}")
        print(f"   Status: {status}")
        print(f"   HTTP Code: {r['response_code']}")

        if r["error"]:
            print(f"   Error: {r['error']}")

        if r["account_id"]:
            match_icon = "\u2705" if r["account_match"] else "\u274C"
            print(f"   Account ID: {r['account_id']} {match_icon}")
            if not r["account_match"]:
                print(f"   Expected: {r['expected_account']}")

        if verbose and "response_environment" in r:
            print(f"   Response Environment: {r['response_environment']}")

    print("\n" + "=" * 70)
    if all_passed:
        print("\u2705 ALL ENVIRONMENTS PASSED")
    else:
        print("\u274C SOME ENVIRONMENTS FAILED")
    print("=" * 70)

    return all_passed


def generate_curl_commands(app: str):
    """Generate curl commands for manual testing."""
    print("\n" + "=" * 70)
    print("CURL COMMANDS FOR MANUAL TESTING")
    print("=" * 70)

    for env in ENVIRONMENTS:
        print(f"\n# Test {env}:")
        print(f'curl -s "{GATEWAY_URL}/api/{app}?action=getConfig" \\')
        print(f'  -H "X-NetSuite-Environment: {env}" | jq \'.success\'')


def main():
    parser = argparse.ArgumentParser(
        description="Test NetSuite API Gateway environment routing"
    )
    parser.add_argument(
        "--app",
        default="homepage",
        help="App ID to test (default: homepage)"
    )
    parser.add_argument(
        "--env",
        choices=ENVIRONMENTS,
        help="Test specific environment only"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output"
    )
    parser.add_argument(
        "--curl",
        action="store_true",
        help="Generate curl commands for manual testing"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    if args.curl:
        generate_curl_commands(args.app)
        return 0

    print(f"Testing app: {args.app}")
    print(f"Gateway URL: {GATEWAY_URL}")

    if args.env:
        # Test single environment
        results = [test_environment(args.app, args.env, args.verbose)]
    else:
        # Test all environments
        results = test_all_environments(args.app, args.verbose)

    if args.json:
        print(json.dumps(results, indent=2))
        return 0 if all(r["success"] for r in results) else 1

    all_passed = print_results(results, args.verbose)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
