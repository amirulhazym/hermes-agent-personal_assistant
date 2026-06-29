"""Qwen LM driver — forwards a prompt to chat.qwenlm.ai via cua-driver MCP.

Mirrors sakana_driver.py. Drives Brave browser to https://chat.qwenlm.ai/,
types the prompt, waits for the response, and returns it as plain text.

Usage:
    python3 qwen_driver.py "your prompt here"

Requirements:
    - cua-driver MCP server running (gateway starts it automatically)
    - Brave browser running with a tab at chat.qwenlm.ai (or this will open it)
"""

import sys
import time

try:
    from hermes_tools import (
        mcp_cua_driver_list_apps,
        mcp_cua_driver_list_windows,
        mcp_cua_driver_page,
        mcp_cua_driver_type_text,
        mcp_cua_driver_click,
    )
except ImportError:
    print("ERROR: hermes_tools not available — run via Hermes gateway context")
    sys.exit(1)

QWEN_URL = "https://chat.qwenlm.ai/"
WAIT_NAVIGATE = 6
WAIT_RESPONSE = 20
WAIT_TYPE = 1.5


def run_qwen(prompt):
    if not prompt or not prompt.strip():
        print("ERROR: no prompt provided")
        print("Usage: python3 qwen_driver.py \"your prompt here\"")
        return

    apps = mcp_cua_driver_list_apps()
    brave = next((app for app in apps if "brave" in app.get("name", "").lower()), None)
    if not brave or not brave.get("running"):
        print("ERROR: Brave browser not running. Open Brave first.")
        return

    wins = mcp_cua_driver_list_windows(pid=brave["pid"])
    if not wins:
        print("ERROR: No Brave window found")
        return
    win = wins[0]

    mcp_cua_driver_page(
        action="execute_javascript",
        pid=brave["pid"],
        window_id=win["window_id"],
        javascript=f"window.location.href='{QWEN_URL}'",
    )
    time.sleep(WAIT_NAVIGATE)

    textarea_js = (
        "const el = document.querySelector('textarea') "
        "|| document.querySelector('[contenteditable=\"true\"]'); "
        "el ? el.id || 'found_no_id' : 'not_found'"
    )
    probe = mcp_cua_driver_page(
        action="execute_javascript",
        pid=brave["pid"],
        window_id=win["window_id"],
        javascript=textarea_js,
    )
    if "not_found" in str(probe).lower():
        print("ERROR: Qwen chat textarea not found. Page may not be loaded or logged in.")
        return

    mcp_cua_driver_type_text(
        pid=brave["pid"],
        window_id=win["window_id"],
        text=prompt,
    )
    time.sleep(WAIT_TYPE)

    submit_js = (
        "const btn = document.querySelector('button[type=\"submit\"]') "
        "|| document.querySelector('[aria-label*=\"Send\" i]') "
        "|| document.querySelector('button.send-button'); "
        "if (btn) { btn.click(); 'clicked'; } else { 'no_submit_btn'; }"
    )
    click_result = mcp_cua_driver_page(
        action="execute_javascript",
        pid=brave["pid"],
        window_id=win["window_id"],
        javascript=submit_js,
    )

    if "no_submit_btn" in str(click_result).lower():
        from pynput.keyboard import Key, Controller as KeyboardController
        kb = KeyboardController()
        kb.press(Key.enter)
        kb.release(Key.enter)

    time.sleep(WAIT_RESPONSE)

    extract_js = (
        "const msgs = document.querySelectorAll('[data-role=\"assistant\"], "
        ".markdown-body, .message-content, .bot-message, .response-content'); "
        "msgs.length ? msgs[msgs.length - 1].innerText.trim() : 'no_response_detected'"
    )
    response = mcp_cua_driver_page(
        action="execute_javascript",
        pid=brave["pid"],
        window_id=win["window_id"],
        javascript=extract_js,
    )

    response_str = str(response) if response else "no_response_detected"
    if "no_response_detected" in response_str.lower():
        print(f"Prompt sent to Qwen LM, but could not auto-extract the response.")
        print(f"Check the Brave window at {QWEN_URL} for the answer.")
        print(f"Prompt was: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    else:
        print(response_str)


if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    run_qwen(prompt)
