# schema.py — Master reference data, allowed values and business rules

# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

CATEGORIES = [
    {"category_id": "CAT-01", "name": "Billing & Payment",      "default_sla_hours": 48},
    {"category_id": "CAT-02", "name": "Product Defect",         "default_sla_hours": 72},
    {"category_id": "CAT-03", "name": "Delivery / Logistics",   "default_sla_hours": 48},
    {"category_id": "CAT-04", "name": "Product Safety",         "default_sla_hours": 4},
    {"category_id": "CAT-05", "name": "Customer Service",       "default_sla_hours": 24},
    {"category_id": "CAT-06", "name": "Refund / Return",        "default_sla_hours": 72},
    {"category_id": "CAT-07", "name": "Missing Order",          "default_sla_hours": 24},
    {"category_id": "CAT-08", "name": "Technical / App Issue",  "default_sla_hours": 96},
    {"category_id": "CAT-09", "name": "Fraud / Unauthorized",   "default_sla_hours": 8},
    {"category_id": "CAT-10", "name": "General Enquiry",        "default_sla_hours": 120},
]

# ---------------------------------------------------------------------------
# Priority Rules  (PR-01 = highest, PR-04 = lowest)
# ---------------------------------------------------------------------------

PRIORITY_RULES = [
    {
        "rule_id":             "PR-01",
        "priority":            "CRITICAL",
        "level":               1,
        "description":         "Safety issue OR fraud OR vulnerable customer",
        "sla_multiplier":      0.25,
        "auto_escalate_hours": 2,
    },
    {
        "rule_id":             "PR-02",
        "priority":            "HIGH",
        "level":               2,
        "description":         "Negative sentiment AND order_value > 500 OR recurrence >= 3",
        "sla_multiplier":      0.5,
        "auto_escalate_hours": 8,
    },
    {
        "rule_id":             "PR-03",
        "priority":            "MEDIUM",
        "level":               3,
        "description":         "Negative sentiment OR order_value 100-500",
        "sla_multiplier":      1.0,
        "auto_escalate_hours": 24,
    },
    {
        "rule_id":             "PR-04",
        "priority":            "LOW",
        "level":               4,
        "description":         "Neutral/positive sentiment AND order_value < 100",
        "sla_multiplier":      1.5,
        "auto_escalate_hours": 72,
    },
]

# ---------------------------------------------------------------------------
# Teams and Agents  (keyed by priority level)
# ---------------------------------------------------------------------------

TEAMS = {
    "CRITICAL": ["Safety-Response", "Fraud-Team"],
    "HIGH":     ["Senior-Support",  "Escalations"],
    "MEDIUM":   ["Standard-Support"],
    "LOW":      ["General-Support"],
}

AGENTS = {
    "Safety-Response":  ["AGT-SR-01", "AGT-SR-02"],
    "Fraud-Team":       ["AGT-FR-01", "AGT-FR-02"],
    "Senior-Support":   ["AGT-SS-01", "AGT-SS-02", "AGT-SS-03"],
    "Escalations":      ["AGT-ES-01", "AGT-ES-02"],
    "Standard-Support": ["AGT-ST-01", "AGT-ST-02", "AGT-ST-03", "AGT-ST-04"],
    "General-Support":  ["AGT-GS-01", "AGT-GS-02", "AGT-GS-03"],
}

# ---------------------------------------------------------------------------
# Enum allowed values
# ---------------------------------------------------------------------------

CHANNELS           = ["Email", "Phone", "Web", "Mobile App", "Social Media", "In-Store"]
SENTIMENTS         = ["Positive", "Neutral", "Negative"]
COMPLAINT_STATUSES = ["Open", "In Progress", "Pending Customer", "Escalated", "Resolved", "Closed", "Reopened"]
ORDER_STATUSES     = ["Pending", "Processing", "Shipped", "Delivered", "Cancelled", "Returned"]
RESOLUTION_TYPES   = ["Refund", "Replacement", "Apology", "Fix Applied", "Escalated Externally", "No Action Required"]
SURVEY_RATINGS     = [1, 2, 3, 4, 5]

# ---------------------------------------------------------------------------
# Products  (safety_risk=True triggers CRITICAL priority)
# ---------------------------------------------------------------------------

PRODUCTS = [
    {"product_id": "PRD-001", "name": "SmartWatch Pro",      "category": "Electronics", "price": 299.99, "safety_risk": False},
    {"product_id": "PRD-002", "name": "Wireless Earbuds",    "category": "Electronics", "price": 89.99,  "safety_risk": False},
    {"product_id": "PRD-003", "name": "Laptop Stand",        "category": "Accessories", "price": 49.99,  "safety_risk": False},
    {"product_id": "PRD-004", "name": "Power Bank 20000mAh", "category": "Electronics", "price": 59.99,  "safety_risk": True},
    {"product_id": "PRD-005", "name": "Running Shoes",       "category": "Footwear",    "price": 129.99, "safety_risk": False},
    {"product_id": "PRD-006", "name": "Yoga Mat",            "category": "Sports",      "price": 39.99,  "safety_risk": False},
    {"product_id": "PRD-007", "name": "Coffee Maker",        "category": "Appliances",  "price": 199.99, "safety_risk": True},
    {"product_id": "PRD-008", "name": "Desk Lamp LED",       "category": "Furniture",   "price": 34.99,  "safety_risk": False},
    {"product_id": "PRD-009", "name": "Gaming Mouse",        "category": "Electronics", "price": 79.99,  "safety_risk": False},
    {"product_id": "PRD-010", "name": "Backpack 30L",        "category": "Bags",        "price": 69.99,  "safety_risk": False},
    {"product_id": "PRD-011", "name": "Bluetooth Speaker",   "category": "Electronics", "price": 149.99, "safety_risk": False},
    {"product_id": "PRD-012", "name": "Air Purifier",        "category": "Appliances",  "price": 249.99, "safety_risk": False},
    {"product_id": "PRD-013", "name": "Electric Kettle",     "category": "Appliances",  "price": 44.99,  "safety_risk": True},
    {"product_id": "PRD-014", "name": "Mechanical Keyboard", "category": "Electronics", "price": 119.99, "safety_risk": False},
    {"product_id": "PRD-015", "name": "Fitness Tracker",     "category": "Electronics", "price": 89.99,  "safety_risk": False},
]
