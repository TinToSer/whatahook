# -*- coding: utf-8 -*-
"""
Send WhatsApp messages via WhataHook.
Supports text, image (URL or file), audio, and document.
Stdlib only — no pip packages needed.

Usage:
    python send_message.py text      919999999999 "Hello!"
    python send_message.py image     919999999999 photo.jpg "Check this out"
    python send_message.py image-url 919999999999 https://example.com/pic.jpg
    python send_message.py audio     919999999999 voice.ogg
    python send_message.py document  919999999999 report.pdf
"""

import base64
import json
import mimetypes
import os
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


def _post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def _file_to_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _mime(path):
    mt, _ = mimetypes.guess_type(path)
    return mt or "application/octet-stream"


def send_text(phone, text):
    return _post("/api/send", {"phone": phone, "type": "text", "text": text})


def send_image(phone, path, caption=""):
    return _post("/api/send", {
        "phone": phone,
        "type": "image",
        "data": _file_to_b64(path),
        "mime": _mime(path),
        "caption": caption,
    })


def send_image_url(phone, url, caption="", mime=""):
    return _post("/api/send", {
        "phone": phone,
        "type": "image",
        "url": url,
        "mime": mime,
        "caption": caption,
    })


def send_audio(phone, path):
    return _post("/api/send", {
        "phone": phone,
        "type": "audio",
        "data": _file_to_b64(path),
        "mime": _mime(path),
    })


def send_document(phone, path, caption=""):
    return _post("/api/send", {
        "phone": phone,
        "type": "document",
        "data": _file_to_b64(path),
        "mime": _mime(path),
        "filename": os.path.basename(path),
        "caption": caption,
    })


USAGE = """Usage:
  python send_message.py text      <phone> <message>
  python send_message.py image     <phone> <file>   [caption]
  python send_message.py image-url <phone> <url>    [caption]
  python send_message.py audio     <phone> <file>
  python send_message.py document  <phone> <file>   [caption]

phone: full international number without + (e.g. 919999999999)
"""

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 3:
        print(USAGE)
        sys.exit(1)

    cmd, phone = args[0], args[1]

    if cmd == "text":
        result = send_text(phone, " ".join(args[2:]))
    elif cmd == "image":
        caption = args[3] if len(args) > 3 else ""
        result = send_image(phone, args[2], caption)
    elif cmd == "image-url":
        caption = args[3] if len(args) > 3 else ""
        result = send_image_url(phone, args[2], caption)
    elif cmd == "audio":
        result = send_audio(phone, args[2])
    elif cmd == "document":
        caption = args[3] if len(args) > 3 else ""
        result = send_document(phone, args[2], caption)
    else:
        print("Unknown command:", cmd)
        print(USAGE)
        sys.exit(1)

    if result.get("ok"):
        print("Sent.")
    else:
        print("Error:", result.get("error", result))
        sys.exit(1)
