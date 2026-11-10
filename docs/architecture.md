# Architecture & System Design — Complaint Lifecycle Engine
**System Context:** Associate AI Forward Deployed Engineer (FDE)  
**Core Technologies:** Amazon Bedrock (Claude 3 Haiku) | FastAPI | PostgreSQL (Neon) & SQLite | Pydantic v2

---

## 1. High-Level Architecture Overview

The **Complaint Lifecycle Engine** is an event-driven, AI-orchestrated microservice designed for multi-tier customer complaint management, automated SLA enforcement, and immutable auditability.

```mermaid
flowchart TD
    subgraph Ingestion["1. Multi-Channel Ingestion Layer"]
        A1["Email Channel"]
        A2["Web Portal"]
        A3["Mobile App"]
        A4["Phone / CRM"]
    end

    subgraph Intelligence["2. AI & Rule Governance Engine"]
        B1["Amazon Bedrock (Claude 3 Haiku)"]
        B2["Classification & Sentiment Analysis"]
        B3["Deterministic Priority Rules Engine"]
        B4["SLA Calculation & Routing Matrix"]
    end

    subgraph CoreEngine["3. Application Core & API Gateway"]
        C1["FastAPI REST API"]
        C2["Event Sourcing Engine (complaint_events)"]
        C3["SLA Clock Monitor & Escalation"]
        C4["Resolution & Approvals Workflow"]
    end

    subgraph Persistence["4. Dual-Engine Persistence Layer"]
        D1["PostgreSQL on Neon (Production Cloud)"]
        D2["SQLite (Local Deterministic Test Store)"]
    end

    subgraph Actors["5. Primary Actor Dashboards"]
        E1["Business Requester"]
        E2["Process Owner"]
        E3["Approver"]
        E4["Operations Analyst"]
        E5["System Administrator"]
    end

    Ingestion --> C1
    C1 --> Intelligence
    Intelligence --> C1
    C1 --> C2
    C2 --> Persistence
    Persistence --> C1
    C1 --> Actors
```

---

## 2. End-to-End Complaint Lifecycle Workflow

```mermaid
sequenceDiagram
    autonumber
    actor Requester as Business Requester
    participant API as FastAPI REST Gateway
    participant AI as Amazon Bedrock (Claude)
    participant Rules as Deterministic Rule Engine
    participant DB as Neon / SQLite Database
    participant Agent as Support Agent
    actor Approver as Financial Approver

    Requester->>API: POST /complaints (text, channel, order_id, order_value)
    API->>AI: Classify Category & Extract Sentiment
    AI-->>API: Category (e.g. Product Safety), Sentiment (Negative)
    API->>Rules: Evaluate Priority (Safety=True -> CRITICAL, Multiplier=0.25x)
    Rules-->>API: Priority: CRITICAL, SLA: 1.0 hour, Team: Safety-Response
    API->>DB: Persist Complaint, SLAClock, Initial Assignment
    API->>DB: Append Event (COMPLAINT_CREATED)
    API-->>Requester: 201 Created (ID, Deadline, Team, AI Summary)

    Agent->>API: PATCH /complaints/{id}/status (In Progress)
    API->>DB: Update Status & Append Event (STATUS_CHANGED)

    Agent->>API: POST /complaints/{id}/resolve (Refund: £350.00)
    Note over API,Approver: Refund > £250.00 triggers Approver authorization flag
    API->>Approver: Authorize High-Value Concession
    Approver-->>API: Concession Authorized
    API->>DB: Commit Resolution & Update SLA to 'Met'
    API->>DB: Append Event (RESOLVED)

    Requester->>API: POST /complaints/{id}/survey (CSAT: 5/5, NPS: 10)
    API->>DB: Commit Survey & Append Event (SURVEY_SUBMITTED)
```

---

## 3. Complaint State Lifecycle Machine

```mermaid
stateDiagram-v2
    [*] --> Open: Customer Ingestion
    Open --> In_Progress: Agent Triage
    Open --> Escalated: Auto-Escalation Threshold Met

    In_Progress --> Pending_Customer: Await Documentation (SLA Paused)
    Pending_Customer --> In_Progress: Customer Responds (SLA Resumed)

    In_Progress --> Escalated: Approaching SLA Breach / Senior Reassignment
    Escalated --> In_Progress: Tier-2 Specialist Assigned

    In_Progress --> Resolved: Settlement Concluded
    Escalated --> Resolved: Executive Resolution

    Resolved --> Closed: Survey Completed or 14-Day Inactivity
    Closed --> Reopened: Subsequent Dissatisfaction (Links parent_complaint_id)
    Reopened --> In_Progress: Reopened Case Review
```

---

## 4. SLA Governance & Escalation Matrix

The engine combines base SLA turnaround times by category with priority multipliers:
$$\text{SLA Hours} = \max\left(1.0, \text{default\_sla\_hours} \times \text{sla\_multiplier}\right)$$

| Category (`category_id`) | Base SLA | CRITICAL (0.25x) | HIGH (0.50x) | MEDIUM (1.00x) | LOW (1.50x) |
|---|---|---|---|---|---|
| **CAT-01: Billing & Payment** | 48 hrs | 12 hrs | 24 hrs | 48 hrs | 72 hrs |
| **CAT-02: Product Defect** | 72 hrs | 18 hrs | 36 hrs | 72 hrs | 108 hrs |
| **CAT-03: Delivery / Logistics** | 48 hrs | 12 hrs | 24 hrs | 48 hrs | 72 hrs |
| **CAT-04: Product Safety** | 4 hrs | **1 hr** | 2 hrs | 4 hrs | 6 hrs |
| **CAT-05: Customer Service** | 24 hrs | 6 hrs | 12 hrs | 24 hrs | 36 hrs |
| **CAT-06: Refund / Return** | 72 hrs | 18 hrs | 36 hrs | 72 hrs | 108 hrs |
| **CAT-07: Missing Order** | 24 hrs | 6 hrs | 12 hrs | 24 hrs | 36 hrs |
| **CAT-08: Technical / App Issue** | 96 hrs | 24 hrs | 48 hrs | 96 hrs | 144 hrs |
| **CAT-09: Fraud / Unauthorized** | 8 hrs | **2 hrs** | 4 hrs | 8 hrs | 12 hrs |
| **CAT-10: General Enquiry** | 120 hrs | 30 hrs | 60 hrs | 120 hrs | 180 hrs |

---

## 5. Primary Actor Role-Based Matrix

| Actor | Permitted API Actions | Audit Trail Event Generated |
|---|---|---|
| **Business Requester** | Submit complaint, send message, view status, submit CSAT/NPS survey. | `COMPLAINT_CREATED`, `MESSAGE_SENT`, `SURVEY_SUBMITTED`, `REOPENED` |
| **Process Owner** | Reassign cases, monitor breach rates, inspect queue depths, adjust priorities. | `ASSIGNED`, `STATUS_CHANGED`, `SLA_PAUSED`, `SLA_RESUMED` |
| **Approver** | Authorize high-value refunds (> £250.00), approve policy exceptions. | `RESOLUTION_APPROVED`, `RESOLVED` |
| **Operations Analyst** | Query `/analytics/summary`, inspect `/ground-truth`, evaluate model drift. | Read-only audit telemetry access. |
| **System Administrator** | Trigger generation pipelines (`run.py`), database migration, adjust SLA benchmarks. | System initialization, DDL execution, configuration updates. |

---

## 6. Dual-Engine Persistence Strategy

The system abstracts the database tier via `src/db.py`:
- **Neon (PostgreSQL):** When `DATABASE_URL` is configured (e.g. Neon connection string in `.env`), the application operates in enterprise cloud mode using `psycopg2` with foreign key enforcement and connection pooling.
- **SQLite:** When `DATABASE_URL` is unset, the engine defaults to `output/complaints.db`, maintaining zero-configuration local execution and 100% test independence.

---

## 7. AI Engine Resilience & Model Fallback

The AI layer in `src/ai_engine.py` invokes **Amazon Bedrock (Claude 3 Haiku)** via `boto3`:
1. If AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`) are valid, calls Claude with structured zero-shot prompts and JSON schema output enforcement.
2. If credentials are unset or the network is unavailable, seamlessly falls back to a deterministic semantic keyword rule engine, ensuring 100% test suite reliability and offline execution without errors.

