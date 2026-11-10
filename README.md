# Complaint Lifecycle Engine

An end-to-end AI-powered complaint management system built for the
**Associate AI Forward Deployed Engineer** role.

Classifies complaints, assigns owners, enforces SLAs, tracks resolution
and customer communication — with Amazon Bedrock (Claude) driving every
AI decision.

---

## Tech Stack

| Layer            | Technology                              | Purpose                                      |
|------------------|-----------------------------------------|----------------------------------------------|
| AI / LLM         | Amazon Bedrock — Claude 3 Haiku         | Classification, sentiment, priority, summary |
| API              | FastAPI + Uvicorn                       | REST endpoints for the full complaint lifecycle |
| Schema / Validation | Pydantic v2                          | Request/response models, type safety         |
| Data Processing  | Pandas + Python stdlib                  | Synthetic data generation, CSV/JSON export   |
| Persistence      | SQLite (via stdlib sqlite3)             | Local complaint, SLA, assignment, resolution store |
| AWS SDK          | boto3 / botocore                        | Bedrock runtime invocation                   |
| Language         | Python 3.8+                             | Core runtime                                 |
| Config           | python-dotenv                           | Environment variable management              |
| Version Control  | Git + GitHub                            | Source control                               |

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Balaswamyvasamsetti/complaint-lifecycle-engine.git
cd complaint-lifecycle-engine

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment (copy and fill in AWS credentials)
cp .env.example .env

# 4. Generate synthetic dataset
python src/run.py

# 5. Start the API server
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: **http://localhost:8000/docs**

---

## Project Structure

```
complaint-lifecycle-engine/
├── src/
│   ├── schema.py        # Master reference data, enums, business rules
│   ├── generator.py     # Synthetic data generation (seed=20261022)
│   ├── validator.py     # PK/FK/enum/date/lifecycle/arithmetic validation
│   ├── exporter.py      # CSV + JSON export (ground truth stripped)
│   ├── ground_truth.py  # Separate anomaly/edge-case export
│   ├── db.py            # SQLite persistence layer
│   ├── ai_engine.py     # Amazon Bedrock (Claude) AI functions
│   ├── api.py           # FastAPI REST API
│   └── run.py           # Data generation orchestrator
├── output/
│   ├── csv/             # Input feature CSVs
│   ├── json/            # Input feature JSONs
│   ├── ground_truth/    # ground_truth.csv + ground_truth.json
│   ├── manifest.json    # Table names, row counts, file paths
│   └── complaints.db    # SQLite database (generated on first run)
├── docs/
│   └── data_dictionary.md  # Full field-level schema documentation
├── data/
│   └── README.md           # External data governance notes
├── requirements.txt
├── .env.example
└── README.md
```

---

## API Endpoints

### Complaints

| Method | Endpoint                              | Description                                      |
|--------|---------------------------------------|--------------------------------------------------|
| POST   | `/complaints`                         | Submit complaint — AI classifies + assigns + SLA |
| GET    | `/complaints`                         | List complaints (filter by status/priority)      |
| GET    | `/complaints/{id}`                    | Get complaint detail                             |
| PATCH  | `/complaints/{id}/status`             | Update complaint status                          |
| GET    | `/complaints/{id}/assignment`         | Get current team/agent assignment                |
| GET    | `/complaints/{id}/sla`                | Get SLA clock + time remaining                   |
| POST   | `/complaints/{id}/resolve`            | Submit resolution                                |
| GET    | `/complaints/{id}/resolution`         | Get resolution detail                            |
| POST   | `/complaints/{id}/survey`             | Submit post-resolution survey                    |

### AI (Amazon Bedrock)

| Method | Endpoint                   | Description                                      |
|--------|----------------------------|--------------------------------------------------|
| POST   | `/ai/classify`             | Classify complaint text into category            |
| POST   | `/ai/sentiment`            | Analyse complaint sentiment                      |
| POST   | `/ai/suggest-resolution`   | Get AI resolution suggestion for a complaint     |

### Health

| Method | Endpoint    | Description     |
|--------|-------------|-----------------|
| GET    | `/`         | Service info    |
| GET    | `/health`   | Health check    |

---

## AI Workflow (Amazon Bedrock — Claude)

```
Complaint Text
      |
      v
[1] classify_complaint()   --> category_id, category_name, confidence
      |
      v
[2] analyse_sentiment()    --> sentiment (Positive/Neutral/Negative), score
      |
      v
[3] predict_priority()     --> priority (CRITICAL/HIGH/MEDIUM/LOW), rule, reason
      |
      v
[4] generate_summary()     --> 2-3 sentence case summary for agent handoff
      |
      v
[5] Assign team/agent      --> based on priority -> TEAMS -> AGENTS
      |
      v
[6] Calculate SLA          --> category.default_sla_hours * priority.sla_multiplier
      |
      v
[7] suggest_resolution()   --> actionable resolution recommendation
```

**Fallback:** When AWS credentials are not configured, a deterministic
rule-based fallback handles all AI calls — the system remains fully
functional without cloud access.

---

## Data Generation

```bash
# Full dataset (5000 customers, 8000 orders, 2000 complaints, 6000 messages)
python src/run.py

# Starter dataset (10%)
python src/run.py --scale 0.1

# Reproducibility check
python src/run.py --reproducibility-check
```

**Seed:** 20261022 — identical output on every run.

---

## Priority Rules (Deterministic)

| Rule  | Priority | Condition                                                   | SLA Multiplier |
|-------|----------|-------------------------------------------------------------|----------------|
| PR-01 | CRITICAL | Safety issue OR fraud (CAT-09) OR vulnerable customer       | 0.25x          |
| PR-02 | HIGH     | Negative sentiment AND order_value > 500 OR recurrence >= 3 | 0.50x          |
| PR-03 | MEDIUM   | Negative sentiment OR order_value 100-500                   | 1.00x          |
| PR-04 | LOW      | Neutral/positive sentiment AND order_value < 100            | 1.50x          |

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

## Edge Cases / Ground Truth

All injected anomalies are labelled with `issue_type` and exported
**only** to `output/ground_truth/` — never leaked into input features.

| issue_type                  | Description                                               |
|-----------------------------|-----------------------------------------------------------|
| missing_customer            | Complaint with no customer_id                             |
| resolution_before_complaint | Resolution timestamp precedes complaint created_at        |
| sla_pause_no_resume         | SLA paused but resumed_at is missing                      |
| safety_low_priority         | Critical safety issue assigned to General-Support queue   |
| survey_before_closure       | Survey submitted before resolution/closure                |
| repeat_not_linked           | Repeat complaint (recurrence>=2) with no parent_complaint_id |

---

## Validation Rules

| Rule             | Check                                                        |
|------------------|--------------------------------------------------------------|
| PK_DUPLICATE     | Primary key uniqueness across all entities                   |
| FK_*             | Foreign key integrity (customer, order, product, complaint)  |
| ENUM_*           | Allowed enum values (status, priority, severity, channel...) |
| DATE_ORDER       | updated_at >= created_at; delivery_date >= order_date        |
| DATE_SLA         | deadline_at = started_at + sla_hours                         |
| DATE_RESOLUTION  | resolved_at >= complaint.created_at                          |
| DATE_SURVEY      | submitted_at >= resolved_at                                  |
| LIFECYCLE_REOPEN | is_reopened=True requires parent_complaint_id                |
| ARITH_SLA        | deadline_at arithmetic reconciliation (< 1 min tolerance)    |
| PRIORITY_RULE    | Priority reproducible from documented rules                  |

---

## Reproducibility

```
scale=0.1  checksum: 17d67f684e96ac1966b0d323f88e585e  (Run 1 == Run 2)
scale=1.0  checksum: 8ae888d54b607313d4532ecf968b4863
```

---

## AWS Configuration

```bash
# Option 1: Environment variables
export AWS_ACCESS_KEY_ID=<your_key>
export AWS_SECRET_ACCESS_KEY=<your_secret>
export AWS_REGION=us-east-1
export BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0

# Option 2: IAM Role (recommended for production)
# Attach BedrockFullAccess or a scoped policy to your EC2/Lambda role
```

Without credentials, the system uses a rule-based fallback automatically.

---

## Source Manifest

| Field          | Value                                        |
|----------------|----------------------------------------------|
| Generator      | src/generator.py                             |
| AI Backend     | Amazon Bedrock — anthropic.claude-3-haiku    |
| API Framework  | FastAPI 0.111+                               |
| Seed           | 20261022                                     |
| External data  | None                                         |
| PII            | None (all synthetic)                         |
| License        | Synthetic — no restrictions                  |
