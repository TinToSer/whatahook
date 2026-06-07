# -*- coding: utf-8 -*-
"""
Ask Meta AI a question via WhataHook.
Stdlib only — no pip packages needed.

Usage:
    python ask_meta_ai.py "What is the speed of light?"
    python ask_meta_ai.py --stream "Tell me a short story"
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
    h = {"Content-Type": "application/json"}
    if API_KEY:
        h["Authorization"] = "Bearer " + API_KEY
    return h


def ask(prompt: str) -> str:
    """Send a prompt and return the complete reply as a string."""
    body = json.dumps({
        "model": "meta-ai",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }).encode()
    req = urllib.request.Request(BASE + "/v1/chat/completions", data=body, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=70) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        data = json.loads(e.read())
    if "error" in data:
        raise RuntimeError(data["error"])
    return data["choices"][0]["message"]["content"]


def ask_stream(prompt: str):
    """Send a prompt and print the reply token-by-token as it arrives."""
    body = json.dumps({
        "model": "meta-ai",
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }).encode()
    req = urllib.request.Request(BASE + "/v1/chat/completions", data=body, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=70) as resp:
            for raw in resp:
                line = raw.decode("utf-8").strip()
                if not line.startswith("data:") or line == "data: [DONE]":
                    continue
                chunk = json.loads(line[5:].strip())
                delta = chunk["choices"][0]["delta"].get("content", "")
                if delta:
                    print(delta, end="", flush=True)
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        raise RuntimeError(err.get("error", str(e)))
    print()


if __name__ == "__main__":
    args = sys.argv[1:]
    stream = "--stream" in args
    args = [a for a in args if a != "--stream"]

    if not args:
        print("Usage: python ask_meta_ai.py [--stream] \"your question\"")
        sys.exit(1)

    prompt = " ".join(args)

    if stream:
        print("Streaming reply:\n")
        ask_stream(prompt)
    else:
        print(ask(prompt))
