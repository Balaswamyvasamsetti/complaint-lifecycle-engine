# verify_live_api.py — End-to-end verification of running FastAPI service

import sys
import os
import time
import httpx

BASE_URL = "http://127.0.0.1:8000"

def run_live_verification():
    print("\n" + "=" * 65)
    print("  LIVE API END-TO-END VERIFICATION")
    print("=" * 65)

    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        # 1. Health check
        print("\n[TEST 1/7] Probing /health...")
        res = client.get("/health")
        assert res.status_code == 200, "Health check failed"
        print("  -> Health Status: %s | DB: %s" % (res.json()["status"], res.json()["database"]))

        # 2. Ingest complaint
        print("\n[TEST 2/7] Submitting new complaint via POST /complaints...")
        payload = {
            "channel": "Email",
            "complaint_text": "The coffee maker caught fire while brewing and melted the kitchen counter.",
            "order_value": 199.99,
            "is_safety_issue": True,
            "is_vulnerable": False,
            "recurrence_count": 1
        }
        res = client.post("/complaints", json=payload)
        assert res.status_code == 201, "Complaint submission failed: %s" % res.text
        data = res.json()
        cmp_id = data["complaint_id"]
        print("  -> Complaint Created: %s" % cmp_id)
        print("  -> AI Category:       %s" % data["category"])
        print("  -> Priority:          %s (SLA: %.1f hrs)" % (data["priority"], data["sla_hours"]))
        print("  -> Assigned Team:     %s (Agent: %s)" % (data["assigned_team"], data["assigned_agent"]))
        print("  -> SLA Deadline:      %s" % data["sla_deadline"])

        # 3. Check SLA clock
        print("\n[TEST 3/7] Checking SLA clock via GET /complaints/%s/sla..." % cmp_id)
        res = client.get("/complaints/%s/sla" % cmp_id)
        assert res.status_code == 200
        sla = res.json()
        print("  -> SLA Status: %s | Hours Remaining: %.2f" % (sla["status"], sla["hours_remaining"]))

        # 4. Pause and Resume SLA
        print("\n[TEST 4/7] Testing SLA pause/resume...")
        res = client.post("/complaints/%s/sla/pause" % cmp_id, json={"reason": "Awaiting customer photos", "actor": "AGT-SR-01"})
        assert res.status_code == 200
        print("  -> Clock Paused: %s" % res.json()["sla_status"])
        time.sleep(0.5)
        res = client.post("/complaints/%s/sla/resume" % cmp_id)
        assert res.status_code == 200
        print("  -> Clock Resumed: %s (Adjusted Deadline: %s)" % (res.json()["sla_status"], res.json()["adjusted_deadline"]))

        # 5. Resolve complaint
        print("\n[TEST 5/7] Resolving complaint via POST /complaints/%s/resolve..." % cmp_id)
        res_payload = {
            "resolution_type": "Refund",
            "resolved_by": "AGT-SR-01",
            "notes": "Full refund and replacement dispatched.",
            "refund_amount": 299.99
        }
        res = client.post("/complaints/%s/resolve" % cmp_id, json=res_payload)
        assert res.status_code == 201
        res_data = res.json()
        print("  -> Resolution: %s | Refund: £299.99" % res_data["resolution_type"])
        print("  -> Approver Sign-off Required: %s (> £250.00 rule)" % res_data["requires_approver_authorization"])

        # 6. Submit survey
        print("\n[TEST 6/7] Submitting CSAT & NPS survey...")
        survey_payload = {
            "rating": 5,
            "feedback_text": "Immediate response and fair resolution.",
            "nps_score": 10
        }
        res = client.post("/complaints/%s/survey" % cmp_id, json=survey_payload)
        assert res.status_code == 201
        print("  -> Survey Logged: ID %s" % res.json()["survey_id"])

        # 7. Audit trail and Analytics
        print("\n[TEST 7/7] Verifying immutable event sourcing timeline & analytics...")
        res = client.get("/complaints/%s/events" % cmp_id)
        assert res.status_code == 200
        timeline = res.json()["timeline"]
        print("  -> Audit Trace: %d events captured:" % len(timeline))
        for evt in timeline:
            print("     * [%s] %-20s by %-18s -> State: %s" % (
                evt["event_timestamp"], evt["event_type"], evt["actor"], evt["new_state"]
            ))

        res = client.get("/analytics/summary")
        assert res.status_code == 200
        stats = res.json()
        print("\n  -> Operational KPIs:")
        print("     Total Complaints:     %d" % stats["total_complaints"])
        print("     Resolved Complaints:  %d" % stats["resolved_complaints"])
        print("     SLA Breach Rate:      %.2f%%" % stats["sla_breach_rate_pct"])
        print("     Average CSAT:         %.2f / 5.0" % stats["avg_csat_rating"])
        print("     Average NPS:          %.2f / 10.0" % stats["avg_nps_score"])

    print("\n" + "=" * 65)
    print("  ALL LIVE API VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    run_live_verification()

