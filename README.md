# Complaint Management System — Synthetic Data Generator

## Overview

End-to-end synthetic dataset for a complaint management workflow:
classify complaints, assign owners, enforce SLAs, track resolution and customer communication.

- **Seed:** 20261022 (fixed, fully reproducible)
- **Full scale:** 5,000 customers | 8,000 orders | 2,000 complaints | 6,000 messages
- **Starter scale:** `--scale 0.1` (10% of full volume, same seed)

---

## Quick Start

```bash
# Full dataset
python src/run.py

# Starter dataset (10%)
python src/run.py --scale 0.1

# Reproducibility check (generates twice, compares checksums)
python src/run.py --reproducibility-check
```

**Requirements:** Python 3.8+ (stdlib only, no pip installs needed)

---

## Project Structure

```
Yottaflex_hackthon/
├── src/
│   ├── schema.py        # Data dictionary, allowed values, business rules
│   ├── generator.py     # Synthetic data generation (all entities)
│   ├── validator.py     # PK/FK/enum/date/lifecycle validation
│   ├── exporter.py      # CSV + JSON export (strips ground-truth fields)
│   ├── ground_truth.py  # Separate anomaly/edge-case export
│   └── run.py           # Orchestrator
├── output/
│   ├── csv/             # Input feature CSVs (ground truth stripped)
│   ├── json/            # Input feature JSONs
│   ├── ground_truth/    # ground_truth.csv + ground_truth.json
│   ├── manifest.json    # Table names, row counts, file paths
│   └── validation_errors.json  # Only present if validation fails
├── data/
└── docs/
```

---

## Entity Relationship Summary

| Entity           | PK                        | FK / Relationships                              | Cardinality |
|------------------|---------------------------|-------------------------------------------------|-------------|
| Customer         | customer_id (CUS-NNNNNN)  | —                                               | —           |
| Product          | product_id (PRD-NNN)      | —                                               | —           |
| Order            | order_id (ORD-YYYY-NNNNNN)| customer_id -> Customer, product_id -> Product  | N:1, N:1    |
| Category         | category_id (CAT-NN)      | —                                               | —           |
| PriorityRule     | rule_id (PR-NN)            | —                                               | —           |
| Complaint        | complaint_id (CMP-YYYY-NNNNNN) | customer_id, order_id, product_id, category_id, parent_complaint_id | N:1 each |
| Assignment       | assignment_id (ASN-NNNNNN)| complaint_id -> Complaint                       | N:1         |
| SLAClock         | sla_id (SLA-<complaint_id>)| complaint_id -> Complaint                      | 1:1         |
| ComplaintMessage | message_id (MSG-<cmp_id>-NNN) | complaint_id -> Complaint                   | N:1         |
| Resolution       | resolution_id (RES-<complaint_id>) | complaint_id -> Complaint              | 1:1         |
| Survey           | survey_id (SRV-NNNNNN)    | complaint_id -> Complaint                       | 1:1         |

---

## ID / Nomenclature Conventions

| Entity           | Format                        | Example                  |
|------------------|-------------------------------|--------------------------|
| Customer         | CUS-NNNNNN                    | CUS-000001               |
| Order            | ORD-YYYY-NNNNNN               | ORD-2026-000001          |
| Complaint        | CMP-YYYY-NNNNNN               | CMP-2026-000001          |
| Message          | MSG-\<complaint_id\>-NNN      | MSG-CMP-2026-000001-001  |
| SLA Clock        | SLA-\<complaint_id\>          | SLA-CMP-2026-000001      |
| Resolution       | RES-\<complaint_id\>          | RES-CMP-2026-000001      |
| Assignment       | ASN-NNNNNN                    | ASN-000001               |
| Survey           | SRV-NNNNNN                    | SRV-000001               |

---

## Priority Rules (Deterministic)

| Rule  | Priority | Condition                                                        | SLA Multiplier |
|-------|----------|------------------------------------------------------------------|----------------|
| PR-01 | CRITICAL | Safety issue OR fraud (CAT-09) OR vulnerable customer            | 0.25x          |
| PR-02 | HIGH     | Negative sentiment AND order_value > 500 OR recurrence >= 3      | 0.50x          |
| PR-03 | MEDIUM   | Negative sentiment OR order_value 100-500                        | 1.00x          |
| PR-04 | LOW      | Neutral/positive sentiment AND order_value < 100                 | 1.50x          |

---

## SLA Calculation

```
sla_hours = category.default_sla_hours * priority_rule.sla_multiplier
deadline  = complaint.created_at + sla_hours
```

| Category              | Base SLA (hrs) |
|-----------------------|----------------|
| Product Safety        | 4              |
| Fraud / Unauthorized  | 8              |
| Customer Service      | 24             |
| Missing Order         | 24             |
| Billing & Payment     | 48             |
| Delivery / Logistics  | 48             |
| Product Defect        | 72             |
| Refund / Return       | 72             |
| Technical / App Issue | 96             |
| General Enquiry       | 120            |

---

## Edge Cases / Anomalies (Ground Truth)

All injected with `issue_type` label. Exported **only** to `output/ground_truth/`.

| issue_type                | Description                                              |
|---------------------------|----------------------------------------------------------|
| missing_customer          | Complaint with no customer_id                            |
| resolution_before_complaint | Resolution timestamp precedes complaint created_at     |
| sla_pause_no_resume       | SLA paused but resumed_at is missing                     |
| safety_low_priority       | Critical safety issue assigned to General-Support queue  |
| survey_before_closure     | Survey submitted before resolution/closure               |
| repeat_not_linked         | Repeat complaint (recurrence>=2) with no parent_complaint_id |

---

## Validation Rules

| Rule               | Check                                                        |
|--------------------|--------------------------------------------------------------|
| PK_DUPLICATE       | Primary key uniqueness across all entities                   |
| FK_*               | Foreign key integrity (customer, order, product, complaint)  |
| ENUM_*             | Allowed enum values (status, priority, severity, channel...) |
| DATE_ORDER         | updated_at >= created_at; delivery_date >= order_date        |
| DATE_SLA           | deadline_at = started_at + sla_hours                         |
| DATE_PAUSE         | resumed_at >= paused_at                                      |
| DATE_RESOLUTION    | resolved_at >= complaint.created_at                          |
| DATE_SURVEY        | submitted_at >= resolved_at                                  |
| LIFECYCLE_REOPEN   | is_reopened=True requires parent_complaint_id                |
| ARITH_SLA          | deadline_at arithmetic reconciliation (< 1 min tolerance)    |
| PRIORITY_RULE      | Priority reproducible from documented rules                  |

---

## Reproducibility

```
Run 1 checksum: c83c97fcbd01ca1aa60a343fd6a56ad9  (scale=0.1)
Run 2 checksum: c83c97fcbd01ca1aa60a343fd6a56ad9  (scale=0.1)
Full scale checksum: b77844c9f2ec9abfff23e02fd779b0d3
```

Same seed (20261022) always produces identical row counts and data.

---

## Source Manifest

All data is **100% synthetic**. No external datasets used.
Reference schemas inspired by publicly documented CRM/complaint management patterns.

| Field              | Value                        |
|--------------------|------------------------------|
| Generator          | src/generator.py             |
| Seed               | 20261022                     |
| Scale parameter    | --scale (default 1.0)        |
| External data      | None                         |
| PII                | None (all synthetic)         |
| License            | Synthetic — no restrictions  |

---

## Data Coverage

- Repeat complaints (recurrence_count >= 2)
- Vulnerable customer flag (is_vulnerable=True, ~5% of customers)
- Product safety issues (safety_risk products + CAT-04 category)
- Missing order complaints (CAT-07)
- Refund pending (CAT-06, resolution_type=Refund)
- Reopened cases (is_reopened=True, ~8% of complaints)
- All 4 priority levels and 10 categories represented
- All 6 complaint channels represented
- SLA breached and met cases
- Escalated complaints
