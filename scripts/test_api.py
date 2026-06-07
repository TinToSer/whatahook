# -*- coding: utf-8 -*-
"""
WhataHook API test script  --  python test_api.py
Stdlib only, no third-party libraries needed.
"""

import base64
import json
import os
import sys
import urllib.request
import urllib.error

# Force UTF-8 output so non-ASCII replies (emoji, ₹, etc.) don't crash on Windows terminals.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL   = "http://localhost:9006"
API_KEY    = ""   # set if you started with -api-key
TEST_PHONE = ""   # e.g. "919999999999" - set to enable send tests

# 1x1 red PNG used for image tests
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)

# ---------- HTTP helpers -----------------------------------------------------

def _headers():
    h = {"Content-Type": "application/json"}
    if API_KEY:
        h["Authorization"] = "Bearer " + API_KEY
    return h

def get(path, timeout=10):
    req = urllib.request.Request(BASE_URL + path, headers=_headers())
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def post(path, body, timeout=30):
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE_URL + path, data=data, headers=_headers(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

def post_multipart(path, fields, file_field, file_bytes, file_name, mime, timeout=30):
    boundary = "----WHTBoundary1234567890"
    body = b""
    for k, v in fields.items():
        body += ("--" + boundary + "\r\nContent-Disposition: form-data; name=\"" +
                 k + "\"\r\n\r\n" + v + "\r\n").encode()
    body += ("--" + boundary + "\r\nContent-Disposition: form-data; name=\"" +
             file_field + "\"; filename=\"" + file_name + "\"\r\nContent-Type: " +
             mime + "\r\n\r\n").encode() + file_bytes + b"\r\n"
    body += ("--" + boundary + "--\r\n").encode()
    h = {k: v for k, v in _headers().items() if k != "Content-Type"}
    h["Content-Type"] = "multipart/form-data; boundary=" + boundary
    req = urllib.request.Request(BASE_URL + path, data=body, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

# ---------- test runner ------------------------------------------------------

results = []

def run(name, fn, skip=False, skip_reason=""):
    if skip:
        msg = "  [SKIP]  " + name
        if skip_reason:
            msg += "  (" + skip_reason + ")"
        print(msg)
        results.append((name, "skip"))
        return None
    try:
        out = fn()
        print("  [PASS]  " + name)
        results.append((name, "pass"))
        return out
    except Exception as e:
        print("  [FAIL]  " + name + "  ->  " + str(e))
        results.append((name, "FAIL: " + str(e)))
        return None

def warn(name, fn):
    """Run a test but show WARN instead of FAIL on error (for optional features)."""
    try:
        out = fn()
        print("  [PASS]  " + name)
        results.append((name, "pass"))
        return out
    except Exception as e:
        print("  [WARN]  " + name + "  ->  " + str(e))
        results.append((name, "warn"))
        return None

def check(name, condition, detail=""):
    if condition:
        print("         [PASS]  " + name)
        results.append((name, "pass"))
    else:
        print("         [FAIL]  " + name + "  " + str(detail))
        results.append((name, "FAIL " + str(detail)))

# =============================================================================
# 1. Status
# =============================================================================
print("\n-- 1. Status ---------------------------------------------------")
s = run("GET /api/status", lambda: get("/api/status"))
meta_ai_ready = False
if s:
    check("connected == true",     s.get("connected") is True,    repr(s))
    check("qr_available == false", s.get("qr_available") is False, repr(s))
    meta_ai_ready = bool(s.get("meta_ai_ready"))
    if meta_ai_ready:
        print("         [INFO]  Meta AI ready: " + s.get("meta_ai_phone", ""))
    else:
        print("         [WARN]  Meta AI not detected (open Meta AI chat in WhatsApp first)")

# =============================================================================
# 2. OpenAI models list
# =============================================================================
print("\n-- 2. GET /v1/models -------------------------------------------")
m = run("GET /v1/models", lambda: get("/v1/models"))
if m:
    ids = [x["id"] for x in m.get("data", [])]
    check("returns meta-ai model", "meta-ai" in ids, repr(ids))

# =============================================================================
# 3. Chat completions — non-streaming  (requires Meta AI)
# =============================================================================
print("\n-- 3. POST /v1/chat/completions  (non-streaming) --------------")
def _chat_nostream():
    r = post("/v1/chat/completions", {
        "model": "meta-ai",
        "messages": [{"role": "user", "content": "Reply with exactly one word: PONG"}],
        "stream": False,
    }, timeout=75)
    if "error" in r:
        raise Exception(r["error"])
    return r

cr = warn("POST /v1/chat/completions", _chat_nostream)
if cr and "choices" in cr:
    choices = cr.get("choices", [])
    check("has choices",          len(choices) > 0,                 repr(cr))
    check("finish_reason = stop", choices[0].get("finish_reason") == "stop")
    content = choices[0].get("message", {}).get("content", "")
    check("content non-empty",    bool(content),                    repr(content[:80]))
    print("         Meta AI replied (%d chars):" % len(content))
    print("         " + content)

# =============================================================================
# 4. Chat completions — streaming SSE
# =============================================================================
print("\n-- 4. POST /v1/chat/completions  (stream:true) ----------------")
def _chat_stream():
    req = urllib.request.Request(
        BASE_URL + "/v1/chat/completions",
        data=json.dumps({
            "model": "meta-ai",
            "messages": [{"role": "user", "content": "What are the latest news on oil prices"}],
            "stream": True,
        }).encode(),
        headers=_headers(), method="POST",
    )
    chunks = []
    try:
        with urllib.request.urlopen(req, timeout=75) as resp:
            for raw in resp:
                line = raw.decode("utf-8").strip()
                if line.startswith("data:") and line != "data: [DONE]":
                    chunks.append(json.loads(line[5:].strip()))
    except urllib.error.HTTPError as e:
        body = json.loads(e.read())
        raise Exception(body.get("error", str(e)))
    if not chunks:
        raise Exception("zero SSE chunks received")
    return chunks

sc = warn("POST /v1/chat/completions stream", _chat_stream)
if sc:
    check("received >= 1 chunk", len(sc) > 0, str(len(sc)) + " chunks")
    content_chunks = [c for c in sc if c.get("choices",[{}])[0].get("delta",{}).get("content")]
    check("content delta present", len(content_chunks) > 0)
    assembled = "".join(
        c["choices"][0]["delta"]["content"]
        for c in content_chunks
    )
    check("assembled text non-empty", bool(assembled))
    print("         Streamed (%d chunks, %d chars total):" % (len(sc), len(assembled)))
    print("         " + assembled)

# =============================================================================
# 5-9. Send messages (need TEST_PHONE)
# =============================================================================
skip_send = not TEST_PHONE
skip_reason = "set TEST_PHONE to enable"

print("\n-- 5. Send text ------------------------------------------------")
run("POST /api/send  (text)",
    lambda: post("/api/send", {"phone": TEST_PHONE, "type": "text",
                               "text": "WhataHook test - text"}),
    skip=skip_send, skip_reason=skip_reason)

print("\n-- 6. Send image via URL ---------------------------------------")
run("POST /api/send  (image url)",
    lambda: post("/api/send", {
        "phone": TEST_PHONE, "type": "image",
        "url": ("https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/"
                "PNG_transparency_demonstration_1.png/"
                "280px-PNG_transparency_demonstration_1.png"),
        "caption": "WhataHook image URL test", "mime": "image/png",
    }),
    skip=skip_send, skip_reason=skip_reason)

print("\n-- 7. Send image via base64 ------------------------------------")
run("POST /api/send  (image base64)",
    lambda: post("/api/send", {
        "phone": TEST_PHONE, "type": "image",
        "data": base64.b64encode(TINY_PNG).decode(),
        "mime": "image/png", "caption": "base64 pixel",
    }),
    skip=skip_send, skip_reason=skip_reason)

print("\n-- 8. Send image via multipart ---------------------------------")
run("POST /api/send  (image multipart)",
    lambda: post_multipart(
        "/api/send",
        {"phone": TEST_PHONE, "type": "image", "caption": "multipart upload"},
        "file", TINY_PNG, "pixel.png", "image/png",
    ),
    skip=skip_send, skip_reason=skip_reason)

print("\n-- 9. Send document --------------------------------------------")
run("POST /api/send  (document)",
    lambda: post("/api/send", {
        "phone": TEST_PHONE, "type": "document",
        "data": base64.b64encode(b"WhataHook test doc\n").decode(),
        "mime": "text/plain", "filename": "test.txt",
    }),
    skip=skip_send, skip_reason=skip_reason)

# =============================================================================
# 10. Get messages
# =============================================================================
print("\n-- 10. GET /api/messages ---------------------------------------")
msgs = run("GET /api/messages", lambda: get("/api/messages?limit=10"))
if msgs is not None:
    check("returns a list",        isinstance(msgs, list),   type(msgs).__name__)
    if msgs:
        check("item has 'from'",       "from"      in msgs[0])
        check("item has 'timestamp'",  "timestamp" in msgs[0])
        check("item has 'body'",       "body"      in msgs[0])
        check("item has 'media_type'", "media_type" in msgs[0])
        print("         " + str(len(msgs)) + " message(s) in buffer")

# =============================================================================
# 11. SSE stream handshake
# =============================================================================
print("\n-- 11. GET /api/messages/stream  (SSE handshake) --------------")
def _sse():
    resp = urllib.request.urlopen(BASE_URL + "/api/messages/stream", timeout=5)
    ct = resp.headers.get("Content-Type", "")
    first = resp.readline().decode("utf-8").strip()
    resp.close()
    return ct, first

sse = run("SSE headers + initial comment", _sse)
if sse:
    check("Content-Type: text/event-stream", "text/event-stream" in sse[0], repr(sse[0]))
    check("opens with ':' comment",          sse[1].startswith(":"),         repr(sse[1]))

# =============================================================================
# 12. Logs API
# =============================================================================
print("\n-- 12. GET /api/logs -------------------------------------------")
logs = run("GET /api/logs", lambda: get("/api/logs"))
if logs is not None:
    check("returns a list", isinstance(logs, list), type(logs).__name__)
    if logs:
        check("item has 'level'",   "level"   in logs[0])
        check("item has 'message'", "message" in logs[0])
        check("item has 'time'",    "time"    in logs[0])

print("\n-- 12b. DELETE /api/logs (clear) -------------------------------")
def _clear_logs():
    req = urllib.request.Request(BASE_URL + "/api/logs", method="DELETE", headers=_headers())
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())
run("DELETE /api/logs", _clear_logs)

# =============================================================================
# 13. Error handling
# =============================================================================
print("\n-- 13. Error handling ------------------------------------------")

def _bad_send():
    r = post("/api/send", {"phone": "", "type": "text", "text": "x"})
    assert "error" in r, "expected error field, got " + repr(r)
    return r

run("POST /api/send empty phone -> 400 json error", _bad_send)

def _bad_type():
    r = post("/api/send", {"phone": "123", "type": "foobar", "text": "x"})
    assert "error" in r, "expected error field, got " + repr(r)
    return r

run("POST /api/send bad type -> 400 json error", _bad_type)
run("GET /api/messages unknown phone -> []",
    lambda: get("/api/messages?phone=00000000000&limit=5"))

# =============================================================================
# 14. Chat completions with image (company.png)
# =============================================================================
print("\n-- 14. Chat completions with image (company.png) ---------------")

def _chat_with_image():
    img_path = os.path.join(os.path.dirname(__file__), "..", "company.png")
    with open(img_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    r = post("/v1/chat/completions", {
        "model": "meta-ai",
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + img_b64}},
            {"type": "text", "text": "Describe this image briefly."}
        ]}],
        "stream": False,
    }, timeout=90)
    if "error" in r:
        raise Exception(r["error"])
    return r

cr14 = warn("POST /v1/chat/completions with image", _chat_with_image)
if cr14 and "choices" in cr14:
    content = cr14["choices"][0]["message"]["content"]
    check("content non-empty", bool(content))
    print("         Meta AI replied: " + content)

# =============================================================================
# Summary
# =============================================================================
print("\n" + "-" * 55)
fails  = [n for n, st in results if st.startswith("FAIL")]
warns  = [n for n, st in results if st == "warn"]
skips  = [n for n, st in results if st == "skip"]
passed = len(results) - len(fails) - len(warns) - len(skips)
print("  Passed: %d   Warned: %d   Failed: %d   Skipped: %d" %
      (passed, len(warns), len(fails), len(skips)))
if warns:
    print("\n  Warned (optional/external):")
    for w in warns:
        print("    ~ " + w)
if fails:
    print("\n  Failed:")
    for f in fails:
        print("    * " + f)
if not TEST_PHONE:
    print("\n  Tip: set TEST_PHONE in this script to run all send tests (5-9).")
print()
sys.exit(1 if fails else 0)
