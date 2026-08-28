# Research pattern: company-site fallback when the job board is blocked

## Why this exists
From this VPS (Tencent Lighthouse, Singapore datacenter IP), job boards like Indeed and
search engines (Google/Bing/DDG/Brave/Mojeek/Yahoo) and aggregators (JobStreet, WhatJobs)
commonly return Cloudflare 403 / captcha / 429. Reader proxies (r.jina.ai) and Google
webcache ALSO return CF challenges from this IP. The COMPANY'S OWN site is usually
reachable (Webflow/hosted), so go there for the legitimacy + role + salary-disclosure checks.

This is a METHOD, not a claim that a specific site is permanently broken. Re-test if the
environment/IP changes. The durable lesson is the fallback chain, not "Indeed never works."

## Recipe (bash + python)
```bash
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
base="https://www.<company>.com"
# 1. core pages
for p in / /about /about/terms /about/contact-us /careers /work-from-home-opportunities; do
  curl -sL -A "$UA" --max-time 25 "$base$p" -o /tmp/c$(echo "$p" | tr / _) .html \
    -w "$p -> %{http_code} %{size_download}\n"
done
```
```python
# 2. extract all role sub-page hrefs from the opportunities page
import re
t=open('/tmp/c_work-from-home-opportunities.html',encoding='utf-8',errors='ignore').read()
for l in sorted(set(re.findall(r'href=["\']([^"\']+)["\']',t))):
    if any(k in l.lower() for k in ['opportunit','job','role','career','apply']):
        print(l)
```
```python
# 3. fetch each sub-page, parse for pay keywords, distinguish boilerplate
import re,html,urllib.request
def text(fn):
    t=open(fn,encoding='utf-8',errors='ignore').read()
    t=re.sub(r'<(script|style|noscript).*?</\1>','',t,flags=re.S)
    t=re.sub('<[^>]+>',' ',t); t=html.unescape(t); t=re.sub(r'\s+',' ',t)
    return t
# loop sub-pages; for each, check pay keywords and print context
```

## Parsing pay keywords — boilerplate traps
- "competitive compensation" / "premium compensation" → NO number.
- "cadence" → English word, NOT CAD currency.
- "pay structure" / "response rate" / "star rating" → not wages.
- Real signal = an actual figure: "RM 3,000", "$20/hr", "USD 15–50", "CAD 25/hour".
- If absent on EVERY page → company publishes no salary. State that plainly.

## Data Gap declaration template (use after >=3 distinct failed routes)
"Salary = DATA GAP. Attempted: (1) direct job board -> CF 403; (2) reader proxy -> CF 403;
(3) webcache -> challenge; (4) company's N role sub-pages -> no salary published;
(5) join-our-team -> 404; (6)+(7) aggregators -> 403. Company publishes zero salaries;
only 'daily pay per call' (call-center) + vague 'competitive compensation'. I will not guess.
Ask them directly in the application."

## Worked example (Agents Only Technologies Inc., 2026-07-13)
- Indeed posting Cloudflare-blocked; company site reachable.
- ToS legal entity "Agents Only Technologies Inc." matched JD poster exactly -> legit.
- HQ Vancouver; locations CA/US/MX/CO/PH/VN; named client (Vessi); BCR data-protection.
- 10 role sub-pages fetched; NONE published a salary; "vibe coding" role not even listed
  among them. Only call-center "daily pay per call" + "competitive compensation" vague.
- Verdict: legit company, but salary = confirmed Data Gap; pay method/currency unverified.
- User corrected the "vibe coding = misnomer" read: title = build-WITH-AI-tools, not eval-only.
