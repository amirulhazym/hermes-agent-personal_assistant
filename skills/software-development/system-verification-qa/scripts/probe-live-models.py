#!/usr/bin/env python3
"""
Live model probe: verify curated models against live API for a provider.
Usage:
    python3 scripts/probe-live-models.py [provider-slug]
    python3 scripts/probe-live-models.py opencode-zen
    python3 scripts/probe-live-models.py opencode-go

If no provider given, probes all from provider_models_cache.
"""
import os, sys, json, requests, time

# Provider -> (env_var, base_url)
PROVIDERS = {
    "opencode-zen": ("OPENCODE_ZEN_API_KEY", "https://opencode.ai/zen/v1"),
    "opencode-go": ("OPENCODE_GO_API_KEY", "https://opencode.ai/zen/go/v1"),
    "deepseek": ("DEEPSEEK_API_KEY", "https://api.deepseek.com/v1"),
}

def probe_model(api_key, base_url, model):
    """Returns (status_code, error_str)."""
    try:
        r = requests.post(f'{base_url}/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={"model": model, "messages": [{"role": "user", "content": "hi"}],
                  "max_tokens": 3},
            timeout=15)
        if r.status_code == 200:
            return (200, "")
        return (r.status_code, r.json().get('error', {}).get('message', '')[:80])
    except Exception as e:
        return (0, str(e)[:80])

def main():
    # Import Hermes curated list
    sys.path.insert(0, os.path.expanduser('~/.hermes/hermes-agent'))
    try:
        from hermes_cli.models import _PROVIDER_MODELS
    except ImportError:
        _PROVIDER_MODELS = {}

    targets = sys.argv[1:] if len(sys.argv) > 1 else list(PROVIDERS.keys())

    for slug in targets:
        if slug not in PROVIDERS:
            print(f"\n❌ Unknown provider '{slug}'. Known: {list(PROVIDERS.keys())}")
            continue

        env_var, base_url = PROVIDERS[slug]
        api_key = os.getenv(env_var, "")
        if not api_key:
            print(f"\n⚠️  {slug}: {env_var} not set — skipping")
            continue

        # Get curated models
        curated = _PROVIDER_MODELS.get(slug, [])
        if not curated:
            # Try live fetch
            try:
                r = requests.get(f'{base_url}/models',
                    headers={'Authorization': f'Bearer {api_key}'}, timeout=10)
                if r.status_code == 200:
                    live = r.json().get('data', [])
                    curated = sorted([m['id'] if isinstance(m, dict) else m for m in live])
                else:
                    print(f"\n⚠️  {slug}: no curated list, live probe failed ({r.status_code})")
                    continue
            except Exception as e:
                print(f"\n⚠️  {slug}: no curated list, live probe error: {e}")
                continue

        print(f"\n{'='*60}")
        print(f"Probing {slug} ({len(curated)} models)")
        print(f"Endpoint: {base_url}")
        print(f"{'='*60}")

        working = []
        dead = []
        for m in curated:
            status, err = probe_model(api_key, base_url, m)
            time.sleep(0.3)  # rate limit
            if status == 200:
                working.append(m)
                print(f"  ✅ {m}")
            else:
                dead.append((m, status, err))
                print(f"  ❌ {m}: {status} {err[:60]}")

        print(f"\n  Working: {len(working)}/{len(curated)}")
        if dead:
            print(f"  DEAD ({len(dead)}):")
            for m, s, e in dead:
                print(f"    - {m}: HTTP {s} {e[:60]}")

if __name__ == '__main__':
    main()
