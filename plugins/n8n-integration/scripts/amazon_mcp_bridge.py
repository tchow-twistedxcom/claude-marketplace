#!/usr/bin/env python3
"""
Amazon SP-API MCP Bridge — stdio ↔ n8n SSE proxy for Claude Desktop.

Bridges the n8n per-workflow SSE endpoint to Claude Desktop's stdio MCP transport.
Claude Desktop spawns this script; it connects to the n8n Amazon tools workflow
and proxies all MCP messages over SSE.

Usage (Claude Desktop config):
    "amazon-tools": {
        "command": "python3",
        "args": ["/path/to/amazon_mcp_bridge.py"]
    }
"""

import json
import os
import sys
import threading
import queue
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from n8n_config import get_api_credentials

MCP_PATH = os.environ.get("AMAZON_MCP_PATH", "amazon-tools")


def main():
    n8n_url, n8n_key = get_api_credentials()
    base = n8n_url.rstrip("/")
    if base.endswith("/api/v1"):
        base = base[: -len("/api/v1")]

    sse_url = f"{base}/mcp/{MCP_PATH}/sse"

    session_id = None
    session_event = threading.Event()
    sse_events = queue.Queue()

    def sse_listener():
        nonlocal session_id
        req = urllib.request.Request(
            sse_url,
            headers={"X-N8N-API-KEY": n8n_key, "Accept": "text/event-stream"},
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                for chunk in resp:
                    line = chunk.decode("utf-8").rstrip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if "sessionId=" in data:
                        session_id = data.split("sessionId=")[-1].strip()
                        session_event.set()
                    elif data:
                        try:
                            sse_events.put(json.loads(data))
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            print(f"SSE error: {e}", file=sys.stderr)

    t = threading.Thread(target=sse_listener, daemon=True)
    t.start()

    # Wait for session ID (up to 10s)
    if not session_event.wait(timeout=10):
        print("ERROR: failed to get session ID from n8n SSE", file=sys.stderr)
        sys.exit(1)

    msg_url = f"{base}/mcp/{MCP_PATH}/messages?sessionId={session_id}"

    def post_message(payload):
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            msg_url,
            data=body,
            headers={
                "Authorization": f"Bearer {n8n_key}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        urllib.request.urlopen(req, timeout=30)

    # Writer thread: SSE events → stdout
    def writer():
        while True:
            event = sse_events.get()
            sys.stdout.write(json.dumps(event) + "\n")
            sys.stdout.flush()

    wt = threading.Thread(target=writer, daemon=True)
    wt.start()

    # Main loop: stdin → POST to n8n
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
            post_message(payload)
        except Exception as e:
            print(f"Bridge error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
