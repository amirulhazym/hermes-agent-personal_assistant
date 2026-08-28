# Nebula Cloud Gaming — Pricing Mechanism (Verified July 2026)

## Geolocation

VPS IP: 119.28.119.151 (AS132203 Tencent, Singapore)
- ifconfig.co: country="Singapore", country_iso="SG", city="Singapore"
- ipinfo.io: country="SG", city="Singapore"

## Pricing Page Mechanics

URL: https://www.nebula.my/pricing

**Country selector**: Manual `<select>` element (`aria-label="Country"`), NOT hard geo-IP lock.
- Geo-IP influences DEFAULT selection (auto-picks Singapore for SG IP)
- User CAN manually switch to any country
- After switching, prices update to selected country's currency

**Prices by country (verified July 2, 2026):**

| Plan | Malaysia (MYR) | Singapore (SGD) |
|------|---------------|-----------------|
| Premium (monthly) | MYR 45 | not displayed ("-") |
| Day Pass | MYR 7.99 | not displayed |
| Week Pass | MYR 39.99 | not displayed |
| Month Pass | MYR 49.99 | not displayed |

**Key insight**: Singapore default shows "-" (no prices), NOT SGD prices. The original agent failure may have been: (1) SG IP → Singapore auto-selected → prices not displayed ("-") → agent scraped no data, OR (2) the page once showed SGD prices and the country selector bug prevented switching to MY.

## Agent Interaction Notes

- The dropdown is a Wix `<select>` element — `browser_click` may not reliably trigger React re-render
- `browser_console` with `sel.value = 'MY'; sel.dispatchEvent(new Event('change', {bubbles: true}))` works
- After programmatic change, React state may not update immediately — full page re-render may be needed
- No URL-based country override found (no `?country=MY` or `/my/` path pattern)

## Payment Methods

- FPX (Malaysian online banking)
- PayPal
- Visa
- MasterCard
- FAQ: "My currency is not supported. Can I still play?" → suggests USD fallback available

## Source

Original research session: July 2, 2026 — Fact-Check Accuracy Phase 3-4 audit.
