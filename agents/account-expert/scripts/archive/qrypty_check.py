#!/usr/bin/env python3
"""Log into QRYPTY inbox via browser (through proxy) and read latest email."""
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import time, sys

PROXY = "socks5://127.0.0.1:1080"
EMAIL = "owner@example.invalid"
ACCESS_CODE = "Q2aunE6zYoHupEAeLbQBX46g47w2kpHJ"
QRYPTY_URL = "https://qrypty.com"

def log(*a):
    print(f"[*] {' '.join(str(x) for x in a)}", flush=True)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            proxy={"server": PROXY},
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
        )
        page = context.new_page()
        Stealth().apply_stealth_sync(page)

        log(f"Navigating to {QRYPTY_URL}")
        page.goto(QRYPTY_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)
        page.screenshot(path="/tmp/qrypty_home.png")
        log("Home screenshot saved")

        # Look for login/inbox link
        links = page.locator("a").all()
        for link in links:
            try:
                text = link.inner_text()
                href = link.get_attribute("href")
                if text and ("inbox" in text.lower() or "login" in text.lower() or "sign" in text.lower()):
                    log(f"Link: {text} -> {href}")
            except:
                pass

        browser.close()

if __name__ == "__main__":
    main()
