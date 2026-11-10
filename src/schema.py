"""
Data Dictionary — defines allowed values, field specs, and lifecycle states
for every entity in the Complaint Management System.
"""

CATEGORIES = [
    {"category_id": "CAT-01", "name": "Billing & Payment",       "default_sla_hours": 48},
    {"category_id": "CAT-02", "name": "Product Defect",          "default_sla_hours": 72},
    {"category_id": "CAT-03", "name": "Delivery / Logistics",    "default_sla_hours": 48},
    {"category_id": "CAT-04", "name": "Product Safety",          "default_sla_hours": 4},
    {"category_id": "CAT-05", "name": "Customer Service",        "default_sla_hours": 24},
    {"category_id": "CAT-06", "name": "Refund / Return",         "default_sla_hours": 72},
    {"category_id": "CAT-07", "name": "Missing Order",           "default_sla_hours": 24},
    {"category_id": "CAT-08", "name": "Technical / App Issue",   "default_sla_hours": 96},
    {"category_id": "CAT-09", "name": "Fraud / Unauthorized",    "default_sla_hours": 8},
    {"category_id": "CAT-10", "name": "General Enquiry",         "default_sla_hours": 120},
]

PRIORITY_RULES = [
    {
        "rule_id":      "PR-01",
        "priority":     "CRITICAL",
        "level":        1,
        "description":  "Safety issue OR fraud OR vulnerable customer",
        "sla_multiplier": 0.25,
        "auto_escalate_hours": 2,
    },
    {
        "rule_id":      "PR-02",
        "priority":     "HIGH",
        "level":        2,
        "description":  "Negative sentiment AND order_value > 500 OR recurrence >= 3",
        "sla_multiplier": 0.5,
        "auto_escalate_hours": 8,
    },
    {
        "rule_id":      "PR-03",
        "priority":     "MEDIUM",
        "level":        3,
        "description":  "Negative sentiment OR order_value 100-500",
        "sla_multiplier": 1.0,
        "auto_escalate_hours": 24,
    },
    {
        "rule_id":      "PR-04",
        "priority":     "LOW",
        "level":        4,
        "description":  "Neutral/positive sentiment AND order_value < 100",
        "sla_multiplier": 1.5,
        "auto_escalate_hours": 72,
    },
]

TEAMS = {
    "CRITICAL": ["Safety-Response", "Fraud-Team"],
    "HIGH":     ["Senior-Support", "Escalations"],
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

CHANNELS = ["Email", "Phone", "Web", "Mobile App", "Social Media", "In-Store"]
SENTIMENTS = ["Positive", "Neutral", "Negative"]
COMPLAINT_STATUSES = ["Open", "In Progress", "Pending Customer", "Escalated", "Resolved", "Closed", "Reopened"]
ORDER_STATUSES = ["Pending", "Processing", "Shipped", "Delivered", "Cancelled", "Returned"]
RESOLUTION_TYPES = ["Refund", "Replacement", "Apology", "Fix Applied", "Escalated Externally", "No Action Required"]
SURVEY_RATINGS = [1, 2, 3, 4, 5]

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

# Field-level data dictionary (for documentation/README)
DATA_DICTIONARY = {
    "Customer": {
        "customer_id":       {"type": "string",   "required": True,  "unique": True,  "format": "CUS-NNNNNN"},
        "first_name":        {"type": "string",   "required": True,  "unique": False},
        "last_name":         {"type": "string",   "required": True,  "unique": False},
        "email":             {"type": "string",   "required": True,  "unique": True,  "validation": "valid email format"},
        "phone":             {"type": "string",   "required": False, "unique": False},
        "segment":           {"type": "enum",     "required": True,  "values": ["Premium", "Standard", "Basic"]},
        "is_vulnerable":     {"type": "boolean",  "required": True,  "note": "synthetic flag only"},
        "registration_date": {"type": "date",     "required": True},
        "lifetime_value":    {"type": "float",    "required": True,  "units": "GBP", "min": 0},
    },
    "Order": {
        "order_id":          {"type": "string",   "required": True,  "unique": True,  "format": "ORD-YYYY-NNNNNN"},
        "customer_id":       {"type": "string",   "required": True,  "fk": "Customer.customer_id"},
        "product_id":        {"type": "string",   "required": True,  "fk": "Product.product_id"},
        "order_date":        {"type": "datetime", "required": True},
        "order_value":       {"type": "float",    "required": True,  "units": "GBP", "min": 0},
        "quantity":          {"type": "integer",  "required": True,  "min": 1},
        "status":            {"type": "enum",     "required": True,  "values": ORDER_STATUSES},
        "delivery_date":     {"type": "datetime", "required": False, "rule": "delivery_date >= order_date"},
    },
    "Complaint": {
        "complaint_id":      {"type": "string",   "required": True,  "unique": True,  "format": "CMP-YYYY-NNNNNN"},
        "customer_id":       {"type": "string",   "required": False, "fk": "Customer.customer_id", "note": "nullable for edge case"},
        "order_id":          {"type": "string",   "required": False, "fk": "Order.order_id"},
        "product_id":        {"type": "string",   "required": False, "fk": "Product.product_id"},
        "category_id":       {"type": "string",   "required": True,  "fk": "Category.category_id"},
        "channel":           {"type": "enum",     "required": True,  "values": CHANNELS},
        "severity":          {"type": "enum",     "required": True,  "values": ["Low", "Medium", "High", "Critical"]},
        "priority":          {"type": "enum",     "required": True,  "values": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
        "sentiment":         {"type": "enum",     "required": True,  "values": SENTIMENTS},
        "status":            {"type": "enum",     "required": True,  "values": COMPLAINT_STATUSES},
        "created_at":        {"type": "datetime", "required": True},
        "updated_at":        {"type": "datetime", "required": True,  "rule": "updated_at >= created_at"},
        "recurrence_count":  {"type": "integer",  "required": True,  "min": 1},
        "is_safety_issue":   {"type": "boolean",  "required": True},
        "is_reopened":       {"type": "boolean",  "required": True},
        "parent_complaint_id": {"type": "string", "required": False, "fk": "Complaint.complaint_id"},
    },
    "ComplaintMessage": {
        "message_id":        {"type": "string",   "required": True,  "unique": True,  "format": "MSG-<complaint_id>-NNN"},
        "complaint_id":      {"type": "string",   "required": True,  "fk": "Complaint.complaint_id"},
        "sender_type":       {"type": "enum",     "required": True,  "values": ["Customer", "Agent", "System"]},
        "message_text":      {"type": "string",   "required": True},
        "sent_at":           {"type": "datetime", "required": True},
        "is_internal":       {"type": "boolean",  "required": True},
    },
    "Assignment": {
        "assignment_id":     {"type": "string",   "required": True,  "unique": True},
        "complaint_id":      {"type": "string",   "required": True,  "fk": "Complaint.complaint_id"},
        "team":              {"type": "string",   "required": True},
        "agent_id":          {"type": "string",   "required": True},
        "assigned_at":       {"type": "datetime", "required": True},
        "is_current":        {"type": "boolean",  "required": True},
        "reason":            {"type": "string",   "required": False},
    },
    "SLAClock": {
        "sla_id":            {"type": "string",   "required": True,  "unique": True,  "format": "SLA-<complaint_id>"},
        "complaint_id":      {"type": "string",   "required": True,  "fk": "Complaint.complaint_id"},
        "sla_hours":         {"type": "float",    "required": True,  "min": 0},
        "started_at":        {"type": "datetime", "required": True},
        "deadline_at":       {"type": "datetime", "required": True,  "rule": "deadline_at = started_at + sla_hours"},
        "paused_at":         {"type": "datetime", "required": False},
        "resumed_at":        {"type": "datetime", "required": False},
        "pause_reason":      {"type": "string",   "required": False},
        "is_breached":       {"type": "boolean",  "required": True},
        "breached_at":       {"type": "datetime", "required": False},
        "status":            {"type": "enum",     "required": True,  "values": ["Active", "Paused", "Met", "Breached"]},
    },
    "Resolution": {
        "resolution_id":     {"type": "string",   "required": True,  "unique": True,  "format": "RES-<complaint_id>"},
        "complaint_id":      {"type": "string",   "required": True,  "fk": "Complaint.complaint_id"},
        "resolution_type":   {"type": "enum",     "required": True,  "values": RESOLUTION_TYPES},
        "resolved_by":       {"type": "string",   "required": True},
        "resolved_at":       {"type": "datetime", "required": True},
        "notes":             {"type": "string",   "required": False},
        "refund_amount":     {"type": "float",    "required": False, "units": "GBP", "min": 0},
    },
    "Survey": {
        "survey_id":         {"type": "string",   "required": True,  "unique": True},
        "complaint_id":      {"type": "string",   "required": True,  "fk": "Complaint.complaint_id"},
        "rating":            {"type": "integer",  "required": True,  "values": SURVEY_RATINGS},
        "feedback_text":     {"type": "string",   "required": False},
        "submitted_at":      {"type": "datetime", "required": True},
        "nps_score":         {"type": "integer",  "required": False, "min": 0, "max": 10},
    },
}
