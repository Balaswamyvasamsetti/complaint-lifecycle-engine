# Complaint Lifecycle Engine

**Enterprise AI-Driven Complaint Intelligence, SLA Orchestration & Event Sourcing Platform**  
*Engineered for the Associate AI Forward Deployed Engineer (FDE) Technical Evaluation*

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon%20Cloud-336791.svg)](https://neon.tech/)
[![SQLite](https://img.shields.io/badge/SQLite-Local%20Fallback-003B57.svg)](https://sqlite.org/)
[![Tests](https://img.shields.io/badge/Tests-9%2F9%20Passed-brightgreen.svg)](#test-results)
[![Live API](https://img.shields.io/badge/Live%20API-7%2F7%20Passed-brightgreen.svg)](#live-api-verification-output)
[![Reproducibility](https://img.shields.io/badge/Reproducibility-Bit--Level%20Verified-success.svg)](#reproducibility-verification)
[![Ground Truth](https://img.shields.io/badge/Ground%20Truth-6%20Edge%20Cases%20Isolated-orange.svg)](#injected-edge-cases--ground-truth)

---

## Executive Summary

The **Complaint Lifecycle Engine** is an industrial-grade platform designed to demonstrate the end-to-end responsibilities of an **AI Forward Deployed Engineer (FDE)**: bridging enterprise operational workflows, deterministic business rules, and LLM reasoning.

The system ingests multi-channel customer grievances, executes automated NLP classification via **Amazon Bedrock (Claude 3 Haiku)**, enforces hard governance rules (safety escalation, Approver financial thresholds, dynamic SLA timers), maintains an **immutable event-sourced audit ledger**, and exposes an **Executive Control Plane UI** for real-time operations.

```
+-----------------------------------------------------------------------------------------+
|                                    PLATFORM AT A GLANCE                                 |
+-----------------------------------------------------------------------------------------+
| Target Scale       | 5,000 Customers · 8,000 Orders · 2,000 Complaints · 6,000 Messages |
| ID Formatting      | Zero-Padded Sequential: CMP-2026-000001, CUS-000001, ORD-2026-000001|
| Persistence        | Dual-Engine: Neon Cloud PostgreSQL + Embedded SQLite Fallback      |
| AI Stack           | Amazon Bedrock (Claude 3 Haiku) + Semantic Rule Fallback (Zero AWS)|
| Governance         | 7-Layer Integrity Validation + 6 Isolated Ground-Truth Anomalies   |
| Reproducibility    | 100% Bit-Level Deterministic Verification (Seed 20261022)          |
| Web Cockpit        | Single-Page Responsive Control Plane UI (White Background Theme)   |
+-----------------------------------------------------------------------------------------+
```

---

## Key Architectural Highlights

### 1. Hybrid Intelligence: LLM Reasoning with Deterministic Guardrails
Unlike naive AI prototypes that let language models make unconstrained business decisions, this engine enforces a **strict two-tier decision hierarchy**:
- **Probabilistic Tier (Claude 3 Haiku):** Extracts grievance taxonomy (`CAT-01` through `CAT-10`), assesses customer sentiment polarity, synthesizes agent briefing notes, and formulates resolution advice.
- **Deterministic Tier (Rule Engine):** Hard-coded governance rules enforce regulatory boundaries. Product safety triggers (`is_safety_issue=True`) or fraud force priority to **CRITICAL** (1-hour SLA) regardless of sentiment. Refund concessions exceeding **£250.00** strictly mandate sign-off by a formal **Approver** role.

### 2. Event Sourcing & Regulatory Auditability
Every state machine transition, ownership reassignment, SLA pause, resolution settlement, and CSAT survey is recorded in the `complaint_events` table as an immutable domain event (`EVT-000001` format). State is never silently updated; a complete, tamper-proof chronological history is available via `/complaints/{id}/events`.

### 3. Bit-Level Deterministic Reproducibility
Running data generation across identical or separate environments with seed `20261022` yields exact row counts and bit-level identical SHA-256 composite hashes across all 13 database tables. Table hashes are continuously checked via `python src/run.py --reproducibility-check`.

### 4. Zero Target Leakage in ML Observability
The platform deliberately seeds **6 mandatory negative and edge scenarios** (missing foreign keys, chronological inversions, frozen SLA clocks, unlinked repeat grievances, safety queue misrouting, premature surveys). To prevent target leakage in future model training, ground-truth defect labels (`issue_type`, `anomaly_category`, `rule_violated`) are strictly isolated in `output/ground_truth/` and stripped from feature export files (`output/csv/` and `output/json/`).

### 5. Resilient Dual-Engine Persistence
The platform seamlessly auto-detects its environment:
- **Cloud Mode:** High-performance connection pooling against **PostgreSQL on Neon Cloud** over TLS.
- **Local Mode:** Self-contained, zero-dependency embedded **SQLite** storage (`output/complaints.db`).
- **Offline AI Fallback:** If AWS credentials are not configured, a rule-based semantic inference engine activates instantly with zero timeouts or process blocking.

---

## System Architecture

```
                                  MULTI-CHANNEL INGESTION
               [ Email ]      [ Web Portal ]      [ Mobile App ]      [ Phone / CRM ]
                   |                 |                   |                   |
                   +-----------------+---------+---------+-------------------+
                                               |
                                               v
                          FASTAPI APPLICATION GATEWAY  (src/api.py)
                          - Swagger / OpenAPI:  http://127.0.0.1:8000/docs
                          - Health Probe:       http://127.0.0.1:8000/health
                          - Control Plane UI:   http://127.0.0.1:8000/dashboard
                                               |
                   +---------------------------+---------------------------+
                   |                           |                           |
                   v                           v                           v
          [ AI INTELLIGENCE ]         [ GOVERNANCE ENGINE ]      [ EVENT SOURCING ]
            Amazon Bedrock              Deterministic Rules         complaint_events
            Claude 3 Haiku              - Safety: CRITICAL          Immutable Ledger
            - Category NLP              - >£250: Approver Gate      Full State Audit
            - Sentiment Polarity        - Dynamic SLA Clocks        Actor Traceability
            - Case Summarization        - Team / Agent Routing
                   |                           |                           |
                   +---------------------------+---------------------------+
                                               |
                                               v
                             DUAL-ENGINE PERSISTENCE (src/db.py)
                             - Production: PostgreSQL on Neon Cloud
                             - Local Mode: Embedded SQLite Engine
```

---

## 10-Step Rubric Compliance Matrix

This implementation addresses every specification requirement outlined in the technical problem statement:

| Step | Requirement | Technical Implementation | Status |
|:---:|---|---|:---:|
| **1** | Formal Data Dictionary for all 11+ entities, cardinality, nullability, enums & actors | Published at [`docs/data_dictionary.md`](docs/data_dictionary.md) covering full schema, types, constraints, and actor personas | COMPLETED |
| **2** | Hierarchical table creation order: parent master data first, followed by dependent transactions | Implemented in [`src/generator.py`](src/generator.py): `customers` and `products` generated first, then `orders`, `complaints`, `assignments`, `sla_clocks`, `messages`, `resolutions`, and `surveys` | COMPLETED |
| **3** | Strictly sequential, zero-padded deterministic IDs across all entities | Standardized in [`src/generator.py`](src/generator.py) & [`src/db.py`](src/db.py): `CUS-000001`, `ORD-2026-000001`, `CMP-2026-000001`, `ASN-000001`, `SLA-000001`, `MSG-000001`, `RES-000001`, `SRV-000001`, `EVT-000001` | COMPLETED |
| **4** | Generate baseline volume: 5,000 customers, 8,000 orders, 2,000 complaints, 6,000 messages (seed `20261022`) | Seeded into Neon Cloud PostgreSQL via `python src/run.py --scale 1.0 --clean`. Validated in `output/manifest.json` | COMPLETED |
| **5** | Deliberately inject 6 labeled edge cases covering critical boundary conditions | Seeded into sequential tickets `CMP-2026-000001` to `CMP-2026-000006` in [`src/generator.py`](src/generator.py) | COMPLETED |
| **6** | Calculate derived values (order exposure, SLA hours, deadline timestamps, breach flags) from source data | Calculated via deterministic helper functions in [`src/generator.py`](src/generator.py) | COMPLETED |
| **7** | Standalone `ground_truth.csv` and `ground_truth.json` with zero target leakage | Isolated in [`src/ground_truth.py`](src/ground_truth.py) and [`src/exporter.py`](src/exporter.py); feature CSVs strip all defect label columns | COMPLETED |
| **8** | 7-layer validation engine: PKs, FKs, enum ranges, chronological sanity, arithmetic reconciliation, lifecycle states | Validated via [`src/validator.py`](src/validator.py): reports 0 genuine data defects and verifies all 6 expected injected edge cases | COMPLETED |
| **9** | Multi-format export: CSV, JSON, SQL DDL & Seed scripts, manifest, validation summary | Exported to `output/csv/`, `output/json/`, `output/sql/schema.sql`, `output/sql/seed.sql`, and `output/manifest.json` | COMPLETED |
| **10** | Deterministic reproducibility check: 2x generation with seed `20261022` produces matching checksums | Verified via `python src/run.py --reproducibility-check`: 100% composite SHA-256 bit-level match across all 13 tables | COMPLETED |

---

## 6 Injected Negative Test Cases & Anomaly Specification

All 6 mandatory negative scenarios are seeded into deterministic sequential tickets (`CMP-2026-000001` through `CMP-2026-000006`) and completely isolated in `output/ground_truth/` to prevent label leakage:

| Complaint ID | Defect Category | Anomaly Type | Rule Violated | Technical Description |
|:---:|:---:|:---:|:---:|---|
| `CMP-2026-000001` | Referential Integrity | `missing_customer` | `FK_CUSTOMER_MISSING` | Complaint record submitted with an empty customer reference string |
| `CMP-2026-000002` | Chronological Inversion | `resolution_before_complaint` | `DATE_RESOLUTION_BEFORE_COMPLAINT` | Resolution timestamp (`resolved_at`) occurs chronologically before ticket creation (`created_at`) |
| `CMP-2026-000003` | SLA State Machine | `sla_pause_no_resume` | `DATE_SLA_PAUSE_NO_RESUME` | SLA clock was paused (`paused_at`) but never resumed, freezing elapsed time indefinitely |
| `CMP-2026-000004` | Duplicate Detection | `repeat_not_linked` | `REPEAT_ISSUE_NOT_LINKED` | Repeat complaint (`recurrence_count=3`) submitted without linking the parent complaint reference |
| `CMP-2026-000005` | Priority Rule Engine | `safety_low_priority` | `PRIORITY_SAFETY_ANOMALY` | Critical fire/burn hazard erroneously routed to the general low-priority queue |
| `CMP-2026-000006` | Lifecycle State Flow | `survey_before_closure` | `DATE_SURVEY_BEFORE_CLOSURE` | Post-resolution CSAT survey recorded prior to formal complaint resolution |

> [!IMPORTANT]
> **Zero Label Leakage Confirmed:** The production feature table `output/csv/complaints.csv` does not contain `issue_type`, `anomaly_category`, `description`, `entity_affected`, or `rule_violated` columns.

---

## Project Structure

```
complaint-lifecycle-engine/
├── docs/
│   ├── data_dictionary.md        # Comprehensive 11-entity schema, types, constraints, enums
│   ├── architecture.md           # System design, workflow diagrams, state machine blueprints
│   └── screenshots/              # Terminal verification logs for auditability
├── frontend/
│   ├── index.html                # Executive Control Plane UI (responsive, white theme)
│   └── README.md                 # UI architecture documentation
├── src/
│   ├── __init__.py
│   ├── schema.py                 # Reference master data, taxonomy categories, priority rules
│   ├── generator.py              # Deterministic synthetic data generator (Scale 1.0 & parameterized)
│   ├── validator.py              # 7-layer validation engine & anomaly detection
│   ├── exporter.py               # Multi-format exporter: CSV, JSON, SQL DDL & Seed
│   ├── ground_truth.py           # Ground truth anomaly label isolation
│   ├── db.py                     # Dual-engine persistence layer (PostgreSQL / Neon + SQLite)
│   ├── ai_engine.py              # Amazon Bedrock Claude engine + semantic fallback
│   ├── api.py                    # Production FastAPI REST service covering all actor workflows
│   └── run.py                    # Master orchestrator CLI (generate, validate, export, verify)
├── tests/
│   ├── __init__.py
│   ├── test_system.py            # Automated pytest suite (9 unit & integration tests)
│   └── verify_live_api.py        # End-to-end live API verification against Neon Cloud DB
├── output/
│   ├── csv/                      # Clean CSV exports for all 12 entities (zero leakage)
│   ├── json/                     # Clean JSON exports for all 12 entities
│   ├── sql/                      # schema.sql and seed.sql exports
│   ├── ground_truth/             # ground_truth.csv and ground_truth.json
│   ├── manifest.json             # Table manifest with row counts and file paths
│   ├── reproducibility_report.json # Bit-level composite SHA-256 proof
│   ├── validation_summary.json   # 7-layer validation audit report
│   └── complaints.db             # Local SQLite database pre-seeded with baseline scale
├── .env.example                  # Environment configuration template
├── Dockerfile                    # Containerization configuration
├── docker-compose.yml            # Multi-service container orchestration
├── requirements.txt              # Production Python dependencies
├── package.json                  # npm scripts for build, test, and execution
└── README.md                     # Platform documentation
```

---

## Evaluate in 60 Seconds

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/Balaswamyvasamsetti/complaint-lifecycle-engine.git
cd complaint-lifecycle-engine
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
```bash
cp .env.example .env
```
*(The system works out-of-the-box with embedded SQLite and rule-based AI fallback. To use Neon Cloud PostgreSQL or live Amazon Bedrock, populate `DATABASE_URL` and `AWS_ACCESS_KEY_ID` in `.env`)*

### 3. Run the Automated Test Suite (9/9 Tests)
```bash
python -m pytest tests/ -v
```

### 4. Verify Deterministic Bit-Level Reproducibility
```bash
python src/run.py --reproducibility-check
```

### 5. Launch the Executive Control Plane UI
```bash
python -m uvicorn src.api:app --reload --host 127.0.0.1 --port 8000
```
- **Executive Control Plane UI:** [http://localhost:8000/dashboard](http://localhost:8000/dashboard)
- **Interactive OpenAPI Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **System Health & Database Probe:** [http://localhost:8000/health](http://localhost:8000/health)

---

## Test Results

### Automated Pytest Suite — 9/9 PASSED

```
tests/test_system.py::test_schema_reference_data              PASSED  [ 11%]
tests/test_system.py::test_deterministic_id_conventions       PASSED  [ 22%]
tests/test_system.py::test_priority_rule_engine               PASSED  [ 33%]
tests/test_system.py::test_sla_calculation                    PASSED  [ 44%]
tests/test_system.py::test_validation_engine                  PASSED  [ 55%]
tests/test_system.py::test_ground_truth_isolation             PASSED  [ 66%]
tests/test_system.py::test_reproducibility                    PASSED  [ 77%]
tests/test_system.py::test_database_persistence_and_event_sourcing  PASSED  [ 88%]
tests/test_system.py::test_fastapi_rest_endpoints             PASSED  [100%]

========================= 9 passed in 49.23s =========================
```

---

## Live API Verification Output

Execution against **Neon Cloud PostgreSQL** covering the full complaint lifecycle:

```
=================================================================
  LIVE API END-TO-END VERIFICATION
=================================================================

[TEST 1/7] Probing /health...
  -> Health Status: ok | DB: connected (PostgreSQL)

[TEST 2/7] Submitting new complaint via POST /complaints...
  -> Complaint Created: CMP-2026-002010
  -> AI Category:       Product Safety
  -> Priority:          CRITICAL (SLA: 1.0 hrs)
  -> Assigned Team:     Safety-Response (Agent: AGT-SR-01)
  -> SLA Deadline:      2026-11-10T09:50:27

[TEST 3/7] Checking SLA clock via GET /complaints/CMP-2026-002010/sla...
  -> SLA Status: Active | Hours Remaining: 1.00

[TEST 4/7] Testing SLA pause/resume...
  -> Clock Paused: Paused
  -> Clock Resumed: Active (Adjusted Deadline: 2026-11-10T09:50:31)

[TEST 5/7] Resolving complaint via POST /complaints/CMP-2026-002010/resolve...
  -> Resolution: Refund | Refund: £299.99
  -> Approver Sign-off Required: True (> £250.00 rule)

[TEST 6/7] Submitting CSAT & NPS survey...
  -> Survey Logged: ID SRV-000782

[TEST 7/7] Verifying immutable event sourcing timeline & analytics...
  -> Audit Trace: 9 events captured:
     * [2026-11-10T08:50:26] ASSIGNED             by System Administrator -> State: Safety-Response
     * [2026-11-10T08:50:30] COMPLAINT_CREATED    by Business Requester   -> State: Open
     * [2026-11-10T08:50:33] MESSAGE_RECEIVED     by Customer             -> State: 
     * [2026-11-10T08:50:37] SLA_PAUSED           by AGT-SR-01            -> State: Paused
     * [2026-11-10T08:50:41] SLA_RESUMED          by Agent                -> State: Active
     * [2026-11-10T08:50:48] STATUS_CHANGED       by AGT-SR-01            -> State: Resolved
     * [2026-11-10T08:50:49] RESOLVED             by AGT-SR-01            -> State: Resolved
     * [2026-11-10T08:50:55] STATUS_CHANGED       by Business Requester   -> State: Closed
     * [2026-11-10T08:50:57] SURVEY_SUBMITTED     by Business Requester   -> State: Closed

  -> Operational KPIs:
     Total Complaints:     2010
     Resolved Complaints:  784
     SLA Breach Rate:      26.67%
     Average CSAT:         3.75 / 5.0
     Average NPS:          6.48 / 10.0

=================================================================
  ALL LIVE API VERIFICATION TESTS PASSED SUCCESSFULLY!
=================================================================
```

---

## Reproducibility Verification

```
=================================================================
  DETERMINISTIC REPRODUCIBILITY CHECK  (Seed: 20261022)
=================================================================

  Run 1 SHA-256: bd490d445f166ceb043c8733eaec5da097f05b3fa7b2f5239bd390197a116cbc
  Run 2 SHA-256: bd490d445f166ceb043c8733eaec5da097f05b3fa7b2f5239bd390197a116cbc

  Table-by-table comparison (all 13 tables):
  +---------------------+--------+--------+-------------+----------------+
  | Table               | Run 1  | Run 2  | Rows Match  | Checksum Match |
  +---------------------+--------+--------+-------------+----------------+
  | anomalies           |      6 |      6 | MATCH       | MATCH          |
  | assignments         |    216 |    216 | MATCH       | MATCH          |
  | categories          |     10 |     10 | MATCH       | MATCH          |
  | complaint_events    |    578 |    578 | MATCH       | MATCH          |
  | complaints          |    200 |    200 | MATCH       | MATCH          |
  | customers           |    500 |    500 | MATCH       | MATCH          |
  | messages            |    600 |    600 | MATCH       | MATCH          |
  | orders              |    800 |    800 | MATCH       | MATCH          |
  | priority_rules      |      4 |      4 | MATCH       | MATCH          |
  | products            |     15 |     15 | MATCH       | MATCH          |
  | resolutions         |     83 |     83 | MATCH       | MATCH          |
  | sla_clocks          |    200 |    200 | MATCH       | MATCH          |
  | surveys             |     82 |     82 | MATCH       | MATCH          |
  +---------------------+--------+--------+-------------+----------------+

  Overall Status: PASSED — 100% BIT-LEVEL MATCH
  Audit report saved: output/reproducibility_report.json
=================================================================
```

---

## Dataset Scale & Distribution (Scale 1.0x)

| Entity / Table | Record Count | Description | Primary Key Format |
|---|:---:|---|---|
| `customers` | **5,000** | Synthetic UK retail customers with segment & vulnerability indicators | `CUS-000001` |
| `products` | 15 | Reference product catalog with SKU, category, and safety flags | `PRD-001` |
| `orders` | **8,000** | Customer orders with purchase values and line-item details | `ORD-2026-000001` |
| `categories` | 10 | Standard grievance taxonomy (`CAT-01` to `CAT-10`) | `CAT-01` |
| `priority_rules` | 4 | Deterministic priority rules (`PR-01` to `PR-04`) | `PR-01` |
| `complaints` | **2,000** | Evaluated customer complaints with sentiment & priority | `CMP-2026-000001` |
| `complaint_events` | 5,743 | Immutable audit log of all domain state changes | `EVT-000001` |
| `assignments` | 2,193 | Full routing and ownership history across specialist queues | `ASN-000001` |
| `sla_clocks` | 2,000 | 1:1 binding tracking started, deadline, pause, and breach states | `SLA-000001` |
| `messages` | **6,000** | Chronological customer and internal caseworker notes | `MSG-000001` |
| `resolutions` | 775 | Formal legal/financial settlements committing case closure | `RES-000001` |
| `surveys` | 775 | Customer CSAT star ratings (1-5) and NPS scores (0-10) | `SRV-000001` |
| `anomalies` | **6** | Injected edge cases isolated in ground truth | `CMP-2026-000001` |

---

## REST API Reference

| Method | Endpoint | Actor Persona | Description |
|---|---|---|---|
| `GET` | `/health` | System | Health check & dual-engine persistence probe |
| `POST` | `/complaints` | Business Requester | Ingest complaint with AI triage, routing & SLA initiation |
| `GET` | `/complaints` | Operations Analyst | Query queue with status, priority, and category filters |
| `GET` | `/complaints/{id}` | Operations Analyst | Full detail: complaint, SLA clock, assignment & settlement |
| `PATCH` | `/complaints/{id}/status` | Process Owner | Advance lifecycle state machine and append audit event |
| `GET` | `/complaints/{id}/events` | Auditor / Compliance | Immutable event sourcing journal and actor traceability |
| `GET` | `/complaints/{id}/assignments` | Process Owner | Full ownership history (retains past agents and teams) |
| `POST` | `/complaints/{id}/reassign` | Process Owner | Escalate ticket to specialist team (e.g. Safety-Response) |
| `GET` | `/complaints/{id}/sla` | Caseworker | Real-time SLA hours remaining and breach indicator |
| `POST` | `/complaints/{id}/sla/pause` | Caseworker | Pause SLA clock (awaiting inspection or customer photos) |
| `POST` | `/complaints/{id}/sla/resume` | Caseworker | Resume SLA clock and adjust deadline timestamp |
| `POST` | `/complaints/{id}/resolve` | Caseworker / Approver | Settle case; enforces £250 Approver authorization gate |
| `GET` | `/complaints/{id}/messages` | Customer / Caseworker | Chronological communication thread |
| `POST` | `/complaints/{id}/messages` | Customer / Caseworker | Post customer response or internal caseworker note |
| `POST` | `/complaints/{id}/survey` | Business Requester | Record customer CSAT rating (1-5) and NPS score (0-10) |
| `GET` | `/analytics/summary` | Analyst / Leadership | Operational KPIs: SLA breach rate, CSAT, NPS, queues |
| `GET` | `/ground-truth` | Analyst / ML Engineer | Isolated ground-truth anomalies for benchmark evaluation |
| `POST` | `/ai/classify` | AI Direct | Test Bedrock Claude text classification |
| `POST` | `/ai/sentiment` | AI Direct | Test Bedrock Claude sentiment analysis |
| `POST` | `/ai/suggest-resolution`| AI Direct | Request Bedrock Claude settlement recommendations |
| `GET` | `/dashboard` | All Personas | Native Executive Control Plane UI |

---

## Primary Actor Personas & Workflows

1. **Business Requester (Customer / Branch Staff):**
   - Ingests complaints via Email, Web, Mobile App, or Phone.
   - Observes ticket progress in real-time.
   - Exchanges threaded messages with caseworkers.
   - Submits post-resolution CSAT (1 to 5 Stars) and NPS (0 to 10) evaluations.

2. **Process Owner (Operations Manager):**
   - Monitors active queue depths, team capacities, and SLA breach rates.
   - Triggers inter-team reassignments and escalations to specialist queues.
   - Audits lifecycle transition latencies and bottlenecks.

3. **Approver (Finance & Compliance Director):**
   - Reviews and authorizes high-value refund concessions exceeding **£250.00**.
   - Validates regulatory compliance for safety-critical product returns.

4. **Operations Analyst (BI & Quality Assurance):**
   - Audits classification accuracy and sentiment polarity distributions.
   - Evaluates priority rule conformance and detects misrouted queues.
   - Inspects isolated ground-truth anomaly benchmarks.

5. **System Administrator (DevOps / Reliability Engineer):**
   - Manages database engine connectivity (Neon Cloud vs. SQLite).
   - Oversees database schema migrations and seed scripts.
   - Monitors health probes and API latency metrics.

---

## Data Provenance & Legal Compliance

- **100% Lawfully Synthesized:** All records, identities, email addresses, order IDs, and synthetic flags are deterministically synthesized in memory. No scraping, proprietary data extraction, or personally identifiable information (PII) is involved.
- **UK GDPR & Privacy Compliance:** Phone numbers (`+44`) and emails use reserved non-routable domains (`example.com`, `enterprise.co.uk`) strictly for benchmark evaluation.

---

## License

Distributed under the MIT License. Developed for the Yottaflex Hackathon technical evaluation.
