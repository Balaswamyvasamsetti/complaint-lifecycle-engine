# Enterprise Data Dictionary — Complaint Lifecycle Engine

**System:** Complaint Lifecycle Engine & Deterministic SLA Orchestration Suite  
**Standard Specification:** Enterprise Forward Deployed Engineering (FDE) Architecture  
**Database Engines Supported:** PostgreSQL (Neon Cloud) & SQLite (Local Fallback)  
**Master Random Seed:** `20261022`  
**Master Volume Requirements:** 5,000 Customers | 8,000 Orders | 2,000+ Complaints | 6,000 Messages  

---

## 1. Architectural Overview & Entity-Relationship Schema

The data model follows an event-sourced, auditable domain schema designed to enforce zero data loss, chronological referential integrity, and deterministic business rules.

```mermaid
erDiagram
    CUSTOMERS ||--o{ ORDERS : places
    CUSTOMERS ||--o{ COMPLAINTS : submits
    PRODUCTS ||--o{ ORDERS : contains
    PRODUCTS ||--o{ COMPLAINTS : references
    CATEGORIES ||--o{ COMPLAINTS : classifies
    PRIORITY_RULES ||--o{ COMPLAINTS : governs
    COMPLAINTS ||--o{ ASSIGNMENTS : assigns
    COMPLAINTS ||--|| SLA_CLOCKS : enforces
    COMPLAINTS ||--o{ MESSAGES : communicates
    COMPLAINTS ||--o{ COMPLAINT_EVENTS : logs
    COMPLAINTS ||--o| RESOLUTIONS : settles
    COMPLAINTS ||--o| SURVEYS : evaluates
```

---

## 2. Core Entities Specification (11 Entities + Surveys)

### Entity 1: `customers`
Stores verified account holders, corporate clients, and guest requesters.

| Field Name | Type (PG / SQLite) | Nullable | Constraints & Keys | Allowed Values / Format | Validation Rules | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `customer_id` | `VARCHAR(32)` / `TEXT` | No | **Primary Key** | Sequential `CUS-000001` to `CUS-005000` | Format regex `^CUS-\d{6}$` | Deterministic unique customer identifier |
| `first_name` | `VARCHAR(64)` / `TEXT` | No | None | Text (English / International) | Non-empty string | Customer given name |
| `last_name` | `VARCHAR(64)` / `TEXT` | No | None | Text | Non-empty string | Customer family name |
| `email` | `VARCHAR(128)` / `TEXT` | No | **Unique** | Valid RFC 5322 email string | Must contain `@` and valid TLD | Primary customer communication channel |
| `phone` | `VARCHAR(32)` / `TEXT` | Yes | None | E.164 (e.g., `+44...`) | Valid international dialing string | Telephone contact number |
| `segment` | `VARCHAR(32)` / `TEXT` | No | Enum | `Premium`, `Standard`, `Basic` | Must match one of 3 tier enums | Business customer account tier |
| `is_vulnerable` | `BOOLEAN` / `INTEGER` | No | Default `FALSE` | `TRUE` / `FALSE` | Boolean flag | Vulnerable customer flag (triggers CRITICAL SLA rule PR-01) |
| `registration_date` | `DATE` / `TEXT` | No | ISO 8601 Date | `YYYY-MM-DD` | Date `<= 2026-10-31` | Date account was onboarded |
| `lifetime_value` | `NUMERIC(10,2)` / `REAL` | No | Default `0.00` | `0.00` to `999999.99` (£ GBP) | Value `>= 0.00` | Cumulative customer net transactional value |

---

### Entity 2: `products`
Master catalog of commercial products and merchandise items.

| Field Name | Type (PG / SQLite) | Nullable | Constraints & Keys | Allowed Values / Format | Validation Rules | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `product_id` | `VARCHAR(32)` / `TEXT` | No | **Primary Key** | `PRD-001` to `PRD-015` | Format regex `^PRD-\d{3}$` | Unique catalog SKU code |
| `name` | `VARCHAR(128)` / `TEXT` | No | None | String (e.g. `SmartWatch Pro`) | Non-empty product name | Commercial product name |
| `category` | `VARCHAR(64)` / `TEXT` | No | None | `Electronics`, `Appliances`, etc. | Department string | Merchandising department |
| `price` | `NUMERIC(10,2)` / `REAL` | No | Check `> 0.00` | Numeric (£ GBP) | Must be strictly positive | Standard retail item selling price |
| `safety_risk` | `BOOLEAN` / `INTEGER` | No | Default `FALSE` | `TRUE` / `FALSE` | Boolean flag | Safety risk indicator (heating, battery, electrical) |

---

### Entity 3: `orders`
Historical purchases and fulfillment transactions.

| Field Name | Type (PG / SQLite) | Nullable | Constraints & Keys | Allowed Values / Format | Validation Rules | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `order_id` | `VARCHAR(32)` / `TEXT` | No | **Primary Key** | Sequential `ORD-2026-000001` to `008000` | Format regex `^ORD-2026-\d{6}$` | Deterministic transaction identifier |
| `customer_id` | `VARCHAR(32)` / `TEXT` | No | **Foreign Key** (`customers.customer_id`) | `CUS-%06d` | Must exist in `customers` | Purchasing customer |
| `product_id` | `VARCHAR(32)` / `TEXT` | No | **Foreign Key** (`products.product_id`) | `PRD-%03d` | Must exist in `products` | Purchased merchandise SKU |
| `order_date` | `VARCHAR(32)` / `TEXT` | No | ISO 8601 Timestamp | `YYYY-MM-DDTHH:MM:SS` | Valid ISO 8601 timestamp | Timestamp purchase was executed |
| `order_value` | `NUMERIC(10,2)` / `REAL` | No | Check `> 0.00` | Total checkout value (£ GBP) | Must be positive currency | Net transaction total |
| `quantity` | `INTEGER` | No | Check `>= 1` | `1` to `10` | Positive integer `>= 1` | Number of item units purchased |
| `status` | `VARCHAR(32)` / `TEXT` | No | Enum | `Pending`, `Processing`, `Shipped`, `Delivered`, `Cancelled`, `Returned` | Must match valid enum | Order fulfillment status |
| `delivery_date` | `VARCHAR(32)` / `TEXT` | Yes | Chronological Check | `YYYY-MM-DDTHH:MM:SS` (or null) | `delivery_date >= order_date` | Carrier proof of delivery timestamp |

---

### Entity 4: `categories`
Hierarchical taxonomy for complaint triage and baseline SLA targets.

| Field Name | Type (PG / SQLite) | Nullable | Constraints & Keys | Allowed Values / Format | Validation Rules | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `category_id` | `VARCHAR(16)` / `TEXT` | No | **Primary Key** | `CAT-01` to `CAT-10` | Format regex `^CAT-\d{2}$` | Master taxonomy node code |
| `name` | `VARCHAR(64)` / `TEXT` | No | **Unique** | E.g. `Billing & Payment`, `Product Safety` | Unique category name | Category display title |
| `default_sla_hours` | `INTEGER` | No | Check `> 0` | `4` to `120` hours | Strictly positive integer | Standard baseline resolution deadline |

---

### Entity 5: `priority_rules`
Governance rules mapping customer, sentiment, and safety inputs to SLA tiers.

| Field Name | Type (PG / SQLite) | Nullable | Constraints & Keys | Allowed Values / Format | Validation Rules | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `rule_id` | `VARCHAR(16)` / `TEXT` | No | **Primary Key** | `PR-01` to `PR-04` | Format regex `^PR-\d{2}$` | Rule governance code |
| `priority` | `VARCHAR(16)` / `TEXT` | No | **Unique** | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` | Must match priority enum | Resulting priority level |
| `level` | `INTEGER` | No | **Unique** | `1` (highest) to `4` (lowest) | Range 1-4 | Numeric hierarchy rank |
| `description` | `TEXT` | No | None | Logic statement string | Plain English policy criteria | Policy condition statement |
| `sla_multiplier` | `NUMERIC(4,2)` / `REAL` | No | Check `> 0.0` | `0.25`, `0.50`, `1.00`, `1.50` | Strictly positive multiplier | Factor applied against default SLA |
| `auto_escalate_hours` | `INTEGER` | No | Check `> 0` | `2`, `8`, `24`, `72` hours | Positive integer | Auto-escalation window |

---

### Entity 6: `complaints`
Central business record representing an ingested customer grievance.

| Field Name | Type (PG / SQLite) | Nullable | Constraints & Keys | Allowed Values / Format | Validation Rules | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `complaint_id` | `VARCHAR(32)` / `TEXT` | No | **Primary Key** | Sequential `CMP-2026-000001` to `002000+` | Format regex `^CMP-2026-\d{6}$` | Zero-padded complaint identifier |
| `customer_id` | `VARCHAR(32)` / `TEXT` | Yes | **Foreign Key** (`customers.customer_id`) | `CUS-%06d` (Empty only on Edge Case #1) | Referential check against `customers` | Submitting customer reference |
| `order_id` | `VARCHAR(32)` / `TEXT` | Yes | Optional Reference | `ORD-2026-%06d` (or null/blank) | Optional check against `orders` | Associated purchase transaction |
| `product_id` | `VARCHAR(32)` / `TEXT` | Yes | Optional Reference | `PRD-%03d` (or null/blank) | Optional check against `products` | Product SKU referenced |
| `category_id` | `VARCHAR(16)` / `TEXT` | No | **Foreign Key** (`categories.category_id`) | `CAT-01` to `CAT-10` | Must match valid category ID | Inferred category code |
| `category_name` | `VARCHAR(64)` / `TEXT` | No | None | Category name string | Must match taxonomy name | Category name snapshot |
| `channel` | `VARCHAR(32)` / `TEXT` | No | Enum | `Email`, `Phone`, `Web`, `Mobile App`, `Social Media`, `In-Store` | Must match channel enum | Ingestion channel |
| `severity` | `VARCHAR(16)` / `TEXT` | No | Enum | `Critical`, `High`, `Medium`, `Low` | Must match severity enum | Severity rating |
| `priority` | `VARCHAR(16)` / `TEXT` | No | Enum | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` | Evaluated by priority rules | Evaluated priority tier |
| `sentiment` | `VARCHAR(16)` / `TEXT` | No | Enum | `Positive`, `Neutral`, `Negative` | Must match sentiment enum | NLP sentiment polarity |
| `status` | `VARCHAR(32)` / `TEXT` | No | Enum | `Open`, `In Progress`, `Pending Customer`, `Escalated`, `Resolved`, `Closed`, `Reopened` | Must match state machine enum | Lifecycle workflow state |
| `created_at` | `VARCHAR(32)` / `TEXT` | No | ISO 8601 Timestamp | `YYYY-MM-DDTHH:MM:SS` | Intake timestamp | Ingestion timestamp |
| `updated_at` | `VARCHAR(32)` / `TEXT` | No | ISO 8601 Timestamp | `YYYY-MM-DDTHH:MM:SS` | `updated_at >= created_at` | Latest state change timestamp |
| `recurrence_count` | `INTEGER` | No | Default `1` | Integer `>= 1` | Non-negative integer | Number of complaints filed by customer |
| `is_safety_issue` | `BOOLEAN` / `INTEGER` | No | Default `FALSE` | `TRUE` / `FALSE` | If `TRUE`, priority MUST be `CRITICAL` (except Edge Case #5) | Product hazard or burn/injury risk |
| `is_reopened` | `BOOLEAN` / `INTEGER` | No | Default `FALSE` | `TRUE` / `FALSE` | Boolean flag | Reopened case flag |
| `parent_complaint_id` | `VARCHAR(32)` / `TEXT` | Yes | Self-reference | `CMP-2026-%06d` | Must exist in `complaints` if present | Parent ticket for reopened/repeat issues |
| `order_value` | `NUMERIC(10,2)` / `REAL` | No | Default `0.00` | Numeric (£ GBP) | Exposure `>= 0.00` | Order financial exposure |
| `ai_classification` | `TEXT` | Yes | None | JSON serialization string | Valid JSON format | Raw AI / Bedrock classification payload |
| `ai_summary` | `TEXT` | Yes | None | Text | Text description | Synthesized case summary |

---

### Entity 7: `complaint_events`
Immutable event sourcing journal recording state transitions and actor actions.

| Field Name | Type (PG / SQLite) | Nullable | Constraints & Keys | Allowed Values / Format | Validation Rules | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `event_id` | `VARCHAR(64)` / `TEXT` | No | **Primary Key** | Sequential `EVT-000001` to `EVT-006000+` | Format regex `^EVT-\d{6}$` | Unique immutable event ID |
| `complaint_id` | `VARCHAR(32)` / `TEXT` | No | **Foreign Key** (`complaints.complaint_id`) | `CMP-2026-%06d` | Must exist in `complaints` | Target complaint reference |
| `event_type` | `VARCHAR(32)` / `TEXT` | No | Enum | `COMPLAINT_CREATED`, `ASSIGNED`, `STATUS_CHANGED`, `SLA_PAUSED`, `SLA_RESUMED`, `SLA_BREACHED`, `MESSAGE_SENT`, `MESSAGE_RECEIVED`, `RESOLVED`, `SURVEY_SUBMITTED`, `REOPENED` | Must match event enum | Discrete domain event type |
| `actor` | `VARCHAR(64)` / `TEXT` | No | None | Actor name, agent ID, or system | Non-empty actor string | User or service triggering event |
| `old_state` | `VARCHAR(32)` / `TEXT` | Yes | None | Status string or blank | Prior lifecycle state | Prior lifecycle state |
| `new_state` | `VARCHAR(32)` / `TEXT` | No | None | Status string or team name | Subsequent lifecycle state | Subsequent lifecycle state |
| `event_timestamp` | `VARCHAR(32)` / `TEXT` | No | ISO 8601 Timestamp | `YYYY-MM-DDTHH:MM:SS` | `event_timestamp >= complaint.created_at` | Exact wall-clock event time |
| `details` | `TEXT` | Yes | None | Text | Non-empty narrative | Human-readable audit narrative |

---

### Entity 8: `assignments`
Operational ownership and queue routing history.

| Field Name | Type (PG / SQLite) | Nullable | Constraints & Keys | Allowed Values / Format | Validation Rules | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `assignment_id` | `VARCHAR(32)` / `TEXT` | No | **Primary Key** | Sequential `ASN-000001` to `ASN-002000+` | Format regex `^ASN-\d{6}$` | Unique assignment record code |
| `complaint_id` | `VARCHAR(32)` / `TEXT` | No | **Foreign Key** (`complaints.complaint_id`) | `CMP-2026-%06d` | Must exist in `complaints` | Associated complaint ticket |
| `team` | `VARCHAR(64)` / `TEXT` | No | Enum | `Safety-Response`, `Fraud-Team`, `Senior-Support`, `Escalations`, `Standard-Support`, `General-Support` | Must match valid team enum | Operational queue unit |
| `agent_id` | `VARCHAR(32)` / `TEXT` | No | None | `AGT-SR-01`, `AGT-SS-01`, etc. | Must be member of assigned team | Assigned employee agent badge |
| `assigned_at` | `VARCHAR(32)` / `TEXT` | No | ISO 8601 Timestamp | `YYYY-MM-DDTHH:MM:SS` | `assigned_at >= complaint.created_at` | Timestamp assignment occurred |
| `is_current` | `BOOLEAN` / `INTEGER` | No | Default `TRUE` | `TRUE` / `FALSE` | Only 1 current assignment per complaint | Active ownership indicator |
| `reason` | `TEXT` | Yes | None | Text | Contextual routing reason | Routing justification rationale |

---

### Entity 9: `sla_clocks`
Deterministic SLA stopwatch tracking active duration, pauses, and breach states.

| Field Name | Type (PG / SQLite) | Nullable | Constraints & Keys | Allowed Values / Format | Validation Rules | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `sla_id` | `VARCHAR(32)` / `TEXT` | No | **Primary Key** | Strict Format: `SLA-<complaint-id>` (e.g. `SLA-CMP-2026-000001`) | Format regex `^SLA-CMP-\d{4}-\d{6}$` | Unique SLA tracker ID keyed to complaint |
| `complaint_id` | `VARCHAR(32)` / `TEXT` | No | **Foreign Key** (`complaints.complaint_id`) | `CMP-2026-%06d` | 1-to-1 relationship with `complaints` | Target complaint ticket |
| `sla_hours` | `NUMERIC(6,2)` / `REAL` | No | Check `> 0.0` | `1.00` to `180.00` hours | Calculated as `default_sla * multiplier` | Enforced maximum duration |
| `started_at` | `VARCHAR(32)` / `TEXT` | No | ISO 8601 Timestamp | `YYYY-MM-DDTHH:MM:SS` | Equals `complaint.created_at` | Stopwatch start time |
| `deadline_at` | `VARCHAR(32)` / `TEXT` | No | ISO 8601 Timestamp | `YYYY-MM-DDTHH:MM:SS` | `deadline_at = started_at + sla_hours` | Guaranteed completion deadline |
| `paused_at` | `VARCHAR(32)` / `TEXT` | Yes | ISO 8601 Timestamp | `YYYY-MM-DDTHH:MM:SS` (or null) | Required if status is `Paused` | Timestamp SLA clock was halted |
| `resumed_at` | `VARCHAR(32)` / `TEXT` | Yes | ISO 8601 Timestamp | `YYYY-MM-DDTHH:MM:SS` (or null) | `resumed_at >= paused_at` (except Edge Case #3) | Timestamp SLA clock restarted |
| `pause_reason` | `TEXT` | Yes | None | Text | Operational justification | Justification for timer pause |
| `is_breached` | `BOOLEAN` / `INTEGER` | No | Default `FALSE` | `TRUE` / `FALSE` | Set `TRUE` when breached | Target deadline breach indicator |
| `breached_at` | `VARCHAR(32)` / `TEXT` | Yes | ISO 8601 Timestamp | `YYYY-MM-DDTHH:MM:SS` (or null) | Required if `is_breached=TRUE` | Timestamp deadline expired |
| `status` | `VARCHAR(16)` / `TEXT` | No | Enum | `Active`, `Paused`, `Met`, `Breached` | Must match SLA status enum | Current SLA stopwatch state |

---

### Entity 10: `messages`
Full customer-agent interaction log and internal collaboration notes.

| Field Name | Type (PG / SQLite) | Nullable | Constraints & Keys | Allowed Values / Format | Validation Rules | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `message_id` | `VARCHAR(64)` / `TEXT` | No | **Primary Key** | Strict Format: `MSG-<complaint-id>-001` (e.g. `MSG-CMP-2026-000001-001`) | Format regex `^MSG-CMP-\d{4}-\d{6}-\d{3}$` | Sequential zero-padded message code per complaint |
| `complaint_id` | `VARCHAR(32)` / `TEXT` | No | **Foreign Key** (`complaints.complaint_id`) | `CMP-2026-%06d` | Must exist in `complaints` | Parent complaint thread |
| `sender_type` | `VARCHAR(16)` / `TEXT` | No | Enum | `Customer`, `Agent`, `System` | Must match sender enum | Message author party |
| `message_text` | `TEXT` | No | Non-empty | Text content | Strictly non-empty string | Content of communication |
| `sent_at` | `VARCHAR(32)` / `TEXT` | No | ISO 8601 Timestamp | `YYYY-MM-DDTHH:MM:SS` | `sent_at >= complaint.created_at` | Timestamp dispatch occurred |
| `is_internal` | `BOOLEAN` / `INTEGER` | No | Default `FALSE` | `TRUE` / `FALSE` | `TRUE` only if sender is `Agent`/`System` | Internal caseworker note flag |

---

### Entity 11: `resolutions`
Legal and financial settlement sign-off committing case closure.

| Field Name | Type (PG / SQLite) | Nullable | Constraints & Keys | Allowed Values / Format | Validation Rules | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `resolution_id` | `VARCHAR(32)` / `TEXT` | No | **Primary Key** | Strict Format: `RES-<complaint-id>` (e.g. `RES-CMP-2026-000001`) | Format regex `^RES-CMP-\d{4}-\d{6}$` | Unique resolution certificate ID keyed to complaint |
| `complaint_id` | `VARCHAR(32)` / `TEXT` | No | **Foreign Key** (`complaints.complaint_id`) | `CMP-2026-%06d` | 1-to-1 relationship with resolved complaints | Resolved complaint ticket |
| `resolution_type` | `VARCHAR(32)` / `TEXT` | No | Enum | `Refund`, `Replacement`, `Apology`, `Fix Applied`, `Escalated Externally`, `No Action Required` | Must match resolution enum | Formal closure strategy |
| `resolved_by` | `VARCHAR(32)` / `TEXT` | No | None | Agent ID (e.g. `AGT-SR-01`) | Assigned caseworker badge | Authorizing caseworker |
| `resolved_at` | `VARCHAR(32)` / `TEXT` | No | ISO 8601 Timestamp | `YYYY-MM-DDTHH:MM:SS` | `resolved_at >= complaint.created_at` (except Edge Case #2) | Closure commit timestamp |
| `notes` | `TEXT` | Yes | None | Text remarks | Operational audit notes | Settlement justification remarks |
| `refund_amount` | `NUMERIC(10,2)` / `REAL` | Yes | Default `0.00` | `0.00` to `9999.99` (£ GBP) | Values `> 250.00` require Approver authorization | Refund sum |

---

### Supplementary Entity: `surveys`
Customer satisfaction (CSAT) and Net Promoter Score (NPS) feedback.

| Field Name | Type (PG / SQLite) | Nullable | Constraints & Keys | Allowed Values / Format | Validation Rules | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `survey_id` | `VARCHAR(32)` / `TEXT` | No | **Primary Key** | Sequential `SRV-000001` to `SRV-000800+` | Format regex `^SRV-\d{6}$` | Unique survey evaluation code |
| `complaint_id` | `VARCHAR(32)` / `TEXT` | No | **Foreign Key** (`complaints.complaint_id`) | `CMP-2026-%06d` | Must exist in `complaints` | Evaluated complaint ticket |
| `rating` | `INTEGER` | No | Check `1 <= rating <= 5` | `1` (Terrible) to `5` (Excellent) | CSAT integer score 1 to 5 | CSAT star rating |
| `feedback_text` | `TEXT` | Yes | None | Text | Non-empty verbatim feedback | Customer verbatim comments |
| `submitted_at` | `VARCHAR(32)` / `TEXT` | No | ISO 8601 Timestamp | `YYYY-MM-DDTHH:MM:SS` | `submitted_at >= resolution.resolved_at` (except Edge Case #6) | Customer submission time |
| `nps_score` | `INTEGER` | Yes | Check `0 <= nps <= 10` | `0` (Detractor) to `10` (Promoter) | NPS integer score 0 to 10 | Net Promoter Score index |

---

## 3. Negative Test Cases & Anomaly Injection Specification

To rigorously evaluate observability, data governance, and automated anomaly detection, exactly 6 mandatory negative test cases are injected into deterministic sequential tickets (`CMP-2026-000001` through `CMP-2026-000006`). These labels are completely isolated in standalone ground-truth export files (`ground_truth.json` and `ground_truth.csv`) to **prevent label leakage into input features or training sets**:

| Test Case | Target Entity | Injected Record | Defect Type | Validation Rule Triggered | Isolated Ground Truth File |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Missing Customer** | `complaints` | `CMP-2026-000001` | Null/empty `customer_id` | `FK_CUSTOMER_MISSING` | `ground_truth.json` / `csv` |
| **2. Inverted Resolution** | `resolutions` | `RES-000001` (on `CMP-2026-000002`) | Chronological inversion: `resolved_at < created_at` | `DATE_RESOLUTION_BEFORE_COMPLAINT` | `ground_truth.json` / `csv` |
| **3. Unresumed SLA Pause** | `sla_clocks` | `SLA-000003` (on `CMP-2026-000003`) | Clock paused indefinitely without `resumed_at` | `DATE_SLA_PAUSE_NO_RESUME` | `ground_truth.json` / `csv` |
| **4. Unlinked Repeat Issue** | `complaints` | `CMP-2026-000004` | `recurrence_count=3` with null `parent_complaint_id` | `REPEAT_ISSUE_NOT_LINKED` | `ground_truth.json` / `csv` |
| **5. Safety Queue Misroute** | `complaints`, `assignments` | `CMP-2026-000005` | Product safety hazard misclassified as `LOW` priority routed to `General-Support` | `PRIORITY_SAFETY_ANOMALY` | `ground_truth.json` / `csv` |
| **6. Premature Survey** | `surveys` | `SRV-000001` (on `CMP-2026-000006`) | CSAT survey timestamp precedes case resolution (`submitted_at < resolved_at`) | `DATE_SURVEY_BEFORE_CLOSURE` | `ground_truth.json` / `csv` |

---

## 4. Master Volume & Integrity Verification

Executing generation at standard baseline scale (`scale=1.0`) produces the exact volumes mandated by the problem statement:
- **Customers:** 5,000 records (`CUS-000001` to `CUS-005000`)
- **Orders:** 8,000 records (`ORD-2026-000001` to `ORD-2026-008000`)
- **Complaints:** 2,000 baseline records (`CMP-2026-000001` to `CMP-2026-002000`)
- **Messages:** 6,000 interaction logs (`MSG-CMP-2026-xxxxxx-xxx`)
- **Reproducibility:** Seed `20261022` yields identical SHA-256 cryptographic hashes and matching row counts across 100% of tables on repeated runs.
