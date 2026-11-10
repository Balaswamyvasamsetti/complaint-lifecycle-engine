# generator.py — Deterministic synthetic data generator for Complaint Management System
# Fixed seed: 20261022 | Baseline: 5,000 customers, 8,000 orders, 2,000 complaints, 6,000 messages

import random
from datetime import datetime, timedelta
from schema import (
    CATEGORIES, PRIORITY_RULES, TEAMS, AGENTS,
    CHANNELS, SENTIMENTS, ORDER_STATUSES, RESOLUTION_TYPES,
    SURVEY_RATINGS, SENDER_TYPES, PRODUCTS, CUSTOMER_SEGMENTS
)

SEED = 20261022
BASE_DATE = datetime(2026, 1, 1, 8, 0, 0)
END_DATE = datetime(2026, 6, 30, 18, 0, 0)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _rand_date(start=BASE_DATE, end=END_DATE):
    delta = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, max(0, delta)))


def _rand_email(first, last, idx):
    domains = ["gmail.com", "yahoo.com", "outlook.com", "enterprise.co.uk", "company.org"]
    return "%s.%s%d@%s" % (first.lower(), last.lower(), idx, random.choice(domains))


def _rand_phone():
    return "+44" + "".join(str(random.randint(0, 9)) for _ in range(10))


def priority_from_rules(is_safety, is_vulnerable, sentiment, order_value, recurrence, is_fraud):
    """
    Deterministic rule engine for complaint priority:
    - CRITICAL: Safety issue OR fraud OR vulnerable customer
    - HIGH: (Negative sentiment AND order_value > 500) OR recurrence >= 3
    - MEDIUM: Negative sentiment OR (100 <= order_value <= 500)
    - LOW: Neutral/positive sentiment AND order_value < 100
    """
    if is_safety or is_vulnerable or is_fraud:
        return "CRITICAL"
    if (sentiment == "Negative" and order_value > 500) or recurrence >= 3:
        return "HIGH"
    if sentiment == "Negative" or (100.0 <= order_value <= 500.0):
        return "MEDIUM"
    return "LOW"


def _sla_hours_for(category_id, priority):
    base = next(c["default_sla_hours"] for c in CATEGORIES if c["category_id"] == category_id)
    mult = next(r["sla_multiplier"] for r in PRIORITY_RULES if r["priority"] == priority)
    return max(1.0, round(base * mult, 2))


def _severity_from_priority(priority):
    return {"CRITICAL": "Critical", "HIGH": "High", "MEDIUM": "Medium", "LOW": "Low"}[priority]


# ---------------------------------------------------------------------------
# Name and text pools
# ---------------------------------------------------------------------------

_FIRST_NAMES = [
    "James", "Oliver", "Harry", "Jack", "George", "Noah", "Charlie", "Jacob", "Alfie", "Freddie",
    "Amelia", "Olivia", "Isla", "Emily", "Poppy", "Ava", "Isabella", "Jessica", "Lily", "Sophie",
    "Alexander", "Charlotte", "Daniel", "Grace", "Liam", "Mia", "William", "Zoe", "Thomas", "Ella"
]

_LAST_NAMES = [
    "Smith", "Jones", "Williams", "Taylor", "Brown", "Davies", "Evans", "Wilson",
    "Thomas", "Roberts", "Johnson", "White", "Martin", "Anderson", "Thompson", "Garcia",
    "Martinez", "Robinson", "Clark", "Lewis", "Walker", "Hall", "Allen", "Young", "King"
]

_CUSTOMER_MSGS = [
    "I am very unhappy with my order. It has been over a week without any tracking update.",
    "The product stopped functioning right after initial setup and sparked.",
    "I have requested a refund two weeks ago and have received no confirmation.",
    "The delivery arrived significantly damaged with packaging torn apart.",
    "I want to escalate this matter to a senior manager immediately.",
    "Please resolve this issue as soon as possible, it is urgent.",
    "I was charged twice on my credit card for this transaction.",
    "The wrong item was delivered to my address.",
    "Customer support promised a call back yesterday which never happened.",
    "The item is defective and constitutes a serious safety hazard.",
]

_AGENT_MSGS = [
    "Thank you for contacting customer support. We are actively investigating your case.",
    "We sincerely apologise for the inconvenience and frustration caused.",
    "Your complaint has been escalated to our specialist resolution team.",
    "We have processed your refund. Please allow 3 to 5 business days for banking clearance.",
    "Could you please provide photographic evidence of the damaged product?",
    "We have re-routed your replacement shipment with priority express delivery.",
    "Our technical engineering team is reviewing the malfunction report.",
    "We have updated the priority level and assigned your case to a tier-2 specialist.",
]

_SYSTEM_MSGS = [
    "Complaint record created and initial triage completed.",
    "Case assigned to specialized support team based on priority classification.",
    "SLA deadline warning: 2 hours remaining before breach.",
    "SLA clock paused: waiting for customer response.",
    "SLA clock resumed upon customer interaction.",
    "Automated escalation triggered due to critical priority policy.",
    "Resolution record committed and verification survey dispatched.",
    "Complaint reopened following customer reply on closed case.",
]

_FEEDBACK_TEXTS = [
    "Very satisfied with the speed and courtesy of the resolution.",
    "The assigned agent was knowledgeable and empathetic.",
    "It took longer than expected, but the outcome was fair and acceptable.",
    "Extremely dissatisfied with the response time and lack of accountability.",
    "Excellent customer care. The replacement item was shipped promptly.",
    "Adequate service, though multiple follow-ups were necessary.",
    "Quick and professional handling of a stressful situation.",
    "Issue resolved satisfactorily. Appreciate the refund processing.",
]

# ---------------------------------------------------------------------------
# Generators for Master & Transaction Data
# ---------------------------------------------------------------------------

def generate_customers(n):
    customers = []
    used_emails = set()
    for i in range(1, n + 1):
        first = random.choice(_FIRST_NAMES)
        last = random.choice(_LAST_NAMES)
        email = _rand_email(first, last, i)
        while email in used_emails:
            email = _rand_email(first, last, i + random.randint(1000, 99999))
        used_emails.add(email)
        reg_date = _rand_date(BASE_DATE - timedelta(days=730), BASE_DATE)
        customers.append({
            "customer_id": "CUS-%06d" % i,
            "first_name": first,
            "last_name": last,
            "email": email,
            "phone": _rand_phone(),
            "segment": random.choices(CUSTOMER_SEGMENTS, weights=[15, 55, 30])[0],
            "is_vulnerable": random.random() < 0.05,
            "registration_date": reg_date.strftime("%Y-%m-%d"),
            "lifetime_value": round(random.uniform(25.0, 5000.0), 2),
        })
    return customers


def generate_orders(customers, n):
    orders = []
    cust_ids = [c["customer_id"] for c in customers]
    for i in range(1, n + 1):
        cust_id = random.choice(cust_ids)
        product = random.choice(PRODUCTS)
        qty = random.randint(1, 4)
        order_date = _rand_date(BASE_DATE, END_DATE - timedelta(days=10))
        delivered = random.random() > 0.15
        delivery_date = order_date + timedelta(days=random.randint(1, 10)) if delivered else None
        status = random.choices(ORDER_STATUSES, weights=[5, 10, 20, 50, 10, 5])[0]
        if status == "Delivered" and not delivery_date:
            delivery_date = order_date + timedelta(days=3)
        orders.append({
            "order_id": "ORD-2026-%06d" % i,
            "customer_id": cust_id,
            "product_id": product["product_id"],
            "order_date": order_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "order_value": round(product["price"] * qty, 2),
            "quantity": qty,
            "status": status,
            "delivery_date": delivery_date.strftime("%Y-%m-%dT%H:%M:%S") if delivery_date else "",
        })
    return orders


def generate_complaints(customers, orders, n):
    complaints = []
    cust_map = {c["customer_id"]: c for c in customers}
    prod_map = {p["product_id"]: p for p in PRODUCTS}
    cust_ids = [c["customer_id"] for c in customers]
    recurrence_counter = {}
    existing_ids = []

    for i in range(1, n + 1):
        cmp_id = "CMP-2026-%06d" % i
        cust_id = random.choice(cust_ids)
        cust = cust_map[cust_id]

        cust_orders = [o for o in orders if o["customer_id"] == cust_id]
        order = random.choice(cust_orders) if cust_orders else None

        product_id = order["product_id"] if order else random.choice(PRODUCTS)["product_id"]
        product = prod_map[product_id]
        order_value = order["order_value"] if order else round(random.uniform(20.0, 800.0), 2)

        category = random.choice(CATEGORIES)
        channel = random.choice(CHANNELS)
        sentiment = random.choices(SENTIMENTS, weights=[10, 25, 65])[0]

        recurrence_counter[cust_id] = recurrence_counter.get(cust_id, 0) + 1
        recurrence = recurrence_counter[cust_id]

        is_safety = (category["category_id"] == "CAT-04") or (product["safety_risk"] and (random.random() < 0.65))
        is_vulnerable = cust["is_vulnerable"]
        is_fraud = category["category_id"] == "CAT-09"

        if is_safety:
            category = next(c for c in CATEGORIES if c["category_id"] == "CAT-04")

        priority = priority_from_rules(is_safety, is_vulnerable, sentiment, order_value, recurrence, is_fraud)
        severity = _severity_from_priority(priority)

        # Baseline created timestamp
        created_at = _rand_date(BASE_DATE, END_DATE - timedelta(days=2))
        updated_at = created_at + timedelta(hours=random.randint(1, 48))

        # Reopened complaints (~5% of volume when prior complaints exist)
        is_reopened = (random.random() < 0.05) and (len(existing_ids) > 0)
        parent_cmp_id = random.choice(existing_ids) if is_reopened else ""

        if is_reopened:
            status = "Reopened"
        else:
            status = random.choices(
                ["Open", "In Progress", "Pending Customer", "Escalated", "Resolved", "Closed"],
                weights=[12, 22, 16, 10, 22, 18],
            )[0]

        complaints.append({
            "complaint_id": cmp_id,
            "customer_id": cust_id,
            "order_id": order["order_id"] if order else "",
            "product_id": product_id,
            "category_id": category["category_id"],
            "category_name": category["name"],
            "channel": channel,
            "severity": severity,
            "priority": priority,
            "sentiment": sentiment,
            "status": status,
            "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%S"),
            "updated_at": updated_at.strftime("%Y-%m-%dT%H:%M:%S"),
            "recurrence_count": recurrence,
            "is_safety_issue": is_safety,
            "is_reopened": is_reopened,
            "parent_complaint_id": parent_cmp_id,
            "order_value": order_value,
        })
        existing_ids.append(cmp_id)

    return complaints


def generate_assignments(complaints):
    assignments = []
    asn_idx = 1
    for cmp in complaints:
        team = random.choice(TEAMS[cmp["priority"]])
        agent = random.choice(AGENTS[team])
        assigned_at = (
            datetime.strptime(cmp["created_at"], "%Y-%m-%dT%H:%M:%S")
            + timedelta(minutes=random.randint(5, 45))
        )
        assignments.append({
            "assignment_id": "ASN-%06d" % asn_idx,
            "complaint_id": cmp["complaint_id"],
            "team": team,
            "agent_id": agent,
            "assigned_at": assigned_at.strftime("%Y-%m-%dT%H:%M:%S"),
            "is_current": True,
            "reason": "Initial priority routing to %s" % team,
        })
        asn_idx += 1

        # Escalated complaints get a secondary reassignment event
        if cmp["status"] == "Escalated":
            esc_team = "Escalations" if "Escalations" in TEAMS.get(cmp["priority"], []) else "Senior-Support"
            esc_agent = random.choice(AGENTS.get(esc_team, ["AGT-SS-01"]))
            esc_at = assigned_at + timedelta(hours=random.randint(4, 24))
            assignments[-1]["is_current"] = False
            assignments.append({
                "assignment_id": "ASN-%06d" % asn_idx,
                "complaint_id": cmp["complaint_id"],
                "team": esc_team,
                "agent_id": esc_agent,
                "assigned_at": esc_at.strftime("%Y-%m-%dT%H:%M:%S"),
                "is_current": True,
                "reason": "Escalated to senior management tier",
            })
            asn_idx += 1

    return assignments


def generate_sla_clocks(complaints):
    sla_records = []
    for i, cmp in enumerate(complaints, 1):
        sla_h = _sla_hours_for(cmp["category_id"], cmp["priority"])
        started_at = datetime.strptime(cmp["created_at"], "%Y-%m-%dT%H:%M:%S")
        deadline = started_at + timedelta(hours=sla_h)
        updated_at = datetime.strptime(cmp["updated_at"], "%Y-%m-%dT%H:%M:%S")

        is_breached = (updated_at > deadline) and (cmp["status"] not in ["Resolved", "Closed"])
        breached_at = deadline.strftime("%Y-%m-%dT%H:%M:%S") if is_breached else ""

        paused_at = ""
        resumed_at = ""
        pause_reason = ""
        if cmp["status"] == "Pending Customer" and random.random() < 0.6:
            offset = max(1, int(sla_h * 0.25))
            pause_dt = started_at + timedelta(hours=offset)
            paused_at = pause_dt.strftime("%Y-%m-%dT%H:%M:%S")
            resume_dt = pause_dt + timedelta(hours=random.randint(2, 18))
            resumed_at = resume_dt.strftime("%Y-%m-%dT%H:%M:%S")
            pause_reason = "Awaiting supplementary documentation from customer"

        if is_breached:
            sla_status = "Breached"
        elif cmp["status"] in ["Resolved", "Closed"]:
            sla_status = "Met"
        elif paused_at and not resumed_at:
            sla_status = "Paused"
        else:
            sla_status = "Active"

        sla_records.append({
            "sla_id": "SLA-%s" % cmp["complaint_id"],
            "complaint_id": cmp["complaint_id"],
            "sla_hours": sla_h,
            "started_at": started_at.strftime("%Y-%m-%dT%H:%M:%S"),
            "deadline_at": deadline.strftime("%Y-%m-%dT%H:%M:%S"),
            "paused_at": paused_at,
            "resumed_at": resumed_at,
            "pause_reason": pause_reason,
            "is_breached": is_breached,
            "breached_at": breached_at,
            "status": sla_status,
        })
    return sla_records


def generate_messages(complaints, total):
    msg_counts = {c["complaint_id"]: 0 for c in complaints}
    cmp_ids = [c["complaint_id"] for c in complaints]
    weights = [
        4 if c["status"] in ["Resolved", "Closed"] else
        3 if c["status"] in ["In Progress", "Escalated"] else 1
        for c in complaints
    ]
    for cmp_id in random.choices(cmp_ids, weights=weights, k=total):
        msg_counts[cmp_id] += 1

    cmp_map = {c["complaint_id"]: c for c in complaints}
    messages = []
    msg_idx = 1
    for cmp_id in sorted(msg_counts.keys()):
        count = msg_counts[cmp_id]
        if count == 0:
            continue
        base_time = datetime.strptime(cmp_map[cmp_id]["created_at"], "%Y-%m-%dT%H:%M:%S")
        for j in range(1, count + 1):
            sender = random.choices(SENDER_TYPES, weights=[40, 45, 15])[0]
            text = random.choice(
                _CUSTOMER_MSGS if sender == "Customer" else
                _AGENT_MSGS if sender == "Agent" else
                _SYSTEM_MSGS
            )
            sent_at = base_time + timedelta(hours=random.randint(0, 48), minutes=j * 15)
            messages.append({
                "message_id": "MSG-%s-%03d" % (cmp_id, j),
                "complaint_id": cmp_id,
                "sender_type": sender,
                "message_text": text,
                "sent_at": sent_at.strftime("%Y-%m-%dT%H:%M:%S"),
                "is_internal": sender == "Agent" and (random.random() < 0.25),
            })
            msg_idx += 1
    return messages


def generate_resolutions(complaints, assignments):
    asn_map = {a["complaint_id"]: a for a in assignments if a.get("is_current")}
    resolutions = []
    res_idx = 1
    for cmp in complaints:
        if cmp["status"] not in ["Resolved", "Closed"]:
            continue
        created_at = datetime.strptime(cmp["created_at"], "%Y-%m-%dT%H:%M:%S")
        resolved_at = created_at + timedelta(hours=random.randint(2, 72))
        agent_id = asn_map.get(cmp["complaint_id"], {}).get("agent_id", "AGT-GS-01")
        res_type = random.choice(RESOLUTION_TYPES)
        refund_amt = round(random.uniform(10.0, cmp["order_value"]), 2) if res_type == "Refund" else 0.0
        resolutions.append({
            "resolution_id": "RES-%s" % cmp["complaint_id"],
            "complaint_id": cmp["complaint_id"],
            "resolution_type": res_type,
            "resolved_by": agent_id,
            "resolved_at": resolved_at.strftime("%Y-%m-%dT%H:%M:%S"),
            "notes": "Complaint resolved via %s with verified customer sign-off." % res_type,
            "refund_amount": refund_amt,
        })
        res_idx += 1
    return resolutions


def generate_surveys(resolutions):
    surveys = []
    for i, res in enumerate(resolutions, 1):
        resolved_at = datetime.strptime(res["resolved_at"], "%Y-%m-%dT%H:%M:%S")
        submitted_at = resolved_at + timedelta(hours=random.randint(1, 48))
        rating = random.choices(SURVEY_RATINGS, weights=[6, 10, 18, 36, 30])[0]
        nps = min(10, max(0, (rating - 1) * 2 + random.randint(0, 2)))
        surveys.append({
            "survey_id": "SRV-%06d" % i,
            "complaint_id": res["complaint_id"],
            "rating": rating,
            "feedback_text": random.choice(_FEEDBACK_TEXTS),
            "submitted_at": submitted_at.strftime("%Y-%m-%dT%H:%M:%S"),
            "nps_score": nps,
        })
    return surveys


def generate_events(complaints, assignments, sla_clocks, resolutions, surveys):
    """
    Persist state changes as explicit records/events where relevant; sequential zero-padded EVT-000001 IDs.
    """
    raw_events = []

    for cmp in complaints:
        cmp_id = cmp["complaint_id"]
        c_time = cmp["created_at"]
        raw_events.append({
            "complaint_id": cmp_id,
            "event_type": "COMPLAINT_CREATED",
            "actor": "Business Requester",
            "old_state": "",
            "new_state": "Open",
            "event_timestamp": c_time,
            "details": "Complaint received via %s and triaged as %s priority." % (cmp["channel"], cmp["priority"])
        })

    for a in assignments:
        raw_events.append({
            "complaint_id": a["complaint_id"],
            "event_type": "ASSIGNED",
            "actor": "System Administrator",
            "old_state": "",
            "new_state": a["team"],
            "event_timestamp": a["assigned_at"],
            "details": "Assigned to %s (Agent: %s). Reason: %s" % (a["team"], a["agent_id"], a.get("reason", ""))
        })

    for r in resolutions:
        raw_events.append({
            "complaint_id": r["complaint_id"],
            "event_type": "RESOLVED",
            "actor": r["resolved_by"],
            "old_state": "In Progress",
            "new_state": "Resolved",
            "event_timestamp": r["resolved_at"],
            "details": "Resolved via %s. Refund: £%.2f" % (r["resolution_type"], r.get("refund_amount") or 0.0)
        })

    for s in surveys:
        raw_events.append({
            "complaint_id": s["complaint_id"],
            "event_type": "SURVEY_SUBMITTED",
            "actor": "Business Requester",
            "old_state": "Resolved",
            "new_state": "Closed",
            "event_timestamp": s["submitted_at"],
            "details": "Customer feedback recorded: CSAT=%d, NPS=%d" % (s["rating"], s.get("nps_score") or 0)
        })

    raw_events.sort(key=lambda e: e["event_timestamp"])

    events = []
    for idx, e in enumerate(raw_events, 1):
        events.append({
            "event_id": "EVT-%06d" % idx,
            "complaint_id": e["complaint_id"],
            "event_type": e["event_type"],
            "actor": e["actor"],
            "old_state": e["old_state"],
            "new_state": e["new_state"],
            "event_timestamp": e["event_timestamp"],
            "details": e["details"]
        })

    return events


# ---------------------------------------------------------------------------
# Labelled Edge Cases / 6 Mandatory Negative Test Cases
# ---------------------------------------------------------------------------

def inject_edge_cases(complaints, resolutions, sla_clocks, surveys, assignments):
    """
    Injects the 6 mandatory negative test cases using strictly sequential,
    zero-padded IDs, with comprehensive metadata for the isolated ground truth dataset.
    """
    anomalies = []

    # 1. Complaint without customer (Referential Integrity defect)
    # Designated to sequential ticket CMP-2026-000001
    c1 = complaints[0]
    c1["customer_id"] = ""
    c1["order_id"] = ""
    c1["issue_type"] = "missing_customer"
    anomalies.append({
        "complaint_id": c1["complaint_id"],
        "issue_type": "missing_customer",
        "anomaly_category": "Referential Integrity",
        "description": "Complaint submitted with null/empty customer_id reference",
        "entity_affected": "complaints",
        "rule_violated": "FK_CUSTOMER_MISSING"
    })

    # 2. Resolution before complaint (Chronological timestamp inversion)
    # Designated to sequential ticket CMP-2026-000002
    c2 = complaints[1]
    c2["status"] = "Resolved"
    created2 = datetime.strptime(c2["created_at"], "%Y-%m-%dT%H:%M:%S")
    # Inverted resolution timestamp: 6 hours BEFORE complaint was filed
    inverted_res_at = (created2 - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%S")
    
    r2 = next((r for r in resolutions if r["complaint_id"] == c2["complaint_id"]), None)
    if not r2:
        r2 = {
            "resolution_id": "RES-%s" % c2["complaint_id"],
            "complaint_id": c2["complaint_id"],
            "resolution_type": "Refund",
            "resolved_by": "AGT-GS-01",
            "resolved_at": inverted_res_at,
            "notes": "Full refund authorized by caseworker.",
            "refund_amount": 50.0,
            "issue_type": "resolution_before_complaint",
        }
        resolutions.append(r2)
    else:
        r2["resolution_id"] = "RES-%s" % c2["complaint_id"]
        r2["resolved_at"] = inverted_res_at
        r2["issue_type"] = "resolution_before_complaint"

    anomalies.append({
        "complaint_id": c2["complaint_id"],
        "issue_type": "resolution_before_complaint",
        "anomaly_category": "Chronological Inversion",
        "description": "Resolution timestamp precedes complaint created_at",
        "entity_affected": "resolutions",
        "rule_violated": "DATE_RESOLUTION_BEFORE_COMPLAINT"
    })

    # 3. SLA clock pauses incorrectly (SLA State Machine defect: paused without resume)
    # Designated to sequential ticket CMP-2026-000003
    c3 = complaints[2]
    s3 = next((s for s in sla_clocks if s["complaint_id"] == c3["complaint_id"]), None)
    if s3:
        s3["paused_at"] = s3["started_at"]
        s3["resumed_at"] = ""
        s3["status"] = "Paused"
        s3["pause_reason"] = "Awaiting supplementary documentation"
        s3["issue_type"] = "sla_pause_no_resume"
        anomalies.append({
            "complaint_id": c3["complaint_id"],
            "issue_type": "sla_pause_no_resume",
            "anomaly_category": "SLA State Machine",
            "description": "SLA clock paused indefinitely without resumption timestamp",
            "entity_affected": "sla_clocks",
            "rule_violated": "DATE_SLA_PAUSE_NO_RESUME"
        })

    # 4. Repeat issue not linked (Duplicate / Recurrence tracking failure)
    # Designated to sequential ticket CMP-2026-000004
    c4 = complaints[3]
    c4["recurrence_count"] = 3
    c4["parent_complaint_id"] = ""
    c4["issue_type"] = "repeat_not_linked"
    anomalies.append({
        "complaint_id": c4["complaint_id"],
        "issue_type": "repeat_not_linked",
        "anomaly_category": "Duplicate Detection",
        "description": "Repeat complaint (recurrence=3) without valid parent_complaint_id link",
        "entity_affected": "complaints",
        "rule_violated": "REPEAT_ISSUE_NOT_LINKED"
    })

    # 5. Critical safety issue assigned to a low-priority queue (Priority Classification defect)
    # Designated to sequential ticket CMP-2026-000005
    c5 = complaints[4]
    c5["category_id"] = "CAT-04"
    c5["category_name"] = "Product Safety"
    c5["is_safety_issue"] = True
    c5["priority"] = "LOW"
    c5["severity"] = "Low"
    c5["issue_type"] = "safety_low_priority"

    a5 = next((a for a in assignments if a["complaint_id"] == c5["complaint_id"] and a.get("is_current")), None)
    if a5:
        a5["team"] = "General-Support"
        a5["agent_id"] = "AGT-GS-01"
        a5["reason"] = "Standard initial queue routing"
        a5["issue_type"] = "safety_low_priority"

    anomalies.append({
        "complaint_id": c5["complaint_id"],
        "issue_type": "safety_low_priority",
        "anomaly_category": "Priority Rule Engine",
        "description": "Critical product safety hazard misclassified and assigned to low-priority General-Support queue",
        "entity_affected": "complaints,assignments",
        "rule_violated": "PRIORITY_SAFETY_ANOMALY"
    })

    # 6. Survey submitted before closure (Lifecycle State Flow defect)
    # Designated to sequential ticket CMP-2026-000006
    c6 = complaints[5]
    c6["status"] = "Resolved"
    r6 = next((r for r in resolutions if r["complaint_id"] == c6["complaint_id"]), None)
    if not r6:
        r6 = {
            "resolution_id": "RES-%s" % c6["complaint_id"],
            "complaint_id": c6["complaint_id"],
            "resolution_type": "Replacement",
            "resolved_by": "AGT-SS-01",
            "resolved_at": (datetime.strptime(c6["created_at"], "%Y-%m-%dT%H:%M:%S") + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S"),
            "notes": "Resolved with replacement item shipped",
            "refund_amount": 0.0,
        }
        resolutions.append(r6)
    else:
        r6["resolution_id"] = "RES-%s" % c6["complaint_id"]

    res6_at = datetime.strptime(r6["resolved_at"], "%Y-%m-%dT%H:%M:%S")
    premature_survey_at = (res6_at - timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%S")

    s6 = next((s for s in surveys if s["complaint_id"] == c6["complaint_id"]), None)
    if not s6:
        s6 = {
            "survey_id": "SRV-%06d" % (len(surveys) + 1),
            "complaint_id": c6["complaint_id"],
            "rating": 4,
            "feedback_text": "Case resolved swiftly.",
            "submitted_at": premature_survey_at,
            "nps_score": 8,
            "issue_type": "survey_before_closure",
        }
        surveys.append(s6)
    else:
        s6["submitted_at"] = premature_survey_at
        s6["issue_type"] = "survey_before_closure"

    anomalies.append({
        "complaint_id": c6["complaint_id"],
        "issue_type": "survey_before_closure",
        "anomaly_category": "Lifecycle State Flow",
        "description": "Customer CSAT survey recorded prior to case resolution timestamp",
        "entity_affected": "surveys",
        "rule_violated": "DATE_SURVEY_BEFORE_CLOSURE"
    })

    return anomalies


# ---------------------------------------------------------------------------
# Master Generation Entrypoint
# ---------------------------------------------------------------------------

def generate_all(scale=1.0):
    random.seed(SEED)
    n_cust = int(5000 * scale)
    n_ord = int(8000 * scale)
    n_cmp = int(2000 * scale)
    n_msg = int(6000 * scale)

    print("[GEN] Generating baseline scale %.2fx (Seed: %d)..." % (scale, SEED))
    print("      Customers=%d, Orders=%d, Complaints=%d, Messages=%d" % (n_cust, n_ord, n_cmp, n_msg))

    customers = generate_customers(n_cust)
    orders = generate_orders(customers, n_ord)
    complaints = generate_complaints(customers, orders, n_cmp)
    assignments = generate_assignments(complaints)
    sla_clocks = generate_sla_clocks(complaints)
    messages = generate_messages(complaints, n_msg)
    resolutions = generate_resolutions(complaints, assignments)
    surveys = generate_surveys(resolutions)
    events = generate_events(complaints, assignments, sla_clocks, resolutions, surveys)
    anomalies = inject_edge_cases(complaints, resolutions, sla_clocks, surveys, assignments)

    return {
        "customers": customers,
        "products": PRODUCTS,
        "orders": orders,
        "categories": CATEGORIES,
        "priority_rules": PRIORITY_RULES,
        "complaints": complaints,
        "complaint_events": events,
        "assignments": assignments,
        "sla_clocks": sla_clocks,
        "messages": messages,
        "resolutions": resolutions,
        "surveys": surveys,
        "anomalies": anomalies,
    }
