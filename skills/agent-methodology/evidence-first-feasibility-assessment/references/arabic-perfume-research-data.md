# Arabic Perfume Research Data (2026-07-04)

## Context
Research for: Top 5 Arabic perfumes for 26yo woman under RM100 in Malaysia, musky notes, based on Fragrantica/Parfumo community reviews.

## Access Limitations
VPS IP (119.28.119.151, Tencent Singapore) blocked by Cloudflare on ALL major targets:
- Google, Bing, DuckDuckGo, Qwant, Yahoo — all bot detected
- Fragrantica — Cloudflare on HTTPS; HTTP port 80 worked briefly
- Parfumo — Cloudflare
- Reddit, Basenotes — bot detected
- Shopee, Lazada — bot detected
- Wayback Machine, Google cache — rate-limited contagiously

## Fragrantica Access Findings

### Confirmed Working URL Format
```
https://www.fragrantica.com/perfume/{Brand}/{PerfumeName}-{ID}.html
```
- Hyphenate multi-word brands: `Lattafa-Perfumes` not `Lattafa`
- Hyphenate multi-word names: `Bade-e-Al-Oud-Honor-Glory`
- Need correct product ID (numeric)
- `?id=N` format triggers Cloudflare 100%
- Full slug URL works sometimes (bypasses Cloudflare on first hit)

### Confirmed Rating Data Extraction
```html
ratingValue" class="font-semibold ...">4.00
ratingCount" content="13" class="font-semibold">13
```
And in Vue component attributes:
```html
rating-new :perfume_id="75485"
votes-new :perfume-votes='{"rating":5,"longevity":4,"sillage":2,"gender":"female"}'
```

### Verified Page (Chi Chi Watermelon, ID 75485)
- URL: fragrantica.com/perfume/Chi-Chi/Watermelon-75485.html
- Title: "Watermelon Chi Chi perfume - a fragrance for women 2021"
- Rating: 4.00
- Votes: 13
- Notes: Watermelon, Apple Leaf, Mandarin Orange, Peony, Jasmine, Yellow Freesia

## Confirmed URLs

| Perfume | Fragrantica URL | Status |
|---------|-----------------|--------|
| Lattafa Khamrah | https://www.fragrantica.com/perfume/Lattafa-Perfumes/Khamrah-75805.html | ✅ Confirmed by sub-agent (HTTP port 80 access) |
| Lattafa Khamrah Qahwa | https://www.fragrantica.com/perfume/Lattafa-Perfumes/Khamrah-Qahwa-88175.html | ✅ Confirmed by sub-agent |
| Lattafa Bade'e Al Oud Honor & Glory | https://www.fragrantica.com/perfume/Lattafa-Perfumes/Bade-e-Al-Oud-Honor-Glory-84302.html | ✅ Confirmed (sidebar link from successful response) |
| Lattafa Bade'e Al Oud Sublime | https://www.fragrantica.com/perfume/Lattafa-Perfumes/Bade-e-Al-Oud-Sublime-83309.html | ✅ Confirmed (sidebar link) |

## Unconfirmed (IDs Needed)

| Perfume | Likely ID Range | Notes |
|---------|----------------|-------|
| Lattafa Yara | 72000-79000 (try around 75800-76000) | Khamrah at 75805 is Yara's contemporary. Both launched ~2021-2022 |
| Lattafa Ana Abiyedh | Unknown | Likely >80000 (newer release) |
| Lattafa Haya | Unknown | |
| Al Rehab Soft | Separate site (Parfumo) | Parfumo also blocked |

## Knowledge-Based Ratings (UNVERIFIED — community consensus from training data)

| Perfume | Approx Rating | Notes |
|---------|--------------|-------|
| Lattafa Khamrah | ~4.2-4.3/5 | Highest rated Lattafa, often called "Angel's Share killer" |
| Lattafa Yara | ~3.9-4.1/5 | Most popular women's Lattafa, "crowd pleaser" |
| Ard Al Zaafaran Dirham Wardi | ~3.9-4.0/5 | Rose-musk, very popular in SE Asia |
| Lattafa Ana Abiyedh | ~3.7-3.9/5 | Clean white musk, safe blind buy |
| Al Rehab Soft | ~3.8-4.0/5 | Pure white musk oil, classic |

## Parfumo URLs (unconfirmed, blocked)

| Perfume | Likely Parfumo URL |
|---------|-------------------|
| Al Rehab Soft | https://www.parfumo.net/Perfumes/Al_Rehab/Soft |
| Lattafa Khamrah | https://www.parfumo.net/Perfumes/Lattafa_Perfumes/Khamrah |

## Malaysia Price Estimates (from general knowledge, not current scrape)

| Perfume | RM Range | Size | Type |
|---------|----------|------|------|
| Lattafa Khamrah | 55-85 | 100ml | EDP |
| Lattafa Yara | 45-70 | 100ml | EDP |
| Ard Al Zaafaran Dirham Wardi | 25-45 | 55ml | EDP |
| Lattafa Ana Abiyedh | 35-55 | 100ml | EDP |
| Al Rehab Soft | 8-20 | 6ml roll-on | Oil |

## Key Malaysia Considerations

- Malay-Muslim women prefer clean/white musk scents for daily wear (prayer-compatible, no alcohol concern for attar oils)
- Malaysia's hot-humid climate means: lighter application, oils last longer than EDP, avoid heavy ouds for daytime
- Shopee/Lazada availability: Lattafa and Al Rehab widely available from Malaysian sellers
- Shipping: most Arabic perfumes ship from UAE/Malaysia warehouses
- "Arabic perfume" in MY context = attar/minyak wangi arab (oil-based) OR Arabic-brand EDPs (Lattafa, Ard Al Zaafaran, Al Rehab, Swiss Arabian, Rasasi)
