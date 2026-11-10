# 🏆 Complaint Lifecycle Engine
**Enterprise AI-Powered Complaint Management, SLA Orchestration & Event Sourcing Platform**  
*Built for the Associate AI Forward Deployed Engineer (FDE) Hackathon*

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon%20Cloud-336791.svg)](https://neon.tech/)
[![Tests](https://img.shields.io/badge/Tests-9%2F9%20Passed-brightgreen.svg)](#-test-results)
[![Live API](https://img.shields.io/badge/Live%20API-7%2F7%20Passed-brightgreen.svg)](#-live-api-verification-output)
[![Reproducibility](https://img.shields.io/badge/Reproducibility-Bit--Level%20Verified-success.svg)](#-reproducibility-verification)
[![Ground Truth](https://img.shields.io/badge/Ground%20Truth-6%20Edge%20Cases%20Isolated-orange.svg)](#-injected-edge-cases--ground-truth)

---

## 📋 Executive Summary

The **Complaint Lifecycle Engine** is an industrial-grade end-to-end platform that automates:
- Customer complaint **classification & AI triage** (Amazon Bedrock Claude 3 Haiku)
- **Priority determination** via deterministic rule engine (Safety → CRITICAL, >£250 → Approver threshold)
- **SLA clock orchestration** with pause/resume/breach detection
- **Ownership routing** to specialist teams (Safety-Response, Billing, Technical, General)
- **Resolution settlement** with £250 Approver authorization rule
- **CSAT & NPS feedback tracking**
- **Immutable event sourcing** — every state transition is permanently logged
- **Bit-level deterministic reproducibility** with SHA-256 verification (seed `20261022`)

**Tech Stack:** FastAPI · Amazon Bedrock Claude 3 Haiku · PostgreSQL (Neon Cloud) · SQLite · Python 3.11

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Multi-Channel Ingestion                       │
│         Email  ·  Web Portal  ·  Mobile App  ·  Phone/CRM       │
└─────────────────────────┬───────────────────────────────────────┘
                           │
┌─────────────────────────▼───────────────────────────────────────┐
│                FastAPI REST API Gateway (/docs)                  │
│                     src/api.py                                   │
└──────┬──────────────────┬──────────────────────┬────────────────┘
       │                  │                       │
┌──────▼──────┐  ┌────────▼────────┐  ┌──────────▼──────────────┐
│  AI Engine  │  │  Rule Engine    │  │  Event Sourcing Engine   │
│  Bedrock    │  │  Priority/SLA   │  │  complaint_events table  │
│  Claude 3   │  │  Routing/Assign │  │  Immutable Audit Log     │
└──────┬──────┘  └────────┬────────┘  └──────────┬──────────────┘
       │                  │                       │
┌──────▼──────────────────▼───────────────────────▼──────────────┐
│          Dual-Engine Persistence Layer  (src/db.py)             │
│    PostgreSQL on Neon Cloud    ·    SQLite (Local Fallback)      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
complaint-lifecycle-engine/
│
├── src/                          # Backend Python services
│   ├── __init__.py
│   ├── api.py                    # FastAPI REST API (all endpoints)
│   ├── db.py                     # Dual-engine persistence (PostgreSQL + SQLite)
│   ├── ai_engine.py              # Amazon Bedrock Claude 3 Haiku + fallback
│   ├── generator.py              # Deterministic synthetic data generator
│   ├── validator.py              # 7-layer validation engine
│   ├── exporter.py               # CSV / JSON / SQL exporter
│   ├── ground_truth.py           # Ground-truth anomaly label isolation
│   ├── schema.py                 # Reference data, enums, priority rules
│   └── run.py                    # Master orchestrator CLI
│
├── frontend/
│   ├── index.html                # Executive Control Plane UI (responsive)
│   └── README.md
│
├── tests/
│   ├── __init__.py
│   ├── test_system.py            # Automated pytest suite (9 tests)
│   └── verify_live_api.py        # Live end-to-end API verification (7 tests)
│
├── docs/
│   ├── data_dictionary.md        # 11-entity schema with types, constraints, enums
│   ├── architecture.md           # System design & state machine diagrams
│   └── screenshots/              # Output screenshots for verification
│
├── output/
│   ├── csv/                      # CSV exports (12 entities)
│   ├── json/                     # JSON exports (12 entities)
│   ├── sql/                      # schema.sql + seed.sql
│   ├── ground_truth/
│   │   ├── ground_truth.json     # 6 labelled edge cases (zero feature leakage)
│   │   └── ground_truth.csv
│   ├── manifest.json             # Row counts & file paths
│   ├── reproducibility_report.json  # SHA-256 bit-level match proof
│   ├── validation_summary.json   # 0 genuine defects + 6 expected anomalies
│   └── complaints.db             # Local SQLite (pre-seeded baseline)
│
├── .env.example                  # Environment configuration template
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── package.json                  # npm scripts: build, test, start
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Balaswamyvasamsetti/complaint-lifecycle-engine.git
cd complaint-lifecycle-engine
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env — set DATABASE_URL and optionally AWS_ACCESS_KEY_ID
```

| Variable | Required | Description |
|---|:---:|---|
| `DATABASE_URL` | Recommended | Neon PostgreSQL connection string |
| `AWS_ACCESS_KEY_ID` | Optional | For live Bedrock Claude calls |
| `AWS_SECRET_ACCESS_KEY` | Optional | Paired with above |
| `AWS_DEFAULT_REGION` | Optional | e.g. `eu-west-2` |

> If `DATABASE_URL` is unset → system auto-falls back to SQLite.  
> If AWS keys absent → system uses deterministic rule-based fallback (no hang, no error).

### 3. Generate Synthetic Dataset

```bash
# Full baseline (5,000 customers · 8,000 orders · 2,000 complaints · 6,000 messages)
python src/run.py --scale 1.0 --clean

# 10% scale for quick testing
python src/run.py --scale 0.1
```

### 4. Run Test Suite

```bash
python -m pytest tests/ -v
```

### 5. Start API Server

```bash
python -m uvicorn src.api:app --reload --host 127.0.0.1 --port 8000
```

| URL | Description |
|---|---|
| http://localhost:8000/dashboard | Executive Control Plane UI |
| http://localhost:8000/docs | Interactive Swagger API docs |
| http://localhost:8000/health | Health probe + DB status |

### 6. Verify Reproducibility

```bash
python src/run.py --reproducibility-check
```

---

## ✅ Test Results

### Pytest Suite — 9/9 PASSED

```
tests/test_system.py::test_schema_reference_data              PASSED  [  11%]
tests/test_system.py::test_deterministic_id_conventions       PASSED  [  22%]
tests/test_system.py::test_priority_rule_engine               PASSED  [  33%]
tests/test_system.py::test_sla_calculation                    PASSED  [  44%]
tests/test_system.py::test_validation_engine                  PASSED  [  55%]
tests/test_system.py::test_ground_truth_isolation             PASSED  [  66%]
tests/test_system.py::test_reproducibility                    PASSED  [  77%]
tests/test_system.py::test_database_persistence_and_event_sourcing  PASSED  [  88%]
tests/test_system.py::test_fastapi_rest_endpoints             PASSED  [ 100%]

========================= 9 passed in 49.23s =========================
```

---

## 🔴 Live API Verification Output

All 7 end-to-end live tests against **Neon Cloud PostgreSQL**:

```
=================================================================
  LIVE API END-TO-END VERIFICATION
=================================================================

[TEST 1/7] Probing /health...
  -> Health Status: ok | DB: connected (PostgreSQL)

[TEST 2/7] Submitting new complaint via POST /complaints...
  -> Complaint Created: CMP-2026-002005
  -> AI Category:       Product Safety
  -> Priority:          CRITICAL (SLA: 1.0 hrs)
  -> Assigned Team:     Safety-Response (Agent: AGT-SR-02)
  -> SLA Deadline:      2026-11-10T08:50:53

[TEST 3/7] Checking SLA clock via GET /complaints/CMP-2026-002005/sla...
  -> SLA Status: Active | Hours Remaining: 1.00

[TEST 4/7] Testing SLA pause/resume...
  -> Clock Paused: Paused
  -> Clock Resumed: Active (Adjusted Deadline: 2026-11-10T08:50:57)

[TEST 5/7] Resolving complaint via POST /complaints/CMP-2026-002005/resolve...
  -> Resolution: Refund | Refund: £299.99
  -> Approver Sign-off Required: True (> £250.00 rule)

[TEST 6/7] Submitting CSAT & NPS survey...
  -> Survey Logged: ID SRV-000779

[TEST 7/7] Verifying immutable event sourcing timeline & analytics...
  -> Audit Trace: 7 events captured:
     * [2026-11-10T07:50:51] ASSIGNED             by System Administrator -> State: Safety-Response
     * [2026-11-10T07:50:55] COMPLAINT_CREATED    by Business Requester   -> State: Open
     * [2026-11-10T07:51:00] SLA_PAUSED           by AGT-SR-01            -> State: Paused
     * [2026-11-10T07:51:04] SLA_RESUMED          by Agent                -> State: Active
     * [2026-11-10T07:51:10] STATUS_CHANGED       by AGT-SR-01            -> State: Resolved
     * [2026-11-10T07:51:12] RESOLVED             by AGT-SR-01            -> State: Resolved
     * [2026-11-10T07:51:17] SURVEY_SUBMITTED     by Business Requester   -> State: Closed

  -> Operational KPIs:
     Total Complaints:     2005
     Resolved Complaints:  780
     SLA Breach Rate:      26.73%
     Average CSAT:         3.74 / 5.0
     Average NPS:          6.47 / 10.0

=================================================================
  ALL LIVE API VERIFICATION TESTS PASSED SUCCESSFULLY!
=================================================================
```

---

## 🔁 Reproducibility Verification

```
=================================================================
  DETERMINISTIC REPRODUCIBILITY CHECK  (Seed: 20261022)
=================================================================

  Run 1 SHA-256: bd490d445f166ceb043c8733eaec5da097f05b3fa7b2f5239bd390197a116cbc
  Run 2 SHA-256: bd490d445f166ceb043c8733eaec5da097f05b3fa7b2f5239bd390197a116cbc

  Table-by-table comparison (all 13 tables):
  ┌─────────────────────┬────────┬────────┬─────────────┬────────────────┐
  │ Table               │ Run 1  │ Run 2  │ Rows Match  │ Checksum Match │
  ├─────────────────────┼────────┼────────┼─────────────┼────────────────┤
  │ anomalies           │      6 │      6 │ ✅ MATCH    │ ✅ MATCH       │
  │ assignments         │    216 │    216 │ ✅ MATCH    │ ✅ MATCH       │
  │ categories          │     10 │     10 │ ✅ MATCH    │ ✅ MATCH       │
  │ complaint_events    │    578 │    578 │ ✅ MATCH    │ ✅ MATCH       │
  │ complaints          │    200 │    200 │ ✅ MATCH    │ ✅ MATCH       │
  │ customers           │    500 │    500 │ ✅ MATCH    │ ✅ MATCH       │
  │ messages            │    600 │    600 │ ✅ MATCH    │ ✅ MATCH       │
  │ orders              │    800 │    800 │ ✅ MATCH    │ ✅ MATCH       │
  │ priority_rules      │      4 │      4 │ ✅ MATCH    │ ✅ MATCH       │
  │ products            │     15 │     15 │ ✅ MATCH    │ ✅ MATCH       │
  │ resolutions         │     83 │     83 │ ✅ MATCH    │ ✅ MATCH       │
  │ sla_clocks          │    200 │    200 │ ✅ MATCH    │ ✅ MATCH       │
  │ surveys             │     82 │     82 │ ✅ MATCH    │ ✅ MATCH       │
  └─────────────────────┴────────┴────────┴─────────────┴────────────────┘

  Overall Status: PASSED — 100% BIT-LEVEL MATCH
=================================================================
```

---

## 📊 Dataset Volume (Full Scale 1.0x)

| Table | Row Count | Description |
|---|:---:|---|
| `customers` | **5,000** | Synthetic UK customers with zero-padded `CUS-000001` IDs |
| `products` | 15 | Product catalogue reference |
| `orders` | **8,000** | Orders linked to customers, `ORD-2026-000001` format |
| `categories` | 10 | Complaint category taxonomy |
| `priority_rules` | 4 | Deterministic SLA multiplier rules |
| `complaints` | **2,000** | Zero-padded `CMP-2026-000001` through `CMP-2026-002000` |
| `complaint_events` | 5,743 | Immutable audit event log |
| `assignments` | 2,193 | Full ownership history |
| `sla_clocks` | 2,000 | 1:1 binding to complaints |
| `messages` | **6,000** | Customer/agent communication threads |
| `resolutions` | 775 | Settled complaint resolutions |
| `surveys` | 775 | CSAT + NPS feedback records |
| `anomalies` | **6** | Injected edge cases (isolated in ground truth) |

---

## 🚨 Injected Edge Cases & Ground Truth

All 6 mandatory negative test cases are **deliberately injected** into the first 6 sequential complaint IDs and **strictly isolated** in `output/ground_truth/` — labels are stripped from all feature CSVs/JSONs to prevent target leakage.

```json
[
  {
    "complaint_id": "CMP-2026-000001",
    "issue_type": "missing_customer",
    "anomaly_category": "Referential Integrity",
    "description": "Complaint submitted without a valid customer reference",
    "entity_affected": "complaints.customer_id",
    "rule_violated": "FK_CUSTOMER_MISSING"
  },
  {
    "complaint_id": "CMP-2026-000002",
    "issue_type": "resolution_before_complaint",
    "anomaly_category": "Chronological Inversion",
    "description": "Resolution timestamp precedes complaint creation timestamp",
    "entity_affected": "resolutions.resolved_at",
    "rule_violated": "DATE_RESOLUTION_BEFORE_COMPLAINT"
  },
  {
    "complaint_id": "CMP-2026-000003",
    "issue_type": "sla_pause_no_resume",
    "anomaly_category": "SLA State Machine",
    "description": "SLA clock was paused but never resumed — time frozen incorrectly",
    "entity_affected": "sla_clocks.resumed_at",
    "rule_violated": "DATE_SLA_PAUSE_NO_RESUME"
  },
  {
    "complaint_id": "CMP-2026-000004",
    "issue_type": "repeat_not_linked",
    "anomaly_category": "Duplicate Detection",
    "description": "Repeat complaint (recurrence_count >= 2) has no parent_complaint_id link",
    "entity_affected": "complaints.parent_complaint_id",
    "rule_violated": "REPEAT_ISSUE_NOT_LINKED"
  },
  {
    "complaint_id": "CMP-2026-000005",
    "issue_type": "safety_low_priority",
    "anomaly_category": "Priority Rule Engine",
    "description": "Critical safety issue misrouted to low-priority queue instead of Safety-Response",
    "entity_affected": "complaints.priority",
    "rule_violated": "PRIORITY_SAFETY_ANOMALY"
  },
  {
    "complaint_id": "CMP-2026-000006",
    "issue_type": "survey_before_closure",
    "anomaly_category": "Lifecycle State Flow",
    "description": "CSAT survey submitted before the complaint was formally resolved",
    "entity_affected": "surveys.submitted_at",
    "rule_violated": "DATE_SURVEY_BEFORE_CLOSURE"
  }
]
```

> **Zero Label Leakage Confirmed:** `output/csv/complaints.csv` header does **NOT** contain `issue_type`, `anomaly_category`, `description`, `entity_affected`, or `rule_violated`.

---

## 🔑 ID Conventions (Zero-Padded Sequential)

| Entity | Format | Example |
|---|---|---|
| Customer | `CUS-{6d}` | `CUS-000001` |
| Order | `ORD-2026-{6d}` | `ORD-2026-000001` |
| Complaint | `CMP-2026-{6d}` | `CMP-2026-000001` |
| Assignment | `ASN-{6d}` | `ASN-000001` |
| SLA Clock | `SLA-{6d}` | `SLA-000001` |
| Message | `MSG-{6d}` | `MSG-000001` |
| Resolution | `RES-{6d}` | `RES-000001` |
| Survey | `SRV-{6d}` | `SRV-000001` |
| Event | `EVT-{6d}` | `EVT-000001` |

---

## 📡 REST API Reference

| Method | Endpoint | Actor | Description |
|---|---|---|---|
| `GET` | `/health` | System | Health check & DB connection probe |
| `POST` | `/complaints` | Requester | Ingest complaint — AI triage, priority, routing |
| `GET` | `/complaints` | Operations | Query with status/priority/category filters |
| `GET` | `/complaints/{id}` | Operations | Full detail: SLA, assignment, resolution |
| `PATCH` | `/complaints/{id}/status` | Process Owner | Advance state machine, log event |
| `GET` | `/complaints/{id}/events` | Auditor | Immutable event sourcing timeline |
| `GET` | `/complaints/{id}/assignments` | Process Owner | Full ownership history |
| `POST` | `/complaints/{id}/reassign` | Process Owner | Escalate or reassign ticket |
| `GET` | `/complaints/{id}/sla` | Process Owner | Real-time SLA hours remaining |
| `POST` | `/complaints/{id}/sla/pause` | Agent | Pause SLA clock (awaiting info) |
| `POST` | `/complaints/{id}/sla/resume` | Agent | Resume clock, adjust deadline |
| `POST` | `/complaints/{id}/resolve` | Agent/Approver | Conclude; checks £250 Approver threshold |
| `GET` | `/complaints/{id}/messages` | Requester/Agent | Chronological communication thread |
| `POST` | `/complaints/{id}/messages` | Requester/Agent | Post customer or internal agent note |
| `POST` | `/complaints/{id}/survey` | Requester | Record CSAT (1-5) and NPS (0-10) |
| `GET` | `/analytics/summary` | Analyst | KPIs: SLA breach rate, CSAT, NPS |
| `GET` | `/ground-truth` | Analyst | Isolated ground-truth anomalies |
| `POST` | `/ai/classify` | AI Direct | Test Bedrock Claude classification |
| `POST` | `/ai/sentiment` | AI Direct | Test Bedrock Claude sentiment |
| `GET` | `/dashboard` | All | Executive Control Plane UI |

---

## 📏 10-Step Rubric Compliance Matrix

| Step | Requirement | Implementation | Status |
|:---:|---|---|:---:|
| **1** | Data dictionary for 11+ entities (types, nullability, constraints, enums) | [`docs/data_dictionary.md`](docs/data_dictionary.md) | ✅ |
| **2** | Parent tables first, then dependent transaction & event records | [`src/generator.py`](src/generator.py) | ✅ |
| **3** | Zero-padded sequential IDs: `CUS-000001`, `ORD-2026-000001`, `CMP-2026-000001` | [`src/generator.py`](src/generator.py) | ✅ |
| **4** | 5,000 customers · 8,000 orders · 2,000 complaints · 6,000 messages (seed `20261022`) | `python src/run.py --scale 1.0` | ✅ |
| **5** | 6 labelled edge cases injected & isolated without feature leakage | [`src/generator.py`](src/generator.py) · [`src/ground_truth.py`](src/ground_truth.py) | ✅ |
| **6** | Derived values: order totals, SLA deadlines, breach flags from source data | [`src/generator.py`](src/generator.py) | ✅ |
| **7** | Separate `ground_truth.csv` & `ground_truth.json` with zero label leakage | [`output/ground_truth/`](output/ground_truth/) | ✅ |
| **8** | 7-layer validation (PK, FK, enums, chronology, arithmetic, lifecycle, rules) | [`src/validator.py`](src/validator.py) | ✅ |
| **9** | Export CSV, JSON, SQL DDL+seed, manifest, validation summary | [`src/exporter.py`](src/exporter.py) | ✅ |
| **10** | Bit-level reproducibility: 2× generation with seed `20261022` → identical SHA-256 | `python src/run.py --reproducibility-check` | ✅ |

---

## 🗄️ Validation Summary

```json
{
  "status": "PASSED",
  "genuine_data_defects": 0,
  "expected_edge_cases_caught": 6,
  "defect_breakdown": {},
  "edge_case_breakdown": {
    "FK_CUSTOMER_MISSING": 1,
    "DATE_RESOLUTION_BEFORE_COMPLAINT": 1,
    "DATE_SLA_PAUSE_NO_RESUME": 1,
    "REPEAT_ISSUE_NOT_LINKED": 1,
    "PRIORITY_SAFETY_ANOMALY": 1,
    "DATE_SURVEY_BEFORE_CLOSURE": 1
  }
}
```

---

## 🛠️ Key Commands Reference

```bash
# --- TESTING ---
python -m pytest tests/ -v                           # 9/9 unit + integration tests
python tests/verify_live_api.py                      # 7/7 live API tests vs Neon DB

# --- DATA GENERATION ---
python src/run.py --scale 1.0 --clean                # Full 1.0x baseline (clean DB first)
python src/run.py --scale 0.1                        # Quick 10% dataset
python src/run.py --reproducibility-check            # SHA-256 bit-level match proof

# --- SERVER ---
python -m uvicorn src.api:app --reload --host 127.0.0.1 --port 8000

# --- DOCKER ---
docker-compose up --build
```

---

## 🔒 Data Provenance & Compliance

- **100% Synthetically Generated** — No real customer data, PII, or scraping involved
- **UK GDPR Compliant** — Names use reserved domains (`example.com`, `enterprise.co.uk`)
- Phone numbers prefixed `+44` are non-routable synthetic patterns
- All generated under a reproducible fixed seed for auditability

---

## 📄 License

MIT License — built for the Yottaflex Hackathon evaluation.
