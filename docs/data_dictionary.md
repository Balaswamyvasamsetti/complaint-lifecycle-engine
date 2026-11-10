# Data Dictionary — Complaint Management System

All fields, types, constraints and relationships for every entity.

---

## Customer

| Field             | Type    | Required | Unique | Notes                        |
|-------------------|---------|----------|--------|------------------------------|
| customer_id       | string  | Yes      | Yes    | Format: CUS-NNNNNN           |
| first_name        | string  | Yes      | No     |                              |
| last_name         | string  | Yes      | No     |                              |
| email             | string  | Yes      | Yes    | Valid email format           |
| phone             | string  | No       | No     | Format: +44XXXXXXXXXX        |
| segment           | enum    | Yes      | No     | Premium / Standard / Basic   |
| is_vulnerable     | boolean | Yes      | No     | Synthetic flag only (~5%)    |
| registration_date | date    | Yes      | No     | YYYY-MM-DD                   |
| lifetime_value    | float   | Yes      | No     | GBP, min 0                   |

---

## Product

| Field       | Type    | Required | Unique | Notes                        |
|-------------|---------|----------|--------|------------------------------|
| product_id  | string  | Yes      | Yes    | Format: PRD-NNN              |
| name        | string  | Yes      | No     |                              |
| category    | string  | Yes      | No     | Product category label       |
| price       | float   | Yes      | No     | GBP, min 0                   |
| safety_risk | boolean | Yes      | No     | Triggers CRITICAL priority   |

---

## Order

| Field         | Type     | Required | Unique | Notes                              |
|---------------|----------|----------|--------|------------------------------------|
| order_id      | string   | Yes      | Yes    | Format: ORD-YYYY-NNNNNN            |
| customer_id   | string   | Yes      | No     | FK -> Customer                     |
| product_id    | string   | Yes      | No     | FK -> Product                      |
| order_date    | datetime | Yes      | No     | ISO 8601                           |
| order_value   | float    | Yes      | No     | GBP, min 0                         |
| quantity      | integer  | Yes      | No     | min 1                              |
| status        | enum     | Yes      | No     | Pending/Processing/Shipped/...     |
| delivery_date | datetime | No       | No     | Must be >= order_date              |

---

## Category

| Field             | Type    | Required | Unique | Notes              |
|-------------------|---------|----------|--------|--------------------|
| category_id       | string  | Yes      | Yes    | Format: CAT-NN     |
| name              | string  | Yes      | Yes    |                    |
| default_sla_hours | integer | Yes      | No     | Base SLA in hours  |

---

## PriorityRule

| Field               | Type   | Required | Unique | Notes                        |
|---------------------|--------|----------|--------|------------------------------|
| rule_id             | string | Yes      | Yes    | Format: PR-NN                |
| priority            | enum   | Yes      | Yes    | CRITICAL/HIGH/MEDIUM/LOW     |
| level               | int    | Yes      | Yes    | 1=highest, 4=lowest          |
| description         | string | Yes      | No     |                              |
| sla_multiplier      | float  | Yes      | No     | Applied to base SLA hours    |
| auto_escalate_hours | int    | Yes      | No     | Hours before auto-escalation |

---

## Complaint

| Field               | Type     | Required | Unique | Notes                              |
|---------------------|----------|----------|--------|------------------------------------|
| complaint_id        | string   | Yes      | Yes    | Format: CMP-YYYY-NNNNNN            |
| customer_id         | string   | No       | No     | FK -> Customer (nullable: edge case)|
| order_id            | string   | No       | No     | FK -> Order                        |
| product_id          | string   | No       | No     | FK -> Product                      |
| category_id         | string   | Yes      | No     | FK -> Category                     |
| channel             | enum     | Yes      | No     | Email/Phone/Web/Mobile App/...     |
| severity            | enum     | Yes      | No     | Low/Medium/High/Critical           |
| priority            | enum     | Yes      | No     | LOW/MEDIUM/HIGH/CRITICAL           |
| sentiment           | enum     | Yes      | No     | Positive/Neutral/Negative          |
| status              | enum     | Yes      | No     | Open/In Progress/Resolved/...      |
| created_at          | datetime | Yes      | No     | ISO 8601                           |
| updated_at          | datetime | Yes      | No     | Must be >= created_at              |
| recurrence_count    | integer  | Yes      | No     | min 1                              |
| is_safety_issue     | boolean  | Yes      | No     |                                    |
| is_reopened         | boolean  | Yes      | No     | Requires parent_complaint_id       |
| parent_complaint_id | string   | No       | No     | FK -> Complaint (self-ref)         |
| order_value         | float    | Yes      | No     | Denormalised from Order            |

---

## ComplaintMessage

| Field        | Type     | Required | Unique | Notes                          |
|--------------|----------|----------|--------|--------------------------------|
| message_id   | string   | Yes      | Yes    | Format: MSG-<complaint_id>-NNN |
| complaint_id | string   | Yes      | No     | FK -> Complaint                |
| sender_type  | enum     | Yes      | No     | Customer / Agent / System      |
| message_text | string   | Yes      | No     |                                |
| sent_at      | datetime | Yes      | No     | ISO 8601                       |
| is_internal  | boolean  | Yes      | No     | Agent-only internal notes      |

---

## Assignment

| Field         | Type     | Required | Unique | Notes                    |
|---------------|----------|----------|--------|--------------------------|
| assignment_id | string   | Yes      | Yes    | Format: ASN-NNNNNN       |
| complaint_id  | string   | Yes      | No     | FK -> Complaint          |
| team          | string   | Yes      | No     |                          |
| agent_id      | string   | Yes      | No     |                          |
| assigned_at   | datetime | Yes      | No     | ISO 8601                 |
| is_current    | boolean  | Yes      | No     | Latest active assignment |
| reason        | string   | No       | No     |                          |

---

## SLAClock

| Field        | Type     | Required | Unique | Notes                              |
|--------------|----------|----------|--------|------------------------------------|
| sla_id       | string   | Yes      | Yes    | Format: SLA-<complaint_id>         |
| complaint_id | string   | Yes      | No     | FK -> Complaint (1:1)              |
| sla_hours    | float    | Yes      | No     | Derived: base * multiplier         |
| started_at   | datetime | Yes      | No     | = complaint.created_at             |
| deadline_at  | datetime | Yes      | No     | = started_at + sla_hours           |
| paused_at    | datetime | No       | No     |                                    |
| resumed_at   | datetime | No       | No     | Must be >= paused_at               |
| pause_reason | string   | No       | No     |                                    |
| is_breached  | boolean  | Yes      | No     |                                    |
| breached_at  | datetime | No       | No     | Set when breach occurs             |
| status       | enum     | Yes      | No     | Active/Paused/Met/Breached         |

---

## Resolution

| Field           | Type     | Required | Unique | Notes                              |
|-----------------|----------|----------|--------|------------------------------------|
| resolution_id   | string   | Yes      | Yes    | Format: RES-<complaint_id>         |
| complaint_id    | string   | Yes      | No     | FK -> Complaint (1:1)              |
| resolution_type | enum     | Yes      | No     | Refund/Replacement/Apology/...     |
| resolved_by     | string   | Yes      | No     | Agent ID                           |
| resolved_at     | datetime | Yes      | No     | Must be >= complaint.created_at    |
| notes           | string   | No       | No     |                                    |
| refund_amount   | float    | No       | No     | GBP, only when type=Refund         |

---

## Survey

| Field         | Type     | Required | Unique | Notes                          |
|---------------|----------|----------|--------|--------------------------------|
| survey_id     | string   | Yes      | Yes    | Format: SRV-NNNNNN             |
| complaint_id  | string   | Yes      | No     | FK -> Complaint (1:1)          |
| rating        | integer  | Yes      | No     | 1-5                            |
| feedback_text | string   | No       | No     |                                |
| submitted_at  | datetime | Yes      | No     | Must be >= resolution.resolved_at |
| nps_score     | integer  | No       | No     | 0-10                           |

---

## Edge Case Labels (ground_truth only)

| issue_type                  | Description                                               |
|-----------------------------|-----------------------------------------------------------|
| missing_customer            | Complaint with no customer_id                             |
| resolution_before_complaint | Resolution timestamp precedes complaint created_at        |
| sla_pause_no_resume         | SLA paused but resumed_at is missing                      |
| safety_low_priority         | Critical safety issue assigned to General-Support queue   |
| survey_before_closure       | Survey submitted before resolution/closure                |
| repeat_not_linked           | Repeat complaint (recurrence>=2) with no parent_complaint_id |
