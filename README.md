# WhataHook

A lightweight Windows server that bridges **WhatsApp** with an **OpenAI-compatible HTTP API**.  
Run `whatahook.exe`, scan a QR code once, then query Meta AI or send/receive WhatsApp messages from any script or tool that speaks the OpenAI chat-completions format.

---

## Quick start

```
whatahook.exe
```

Open http://localhost:9006/setup and scan the QR code with WhatsApp → three-dot menu → **Linked Devices** → **Link a Device**.

Once connected, the dashboard at http://localhost:9006 shows connection status and live error logs.

### Flags

| Flag | Default | Description |
|------|---------|-------------|
| `-port` | `9006` | HTTP listen port |
| `-db` | `whatahook.db` | SQLite file for WhatsApp auth state |
| `-api-key` | *(none)* | Optional Bearer token for all API calls |

```
whatahook.exe -port 8080 -api-key mysecret
```

---

## API reference

### Authentication

When started with `-api-key`, every request must include the token:

```
Authorization: Bearer <key>
```

or as a query parameter: `?api_key=<key>`

---

### GET /api/status

Returns connection and Meta AI state.

```json
{
  "connected": true,
  "qr_available": false,
  "meta_ai_ready": true,
  "meta_ai_phone": "1234567890@s.whatsapp.net"
}
```

---

### GET /api/qr

Returns the current QR code as a PNG image (`image/png`).  
Returns `503` when no QR is available (already connected or not yet generated).

---

### POST /v1/chat/completions

OpenAI-compatible endpoint. Proxies the prompt to **Meta AI** via WhatsApp and returns the reply.

**Request**

```json
{
  "model": "meta-ai",
  "messages": [
    { "role": "system", "content": "You are a helpful assistant." },
    { "role": "user",   "content": "What is the capital of France?" }
  ],
  "stream": false
}
```

`model` is accepted but ignored — always routes to Meta AI.  
`stream: true` returns Server-Sent Events in the OpenAI streaming format.

**Content can also be an array** (for image + text):

```json
{
  "role": "user",
  "content": [
    { "type": "image_url", "image_url": { "url": "data:image/png;base64,..." } },
    { "type": "text",      "text": "Describe this image." }
  ]
}
```

Only `data:` URIs are supported for images (plain URLs are not forwarded to WhatsApp).

**Non-streaming response**

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1700000000,
  "model": "meta-ai",
  "choices": [{
    "index": 0,
    "message": { "role": "assistant", "content": "Paris." },
    "finish_reason": "stop"
  }],
  "usage": { "prompt_tokens": 12, "completion_tokens": 2, "total_tokens": 14 }
}
```

---

### GET /v1/models

```json
{
  "object": "list",
  "data": [{ "id": "meta-ai", "object": "model", "created": 1700000000, "owned_by": "meta" }]
}
```

---

### POST /api/send

Send a WhatsApp message. Accepts JSON or `multipart/form-data`.

#### Text

```json
{ "phone": "919999999999", "type": "text", "text": "Hello!" }
```

#### Image

```json
{
  "phone": "919999999999",
  "type": "image",
  "url": "https://example.com/photo.jpg",
  "caption": "Look at this",
  "mime": "image/jpeg"
}
```

Or base64:

```json
{ "phone": "919999999999", "type": "image", "data": "<base64>", "mime": "image/png", "caption": "hi" }
```

Or multipart upload:

```
curl http://localhost:9006/api/send \
  -F phone=919999999999 -F type=image -F caption=Hi -F file=@photo.jpg
```

#### Video

```json
{ "phone": "919999999999", "type": "video", "url": "https://example.com/clip.mp4", "caption": "Watch this" }
```

#### Audio (voice note)

```
curl http://localhost:9006/api/send \
  -F phone=919999999999 -F type=audio -F file=@voice.ogg
```

#### Document

```json
{
  "phone": "919999999999",
  "type": "document",
  "url": "https://example.com/report.pdf",
  "filename": "report.pdf"
}
```

**Fields**

| Field | Description |
|-------|-------------|
| `phone` | Recipient number — digits only, with country code (e.g. `919999999999`) |
| `type` | `text` · `image` · `video` · `audio` · `document` |
| `text` | Message body (type=text) |
| `url` | Public URL to fetch media from |
| `data` | Base64-encoded media (with or without `data:mime;base64,` prefix) |
| `mime` | MIME type; auto-detected when omitted |
| `caption` | Caption for image/video/document |
| `filename` | Filename for document (default: `file`) |

**Response**

```json
{ "ok": true }
```

---

### GET /api/messages

Returns recent received messages from the in-memory ring buffer (last 500).

```
GET /api/messages?limit=50&phone=919999999999
```

| Query param | Description |
|-------------|-------------|
| `limit` | Max messages to return (default 50) |
| `phone` | Filter by sender/recipient number |

```json
[
  {
    "id": "...",
    "from": "919999999999",
    "to": "me",
    "body": "Hey!",
    "media_type": "",
    "timestamp": "2024-01-15T10:30:00Z",
    "is_from_me": false
  }
]
```

---

### GET /api/messages/stream

Server-Sent Events stream. Fires one `data:` event per incoming message.

```
curl -N http://localhost:9006/api/messages/stream
```

Each event:

```
data: {"from":"919999999999","body":"Hey!","media_type":"","timestamp":"...","is_from_me":false}
```

A `: keepalive` comment is sent every 15 seconds to keep the connection alive.

---

### GET /api/logs

Returns the in-memory log buffer (last 200 entries).

```json
[{ "time": "2024-01-15T10:30:00Z", "level": "info", "message": "[WA] Connected" }]
```

`level` is `info`, `warn`, or `error`.

### DELETE /api/logs

Clears the log buffer. Returns `{ "ok": true }`.

---

## Notes

- **Meta AI detection** — on first connect, WhataHook scans your contacts for the Meta AI chat. If not found, open the Meta AI conversation in WhatsApp once and restart.
- **Phone number format** — always use the full international number without `+` or spaces (e.g. `919999999999` for India +91 99999 99999).
- **The `.db` file** holds your WhatsApp session. Keep it safe — deleting it requires re-scanning the QR code.
- **Timeout** — Meta AI responses time out after 60 seconds.

---

## Example scripts

See the [`scripts/`](scripts/) folder:

| File | Description |
|------|-------------|
| `test_api.py` | Full API test suite — runs against a live server |
| `ask_meta_ai.py` | Ask Meta AI a question (stdlib, no pip required) |
| `send_message.py` | Send text, image, audio, and document messages |
| `listen_messages.py` | Live SSE stream — print every incoming message |
| `auto_reply_bot.py` | Auto-reply bot: incoming message → Meta AI → reply |
