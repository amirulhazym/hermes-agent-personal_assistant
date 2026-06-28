# curl-impersonate Integration

> Priority #5 — Standby. Lightweight TLS fingerprint spoofing to bypass bot detection.

## What It Is

**curl-impersonate** ([lwthiker/curl-impersonate](https://github.com/lwthiker/curl-impersonate)) is a modified build of curl that produces TLS/HTTP handshakes identical to Chrome, Edge, Safari, or Firefox. Useful for evading TLS fingerprint-based bot detection.

- **License**: MIT ✅ Free
- **Stars**: ~6.2K
- **Stack**: C binary / system package
- **Why:** Simple, lightweight bypass for basic requests before needing Playwright/Craw4AI.

## Status

`standby` — queue after Scrapling (#4).

## Use Cases

- Direct `curl` requests where standard `curl` gets blocked (TLS fingerprint mismatch)
- Simple GET/POST that don’t need JavaScript rendering
- First-line defense before escalating to browser-based tools

## Install

### Ubuntu / WSL

```bash
sudo apt-get update
sudo apt-get install -y curl-impersonate-bin   # or build from source
# OR use the prebuilt static binaries:
# wget https://github.com/lwthiker/curl-impersonate/releases/latest/download/curl-标点
```

### Build from source (if prebuilt unavailable)

```bash
# See: https://github.com/lwthiker/curl-impersonate#build-from-source
```

## Usage

```bash
# Impersonate Chrome
curl_chrome --url https://example.com

# Works with standard curl flags
curl_chrome -X POST -d "foo=bar" https://example.com/api
```

### In Python (via subprocess)

```python
import subprocess

def fetch_via_curl(url):
    # Assumes curl_chrome is on PATH
    result = subprocess.run(
        ["curl_chrome", "--url", url, "-s"],
        capture_output=True,
        text=True
    )
    return result.stdout
```

## Links

- GitHub: https://github.com/lwthiker/curl-impersonate
