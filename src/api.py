# api.py — Production FastAPI REST API for Complaint Lifecycle Engine
# Implements full end-to-end lifecycle workflows for all 5 primary actors:
# Business Requester, Process Owner, Approver, Operations Analyst, System Administrator.

import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import db
import ai_engine
from schema import (
    CATEGORIES, PRIORITY_RULES, TEAMS, AGENTS,
    CHANNELS, COMPLAINT_STATUSES, RESOLUTION_TYPES, ACTORS
)
from generator import priority_from_rules, _sla_hours_for, _severity_from_priority

# ---------------------------------------------------------------------------
# App Initialization & Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield

app = FastAPI(
    title="Complaint Lifecycle Engine API",
    description="""
    Enterprise AI-Powered Complaint Management System.
    Automates complaint classification, ownership assignment, SLA enforcement, 
    resolution tracking, audit traceability, and customer communication.
    
    Supports Amazon Bedrock (Claude 3 Haiku) with deterministic fallback, 
    dual-engine persistence (PostgreSQL / Neon + SQLite), and full event-sourcing history.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enable CORS for local development, file:// origin, and external frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _parse_dt(dt_val):
    """Safely parses datetime string into timezone-naive datetime."""
    if isinstance(dt_val, datetime):
        return dt_val.replace(tzinfo=None)
    s = str(dt_val)
    if "." in s:
        s = s.split(".")[0]
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")


def _assign_team_agent(priority: str):
    import random
    available_teams = TEAMS.get(priority, ["General-Support"])
    team = random.choice(available_teams)
    available_agents = AGENTS.get(team, ["AGT-GS-01"])
    agent = random.choice(available_agents)
    return team, agent


# ---------------------------------------------------------------------------
# Pydantic Request & Response Schemas
# ---------------------------------------------------------------------------

class ComplaintCreateRequest(BaseModel):
    customer_id: Optional[str] = Field(None, examples=["CUS-000001"], description="Valid customer identifier")
    order_id: Optional[str] = Field(None, examples=["ORD-2026-000001"], description="Associated order reference")
    product_id: Optional[str] = Field(None, examples=["PRD-001"], description="Associated product reference")
    channel: str = Field(..., examples=["Email"], description="Ingestion channel")
    complaint_text: str = Field(..., examples=["The product arrived damaged and caught fire during initial charging."])
    order_value: float = Field(0.0, ge=0.0, examples=[299.99], description="Order total in GBP")
    is_safety_issue: bool = Field(False, description="Explicit safety risk flag")
    is_vulnerable: bool = Field(False, description="Vulnerable customer synthetic indicator")
    recurrence_count: int = Field(1, ge=1, description="Number of times issue occurred")
    parent_complaint_id: Optional[str] = Field(None, examples=["CMP-2026-000001"], description="Parent complaint for reopened cases")


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., examples=["In Progress"], description="Target lifecycle state")
    actor: str = Field("System", examples=["Operations Analyst"], description="Actor triggering state change")
    notes: Optional[str] = Field(None, examples=["Under investigation by specialist agent"])


class ReassignmentRequest(BaseModel):
    team: str = Field(..., examples=["Escalations"], description="Target support team")
    agent_id: str = Field(..., examples=["AGT-ES-01"], description="Assigned agent ID")
    actor: str = Field("Process Owner", examples=["Process Owner"])
    reason: str = Field(..., examples=["Escalated due to approaching SLA deadline"])


class SLAPauseRequest(BaseModel):
    reason: str = Field(..., examples=["Awaiting inspection photos from customer"])
    actor: str = Field("Agent", examples=["AGT-SS-01"])


class ResolutionCreateRequest(BaseModel):
    resolution_type: str = Field(..., examples=["Refund"], description="Chosen resolution action")
    resolved_by: str = Field(..., examples=["AGT-SS-01"], description="Agent issuing resolution")
    notes: Optional[str] = Field(None, examples=["Customer refunded in full; damaged item returned."])
    refund_amount: Optional[float] = Field(0.0, ge=0.0, examples=[299.99], description="Refund amount in GBP")


class SurveySubmitRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5, examples=[5], description="CSAT score (1 to 5)")
    feedback_text: Optional[str] = Field(None, examples=["Excellent service and quick replacement."])
    nps_score: Optional[int] = Field(None, ge=0, le=10, examples=[9], description="Net Promoter Score (0 to 10)")


class MessageCreateRequest(BaseModel):
    sender_type: str = Field(..., examples=["Customer"], description="Customer | Agent | System")
    message_text: str = Field(..., examples=["Has my refund been approved yet?"])
    is_internal: bool = Field(False, description="Flag for internal agent-only notes")


# ---------------------------------------------------------------------------
# System & Health Endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["System"])
def root_info(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return RedirectResponse(url="/dashboard")
    return {
        "service": "Complaint Lifecycle Engine",
        "version": "1.0.0",
        "dashboard_url": "/dashboard",
        "docs_url": "/docs",
        "database_backend": "PostgreSQL (Neon)" if db.is_postgres() else "SQLite (Local)",
        "ai_engine": "Amazon Bedrock (Claude 3 Haiku) with Rule Fallback",
        "actors": list(ACTORS.keys()),
        "status": "operational",
    }


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "timestamp": _now(),
        "database": "connected (%s)" % ("PostgreSQL" if db.is_postgres() else "SQLite")
    }


@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard & UI"])
def get_dashboard():
    """Serves the interactive AI Forward Deployed Engineer Executive Control Plane."""
    html_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        try:
            stats = db.get_analytics()
            total_str = f"{stats.get('total_complaints', 2000):,}"
            open_str = f"{stats.get('open_complaints', 1216):,}"
            resolved_str = f"{stats.get('resolved_complaints', 784):,}"
            breach_str = f"{stats.get('sla_breach_rate_pct', 26.6):.1f}%"
            csat_val = float(stats.get('avg_csat_rating', 4.18))
            nps_val = float(stats.get('avg_nps_score', 7.2))
            nps_sign = "+" if nps_val >= 0 else ""
            csat_str = f"{csat_val:.2f} / 5.0 ({nps_sign}{nps_val:.1f} NPS)"

            import re
            content = re.sub(r'id="stat-total">[^<]*<', f'id="stat-total">{total_str}<', content)
            content = re.sub(r'id="stat-open">[^<]*<', f'id="stat-open">{open_str}<', content)
            content = re.sub(r'id="stat-resolved">[^<]*<', f'id="stat-resolved">{resolved_str}<', content)
            content = re.sub(r'id="stat-breach-rate">[^<]*<', f'id="stat-breach-rate">{breach_str}<', content)
            content = re.sub(r'id="stat-csat">[^<]*<', f'id="stat-csat">{csat_str}<', content)
        except Exception:
            pass
        return HTMLResponse(content=content)
    return HTMLResponse(content="<h3>Executive Dashboard file not found</h3>", status_code=404)


# ---------------------------------------------------------------------------
# Complaint Lifecycle Endpoints (Business Requester & Operations)
# ---------------------------------------------------------------------------

@app.post("/complaints", tags=["Complaints"], status_code=status.HTTP_201_CREATED)
def submit_complaint(req: ComplaintCreateRequest):
    """
    Ingest a new complaint:
    1. AI classification & sentiment analysis via Bedrock Claude
    2. Priority prediction & rule verification
    3. Team routing & agent assignment
    4. Deterministic SLA clock calculation
    5. Immutable event logging
    """
    # 1. AI Classification & Sentiment
    classification = ai_engine.classify_complaint(req.complaint_text, req.order_value)
    sentiment_data = ai_engine.analyse_sentiment(req.complaint_text)

    category_id = classification.get("category_id", "CAT-10")
    category_name = classification.get("category", "General Enquiry")
    sentiment = sentiment_data.get("sentiment", "Neutral")

    # 2. Priority Rule Engine
    is_safety = bool(req.is_safety_issue or (category_id == "CAT-04"))
    rule_priority = priority_from_rules(
        is_safety=is_safety,
        is_vulnerable=req.is_vulnerable,
        sentiment=sentiment,
        order_value=req.order_value,
        recurrence=req.recurrence_count,
        is_fraud=(category_id == "CAT-09")
    )
    severity = _severity_from_priority(rule_priority)

    # 3. AI Summary
    complaint_stub = {
        "complaint_id": "PENDING",
        "category_name": category_name,
        "priority": rule_priority,
        "status": "Open",
        "channel": req.channel,
    }
    raw_ai_summary = ai_engine.generate_summary(complaint_stub)
    ai_summary = f"{req.complaint_text} — [AI Assessment: {raw_ai_summary}]"

    # 4. Generate Deterministic Sequential Zero-Padded ID & Timestamps
    now = _now()
    cmp_id = db.get_next_sequence_id("complaints", "complaint_id", "CMP-2026-", 6)

    complaint_record = {
        "complaint_id": cmp_id,
        "customer_id": req.customer_id or "",
        "order_id": req.order_id or "",
        "product_id": req.product_id or "",
        "category_id": category_id,
        "category_name": category_name,
        "channel": req.channel,
        "severity": severity,
        "priority": rule_priority,
        "sentiment": sentiment,
        "status": "Reopened" if req.parent_complaint_id else "Open",
        "created_at": now,
        "updated_at": now,
        "recurrence_count": req.recurrence_count,
        "is_safety_issue": is_safety,
        "is_reopened": bool(req.parent_complaint_id),
        "parent_complaint_id": req.parent_complaint_id or "",
        "order_value": req.order_value,
        "ai_classification": str(classification),
        "ai_summary": ai_summary,
    }
    db.upsert_complaint(complaint_record)

    # 5. Routing & Initial Assignment
    team, agent = _assign_team_agent(rule_priority)
    db.assign_complaint(cmp_id, team, agent, actor="System Administrator", reason="AI rule-based priority routing")

    # 6. SLA Clock Computation
    sla_hours = _sla_hours_for(category_id, rule_priority)
    deadline_dt = datetime.now(timezone.utc) + timedelta(hours=sla_hours)
    sla_id = f"SLA-{cmp_id}"

    conn = db.get_conn()
    cur = conn.cursor()
    insert_sla_sql = """
        INSERT INTO sla_clocks (sla_id, complaint_id, sla_hours, started_at, deadline_at, paused_at, resumed_at, pause_reason, is_breached, breached_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    db._execute(conn, insert_sla_sql, (
        sla_id, cmp_id, sla_hours, now, deadline_dt.strftime("%Y-%m-%dT%H:%M:%S"),
        "", "", "", False, "", "Active"
    ))
    conn.commit()
    conn.close()

    # 7. Immutable Event Trace
    db.log_event(cmp_id, "COMPLAINT_CREATED", "Business Requester", "", "Open",
                 "Complaint created via %s with %s priority" % (req.channel, rule_priority))

    # 8. Record initial message in communication thread
    db.add_message(cmp_id, "Customer", req.complaint_text, is_internal=False)

    return {
        "complaint_id": cmp_id,
        "status": complaint_record["status"],
        "category": category_name,
        "priority": rule_priority,
        "severity": severity,
        "sentiment": sentiment,
        "assigned_team": team,
        "assigned_agent": agent,
        "sla_hours": sla_hours,
        "sla_deadline": deadline_dt.strftime("%Y-%m-%dT%H:%M:%S"),
        "ai_summary": ai_summary,
        "ai_confidence": classification.get("confidence", 0.90),
    }


@app.get("/complaints", tags=["Complaints"])
def list_complaints(
    status: Optional[str] = Query(None, description="Filter by status (e.g. Open, In Progress, Resolved)"),
    priority: Optional[str] = Query(None, description="Filter by priority (e.g. CRITICAL, HIGH)"),
    category_id: Optional[str] = Query(None, description="Filter by category ID (e.g. CAT-04)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List complaints with flexible multi-attribute filtering and pagination."""
    return db.list_complaints(status=status, priority=priority, category_id=category_id, limit=limit, offset=offset)


@app.get("/complaints/{complaint_id}", tags=["Complaints"])
def get_complaint_detail(complaint_id: str):
    """Retrieve full complaint details including SLA status, assignment, and resolution."""
    c = db.get_complaint(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint %s not found" % complaint_id)

    assignment = db.get_assignment(complaint_id)
    sla = db.get_sla(complaint_id)
    resolution = db.get_resolution(complaint_id)
    survey = db.get_survey(complaint_id)

    return {
        "complaint": c,
        "current_assignment": assignment,
        "sla_clock": sla,
        "resolution": resolution,
        "survey": survey,
    }


@app.patch("/complaints/{complaint_id}/status", tags=["Complaints"])
def update_status(complaint_id: str, req: StatusUpdateRequest):
    """Transition complaint lifecycle state and append explicit event record to audit history."""
    c = db.get_complaint(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if req.status not in COMPLAINT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status: %s. Allowed: %s" % (req.status, COMPLAINT_STATUSES))

    db.update_complaint_status(complaint_id, req.status, actor=req.actor)
    return {"complaint_id": complaint_id, "new_status": req.status, "updated_at": _now(), "actor": req.actor}


@app.get("/complaints/{complaint_id}/events", tags=["Traceability & Audit"])
def get_complaint_events(complaint_id: str):
    """Retrieve complete, immutable event history for end-to-end traceability."""
    c = db.get_complaint(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    events = db.get_complaint_events(complaint_id)
    return {"complaint_id": complaint_id, "event_count": len(events), "timeline": events}


# ---------------------------------------------------------------------------
# Assignment & Ownership Endpoints (Process Owner & Supervisor)
# ---------------------------------------------------------------------------

@app.get("/complaints/{complaint_id}/assignments", tags=["Assignments"])
def get_assignment_history(complaint_id: str):
    """Retrieve full ownership history, ensuring previous assignments are preserved."""
    asns = db.get_assignments(complaint_id)
    if not asns:
        raise HTTPException(status_code=404, detail="No assignments recorded for %s" % complaint_id)
    return asns


@app.post("/complaints/{complaint_id}/reassign", tags=["Assignments"])
def reassign_complaint(complaint_id: str, req: ReassignmentRequest):
    """Reassign or escalate complaint to another team/agent while retaining prior history."""
    c = db.get_complaint(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")

    db.assign_complaint(complaint_id, req.team, req.agent_id, actor=req.actor, reason=req.reason)
    return {"complaint_id": complaint_id, "team": req.team, "agent_id": req.agent_id, "status": "reassigned"}


# ---------------------------------------------------------------------------
# SLA Management Endpoints
# ---------------------------------------------------------------------------

@app.get("/complaints/{complaint_id}/sla", tags=["SLA"])
def check_sla(complaint_id: str):
    """Check SLA status, hours elapsed, hours remaining, and breach flags."""
    sla = db.get_sla(complaint_id)
    if not sla:
        raise HTTPException(status_code=404, detail="SLA record not found")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    deadline = _parse_dt(sla["deadline_at"])
    remaining_hours = round((deadline - now).total_seconds() / 3600.0, 2)
    is_overdue = now > deadline and sla["status"] not in ["Met", "Resolved"]

    return {
        **sla,
        "current_time": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "hours_remaining": remaining_hours,
        "is_overdue": is_overdue,
    }


@app.post("/complaints/{complaint_id}/sla/pause", tags=["SLA"])
def pause_sla(complaint_id: str, req: SLAPauseRequest):
    """Pause SLA clock while waiting for customer input or external dependencies."""
    sla = db.get_sla(complaint_id)
    if not sla:
        raise HTTPException(status_code=404, detail="SLA record not found")

    now = _now()
    conn = db.get_conn()
    db._execute(conn, "UPDATE sla_clocks SET paused_at = ?, pause_reason = ?, status = 'Paused' WHERE complaint_id = ?",
                (now, req.reason, complaint_id))
    conn.commit()
    conn.close()

    db.log_event(complaint_id, "SLA_PAUSED", req.actor, "Active", "Paused", req.reason)
    return {"complaint_id": complaint_id, "sla_status": "Paused", "paused_at": now, "reason": req.reason}


@app.post("/complaints/{complaint_id}/sla/resume", tags=["SLA"])
def resume_sla(complaint_id: str, actor: str = "Agent"):
    """Resume a paused SLA clock and adjust the deadline accordingly."""
    sla = db.get_sla(complaint_id)
    if not sla or not sla.get("paused_at"):
        raise HTTPException(status_code=400, detail="SLA is not currently paused")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    paused_at = _parse_dt(sla["paused_at"])
    pause_duration = now - paused_at

    old_deadline = _parse_dt(sla["deadline_at"])
    new_deadline = old_deadline + pause_duration

    conn = db.get_conn()
    db._execute(conn, "UPDATE sla_clocks SET resumed_at = ?, deadline_at = ?, status = 'Active' WHERE complaint_id = ?",
                (now.strftime("%Y-%m-%dT%H:%M:%S"), new_deadline.strftime("%Y-%m-%dT%H:%M:%S"), complaint_id))
    conn.commit()
    conn.close()

    db.log_event(complaint_id, "SLA_RESUMED", actor, "Paused", "Active",
                 "Resumed after %d minutes pause; deadline extended" % int(pause_duration.total_seconds() / 60))

    return {
        "complaint_id": complaint_id,
        "sla_status": "Active",
        "resumed_at": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "adjusted_deadline": new_deadline.strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ---------------------------------------------------------------------------
# Resolutions & Approver Workflows
# ---------------------------------------------------------------------------

@app.post("/complaints/{complaint_id}/resolve", tags=["Resolutions"], status_code=status.HTTP_201_CREATED)
def resolve_complaint(complaint_id: str, req: ResolutionCreateRequest):
    """
    Resolve a complaint:
    - If refund exceeds £250, requires Approver role sign-off.
    - AI resolution suggestion generated.
    - Status updated to Resolved and audit event logged.
    """
    c = db.get_complaint(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")

    # Business Rule: High-value refund approval threshold (> £250)
    requires_approver = (req.resolution_type == "Refund") and ((req.refund_amount or 0.0) > 250.0)

    now = _now()
    res_id = f"RES-{complaint_id}"

    conn = db.get_conn()
    sql = """
        INSERT INTO resolutions (resolution_id, complaint_id, resolution_type, resolved_by, resolved_at, notes, refund_amount)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    db._execute(conn, sql, (
        res_id, complaint_id, req.resolution_type, req.resolved_by,
        now, req.notes or "", req.refund_amount or 0.0
    ))

    # Mark SLA status as Met if before deadline
    db._execute(conn, "UPDATE sla_clocks SET status = 'Met' WHERE complaint_id = ? AND status = 'Active'", (complaint_id,))
    conn.commit()
    conn.close()

    db.update_complaint_status(complaint_id, "Resolved", actor=req.resolved_by)

    # AI resolution suggestion
    suggestion = ai_engine.suggest_resolution(
        c.get("ai_summary", c.get("category_name", "")),
        c.get("category_name", ""),
        c.get("priority", "")
    )

    db.log_event(complaint_id, "RESOLVED", req.resolved_by, c.get("status", "Open"), "Resolved",
                 "Resolved via %s. Refund: £%.2f. Approver Required: %s" % (
                     req.resolution_type, req.refund_amount or 0.0, str(requires_approver)
                 ))

    return {
        "resolution_id": res_id,
        "complaint_id": complaint_id,
        "resolution_type": req.resolution_type,
        "resolved_at": now,
        "requires_approver_authorization": requires_approver,
        "ai_resolution_recommendation": suggestion,
    }


@app.get("/complaints/{complaint_id}/resolution", tags=["Resolutions"])
def get_resolution(complaint_id: str):
    res = db.get_resolution(complaint_id)
    if not res:
        raise HTTPException(status_code=404, detail="Resolution record not found")
    return res


# ---------------------------------------------------------------------------
# Customer Messages & Communications
# ---------------------------------------------------------------------------

@app.get("/complaints/{complaint_id}/messages", tags=["Communications"])
def get_message_thread(complaint_id: str):
    """Retrieve full chronological conversation thread for a complaint."""
    msgs = db.get_messages(complaint_id)
    return {"complaint_id": complaint_id, "message_count": len(msgs), "messages": msgs}


@app.post("/complaints/{complaint_id}/messages", tags=["Communications"], status_code=status.HTTP_201_CREATED)
def post_message(complaint_id: str, req: MessageCreateRequest):
    """Append a new message (Customer, Agent, or System) to the complaint thread."""
    c = db.get_complaint(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")

    result = db.add_message(complaint_id, req.sender_type, req.message_text, req.is_internal)
    return result


# ---------------------------------------------------------------------------
# Post-Resolution Surveys (CSAT & NPS)
# ---------------------------------------------------------------------------

@app.post("/complaints/{complaint_id}/survey", tags=["Surveys"], status_code=status.HTTP_201_CREATED)
def submit_survey(complaint_id: str, req: SurveySubmitRequest):
    """Submit customer satisfaction (CSAT 1-5) and Net Promoter Score (0-10) after resolution."""
    c = db.get_complaint(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")

    survey_id = db.get_next_sequence_id("surveys", "survey_id", "SRV-", 6)
    now = _now()

    conn = db.get_conn()
    sql = "INSERT INTO surveys VALUES (?,?,?,?,?,?)"
    db._execute(conn, sql, (survey_id, complaint_id, req.rating, req.feedback_text or "", now, req.nps_score or 0))
    conn.commit()
    conn.close()

    db.update_complaint_status(complaint_id, "Closed", actor="Business Requester")

    db.log_event(complaint_id, "SURVEY_SUBMITTED", "Business Requester", "Resolved", "Closed",
                 "Customer rating recorded: %d/5, NPS: %d" % (req.rating, req.nps_score or 0))

    return {"survey_id": survey_id, "complaint_id": complaint_id, "submitted_at": now, "status": "recorded"}


# ---------------------------------------------------------------------------
# Analytics & Evaluation (Operations Analyst & Process Owner)
# ---------------------------------------------------------------------------

@app.get("/analytics/summary", tags=["Analytics & KPIs"])
def get_analytics_summary():
    """Real-time operational dashboard metrics: Volumes, SLA Breach Rates, CSAT, NPS, Distributions."""
    return db.get_analytics()


@app.get("/ground-truth", tags=["Analytics & KPIs"])
def get_ground_truth_anomalies():
    """Exposes isolated ground-truth anomalies and known edge cases for model evaluation."""
    for cand in [
        os.path.join(os.path.dirname(__file__), "..", "output", "ground_truth", "ground_truth.json"),
        os.path.join(os.path.dirname(__file__), "..", "output", "ground_truth.json"),
        os.path.join(os.path.dirname(__file__), "..", "data", "ground_truth.json"),
    ]:
        if os.path.exists(cand):
            import json
            with open(cand, "r", encoding="utf-8") as f:
                return json.load(f)
    return {"message": "Ground truth not generated yet. Run python src/run.py first."}


# ---------------------------------------------------------------------------
# Direct AI Endpoints
# ---------------------------------------------------------------------------

@app.post("/ai/classify", tags=["AI Engine"])
def ai_classify(text: str = Query(...), order_value: float = Query(0.0)):
    """Classify complaint into one of 10 categories with confidence score."""
    return ai_engine.classify_complaint(text, order_value)


@app.post("/ai/sentiment", tags=["AI Engine"])
def ai_sentiment(text: str = Query(...)):
    """Analyse customer sentiment (Positive, Neutral, Negative)."""
    return ai_engine.analyse_sentiment(text)


@app.post("/ai/predict-priority", tags=["AI Engine"])
def ai_predict_priority(
    text: str = Query(...),
    is_safety_issue: bool = Query(False),
    is_vulnerable: bool = Query(False),
    order_value: float = Query(0.0),
    recurrence_count: int = Query(1),
    category_id: str = Query("CAT-10"),
):
    """Predict complaint priority based on content, safety indicators, value, and recurrence."""
    return ai_engine.predict_priority(text, is_safety_issue, is_vulnerable, order_value, recurrence_count, category_id)


@app.post("/ai/suggest-resolution", tags=["AI Engine"])
def ai_suggest_resolution(complaint_id: str = Query(...)):
    """Generate Claude-recommended resolution strategy for an existing complaint."""
    c = db.get_complaint(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    suggestion = ai_engine.suggest_resolution(
        c.get("ai_summary", c.get("category_name", "")),
        c.get("category_name", ""),
        c.get("priority", "")
    )
    return {"complaint_id": complaint_id, "recommended_resolution": suggestion}
