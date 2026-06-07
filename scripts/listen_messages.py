# -*- coding: utf-8 -*-
"""
Listen for incoming WhatsApp messages via the SSE stream.
Prints each message as it arrives. Press Ctrl+C to stop.
Stdlib only — no pip packages needed.

Usage:
    python listen_messages.py
    python listen_messages.py --phone 919999999999   # filter by number
"""

import json
import sys
import urllib.request
import urllib.error

BASE = "http://localhost:9006"
API_KEY = ""  # set if you started whatahook.exe with -api-key

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _headers():
    h = {}
    if API_KEY:
        h["Authorization"] = "Bearer " + API_KEY
    return h


def listen(phone_filter=""):
    url = BASE + "/api/messages/stream"
    if phone_filter:
        url += "?phone=" + phone_filter
    req = urllib.request.Request(url, headers=_headers())

    print(f"Listening for messages{' from ' + phone_filter if phone_filter else ''}... (Ctrl+C to stop)\n")

    try:
        with urllib.request.urlopen(req) as stream:
            for raw in stream:
                line = raw.decode("utf-8").strip()
                if not line.startswith("data:") or line == "data: [DONE]":
                    continue
                msg = json.loads(line[5:].strip())
                _print_message(msg)
    except KeyboardInterrupt:
        print("\nStopped.")
    except urllib.error.URLError as e:
        print(f"Connection error: {e}")
        sys.exit(1)


def _print_message(msg):
    sender = msg.get("from", "?")
    body = msg.get("body", "")
    media = msg.get("media_type", "")
    ts = msg.get("timestamp", "")

    time_str = ts[11:19] if len(ts) >= 19 else ts  # HH:MM:SS from ISO string

    if media:
        print(f"[{time_str}] {sender}: <{media}> {body}".rstrip())
    elif body:
        print(f"[{time_str}] {sender}: {body}")


if __name__ == "__main__":
    args = sys.argv[1:]
    phone = ""
    if "--phone" in args:
        idx = args.index("--phone")
        if idx + 1 < len(args):
            phone = args[idx + 1]

    listen(phone)
