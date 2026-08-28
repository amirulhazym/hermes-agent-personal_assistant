# ShadowMail Temp Mail — Inbox API (OTP / Verification Code Reader)

**Use when:** A signup/verification flow sends a code to a temp-mail domain
hosted on ShadowMail (e.g. `*.nexaroin.com`, MX → `temp.ilvyoraz.store`).
You need to read the code programmatically without a browser.

**Discovered:** 2026-07-13, during x.ai Grok account signup. Web UI is
"ShadowMail — Temporary Email Generator" at `https://temp.ilvyoraz.store/`.

## Endpoint
```
POST https://temp.ilvyoraz.store/api/inbox/messages
Content-Type: application/json
Body: {"email": "user@example.invalid"}
```
Response (200):
```json
{
  "email": "user@example.invalid",
  "count": 1,
  "messages": [{
    "id": 6258,
    "to": "user@example.invalid",
    "from": "SpaceXAI <user@example.invalid>",
    "from_email": "user@example.invalid",
    "subject": "UL7-LXL xAI confirmation code",
    "body": "<!doctype html>...full HTML email..."
  }]
}
```

## Reading the code (Python)
```python
import json, urllib.request, re
EMAIL = "user@example.invalid"
req = urllib.request.Request(
    "https://temp.ilvyoraz.store/api/inbox/messages",
    data=json.dumps({"email": EMAIL}).encode(),
    headers={"Content-Type": "application/json"}, method="POST")
resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
for m in resp["messages"]:
    body = m["body"]
    text = re.sub(r'<[^>]+>', ' ', body)
    text = re.sub(r'\s+', ' ', text).strip()
    # xAI confirmation codes are ALPHANUMERIC like "UL7-LXL", NOT 6 digits
    code = re.search(r'([A-Z0-9]{2,3}-?[A-Z0-9]{2,3})', m["subject"])
    print("Code:", code.group(1) if code else "check body")
```

## Gotchas
- **Code format is alphanumeric, not numeric.** xAI sends `UL7-LXL`
  (subject: "UL7-LXL xAI confirmation code"). A naive `\d{6}` regex will match
  CSS artifacts (e.g. `333333`, `888888`, color hex `FAFAFA`) from the email
  HTML — those are FALSE positives. Extract from the subject or the bold `<td>`
  that displays the code. The real code appears as `UL7-LXL` in the body:
  `<td ... font-weight: bold;">UL7-LXL</td>`.
- **Other ShadowMail endpoints (from app.js):** `/api/domains` (GET),
  `/api/generate` (POST), `/api/inbox/bulk` (POST). The `API` base in their
  JS is the empty string → endpoints are same-origin relative paths.
- **No auth needed** to read a specific email's inbox — just POST the email
  address. Anyone who knows the address can read it (inherent to temp mail).
- **Message retention is short** — poll promptly after the signup request; the
  message may expire. Re-POST the email to refresh; if `count` drops to 0 the
  code is gone and you must re-trigger the send from the signup flow.
