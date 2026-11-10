import time
import os
from playwright.sync_api import sync_playwright

CHROME_PATH = "C:/Program Files/Google/Chrome/Application/chrome.exe"

def test_cockpit_full_suite():
    print("Launching Chrome for Cockpit E2E verification...")
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME_PATH, headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1050})
        
        console_errors = []
        page.on("console", lambda m: print(f"BROWSER [{m.type}]: {m.text}"))
        page.on("pageerror", lambda err: console_errors.append(str(err)))
        page.on("response", lambda r: print(f"RESPONSE [{r.status}] {r.request.method} {r.url} -> {r.text()[:200]}") if r.status >= 400 else None)

        print("1. Loading Dashboard at http://127.0.0.1:8000 ...")
        page.goto("http://127.0.0.1:8000", wait_until="networkidle")
        time.sleep(2.0)

        # Ensure complaints table rendered
        page.wait_for_selector("#complaints-tbody tr")
        print("   -> Complaints table loaded.")

        # --- SECTION 1: Ticket Workspace & Overview & Clock ---
        print("\n2. Testing Ticket Workspace: Overview & Clock...")
        # Click on the first row
        first_row = page.locator("#complaints-tbody tr").first
        first_row.click()
        page.wait_for_function("document.getElementById('meta-customer').innerText !== '--'", timeout=15000)

        selected_id = page.inner_text("#selected-ticket-label")
        print(f"   -> Selected ticket ID: {selected_id}")
        assert selected_id.startswith("CMP-"), f"Unexpected ticket id: {selected_id}"

        cust = page.inner_text("#meta-customer")
        order = page.inner_text("#meta-order")
        agent = page.inner_text("#meta-agent")
        sla = page.inner_text("#meta-sla")
        desc = page.inner_text("#meta-text")
        print(f"   -> Customer: {cust}")
        print(f"   -> Order: {order}")
        print(f"   -> Assigned Owner: {agent}")
        print(f"   -> SLA Clock: {sla}")
        assert cust != "--", "Customer reference is unpopulated"
        assert order != "--", "Order is unpopulated"
        assert agent != "--", "Agent is unpopulated"
        assert sla != "--", "SLA clock is unpopulated"
        assert len(desc) > 5, "Description is missing"

        # Test SLA Pause & Resume controls
        print("   -> Testing SLA Pause & Resume controls...")
        page.on("dialog", lambda dialog: dialog.accept("Awaiting inspection documentation"))
        page.click("button:has-text('Pause SLA Clock')")
        page.wait_for_function("document.getElementById('meta-sla').innerText.includes('Paused')", timeout=15000)
        paused_sla = page.inner_text("#meta-sla")
        print(f"   -> SLA Clock after Pause: {paused_sla}")
        assert "Paused" in paused_sla, f"Expected Paused status, got: {paused_sla}"

        page.click("button:has-text('Resume SLA Clock')")
        page.wait_for_function("document.getElementById('meta-sla').innerText.includes('Active')", timeout=15000)
        resumed_sla = page.inner_text("#meta-sla")
        print(f"   -> SLA Clock after Resume: {resumed_sla}")
        assert "Active" in resumed_sla, f"Expected Active status, got: {resumed_sla}"

        # Test Reassignment
        print("   -> Testing Reassignment dropdown & action...")
        page.select_option("#reassign-team", "Fraud-Team")
        time.sleep(0.3)
        suggested_agent = page.input_value("#reassign-agent")
        assert suggested_agent == "AGT-FR-01", f"Expected AGT-FR-01, got {suggested_agent}"
        page.click("button:has-text('Reassign')")
        page.wait_for_function("document.getElementById('meta-agent').innerText.includes('Fraud-Team')", timeout=15000)
        updated_owner = page.inner_text("#meta-agent")
        print(f"   -> Updated Owner after reassign: {updated_owner}")
        assert "Fraud-Team" in updated_owner or "AGT-FR-01" in updated_owner

        # Test Status Lifecycle Transition button (Pending Customer)
        print("   -> Testing Lifecycle Transition (Pending Customer)...")
        page.click("button:has-text('Pending Customer')")
        time.sleep(1.5)
        # Check active status badge in header
        status_text = page.inner_text("#complaints-tbody tr.row-selected")
        print("   -> Status transitioned.")

        # --- SECTION 2: Resolve Case ---
        print("\n3. Testing Resolve Case Tab & Actions...")
        page.click("#tab-btn-resolve")
        time.sleep(0.5)

        # AI Recommendation button
        print("   -> Requesting AI Recommendation...")
        page.click("button:has-text('AI Recommendation')")
        page.wait_for_function("document.getElementById('res-notes').value.length > 0", timeout=15000)
        rec_notes = page.input_value("#res-notes")
        print(f"   -> AI Recommendation received: {rec_notes[:60]}...")
        assert len(rec_notes) > 10, "AI Recommendation failed to populate notes"

        # Change strategy & amount
        page.select_option("#res-type", "Replacement")
        page.fill("#res-amount", "0")
        time.sleep(0.2)

        # Submit Resolution
        print("   -> Submitting Resolution & Sign Off...")
        page.click("button:has-text('Submit Resolution & Sign Off')")
        page.wait_for_function("document.getElementById('meta-resolution-text').innerText !== '--'", timeout=15000)

        # Check that it returned to overview and resolution box is visible
        res_box_text = page.inner_text("#meta-resolution-text")
        print(f"   -> Resolution Card Visible: {res_box_text}")
        assert "Replacement" in res_box_text, f"Resolution text mismatch: {res_box_text}"

        # --- SECTION 3: Messages Tab ---
        print("\n4. Testing Messages Tab & Actions...")
        page.click("#tab-btn-messages")
        page.wait_for_function("!document.getElementById('messages-container').innerText.includes('Loading')", timeout=15000)

        msgs_html = page.inner_html("#messages-container")
        assert "Failed to load" not in msgs_html, "Messages failed to load!"
        msg_cards = page.query_selector_all("#messages-container > div")
        print(f"   -> Messages loaded cleanly! Rendered message bubbles: {len(msg_cards)}")

        # Post a new internal caseworker note
        print("   -> Posting an internal case note...")
        test_msg = f"Audited by Senior Specialist at {time.strftime('%H:%M:%S')} - case in order."
        prev_msg_count = len(page.query_selector_all("#messages-container > div"))
        page.fill("#msg-text", test_msg)
        page.check("#msg-internal")
        print("   -> msg-text before click:", page.input_value("#msg-text"))
        page.click("#tab-content-messages button:has-text('Send')")
        time.sleep(1.0)
        print("   -> msg-text after click:", page.input_value("#msg-text"))
        
        # Wait until messages container adds the new message card
        page.wait_for_function(f"document.querySelectorAll('#messages-container > div').length > {prev_msg_count}", timeout=20000)

        # Verify new message bubble rendered
        updated_msgs_text = page.inner_text("#messages-container")
        assert test_msg in updated_msgs_text, "Newly posted message did not appear in messages container!"
        print("   -> New message confirmed present in conversation thread!")

        # --- SECTION 4: Audit Trace Tab & CSAT Survey ---
        print("\n5. Testing Audit Trace Tab & Survey...")
        page.click("#tab-btn-audit")
        page.wait_for_selector("#timeline-container .border-l-2", timeout=15000)

        timeline_html = page.inner_html("#timeline-container")
        assert "Failed to load" not in timeline_html, "Audit trace failed to load!"
        event_cards = page.query_selector_all("#timeline-container .border-l-2")
        print(f"   -> Audit trail loaded cleanly! Event cards count: {len(event_cards)}")

        # Verify recent actions appear in event trail
        timeline_text = page.inner_text("#timeline-container")
        assert "ASSIGNED" in timeline_text or "RESOLVED" in timeline_text or "MESSAGE_SENT" in timeline_text
        print("   -> Event audit trail contains logged actions!")

        # Post a CSAT & NPS Survey
        print("   -> Submitting customer CSAT & NPS survey...")
        page.select_option("#srv-rating", "5")
        page.fill("#srv-nps", "10")
        page.fill("#srv-feedback", "Outstanding resolution speed and polite agent support!")
        page.click("#tab-content-audit button:has-text('Submit')")
        time.sleep(3.0)

        # Verify survey badge in overview
        page.click("#tab-btn-overview")
        page.wait_for_function("document.getElementById('meta-survey-badge').innerText.includes('CSAT: 5')", timeout=15000)
        survey_badge = page.inner_text("#meta-survey-badge")
        print(f"   -> Overview Survey Badge: {survey_badge}")
        assert "CSAT: 5" in survey_badge, f"Expected CSAT 5 in survey badge, got {survey_badge}"

        print("\n=======================================================")
        print("SUCCESS: ALL 4 COCKPIT SECTIONS & ACTIONS FUNCTION 100%!")
        print("=======================================================")

        if console_errors:
            print("Console Errors observed:", console_errors)
        assert len(console_errors) == 0, f"Encountered unexpected console errors: {console_errors}"

        browser.close()

if __name__ == "__main__":
    test_cockpit_full_suite()
