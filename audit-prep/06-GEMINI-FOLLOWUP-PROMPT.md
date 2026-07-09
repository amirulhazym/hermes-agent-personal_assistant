# GEMINI FOLLOW-UP PROMPT — Complete Missing Dimensions

> **Prompt untuk:** Gemini (sambungan dari audit pertama)
> **Tujuan:** Cover 8 dimensi yang belum disentuh dalam audit pertama
> **Files access:** `F:\AI Prep\OVIS\Hermes Agent\drive-download-20260707T151046Z-3-001\` (prep files) + hermes-snapshot-20260707 (VPS rsync)

---

## COPY MULAI SINI 👇

```
Anda adalah GEMINI — meneruskan audit sistem Hermes Agent (MarryJane/MJ).

Dalam audit pertama, anda sudah cover:
1. Medication System → Dexamethasone BD underdosing defect
2. Cron Jobs → hello-world-watch every 1 min (excessive), Daily Health broken pipe error
3. Architecture → cua-driver MCP config pointing to Windows binary on Linux
4. Context-aware reminders via chain_llm.py

SEKARANG: Audit 8 dimensi BERIKUT yang belum disentuh.
Untuk setiap finding: TUNJUKKAN BUKTI dari actual files.

====================================================================
## DIMENSI 1: SECURITY 🔐
====================================================================

Check:
- Ada API keys exposed dalam plaintext dalam mana-mana file?
- WhatsApp allowlist / Telegram allowlist properly configured?
- Baileys WhatsApp library — ada known CVE? (check GHSA-qvv5-jq5g-4cgg)
- Ada secrets (tokens, passwords) dalam cron job definitions?
- Medication names visible dalam cron system — health data exposure risk?

Files to check:
- ~/.hermes/.env (var names ONLY — jangan baca values)
- ~/.hermes/config.yaml
- ~/.hermes/auth.json
- ~/.hermes/cron/jobs.json
- ~/.hermes/scripts/*.py (grep untuk tokens, API keys)
- AGENTS.md (git commit policy — adequate?)

====================================================================
## DIMENSI 2: CONFIG & MODELS ⚙️
====================================================================

Check:
1. Fallback providers — config.yaml ada fallback_providers: [] (kosong). Risiko?
2. Default model = deepseek-v4-pro (mahal) — patut tukar ke flash, pro untuk hard tasks?
3. Model override system (fix_models.py) — fragile lepas hermes update?
4. Cost efficiency — berapa monthly? Ada cara optimize?
5. Prompt caching — enabled? TTL sesuai?
6. Reasoning effort xhigh — selalu guna? Boleh turunkan untuk tasks ringkas?

Files to check:
- config.yaml
- ~/.hermes/scripts/fix_models.py
- ~/.hermes/scripts/billing.py

====================================================================
## DIMENSI 3: SCRIPTS — Kualiti & Keselamatan 📜
====================================================================

Check:
- Ada hardcoded paths? (contoh: /mnt/f/... — Windows path kat Linux)
- Ada security issues? (eval(), exec(), shell injection risk?)
- Error handling adequate?
- Ada script yang tak pernah guna / orphan?
- Cross-platform compatible? (Linux vs Windows paths)

Files to check:
- ~/.hermes/scripts/chain_monitor.sh
- ~/.hermes/scripts/chain_calc.py
- ~/.hermes/scripts/chain_llm.py
- ~/.hermes/scripts/med_confirm.py
- ~/.hermes/scripts/med_resolve.py
- ~/.hermes/scripts/med_report.py
- ~/.hermes/scripts/med_supply.py
- ~/.hermes/scripts/med_interact.py
- ~/.hermes/scripts/med_substitute.py
- ~/.hermes/scripts/taper_alert.py
- ~/.hermes/scripts/watchdog.sh
- ~/.hermes/scripts/hello_watch.py
- ~/.hermes/scripts/memory_watch.py
- ~/.hermes/scripts/health_check.py
- ~/.hermes/scripts/fix_models.py
- ~/.hermes/scripts/restart-gateway.sh
- ~/.hermes/scripts/restart_gateway.sh
- ~/.hermes/scripts/gw_restart.sh
- ~/.hermes/scripts/logrotate-run.sh
- ~/.hermes/scripts/check_ds_balance.sh

====================================================================
## DIMENSI 4: STATE FILES — Integriti & Format 📊
====================================================================

Check:
- med-status.json → format betul? Drug-level tracking correct? Ada data corruption?
- med-schedule.json → v1.3 drug_id per slot betul? Ada missing entries?
- chain-state.json → format konsisten dengan chain_calc.py?
- dexa_taper.json → phase transitions betul? TDS→BD→OD timing correct?
- gateway_state.json → stale-state bug (blocks restart)?
- appointments.json → format betul?
- med-supply.json → quantity tracking accurate?

Files to check:
- ~/.hermes/med-status.json
- ~/.hermes/med-schedule.json
- ~/.hermes/chain-state.json
- ~/.hermes/dexa_taper.json
- ~/.hermes/med-supply.json
- ~/.hermes/gateway_state.json
- ~/.hermes/appointments.json

====================================================================
## DIMENSI 5: DOCUMENTATION 📝
====================================================================

Check:
- PROGRESS.md → up to date? Phase 23 last, banyak lagi tak direkod?
- DECISIONS.md → all key decisions recorded?
- AUDIT.md → reflects current state?
- README.md → accurate?
- RUNBOOK.md → operational docs adequate?
- AGENTS.md → safety rules comprehensive?
- persona/SOUL.md (61 lines .md in git) vs live SOUL.md (132 lines) → sync gap!
- Mana-mana doc yang outdated / conflicting?

Files to check:
- mjay/PROGRESS.md
- mjay/DECISIONS.md
- mjay/AUDIT.md
- mjay/README.md
- mjay/RUNBOOK.md
- mjay/AGENTS.md
- mjay/persona/SOUL.md
- ~/.hermes/SOUL.md
- drive-download-20260707T151046Z-3-001/01-VPS-BASELINE.md
- drive-download-20260707T151046Z-3-001/02-SYNC-GAP-ANALYSIS.md

====================================================================
## DIMENSI 6: BACKUP & RECOVERY 💾
====================================================================

Check:
- Ada automated backup? or only manual?
- Single point of failure? (VPS je, takde DR)
- Berapa lama nak recover kalau VPS mati?
- Ada offsite backup? (GitHub? WSL2?)
- State files backup? (med-status.json, etc.)
- Cron job definitions backup?

====================================================================
## DIMENSI 7: COST 💰
====================================================================

Check:
- OpenCode Go: $10/month? Justified?
- OpenCode Zen: free — adequate?
- NVIDIA: free — used?
- DeepSeek: CNY balance ~RM2-3/month
- Total monthly: berapa?
- Default model deepseek-v4-pro vs flash — cost difference?
- hello-world-watch every 1 min — wastes tokens/cpu?

Files to check:
- ~/.hermes/scripts/billing.py
- config.yaml model section

====================================================================
## DIMENSI 8: CROSS-PLATFORM SYNC 🔄
====================================================================

Check:
- VPS (Singapore) vs WSL2/Windows vs GitHub — semua sync?
- SOUL.md live (132 lines) vs git (61 lines) — DRIFT!
- Scripts version: VPS punya latest? WSL2 punya tertinggal?
- Cron jobs: VPS ada 14, WSL2 maybe berbeza?
- med-status.json: VPS punya current? WSL2 punya outdated?
- Git branches: hermes-live vs main — divergence?

Files to check:
- 02-SYNC-GAP-ANALYSIS.md (framework provided)
- Git log on VPS vs GitHub

====================================================================
## OUTPUT FORMAT

RESPOND STRICTLY IN THIS FORMAT:

```
## EXECUTIVE SUMMARY (2-3 paragraphs)
Overall health score (cumulative with first audit): __/10
Coverage: 8/8 missing dimensions now audited
Biggest risk found: ...
Biggest strength: ...

## FINDINGS BY DIMENSION

### Dimension 1: Security
Score: _/10

| # | Finding | Severity | Evidence | Fix Recommendation |
|---|---------|----------|----------|-------------------|
| 1 | ... | CRITICAL/HIGH/MEDIUM/LOW | (actual file line, quote) | ... |
| 2 | ... | ... | ... | ... |

### Dimension 2: Config & Models
Score: _/10
...

... (repeat for all 8 dimensions)

## QUICK WINS (< 30 min each)
- [ ] Finding X: ...
- [ ] Finding Y: ...

## CRITICAL FINDINGS (must fix today)
- ...

## BOTTOM LINE
Most urgent: ...
Most impactful: ...
```

## METHODOLOGY RULES

1. **EVIDENCE-FIRST** — Never say "verified" without showing the evidence.
2. **Single source = flagged** — If a finding comes from only 1 source, say so.
3. **Refuse to guess** — If you can't verify, say "could not verify because [reason]".
4. **Default to downgrading confidence** — Assume things are broken until proven working.
5. **For each finding: EVIDENCE → SEVERITY → FIX → TIME ESTIMATE**

## FILES ACCESS

Prep files: `F:\AI Prep\OVIS\Hermes Agent\drive-download-20260707T151046Z-3-001\`
VPS snapshot: `C:\Users\amiru\hermes-snapshot-20260707\`

If you need live VPS access for verification, use:
```
rsync -avz -e 'ssh -i /tmp/id_ed25519 -o StrictHostKeyChecking=accept-new' ubuntu@119.28.119.151:~/.hermes/ /mnt/c/Users/amiru/hermes-snapshot-20260707/
```

---

**MULAI. Baca semua fail yang relevan, then audit secara sistematik.**
```

## TAMAT COPY 👆
