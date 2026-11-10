# generator.py — Synthetic data generation for all entities
# Seed: 20261022 | Full scale: 5000 customers, 8000 orders, 2000 complaints, 6000 messages

import random
from datetime import datetime, timedelta
from schema import (
    CATEGORIES, PRIORITY_RULES, TEAMS, AGENTS,
    CHANNELS, SENTIMENTS, ORDER_STATUSES, RESOLUTION_TYPES, SURVEY_RATINGS, PRODUCTS
)

SEED      = 20261022
BASE_DATE = datetime(2024, 1, 1)
END_DATE  = datetime(2026, 6, 30)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rand_date(start=BASE_DATE, end=END_DATE):
    delta = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, delta))

def _rand_email(first, last, idx):
    domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "example.com"]
    return "%s.%s%d@%s" % (first.lower(), last.lower(), idx, random.choice(domains))

def _rand_phone():
    return "+44" + "".join(str(random.randint(0, 9)) for _ in range(10))

def priority_from_rules(is_safety, is_vulnerable, sentiment, order_value, recurrence, is_fraud):
    if is_safety or is_vulnerable or is_fraud:
        return "CRITICAL"
    if (sentiment == "Negative" and order_value > 500) or recurrence >= 3:
        return "HIGH"
    if sentiment == "Negative" or 100 <= order_value <= 500:
        return "MEDIUM"
    return "LOW"

def _sla_hours_for(category_id, priority):
    base = next(c["default_sla_hours"] for c in CATEGORIES if c["category_id"] == category_id)
    mult = next(r["sla_multiplier"]     for r in PRIORITY_RULES if r["priority"] == priority)
    return max(1.0, base * mult)

def _severity_from_priority(priority):
    return {"CRITICAL": "Critical", "HIGH": "High", "MEDIUM": "Medium", "LOW": "Low"}[priority]

# ---------------------------------------------------------------------------
# Name pools
# ---------------------------------------------------------------------------

_FIRST_NAMES = [
    "James", "Oliver", "Harry", "Jack",  "George", "Noah",  "Charlie", "Jacob", "Alfie",    "Freddie",
    "Amelia","Olivia", "Isla",  "Emily", "Poppy",  "Ava",   "Isabella","Jessica","Lily",    "Sophie",
]
_LAST_NAMES = [
    "Smith",  "Jones",    "Williams", "Taylor",   "Brown",    "Davies",   "Evans",    "Wilson",
    "Thomas", "Roberts",  "Johnson",  "White",    "Martin",   "Anderson", "Thompson", "Garcia",
    "Martinez","Robinson","Clark",    "Lewis",
]

_CUSTOMER_MSGS = [
    "I am very unhappy with my order.",
    "This product stopped working after one day.",
    "I have not received my refund yet.",
    "The delivery was late and the item was damaged.",
    "I want to escalate this issue immediately.",
    "Please resolve this as soon as possible.",
    "I have been waiting for over a week.",
    "This is unacceptable service.",
]
_AGENT_MSGS = [
    "Thank you for contacting us. We are looking into this.",
    "We apologise for the inconvenience caused.",
    "Your case has been escalated to our specialist team.",
    "We have processed your refund. Please allow 3-5 business days.",
    "Could you please provide your order number?",
    "We have assigned your case to a senior agent.",
    "Your complaint has been logged and we will respond within 24 hours.",
]
_SYSTEM_MSGS = [
    "Complaint status updated to In Progress.",
    "SLA deadline approaching in 2 hours.",
    "Complaint escalated due to SLA breach.",
    "Resolution submitted by agent.",
    "Survey sent to customer.",
    "Complaint reopened by customer.",
]
_FEEDBACK_TEXTS = [
    "Very satisfied with the resolution.",
    "The agent was helpful and professional.",
    "Took too long but eventually resolved.",
    "Not happy with the outcome.",
    "Excellent service, will shop again.",
    "Average experience, could be better.",
    "The issue was resolved quickly.",
    "I had to follow up multiple times.",
]

# ---------------------------------------------------------------------------
# Master / reference tables
# ---------------------------------------------------------------------------

def generate_customers(n):
    customers   = []
    used_emails = set()
    for i in range(1, n + 1):
        first = random.choice(_FIRST_NAMES)
        last  = random.choice(_LAST_NAMES)
        email = _rand_email(first, last, i)
        while email in used_emails:
            email = _rand_email(first, last, i + random.randint(1000, 9999))
        used_emails.add(email)
        reg_date = _rand_date(BASE_DATE, END_DATE - timedelta(days=30))
        customers.append({
            "customer_id":       "CUS-%06d" % i,
            "first_name":        first,
            "last_name":         last,
            "email":             email,
            "phone":             _rand_phone(),
            "segment":           random.choices(["Premium", "Standard", "Basic"], weights=[15, 55, 30])[0],
            "is_vulnerable":     random.random() < 0.05,
            "registration_date": reg_date.strftime("%Y-%m-%d"),
            "lifetime_value":    round(random.uniform(10, 5000), 2),
        })
    return customers


def generate_orders(customers, n):
    orders   = []
    cust_ids = [c["customer_id"] for c in customers]
    for i in range(1, n + 1):
        cust_id = random.choice(cust_ids)
        product = random.choice(PRODUCTS)
        qty     = random.randint(1, 5)
        o_date  = _rand_date()
        d_date  = o_date + timedelta(days=random.randint(1, 14)) if random.random() > 0.1 else None
        orders.append({
            "order_id":      "ORD-%d-%06d" % (o_date.year, i),
            "customer_id":   cust_id,
            "product_id":    product["product_id"],
            "order_date":    o_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "order_value":   round(product["price"] * qty, 2),
            "quantity":      qty,
            "status":        random.choices(ORDER_STATUSES, weights=[5, 10, 20, 50, 10, 5])[0],
            "delivery_date": d_date.strftime("%Y-%m-%dT%H:%M:%S") if d_date else "",
        })
    return orders

# ---------------------------------------------------------------------------
# Complaints
# ---------------------------------------------------------------------------

def generate_complaints(customers, orders, n):
    complaints        = []
    cust_map          = {c["customer_id"]: c for c in customers}
    prod_map          = {p["product_id"]:  p for p in PRODUCTS}
    cust_ids          = [c["customer_id"] for c in customers]
    recurrence_counter = {}
    existing_ids      = []

    for i in range(1, n + 1):
        year   = random.choice([2025, 2026])
        cmp_id = "CMP-%d-%06d" % (year, i)

        cust_id = random.choice(cust_ids)
        cust    = cust_map[cust_id]

        cust_orders = [o for o in orders if o["customer_id"] == cust_id]
        order       = random.choice(cust_orders) if cust_orders else None

        product_id  = order["product_id"] if order else random.choice(PRODUCTS)["product_id"]
        product     = prod_map[product_id]
        order_value = order["order_value"] if order else round(random.uniform(10, 1000), 2)

        category  = random.choice(CATEGORIES)
        channel   = random.choice(CHANNELS)
        sentiment = random.choices(SENTIMENTS, weights=[10, 30, 60])[0]

        recurrence_counter[cust_id] = recurrence_counter.get(cust_id, 0) + 1
        recurrence = recurrence_counter[cust_id]

        is_safety    = product["safety_risk"] and random.random() < 0.6
        is_vulnerable = cust["is_vulnerable"]
        is_fraud     = category["category_id"] == "CAT-09"

        if is_safety:
            category = next(c for c in CATEGORIES if c["category_id"] == "CAT-04")

        priority   = priority_from_rules(is_safety, is_vulnerable, sentiment, order_value, recurrence, is_fraud)
        severity   = _severity_from_priority(priority)
        created_at = _rand_date()
        updated_at = created_at + timedelta(hours=random.randint(0, 72))

        is_reopened   = random.random() < 0.08 and len(existing_ids) > 0
        parent_cmp_id = random.choice(existing_ids) if is_reopened else ""

        if is_reopened:
            status = "Reopened"
        else:
            status = random.choices(
                ["Open", "In Progress", "Pending Customer", "Escalated", "Resolved", "Closed"],
                weights=[10, 20, 15, 10, 25, 20],
            )[0]

        complaints.append({
            "complaint_id":        cmp_id,
            "customer_id":         cust_id,
            "order_id":            order["order_id"] if order else "",
            "product_id":          product_id,
            "category_id":         category["category_id"],
            "category_name":       category["name"],
            "channel":             channel,
            "severity":            severity,
            "priority":            priority,
            "sentiment":           sentiment,
            "status":              status,
            "created_at":          created_at.strftime("%Y-%m-%dT%H:%M:%S"),
            "updated_at":          updated_at.strftime("%Y-%m-%dT%H:%M:%S"),
            "recurrence_count":    recurrence,
            "is_safety_issue":     is_safety,
            "is_reopened":         is_reopened,
            "parent_complaint_id": parent_cmp_id,
            "order_value":         order_value,
        })
        existing_ids.append(cmp_id)

    return complaints

# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------

def generate_assignments(complaints):
    assignments = []
    for i, cmp in enumerate(complaints, 1):
        team  = random.choice(TEAMS[cmp["priority"]])
        agent = random.choice(AGENTS[team])
        assigned_at = (
            datetime.strptime(cmp["created_at"], "%Y-%m-%dT%H:%M:%S")
            + timedelta(minutes=random.randint(5, 60))
        )
        assignments.append({
            "assignment_id": "ASN-%06d" % i,
            "complaint_id":  cmp["complaint_id"],
            "team":          team,
            "agent_id":      agent,
            "assigned_at":   assigned_at.strftime("%Y-%m-%dT%H:%M:%S"),
            "is_current":    True,
            "reason":        "Initial assignment",
        })
    return assignments

# ---------------------------------------------------------------------------
# SLA Clocks
# ---------------------------------------------------------------------------

def generate_sla_clocks(complaints):
    sla_records = []
    for cmp in complaints:
        sla_h      = _sla_hours_for(cmp["category_id"], cmp["priority"])
        started_at = datetime.strptime(cmp["created_at"], "%Y-%m-%dT%H:%M:%S")
        deadline   = started_at + timedelta(hours=sla_h)
        updated_at = datetime.strptime(cmp["updated_at"], "%Y-%m-%dT%H:%M:%S")

        is_breached = updated_at > deadline and cmp["status"] not in ["Resolved", "Closed"]
        breached_at = deadline.strftime("%Y-%m-%dT%H:%M:%S") if is_breached else ""

        paused_at    = ""
        resumed_at   = ""
        pause_reason = ""
        if cmp["status"] == "Pending Customer" and random.random() < 0.5:
            offset     = random.randint(1, int(sla_h / 2) or 1)
            paused_at  = (started_at + timedelta(hours=offset)).strftime("%Y-%m-%dT%H:%M:%S")
            resumed_at = (started_at + timedelta(hours=offset + random.randint(1, 12))).strftime("%Y-%m-%dT%H:%M:%S")
            pause_reason = "Awaiting customer response"

        if is_breached:
            sla_status = "Breached"
        elif cmp["status"] in ["Resolved", "Closed"]:
            sla_status = "Met"
        elif paused_at and not resumed_at:
            sla_status = "Paused"
        else:
            sla_status = "Active"

        sla_records.append({
            "sla_id":       "SLA-%s" % cmp["complaint_id"],
            "complaint_id":  cmp["complaint_id"],
            "sla_hours":     sla_h,
            "started_at":    started_at.strftime("%Y-%m-%dT%H:%M:%S"),
            "deadline_at":   deadline.strftime("%Y-%m-%dT%H:%M:%S"),
            "paused_at":     paused_at,
            "resumed_at":    resumed_at,
            "pause_reason":  pause_reason,
            "is_breached":   is_breached,
            "breached_at":   breached_at,
            "status":        sla_status,
        })
    return sla_records

# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

def generate_messages(complaints, total):
    msg_counts = {c["complaint_id"]: 0 for c in complaints}
    cmp_ids    = [c["complaint_id"] for c in complaints]
    weights    = [
        4 if c["status"] in ["Resolved", "Closed"] else
        2 if c["status"] in ["In Progress", "Escalated"] else 1
        for c in complaints
    ]
    for cmp_id in random.choices(cmp_ids, weights=weights, k=total):
        msg_counts[cmp_id] += 1

    cmp_map  = {c["complaint_id"]: c for c in complaints}
    messages = []
    for cmp_id, count in msg_counts.items():
        if count == 0:
            continue
        base_time = datetime.strptime(cmp_map[cmp_id]["created_at"], "%Y-%m-%dT%H:%M:%S")
        for j in range(1, count + 1):
            sender = random.choices(["Customer", "Agent", "System"], weights=[40, 45, 15])[0]
            text   = random.choice(
                _CUSTOMER_MSGS if sender == "Customer" else
                _AGENT_MSGS    if sender == "Agent"    else
                _SYSTEM_MSGS
            )
            messages.append({
                "message_id":   "MSG-%s-%03d" % (cmp_id, j),
                "complaint_id": cmp_id,
                "sender_type":  sender,
                "message_text": text,
                "sent_at":      (base_time + timedelta(hours=random.randint(0, 48))).strftime("%Y-%m-%dT%H:%M:%S"),
                "is_internal":  sender == "Agent" and random.random() < 0.2,
            })
    return messages

# ---------------------------------------------------------------------------
# Resolutions
# ---------------------------------------------------------------------------

def generate_resolutions(complaints, assignments):
    asn_map     = {a["complaint_id"]: a for a in assignments}
    resolutions = []
    for cmp in complaints:
        if cmp["status"] not in ["Resolved", "Closed"]:
            continue
        created_at  = datetime.strptime(cmp["created_at"], "%Y-%m-%dT%H:%M:%S")
        resolved_at = created_at + timedelta(hours=random.randint(1, 96))
        agent_id    = asn_map.get(cmp["complaint_id"], {}).get("agent_id", "AGT-GS-01")
        res_type    = random.choice(RESOLUTION_TYPES)
        refund_amt  = round(random.uniform(5, cmp["order_value"]), 2) if res_type == "Refund" else ""
        resolutions.append({
            "resolution_id":   "RES-%s" % cmp["complaint_id"],
            "complaint_id":    cmp["complaint_id"],
            "resolution_type": res_type,
            "resolved_by":     agent_id,
            "resolved_at":     resolved_at.strftime("%Y-%m-%dT%H:%M:%S"),
            "notes":           "Resolved via %s." % res_type,
            "refund_amount":   refund_amt,
        })
    return resolutions

# ---------------------------------------------------------------------------
# Surveys
# ---------------------------------------------------------------------------

def generate_surveys(resolutions):
    surveys = []
    for i, res in enumerate(resolutions, 1):
        resolved_at  = datetime.strptime(res["resolved_at"], "%Y-%m-%dT%H:%M:%S")
        submitted_at = resolved_at + timedelta(hours=random.randint(1, 48))
        rating       = random.choices(SURVEY_RATINGS, weights=[5, 10, 20, 35, 30])[0]
        nps          = min(10, max(0, (rating - 1) * 2 + random.randint(0, 2)))
        surveys.append({
            "survey_id":     "SRV-%06d" % i,
            "complaint_id":  res["complaint_id"],
            "rating":        rating,
            "feedback_text": random.choice(_FEEDBACK_TEXTS),
            "submitted_at":  submitted_at.strftime("%Y-%m-%dT%H:%M:%S"),
            "nps_score":     nps,
        })
    return surveys

# ---------------------------------------------------------------------------
# Edge case injection  (labelled anomalies — never leak into input features)
# ---------------------------------------------------------------------------

def inject_edge_cases(complaints, resolutions, sla_clocks, surveys, assignments):
    anomalies = []

    # 1. Complaint with no customer_id
    ec1 = complaints[0].copy()
    ec1["complaint_id"] = "CMP-EDGE-000001"
    ec1["customer_id"]  = ""
    ec1["order_id"]     = ""
    ec1["issue_type"]   = "missing_customer"
    complaints.append(ec1)
    anomalies.append({
        "complaint_id": "CMP-EDGE-000001",
        "issue_type":   "missing_customer",
        "description":  "Complaint with no customer_id",
    })

    # 2. Resolution timestamp before complaint created_at
    base_cmp = next(c for c in complaints if c["status"] in ["Resolved", "Closed"])
    created  = datetime.strptime(base_cmp["created_at"], "%Y-%m-%dT%H:%M:%S")
    resolutions.append({
        "resolution_id":   "RES-CMP-EDGE-000002",
        "complaint_id":    base_cmp["complaint_id"],
        "resolution_type": "Refund",
        "resolved_by":     "AGT-GS-01",
        "resolved_at":     (created - timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%S"),
        "notes":           "EDGE: resolved before complaint created",
        "refund_amount":   50.0,
        "issue_type":      "resolution_before_complaint",
    })
    anomalies.append({
        "complaint_id": base_cmp["complaint_id"],
        "issue_type":   "resolution_before_complaint",
        "description":  "Resolution timestamp precedes complaint created_at",
    })

    # 3. SLA clock paused but never resumed
    ec3 = sla_clocks[5].copy()
    ec3["sla_id"]       = "SLA-CMP-EDGE-000003"
    ec3["complaint_id"] = complaints[10]["complaint_id"]
    ec3["paused_at"]    = ec3["started_at"]
    ec3["resumed_at"]   = ""
    ec3["status"]       = "Paused"
    ec3["issue_type"]   = "sla_pause_no_resume"
    sla_clocks.append(ec3)
    anomalies.append({
        "complaint_id": complaints[10]["complaint_id"],
        "issue_type":   "sla_pause_no_resume",
        "description":  "SLA paused but resumed_at is missing",
    })

    # 4. Critical safety issue assigned to low-priority queue
    ec4 = complaints[20].copy()
    ec4["complaint_id"]   = "CMP-EDGE-000004"
    ec4["is_safety_issue"] = True
    ec4["priority"]       = "LOW"
    ec4["issue_type"]     = "safety_low_priority"
    complaints.append(ec4)
    assignments.append({
        "assignment_id": "ASN-EDGE-000004",
        "complaint_id":  "CMP-EDGE-000004",
        "team":          "General-Support",
        "agent_id":      "AGT-GS-01",
        "assigned_at":   ec4["created_at"],
        "is_current":    True,
        "reason":        "EDGE: safety issue in low-priority queue",
        "issue_type":    "safety_low_priority",
    })
    anomalies.append({
        "complaint_id": "CMP-EDGE-000004",
        "issue_type":   "safety_low_priority",
        "description":  "Critical safety issue assigned to General-Support (low priority)",
    })

    # 5. Survey submitted before resolution
    base_res    = resolutions[0]
    resolved_at = datetime.strptime(base_res["resolved_at"], "%Y-%m-%dT%H:%M:%S")
    surveys.append({
        "survey_id":     "SRV-EDGE-000005",
        "complaint_id":  base_res["complaint_id"],
        "rating":        4,
        "feedback_text": "EDGE: survey before closure",
        "submitted_at":  (resolved_at - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%S"),
        "nps_score":     7,
        "issue_type":    "survey_before_closure",
    })
    anomalies.append({
        "complaint_id": base_res["complaint_id"],
        "issue_type":   "survey_before_closure",
        "description":  "Survey submitted before resolution/closure",
    })

    # 6. Repeat complaint with no parent link
    repeat = next((c for c in complaints if c["recurrence_count"] >= 2 and not c["parent_complaint_id"]), None)
    if repeat:
        anomalies.append({
            "complaint_id": repeat["complaint_id"],
            "issue_type":   "repeat_not_linked",
            "description":  "Repeat complaint (recurrence>=2) with no parent_complaint_id",
        })

    return anomalies

# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def generate_all(scale=1.0):
    random.seed(SEED)
    n_cust = int(5000 * scale)
    n_ord  = int(8000 * scale)
    n_cmp  = int(2000 * scale)
    n_msg  = int(6000 * scale)

    print("[GEN] Customers=%d, Orders=%d, Complaints=%d, Messages=%d" % (n_cust, n_ord, n_cmp, n_msg))

    customers   = generate_customers(n_cust)
    orders      = generate_orders(customers, n_ord)
    complaints  = generate_complaints(customers, orders, n_cmp)
    assignments = generate_assignments(complaints)
    sla_clocks  = generate_sla_clocks(complaints)
    messages    = generate_messages(complaints, n_msg)
    resolutions = generate_resolutions(complaints, assignments)
    surveys     = generate_surveys(resolutions)
    anomalies   = inject_edge_cases(complaints, resolutions, sla_clocks, surveys, assignments)

    return {
        "customers":      customers,
        "products":       PRODUCTS,
        "orders":         orders,
        "categories":     CATEGORIES,
        "priority_rules": PRIORITY_RULES,
        "complaints":     complaints,
        "assignments":    assignments,
        "sla_clocks":     sla_clocks,
        "messages":       messages,
        "resolutions":    resolutions,
        "surveys":        surveys,
        "anomalies":      anomalies,
    }
