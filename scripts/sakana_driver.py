import time
import sys
from hermes_tools import mcp_cua_driver_list_apps, mcp_cua_driver_list_windows, mcp_cua_driver_page, mcp_cua_driver_type_text, mcp_cua_driver_click

def run_sakana(prompt):
    # Find Brave
    apps = mcp_cua_driver_list_apps()
    brave = next((app for app in apps if "brave" in app['name'].lower()), None)
    if not brave or not brave['running']:
        print("Brave not running")
        return

    # Find window
    wins = mcp_cua_driver_list_windows(pid=brave['pid'])
    if not wins:
        print("No window found")
        return
    win = wins[0]

    # Navigate/Type
    mcp_cua_driver_page(action='execute_javascript', pid=brave['pid'], window_id=win['window_id'], 
                       javascript=f"window.location.href='https://chat.sakana.ai/'")
    time.sleep(5)
    
    # Needs actual element selection for the textarea, simplified for now
    print(f"Driver connected. Prompt: {prompt}")

if __name__ == "__main__":
    run_sakana(sys.argv[1])
