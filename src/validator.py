# validator.py — PK uniqueness, FK integrity, enum, date, lifecycle and arithmetic checks

from datetime import datetime, timedelta
from collections import Counter
from schema import (
    CHANNELS, SENTIMENTS, COMPLAINT_STATUSES,
    ORDER_STATUSES, RESOLUTION_TYPES, SURVEY_RATINGS, CATEGORIES, PRIORITY_RULES
)
from generator import priority_from_rules

VALID_PRIORITIES  = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_SEVERITIES  = {"Low", "Medium", "High", "Critical"}
VALID_SLA_STATUS  = {"Active", "Paused", "Met", "Breached"}
VALID_SENDER_TYPE = {"Customer", "Agent", "System"}
CATEGORY_IDS      = {c["category_id"] for c in CATEGORIES}


def _fail(errors, entity, pk, rule, detail=""):
    errors.append({"entity": entity, "id": pk, "rule": rule, "detail": detail})


def _dt(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S") if s else None


def validate(data):
    errors = []

    customers   = {c["customer_id"]: c for c in data["customers"]}
    products    = {p["product_id"]:  p for p in data["products"]}
    orders      = {o["order_id"]:    o for o in data["orders"]}
    complaints  = {c["complaint_id"]: c for c in data["complaints"]}
    assignments = data["assignments"]
    sla_clocks  = data["sla_clocks"]
    messages    = data["messages"]
    resolutions = {r["complaint_id"]: r for r in data["resolutions"]}
    surveys     = data["surveys"]

    # ---------------------------------------------------------------------------
    # PK uniqueness
    # ---------------------------------------------------------------------------
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
                _fail(errors, entity_name, pk, "PK_DUPLICATE", "Duplicate %s" % pk_field)
            seen.add(pk)

    # ---------------------------------------------------------------------------
    # FK integrity
    # ---------------------------------------------------------------------------
    for o in data["orders"]:
        if o["customer_id"] not in customers:
            _fail(errors, "Order", o["order_id"], "FK_CUSTOMER", "customer_id not found")
        if o["product_id"] not in products:
            _fail(errors, "Order", o["order_id"], "FK_PRODUCT", "product_id not found")

    for c in data["complaints"]:
        if c["customer_id"] and c["customer_id"] not in customers:
            _fail(errors, "Complaint", c["complaint_id"], "FK_CUSTOMER", "customer_id not found")
        if c["order_id"] and c["order_id"] not in orders:
            _fail(errors, "Complaint", c["complaint_id"], "FK_ORDER", "order_id not found")
        if c["product_id"] and c["product_id"] not in products:
            _fail(errors, "Complaint", c["complaint_id"], "FK_PRODUCT", "product_id not found")
        if c["category_id"] not in CATEGORY_IDS:
            _fail(errors, "Complaint", c["complaint_id"], "FK_CATEGORY", "category_id not found")
        if c["parent_complaint_id"] and c["parent_complaint_id"] not in complaints:
            _fail(errors, "Complaint", c["complaint_id"], "FK_PARENT", "parent_complaint_id not found")

    for a in assignments:
        if a["complaint_id"] not in complaints:
            _fail(errors, "Assignment", a["assignment_id"], "FK_COMPLAINT", "complaint_id not found")

    for s in sla_clocks:
        if s["complaint_id"] not in complaints:
            _fail(errors, "SLAClock", s["sla_id"], "FK_COMPLAINT", "complaint_id not found")

    for m in messages:
        if m["complaint_id"] not in complaints:
            _fail(errors, "Message", m["message_id"], "FK_COMPLAINT", "complaint_id not found")

    for r in data["resolutions"]:
        if r["complaint_id"] not in complaints:
            _fail(errors, "Resolution", r["resolution_id"], "FK_COMPLAINT", "complaint_id not found")

    for sv in surveys:
        if sv["complaint_id"] not in complaints:
            _fail(errors, "Survey", sv["survey_id"], "FK_COMPLAINT", "complaint_id not found")

    # ---------------------------------------------------------------------------
    # Enum checks
    # ---------------------------------------------------------------------------
    for o in data["orders"]:
        if o["status"] not in ORDER_STATUSES:
            _fail(errors, "Order", o["order_id"], "ENUM_STATUS", "Invalid status: %s" % o["status"])

    for c in data["complaints"]:
        if c.get("issue_type"):
            continue
        if c["priority"]  not in VALID_PRIORITIES:
            _fail(errors, "Complaint", c["complaint_id"], "ENUM_PRIORITY",  "Invalid priority: %s"  % c["priority"])
        if c["severity"]  not in VALID_SEVERITIES:
            _fail(errors, "Complaint", c["complaint_id"], "ENUM_SEVERITY",  "Invalid severity: %s"  % c["severity"])
        if c["sentiment"] not in SENTIMENTS:
            _fail(errors, "Complaint", c["complaint_id"], "ENUM_SENTIMENT", "Invalid sentiment: %s" % c["sentiment"])
        if c["status"]    not in COMPLAINT_STATUSES:
            _fail(errors, "Complaint", c["complaint_id"], "ENUM_STATUS",    "Invalid status: %s"    % c["status"])
        if c["channel"]   not in CHANNELS:
            _fail(errors, "Complaint", c["complaint_id"], "ENUM_CHANNEL",   "Invalid channel: %s"   % c["channel"])

    for s in sla_clocks:
        if not s.get("issue_type") and s["status"] not in VALID_SLA_STATUS:
            _fail(errors, "SLAClock", s["sla_id"], "ENUM_STATUS", "Invalid SLA status: %s" % s["status"])

    for m in messages:
        if m["sender_type"] not in VALID_SENDER_TYPE:
            _fail(errors, "Message", m["message_id"], "ENUM_SENDER", "Invalid sender_type: %s" % m["sender_type"])

    for r in data["resolutions"]:
        if not r.get("issue_type") and r["resolution_type"] not in RESOLUTION_TYPES:
            _fail(errors, "Resolution", r["resolution_id"], "ENUM_RES_TYPE", "Invalid resolution_type: %s" % r["resolution_type"])

    for sv in surveys:
        if not sv.get("issue_type") and sv["rating"] not in SURVEY_RATINGS:
            _fail(errors, "Survey", sv["survey_id"], "ENUM_RATING", "Invalid rating: %s" % sv["rating"])

    # ---------------------------------------------------------------------------
    # Date ordering
    # ---------------------------------------------------------------------------
    for o in data["orders"]:
        if o["delivery_date"] and _dt(o["delivery_date"]) < _dt(o["order_date"]):
            _fail(errors, "Order", o["order_id"], "DATE_ORDER", "delivery_date < order_date")

    for c in data["complaints"]:
        if _dt(c["updated_at"]) < _dt(c["created_at"]):
            _fail(errors, "Complaint", c["complaint_id"], "DATE_ORDER", "updated_at < created_at")

    for s in sla_clocks:
        if s.get("issue_type"):
            continue
        if _dt(s["deadline_at"]) <= _dt(s["started_at"]):
            _fail(errors, "SLAClock", s["sla_id"], "DATE_SLA", "deadline_at <= started_at")
        if s["paused_at"] and s["resumed_at"] and _dt(s["resumed_at"]) < _dt(s["paused_at"]):
            _fail(errors, "SLAClock", s["sla_id"], "DATE_PAUSE", "resumed_at < paused_at")

    for r in data["resolutions"]:
        if r.get("issue_type"):
            continue
        cmp = complaints.get(r["complaint_id"])
        if cmp and _dt(r["resolved_at"]) < _dt(cmp["created_at"]):
            _fail(errors, "Resolution", r["resolution_id"], "DATE_RESOLUTION", "resolved_at < complaint created_at")

    for sv in surveys:
        if sv.get("issue_type"):
            continue
        res = resolutions.get(sv["complaint_id"])
        if res and _dt(sv["submitted_at"]) < _dt(res["resolved_at"]):
            _fail(errors, "Survey", sv["survey_id"], "DATE_SURVEY", "submitted_at < resolved_at")

    # ---------------------------------------------------------------------------
    # Lifecycle: reopened complaint must have a parent
    # ---------------------------------------------------------------------------
    for c in data["complaints"]:
        if not c.get("issue_type") and c["is_reopened"] and not c["parent_complaint_id"]:
            _fail(errors, "Complaint", c["complaint_id"], "LIFECYCLE_REOPEN", "is_reopened=True but no parent_complaint_id")

    # ---------------------------------------------------------------------------
    # SLA arithmetic  (tolerance: < 1 minute)
    # ---------------------------------------------------------------------------
    for s in sla_clocks:
        if s.get("issue_type"):
            continue
        expected = _dt(s["started_at"]) + timedelta(hours=s["sla_hours"])
        diff_min = abs((expected - _dt(s["deadline_at"])).total_seconds() / 60)
        if diff_min > 1:
            _fail(errors, "SLAClock", s["sla_id"], "ARITH_SLA", "deadline_at mismatch by %.1f min" % diff_min)

    # ---------------------------------------------------------------------------
    # Priority reproducibility
    # ---------------------------------------------------------------------------
    for c in data["complaints"]:
        if c.get("issue_type"):
            continue
        prod = products.get(c["product_id"])
        cust = customers.get(c["customer_id"])
        if not prod or not cust:
            continue
        expected = priority_from_rules(
            c["is_safety_issue"], cust["is_vulnerable"],
            c["sentiment"], c["order_value"],
            c["recurrence_count"], c["category_id"] == "CAT-09",
        )
        if expected != c["priority"]:
            _fail(errors, "Complaint", c["complaint_id"], "PRIORITY_RULE",
                  "Expected %s, got %s" % (expected, c["priority"]))

    return errors


def summarise(errors):
    counts = Counter(e["rule"] for e in errors)
    print("\n[VALIDATION] Total issues: %d" % len(errors))
    for rule, cnt in counts.most_common():
        print("  %s: %d" % (rule, cnt))
    real = [e for e in errors if "EDGE" not in e.get("id", "")]
    print("[VALIDATION] Real data issues (non-edge): %d" % len(real))
    return len(real) == 0
