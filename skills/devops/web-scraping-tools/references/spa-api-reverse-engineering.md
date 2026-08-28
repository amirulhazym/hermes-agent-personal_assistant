# SPA API Reverse Engineering via JS Bundle Analysis

## When to Use

A web app (React/Vue/Svelte SPA) you're trying to automate has no documented
public API, but you suspect it communicates with a backend via REST/GraphQL
endpoints. Instead of browser network inspection (which requires live interaction),
you can extract API endpoints directly from the JavaScript bundle files.

## The Technique

Modern SPAs bundle ALL frontend code — including API endpoint paths — into
fingerprinted JavaScript files. These can be fetched with plain `curl` and
searched for endpoint patterns.

### Step 1: Identify the Main JS Bundle

Check the HTML source of the page for `<script>` tags with `type="module"` or
`crossorigin` attributes pointing to `/assets/` files:

```bash
curl -sL "https://target.com" | grep -oP 'src="[^"]*\.js"' | head -10
```

The main app bundle is usually the largest non-vendor `.js` file:
- `index-XXXXXX.js`
- `app-XXXXXX.js`
- `main-XXXXXX.js`

### Step 2: Extract Endpoint Paths

Fetch the bundle and grep for common API patterns:

```bash
# Find all API-like paths
curl -sL "https://target.com/assets/index-XXXXXX.js" | \
  grep -oP '["'\''`](/[a-zA-Z]+/[a-zA-Z_-]+)["'\''`]' | \
  sort -u

# Find URLs (full or partial)
curl -sL "https://target.com/assets/index-XXXXXX.js" | \
  grep -oP 'https?://[^"'\''` )]*' | \
  sort -u

# Find paths with common API prefixes
curl -sL "https://target.com/assets/index-XXXXXX.js" | \
  grep -oP '["'\''`](/api/[^"'\''`]*)["'\''`]' | \
  sort -u
```

### Step 3: Test Endpoints

Try the discovered endpoints directly:

```bash
# JSON API endpoint
curl -s "https://target.com/auth/challenge" -H "Accept: application/json"

# Check if it returns JSON or HTML
curl -s "https://target.com/api/endpoint" | head -5
```

⚠️ **SPA endpoints may require specific Accept headers, CSRF tokens, or session
cookies.** The endpoint discovered in the bundle may only work when called from
within the authenticated app context.

### Step 4: If Direct Calls Fail

If the API is protected (CSRF tokens, session-based auth), fall back to:
- Browser-based automation (Playwright + captcha solving per session)
- Intercepting network calls via browser_console fetch hooking

## Live Example: QRYPTY Mail (2026-07-13)

QRYPTY's main bundle was identified from the register page HTML:
```html
<script type="module" crossorigin src="/assets/index-CUb4fjcM.js"></script>
```

Fetching and searching revealed:
```bash
curl -sL "https://qrypty.com/assets/index-CUb4fjcM.js" | \
  grep -oP '["'\''`](/[a-zA-Z]+/[a-zA-Z]+)["'\''`]' | \
  sort -u
```

**Discovered endpoints:**
| Endpoint | Purpose | Works via curl? |
|----------|---------|----------------|
| `/auth/register` | Account creation | ❌ Needs captcha token from browser |
| `/auth/challenge` | Captcha challenge | ❌ SPA-rendered, server returns HTML |
| `/auth/login` | Login with access code | ❌ SPA-rendered |
| `/auth/me` | Current session | ❌ Needs auth cookie |
| `/domains/check` | Check domain availability | Unknown |
| `/emails/folders` | Get folder list | ❌ Needs auth |
| `/profile/settings` | User settings | ❌ Needs auth |

**Why direct API calls don't work here:** The captcha challenge is DOM-generated
(not server-provided), so the answer is computed client-side. The `/auth/challenge`
endpoint returns HTML (the SPA shell), not JSON challenge data. The captcha answer
is checked server-side against session state set during page load.

**Workaround:** Browser automation with Playwright (captcha solving via
`page.evaluate()` DOM inspection).

## When Direct API Calls DO Work

Some SPAs expose genuine REST endpoints behind their JS bundle. Success factors:
- Endpoint returns `Content-Type: application/json` (not `text/html`)
- No custom headers/CAPTCHA session token required
- Rate limit is per-IP not per-session

If the endpoint returns JSON, you can script it directly — this is the fastest path.

## Pitfalls

- **Bundle filenames change with every deploy** — the filename hash (`index-CUb4fjcM.js`)
  changes when the code is rebuilt. Always check the HTML first for the current filename.
- **Minified bundles** — single-letter variable names make grep harder. Focus on
  string literals (path strings, URL constants) which survive minification.
- **Partial paths only** — bundles often store paths as `/path/endpoint` without
  the origin. You need to prepend the base URL when testing.
- **CORS guards** — even if you find the endpoint, the server may reject
  non-browser origins. Check the `Access-Control-*` response headers.
- **Template literal paths** — some bundles embed dynamic segments:
  `/api/users/${userId}` — grep for the literal prefix `/api/users/` instead.
