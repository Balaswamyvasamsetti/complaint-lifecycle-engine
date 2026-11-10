"""
Validator — runs PK uniqueness, FK integrity, enum checks,
date ordering, arithmetic reconciliation and lifecycle transitions.
"""

from schema import (
    CHANNELS, SENTIMENTS, COMPLAINT_STATUSES,
    ORDER_STATUSES, RESOLUTION_TYPES, SURVEY_RATINGS, CATEGORIES, PRIORITY_RULES
)

VALID_PRIORITIES  = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_SEVERITIES  = {"Low", "Medium", "High", "Critical"}
VALID_SLA_STATUS  = {"Active", "Paused", "Met", "Breached"}
VALID_SENDER_TYPE = {"Customer", "Agent", "System"}
CATEGORY_IDS      = {c["category_id"] for c in CATEGORIES}
PRODUCT_IDS_GLOBAL = set()


def _fail(errors, entity, pk, rule, detail=""):
    errors.append({"entity": entity, "id": pk, "rule": rule, "detail": detail})


def validate(data):
    errors = []

    customers   = {c["customer_id"]: c for c in data["customers"]}
    products    = {p["product_id"]: p for p in data["products"]}
    orders      = {o["order_id"]: o for o in data["orders"]}
    complaints  = {c["complaint_id"]: c for c in data["complaints"]}
    assignments = data["assignments"]
    sla_clocks  = data["sla_clocks"]
    messages    = data["messages"]
    resolutions = {r["complaint_id"]: r for r in data["resolutions"]}
    surveys     = data["surveys"]

    # ── PK uniqueness ─────────────────────────────────────────────────────────
    for entity_name, records, pk_field in [
        ("Customer",   data["customers"],   "customer_id"),
        ("Order",      data["orders"],       "order_id"),
        ("Complaint",  data["complaints"],   "complaint_id"),
        ("Assignment", assignments,          "assignment_id"),
        ("SLAClock",   sla_clocks,           "sla_id"),
        ("Message",    messages,             "message_id"),
        ("Resolution", data["resolutions"],  "resolution_id"),
        ("Survey",     surveys,              "survey_id"),
    ]:
        seen = set()
        for r in records:
            pk = r[pk_field]
            if pk in seen:
                _fail(errors, entity_name, pk, "PK_DUPLICATE", f"Duplicate {pk_field}")
            seen.add(pk)

    # ── FK integrity ──────────────────────────────────────────────────────────
    for o in data["orders"]:
        if o["customer_id"] not in customers:
            _fail(errors, "Order", o["order_id"], "FK_CUSTOMER", f"customer_id {o['customer_id']} not found")
        if o["product_id"] not in products:
            _fail(errors, "Order", o["order_id"], "FK_PRODUCT", f"product_id {o['product_id']} not found")

    for c in data["complaints"]:
        # customer_id nullable for edge case
        if c["customer_id"] and c["customer_id"] not in customers:
            _fail(errors, "Complaint", c["complaint_id"], "FK_CUSTOMER", f"customer_id {c['customer_id']} not found")
        if c["order_id"] and c["order_id"] not in orders:
            _fail(errors, "Complaint", c["complaint_id"], "FK_ORDER", f"order_id {c['order_id']} not found")
        if c["product_id"] and c["product_id"] not in products:
            _fail(errors, "Complaint", c["complaint_id"], "FK_PRODUCT", f"product_id {c['product_id']} not found")
        if c["category_id"] not in CATEGORY_IDS:
            _fail(errors, "Complaint", c["complaint_id"], "FK_CATEGORY", f"category_id {c['category_id']} not found")
        if c["parent_complaint_id"] and c["parent_complaint_id"] not in complaints:
            _fail(errors, "Complaint", c["complaint_id"], "FK_PARENT", f"parent_complaint_id not found")

    for a in assignments:
        if a["complaint_id"] not in complaints:
            _fail(errors, "Assignment", a["assignment_id"], "FK_COMPLAINT", f"complaint_id {a['complaint_id']} not found")

    for s in sla_clocks:
        if s["complaint_id"] not in complaints:
            _fail(errors, "SLAClock", s["sla_id"], "FK_COMPLAINT", f"complaint_id {s['complaint_id']} not found")

    for m in messages:
        if m["complaint_id"] not in complaints:
            _fail(errors, "Message", m["message_id"], "FK_COMPLAINT", f"complaint_id {m['complaint_id']} not found")

    for r in data["resolutions"]:
        if r["complaint_id"] not in complaints:
            _fail(errors, "Resolution", r["resolution_id"], "FK_COMPLAINT", f"complaint_id {r['complaint_id']} not found")

    for sv in surveys:
        if sv["complaint_id"] not in complaints:
            _fail(errors, "Survey", sv["survey_id"], "FK_COMPLAINT", f"complaint_id {sv['complaint_id']} not found")

    # ── enum checks ───────────────────────────────────────────────────────────
    for o in data["orders"]:
        if o["status"] not in ORDER_STATUSES:
            _fail(errors, "Order", o["order_id"], "ENUM_STATUS", f"Invalid status: {o['status']}")

    for c in data["complaints"]:
        if c.get("issue_type"):
            continue  # skip edge-case rows for enum checks
        if c["priority"] not in VALID_PRIORITIES:
            _fail(errors, "Complaint", c["complaint_id"], "ENUM_PRIORITY", f"Invalid priority: {c['priority']}")
        if c["severity"] not in VALID_SEVERITIES:
            _fail(errors, "Complaint", c["complaint_id"], "ENUM_SEVERITY", f"Invalid severity: {c['severity']}")
        if c["sentiment"] not in SENTIMENTS:
            _fail(errors, "Complaint", c["complaint_id"], "ENUM_SENTIMENT", f"Invalid sentiment: {c['sentiment']}")
        if c["status"] not in COMPLAINT_STATUSES:
            _fail(errors, "Complaint", c["complaint_id"], "ENUM_STATUS", f"Invalid status: {c['status']}")
        if c["channel"] not in CHANNELS:
            _fail(errors, "Complaint", c["complaint_id"], "ENUM_CHANNEL", f"Invalid channel: {c['channel']}")

    for s in sla_clocks:
        if s.get("issue_type"):
            continue
        if s["status"] not in VALID_SLA_STATUS:
            _fail(errors, "SLAClock", s["sla_id"], "ENUM_STATUS", f"Invalid SLA status: {s['status']}")

    for m in messages:
        if m["sender_type"] not in VALID_SENDER_TYPE:
            _fail(errors, "Message", m["message_id"], "ENUM_SENDER", f"Invalid sender_type: {m['sender_type']}")

    for r in data["resolutions"]:
        if r.get("issue_type"):
            continue
        if r["resolution_type"] not in RESOLUTION_TYPES:
            _fail(errors, "Resolution", r["resolution_id"], "ENUM_RES_TYPE", f"Invalid resolution_type: {r['resolution_type']}")

    for sv in surveys:
        if sv.get("issue_type"):
            continue
        if sv["rating"] not in SURVEY_RATINGS:
            _fail(errors, "Survey", sv["survey_id"], "ENUM_RATING", f"Invalid rating: {sv['rating']}")

    # ── date ordering ─────────────────────────────────────────────────────────
    from datetime import datetime

    def dt(s):
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S") if s else None

    for o in data["orders"]:
        if o["delivery_date"]:
            if dt(o["delivery_date"]) < dt(o["order_date"]):
                _fail(errors, "Order", o["order_id"], "DATE_ORDER", "delivery_date < order_date")

    for c in data["complaints"]:
        if dt(c["updated_at"]) < dt(c["created_at"]):
            _fail(errors, "Complaint", c["complaint_id"], "DATE_ORDER", "updated_at < created_at")

    for s in sla_clocks:
        if s.get("issue_type"):
            continue
        if dt(s["deadline_at"]) <= dt(s["started_at"]):
            _fail(errors, "SLAClock", s["sla_id"], "DATE_SLA", "deadline_at <= started_at")
        if s["paused_at"] and s["resumed_at"]:
            if dt(s["resumed_at"]) < dt(s["paused_at"]):
                _fail(errors, "SLAClock", s["sla_id"], "DATE_PAUSE", "resumed_at < paused_at")

    # ── resolution date vs complaint (skip edge cases) ────────────────────────
    for r in data["resolutions"]:
        if r.get("issue_type"):
            continue
        cmp = complaints.get(r["complaint_id"])
        if cmp and dt(r["resolved_at"]) < dt(cmp["created_at"]):
            _fail(errors, "Resolution", r["resolution_id"], "DATE_RESOLUTION", "resolved_at < complaint created_at")

    # ── survey date vs resolution (skip edge cases) ───────────────────────────
    for sv in surveys:
        if sv.get("issue_type"):
            continue
        res = resolutions.get(sv["complaint_id"])
        if res and dt(sv["submitted_at"]) < dt(res["resolved_at"]):
            _fail(errors, "Survey", sv["survey_id"], "DATE_SURVEY", "submitted_at < resolved_at")

    # ── lifecycle: reopened must have parent ──────────────────────────────────
    for c in data["complaints"]:
        if c.get("issue_type"):
            continue
        if c["is_reopened"] and not c["parent_complaint_id"]:
            _fail(errors, "Complaint", c["complaint_id"], "LIFECYCLE_REOPEN", "is_reopened=True but no parent_complaint_id")

    # ── SLA arithmetic ────────────────────────────────────────────────────────
    for s in sla_clocks:
        if s.get("issue_type"):
            continue
        expected_deadline = dt(s["started_at"]) + __import__("datetime").timedelta(hours=s["sla_hours"])
        actual_deadline   = dt(s["deadline_at"])
        diff_minutes      = abs((expected_deadline - actual_deadline).total_seconds() / 60)
        if diff_minutes > 1:
            _fail(errors, "SLAClock", s["sla_id"], "ARITH_SLA", f"deadline_at mismatch by {diff_minutes:.1f} min")

    # ── priority reproducibility ──────────────────────────────────────────────
    from generator import priority_from_rules
    for c in data["complaints"]:
        if c.get("issue_type"):
            continue
        prod = products.get(c["product_id"])
        cust = customers.get(c["customer_id"])
        if not prod or not cust:
            continue
        is_fraud = c["category_id"] == "CAT-09"
        expected = priority_from_rules(
            c["is_safety_issue"], cust["is_vulnerable"],
            c["sentiment"], c["order_value"],
            c["recurrence_count"], is_fraud
        )
        if expected != c["priority"]:
            _fail(errors, "Complaint", c["complaint_id"], "PRIORITY_RULE",
                  f"Expected {expected}, got {c['priority']}")

    return errors


def summarise(errors):
    from collections import Counter
    counts = Counter(e["rule"] for e in errors)
    print(f"\n[VALIDATION] Total issues: {len(errors)}")
    for rule, cnt in counts.most_common():
        print(f"  {rule}: {cnt}")
    # separate edge-case anomalies from real errors
    real = [e for e in errors if "EDGE" not in e.get("id","")]
    print(f"[VALIDATION] Real data issues (non-edge): {len(real)}")
    return len(real) == 0
