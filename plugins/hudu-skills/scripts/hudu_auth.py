#!/usr/bin/env python3
"""
Hudu authentication and config loader.

Usage:
    python3 hudu_auth.py --test [--profile NAME] [--config PATH]
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
CONFIG_FILE = CONFIG_DIR / "hudu_config.json"
TEMPLATE_FILE = CONFIG_DIR / "hudu_config.template.json"


class HuduAuth:
    def __init__(self, config_path=None, profile=None):
        self.config_path = Path(config_path) if config_path else CONFIG_FILE
        self._config = self._load_config()
        profile_name = profile or self._config.get("default_profile", "production")
        self._profile = self._get_profile(profile_name)
        self.base_api_url = self._normalize_base_url(self._profile["base_url"])

    def _load_config(self):
        if not self.config_path.exists():
            sys.exit(
                f"Config not found: {self.config_path}\n"
                f"Copy the template and fill in your credentials:\n"
                f"  cp {TEMPLATE_FILE} {CONFIG_FILE}\n"
                f"  # Edit {CONFIG_FILE}: set base_url and api_key"
            )
        with open(self.config_path) as f:
            return json.load(f)

    def _get_profile(self, name):
        profiles = self._config.get("profiles", {})
        if name not in profiles:
            available = ", ".join(profiles.keys()) or "(none)"
            sys.exit(
                f"Profile '{name}' not found in config.\n"
                f"Available profiles: {available}"
            )
        profile = profiles[name]
        for field in ("base_url", "api_key"):
            if not profile.get(field) or profile[field].startswith("YOUR_"):
                sys.exit(
                    f"Profile '{name}' is missing a value for '{field}'.\n"
                    f"Edit {self.config_path} and fill in your Hudu credentials."
                )
        return profile

    @staticmethod
    def _normalize_base_url(url):
        url = url.rstrip("/")
        if not url.endswith("/api/v1"):
            url = url + "/api/v1"
        return url

    def auth_headers(self):
        return {
            "x-api-key": self._profile["api_key"],
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def test_connection(self):
        url = f"{self.base_api_url}/api_info"
        req = urllib.request.Request(url, headers=self.auth_headers())
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            print("Connection successful")
            print(f"  Version:  {data.get('version', 'unknown')}")
            print(f"  Base URL: {self.base_api_url}")
            return True
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            sys.exit(f"HTTP {e.code}: {body}")
        except urllib.error.URLError as e:
            sys.exit(f"Connection failed: {e.reason}")


def main():
    parser = argparse.ArgumentParser(description="Test Hudu API connectivity")
    parser.add_argument("--test", action="store_true", help="Test connection and print version")
    parser.add_argument("--profile", "-p", default=None, help="Config profile name")
    parser.add_argument("--config", default=None, help="Path to config JSON file")
    args = parser.parse_args()

    auth = HuduAuth(config_path=args.config, profile=args.profile)
    if args.test:
        auth.test_connection()


if __name__ == "__main__":
    main()
