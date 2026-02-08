#!/usr/bin/env python3
"""
Inspect API requests and responses from the NetSuite API Gateway.

Captures and displays:
- Request URL, headers, and body
- Response status, headers, and body
- Environment routing decisions
- Timing information

Usage:
    python3 inspect_request.py --app homepage --action getOperationsStatus --env sandbox2
    python3 inspect_request.py --app homepage --action getConfig --curl
"""

import argparse
import json
import sys
import time
import requests

GATEWAY_URL = "http://localhost:3001"


def make_request(app: str, action: str, env: str, method: str = "GET", body: dict = None) -> dict:
    """Make a request and capture all details."""
    url = f"{GATEWAY_URL}/api/{app}"

    headers = {
        "Content-Type": "application/json",
        "X-NetSuite-Environment": env
    }

    params = {"action": action}

    result = {
        "request": {
            "method": method,
            "url": url,
            "params": params,
            "headers": dict(headers),
            "body": body
        },
        "response": {
            "status_code": None,
            "headers": {},
            "body": None,
            "environment": None
        },
        "timing": {
            "start": None,
            "end": None,
            "duration_ms": None
        },
        "error": None
    }

    try:
        result["timing"]["start"] = time.time()

        if method == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=30)
        else:
            response = requests.post(url, headers=headers, params=params, json=body, timeout=30)

        result["timing"]["end"] = time.time()
        result["timing"]["duration_ms"] = round((result["timing"]["end"] - result["timing"]["start"]) * 1000, 2)

        result["response"]["status_code"] = response.status_code
        result["response"]["headers"] = dict(response.headers)

        try:
            result["response"]["body"] = response.json()

            # Extract environment from response if present
            if "environment" in result["response"]["body"]:
                result["response"]["environment"] = result["response"]["body"]["environment"]

        except json.JSONDecodeError:
            result["response"]["body"] = response.text

    except requests.exceptions.ConnectionError:
        result["error"] = "Connection refused - is gateway running?"
    except requests.exceptions.Timeout:
        result["error"] = "Request timeout"
    except Exception as e:
        result["error"] = str(e)

    return result


def print_request_details(result: dict, verbose: bool = False):
    """Print request details in a formatted way."""
    req = result["request"]
    res = result["response"]
    timing = result["timing"]

    print("\n" + "=" * 70)
    print("REQUEST")
    print("=" * 70)
    print(f"Method: {req['method']}")
    print(f"URL: {req['url']}")
    print(f"Params: {json.dumps(req['params'])}")
    print(f"Headers:")
    for k, v in req["headers"].items():
        print(f"   {k}: {v}")

    if req["body"]:
        print(f"Body: {json.dumps(req['body'], indent=2)}")

    print("\n" + "=" * 70)
    print("RESPONSE")
    print("=" * 70)

    if result["error"]:
        print(f"\u274C Error: {result['error']}")
        return

    status_icon = "\u2705" if res["status_code"] == 200 else "\u274C"
    print(f"Status: {status_icon} {res['status_code']}")
    print(f"Duration: {timing['duration_ms']}ms")

    if res["environment"]:
        print(f"Environment: {res['environment']}")

    if verbose:
        print(f"Response Headers:")
        for k, v in res["headers"].items():
            print(f"   {k}: {v}")

    print(f"\nBody:")
    if isinstance(res["body"], dict):
        # Pretty print, but truncate large responses
        body_str = json.dumps(res["body"], indent=2)
        if len(body_str) > 2000:
            body_str = body_str[:2000] + "\n... (truncated)"
        print(body_str)
    else:
        print(res["body"])


def generate_curl(app: str, action: str, env: str, method: str = "GET", body: dict = None) -> str:
    """Generate a curl command for the request."""
    url = f"{GATEWAY_URL}/api/{app}?action={action}"

    cmd = f'curl -s -X {method} "{url}" \\\n'
    cmd += f'  -H "Content-Type: application/json" \\\n'
    cmd += f'  -H "X-NetSuite-Environment: {env}"'

    if body:
        cmd += f' \\\n  -d \'{json.dumps(body)}\''

    cmd += " | jq '.'"

    return cmd


def main():
    parser = argparse.ArgumentParser(
        description="Inspect API requests and responses"
    )
    parser.add_argument(
        "--app",
        required=True,
        help="App ID to test"
    )
    parser.add_argument(
        "--action",
        required=True,
        help="API action to call"
    )
    parser.add_argument(
        "--env",
        default="sandbox2",
        help="Target environment (default: sandbox2)"
    )
    parser.add_argument(
        "--method",
        default="GET",
        choices=["GET", "POST"],
        help="HTTP method (default: GET)"
    )
    parser.add_argument(
        "--body",
        help="Request body as JSON string"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show all response headers"
    )
    parser.add_argument(
        "--curl",
        action="store_true",
        help="Generate curl command instead of making request"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    body = None
    if args.body:
        try:
            body = json.loads(args.body)
        except json.JSONDecodeError:
            print(f"\u274C Invalid JSON body: {args.body}")
            return 1

    if args.curl:
        print(generate_curl(args.app, args.action, args.env, args.method, body))
        return 0

    result = make_request(args.app, args.action, args.env, args.method, body)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if result["response"]["status_code"] == 200 else 1

    print_request_details(result, args.verbose)

    return 0 if result["response"]["status_code"] == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
