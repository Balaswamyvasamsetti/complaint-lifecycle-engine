# api.py — FastAPI REST API for the Complaint Lifecycle Engine
# Exposes: classify, assign, SLA check, resolve, survey, list endpoints

import os
import sys
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

import db
import ai_engine
from schema import CATEGORIES, PRIORITY_RULES, TEAMS, AGENTS
from generator import priority_from_rules, _sla_hours_for, _severity_from_priority

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Complaint Lifecycle Engine",
    description="AI-powered complaint management: classify, assign, enforce SLAs, track resolution. "
                "Powered by Amazon Bedrock (Claude) + FastAPI + SQLite.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

@app.on_event("startup")
def startup():
    db.init_db()

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ComplaintRequest(BaseModel):
    customer_id:  Optional[str] = Field(None,  example="CUS-000001")
    order_id:     Optional[str] = Field(None,  example="ORD-2026-000001")
    product_id:   Optional[str] = Field(None,  example="PRD-001")
    channel:      str           = Field(...,   example="Email")
    complaint_text: str         = Field(...,   example="My order arrived damaged and I want a refund.")
    order_value:  float         = Field(0.0,   example=299.99)
    is_safety_issue: bool       = Field(False)
    is_vulnerable:   bool       = Field(False)
    recurrence_count: int       = Field(1,     ge=1)
    parent_complaint_id: Optional[str] = Field(None)


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., example="Resolved")


class ResolutionRequest(BaseModel):
    resolution_type: str         = Field(..., example="Refund")
    resolved_by:     str         = Field(..., example="AGT-SS-01")
    notes:           Optional[str] = Field(None)
    refund_amount:   Optional[float] = Field(None)


class SurveyRequest(BaseModel):
    rating:        int            = Field(..., ge=1, le=5, example=4)
    feedback_text: Optional[str]  = Field(None)
    nps_score:     Optional[int]  = Field(None, ge=0, le=10)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _now():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

def _assign_team_agent(priority: str):
    import random
    team  = random.choice(TEAMS[priority])
    agent = random.choice(AGENTS[team])
    return team, agent

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
def root():
    return {
        "service": "Complaint Lifecycle Engine",
        "version": "1.0.0",
        "ai_backend": "Amazon Bedrock (Claude)",
        "status": "running",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "timestamp": _now()}


# -- Complaints ---------------------------------------------------------------

@app.post("/complaints", tags=["Complaints"], status_code=201)
def create_complaint(req: ComplaintRequest):
    """
    Submit a new complaint. AI engine (Amazon Bedrock) classifies category,
    analyses sentiment, predicts priority, assigns team/agent and calculates SLA.
    """
    # AI: classify + sentiment
    classification = ai_engine.classify_complaint(req.complaint_text, req.order_value)
    sentiment_data = ai_engine.analyse_sentiment(req.complaint_text)

    category_id   = classification.get("category_id", "CAT-10")
    category_name = classification.get("category", "General Enquiry")
    sentiment     = sentiment_data.get("sentiment", "Neutral")

    # AI: priority prediction
    priority_data = ai_engine.predict_priority(
        req.complaint_text, req.is_safety_issue, req.is_vulnerable,
        req.order_value, req.recurrence_count, category_id
    )
    priority = priority_data.get("priority", priority_from_rules(
        req.is_safety_issue, req.is_vulnerable, sentiment,
        req.order_value, req.recurrence_count, category_id == "CAT-09"
    ))
    severity = _severity_from_priority(priority)

    # AI: summary
    complaint_stub = {
        "complaint_id": "PENDING", "category_name": category_name,
        "priority": priority, "status": "Open", "channel": req.channel,
    }
    ai_summary = ai_engine.generate_summary(complaint_stub)

    # IDs and timestamps
    year         = datetime.utcnow().year
    complaint_id = "CMP-%d-%s" % (year, uuid.uuid4().hex[:6].upper())
    now          = _now()

    complaint = {
        "complaint_id":        complaint_id,
        "customer_id":         req.customer_id or "",
        "order_id":            req.order_id    or "",
        "product_id":          req.product_id  or "",
        "category_id":         category_id,
        "category_name":       category_name,
        "channel":             req.channel,
        "severity":            severity,
        "priority":            priority,
        "sentiment":           sentiment,
        "status":              "Open",
        "created_at":          now,
        "updated_at":          now,
        "recurrence_count":    req.recurrence_count,
        "is_safety_issue":     req.is_safety_issue,
        "is_reopened":         bool(req.parent_complaint_id),
        "parent_complaint_id": req.parent_complaint_id or "",
        "order_value":         req.order_value,
        "ai_classification":   str(classification),
        "ai_summary":          ai_summary,
    }
    db.upsert_complaint(complaint)

    # Assignment
    team, agent = _assign_team_agent(priority)
    assignment_id = "ASN-%s" % uuid.uuid4().hex[:6].upper()
    db.get_conn()  # ensure open
    conn = db.get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO assignments VALUES (?,?,?,?,?,?,?)",
        (assignment_id, complaint_id, team, agent, now, 1, "AI-driven initial assignment")
    )
    conn.commit()
    conn.close()

    # SLA clock
    sla_h    = _sla_hours_for(category_id, priority)
    deadline = (datetime.utcnow() + timedelta(hours=sla_h)).strftime("%Y-%m-%dT%H:%M:%S")
    sla_id   = "SLA-%s" % complaint_id
    conn = db.get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO sla_clocks VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (sla_id, complaint_id, sla_h, now, deadline, "", "", "", 0, "", "Active")
    )
    conn.commit()
    conn.close()

    return {
        "complaint_id":    complaint_id,
        "category":        category_name,
        "category_id":     category_id,
        "sentiment":       sentiment,
        "priority":        priority,
        "severity":        severity,
        "assigned_team":   team,
        "assigned_agent":  agent,
        "sla_deadline":    deadline,
        "sla_hours":       sla_h,
        "ai_summary":      ai_summary,
        "ai_confidence":   classification.get("confidence", 0.0),
    }


@app.get("/complaints", tags=["Complaints"])
def list_complaints(
    status:   Optional[str] = Query(None, example="Open"),
    priority: Optional[str] = Query(None, example="HIGH"),
    limit:    int            = Query(50, ge=1, le=500),
):
    return db.list_complaints(status=status, priority=priority, limit=limit)


@app.get("/complaints/{complaint_id}", tags=["Complaints"])
def get_complaint(complaint_id: str):
    c = db.get_complaint(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return c


@app.patch("/complaints/{complaint_id}/status", tags=["Complaints"])
def update_status(complaint_id: str, req: StatusUpdateRequest):
    c = db.get_complaint(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    db.update_complaint_status(complaint_id, req.status)
    return {"complaint_id": complaint_id, "status": req.status, "updated_at": _now()}


# -- Assignments --------------------------------------------------------------

@app.get("/complaints/{complaint_id}/assignment", tags=["Assignments"])
def get_assignment(complaint_id: str):
    a = db.get_assignment(complaint_id)
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return a


# -- SLA ----------------------------------------------------------------------

@app.get("/complaints/{complaint_id}/sla", tags=["SLA"])
def get_sla(complaint_id: str):
    s = db.get_sla(complaint_id)
    if not s:
        raise HTTPException(status_code=404, detail="SLA record not found")
    now      = datetime.utcnow()
    deadline = datetime.strptime(s["deadline_at"], "%Y-%m-%dT%H:%M:%S")
    s["time_remaining_hours"] = round((deadline - now).total_seconds() / 3600, 2)
    s["is_overdue"]           = now > deadline
    return s


# -- Resolutions --------------------------------------------------------------

@app.post("/complaints/{complaint_id}/resolve", tags=["Resolutions"], status_code=201)
def resolve_complaint(complaint_id: str, req: ResolutionRequest):
    c = db.get_complaint(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")

    resolution_id = "RES-%s" % complaint_id
    now           = _now()
    conn = db.get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO resolutions VALUES (?,?,?,?,?,?,?)",
        (resolution_id, complaint_id, req.resolution_type,
         req.resolved_by, now, req.notes or "", req.refund_amount or 0)
    )
    conn.commit()
    conn.close()
    db.update_complaint_status(complaint_id, "Resolved")

    # AI resolution suggestion
    suggestion = ai_engine.suggest_resolution(
        c.get("ai_summary", ""), c.get("category_name", ""), c.get("priority", "")
    )

    return {
        "resolution_id":   resolution_id,
        "complaint_id":    complaint_id,
        "resolution_type": req.resolution_type,
        "resolved_at":     now,
        "ai_suggestion":   suggestion,
    }


@app.get("/complaints/{complaint_id}/resolution", tags=["Resolutions"])
def get_resolution(complaint_id: str):
    r = db.get_resolution(complaint_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resolution not found")
    return r


# -- Surveys ------------------------------------------------------------------

@app.post("/complaints/{complaint_id}/survey", tags=["Surveys"], status_code=201)
def submit_survey(complaint_id: str, req: SurveyRequest):
    c = db.get_complaint(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    survey_id = "SRV-%s" % uuid.uuid4().hex[:6].upper()
    now       = _now()
    conn = db.get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO surveys VALUES (?,?,?,?,?,?)",
        (survey_id, complaint_id, req.rating,
         req.feedback_text or "", now, req.nps_score or 0)
    )
    conn.commit()
    conn.close()
    return {"survey_id": survey_id, "complaint_id": complaint_id, "submitted_at": now}


# -- AI direct endpoints ------------------------------------------------------

@app.post("/ai/classify", tags=["AI"])
def ai_classify(text: str = Query(...), order_value: float = Query(0.0)):
    """Classify complaint text using Amazon Bedrock (Claude)."""
    return ai_engine.classify_complaint(text, order_value)


@app.post("/ai/sentiment", tags=["AI"])
def ai_sentiment(text: str = Query(...)):
    """Analyse complaint sentiment using Amazon Bedrock (Claude)."""
    return ai_engine.analyse_sentiment(text)


@app.post("/ai/suggest-resolution", tags=["AI"])
def ai_suggest(complaint_id: str = Query(...)):
    """Get AI-powered resolution suggestion for an existing complaint."""
    c = db.get_complaint(complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    suggestion = ai_engine.suggest_resolution(
        c.get("ai_summary", c.get("category_name", "")),
        c.get("category_name", ""),
        c.get("priority", ""),
    )
    return {"complaint_id": complaint_id, "suggestion": suggestion}
