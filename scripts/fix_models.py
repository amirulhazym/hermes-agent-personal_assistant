#!/usr/bin/env python3
"""fix_models.py — Re-apply custom model list overrides after hermes update.

Replaces the fragile fix-models.sh (which had a SyntaxError in its heredoc
and silently did nothing). This script is standalone Python, ast-validated,
idempotent, and covers MoA removal + Gemini removal + curated model lists
+ skip-live-fetch + inventory.py MoA gate.

Usage:
    python3 fix_models.py            # apply all overrides
    python3 fix_models.py --dry-run  # show what would change, write nothing
    python3 fix_models.py --verify   # exit 0 if all applied, exit 1 if not

Run this after `hermes update` if models revert to upstream defaults.
Restart the gateway after applying: pkill -f 'venv/bin/hermes' && hermes gateway &
"""

import argparse
import ast
import os
import re
import shutil
import sys
from pathlib import Path

HERMES_HOME = Path(os.path.expanduser("~/.hermes"))
AGENT_ROOT = HERMES_HOME / "hermes-agent"
MODELS_FILE = AGENT_ROOT / "hermes_cli" / "models.py"
AUTH_FILE = AGENT_ROOT / "hermes_cli" / "auth.py"
MDEV_FILE = AGENT_ROOT / "agent" / "models_dev.py"
INVENTORY_FILE = AGENT_ROOT / "hermes_cli" / "inventory.py"
PLUGIN_DIR = AGENT_ROOT / "plugins" / "model-providers" / "gemini"
DISABLED_PLUGIN_DIR = AGENT_ROOT / "plugins" / "model-providers" / "_gemini"

NVIDIA_MODELS = [
    "minimaxai/minimax-m3",
    "moonshotai/kimi-k2.6",
    "deepseek-ai/deepseek-v4-flash",
    "deepseek-ai/deepseek-v4-pro",
    "z-ai/glm-5.1",
]

ZEN_MODELS = [
    "deepseek-v4-flash-free",
    "minimax-m3-free",
    "mimo-v2.5-free",
    "qwen3.6-plus-free",
    "nemotron-3-ultra-free",
    "north-mini-code-free",
]

GO_MODELS = [
    "deepseek-v4-flash",
    "deepseek-v4-pro",
    "glm-5.2",
    "glm-5.1",
    "kimi-k2.7-code",
    "kimi-k2.6",
    "mimo-v2.5",
    "mimo-v2.5-pro",
    "minimax-m3",
    "minimax-m2.7",
    "qwen3.7-max",
    "qwen3.7-plus",
    "qwen3.6-plus",
]

CHANGES = []


def log(msg):
    CHANGES.append(msg)
    print(msg)


def _models_block(key, models, comment):
    lines = [f'    "{key}": [']
    if comment:
        lines.append(f"        # {comment}")
    for m in models:
        lines.append(f'        "{m}",')
    lines.append("    ],")
    return "\n".join(lines)


def replace_models_list(content, key, models, comment):
    pattern = re.compile(
        r'    "' + re.escape(key) + r'": \[\s*(?:#[^\n]*\n\s*)?(?:[^\]]*?)\],',
        re.S,
    )
    replacement = _models_block(key, models, comment)
    new_content, count = pattern.subn(replacement, content, count=1)
    if count == 0:
        log(f"  WARNING: could not find '{key}' model list to replace")
        return content
    log(f"  Replaced _PROVIDER_MODELS['{key}'] → {len(models)} models")
    return new_content


def remove_line_matching(content, pattern):
    new_lines = []
    removed = 0
    for line in content.splitlines(True):
        if re.search(pattern, line):
            removed += 1
            continue
        new_lines.append(line)
    if removed:
        log(f"  Removed {removed} line(s) matching /{pattern}/")
    return "".join(new_lines), removed


def remove_provider_entry(content, key):
    """Remove a single-line `ProviderEntry("key", ...)` from CANONICAL_PROVIDERS.

    Uses a full-line match so parentheses inside the human-readable description
    (e.g. "Google AI Studio (Native Gemini API)") do not break the match.
    """
    pattern = re.compile(
        r'^    ProviderEntry\("' + re.escape(key) + r'".*\n', re.M
    )
    new_content, count = pattern.subn("", content)
    if count:
        log(f"  Removed ProviderEntry('{key}') from CANONICAL_PROVIDERS ({count})")
    else:
        log(f"  ProviderEntry('{key}') already absent")
    return new_content


def remove_gemini_from_canonical(content):
    return remove_provider_entry(content, "gemini")


def remove_moa_from_canonical(content):
    return remove_provider_entry(content, "moa")


def remove_gemini_alias(content):
    pattern = r'    "google":\s*"gemini",\n'
    new_content, count = re.subn(pattern, "", content)
    if count:
        log(f"  Removed 'google' → 'gemini' alias ({count})")
    else:
        log("  'google' → 'gemini' alias already absent")
    return new_content


def remove_gemini_provider_models(content):
    pattern = re.compile(r'    "gemini": \[\s*(?:[^\]]*?)\],\n', re.S)
    new_content, count = pattern.subn("", content, count=1)
    if count:
        log(f"  Removed _PROVIDER_MODELS['gemini'] ({count})")
    else:
        log("  _PROVIDER_MODELS['gemini'] already absent")
    return new_content


def ensure_skip_live_fetch(content, provider, comment):
    guard = f'    if normalized == "{provider}":'
    if guard in content:
        log(f"  skip-live-fetch for '{provider}' already present")
        return content

    anchor = '    if normalized == "openrouter":\n        return model_ids(force_refresh=force_refresh)'
    if anchor not in content:
        log(f"  WARNING: could not find anchor to insert skip-live-fetch for '{provider}'")
        return content

    insertion = (
        f'    if normalized == "{provider}":\n'
        f"        # {comment}\n"
        f'        return list(_PROVIDER_MODELS.get("{provider}", []))\n'
    )
    new_content = content.replace(anchor, insertion + anchor, 1)
    log(f"  Added skip-live-fetch for '{provider}'")
    return new_content


def patch_models_file(dry_run):
    log("[1/5] Patching hermes_cli/models.py ...")
    if not MODELS_FILE.exists():
        log(f"  ERROR: {MODELS_FILE} not found")
        return False
    content = MODELS_FILE.read_text()

    content = replace_models_list(
        content, "nvidia", NVIDIA_MODELS,
        "Custom list — only models the user actually uses (MJ override 2026-06-27)",
    )
    content = replace_models_list(
        content, "opencode-zen", ZEN_MODELS,
        "Free models only — no billing needed (MJ override 2026-06-27)",
    )
    content = replace_models_list(
        content, "opencode-go", GO_MODELS,
        "OpenCode Go subscription models (MJ override 2026-06-28)",
    )
    content = ensure_skip_live_fetch(
        content, "nvidia",
        "Custom override — only curated models, skip live API (MJ override 2026-06-27)",
    )
    content = ensure_skip_live_fetch(
        content, "opencode-go",
        "Custom override - skip live API, use curated list (MJ override 2026-06-28)",
    )
    content = ensure_skip_live_fetch(
        content, "opencode-zen",
        "Custom override — only free models, skip live API (MJ override 2026-06-27)",
    )

    try:
        ast.parse(content)
    except SyntaxError as e:
        log(f"  ERROR: patched models.py has syntax error: {e}")
        return False

    if not dry_run:
        MODELS_FILE.write_text(content)
        log(f"  Written: {MODELS_FILE}")
    else:
        log("  (dry-run: not writing)")
    return True


def patch_inventory_file(dry_run):
    log("[2/5] Patching hermes_cli/inventory.py (_moa_provider_row gate) ...")
    if not INVENTORY_FILE.exists():
        log(f"  ERROR: {INVENTORY_FILE} not found")
        return False
    content = INVENTORY_FILE.read_text()

    old_block = (
        '        cfg = normalize_moa_config(load_config().get("moa") or {})\n'
        '        models = list(cfg.get("presets", {}).keys())\n'
        '        if not models:\n'
        '            return None'
    )
    new_block = (
        '        from hermes_cli.config import read_raw_config\n'
        '        if not read_raw_config().get("moa"):\n'
        '            return None\n'
        '        cfg = normalize_moa_config(load_config().get("moa") or {})\n'
        '        models = list(cfg.get("presets", {}).keys())\n'
        '        if not models:\n'
        '            return None'
    )

    if old_block in content:
        content = content.replace(old_block, new_block, 1)
        log("  Patched _moa_provider_row: gate on read_raw_config before normalize_moa_config")
    elif "read_raw_config().get(\"moa\")" in content:
        log("  _moa_provider_row gate already applied")
    else:
        log("  WARNING: could not find _moa_provider_row block to patch — manual review needed")
        return True

    try:
        ast.parse(content)
    except SyntaxError as e:
        log(f"  ERROR: patched inventory.py has syntax error: {e}")
        return False

    if not dry_run:
        INVENTORY_FILE.write_text(content)
        log(f"  Written: {INVENTORY_FILE}")
    else:
        log("  (dry-run: not writing)")
    return True


def patch_auth_file(dry_run):
    log("[3/5] Patching hermes_cli/auth.py (remove Gemini ProviderConfig) ...")
    if not AUTH_FILE.exists():
        log(f"  ERROR: {AUTH_FILE} not found")
        return False
    content = AUTH_FILE.read_text()

    content, _ = remove_line_matching(
        content, r'    "gemini":\s*ProviderConfig\('
    )
    content, _ = remove_line_matching(
        content, r'        "google":\s*"gemini"'
    )
    content, _ = remove_line_matching(
        content, r'        "google-gemini":\s*"gemini"'
    )
    content, _ = remove_line_matching(
        content, r'        "google-ai-studio":\s*"gemini"'
    )

    try:
        ast.parse(content)
    except SyntaxError as e:
        log(f"  ERROR: patched auth.py has syntax error: {e}")
        return False

    if not dry_run:
        AUTH_FILE.write_text(content)
        log(f"  Written: {AUTH_FILE}")
    else:
        log("  (dry-run: not writing)")
    return True


def patch_models_dev_file(dry_run):
    log("[4/5] Patching agent/models_dev.py (remove Gemini mapping) ...")
    if not MDEV_FILE.exists():
        log(f"  ERROR: {MDEV_FILE} not found")
        return False
    content = MDEV_FILE.read_text()

    content, _ = remove_line_matching(content, r'"gemini":\s*"google"')
    content, _ = remove_line_matching(content, r'"google":\s*"google"')

    try:
        ast.parse(content)
    except SyntaxError as e:
        log(f"  ERROR: patched models_dev.py has syntax error: {e}")
        return False

    if not dry_run:
        MDEV_FILE.write_text(content)
        log(f"  Written: {MDEV_FILE}")
    else:
        log("  (dry-run: not writing)")
    return True


def disable_gemini_plugin(dry_run):
    log("[5/5] Disabling Gemini plugin dir ...")
    if PLUGIN_DIR.is_dir() and not DISABLED_PLUGIN_DIR.is_dir():
        if not dry_run:
            shutil.move(str(PLUGIN_DIR), str(DISABLED_PLUGIN_DIR))
            log(f"  Renamed: {PLUGIN_DIR.name} → {DISABLED_PLUGIN_DIR.name}")
        else:
            log("  (dry-run: would rename gemini/ → _gemini/)")
    elif DISABLED_PLUGIN_DIR.is_dir():
        log("  Gemini plugin already disabled (_gemini/ exists)")
    else:
        log("  Gemini plugin not found (already removed)")


def verify():
    """Check that all overrides are currently applied. Exit 0 if yes, 1 if not."""
    log("VERIFY MODE: checking all overrides are applied ...")
    all_ok = True

    if not MODELS_FILE.exists():
        print(f"FAIL: {MODELS_FILE} not found")
        return False
    content = MODELS_FILE.read_text()

    for key, expected in [("nvidia", NVIDIA_MODELS), ("opencode-zen", ZEN_MODELS), ("opencode-go", GO_MODELS)]:
        m = re.search(r'"' + key + r'": \[(.*?)\]', content, re.S)
        if not m:
            print(f"FAIL: _PROVIDER_MODELS['{key}'] not found")
            all_ok = False
            continue
        found = [re.search(r'"([^"]+)"', x).group(1) for x in m.group(1).splitlines() if '"' in x and not x.strip().startswith("#")]
        if found != expected:
            print(f"FAIL: _PROVIDER_MODELS['{key}'] mismatch — found {found[:3]}..., expected {expected[:3]}...")
            all_ok = False
        else:
            print(f"OK:   _PROVIDER_MODELS['{key}'] ({len(found)} models)")

    if 'ProviderEntry("gemini"' in content:
        print("NOTE: ProviderEntry('gemini') present (upstream default — hands-off)")
    else:
        print("NOTE: ProviderEntry('gemini') already absent")

    if 'ProviderEntry("moa"' in content:
        print("NOTE: ProviderEntry('moa') present (upstream default — hands-off)")
    else:
        print("NOTE: ProviderEntry('moa') already absent")

    # Google → gemini alias — FYI only, not a failure
    if '"google": "gemini"' in content:
        print("NOTE: 'google' → 'gemini' alias present (upstream default)")
    else:
        print("NOTE: 'google' → 'gemini' alias absent")

    for p in ["nvidia", "opencode-go", "opencode-zen"]:
        if f'if normalized == "{p}"' not in content:
            print(f"FAIL: skip-live-fetch for '{p}' missing")
            all_ok = False
        else:
            print(f"OK:   skip-live-fetch for '{p}' present")

    inv_content = INVENTORY_FILE.read_text() if INVENTORY_FILE.exists() else ""
    if 'read_raw_config().get("moa")' in inv_content:
        print("OK:   inventory.py _moa_provider_row gate present")
    else:
        print("FAIL: inventory.py _moa_provider_row gate missing")
        all_ok = False

    if DISABLED_PLUGIN_DIR.is_dir():
        print("OK:   Gemini plugin disabled (_gemini/ exists)")
    elif PLUGIN_DIR.is_dir():
        print("NOTE: Gemini plugin dir present (upstream default — hands-off)")
    else:
        print("NOTE: Gemini plugin not found")

    if all_ok:
        print("\nAll overrides verified ✓")
    else:
        print("\nSome overrides missing — run fix_models.py to re-apply")
    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Re-apply Hermes model overrides after hermes update")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    parser.add_argument("--verify", action="store_true", help="Check all overrides are applied, exit 0/1")
    args = parser.parse_args()

    if args.verify:
        ok = verify()
        sys.exit(0 if ok else 1)

    print(f"{'DRY RUN — ' if args.dry_run else ''}Applying model overrides to {AGENT_ROOT}\n")

    ok = True
    ok = patch_models_file(args.dry_run) and ok
    print()
    ok = patch_inventory_file(args.dry_run) and ok
    print()
    # Skipped: patch_auth_file, patch_models_dev_file, disable_gemini_plugin
    # — gemini/moa removal is a destructive upstream patch, not our custom setup.
    # The user explicitly instructed: default Hermes code = hands-off.
    # MoA is gated in inventory.py (above); Gemini is inert without an API key.
    # Log the skip but don't count it as failure
    log("[3-5/5] Skipped: gemini/moa ProviderConfig/ProviderEntry removal + plugin rename (upstream code — hands-off)")

    print(f"\n{'DRY RUN' if args.dry_run else 'DONE'} — {len(CHANGES)} actions")
    if not args.dry_run and ok:
        print("\nRestart gateway: pkill -f 'venv/bin/hermes' && hermes gateway &")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
