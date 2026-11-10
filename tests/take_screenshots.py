import time
import os
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def capture_all():
    print("[1/4] Launching headless browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",
            headless=True
        )

        # 1. Executive Dashboard Overview
        print("[2/4] Capturing Executive Dashboard Overview...")
        page = browser.new_page(viewport={"width": 1600, "height": 1050})
        page.goto("http://127.0.0.1:8000/dashboard", wait_until="networkidle")
        time.sleep(2.5)
        path1 = os.path.join(SCREENSHOT_DIR, "01_dashboard_overview.png")
        page.screenshot(path=path1)
        print("  -> Saved:", path1)

        # 2. Interactive AI Triage
        print("[3/4] Executing AI Triage & Capturing Result...")
        page.evaluate("applyPreset(1)")
        time.sleep(0.5)
        page.evaluate("executeTriage()")
        time.sleep(3.0)
        path2 = os.path.join(SCREENSHOT_DIR, "02_live_ai_triage.png")
        page.screenshot(path=path2)
        print("  -> Saved:", path2)

        # 3. Interactive Cockpit & Audit Trail Tab
        print("[4/4] Capturing Interactive Ticket Cockpit & Audit Trail...")
        page.evaluate("switchCockpitTab('audit')")
        time.sleep(1.5)
        path3 = os.path.join(SCREENSHOT_DIR, "03_event_audit_trace.png")
        page.screenshot(path=path3)
        print("  -> Saved:", path3)

        # 4. Interactive OpenAPI / Swagger Documentation
        print("[5/5] Capturing Swagger API Documentation...")
        page.goto("http://127.0.0.1:8000/docs", wait_until="networkidle")
        time.sleep(1.5)
        path4 = os.path.join(SCREENSHOT_DIR, "04_swagger_api_docs.png")
        page.screenshot(path=path4)
        print("  -> Saved:", path4)

        browser.close()
        print("\n[SUCCESS] All 4 UI output screenshots captured successfully!")

if __name__ == "__main__":
    capture_all()
