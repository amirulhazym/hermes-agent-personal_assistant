# Login capture + the token-loss incident (2026-11-15)

Owner: Malaysia HUAWEI ID, Watch Fit 4 Pro (HarmonyOS 6.1.0.117 SP20C00M05patch01),
Honor 600 Pro 5G (MagicOS 11.0). Client: `and7ey/huawei_health` v1.0.8 vendored.

## Attempt log

| Time (MYT) | Setup | Outcome |
|---|---|---|
| 16:44 | phone, desktop mode, HMS Core installed | page renders, blue `Allow` unresponsive, no error |
| 16:54 | 3 URL variants (`display=touch` / `page` / none), HMS Core + AppGallery uninstalled | same dead button |
| 16:54 | retry | reached gateway, then `hms://redirect_url?sub_error=20132&error_description=invalid+ticket&error=1201&state=…` |
| 17:05 | fresh incognito, single URL, fast | real `code` (364 chars) captured |
| 17:05 | exchange | **server-side success**, helper crashed at `tokens.as_dict()` → tokens lost |
| 17:07 | repeat | exchange + storage OK |

## What each failure actually meant

- Dead `Allow` on a phone in "desktop mode": the consent page is `display=touch`; it binds touch events.
  Desktop rendering shows a button that no click reaches. Fix = native mobile Chrome, or desktop DevTools
  device emulation **and a reload after enabling it** (a page opened before toggling stays desktop-bound).
- `error=1201 / sub_error=20132 invalid ticket`: the CAS `ticket=` in the `loginCallback` URL had gone stale
  because the same auth URL was opened several times over ~15 minutes. The fix is not a parameter change —
  a fresh URL, a fresh incognito session, one attempt, completed inside ~2 minutes.
- Console CSP lines (`script-src 'none'`, `jsAnalysis.js`, `simulator.js` sandbox warnings) are Huawei's own
  blocked inline scripts. They appear on **every** load, including the successful one. Ignore them.

## The token-loss trap, precisely

```
code_len=364
Traceback (most recent call last):
  File "exchange_code.py", line 55, in main
    data = tokens.as_dict()
TypeError: 'dict' object is not callable
```

The exchange had already consumed the single-use code. Nothing was persisted, so the whole login had to be
repeated with a new URL. Root cause: `Tokens.as_dict` is declared with `@property`.

Order of operations that prevents it:

1. Write the helper.
2. Run it against a **fake** `Tokens` with `SECRETS` pointed at `/tmp` (`SMOKE_TEST_PASS`, mode 600, 195 bytes).
3. Only then spend a live code.

## Successful capture line (shape)

```
Failed to launch 'hms://redirect_url?code=EQEE…%3D%3D&state=c3f9a15e' because the scheme does not have a registered handler.
```

`authorization_code_from()` accepts the whole line and URL-unquotes the code itself — do not pre-decode.

## Post-exchange facts worth keeping

- `session_host` came back as the **added** Asia host `healthcommon-dra.things.dbankcloud.com`; the client
  then read from `sportdata-dra...` with `resultCode 0`.
- Token file: 624 bytes, mode 600, keys `access_token, expires_at, refresh_expires_at, refresh_token,
  session_host, site_id, uid`; `access_expires_in_s ≈ 3569` (~59 min), refresh TTL 15552000 s (180 d).
- `bind_devices()` returned the phone (`HONOR 600 Pro`, `VKP-NX9`) and the watch (`productId 822`,
  `uniqueId 4SPBB26713101822#ANDROID2…`).
