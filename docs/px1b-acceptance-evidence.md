# PX-1b Acceptance Evidence

> Date: 2026-07-17  
> Branch: `overhaul/exec`  
> Host: VPS `ubuntu@119.28.119.151` Hermes v0.17.0  
> Suite artifact (VPS): `~/.hermes/web-operator/acceptance-latest.json`  
> Manual live markers: `~/.hermes/web-operator/acceptance-manual.json`

## Final scoreboard — **20/20 PASS**

| Case | Name | Status | Evidence |
|---:|---|---|---|
| 1 | research_l2_live | **PASS** | Live L2 search via wired tools |
| 2 | whatsapp_triggers_web_operator | **PASS** | Live WA: click through example.com → Example Domain |
| 3 | telegram_triggers_web_operator | **PASS** | Live TG `/browse` + `/web-operator` → L3 Example Domain VALIDATED |
| 4 | public_static_l1 | **PASS** | Live HTTP GET example.com |
| 5 | public_l3_browse | **PASS** | Live native browser navigate+snapshot |
| 6 | l2_l3_escalation_logged | **PASS** | Escalate event in artifacts |
| 7 | network_fail_closed | **PASS** | Private/metadata/file/js blocked |
| 8 | budget_action_limit | **PASS** | RunBudget hard stop |
| 9 | approvals_single_use_mutation | **PASS** | Single-use + digest mutation |
| 10 | form_double_approval | **PASS** | Type + submit both require approval |
| 11 | external_send_approval | **PASS** | EXTERNAL_SEND pauses |
| 12 | file_transfer_approval | **PASS** | Quarantine + dual approval classes |
| 13 | takeover_observation_suspend | **PASS** | Observation gate blocks emit |
| 14 | financial_secrets_phone_only | **PASS** | Password intent → private takeover pause |
| 15 | medical_artifact_isolation | **PASS** | Medical audit metadata only |
| 16 | medical_portal_isolated | **PASS** | No med automation state touchpoints |
| 17 | captcha_l5_handoff | **PASS** | Bypass/farming not auto-allowed |
| 18 | pc_grants_failclosed | **PASS** | Sign/verify + expiry/device/offline fail-closed |
| 19 | named_app_cua_success | **PASS** | Enrolled `pc-7633a84681a0`; signed grant; Notepad launch via cua-driver |
| 20 | phone_first_vps_pc_workflow | **PASS** | L3 VPS + L4 PC + offline postpone + wrong-app fail-closed |

### Counts (clean RC)

- **PASS: 20**
- **FAIL: 0**
- **PARTIAL: 0**
- **PENDING: 0**

## L4 bridge architecture (implemented)

- **Transport:** outbound-only SSH/SCP mailbox (`~/.hermes/web-operator/bridge/{inbox,outbox,status,devices,keys,consumed}`)
- **No inbound PC ports** (no public CUA/VNC/CDP)
- **VPS:** `BridgeControlPlane` issues Ed25519 signed grants
- **PC:** `PcWorkerRuntime` + `windows/web-operator-worker.ps1` polls, verifies, executes grant-scoped `cua-driver` actions only
- **Fail-closed:** unknown app, replay nonce, offline → postpone, privilege actions denied

## Live wiring (L1–L3)

| Check | Result |
|---|---|
| Browser/search/extract wired | true |
| L1/L2/L3 smokes | VALIDATED |
| Gateway TG+WA | connected after restarts |
| `computer_use.enabled` | false (project bridge is separate; Hermes MCP CUA not claimed) |
| L3 concurrency | 1 |

## Operator commands

### VPS
```bash
export PYTHONPATH=$HOME/.hermes HERMES_AGENT_ROOT=$HOME/.hermes/hermes-agent
CFG=$HOME/.hermes/web-operator/config.yaml
python -m scripts.web_operator bridge-status --config $CFG
python -m scripts.web_operator run-live --config $CFG \
  --text "open notepad named app via computer use"
python -m scripts.web_operator.acceptance_suite --config $CFG \
  --out $HOME/.hermes/web-operator/acceptance-latest.json
```

### PC
```powershell
pwsh -File windows/web-operator-worker.ps1 -Action Enroll
pwsh -File windows/web-operator-worker.ps1 -Action Run -Seconds 300
# Optional persistent logon worker (register once; do not run during static tests)
pwsh -File windows/web-operator-worker-autostart.ps1 -Action Install
```

## Telegram fix note

`/browse` was unknown slash command → fixed with `quick_commands.browse` alias → `web-operator`.
