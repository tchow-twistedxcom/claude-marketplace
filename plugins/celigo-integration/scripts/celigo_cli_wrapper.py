#!/usr/bin/env python3
"""
Celigo CLI Wrapper

Subprocess wrapper for @celigo/celigo-cli (official npm package, Node 22+).

Use when: the official CLI covers a verb cleanly and you want CLI parity.
Use direct REST (celigo_api.py's CeligoClient) when:
  - The operation requires fetch-merge-PUT (update with partial payload).
  - The verb is not available in @celigo/celigo-cli.
  - Cross-system orchestration (e.g., edi_audit.py) where raw response control matters.

This module is stateless — each call is a fresh subprocess invocation.

Install:
    npm install -g @celigo/celigo-cli   # requires Node 22+
    celigo auth login                   # authenticate once

Environment:
    CELIGO_ENVIRONMENT: 'sandbox' or 'production' (default). Passed via --environment.
"""

import json
import shutil
import subprocess
import sys
from typing import Any, Optional


CLI_BINARY = "celigo"


def _find_cli() -> str:
    """Return path to celigo CLI binary or raise with install hint."""
    path = shutil.which(CLI_BINARY)
    if path is None:
        print(
            "Error: @celigo/celigo-cli not found. Install with:\n"
            "    npm install -g @celigo/celigo-cli   # requires Node 22+\n"
            "Then authenticate:\n"
            "    celigo auth login\n"
            "Or run celigo-setup for guided installation.",
            file=sys.stderr,
        )
        raise FileNotFoundError("@celigo/celigo-cli is not installed or not on PATH")
    return path


def run(
    verb_string: str,
    *,
    json_output: bool = True,
    env_name: Optional[str] = None,
    timeout: int = 60,
) -> Any:
    """
    Invoke the official Celigo CLI and return parsed output.

    Args:
        verb_string: Space-separated resource + verb + args, e.g. 'tools list'.
        json_output: When True (default), parses stdout as JSON and returns it.
                     When False, returns raw stdout string.
        env_name: 'sandbox' or 'production'. Passed as --environment flag.
        timeout: Subprocess timeout in seconds.

    Returns:
        Parsed JSON (dict or list) when json_output=True, else raw str.

    Raises:
        FileNotFoundError: CLI binary not found.
        subprocess.CalledProcessError: Non-zero exit from CLI.
        json.JSONDecodeError: CLI returned non-JSON when json_output=True.
    """
    cli_path = _find_cli()

    argv = [cli_path] + verb_string.split()
    if json_output:
        argv += ["--output", "json"]
    if env_name:
        argv += ["--environment", env_name]

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"celigo CLI timed out after {timeout}s: {verb_string}")

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise subprocess.CalledProcessError(
            result.returncode,
            argv,
            output=result.stdout,
            stderr=stderr,
        )

    stdout = result.stdout.strip()
    if not json_output:
        return stdout

    if not stdout:
        return {}

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        # CLI may print a help banner or non-JSON on some conditions
        return stdout


def version() -> str:
    """Return the installed CLI version string."""
    return run("--version", json_output=False)


def is_available() -> bool:
    """Return True if @celigo/celigo-cli is installed and on PATH."""
    return shutil.which(CLI_BINARY) is not None
