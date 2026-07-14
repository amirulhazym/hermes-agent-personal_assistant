# Research Expert — Verification Rules (Fasa 3)

Applied at Stage 4 of every non-trivial research pipeline run. Not optional.

---

## 1. Cross-Check Rules

### Claim-support mapping
Every material claim in the synthesis must be traceable to ≥1 extracted source.

```
claim → source_id → excerpt (verbatim) → label
```

- **No excerpt = UNTESTED** (even if URL is present). You must have the text that supports the claim.
- **Single source = flag**: "Single-source: claim supported only by {Sx}" — do not present as settled.
- **Circular check**: If source A quotes source B, and source B quotes source A, that is circular — label PENDING, not VALIDATED.

### Multi-source corroboration
- ≥2 independent sources for statistical/numeric claims → VALIDATED
- 1 source for non-controversial factual claims → VALIDATED (with single-source flag)
- 0 sources for any material claim → REJECTED (or UNTESTED if awaiting extract)

### Independence test
Two sources are independent if:
- Different domains (hostname)
- Different extraction pipelines (trafilatura vs crawl4ai vs playwright)
- Not obviously syndicated (same byline, same framing)

If two sources from same domain/crawl say the same thing, they count as **one source** for corroboration.

---

## 2. Freshness / Currency Rules

| Domain | Max age for VALIDATED | Notes |
|--------|----------------------|-------|
| Tech (APIs, libraries, features) | 180 days | Stale if >6 months without explicit "still current" |
| Medical / Drug | 365 days | Unless explicitly superseded |
| News / Events | 30 days | After 30 days, add "as of {date}" caveat |
| Legal / Regulatory | 365 days | Check for amendments |
| General reference | 730 days | 2 years; label "may be outdated" after |
| Pricing | 90 days | Always caveat: "pricing as of {source_date}" |

**Hard rule:** If no date can be extracted from the source, set freshness = low and do not auto-label VALIDATED.

---

## 3. Contradiction Handling

### Detection
During verify pass, scan all extracted claims for conflicts:
- Opposite conclusions from different sources
- Mutually exclusive numeric values (≥2× apart)
- Incompatible dates/timelines

### Response
1. **Surface both sides explicitly** in the report
2. Do NOT pick one silently
3. Label the conflict: "CONTRADICTED: S3 says X, S5 says Y"
4. Confidence → **low** when unresolved contradictions exist
5. Prefer the source with:
   - More direct evidence (primary > secondary)
   - More recent date
   - Higher-authority domain (.gov > .edu > .org > .com > personal blog)
6. If unable to resolve: mark both as PENDING, note the conflict, keep confidence downgraded

---

## 4. Source Quality Gates

### Auto-reject (mark REJECTED, do not cite)
- Pure SEO spam (keyword-stuffed, no original content)
- Empty extract (content length < 50 chars after cleaning)
- Paywall-blocked (only snippet visible, full text inaccessible)
- AI-generated placeholder content (detectable pattern: "In this article we will explore...")
- Forum/Reddit thread with <3 upvotes/votes on factual claim
- Machine-translated content with obvious errors

### Downgrade (mark UNTESTED or flag in report)
- Personal blog, Medium, Substack (not per se bad, but not authoritative)
- Wikipedia (use as pointer to primary source, not primary source itself)
- Press release (bias toward subject)
- Vendor page for that vendor's own product
- PDF behind CDN without accessible date

### Prefer (primary source)
- Official documentation (README, docs site, API reference)
- Peer-reviewed paper (arXiv counts as pre-print, flag as such)
- Government/regulatory site
- Direct statement from named individual (original tweet, press conference)
- Standards body (W3C, ISO, IETF RFC)

---

## 5. Label Application

| Label | Condition |
|-------|-----------|
| **VALIDATED** | ≥1 independent source with verbatim excerpt, freshness within domain limits, no contradiction |
| **UNTESTED** | Claim present but not yet extracted or cross-checked against source content |
| **REJECTED** | Source fails quality gate, or claim contradicted by higher-quality source |
| **PENDING** | Source identifies gap but need follow-up (e.g., future event, paywall, requires auth) |

**Never upgrade a label without new evidence.** UNTESTED stays UNTESTED until extract is live-checked.

---

## 6. Self-Audit (before synthesis release)

Before calling the research complete:

1. Count VALIDATED vs UNTESTED claims. If UNTESTED > VALIDATED, **do not present as confident**.
2. Spot-check 2 random claims: can you trace each to a verbatim source excerpt?
3. Any "probably", "likely", "should be" that isn't backed by extract? → change to UNTESTED.
4. Any fabricated URL, title, or number? → HARD FAIL, discard the entire synthesis, re-do.

---

## 7. Alignment with SOUL Grounding

These rules extend (do not replace) SOUL.md grounding rules 1-9. Specifically:

- SOUL #1 (no self-attestation) → applies: every claim needs source excerpt, not just URL
- SOUL #2 (single source flagged) → applies: single-source flag mandatory for numeric/stat claims
- SOUL #3 (refuse over guess) → applies: never fabricate a URL, date, or statistic
- SOUL #4 (downgrade confidence) → applies: when in doubt, UNTESTED > VALIDATED
- SOUL #7 (rank by evidence) → applies: proposal ranking uses verification labels
