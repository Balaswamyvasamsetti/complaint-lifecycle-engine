# validator.py — Multi-layer enterprise validation engine
# Evaluates PK uniqueness, FK referential integrity, enums, dates, arithmetic, and lifecycle rules

import json
import os
from datetime import datetime, timedelta
from collections import Counter
from schema import (
    CHANNELS, SENTIMENTS, COMPLAINT_STATUSES,
    ORDER_STATUSES, RESOLUTION_TYPES, SURVEY_RATINGS,
    CATEGORIES, PRIORITY_RULES, SENDER_TYPES, SLA_STATUSES
)
from generator import priority_from_rules

VALID_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_SEVERITIES = {"Low", "Medium", "High", "Critical"}
VALID_SLA_STATUS = set(SLA_STATUSES)
VALID_SENDER_TYPE = set(SENDER_TYPES)
CATEGORY_IDS = {c["category_id"] for c in CATEGORIES}


def _fail(errors, entity, pk, rule, detail="", is_expected_anomaly=False):
    errors.append({
        "entity": entity,
        "id": pk,
        "rule": rule,
        "detail": detail,
        "is_expected_anomaly": is_expected_anomaly
    })


def _dt(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S") if s else None


def validate(data):
    errors = []

    customers = {c["customer_id"]: c for c in data["customers"]}
    products = {p["product_id"]: p for p in data["products"]}
    orders = {o["order_id"]: o for o in data["orders"]}
    complaints = {c["complaint_id"]: c for c in data["complaints"]}
    assignments = data.get("assignments", [])
    sla_clocks = data.get("sla_clocks", [])
    messages = data.get("messages", [])
    events = data.get("complaint_events", [])
    resolutions = {r["complaint_id"]: r for r in data.get("resolutions", [])}
    surveys = data.get("surveys", [])

    # Known edge case IDs
    edge_cmp_ids = {c["complaint_id"] for c in data["complaints"] if c.get("issue_type")}
    edge_sla_ids = {s["sla_id"] for s in sla_clocks if s.get("issue_type")}
    edge_res_ids = {r["resolution_id"] for r in data.get("resolutions", []) if r.get("issue_type")}
    edge_srv_ids = {s["survey_id"] for s in surveys if s.get("issue_type")}

    # ---------------------------------------------------------------------------
    # 1. Primary Key Uniqueness
    # ---------------------------------------------------------------------------
    for entity_name, records, pk_field in [
        ("Customer", data["customers"], "customer_id"),
        ("Product", data["products"], "product_id"),
        ("Order", data["orders"], "order_id"),
        ("Category", data["categories"], "category_id"),
        ("PriorityRule", data["priority_rules"], "rule_id"),
        ("Complaint", data["complaints"], "complaint_id"),
        ("ComplaintEvent", events, "event_id"),
        ("Assignment", assignments, "assignment_id"),
        ("SLAClock", sla_clocks, "sla_id"),
        ("Message", messages, "message_id"),
        ("Resolution", data.get("resolutions", []), "resolution_id"),
        ("Survey", surveys, "survey_id"),
    ]:
        seen = set()
        for r in records:
            pk = r.get(pk_field)
            if pk in seen:
                _fail(errors, entity_name, pk, "PK_DUPLICATE", "Duplicate primary key: %s" % pk)
            seen.add(pk)

    # ---------------------------------------------------------------------------
    # 1b. Child Entity ID Format Conventions
    # ---------------------------------------------------------------------------
    for s in sla_clocks:
        expected_sla_id = "SLA-%s" % s["complaint_id"]
        if s["sla_id"] != expected_sla_id:
            _fail(errors, "SLAClock", s["sla_id"], "ID_FORMAT_SLA",
                  "SLA ID %s does not match expected %s" % (s["sla_id"], expected_sla_id))

    for r in data.get("resolutions", []):
        expected_res_id = "RES-%s" % r["complaint_id"]
        if r["resolution_id"] != expected_res_id:
            _fail(errors, "Resolution", r["resolution_id"], "ID_FORMAT_RESOLUTION",
                  "Resolution ID %s does not match expected %s" % (r["resolution_id"], expected_res_id))

    for m in messages:
        prefix = "MSG-%s-" % m["complaint_id"]
        if not m["message_id"].startswith(prefix):
            _fail(errors, "Message", m["message_id"], "ID_FORMAT_MESSAGE",
                  "Message ID %s does not start with expected prefix %s" % (m["message_id"], prefix))

    # ---------------------------------------------------------------------------
    # 2. Foreign Key Integrity
    # ---------------------------------------------------------------------------
    for o in data["orders"]:
        if o["customer_id"] not in customers:
            _fail(errors, "Order", o["order_id"], "FK_CUSTOMER", "customer_id not found")
        if o["product_id"] not in products:
            _fail(errors, "Order", o["order_id"], "FK_PRODUCT", "product_id not found")

    for c in data["complaints"]:
        is_edge = c.get("issue_type") == "missing_customer"
        if not c["customer_id"]:
            if is_edge:
                _fail(errors, "Complaint", c["complaint_id"], "FK_CUSTOMER_MISSING", "Deliberate edge case: missing customer", is_expected_anomaly=True)
            else:
                _fail(errors, "Complaint", c["complaint_id"], "FK_CUSTOMER_MISSING", "Missing customer_id without edge label")
        elif c["customer_id"] not in customers:
            _fail(errors, "Complaint", c["complaint_id"], "FK_CUSTOMER", "customer_id not found in customers")

        if c["order_id"] and c["order_id"] not in orders:
            _fail(errors, "Complaint", c["complaint_id"], "FK_ORDER", "order_id not found in orders")
        if c["product_id"] and c["product_id"] not in products:
            _fail(errors, "Complaint", c["complaint_id"], "FK_PRODUCT", "product_id not found in products")
        if c["category_id"] not in CATEGORY_IDS:
            _fail(errors, "Complaint", c["complaint_id"], "FK_CATEGORY", "category_id not found in categories")
        if c["parent_complaint_id"] and c["parent_complaint_id"] not in complaints:
            _fail(errors, "Complaint", c["complaint_id"], "FK_PARENT", "parent_complaint_id not found in complaints")

    for a in assignments:
        if a["complaint_id"] not in complaints:
            _fail(errors, "Assignment", a["assignment_id"], "FK_COMPLAINT", "complaint_id not found")

    for s in sla_clocks:
        if s["complaint_id"] not in complaints:
            _fail(errors, "SLAClock", s["sla_id"], "FK_COMPLAINT", "complaint_id not found")

    for m in messages:
        if m["complaint_id"] not in complaints:
            _fail(errors, "Message", m["message_id"], "FK_COMPLAINT", "complaint_id not found")

    for e in events:
        if e["complaint_id"] not in complaints:
            _fail(errors, "ComplaintEvent", e["event_id"], "FK_COMPLAINT", "complaint_id not found")

    for r in data.get("resolutions", []):
        if r["complaint_id"] not in complaints:
            _fail(errors, "Resolution", r["resolution_id"], "FK_COMPLAINT", "complaint_id not found")

    for sv in surveys:
        if sv["complaint_id"] not in complaints:
            _fail(errors, "Survey", sv["survey_id"], "FK_COMPLAINT", "complaint_id not found")

    # ---------------------------------------------------------------------------
    # 3. Enum Values Validation
    # ---------------------------------------------------------------------------
    for o in data["orders"]:
        if o["status"] not in ORDER_STATUSES:
            _fail(errors, "Order", o["order_id"], "ENUM_ORDER_STATUS", "Invalid order status: %s" % o["status"])

    for c in data["complaints"]:
        if c["priority"] not in VALID_PRIORITIES:
            _fail(errors, "Complaint", c["complaint_id"], "ENUM_PRIORITY", "Invalid priority: %s" % c["priority"])
        if c["severity"] not in VALID_SEVERITIES:
            _fail(errors, "Complaint", c["complaint_id"], "ENUM_SEVERITY", "Invalid severity: %s" % c["severity"])
        if c["sentiment"] not in SENTIMENTS:
            _fail(errors, "Complaint", c["complaint_id"], "ENUM_SENTIMENT", "Invalid sentiment: %s" % c["sentiment"])
        if c["status"] not in COMPLAINT_STATUSES:
            _fail(errors, "Complaint", c["complaint_id"], "ENUM_STATUS", "Invalid complaint status: %s" % c["status"])
        if c["channel"] not in CHANNELS:
            _fail(errors, "Complaint", c["complaint_id"], "ENUM_CHANNEL", "Invalid channel: %s" % c["channel"])

    for s in sla_clocks:
        if s["status"] not in VALID_SLA_STATUS:
            _fail(errors, "SLAClock", s["sla_id"], "ENUM_SLA_STATUS", "Invalid SLA status: %s" % s["status"])

    for m in messages:
        if m["sender_type"] not in VALID_SENDER_TYPE:
            _fail(errors, "Message", m["message_id"], "ENUM_SENDER", "Invalid sender type: %s" % m["sender_type"])

    for r in data.get("resolutions", []):
        if r["resolution_type"] not in RESOLUTION_TYPES:
            _fail(errors, "Resolution", r["resolution_id"], "ENUM_RESOLUTION_TYPE", "Invalid resolution type: %s" % r["resolution_type"])

    for sv in surveys:
        if sv["rating"] not in SURVEY_RATINGS:
            _fail(errors, "Survey", sv["survey_id"], "ENUM_RATING", "Invalid rating: %s" % sv["rating"])

    # ---------------------------------------------------------------------------
    # 4. Date Ordering & Chronological Integrity
    # ---------------------------------------------------------------------------
    for o in data["orders"]:
        if o["delivery_date"] and _dt(o["delivery_date"]) < _dt(o["order_date"]):
            _fail(errors, "Order", o["order_id"], "DATE_ORDER", "delivery_date < order_date")

    for c in data["complaints"]:
        if _dt(c["updated_at"]) < _dt(c["created_at"]):
            _fail(errors, "Complaint", c["complaint_id"], "DATE_COMPLAINT", "updated_at < created_at")

    for s in sla_clocks:
        if _dt(s["deadline_at"]) <= _dt(s["started_at"]):
            _fail(errors, "SLAClock", s["sla_id"], "DATE_SLA_DEADLINE", "deadline_at <= started_at")
        if s["paused_at"] and not s["resumed_at"]:
            if s.get("issue_type") == "sla_pause_no_resume":
                _fail(errors, "SLAClock", s["sla_id"], "DATE_SLA_PAUSE_NO_RESUME", "Deliberate edge case: paused without resume", is_expected_anomaly=True)
        elif s["paused_at"] and s["resumed_at"] and _dt(s["resumed_at"]) < _dt(s["paused_at"]):
            _fail(errors, "SLAClock", s["sla_id"], "DATE_SLA_PAUSE", "resumed_at < paused_at")

    for r in data.get("resolutions", []):
        cmp = complaints.get(r["complaint_id"])
        if cmp:
            if _dt(r["resolved_at"]) < _dt(cmp["created_at"]):
                if r.get("issue_type") == "resolution_before_complaint":
                    _fail(errors, "Resolution", r["resolution_id"], "DATE_RESOLUTION_BEFORE_COMPLAINT", "Deliberate edge case: resolved before complaint", is_expected_anomaly=True)
                else:
                    _fail(errors, "Resolution", r["resolution_id"], "DATE_RESOLUTION", "resolved_at < complaint created_at")

    for sv in surveys:
        res = resolutions.get(sv["complaint_id"])
        if res:
            if _dt(sv["submitted_at"]) < _dt(res["resolved_at"]):
                if sv.get("issue_type") == "survey_before_closure":
                    _fail(errors, "Survey", sv["survey_id"], "DATE_SURVEY_BEFORE_CLOSURE", "Deliberate edge case: survey before resolution", is_expected_anomaly=True)
                else:
                    _fail(errors, "Survey", sv["survey_id"], "DATE_SURVEY", "submitted_at < resolved_at")

    # ---------------------------------------------------------------------------
    # 5. Lifecycle Consistency & Event Flow
    # ---------------------------------------------------------------------------
    for c in data["complaints"]:
        if c.get("issue_type") == "repeat_not_linked":
            _fail(errors, "Complaint", c["complaint_id"], "REPEAT_ISSUE_NOT_LINKED", "Deliberate edge case: repeat issue not linked to parent", is_expected_anomaly=True)
            continue
        if c.get("issue_type"):
            continue
        if c["is_reopened"] and not c["parent_complaint_id"]:
            _fail(errors, "Complaint", c["complaint_id"], "LIFECYCLE_REOPEN", "is_reopened=True but parent_complaint_id missing")

    # ---------------------------------------------------------------------------
    # 6. Arithmetic Reconciliation (SLA hours & Deadlines)
    # ---------------------------------------------------------------------------
    for s in sla_clocks:
        if s.get("issue_type"):
            continue
        expected_dl = _dt(s["started_at"]) + timedelta(hours=float(s["sla_hours"]))
        actual_dl = _dt(s["deadline_at"])
        diff_sec = abs((expected_dl - actual_dl).total_seconds())
        if diff_sec > 60:
            _fail(errors, "SLAClock", s["sla_id"], "ARITHMETIC_SLA_DEADLINE", "Deadline arithmetic mismatch: %.1f seconds" % diff_sec)

    # ---------------------------------------------------------------------------
    # 7. Priority Rule Reproducibility
    # ---------------------------------------------------------------------------
    for c in data["complaints"]:
        if c.get("issue_type") == "safety_low_priority":
            _fail(errors, "Complaint", c["complaint_id"], "PRIORITY_SAFETY_ANOMALY", "Deliberate edge case: safety assigned low priority", is_expected_anomaly=True)
            continue
        if c.get("issue_type"):
            continue

        cust = customers.get(c["customer_id"])
        prod = products.get(c["product_id"])
        if not cust or not prod:
            continue

        expected_prio = priority_from_rules(
            is_safety=c["is_safety_issue"],
            is_vulnerable=cust["is_vulnerable"],
            sentiment=c["sentiment"],
            order_value=c["order_value"],
            recurrence=c["recurrence_count"],
            is_fraud=(c["category_id"] == "CAT-09")
        )

        if expected_prio != c["priority"]:
            _fail(errors, "Complaint", c["complaint_id"], "PRIORITY_REPRODUCIBILITY",
                  "Rule mismatch: expected %s, got %s" % (expected_prio, c["priority"]))

    return errors


def summarise(errors, out_dir=None):
    total = len(errors)
    expected_anomalies = [e for e in errors if e.get("is_expected_anomaly")]
    genuine_issues = [e for e in errors if not e.get("is_expected_anomaly")]

    rule_counts = Counter(e["rule"] for e in errors)
    genuine_counts = Counter(e["rule"] for e in genuine_issues)

    summary = {
        "status": "PASSED" if len(genuine_issues) == 0 else "FAILED",
        "total_evaluations_checked": total,
        "genuine_data_defects": len(genuine_issues),
        "expected_edge_cases_caught": len(expected_anomalies),
        "defect_breakdown": dict(genuine_counts),
        "edge_case_breakdown": dict(Counter(e["rule"] for e in expected_anomalies)),
    }

    print("\n" + "=" * 60)
    print("  VALIDATION SUMMARY REPORT")
    print("=" * 60)
    print("  Status:                     %s" % summary["status"])
    print("  Genuine Data Issues:        %d" % len(genuine_issues))
    print("  Expected Anomalies Caught:  %d" % len(expected_anomalies))
    print("  Rule Checks Evaluated:      %d" % len(rule_counts))

    for rule, count in rule_counts.most_common():
        marker = "[EXPECTED ANOMALY]" if any(e["rule"] == rule and e.get("is_expected_anomaly") for e in errors) else "[DEFECT]"
        print("    %-32s: %3d  %s" % (rule, count, marker))
    print("=" * 60 + "\n")

    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        summary_path = os.path.join(out_dir, "validation_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print("  [VALIDATION] Audit report saved -> %s" % summary_path)

    return len(genuine_issues) == 0
