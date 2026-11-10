# db.py — SQLite persistence layer
# Stores complaints, assignments, SLA clocks and resolutions with full history

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "output", "complaints.db"))


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    cur  = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS complaints (
            complaint_id        TEXT PRIMARY KEY,
            customer_id         TEXT,
            order_id            TEXT,
            product_id          TEXT,
            category_id         TEXT,
            category_name       TEXT,
            channel             TEXT,
            severity            TEXT,
            priority            TEXT,
            sentiment           TEXT,
            status              TEXT,
            created_at          TEXT,
            updated_at          TEXT,
            recurrence_count    INTEGER,
            is_safety_issue     INTEGER,
            is_reopened         INTEGER,
            parent_complaint_id TEXT,
            order_value         REAL,
            ai_classification   TEXT,
            ai_summary          TEXT
        );

        CREATE TABLE IF NOT EXISTS assignments (
            assignment_id TEXT PRIMARY KEY,
            complaint_id  TEXT,
            team          TEXT,
            agent_id      TEXT,
            assigned_at   TEXT,
            is_current    INTEGER,
            reason        TEXT,
            FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id)
        );

        CREATE TABLE IF NOT EXISTS sla_clocks (
            sla_id        TEXT PRIMARY KEY,
            complaint_id  TEXT,
            sla_hours     REAL,
            started_at    TEXT,
            deadline_at   TEXT,
            paused_at     TEXT,
            resumed_at    TEXT,
            pause_reason  TEXT,
            is_breached   INTEGER,
            breached_at   TEXT,
            status        TEXT,
            FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id)
        );

        CREATE TABLE IF NOT EXISTS resolutions (
            resolution_id   TEXT PRIMARY KEY,
            complaint_id    TEXT,
            resolution_type TEXT,
            resolved_by     TEXT,
            resolved_at     TEXT,
            notes           TEXT,
            refund_amount   REAL,
            FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            message_id    TEXT PRIMARY KEY,
            complaint_id  TEXT,
            sender_type   TEXT,
            message_text  TEXT,
            sent_at       TEXT,
            is_internal   INTEGER,
            FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id)
        );

        CREATE TABLE IF NOT EXISTS surveys (
            survey_id     TEXT PRIMARY KEY,
            complaint_id  TEXT,
            rating        INTEGER,
            feedback_text TEXT,
            submitted_at  TEXT,
            nps_score     INTEGER,
            FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id)
        );
    """)
    conn.commit()
    conn.close()
    print("[DB] Initialised: %s" % DB_PATH)


def upsert_complaint(c: dict):
    conn = get_conn()
    conn.execute("""
        INSERT INTO complaints VALUES (
            :complaint_id, :customer_id, :order_id, :product_id,
            :category_id, :category_name, :channel, :severity, :priority,
            :sentiment, :status, :created_at, :updated_at, :recurrence_count,
            :is_safety_issue, :is_reopened, :parent_complaint_id, :order_value,
            :ai_classification, :ai_summary
        ) ON CONFLICT(complaint_id) DO UPDATE SET
            status           = excluded.status,
            updated_at       = excluded.updated_at,
            priority         = excluded.priority,
            ai_classification = excluded.ai_classification,
            ai_summary       = excluded.ai_summary
    """, {**c, "ai_classification": c.get("ai_classification", ""), "ai_summary": c.get("ai_summary", "")})
    conn.commit()
    conn.close()


def bulk_load(data: dict):
    conn = get_conn()
    cur  = conn.cursor()

    for c in data.get("complaints", []):
        cur.execute("""
            INSERT OR IGNORE INTO complaints VALUES (
                ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
            )""", (
            c["complaint_id"], c.get("customer_id",""), c.get("order_id",""),
            c.get("product_id",""), c["category_id"], c.get("category_name",""),
            c["channel"], c["severity"], c["priority"], c["sentiment"],
            c["status"], c["created_at"], c["updated_at"], c["recurrence_count"],
            int(c["is_safety_issue"]), int(c["is_reopened"]),
            c.get("parent_complaint_id",""), c.get("order_value", 0),
            "", ""
        ))

    for a in data.get("assignments", []):
        cur.execute("""
            INSERT OR IGNORE INTO assignments VALUES (?,?,?,?,?,?,?)""", (
            a["assignment_id"], a["complaint_id"], a["team"],
            a["agent_id"], a["assigned_at"], int(a["is_current"]), a.get("reason","")
        ))

    for s in data.get("sla_clocks", []):
        cur.execute("""
            INSERT OR IGNORE INTO sla_clocks VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (
            s["sla_id"], s["complaint_id"], s["sla_hours"],
            s["started_at"], s["deadline_at"], s.get("paused_at",""),
            s.get("resumed_at",""), s.get("pause_reason",""),
            int(s["is_breached"]), s.get("breached_at",""), s["status"]
        ))

    for r in data.get("resolutions", []):
        cur.execute("""
            INSERT OR IGNORE INTO resolutions VALUES (?,?,?,?,?,?,?)""", (
            r["resolution_id"], r["complaint_id"], r["resolution_type"],
            r["resolved_by"], r["resolved_at"], r.get("notes",""),
            r.get("refund_amount") or 0
        ))

    for m in data.get("messages", []):
        cur.execute("""
            INSERT OR IGNORE INTO messages VALUES (?,?,?,?,?,?)""", (
            m["message_id"], m["complaint_id"], m["sender_type"],
            m["message_text"], m["sent_at"], int(m["is_internal"])
        ))

    for sv in data.get("surveys", []):
        cur.execute("""
            INSERT OR IGNORE INTO surveys VALUES (?,?,?,?,?,?)""", (
            sv["survey_id"], sv["complaint_id"], sv["rating"],
            sv.get("feedback_text",""), sv["submitted_at"], sv.get("nps_score", 0)
        ))

    conn.commit()
    conn.close()
    print("[DB] Bulk load complete.")


def get_complaint(complaint_id: str):
    conn = get_conn()
    row  = conn.execute("SELECT * FROM complaints WHERE complaint_id=?", (complaint_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_complaints(status: str = None, priority: str = None, limit: int = 50):
    conn  = get_conn()
    query = "SELECT * FROM complaints WHERE 1=1"
    params = []
    if status:
        query += " AND status=?";   params.append(status)
    if priority:
        query += " AND priority=?"; params.append(priority)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_sla(complaint_id: str):
    conn = get_conn()
    row  = conn.execute("SELECT * FROM sla_clocks WHERE complaint_id=?", (complaint_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_assignment(complaint_id: str):
    conn = get_conn()
    row  = conn.execute(
        "SELECT * FROM assignments WHERE complaint_id=? AND is_current=1", (complaint_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_resolution(complaint_id: str):
    conn = get_conn()
    row  = conn.execute("SELECT * FROM resolutions WHERE complaint_id=?", (complaint_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_complaint_status(complaint_id: str, status: str):
    conn = get_conn()
    conn.execute(
        "UPDATE complaints SET status=?, updated_at=? WHERE complaint_id=?",
        (status, datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), complaint_id)
    )
    conn.commit()
    conn.close()
