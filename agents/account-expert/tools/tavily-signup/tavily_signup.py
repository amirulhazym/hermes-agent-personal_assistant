#!/usr/bin/env python3
"""Semi-automated Tavily signup helper for local Windows use.

Human handles Turnstile and QRYPTY email verification. The script never prints
passwords, access codes, or raw Tavily API keys.
"""

from __future__ import annotations

import argparse
import csv
import getpass
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


PACKAGE_DIR = Path(__file__).resolve().parent
CSV_PATH = PACKAGE_DIR / "accounts" / "tavily_remaining_7_accounts.csv"
OUTPUT_PATH = PACKAGE_DIR / "tavily_keys.json"
TAVILY_SIGNUP_URL = "https://app.tavily.com/home"
QRYPTY_WEB_URL = "https://qrypty.com"
TARGET_EMAILS = [
    "owner@example.invalid",
    "owner@example.invalid",
    "owner@example.invalid",
    "owner@example.invalid",
    "owner@example.invalid",
    "owner@example.invalid",
    "owner@example.invalid",
]
KEY_RE = re.compile(r"^tvly-[A-Za-z0-9_-]{20,}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def chmod_owner_only(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError:
        pass


def key_fingerprint(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]


def validate_tavily_key(value: str) -> str:
    key = (value or "").strip()
    if not KEY_RE.match(key):
        raise ValueError("Invalid Tavily key format")
    return key


def load_accounts() -> List[Dict[str, Any]]:
    accounts: List[Dict[str, Any]] = []
    with CSV_PATH.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"No", "Email", "Password", "Access Code", "Nickname"}
        if set(reader.fieldnames or []) != required:
            missing = required - set(reader.fieldnames or [])
            extra = set(reader.fieldnames or []) - required
            raise ValueError(f"Unexpected CSV headers. missing={missing} extra={extra}")
        for row in reader:
            no = int(row["No"])
            accounts.append(
                {
                    "no": no,
                    "email": row["Email"].strip(),
                    "password": row["Password"].strip(),
                    "access_code": row["Access Code"].strip(),
                    "nickname": row["Nickname"].strip(),
                }
            )
    if [a["email"] for a in accounts] != TARGET_EMAILS:
        raise ValueError("Reduced CSV must contain exactly emails -05, -10, -11, -12, -13, -14, -15")
    return accounts


def empty_key_data() -> Dict[str, Any]:
    return {"keys": [], "failures": {}, "last_updated": None}


def load_existing_keys() -> Dict[str, Any]:
    if not OUTPUT_PATH.exists():
        return empty_key_data()
    with OUTPUT_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("keys", [])
    data.setdefault("failures", {})
    return data


def save_keys(data: Dict[str, Any]) -> None:
    data["last_updated"] = utc_now()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=OUTPUT_PATH.name + ".", suffix=".tmp", dir=OUTPUT_PATH.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        chmod_owner_only(tmp_path)
        os.replace(tmp_path, OUTPUT_PATH)
        chmod_owner_only(OUTPUT_PATH)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def completed_emails(keys_data: Dict[str, Any]) -> set[str]:
    return {str(k.get("email", "")) for k in keys_data.get("keys", [])}


def mark_completed(keys_data: Dict[str, Any], account_no: int, email: str, api_key: str) -> None:
    key = validate_tavily_key(api_key)
    keys = keys_data.setdefault("keys", [])
    existing = next((k for k in keys if k.get("email") == email), None)
    record = {
        "account_no": account_no,
        "email": email,
        "api_key_fingerprint": key_fingerprint(key),
        "api_key": key,
        "obtained_at": utc_now(),
        "validation_status": "valid_format",
    }
    if existing:
        existing.update(record)
    else:
        keys.append(record)
    keys_data.setdefault("failures", {}).pop(email, None)
    save_keys(keys_data)


def mark_failed(keys_data: Dict[str, Any], email: str, reason: str) -> None:
    keys_data.setdefault("failures", {})[email] = {"reason": reason[:160], "at": utc_now()}
    save_keys(keys_data)


def status_counts(accounts: List[Dict[str, Any]], keys_data: Dict[str, Any]) -> Dict[str, int]:
    done = completed_emails(keys_data)
    failed = set((keys_data.get("failures") or {}).keys()) - done
    total = len(accounts)
    completed = sum(1 for a in accounts if a["email"] in done)
    failed_count = sum(1 for a in accounts if a["email"] in failed)
    return {"total": total, "completed": completed, "pending": total - completed - failed_count, "failed": failed_count}


def print_status(accounts: List[Dict[str, Any]], keys_data: Dict[str, Any]) -> None:
    counts = status_counts(accounts, keys_data)
    print(f"total={counts['total']} completed={counts['completed']} pending={counts['pending']} failed={counts['failed']}")


def list_accounts(accounts: List[Dict[str, Any]], keys_data: Dict[str, Any]) -> None:
    done = completed_emails(keys_data)
    failed = set((keys_data.get("failures") or {}).keys()) - done
    print("\n=== ACCOUNT STATUS (no credentials shown) ===\n")
    for acc in accounts:
        if acc["email"] in done:
            status = "DONE"
        elif acc["email"] in failed:
            status = "FAILED"
        else:
            status = "PENDING"
        print(f"  #{acc['no']:02d} | {acc['email']:<35} | {acc['nickname']:<15} | {status}")
    print()
    print_status(accounts, keys_data)
    print(f"keys_file={OUTPUT_PATH}")


def select_accounts(
    accounts: List[Dict[str, Any]],
    keys_data: Dict[str, Any],
    *,
    email: Optional[str] = None,
    count: Optional[int] = None,
    include_failed: bool = True,
) -> List[Dict[str, Any]]:
    done = completed_emails(keys_data)
    selected = [a for a in accounts if a["email"] not in done]
    if not include_failed:
        failed = set((keys_data.get("failures") or {}).keys())
        selected = [a for a in selected if a["email"] not in failed]
    if email:
        selected = [a for a in selected if a["email"].lower() == email.lower()]
        if not selected and email in done:
            return []
        if not selected:
            raise ValueError(f"Email not found or already completed: {email}")
    if count is not None:
        selected = selected[: max(0, count)]
    return selected


def browser_channel_available(name: str) -> bool:
    # Prefer Playwright-managed browser channels for Chrome/Edge. Brave needs an executable path.
    if name in {"chrome", "msedge"}:
        return True
    if name == "brave":
        return find_brave_executable() is not None
    if name == "chromium":
        return True
    return False


def find_brave_executable() -> Optional[str]:
    candidates = []
    for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        base = os.environ.get(env)
        if base:
            candidates.append(Path(base) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe")
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return shutil.which("brave") or shutil.which("brave-browser")


def select_browser(requested: str, profile_root: Path) -> Dict[str, Any]:
    requested = (requested or "auto").lower().strip()
    order = ["chrome", "msedge", "brave", "chromium"] if requested == "auto" else [requested]
    for name in order:
        if name not in {"chrome", "msedge", "brave", "chromium"}:
            raise ValueError(f"Unsupported browser: {requested}")
        if browser_channel_available(name):
            profile_dir = profile_root / f"profile-{name}"
            profile_dir.mkdir(parents=True, exist_ok=True)
            return {"browser": name, "profile_dir": profile_dir}
    raise RuntimeError("No supported browser found (Chrome, Edge, Brave, or Playwright Chromium).")


def launch_context(playwright, browser_choice: Dict[str, Any]):
    name = browser_choice["browser"]
    profile_dir = str(browser_choice["profile_dir"])
    kwargs = {"headless": False, "viewport": {"width": 1280, "height": 850}}
    if name in {"chrome", "msedge"}:
        return playwright.chromium.launch_persistent_context(user_data_dir=profile_dir, channel=name, **kwargs)
    if name == "brave":
        exe = find_brave_executable()
        if not exe:
            raise RuntimeError("Brave executable not found")
        return playwright.chromium.launch_persistent_context(user_data_dir=profile_dir, executable_path=exe, **kwargs)
    return playwright.chromium.launch_persistent_context(user_data_dir=profile_dir, **kwargs)


def first_visible(page, selectors: Iterable[str], timeout: int = 1000):
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=timeout):
                return loc, sel
        except Exception:
            continue
    return None, ""


def captcha_ready(page) -> bool:
    try:
        token = page.locator("input[name='cf-turnstile-response'], textarea[name='cf-turnstile-response']").first
        value = token.input_value(timeout=1000)
        return bool(value.strip())
    except Exception:
        return True  # UI changes often; do not block the human-driven flow.


def extract_api_key(page) -> Optional[str]:
    candidates: List[str] = []
    try:
        candidates.extend(re.findall(r"tvly-[A-Za-z0-9_-]{20,}", page.content()))
    except Exception:
        pass
    try:
        inputs = page.locator("input")
        for i in range(inputs.count()):
            val = inputs.nth(i).input_value()
            if val and val.startswith("tvly-"):
                candidates.append(val)
    except Exception:
        pass
    for candidate in candidates:
        try:
            key = validate_tavily_key(candidate)
            print(f"  Found Tavily key fingerprint: {key_fingerprint(key)}")
            return key
        except ValueError:
            continue
    print("  API key not auto-detected. Manual paste fallback is hidden.")
    raw = getpass.getpass("  Paste API key (input hidden, or blank to skip): ")
    if not raw.strip():
        return None
    try:
        key = validate_tavily_key(raw)
        print(f"  Accepted Tavily key fingerprint: {key_fingerprint(key)}")
        return key
    except ValueError as exc:
        print(f"  Invalid key: {exc}")
        return None


def signup_single(page, account: Dict[str, Any]) -> Optional[str]:
    print("  [1/6] Opening Tavily signup/home page...")
    page.goto(TAVILY_SIGNUP_URL, wait_until="domcontentloaded", timeout=45000)
    time.sleep(2)

    try:
        signup_btn = page.get_by_text("Sign up").first
        if signup_btn.is_visible(timeout=3000):
            signup_btn.click()
            time.sleep(2)
            print("  [2/6] Opened signup form")
    except Exception:
        print("  [2/6] Signup form/page already available")

    print("  [3/6] Filling account email...")
    email_input, _ = first_visible(page, ["input[name='email']", "input#email", "input[type='email']"], timeout=3000)
    if email_input is None:
        raise RuntimeError("Email input not found")
    email_input.fill(account["email"])

    try:
        pwd_input, _ = first_visible(page, ["input[name='password']", "input[type='password']"], timeout=1500)
        if pwd_input is not None:
            pwd_input.fill(account["password"])
            print("  [4/6] Filled password field (value not shown)")
        else:
            print("  [4/6] Password field not currently shown")
    except Exception:
        print("  [4/6] Password field not currently shown")

    print("\n  Complete Turnstile in the headed browser, then return here.")
    input("  Press ENTER after Turnstile is complete... ")
    if not captcha_ready(page):
        raise RuntimeError("Captcha response not detected; try this account again")

    print("  [5/6] Submitting signup form...")
    submit, sel = first_visible(
        page,
        [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Sign up')",
            "button:has-text('Continue')",
            "button:has-text('Create')",
        ],
        timeout=1500,
    )
    if submit is not None:
        submit.click()
        print(f"  Submitted via selector: {sel}")
    else:
        page.keyboard.press("Enter")
        print("  Submitted via Enter key")
    time.sleep(4)

    print("\n  Email verification may be required.")
    print(f"  Open QRYPTY mailbox for: {account['email']}")
    print(f"  QRYPTY site: {QRYPTY_WEB_URL}")
    print("  Use the 32-character Access Code from the CSV/package, not chat.")
    input("  Press ENTER after clicking the Tavily verification link... ")

    print("  [6/6] Opening Tavily home/dashboard to capture key...")
    page.goto(TAVILY_SIGNUP_URL, wait_until="domcontentloaded", timeout=45000)
    time.sleep(3)
    return extract_api_key(page)


def run_signup(accounts: List[Dict[str, Any]], selected: List[Dict[str, Any]], keys_data: Dict[str, Any], browser: str) -> None:
    if not selected:
        print("No pending accounts selected.")
        return
    print(f"\nProcessing {len(selected)} account(s):")
    for acc in selected:
        print(f"  #{acc['no']:02d} — {acc['email']}")

    from playwright.sync_api import sync_playwright

    profile_root = PACKAGE_DIR / ".browser-profile"
    choice = select_browser(browser, profile_root)
    print(f"Selected browser: {choice['browser']}")
    print(f"Dedicated profile: {choice['profile_dir']}")

    with sync_playwright() as p:
        context = launch_context(p, choice)
        page = context.pages[0] if context.pages else context.new_page()
        try:
            for idx, acc in enumerate(selected, 1):
                print("\n" + "=" * 60)
                print(f"[{idx}/{len(selected)}] Account #{acc['no']:02d}: {acc['email']}")
                print("=" * 60)
                try:
                    api_key = signup_single(page, acc)
                    if api_key:
                        mark_completed(keys_data, acc["no"], acc["email"], api_key)
                        print(f"  SUCCESS — key stored for {acc['email']} (fingerprint only shown)")
                    else:
                        mark_failed(keys_data, acc["email"], "no valid key captured")
                        print(f"  PENDING/FAILED — no valid key stored for {acc['email']}")
                except Exception as exc:
                    mark_failed(keys_data, acc["email"], str(exc))
                    print(f"  ERROR for {acc['email']}: {exc}")
                    print("  Browser remains available; continue or retry later.")
                if idx < len(selected):
                    print("  Cooldown 10s before next account...")
                    time.sleep(10)
        finally:
            input("\nPress ENTER to close the automation browser... ")
            context.close()
    print_status(accounts, keys_data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Semi-automated Tavily API key signup (local headed browser)")
    parser.add_argument("--count", type=int, default=None, help="Number of pending accounts to process")
    parser.add_argument("--email", help="Process/retry one exact account email")
    parser.add_argument("--browser", default="auto", choices=["auto", "chrome", "msedge", "brave", "chromium"], help="Headed browser to use")
    parser.add_argument("--dry-run", action="store_true", help="Show selected accounts without signing up")
    parser.add_argument("--list", action="store_true", help="List accounts and statuses; no credentials")
    parser.add_argument("--status", action="store_true", help="Print only total/completed/pending/failed")
    args = parser.parse_args()

    accounts = load_accounts()
    keys_data = load_existing_keys()

    if args.status:
        print_status(accounts, keys_data)
        return
    if args.list:
        list_accounts(accounts, keys_data)
        return

    selected = select_accounts(accounts, keys_data, email=args.email, count=args.count)
    if args.dry_run:
        print(f"Would process {len(selected)} account(s):")
        for acc in selected:
            print(f"  #{acc['no']:02d} — {acc['email']} ({acc['nickname']})")
        return

    print("Tavily local signup helper")
    print("Secrets are not printed. Do not run this package inside sync folders or Git repos.")
    print_status(accounts, keys_data)
    confirm = input("Proceed with headed browser signup? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        return
    run_signup(accounts, selected, keys_data, args.browser)


if __name__ == "__main__":
    main()
