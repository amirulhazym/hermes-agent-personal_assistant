#!/usr/bin/env python3
"""
Verify all openai-codex credential pool entries.

Tests each entry by:
1. Decoding the JWT to check expiry + extract client_id
2. Attempting a token refresh
3. Making a minimal API call to the Codex Responses API

Usage:
    python3 scripts/verify-codex-pool.py
    python3 scripts/verify-codex-pool.py --write-back   # refresh + write live tokens back to auth.json

Exit codes:
    0 = at least one entry is live
    1 = all entries are dead
    2 = auth.json not found or no openai-codex entries
"""

import json
import sys
import time
import base64
import urllib.request
import urllib.error
import argparse

AUTH_JSON = "/home/ubuntu/.hermes/auth.json"
CLIENT_ID_FALLBACK = "app_EMoamEEZ73f0CkXaXp7hrann"
TOKEN_URL = "https://auth.openai.com/oauth/token"
API_URL = "https://chatgpt.com/backend-api/codex/responses"
REDIRECT_URI = "https://chatgpt.com/backend-api/codex/auth/callback"


def decode_jwt(token):
    """Decode JWT payload without verification."""
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    payload_b64 = parts[1]
    payload_b64 += "=" * (4 - len(payload_b64) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception:
        return {}


def refresh_token(rt, client_id):
    """Attempt to refresh an OAuth token. Returns (access, refresh) or (None, None, error)."""
    data = json.dumps({
        "grant_type": "refresh_token",
        "refresh_token": rt,
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
    }).encode()

    req = urllib.request.Request(
        TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "codex/1.0.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            return result.get("access_token"), result.get("refresh_token"), None
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        return None, None, f"HTTP {e.code}: {body}"
    except Exception as e:
        return None, None, str(e)


def test_api(access_token, model="gpt-5.6-luna"):
    """Make a minimal API call to verify the token works. Returns (text, error)."""
    api_data = json.dumps({
        "model": model,
        "input": [{"role": "user", "content": "Say hello in one word."}],
        "store": False,
        "stream": True,
    }).encode()

    api_req = urllib.request.Request(
        API_URL,
        data=api_data,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": "codex/1.0.0",
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(api_req, timeout=60) as api_resp:
            raw = api_resp.read().decode()
            text_parts = []
            model_name = None
            for line in raw.split("\n"):
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str and data_str != "[DONE]":
                        try:
                            event = json.loads(data_str)
                            if event.get("type") == "response.output_text.delta":
                                text_parts.append(event.get("delta", ""))
                            elif event.get("type") == "response.created":
                                model_name = event.get("response", {}).get("model")
                        except json.JSONDecodeError:
                            pass
            return "".join(text_parts), model_name, None
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        return None, None, f"HTTP {e.code}: {body}"
    except Exception as e:
        return None, None, str(e)


def main():
    parser = argparse.ArgumentParser(description="Verify openai-codex credential pool")
    parser.add_argument("--write-back", action="store_true",
                        help="Refresh live tokens and write back to auth.json")
    parser.add_argument("--model", default="gpt-5.6-luna",
                        help="Model to test (default: gpt-5.6-luna)")
    args = parser.parse_args()

    try:
        with open(AUTH_JSON) as f:
            d = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {AUTH_JSON} not found")
        sys.exit(2)

    pool = d.get("credential_pool", {}).get("openai-codex", [])
    if not pool:
        print("ERROR: No openai-codex entries in credential pool")
        sys.exit(2)

    print(f"Found {len(pool)} credential pool entries\n")

    live_entries = []
    dead_entries = []

    for i, entry in enumerate(pool):
        label = entry.get("label", "unknown")
        eid = entry.get("id", "?")
        access_token = entry.get("access_token", "")
        refresh_tok = entry.get("refresh_token", "")
        last_status = entry.get("last_status")

        print(f"{'='*60}")
        print(f"[{i}] id={eid}, label={label}, last_status={last_status}")
        print(f"{'='*60}")

        # Step 1: Decode JWT
        payload = decode_jwt(access_token) if access_token else {}
        client_id = payload.get("client_id", CLIENT_ID_FALLBACK)
        now = int(time.time())
        exp = payload.get("exp", 0)
        sub = payload.get("sub", "?")

        if exp:
            if now > exp:
                print(f"  JWT: expired {now - exp}s ago, sub={sub[:20]}...")
            else:
                print(f"  JWT: valid for {exp - now}s, sub={sub[:20]}...")
        print(f"  client_id: {client_id}")

        # Step 2: Refresh
        print(f"  Refreshing token...")
        new_access, new_refresh, err = refresh_token(refresh_tok, client_id)
        if err:
            print(f"  ❌ REFRESH FAILED: {err}")
            # Try fallback client_id if different
            if client_id != CLIENT_ID_FALLBACK:
                print(f"  Retrying with fallback client_id...")
                new_access, new_refresh, err = refresh_token(refresh_tok, CLIENT_ID_FALLBACK)
                if err:
                    print(f"  ❌ RETRY FAILED: {err}")
                    dead_entries.append(entry)
                    continue

        if not new_access:
            dead_entries.append(entry)
            continue

        print(f"  ✅ REFRESH OK: {new_access[:30]}...{new_access[-10:]}")

        # Step 3: API test
        print(f"  Testing API ({args.model})...")
        text, model_name, api_err = test_api(new_access, args.model)
        if api_err:
            print(f"  ❌ API FAILED: {api_err}")
            dead_entries.append(entry)
            continue

        print(f"  ✅ API OK: model={model_name}, response=\"{text}\"")
        entry["access_token"] = new_access
        entry["refresh_token"] = new_refresh
        live_entries.append(entry)

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(live_entries)} live, {len(dead_entries)} dead")
    print(f"{'='*60}")

    for e in live_entries:
        print(f"  ✅ {e.get('label')} (id={e.get('id')})")
    for e in dead_entries:
        print(f"  ❌ {e.get('label')} (id={e.get('id')})")

    # Write back if requested
    if args.write_back and live_entries:
        print(f"\nWriting back {len(live_entries)} live entries to auth.json...")
        new_pool = live_entries + dead_entries  # keep dead ones too; gateway will skip them

        # Reset error fields on live entries, promote to priority 1
        for idx, entry in enumerate(live_entries):
            entry["priority"] = idx + 1
            entry["last_status"] = None
            entry["last_status_at"] = None
            entry["last_error_code"] = None
            entry["last_error_reason"] = None
            entry["last_error_message"] = None
            entry["last_error_reset_at"] = None
            entry["last_refresh"] = time.strftime("%Y-%m-%dT%H:%M:%S.000000Z", time.gmtime())
            entry["request_count"] = 0
            entry["failure_reason"] = None

        d["credential_pool"]["openai-codex"] = new_pool

        # Update primary provider tokens with the first live entry
        if live_entries:
            d["providers"]["openai-codex"]["tokens"] = {
                "access_token": live_entries[0]["access_token"],
                "refresh_token": live_entries[0]["refresh_token"],
            }
            d["providers"]["openai-codex"]["last_refresh"] = time.strftime(
                "%Y-%m-%dT%H:%M:%S.000000Z", time.gmtime()
            )
            d["providers"]["openai-codex"]["auth_mode"] = "oauth"

        d["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S.000000Z", time.gmtime())

        with open(AUTH_JSON, "w") as f:
            json.dump(d, f, indent=2)
        print("✅ auth.json updated")

    if live_entries:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
